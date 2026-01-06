#!/usr/bin/env python3
from __future__ import annotations
import logging
import hashlib
from pathlib import Path
from PIL import Image, ImageOps, ImageColor
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

        im = Image.open(src_path).convert("RGBA")
        gray = ImageOps.grayscale(im).convert("RGBA")
        color = Image.new("RGBA", im.size, ImageColor.getrgb(tint_hex) + (255,))
        tinted = Image.blend(gray, color, float(strength))
        tinted.save(dst)
        logger.info("tint_image: created tinted image %s", dst)
        return str(dst)
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