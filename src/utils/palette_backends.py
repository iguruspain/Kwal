#!/usr/bin/env python3
"""Palette extraction backends (pywal16, material-you, imagemagick)."""
from __future__ import annotations

import colorsys
import logging
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from .color_utils import PaletteData, suppress_stdout
from .xdg_paths import kwal_cache_dir

logger = logging.getLogger(__name__)


def extract_pywal16(path: Path, **kwargs) -> PaletteData:
    """Extract palette using pywal, falling back to colorthief backends if 'wal' fails."""
    try:
        import pywal.colors as pywal_colors  # type: ignore
    except ImportError:
        raise ImportError("pywal16 (pywal module) is not installed.")

    cache = kwal_cache_dir() / "pywal"
    cache.mkdir(parents=True, exist_ok=True)

    light_mode = not kwargs.get("dark_mode", True)
    backend = "wal"

    try:
        data = pywal_colors.get(
            str(path),
            light=light_mode,
            backend=backend,
            c16="darken",
            cache_dir=str(cache),
        )
        logger.info("Successfully generated palette using 'wal' backend")
    except IndexError as e:
        logger.warning("pywal16 'wal' backend failed, trying fallback backends...")
        fallback_backends = ["modern_colorthief", "fast_colorthief", "colorthief"]
        success = False
        for fallback in fallback_backends:
            try:
                data = pywal_colors.get(
                    str(path),
                    light=light_mode,
                    backend=fallback,
                    c16="darken",
                    cache_dir=str(cache),
                )
                backend = fallback
                logger.info("Successfully generated palette using '%s' backend as fallback", fallback)
                success = True
                break
            except Exception as fallback_error:
                logger.debug("Fallback backend '%s' not available or failed: %s", fallback, fallback_error)
                continue
        if not success:
            logger.error("All backends failed. Original error: %s", e)
            raise ValueError(
                "pywal failed to generate palette with all available backends. "
                "Install 'modern-colorthief': pip install modern-colorthief"
            ) from e

    colors_dict = data.get("colors", {})
    colors_list = [str(colors_dict.get(f"color{i}", "#000000")) for i in range(16)]
    if len(colors_list) < 16:
        logger.warning("pywal generated less than 16 colors, padding with #000000")
        while len(colors_list) < 16:
            colors_list.append("#000000")
    colors_list = colors_list[:16]

    # Colors 1-6 are usually the accents
    accents = colors_list[1:7]

    return PaletteData(colors=colors_list, accents=accents, backend_used=f"pywal16({backend})", source_path=str(path))


