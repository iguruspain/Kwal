#!/usr/bin/env python3
"""Reader for fastfetch JSONC configuration using json5.

Reads `~/.config/fastfetch/config.jsonc` and returns values by key.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import json5

logger = logging.getLogger(__name__)


def read_config_fastfetch(key: str, default: Optional[object] = None) -> Optional[object]:
    """Read a value from ~/.config/fastfetch/config.jsonc safely.

    Args:
        key: Top-level key to read from the JSON object. Dot-separated
             paths are supported (e.g. "section.subkey").
        default: Value to return if the file/key is missing or parsing fails.

    Returns:
        The stored value or ``default`` if not found or on error.
    """
    config_path = Path.home() / ".config" / "fastfetch" / "config.jsonc"

    if not config_path.exists():
        logger.debug("Config file not found: %s", config_path)
        return default

    try:
        with config_path.open("r", encoding="utf-8") as fh:
            raw = fh.read()

        try:
            config_data = json5.loads(raw)
        except Exception as exc:
            logger.error("json5 failed to parse %s: %s", config_path, exc)
            return default

        if not isinstance(config_data, dict):
            logger.warning("Config content is not an object: %s", config_path)
            return default

        if "." in key:
            current = config_data
            for part in key.split("."):
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return default
            return current

        if key in config_data:
            return config_data[key]
        if "." not in key:
            for v in config_data.values():
                if isinstance(v, dict) and key in v:
                    return v[key]

        return default

    except Exception as exc:
        logger.error("Failed to read or parse %s: %s", config_path, exc)
        return default


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    value = read_config_fastfetch("source", None)
    logger.info("Config value for 'source': %s", value)