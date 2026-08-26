"""Starship models: template list and the editable config model."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    Signal,
    Slot,
)

from ..utils import starship_preview
from ..utils.xdg_paths import kwal_config_dir
from .preview_base import PreviewModelBase

# Logger
logger = logging.getLogger(__name__)


class StarshipTemplateModel(QAbstractListModel):
    FileNameRole = Qt.UserRole + 1
    FilePathRole = Qt.UserRole + 2
    FileUrlRole = Qt.UserRole + 3

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._files: list[Path] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._files)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None
        p = self._files[index.row()]
        if role == StarshipTemplateModel.FileNameRole:
            return p.name
        if role == StarshipTemplateModel.FilePathRole:
            return str(p)
        if role == StarshipTemplateModel.FileUrlRole:
            return "file://" + str(p)
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            StarshipTemplateModel.FileNameRole: b"fileName",
            StarshipTemplateModel.FilePathRole: b"filePath",
            StarshipTemplateModel.FileUrlRole: b"fileUrl",
        }

    @Slot(str)
    def refresh(self, folder_path: str | None = None) -> None:
        """Populate model from a folder path."""
        try:
            if not folder_path:
                self.beginResetModel()
                self._files.clear()
                self.endResetModel()
                return

            # Import here to avoid circular dependencies if utils imports models
            from ..utils.starship_config import list_starship_templates

            startship_files = list_starship_templates(folder_path)

            self.beginResetModel()
            self._files = [Path(x) for x in startship_files]
            self.endResetModel()
            logger.debug("StarshipTemplateModel refreshed %d files", len(self._files))
        except Exception:
            logger.exception("Failed refreshing StarshipTemplateModel")

    @Slot(int, result="QVariantMap")
    def get(self, row: int) -> dict[str, str]:
        if 0 <= row < self.rowCount():
            p = self._files[row]
            return {
                "fileName": p.name,
                "filePath": str(p),
                "fileUrl": "file://" + str(p)
            }
        return {}


class StarshipModel(PreviewModelBase):
    """Lightweight QObject model exposing Starship config info for QML.

    Provides:
    - `configPath` (str): path to starship.toml
    - `templateFolder` (str): templates folder for starship
    - `paletteNames` (list[str]): list of palette names found in config
    - `paletteValues` (list[list[str]]): parallel list of palettes values (each is list of color strings)
    """

    configPathChanged = Signal()
    templateFolderChanged = Signal()
    paletteNamesChanged = Signal()
    paletteValuesChanged = Signal()
    paletteKeysChanged = Signal()

    def __init__(
        self,
        config_path: str | None = None,
        template_folder: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(default_scale=1.0, default_width=800, render_interval_ms=100, parent=parent)
        from pathlib import Path

        default_cfg = str(Path.home() / ".config" / "starship.toml")
        default_templates = str(kwal_config_dir() / "templates" / "starship")

        self._config_path: str = config_path or default_cfg
        self._template_folder: str = template_folder or default_templates
        self._palette_names: list[str] = []
        self._palette_values: list[list[str]] = []
        self._palette_keys: list[list[str]] = []
        self._full_config_data: dict[str, Any] = {}

        # Debounce timer renders the editable preview on palette/scale/width changes
        self._render_timer.timeout.connect(self._regenerate_preview_task)

    def _get_config_path(self) -> str:
        return self._config_path

    def _set_config_path(self, p: str) -> None:
        val = str(p or "")
        if self._config_path != val:
            self._config_path = val
            self.configPathChanged.emit()

    def _get_template_folder(self) -> str:
        return self._template_folder

    def _set_template_folder(self, p: str) -> None:
        val = str(p or "")
        if self._template_folder != val:
            self._template_folder = val
            self.templateFolderChanged.emit()

    def _get_palette_names(self) -> list[str]:
        return list(self._palette_names)

    def _get_palette_values(self) -> list[list[str]]:
        return [list(x) for x in self._palette_values]

    def _get_palette_keys(self) -> list[list[str]]:
        return [list(x) for x in self._palette_keys]

    def _on_preview_params_changed(self) -> None:
        # Resizing the preview also requires re-reading the on-disk config preview
        self.reloadCurrentConfigPreview()

    configPath = Property(str, _get_config_path, _set_config_path, notify=configPathChanged)
    templateFolder = Property(str, _get_template_folder, _set_template_folder, notify=templateFolderChanged)
    paletteNames = Property('QVariantList', _get_palette_names, notify=paletteNamesChanged)
    paletteValues = Property('QVariantList', _get_palette_values, notify=paletteValuesChanged)
    paletteKeys = Property('QVariantList', _get_palette_keys, notify=paletteKeysChanged)

    @Slot()
    def reloadCurrentConfigPreview(self) -> None:
        """Reads the actual config file from disk and triggers background rendering."""
        try:
            import json

            from ..utils import starship_config

            if not os.path.exists(self._config_path):
                self._current_config_preview_html = ""
                self.currentConfigPreviewChanged.emit()
                return

            json_str, _ = starship_config.read_starship_config(self._config_path)
            data = json.loads(json_str)

            # Render in a background worker to keep the UI responsive.
            self._start_worker(
                starship_preview.generate_starship_preview_html,
                (data, None, self._preview_scale, self._preview_width),
                "currentConfigPreviewHtml"
            )
        except Exception:
            logger.exception("Failed triggering current config preview background task")

    @Slot(int, int, str)
    def setPaletteColor(self, palette_idx: int, color_idx: int, color: str) -> None:
        try:
            if 0 <= palette_idx < len(self._palette_values):
                # We need to make a copy if we want to ensure immutability paradigms, but modifying in place is fine
                # self._palette_values is a list of lists of strings
                self._palette_values[palette_idx][color_idx] = str(color)
                self.paletteValuesChanged.emit()
                # regenerate preview for the palette we modified
                try:
                    self._render_timer.start()
                except Exception:
                    logger.exception("Failed starting render timer after setPaletteColor")
        except Exception:
            logger.exception("Failed setting palette color")

    def _regenerate_preview_task(self) -> None:
        """Build a minimal data structure from current palette arrays and start background worker."""
        try:
            from ..utils import starship_preview

            # Start with full config data to preserve format, modules, etc.
            out = self._full_config_data.copy() if self._full_config_data else {}

            # Ensure basic structure exists if full config missing
            if "config_path" not in out:
                out["config_path"] = self._config_path
            if "palettes" not in out:
                out["palettes"] = {}

            # Override/Update palettes with current values from QML model
            for i, name in enumerate(self._palette_names):
                klist = self._palette_keys[i] if i < len(self._palette_keys) else []
                vlist = self._palette_values[i] if i < len(self._palette_values) else []
                mapping: dict[str, str] = {}
                for j, k in enumerate(klist):
                    mapping[k] = vlist[j] if j < len(vlist) else ""
                out["palettes"][name] = mapping

            self._start_worker(
                starship_preview.generate_starship_preview_html,
                (out, None, self._preview_scale, self._preview_width),
                "previewHtml"
            )
        except Exception:
            logger.exception("Failed starting Starship background preview task")

    @Slot(int)
    def setPreviewPaletteIndex(self, idx: int) -> None:
        try:
             # Just trigger a render, we can't easily pass the index through the timer
             # without complex state, but usually if we are switching, we want a fresh render anyway.
             self._render_timer.start()
        except Exception:
            logger.exception("setPreviewPaletteIndex failed")

    @Slot(result="QVariantMap")
    @Slot(str, result="QVariantMap")
    def refresh(self, path: str | None = None) -> dict:
        """Read starship config (using utils.starship_config.read_starship_config) and update properties.

        Returns a small map for QML with `config_path` and `palettes_count` for convenience.
        """
        try:
            # Import inside method to avoid circular imports
            import json

            from ..utils import starship_config

            json_str, display = starship_config.read_starship_config(path or self._config_path)
            data = json.loads(json_str)

            # Store full data for preview generation
            self._full_config_data = data

            palettes = data.get("palettes", {}) if isinstance(data, dict) else {}

            names: list[str] = []
            values: list[list[str]] = []
            keys: list[list[str]] = []

            if isinstance(palettes, dict):
                for pname, pvals in palettes.items():
                    names.append(str(pname))
                    # pvals may be dict of color entries; collect keys and values in stable key order
                    if isinstance(pvals, dict):
                        # Preserve file order as provided by the TOML parser (do not sort)
                        klist = [str(k) for k in pvals.keys()]
                        vlist = [str(v) for v in pvals.values()]
                    else:
                        klist = ["value"]
                        vlist = [str(pvals)] if pvals is not None else []

                    keys.append(klist)
                    values.append(vlist)

            self._palette_names = names
            self._palette_values = values
            self._palette_keys = keys

            self.paletteNamesChanged.emit()
            self.paletteValuesChanged.emit()
            self.paletteKeysChanged.emit()

            # regenerate preview using first palette by default
            try:
                self._render_timer.start()
            except Exception:
                logger.exception("Failed to trigger preview after refresh")

            # Also reload current config preview if this was a refresh of the main config
            if path is None or path == self._config_path:
                 self.reloadCurrentConfigPreview()
            else:
                 # If we loaded a template, make sure we still have the current system preview loaded
                 if not self._current_config_preview_html:
                      self.reloadCurrentConfigPreview()

            return {"config_path": display, "palettes_count": len(names)}
        except Exception:
            logger.exception("StarshipModel.refresh failed")
            return {"config_path": self._config_path, "palettes_count": 0}
