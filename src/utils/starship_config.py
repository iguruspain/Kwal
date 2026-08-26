"""Starship TOML configuration helpers."""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

import tomlkit

from .file_utils import write_config_atomic

logger = logging.getLogger(__name__)


def list_starship_templates(folder: str | Path) -> list[str]:
    """Return absolute paths of starship template toml files in `folder`."""
    try:
        p = Path(folder)
        if not p.is_dir():
            return []

        files: list[str] = []
        for f in sorted(p.iterdir()):
            if f.is_file() and f.suffix.lower() == ".toml":
                files.append(str(f.resolve()))
        return files
    except Exception:
        logger.exception("Error listing starship templates in %s", folder)
        return []


def read_starship_config(path: str | Path | None = None) -> tuple[str, str]:
    """Read starship config at `path` (or default) and return simplified JSON.

    Returns `(json_str, display_path)` where `json_str` is pretty JSON of the
    config. If the file is missing, `palettes` is empty.
    """
    cfg_path = Path(path).expanduser() if path else (Path.home() / ".config" / "starship.toml")

    try:
        display_path = f"~/{cfg_path.relative_to(Path.home()).as_posix()}"
    except Exception:
        display_path = str(cfg_path)

    if not cfg_path.exists():
        logger.debug("Config file not found: %s", cfg_path)
        return json.dumps({"config_path": display_path, "palettes": {}}, ensure_ascii=False, indent=2), display_path

    try:
        with cfg_path.open("r", encoding="utf-8") as fh:
            config_data = tomlkit.load(fh)

        if not isinstance(config_data, dict):
            return json.dumps({"config_path": display_path, "palettes": {}}, ensure_ascii=False, indent=2), display_path

        def clean_val(v: object) -> Any:
            """Recursively clean TOML values for JSON serialization."""
            if isinstance(v, dict):
                return {str(ki): clean_val(vi) for ki, vi in v.items()}
            if isinstance(v, list):
                return [clean_val(vi) for vi in v]
            if isinstance(v, (str, int, float, bool)) or v is None:
                return v
            try:
                if hasattr(v, "unwrap"):
                    unwrapped: Any = v.unwrap()
                    if isinstance(unwrapped, (dict, list, str, int, float, bool)) or unwrapped is None:
                        return clean_val(unwrapped)
                return str(v)
            except Exception:
                return None

        out: dict[str, Any] = {
            "config_path": display_path, "palettes": {}, "preview": {},
            "format": None, "palette": None,
        }
        for key, val in config_data.items():
            out[key] = clean_val(val)

        try:
            json_str = json.dumps(out, ensure_ascii=False, indent=2)
        except Exception:
            json_str = json.dumps({"config_path": display_path, "palettes": {}}, ensure_ascii=False, indent=2)

        return json_str, display_path

    except Exception:
        logger.exception("Failed to read %s", cfg_path)
        return json.dumps({"config_path": display_path, "palettes": {}}, ensure_ascii=False, indent=2), display_path


def restore_starship_config_backup(config_path: str | None = None) -> bool:
    """Restore starship.toml.bak."""
    cfg = Path(config_path).expanduser() if config_path else (Path.home() / ".config" / "starship.toml")
    bak = cfg.with_name(cfg.name + ".bak")

    if not bak.is_file():
        return False

    try:
        shutil.copyfile(bak, cfg)
        logger.info("Restored starship backup %s", bak)
        return True
    except Exception:
        logger.exception("Failed restoring starship backup")
        return False


def apply_starship_palettes_atomic(
    config_path: str, palettes: list[tuple[str, dict[str, str]]], active_palette: str | None = None
) -> bool:
    """Apply multiple palettes in a single atomic write.

    Writes all provided palettes to the `[palettes]` table and sets the root
    `palette` key to `active_palette` (if provided).
    """
    path = Path(config_path)
    if not path.exists():
        return False

    try:
        with path.open("r", encoding="utf-8") as f:
            doc = tomlkit.parse(f.read())

        if "palettes" not in doc:
            doc.add("palettes", tomlkit.table())

        palettes_table: Any = doc["palettes"]

        for pname, pdata in palettes:
            cleaned_data: dict[str, Any] = {}
            for k, v in pdata.items():
                # Sanitize #AARRGGBB to #RRGGBB
                if isinstance(v, str) and v.startswith("#") and len(v) == 9:
                    cleaned_data[k] = "#" + v[3:]
                else:
                    cleaned_data[k] = v
            palettes_table[pname] = cleaned_data

        if active_palette:
            doc["palette"] = active_palette

        return write_config_atomic(path, doc.as_string())

    except Exception:
        logger.exception("Failed atomic update of starship config")
        return False
