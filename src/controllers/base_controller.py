"""Base controller mixin: shared state, config, palette, and cross-feature helpers."""

from __future__ import annotations

import json
import logging
import shutil
import threading
from pathlib import Path
from typing import Optional, Any
from PySide6.QtCore import QCoreApplication, QObject, Property, Signal, Slot
from PySide6.QtGui import QColor
from ..models.models import ImageModel, SettingsApp, SettingsAppModel
from ..utils import color_utils
from ..utils.palette_worker import PaletteWorker
from ..utils.xdg_paths import kwal_config_dir

class BaseMixin:
    templatesInstalledChanged = Signal()

    resultDialogVisibleChanged = Signal()

    resultDialogTextChanged = Signal()

    currentPaletteDataChanged = Signal()

    paletteGenerationError = Signal(str)

    compositingEnabledChanged = Signal()

    simulateAllAppsChanged = Signal()

    showExtensionBadgeChanged = Signal()

    customCommandsChanged = Signal()

    notification = Signal(str, str)

    def _get_config_path_file(self) -> Path:
        cfg_dir = kwal_config_dir()
        cfg_dir.mkdir(parents=True, exist_ok=True)
        return cfg_dir / "folders.json"

    @staticmethod
    def _normalize_custom_commands(raw: list) -> list[dict[str, Any]]:
        """Normalize custom commands to {"command": str, "enabled": bool}.

        Accepts the legacy format (plain list of command strings, all
        implicitly enabled) as well as the current dict format, so existing
        config files keep working after upgrading.
        """
        normalized: list[dict[str, Any]] = []
        for item in raw:
            if isinstance(item, str):
                normalized.append({"command": item, "enabled": True})
            elif isinstance(item, dict):
                normalized.append({
                    "command": str(item.get("command", "")),
                    "enabled": bool(item.get("enabled", True)),
                })
        return normalized

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
            "selected_folder": self._selected_folder,
            "custom_commands": self._custom_commands
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

    @Property(QObject, constant=True)
    def settingsAppModel(self) -> SettingsAppModel:
        return self._settings_app_model

    def imageModel(self) -> ImageModel:
        return self._image_model

    def _get_home_path(self) -> str:
        return self._home_path

    homePath = Property(str, _get_home_path, constant=True)

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

    def _get_custom_commands(self) -> list[dict[str, Any]]:
            return self._custom_commands

    def _set_custom_commands(self, cmds: list) -> None:
        normalized = self._normalize_custom_commands(cmds)
        if self._custom_commands != normalized:
            self._custom_commands = normalized
            self._save_config()
            self.customCommandsChanged.emit()

    customCommands = Property("QVariantList", _get_custom_commands, _set_custom_commands, notify=customCommandsChanged)

    @Slot(str)
    def addCustomCommand(self, cmd: str) -> None:
        """Añade un comando nuevo al final de la lista (activado por defecto)."""
        self._custom_commands.append({"command": cmd, "enabled": True})
        self._save_config()
        self.customCommandsChanged.emit()

    @Slot(int, str)
    def updateCustomCommand(self, index: int, cmd: str) -> None:
        """Actualiza el texto del comando en un índice específico, preservando su estado enabled."""
        if 0 <= index < len(self._custom_commands):
            self._custom_commands[index]["command"] = cmd
            self._save_config()
            self.customCommandsChanged.emit()

    @Slot(int, bool)
    def setCustomCommandEnabled(self, index: int, enabled: bool) -> None:
        """Activa/desactiva un comando sin tocar su texto."""
        if 0 <= index < len(self._custom_commands):
            self._custom_commands[index]["enabled"] = enabled
            self._save_config()
            self.customCommandsChanged.emit()

    @Slot(int, int)
    def moveCustomCommand(self, from_index: int, to_index: int) -> None:
        """Mueve un comando dentro de la lista.

        La posición dentro de la lista determina su prioridad de ejecución.
        """
        if not (0 <= from_index < len(self._custom_commands)):
            return

        if not (0 <= to_index < len(self._custom_commands)):
            return

        if from_index == to_index:
            return

        command = self._custom_commands.pop(from_index)
        self._custom_commands.insert(to_index, command)

        self._save_config()
        self.customCommandsChanged.emit()

    @Slot(int)
    def removeCustomCommand(self, index: int) -> None:
        """Elimina el comando de la lista según su posición."""
        if 0 <= index < len(self._custom_commands):
            self._custom_commands.pop(index)
            self._save_config()
            self.customCommandsChanged.emit()

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
        return apps

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

    @Slot(result=bool)
    def templatesInstalled(self) -> bool:
        return self._templates_installed

    @Slot(result=bool)
    def _check_templates_installed(self) -> bool:
        cfg_dir = kwal_config_dir() / "templates"
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

    def _show_result_dialog(self, text: str) -> None:
        self._set_result_dialog_text(text)
        self._set_result_dialog_visible(True)

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

    @Slot(result="QVariantList")
    def getColorCategoryList(self) -> list[str]:
        """Return the fixed list of color categories used for classification."""
        from ..utils import color_extractor
        return color_extractor.list_categories()

    @Slot(str, result="QVariantList")
    def getWallpaperCategories(self, path: str) -> list[str]:
        """Return the categories currently stored for a single wallpaper path."""
        try:
            from ..utils import color_extractor
            return color_extractor.get_categories_for_path(path)
        except Exception:
            self._logger.exception("Failed reading categories for %s", path)
            return []

    @Slot(result="QVariantList")
    def getCachedColorEntries(self) -> list[dict[str, Any]]:
        """Return every cached wallpaper's colors/categories for the editor panel."""
        try:
            from ..utils import color_extractor, video_utils
            entries = color_extractor.list_cache_entries()
            for e in entries:
                e["isVideo"] = video_utils.is_video_file(e["path"])
            return entries
        except Exception:
            self._logger.exception("Failed loading cached color entries")
            return []

    @Slot(str, "QVariantList", result=bool)
    def updateWallpaperCategories(self, path: str, categories: list) -> bool:
        """Persist a manual correction of an image's color categories."""
        try:
            from ..utils import color_extractor
            clean = [str(c) for c in categories]
            ok = color_extractor.update_entry_categories(path, clean)
            if ok:
                # Keep the live ImageModel color cache (used by the filter chips) in sync
                self._image_model.updateCachedCategories(path, clean)
            return ok
        except Exception:
            self._logger.exception("Failed updating categories for %s", path)
            return False

    def _stop_bg_thread(self, thread: Optional[threading.Thread]) -> None:
        if thread and thread.is_alive():
            # We can't really kill a thread in Python safely.
            # Just let it finish or join with timeout
            try:
                thread.join(timeout=0.2)
            except Exception:
                pass
