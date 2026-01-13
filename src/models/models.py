from __future__ import annotations

import hashlib
import logging
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, cast

from PySide6.QtCore import (
    QAbstractListModel,
    QModelIndex,
    QObject,
    Property,
    Qt,
    QThread,
    QTimer,
    Signal,
    Slot,
)
from PySide6.QtGui import QImage

# Logger
logger = logging.getLogger(__name__)


@dataclass
class Folder:
    name: str
    path: str


@dataclass
class SettingsApp:
    app_name: str
    section: str
    qml_page: str
    title: str = ""

    def __post_init__(self) -> None:
        if not self.title:
            self.title = self.app_name.capitalize()


class WallpaperFolderModel(QAbstractListModel):
    NameRole = Qt.UserRole + 1
    PathRole = Qt.UserRole + 2

    def __init__(self, folders: list[Folder] | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._folders: list[Folder] = folders or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._folders)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None
        folder = self._folders[index.row()]
        if role == WallpaperFolderModel.NameRole:
            return folder.name
        if role == WallpaperFolderModel.PathRole:
            return folder.path
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            WallpaperFolderModel.NameRole: b"name",
            WallpaperFolderModel.PathRole: b"path",
        }

    @Slot(str, str)
    def addFolder(self, name: str, path: str) -> None:
        logger.debug("Adding folder %s %s", name, path)
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        self._folders.append(Folder(name=name, path=path))
        self.endInsertRows()

    @Slot(int)
    def removeFolder(self, index: int) -> None:
        logger.debug("removeFolder called with index=%d; rowCount=%d", index, self.rowCount())
        if 0 <= index < self.rowCount():
            removed = self._folders[index]
            try:
                self._clear_cache_for_folder(removed.path)
            except Exception:
                logger.exception("Failed clearing cache for folder %s", removed.path)
            
            self.beginRemoveRows(QModelIndex(), index, index)
            del self._folders[index]
            self.endRemoveRows()
            logger.info("Removed folder %s", removed)
        else:
            logger.warning("removeFolder: invalid index %s", index)

    def _clear_cache_for_folder(self, folder_path: str) -> None:
        p = Path(folder_path)
        cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "kwal" / "thumbnails"
        folder_digest = hashlib.sha1(str(p).encode("utf-8")).hexdigest()
        folder_cache = cache_root / folder_digest
        
        if folder_cache.exists():
            try:
                shutil.rmtree(folder_cache)
                logger.info("Cleared thumbnail cache directory %s", folder_cache)
            except Exception:
                logger.exception("Failed to remove cache directory %s", folder_cache)


