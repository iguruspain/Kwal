from __future__ import annotations

import json
import logging
import os
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
)
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QColorDialog, QFileDialog

from ..models.models import (
    FastfetchTemplateModel,
    Folder,
    ImageModel,
    SettingsApp,
    SettingsAppModel,
    WallpaperFolderModel,
)
from ..utils import color_utils, file_utils


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
    # Signal for compositing
    compositingEnabledChanged = Signal()

    tintResult = Signal(str)
    fastfetchApplyResult = Signal(bool, str)
    
    # Global notification signal (message, type["error"|"success"|"info"])
    notification = Signal(str, str)

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
        
        # Draft State (Persist across tabs)
        self._fastfetch_draft_color: str = "transparent"
        self._fastfetch_is_file_mode: bool = False
        self._fastfetch_template_index: int = -1
        
        # Compositing state (True by default for modern desktops)
        self._compositing_enabled: bool = True

        # Thread References
        self._tint_thread: Optional[threading.Thread] = None
        self._apply_thread: Optional[threading.Thread] = None
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
        apps = [
            SettingsApp(app_name="wallpapers", section="Apps", qml_page="apps/wallpapers.qml"), # experimental
            SettingsApp(app_name="fastfetch", section="Apps", qml_page="apps/fastfetch.qml"),
            SettingsApp(app_name="starship", section="Apps", qml_page="apps/starship.qml"),
            SettingsApp(app_name="ulauncher", section="Apps", qml_page="apps/ulauncher.qml"),
        ]
        self._settings_app_model = SettingsAppModel(apps)

        # Connect Signals
        self.tintResult.connect(self._on_tint_done)

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

    def _get_home_path(self) -> str:
        return self._home_path

    homePath = Property(str, _get_home_path, constant=True)

    def _get_selected_wallpaper(self) -> str:
        return self._selected_wallpaper

    selectedWallpaper = Property(str, _get_selected_wallpaper, notify=selectedWallpaperChanged)

    def _get_selected_wallpaper_resolution(self) -> str:
        return self._selected_wallpaper_resolution

    selectedWallpaperResolution = Property(str, _get_selected_wallpaper_resolution, notify=selectedWallpaperChanged)

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
    def formatColorWithAlpha(self, color: str) -> str:
        """Return a display string with RGB hex and alpha decimal for QML tooltips.

        Examples:
        - input: "#AARRGGBB" -> returns: "#RRGGBB alpha: 204"
        - input: "#RRGGBB" or named color -> preserves and computes alpha
        """
        try:
            if not color or str(color).lower() == "transparent":
                return ""

            s = str(color)
            # If already in #AARRGGBB
            if s.startswith("#") and len(s) == 9:
                aa = s[1:3]
                rr = s[3:5]
                gg = s[5:7]
                bb = s[7:9]
                alpha_dec = int(aa, 16)
                return f"#{rr}{gg}{bb} alpha: {alpha_dec}"

            # Try to resolve via QColor to ensure we include alpha
            if QColor.isValidColor(s):
                qc = QColor(s)
                try:
                    hexargb = qc.name(QColor.HexArgb)
                except TypeError:
                    hexargb = "#{:02x}{:02x}{:02x}{:02x}".format(qc.alpha(), qc.red(), qc.green(), qc.blue())

                if hexargb.startswith("#") and len(hexargb) == 9:
                    aa = hexargb[1:3]
                    rr = hexargb[3:5]
                    gg = hexargb[5:7]
                    bb = hexargb[7:9]
                    alpha_dec = int(aa, 16)
                    return f"#{rr}{gg}{bb} alpha: {alpha_dec}"

            # Fallback: return original string
            return s
        except Exception:
            self._logger.exception("Error formatting color tooltip for %r", color)
            return str(color or "")

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
                    img = QImage(path)
                    if not img.isNull():
                        self._selected_wallpaper_resolution = f"{img.width()}x{img.height()}"
                    else:
                        self._selected_wallpaper_resolution = ""
                else:
                    self._selected_wallpaper_resolution = ""
                    
                self.selectedWallpaperChanged.emit()
        except Exception:
            self._logger.exception("Error selecting wallpaper %r", path)

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

    @Slot(result=str)
    def getCurrentSystemWallpaper(self) -> str:
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
            # If no valid initial color is provided, start with opaque white.
            # If an initial color (including an alpha channel) is provided, preserve its alpha.
            if not initial or not QColor.isValidColor(initial) or str(initial).lower() == "transparent":
                initial_col = QColor("#ffffff")
                try:
                    initial_col.setAlpha(255)
                except Exception:
                    pass
            else:
                initial_col = QColor(initial)
            
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
