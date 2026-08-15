"""Centralized XDG base-directory helpers.

All code that needs a user config or cache location should go through these
functions instead of re-reading ``XDG_CONFIG_HOME`` / ``XDG_CACHE_HOME``
inline. This keeps the fallback logic in a single place and makes the
Kwal-specific sub-paths explicit.
"""

from __future__ import annotations

import os
from pathlib import Path


def xdg_config_home() -> Path:
    """Return the user's XDG config home directory."""
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def xdg_cache_home() -> Path:
    """Return the user's XDG cache home directory."""
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))


def kwal_config_dir() -> Path:
    """Return the Kwal config directory (``$XDG_CONFIG_HOME/kwal``)."""
    return xdg_config_home() / "kwal"


def kwal_cache_dir() -> Path:
    """Return the Kwal cache directory (``$XDG_CACHE_HOME/kwal``)."""
    return xdg_cache_home() / "kwal"


def fastfetch_config_path() -> Path:
    """Return the fastfetch config file path."""
    return xdg_config_home() / "fastfetch" / "config.jsonc"