class ThumbnailWorker(QObject):
    finished = Signal(list, list)

    def __init__(self, folder_path: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.folder_path = folder_path
        self._stopped = False

    @Slot()
    def process(self) -> None:
        try:
            p = Path(self.folder_path)
            if not p.exists() or not p.is_dir():
                logger.warning("ThumbnailWorker: invalid folder %s", self.folder_path)
                self.finished.emit([], [])
                return

            exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
            files: list[Path] = []
            
            # Gather files
            for f in sorted(p.rglob("*")):
                if not f.is_file():
                    continue
                if f.suffix.lower() not in exts:
                    continue
                
                # Filters
                name_lower = f.name.lower()
                sf = str(f)
                if "/previews/" in sf or "screenshot" in name_lower or "preview" in name_lower:
                    continue
                files.append(f)

            # Generate/Load thumbnails
            cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "kwal" / "thumbnails"
            folder_digest = hashlib.sha1(str(p).encode("utf-8")).hexdigest()
            cache_base = cache_root / folder_digest
            cache_base.mkdir(parents=True, exist_ok=True)

            thumbs: list[str] = []
            thumb_w, thumb_h = 320, 240
            
            for f in files:
                if self._stopped:
                    break
                
                f_str = str(f)
                digest = hashlib.sha1(f_str.encode("utf-8")).hexdigest()
                thumb_path = cache_base / (digest + ".png")
                thumb_path_str = str(thumb_path)

                if not thumb_path.exists():
                    try:
                        img = QImage(f_str)
                        if not img.isNull():
                            scaled = img.scaled(thumb_w, thumb_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            scaled.save(thumb_path_str)
                        else:
                            # If image load fails, append empty or fallback? 
                            # Original code omitted lines, assuming empty is safer to avoid desync
                            pass
                    except Exception:
                        logger.exception("Failed creating thumbnail for %s", f)
                        # Ensure we append something to keep lists aligned
                        thumbs.append("")
                        continue

                thumbs.append(thumb_path_str)

            # Safety check: ensure lists are same length
            if len(files) != len(thumbs):
                # If we skipped some thumbs due to check, trim files?
                # Actually my logic above guarantees append unless exception occurs before append
                pass

            self.finished.emit([str(x) for x in files], thumbs)

        except Exception:
            logger.exception("ThumbnailWorker failed for %s", self.folder_path)
            self.finished.emit([], [])


class FastfetchTintWorker(QObject):
    """Worker to generate a tinted image off the main thread."""
    finished = Signal(str)

    def __init__(self, src: str, tint_hex: str, strength: float = 0.8, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.src = src
        self.tint_hex = tint_hex
        self.strength = strength

    @Slot()
    def process(self) -> None:
        try:
            from ..utils import color_utils
            dst = color_utils.tint_image(self.src, self.tint_hex, float(self.strength))
            self.finished.emit(str(dst) if dst else "")
        except Exception:
            logger.exception("FastfetchTintWorker failed for %s", self.src)
            self.finished.emit("")


class ImageModel(QAbstractListModel):
    FileNameRole = Qt.UserRole + 1
    FilePathRole = Qt.UserRole + 2
    ThumbnailRole = Qt.UserRole + 3

    loadingChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._files: list[Path] = []
        self._thumbs: list[str] = []
        self._worker_thread: QThread | None = None
        self._worker: ThumbnailWorker | None = None
        self._loading: bool = False

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._files)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None
        
        idx = index.row()
        if role == ImageModel.FileNameRole:
            return self._files[idx].name
        if role == ImageModel.FilePathRole:
            return str(self._files[idx])
        if role == ImageModel.ThumbnailRole:
            # Handle potential index out of range if arrays desynced (shouldn't happen)
            if idx < len(self._thumbs):
                return self._thumbs[idx]
            return ""
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            ImageModel.FileNameRole: b"fileName",
            ImageModel.FilePathRole: b"filePath",
            ImageModel.ThumbnailRole: b"thumbPath",
        }

    def _get_loading(self) -> bool:
        return self._loading

    loading = Property(bool, _get_loading, notify=loadingChanged)

    def _cleanup_worker(self) -> None:
        if self._worker:
            try:
                self._worker._stopped = True
            except Exception:
                pass
            self._worker = None
            
        if self._worker_thread:
            try:
                if self._worker_thread.isRunning():
                    self._worker_thread.quit()
                    self._worker_thread.wait(1000)
            except RuntimeError:
                pass
            finally:
                self._worker_thread = None

    def setFolder(self, folder_path: str) -> None:
        self._cleanup_worker()

        self.beginResetModel()
        self._files.clear()
        self._thumbs.clear()
        self.endResetModel()

        self._loading = True
        self.loadingChanged.emit()

        if not folder_path:
            self._loading = False
            self.loadingChanged.emit()
            return

        thread = QThread()
        worker = ThumbnailWorker(folder_path)
        worker.moveToThread(thread)
        
        # Connect signals
        thread.started.connect(worker.process)
        worker.finished.connect(self._on_worker_done)
        worker.finished.connect(thread.quit)
        # Clean up
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        
        self._worker = worker
        self._worker_thread = thread
        thread.start()

    @Slot(list, list)
    def _on_worker_done(self, files: list[str], thumbs: list[str]) -> None:
        try:
            self.beginResetModel()
            self._files = [Path(x) for x in files]
            self._thumbs = thumbs
            self.endResetModel()
            logger.debug("ImageModel loaded %d files", len(self._files))
        finally:
            self._loading = False
            self.loadingChanged.emit()


class SettingsAppModel(QAbstractListModel):
    TitleRole = Qt.UserRole + 1
    SectionRole = Qt.UserRole + 2
    PageRole = Qt.UserRole + 3
    AppNameRole = Qt.UserRole + 4

    def __init__(self, apps: list[SettingsApp] | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._apps: list[SettingsApp] = apps or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._apps)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None
        app = self._apps[index.row()]
        if role == SettingsAppModel.AppNameRole:
            return app.app_name
        if role == SettingsAppModel.TitleRole:
            return app.title
        if role == SettingsAppModel.SectionRole:
            return app.section
        if role == SettingsAppModel.PageRole:
            return app.qml_page
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            SettingsAppModel.AppNameRole: b"app_name",
            SettingsAppModel.TitleRole: b"title",
            SettingsAppModel.SectionRole: b"section",
            SettingsAppModel.PageRole: b"qmlpage",
        }

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        default_flags = super().flags(index)  # type: ignore
        if index.isValid():
            return default_flags | Qt.ItemIsDragEnabled
        return default_flags

    @Slot(int, result="QVariantMap")
    def get(self, row: int) -> dict[str, str]:
        if 0 <= row < self.rowCount():
            app = self._apps[row]
            return {
                "app_name": app.app_name,
                "title": app.title,
                "section": app.section,
                "qmlpage": app.qml_page
            }
        return {}

    @Slot(int, int, int)
    def move(self, source: int, destination: int, count: int = 1) -> None:
        if source == destination:
            return
        
        qt_dest = destination + 1 if source < destination else destination
        
        if self.beginMoveRows(QModelIndex(), source, source, QModelIndex(), qt_dest):
            item = self._apps.pop(source)
            self._apps.insert(destination, item)
            self.endMoveRows()


