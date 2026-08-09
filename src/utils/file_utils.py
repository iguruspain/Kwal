#!/usr/bin/env python3
"""Reader for fastfetch JSONC configuration using json5."""
from __future__ import annotations

import logging
import os
import re
import shutil
import tomlkit
import json
from pathlib import Path
from typing import Any

import json5

logger = logging.getLogger(__name__)


def read_config_fastfetch(key: str, default: Any = None) -> tuple[Any, str]:
    """Read a value from ~/.config/fastfetch/config.jsonc safely."""
    config_path = Path.home() / ".config" / "fastfetch" / "config.jsonc"
    
    # helper for logging path
    try:
        display_path = f"~/{config_path.relative_to(Path.home()).as_posix()}"
    except ValueError:
        display_path = str(config_path)

    if not config_path.exists():
        logger.debug("Config file not found: %s", config_path)
        return default, display_path

    try:
        with config_path.open("r", encoding="utf-8") as fh:
            try:
                config_data = json5.load(fh)
            except Exception as exc:
                logger.error("json5 failed to parse %s: %s", config_path, exc)
                return default, display_path

        if not isinstance(config_data, dict):
            return default, display_path

        # Dot-notation support
        if "." in key:
            current = config_data
            for part in key.split("."):
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return default, display_path
            return current, display_path

        # Direct key
        if key in config_data:
            return config_data[key], display_path

        # Flattened search (if simple key not found)
        # Why searching values? Is this a specific fastfetch structure thing? 
        # Maintaining original logic but cleaning it up.
        for v in config_data.values():
            if isinstance(v, dict) and key in v:
                return v[key], display_path

        return default, display_path

    except Exception:
        logger.exception("Failed to read %s", config_path)
        return default, display_path


def list_template_images(folder: str | Path) -> list[str]:
    """Return list of absolute file paths for template images in `folder`."""
    try:
        p = Path(folder)
        if not p.is_dir():
            return []
            
        exts = {".png", ".jpg", ".jpeg", ".bmp", ".svg"}
        files: list[str] = []
        
        # Sorted mainly for UI stability
        for f in sorted(p.iterdir()):
            if f.is_file() and f.suffix.lower() in exts:
                files.append(str(f.resolve()))
        return files
    except Exception:
        logger.exception("Error listing images in %s", folder)
        return []


def ensure_fastfetch_config_dir() -> Path:
    """Ensure and return the user's fastfetch config directory."""
    cfg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "fastfetch"
    try:
        cfg.mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception("Failed ensuring fastfetch config dir")
    return cfg


def set_fastfetch_source_inplace(config_path: str | None, new_source: str) -> bool:
    """Replace the `source` key value in config.jsonc textually."""
    cfg = Path(config_path).expanduser() if config_path else (Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "fastfetch" / "config.jsonc")
    
    if not cfg.is_file():
        return False

    try:
        raw = cfg.read_text(encoding="utf-8")
    except Exception:
        logger.exception("Failed reading config %s", cfg)
        return False

    # Calculate write value
    dst_path = Path(new_source).expanduser()
    try:
        # try to use ~/ relative path if possible
        write_value = "~/" + dst_path.relative_to(Path.home()).as_posix()
    except ValueError:
        write_value = str(dst_path)

    write_value_esc = write_value.replace('"', '\\"')

    # 1. Quoted key replace: "source": "..."
    # Using DOTALL for multi-line JSON matching if needed, though usually on one line
    # Original Regex: r'("source"\s*:\s*)(["\"]).*?\2'
    pattern1 = re.compile(r'("source"\s*:\s*)(["\"]).*?\2', re.DOTALL)
    if pattern1.search(raw):
        new_raw = pattern1.sub(lambda m: f'{m.group(1)}"{write_value_esc}"', raw, count=1)
        return _write_config_atomic(cfg, new_raw)

    # 2. Unquoted key replace (JSONC): source: ...
    # Original Regex: r'(^\s*source\s*:\s*)(["\']?).*?(["\']?)(\s*(,?)\s*$)'
    pattern2 = re.compile(r'(^\s*source\s*:\s*)(["\']?).*?(["\']?)(\s*(,?)\s*$)', re.MULTILINE)
    match2 = pattern2.search(raw)
    if match2:
        # group 1: '  source : '
        # group 4: trailing space/comma
        # We enforce double quotes for the new value
        prefix = match2.group(1)
        suffix = match2.group(4)
        replacement = f'{prefix}"{write_value_esc}"{suffix}'
        
        # Since regex matched a specific range, we can splice string
        new_raw = raw[:match2.start()] + replacement + raw[match2.end():]
        return _write_config_atomic(cfg, new_raw)

    logger.warning("No 'source' key found in %s", cfg)
    return False


