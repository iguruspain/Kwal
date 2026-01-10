#!/usr/bin/env python3
from __future__ import annotations

import colorsys
import hashlib
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, cast

from PIL import Image, ImageColor

from src.models.models import PaletteData
from src.utils.file_utils import check_binary

logger = logging.getLogger(__name__)


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


def extract_palette(image_path: str, backend: str, **kwargs) -> PaletteData:
    """Extract a color palette from an image using the specified backend."""
    path = Path(image_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    logger.info("Extracting palette from %s using %s", path, backend)

    if backend == "pywal16":
        return _extract_pywal16(path)
    elif backend == "material-you":
        return _extract_material_you(path, **kwargs)
    elif backend == "imagemagick":
        return _extract_imagemagick(path)
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _extract_pywal16(path: Path) -> PaletteData:
    try:
        import pywal.colors as pywal_colors # type: ignore
    except ImportError:
        raise ImportError("pywal16 (pywal module) is not installed.")

    # pywal16 needs a valid cache_dir even if we don't care much, or handles None poorly in some versions
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "kwal" / "pywal"
    cache.mkdir(parents=True, exist_ok=True)
    
    # pywal16 returns a dict. In some pywal versions or on certain images
    # the backend can raise IndexError (internal color list shorter than expected).
    # Catch such failures and fallback to the ImageMagick extractor.
    try:
        data = pywal_colors.get(str(path), cache_dir=str(cache))
    except IndexError as e:
        logger.warning("pywal returned incomplete color data for %s: %s. Falling back to ImageMagick.", path, e)
        return _extract_imagemagick(path)
    except Exception:
        logger.exception("pywal.get failed for %s, falling back to ImageMagick", path)
        return _extract_imagemagick(path)

    colors_dict = data.get('colors', {})
    # Extract color0 to color15, defaulting to #000000 if missing
    colors_list = [str(colors_dict.get(f"color{i}", "#000000")) for i in range(16)]

    # Accents: Use a selection of the generated colors (1-6 are usually the accents)
    accents = colors_list[1:7]

    return PaletteData(colors=colors_list, accents=accents, backend_used="pywal16", source_path=str(path))

# def _extract_material_you(path: Path, **kwargs) -> PaletteData:
#     try:
#         from materialyoucolor.quantize import QuantizeCelebi
#         from materialyoucolor.score.score import Score
#         from materialyoucolor.hct import Hct
#         from materialyoucolor.scheme.scheme_tonal_spot import SchemeTonalSpot
#         from materialyoucolor.scheme.scheme_vibrant import SchemeVibrant
#         from materialyoucolor.scheme.scheme_expressive import SchemeExpressive
#         from materialyoucolor.scheme.scheme_content import SchemeContent
#         from materialyoucolor.scheme.scheme_fruit_salad import SchemeFruitSalad
#         from materialyoucolor.scheme.scheme_rainbow import SchemeRainbow
#         from materialyoucolor.scheme.scheme_monochrome import SchemeMonochrome
#         from materialyoucolor.scheme.scheme_neutral import SchemeNeutral
#         from materialyoucolor.scheme.scheme_fidelity import SchemeFidelity
#     except ImportError:
#         raise ImportError("materialyoucolor module is not installed.")

#     # Mapeo de nombres de QML a clases de la librería
#     schemes = {
#         "TonalSpot": SchemeTonalSpot, "Vibrant": SchemeVibrant,
#         "Expressive": SchemeExpressive, "Content": SchemeContent,
#         "FruitSalad": SchemeFruitSalad, "Rainbow": SchemeRainbow,
#         "Monochrome": SchemeMonochrome, "Neutral": SchemeNeutral,
#         "Fidelity": SchemeFidelity,
#     }

#     # Inputs externos
#     selected_scheme_name = kwargs.get("scheme", "TonalSpot")
#     scheme_class = schemes.get(selected_scheme_name, SchemeTonalSpot)
#     is_dark = kwargs.get("dark_mode", True)
#     contrast = float(kwargs.get("contrast", 0.0))
#     colorfulness = float(kwargs.get("colorfulness", 1.0))
#     brightness = float(kwargs.get("brightness", 0.8))
#     override_seed_hex = kwargs.get("seed_color", None)

#     # Determinación del color semilla (Seed Color)
#     if override_seed_hex:
#         rgb = ImageColor.getrgb(override_seed_hex)
#         seed_int = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]
#     else:
#         # with Image.open(path) as img:
#         #     img = img.convert("RGBA").thumbnail((128, 128))
#         #     pixels = list(img.getdata())
        
#         # NEW (Fixed)
#         with Image.open(path) as img:
#             img = img.convert("RGBA")
#             img.thumbnail((128, 128))  # Modifies img in-place
#             pixels = list(img.getdata()) # img is still the Image object
#             pixel_ints = [(r << 16) | (g << 8) | b for r, g, b, a in pixels if a > 128]
        
#         with suppress_stdout():
#             stats = QuantizeCelebi(pixel_ints, 128)
#             ranked = Score.score(stats)
#             seed_int = ranked[0] if ranked else 0xff4285F4
    
#     print(f"Seed int: {seed_int}")

#     # Aplicar modificadores de Colorfulness y Brightness al HCT
#     hct_seed = Hct.from_int(seed_int)
#     adjusted_hct = Hct.from_hct(
#         hct_seed.hue,
#         hct_seed.chroma * kwargs.get("colorfulness", 1.0),
#         hct_seed.tone * kwargs.get("brightness", 0.8)
#     )

#     scheme_class = schemes.get(kwargs.get("scheme", "TonalSpot"))
#     scheme = scheme_class(adjusted_hct, is_dark, contrast)
#     def hex_f(i: int) -> str: return f"#{i & 0xFFFFFF:06x}"

#     # Generación de 16 colores ANSI
#     p, s, t, n = scheme.primary_palette, scheme.secondary_palette, scheme.tertiary_palette, scheme.neutral_palette
#     c = [
#         hex_f(n.get_tone(10 if is_dark else 95)), hex_f(p.get_tone(40 if is_dark else 60)),
#         hex_f(s.get_tone(40 if is_dark else 60)), hex_f(t.get_tone(40 if is_dark else 60)),
#         hex_f(p.get_tone(50 if is_dark else 50)), hex_f(s.get_tone(50 if is_dark else 50)),
#         hex_f(t.get_tone(50 if is_dark else 50)), hex_f(n.get_tone(80 if is_dark else 20)),
#         hex_f(n.get_tone(30 if is_dark else 85)), hex_f(p.get_tone(70 if is_dark else 30)),
#         hex_f(s.get_tone(70 if is_dark else 30)), hex_f(t.get_tone(70 if is_dark else 30)),
#         hex_f(p.get_tone(80 if is_dark else 40)), hex_f(s.get_tone(80 if is_dark else 40)),
#         hex_f(t.get_tone(80 if is_dark else 40)), hex_f(n.get_tone(95 if is_dark else 10)),
#     ]

#     # Lista de acentos para el QML (usamos los dominantes detectados)
#     accents = [hex_f(color) for color in ranked[:8]] if not override_seed_hex else [override_seed_hex]

#     return PaletteData(colors=c, accents=accents, backend_used="material-you", source_path=str(path))

def _extract_material_you(path: Path, **kwargs) -> PaletteData:
    try:
        from materialyoucolor.quantize import QuantizeCelebi
        from materialyoucolor.score.score import Score
        from materialyoucolor.hct import Hct
        from materialyoucolor.scheme.scheme_tonal_spot import SchemeTonalSpot
        from materialyoucolor.scheme.scheme_vibrant import SchemeVibrant
        from materialyoucolor.scheme.scheme_expressive import SchemeExpressive
        from materialyoucolor.scheme.scheme_content import SchemeContent
        from materialyoucolor.scheme.scheme_fruit_salad import SchemeFruitSalad
        from materialyoucolor.scheme.scheme_rainbow import SchemeRainbow
        from materialyoucolor.scheme.scheme_monochrome import SchemeMonochrome
        from materialyoucolor.scheme.scheme_neutral import SchemeNeutral
        from materialyoucolor.scheme.scheme_fidelity import SchemeFidelity
    except ImportError:
        raise ImportError("materialyoucolor module is not installed.")

    schemes = {
        "TonalSpot": SchemeTonalSpot, "Vibrant": SchemeVibrant,
        "Expressive": SchemeExpressive, "Content": SchemeContent,
        "FruitSalad": SchemeFruitSalad, "Rainbow": SchemeRainbow,
        "Monochrome": SchemeMonochrome, "Neutral": SchemeNeutral,
        "Fidelity": SchemeFidelity,
    }

    selected_scheme_name = kwargs.get("scheme", "TonalSpot")
    scheme_class = schemes.get(selected_scheme_name, SchemeTonalSpot)
    is_dark = kwargs.get("dark_mode", True)
    contrast = float(kwargs.get("contrast", 0.0))
    override_seed_hex = kwargs.get("seed_color", None)
    
    ranked = []

    if override_seed_hex:
        rgb = ImageColor.getrgb(override_seed_hex)
        seed_int = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]
    else:
        with Image.open(path) as img:
            img = img.convert("RGBA")
            img.thumbnail((128, 128)) 
            pixels = list(img.getdata())
            # FIX: QuantizeCelebi expects a list of lists [r, g, b]
            pixel_list = [[r, g, b] for r, g, b, a in pixels if a > 128]
        
        with suppress_stdout():
            # Pass the list of [r,g,b] lists
            stats = QuantizeCelebi(pixel_list, 128)
            ranked = Score.score(stats)
            seed_int = ranked[0] if ranked else 0xff4285F4

    hct_seed = Hct.from_int(seed_int)
    adjusted_hct = Hct.from_hct(
        hct_seed.hue,
        hct_seed.chroma * float(kwargs.get("colorfulness", 1.0)),
        hct_seed.tone * float(kwargs.get("brightness", 0.8))
    )

    scheme = scheme_class(adjusted_hct, is_dark, contrast)
    
    def hex_f(i: int | list) -> str:
        if isinstance(i, list):
            return f"#{i[0]:02x}{i[1]:02x}{i[2]:02x}"
        return f"#{i & 0xFFFFFF:06x}"

    p, s, t, n = scheme.primary_palette, scheme.secondary_palette, scheme.tertiary_palette, scheme.neutral_palette
    
    c = [
        hex_f(n.tone(10 if is_dark else 95)), hex_f(p.tone(40 if is_dark else 60)),
        hex_f(s.tone(40 if is_dark else 60)), hex_f(t.tone(40 if is_dark else 60)),
        hex_f(p.tone(50 if is_dark else 50)), hex_f(s.tone(50 if is_dark else 50)),
        hex_f(t.tone(50 if is_dark else 50)), hex_f(n.tone(80 if is_dark else 20)),
        hex_f(n.tone(30 if is_dark else 85)), hex_f(p.tone(70 if is_dark else 30)),
        hex_f(s.tone(70 if is_dark else 30)), hex_f(t.tone(70 if is_dark else 30)),
        hex_f(p.tone(80 if is_dark else 40)), hex_f(s.tone(80 if is_dark else 40)),
        hex_f(t.tone(80 if is_dark else 40)), hex_f(n.tone(95 if is_dark else 10)),
    ]

    if override_seed_hex:
        accents = [override_seed_hex]
    elif ranked:
        accents = [hex_f(color) for color in ranked[:8]]
    else:
        accents = [hex_f(seed_int)]

    return PaletteData(
        colors=c, 
        accents=accents, 
        backend_used="material-you", 
        source_path=str(path)
    )