class FastfetchTemplateModel(QAbstractListModel):
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
        if role == FastfetchTemplateModel.FileNameRole:
            return p.name
        if role == FastfetchTemplateModel.FilePathRole:
            return str(p)
        if role == FastfetchTemplateModel.FileUrlRole:
            return "file://" + str(p)
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            FastfetchTemplateModel.FileNameRole: b"fileName",
            FastfetchTemplateModel.FilePathRole: b"filePath",
            FastfetchTemplateModel.FileUrlRole: b"fileUrl",
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
            from ..utils.file_utils import list_template_images

            files = list_template_images(folder_path)
            
            self.beginResetModel()
            self._files = [Path(x) for x in files]
            self.endResetModel()
            logger.debug("FastfetchTemplateModel refreshed %d files", len(self._files))
        except Exception:
            logger.exception("Failed refreshing FastfetchTemplateModel")

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
            from ..utils.file_utils import list_starship_templates

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


class StarshipModel(QObject):
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
    previewChanged = Signal()
    currentConfigPreviewChanged = Signal()

    def __init__(self, config_path: str | None = None, template_folder: str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        from pathlib import Path
        import os

        default_cfg = str(Path.home() / ".config" / "starship.toml")
        default_templates = str(Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kwal" / "templates" / "starship")

        self._config_path: str = config_path or default_cfg
        self._template_folder: str = template_folder or default_templates
        self._palette_names: list[str] = []
        self._palette_values: list[list[str]] = []
        self._palette_keys: list[list[str]] = []
        self._preview_html: str = ""
        self._current_config_preview_html: str = ""
        self._full_config_data: dict[str, Any] = {}

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

    def _get_preview_html(self) -> str:
        return str(self._preview_html)

    def _get_current_config_preview_html(self) -> str:
        return str(self._current_config_preview_html)

    configPath = Property(str, _get_config_path, _set_config_path, notify=configPathChanged)
    templateFolder = Property(str, _get_template_folder, _set_template_folder, notify=templateFolderChanged)
    paletteNames = Property('QVariantList', _get_palette_names, notify=paletteNamesChanged)
    paletteValues = Property('QVariantList', _get_palette_values, notify=paletteValuesChanged)
    paletteKeys = Property('QVariantList', _get_palette_keys, notify=paletteKeysChanged)
    previewHtml = Property(str, _get_preview_html, notify=previewChanged)
    currentConfigPreviewHtml = Property(str, _get_current_config_preview_html, notify=currentConfigPreviewChanged)

    @Slot()
    def reloadCurrentConfigPreview(self) -> None:
        """Reads the actual config file from disk and updates currentConfigPreviewHtml."""
        try:
            from ..utils import file_utils, starship_preview
            import json
            
            # Read from the configured active path (usually ~/.config/starship.toml)
            # If it doesn't exist, we'll get default or error, which is fine
            if not os.path.exists(self._config_path):
                self._current_config_preview_html = ""
                self.currentConfigPreviewChanged.emit()
                return

            json_str, _ = file_utils.read_starship_config(self._config_path)
            data = json.loads(json_str)
            html = starship_preview.generate_preview_html(data)
            
            if self._current_config_preview_html != html:
                self._current_config_preview_html = html
                self.currentConfigPreviewChanged.emit()
        except Exception:
            logger.exception("Failed reloading current config preview")
            self._current_config_preview_html = ""
            self.currentConfigPreviewChanged.emit()

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
                    self._regenerate_preview(palette_idx)
                except Exception:
                    logger.exception("Failed regenerating preview after setPaletteColor")
        except Exception:
            logger.exception("Failed setting palette color")

    def _regenerate_preview(self, palette_index: int | None = None) -> None:
        """Build a minimal data structure from current palette arrays and regenerate preview HTML."""
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
            
            # Generate preview using our internal generator
            self._preview_html = starship_preview.generate_preview_html(out, palette_index)
            self.previewChanged.emit()
        except Exception:
            logger.exception("Failed regenerating preview")

    @Slot(int)
    def setPreviewPaletteIndex(self, idx: int) -> None:
        try:
            self._regenerate_preview(int(idx) if idx is not None else 0)
        except Exception:
            logger.exception("setPreviewPaletteIndex failed")

    @Slot(result="QVariantMap")
    @Slot(str, result="QVariantMap")
    def refresh(self, path: str | None = None) -> dict:
        """Read starship config (using utils.file_utils.read_starship_config) and update properties.

        Returns a small map for QML with `config_path` and `palettes_count` for convenience.
        """
        try:
            # Import inside method to avoid circular imports
            from ..utils import file_utils
            import json

            json_str, display = file_utils.read_starship_config(path or self._config_path)
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
                self._regenerate_preview(0 if len(names) > 0 else None)
            except Exception:
                logger.exception("Failed to generate preview after refresh")

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

@dataclass
class PaletteData:
    colors: list[str]      # 16 Base colors
    accents: list[str]     # Accent colors
    backend_used: str      # 'pywal16', 'material-you', 'imagemagick'
    source_path: str       # Source image path
    seed: str = ""         # Seed color used (hex)


class UlauncherTemplateModel(QAbstractListModel):
    FolderNameRole = Qt.UserRole + 1
    FolderPathRole = Qt.UserRole + 2
    FolderUrlRole = Qt.UserRole + 3
    IsTemplateRole = Qt.UserRole + 4

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None
        item = self._items[index.row()]
        p = item["path"]
        if role == UlauncherTemplateModel.FolderNameRole:
            return p.name
        if role == UlauncherTemplateModel.FolderPathRole:
            return str(p)
        if role == UlauncherTemplateModel.FolderUrlRole:
            return "file://" + str(p)
        if role == UlauncherTemplateModel.IsTemplateRole:
            return item["is_template"]
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            UlauncherTemplateModel.FolderNameRole: b"fileName",
            UlauncherTemplateModel.FolderPathRole: b"filePath",
            UlauncherTemplateModel.FolderUrlRole: b"fileUrl",
            UlauncherTemplateModel.IsTemplateRole: b"isTemplate",
        }

    @Slot()
    @Slot(str)
    def refresh(self, template_folder: str | None = None) -> None:
        """Populate model from multiple theme sources.
        
        Sources:
        Sources:
        1. Managed templates (configured folder) -> is_template=True
        2. Internal templates (src/resources/templates/ulauncher) -> is_template=True
        3. User themes (~/.config/ulauncher/user-themes/) -> is_template=False
        """
        try:
            from ..utils.file_utils import list_ulauncher_templates
            
            new_items: list[dict[str, Any]] = []
            seen_paths: set[str] = set()

            # 1. Managed templates (external config)
            if template_folder:
                for p_str in list_ulauncher_templates(template_folder):
                    p = Path(p_str)
                    res_path = str(p.resolve())
                    theme_key = p.name # Use folder name as key
                    if theme_key not in seen_paths and res_path not in seen_paths:
                        new_items.append({"path": p, "is_template": True})
                        seen_paths.add(theme_key)
                        seen_paths.add(res_path)

            # 2. Internal templates (Development/Bundled)
            try:
                internal_root = Path(__file__).parent.parent / "resources" / "templates" / "ulauncher"
                if internal_root.is_dir():
                    for p_str in list_ulauncher_templates(internal_root):
                        p = Path(p_str)
                        res_path = str(p.resolve())
                        theme_key = p.name
                        if theme_key not in seen_paths and res_path not in seen_paths:
                            new_items.append({"path": p, "is_template": True})
                            seen_paths.add(theme_key)
                            seen_paths.add(res_path)
            except Exception:
                pass

            # 3. User themes (These are installed, so we don't deduplicate against templates folder names, 
            # but we still check path to avoid absolute path duplicates)
            user_themes = Path.home() / ".config" / "ulauncher" / "user-themes"
            for p_str in list_ulauncher_templates(user_themes):
                p = Path(p_str)
                res_path = str(p.resolve())
                if res_path not in seen_paths:
                    new_items.append({"path": p, "is_template": False})
                    seen_paths.add(res_path)

            self.beginResetModel()
            self._items = new_items
            self.endResetModel()
            logger.debug("UlauncherTemplateModel refreshed %d items", len(self._items))
        except Exception:
            logger.exception("Failed refreshing UlauncherTemplateModel")

    @Slot(int, result="QVariantMap")
    def get(self, row: int) -> dict[str, Any]:
        """Expose item as map for QML."""
        if 0 <= row < self.rowCount():
            item = self._items[row]
            return {
                "fileName": item["path"].name,
                "filePath": str(item["path"]),
                "fileUrl": "file://" + str(item["path"]),
                "isTemplate": item["is_template"]
            }
        return {}



class UlauncherModel(QObject):
    """QObject model exposing Ulauncher theme info for QML.

    Provides:
    - `configPath` (str): path to current theme directory
    - `templateFolder` (str): templates folder for ulauncher
    - `paletteNames` (list[str]): ["manifest", "theme"]
    - `paletteValues` (list[list[str]]): colors corresponding to keys
    - `paletteKeys` (list[list[str]]): keys for manifest and theme.css
    """

    configPathChanged = Signal()
    actualConfigPathChanged = Signal()
    templateFolderChanged = Signal()
    paletteNamesChanged = Signal()
    paletteValuesChanged = Signal()
    paletteKeysChanged = Signal()
    previewScaleChanged = Signal()
    previewWidthChanged = Signal()

    def __init__(self, config_path: str | None = None, template_folder: str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        from pathlib import Path
        import os

        # Ulauncher config default
        self._config_file = Path.home() / ".config" / "ulauncher" / "settings.json"
        
        default_templates = str(Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kwal" / "templates" / "ulauncher")

        self._current_theme_path: str = config_path or ""
        self._template_folder: str = template_folder or default_templates
        self._palette_names: list[str] = []
        self._palette_values: list[list[str]] = []
        self._palette_keys: list[list[str]] = []
        
        # Internal storage of full extracted data
        self._full_data: dict[str, Any] = {}
        self._original_palette_values: list[list[str]] = []
        self._preview_html: str = ""
        self._current_config_preview_html: str = ""
        self._preview_scale: float = 0.4
        self._preview_width: int = 650

        # Debounce timer to avoid lag during resizing/editing
        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(50) # 50ms delay
        self._render_timer.timeout.connect(self._refresh_previews)

    def _get_config_path(self) -> str:
        return self._current_theme_path

    def _set_config_path(self, p: str) -> None:
        val = str(p or "")
        if self._current_theme_path != val:
            self._current_theme_path = val
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


    @Slot(int, int, str)
    def setPaletteColor(self, palette_idx: int, color_idx: int, color: str) -> None:
        try:
            from ..utils import color_utils
            if 0 <= palette_idx < len(self._palette_values):
                current_vals = self._palette_values[palette_idx]
                if 0 <= color_idx < len(current_vals):
                    # Smart format: Hex if solid, rgba if transparent
                    formatted_color = color_utils.format_css_color(color)
                    current_vals[color_idx] = formatted_color
                    
                    # Update _full_data for preview
                    section_name = self._palette_names[palette_idx]
                    key_name = self._palette_keys[palette_idx][color_idx]
                    if section_name in self._full_data:
                        self._full_data[section_name][key_name] = formatted_color
                    
                    # Update Preview
                    try:
                        from ..utils import ulauncher_preview2
                        live = self._get_live_colors()
                        self._preview_html = ulauncher_preview2.generate_preview_html(
                            self._current_theme_path, live, scale=self._preview_scale, window_width=self._preview_width
                        )
                    except Exception:
                        pass
                    
                    self.paletteValuesChanged.emit()
        except Exception:
            logger.exception("Failed setting ulauncher palette color")

    def _get_live_colors(self) -> dict[str, str]:
        """Flatten hierarchical palette into a single dict."""
        flat = {}
        for p_idx, p_name in enumerate(self._palette_names):
            # We only care about root values (manifest keys, theme variable names)
            # for the preview renderer logic.
            keys = self._palette_keys[p_idx]
            values = self._palette_values[p_idx]
            for k, v in zip(keys, values):
                flat[k] = str(v)
        return flat

    def _resolve_current_theme_path(self) -> str:
        """Read ulauncher settings.json, get theme_name, then find folder where manifest['name'] matches."""
        try:
            import json
            if not self._config_file.exists():
                return ""
            
            with self._config_file.open("r", encoding="utf-8") as f:
                settings = json.load(f)
                
            required_theme_name = settings.get("theme_name", "")
            if not required_theme_name:
                return ""
            
            # Helper to check a root directory
            def find_in_root(root: Path) -> str | None:
                if not root.is_dir():
                    return None
                for child in root.iterdir():
                    if child.is_dir():
                        manifest = child / "manifest.json"
                        if manifest.exists():
                            try:
                                with manifest.open("r", encoding="utf-8") as mf:
                                    data = json.load(mf)
                                    if data.get("name") == required_theme_name:
                                        return str(child.resolve())
                            except Exception:
                                pass
                return None

            # 1. Check user themes (Priority)
            found = find_in_root(Path.home() / ".config" / "ulauncher" / "user-themes")
            if found: return found

            # 2. Check system themes (Standard locations)
            # ~/.local/share/ulauncher/themes
            found = find_in_root(Path.home() / ".local" / "share" / "ulauncher" / "themes")
            if found: return found
            
            # /usr/share/ulauncher/themes
            found = find_in_root(Path("/usr/share/ulauncher/themes"))
            if found: return found
            
            # Fallback: check if directory exists with that name directly (old behavior/fallback)
            for p in [
                Path.home() / ".config" / "ulauncher" / "user-themes" / required_theme_name,
                Path("/usr/share/ulauncher/themes") / required_theme_name
            ]:
                if p.is_dir():
                    return str(p.resolve())

            return ""
        except Exception:
            logger.exception("Failed resolving ulauncher theme path")
            return ""

    @Slot(result=bool)
    def _get_is_modified(self) -> bool:
        return self._palette_values != self._original_palette_values

    def _get_all_colors_filled(self) -> bool:
        """Check if any color is still 'transparent' (the placeholder for ulauncher)."""
        for section in self._palette_values:
            for val in section:
                if str(val).lower() == "transparent":
                    return False
        return True

    def _get_preview_scale(self) -> float:
        return self._preview_scale

    def _set_preview_scale(self, val: float) -> None:
        if self._preview_scale != val:
            self._preview_scale = float(val)
            self._render_timer.start() # Trigger non-blocking re-render
            self.previewScaleChanged.emit()

    def _get_preview_width(self) -> int:
        return self._preview_width

    def _set_preview_width(self, val: int) -> None:
        if self._preview_width != val:
            self._preview_width = int(val)
            self._render_timer.start() # Trigger non-blocking re-render
            self.previewWidthChanged.emit()

    def _get_preview_html(self) -> str:
        return self._preview_html

    def _get_current_config_preview_html(self) -> str:
        return self._current_config_preview_html

    def _refresh_previews(self) -> None:
        """Internal helper to regenerate HTML for all preview properties."""
        try:
            from ..utils import ulauncher_preview2
            live = self._get_live_colors()
            
            # Resolve paths
            actual_current_path = self._resolve_current_theme_path()
            target_path = self._current_theme_path or actual_current_path
            
            if not target_path:
                return

            # 1. Update Live Preview (Always)
            new_live_html = ulauncher_preview2.generate_preview_html(
                target_path, live, scale=self._preview_scale, window_width=self._preview_width
            )
            self._preview_html = new_live_html

            # 2. Update Current Config Preview
            # We update it ONLY if we are currently looking at the actual system theme,
            # OR if it's already populated (to maintain sync during resizing).
            if target_path == actual_current_path or self._current_config_preview_html:
                 self._current_config_preview_html = ulauncher_preview2.generate_preview_html(
                     actual_current_path, {}, scale=self._preview_scale, window_width=self._preview_width
                 )

            self.paletteValuesChanged.emit() # Trigger QML update
        except Exception:
            logger.exception("Failed refreshing previews")

    configPath = Property(str, _get_config_path, _set_config_path, notify=configPathChanged)
    actualConfigPath = Property(str, _resolve_current_theme_path, notify=actualConfigPathChanged)
    templateFolder = Property(str, _get_template_folder, _set_template_folder, notify=templateFolderChanged)
    paletteNames = Property('QVariantList', _get_palette_names, notify=paletteNamesChanged)
    paletteValues = Property('QVariantList', _get_palette_values, notify=paletteValuesChanged)
    paletteKeys = Property('QVariantList', _get_palette_keys, notify=paletteKeysChanged)
    isModified = Property(bool, _get_is_modified, notify=paletteValuesChanged)
    allColorsFilled = Property(bool, _get_all_colors_filled, notify=paletteValuesChanged)
    previewHtml = Property(str, _get_preview_html, notify=paletteValuesChanged)
    currentConfigPreviewHtml = Property(str, _get_current_config_preview_html, notify=paletteValuesChanged)
    previewScale = Property(float, _get_preview_scale, _set_preview_scale, notify=previewScaleChanged)
    previewWidth = Property(int, _get_preview_width, _set_preview_width, notify=previewWidthChanged)


    @Slot(result="QVariantMap")
    @Slot(str, result="QVariantMap")
    def refresh(self, path: str | None = None) -> dict:
        """Read ulauncher theme at path (or resolve current if None)."""
        try:
            from ..utils import file_utils
            
            target_path = path
            if not target_path:
                target_path = self._resolve_current_theme_path()
                # On startup/auto-refresh, signal that the actual config path is resolved
                self.actualConfigPathChanged.emit()

            self._set_config_path(target_path)
            
            if not target_path:
                # Clear if no theme found
                self._palette_names = []
                self._palette_values = []
                self._palette_keys = []
                self.paletteNamesChanged.emit()
                self.paletteValuesChanged.emit()
                self.paletteKeysChanged.emit()
                return {"config_path": "", "palettes_count": 0}

            data = file_utils.read_ulauncher_theme(target_path)
            self._full_data = data
            
            # Convert to lists for QML
            # We enforce a specific order: manifest, theme
            names = []
            keys = []
            values = []
            
            # Manifest
            manifest = data.get("manifest", {})
            if manifest:
                names.append("manifest")
                m_keys = list(manifest.keys())
                keys.append(m_keys)
                values.append([str(manifest[k]) for k in m_keys])
                
            # Theme
            # Theme
            theme = data.get("theme", {})
            if theme:
                 names.append("theme")
                 t_keys = list(theme.keys())
                 keys.append(t_keys)
                 values.append([str(theme[k]) for k in t_keys])

            self._palette_names = names
            self._palette_keys = keys
            self._palette_values = values
            self._original_palette_values = [list(x) for x in values] # Deep copy

            # Generate Preview - use timer for initial load too if it's the first time
            # or if we are refreshing against a new path.
            # This avoids blocking the UI when first opening the tab.
            self._render_timer.start()
            
            self.paletteNamesChanged.emit()
            self.paletteKeysChanged.emit()
            self.paletteValuesChanged.emit()
            
            return {"config_path": target_path, "palettes_count": len(names)}
        except Exception:
            logger.exception("UlauncherModel.refresh failed")
            return {"config_path": "", "palettes_count": 0}

    def _get_has_backup(self) -> bool:
        try:
             # Check if theme-specific .bak files exist
             theme_bak = False
             if self._current_theme_path:
                 p = Path(self._current_theme_path)
                 theme_bak = (p / "theme.css.bak").exists() or (p / "manifest.json.bak").exists()
             
             return theme_bak
        except Exception:
            return False

    hasBackup = Property(bool, _get_has_backup, notify=configPathChanged) # Re-check when config path changes

    @Slot()
    def restore(self) -> None:
        """Restore .bak files if they exist (both settings and theme files)."""
        try:
            restored = False


            # 2. Restore Theme Files
            if self._current_theme_path:
                p = Path(self._current_theme_path)
                
                # Restore Manifest
                man_bak = p / "manifest.json.bak"
                man_orig = p / "manifest.json"
                if man_bak.exists():
                    shutil.copy2(man_bak, man_orig)
                    restored = True
                    
                # Restore CSS
                css_bak = p / "theme.css.bak"
                css_orig = p / "theme.css"
                if css_bak.exists():
                    shutil.copy2(css_bak, css_orig)
                    restored = True
                
            if restored:
                logger.info("Restored Ulauncher backups")
                self.refresh() # Reload model
                # Trigger property changes
                self.configPathChanged.emit() 
        except Exception:
            logger.exception("Failed to restore Ulauncher backup")

    @Slot()
    def apply(self, skip_backup: bool = False) -> bool:
        """Write current in-memory palette values to the files at `configPath`."""
        try:
            if not self._current_theme_path:
                return False

            from ..utils import file_utils
            
            # Reconstruct data dict from properties
            data_to_write = {"manifest": {}, "theme": {}}
            
            for i, name in enumerate(self._palette_names):
                if i >= len(self._palette_keys) or i >= len(self._palette_values):
                    continue
                
                k_list = self._palette_keys[i]
                v_list = self._palette_values[i]
                
                # Combine
                combined = {}
                for j, key in enumerate(k_list):
                    val = v_list[j] if j < len(v_list) else ""
                    combined[key] = val
                
                if name == "manifest":
                    data_to_write["manifest"] = combined
                elif name == "theme":
                    data_to_write["theme"] = combined
            
            return file_utils.write_ulauncher_theme(self._current_theme_path, data_to_write, skip_backup=skip_backup)
            
        except Exception:
            logger.exception("UlauncherModel.apply failed")
            return False