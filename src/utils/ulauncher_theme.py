"""Ulauncher theme (manifest.json + theme.css) helpers."""
from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

import json5

logger = logging.getLogger(__name__)


def list_ulauncher_templates(folder: str | Path) -> list[str]:
    """Return absolute paths of ulauncher template directories in `folder`.

    A template is a directory containing a manifest.json.
    """
    try:
        p = Path(folder)
        if not p.is_dir():
            return []

        dirs: list[str] = []
        for f in sorted(p.iterdir()):
            if f.is_dir() and (f / "manifest.json").exists():
                dirs.append(str(f.resolve()))
        return dirs
    except Exception:
        logger.exception("Error listing ulauncher templates in %s", folder)
        return []


def read_ulauncher_theme(path: str | Path) -> dict[str, Any]:
    """Read an Ulauncher theme and return palette data.

    Returns a dict with:
    - manifest: dict of keys (when_selected, when_not_selected) -> color
    - theme: dict of @define-color names -> color
    """
    theme_path = Path(path)
    result: dict[str, Any] = {"manifest": {}, "theme": {}}

    if not theme_path.is_dir():
        return result

    # 1. Parse manifest.json (when_selected / when_not_selected at root or under matched_text_hl_colors)
    manifest_file = theme_path / "manifest.json"
    if manifest_file.exists():
        try:
            with manifest_file.open("r", encoding="utf-8") as f:
                data = json5.load(f)

            sources = [data]
            if "matched_text_hl_colors" in data and isinstance(data["matched_text_hl_colors"], dict):
                sources.append(data["matched_text_hl_colors"])

            for key in ["when_selected", "when_not_selected"]:
                for source in sources:
                    val = source.get(key)
                    if val:
                        if val in ["provisional_rgba_color", "provisional_hex_color"]:
                            val = "transparent"
                        result["manifest"][key] = str(val)
                        break
        except Exception:
            logger.exception("Failed reading ulauncher manifest %s", manifest_file)

    # 2. Parse theme.css @define-color entries
    css_file = theme_path / "theme.css"
    if css_file.exists():
        try:
            content = css_file.read_text(encoding="utf-8")
            for name, val in re.findall(r"@define-color\s+([\w-]+)\s+([^;]+);", content):
                val = val.strip()

                # Map template placeholders to transparent so the user must set them.
                if val in ["provisional_rgba_color", "provisional_hex_color"]:
                    val = "transparent"

                # Skip references and non-standard color functions.
                if "@" in val:
                    continue
                if "(" in val and not re.match(r"^(rgb|rgba|hsl|hsla)\(", val, re.IGNORECASE):
                    continue

                result["theme"][name] = val
        except Exception:
            logger.exception("Failed reading ulauncher theme.css %s", css_file)

    return result


def write_ulauncher_theme(theme_path_str: str, data: dict[str, Any], skip_backup: bool = False) -> bool:
    """Update manifest.json and theme.css in place.

    data = {
       "manifest": {"when_selected": "...", ...},
       "theme": {"bg": "...", ...}
    }
    """
    try:
        theme_path = Path(theme_path_str)
        success = True

        # 1. Update manifest.json
        manifest_updates = data.get("manifest", {})
        if manifest_updates:
            manifest_file = theme_path / "manifest.json"
            try:
                if manifest_file.exists():
                    with manifest_file.open("r", encoding="utf-8") as f:
                        current_data = json.load(f)

                    changed = False
                    for k, v in manifest_updates.items():
                        target_dict = current_data
                        if "matched_text_hl_colors" in current_data and k in current_data["matched_text_hl_colors"]:
                            target_dict = current_data["matched_text_hl_colors"]

                        if target_dict.get(k) != v:
                            target_dict[k] = v
                            changed = True

                    if changed:
                        if not skip_backup:
                            try:
                                shutil.copy2(manifest_file, manifest_file.with_suffix(".json.bak"))
                            except Exception:
                                logger.warning("Failed to backup manifest %s", manifest_file)

                        with manifest_file.open("w", encoding="utf-8") as f:
                            json.dump(current_data, f, indent=4)
                        logger.info("Updated ulauncher manifest %s", manifest_file)
            except Exception:
                logger.exception("Failed updating ulauncher manifest %s", manifest_file)
                success = False

        # 2. Update theme.css
        theme_updates = data.get("theme", {})
        if theme_updates:
            css_file = theme_path / "theme.css"
            try:
                if css_file.exists():
                    content = css_file.read_text(encoding="utf-8")
                    new_content = content
                    changed_css = False

                    for name, new_val in theme_updates.items():
                        pattern = re.compile(rf"(@define-color\s+{re.escape(name)}\s+)[^;]+(?=;)", re.IGNORECASE)
                        if pattern.search(new_content):
                            new_content, n = pattern.subn(lambda m: f"{m.group(1)}{new_val}", new_content)
                            if n > 0:
                                changed_css = True

                    if changed_css and new_content != content:
                        if not skip_backup:
                            try:
                                shutil.copy2(css_file, css_file.with_suffix(".css.bak"))
                            except Exception:
                                logger.warning("Failed to backup css %s", css_file)

                        css_file.write_text(new_content, encoding="utf-8")
                        logger.info("Updated ulauncher theme.css %s", css_file)
            except Exception:
                logger.exception("Failed updating ulauncher theme.css %s", css_file)
                success = False

        return success
    except Exception:
        logger.exception("Failed write_ulauncher_theme")
        return False
