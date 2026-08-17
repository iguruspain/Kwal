"""SVG image provider for QML.

Renders SVG files on demand so QML Image items can display them via
``image://svgprovider`` sources.
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtSvg import QSvgRenderer

logger = logging.getLogger(__name__)


class SvgImageProvider(QQuickImageProvider):
    """QQuickImageProvider that renders SVG files on demand for QML Image items.

    Usage in QML:  Image { source: "image://svgprovider" + absoluteSvgPath + "?t=" + cacheBuster }
    The query string is stripped before loading so callers can force reloads.
    """

    def __init__(self) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)

    def requestImage(self, id: str, size: QSize, requestedSize: QSize) -> QImage:  # type: ignore[override]
        # Strip cache-busting query (e.g. "?t=123")
        path = id.split("?")[0]
        if not path.startswith("/"):
            path = "/" + path

        w = requestedSize.width() if requestedSize.width() > 0 else 256
        h = requestedSize.height() if requestedSize.height() > 0 else 256

        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)

        try:
            p = Path(path)
            if p.exists() and p.is_file():
                renderer = QSvgRenderer(path)
                if renderer.isValid():
                    painter = QPainter(img)
                    renderer.render(painter)
                    painter.end()
        except Exception:
            logger.debug("SvgImageProvider: failed rendering %s", path, exc_info=True)

        # Set the out-parameter so QML knows the actual rendered size
        size.setWidth(img.width())
        size.setHeight(img.height())
        return img
