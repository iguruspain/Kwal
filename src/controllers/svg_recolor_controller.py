"""SVG recolor feature mixin: gradient/mono recoloring and preview."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from PySide6.QtCore import Property, Signal, Slot
from PySide6.QtWidgets import QFileDialog

from ..models.svg_worker import SvgWorker
from ..utils.svg_utils import get_svg_preview_cache_dir


class SvgMixin:
    svgDirectoryChanged = Signal()

    svgGradientColorsChanged = Signal()

    svgColorCountChanged = Signal()

    svgMonoColorChanged = Signal()

    svgProcessingChanged = Signal()

    svgLogTextChanged = Signal()

    svgPreviewFilesChanged = Signal()

    svgPreviewIndexChanged = Signal()

    svgCurrentPreviewFileChanged = Signal()

    svgPreviewTimestampChanged = Signal()

    svgHasPreviewChanged = Signal()

    svgHasBackupChanged = Signal()

    def _get_svg_directory(self) -> str:
        return self._svg_directory

    def _set_svg_directory(self, val: str) -> None:
        if self._svg_directory != val:
            self._svg_directory = val
            self.svgDirectoryChanged.emit()

    svgDirectory = Property(str, _get_svg_directory, _set_svg_directory, notify=svgDirectoryChanged)

    def _get_svg_gradient_colors(self) -> list[str]:
        return list(self._svg_gradient_colors)

    svgGradientColors = Property("QVariantList", _get_svg_gradient_colors, notify=svgGradientColorsChanged)

    def _get_svg_color_count(self) -> int:
        return self._svg_color_count

    def _set_svg_color_count(self, val: int) -> None:
        clamped = max(2, min(6, int(val)))
        if self._svg_color_count != clamped:
            self._svg_color_count = clamped
            self.svgColorCountChanged.emit()

    svgColorCount = Property(int, _get_svg_color_count, _set_svg_color_count, notify=svgColorCountChanged)

    def _get_svg_mono_color(self) -> str:
        return self._svg_mono_color

    def _set_svg_mono_color(self, val: str) -> None:
        if self._svg_mono_color != val:
            self._svg_mono_color = val
            self.svgMonoColorChanged.emit()

    svgMonoColor = Property(str, _get_svg_mono_color, _set_svg_mono_color, notify=svgMonoColorChanged)

    def _get_svg_processing(self) -> bool:
        return self._svg_processing

    svgProcessing = Property(bool, _get_svg_processing, notify=svgProcessingChanged)

    def _get_svg_log_text(self) -> str:
        return self._svg_log

    svgLogText = Property(str, _get_svg_log_text, notify=svgLogTextChanged)

    def _get_svg_preview_index(self) -> int:
        return self._svg_preview_index

    svgPreviewIndex = Property(int, _get_svg_preview_index, notify=svgPreviewIndexChanged)

    def _get_svg_current_preview_file(self) -> str:
        if 0 <= self._svg_preview_index < len(self._svg_preview_files):
            return self._svg_preview_files[self._svg_preview_index]
        return ""

    svgCurrentPreviewFile = Property(str, _get_svg_current_preview_file, notify=svgCurrentPreviewFileChanged)

    def _get_svg_preview_count(self) -> int:
        return len(self._svg_preview_files)

    svgPreviewCount = Property(int, _get_svg_preview_count, notify=svgPreviewFilesChanged)

    def _get_svg_preview_timestamp(self) -> int:
        return self._svg_preview_timestamp

    svgPreviewTimestamp = Property(int, _get_svg_preview_timestamp, notify=svgPreviewTimestampChanged)

    def _get_svg_has_preview(self) -> bool:
        return bool(self._svg_preview_dir) and os.path.isdir(self._svg_preview_dir)

    svgHasPreview = Property(bool, _get_svg_has_preview, notify=svgHasPreviewChanged)

    def _get_svg_has_backup(self) -> bool:
        return bool(self._svg_backup_dir) and os.path.isdir(self._svg_backup_dir)

    svgHasBackup = Property(bool, _get_svg_has_backup, notify=svgHasBackupChanged)

    @Slot()
    def svgBrowseDirectory(self) -> None:
        try:
            initial = self._svg_directory or str(Path.home())
            selected = QFileDialog.getExistingDirectory(None, "Select SVG folder", initial)
            if selected:
                self._set_svg_directory(selected)
        except Exception:
            self._logger.exception("svgBrowseDirectory failed")

    @Slot(int, str)
    def svgSetGradientColor(self, index: int, color_hex: str) -> None:
        try:
            if 0 <= index < len(self._svg_gradient_colors):
                self._svg_gradient_colors[index] = color_hex
                self.svgGradientColorsChanged.emit()
        except Exception:
            self._logger.exception("svgSetGradientColor failed")

    @Slot(str)
    def svgSetMonoColor(self, color_hex: str) -> None:
        self._set_svg_mono_color(color_hex)

    @Slot(int)
    def svgSetColorCount(self, count: int) -> None:
        self._set_svg_color_count(count)

    @Slot()
    def svgStartProcessing(self) -> None:
        try:
            if not self._svg_directory or not os.path.isdir(self._svg_directory):
                self.notification.emit("Please select a valid directory first.", "error")
                return

            if self._svg_processing:
                return

            preview_dir = str(get_svg_preview_cache_dir())

            # Rebuild preview directory from scratch
            if os.path.exists(preview_dir):
                shutil.rmtree(preview_dir)
            os.makedirs(preview_dir, exist_ok=True)

            original_files: dict[str, str] = {}

            for root_str, _dirs, files in os.walk(self._svg_directory):
                if root_str == preview_dir or root_str.startswith(preview_dir + os.sep):
                    continue
                for fname in files:
                    if not fname.lower().endswith(".svg"):
                        continue
                    src = os.path.join(root_str, fname)
                    rel = os.path.relpath(src, self._svg_directory)
                    dst = os.path.join(preview_dir, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    original_files[dst] = src

            if not original_files:
                shutil.rmtree(preview_dir, ignore_errors=True)
                self.notification.emit("No SVG files found in the selected directory.", "error")
                return

            self._svg_preview_dir = preview_dir
            self._svg_original_files = original_files
            self._svg_log = ""
            self.svgLogTextChanged.emit()
            self.svgHasPreviewChanged.emit()

            active_colors = self._svg_gradient_colors[: self._svg_color_count]
            worker = SvgWorker(preview_dir, active_colors, self._svg_mono_color)
            self._svg_worker = worker

            worker.logMessage.connect(self._svg_on_log)
            worker.progressChanged.connect(self._svg_on_progress)
            worker.finished.connect(self._svg_on_finished)
            worker.stopped.connect(self._svg_on_stopped)

            self._svg_processing = True
            self.svgProcessingChanged.emit()

            separator = "=" * 60
            lines = [
                separator,
                "SVG RECOLOR — KWAL",
                separator,
                f"📁 Source: {self._svg_directory}",
                f"📁 Preview: {preview_dir}",
                f"🎨 Colors ({self._svg_color_count}): {' → '.join(active_colors)}",
                f"🎨 System icons: {self._svg_mono_color}",
                separator,
            ]
            self._svg_log = "\n".join(lines)
            self.svgLogTextChanged.emit()

            worker.start()
        except Exception:
            self._logger.exception("svgStartProcessing failed")
            self._svg_processing = False
            self.svgProcessingChanged.emit()
            self.notification.emit("Failed to start SVG processing.", "error")

    @Slot()
    def svgStopProcessing(self) -> None:
        try:
            if self._svg_worker and self._svg_worker.isRunning():
                self._svg_worker.stop()
                self._svg_worker.wait()
        except Exception:
            self._logger.exception("svgStopProcessing failed")

    @Slot()
    def svgApplyChanges(self) -> None:
        try:
            if not self._svg_preview_dir or not os.path.isdir(self._svg_preview_dir):
                self.notification.emit("No preview directory available.", "error")
                return

            import datetime as _datetime
            timestamp_str = _datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(self._svg_directory, f"backup_{timestamp_str}")
            os.makedirs(backup_dir, exist_ok=True)

            applied = 0
            for preview_path, original_path in self._svg_original_files.items():
                if not os.path.exists(preview_path) or not os.path.exists(original_path):
                    continue
                rel = os.path.relpath(original_path, self._svg_directory)
                backup_path = os.path.join(backup_dir, rel)
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                shutil.copy2(original_path, backup_path)
                shutil.copy2(preview_path, original_path)
                applied += 1

            shutil.rmtree(self._svg_preview_dir, ignore_errors=True)
            self._svg_preview_dir = ""
            self._svg_preview_files = []
            self._svg_preview_index = 0
            self._svg_original_files = {}
            self._svg_backup_dir = backup_dir

            self.svgPreviewFilesChanged.emit()
            self.svgPreviewIndexChanged.emit()
            self.svgCurrentPreviewFileChanged.emit()
            self.svgHasPreviewChanged.emit()
            self.svgHasBackupChanged.emit()

            msg = f"Applied {applied} files. Backup saved to backup_{timestamp_str}/"
            self._svg_append_log(f"\n✅ {msg}")
            self._show_result_dialog(msg)
        except Exception:
            self._logger.exception("svgApplyChanges failed")
            self.notification.emit("Failed to apply SVG changes.", "error")

    @Slot()
    def svgUndoChanges(self) -> None:
        try:
            if not self._svg_backup_dir or not os.path.isdir(self._svg_backup_dir):
                self.notification.emit("No backup directory available.", "error")
                return

            restored = 0
            for root_str, _dirs, files in os.walk(self._svg_backup_dir):
                for fname in files:
                    if not fname.lower().endswith(".svg"):
                        continue
                    backup_path = os.path.join(root_str, fname)
                    rel = os.path.relpath(backup_path, self._svg_backup_dir)
                    original_path = os.path.join(self._svg_directory, rel)
                    if os.path.exists(original_path):
                        shutil.copy2(backup_path, original_path)
                        restored += 1

            shutil.rmtree(self._svg_backup_dir, ignore_errors=True)
            self._svg_backup_dir = ""
            self.svgHasBackupChanged.emit()

            msg = f"Restored {restored} files from backup."
            self._svg_append_log(f"\n↩️ {msg}")
            self._show_result_dialog(msg)
        except Exception:
            self._logger.exception("svgUndoChanges failed")
            self.notification.emit("Failed to undo SVG changes.", "error")

    @Slot(int)
    def svgNavigatePreview(self, direction: int) -> None:
        new_index = self._svg_preview_index + int(direction)
        count = len(self._svg_preview_files)
        if count == 0:
            return
        new_index = max(0, min(count - 1, new_index))
        if new_index != self._svg_preview_index:
            self._svg_preview_index = new_index
            self._svg_preview_timestamp += 1
            self.svgPreviewIndexChanged.emit()
            self.svgCurrentPreviewFileChanged.emit()
            self.svgPreviewTimestampChanged.emit()

    def _svg_append_log(self, text: str) -> None:
        self._svg_log += text
        self.svgLogTextChanged.emit()

    @Slot(str)
    def _svg_on_log(self, message: str) -> None:
        self._svg_append_log("\n" + message if self._svg_log else message)

    @Slot(bool)
    def _svg_on_progress(self, active: bool) -> None:
        self._svg_processing = active
        self.svgProcessingChanged.emit()

    @Slot(int, int)
    def _svg_on_finished(self, total: int, success: int) -> None:
        self._svg_processing = False
        self.svgProcessingChanged.emit()
        rate = (success / total * 100) if total > 0 else 0.0
        separator = "=" * 60
        summary = (
            f"\n{separator}\n"
            f"✅ Done: {success}/{total} files recolored ({rate:.1f}%).\n"
            f"📁 Preview folder ready. Use ◀ ▶ to inspect, then Apply.\n"
            f"{separator}"
        )
        self._svg_append_log(summary)
        self._svg_load_preview_files()

    @Slot()
    def _svg_on_stopped(self) -> None:
        self._svg_processing = False
        self.svgProcessingChanged.emit()
        self._svg_append_log("\n🛑 Processing stopped by user.")
        self._svg_load_preview_files()

    def _svg_load_preview_files(self) -> None:
        files: list[str] = []
        if self._svg_preview_dir and os.path.isdir(self._svg_preview_dir):
            for root_str, _dirs, fnames in os.walk(self._svg_preview_dir):
                for fname in sorted(fnames):
                    if fname.lower().endswith(".svg"):
                        files.append(os.path.join(root_str, fname))
        files.sort()
        self._svg_preview_files = files
        self._svg_preview_index = 0
        self._svg_preview_timestamp += 1
        self.svgPreviewFilesChanged.emit()
        self.svgPreviewIndexChanged.emit()
        self.svgCurrentPreviewFileChanged.emit()
        self.svgPreviewTimestampChanged.emit()
        self.svgHasPreviewChanged.emit()

    def stopSvgWorker(self) -> None:
        """Stop SVG worker on application quit."""
        if self._svg_worker and self._svg_worker.isRunning():
            try:
                self._svg_worker.stop()
                self._svg_worker.wait(2000)
            except Exception:
                self._logger.exception("Error stopping SVG worker during shutdown")

    def _init_svg(self) -> None:
        """Initialize SVG recolor state."""
        self._svg_directory: str = ""
        self._svg_gradient_colors: list[str] = [
            "#000000", "#464646", "#D81C4A", "#b6b6b6", "#FFFFFF", "#888888",
        ]
        self._svg_color_count: int = 5
        self._svg_mono_color: str = "#ACACAC"
        self._svg_preview_dir: str = ""
        self._svg_backup_dir: str = ""
        self._svg_preview_files: list[str] = []
        self._svg_preview_index: int = 0
        self._svg_processing: bool = False
        self._svg_log: str = ""
        self._svg_original_files: dict[str, str] = {}
        self._svg_preview_timestamp: int = 0
        self._svg_worker: SvgWorker | None = None
