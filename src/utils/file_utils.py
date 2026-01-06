#!/usr/bin/env python3
"""Reader for fastfetch JSONC configuration using json5.

Reads `~/.config/fastfetch/config.jsonc` and returns values by key.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

import json5

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