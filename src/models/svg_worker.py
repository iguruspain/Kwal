"""Background worker that recolors SVG files inside a preview directory."""

from __future__ import annotations

import logging
import os

from PySide6.QtCore import QMutex, QObject, QThread, Signal

logger = logging.getLogger(__name__)


class SvgWorker(QThread):
    """Background worker that recolors SVG files inside a preview directory."""

    logMessage = Signal(str)
    progressChanged = Signal(bool)
    finished = Signal(int, int)  # (total_count, success_count)
    stopped = Signal()

    def __init__(
        self,
        preview_dir: str,
        gradient_colors: list[str],
        mono_color: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._preview_dir = preview_dir
        self._gradient_colors = list(gradient_colors)
        self._mono_color = mono_color
        self._mutex = QMutex()
        self._is_running = True

    def stop(self) -> None:
        self._mutex.lock()
        self._is_running = False
        self._mutex.unlock()

    def _check_running(self) -> bool:
        self._mutex.lock()
        running = self._is_running
        self._mutex.unlock()
        return running

    def run(self) -> None:
        self.progressChanged.emit(True)
        svg_count, success_count = self._process_directory()
        self.progressChanged.emit(False)
        if self._check_running():
            self.finished.emit(svg_count, success_count)
        else:
            self.stopped.emit()

    def _process_directory(self) -> tuple[int, int]:
        from ..utils.svg_utils import recolor_svg_file

        svg_count = 0
        success_count = 0

        for root_str, _dirs, files in os.walk(self._preview_dir):
            if not self._check_running():
                break

            svg_files = [f for f in files if f.lower().endswith(".svg")]
            if not svg_files:
                continue

            rel = os.path.relpath(root_str, self._preview_dir)
            header = "\n📁 Main folder:" if rel == "." else f"\n📁 {rel}:"
            self.logMessage.emit(header)

            for svg_file in svg_files:
                if not self._check_running():
                    break
                svg_count += 1
                file_path = os.path.join(root_str, svg_file)
                try:
                    ok, info = recolor_svg_file(
                        file_path, self._gradient_colors, self._mono_color
                    )
                    if ok:
                        success_count += 1
                        self.logMessage.emit(f"  ✓ {svg_file} ({info})")
                    else:
                        self.logMessage.emit(f"  ✗ {svg_file} ({info})")
                except Exception as exc:
                    self.logMessage.emit(f"  ✗ {svg_file} (Exception: {exc})")
