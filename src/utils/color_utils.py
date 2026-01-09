#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from PIL import ImageColor

logger = logging.getLogger(__name__)


def _normalize_tint(tint_hex: str | None) -> str | None:
    """Validate `tint_hex`.

    Return the original string if valid. If `tint_hex` is None, the string "transparent",
    or cannot be parsed, return `None`.
    """
    if not tint_hex:
        return None
    if str(tint_hex).lower() == "transparent":
        return None
    s = str(tint_hex).strip()
    # Accept #AARRGGBB by converting to ImageMagick-friendly rgba(r,g,b,a)
    if s.startswith("#") and len(s) == 9:
        try:
            a = int(s[1:3], 16)
            r = int(s[3:5], 16)
            g = int(s[5:7], 16)
            b = int(s[7:9], 16)
            a_f = round(a / 255.0, 3)
            return f"rgba({r},{g},{b},{a_f})"
        except Exception:
            logger.debug("tint_image: failed parsing ARGB hex '%s'", s)
            return None

    # For all other formats, let Pillow validate (e.g. #RRGGBB, color names, rgb(...))
    try:
        ImageColor.getrgb(s)
        return s
    except Exception:
        logger.debug("tint_image: invalid tint '%s', skipping tinted generation", tint_hex)
        return None


def tint_image(src: str, tint_hex: str, strength: float = 0.8) -> str:
    """Apply grayscale+color tint to source image and return a deterministic cached file path."""
    try:
        src_path = Path(src).expanduser().resolve()
        if not src_path.exists():
            logger.error("tint_image: source does not exist: %s", src_path)
            return ""

        # Validate tint
        valid_tint = _normalize_tint(tint_hex)
        if valid_tint is None:
            logger.debug("tint_image: tint is None or invalid, skipping generation")
            return ""

        # Setup cache
        cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "kwal" / "fastfetch_tinted"
        cache_root.mkdir(parents=True, exist_ok=True)

        # Deterministic name
        key = f"{str(src_path)}|{valid_tint}|{float(strength)}"
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        dst = cache_root / f"{src_path.stem}-{digest}.png"

        if dst.exists():
            logger.debug("tint_image: using cached tinted image %s", dst)
            return str(dst)

        # ImageMagick backend
        im_exe = shutil.which("magick") or shutil.which("convert")
        if not im_exe:
            logger.error("tint_image: ImageMagick not found")
            return ""

        tint_pct = max(0, min(100, int(float(strength) * 100)))
        
        # Use temp file for intermediate grayscale
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png", dir=str(cache_root)) as tmpf:
            tmp_gray = Path(tmpf.name)
            
        try:
            # 1. Grayscale
            subprocess.run([im_exe, str(src_path), "-colorspace", "gray", str(tmp_gray)], check=True)
            # 2. Tint
            subprocess.run([im_exe, str(tmp_gray), "-fill", valid_tint, "-tint", str(tint_pct), str(dst)], check=True)
            
            logger.info("Created tinted image: %s", dst)
            return str(dst)
        except subprocess.CalledProcessError:
            logger.exception("ImageMagick failed for %s", src_path)
            return ""
        finally:
            try:
                tmp_gray.unlink(missing_ok=True)
            except Exception:
                pass

    except Exception:
        logger.exception("tint_image failed for %s", src)
        return ""


def clear_fastfetch_tinted_cache() -> None:
    """Remove the fastfetch_tinted cache directory entirely."""
    try:
        cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "kwal" / "fastfetch_tinted"
        if cache_root.exists():
            shutil.rmtree(cache_root)
            logger.info("Cleared fastfetch tinted cache %s", cache_root)
    except Exception:
        logger.exception("Failed clearing fastfetch tinted cache")