def _extract_imagemagick(path: Path) -> PaletteData:
    im_exe = shutil.which("magick") or shutil.which("convert")
    if not im_exe:
        raise OSError("ImageMagick not found")

    # 1. Generate 16 colors
    # -unique-colors gets all colors found (which are 16 max due to -colors 16)
    cmd_pal = [im_exe, str(path), "-resize", "128x128", "-colors", "16", "-unique-colors", "txt:-"]
    res_pal = subprocess.run(cmd_pal, capture_output=True, text=True, check=True)
    
    colors = []
    for line in res_pal.stdout.splitlines():
        if "#" in line:
            # Output format: 0,0: (87,81,87,255)  #575157  srgb(87,81,87)
            # We look for #RRGGBB
            parts = line.split()
            for p in parts:
                if p.startswith("#") and len(p) >= 7:
                    # Take first 7 chars (#RRGGBB), ignore alpha if any
                    colors.append(p[:7])
                    break
    
    # Fill if missing (if image has fewer than 16 colors)
    while len(colors) < 16:
        colors.append(colors[-1] if colors else "#000000")
    
    # 2. Calculate best accent (Scoring logic ported from Gawk)
    # histogram:info: Output format: 
    #       120: ( 77,140, 84) #4D8C54 srgb(77,140,84)
    cmd_acc = [im_exe, str(path), "-resize", "64x64", "+dither", "-colors", "8", "-format", "%c", "histogram:info:"]
    res_acc = subprocess.run(cmd_acc, capture_output=True, text=True, check=True)
    
    best_score = -1.0
    best_hex = colors[0]
    hex_pattern = re.compile(r"#([0-9A-Fa-f]{6})")
    
    for line in res_acc.stdout.splitlines():
        match = hex_pattern.search(line)
        if match:
            hex_code = match.group(1)
            try:
                r = int(hex_code[0:2], 16) / 255.0
                g = int(hex_code[2:4], 16) / 255.0
                b = int(hex_code[4:6], 16) / 255.0
                h, s, v = colorsys.rgb_to_hsv(r, g, b)
                
                # Logic: s > 0.15 && v > 0.15 && v < 0.95
                if s > 0.15 and v > 0.15 and v < 0.95:
                    score = s * v
                    if score > best_score:
                        best_score = score
                        # Avoid duplicates in accents if we were collecting multiple, 
                        # but here we just want the best one.
                        best_hex = f"#{hex_code}"
            except ValueError:
                continue

    return PaletteData(colors=colors[:16], accents=[best_hex], backend_used="imagemagick", source_path=str(path))
