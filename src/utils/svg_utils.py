from __future__ import annotations

import logging
import os
import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING
from xml.dom import minidom

if TYPE_CHECKING:
    from xml.dom.minidom import Document, Element

logger = logging.getLogger(__name__)

_INVALID_COLOR_TOKENS: tuple[str, ...] = (
    "none",
    "transparent",
    "currentcolor",
    "inherit",
    "url(",
    "rgba(0,0,0,0)",
    "rgba(255,255,255,0)",
)

_NAMED_COLORS: dict[str, str] = {
    "black": "#000000",
    "white": "#ffffff",
    "red": "#ff0000",
    "green": "#008000",
    "blue": "#0000ff",
    "yellow": "#ffff00",
    "gray": "#808080",
    "grey": "#808080",
    "silver": "#c0c0c0",
    "maroon": "#800000",
    "purple": "#800080",
    "fuchsia": "#ff00ff",
    "lime": "#00ff00",
    "olive": "#808000",
    "navy": "#000080",
    "teal": "#008080",
    "aqua": "#00ffff",
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def interpolate_color(color1: str, color2: str, factor: float) -> str:
    try:
        r1, g1, b1 = hex_to_rgb(color1)
        r2, g2, b2 = hex_to_rgb(color2)
        rgb = (
            r1 + (r2 - r1) * factor,
            g1 + (g2 - g1) * factor,
            b1 + (b2 - b1) * factor,
        )
        return rgb_to_hex(rgb)
    except Exception:
        return color1


def is_valid_color(color_str: str) -> bool:
    if not color_str:
        return False
    val = color_str.strip().lower()
    return not any(token in val for token in _INVALID_COLOR_TOKENS)


def normalize_color(color_str: str) -> str | None:
    if not color_str:
        return None
    val = color_str.strip().lower()

    rgb_match = re.match(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", val)
    if rgb_match:
        r, g, b = rgb_match.groups()
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    rgba_match = re.match(
        r"rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*[^)]+\)", val
    )
    if rgba_match:
        r, g, b = rgba_match.groups()
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    if re.match(r"^#[0-9a-f]{3}$", val):
        return f"#{val[1]*2}{val[2]*2}{val[3]*2}"

    if re.match(r"^#[0-9a-f]{6}$", val):
        return val

    return _NAMED_COLORS.get(val)


def get_gradient_colors(base_colors: list[str], num_needed: int) -> list[str]:
    """Interpolate or pick from base_colors to produce exactly num_needed colors."""
    n = len(base_colors)
    if n == 0:
        return ["#888888"] * num_needed
    if num_needed <= n:
        return base_colors[:num_needed]

    result: list[str] = []
    for i in range(num_needed):
        factor = i / (num_needed - 1) if num_needed > 1 else 0.0
        seg = int(factor * (n - 1))
        if seg >= n - 1:
            seg = n - 2
            seg_f = 1.0
        else:
            seg_start = seg / (n - 1)
            seg_end = (seg + 1) / (n - 1)
            denom = seg_end - seg_start
            seg_f = (factor - seg_start) / denom if denom != 0.0 else 0.0
        result.append(interpolate_color(base_colors[seg], base_colors[seg + 1], seg_f))
    return result


# (element_node, normalized_color, attr_type, attr_name)
# attr_type: "fill" | "stroke" | "stop-color" | "style"
# attr_name: the CSS property name inside a style; same as attr_type for direct attrs
_SvgLayer = tuple[object, str, str, str]


def _get_svg_layers(
    content: str,
) -> tuple["Document", list[_SvgLayer], set[str], bool] | None:
    """Parse SVG content string and extract color-bearing element descriptors."""
    try:
        cleaned = content.replace('xmlns="http://www.w3.org/2000/svg"', "")
        doc = minidom.parseString(cleaned)
    except Exception:
        logger.exception("Failed to parse SVG content")
        return None

    layers: list[_SvgLayer] = []
    colors_found: set[str] = set()

    for element in doc.getElementsByTagName("*"):
        if element.hasAttribute("fill"):
            raw = element.getAttribute("fill")
            norm = normalize_color(raw)
            if norm and is_valid_color(raw):
                layers.append((element, norm, "fill", "fill"))
                colors_found.add(norm)

        if element.hasAttribute("stroke"):
            raw = element.getAttribute("stroke")
            norm = normalize_color(raw)
            if norm and is_valid_color(raw):
                layers.append((element, norm, "stroke", "stroke"))
                colors_found.add(norm)

        if element.hasAttribute("style"):
            style = element.getAttribute("style")
            fill_m = re.search(r"fill\s*:\s*([^;]+)", style, re.IGNORECASE)
            if fill_m:
                fc = fill_m.group(1).strip()
                norm = normalize_color(fc)
                if norm and is_valid_color(fc):
                    layers.append((element, norm, "style", "fill"))
                    colors_found.add(norm)
            stroke_m = re.search(r"stroke\s*:\s*([^;]+)", style, re.IGNORECASE)
            if stroke_m:
                sc = stroke_m.group(1).strip()
                norm = normalize_color(sc)
                if norm and is_valid_color(sc):
                    layers.append((element, norm, "style", "stroke"))
                    colors_found.add(norm)

        if element.hasAttribute("stop-color"):
            raw = element.getAttribute("stop-color")
            norm = normalize_color(raw)
            if norm and is_valid_color(raw):
                layers.append((element, norm, "stop-color", "stop-color"))
                colors_found.add(norm)

    is_mono = len(colors_found) <= 1
    return doc, layers, colors_found, is_mono


def _apply_color(
    element: object,
    attr_type: str,
    original_color: str,
    new_color: str,
    is_mono: bool,
) -> None:
    el = element  # type: ignore[assignment]
    if attr_type == "fill":
        el.setAttribute("fill", new_color)
    elif attr_type == "stroke":
        el.setAttribute("stroke", new_color)
    elif attr_type == "stop-color":
        el.setAttribute("stop-color", new_color)
    elif attr_type == "style":
        style: str = el.getAttribute("style")
        if is_mono:
            style = re.sub(
                r"fill\s*:\s*[^;]+", f"fill:{new_color}", style, flags=re.IGNORECASE
            )
            style = re.sub(
                r"stroke\s*:\s*[^;]+",
                f"stroke:{new_color}",
                style,
                flags=re.IGNORECASE,
            )
        else:
            if "fill:" in style.lower():
                style = re.sub(
                    rf"fill\s*:\s*{re.escape(original_color)}",
                    f"fill:{new_color}",
                    style,
                    flags=re.IGNORECASE,
                )
            if "stroke:" in style.lower():
                style = re.sub(
                    rf"stroke\s*:\s*{re.escape(original_color)}",
                    f"stroke:{new_color}",
                    style,
                    flags=re.IGNORECASE,
                )
        el.setAttribute("style", style)


def recolor_svg_file(
    svg_path: str,
    gradient_colors: list[str],
    mono_color: str,
) -> tuple[bool, str]:
    """Recolor an SVG file in-place using gradient or mono strategy.

    Returns (success, info_message).
    """
    try:
        with open(svg_path, "r", encoding="utf-8") as fh:
            content = fh.read()
    except OSError as exc:
        return False, f"Read error: {exc}"

    parsed = _get_svg_layers(content)
    if parsed is None:
        return False, "Cannot parse"

    doc, layers, colors_found, is_mono = parsed

    if not layers:
        return False, "No colored layers found"

    try:
        if is_mono:
            for element, original_color, attr_type, _ in layers:
                _apply_color(element, attr_type, original_color, mono_color, is_mono=True)
            with open(svg_path, "w", encoding="utf-8") as fh:
                fh.write(doc.toxml())
            return True, f"monochrome ({len(layers)} layers)"
        else:
            unique = sorted(colors_found)
            mapped = get_gradient_colors(gradient_colors, len(unique))
            color_map = dict(zip(unique, mapped))
            for element, original_color, attr_type, _ in layers:
                new_color = color_map.get(original_color, original_color)
                _apply_color(element, attr_type, original_color, new_color, is_mono=False)
            with open(svg_path, "w", encoding="utf-8") as fh:
                fh.write(doc.toxml())
            return True, f"{len(unique)} colors ({len(layers)} layers)"
    except Exception as exc:
        return False, f"Processing error: {exc}"


def get_svg_preview_cache_dir() -> Path:
    """Return (and create) the SVG preview cache directory under ~/.cache/kwal/svg_preview/."""
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "kwal" / "svg_preview"
    cache_root.mkdir(parents=True, exist_ok=True)
    return cache_root


def clear_svg_preview_cache() -> None:
    """Remove the SVG preview cache directory entirely."""
    try:
        cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "kwal" / "svg_preview"
        if cache_root.exists():
            shutil.rmtree(cache_root)
            logger.info("Cleared SVG preview cache %s", cache_root)
    except Exception:
        logger.exception("Failed clearing SVG preview cache")
