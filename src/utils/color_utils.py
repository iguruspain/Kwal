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
from typing import Optional, cast, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.models import PaletteData
from PIL import Image, ImageColor
from PySide6.QtGui import QColor

from .file_utils import check_binary

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

    logger.info("Extracting palette from %s using %s with kwargs: %s", path, backend, kwargs)

    if backend == "pywal16":
        return _extract_pywal16(path, **kwargs)
    elif backend == "material-you-kwal":
        return _extract_material_you_kwal(path, **kwargs)
    elif backend == "material-you":
        return _extract_material_you(path, **kwargs)
    elif backend == "imagemagick":
        return _extract_imagemagick(path)
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _extract_colors_matugen(image_path: str, count: int) -> list[str]:
    """Extract scored colors by running matugen in dry-run mode and parsing hex output.

    RUST_LOG=debug is required so matugen emits the ranked-color DEBUG lines
    regardless of the environment from which the app was launched (e.g. KDE).
    """
    env = os.environ.copy()
    env["RUST_LOG"] = "debug"
    result = subprocess.run(
        ["matugen", "image", image_path, "-d", "--dry-run", "--source-color-index", "0"],
        capture_output=True,
        text=True,
        env=env,
    )
    combined = result.stdout + result.stderr
    found = re.findall(r"#[0-9a-fA-F]{6}", combined)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
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



def _extract_pywal16(path: Path, **kwargs) -> PaletteData:
    """
    Extract palette using pywal backend with automatic fallback to alternative backend.
    If 'wal' backend fails (ImageMagick issues), falls back to 'colorthief' or 'fast_colorthief'.
    """
    try:
        import pywal.colors as pywal_colors # type: ignore
    except ImportError:
        raise ImportError("pywal16 (pywal module) is not installed.")

    # pywal needs a valid cache_dir
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "kwal" / "pywal"
    cache.mkdir(parents=True, exist_ok=True)
    
    # Get parameters from kwargs
    is_dark = kwargs.get("dark_mode", True)
    light_mode = not is_dark
    backend = 'wal'
    
    # Try with 'wal' backend first
    try:
        from ..models.models import PaletteData
        data = pywal_colors.get(
            str(path), 
            light=light_mode,
            backend=backend,
            c16='darken',
            cache_dir=str(cache)
        )
        logger.info("Successfully generated palette using 'wal' backend")
        
    except IndexError as e:
        # Fallback: Try alternative backends (colorthief, fast_colorthief, modern_colorthief)
        logger.warning("pywal16 'wal' backend failed with this image, trying fallback backends...")
        
        fallback_backends = ['modern_colorthief', 'fast_colorthief', 'colorthief']
        success = False
        
        for fallback in fallback_backends:
            try:
                data = pywal_colors.get(
                    str(path),
                    light=light_mode,
                    backend=fallback,
                    c16='darken',
                    cache_dir=str(cache)
                )
                backend = fallback
                logger.info("Successfully generated palette using '%s' backend as fallback", fallback)
                success = True
                break
            except (ImportError, Exception) as fallback_error:
                logger.debug("Fallback backend '%s' not available or failed: %s", fallback, fallback_error)
                continue
        
        if not success:
            logger.error("All backends failed. Original error: %s", e)
            raise ValueError(f"pywal failed to generate palette with all available backends. Install 'modern-colorthief': pip install modern-colorthief") from e

    colors_dict = data.get('colors', {})
    # Extract color0 to color15
    colors_list = [str(colors_dict.get(f"color{i}", "#000000")) for i in range(16)]
    
    # Ensure we have exactly 16 colors
    if len(colors_list) < 16:
        logger.warning("pywal generated less than 16 colors, padding with #000000")
        while len(colors_list) < 16:
            colors_list.append("#000000")
    colors_list = colors_list[:16]

    # Accents: Use a selection of the generated colors (1-6 are usually the accents)
    accents = colors_list[1:7]

    return PaletteData(colors=colors_list, accents=accents, backend_used=f"pywal16({backend})", source_path=str(path))

