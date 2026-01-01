from __future__ import annotations

from dataclasses import dataclass
from typing import List
import logging

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Slot


@dataclass
class Folder:
	name: str
	path: str


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
			self.beginRemoveRows(QModelIndex(), index, index)
			removed = self._folders[index]
			del self._folders[index]
			self.endRemoveRows()
			logger.info("Removed folder %s; remaining=%s", removed, [(f.name, f.path) for f in self._folders])
		else:
			logger.warning("removeFolder: invalid index %s", index)
