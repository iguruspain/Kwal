"""Generate HTML previews for Ulauncher themes.

This module parses Ulauncher theme files (``manifest.json`` and ``theme.css``)
and produces a self-contained HTML document that renders a visual preview of
the theme in a WebView.  It supports GTK-style CSS variables (``@define-color``),
function calls (``alpha()``, ``darker()``), and live colour overrides from the UI.

Architecture
------------
``UlauncherRendererV2`` is the main coordinator class.  It delegates to three
specialised sub-components:

* ``UlauncherThemeParser`` – loads and parses ``manifest.json`` / ``theme.css``.
* ``UlauncherColorResolver`` – resolves ``@variables``, ``alpha()``, and
  ``darker()`` functions, with support for live colour overrides.
* ``UlauncherIconResolver`` – resolves system icon names to file URIs with caching.

Public API
----------
:func:`generate_ulauncher_preview_html` is the entry point.  Call it with a
theme path and optional live colour overrides to obtain a complete HTML string.
"""

import json
import logging
import re
from pathlib import Path

from . import color_utils

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# CSS variable / function regex patterns
_DEFINE_COLOR_RE = re.compile(r"@define-color\s+([\w-]+)\s+([^;]+);")
_VAR_REFERENCE_RE = re.compile(r"@([\w-]+)(?!\w)")
_ALPHA_FUNC_RE = re.compile(r"alpha\s*\(([^,]+),\s*([^)]+)\)")
_DARKER_FUNC_RE = re.compile(r"darker\s*\(([^)]+)\)")
_CSS_FUNC_RE = re.compile(r"(alpha|darker)\s*\([^)]+\)")

# Icon resolution
ICON_SEARCH_PATHS = [
    "/usr/share/icons/hicolor/128x128/apps/",
    "/usr/share/icons/breeze/apps/48/",
    "/usr/share/icons/hicolor/scalable/apps/",
]



_SPOTIFY_SVG_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" style="color:#5ecf7d;fill:currentColor" shape-rendering="geometricPrecision" text-rendering="geometricPrecision" image-rendering="optimizeQuality" fill-rule="evenodd" clip-rule="evenodd" viewBox="0 0 512 511.992"><path fill-rule="nonzero" fill="currentColor" d="M255.998.004C114.617.004 0 114.616 0 255.998c0 141.385 114.617 255.994 255.998 255.994C397.395 511.992 512 397.387 512 255.998 512 114.624 397.395.015 255.994.015l.004-.015v.004zm117.4 369.22c-4.585 7.519-14.426 9.907-21.949 5.288-60.104-36.715-135.771-45.028-224.882-24.669-8.587 1.955-17.146-3.425-19.104-12.015-1.966-8.59 3.394-17.149 12.004-19.104 97.517-22.28 181.164-12.687 248.644 28.551 7.523 4.615 9.907 14.427 5.287 21.949zm31.335-69.704c-5.779 9.389-18.067 12.353-27.452 6.578-68.813-42.297-173.703-54.547-255.096-29.837-10.556 3.188-21.704-2.761-24.906-13.298-3.18-10.556 2.772-21.68 13.309-24.89 92.971-28.209 208.551-14.546 287.575 34.015 9.385 5.778 12.349 18.066 6.574 27.44v-.004l-.004-.004zm2.692-72.583c-82.51-49.006-218.635-53.511-297.409-29.603-12.649 3.836-26.027-3.302-29.859-15.955-3.833-12.657 3.302-26.024 15.959-29.868 90.428-27.452 240.753-22.149 335.747 34.015 11.401 6.755 15.133 21.447 8.375 32.809-6.728 11.378-21.462 15.13-32.802 8.372h-.011z"/></svg>'
    )

ICON_CANDIDATES_MAP: dict[str, list[str]] = {
    "spotify": ["spotify.png", "spotify-client.png"],
    "spectacle": ["spectacle.svg"],
}

_GEAR_SVG_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" shape-rendering="geometricPrecision" text-rendering="geometricPrecision" image-rendering="optimizeQuality" fill-rule="evenodd" clip-rule="evenodd" viewBox="0 0 24 24"><circle cx="12" cy="12" r="12" fill="{prefs_bg_color}"/><path fill-rule="nonzero" fill="{prefs_fg_color}" opacity="0.95" d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94L14.4 2.81c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg>'
)