def _write_config_atomic(cfg_path: Path, content: str) -> bool:
    """Write config content atomically, creating backup first."""
    try:
        bak = cfg_path.with_name(cfg_path.name + ".bak")
        # Only create a backup if one does not already exist. This prevents
        # accidentally overwriting the user's original backup when multiple
        # layers of code (controller + surgical writer) both attempt a
        # backup. If a backup already exists, keep it to preserve the
        # original config state.
        if cfg_path.exists() and not bak.exists():
            try:
                shutil.copyfile(cfg_path, bak)
            except Exception:
                logger.warning("Failed creating backup %s", bak)

        cfg_path.write_text(content, encoding="utf-8")
        logger.info("Updated config %s", cfg_path)
        return True
    except Exception:
        logger.exception("Failed writing config %s", cfg_path)
        return False


def restore_fastfetch_config_backup(config_path: str | None = None) -> bool:
    """Restore config.jsonc.bak."""
    cfg = Path(config_path).expanduser() if config_path else (Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "fastfetch" / "config.jsonc")
    bak = cfg.with_name(cfg.name + ".bak")
    
    if not bak.is_file():
        return False
        
    try:
        shutil.copyfile(bak, cfg)
        logger.info("Restored backup %s", bak)
        return True
    except Exception:
        logger.exception("Failed restoring backup")
        return False


def clear_fastfetch_cache() -> None:
    """Remove standard fastfetch cache."""
    try:
        cache_base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        target = cache_base / "fastfetch"
        if target.exists():
            shutil.rmtree(target)
            logger.info("Cleared cache %s", target)
    except Exception:
        logger.exception("Failed clearing fastfetch cache")

def check_binary(command: str) -> bool:
    """Check if a binary exists in the system PATH."""
    return shutil.which(command) is not None

def list_starship_templates(folder: str | Path) -> list[str]:
    """Return list of absolute file paths for starship template toml files in `folder`."""
    try:
        p = Path(folder)
        if not p.is_dir():
            return []
            
        exts = {".toml"}
        files: list[str] = []
        
        # Sorted mainly for UI stability
        for f in sorted(p.iterdir()):
            if f.is_file() and f.suffix.lower() in exts:
                files.append(str(f.resolve()))
        return files
    except Exception:
        logger.exception("Error listing starship templates in %s", folder)
        return []

def read_starship_config(path: str | Path | None = None) -> tuple[str, str]:
    """Read starship config at `path` (or default) and return simplified JSON.

    The function accepts a single optional `path`. If `path` is not
    provided it uses the default: `~/.config/starship.toml`.

    Returns `(json_str, display_path)` where `json_str` is a pretty
    JSON containing only `config_path` and `palettes` (each palette
    contains simple color values). If the file is missing the
    `palettes` mapping is empty.
    """
    cfg_path = Path(path).expanduser() if path else (Path.home() / ".config" / "starship.toml")

    # helper for logging path
    try:
        display_path = f"~/{cfg_path.relative_to(Path.home()).as_posix()}"
    except Exception:
        display_path = str(cfg_path)

    if not cfg_path.exists():
        logger.debug("Config file not found: %s", cfg_path)
        # Return empty palettes JSON when missing
        return json.dumps({"config_path": display_path, "palettes": {}}, ensure_ascii=False, indent=2), display_path

    try:
        # Load TOML configuration
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
                # tomlkit items often have unwrap() or can be stringified
                if hasattr(v, "unwrap"):
                    unwrapped: Any = v.unwrap()
                    if isinstance(unwrapped, (dict, list, str, int, float, bool)) or unwrapped is None:
                        return clean_val(unwrapped)
                return str(v)
            except Exception:
                return None

        # Build simplified output: include config_path, palettes, top-level format/palette and a small preview mapping
        out: dict[str, Any] = {"config_path": display_path, "palettes": {}, "preview": {}, "format": None, "palette": None}

        # Use the recursive cleaner for everything
        for key, val in config_data.items():
            out[key] = clean_val(val)

        try:
            json_str = json.dumps(out, ensure_ascii=False, indent=2)
        except Exception:
            # Fallback to a very minimal structure if everything fails
            json_str = json.dumps({"config_path": display_path, "palettes": {}}, ensure_ascii=False, indent=2)

        return json_str, display_path

    except Exception:
        logger.exception("Failed to read %s", cfg_path)
        return json.dumps({"config_path": display_path, "palettes": {}}, ensure_ascii=False, indent=2), display_path

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

