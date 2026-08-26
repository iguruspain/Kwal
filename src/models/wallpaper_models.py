"""Wallpaper-related models: folder list, image grid, and background scanners."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Any

import shiboken6 as shiboken
from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    QThread,
    Signal,
    Slot,
)

from ..utils.worker_thread import start_worker_thread
from ..utils.xdg_paths import kwal_cache_dir
from .common import Folder

# Logger
logger = logging.getLogger(__name__)


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
        cache_root = kwal_cache_dir() / "thumbnails"
        folder_digest = hashlib.sha1(str(p).encode("utf-8")).hexdigest()
        folder_cache = cache_root / folder_digest

        if folder_cache.exists():
            try:
                shutil.rmtree(folder_cache)
                logger.info("Cleared thumbnail cache directory %s", folder_cache)
            except Exception:
                logger.exception("Failed to remove cache directory %s", folder_cache)


class ImageScannerWorker(QObject):
    finished = Signal(list)

    def __init__(self, folder_path: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.folder_path = folder_path
        self._stopped = False

    @Slot()
    def process(self) -> None:
        try:
            from ..utils import video_utils

            p = Path(self.folder_path)
            if not p.exists() or not p.is_dir():
                logger.warning("ImageScannerWorker: invalid folder %s", self.folder_path)
                self.finished.emit([])
                return

            image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
            video_exts = video_utils.VIDEO_EXTENSIONS
            supported_exts = image_exts | video_exts
            files: list[str] = []

            # Gather files
            for f in sorted(p.rglob("*")):
                if self._stopped:
                    break
                if not f.is_file():
                    continue
                if f.suffix.lower() not in supported_exts:
                    continue

                # Filters
                name_lower = f.name.lower()
                sf = str(f)
                if "/previews/" in sf or "screenshot" in name_lower or "preview" in name_lower:
                    continue
                files.append(sf)

            self.finished.emit(files)

        except Exception:
            logger.exception("ImageScannerWorker failed for %s", self.folder_path)
            self.finished.emit([])


class ColorScannerWorker(QObject):
    progress = Signal(str, list, list) # path, colors, categories
    finished = Signal()

    def __init__(self, files: list[Path], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.files = files
        self._stopped = False

    @Slot()
    def process(self) -> None:
        try:
            from ..utils import color_extractor, color_utils, video_utils
            cache = color_extractor.load_color_cache()
            dirty = False

            for f in self.files:
                if self._stopped:
                    break
                try:
                    path_str = str(f)
                    mtime = os.path.getmtime(path_str)

                    cached_data = cache.get(path_str)
                    if cached_data and cached_data.get("last_modified") == mtime:
                        continue # Already cached

                    # For videos, use the cached native-resolution frame for color extraction.
                    # This ensures consistency with the controller path (selectWallpaper) and
                    # avoids artifacts from downscaled thumbnails or PIL re-encoding.
                    image_path = path_str
                    if video_utils.is_video_file(path_str):
                        frame_path = video_utils.get_video_frame_path(path_str, timestamp=0.0)
                        if frame_path:
                            image_path = frame_path
                        else:
                            logger.debug("Failed to extract frame from video: %s", path_str)
                            continue

                    # Extract colors using Matugen/Celebi utility
                    colors = color_utils.extract_wallpaper_top_colors(image_path, 8)

                    if colors:
                        cats = []
                        for c in colors:
                            cat = color_extractor.get_color_category(c)
                            if cat not in cats:
                                cats.append(cat)
                            if len(cats) > color_extractor.MAX_CATEGORIES:
                                break

                        cache[path_str] = {
                            "colors": colors,
                            "categories": cats,
                            "last_modified": mtime
                        }
                        dirty = True
                        self.progress.emit(path_str, colors, cats)
                except Exception as e:
                    logger.debug("ColorScannerWorker error processing %s: %s", f, e)

            if dirty and not self._stopped:
                color_extractor.save_color_cache(cache)

        except Exception:
            logger.exception("ColorScannerWorker failed")
        finally:
            self.finished.emit()


class ImageModel(QAbstractListModel):
    FileNameRole = Qt.UserRole + 1
    FilePathRole = Qt.UserRole + 2
    ThumbnailRole = Qt.UserRole + 3
    FileTypeRole = Qt.UserRole + 4
    IsVideoRole = Qt.UserRole + 5

    loadingChanged = Signal()
    filterTextChanged = Signal()
    colorFilterChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._all_files: list[Path] = []
        self._files: list[Path] = []

        self._worker_thread: QThread | None = None
        self._worker: ImageScannerWorker | None = None

        self._color_worker_thread: QThread | None = None
        self._color_worker: ColorScannerWorker | None = None

        self._loading: bool = False
        self._filter_text: str = ""
        self._color_filter: list[str] = []
        self._color_cache: dict[str, dict] = {}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._files)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < self.rowCount()):
            return None

        idx = index.row()
        from ..utils import video_utils

        if role == ImageModel.FileNameRole:
            return self._files[idx].name
        if role == ImageModel.FilePathRole:
            return str(self._files[idx])
        if role == ImageModel.ThumbnailRole:
            file_path = str(self._files[idx])
            if video_utils.is_video_file(file_path):
                return "image://video_thumbnail/" + file_path
            return "image://fdo_thumbnail/" + file_path
        if role == ImageModel.FileTypeRole:
            file_path = str(self._files[idx])
            if video_utils.is_video_file(file_path):
                return "video"
            return "image"
        if role == ImageModel.IsVideoRole:
            return video_utils.is_video_file(str(self._files[idx]))
        return None

    def roleNames(self) -> dict[int, bytes]:
        return {
            ImageModel.FileNameRole: b"fileName",
            ImageModel.FilePathRole: b"filePath",
            ImageModel.ThumbnailRole: b"thumbPath",
            ImageModel.FileTypeRole: b"fileType",
            ImageModel.IsVideoRole: b"isVideo",
        }

    def _get_loading(self) -> bool:
        return self._loading

    loading = Property(bool, _get_loading, notify=loadingChanged)

    def _get_filter_text(self) -> str:
        return self._filter_text

    def _set_filter_text(self, text: str) -> None:
        if self._filter_text != text:
            self._filter_text = text
            self._apply_filter()
            self.filterTextChanged.emit()

    filterText = Property(str, _get_filter_text, _set_filter_text, notify=filterTextChanged)

    def _get_color_filters(self) -> list:
        return self._color_filter

    def _set_color_filters(self, filters: list) -> None:
        if self._color_filter != filters:
            self._color_filter = list(filters) if filters else []
            self._apply_filter()
            self.colorFilterChanged.emit()

    colorFilters = Property(list, _get_color_filters, _set_color_filters, notify=colorFilterChanged)

    def _apply_filter(self) -> None:
        self.beginResetModel()
        self._files = []
        term = self._filter_text.lower() if self._filter_text else ""

        for f in self._all_files:
            # Text filter
            if term and term not in f.name.lower():
                continue

            # Color filter (AND logic: must have ALL selected colors)
            if self._color_filter:
                cache_entry = self._color_cache.get(str(f))
                if not cache_entry:
                    continue

                cats = cache_entry.get("categories", [])
                old_cat = cache_entry.get("category", "")

                has_all_colors = True
                for filter_name in self._color_filter:
                    if filter_name not in cats and filter_name != old_cat:
                        has_all_colors = False
                        break
                if not has_all_colors:
                    continue

            self._files.append(f)

        self.endResetModel()

    def _cleanup_worker(self) -> None:
        if self._worker:
            try:
                self._worker._stopped = True
            except Exception:
                pass
            self._worker = None

        if self._worker_thread:
            try:
                if shiboken.isValid(self._worker_thread) and self._worker_thread.isRunning():
                    self._worker_thread.quit()
                    self._worker_thread.wait(1000)
            except RuntimeError:
                pass
            finally:
                self._worker_thread = None

    def _cleanup_color_worker(self) -> None:
        if self._color_worker:
            try:
                self._color_worker._stopped = True
            except Exception:
                pass
            self._color_worker = None

        if self._color_worker_thread:
            try:
                if shiboken.isValid(self._color_worker_thread) and self._color_worker_thread.isRunning():
                    self._color_worker_thread.quit()
                    self._color_worker_thread.wait(1000)
            except RuntimeError:
                pass
            finally:
                self._color_worker_thread = None

    def setFolder(self, folder_path: str) -> None:
        self._cleanup_worker()
        self._cleanup_color_worker()

        self.beginResetModel()
        self._all_files.clear()
        self._files.clear()
        self.endResetModel()

        self._loading = True
        self.loadingChanged.emit()

        if not folder_path:
            self._loading = False
            self.loadingChanged.emit()
            return

        worker = ImageScannerWorker(folder_path)
        worker.finished.connect(self._on_worker_done)
        thread = start_worker_thread(worker)

        self._worker = worker
        self._worker_thread = thread

    @Slot(list)
    def _on_worker_done(self, files: list[str]) -> None:
        try:
            self._all_files = [Path(x) for x in files]

            # Load cache instantly to allow immediate filtering
            from ..utils import color_extractor
            self._color_cache = color_extractor.load_color_cache()

            self._apply_filter()
            logger.debug("ImageModel loaded %d files", len(self._all_files))

            # Start background color extraction
            self._start_color_scanner()
        finally:
            self._loading = False
            self.loadingChanged.emit()

    def _start_color_scanner(self) -> None:
        if not self._all_files:
            return

        self._cleanup_color_worker()

        worker = ColorScannerWorker(self._all_files)
        worker.progress.connect(self._on_color_progress)
        worker.finished.connect(self._on_color_done)
        thread = start_worker_thread(worker)

        self._color_worker = worker
        self._color_worker_thread = thread

    @Slot(str, list, list)
    def _on_color_progress(self, path: str, colors: list, categories: list) -> None:
        self._color_cache[path] = {"colors": colors, "categories": categories}

    @Slot()
    def _on_color_done(self) -> None:
        # Reapply filter when background scanning completes
        if self._color_filter:
            self._apply_filter()

    def updateCachedCategories(self, path: str, categories: list) -> None:
        """Keep the in-memory color cache in sync after a manual category edit.

        Called from Controller.updateWallpaperCategories() once the on-disk
        cache has been updated, so color-filter chips reflect the change
        immediately without needing to rescan.
        """
        entry = self._color_cache.get(path)
        if not isinstance(entry, dict):
            entry = {"colors": []}
        entry["categories"] = list(categories)
        self._color_cache[path] = entry
        if self._color_filter:
            self._apply_filter()