# Gear SVG template for the settings button (hover state)
# Placeholder: {prefs_bg_color} {prefs_fg_color}
# _GEAR_SVG_TEMPLATE = (
#     '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" '
#     'xmlns="http://www.w3.org/2000/svg">'
#     '<circle cx="12" cy="12" r="12" fill="{prefs_bg_color}"/>'
#     '<path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58'
#     'c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96'
#     'c-.5-.38-1.03-.7-1.62-.94L14.4 2.81c-.04-.24-.24-.41-.48-.41h-3.84'
#     'c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96'
#     'c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58'
#     'c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61'
#     'l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54'
#     'c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 '
#     '1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07'
#     '-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 '
#     '3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z" fill="#605c5a" opacity="0.95"/>'
#     '</svg>'
# )

# Provisional/transparent color sentinels
_INVALID_COLORS = {"provisional_rgba_color", "provisional_hex_color", "transparent"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_ulauncher_preview_html(
    theme_path: str | Path,
    live_colors: dict[str, str] | None = None,
    scale: float = 0.75,
    window_width: int | None = None,
    manifest: dict[str, object] | None = None,
    css_content: str | None = None,
) -> str:
    """Generate a complete HTML preview for an Ulauncher theme.

    Parameters
    ----------
    theme_path:
        Path to the theme directory (must contain ``manifest.json`` and
        ``theme.css``).
    live_colors:
        Optional dictionary of variable-name → CSS colour overrides.  These
        take precedence over values defined in ``theme.css``.
    scale:
        CSS scaler factor applied to the preview (default ``0.75``).
    window_width:
        Custom window width in pixels.  Falls back to
        ``UlauncherRendererV2.LAYOUT_DEFAULTS["window_width"]`` (650 px).
    manifest:
        Pre-parsed manifest dictionary.  When supplied the file is not read
        from disk (useful for incremental updates).
    css_content:
        Pre-loaded CSS content.  When supplied ``theme.css`` is not read
        from disk.

    Returns
    -------
    str
        A self-contained HTML document (``<!DOCTYPE html>...``) ready to be
        injected into a ``QWebEngineView``.
    """
    renderer = UlauncherRendererV2(
        theme_path, live_colors, window_width=window_width,
        manifest=manifest, css_content=css_content,
    )
    return renderer.render(scale=scale)


# ---------------------------------------------------------------------------
# Sub-components
# ---------------------------------------------------------------------------

class UlauncherThemeParser:
    """Parse manifest.json and theme.css to extract theme data."""

    def __init__(
        self,
        theme_path: Path,
        manifest: dict[str, object] | None = None,
        css_content: str | None = None,
    ) -> None:
        """Initialise the parser with a theme path and optional pre-loaded data.

        Parameters
        ----------
        theme_path:
            Directory containing ``manifest.json`` and ``theme.css``.
        manifest:
            Pre-parsed manifest dictionary (skips file I/O when provided).
        css_content:
            Pre-loaded CSS content (currently unused; reserved for future caching).
        """
        self.theme_path = theme_path
        self.manifest: dict[str, object] = manifest or {}
        self.css_content = css_content or ""
        self.raw_css: str = ""
        self.variables: dict[str, str] = {}

    def load_data(self) -> None:
        """Parse manifest.json and theme.css to extract UI properties."""
        if not self.theme_path.is_dir():
            return

        manifest_file = self.theme_path / "manifest.json"
        if manifest_file.exists():
            try:
                with manifest_file.open("r", encoding="utf-8") as f:
                    self.manifest = json.load(f)
            except Exception:
                logger.warning(f"Failed to load manifest: {manifest_file}")

        css_file = self.theme_path / "theme.css"
        if css_file.exists():
            try:
                self.raw_css = css_file.read_text(encoding="utf-8")
                color_matches = _DEFINE_COLOR_RE.findall(self.raw_css)
                for name, val in color_matches:
                    self.variables[name] = val.strip()
            except Exception:
                logger.exception(f"Failed to parse CSS: {css_file}")

    def transform_css(self, color_resolver: "UlauncherColorResolver") -> str:
        """Transform Ulauncher GTK-style CSS into standard Web-compatible CSS."""
        if not self.raw_css:
            return ""

        css = _DEFINE_COLOR_RE.sub("", self.raw_css)

        resolved_vars: dict[str, str] = {}
        for name in self.variables:
            resolved_vars[name] = color_resolver.get_color(name, "transparent")

        def replace_var(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return resolved_vars.get(var_name, f"@{var_name}")

        css = _VAR_REFERENCE_RE.sub(replace_var, css)

        def resolve_func(match: re.Match[str]) -> str:
            return color_resolver.resolve_value(match.group(0))

        css = _CSS_FUNC_RE.sub(resolve_func, css)

        return css


class UlauncherColorResolver:
    """Resolve @variables, alpha(), darker() functions, and live color overrides."""

    def __init__(
        self,
        variables: dict[str, str],
        live_colors: dict[str, str],
    ) -> None:
        """Initialise the colour resolver.

        Parameters
        ----------
        variables:
            CSS ``@define-color`` variables extracted from ``theme.css``.
        live_colors:
            Runtime colour overrides (e.g. from the UI palette editor).
        """
        self.variables = variables
        self.live_colors = live_colors
        self._resolving_stack: set[str] = set()

    def get_color(self, name: str, fallback: str) -> str:
        """Get color from live overrides, then CSS variables, then fallback."""
        if name in self._resolving_stack:
            logger.warning(
                f"Circular reference detected for color '{name}', using fallback"
            )
            return fallback

        self._resolving_stack.add(name)
        try:
            val = fallback
            if name in self.live_colors:
                raw = self.live_colors[name]
                if raw and raw not in _INVALID_COLORS:
                    val = raw
            elif name in self.variables:
                val = self.variables[name]

            return self.resolve_value(val)
        finally:
            self._resolving_stack.discard(name)

    def resolve_value(self, val: str) -> str:
        """Recursively resolve @variables and CSS functions like alpha() or darker()."""
        if not isinstance(val, str):
            return str(val)

        val = val.strip()

        if val.startswith("@"):
            ref = val[1:]
            fallback = self.variables.get(ref, val)
            return self.get_color(ref, fallback)

        alpha_match = _ALPHA_FUNC_RE.match(val)
        if alpha_match:
            base_color = self.resolve_value(alpha_match.group(1).strip())
            opacity = alpha_match.group(2).strip()
            rgba = self._hex_to_rgba(base_color)
            if rgba:
                r, g, b, _ = rgba
                return f"rgba({r}, {g}, {b}, {opacity})"
            return base_color

        darker_match = _DARKER_FUNC_RE.match(val)
        if darker_match:
            base_color = self.resolve_value(darker_match.group(1).strip())
            return self._shade_color(base_color, -20)

        return val

    @staticmethod
    def _hex_to_rgba(hex_color: str) -> tuple[int, int, int, int] | None:
        """Convert a hex/CSS color to ``(r, g, b, a)``."""
        try:
            qcolor = color_utils.parse_css_color(hex_color)
            return qcolor.red(), qcolor.green(), qcolor.blue(), qcolor.alpha()
        except Exception:
            return None

    @staticmethod
    def _shade_color(color_str: str, percent: int) -> str:
        """Darken (*percent* < 0) or lighten (*percent* > 0) a CSS color."""
        try:
            qcolor = color_utils.parse_css_color(color_str)
            if percent < 0:
                shaded = qcolor.darker(100 - percent)
            else:
                shaded = qcolor.lighter(100 + percent)
            return color_utils.format_css_color(shaded)
        except Exception:
            return color_str


class UlauncherIconResolver:
    """Resolve system icon URIs with caching."""

    def __init__(self) -> None:
        """Initialise the icon resolver with an empty cache."""
        self._cache: dict[str, str] = {}

    def resolve(self, name: str) -> str:
        """Resolve a system icon URI for a given app name."""
        if name in self._cache:
            return self._cache[name]

        key = name.lower()
        candidates = ICON_CANDIDATES_MAP.get(key, [])

        for base_path in ICON_SEARCH_PATHS:
            for cand in candidates:
                full_path = Path(base_path) / cand
                if full_path.exists():
                    uri = full_path.as_uri()
                    self._cache[name] = uri
                    logger.debug(f"Resolved Ulauncher icon {name}: {uri}")
                    return uri

        logger.warning(f"Failed to resolve Ulauncher icon {name}")
        self._cache[name] = ""
        return ""


# ---------------------------------------------------------------------------
# Main Renderer
# ---------------------------------------------------------------------------

class UlauncherRendererV2:
    """Enhanced Ulauncher preview renderer that interprets theme CSS and manifest files.

    Acts as a coordinator that delegates to specialised sub-components:
    - ``UlauncherThemeParser`` for loading/parsing manifest and CSS.
    - ``UlauncherColorResolver`` for colour resolution.
    - ``UlauncherIconResolver`` for system icon look-up.
    """

    # Fixed Layout Parameters ("Nosotros" part)
    # These are the "design standard" values (pixels)
    LAYOUT_DEFAULTS = {
        "window_width": 650,
        "input_font_size": 50,
        "shortcut_font_size": 20,
        "item_name_font_size": 26,
        "item_text_font_size": 16,
        "results_padding_bottom": 25,
        "input_padding_v": 35,
        "input_padding_h": 45,
        "item_padding_v": 22,
        "item_padding_h": 30,
        "item_margin_h": 16,
        "icon_container_width": 70,
        "icon_size": 48,
        "text_padding_left": 25,
    }

    def __init__(
        self,
        theme_path: str | Path,
        live_colors: dict[str, str] | None = None,
        window_width: int | None = None,
        manifest: dict[str, object] | None = None,
        css_content: str | None = None,
    ) -> None:
        """Initialise the renderer and all sub-components.

        Parameters
        ----------
        theme_path:
            Path to the Ulauncher theme directory.
        live_colors:
            Runtime colour overrides from the UI.
        window_width:
            Custom preview width in pixels.
        manifest:
            Pre-parsed manifest dictionary.
        css_content:
            Pre-loaded CSS content.
        """
        self.theme_path = Path(theme_path)
        self.live_colors = live_colors or {}
        self.layout = self.LAYOUT_DEFAULTS.copy()

        if window_width is not None:
            self.layout["window_width"] = window_width

        # Sub-components
        self._parser = UlauncherThemeParser(
            self.theme_path, manifest, css_content
        )
        self._parser.load_data()
        self._color_resolver = UlauncherColorResolver(
            self._parser.variables, self.live_colors
        )
        self._icon_resolver = UlauncherIconResolver()

    @property
    def calced(self) -> dict[str, int | str]:
        """Expose layout values as ready-to-use CSS values (absolute pixels)."""
        layout = self.layout
        return {
            "results_padding_bottom": layout["results_padding_bottom"],
            "input_padding": f"{layout['input_padding_v']}px {layout['input_padding_h']}px",
            "item_padding": f"{layout['item_padding_v']}px {layout['item_padding_h']}px",
            "item_margin": f"0 {layout['item_margin_h']}px",
            "icon_container_width": layout["icon_container_width"],
            "icon_size": layout["icon_size"],
            "text_padding_left": layout["text_padding_left"],
            "input_font_size": layout["input_font_size"],
            "item_name_font_size": layout["item_name_font_size"],
            "item_text_font_size": layout["item_text_font_size"],
            "shortcut_font_size": layout["shortcut_font_size"],
        }

    @property
    def manifest(self) -> dict[str, object]:
        """Expose parsed manifest data."""
        return self._parser.manifest

    @property
    def variables(self) -> dict[str, str]:
        """Expose parsed CSS variables (for backward compatibility)."""
        return self._parser.variables

    def transform_css(self) -> str:
        """Transform Ulauncher GTK-style CSS into standard Web-compatible CSS."""
        return self._parser.transform_css(self._color_resolver)

    def _get_color(self, name: str, fallback: str) -> str:
        """Get color from live overrides, then CSS variables, then fallback."""
        return self._color_resolver.get_color(name, fallback)

    def resolve_system_icon(self, name: str) -> str:
        """Resolve system icon URI with caching."""
        return self._icon_resolver.resolve(name)

    def _highlight_match(self, text: str, query: str, color: str) -> str:
        """Apply color highlighting to characters that match the fuzzy query.

        Walks through `text` and wraps matching characters (in order, case-insensitive)
        with a `<span>` using the given CSS color. Non-matching characters are left plain.
        """
        if not query or not color:
            return text

        result = ""
        q_idx = 0
        q_lower = query.lower()

        for char in text:
            if q_idx < len(q_lower) and char.lower() == q_lower[q_idx]:
                result += f'<span style="color: {color};">{char}</span>'
                q_idx += 1
            else:
                result += char
        return result

    # ------------------------------------------------------------------
    # HTML section builders
    # ------------------------------------------------------------------

    def _build_input_section(self, query: str, gear_svg: str) -> str:
        """Build the ``<div class="input">`` section (query bar + gear icon)."""
        return f"""
        <div class="input">
            <div class="input-text">{query}<span class="caret">|</span></div>
            <div class="prefs-btn">{gear_svg}</div>
        </div>
        """

    def _build_result_item(self, icon_html: str, name_label: str,
                           description: str, shortcut: str,
                           is_selected: bool) -> str:
        """Build a single ``<div class="item-box">`` result row.

        When *is_selected* is ``True`` the ``selected`` class is added
        to highlight the active match.
        """
        css_class = "selected item-box" if is_selected else "item-box"
        return f"""
        <div class="{css_class}">
            <div class="item-icon-container">{icon_html}</div>
            <div class="item-text-container">
                <div class="item-name">{name_label}</div>
                <div class="item-text">{description}</div>
            </div>
            <div class="item-shortcut">{shortcut}</div>
        </div>
        """

    def _build_results_section(self, items_html: str) -> str:
        """Wrap pre-built item HTML strings inside ``<div class="results">``."""
        return f'<div class="results">\n{items_html}\n</div>'

    def _build_layout_css(self, scale: float, shadow_blur: int, shadow_y: int,
                          prefs_bg_hover: str) -> str:
        """Generate the preview-specific CSS (layout, scaler, shadows).

        This CSS is *injected* on top of the theme CSS and is responsible
        for scaling, shadows, and dimension overrides.
        """
        c = self.calced
        return f"""
                .scaler {{
                    padding: {shadow_blur}px;
                    transform: scale({scale});
                    transform-origin: top center;
                    display: inline-block;
                }}
                .app {{
                    width: {self.layout['window_width']}px;
                    box-shadow: 0 {shadow_y}px {shadow_blur}px rgba(0,0,0,0.8);
                    overflow: hidden;
                    position: relative;
                }}
                .item-icon-container {{
                    width: {c['icon_container_width']}px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                .item-icon {{
                    width: {c['icon_size']}px;
                    height: {c['icon_size']}px;
                    object-fit: contain;
                }}
                .item-text-container {{
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    padding-left: {c['text_padding_left']}px;
                    flex-grow: 1;
                }}
                .item-box {{
                    display: flex;
                    align-items: center;
                    padding: {c['item_padding']};
                    margin: {c['item_margin']};
                }}
                .results {{
                    padding-bottom: {c['results_padding_bottom']}px;
                }}
                .input {{
                    padding: {c['input_padding']};
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    position: relative;
                }}
                .input-text {{
                    font-size: {c['input_font_size']}px;
                    font-weight: 300;
                    flex-grow: 1;
                }}
                .prefs-btn {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    opacity: 0.8;
                    border-radius: 50%;
                    padding: 0;
                    min-width: 28px;
                    min-height: 28px;
                }}
                .prefs-btn:hover {{
                    background-color: {prefs_bg_hover};
                }}
                .prefs-btn svg {{
                    display: block;
                }}
                .item-name {{
                    font-size: {c['item_name_font_size']}px;
                    font-weight: 500;
                }}
                .item-text {{
                    font-size: {c['item_text_font_size']}px;
                    font-weight: normal;
                }}
                .caret {{
                    margin-left: 2px;
                }}
                .item-shortcut {{
                    margin-left: auto;
                    font-size: {c['shortcut_font_size']}px;
                }}
        """

    def render(self, scale: float = 0.75) -> str:
        """Render the full HTML preview for the Ulauncher theme.

        Orchestrates colour resolution, icon resolution, and HTML generation
        before delegating to :meth:`dimension_html` for final wrapping.
        """
        # Transformed CSS
        injected_css = self.transform_css()

        # Resolve essential colours for the outer container and fallback
        bg_color = self._get_color("window_bg", self._get_color("bg_color", "#1a1a1a"))
        border_color = self._get_color("window_border_color", "#333333")

        # Resolve match-highlight colours (multiple possible locations in manifest)
        m = self.manifest
        m_colors = m.get("colors", {})
        m_hl = m.get("matched_text_hl_colors", {})

        color_sel = (
            self.live_colors.get("when_selected")
            or m.get("when_selected")
            or m_colors.get("when_selected")
            or m_hl.get("when_selected")
            or "#ffffff"
        )

        color_nosel = (
            self.live_colors.get("when_not_selected")
            or m.get("when_not_selected")
            or m_colors.get("when_not_selected")
            or m_hl.get("when_not_selected")
            or "#888888"
        )

        # Icon fallbacks
        spotify_path = self.resolve_system_icon("spotify")
        spectacle_path = self.resolve_system_icon("spectacle")

        spotify_svg = _SPOTIFY_SVG_TEMPLATE
        # Settings gear icon (using prefs_background as hover state for preview)
        prefs_bg_color = self._get_color("prefs_background", "#555555")
        prefs_fg_color = self._get_color("bg_color", "#1a1a1a")
        gear_svg = _GEAR_SVG_TEMPLATE.format(prefs_bg_color=prefs_bg_color, prefs_fg_color=prefs_fg_color)

        spotify_img = (
            f'<img src="{spotify_path}" class="item-icon">'
            if spotify_path
            else f'<div class="item-icon" style="background:transparent;border-radius:4px;">{spotify_svg}</div>'
        )
        spectacle_img = (
            f'<img src="{spectacle_path}" class="item-icon">'
            if spectacle_path
            else '<div class="item-icon" style="background:transparent;border-radius:4px;"></div>'
        )

        # Highlighted labels
        query = "sptf"
        spotify_label = self._highlight_match("Spotify", query, color_sel)
        spectacle_label = self._highlight_match("Spectacle", query, color_nosel)
        gear_label = self._highlight_match("Settings", query, color_nosel)


        # Build content sections
        input_section = self._build_input_section(query, gear_svg)

        item1 = self._build_result_item(spotify_img, spotify_label,
                                         "Music Player", "Alt+1", True)
        item2 = self._build_result_item(spectacle_img, spectacle_label,
                                         "Capturas y grabaciones de pantalla",
                                         "Alt+2", False)
        results_section = self._build_results_section(f"{item1}\n{item2}")

        content = f'<div class="app">\n{input_section}\n{results_section}\n</div>'

        return self.dimension_html(content, scale, bg_color, border_color, injected_css)

    def dimension_html(self, content: str, scale: float, bg_color: str,
                       border_color: str, injected_css: str) -> str:
        """Dimension and scale the resulting HTML.

        Wraps *content* in a complete ``<html>`` document with injected
        theme CSS and preview-specific layout CSS (scaler, shadows, etc.).
        """
        # Fixed base values for design standard.
        # CSS scale() will decrease/increase these proportionally.
        shadow_blur = 50
        shadow_y = 25

        prefs_bg_hover = self._get_color("prefs_background", "#555555")
        layout_css = self._build_layout_css(scale, shadow_blur, shadow_y, prefs_bg_hover)

        return f"""
        <html>
        <head>
            <style>
                body {{
                    background: transparent;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: flex-start;
                    width: 100vw;
                    overflow: hidden;
                    font-family: sans-serif;
                }}
                body::-webkit-scrollbar {{
                    display: none;
                }}

                /* Injected Theme CSS */
                {injected_css}

                /* Layout Fixes for Preview */
                {layout_css}
            </style>
        </head>
        <body>
            <div class="scaler">
                {content}
            </div>
        </body>
        </html>
        """

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Generate a standalone Ulauncher theme preview.")
    parser.add_argument("theme_path", help="Path to the Ulauncher theme directory")
    parser.add_argument("--output", default="preview.html", help="Path to the output HTML file")
    parser.add_argument("--scale", type=float, default=1.0, help="Scaling factor (e.g. 0.8)")

    args = parser.parse_args()

    theme_dir = Path(args.theme_path).expanduser().resolve()
    if not theme_dir.is_dir():
        print(f"Error: {theme_dir} is not a directory.")
        sys.exit(1)

    renderer = UlauncherRendererV2(theme_dir)
    html_content = renderer.render(scale=args.scale)

    output_file = Path(args.output).resolve()
    output_file.write_text(html_content, encoding="utf-8")
    print(f"Preview generated successfully: {output_file}")
