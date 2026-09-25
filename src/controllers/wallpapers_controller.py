"""Wallpaper feature mixin: folders, wallpaper selection, and color extraction."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from pathlib import Path

from PySide6.QtCore import Property, QStandardPaths, Signal, Slot
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QColorDialog, QFileDialog

from ..models.common import Folder
from ..models.wallpaper_models import ImageModel, WallpaperFolderModel
from ..utils import color_utils, plasma_wallpaper


class WallpapersMixin:
    selectedFolderChanged = Signal()

    selectedWallpaperChanged = Signal()

    selectedFileChanged = Signal()

    wallpaperColorsChanged = Signal()

    initialWallpaperIndexChanged = Signal()

    def wallpaperModel(self) -> WallpaperFolderModel:
        return self._model

    def _get_selected_wallpaper(self) -> str:
        return self._selected_wallpaper

    selectedWallpaper = Property(str, _get_selected_wallpaper, notify=selectedWallpaperChanged)

    def _get_initial_wallpaper_index(self) -> int:
        return self._initial_wallpaper_index

    initialWallpaperIndex = Property(int, _get_initial_wallpaper_index, notify=initialWallpaperIndexChanged)

    def _get_selected_wallpaper_resolution(self) -> str:
        return self._selected_wallpaper_resolution

    selectedWallpaperResolution = Property(str, _get_selected_wallpaper_resolution, notify=selectedWallpaperChanged)

    def _get_thumb_path(self) -> str:
        return self._thumb_path

    thumbPath = Property(str, _get_thumb_path, notify=selectedWallpaperChanged)

    def _get_wallpaper_colors(self) -> list[str]:
        return self._wallpaper_colors

    wallpaperColors = Property("QVariantList", _get_wallpaper_colors, notify=wallpaperColorsChanged)

    def _get_selected_file(self) -> str:
        return self._selected_file

    selectedFile = Property(str, _get_selected_file, notify=selectedFileChanged)

    def _get_selected_folder(self) -> str:
        return self._selected_folder

    selectedFolder = Property(str, _get_selected_folder, notify=selectedFolderChanged)

    @Slot(str)
    def selectWallpaper(self, path: str) -> None:
        try:
            if self._selected_wallpaper != path:
                self._selected_wallpaper = path

                if path:
                    from ..utils import color_extractor, video_utils

                    # For videos, extract frame and use that for color extraction
                    # and as the thumbnail image (%vidimg%). For regular images,
                    # the thumbnail is simply the wallpaper itself.
                    image_for_colors = path
                    if video_utils.is_video_file(path):
                        try:
                            frame_path = video_utils.get_video_frame_path(path)
                            if frame_path:
                                image_for_colors = frame_path
                                self._logger.info("Using video frame for color extraction: %s", frame_path)
                        except Exception as e:
                            self._logger.warning("Failed to extract video frame for colors: %s", e)

                    self._thumb_path = image_for_colors

                    img = QImage(image_for_colors)
                    if not img.isNull():
                        if video_utils.is_video_file(path):
                            # Never trust the extracted/cached frame's size for
                            # videos: it can be a downscaled thumbnail shared
                            # with the grid preview cache. Ask the video itself.
                            res = video_utils.get_video_resolution(path)
                            if res:
                                self._selected_wallpaper_resolution = f"{res[0]}x{res[1]}"
                            else:
                                self._selected_wallpaper_resolution = f"{img.width()}x{img.height()}"
                        else:
                            self._selected_wallpaper_resolution = f"{img.width()}x{img.height()}"

                        cache = color_extractor.load_color_cache()
                        if path in cache and "colors" in cache[path]:
                            self._wallpaper_colors = cache[path]["colors"]
                            self.wallpaperColorsChanged.emit()
                            self._logger.info("Instantly loaded wallpaper colors from cache.")
                        else:
                            self._start_color_extraction(image_for_colors)
                    else:
                        self._selected_wallpaper_resolution = ""
                        self._wallpaper_colors = []
                        self.wallpaperColorsChanged.emit()
                else:
                    self._selected_wallpaper_resolution = ""
                    self._wallpaper_colors = []
                    self._thumb_path = ""
                    self.wallpaperColorsChanged.emit()

                self.selectedWallpaperChanged.emit()
        except Exception:
            self._logger.exception("Error selecting wallpaper %r", path)

    _colorsExtracted = Signal(list)

    def _start_color_extraction(self, image_path: str) -> None:
        """Starts a background thread to extract top colors using Celebi quantization."""
        self._color_extraction_thread = threading.Thread(
            target=self._extract_colors_task,
            args=(image_path,),
            daemon=True
        )
        self._color_extraction_thread.start()

    def _extract_colors_task(self, image_path: str) -> None:
        """Background task to extract colors using materialyoucolor.

        Like matugen, it resizes the image to 128x128 for speed,
        then uses Celebi algorithm to quantize colors, and scores them.
        """
        try:
            import os

            from ..utils import color_extractor
            from ..utils.color_utils import extract_wallpaper_top_colors

            hex_colors = extract_wallpaper_top_colors(image_path, count=8)
            self._logger.info(f"Extracted wallpaper colors: {hex_colors}")

            if hex_colors:
                try:
                    cache = color_extractor.load_color_cache()
                    cats = []
                    for c in hex_colors:
                        cat = color_extractor.get_color_category(c)
                        if cat not in cats:
                            cats.append(cat)
                        if len(cats) > color_extractor.MAX_CATEGORIES:
                            break

                    cache[image_path] = {
                        "colors": hex_colors,
                        "categories": cats,
                        "last_modified": os.path.getmtime(image_path)
                    }
                    color_extractor.save_color_cache(cache)
                except Exception as cache_err:
                    self._logger.warning("Failed to save extracted colors to cache: %s", cache_err)

            # Only update if the selection hasn't changed while we were processing
            if self._selected_wallpaper == image_path:
                self._colorsExtracted.emit(hex_colors)

        except Exception as e:
            self._logger.error("Failed to extract wallpaper colors: %s", e)
            self._colorsExtracted.emit([])

    @Slot(list)
    def _update_colors_main_thread(self, colors: list) -> None:
        """Safely updates the property on the main thread via Qt slot mechanism."""
        self._logger.info(f"Updating UI with Colors: {colors}")
        self._wallpaper_colors = colors
        self.wallpaperColorsChanged.emit()

    @Slot(str)
    def setAsWallpaper(self, path: str) -> None:
        """Call standard KDE mechanism to set wallpaper."""
        if not path:
            self._logger.warning("setAsWallpaper called with empty path")
            return

        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            self._logger.error("Wallpaper path does not exist: %s", abs_path)
            return

        self._last_set_wallpaper = abs_path
        self._logger.info("Setting wallpaper to %s", abs_path)

        if not plasma_wallpaper.set_wallpaper(abs_path):
            self.notification.emit("qdbus executable not found (required for KDE Plasma)", "error")

        self._save_config()

    @Slot(str)
    def runCMD(self, command: str) -> None:
        """Execute a user-provided shell command in the background (fire & forget)."""
        cmd = (command or "").strip()
        if not cmd:
            return
        try:
            subprocess.Popen(cmd, shell=True, start_new_session=True)
            self._logger.info("Launched custom command: %r", cmd)
        except Exception:
            self._logger.exception("Failed to launch custom command: %r", cmd)
            self.notification.emit(f"Failed to run command: {cmd}", "error")

    @Slot(result=str)
    def getCurrentSystemWallpaper(self) -> str:
        #NEVER TOUCH THIS getCurrentSystemWallpaper FUNCTION ITS CORRECT
        """Retrieve current wallpaper from KDE Plasma via config file directly (more reliable than qdbus parsing)."""
        # Prefer qdbus / PlasmaShell evaluateScript parsing (uses Plasma's runtime state)
        try:
            qdbus_path = shutil.which("qdbus") or shutil.which("qdbus-qt6") or shutil.which("qdbus6")
            if qdbus_path:
                script = (
                    "var ds = desktops();\n"
                    "for (let i = 0; i < ds.length; i++) {\n"
                    "  if (ds[i].screen == 0) {\n"
                    "    ds[i].currentConfigGroup = Array('Wallpaper', ds[i].wallpaperPlugin, 'General');\n"
                    "    if (ds[i].wallpaperPlugin == 'org.kde.image') {\n"
                    "      print(ds[i].readConfig('Image').replace('file://', ''));\n"
                    "    }\n"
                    "  }\n"
                    "}\n"
                )
                try:
                    proc = subprocess.run(
                        [qdbus_path, "org.kde.plasmashell", "/PlasmaShell",
                         "org.kde.PlasmaShell.evaluateScript", script],
                        capture_output=True, text=True, check=False
                    )
                    out = (proc.stdout or "").strip()
                    if out:
                        # Filter empty lines and take first non-empty
                        lines = [line.strip() for line in out.splitlines() if line.strip()]
                        if lines:
                            candidate = lines[0]
                            # If value looks like a file path and exists, return it
                            if os.path.exists(candidate):
                                return candidate
                except Exception:
                    self._logger.debug("qdbus evaluateScript failed", exc_info=True)
        except Exception:
            # Do not fail hard on qdbus detection; fall back to config parsing below
            self._logger.debug("Error checking qdbus for wallpaper", exc_info=True)

        # Fallback: parse plasma-org.kde.plasma.desktop-appletsrc (heuristic)
        try:
            config_path = Path.home() / ".config" / "plasma-org.kde.plasma.desktop-appletsrc"
            if not config_path.exists():
                return self._last_set_wallpaper if self._last_set_wallpaper else ""

            found_image = ""
            with open(config_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            in_wallpaper_group = False
            for line in lines:
                line = line.strip()
                if "[Wallpaper]" in line and "org.kde.image" in line:
                    in_wallpaper_group = True
                    continue
                if line.startswith("[") and "Wallpaper" not in line:
                    pass

                if in_wallpaper_group and line.startswith("Image="):
                    val = line.split("=", 1)[1].strip()
                    if val.startswith("file://"):
                        get_path = val[7:]
                        if os.path.exists(get_path):
                            found_image = get_path
                            break

            if found_image:
                return found_image
        except Exception as e:
            self._logger.error("Error reading system wallpaper: %s", e)

        # Final fallback
        return self._last_set_wallpaper if self._last_set_wallpaper else ""

    @Slot(str, str)
    def addFolder(self, name: str, path: str) -> None:
        self._logger.debug("addFolder called: %s %s", name, path)
        norm_path = os.path.normpath(path)

        for f in self._model._folders:
            if os.path.normpath(f.path) == norm_path:
                self._logger.info("Folder %s already present", norm_path)
                return

        self._model.addFolder(name, norm_path)

        # Use simple logic to select last
        count = self._model.rowCount()
        if count > 0:
            self.selectFolder(count - 1)

        self._save_config()

    @Slot()
    def openFolderDialog(self) -> None:
        try:
            initial_dir = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation) or os.path.expanduser("~")
            selected = QFileDialog.getExistingDirectory(None, "Select Folder", initial_dir)

            if selected:
                name = os.path.basename(selected) or selected
                self.addFolder(name, selected)
        except Exception:
            self._logger.exception("Failed in openFolderDialog")

    @Slot(int)
    def removeFolder(self, index: int) -> None:
        # Cast just in case
        try:
            idx = int(index)
        except ValueError:
            return

        if not (0 <= idx < self._model.rowCount()):
            return

        folder_to_remove = self._model._folders[idx]
        was_selected = (folder_to_remove.path == self._selected_folder)

        self._model.removeFolder(idx)

        if was_selected:
            new_count = self._model.rowCount()
            if new_count > 0:
                self.selectFolder(min(idx, new_count - 1))
            else:
                self._selected_folder = ""
                self._image_model.setFolder("")
                self.selectedFolderChanged.emit()

        self._save_config()

    @Slot(int, str)
    def renameFolder(self, index: int, new_name: str) -> None:
        """Rename the folder at *index* to *new_name* and persist the change."""
        new_name = new_name.strip()
        if not new_name:
            return
        try:
            idx = int(index)
        except (ValueError, TypeError):
            return
        if not (0 <= idx < self._model.rowCount()):
            return
        if self._model._folders[idx].name == "Local":
            return
        self._model.renameFolder(idx, new_name)
        self._save_config()

    @Slot(int)
    def selectFolder(self, index: int) -> None:
        try:
            if 0 <= index < len(self._model._folders):
                folder = self._model._folders[index]
                self._selected_folder = folder.path
                self._image_model.setFolder(self._selected_folder)
                self.selectedFolderChanged.emit()
                self._save_config()
        except Exception:
            self._logger.exception("Error selecting folder")

    @Slot()
    def openFileDialog(self) -> None:
        try:
            initial_dir = QStandardPaths.writableLocation(QStandardPaths.PicturesLocation) or os.path.expanduser("~")
            image_filter = "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff *.tif);;All Files (*)"
            selected, _ = QFileDialog.getOpenFileName(
                parent=None, caption="Select image", dir=initial_dir, filter=image_filter
            )
            if selected:
                self.selectFile(selected)
        except Exception:
            self._logger.exception("Failed in openFileDialog")

    @Slot(str, result=str)
    def openColorDialog(self, initial: str) -> str:
        """Open color dialog and return selected color hex."""
        try:
            # Parse initial color robustly
            initial_col = color_utils.parse_css_color(initial)
            if not initial_col.isValid() or initial.lower() == "transparent" or initial_col.alpha() == 0:
                if not initial_col.isValid():
                    initial_col = QColor("#ffffff")
                initial_col.setAlpha(255)

            # Show alpha channel in the dialog and return hex including alpha
            color = QColorDialog.getColor(initial_col, None, "Select color", QColorDialog.ShowAlphaChannel)
            if color.isValid():
                try:
                    return color.name(QColor.HexArgb)
                except TypeError:
                    # Fallback: construct #AARRGGBB manually if name() signature differs
                    a = color.alpha()
                    return "#{:02x}{:02x}{:02x}{:02x}".format(a, color.red(), color.green(), color.blue())
            return ""
        except Exception:
            self._logger.exception("Error opening color dialog")
            return ""

    @Slot(str)
    def selectFile(self, path: str) -> None:
        try:
            if not path:
                return
            abs_path = os.path.abspath(path)
            if not os.path.exists(abs_path):
                self._logger.warning("File does not exist: %s", abs_path)
                return
            self._selected_file = "file://" + abs_path
            self.selectedFileChanged.emit()
        except Exception:
            self._logger.exception("Error selecting file")

    @Slot()
    def clearSelectedFile(self) -> None:
        try:
            if self._selected_file:
                self._selected_file = ""
                self.clearTintState()
                self.selectedFileChanged.emit()
        except Exception:
            self._logger.exception("Error clearing selected file")

    def _init_wallpapers(self) -> None:
        """Initialize wallpaper folder and image models."""
        self._colorsExtracted.connect(self._update_colors_main_thread)

        folders: list[Folder] = []
        if self._loaded_folders:
            folders = [Folder(name=f.get("name", ""), path=f.get("path", "")) for f in self._loaded_folders]
        if not folders:
            folders = [Folder(name="Local", path="/usr/share/wallpapers")]

        self._model = WallpaperFolderModel(folders)
        self._image_model = ImageModel()
        self._pending_initial_wallpaper = self._last_set_wallpaper
        self._image_model.loadingChanged.connect(self._on_image_model_loading_changed)

    @Slot()
    def _on_image_model_loading_changed(self) -> None:
        """Select and position the last-set wallpaper once the folder scan finishes."""
        if self._image_model.loading:
            return
        if not self._pending_initial_wallpaper:
            return
        path = self._pending_initial_wallpaper
        self._pending_initial_wallpaper = ""
        for i, f in enumerate(self._image_model._files):
            if str(f) == path:
                self.selectWallpaper(path)
                self._initial_wallpaper_index = i
                self.initialWallpaperIndexChanged.emit()
                break
