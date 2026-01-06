#!/usr/bin/env python3
from __future__ import annotations
import logging
import hashlib
from pathlib import Path
from PIL import ImageColor
import subprocess
import tempfile
import shutil
from typing import Optional
import os

logger = logging.getLogger(__name__)

def _normalize_tint(tint_hex: Optional[str]) -> Optional[str]:
    """Validate `tint_hex`.

    Return the original string if valid. If `tint_hex` is None, the string "transparent",
    or cannot be parsed, return `None` to indicate that no tinted image should be produced.
    """
    if not tint_hex:
        return None
    if str(tint_hex).lower() == "transparent":
        return None
    try:
        ImageColor.getrgb(tint_hex)
        return tint_hex
    except Exception:
        logger.debug("tint_image: invalid tint '%s', skipping tinted generation", tint_hex)
        return None


def tint_image(src: str, tint_hex: str, strength: float = 0.8) -> str:
    """Apply grayscale+color tint to source image and return a deterministic cached file path.

    Cache filename is derived from a sha1 of (absolute src path, tint_hex, strength) to avoid collisions.
    Returns the absolute filesystem path to the generated tinted image, or an empty string on error.
    """
    try:
        src_path = Path(src).expanduser().resolve()
        if not src_path.exists():
            logger.error("tint_image: source does not exist: %s", src_path)
            return ""

        # create cache directory under XDG_CACHE_HOME if set
        cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "kwal" / "fastfetch_tinted"
        cache_root.mkdir(parents=True, exist_ok=True)

        # validate tint value; None means no tinted output requested/possible
        tint_hex = _normalize_tint(tint_hex)
        if tint_hex is None:
            logger.debug("tint_image: tint is None or invalid, skipping generation for %s", src_path)
            return ""

        # deterministic name based on parameters
        key = f"{str(src_path)}|{tint_hex}|{float(strength)}"
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        # always write tinted output as PNG to preserve alpha and avoid format issues
        dst = cache_root / f"{src_path.stem}-{digest}.png"

        # if already exists, return quickly
        if dst.exists():
            logger.debug("tint_image: using cached tinted image %s", dst)
            return str(dst)

        # Use ImageMagick (`magick` or `convert`) as the primary tinting backend
        im_exe = shutil.which("magick") or shutil.which("convert")
        if im_exe:
            # ImageMagick `-tint` expects a percentage value in the range 0-100
            tint_pct = max(0, min(100, int(float(strength) * 100)))
            # Create a temporary grayscale intermediate and apply the tint into `dst`
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=str(cache_root)) as tmpf:
                tmp_gray = Path(tmpf.name)
            try:
                # Convert source image to grayscale (intermediate)
                cmd1 = [im_exe, str(src_path), "-colorspace", "gray", str(tmp_gray)]
                subprocess.run(cmd1, check=True)
                # Apply tint color to the grayscale intermediate
                cmd2 = [im_exe, str(tmp_gray), "-fill", tint_hex, "-tint", str(tint_pct), str(dst)]
                subprocess.run(cmd2, check=True)
                logger.info("tint_image: created tinted image via ImageMagick %s", dst)
                return str(dst)
            except subprocess.CalledProcessError:
                logger.exception("tint_image: ImageMagick failed for %s", src_path)
                return ""
            finally:
                try:
                    tmp_gray.unlink(missing_ok=True)
                except Exception:
                    pass
        # If ImageMagick is unavailable or failed, log an error and return an empty result
        logger.error("tint_image: ImageMagick not available or failed; cannot generate tinted image for %s", src_path)
        return ""
    except Exception:
        logger.exception("tint_image failed for %s with tint %s", src, tint_hex)
        return ""


def clear_fastfetch_tinted_cache() -> None:
    """Remove the fastfetch_tinted cache directory entirely.

    Safe to call on exit; logs exceptions.
    """
    try:
        cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "kwal" / "fastfetch_tinted"
        if cache_root.exists():
            import shutil
            shutil.rmtree(cache_root)
            logger.info("Cleared fastfetch tinted cache %s", cache_root)
    except Exception:
        logger.exception("Failed clearing fastfetch tinted cache")