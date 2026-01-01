from __future__ import annotations

from typing import Optional
import logging
import os

from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import QObject, Slot, Signal, Property, QCoreApplication, QStandardPaths

from models.models import WallpaperFolderModel, Folder, ImageModel


class Controller(QObject):
	"""Controller that bridges Python models and QML UI."""

	selectedFolderChanged = Signal()

	def __init__(self, parent: Optional[QObject] = None):
		super().__init__(parent)
		self._model = WallpaperFolderModel([Folder(name="Local", path="/usr/share/wallpapers")])
		self._image_model = ImageModel()
		self._logger = logging.getLogger(__name__)
		self._selected_folder: str = ""
		# Select the first folder by default if available
		if self._model.rowCount() > 0 and QCoreApplication.instance() is not None:
			# use selectFolder to ensure notify signal is emitted
			self.selectFolder(0)

	def wallpaperModel(self) -> WallpaperFolderModel:
		return self._model

	def imageModel(self) -> ImageModel:
		return self._image_model

	@Slot(str, str)
	def addFolder(self, name: str, path: str) -> None:
		self._logger.debug(QCoreApplication.translate("Controller", "addFolder called: %s %s"), name, path)
		self._model.addFolder(name, path)

	@Slot()
	def openFolderDialog(self) -> None:
		"""Open a native folder selection dialog and add the chosen folder to the model.
		The folder's display name is derived from the folder basename.
		"""
		try:
			self._logger.debug(QCoreApplication.translate("Controller", "Opening folder selection dialog"))
			# determine sensible initial directory: user's Pictures location (localized by the system)
			initial_dir = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
			if not initial_dir:
				initial_dir = os.path.expanduser("~")
			# This shows a native dialog and returns an empty string if cancelled
			selected = QFileDialog.getExistingDirectory(None, QCoreApplication.translate("Controller", "Select Folder"), initial_dir)
			if selected:
				name = os.path.basename(selected) or selected
				self.addFolder(name, selected)
				self._logger.info(QCoreApplication.translate("Controller", "Added folder %s -> %s"), name, selected)
			else:
				self._logger.debug(QCoreApplication.translate("Controller", "Folder selection cancelled or no folder chosen"))
		except Exception:
			self._logger.exception(QCoreApplication.translate("Controller", "Failed to open folder dialog or add folder"))

	@Slot(int)
	def removeFolder(self, index: int) -> None:
		self._logger.debug(QCoreApplication.translate("Controller", "removeFolder called: %r (type=%s); model_count=%d"), index, type(index), self._model.rowCount())
		# Defensive: try to coerce index to int if QML passes a string
		try:
			idx = int(index)
		except Exception:
			self._logger.exception(QCoreApplication.translate("Controller", "Invalid index received for removeFolder: %r"), index)
			return
		self._model.removeFolder(idx)

	@Slot(int)
	def selectFolder(self, index: int) -> None:
		"""Select a folder by model index and notify QML."""
		try:
			if 0 <= index < len(self._model._folders):
				folder = self._model._folders[index]
				self._selected_folder = folder.path
				self._logger.debug(QCoreApplication.translate("Controller", "Selected folder set to %s"), self._selected_folder)
				# update image model for the selected folder
				self._image_model.setFolder(self._selected_folder)
				self.selectedFolderChanged.emit()
		except Exception:
			self._logger.exception(QCoreApplication.translate("Controller", "Error selecting folder"))

	def _get_selected_folder(self) -> str:
		return self._selected_folder

	selectedFolder = Property(str, _get_selected_folder, notify=selectedFolderChanged)
