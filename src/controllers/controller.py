from __future__ import annotations

from typing import Optional
import logging
import os
import json

from PySide6.QtWidgets import QFileDialog
from PySide6.QtCore import QObject, Slot, Signal, Property, QCoreApplication, QStandardPaths

from models.models import WallpaperFolderModel, Folder, ImageModel


class Controller(QObject):
	"""Controller that bridges Python models and QML UI."""

	selectedFolderChanged = Signal()
	selectedWallpaperChanged = Signal()

	def __init__(self, parent: Optional[QObject] = None):
		super().__init__(parent)
		# Load persisted folders or fallback to default
		folders: list[Folder] = []
		try:
			loaded = self._load_config()
			if loaded:
				folders = [Folder(name=f.get("name", ""), path=f.get("path", "")) for f in loaded]
		except Exception:
			self._logger = logging.getLogger(__name__)
			self._logger.exception("Failed loading saved folders; using defaults")
		if not folders:
			folders = [Folder(name="Local", path="/usr/share/wallpapers")]
		self._model = WallpaperFolderModel(folders)
		self._image_model = ImageModel()
		self._logger = logging.getLogger(__name__)
		self._selected_folder: str = ""
		self._selected_wallpaper: str = ""
		# Select the first folder by default if available
		if self._model.rowCount() > 0 and QCoreApplication.instance() is not None:
			# use selectFolder to ensure notify signal is emitted
			self.selectFolder(0)

	def wallpaperModel(self) -> WallpaperFolderModel:
		return self._model

	def imageModel(self) -> ImageModel:
		return self._image_model

	@Slot(str)
	def selectWallpaper(self, path: str) -> None:
		if self._selected_wallpaper != path:
			self._selected_wallpaper = path
			self.selectedWallpaperChanged.emit()

	def _get_selected_wallpaper(self) -> str:
		return self._selected_wallpaper

	selectedWallpaper = Property(str, _get_selected_wallpaper, notify=selectedWallpaperChanged)

	@Slot(str, str)
	def addFolder(self, name: str, path: str) -> None:
		self._logger.debug(QCoreApplication.translate("Controller", "addFolder called: %s %s"), name, path)
		# avoid duplicates by path
		for f in self._model._folders:
			if f.path == path:
				self._logger.info("Folder %s already present, skipping add", path)
				return
		self._model.addFolder(name, path)
		# persist
		try:
			self._save_config()
		except Exception:
			self._logger.exception("Failed saving config after addFolder")

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
		# perform removal and persist
		self._model.removeFolder(idx)
		try:
			self._save_config()
		except Exception:
			self._logger.exception("Failed saving config after removeFolder")

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

	def _config_path(self) -> Path:
		from pathlib import Path
		cfg_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kwal"
		cfg_dir.mkdir(parents=True, exist_ok=True)
		return cfg_dir / "folders.json"

	def _load_config(self) -> list[dict]:
		"""Load persisted folders list from config file. Returns list of dicts.
		If file missing or invalid, returns empty list.
		"""
		cfg = self._config_path()
		if not cfg.exists():
			return []
		try:
			with open(cfg, "r", encoding="utf-8") as fh:
				return json.load(fh)
		except Exception:
			self._logger.exception("Failed reading config file %s", cfg)
			return []

	def _save_config(self) -> None:
		"""Save current folder list into config file as JSON.
		Format: [{"name": str, "path": str}, ...]
		"""
		cfg = self._config_path()
		data = [{"name": f.name, "path": f.path} for f in self._model._folders]
		with open(cfg, "w", encoding="utf-8") as fh:
			json.dump(data, fh, ensure_ascii=False, indent=2)

	selectedFolder = Property(str, _get_selected_folder, notify=selectedFolderChanged)
