from __future__ import annotations

from typing import Optional
import logging
import os
import json

from PySide6.QtWidgets import QFileDialog
from PySide6.QtGui import QImage
from PySide6.QtCore import QObject, Slot, Signal, Property, QCoreApplication, QStandardPaths
import subprocess
import shutil

from models.models import WallpaperFolderModel, Folder, ImageModel


class Controller(QObject):
	"""Controller that bridges Python models and QML UI."""

	selectedFolderChanged = Signal()
	selectedWallpaperChanged = Signal()

	def __init__(self, parent: Optional[QObject] = None):
		super().__init__(parent)
		self._logger = logging.getLogger(__name__)
		self._selected_folder: str = ""
		self._selected_wallpaper: str = ""
		self._last_set_wallpaper: str = ""
		self._selected_wallpaper_resolution: str = ""

		# Load persisted config
		config = self._load_config()
		loaded_folders = config.get("folders", [])
		last_selected = config.get("selected_folder", "")
		# restore last explicitly set wallpaper if present
		self._last_set_wallpaper = config.get("last_set_wallpaper", "")

		folders: list[Folder] = []
		if loaded_folders:
			folders = [Folder(name=f.get("name", ""), path=f.get("path", "")) for f in loaded_folders]
		
		if not folders:
			folders = [Folder(name="Local", path="/usr/share/wallpapers")]
			
		self._model = WallpaperFolderModel(folders)
		self._image_model = ImageModel()

		# Restore selection or default to first
		initial_index = 0
		if last_selected:
			for i, f in enumerate(folders):
				if f.path == last_selected:
					initial_index = i
					break
		
		if self._model.rowCount() > 0 and QCoreApplication.instance() is not None:
			self.selectFolder(initial_index)

	def wallpaperModel(self) -> WallpaperFolderModel:
		return self._model

	def imageModel(self) -> ImageModel:
		return self._image_model

	@Slot(str)
	def selectWallpaper(self, path: str) -> None:
		# Set selected wallpaper and compute its resolution
		try:
			if self._selected_wallpaper != path:
				self._selected_wallpaper = path
				# compute resolution
				if path:
					img = QImage(path)
					if not img.isNull():
						self._selected_wallpaper_resolution = f"{img.width()}x{img.height()}"
					else:
						self._selected_wallpaper_resolution = ""
				else:
					self._selected_wallpaper_resolution = ""
				self.selectedWallpaperChanged.emit()
		except Exception:
			self._logger.exception("Error selecting wallpaper %r", path)

	def _get_selected_wallpaper(self) -> str:
		return self._selected_wallpaper

	def _get_selected_wallpaper_resolution(self) -> str:
		return self._selected_wallpaper_resolution

	selectedWallpaper = Property(str, _get_selected_wallpaper, notify=selectedWallpaperChanged)

	@Slot(str)
	def setAsWallpaper(self, path: str) -> None:
		"""Record the chosen wallpaper and persist it. This is a best-effort helper;
		actual desktop wallpaper integration is platform-specific and not implemented here.
		"""
		if not path:
			self._logger.warning("setAsWallpaper called with empty path")
			return
		# normalize path
		path = os.path.abspath(path)
		if not os.path.exists(path):
			self._logger.error("Wallpaper path does not exist: %s", path)
			return
		self._last_set_wallpaper = path
		self._logger.info("Marked %s as last set wallpaper (attempting to apply)", path)
		# Try KDE Plasma via qdbus/org.kde.plasmashell
		qdbus_path = shutil.which("qdbus")
		if qdbus_path:
			# JS to apply wallpaper to all desktops
			script = (
				"var allDesktops = desktops();\n"
				"for (var i = 0; i < allDesktops.length; i++) {\n"
				"  var d = allDesktops[i];\n"
				"  d.wallpaperPlugin = 'org.kde.image';\n"
				"  d.currentConfigGroup = Array('Wallpaper','org.kde.image','General');\n"
				f"  d.writeConfig('Image', 'file://{path}');\n"
				"}\n"
			)
			try:
				res = subprocess.run([qdbus_path, "org.kde.plasmashell", "/PlasmaShell", "org.kde.PlasmaShell.evaluateScript", script], capture_output=True, text=True, check=False)
				if res.returncode == 0:
					self._logger.info("Wallpaper applied via plasmashell/qdbus")
				else:
					self._logger.warning("qdbus returned code %s; stdout=%s stderr=%s", res.returncode, res.stdout, res.stderr)
			except Exception:
				self._logger.exception("Failed to call qdbus to set wallpaper")
		else:
			self._logger.warning("qdbus not found; cannot apply wallpaper programmatically on KDE Plasma")
		# persist the chosen wallpaper path alongside folders/selection
		try:
			self._save_config()
		except Exception:
			self._logger.exception("Failed saving config after setAsWallpaper")

	selectedWallpaperResolution = Property(str, _get_selected_wallpaper_resolution, notify=selectedWallpaperChanged)

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
		
		# Check if we are removing the currently selected folder
		folder_to_remove = self._model._folders[idx] if 0 <= idx < self._model.rowCount() else None
		was_selected = (folder_to_remove is not None and folder_to_remove.path == self._selected_folder)

		# perform removal
		self._model.removeFolder(idx)
		
		# Handle selection update if needed
		if was_selected:
			new_count = self._model.rowCount()
			if new_count > 0:
				# Select the same index if it still exists, or the last one
				new_index = min(idx, new_count - 1)
				self.selectFolder(new_index)
			else:
				# No folders left
				self._selected_folder = ""
				self._image_model.setFolder("")
				self.selectedFolderChanged.emit()
		
		# persist
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
				self._save_config()
		except Exception:
			self._logger.exception(QCoreApplication.translate("Controller", "Error selecting folder"))

	def _get_selected_folder(self) -> str:
		return self._selected_folder

	def _config_path(self) -> Path:
		from pathlib import Path
		cfg_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kwal"
		cfg_dir.mkdir(parents=True, exist_ok=True)
		return cfg_dir / "folders.json"

	def _load_config(self) -> dict:
		"""Load persisted config. Returns dict with keys 'folders' (list) and 'selected_folder' (str)."""
		cfg = self._config_path()
		default_config = {"folders": [], "selected_folder": ""}
		if not cfg.exists():
			return default_config
		try:
			with open(cfg, "r", encoding="utf-8") as fh:
				data = json.load(fh)
				if isinstance(data, list):
					# Migration from old list-only format
					return {"folders": data, "selected_folder": ""}
				if isinstance(data, dict):
					return data
				return default_config
		except Exception:
			self._logger.exception("Failed reading config file %s", cfg)
			return default_config

	def _save_config(self) -> None:
		"""Save current state into config file."""
		cfg = self._config_path()
		data = {
			"folders": [{"name": f.name, "path": f.path} for f in self._model._folders],
			"selected_folder": self._selected_folder
		}
		# persist last explicit wallpaper if available
		if self._last_set_wallpaper:
			data["last_set_wallpaper"] = self._last_set_wallpaper
		with open(cfg, "w", encoding="utf-8") as fh:
			json.dump(data, fh, ensure_ascii=False, indent=2)

	selectedFolder = Property(str, _get_selected_folder, notify=selectedFolderChanged)
