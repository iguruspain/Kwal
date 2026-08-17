"""Controller that bridges Python models and QML UI."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional, cast, Any
from PySide6.QtCore import QObject
from ..models.models import Folder, ImageModel, SettingsApp, SettingsAppModel, StarshipModel, StarshipTemplateModel, SvgWorker, WallpaperFolderModel, UlauncherModel, UlauncherTemplateModel
from ..utils.palette_worker import PaletteWorker
from ..utils.xdg_paths import kwal_config_dir

from .base_controller import BaseMixin
from .fastfetch_controller import FastfetchMixin
from .starship_controller import StarshipMixin
from .svg_recolor_controller import SvgMixin
from .ulauncher_controller import UlauncherMixin
from .wallpapers_controller import WallpapersMixin
from ..providers.svg_provider import SvgImageProvider


class Controller(BaseMixin, WallpapersMixin, FastfetchMixin, StarshipMixin, UlauncherMixin, SvgMixin, QObject):
    """Controller that bridges Python models and QML UI."""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)

        self._current_palette_data: dict[str, Any] = {}

        # State Variables
        self._selected_folder: str = ""
        self._selected_wallpaper: str = ""
        self._last_set_wallpaper: str = ""
        self._selected_wallpaper_resolution: str = ""
        self._thumb_path: str = ""
        self._selected_file: str = ""
        self._fastfetch_tinted_preview: str = ""
        self._fastfetch_tinting: bool = False
        self._fastfetch_config_image: str = ""
        self._result_dialog_visible: bool = False
        self._result_dialog_text: str = ""
        self._templates_installed: bool = False
        self._custom_commands: list[dict[str, Any]] = []
        self._wallpaper_colors: list[str] = []
        
        # Draft State (Persist across tabs)
        self._fastfetch_draft_color: str = "transparent"
        
        # Starship Draft State (Persist across tabs)
        self._starship_draft_color: str = "transparent"
        self._starship_is_file_mode: bool = False
        self._starship_template_index: int = -1

        # Compositing state (True by default for modern desktops)
        self._compositing_enabled: bool = True

        # Dev toggle: simulate all apps installed
        self._simulate_all_apps: bool = False

        # UI preference: show file extension badge on wallpaper thumbnails
        self._show_extension_badge: bool = True

        # Thread References
        self._tint_thread: Optional[threading.Thread] = None
        self._apply_thread: Optional[threading.Thread] = None
        self._color_extraction_thread: Optional[threading.Thread] = None
        self._colorsExtracted.connect(self._update_colors_main_thread)
        # Palette workers (to avoid premature destruction and track latest request)
        self._palette_workers: set[PaletteWorker] = set()
        self._latest_palette_request_id: int = 0

        # Helper Paths
        # expose home path for QML convenience (ensure trailing slash)
        self._home_path: str = str(Path.home()).rstrip("/") + "/"
        
        # Configuration
        self._config_path_file = self._get_config_path_file()
        config = self._load_config()
        loaded_folders = config.get("folders", [])
        last_selected = cast(str, config.get("selected_folder", ""))
        self._last_set_wallpaper = cast(str, config.get("last_set_wallpaper", ""))
        if "custom_commands" in config and isinstance(config["custom_commands"], list):
            self._custom_commands = self._normalize_custom_commands(config["custom_commands"])
        else:
            self._custom_commands = []

        # Initialize Models
        folders: list[Folder] = []
        if loaded_folders:
            folders = [Folder(name=f.get("name", ""), path=f.get("path", "")) for f in loaded_folders]
        
        if not folders:
            # Default fallback
            folders = [Folder(name="Local", path="/usr/share/wallpapers")]

        self._model = WallpaperFolderModel(folders)
        self._image_model = ImageModel()

        # Settings App Model
        # Full list of optional apps (used for simulate mode and filtering)
        self._optional_apps: list[tuple[str, SettingsApp]] = [
            ("fastfetch", SettingsApp(app_name="fastfetch", section="Apps", qml_page="apps/fastfetch.qml")),
            ("starship", SettingsApp(app_name="starship", section="Apps", qml_page="apps/starship.qml")),
            ("ulauncher", SettingsApp(app_name="ulauncher", section="Apps", qml_page="apps/ulauncher.qml")),
        ]
        self._settings_app_model = SettingsAppModel(self._build_app_list())
        # Starship model
        try:
            # Default template folder similar to fastfetch
            default_starship_templates = str(kwal_config_dir() / "templates" / "starship")
            self._starship_model = StarshipModel(template_folder=default_starship_templates)
            self._starship_template_model = StarshipTemplateModel()
            self._starship_template_model.refresh(default_starship_templates)
            # Attempt an initial refresh (safe no-op if file absent)
            try:
                self._starship_model.refresh()
            except Exception:
                self._logger.debug("Initial starship model refresh failed or file missing")
        except Exception:
            self._logger.exception("Failed initializing StarshipModel")

        # Ulauncher model
        try:
            default_ulauncher_templates = str(kwal_config_dir() / "templates" / "ulauncher")
            self._ulauncher_model = UlauncherModel(template_folder=default_ulauncher_templates)
            self._ulauncher_template_model = UlauncherTemplateModel()
            self._ulauncher_template_model.refresh(default_ulauncher_templates)
            try:
                self._ulauncher_model.refresh()
            except Exception:
                self._logger.debug("Initial ulauncher model refresh failed or no theme set")
            self._ulauncher_model.configPathChanged.connect(self.ulauncherBackupExistsChanged)
        except Exception:
            self._logger.exception("Failed initializing UlauncherModel")

        # Connect Signals
        self.tintResult.connect(self._on_tint_done)

        # SVG Recolor state (persists across tab switches)
        self._svg_directory: str = ""
        self._svg_gradient_colors: list[str] = [
            "#000000", "#464646", "#D81C4A", "#b6b6b6", "#FFFFFF", "#888888",
        ]
        self._svg_color_count: int = 5
        self._svg_mono_color: str = "#ACACAC"
        self._svg_preview_dir: str = ""
        self._svg_backup_dir: str = ""
        self._svg_preview_files: list[str] = []
        self._svg_preview_index: int = 0
        self._svg_processing: bool = False
        self._svg_log: str = ""
        self._svg_original_files: dict[str, str] = {}  # preview_path -> original_path
        self._svg_preview_timestamp: int = 0
        self._svg_worker: SvgWorker | None = None

        # Update State
        self._templates_installed = self._check_templates_installed()
        
        # Initialize Fastfetch config image state
        init_img = self._detect_current_fastfetch_image()
        if init_img:
            self._fastfetch_config_image = "file://" + init_img

        # Restore Selection
        self._restore_folder_selection(last_selected)
