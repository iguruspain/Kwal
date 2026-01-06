from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import logging
from pathlib import Path
import hashlib
import os
import shutil
from PySide6.QtGui import QImage
from PySide6.QtCore import QObject, Signal, Slot, QThread, Property

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Slot


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
		# If title not provided, derive it from app_name (capitalize)
		if not self.title:
			# Keep title human-friendly by capitalizing the app_name
			self.title = self.app_name.capitalize()


class WallpaperFolderModel(QAbstractListModel):
	NameRole = Qt.UserRole + 1
	PathRole = Qt.UserRole + 2

	def __init__(self, folders: List[Folder] | None = None, parent=None):
		super().__init__(parent)
		self._folders: List[Folder] = folders or []

	def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
		return len(self._folders)

	def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
		if not index.isValid() or index.row() < 0 or index.row() >= self.rowCount():
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
		logging.getLogger(__name__).debug("Adding folder %s %s", name, path)
		self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
		self._folders.append(Folder(name=name, path=path))
		self.endInsertRows()

	@Slot(int)
	def removeFolder(self, index: int) -> None:
		logger = logging.getLogger(__name__)
		logger.debug("removeFolder called with index=%d; rowCount=%d", index, self.rowCount())
		if 0 <= index < self.rowCount():
			# determine which folder will be removed
			removed = self._folders[index]
			# attempt to clear thumbnail cache for that folder
			try:
				self._clear_cache_for_folder(removed.path)
			except Exception:
				logger.exception("Failed clearing cache for folder %s", removed.path)
			# remove from model
			self.beginRemoveRows(QModelIndex(), index, index)
			del self._folders[index]
			self.endRemoveRows()
			logger.info("Removed folder %s; remaining=%s", removed, [(f.name, f.path) for f in self._folders])
		else:
			logger.warning("removeFolder: invalid index %s", index)

	def _clear_cache_for_folder(self, folder_path: str) -> None:
		"""Remove thumbnail cache files that belong to a given folder path."""
		logger = logging.getLogger(__name__)
		p = Path(folder_path)
		# Even if folder doesn't exist on disk anymore, we might have cache
		cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "kwal" / "thumbnails"
		# folder-specific cache dir is the sha1 of the folder path
		folder_digest = hashlib.sha1(str(p).encode("utf-8")).hexdigest()
		folder_cache = cache_root / folder_digest
		if not folder_cache.exists():
			logger.debug("_clear_cache_for_folder: no cache directory for folder %s", folder_cache)
			return
		# remove the entire folder cache tree
		try:
			shutil.rmtree(folder_cache)
			logger.info("Cleared thumbnail cache directory %s for folder %s", folder_cache, folder_path)
		except Exception:
			logger.exception("Failed to remove cache directory %s", folder_cache)


class ThumbnailWorker(QObject):
	finished = Signal(list, list)

	def __init__(self, folder_path: str, parent: Optional[QObject] = None):
		super().__init__(parent)
		self.folder_path = folder_path
		self._stopped = False

	@Slot()
	def process(self) -> None:
		logger = logging.getLogger(__name__)
		try:
			p = Path(self.folder_path)
			if not p.exists() or not p.is_dir():
				logger.warning("ThumbnailWorker: invalid folder %s", self.folder_path)
				self.finished.emit([], [])
				return

			exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
			files = []
			for f in sorted(p.rglob("*")):
				if not f.is_file():
					continue
				if f.suffix.lower() not in exts:
					continue
				sf = str(f)
				name_lower = f.name.lower()
				# Exclude preview and screenshot images and any in /previews/ folders
				if "/previews/" in sf or "screenshot" in name_lower or "preview" in name_lower:
					continue
				files.append(f)

			# Organize thumbnails per-source-folder to make cleanup simple
			cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "kwal" / "thumbnails"
			folder_digest = hashlib.sha1(str(p).encode("utf-8")).hexdigest()
			cache_base = cache_root / folder_digest
			cache_base.mkdir(parents=True, exist_ok=True)

			thumbs: List[str] = []
			THUMB_W = 320
			THUMB_H = 240
			for f in files:
				if self._stopped:
					break
				digest = hashlib.sha1(str(f).encode("utf-8")).hexdigest()
				thumb_path = cache_base / (digest + ".png")
				if not thumb_path.exists():
					try:
						img = QImage(str(f))
						if img.isNull():
							logger.debug("Skipping unreadable image %s", f)
							thumbs.append("")
							continue
						scaled = img.scaled(THUMB_W, THUMB_H, Qt.KeepAspectRatio, Qt.SmoothTransformation)
						scaled.save(str(thumb_path))
					except Exception:
						logger.exception("Failed creating thumbnail for %s", f)
						thumbs.append("")
						continue
				thumbs.append(str(thumb_path))

			self.finished.emit([str(x) for x in files], thumbs)
		except Exception:
			logger.exception("ThumbnailWorker failed for %s", self.folder_path)
			self.finished.emit([], [])


