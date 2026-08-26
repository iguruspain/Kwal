"""Controller that bridges Python models and QML UI."""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import QObject

from ..providers.svg_provider import SvgImageProvider  # noqa: F401  # re-exported for app.py
from .base_controller import BaseMixin
from .commands_controller import CommandsMixin
from .fastfetch_controller import FastfetchMixin
from .starship_controller import StarshipMixin
from .svg_recolor_controller import SvgMixin
from .ulauncher_controller import UlauncherMixin
from .wallpapers_controller import WallpapersMixin


class Controller(
    BaseMixin, CommandsMixin, WallpapersMixin, FastfetchMixin,
    StarshipMixin, UlauncherMixin, SvgMixin, QObject,
):
    """Controller that bridges Python models and QML UI."""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)

        self._init_base()
        self._init_wallpapers()
        self._init_fastfetch()
        self._init_starship()
        self._init_ulauncher()
        self._init_svg()
        self._restore_folder_selection(self._last_selected_folder)
