"""
Video thumbnail provider for QML.
Extracts and caches frames from video files.
"""

import hashlib
import logging
import os
from pathlib import Path
from urllib.parse import quote

from PySide6.QtCore import QSize, Qt, QRunnable, QThreadPool, QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickAsyncImageProvider, QQuickImageResponse, QQuickTextureFactory

logger = logging.getLogger(__name__)


class VideoThumbnailRunnable(QRunnable):
    def __init__(self, response):
        super().__init__()
        self.response = response

    def run(self):
        try:
            from ..utils import video_utils
            
            req_id = self.response.requested_id
            if not Path(req_id).exists():
                logger.warning(f"Video file not found: {req_id}")
                self.response.set_texture(None)
                self.response.finished.emit()
                return
            
            # Extract frame from video
            frame_image = video_utils.get_video_frame_as_image(
                req_id,
                timestamp=0.0,
                max_size=512
            )
            
            texture = None
            if frame_image:
                try:
                    # Convert PIL Image to QImage
                    # PIL to RGB first for proper conversion
                    rgb_image = frame_image.convert("RGB")
                    
                    # Get raw image data
                    width, height = rgb_image.size
                    data = rgb_image.tobytes("raw", "RGB")
                    
                    # Create QImage from raw data
                    q_image = QImage(data, width, height, 3 * width, QImage.Format.Format_RGB888)
                    
                    if not q_image.isNull():
                        texture = QQuickTextureFactory.textureFactoryForImage(q_image)
                    else:
                        logger.warning(f"Failed to create QImage for {req_id}")
                except Exception as e:
                    logger.warning(f"Error converting PIL image to QImage for {req_id}: {e}")
            else:
                logger.warning(f"Failed to extract frame from {req_id}")
            
            self.response.set_texture(texture)
            
        except Exception as e:
            logger.exception(f"Error generating video thumbnail for {self.response.requested_id}: {e}")
            self.response.set_texture(None)
        finally:
            self.response.finished.emit()


class VideoThumbnailResponse(QQuickImageResponse):
    def __init__(self, requested_id: str, requested_size: QSize):
        super().__init__()
        self.requested_id = requested_id
        self.requested_size = requested_size
        self._texture = None
        
        runnable = VideoThumbnailRunnable(self)
        QThreadPool.globalInstance().start(runnable)

    def set_texture(self, texture):
        self._texture = texture

    def textureFactory(self):
        return self._texture


class VideoThumbnailProvider(QQuickAsyncImageProvider):
    """Provider for video frame thumbnails."""
    
    def requestImageResponse(self, id: str, requestedSize: QSize) -> QQuickImageResponse:
        return VideoThumbnailResponse(id, requestedSize)
