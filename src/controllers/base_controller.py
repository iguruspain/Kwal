"""Base controller mixin: shared state, config, palette, and cross-feature helpers."""

from __future__ import annotations

import json
import logging
import re
import shutil
import threading
from pathlib import Path
from typing import Any, Optional, cast

import tomlkit

from PySide6.QtCore import Property, QCoreApplication, QObject, Signal, Slot
from PySide6.QtGui import QColor

from ..models.common import SettingsApp
from ..models.settings_models import SettingsAppModel
from ..models.wallpaper_models import ImageModel
from ..utils import color_utils, video_utils
from ..utils.palette_worker import PaletteWorker
from ..utils.xdg_paths import kwal_config_dir
from .commands_controller import normalize_custom_commands


class BaseMixin:
    templatesInstalledChanged = Signal()

    resultDialogVisibleChanged = Signal()

    resultDialogTextChanged = Signal()

    currentPaletteDataChanged = Signal()

    paletteGenerationError = Signal(str)

    compositingEnabledChanged = Signal()

    simulateAllAppsChanged = Signal()

    showExtensionBadgeChanged = Signal()

    notification = Signal(str, str)

    def _get_config_path_file(self) -> Path:
        cfg_dir = kwal_config_dir()
        cfg_dir.mkdir(parents=True, exist_ok=True)
        return cfg_dir / "config.toml"

    @staticmethod
    def _strip_jsonc_comments(text: str) -> str:
        """Remove // line comments and /* block comments */ from a JSONC string."""
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        text = re.sub(r"//[^\n]*", "", text)
        return text

    def _migrate_legacy_config(self) -> None:
        """Silently migrate older config formats to config.toml.

        Migration chain (oldest first):
          folders.json  →  config.jsonc  →  config.toml
        """
        toml_path = self._config_path_file

        # Step 1: folders.json → config.jsonc  (already done in a previous release)
        jsonc_path = toml_path.parent / "config.jsonc"
        old_json   = toml_path.parent / "folders.json"
        if old_json.exists() and not jsonc_path.exists() and not toml_path.exists():
            try:
                old_json.rename(jsonc_path)
                self._logger.info("Migrated folders.json → config.jsonc")
            except Exception:
                self._logger.exception("Could not rename folders.json → config.jsonc")

        # Step 2: config.jsonc → config.toml
        if jsonc_path.exists() and not toml_path.exists():
            try:
                raw  = jsonc_path.read_text(encoding="utf-8")
                data = json.loads(self._strip_jsonc_comments(raw))

                doc = tomlkit.document()
                doc.add(tomlkit.comment("Kwal configuration — comments are preserved on save"))
                doc.add(tomlkit.comment("Do not edit while Kwal is running."))
                doc.add(tomlkit.nl())
                doc["selected_folder"]  = data.get("selected_folder", "")
                doc["last_set_wallpaper"] = data.get("last_set_wallpaper", "")

                for f in data.get("folders", []):
                    tbl = tomlkit.table()
                    tbl["name"] = f.get("name", "")
                    tbl["path"] = f.get("path", "")
                    doc.append("folders", tbl)

                for cmd in data.get("custom_commands", []):
                    tbl = tomlkit.table()
                    tbl["command"] = cmd.get("command", "")
                    tbl["enabled"] = bool(cmd.get("enabled", True))
                    doc.append("custom_commands", tbl)

                toml_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
                jsonc_path.unlink()
                self._logger.info("Migrated config.jsonc → config.toml")
            except Exception:
                self._logger.exception("Could not migrate config.jsonc → config.toml")

    def _load_config(self) -> dict[str, Any]:
        """Load persisted config from config.toml, migrating legacy formats if needed."""
        default_config: dict[str, Any] = {"folders": [], "selected_folder": ""}

        self._migrate_legacy_config()

        if not self._config_path_file.exists():
            return default_config

        try:
            raw  = self._config_path_file.read_text(encoding="utf-8")
            data = tomlkit.loads(raw)
            return dict(data)
        except Exception:
            self._logger.exception("Failed reading config file %s", self._config_path_file)
            return default_config

    def _save_config(self) -> None:
        """Save current state into config.toml, preserving existing comments and formatting."""
        try:
            # Load existing document to preserve comments; fall back to a fresh one
            if self._config_path_file.exists():
                raw = self._config_path_file.read_text(encoding="utf-8")
                doc = tomlkit.loads(raw)
            else:
                doc = tomlkit.document()
                doc.add(tomlkit.comment("Kwal configuration — comments are preserved on save"))
                doc.add(tomlkit.comment("Do not edit while Kwal is running."))
                doc.add(tomlkit.nl())

            # ── scalar values ────────────────────────────────────────────────
            doc["selected_folder"]    = self._selected_folder
            doc["last_set_wallpaper"] = self._last_set_wallpaper

            # ── folders (array of tables) ────────────────────────────────────
            folders_arr = tomlkit.aot()
            for f in self._model._folders:
                tbl = tomlkit.table()
                tbl["name"] = f.name
                tbl["path"] = f.path
                folders_arr.append(tbl)
            doc["folders"] = folders_arr

            # ── custom_commands (array of tables) ────────────────────────────
            cmds_arr = tomlkit.aot()
            for cmd in self._custom_commands:
                tbl = tomlkit.table()
                tbl["command"] = cmd.get("command", "")
                tbl["enabled"] = bool(cmd.get("enabled", True))
                cmds_arr.append(tbl)
            doc["custom_commands"] = cmds_arr

            self._config_path_file.write_text(tomlkit.dumps(doc), encoding="utf-8")
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

    resultDialogVisible = Property(
        bool, _get_result_dialog_visible, _set_result_dialog_visible,
        notify=resultDialogVisibleChanged,
    )

    def _get_result_dialog_text(self) -> str:
        return self._result_dialog_text

    def _set_result_dialog_text(self, txt: str) -> None:
        t = txt or ""
        if self._result_dialog_text != t:
            self._result_dialog_text = t
            self.resultDialogTextChanged.emit()

    resultDialogText = Property(str, _get_result_dialog_text, _set_result_dialog_text, notify=resultDialogTextChanged)

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
            logging.debug(
                "Ignoring stale palette result (req %d, latest %d)",
                request_id, self._latest_palette_request_id,
            )

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
            from ..utils import color_extractor
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

    def _init_base(self) -> None:
        """Initialize base state, config, and shared models."""
        self._current_palette_data: dict[str, Any] = {}

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

        self._compositing_enabled: bool = True
        self._simulate_all_apps: bool = False
        self._show_extension_badge: bool = True

        self._tint_thread: Optional[threading.Thread] = None
        self._apply_thread: Optional[threading.Thread] = None
        self._color_extraction_thread: Optional[threading.Thread] = None
        self._palette_workers: set[PaletteWorker] = set()
        self._latest_palette_request_id: int = 0

        self._home_path: str = str(Path.home()).rstrip("/") + "/"

        self._config_path_file = self._get_config_path_file()
        config = self._load_config()
        self._last_set_wallpaper = cast(str, config.get("last_set_wallpaper", ""))
        if "custom_commands" in config and isinstance(config["custom_commands"], list):
            self._custom_commands = normalize_custom_commands(config["custom_commands"])
        else:
            self._custom_commands = []
        self._last_selected_folder = cast(str, config.get("selected_folder", ""))
        self._loaded_folders = config.get("folders", [])

        self._optional_apps: list[tuple[str, SettingsApp]] = [
            ("fastfetch", SettingsApp(app_name="fastfetch", section="Apps", qml_page="apps/fastfetch.qml")),
            ("starship", SettingsApp(app_name="starship", section="Apps", qml_page="apps/starship.qml")),
            ("ulauncher", SettingsApp(app_name="ulauncher", section="Apps", qml_page="apps/ulauncher.qml")),
        ]
        self._settings_app_model = SettingsAppModel(self._build_app_list())

        self._templates_installed = self._check_templates_installed()