def apply_starship_palette_surgical(
    config_path: str, palette_name: str, palette_data: dict[str, str]
) -> bool:
    """Apply a palette to starship.toml using tomlkit to preserve formatted comments.

    1. Updates `palette = "palette_name"` at root level.
    2. Updates or creates `[palettes.palette_name]` block.
    """
    path = Path(config_path)
    if not path.exists():
        return False
        
    try:
        with path.open("r", encoding="utf-8") as f:
            doc = tomlkit.parse(f.read())
        
        # 1. Update root 'palette' reference
        doc["palette"] = palette_name
        
        # 2. Ensure 'palettes' table exists
        if "palettes" not in doc:
            doc.add("palettes", tomlkit.table())
            
        palettes: Any = doc["palettes"]
        
        # 3. Update the specific palette
        # We replace the content to ensure it matches our data, but keep the key
        
        # Sanitize colors: ensure #RRGGBB format (strip alpha from #AARRGGBB)
        cleaned_data = {}
        for k, v in palette_data.items():
            if isinstance(v, str) and v.startswith("#") and len(v) == 9:
                 # Qt color.toString() returns #AARRGGBB. Starship generally needs #RRGGBB
                 # We strip the first 2 chars of the hex component (Alpha)
                 cleaned_data[k] = "#" + v[3:]
            else:
                 cleaned_data[k] = v
                 
        palettes[palette_name] = cleaned_data

        # 4. Write back preserving structure
        return _write_config_atomic(path, doc.as_string())

    except Exception:
        logger.exception("Failed surgical update of starship config")
        return False


def apply_starship_palettes_atomic(
    config_path: str, palettes: list[tuple[str, dict[str, str]]], active_palette: str | None = None
) -> bool:
    """Apply multiple palettes in a single atomic write.

    This writes all provided palettes to the `[palettes]` table and sets
    the root `palette` key to `active_palette` (if provided). Writing is
    performed once to avoid multiple overwrites and duplicated logs.
    """
    path = Path(config_path)
    if not path.exists():
        return False

    try:
        with path.open("r", encoding="utf-8") as f:
            doc = tomlkit.parse(f.read())

        # Ensure 'palettes' table exists
        if "palettes" not in doc:
            doc.add("palettes", tomlkit.table())

        palettes_table: Any = doc["palettes"]

        # Sanitize and set each palette
        for pname, pdata in palettes:
            cleaned_data: dict[str, Any] = {}
            for k, v in pdata.items():
                if isinstance(v, str) and v.startswith("#") and len(v) == 9:
                    cleaned_data[k] = "#" + v[3:]
                else:
                    cleaned_data[k] = v
            palettes_table[pname] = cleaned_data

        # Set active palette if provided
        if active_palette:
            doc["palette"] = active_palette

        return _write_config_atomic(path, doc.as_string())

    except Exception:
        logger.exception("Failed atomic update of starship config")
        return False


def list_ulauncher_templates(folder: str | Path) -> list[str]:
    """Return list of absolute paths for ulauncher template directories in `folder`."""
    try:
        p = Path(folder)
        if not p.is_dir():
            return []
            
        # Ulauncher themes are directories containing manifest.json
        dirs: list[str] = []
        
        for f in sorted(p.iterdir()):
            if f.is_dir() and (f / "manifest.json").exists():
                dirs.append(str(f.resolve()))
        return dirs
    except Exception:
        logger.exception("Error listing ulauncher templates in %s", folder)
        return []


