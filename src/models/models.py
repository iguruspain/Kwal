"""Facade module re-exporting all Kwal models for backward compatibility.

The concrete implementations live in feature-specific modules:

- :mod:`.common`            — shared dataclasses (``Folder``, ``SettingsApp``)
- :mod:`.wallpaper_models`  — wallpaper folder/image models and scanners
- :mod:`.settings_models`   — settings app list model
- :mod:`.starship_models`   — Starship template and config models
- :mod:`.ulauncher_models`  — Ulauncher template and theme models
- :mod:`.svg_worker`        — background SVG recolor worker

Importing from this module keeps existing call sites (e.g. the controller)
unchanged while the code is organized by feature.
"""

from __future__ import annotations

from .common import Folder, SettingsApp
from .settings_models import SettingsAppModel
from .starship_models import StarshipModel, StarshipTemplateModel
from .svg_worker import SvgWorker
from .ulauncher_models import UlauncherModel, UlauncherTemplateModel
from .wallpaper_models import (
    ColorScannerWorker,
    ImageModel,
    ImageScannerWorker,
    WallpaperFolderModel,
)

__all__ = [
    "ColorScannerWorker",
    "Folder",
    "ImageModel",
    "ImageScannerWorker",
    "SettingsApp",
    "SettingsAppModel",
    "StarshipModel",
    "StarshipTemplateModel",
    "SvgWorker",
    "UlauncherModel",
    "UlauncherTemplateModel",
    "WallpaperFolderModel",
]
