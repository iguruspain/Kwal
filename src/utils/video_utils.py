"""
Video utilities for extracting frames from video files.
Uses ffmpeg for frame extraction and PIL for image handling.
"""

import hashlib
import logging
import subprocess
from pathlib import Path

from PIL import Image

from .xdg_paths import kwal_cache_dir

logger = logging.getLogger(__name__)

# Supported video extensions
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".avi", ".mov", ".flv", ".m4v", ".wmv", ".3gp"}


def get_video_cache_dir() -> Path:
    """Get the cache directory for extracted video frames."""
    cache_dir = kwal_cache_dir() / "video_frames"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_frame_cache_path(video_path: str, timestamp: float = 0.0) -> Path:
    """
    Generate a cache path for a video frame.
    Uses MD5 hash of video path + timestamp for uniqueness.

    This is the single, shared cache file for a given (video, timestamp): it
    always holds the native-resolution extracted frame. Callers that need a
    thumbnail (get_video_frame_as_image) must downscale an in-memory copy
    instead of overwriting this file, so full-resolution consumers (color
    extraction, get_video_frame_path) always get the real frame.
    """
    cache_dir = get_video_cache_dir()
    hash_input = f"{video_path}:{timestamp}".encode('utf-8')
    hash_str = hashlib.md5(hash_input).hexdigest()
    return cache_dir / f"{hash_str}.png"


def extract_video_frame(video_path: str, output_path: str, timestamp: float = 0.0) -> bool:
    """
    Extract a single frame from a video file using ffmpeg.
    
    Args:
        video_path: Path to video file
        output_path: Path where to save the extracted frame
        timestamp: Timestamp in seconds (default 0.0 for first frame)
    
    Returns:
        True if successful, False otherwise
    """
    if not Path(video_path).exists():
        logger.warning(f"Video file not found: {video_path}")
        return False
    
    try:
        # Use ffmpeg to extract first frame
        cmd = [
            "ffmpeg",
            "-ss", str(timestamp),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",  # High quality
            "-f", "image2",
            output_path,
            "-loglevel", "error"
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=10)
        
        if result.returncode == 0 and Path(output_path).exists():
            logger.debug(f"Successfully extracted frame from {video_path}")
            return True
        else:
            logger.warning(f"ffmpeg failed for {video_path}: {result.stderr.decode()}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.warning(f"ffmpeg timeout extracting frame from {video_path}")
        return False
    except Exception as e:
        logger.exception(f"Error extracting frame from {video_path}: {e}")
        return False


def get_video_frame_as_image(video_path: str, timestamp: float = 0.0, max_size: int = 512) -> Image.Image | None:
    """
    Get a scaled frame from a video file as a PIL Image.
    Uses cache if available.

    The on-disk cache always holds the native-resolution extracted frame
    (shared with get_video_frame_path/color extraction). This function only
    downscales an in-memory COPY to return -- it never overwrites the cached
    file, so callers that need full resolution are never handed a thumbnail.

    Args:
        video_path: Path to video file
        timestamp: Timestamp in seconds (default 0.0 for first frame)
        max_size: Maximum dimension for thumbnail (default 256)
    
    Returns:
        PIL Image object or None if extraction fails
    """
    cache_path = get_frame_cache_path(video_path, timestamp)

    def _thumbnail_copy(full_img: Image.Image) -> Image.Image:
        thumb = full_img.copy()
        thumb.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        return thumb

    # Try to load from cache first
    if cache_path.exists():
        try:
            img = Image.open(cache_path)
            return _thumbnail_copy(img)
        except Exception as e:
            logger.warning(f"Failed to load cached frame: {e}")
            cache_path.unlink()  # Remove corrupted cache
    
    # Extract frame and cache it (native resolution, left untouched on disk)
    if extract_video_frame(video_path, str(cache_path), timestamp):
        try:
            img = Image.open(cache_path)
            return _thumbnail_copy(img)
        except Exception as e:
            logger.exception(f"Failed to process extracted frame: {e}")
            return None
    
    return None


def get_video_resolution(video_path: str) -> tuple[int, int] | None:
    """
    Get the native (width, height) of a video file directly from its stream
    metadata via ffprobe -- never from an extracted/cached frame, since those
    can be downscaled thumbnails (see get_video_frame_as_image's max_size).

    Args:
        video_path: Path to video file

    Returns:
        (width, height) tuple, or None if unable to determine
    """
    if not Path(video_path).exists():
        return None

    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=5, text=True)

        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().splitlines()[0].split("x")
            if len(parts) == 2:
                return int(parts[0]), int(parts[1])

        logger.warning(f"Could not determine resolution for {video_path}")
        return None

    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        logger.warning(f"Error getting resolution for {video_path}")
        return None
    except Exception as e:
        logger.exception(f"Error getting video resolution: {e}")
        return None


def get_video_duration(video_path: str) -> float:
    """
    Get the duration of a video file in seconds.
    
    Args:
        video_path: Path to video file
    
    Returns:
        Duration in seconds, or 0.0 if unable to determine
    """
    if not Path(video_path).exists():
        return 0.0
    
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1:noprint_names=1",
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, timeout=5, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
        else:
            logger.warning(f"Could not determine duration for {video_path}")
            return 0.0
            
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        logger.warning(f"Error getting duration for {video_path}")
        return 0.0
    except Exception as e:
        logger.exception(f"Error getting video duration: {e}")
        return 0.0


def is_video_file(file_path: str) -> bool:
    """Check if a file is a supported video file."""
    return Path(file_path).suffix.lower() in VIDEO_EXTENSIONS


def get_video_frame_path(video_path: str, timestamp: float = 0.0) -> str | None:
    """
    Get the cached native-resolution frame path for a video, extracting if needed.
    Used for color extraction and the lightbox preview. Shares the same cache
    file as get_video_frame_as_image, which never overwrites it with a
    downscaled copy (see that function's docstring).

    Args:
        video_path: Path to video file
        timestamp: Timestamp in seconds (default 0.0 for first frame)
    
    Returns:
        Path to cached frame PNG file, or None if extraction fails
    """
    cache_path = get_frame_cache_path(video_path, timestamp)
    
    # If already cached, return it
    if cache_path.exists():
        return str(cache_path)
    
    # Extract frame and cache it
    if extract_video_frame(video_path, str(cache_path), timestamp):
        return str(cache_path)
    
    return None

def is_image_file(file_path: str) -> bool:
    """Check if a file is a supported image file."""
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
    return Path(file_path).suffix.lower() in IMAGE_EXTENSIONS


def is_media_file(file_path: str) -> bool:
    """Check if a file is either a supported image or video file."""
    return is_image_file(file_path) or is_video_file(file_path)