def read_ulauncher_theme(path: str | Path) -> dict[str, Any]:
    """Read Ulauncher theme (manifest.json and theme.css) and return palette data.
    
    Returns a dict with:
    - manifest: dict of keys (when_selected, when_not_selected) -> color
    - theme: dict of keys (Selector { Property }) -> color
    """
    theme_path = Path(path)
    result = {"manifest": {}, "theme": {}}
    
    if not theme_path.is_dir():
        return result

    # 1. Parse manifest.json
    manifest_file = theme_path / "manifest.json"
    if manifest_file.exists():
        try:
            with manifest_file.open("r", encoding="utf-8") as f:
                data = json5.load(f)
                # We are interested in these specific keys usually found in some ulauncher manifests
                # or injected by users. If they don't exist, we skip.
                # Actually, ulauncher manifest usually has 'color_palette' or direct hex codes in logic?
                # The user instruction says: "En manifest.json, solo nos interesan when_selected y when_not_selected"
                # These keys might be at root or under some object? 
                # We will check root first, then look for 'styles' or similar if typical structure differs.
                # Assuming root or flat helper for now based on request simplicity.
                
                # Check known keys
                # They can be at root or under 'matched_text_hl_colors'
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
                             break # Found it
        except Exception:
            logger.exception("Failed reading ulauncher manifest %s", manifest_file)

    # 2. Parse theme.css for @define-color
    # Format: @define-color NAME VALUE;
    # Regex: @define-color\s+([\w-]+)\s+([^;]+);
    css_file = theme_path / "theme.css"
    if css_file.exists():
        try:
            content = css_file.read_text(encoding='utf-8')
            # Find all definitions
            # We want names as keys. 
            # Note: Values might be hex or rgba.
            matches = re.findall(r'@define-color\s+([\w-]+)\s+([^;]+);', content)
            for name, val in matches:
                val = val.strip()
                
                # Placeholder handling: if it matches unofficial template placeholders,
                # we show it as transparent/empty so the user is forced to set it.
                if val in ["provisional_rgba_color", "provisional_hex_color"]:
                    val = "transparent"

                # Filter out references (containing @)
                if '@' in val:
                    continue
                
                # If it's a function (contains parens), ensure it's a standard color function
                if '(' in val:
                    # We allow rgb, rgba, hsl, hsla
                    # Regex check for start of string
                    if not re.match(r'^(rgb|rgba|hsl|hsla)\(', val, re.IGNORECASE):
                        continue

                # Store key as just the name for cleaner UI
                result["theme"][name] = val
        except Exception:
            logger.exception("Failed reading ulauncher theme.css %s", css_file)
            
    return result


def write_ulauncher_theme(theme_path_str: str, data: dict[str, Any], skip_backup: bool = False) -> bool:
    """Updates manifest.json and theme.css in place.
    
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
                    import json
                    with manifest_file.open("r", encoding="utf-8") as f:
                        current_data = json.load(f)
                    
                    changed = False
                    for k, v in manifest_updates.items():
                         # We need to find where k is. 
                         # It could be root or matched_text_hl_colors
                         
                         target_dict = current_data
                         if "matched_text_hl_colors" in current_data and k in current_data["matched_text_hl_colors"]:
                             target_dict = current_data["matched_text_hl_colors"]
                         
                         if target_dict.get(k) != v:
                             target_dict[k] = v
                             changed = True
                    
                    if changed:
                        # Backup
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
                    content = css_file.read_text(encoding='utf-8')
                    new_content = content
                    changed_css = False
                    
                    for name, new_val in theme_updates.items():
                        pattern = re.compile(rf'(@define-color\s+{re.escape(name)}\s+)[^;]+(?=;)', re.IGNORECASE)
                        if pattern.search(new_content):
                             def replacer(m):
                                 return f"{m.group(1)}{new_val}"
                             new_content, n = pattern.subn(replacer, new_content)
                             if n > 0:
                                 changed_css = True

                    if changed_css and new_content != content:
                        # Backup
                        if not skip_backup:
                            try:
                                shutil.copy2(css_file, css_file.with_suffix(".css.bak"))
                            except Exception:
                               logger.warning("Failed to backup css %s", css_file)
                               
                        css_file.write_text(new_content, encoding='utf-8')
                        logger.info("Updated ulauncher theme.css %s", css_file)
            except Exception:
                logger.exception("Failed updating ulauncher theme.css %s", css_file)
                success = False
                
        return success
    except Exception:
        logger.exception("Failed write_ulauncher_theme")
        return False