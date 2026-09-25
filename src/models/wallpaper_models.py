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

    @Slot(int, str)
    def renameFolder(self, index: int, new_name: str) -> None:
        """Rename the folder at *index* to *new_name* and notify the view."""
        if not new_name or not (0 <= index < self.rowCount()):
            return
        self._folders[index].name = new_name
        model_index = self.index(index)
        self.dataChanged.emit(model_index, model_index, [WallpaperFolderModel.NameRole])
        logger.info("Renamed folder at index %d to '%s'", index, new_name)

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

        self._rescan_worker: ImageScannerWorker | None = None
        self._rescan_thread: QThread | None = None
        self._rescanning: bool = False
        self._rescan_generation: int = 0

        self._folder_path: str = ""

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

    def _compute_filtered_files(self) -> list[Path]:
        """Return the subset of _all_files matching the text and color filters."""
        result: list[Path] = []
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

            result.append(f)
        return result

    def _apply_filter(self) -> None:
        self.beginResetModel()
        self._files = self._compute_filtered_files()
        self.endResetModel()

    @Slot()
    def rescan(self) -> None:
        """Re-scan the current folder and update the grid incrementally.

        Triggered by the file-system watcher when files are added, removed or
        renamed on disk. Does not reset the model or touch the loading flag,
        so the view keeps its scroll position and selection.
        """
        if self._rescanning or not self._folder_path:
            return

        self._rescanning = True
        generation = self._rescan_generation
        worker = ImageScannerWorker(self._folder_path)
        worker.finished.connect(lambda files, gen=generation: self._on_rescan_done(files, gen))
        thread = start_worker_thread(worker)
        thread.finished.connect(lambda t=thread: self._release_thread_ref("_rescan_thread", t))

        self._rescan_worker = worker
        self._rescan_thread = thread

    def _cleanup_rescan_worker(self) -> None:
        self._stop_worker_pair("_rescan_worker", "_rescan_thread")
        self._rescanning = False

    @Slot(list, int)
    def _on_rescan_done(self, files: list[str], generation: int) -> None:
        try:
            # A newer scan (or folder switch) superseded this one
            if generation != self._rescan_generation:
                return

            new_all = [Path(x) for x in files]
            old_set = {str(f) for f in self._all_files}
            new_set = {str(f) for f in new_all}
            added = [f for f in new_all if str(f) not in old_set]
            removed = [f for f in self._all_files if str(f) not in new_set]

            if not added and not removed:
                return

            self._all_files = new_all
            # Drop color-cache entries of removed files so a re-added file
            # with the same name is re-extracted instead of reusing stale data
            for f in removed:
                self._color_cache.pop(str(f), None)
            # _files keeps the old list while _sync_view transforms it in place
            self._sync_view(self._compute_filtered_files())

            # Extract colors for newly added files so color filters work on them
            if added:
                self._start_color_scanner(added)

            logger.debug("ImageModel rescan: +%d -%d files", len(added), len(removed))
        finally:
            self._rescanning = False
            self._rescan_worker = None
            # The thread reference is released by its finished signal

    def _sync_view(self, target_files: list[Path]) -> None:
        """Transform _files into target_files, notifying the view via a full reset.

        A full reset is safe and correct: the previous LCS-based diff was
        calling beginRemoveRows(0, n-1) while only deleting a subset of rows,
        which violates the Qt model contract and caused the view to show
        'No wallpapers found' after any on-disk deletion.
        """
        old = [str(f) for f in self._files]
        new = [str(f) for f in target_files]
        if old == new:
            return

        self.beginResetModel()
        self._files = list(target_files)
        self.endResetModel()

    def _stop_worker_pair(self, worker_attr: str, thread_attr: str) -> None:
        """Stop a worker and release its thread reference safely.

        If the thread is still running after the wait (e.g. a slow color
        extraction blocked its event loop), the reference is kept until the
        thread's finished signal releases it, so the QThread is never
        destroyed while its thread is still running.
        """
        worker = getattr(self, worker_attr)
        if worker:
            try:
                worker._stopped = True
            except Exception:
                pass
            setattr(self, worker_attr, None)

        thread = getattr(self, thread_attr)
        if thread:
            try:
                if shiboken.isValid(thread) and thread.isRunning():
                    thread.quit()
                    thread.wait(1000)
            except RuntimeError:
                pass
            try:
                still_running = shiboken.isValid(thread) and thread.isRunning()
            except RuntimeError:
                still_running = False
            if not still_running:
                setattr(self, thread_attr, None)

    def _release_thread_ref(self, attr: str, thread: QThread) -> None:
        """Drop a stored thread reference once its thread has actually finished."""
        if getattr(self, attr) is thread:
            setattr(self, attr, None)

    def _cleanup_worker(self) -> None:
        self._stop_worker_pair("_worker", "_worker_thread")

    def _cleanup_color_worker(self) -> None:
        self._stop_worker_pair("_color_worker", "_color_worker_thread")

    def setFolder(self, folder_path: str) -> None:
        self._cleanup_worker()
        self._cleanup_color_worker()
        self._cleanup_rescan_worker()
        self._rescan_generation += 1

        self.beginResetModel()
        self._all_files.clear()
        self._files.clear()
        self.endResetModel()

        self._folder_path = folder_path

        self._loading = True
        self.loadingChanged.emit()

        if not folder_path:
            self._loading = False
            self.loadingChanged.emit()
            return

        worker = ImageScannerWorker(folder_path)
        worker.finished.connect(self._on_worker_done)
        thread = start_worker_thread(worker)
        thread.finished.connect(lambda t=thread: self._release_thread_ref("_worker_thread", t))

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

    def _start_color_scanner(self, files: list[Path] | None = None) -> None:
        targets = files if files is not None else self._all_files
        if not targets:
            return

        self._cleanup_color_worker()

        worker = ColorScannerWorker(targets)
        worker.progress.connect(self._on_color_progress)
        worker.finished.connect(self._on_color_done)
        thread = start_worker_thread(worker)
        thread.finished.connect(lambda t=thread: self._release_thread_ref("_color_worker_thread", t))

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
