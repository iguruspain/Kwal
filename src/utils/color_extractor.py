import colorsys
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

def get_cache_path() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "kwal" / "wallpapers_colors.json"

def load_color_cache() -> dict:
    """Load the JSON color cache from disk."""
    cache_path = get_cache_path()
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Failed to load color cache: %s", e)
    return {}

def save_color_cache(data: dict) -> None:
    """Save the JSON color cache to disk."""
    cache_path = get_cache_path()
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error("Failed to save color cache: %s", e)

def get_color_category(hex_color: str) -> str:
    """
    Map a hex color to one of 12 chromatic categories (+ black/white/gray).
    Each category covers a 30 degree Hue arc in the chromatic wheel.
    """
    if not hex_color or not hex_color.startswith('#') or len(hex_color) < 7:
        return "gray"
        
    try:
        r = int(hex_color[1:3], 16) / 255.0
        g = int(hex_color[3:5], 16) / 255.0
        b = int(hex_color[5:7], 16) / 255.0
    except ValueError:
        return "gray"

    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h_deg = h * 360.0

    # Handle achromatic cases based on saturation and value
    if v < 0.15:
        return "black"
    if s < 0.15 and v > 0.85:
        return "white"
    if s < 0.15:
        return "gray"

    # 12 chromatic categories
    # Adjusted Hue thresholds for better human perception
    if h_deg < 12 or h_deg >= 348:
        return "red"
    elif h_deg < 45:
        return "orange"
    elif h_deg < 75:
        return "yellow"
    elif h_deg < 105:
        return "yellow-green"
    elif h_deg < 140:
        return "green"
    elif h_deg < 170:
        return "cyan-green"
    elif h_deg < 200:
        return "cyan"
    elif h_deg < 230:
        return "blue-cyan"
    elif h_deg < 260:
        return "blue"
    elif h_deg < 290:
        return "violet"
    elif h_deg < 320:
        return "magenta"
    else:
        return "rose"
