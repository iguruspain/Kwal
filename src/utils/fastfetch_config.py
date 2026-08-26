"""Fastfetch JSONC configuration helpers."""
from __future__ import annotations

import logging
import re
import shutil
from pathlib import Path
from typing import Any

import json5

from .file_utils import write_config_atomic
from .xdg_paths import fastfetch_config_path, xdg_cache_home, xdg_config_home

logger = logging.getLogger(__name__)


def read_config_fastfetch(key: str, default: Any = None) -> tuple[Any, str]:
    """Read a value from ~/.config/fastfetch/config.jsonc safely."""
    config_path = fastfetch_config_path()

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

        if key in config_data:
            return config_data[key], display_path

        # Flattened search fallback for nested fastfetch sections.
        for v in config_data.values():
            if isinstance(v, dict) and key in v:
                return v[key], display_path

        return default, display_path

    except Exception:
        logger.exception("Failed to read %s", config_path)
        return default, display_path


def ensure_fastfetch_config_dir() -> Path:
    """Ensure and return the user's fastfetch config directory."""
    cfg = xdg_config_home() / "fastfetch"
    try:
        cfg.mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.exception("Failed ensuring fastfetch config dir")
    return cfg


def set_fastfetch_source_inplace(config_path: str | None, new_source: str) -> bool:
    """Replace the `source` key value in config.jsonc textually."""
    cfg = Path(config_path).expanduser() if config_path else fastfetch_config_path()

    if not cfg.is_file():
        return False

    try:
        raw = cfg.read_text(encoding="utf-8")
    except Exception:
        logger.exception("Failed reading config %s", cfg)
        return False

    dst_path = Path(new_source).expanduser()
    try:
        write_value = "~/" + dst_path.relative_to(Path.home()).as_posix()
    except ValueError:
        write_value = str(dst_path)

    write_value_esc = write_value.replace('"', '\\"')

    # Quoted key: "source": "..."
    pattern1 = re.compile(r'("source"\s*:\s*)(["\']).*?\2', re.DOTALL)
    if pattern1.search(raw):
        new_raw = pattern1.sub(lambda m: f'{m.group(1)}"{write_value_esc}"', raw, count=1)
        return write_config_atomic(cfg, new_raw)

    # Unquoted key (JSONC): source: ...
    pattern2 = re.compile(r'(^\s*source\s*:\s*)(["\']?).*?(["\']?)(\s*(,?)\s*$)', re.MULTILINE)
    match2 = pattern2.search(raw)
    if match2:
        prefix = match2.group(1)
        suffix = match2.group(4)
        replacement = f'{prefix}"{write_value_esc}"{suffix}'
        new_raw = raw[:match2.start()] + replacement + raw[match2.end():]
        return write_config_atomic(cfg, new_raw)

    logger.warning("No 'source' key found in %s", cfg)
    return False


def restore_fastfetch_config_backup(config_path: str | None = None) -> bool:
    """Restore config.jsonc.bak."""
    cfg = Path(config_path).expanduser() if config_path else fastfetch_config_path()
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
        target = xdg_cache_home() / "fastfetch"
        if target.exists():
            shutil.rmtree(target)
            logger.info("Cleared cache %s", target)
    except Exception:
        logger.exception("Failed clearing fastfetch cache")