class FastfetchTintWorker(QObject):
	"""Worker to generate a tinted image off the main thread."""
	finished = Signal(str)

	def __init__(self, src: str, tint_hex: str, strength: float = 0.8, parent: Optional[QObject] = None):
		super().__init__(parent)
		self.src = src
		self.tint_hex = tint_hex
		self.strength = strength

	@Slot()
	def process(self) -> None:
		logger = logging.getLogger(__name__)
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

	def __init__(self, parent=None):
		super().__init__(parent)
		self._files: List[Path] = []
		self._thumbs: List[str] = []
		self._worker_thread: Optional[QThread] = None
		self._worker: Optional[ThumbnailWorker] = None
		self._loading: bool = False

	def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
		return len(self._files)

	def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
		if not index.isValid() or index.row() < 0 or index.row() >= self.rowCount():
			return None
		p = self._files[index.row()]
		if role == ImageModel.FileNameRole:
			return Path(p).name
		if role == ImageModel.FilePathRole:
			return str(p)
		if role == ImageModel.ThumbnailRole:
			try:
				return self._thumbs[index.row()]
			except Exception:
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
		# Stop worker safely, guarding against threads already deleted
		if self._worker:
			try:
				self._worker._stopped = True
			except Exception:
				pass
			self._worker = None
		if self._worker_thread:
			try:
				# only attempt to quit/wait if thread thinks it's running
				if hasattr(self._worker_thread, "isRunning") and self._worker_thread.isRunning():
					self._worker_thread.quit()
					self._worker_thread.wait(1000)
			except RuntimeError:
				# thread object was already deleted at C++ level; ignore
				pass
			finally:
				self._worker_thread = None

	def setFolder(self, folder_path: str) -> None:
		logger = logging.getLogger(__name__)
		# stop any existing worker
		self._cleanup_worker()

		# clear current model immediately and set loading state
		self.beginResetModel()
		self._files = []
		self._thumbs = []
		self.endResetModel()
		self._loading = True
		self.loadingChanged.emit()

		if not folder_path:
			self._loading = False
			self.loadingChanged.emit()
			return

		# start background worker
		thread = QThread()
		worker = ThumbnailWorker(folder_path)
		worker.moveToThread(thread)
		thread.started.connect(worker.process)
		worker.finished.connect(self._on_worker_done)
		worker.finished.connect(thread.quit)
		thread.finished.connect(worker.deleteLater)
		thread.finished.connect(thread.deleteLater)
		self._worker = worker
		self._worker_thread = thread
		thread.start()

	@Slot(list, list)
	def _on_worker_done(self, files: list, thumbs: list) -> None:
		logger = logging.getLogger(__name__)
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

	def __init__(self, apps: List[SettingsApp] | None = None, parent: Optional[QObject] = None):
		super().__init__(parent)
		self._apps = apps or []

	def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
		return len(self._apps)

	def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
		if not index.isValid() or index.row() < 0 or index.row() >= self.rowCount():
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
		default_flags = super().flags(index)
		if index.isValid():
			return default_flags | Qt.ItemIsDragEnabled
		return default_flags

	@Slot(int, result="QVariantMap")
	def get(self, row: int) -> dict:
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
		
		# Calculate destination for beginMoveRows
		# When moving down (source < destination), the item is removed first, 
		# so the insertion index in the *original* list (which beginMoveRows expects as destinationChild)
		# needs to be destination + 1.
		qt_dest = destination + 1 if source < destination else destination
		
		if self.beginMoveRows(QModelIndex(), source, source, QModelIndex(), qt_dest):
			item = self._apps.pop(source)
			self._apps.insert(destination, item)
			self.endMoveRows()


class FastfetchTemplateModel(QAbstractListModel):
	FileNameRole = Qt.UserRole + 1
	FilePathRole = Qt.UserRole + 2
	FileUrlRole = Qt.UserRole + 3

	def __init__(self, parent: Optional[QObject] = None):
		super().__init__(parent)
		self._files: List[Path] = []

	def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
		return len(self._files)

	def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
		if not index.isValid() or index.row() < 0 or index.row() >= self.rowCount():
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
		"""Populate model from a folder path. If folder_path is None or empty, clears the model."""
		logger = logging.getLogger(__name__)
		try:
			if not folder_path:
				self.beginResetModel()
				self._files = []
				self.endResetModel()
				return
			from ..utils.file_utils import list_template_images

			files = list_template_images(folder_path)
			self.beginResetModel()
			self._files = [Path(x) for x in files]
			self.endResetModel()
			logger.debug("FastfetchTemplateModel refreshed %d files from %s", len(self._files), folder_path)
		except Exception:
			logger.exception("Failed refreshing FastfetchTemplateModel for %s", folder_path)

	@Slot(int, result="QVariantMap")
	def get(self, row: int) -> dict:
		if 0 <= row < self.rowCount():
			p = self._files[row]
			return {"fileName": p.name, "filePath": str(p), "fileUrl": "file://" + str(p)}
		return {}
