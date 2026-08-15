"""Base class for HTML-preview models (Starship, Ulauncher).

Both ``StarshipModel`` and ``UlauncherModel`` share the same preview machinery:
a pair of background :class:`HtmlPreviewWorker` threads (one for the editable
preview, one for the on-disk "current config" preview), a debounce ``QTimer``
that re-renders on palette/scale/width changes, and the QML properties that
expose the rendered HTML plus the scale/width controls.

This module centralises that shared logic so the concrete models only implement
their feature-specific ``refresh()`` and the timer callback that builds the
renderer arguments.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Property, QThread, QTimer, Signal, Slot
import shiboken6 as shiboken

from ..utils.worker_thread import start_worker_thread

logger = logging.getLogger(__name__)


class HtmlPreviewWorker(QObject):
    """Worker to generate HTML previews in a background thread."""

    finished = Signal(str, str)  # (html, target_property_name)

    def __init__(self, renderer_func, args, target_name: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.renderer_func = renderer_func
        self.args = args
        self.target_name = target_name

    @Slot()
    def process(self) -> None:
        try:
            # Check if args is a list/tuple or dict
            if isinstance(self.args, dict):
                html = self.renderer_func(**self.args)
            else:
                html = self.renderer_func(*self.args)
            self.finished.emit(html, self.target_name)
        except Exception:
            logger.exception("HtmlPreviewWorker failed for %s", self.target_name)
            self.finished.emit("", self.target_name)


class PreviewModelBase(QObject):
    """Shared preview state, worker lifecycle and QML properties.

    Subclasses must call ``super().__init__(default_scale, default_width,
    render_interval_ms, parent)`` and then connect ``self._render_timer.timeout``
    to their own render callback (e.g. ``_regenerate_preview_task``).
    """

    previewChanged = Signal()
    currentConfigPreviewChanged = Signal()
    previewScaleChanged = Signal()
    previewWidthChanged = Signal()

    def __init__(
        self,
        default_scale: float,
        default_width: int,
        render_interval_ms: int,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._preview_html: str = ""
        self._current_config_preview_html: str = ""
        self._preview_scale: float = default_scale
        self._preview_width: int = default_width

        # Rendering state
        self._worker: HtmlPreviewWorker | None = None
        self._worker_thread: QThread | None = None
        self._current_worker: HtmlPreviewWorker | None = None
        self._current_worker_thread: QThread | None = None

        # Debounce timer (subclasses connect ``timeout`` to their render task)
        self._render_timer = QTimer()
        self._render_timer.setSingleShot(True)
        self._render_timer.setInterval(render_interval_ms)

    # -- Preview HTML -----------------------------------------------------

    def _get_preview_html(self) -> str:
        return str(self._preview_html)

    def _get_current_config_preview_html(self) -> str:
        return str(self._current_config_preview_html)

    # -- Scale / width ----------------------------------------------------

    def _get_preview_scale(self) -> float:
        return self._preview_scale

    def _set_preview_scale(self, val: float) -> None:
        if self._preview_scale != val:
            self._preview_scale = float(val)
            self._render_timer.start()
            self._on_preview_params_changed()
            self.previewScaleChanged.emit()

    def _get_preview_width(self) -> int:
        return self._preview_width

    def _set_preview_width(self, val: int) -> None:
        if self._preview_width != val:
            self._preview_width = int(val)
            self._render_timer.start()
            self._on_preview_params_changed()
            self.previewWidthChanged.emit()

    def _on_preview_params_changed(self) -> None:
        """Hook invoked after a scale/width change. Override in subclasses."""

    # -- Worker lifecycle -------------------------------------------------

    def _cleanup_worker(self, current: bool = False) -> None:
        t_attr = "_current_worker_thread" if current else "_worker_thread"
        w_attr = "_current_worker" if current else "_worker"

        thread = getattr(self, t_attr)
        if thread:
            try:
                if shiboken.isValid(thread) and thread.isRunning():
                    thread.quit()
                    thread.wait(500)
            except RuntimeError:
                pass
            finally:
                setattr(self, t_attr, None)
        setattr(self, w_attr, None)

    def _start_worker(self, func, args, target_name) -> None:
        """Helper to start a background worker thread."""
        is_current = (target_name == "currentConfigPreviewHtml")
        self._cleanup_worker(current=is_current)

        worker = HtmlPreviewWorker(func, args, target_name)
        worker.finished.connect(self._on_worker_done)
        thread = start_worker_thread(worker)

        if is_current:
            self._current_worker = worker
            self._current_worker_thread = thread
        else:
            self._worker = worker
            self._worker_thread = thread

    @Slot(str, str)
    def _on_worker_done(self, html: str, target: str) -> None:
        if target == "previewHtml":
            self._preview_html = html
            self.previewChanged.emit()
        elif target == "currentConfigPreviewHtml":
            self._current_config_preview_html = html
            self.currentConfigPreviewChanged.emit()

    # -- QML properties ---------------------------------------------------

    previewHtml = Property(str, _get_preview_html, notify=previewChanged)
    currentConfigPreviewHtml = Property(str, _get_current_config_preview_html, notify=currentConfigPreviewChanged)
    previewScale = Property(float, _get_preview_scale, _set_preview_scale, notify=previewScaleChanged)
    previewWidth = Property(int, _get_preview_width, _set_preview_width, notify=previewWidthChanged)
