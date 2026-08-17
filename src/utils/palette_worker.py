"""Background worker for palette extraction."""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QThread, Signal

from . import color_utils

logger = logging.getLogger(__name__)


class PaletteWorker(QThread):
    """Extracts a color palette from an image in a background thread.

    Emits ``dataReady`` with the extracted palette on success or ``error``
    with a message on failure.
    """

    # Renamed to avoid shadowing QThread.finished
    dataReady = Signal(dict)
    error = Signal(str)

    def __init__(self, path: str, backend: str, kwargs: dict[str, Any]):
        super().__init__()
        self.path = path
        self.backend = backend
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            pdata = color_utils.extract_palette(self.path, self.backend, **self.kwargs)
            result = {
                "colors": pdata.colors,
                "accents": pdata.accents,
                "backend": pdata.backend_used,
                "source": pdata.source_path,
                "seed": pdata.seed,
            }
            self.dataReady.emit(result)
        except Exception as e:
            logger.exception("Palette extraction failed")
            self.error.emit(str(e))
