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


def copy_image_to_fastfetch(src: str, dest_name: str) -> str:
    """Copy an image file to the fastfetch config directory."""
    if not src:
        raise FileNotFoundError("Empty source path")
        
    src_path = Path(src.replace("file://", "") if src.startswith("file://") else src)
    if not src_path.is_file():
        raise FileNotFoundError(f"Source image not found: {src_path}")

    dest_dir = ensure_fastfetch_config_dir()
    dest_basename = os.path.basename(dest_name) or "chica-tinted.png"
    dst = dest_dir / dest_basename

    try:
        shutil.copyfile(src_path, dst)
        try:
            dst.chmod(0o644)
        except Exception:
            pass
        return str(dst)
    except Exception:
        logger.exception("Failed copying %s to %s", src_path, dst)
        raise


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

        # Build simplified output: only config_path and palettes
        out: dict[str, Any] = {"config_path": display_path, "palettes": {}}

        palettes = config_data.get("palettes")
        if isinstance(palettes, dict):
            for pname, pval in palettes.items():
                # include only dict-like palettes (e.g. 'colors')
                if isinstance(pval, dict):
                    cleaned: dict[str, Any] = {}
                    for k, v in pval.items():
                        if isinstance(v, (str, int, float, bool)) or v is None:
                            cleaned[k] = v
                        else:
                            try:
                                cleaned[k] = str(v)
                            except Exception:
                                cleaned[k] = None
                    out["palettes"][pname] = cleaned

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