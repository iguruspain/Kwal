#!/usr/bin/env python3
"""Reader for fastfetch JSONC configuration using json5.

Reads `~/.config/fastfetch/config.jsonc` and returns values by key.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

import json5
import shutil
from datetime import datetime
import re
import os

logger = logging.getLogger(__name__)


def read_config_fastfetch(key: str, default: Optional[object] = None) -> Tuple[Optional[object], str]:
    """Read a value from ~/.config/fastfetch/config.jsonc safely and return its path.

    Args:
        key: Top-level key to read from the JSON object. Dot-separated
             paths are supported (e.g. "section.subkey").
        default: Value to return if the file/key is missing or parsing fails.

    Returns:
        A tuple ``(value, config_path)`` where ``value`` is the stored value or
        ``default`` if not found or on error, and ``config_path`` is the
        `Path` to the config file that was consulted.
    """
    config_path = Path.home() / ".config" / "fastfetch" / "config.jsonc"
    # Represent path with a leading tilde for caller convenience: '~/.config/...'
    try:
        tilde_path = f"~/{config_path.relative_to(Path.home()).as_posix()}"
    except Exception:
        # Fallback to absolute path string if something unexpected occurs
        tilde_path = str(config_path)

    if not config_path.exists():
        logger.debug("Config file not found: %s", config_path)
        return default, tilde_path

    try:
        with config_path.open("r", encoding="utf-8") as fh:
            raw = fh.read()

            try:
                config_data = json5.loads(raw)
            except Exception as exc:
                logger.error("json5 failed to parse %s: %s", config_path, exc)
                return default, tilde_path

        if not isinstance(config_data, dict):
            logger.warning("Config content is not an object: %s", config_path)
            return default, tilde_path

        # Support dot-separated paths (e.g. "section.subkey")
        if "." in key:
            current = config_data
            for part in key.split("."):
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return default, tilde_path
            return current, tilde_path

        # Direct top-level key
        if key in config_data:
            return config_data[key], tilde_path

        # Single-level fallback: search inside child objects for the key
        if "." not in key:
            for v in config_data.values():
                if isinstance(v, dict) and key in v:
                    return v[key], tilde_path

        return default, tilde_path

    except Exception as exc:
        logger.error("Failed to read or parse %s: %s", config_path, exc)
        return default, tilde_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    value, path = read_config_fastfetch("source", None)
    logger.info("Config file: %s", path)
    logger.info("Config value for 'source': %s", value)


def list_template_images(folder: str | Path) -> list[str]:
    """Return list of absolute file paths for template images in `folder`.

    Accepts a string or Path. Applies extension filters and returns sorted list.
    """
    try:
        p = Path(folder) if not isinstance(folder, Path) else folder
        if not p.exists() or not p.is_dir():
            logger.debug("list_template_images: folder does not exist or is not a dir: %s", p)
            return []
        exts = {".png", ".jpg", ".jpeg", ".bmp", ".svg"}
        files: list[Path] = []
        for f in sorted(p.iterdir()):
            if not f.is_file():
                continue
            if f.suffix.lower() in exts:
                files.append(f.resolve())
        return [str(x) for x in files]
    except Exception:
        logger.exception("Error listing template images in %s", folder)
        return []


def ensure_fastfetch_config_dir() -> Path:
    """Ensure and return the user's fastfetch config directory path.

    Returns:
        Path to ~/.config/fastfetch (created if missing).
    """
    cfg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "fastfetch"
    try:
        cfg.mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception("Failed ensuring fastfetch config dir %s", cfg)
    return cfg


def copy_image_to_fastfetch(src: str, dest_name: str) -> str:
    """Copy an image file to the fastfetch config directory using dest_name.

    Args:
        src: Source path (may be a file:// URI or plain path).
        dest_name: Simple filename to use in destination (no directories).

    Returns:
        Absolute destination path as string on success.

    Raises:
        FileNotFoundError if source doesn't exist.
    """
    if not src:
        raise FileNotFoundError("Empty source path")
    # accept file:// URIs
    if src.startswith("file://"):
        src_path = Path(src.replace("file://", ""))
    else:
        src_path = Path(src)

    if not src_path.exists() or not src_path.is_file():
        raise FileNotFoundError(f"Source image not found: {src_path}")

    dest_dir = ensure_fastfetch_config_dir()
    # sanitize dest_name to avoid directories
    dest_basename = os.path.basename(dest_name) or "chica-tinted.png"
    dst = dest_dir / dest_basename
    try:
        shutil.copyfile(src_path, dst)
        # apply permissive read permissions for user
        try:
            dst.chmod(0o644)
        except Exception:
            pass
        return str(dst)
    except Exception:
        logger.exception("Failed copying %s to %s", src_path, dst)
        raise


def set_fastfetch_source_inplace(config_path: str | None, new_source: str) -> bool:
    """Replace the `source` key value in fastfetch `config.jsonc` textually.

    This attempts to preserve comments by performing an in-place textual
    replacement of the first occurrence of a `source` key. It does NOT
    attempt to fully parse and rewrite the JSONC file.

    Args:
        config_path: Path to config.jsonc; if None, defaults to ~/.config/fastfetch/config.jsonc
        new_source: New path value to set (absolute path string).

    Returns:
        True if a replacement was made and file written, False otherwise.
    """
    # resolve actual file path for reading/writing (expanduser for provided path)
    cfg = Path(config_path).expanduser() if config_path else (Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "fastfetch" / "config.jsonc")
    if not cfg.exists() or not cfg.is_file():
        logger.error("Config file not found for in-place update: %s", cfg)
        return False

    try:
        raw = cfg.read_text(encoding="utf-8")
    except Exception:
        logger.exception("Failed reading config file %s for in-place update", cfg)
        return False

    # Prepare the new value to write: prefer using '~' when path is under the user's home
    try:
        dst_path = Path(new_source).expanduser()
        try:
            rel = dst_path.relative_to(Path.home())
            write_value = "~/" + rel.as_posix()
        except Exception:
            write_value = str(dst_path)
    except Exception:
        write_value = str(new_source)

    # Escape double quotes inside the value (rare for file paths)
    write_value_escaped = write_value.replace('"', '\\"')

    # First try JSON style with quoted key: "source": "..."
    pattern1 = re.compile(r'("source"\s*:\s*)(["\"]).*?\2', re.DOTALL)
    m1 = pattern1.search(raw)
    if m1:
        def repl1(match: re.Match) -> str:
            return f'{match.group(1)}"{write_value_escaped}"'

        new_raw = pattern1.sub(repl1, raw, count=1)
        try:
            # create a timestamped backup before overwriting
            try:
                bak = cfg.with_name(cfg.name + ".bak")
                shutil.copyfile(cfg, bak)
                logger.info("Backup of config created: %s", bak)
            except Exception:
                logger.exception("Failed creating backup of %s", cfg)
            cfg.write_text(new_raw, encoding="utf-8")
            logger.info("Replaced quoted 'source' value in %s", cfg)
            return True
        except Exception:
            logger.exception("Failed writing updated config to %s", cfg)
            return False

    # Fallback: look for unquoted key style used in JSONC: source: value
    pattern2 = re.compile(r'(^\s*source\s*:\s*)(["\']?).*?(["\']?)(\s*(,?)\s*$)', re.MULTILINE)
    m2 = pattern2.search(raw)
    if m2:
        prefix = m2.group(1)
        suffix = m2.group(4)
        new_val = '"' + write_value_escaped + '"' + suffix
        new_raw = raw[: m2.start()] + prefix + new_val + raw[m2.end() :]
        try:
            # create a timestamped backup before overwriting
            try:
                bak = cfg.with_name(cfg.name + ".bak")
                shutil.copyfile(cfg, bak)
                logger.info("Backup of config created: %s", bak)
            except Exception:
                logger.exception("Failed creating backup of %s", cfg)
            cfg.write_text(new_raw, encoding="utf-8")
            logger.info("Replaced unquoted 'source' value in %s", cfg)
            return True
        except Exception:
            logger.exception("Failed writing updated config to %s", cfg)
            return False

    logger.warning("No 'source' key found in %s; no changes made", cfg)
    return False


def restore_fastfetch_config_backup(config_path: str | None = None) -> bool:
    """Restore the fixed backup (config.jsonc.bak) over the active config.

    Returns True if restore performed, False if backup not found or on error.
    """
    cfg = Path(config_path).expanduser() if config_path else (Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "fastfetch" / "config.jsonc")
    bak = cfg.with_name(cfg.name + ".bak")
    if not bak.exists() or not bak.is_file():
        logger.warning("No backup file found to restore: %s", bak)
        return False
    try:
        # Copy backup over config (overwrite)
        shutil.copyfile(bak, cfg)
        logger.info("Restored backup %s -> %s", bak, cfg)
        return True
    except Exception:
        logger.exception("Failed restoring backup %s to %s", bak, cfg)
        return False


def clear_fastfetch_cache() -> None:
    """Remove common fastfetch cache locations under XDG cache.

    Removes only `$XDG_CACHE_HOME/fastfetch` when present. Do NOT remove
    the `kwal/fastfetch_tinted` cache here — that cache is managed separately
    by the tinting code and cleared on application shutdown.
    """
    try:
        cache_base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
        targets = [cache_base / "fastfetch"]
        for t in targets:
            if t.exists():
                shutil.rmtree(t)
                logger.info("Cleared fastfetch cache path %s", t)
    except Exception:
        logger.exception("Failed clearing fastfetch cache directories")