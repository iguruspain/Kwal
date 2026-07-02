from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional, cast, Any

from PySide6.QtCore import (
    QCoreApplication,
    QObject,
    Property,
    QStandardPaths,
    QThread,
    Signal,
    Slot,
    Qt,
    QSize,
)
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QColorDialog, QFileDialog
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

from ..models.models import (
    FastfetchTemplateModel,
    Folder,
    ImageModel,
    SettingsApp,
    SettingsAppModel,
    # Starship model will be used to expose starship config to QML
    StarshipModel,
    StarshipTemplateModel,
    SvgWorker,
    WallpaperFolderModel,
    UlauncherModel,
    UlauncherTemplateModel,
)
from ..utils import color_utils, file_utils
from ..utils.svg_utils import get_svg_preview_cache_dir


class SvgImageProvider(QQuickImageProvider):
    """QQuickImageProvider that renders SVG files on demand for QML Image items.

    Usage in QML:  Image { source: "image://svgprovider" + absoluteSvgPath + "?t=" + cacheBuster }
    The query string is stripped before loading so callers can force reloads.
    """

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, id: str, size: QSize, requestedSize: QSize) -> QImage:  # type: ignore[override]
        # Strip cache-busting query (e.g. "?t=123")
        path = id.split("?")[0]
        if not path.startswith("/"):
            path = "/" + path

        w = requestedSize.width() if requestedSize.width() > 0 else 256
        h = requestedSize.height() if requestedSize.height() > 0 else 256

        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)

        try:
            from pathlib import Path as _Path

            p = _Path(path)
            if p.exists() and p.is_file():
                renderer = QSvgRenderer(path)
                if renderer.isValid():
                    painter = QPainter(img)
                    renderer.render(painter)
                    painter.end()
        except Exception:
            logging.getLogger(__name__).debug(
                "SvgImageProvider: failed rendering %s", path, exc_info=True
            )

        # Set the out-parameter so QML knows the actual rendered size
        size.setWidth(img.width())
        size.setHeight(img.height())
        return img


class PaletteWorker(QThread):
    # Renamed to avoid shadowing QThread.finished
    dataReady = Signal(dict)
    error = Signal(str)

    def __init__(self, path: str, backend: str, kwargs: dict[str, Any]):
        super().__init__()
        self.path = path
        self.backend = backend
        self.kwargs = kwargs

    def run(self):
        try:
            # Import here to avoid circular imports if module-level import is problematic
            # But normally we import models at top. We just ensure we use color_utils
            # which might import PaletteData.
            pdata = color_utils.extract_palette(self.path, self.backend, **self.kwargs)
            result = {
                "colors": pdata.colors,
                "accents": pdata.accents,
                "backend": pdata.backend_used,
                "source": pdata.source_path,
                "seed": pdata.seed
            }
            self.dataReady.emit(result)
        except Exception as e:
            logging.exception("Palette extraction failed")
            self.error.emit(str(e))