def extract_material_you(path: Path, **kwargs) -> PaletteData:
    """Standard Material You implementation from a single auto-detected seed color."""
    try:
        from materialyoucolor.hct import Hct
        from materialyoucolor.quantize import QuantizeCelebi
        from materialyoucolor.scheme.scheme_content import SchemeContent
        from materialyoucolor.scheme.scheme_expressive import SchemeExpressive
        from materialyoucolor.scheme.scheme_fidelity import SchemeFidelity
        from materialyoucolor.scheme.scheme_fruit_salad import SchemeFruitSalad
        from materialyoucolor.scheme.scheme_monochrome import SchemeMonochrome
        from materialyoucolor.scheme.scheme_neutral import SchemeNeutral
        from materialyoucolor.scheme.scheme_rainbow import SchemeRainbow
        from materialyoucolor.scheme.scheme_tonal_spot import SchemeTonalSpot
        from materialyoucolor.scheme.scheme_vibrant import SchemeVibrant
        from materialyoucolor.score.score import Score, ScoreOptions
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
    contrast = 0.0

    # Extract dominant colors
    score_options = ScoreOptions(
        desired=7,
        fallback_color_argb=0xFF4285F4,
        filter=True,
    )

    ranked: list[int] = []
    try:
        with Image.open(path) as opened:
            img: Image.Image = opened.convert("RGBA")
            img.thumbnail((128, 128))
            pixels = list(img.getdata())
            pixel_list = [[r, g, b] for r, g, b, a in pixels if a > 128]

        with suppress_stdout():
            stats = QuantizeCelebi(pixel_list, 128)
            ranked = Score.score(stats, score_options)
    except Exception:
        logger.exception("Failed to quantize image for accents")

    seed_int = ranked[0] if ranked else 0xFF4285F4

    hct_seed = Hct.from_int(seed_int)
    try:
        scheme = scheme_class(hct_seed, is_dark, contrast)
    except (ZeroDivisionError, ValueError) as e:
        logger.warning("Scheme %s failed: %s. Falling back to TonalSpot.", selected_scheme_name, e)
        scheme = SchemeTonalSpot(hct_seed, is_dark, contrast)

    def hex_f(i: int | list[int]) -> str:
        if isinstance(i, list):
            return f"#{i[0]:02x}{i[1]:02x}{i[2]:02x}"
        return f"#{i & 0xFFFFFF:06x}"

    n = scheme.neutral_palette
    p = scheme.primary_palette
    s = scheme.secondary_palette
    t = scheme.tertiary_palette

    bg_tone = 10 if is_dark else 95
    fg_tone = 95 if is_dark else 10
    bg_color = hex_f(n.tone(bg_tone))
    fg_color = hex_f(n.tone(fg_tone))

    # 2 tones from each palette, grouped for visual coherence
    if is_dark:
        palette_colors = [
            hex_f(p.tone(80)), hex_f(p.tone(70)),
            hex_f(s.tone(70)), hex_f(s.tone(60)),
            hex_f(t.tone(60)), hex_f(t.tone(50)),
        ]
        bright_colors = [
            hex_f(p.tone(90)), hex_f(p.tone(85)),
            hex_f(s.tone(85)), hex_f(s.tone(80)),
            hex_f(t.tone(80)), hex_f(t.tone(75)),
        ]
    else:
        palette_colors = [
            hex_f(p.tone(40)), hex_f(p.tone(50)),
            hex_f(s.tone(50)), hex_f(s.tone(60)),
            hex_f(t.tone(60)), hex_f(t.tone(70)),
        ]
        bright_colors = [
            hex_f(p.tone(30)), hex_f(p.tone(35)),
            hex_f(s.tone(35)), hex_f(s.tone(40)),
            hex_f(t.tone(40)), hex_f(t.tone(45)),
        ]

    c = [
        bg_color,
        *palette_colors,
        fg_color,
        hex_f(n.tone(30 if is_dark else 85)),
        *bright_colors,
        hex_f(n.tone(90 if is_dark else 15)),
    ]

    accents = [hex_f(color) for color in ranked[:8]] if ranked else [hex_f(seed_int)]

    return PaletteData(
        colors=c,
        accents=accents,
        backend_used="material-you",
        source_path=str(path),
        seed=hex_f(seed_int),
    )


def extract_imagemagick(path: Path) -> PaletteData:
    """Extract palette using ImageMagick: 16 unique colors + best-scoring accent."""
    im_exe = shutil.which("magick") or shutil.which("convert")
    if not im_exe:
        raise OSError("ImageMagick not found")

    # 1. Generate up to 16 unique colors
    cmd_pal = [im_exe, str(path), "-resize", "128x128", "-colors", "16", "-unique-colors", "txt:-"]
    res_pal = subprocess.run(cmd_pal, capture_output=True, text=True, check=True)

    colors = []
    for line in res_pal.stdout.splitlines():
        if "#" in line:
            # Output format: 0,0: (87,81,87,255)  #575157  srgb(87,81,87)
            for part in line.split():
                if part.startswith("#") and len(part) >= 7:
                    colors.append(part[:7])
                    break

    # Keep only detected colors (no padding) so the UI can render a variable-length palette.

    # 2. Best accent via HSV scoring (s > 0.15, 0.15 < v < 0.95, score = s * v)
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
                if s > 0.15 and v > 0.15 and v < 0.95:
                    score = s * v
                    if score > best_score:
                        best_score = score
                        best_hex = f"#{hex_code}"
            except ValueError:
                continue

    return PaletteData(colors=colors[:16], accents=[best_hex], backend_used="imagemagick", source_path=str(path))
