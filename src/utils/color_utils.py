#!/usr/bin/env python3
"""Color helpers: palette extraction dispatch, tinting, and CSS color parsing."""
from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageColor
from PySide6.QtGui import QColor

from .file_utils import check_binary
from .xdg_paths import kwal_cache_dir

logger = logging.getLogger(__name__)


@dataclass
class PaletteData:
    colors: list[str]      # 16 Base colors
    accents: list[str]     # Accent colors
    backend_used: str      # 'pywal16', 'material-you', 'imagemagick'
    source_path: str       # Source image path
    seed: str = ""         # Seed color used (hex)


@contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout


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
        cache_root = kwal_cache_dir() / "fastfetch_tinted"
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
        cache_root = kwal_cache_dir() / "fastfetch_tinted"
        if cache_root.exists():
            shutil.rmtree(cache_root)
            logger.info("Cleared fastfetch tinted cache %s", cache_root)
    except Exception:
        logger.exception("Failed clearing fastfetch tinted cache")


def extract_palette(image_path: str, backend: str, **kwargs) -> PaletteData:
    """Extract a color palette from an image using the specified backend."""
    # Imported here to avoid a circular import (palette_backends imports from this module).
    from .palette_backends import extract_imagemagick, extract_material_you, extract_pywal16

    path = Path(image_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    logger.info("Extracting palette from %s using %s with kwargs: %s", path, backend, kwargs)

    if backend == "pywal16":
        return extract_pywal16(path, **kwargs)
    elif backend == "material-you":
        return extract_material_you(path, **kwargs)
    elif backend == "imagemagick":
        return extract_imagemagick(path)
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _extract_colors_matugen(image_path: str, count: int) -> list[str]:
    """Extract source colors by running matugen with --show-source-colors."""
    result = subprocess.run(
        ["matugen", "image", image_path, "--show-source-colors"],
        capture_output=True,
        text=True,
        check=True  # Raise if the command fails
    )

    # Extract hex codes from stdout
    found = re.findall(r"#[0-9a-fA-F]{6}", result.stdout)

    # Deduplicate preserving original order
    seen = set()
    unique = []
    for color in found:
        lower = color.lower()
        if lower not in seen:
            seen.add(lower)
            unique.append(lower)

    return unique[:count]


def _extract_colors_materialyoucolor(image_path: str, count: int) -> list[str]:
    """Extract top dominant colors using materialyoucolor's Celebi quantization."""
    from materialyoucolor.quantize import QuantizeCelebi
    from materialyoucolor.score.score import Score, ScoreOptions

    img = Image.open(image_path)
    img.thumbnail((128, 128))

    if img.mode != "RGB":
        img = img.convert("RGB")

    pixels = list(img.getdata())
    quantized = QuantizeCelebi(pixels, 128)

    options = ScoreOptions(desired=count)
    ranked_colors = Score.score(quantized, options)

    return [f"#{color & 0xFFFFFF:06x}" for color in ranked_colors]


def extract_wallpaper_top_colors(image_path: str, count: int = 4) -> list[str]:
    """Extract top scored colors from a wallpaper image.

    Prefers matugen (if installed) for consistency with the system theme engine.
    Falls back to materialyoucolor's Celebi quantization otherwise.
    Returns a list of hex color strings (e.g. ['#rrggbb', ...]).
    """
    path = Path(image_path).expanduser().resolve()
    if not path.exists() or not path.is_file():
        logger.error("extract_wallpaper_top_colors: image not found: %s", path)
        return []

    if check_binary("matugen"):
        try:
            colors = _extract_colors_matugen(str(path), count)
            if colors:
                logger.info("Scored colors via matugen: %s", colors)
                return colors
            logger.warning("matugen returned no colors, falling back to materialyoucolor (Celebi)")
        except Exception as e:
            logger.warning("matugen extraction failed (%s), falling back to materialyoucolor (Celebi)", e)
    else:
        logger.debug("matugen not found — using materialyoucolor (Celebi) for color extraction")

    try:
        colors = _extract_colors_materialyoucolor(str(path), count)
        logger.info("Scored colors via materialyoucolor (Celebi): %s", colors)
        return colors
    except ImportError:
        logger.error("materialyoucolor not installed. Cannot extract top colors.")
        return []
    except Exception as e:
        logger.error("Failed to extract wallpaper colors: %s", e)
        return []


def parse_css_color(color_str: str) -> QColor:
    """Robustly parse a CSS color string into a QColor object.

    Supports:
    - Hex: #RRGGBB, #AARRGGBB
    - Functional: rgb(r, g, b), rgba(r, g, b, a)
    - Named: transparent, red, etc.

    Handles float alpha (0.0-1.0) by converting to 0-255.
    """
    s = str(color_str).strip()
    if not s or s.lower() == "transparent":
        return QColor(0, 0, 0, 0)

    # Regex for rgba()/rgb() syntax that QColor might miss (especially float alpha)
    rgba_match = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d\.]+))?\s*\)', s, re.IGNORECASE)
    if rgba_match:
        r, g, b, a_str = rgba_match.groups()
        r, g, b = int(r), int(g), int(b)
        alpha = 255
        if a_str:
            try:
                val = float(a_str)
                # CSS alpha is 0.0-1.0; values above 1.0 are treated as 0-255 bytes.
                if val <= 1.0:
                    alpha = int(val * 255)
                else:
                    alpha = int(val)

                # Clamp
                alpha = max(0, min(255, alpha))
            except ValueError:
                pass
        return QColor(r, g, b, alpha)

    # Fallback to QColor's native parsing (hex, color names, etc.)
    c = QColor(s)
    if c.isValid():
        return c

    return QColor()  # Invalid


def format_css_color(color: str | QColor) -> str:
    """Format a color for CSS usage.

    - If Alpha is 255: Returns Hex #RRGGBB
    - If Alpha < 255: Returns rgba(r, g, b, 0.X)
    """
    if isinstance(color, QColor):
        c = color
    else:
        c = parse_css_color(color)

    if not c.isValid():
        return str(color)

    if c.alpha() == 255:
        # Solid -> pure RGB hex
        return f"#{c.red():02x}{c.green():02x}{c.blue():02x}"
    else:
        # Transparent -> rgba with alpha rounded to 3 decimals
        a_float = round(c.alpha() / 255.0, 3)
        return f"rgba({c.red()}, {c.green()}, {c.blue()}, {a_float})"
