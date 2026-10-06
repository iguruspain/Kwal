#!/usr/bin/env python3
"""Generic file helpers."""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
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
    """Atomically write config content (temp file + ``os.replace``).

    Creates a ``.bak`` backup of the existing config first if none exists, so
    an interrupted write never leaves a partially written target behind.
    """
    try:
        bak = cfg_path.with_name(cfg_path.name + ".bak")
        # Keep the first backup so the original config is never overwritten.
        if cfg_path.exists() and not bak.exists():
            try:
                shutil.copyfile(cfg_path, bak)
            except Exception:
                logger.warning("Failed creating backup %s", bak)

        # Write to a temp file in the same directory, then atomically replace.
        fd, tmp_name = tempfile.mkstemp(
            dir=cfg_path.parent, prefix=f".{cfg_path.name}.", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
            os.replace(tmp_path, cfg_path)
        except Exception:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                logger.warning("Failed removing temp file %s", tmp_path)
            raise
        logger.info("Updated config %s", cfg_path)
        return True
    except Exception:
        logger.exception("Failed writing config %s", cfg_path)
        return False