def _extract_material_you_kwal(path: Path, **kwargs) -> PaletteData:
    """
    Kwal's Material You implementation.
    Preserves image color variety by using ranked colors directly,
    with scheme-specific adjustments for colorfulness.
    """
    from ..models.models import PaletteData
    try:
        from materialyoucolor.quantize import QuantizeCelebi
        from materialyoucolor.score.score import Score, ScoreOptions
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
    # Amplify contrast for more visible effect: map 0.0-1.0 user input to -1.0 to 1.0 Material You range
    contrast_input = float(kwargs.get("contrast", 0.0))
    contrast = (contrast_input * 2.0) - 1.0  # Maps 0.0->-1.0, 0.5->0.0, 1.0->1.0
    override_seed_hex = kwargs.get("seed_color", None)
    colorfulness = float(kwargs.get("colorfulness", 1.0))
    brightness = float(kwargs.get("brightness", 0.8))
    
    # Extract dominant colors from image with ScoreOptions for better results
    # desired=7 to get more diverse colors like kde-material-you-colors
    score_options = ScoreOptions(
        desired=7,
        fallback_color_argb=0xFF4285F4,
        filter=True,
        #dislike_filter=True,
    )
    
    ranked: list[int] = []
    try:
        with Image.open(path) as img:
            img = img.convert("RGBA")
            img.thumbnail((128, 128)) 
            pixels = list(img.getdata())
            pixel_list = [[r, g, b] for r, g, b, a in pixels if a > 128]
        
        with suppress_stdout():
            stats = QuantizeCelebi(pixel_list, 128)
            ranked = Score.score(stats, score_options)
    except Exception:
        logger.exception("Failed to quantize image for accents")

    if override_seed_hex:
        try:
            rgb = ImageColor.getrgb(override_seed_hex)
            seed_int = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]
            logger.info("Using override seed color: %s (ARGB: %s)", override_seed_hex, hex(seed_int))
        except ValueError:
             logger.warning("Invalid seed color %s, falling back to auto", override_seed_hex)
             seed_int = ranked[0] if ranked else 0xFF4285F4
    else:
        seed_int = ranked[0] if ranked else 0xFF4285F4

    # Apply brightness to seed tone before creating scheme
    # Don't apply colorfulness here - we'll apply it per-color later
    hct_seed = Hct.from_int(seed_int)
    
    # For Fidelity, use the seed directly without adjustments to avoid division by zero
    if selected_scheme_name == "Fidelity":
        adjusted_hct = hct_seed
    else:
        adjusted_hct = Hct.from_hct(
            hct_seed.hue,
            hct_seed.chroma,
            hct_seed.tone * brightness
        )

    # Create scheme with error handling for edge cases
    try:
        scheme = scheme_class(adjusted_hct, is_dark, contrast)
    except (ZeroDivisionError, ValueError) as e:
        logger.warning("Scheme %s failed with error: %s. Falling back to TonalSpot.", selected_scheme_name, e)
        scheme = SchemeTonalSpot(adjusted_hct, is_dark, contrast)
        selected_scheme_name = "TonalSpot"
    
    n = scheme.neutral_palette
    
    def hex_f(i: int | list[int]) -> str:
        if isinstance(i, list):
            return f"#{i[0]:02x}{i[1]:02x}{i[2]:02x}"
        return f"#{i & 0xFFFFFF:06x}"
    
    def adjust_color_hct(argb: int, chroma_mult: float, tone_mult: float, target_tone: int, bright_mult: float) -> str:
        """Adjust a color's chroma and tone using HCT color space."""
        hct = Hct.from_int(argb)
        # Apply colorfulness multiplier to chroma
        new_chroma = max(0, min(120, hct.chroma * chroma_mult))
        # Apply brightness and tone multiplier
        new_tone = max(0, min(100, (target_tone * bright_mult) * tone_mult))
        # Create new HCT with adjusted values
        adjusted = Hct.from_hct(hct.hue, new_chroma, new_tone)
        return hex_f(adjusted.to_int())
    
    def get_luminance(hex_color: str) -> float:
        """Calculate relative luminance of a color for sorting."""
        rgb = ImageColor.getrgb(hex_color)
        # sRGB to linear RGB
        def to_linear(c: int) -> float:
            v = c / 255.0
            return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        r, g, b = to_linear(rgb[0]), to_linear(rgb[1]), to_linear(rgb[2])
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    def get_hue(hex_color: str) -> float:
        """Extract HUE from color for rainbow-like sorting."""
        rgb = ImageColor.getrgb(hex_color)
        hct = Hct.from_int((rgb[0] << 16) | (rgb[1] << 8) | rgb[2])
        return hct.hue

    # Background and foreground from neutral palette - affected by contrast
    bg_tone = 10 if is_dark else 95
    fg_tone = 95 if is_dark else 10
    bg_color = hex_f(n.tone(bg_tone))
    fg_color = hex_f(n.tone(fg_tone))
    
    # Determine color generation strategy:
    # - If user selected a seed (accent click): use scheme palettes exclusively
    # - Otherwise: use ranked colors from image (including Fidelity)
    use_scheme_palettes = bool(override_seed_hex)
    
    if use_scheme_palettes:
        # User selected an accent - generate all colors from the scheme
        logger.info("Generating palette from selected seed using scheme palettes")
        colors_to_use = []
    else:
        # Use ranked colors from image
        colors_to_use = ranked
    
    # Build palette using dominant colors from image
    # Apply scheme transformations based on the selected tone
    palette_colors: list[str] = []
    
    # Tones for normal colors (color1-6) and bright variants (color9-14)
    normal_tone_mult = 0.85 if is_dark else 1.1
    bright_tone_mult = 1.15 if is_dark else 0.75
    
    # Get scheme-specific chroma multiplier
    def get_scheme_chroma_factor(scheme_name: str) -> float:
        """Return chroma multiplier based on scheme type."""
        chroma_factors = {
            "Rainbow": 1.4,
            "FruitSalad": 1.4,
            "Vibrant": 1.3,
            "Expressive": 1.2,
            "TonalSpot": 1.0,
            "Content": 1.0,
            "Fidelity": 1.0,  # Fidelity = faithful to original colors, no boost
            "Neutral": 0.6,
            "Monochrome": 0.05,
        }
        return chroma_factors.get(scheme_name, 1.0)
    
    scheme_chroma = get_scheme_chroma_factor(selected_scheme_name)
    
    # Use up to 6 colors for main palette slots
    num_ranked = len(colors_to_use)
    
    # Define tones to extract from scheme palettes when using scheme-based generation
    if is_dark:
        scheme_normal_tones = [80, 70, 60, 50, 40, 30]
        scheme_bright_tones = [90, 85, 80, 75, 70, 65]
    else:
        scheme_normal_tones = [40, 50, 60, 70, 80, 90]
        scheme_bright_tones = [30, 35, 40, 45, 50, 55]
    
    for i in range(6):
        if i < num_ranked:
            # Use ranked color from image with adjustments
            total_chroma_mult = colorfulness * scheme_chroma
            palette_colors.append(adjust_color_hct(colors_to_use[i], total_chroma_mult, normal_tone_mult, 50, brightness))
        else:
            # Use scheme palettes
            palettes = [scheme.primary_palette, scheme.secondary_palette, scheme.tertiary_palette]
            pal = palettes[i % 3]
            tone = scheme_normal_tones[i] if use_scheme_palettes else (40 + (i // 3) * 10 if is_dark else 60 - (i // 3) * 10)
            palette_colors.append(hex_f(pal.tone(tone)))
    
    # Sort palette colors by HUE for visual coherence (rainbow-like)
    palette_colors.sort(key=get_hue)
    
    # Build bright variants of the palette colors
    bright_colors: list[str] = []
    for i in range(6):
        if i < num_ranked:
            total_chroma_mult = colorfulness * scheme_chroma
            bright_colors.append(adjust_color_hct(colors_to_use[i], total_chroma_mult, bright_tone_mult, 70, brightness))
        else:
            palettes = [scheme.primary_palette, scheme.secondary_palette, scheme.tertiary_palette]
            pal = palettes[i % 3]
            tone = scheme_bright_tones[i] if use_scheme_palettes else (70 + (i // 3) * 10 if is_dark else 30 - (i // 3) * 5)
            bright_colors.append(hex_f(pal.tone(max(10, min(90, tone)))))
    
    # Sort bright colors by HUE to match palette_colors order
    bright_colors.sort(key=get_hue)
    
    # Final 16-color palette structure:
    # color0: background
    # color1-6: main palette colors (from ranked image colors)
    # color7: foreground
    # color8: background variant (slightly lighter/darker)
    # color9-14: bright variants of main colors
    # color15: foreground variant
    c = [
        bg_color,                              # color0: background
        palette_colors[0],                     # color1: main color 1
        palette_colors[1],                     # color2: main color 2
        palette_colors[2],                     # color3: main color 3
        palette_colors[3],                     # color4: main color 4
        palette_colors[4],                     # color5: main color 5
        palette_colors[5],                     # color6: main color 6
        fg_color,                              # color7: foreground
        hex_f(n.tone(30 if is_dark else 85)),  # color8: background variant
        bright_colors[0],                      # color9: bright color 1
        bright_colors[1],                      # color10: bright color 2
        bright_colors[2],                      # color11: bright color 3
        bright_colors[3],                      # color12: bright color 4
        bright_colors[4],                      # color13: bright color 5
        bright_colors[5],                      # color14: bright color 6
        hex_f(n.tone(90 if is_dark else 15)),  # color15: foreground variant
    ]

    # Accents remain unchanged - top 8 ranked colors for UI accent selection
    if ranked:
        accents = [hex_f(color) for color in ranked[:8]]
    else:
        accents = [hex_f(seed_int)]

    return PaletteData(
        colors=c, 
        accents=accents, 
        backend_used="material-you-kwal", 
        source_path=str(path),
        seed=hex_f(seed_int)
    )


def _extract_material_you(path: Path, **kwargs) -> PaletteData:
    """
    Standard Material You implementation following Google's specification.
    Uses only primary/secondary/tertiary palettes from a single seed color.
    """
    from ..models.models import PaletteData
    try:
        from materialyoucolor.quantize import QuantizeCelebi
        from materialyoucolor.score.score import Score, ScoreOptions
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

    # Standard Material You: only scheme and dark_mode, no custom parameters
    selected_scheme_name = kwargs.get("scheme", "TonalSpot")
    scheme_class = schemes.get(selected_scheme_name, SchemeTonalSpot)
    is_dark = kwargs.get("dark_mode", True)
    # Standard Material You uses contrast=0.0 (default)
    contrast = 0.0
    # No manual seed override in standard mode - always use auto-detected seed
    override_seed_hex = None
    
    # Extract dominant colors
    score_options = ScoreOptions(
        desired=7,
        fallback_color_argb=0xFF4285F4,
        filter=True,
        #dislike_filter=True,
    )
    
    ranked: list[int] = []
    try:
        with Image.open(path) as img:
            img = img.convert("RGBA")
            img.thumbnail((128, 128)) 
            pixels = list(img.getdata())
            pixel_list = [[r, g, b] for r, g, b, a in pixels if a > 128]
        
        with suppress_stdout():
            stats = QuantizeCelebi(pixel_list, 128)
            ranked = Score.score(stats, score_options)
    except Exception:
        logger.exception("Failed to quantize image for accents")

    # Determine seed color
    if override_seed_hex:
        try:
            rgb = ImageColor.getrgb(override_seed_hex)
            seed_int = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]
            logger.info("Using override seed color: %s", override_seed_hex)
        except ValueError:
             logger.warning("Invalid seed color %s, falling back to auto", override_seed_hex)
             seed_int = ranked[0] if ranked else 0xFF4285F4
    else:
        seed_int = ranked[0] if ranked else 0xFF4285F4

    # Create scheme from seed
    hct_seed = Hct.from_int(seed_int)
    
    try:
        scheme = scheme_class(hct_seed, is_dark, contrast)
    except (ZeroDivisionError, ValueError) as e:
        logger.warning("Scheme %s failed: %s. Falling back to TonalSpot.", selected_scheme_name, e)
        scheme = SchemeTonalSpot(hct_seed, is_dark, contrast)
    
    # Helper functions
    def hex_f(i: int | list[int]) -> str:
        if isinstance(i, list):
            return f"#{i[0]:02x}{i[1]:02x}{i[2]:02x}"
        return f"#{i & 0xFFFFFF:06x}"
    
    def get_luminance(hex_color: str) -> float:
        rgb = ImageColor.getrgb(hex_color)
        def to_linear(c: int) -> float:
            v = c / 255.0
            return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
        r, g, b = to_linear(rgb[0]), to_linear(rgb[1]), to_linear(rgb[2])
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    # Extract colors from scheme palettes (standard Material You approach)
    n = scheme.neutral_palette
    p = scheme.primary_palette
    s = scheme.secondary_palette
    t = scheme.tertiary_palette
    
    # Background and foreground
    bg_tone = 10 if is_dark else 95
    fg_tone = 95 if is_dark else 10
    bg_color = hex_f(n.tone(bg_tone))
    fg_color = hex_f(n.tone(fg_tone))
    
    # Generate 6 main colors from the three palettes
    # Standard Material You: 2 tones from each palette (primary, secondary, tertiary)
    # Keep them grouped by palette for visual coherence
    if is_dark:
        # Dark mode: lighter tones for better visibility
        palette_colors = [
            hex_f(p.tone(80)),  # primary light
            hex_f(p.tone(70)),  # primary medium
            hex_f(s.tone(70)),  # secondary medium
            hex_f(s.tone(60)),  # secondary darker
            hex_f(t.tone(60)),  # tertiary darker
            hex_f(t.tone(50)),  # tertiary darkest
        ]
        bright_colors = [
            hex_f(p.tone(90)),
            hex_f(p.tone(85)),
            hex_f(s.tone(85)),
            hex_f(s.tone(80)),
            hex_f(t.tone(80)),
            hex_f(t.tone(75)),
        ]
    else:
        # Light mode: darker tones for better visibility
        palette_colors = [
            hex_f(p.tone(40)),
            hex_f(p.tone(50)),
            hex_f(s.tone(50)),
            hex_f(s.tone(60)),
            hex_f(t.tone(60)),
            hex_f(t.tone(70)),
        ]
        bright_colors = [
            hex_f(p.tone(30)),
            hex_f(p.tone(35)),
            hex_f(s.tone(35)),
            hex_f(s.tone(40)),
            hex_f(t.tone(40)),
            hex_f(t.tone(45)),
        ]
    
    # Build final 16-color palette (NO sorting - keep palette order)
    c = [
        bg_color,                              # color0
        palette_colors[0],                     # color1
        palette_colors[1],                     # color2
        palette_colors[2],                     # color3
        palette_colors[3],                     # color4
        palette_colors[4],                     # color5
        palette_colors[5],                     # color6
        fg_color,                              # color7
        hex_f(n.tone(30 if is_dark else 85)),  # color8
        bright_colors[0],                      # color9
        bright_colors[1],                      # color10
        bright_colors[2],                      # color11
        bright_colors[3],                      # color12
        bright_colors[4],                      # color13
        bright_colors[5],                      # color14
        hex_f(n.tone(90 if is_dark else 15)),  # color15
    ]

    # Accents from ranked colors
    if ranked:
        accents = [hex_f(color) for color in ranked[:8]]
    else:
        accents = [hex_f(seed_int)]

    return PaletteData(
        colors=c, 
        accents=accents, 
        backend_used="material-you", 
        source_path=str(path),
        seed=hex_f(seed_int)
    )

def _extract_imagemagick(path: Path) -> PaletteData:
    from ..models.models import PaletteData
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
    
    # Do not pad the color list with repeated values. Keep only the detected colors
    # (limit to 16 maximum) so the UI can render a variable-length palette.
    # This avoids visual duplication and matches UX expectations when the image
    # has fewer distinct colors.
    
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


# Validates and parses CSS color strings into QColor
# Handles: #hex, rgb(r,g,b), rgba(r,g,b,a)
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

    # 1. Regex for funky css syntax that QColor might miss (especially rgba with float alpha)
    # Matches: rgba( r, g, b, a ) or rgb(...)
    # We accommodate comma or space separation if needed, but CSS is usually comma
    rgba_match = re.match(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d\.]+))?\s*\)', s, re.IGNORECASE)
    if rgba_match:
        r, g, b, a_str = rgba_match.groups()
        r, g, b = int(r), int(g), int(b)
        alpha = 255
        if a_str:
            try:
                val = float(a_str)
                # CSS alpha is 0.0 to 1.0, but sometimes users might use 0-255 ints if they are confused.
                # Standard CSS3/4 is 0-1 (or percentage).
                # Logic: if <= 1.0, treat as float factor. If > 1.0, treat as byte.
                if val <= 1.0:
                    alpha = int(val * 255)
                else:
                    alpha = int(val)
                
                # Clamp
                alpha = max(0, min(255, alpha))
            except ValueError:
                pass
        return QColor(r, g, b, alpha)

    # 2. Fallback to QColor's native parsing (Hex, names, etc)
    c = QColor(s)
    if c.isValid():
        return c

    return QColor() # Invalid


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
        # Solid -> Hex
        # name() returns #AARRGGBB usually or #RRGGBB depending on setting, 
        # but we want pure RGB hex if solid
        return f"#{c.red():02x}{c.green():02x}{c.blue():02x}"
    else:
        # Transparent -> rgba
        # Round alpha float to ~3 decimals for reasonable precision without being verbose
        a_float = round(c.alpha() / 255.0, 3) 
        return f"rgba({c.red()}, {c.green()}, {c.blue()}, {a_float})"
