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
            json.dump(data, f, indent=2, ensure_ascii=False)
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
