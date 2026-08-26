#!/usr/bin/env python3
"""Generic file helpers."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def check_binary(command: str) -> bool:
    """Check if a binary exists in the system PATH."""
    return shutil.which(command) is not None


def backup_config_file(path: Path) -> Path | None:
    """Create a ``.bak`` backup of ``path`` if it exists.

    Returns the backup path on success, or ``None`` if the source file does
    not exist or the copy failed.
    """
    src = Path(path)
    if not src.is_file():
        return None
    bak = src.with_name(src.name + ".bak")
    try:
        shutil.copy2(src, bak)
        logger.info("Created backup %s", bak)
        return bak
    except Exception:
        logger.exception("Failed creating backup for %s", src)
        return None


def write_config_atomic(cfg_path: Path, content: str) -> bool:
    """Write config content, creating a ``.bak`` backup first if none exists."""
    try:
        bak = cfg_path.with_name(cfg_path.name + ".bak")
        # Keep the first backup so the original config is never overwritten.
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
