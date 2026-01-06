from __future__ import annotations

from typing import Optional
import logging
import os
import json
import subprocess
import shutil
from pathlib import Path
from PySide6.QtWidgets import QFileDialog,QColorDialog
from PySide6.QtGui import QImage, QColor
from PySide6.QtCore import QObject, Slot, Signal, Property, QCoreApplication, QStandardPaths, QThread
import threading


from ..models.models import WallpaperFolderModel, Folder, ImageModel, SettingsAppModel, SettingsApp, FastfetchTemplateModel
from ..utils import color_utils, file_utils


class Controller(QObject):
	"""Controller that bridges Python models and QML UI."""

	selectedFolderChanged = Signal()
	selectedWallpaperChanged = Signal()
	templatesInstalledChanged = Signal()
	selectedFileChanged = Signal()
	fastfetchTintedPreviewChanged = Signal()
	fastfetchTintingChanged = Signal()
	tintResult = Signal(str)

	def __init__(self, parent: Optional[QObject] = None):
		super().__init__(parent)
		self._logger = logging.getLogger(__name__)
		self._selected_folder: str = ""
		self._selected_wallpaper: str = ""
		self._last_set_wallpaper: str = ""
		self._selected_wallpaper_resolution: str = ""
		self._selected_file: str = ""

		# expose home path for QML convenience (ensure trailing slash)
		self._home_path: str = str(Path.home()).rstrip("/") + "/"

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

		# Fastfetch template model (populated from user templates folder)
		self._fastfetch_model = FastfetchTemplateModel()
		# default templates folder (user XDG location)
		self._fastfetch_templates_folder = str(Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kwal" / "templates" / "fastfetch")
		# attempt initial refresh (non-fatal)
		try:
			self._fastfetch_model.refresh(self._fastfetch_templates_folder)
		except Exception:
			self._logger.debug("Initial fastfetch template refresh failed or empty")

		self._fastfetch_tinted_preview: str = ""
		self._fastfetch_tinting: bool = False
		self._tint_worker: Optional[object] = None
		self._tint_thread: Optional[QThread] = None
		# connect tint result signal (used by background Python thread)
		self.tintResult.connect(self._on_tint_done)

		# templates installed flag
		self._templates_installed = self._check_templates_installed()

		# Initialize Settings App Model
		apps = [
			SettingsApp(app_name="fastfetch", section="Apps", qml_page="apps/fastfetch.qml"),
			SettingsApp(app_name="starship", section="Apps", qml_page="apps/starship.qml"),
			SettingsApp(app_name="ulauncher", section="Apps", qml_page="apps/ulauncher.qml"),
		]
		self._settings_app_model = SettingsAppModel(apps)

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

	def fastfetchTemplateModel(self) -> FastfetchTemplateModel:
		return self._fastfetch_model

	@Property(QObject, constant=True)
	def settingsAppModel(self) -> SettingsAppModel:
		return self._settings_app_model

	@Slot(result=str)
	def longestSettingsTitle(self) -> str:
		"""Return the longest settings app title (by character count)."""
		try:
			apps_model = getattr(self, "_settings_app_model", None)
			if apps_model is None:
				return ""
			apps = getattr(apps_model, "_apps", []) or []
			longest = ""
			for a in apps:
				t = getattr(a, "title", "") or ""
				if len(t) > len(longest):
					longest = t
			return longest
		except Exception:
			self._logger.exception("Error computing longest settings title")
			return ""

	def _get_home_path(self) -> str:
		return self._home_path

	# homePath is immutable for the lifetime of the app -> mark as constant to avoid binding warnings
	homePath = Property(str, _get_home_path, constant=True)

	def imageModel(self) -> ImageModel:
		return self._image_model

	@Slot(result=bool)
	def templatesInstalled(self) -> bool:
		"""Return True if user templates are present in XDG config."""
		return self._templates_installed

	@Slot(result=bool)
	def _check_templates_installed(self) -> bool:
		cfg_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "kwal" / "templates"
		try:
			return cfg_dir.exists() and any(cfg_dir.iterdir())
		except Exception:
			return False

	@Slot(result=bool)
	def installTemplates(self) -> bool:
		"""Attempt to install packaged templates to user's XDG config.
		Returns True on success.
		"""
		try:
			from ..utils.setup import install_templates_to_user
			install_templates_to_user()
			self._templates_installed = self._check_templates_installed()
			self.templatesInstalledChanged.emit()
			return self._templates_installed

		except Exception:
			self._logger.exception("Failed to install templates")
			return False

	@Slot(str, str, result=str)
	def generateTintedPreview(self, src: str, tint_hex: str, strength: float = 0.8) -> str:
		"""Generate a tinted preview from `src` using color_utils and return a file:// URL."""
		# accept file:// URIs and plain paths
		if src.startswith("file://"):
			src_path = src.replace("file://", "")
		else:
			src_path = src

		# Do not tint if tint_hex is empty, 'transparent' or invalid
		try:
			if not tint_hex or str(tint_hex).lower() == "transparent" or not QColor.isValidColor(tint_hex):
				# clear any existing tinted preview and return empty so QML shows original
				self._fastfetch_tinted_preview = ""
				self.fastfetchTintedPreviewChanged.emit()
				self._logger.info("generateTintedPreview: skipping tint generation for invalid/transparent color %r", tint_hex)
				return ""
		except Exception:
			# If QColor check fails for any reason, fallback to no-tint and log
			self._logger.info("generateTintedPreview: QColor validation error for %r, skipping tint", tint_hex)
			self._logger.debug("generateTintedPreview: QColor validation failed for %r", tint_hex)
			self._fastfetch_tinted_preview = ""
			self.fastfetchTintedPreviewChanged.emit()
			return ""

		# start background Python thread to run tint_image (avoids QThread lifetime issues)
		try:
			def _run_tint(s: str, t: str, st: float) -> None:
				try:
					from ..utils import color_utils as _cu
					res = _cu.tint_image(s, t, float(st))
					# emit result back to main thread via signal; emit from this thread is safe (queued)
					self.tintResult.emit(res if res else "")
				except Exception:
					self._logger.exception("Background tint failed for %s", s)
					self.tintResult.emit("")

			# set tinting flag and start thread
			self._fastfetch_tinting = True
			self.fastfetchTintingChanged.emit()
			thr = threading.Thread(target=_run_tint, args=(src_path, tint_hex, float(strength)), daemon=True)
			thr.start()
			# store reference so it isn't GC'd (optional)
			self._tint_thread = thr
			return ""
		except Exception:
			self._logger.exception("Failed starting background tint thread for %s", src)
			return ""

	@Slot(str)
	def refreshFastfetchTemplates(self, folder: str) -> None:
		try:
			self._fastfetch_templates_folder = folder or self._fastfetch_templates_folder
			self._fastfetch_model.refresh(self._fastfetch_templates_folder)
		except Exception:
			self._logger.exception("Failed refreshing fastfetch templates for %s", folder)

	@Slot(result="QVariantMap")
	def getFastfetchInfo(self) -> dict:
		"""Return small dict with keys `config_image` and `template_folder` for QML consumption."""
		try:
			# Try to discover a reasonable template folder and any config image
			template_folder = self._fastfetch_templates_folder
			# Try several common keys in fastfetch config for a configured image
			config_image = ""
			cfg_path = ""
			for key in ("config_image", "image", "source", "logo", "icon"):
				val, cfg_path = file_utils.read_config_fastfetch(key, None)
				if val:
					# expand and verify
					p = Path(str(val)).expanduser()
					if p.exists():
						config_image = str(p)
						break
			# as a last resort, check a reasonable default location
			if not config_image:
				fallback = Path.home() / ".config" / "fastfetch" / "chica-tinted.png"
				if fallback.exists():
					config_image = str(fallback)

			return {"config_image": config_image, "template_folder": template_folder, "config_path": cfg_path}
		except Exception:
			self._logger.exception("Failed reading fastfetch info")
			return {"config_image": "", "template_folder": self._fastfetch_templates_folder, "config_path": ""}

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
		
		path = os.path.normpath(path)

		# avoid duplicates by path
		for f in self._model._folders:
			if os.path.normpath(f.path) == path:
				self._logger.info("Folder %s already present, skipping add", path)
				return
		# add to model
		self._model.addFolder(name, path)
		# select the newly added folder
		try:
			new_index = self._model.rowCount() - 1
			if new_index >= 0:
				self.selectFolder(new_index)
		except Exception:
			self._logger.exception("Failed selecting newly added folder %s", path)
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

	@Slot()
	def openFileDialog(self) -> None:
		"""Open a native file selection dialog to choose a file.
		"""
		try:
			self._logger.debug(QCoreApplication.translate("Controller", "Opening file selection dialog"))
			# determine sensible initial directory: user's Pictures location (localized by the system)
			initial_dir = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation)
			if not initial_dir:
				initial_dir = os.path.expanduser("~")
			# This shows a native dialog and returns an empty string if cancelled
			selected, _ = QFileDialog.getOpenFileName(
				parent=None,
				caption=QCoreApplication.translate("Controller", "Select file"),
				dir=initial_dir
			)
			if selected:
				self.selectFile(selected)
				self._logger.info(QCoreApplication.translate("Controller", "Selected file %s"), selected)
			else:
				self._logger.debug(QCoreApplication.translate("Controller", "File selection cancelled or no file chosen"))
		except Exception:
			self._logger.exception(QCoreApplication.translate("Controller", "Failed to open file dialog or select file"))

	@Slot(str,result=str)
	def openColorDialog(self,initial: str) -> str:
		"""Compatibility wrapper for QML: open color dialog and return selected color hex."""
		try:
			return self.pickColor(initial)
		except Exception:
			self._logger.exception("Error opening color dialog")
			return ""
	@Slot(str)
	def selectFile(self, path: str) -> None:
		"""Select a file and notify QML. Accepts a filesystem path (absolute or relative).
		If the path exists, sets `self._selected_file` to a file:// URL and emits `selectedFileChanged`.
		"""
		try:
			if not path:
				self._logger.debug(QCoreApplication.translate("Controller", "selectFile called with empty path"))
				return
			# normalize and validate path
			abs_path = os.path.abspath(path)
			if not os.path.exists(abs_path):
				self._logger.warning(QCoreApplication.translate("Controller", "Selected file does not exist: %s"), abs_path)
				return
			self._selected_file = "file://" + abs_path
			self.selectedFileChanged.emit()
		except Exception:
			self._logger.exception(QCoreApplication.translate("Controller", "Error selecting file"))

	@Slot()
	def clearSelectedFile(self) -> None:
		"""Clear the currently selected file and notify QML."""
		try:
			if self._selected_file:
				self._selected_file = ""
				# attempt to stop any running tint worker
				try:
					if self._tint_thread and hasattr(self._tint_thread, "isRunning") and self._tint_thread.isRunning():
						self._tint_thread.quit()
						self._tint_thread.wait(200)
				except Exception:
					pass
				# also clear any tinted preview since selection was cleared
				self._fastfetch_tinted_preview = ""
				self.fastfetchTintedPreviewChanged.emit()
				self.selectedFileChanged.emit()
		except Exception:
			self._logger.exception(QCoreApplication.translate("Controller", "Error clearing selected file"))

	@Slot(str, result=str)
	def pickColor(self, initial: str = "") -> str:
		try:
			if not initial or not QColor.isValidColor(initial):
				initial = "#ffffff"
			color = QColorDialog.getColor(QColor(initial), None, "Select color")
		except Exception:
			self._logger.exception("Error opening color dialog")
			return ""
		return color.name()

	def _get_selected_file(self) -> str:
		return self._selected_file
	

	def _get_selected_folder(self) -> str:
		return self._selected_folder

	def _get_fastfetch_tinted_preview(self) -> str:
		return self._fastfetch_tinted_preview

	def _get_fastfetch_tinting(self) -> bool:
		return getattr(self, "_fastfetch_tinting", False)

	@Slot(str)
	def _on_tint_done(self, dst: str) -> None:
		"""Handler for FastfetchTintWorker.finished signal."""
		try:
			if dst:
				self._fastfetch_tinted_preview = "file://" + str(Path(dst))
			else:
				self._fastfetch_tinted_preview = ""
			self.fastfetchTintedPreviewChanged.emit()
		finally:
			# clear tinting flag and cleanup thread references
			self._fastfetch_tinting = False
			self.fastfetchTintingChanged.emit()
			self._tint_worker = None
			self._tint_thread = None

	@Slot()
	def stopTintWorker(self) -> None:
		"""Stop any running tint worker/thread safely. Intended to be called on app shutdown."""
		try:
			# If using Python thread, attempt to join briefly
			if self._tint_thread and isinstance(self._tint_thread, threading.Thread):
				try:
					self._tint_thread.join(timeout=1.0)
				except Exception:
					pass
			# If using QThread fallback, handle quit/wait
			if self._tint_thread and hasattr(self._tint_thread, "isRunning") and self._tint_thread.isRunning():
				self._tint_thread.quit()
				self._tint_thread.wait(1000)
		except Exception:
			self._logger.exception("Error stopping tint thread")
		finally:
			self._tint_worker = None
			self._tint_thread = None
			self._fastfetch_tinting = False
			self.fastfetchTintingChanged.emit()

	def _config_path(self) -> Path:
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
	
	selectedFile = Property(str, _get_selected_file, notify=selectedFileChanged)
	selectedFolder = Property(str, _get_selected_folder, notify=selectedFolderChanged)
	fastfetchTintedPreview = Property(str, _get_fastfetch_tinted_preview, notify=fastfetchTintedPreviewChanged)
	fastfetchTinting = Property(bool, _get_fastfetch_tinting, notify=fastfetchTintingChanged)
