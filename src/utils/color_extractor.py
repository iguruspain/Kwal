import json
import logging
import os
from pathlib import Path

from materialyoucolor.hct import Hct

logger = logging.getLogger(__name__)

# Maximum number of unique color categories stored per wallpaper
MAX_CATEGORIES = 5

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
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("Failed to save color cache: %s", e)

def get_color_category(hex_color: str) -> str:
    """
    Map a hex color to one of 12 chromatic categories (+ black/white/gray).

    Uses OKLCH-based HCT (Hue, Chroma, Tone) from materialyoucolor for
    perceptually uniform classification. Each chromatic category covers a
    30 degree arc on the OKLCH hue wheel.
    """
    if not hex_color or not hex_color.startswith('#') or len(hex_color) < 7:
        return "gray"

    try:
        # Hct.from_int() expects an ARGB integer; input is #RRGGBB, so we parse
        # each component and pack them with full alpha (255).
        hex_str = hex_color.lstrip('#')
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        int_color = (255 << 24) | (r << 16) | (g << 8) | b
    except (ValueError, IndexError):
        return "gray"

    try:
        hct = Hct.from_int(int_color)
    except (ValueError, OverflowError):
        return "gray"

    hue = hct.hue
    chroma = hct.chroma
    tone = hct.tone

    # Achromatic classification using perceptually uniform OKLCH metrics
    if tone < 20:
        return "black"
    if tone > 90 and chroma < 10:
        return "white"
    if chroma < 10:
        return "gray"

    # 12 chromatic categories calibrated for OKLCH hue wheel.
    # Thresholds are midpoints between adjacent pure-color hue anchors:
    #   rose: 2.5°, red: 27.4°, orange: 52.5°, yellow: 111.1°,
    #   yellow-green: 136.0°, green: 142.1°, cyan-green: 152.7°,
    #   cyan: 196.5°, blue-cyan: 263.9°, blue: 282.8°,
    #   violet: 304.5°, magenta: 334.6°
    if hue < 15.0 or hue >= 348.5:
        return "rose"
    elif hue < 40.0:
        return "red"
    elif hue < 81.8:
        return "orange"
    elif hue < 123.6:
        return "yellow"
    elif hue < 139.0:
        return "yellow-green"
    elif hue < 147.4:
        return "green"
    elif hue < 174.6:
        return "cyan-green"
    elif hue < 230.2:
        return "cyan"
    elif hue < 273.4:
        return "blue-cyan"
    elif hue < 293.7:
        return "blue"
    elif hue < 319.6:
        return "violet"
    elif hue < 348.5:
        return "magenta"
    else:
        return "rose"


# Fixed list of categories produced by get_color_category(), in a sensible
# hue-wheel order. Kept as a single source of truth for both the automatic
# classifier and the manual category editor UI.
CATEGORY_LIST: list[str] = [
    "red", "orange", "yellow", "yellow-green", "green", "cyan-green",
    "cyan", "blue-cyan", "blue", "violet", "magenta", "rose",
    "black", "gray", "white",
]


def list_categories() -> list[str]:
    """Return the fixed list of supported color categories."""
    return list(CATEGORY_LIST)


def get_categories_for_path(path: str) -> list[str]:
    """Return the stored categories for a single cached path (empty if not cached)."""
    if not path:
        return []
    cache = load_color_cache()
    entry = cache.get(path)
    if not isinstance(entry, dict):
        return []
    return list(entry.get("categories", []) or [])


def list_cache_entries() -> list[dict]:
    """Return every cached entry as a flat list, sorted by path.

    Each item: {"path": str, "colors": list[str], "categories": list[str]}
    Used by the manual category editor to show every wallpaper that has
    already been color-analyzed.
    """
    cache = load_color_cache()
    entries = []
    for path, data in cache.items():
        if not isinstance(data, dict):
            continue
        entries.append({
            "path": path,
            "colors": list(data.get("colors", []) or []),
            "categories": list(data.get("categories", []) or []),
        })
    entries.sort(key=lambda e: e["path"].lower())
    return entries


def update_entry_categories(path: str, categories: list[str]) -> bool:
    """Overwrite the stored categories for a cached image.

    Preserves `colors` and `last_modified`; only `categories` is replaced.
    Silently drops unknown category names and duplicates.
    Returns False if there is no existing cache entry for `path`.
    """
    if not path:
        return False

    cache = load_color_cache()
    entry = cache.get(path)
    if not isinstance(entry, dict):
        logger.warning("update_entry_categories: no cache entry for %s", path)
        return False

    seen: set[str] = set()
    clean: list[str] = []
    for c in categories:
        c = str(c)
        if c in CATEGORY_LIST and c not in seen:
            seen.add(c)
            clean.append(c)

    entry["categories"] = clean
    cache[path] = entry
    save_color_cache(cache)
    logger.info("Updated categories for %s -> %s", path, clean)
    return True
