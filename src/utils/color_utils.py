#!/usr/bin/env python3
from __future__ import annotations
import logging
import hashlib
from pathlib import Path
from PIL import Image, ImageOps, ImageColor

logger = logging.getLogger(__name__)

def tint_image(src: str, tint_hex: str="#FF0000", strength: float = 0.8) -> str:
    """Apply grayscale+color tint to source image and return a cache file from hash of parameters to tinted image."""
    src_path = Path(src).expanduser()
    #temporal file in cache kwal with hash of parameters
    cache = Path.home() / ".cache" / "kwal" / "fastfetch_tinted"
    cache.mkdir(parents=True, exist_ok=True)

    dst = cache / f"{src_path.stem}-tinted{src_path.suffix}"

    im = Image.open(src_path).convert("RGBA")
    gray = ImageOps.grayscale(im).convert("RGBA")
    color = Image.new("RGBA", im.size, ImageColor.getrgb(tint_hex) + (255,))
    tinted = Image.blend(gray, color, float(strength))
    tinted.save(dst)
    return str(dst)