class Controller(QObject):
    """Controller that bridges Python models and QML UI."""

    # Signals
    selectedFolderChanged = Signal()
    selectedWallpaperChanged = Signal()
    templatesInstalledChanged = Signal()
    selectedFileChanged = Signal()
    fastfetchTintedPreviewChanged = Signal()
    fastfetchTintingChanged = Signal()
    resultDialogVisibleChanged = Signal()
    resultDialogTextChanged = Signal()
    fastfetchDestNameChanged = Signal()
    fastfetchBackupExistsChanged = Signal()
    fastfetchConfigImageChanged = Signal()
    # Palette signals
    currentPaletteDataChanged = Signal()
    paletteGenerationError = Signal(str)
    # Draft signals
    fastfetchDraftColorChanged = Signal()
    fastfetchIsFileModeChanged = Signal()
    fastfetchTemplateIndexChanged = Signal()
    # Starship Draft signals
    starshipDraftColorChanged = Signal()
    starshipIsFileModeChanged = Signal()
    starshipTemplateIndexChanged = Signal()
    starshipBackupExistsChanged = Signal()
    # Signal for compositing
    compositingEnabledChanged = Signal()
    # Signal for simulate all apps dev toggle
    simulateAllAppsChanged = Signal()
    # Signal for wallpaper extension badge visibility
    showExtensionBadgeChanged = Signal()
    # Wallpaper custom command signal
    customCommandWallpaperChanged = Signal()
    customCommandWallpaper2Changed = Signal()
    customCommandWallpaper3Changed = Signal()

    tintResult = Signal(str)
    fastfetchApplyResult = Signal(bool, str)
    
    # Global notification signal (message, type["error"|"success"|"info"])
    notification = Signal(str, str)

    # Wallpaper color extraction
    wallpaperColorsChanged = Signal()


    # SVG Recolor signals
    svgDirectoryChanged = Signal()
    svgGradientColorsChanged = Signal()
    svgColorCountChanged = Signal()
    svgMonoColorChanged = Signal()
    svgProcessingChanged = Signal()
    svgLogTextChanged = Signal()
    svgPreviewFilesChanged = Signal()
    svgPreviewIndexChanged = Signal()
    svgCurrentPreviewFileChanged = Signal()
    svgPreviewTimestampChanged = Signal()
    svgHasPreviewChanged = Signal()
    svgHasBackupChanged = Signal()

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)

        self._current_palette_data: dict[str, Any] = {}

        # State Variables
        self._selected_folder: str = ""
        self._selected_wallpaper: str = ""
        self._last_set_wallpaper: str = ""
        self._selected_wallpaper_resolution: str = ""
        self._selected_file: str = ""
        self._fastfetch_tinted_preview: str = ""
        self._fastfetch_tinting: bool = False
        self._fastfetch_dest_name: str = ""
        self._fastfetch_config_image: str = ""
        self._result_dialog_visible: bool = False
        self._result_dialog_text: str = ""
        self._templates_installed: bool = False
        self._custom_command_wallpaper: str = ""
        self._custom_command_wallpaper2: str = ""
        self._custom_command_wallpaper3: str = ""
        self._wallpaper_colors: list[str] = []
        
        # Draft State (Persist across tabs)
        self._fastfetch_draft_color: str = "transparent"
        self._fastfetch_is_file_mode: bool = False
        self._fastfetch_template_index: int = -1
        
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
        self._custom_command_wallpaper = cast(str, config.get("custom_command_wallpaper", ""))
        self._custom_command_wallpaper2 = cast(str, config.get("custom_command_wallpaper2", ""))
        self._custom_command_wallpaper3 = cast(str, config.get("custom_command_wallpaper3", ""))

        # Initialize Models
        folders: list[Folder] = []
        if loaded_folders:
            folders = [Folder(name=f.get("name", ""), path=f.get("path", "")) for f in loaded_folders]
        
        if not folders:
            # Default fallback
            folders = [Folder(name="Local", path="/usr/share/wallpapers")]

        self._model = WallpaperFolderModel(folders)
        self._image_model = ImageModel()

        # Fastfetch Model
        self._fastfetch_model = FastfetchTemplateModel()
        self._fastfetch_templates_folder = str(Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kwal" / "templates" / "fastfetch")
        
        try:
            self._fastfetch_model.refresh(self._fastfetch_templates_folder)
        except Exception:
            self._logger.debug("Initial fastfetch template refresh failed or empty")

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
            default_starship_templates = str(Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kwal" / "templates" / "starship")
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
            default_ulauncher_templates = str(Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kwal" / "templates" / "ulauncher")
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

    def _get_config_path_file(self) -> Path:
        cfg_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kwal"
        cfg_dir.mkdir(parents=True, exist_ok=True)
        return cfg_dir / "folders.json"

    def _load_config(self) -> dict[str, Any]:
        """Load persisted config."""
        default_config: dict[str, Any] = {"folders": [], "selected_folder": ""}
        if not self._config_path_file.exists():
            return default_config
        
        try:
            with open(self._config_path_file, "r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    # Migration from old list-only format
                    return {"folders": data, "selected_folder": ""}
                if isinstance(data, dict):
                    return data
                return default_config
        except Exception:
            self._logger.exception("Failed reading config file %s", self._config_path_file)
            return default_config

    def _save_config(self) -> None:
        """Save current state into config file."""
        data = {
            "folders": [{"name": f.name, "path": f.path} for f in self._model._folders],
            "selected_folder": self._selected_folder
        }
        if self._last_set_wallpaper:
            data["last_set_wallpaper"] = self._last_set_wallpaper
        if self._custom_command_wallpaper:
            data["custom_command_wallpaper"] = self._custom_command_wallpaper
        if self._custom_command_wallpaper2:
            data["custom_command_wallpaper2"] = self._custom_command_wallpaper2
        if self._custom_command_wallpaper3:
            data["custom_command_wallpaper3"] = self._custom_command_wallpaper3
            
        try:
            with open(self._config_path_file, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
        except Exception as e:
            self._logger.exception("Failed saving config")
            self.notification.emit(f"Failed to save config: {e}", "error")

    def _restore_folder_selection(self, last_selected: str) -> None:
        initial_index = 0
        if last_selected:
            for i, f in enumerate(self._model._folders):
                if f.path == last_selected:
                    initial_index = i
                    break
        
        if self._model.rowCount() > 0 and QCoreApplication.instance() is not None:
            self.selectFolder(initial_index)

    # --- Property Accessors ---

    def wallpaperModel(self) -> WallpaperFolderModel:
        return self._model

    def fastfetchTemplateModel(self) -> FastfetchTemplateModel:
        return self._fastfetch_model

    @Property(QObject, constant=True)
    def settingsAppModel(self) -> SettingsAppModel:
        return self._settings_app_model

    def imageModel(self) -> ImageModel:
        return self._image_model

    @Property(QObject, constant=True)
    def starshipModel(self) -> QObject:
        """Expose the StarshipModel instance to QML as an object."""
        return getattr(self, "_starship_model", None)

    def _get_home_path(self) -> str:
        return self._home_path

    homePath = Property(str, _get_home_path, constant=True)

    def _get_selected_wallpaper(self) -> str:
        return self._selected_wallpaper

    selectedWallpaper = Property(str, _get_selected_wallpaper, notify=selectedWallpaperChanged)

    def _get_selected_wallpaper_resolution(self) -> str:
        return self._selected_wallpaper_resolution

    selectedWallpaperResolution = Property(str, _get_selected_wallpaper_resolution, notify=selectedWallpaperChanged)

    def _get_wallpaper_colors(self) -> list[str]:
        return self._wallpaper_colors

    wallpaperColors = Property("QVariantList", _get_wallpaper_colors, notify=wallpaperColorsChanged)

    def _get_selected_file(self) -> str:
        return self._selected_file

    selectedFile = Property(str, _get_selected_file, notify=selectedFileChanged)

    def _get_selected_folder(self) -> str:
        return self._selected_folder

    selectedFolder = Property(str, _get_selected_folder, notify=selectedFolderChanged)

    def _get_fastfetch_tinted_preview(self) -> str:
        return self._fastfetch_tinted_preview

    fastfetchTintedPreview = Property(str, _get_fastfetch_tinted_preview, notify=fastfetchTintedPreviewChanged)

    def _get_fastfetch_tinting(self) -> bool:
        return self._fastfetch_tinting

    fastfetchTinting = Property(bool, _get_fastfetch_tinting, notify=fastfetchTintingChanged)

    def _get_fastfetch_dest_name(self) -> str:
        return self._fastfetch_dest_name

    def _set_fastfetch_dest_name(self, name: str) -> None:
        val = name or ""
        if self._fastfetch_dest_name != val:
            self._fastfetch_dest_name = val
            self.fastfetchDestNameChanged.emit()

    fastfetchDestName = Property(str, _get_fastfetch_dest_name, _set_fastfetch_dest_name, notify=fastfetchDestNameChanged)

    def _get_fastfetch_config_image(self) -> str:
        return self._fastfetch_config_image

    def _set_fastfetch_config_image(self, path: str) -> None:
        p = path or ""
        if self._fastfetch_config_image != p:
            self._fastfetch_config_image = p
            self.fastfetchConfigImageChanged.emit()

    fastfetchConfigImage = Property(str, _get_fastfetch_config_image, _set_fastfetch_config_image, notify=fastfetchConfigImageChanged)

    def _get_result_dialog_visible(self) -> bool:
        return self._result_dialog_visible

    def _set_result_dialog_visible(self, v: bool) -> None:
        v_bool = bool(v)
        if self._result_dialog_visible != v_bool:
            self._result_dialog_visible = v_bool
            self.resultDialogVisibleChanged.emit()

    resultDialogVisible = Property(bool, _get_result_dialog_visible, _set_result_dialog_visible, notify=resultDialogVisibleChanged)

    def _get_result_dialog_text(self) -> str:
        return self._result_dialog_text

    def _set_result_dialog_text(self, txt: str) -> None:
        t = txt or ""
        if self._result_dialog_text != t:
            self._result_dialog_text = t
            self.resultDialogTextChanged.emit()

    resultDialogText = Property(str, _get_result_dialog_text, _set_result_dialog_text, notify=resultDialogTextChanged)

    def _get_fastfetch_backup_exists(self) -> bool:
        cfg = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "fastfetch" / "config.jsonc"
        bak = cfg.with_name(cfg.name + ".bak")
        return bak.exists() and bak.is_file()

    hasFastfetchBackup = Property(bool, _get_fastfetch_backup_exists, notify=fastfetchBackupExistsChanged)

    def _get_custom_command_wallpaper(self) -> str:
        return self._custom_command_wallpaper

    def _set_custom_command_wallpaper(self, cmd: str) -> None:
        val = cmd or ""
        if self._custom_command_wallpaper != val:
            self._custom_command_wallpaper = val
            self._save_config()
            self.customCommandWallpaperChanged.emit()

    customCommandWallpaper = Property(
        str,
        _get_custom_command_wallpaper,
        _set_custom_command_wallpaper,
        notify=customCommandWallpaperChanged,
    )

    def _get_custom_command_wallpaper2(self) -> str:
        return self._custom_command_wallpaper2

    def _set_custom_command_wallpaper2(self, cmd: str) -> None:
        val = cmd or ""
        if self._custom_command_wallpaper2 != val:
            self._custom_command_wallpaper2 = val
            self._save_config()
            self.customCommandWallpaper2Changed.emit()

    customCommandWallpaper2 = Property(
        str,
        _get_custom_command_wallpaper2,
        _set_custom_command_wallpaper2,
        notify=customCommandWallpaper2Changed,
    )

    def _get_custom_command_wallpaper3(self) -> str:
        return self._custom_command_wallpaper3

    def _set_custom_command_wallpaper3(self, cmd: str) -> None:
        val = cmd or ""
        if self._custom_command_wallpaper3 != val:
            self._custom_command_wallpaper3 = val
            self._save_config()
            self.customCommandWallpaper3Changed.emit()

    customCommandWallpaper3 = Property(
        str,
        _get_custom_command_wallpaper3,
        _set_custom_command_wallpaper3,
        notify=customCommandWallpaper3Changed,
    )

    # --- Compositing Control ---

    @Property(bool, notify=compositingEnabledChanged)
    def compositingEnabled(self) -> bool:
        return self._compositing_enabled

    @compositingEnabled.setter
    def compositingEnabled(self, value: bool) -> None:
        if self._compositing_enabled != value:
            self._compositing_enabled = value
            self.compositingEnabledChanged.emit()

    @Slot()
    def toggleCompositing(self) -> None:
        self.compositingEnabled = not self._compositing_enabled

    # --- Simulate All Apps (Dev Toggle) ---

    @Property(bool, notify=simulateAllAppsChanged)
    def simulateAllApps(self) -> bool:
        return self._simulate_all_apps

    @simulateAllApps.setter
    def simulateAllApps(self, value: bool) -> None:
        if self._simulate_all_apps != value:
            self._simulate_all_apps = value
            self.simulateAllAppsChanged.emit()
            self._settings_app_model.resetApps(self._build_app_list())
            self._logger.info("Simulate all apps: %s", value)

    @Slot()
    def toggleSimulateAllApps(self) -> None:
        self.simulateAllApps = not self._simulate_all_apps

    # --- Wallpaper Extension Badge ---

    @Property(bool, notify=showExtensionBadgeChanged)
    def showExtensionBadge(self) -> bool:
        return self._show_extension_badge

    @showExtensionBadge.setter
    def showExtensionBadge(self, value: bool) -> None:
        if self._show_extension_badge != value:
            self._show_extension_badge = value
            self.showExtensionBadgeChanged.emit()

    @Slot()
    def toggleExtensionBadge(self) -> None:
        self.showExtensionBadge = not self._show_extension_badge

    def _build_app_list(self) -> list[SettingsApp]:
        """Build the list of app tabs based on installed apps or simulate mode."""
        # Wallpapers is always available; optional app tabs are added next; SVG Recolor goes last
        apps: list[SettingsApp] = [
            SettingsApp(app_name="wallpapers", section="Apps", qml_page="apps/wallpapers.qml"),
        ]
        for binary_name, setting in self._optional_apps:
            if self._simulate_all_apps or shutil.which(binary_name):
                apps.append(setting)
                self._logger.info("Detected '%s' installed, enabling tab", binary_name)
            else:
                self._logger.info("'%s' not found in PATH, tab hidden", binary_name)
        apps.append(SettingsApp(app_name="SVG Recolor", section="Apps", qml_page="apps/svgrecolor.qml", title="SVG Recolor"))
        return apps

    # --- Draft Properties ---

    def _get_fastfetch_draft_color(self) -> str:
        return self._fastfetch_draft_color

    def _set_fastfetch_draft_color(self, color: str) -> None:
        # Normalize incoming color to a consistent #AARRGGBB when possible.
        val = color or ""
        norm: str = val
        try:
            if val and val.lower() != "transparent" and QColor.isValidColor(val):
                qc = QColor(val)
                try:
                    norm = qc.name(QColor.HexArgb)
                except TypeError:
                    # Fallback construction: #AARRGGBB
                    norm = "#{:02x}{:02x}{:02x}{:02x}".format(qc.alpha(), qc.red(), qc.green(), qc.blue())
        except Exception:
            self._logger.debug("Failed normalizing color %r", val)

        if self._fastfetch_draft_color != norm:
            self._fastfetch_draft_color = norm
            self.fastfetchDraftColorChanged.emit()

    @Slot(str, result=str)
    def normalizeColor(self, color: str) -> str:
        """Convert CSS color string to QML-compatible hex string (#AARRGGBB)."""
        try:
            c = color_utils.parse_css_color(color)
            if c.isValid():
                return c.name(QColor.HexArgb)
            return str(color)
        except Exception:
            return str(color)

    @Slot(str, result=str)
    def formatColorWithAlpha(self, color: str) -> str:
        """Return a display string with RGB hex and alpha decimal for QML tooltips.

        Examples:
        - input: "#AARRGGBB" -> returns: "#RRGGBB alpha: 204"
        - input: "rgba(32, 24, 18, 0.8)" -> returns: "#201812 alpha: 204"
        """
        try:
            c = color_utils.parse_css_color(color)
            if not c.isValid():
                return str(color)

            # Format manually to ensure consistent output
            alpha = c.alpha()
            # Calculate percent (0-100)
            val = alpha / 255.0
            perc = int(round(val * 100))
             
            # If standard hex form is requested by QML tooltip style
            return f"#{c.red():02x}{c.green():02x}{c.blue():02x} alpha: {alpha} ({perc}%)"
        except Exception:
            self._logger.exception("Error formatting color tooltip for %r", color)
            return str(color or "")

    @Slot(str, result=bool)
    def isVideoFile(self, file_path: str) -> bool:
        """Check if a file is a supported video format."""
        try:
            from ..utils import video_utils
            return video_utils.is_video_file(file_path)
        except Exception:
            return False

    fastfetchDraftColor = Property(str, _get_fastfetch_draft_color, _set_fastfetch_draft_color, notify=fastfetchDraftColorChanged)

    def _get_fastfetch_is_file_mode(self) -> bool:
        return self._fastfetch_is_file_mode

    def _set_fastfetch_is_file_mode(self, v: bool) -> None:
        if self._fastfetch_is_file_mode != v:
            self._fastfetch_is_file_mode = v
            self.fastfetchIsFileModeChanged.emit()

    fastfetchIsFileMode = Property(bool, _get_fastfetch_is_file_mode, _set_fastfetch_is_file_mode, notify=fastfetchIsFileModeChanged)

    def _get_fastfetch_template_index(self) -> int:
        return self._fastfetch_template_index

    def _set_fastfetch_template_index(self, idx: int) -> None:
        if self._fastfetch_template_index != idx:
            self._fastfetch_template_index = idx
            self.fastfetchTemplateIndexChanged.emit()

    fastfetchTemplateIndex = Property(int, _get_fastfetch_template_index, _set_fastfetch_template_index, notify=fastfetchTemplateIndexChanged)

    # --- Starship Properties ---

    def _get_starship_draft_color(self) -> str:
        return self._starship_draft_color
    
    def _set_starship_draft_color(self, val: str) -> None:
        if self._starship_draft_color != val:
            self._starship_draft_color = val
            self.starshipDraftColorChanged.emit()
    
    starshipDraftColor = Property(str, _get_starship_draft_color, _set_starship_draft_color, notify=starshipDraftColorChanged)

    def _get_starship_is_file_mode(self) -> bool:
        return self._starship_is_file_mode
    
    def _set_starship_is_file_mode(self, val: bool) -> None:
        if self._starship_is_file_mode != val:
            self._starship_is_file_mode = val
            self.starshipIsFileModeChanged.emit()

    starshipIsFileMode = Property(bool, _get_starship_is_file_mode, _set_starship_is_file_mode, notify=starshipIsFileModeChanged)

    def _get_starship_template_index(self) -> int:
        return self._starship_template_index

    def _set_starship_template_index(self, val: int) -> None:
        if self._starship_template_index != val:
            self._starship_template_index = val
            self.starshipTemplateIndexChanged.emit()

    starshipTemplateIndex = Property(int, _get_starship_template_index, _set_starship_template_index, notify=starshipTemplateIndexChanged)

    @Property(QObject, constant=True)
    def starshipTemplateModel(self) -> StarshipTemplateModel:
        return self._starship_template_model

    def _get_starship_backup_exists(self) -> bool:
        cfg = Path.home() / ".config" / "starship.toml"
        bak = cfg.with_name(cfg.name + ".bak")
        return bak.exists() and bak.is_file()

    hasStarshipBackup = Property(bool, _get_starship_backup_exists, notify=starshipBackupExistsChanged)

    @Property(bool, notify=starshipBackupExistsChanged) # Re-using signal for simplicity as file IO usually affects both
    def hasStarshipConfig(self) -> bool:
        cfg = Path.home() / ".config" / "starship.toml"
        return cfg.exists() and cfg.is_file()

    # --- Slots & Logic ---

    @Slot(result=str)
    def longestSettingsTitle(self) -> str:
        """Return the longest settings app title."""
        try:
            apps = getattr(self._settings_app_model, "_apps", []) or []
            longest = ""
            for a in apps:
                t = getattr(a, "title", "") or ""
                if len(t) > len(longest):
                    longest = t
            return longest
        except Exception:
            self._logger.exception("Error computing longest settings title")
            return ""

    @Slot(result=bool)
    def templatesInstalled(self) -> bool:
        return self._templates_installed

    @Slot(result=bool)
    def _check_templates_installed(self) -> bool:
        cfg_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kwal" / "templates"
        try:
            return cfg_dir.exists() and any(cfg_dir.iterdir())
        except Exception:
            return False

    @Slot(result=bool)
    def installTemplates(self) -> bool:
        """Attempt to install packaged templates to user's XDG config."""
        try:
            from ..utils.template_installer import install_templates_to_user
            install_templates_to_user()
            self._templates_installed = self._check_templates_installed()
            self.templatesInstalledChanged.emit()
            return self._templates_installed
        except Exception:
            self._logger.exception("Failed to install templates")
            return False

    @Slot(str, str, result=str)
    def generateTintedPreview(self, src: str, tint_hex: str, strength: float = 0.8) -> str:
        """Generate a tinted preview in a background thread."""
        if src.startswith("file://"):
            src_path = src.replace("file://", "")
        else:
            src_path = src

        if not self._is_valid_tint(tint_hex):
            self._clear_tinted_preview()
            return ""

        try:
            self._fastfetch_tinting = True
            self.fastfetchTintingChanged.emit()
            
            thr = threading.Thread(
                target=self._tint_image_task, 
                args=(src_path, tint_hex, float(strength)), 
                daemon=True
            )
            thr.start()
            self._tint_thread = thr
            return ""
        except Exception:
            self._logger.exception("Failed starting background tint thread for %s", src)
            return ""

    def _is_valid_tint(self, tint_hex: str) -> bool:
        try:
            if not tint_hex or str(tint_hex).lower() == "transparent":
                return False
            return QColor.isValidColor(tint_hex)
        except Exception:
            self._logger.debug("Validation failed for color %r", tint_hex)
            return False

    def _clear_tinted_preview(self) -> None:
        self._fastfetch_tinted_preview = ""
        self.fastfetchTintedPreviewChanged.emit()

    def _tint_image_task(self, src: str, tint_hex: str, strength: float) -> None:
        """Background task for tinting."""
        try:
            res = color_utils.tint_image(src, tint_hex, strength)
            self.tintResult.emit(res if res else "")
        except Exception:
            self._logger.exception("Background tint failed for %s", src)
            self.tintResult.emit("")

    @Slot(str)
    def _on_tint_done(self, dst: str) -> None:
        """Handle tint completion."""
        try:
            self._fastfetch_tinted_preview = ("file://" + str(Path(dst))) if dst else ""
            self.fastfetchTintedPreviewChanged.emit()
        finally:
            self._fastfetch_tinting = False
            self.fastfetchTintingChanged.emit()
            self._tint_thread = None

    @Slot(str)
    def refreshFastfetchTemplates(self, folder: str) -> None:
        try:
            self._fastfetch_templates_folder = folder or self._fastfetch_templates_folder
            self._fastfetch_model.refresh(self._fastfetch_templates_folder)
        except Exception:
            self._logger.exception("Failed refreshing fastfetch templates for %s", folder)

    @Slot()
    def refreshFastfetchConfigImage(self) -> None:
        """Re-detect the current fastfetch config image from disk.
        
        Forces re-read and emits change signal with a cache-buster to ensure
        QML Image reloads even if the file path is the same but content changed.
        """
        try:
            import time
            detected = self._detect_current_fastfetch_image()
            if detected:
                # Append cache-buster to force QML Image reload
                url = f"file://{detected}?t={int(time.time() * 1000)}"
                self._fastfetch_config_image = url
                self.fastfetchConfigImageChanged.emit()
            else:
                if self._fastfetch_config_image != "":
                    self._fastfetch_config_image = ""
                    self.fastfetchConfigImageChanged.emit()
        except Exception:
            self._logger.exception("Failed refreshing fastfetch config image")

    @Slot(result="QVariantMap")
    def getFastfetchInfo(self) -> dict[str, str]:
        """Return info for QML."""
        try:
            config_image = self._detect_current_fastfetch_image()
            # Also update property if it differs (sync state)
            if config_image:
                 url = "file://" + config_image
                 if self._fastfetch_config_image != url:
                     self._fastfetch_config_image = url
                     self.fastfetchConfigImageChanged.emit()

            return {
                "config_image": config_image, 
                "template_folder": self._fastfetch_templates_folder, 
                "config_path": ""  # path logic simplified out of detection
            }
        except Exception:
            self._logger.exception("Failed reading fastfetch info")
            return {
                "config_image": "", 
                "template_folder": self._fastfetch_templates_folder, 
                "config_path": ""
            }

    def _detect_current_fastfetch_image(self) -> str:
        try:
            config_image = ""
            for key in ("config_image", "image", "source", "logo", "icon"):
                val, _ = file_utils.read_config_fastfetch(key, None)
                if val:
                    p = Path(str(val)).expanduser()
                    if p.exists():
                        config_image = str(p)
                        break
            
            if not config_image:
                fallback = Path.home() / ".config" / "fastfetch" / "chica-tinted.png"
                if fallback.exists():
                    config_image = str(fallback)
            return config_image
        except Exception:
            self._logger.warning("Error detecting fastfetch image")
            return ""

    @Slot(str)
    def selectWallpaper(self, path: str) -> None:
        try:
            if self._selected_wallpaper != path:
                self._selected_wallpaper = path
                
                if path:
                    from ..utils import video_utils, color_extractor
                    
                    # For videos, extract frame and use that for color extraction
                    image_for_colors = path
                    if video_utils.is_video_file(path):
                        try:
                            frame_path = video_utils.get_video_frame_path(path)
                            if frame_path:
                                image_for_colors = frame_path
                                self._logger.info("Using video frame for color extraction: %s", frame_path)
                        except Exception as e:
                            self._logger.warning("Failed to extract video frame for colors: %s", e)
                    
                    img = QImage(image_for_colors)
                    if not img.isNull():
                        self._selected_wallpaper_resolution = f"{img.width()}x{img.height()}"
                        
                        cache = color_extractor.load_color_cache()
                        if path in cache and "colors" in cache[path]:
                            self._wallpaper_colors = cache[path]["colors"]
                            self.wallpaperColorsChanged.emit()
                            self._logger.info("Instantly loaded wallpaper colors from cache.")
                        else:
                            self._start_color_extraction(image_for_colors)
                    else:
                        self._selected_wallpaper_resolution = ""
                        self._wallpaper_colors = []
                        self.wallpaperColorsChanged.emit()
                else:
                    self._selected_wallpaper_resolution = ""
                    self._wallpaper_colors = []
                    self.wallpaperColorsChanged.emit()
                    
                self.selectedWallpaperChanged.emit()
        except Exception:
            self._logger.exception("Error selecting wallpaper %r", path)

    # Signals for internal threading
    _colorsExtracted = Signal(list)

    def _start_color_extraction(self, image_path: str) -> None:
        """Starts a background thread to extract top colors using Celebi quantization."""
        self._color_extraction_thread = threading.Thread(
            target=self._extract_colors_task,
            args=(image_path,),
            daemon=True
        )
        self._color_extraction_thread.start()

    def _extract_colors_task(self, image_path: str) -> None:
        """Background task to extract colors using materialyoucolor.
        
        Like matugen, it resizes the image to 128x128 for speed, 
        then uses Celebi algorithm to quantize colors, and scores them.
        """
        try:
            from ..utils.color_utils import extract_wallpaper_top_colors
            from ..utils import color_extractor
            import os
            
            hex_colors = extract_wallpaper_top_colors(image_path, count=8)
            self._logger.info(f"Extracted wallpaper colors: {hex_colors}")
            
            if hex_colors:
                try:
                    cache = color_extractor.load_color_cache()
                    cats = []
                    for c in hex_colors:
                        cat = color_extractor.get_color_category(c)
                        if cat not in cats:
                            cats.append(cat)
                        if len(cats) >= 3:
                            break
                            
                    cache[image_path] = {
                        "colors": hex_colors,
                        "categories": cats,
                        "last_modified": os.path.getmtime(image_path)
                    }
                    color_extractor.save_color_cache(cache)
                except Exception as cache_err:
                    self._logger.warning("Failed to save extracted colors to cache: %s", cache_err)
            
            # Only update if the selection hasn't changed while we were processing
            if self._selected_wallpaper == image_path:
                self._colorsExtracted.emit(hex_colors)
                
        except Exception as e:
            self._logger.error("Failed to extract wallpaper colors: %s", e)
            self._colorsExtracted.emit([])
            
    @Slot(list)
    def _update_colors_main_thread(self, colors: list) -> None:
        """Safely updates the property on the main thread via Qt slot mechanism."""
        self._logger.info(f"Updating UI with Colors: {colors}")
        self._wallpaper_colors = colors
        self.wallpaperColorsChanged.emit()


    @Slot(str)
    def setAsWallpaper(self, path: str) -> None:
        """Call standard KDE mechanism to set wallpaper."""
        if not path:
            self._logger.warning("setAsWallpaper called with empty path")
            return
            
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            self._logger.error("Wallpaper path does not exist: %s", abs_path)
            return

        self._last_set_wallpaper = abs_path
        self._logger.info("Setting wallpaper to %s", abs_path)
        
        # KDE Plasma via qdbus 
        qdbus_path = shutil.which("qdbus") or shutil.which("qdbus-qt6") or shutil.which("qdbus6")
        if qdbus_path:
            # Escape single quotes for JS string context
            safe_path = abs_path.replace("'", r"\'")
            script = (
                "var allDesktops = desktops();\n"
                "for (var i = 0; i < allDesktops.length; i++) {\n"
                "  var d = allDesktops[i];\n"
                "  d.wallpaperPlugin = 'org.kde.image';\n"
                "  d.currentConfigGroup = Array('Wallpaper','org.kde.image','General');\n"
                f"  d.writeConfig('Image', 'file://{safe_path}');\n"
                "}\n"
            )
            try:
                subprocess.run(
                    [qdbus_path, "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", script],
                    capture_output=True, text=True, check=False
                )
            except Exception as e:
                self._logger.exception("Failed to call qdbus")
                self.notification.emit(f"Failed to apply wallpaper: {e}", "error")
        else:
            self._logger.warning("qdbus not found")
            self.notification.emit("qdbus executable not found (required for KDE Plasma)", "error")
            
        self._save_config()

    @Slot(str)
    def runCMD(self, command: str) -> None:
        """Execute a user-provided shell command in the background (fire & forget)."""
        cmd = (command or "").strip()
        if not cmd:
            return
        try:
            subprocess.Popen(cmd, shell=True, start_new_session=True)
            self._logger.info("Launched custom command: %r", cmd)
        except Exception:
            self._logger.exception("Failed to launch custom command: %r", cmd)
            self.notification.emit(f"Failed to run command: {cmd}", "error")

    @Slot(result=str)
    def getCurrentSystemWallpaper(self) -> str:
        #NEVER TOUCH THIS getCurrentSystemWallpaper FUNCTION ITS CORRECT 
        """Retrieve current wallpaper from KDE Plasma via config file directly (more reliable than qdbus parsing)."""
        # Prefer qdbus / PlasmaShell evaluateScript parsing (uses Plasma's runtime state)
        try:
            qdbus_path = shutil.which("qdbus") or shutil.which("qdbus-qt6") or shutil.which("qdbus6")
            if qdbus_path:
                script = (
                    "var ds = desktops();\n"
                    "for (let i = 0; i < ds.length; i++) {\n"
                    "  if (ds[i].screen == 0) {\n"
                    "    ds[i].currentConfigGroup = Array('Wallpaper', ds[i].wallpaperPlugin, 'General');\n"
                    "    if (ds[i].wallpaperPlugin == 'org.kde.image') {\n"
                    "      print(ds[i].readConfig('Image').replace('file://', ''));\n"
                    "    }\n"
                    "  }\n"
                    "}\n"
                )
                try:
                    proc = subprocess.run(
                        [qdbus_path, "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", script],
                        capture_output=True, text=True, check=False
                    )
                    out = (proc.stdout or "").strip()
                    if out:
                        # Filter empty lines and take first non-empty
                        lines = [l.strip() for l in out.splitlines() if l.strip()]
                        if lines:
                            candidate = lines[0]
                            # If value looks like a file path and exists, return it
                            if os.path.exists(candidate):
                                return candidate
                except Exception:
                    self._logger.debug("qdbus evaluateScript failed", exc_info=True)
        except Exception:
            # Do not fail hard on qdbus detection; fall back to config parsing below
            self._logger.debug("Error checking qdbus for wallpaper", exc_info=True)

        # Fallback: parse plasma-org.kde.plasma.desktop-appletsrc (heuristic)
        try:
            config_path = Path.home() / ".config" / "plasma-org.kde.plasma.desktop-appletsrc"
            if not config_path.exists():
                return self._last_set_wallpaper if self._last_set_wallpaper else ""

            found_image = ""
            with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            in_wallpaper_group = False
            for line in lines:
                line = line.strip()
                if "[Wallpaper]" in line and "org.kde.image" in line:
                    in_wallpaper_group = True
                    continue
                if line.startswith("[") and "Wallpaper" not in line:
                    pass

                if in_wallpaper_group and line.startswith("Image="):
                    val = line.split("=", 1)[1].strip()
                    if val.startswith("file://"):
                        getPath = val[7:]
                        if os.path.exists(getPath):
                            found_image = getPath
                            break

            if found_image:
                return found_image
        except Exception as e:
            self._logger.error("Error reading system wallpaper: %s", e)

        # Final fallback
        return self._last_set_wallpaper if self._last_set_wallpaper else ""

    @Slot(str, str)
    def addFolder(self, name: str, path: str) -> None:
        self._logger.debug("addFolder called: %s %s", name, path)
        norm_path = os.path.normpath(path)

        for f in self._model._folders:
            if os.path.normpath(f.path) == norm_path:
                self._logger.info("Folder %s already present", norm_path)
                return

        self._model.addFolder(name, norm_path)
        
        # Use simple logic to select last
        count = self._model.rowCount()
        if count > 0:
            self.selectFolder(count - 1)
            
        self._save_config()

    @Slot()
    def openFolderDialog(self) -> None:
        try:
            initial_dir = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation) or os.path.expanduser("~")
            selected = QFileDialog.getExistingDirectory(None, "Select Folder", initial_dir)
            
            if selected:
                name = os.path.basename(selected) or selected
                self.addFolder(name, selected)
        except Exception:
            self._logger.exception("Failed in openFolderDialog")

    @Slot(int)
    def removeFolder(self, index: int) -> None:
        # Cast just in case
        try:
            idx = int(index)
        except ValueError:
            return

        if not (0 <= idx < self._model.rowCount()):
            return

        folder_to_remove = self._model._folders[idx]
        was_selected = (folder_to_remove.path == self._selected_folder)

        self._model.removeFolder(idx)
        
        if was_selected:
            new_count = self._model.rowCount()
            if new_count > 0:
                self.selectFolder(min(idx, new_count - 1))
            else:
                self._selected_folder = ""
                self._image_model.setFolder("")
                self.selectedFolderChanged.emit()
        
        self._save_config()

    @Slot(int)
    def selectFolder(self, index: int) -> None:
        try:
            if 0 <= index < len(self._model._folders):
                folder = self._model._folders[index]
                self._selected_folder = folder.path
                self._image_model.setFolder(self._selected_folder)
                self.selectedFolderChanged.emit()
                self._save_config()
        except Exception:
            self._logger.exception("Error selecting folder")

    @Slot()
    def openFileDialog(self) -> None:
        try:
            initial_dir = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation) or os.path.expanduser("~")
            selected, _ = QFileDialog.getOpenFileName(parent=None, caption="Select file", dir=initial_dir)
            if selected:
                self.selectFile(selected)
        except Exception:
            self._logger.exception("Failed in openFileDialog")

    @Slot(str, result=str)
    def openColorDialog(self, initial: str) -> str:
        """Open color dialog and return selected color hex."""
        try:
            # Parse initial color robustly
            initial_col = color_utils.parse_css_color(initial)
            if not initial_col.isValid() or initial.lower() == "transparent" or initial_col.alpha() == 0:
                if not initial_col.isValid():
                    initial_col = QColor("#ffffff")
                initial_col.setAlpha(255)
            
            # Show alpha channel in the dialog and return hex including alpha
            color = QColorDialog.getColor(initial_col, None, "Select color", QColorDialog.ShowAlphaChannel)
            if color.isValid():
                try:
                    return color.name(QColor.HexArgb)
                except TypeError:
                    # Fallback: construct #AARRGGBB manually if name() signature differs
                    a = color.alpha()
                    return "#{:02x}{:02x}{:02x}{:02x}".format(a, color.red(), color.green(), color.blue())
            return ""
        except Exception:
            self._logger.exception("Error opening color dialog")
            return ""

    @Slot(str)
    def selectFile(self, path: str) -> None:
        try:
            if not path:
                return
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                self._logger.warning("File does not exist: %s", abs_path)
                return
            self._selected_file = "file://" + abs_path
            self.selectedFileChanged.emit()
        except Exception:
            self._logger.exception("Error selecting file")

    @Slot()
    def clearSelectedFile(self) -> None:
        try:
            if self._selected_file:
                self._selected_file = ""
                self._stop_bg_thread(self._tint_thread)
                self._clear_tinted_preview()
                self.selectedFileChanged.emit()
        except Exception:
            self._logger.exception("Error clearing selected file")

    @Slot(str, result=bool)
    def applyTintedImage(self, dest_name: str) -> bool:
        if not dest_name:
            self._show_result_dialog("No destination filename available.")
            return False
        
        src = self._fastfetch_tinted_preview
        if not src:
            self._show_result_dialog("No tinted preview available to apply.")
            return False

        src_path = src.replace("file://", "") if src.startswith("file://") else src

        thr = threading.Thread(
            target=self._apply_tint_task, 
            args=(src_path, dest_name), 
            daemon=True
        )
        thr.start()
        self._apply_thread = thr
        return True

    def _apply_tint_task(self, src: str, dname: str) -> None:
        try:
            dst_path = file_utils.copy_image_to_fastfetch(src, dname)
            ok = file_utils.set_fastfetch_source_inplace(None, dst_path)
            
            if not ok:
                msg = f"Copied to {dst_path} but failed to update config."
                self.fastfetchApplyResult.emit(False, msg)
                self._show_result_dialog(msg)
            else:
                self._on_apply_success(dst_path)

        except FileNotFoundError as exc:
            self._logger.error("applyTintedImage task: %s", exc)
            self.fastfetchApplyResult.emit(False, str(exc))
            self._show_result_dialog(str(exc))
        except Exception:
            self._logger.exception("applyTintedImage task failed")
            self.fastfetchApplyResult.emit(False, "Unexpected error.")
            self._show_result_dialog("Unexpected error while applying tinted image.")

    def _on_apply_success(self, dst_path: Path) -> None:
        # Notify success
        self.fastfetchTintedPreviewChanged.emit()
        
        try:
            file_utils.clear_fastfetch_cache()
        except Exception:
            self._logger.warning("Failed clearing fastfetch cache")

        msg = f"Applied tinted image to {dst_path}"
        self._set_fastfetch_config_image('file://' + str(dst_path))
        self.fastfetchBackupExistsChanged.emit()
        self.fastfetchApplyResult.emit(True, msg)
        self._show_result_dialog(msg)

    def _show_result_dialog(self, text: str) -> None:
        self._set_result_dialog_text(text)
        self._set_result_dialog_visible(True)

    @Slot(str, result=bool)
    def fastfetchDestinationExists(self, dest_name: str) -> bool:
        try:
            if not dest_name:
                return False
            cfg_dir = file_utils.ensure_fastfetch_config_dir()
            dst = cfg_dir / dest_name
            return dst.exists()
        except Exception:
            return False

    @Property("QVariantMap", notify=currentPaletteDataChanged)
    def currentPaletteData(self) -> dict[str, Any]:
        return self._current_palette_data

    @Slot(str, str, "QVariantMap")
    def generatePalette(self, path: str, backend: str, params: dict[str, Any]):
        """Starts background palette generation."""
        if not path:
            self.paletteGenerationError.emit("No image path provided")
            return
            
        logging.info("Starting palette generation for %s with %s", path, backend)
        
        # Increment request ID
        self._latest_palette_request_id += 1
        request_id = self._latest_palette_request_id
        
        worker = PaletteWorker(path, backend, params)
        self._palette_workers.add(worker)
        
        # Connect signals
        worker.dataReady.connect(lambda data: self._on_palette_ready(data, request_id))
        worker.error.connect(self.paletteGenerationError)
        
        # Cleanup when thread finishes (using standard QThread.finished signal)
        # Using lambda allows proper closure over 'worker'
        worker.finished.connect(lambda: self._cleanup_palette_worker(worker))
        
        worker.start()

    def _cleanup_palette_worker(self, worker: PaletteWorker):
        if worker in self._palette_workers:
            self._palette_workers.remove(worker)
        # Schedule for deletion
        worker.deleteLater()

    def _on_palette_ready(self, data: dict[str, Any], request_id: int):
        # Only update if this is the latest request
        if request_id == self._latest_palette_request_id:
            self._current_palette_data = data
            self.currentPaletteDataChanged.emit()
        else:
            logging.debug("Ignoring stale palette result (req %d, latest %d)", request_id, self._latest_palette_request_id)

    @Slot()
    def clearPalette(self) -> None:
        """Clear current palette data and notify QML."""
        self._current_palette_data = {}
        self.currentPaletteDataChanged.emit()

    @Slot(result="QVariantMap")
    def restoreFastfetchBackup(self) -> dict[str, Any]:
        """Restore the fixed fastfetch config backup."""
        try:
            ok = file_utils.restore_fastfetch_config_backup(None)
            if ok:
                try:
                    file_utils.clear_fastfetch_cache()
                except Exception:
                    pass
                
                msg = "Restored fastfetch config from backup"
                self._show_result_dialog(msg)
                
                # Update info
                try:
                    info = self.getFastfetchInfo()
                    if info and info.get("config_image"):
                        self._set_fastfetch_config_image("file://" + str(info.get("config_image")))
                    else:
                        self._set_fastfetch_config_image("")
                except Exception:
                    pass

                self.fastfetchBackupExistsChanged.emit()
                self.fastfetchApplyResult.emit(True, msg)
                return {"success": True, "message": msg}
            else:
                msg = "No backup found to restore"
                self._show_result_dialog(msg)
                self.fastfetchApplyResult.emit(False, msg)
                return {"success": False, "message": msg}
        except Exception:
            self._logger.exception("Failed restoring fastfetch backup")
            return {"success": False, "message": "Unexpected error"}

    @Slot()
    def stopTintWorker(self) -> None:
        """Stop any running tint worker."""
        self._stop_bg_thread(self._tint_thread)
        self._fastfetch_tinting = False
        self.fastfetchTintingChanged.emit()

    def _stop_bg_thread(self, thread: Optional[threading.Thread]) -> None:
        if thread and thread.is_alive():
            # We can't really kill a thread in Python safely.
            # Just let it finish or join with timeout
            try:
                thread.join(timeout=0.2)
            except Exception:
                pass

    @Slot()
    def starshipClearSelection(self) -> None:
        """Clear starship selection state."""
        # Use public Property assignments so QML bindings reliably receive
        # notifications. Also refresh the Starship template model to ensure
        # the UI (ComboBox) reflects the cleared state.
        try:
            self.starshipIsFileMode = False
        except Exception:
            self._set_starship_is_file_mode(False)

        try:
            self.starshipTemplateIndex = -1
        except Exception:
            self._set_starship_template_index(-1)

        # Clear any selected custom file and reset draft color
        self.clearSelectedFile()
        try:
            self.starshipDraftColor = "transparent"
        except Exception:
            self._set_starship_draft_color("transparent")

        # Ensure template model is refreshed from the StarshipModel's template folder
        try:
            if hasattr(self, "_starship_template_model") and hasattr(self, "_starship_model") and getattr(self._starship_model, "_template_folder", None):
                self._starship_template_model.refresh(self._starship_model._template_folder)
            elif hasattr(self, "_starship_template_model"):
                # Fallback: try refreshing with None (model should handle missing path)
                try:
                    self._starship_template_model.refresh()
                except Exception:
                    pass
        except Exception:
            # Best-effort refresh; ignore failures here
            pass

    @Slot()
    def restoreStarshipBackup(self) -> None:
        """Restore the starship config backup."""
        try:
            ok = file_utils.restore_starship_config_backup(None)
            if ok:
                msg = "Restored starship config from backup"
                self._show_result_dialog(msg)
                self.starshipBackupExistsChanged.emit()
                
                # Refresh model
                self._starship_model.refresh()
                # Reload current preview since we changed disk state
                self._starship_model.reloadCurrentConfigPreview()
                
                # Clear selection
                self.starshipClearSelection()
            else:
                msg = "No backup found to restore"
                self._show_result_dialog(msg)
        except Exception:
            self._logger.exception("Failed restoring starship backup")
            self._show_result_dialog("Unexpected error restoring backup")

    @Slot()
    def applyStarshipConfig(self) -> None:
        """Apply the current starship configuration state to ~/.config/starship.toml."""
        from ..utils.file_utils import apply_starship_palettes_atomic
        try:
            # Determine Source
            source_path = ""
            if self._starship_is_file_mode and self._selected_file:
                source_path = self._selected_file.replace("file://", "")
            elif self._starship_template_index >= 0:
                data = self._starship_template_model.get(self._starship_template_index)
                if data and "filePath" in data:
                    source_path = data["filePath"]
            else:
                # Use current config as base if no template selected (just applying palette edits to current)
                source_path = self._starship_model.configPath

            if not source_path or not os.path.exists(source_path):
                self._show_result_dialog("Invalid source configuration.")
                return

            dest_path = Path.home() / ".config" / "starship.toml"
            self._logger.info("Applying starship config (Surgical) Source: %s -> Dest: %s", source_path, dest_path)

            # Decide if we should copy the selected source into the dest.
            # Per spec:
            # - If dest does not exist -> copy source (template/file/current) to initialize
            # - If dest exists and user selected a template/file (not Current Config) -> overwrite dest with source
            # - If dest exists and user selected Current Config -> do NOT overwrite, only apply palette edits
            is_template_selection = bool(self._starship_template_index >= 0 or self._starship_is_file_mode)
            should_copy_to_dest = (not dest_path.exists()) or is_template_selection

            # Create Backup of existing config (do this before any filesystem changes)
            bak_path = dest_path.with_name(dest_path.name + ".bak")
            if dest_path.exists():
                try:
                    shutil.copyfile(dest_path, bak_path)
                    self.starshipBackupExistsChanged.emit()
                except Exception:
                    self._logger.warning("Failed creating starship backup")

            # Ensure destination directory exists (after attempting backup)
            try:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                self._logger.exception("Failed ensuring starship config dir")
                self._show_result_dialog("Failed ensuring config directory")
                return

            # If we should initialize/overwrite dest from the selected source, do it now
            if should_copy_to_dest:
                try:
                    if source_path and os.path.exists(source_path):
                        shutil.copy2(source_path, dest_path)
                    else:
                        # If no valid source, create an empty file so surgical updater has something to work on
                        dest_path.touch()
                except Exception as e:
                    self._logger.error("Failed to initialize config file from source: %s", e)
                    self._show_result_dialog(f"Failed to initialize config file: {e}")
                    return

            # 3. Prepare Data from Model (which holds the current edited state)
            names = self._starship_model._palette_names
            values = self._starship_model._palette_values
            keys = self._starship_model._palette_keys
            
            if not names:
                 self._show_result_dialog("No palette data available to apply.")
                 return

            # 4. Construct Palette Dictionaries
            palettes_to_save = []
            for idx, pname in enumerate(names):
                if idx < len(values) and idx < len(keys):
                    pvals = values[idx]
                    pkeys = keys[idx]
                    
                    palette_dict = {}
                    # Single value check logic preserved from original, though rare for starship palettes
                    if len(pkeys) == 1 and pkeys[0] == "value":
                         # If it's a single value, surgical tool can't handle it as a [block]
                         # Skip or warn? For now, skip to avoid breaking standard palettes
                         continue
                    else:
                         for k, v in zip(pkeys, pvals):
                             palette_dict[k] = v
                    palettes_to_save.append((pname, palette_dict))

            # 5. Apply Updates atomically in a single write to avoid multiple
            # overwrites and duplicated log entries. Move first palette to the end
            # so the original index 0 becomes the active palette.
            if palettes_to_save:
                ordered = palettes_to_save[1:] + [palettes_to_save[0]] if len(palettes_to_save) > 1 else palettes_to_save
                active_name = ordered[-1][0]
            else:
                ordered = []
                active_name = None

            if ordered:
                if not apply_starship_palettes_atomic(str(dest_path), ordered, active_name):
                    self._logger.error("Atomic update failed for starship config")
                    self._show_result_dialog("Failed writing to config file (Atomic Error).")
                    return
            
              # success path continues

            self._show_result_dialog("Starship configuration applied successfully.")
            
            # Refresh to reflect disk state
            self._starship_model.refresh(str(dest_path))
            # Force reload of current preview
            self._starship_model.reloadCurrentConfigPreview()

        except Exception as e:
            self._logger.exception("Failed processing starship config")
            self._show_result_dialog(f"Error applying config: {e}")

    # --- Ulauncher Properties and Slots ---

    # Signals (Must be defined before Properties)
    ulauncherDraftColorChanged = Signal()
    ulauncherIsFileModeChanged = Signal()
    ulauncherTemplateIndexChanged = Signal()
    ulauncherBackupExistsChanged = Signal()
    ulauncherNewThemeNameChanged = Signal()
    ulauncherTemplatesChanged = Signal()

    def _get_ulauncher_templates_generation(self) -> int:
        return getattr(self, "_ulauncher_templates_gen", 0)

    ulauncherTemplatesGeneration = Property(int, _get_ulauncher_templates_generation, notify=ulauncherTemplatesChanged)

    def _increment_ulauncher_templates_gen(self) -> None:
        val = getattr(self, "_ulauncher_templates_gen", 0)
        self._ulauncher_templates_gen = val + 1
        self.ulauncherTemplatesChanged.emit()

    def _get_ulauncher_draft_color(self) -> str:
        # Re-use simple string storage for draft (persisted per session if needed)
        return getattr(self, "_ulauncher_draft_color", "transparent")

    def _set_ulauncher_draft_color(self, val: str) -> None:
        if getattr(self, "_ulauncher_draft_color", "") != val:
            self._ulauncher_draft_color = val
            self.ulauncherDraftColorChanged.emit()

    ulauncherDraftColor = Property(str, _get_ulauncher_draft_color, _set_ulauncher_draft_color, notify=ulauncherDraftColorChanged)

    def _get_ulauncher_is_file_mode(self) -> bool:
        return getattr(self, "_ulauncher_is_file_mode", False)

    def _set_ulauncher_is_file_mode(self, val: bool) -> None:
        if getattr(self, "_ulauncher_is_file_mode", False) != val:
            self._ulauncher_is_file_mode = val
            self.ulauncherIsFileModeChanged.emit()

    ulauncherIsFileMode = Property(bool, _get_ulauncher_is_file_mode, _set_ulauncher_is_file_mode, notify=ulauncherIsFileModeChanged)

    def _get_ulauncher_template_index(self) -> int:
        return getattr(self, "_ulauncher_template_index", -1)

    def _set_ulauncher_template_index(self, val: int) -> None:
        if getattr(self, "_ulauncher_template_index", -1) != val:
            self._ulauncher_template_index = val
            self.ulauncherTemplateIndexChanged.emit()

    ulauncherTemplateIndex = Property(int, _get_ulauncher_template_index, _set_ulauncher_template_index, notify=ulauncherTemplateIndexChanged)

    def _get_ulauncher_new_theme_name(self) -> str:
        return getattr(self, "_ulauncher_new_theme_name", "")

    def _set_ulauncher_new_theme_name(self, val: str) -> None:
        if getattr(self, "_ulauncher_new_theme_name", "") != val:
            self._ulauncher_new_theme_name = val
            self.ulauncherNewThemeNameChanged.emit()

    ulauncherNewThemeName = Property(str, _get_ulauncher_new_theme_name, _set_ulauncher_new_theme_name, notify=ulauncherNewThemeNameChanged)

    @Property(QObject, constant=True)
    def ulauncherModel(self) -> QObject:
        return getattr(self, "_ulauncher_model", None)

    @Property(QObject, constant=True)
    def ulauncherTemplateModel(self) -> QObject:
        return getattr(self, "_ulauncher_template_model", None)
    

    @Property(bool, notify=ulauncherBackupExistsChanged)
    def hasUlauncherBackup(self) -> bool:
        if self._ulauncher_model:
            return self._ulauncher_model.hasBackup
        return False

    @Slot()
    def restoreUlauncherBackup(self) -> None:
        """Restore Ulauncher backups (settings and theme) and notify user."""
        try:
            if self._ulauncher_model:
                self._ulauncher_model.restore()
                self._show_result_dialog("Restored Ulauncher settings and theme from backups.")
                self.ulauncherBackupExistsChanged.emit()
                # Clear any transient selection state
                self.ulauncherClearSelection()
        except Exception:
            self._logger.exception("Failed restoring Ulauncher backup")
            self._show_result_dialog("Error restoring Ulauncher backup.")

    @Slot()
    def ulauncherClearSelection(self) -> None:
        self.ulauncherIsFileMode = False
        self.ulauncherTemplateIndex = -1
        self.clearSelectedFile()
        self.ulauncherDraftColor = "transparent"
        # Refresh from current config
        if hasattr(self, "_ulauncher_model"):
            self._ulauncher_model.refresh()
            
    @Slot()
    def ulauncherCreateNewTheme(self) -> None:
        """Create a new theme from the current selection (template or existing theme)."""
        try:
            name = self.ulauncherNewThemeName.strip()
            if not name:
                self._show_result_dialog("Please provide a name for the new theme.")
                return

            # Determine Source
            source_path = ""
            if self.ulauncherTemplateIndex >= 0:
                info = self._ulauncher_template_model.get(self.ulauncherTemplateIndex)
                source_path = info.get("filePath", "")
            
            if not source_path:
                 # Fallback to current config path if valid
                 source_path = self._ulauncher_model.configPath
            
            if not source_path:
                self._show_result_dialog("No source theme selected.")
                return

            new_path = self._ulauncher_model.createNewTheme(source_path, name)
            if new_path:
                self._show_result_dialog(f"Theme '{name}' created successfully.")
                self.ulauncherNewThemeName = ""
                
                # Refresh templates list to show new theme
                self._ulauncher_template_model.refresh(self._ulauncher_model.templateFolder)
                self._increment_ulauncher_templates_gen()
                
                # Select the new theme
                self._ulauncher_model.refresh(new_path)
                
                # Find index in template model
                tm = self._ulauncher_template_model
                for i in range(tm.rowCount()):
                    if tm.get(i)["filePath"] == new_path:
                        self.ulauncherTemplateIndex = i
                        break
            else:
                self._show_result_dialog("Failed to create theme. Check logs for details.")
        except Exception as e:
            self._logger.exception("ulauncherCreateNewTheme failed")
            self._show_result_dialog(f"Error creating theme: {e}")

    @Slot()
    def ulauncherSaveTheme(self) -> None:
        """Save changes to the currently selected USER theme."""
        try:
            # Prevent saving if it's a template
            if self.ulauncherTemplateIndex >= 0:
                info = self._ulauncher_template_model.get(self.ulauncherTemplateIndex)
                if info.get("isTemplate", False):
                    self._show_result_dialog("Cannot save changes to a template directly.\nPlease create a new theme.")
                    return

            err = self._ulauncher_model.saveTheme()
            if err:
                self._show_result_dialog(f"Failed to save theme:\n{err}")
            else:
                self._show_result_dialog("Theme saved successfully.")
                self._ulauncher_model.refresh(self._ulauncher_model.configPath) # Reload to clear modified state, keeping selection
        except Exception as e:
             self._logger.exception("ulauncherSaveTheme failed")
             self._show_result_dialog(f"Error saving theme: {e}")

    @Slot()
    def ulauncherDeleteTheme(self) -> None:
        """Delete the currently selected theme."""
        try:
             path = self._ulauncher_model.configPath
             if not path:
                 return
             
             # Double check via model's logic
             if self._ulauncher_model.deleteTheme(path):
                 self._show_result_dialog("Theme deleted successfully.")
                 self._ulauncher_template_model.refresh(self._ulauncher_model.templateFolder)
                 self._increment_ulauncher_templates_gen()
                 # Reset selection to actual current
                 self.ulauncherClearSelection()
             else:
                 self._show_result_dialog("Failed to delete theme.\n(Cannot delete active theme or templates).")
        except Exception as e:
            self._logger.exception("ulauncherDeleteTheme failed")
            self._show_result_dialog(f"Error deleting theme: {e}")

    @Slot()
    def ulauncherApplyTheme(self) -> None:
        """Apply the currently selected theme to system config."""
        try:
            err = self._ulauncher_model.apply()
            if err:
                 self._show_result_dialog(f"Failed to apply theme:\n{err}")
            else:
                 self._show_result_dialog("Theme applied to Ulauncher configuration.")
                 self._ulauncher_model.refresh() 
        except Exception as e:
            self._logger.exception("ulauncherApplyTheme failed")
            self._show_result_dialog(f"Error applying theme: {e}")

    @Slot()
    def applyUlauncherConfig(self) -> None:
        self.ulauncherApplyTheme()

    def _deprecated_applyUlauncherConfig(self) -> None:
        """Apply Ulauncher configuration.
        
        If a template is selected:
        1. Copy template to user-themes with NEW name.
        2. update manifest.json metadata with NEW name.
        3. updates settings.json to use that theme.
        4. Saves current palette modifications to the new theme files.
        
        If an existing theme is selected:
        1. Just saves palette modifications (performed by model.apply()).
        """
        try:
            import json
            
            # 1. Determine Intent
            is_template_entry = False
            source_info = {}
            if self.ulauncherTemplateIndex >= 0:
                source_info = self._ulauncher_template_model.get(self.ulauncherTemplateIndex)
                is_template_entry = source_info.get("isTemplate", False)
            
            target_theme_path = ""
            theme_name = ""
            
            if is_template_entry:
                # NEW THEME FROM TEMPLATE FLOW
                theme_name = self.ulauncherNewThemeName.strip()
                if not theme_name:
                    self._show_result_dialog("Please provide a name for the new theme.")
                    return
                
                # Validation: Ensure all mandatory colors (placeholders) are set
                if not self._ulauncher_model.allColorsFilled:
                    self._show_result_dialog("Please fill all mandatory colors before creating the theme.\n(Empty color boxes must be assigned a value).")
                    return
                
                source_path = source_info.get("filePath")
                if not source_path or not os.path.exists(source_path):
                    self._show_result_dialog("Invalid template source path.")
                    return

                # Determine Destination
                dest_root = Path.home() / ".config" / "ulauncher" / "user-themes"
                dest_root.mkdir(parents=True, exist_ok=True)
                target_theme_path = str(dest_root / theme_name)
                
                # Copy Template
                if os.path.exists(target_theme_path):
                    # We could auto-increment or warn. User spec says "skip backup" for new,
                    # but if it exists, let's just overwrite for now.
                    try:
                        shutil.rmtree(target_theme_path)
                    except Exception:
                        pass
                
                try:
                    shutil.copytree(source_path, target_theme_path)
                except Exception as e:
                    self._show_result_dialog(f"Failed creating theme directory: {e}")
                    return

                # Update manifest.json metadata (name and display_name)
                manifest_path = Path(target_theme_path) / "manifest.json"
                if manifest_path.exists():
                    try:
                        with manifest_path.open("r", encoding="utf-8") as f:
                            import json5 # using json5 for manifests as they often have comments
                            mdata = json5.load(f)
                        mdata["name"] = theme_name
                        mdata["display_name"] = theme_name
                        with manifest_path.open("w", encoding="utf-8") as f:
                            json.dump(mdata, f, indent=4, ensure_ascii=False)
                    except Exception as e:
                        self._logger.warning("Failed updating manifest metadata: %s", e)

                # Update settings.json (No backup for NEW theme creation per spec)
                settings_path = Path.home() / ".config" / "ulauncher" / "settings.json"
                settings_data = {}
                if settings_path.exists():
                     try:
                         with settings_path.open("r", encoding="utf-8") as f:
                             settings_data = json.load(f)
                     except Exception:
                         pass
                
                settings_data["theme_name"] = theme_name
                try:
                    with settings_path.open("w", encoding="utf-8") as f:
                        json.dump(settings_data, f, indent=4)
                except Exception as e:
                    self._show_result_dialog(f"Failed updating settings.json: {e}")
                    return
                
                # Update model's config path to point to the new location so apply() works on it
                # We also need to refresh the template model so it shows the new theme in the list
                self._ulauncher_model._set_config_path(target_theme_path)

            else:
                # EDITING EXISTING THEME FLOW
                if self.ulauncherTemplateIndex >= 0:
                    # Chose an existing theme from user-themes or system themes
                    theme_name = source_info.get("fileName")
                    target_theme_path = source_info.get("filePath")
                    
                    # If it's a system theme, we should probably copy it to user-themes first 
                    # before editing, but for now let's follow plan: "apply directly with backup"
                    # Wait, if it's system theme, we CANT apply directly.
                    if target_theme_path.startswith("/usr/share"):
                        self._show_result_dialog("System themes cannot be edited directly. Please use them as templates.")
                        return
                    
                    # Update settings.json to ensure it matches selection
                    settings_path = Path.home() / ".config" / "ulauncher" / "settings.json"
                    settings_data = {}
                    if settings_path.exists():
                        try:
                            with settings_path.open("r", encoding="utf-8") as f:
                                settings_data = json.load(f)
                        except Exception:
                            pass
                    
                    if settings_data.get("theme_name") != theme_name:
                        settings_data["theme_name"] = theme_name
                        try:
                            with settings_path.open("w", encoding="utf-8") as f:
                                json.dump(settings_data, f, indent=4)
                        except Exception:
                            pass
                    
                    self._ulauncher_model._set_config_path(target_theme_path)
                else:
                    # Current config (already loaded in model)
                    if not self._ulauncher_model.configPath:
                         self._show_result_dialog("No active theme found to edit.")
                         return

            # 2. Apply Palette Changes (Handles theme.css / manifest.json with backups if not template)
            # Apply if colors were modified OR if we are creating a new theme from a template
            if self._ulauncher_model.isModified or is_template_entry:
                success = self._ulauncher_model.apply(skip_backup=is_template_entry)
            else:
                self._logger.info("No color changes detected for Ulauncher, skipping theme file writes.")
                success = True # Settings update was already done above
            
            if success:
                self._show_result_dialog("Ulauncher configuration applied.")
                # Refresh everything
                self._ulauncher_model.refresh()
                self._ulauncher_template_model.refresh()
                # Clear new theme name after success
                self.ulauncherNewThemeName = ""
            else:
                self._show_result_dialog("Failed applying palette changes.")

        except Exception as e:
            self._logger.exception("Failed applying Ulauncher config")
            self._show_result_dialog(f"Error: {e}")

    # --- SVG Recolor Properties ---

    def _get_svg_directory(self) -> str:
        return self._svg_directory

    def _set_svg_directory(self, val: str) -> None:
        if self._svg_directory != val:
            self._svg_directory = val
            self.svgDirectoryChanged.emit()

    svgDirectory = Property(str, _get_svg_directory, _set_svg_directory, notify=svgDirectoryChanged)

    def _get_svg_gradient_colors(self) -> list[str]:
        return list(self._svg_gradient_colors)

    svgGradientColors = Property("QVariantList", _get_svg_gradient_colors, notify=svgGradientColorsChanged)

    def _get_svg_color_count(self) -> int:
        return self._svg_color_count

    def _set_svg_color_count(self, val: int) -> None:
        clamped = max(2, min(6, int(val)))
        if self._svg_color_count != clamped:
            self._svg_color_count = clamped
            self.svgColorCountChanged.emit()

    svgColorCount = Property(int, _get_svg_color_count, _set_svg_color_count, notify=svgColorCountChanged)

    def _get_svg_mono_color(self) -> str:
        return self._svg_mono_color

    def _set_svg_mono_color(self, val: str) -> None:
        if self._svg_mono_color != val:
            self._svg_mono_color = val
            self.svgMonoColorChanged.emit()

    svgMonoColor = Property(str, _get_svg_mono_color, _set_svg_mono_color, notify=svgMonoColorChanged)

    def _get_svg_processing(self) -> bool:
        return self._svg_processing

    svgProcessing = Property(bool, _get_svg_processing, notify=svgProcessingChanged)

    def _get_svg_log_text(self) -> str:
        return self._svg_log

    svgLogText = Property(str, _get_svg_log_text, notify=svgLogTextChanged)

    def _get_svg_preview_index(self) -> int:
        return self._svg_preview_index

    svgPreviewIndex = Property(int, _get_svg_preview_index, notify=svgPreviewIndexChanged)

    def _get_svg_current_preview_file(self) -> str:
        if 0 <= self._svg_preview_index < len(self._svg_preview_files):
            return self._svg_preview_files[self._svg_preview_index]
        return ""

    svgCurrentPreviewFile = Property(str, _get_svg_current_preview_file, notify=svgCurrentPreviewFileChanged)

    def _get_svg_preview_count(self) -> int:
        return len(self._svg_preview_files)

    svgPreviewCount = Property(int, _get_svg_preview_count, notify=svgPreviewFilesChanged)

    def _get_svg_preview_timestamp(self) -> int:
        return self._svg_preview_timestamp

    svgPreviewTimestamp = Property(int, _get_svg_preview_timestamp, notify=svgPreviewTimestampChanged)

    def _get_svg_has_preview(self) -> bool:
        return bool(self._svg_preview_dir) and os.path.isdir(self._svg_preview_dir)

    svgHasPreview = Property(bool, _get_svg_has_preview, notify=svgHasPreviewChanged)

    def _get_svg_has_backup(self) -> bool:
        return bool(self._svg_backup_dir) and os.path.isdir(self._svg_backup_dir)

    svgHasBackup = Property(bool, _get_svg_has_backup, notify=svgHasBackupChanged)

    # --- SVG Recolor Slots ---

    @Slot()
    def svgBrowseDirectory(self) -> None:
        try:
            initial = self._svg_directory or str(Path.home())
            selected = QFileDialog.getExistingDirectory(None, "Select SVG folder", initial)
            if selected:
                self._set_svg_directory(selected)
        except Exception:
            self._logger.exception("svgBrowseDirectory failed")

    @Slot(int, str)
    def svgSetGradientColor(self, index: int, color_hex: str) -> None:
        try:
            if 0 <= index < len(self._svg_gradient_colors):
                self._svg_gradient_colors[index] = color_hex
                self.svgGradientColorsChanged.emit()
        except Exception:
            self._logger.exception("svgSetGradientColor failed")

    @Slot(str)
    def svgSetMonoColor(self, color_hex: str) -> None:
        self._set_svg_mono_color(color_hex)

    @Slot(int)
    def svgSetColorCount(self, count: int) -> None:
        self._set_svg_color_count(count)

    @Slot()
    def svgStartProcessing(self) -> None:
        try:
            if not self._svg_directory or not os.path.isdir(self._svg_directory):
                self.notification.emit("Please select a valid directory first.", "error")
                return

            if self._svg_processing:
                return

            preview_dir = str(get_svg_preview_cache_dir())

            # Rebuild preview directory from scratch
            if os.path.exists(preview_dir):
                shutil.rmtree(preview_dir)
            os.makedirs(preview_dir, exist_ok=True)

            original_files: dict[str, str] = {}

            for root_str, _dirs, files in os.walk(self._svg_directory):
                if root_str == preview_dir or root_str.startswith(preview_dir + os.sep):
                    continue
                for fname in files:
                    if not fname.lower().endswith(".svg"):
                        continue
                    src = os.path.join(root_str, fname)
                    rel = os.path.relpath(src, self._svg_directory)
                    dst = os.path.join(preview_dir, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    original_files[dst] = src

            if not original_files:
                shutil.rmtree(preview_dir, ignore_errors=True)
                self.notification.emit("No SVG files found in the selected directory.", "error")
                return

            self._svg_preview_dir = preview_dir
            self._svg_original_files = original_files
            self._svg_log = ""
            self.svgLogTextChanged.emit()
            self.svgHasPreviewChanged.emit()

            active_colors = self._svg_gradient_colors[: self._svg_color_count]
            worker = SvgWorker(preview_dir, active_colors, self._svg_mono_color)
            self._svg_worker = worker

            worker.logMessage.connect(self._svg_on_log)
            worker.progressChanged.connect(self._svg_on_progress)
            worker.finished.connect(self._svg_on_finished)
            worker.stopped.connect(self._svg_on_stopped)

            self._svg_processing = True
            self.svgProcessingChanged.emit()

            separator = "=" * 60
            lines = [
                separator,
                "SVG RECOLOR — KWAL",
                separator,
                f"📁 Source: {self._svg_directory}",
                f"📁 Preview: {preview_dir}",
                f"🎨 Colors ({self._svg_color_count}): {' → '.join(active_colors)}",
                f"🎨 System icons: {self._svg_mono_color}",
                separator,
            ]
            self._svg_log = "\n".join(lines)
            self.svgLogTextChanged.emit()

            worker.start()
        except Exception:
            self._logger.exception("svgStartProcessing failed")
            self._svg_processing = False
            self.svgProcessingChanged.emit()
            self.notification.emit("Failed to start SVG processing.", "error")

    @Slot()
    def svgStopProcessing(self) -> None:
        try:
            if self._svg_worker and self._svg_worker.isRunning():
                self._svg_worker.stop()
                self._svg_worker.wait()
        except Exception:
            self._logger.exception("svgStopProcessing failed")

    @Slot()
    def svgApplyChanges(self) -> None:
        try:
            if not self._svg_preview_dir or not os.path.isdir(self._svg_preview_dir):
                self.notification.emit("No preview directory available.", "error")
                return

            import time as _time
            import datetime as _datetime
            timestamp_str = _datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(self._svg_directory, f"backup_{timestamp_str}")
            os.makedirs(backup_dir, exist_ok=True)

            applied = 0
            for preview_path, original_path in self._svg_original_files.items():
                if not os.path.exists(preview_path) or not os.path.exists(original_path):
                    continue
                rel = os.path.relpath(original_path, self._svg_directory)
                backup_path = os.path.join(backup_dir, rel)
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                shutil.copy2(original_path, backup_path)
                shutil.copy2(preview_path, original_path)
                applied += 1

            shutil.rmtree(self._svg_preview_dir, ignore_errors=True)
            self._svg_preview_dir = ""
            self._svg_preview_files = []
            self._svg_preview_index = 0
            self._svg_original_files = {}
            self._svg_backup_dir = backup_dir

            self.svgPreviewFilesChanged.emit()
            self.svgPreviewIndexChanged.emit()
            self.svgCurrentPreviewFileChanged.emit()
            self.svgHasPreviewChanged.emit()
            self.svgHasBackupChanged.emit()

            msg = f"Applied {applied} files. Backup saved to backup_{timestamp_str}/"
            self._svg_append_log(f"\n✅ {msg}")
            self._show_result_dialog(msg)
        except Exception:
            self._logger.exception("svgApplyChanges failed")
            self.notification.emit("Failed to apply SVG changes.", "error")

    @Slot()
    def svgUndoChanges(self) -> None:
        try:
            if not self._svg_backup_dir or not os.path.isdir(self._svg_backup_dir):
                self.notification.emit("No backup directory available.", "error")
                return

            restored = 0
            for root_str, _dirs, files in os.walk(self._svg_backup_dir):
                for fname in files:
                    if not fname.lower().endswith(".svg"):
                        continue
                    backup_path = os.path.join(root_str, fname)
                    rel = os.path.relpath(backup_path, self._svg_backup_dir)
                    original_path = os.path.join(self._svg_directory, rel)
                    if os.path.exists(original_path):
                        shutil.copy2(backup_path, original_path)
                        restored += 1

            shutil.rmtree(self._svg_backup_dir, ignore_errors=True)
            self._svg_backup_dir = ""
            self.svgHasBackupChanged.emit()

            msg = f"Restored {restored} files from backup."
            self._svg_append_log(f"\n↩️ {msg}")
            self._show_result_dialog(msg)
        except Exception:
            self._logger.exception("svgUndoChanges failed")
            self.notification.emit("Failed to undo SVG changes.", "error")

    @Slot(int)
    def svgNavigatePreview(self, direction: int) -> None:
        new_index = self._svg_preview_index + int(direction)
        count = len(self._svg_preview_files)
        if count == 0:
            return
        new_index = max(0, min(count - 1, new_index))
        if new_index != self._svg_preview_index:
            self._svg_preview_index = new_index
            self._svg_preview_timestamp += 1
            self.svgPreviewIndexChanged.emit()
            self.svgCurrentPreviewFileChanged.emit()
            self.svgPreviewTimestampChanged.emit()

    def _svg_append_log(self, text: str) -> None:
        self._svg_log += text
        self.svgLogTextChanged.emit()

    @Slot(str)
    def _svg_on_log(self, message: str) -> None:
        self._svg_append_log("\n" + message if self._svg_log else message)

    @Slot(bool)
    def _svg_on_progress(self, active: bool) -> None:
        self._svg_processing = active
        self.svgProcessingChanged.emit()

    @Slot(int, int)
    def _svg_on_finished(self, total: int, success: int) -> None:
        self._svg_processing = False
        self.svgProcessingChanged.emit()
        rate = (success / total * 100) if total > 0 else 0.0
        separator = "=" * 60
        summary = (
            f"\n{separator}\n"
            f"✅ Done: {success}/{total} files recolored ({rate:.1f}%).\n"
            f"📁 Preview folder ready. Use ◀ ▶ to inspect, then Apply.\n"
            f"{separator}"
        )
        self._svg_append_log(summary)
        self._svg_load_preview_files()

    @Slot()
    def _svg_on_stopped(self) -> None:
        self._svg_processing = False
        self.svgProcessingChanged.emit()
        self._svg_append_log("\n🛑 Processing stopped by user.")
        self._svg_load_preview_files()

    def _svg_load_preview_files(self) -> None:
        files: list[str] = []
        if self._svg_preview_dir and os.path.isdir(self._svg_preview_dir):
            for root_str, _dirs, fnames in os.walk(self._svg_preview_dir):
                for fname in sorted(fnames):
                    if fname.lower().endswith(".svg"):
                        files.append(os.path.join(root_str, fname))
        files.sort()
        self._svg_preview_files = files
        self._svg_preview_index = 0
        self._svg_preview_timestamp += 1
        self.svgPreviewFilesChanged.emit()
        self.svgPreviewIndexChanged.emit()
        self.svgCurrentPreviewFileChanged.emit()
        self.svgPreviewTimestampChanged.emit()
        self.svgHasPreviewChanged.emit()

    def stopSvgWorker(self) -> None:
        """Stop SVG worker on application quit."""
        if self._svg_worker and self._svg_worker.isRunning():
            try:
                self._svg_worker.stop()
                self._svg_worker.wait(2000)
            except Exception:
                self._logger.exception("Error stopping SVG worker during shutdown")
