import hashlib
import logging
import os
from pathlib import Path
from urllib.parse import quote

from PySide6.QtCore import QSize, Qt, QRunnable, QThreadPool
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickAsyncImageProvider, QQuickImageResponse, QQuickTextureFactory

logger = logging.getLogger(__name__)

class ThumbnailRunnable(QRunnable):
    def __init__(self, response):
        super().__init__()
        self.response = response

    def run(self):
        try:
            # FreeDesktop Standard Cache Directory
            cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "thumbnails" / "large"
            cache_root.mkdir(parents=True, exist_ok=True)

            # File URI formatting and MD5 hashing per FreeDesktop standard
            req_id = self.response.requested_id
            if not req_id.startswith("file://"):
                file_uri = "file://" + quote(req_id)
            else:
                file_uri = req_id
                
            hash_md5 = hashlib.md5(file_uri.encode('utf-8')).hexdigest()
            thumbnail_path = cache_root / f"{hash_md5}.png"

            img = QImage()
            texture = None

            # 1. Try to load from cache
            if thumbnail_path.exists():
                if img.load(str(thumbnail_path)):
                    texture = QQuickTextureFactory.textureFactoryForImage(img)
            
            if texture is None:
                # 2. Cache miss or corrupt cache: Generate thumbnail
                original_path = req_id
                if original_path.startswith("file://"):
                    original_path = original_path[7:]

                if img.load(original_path):
                    # FreeDesktop 'large' thumbnails are up to 256x256
                    scaled_img = img.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    
                    # Save to cache
                    scaled_img.save(str(thumbnail_path), "PNG")
                    
                    texture = QQuickTextureFactory.textureFactoryForImage(scaled_img)
                else:
                    logger.warning(f"ThumbnailProvider failed to load original image: {original_path}")

            self.response.set_texture(texture)

        except Exception as e:
            logger.exception(f"Error generating thumbnail for {self.response.requested_id}: {e}")
        finally:
            self.response.finished.emit()


class ThumbnailResponse(QQuickImageResponse):
    def __init__(self, requested_id: str, requested_size: QSize):
        super().__init__()
        self.requested_id = requested_id
        self.requested_size = requested_size
        self._texture = None
        
        runnable = ThumbnailRunnable(self)
        QThreadPool.globalInstance().start(runnable)

    def set_texture(self, texture):
        self._texture = texture

    def textureFactory(self):
        return self._texture


class ThumbnailProvider(QQuickAsyncImageProvider):
    def requestImageResponse(self, id: str, requestedSize: QSize) -> QQuickImageResponse:
        return ThumbnailResponse(id, requestedSize)
