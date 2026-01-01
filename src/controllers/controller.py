from __future__ import annotations

from typing import Optional
import logging

from PySide6.QtCore import QObject, Slot, Signal, Property

from models.models import WallpaperFolderModel, Folder


class Controller(QObject):
	"""Controller that bridges Python models and QML UI."""

	selectedFolderChanged = Signal()

	def __init__(self, parent: Optional[QObject] = None):
		super().__init__(parent)
		self._model = WallpaperFolderModel([Folder(name="Local", path="/usr/share/wallpapers")])
		self._logger = logging.getLogger(__name__)
		self._selected_folder: str = ""
		# Select the first folder by default if available
		if self._model.rowCount() > 0:
			# use selectFolder to ensure notify signal is emitted
			self.selectFolder(0)

	def wallpaperModel(self) -> WallpaperFolderModel:
		return self._model

	@Slot(str, str)
	def addFolder(self, name: str, path: str) -> None:
		self._logger.debug("addFolder called: %s %s", name, path)
		self._model.addFolder(name, path)

	@Slot(int)
	def removeFolder(self, index: int) -> None:
		self._logger.debug("removeFolder called: %r (type=%s); model_count=%d", index, type(index), self._model.rowCount())
		# Defensive: try to coerce index to int if QML passes a string
		try:
			idx = int(index)
		except Exception:
			self._logger.exception("Invalid index received for removeFolder: %r", index)
			return
		self._model.removeFolder(idx)

	@Slot(int)
	def selectFolder(self, index: int) -> None:
		"""Select a folder by model index and notify QML."""
		try:
			if 0 <= index < len(self._model._folders):
				folder = self._model._folders[index]
				self._selected_folder = folder.path
				self._logger.debug("Selected folder set to %s", self._selected_folder)
				self.selectedFolderChanged.emit()
		except Exception:
			self._logger.exception("Error selecting folder")

	def _get_selected_folder(self) -> str:
		return self._selected_folder

	selectedFolder = Property(str, _get_selected_folder, notify=selectedFolderChanged)
