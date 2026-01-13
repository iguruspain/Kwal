import os
import re
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Global cache to avoid expensive Path.exists lookups
_ICON_CACHE: dict[str, str] = {}

def generate_preview_html(theme_path: str | Path, live_colors: dict[str, str] | None = None, scale: float = 0.75, window_width: int | None = None,
                          manifest: dict[str, Any] | None = None, css_content: str | None = None) -> str:
    """Helper to quickly render a preview."""
    renderer = UlauncherRendererV2(theme_path, live_colors, window_width=window_width, manifest=manifest, css_content=css_content)
    return renderer.render(scale=scale)

class UlauncherRendererV2:
    """Enhanced Ulauncher preview renderer that interprets theme CSS and manifest files."""

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

    def __init__(self, theme_path: str | Path, live_colors: dict[str, str] | None = None, window_width: int | None = None,
                 manifest: dict[str, Any] | None = None, css_content: str | None = None):
        self.theme_path = Path(theme_path)
        self.live_colors = live_colors or {}
        self.variables: dict[str, str] = {}
        self.manifest = manifest or {}
        self.css_content = css_content or ""
        self.layout = self.LAYOUT_DEFAULTS.copy()
        
        if window_width is not None:
             self.layout["window_width"] = window_width
        
        self._load_data()

    @property
    def calced(self) -> dict[str, Any]:
        """Expose layout values as ready-to-use CSS values (absolute pixels)."""
        l = self.layout
        return {
            "results_padding_bottom": l["results_padding_bottom"],
            "input_padding": f"{l['input_padding_v']}px {l['input_padding_h']}px",
            "item_padding": f"{l['item_padding_v']}px {l['item_padding_h']}px",
            "item_margin": f"0 {l['item_margin_h']}px",
            "icon_container_width": l["icon_container_width"],
            "icon_size": l["icon_size"],
            "text_padding_left": l["text_padding_left"],
            "input_font_size": l["input_font_size"],
            "item_name_font_size": l["item_name_font_size"],
            "item_text_font_size": l["item_text_font_size"],
            "shortcut_font_size": l["shortcut_font_size"],
        }

    def _load_data(self):
        """Parse manifest.json and theme.css to extract UI properties."""
        self.raw_css = ""
        if not self.theme_path.is_dir():
            return

        # 1. Load Manifest
        manifest_file = self.theme_path / "manifest.json"
        if manifest_file.exists():
            try:
                with manifest_file.open("r", encoding="utf-8") as f:
                    self.manifest = json.load(f)
            except Exception:
                logger.warning(f"Failed to load manifest: {manifest_file}")

        # 2. Load and Parse CSS
        css_file = self.theme_path / "theme.css"
        if css_file.exists():
            try:
                self.raw_css = css_file.read_text(encoding="utf-8")
                
                # Extract @define-color
                color_matches = re.findall(r"@define-color\s+([\w-]+)\s+([^;]+);", self.raw_css)
                for name, val in color_matches:
                    self.variables[name] = val.strip()

            except Exception:
                logger.exception(f"Failed to parse CSS: {css_file}")

    def transform_css(self) -> str:
        """Transform Ulauncher Gtk-style CSS into standard Web-compatible CSS."""
        if not self.raw_css:
            return ""
            
        css = self.raw_css
        
        # 1. Remove @define-color lines as they break standard CSS
        css = re.sub(r"@define-color\s+[\w-]+\s+[^;]+;", "", css)
        
        # 2. Resolve all variables and functions in the variables dict first
        resolved_vars = {}
        for name in self.variables:
            resolved_vars[name] = self._get_color(name, "transparent")
            
        # 3. Replace @variable references in the CSS body
        # Matches @name followed by non-word char or end of string
        def replace_var(match):
            var_name = match.group(1)
            return resolved_vars.get(var_name, f"@{var_name}")
            
        css = re.sub(r"@([\w-]+)(?!\w)", replace_var, css)
        
        # 4. Replace CSS functions that Chromium doesn't know
        # Handle alpha(color_ref, opacity) -> rgba(...)
        # We already resolved them in step 2, but they might be used directly in rules
        def resolve_func(match):
            return self._resolve_value(match.group(0))
            
        css = re.sub(r"(alpha|darker)\s*\([^)]+\)", resolve_func, css)
        
        return css

    def _get_color(self, name: str, fallback: str) -> str:
        """Get color from live overrides, then CSS variables, then fallback. Handles alpha/darker."""
        val = fallback
        if name in self.live_colors:
            raw = self.live_colors[name]
            if raw and raw not in ["provisional_rgba_color", "provisional_hex_color", "transparent"]:
                val = raw
        elif name in self.variables:
            val = self.variables[name]
        
        return self._resolve_value(val)

    def _hex_to_rgba(self, hex_color: str) -> tuple[int, int, int, int] | None:
        """Convert hex to (r, g, b, a)."""
        from . import color_utils
        try:
            qcolor = color_utils.parse_css_color(hex_color)
            return qcolor.red(), qcolor.green(), qcolor.blue(), qcolor.alpha()
        except Exception:
            return None

    def _shade_color(self, color_str: str, percent: int) -> str:
        """Darken or lighten a color string."""
        from . import color_utils
        try:
            qcolor = color_utils.parse_css_color(color_str)
            if percent < 0:
                # QColor.darker(factor): 100 is same, 125 is 25% darker
                shaded = qcolor.darker(100 - percent)
            else:
                shaded = qcolor.lighter(100 + percent)
            return color_utils.format_css_color(shaded)
        except Exception:
            return color_str

    def _resolve_value(self, val: str) -> str:
        """Recursively resolve @variables and CSS functions like alpha() or darker()."""
        if not isinstance(val, str):
            return str(val)
        
        val = val.strip()
        
        # 1. Resolve @variable
        if val.startswith("@"):
            ref = val[1:]
            if ref in self.variables:
                return self._resolve_value(self.variables[ref])
            return val

        # 2. Handle alpha(color, opacity)
        alpha_match = re.match(r"alpha\s*\(([^,]+),\s*([^)]+)\)", val)
        if alpha_match:
            base_color = self._resolve_value(alpha_match.group(1).strip())
            opacity = alpha_match.group(2).strip()
            # If it's a hex color, convert to rgba
            rgba = self._hex_to_rgba(base_color)
            if rgba:
                r, g, b, _ = rgba
                return f"rgba({r}, {g}, {b}, {opacity})"
            return base_color

        # 3. Handle darker(color)
        darker_match = re.match(r"darker\s*\(([^)]+)\)", val)
        if darker_match:
            base_color = self._resolve_value(darker_match.group(1).strip())
            return self._shade_color(base_color, -20)

        return val

    def resolve_system_icon(self, name: str) -> str:
        """Resolve a system icon path for a given app name (with global caching)."""
        global _ICON_CACHE
        if name in _ICON_CACHE:
            return _ICON_CACHE[name]

        # Common hicolor paths
        base_paths = [
            "/usr/share/icons/hicolor/128x128/apps/",
            "/usr/share/icons/breeze/apps/48/",
            "/usr/share/icons/hicolor/scalable/apps/"
        ]
        
        candidates = []
        if name.lower() == "spotify":
            candidates = ["spotify.png", "spotify-client.png"]
        elif name.lower() == "spectacle":
            candidates = ["spectacle.svg"]

        for bp in base_paths:
            for cand in candidates:
                full_path = Path(bp) / cand
                if full_path.exists():
                    uri = full_path.as_uri()
                    _ICON_CACHE[name] = uri
                    logger.info(f"Resolved Ulauncher icon {name}: {uri}")
                    return uri
        
        logger.warning(f"Failed to resolve Ulauncher icon {name} in {base_paths}")
        _ICON_CACHE[name] = "" # Prevent repeated failures
        return ""

    def _highlight_match(self, text: str, query: str, color: str) -> str:
        """Apply color highlighting to characters that match the fuzzy query."""
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

    def render(self, scale: float = 0.75) -> str:
        # Transformed CSS
        injected_css = self.transform_css()
        
        # Resolve essential colors for the outer container and fallback
        bg_color = self._get_color("window_bg", self._get_color("bg_color", "#1a1a1a"))
        border_color = self._get_color("window_border_color", "#333333")

        # Resolve Match Highlights (Look in multiple possible locations in manifest)
        m = self.manifest
        m_colors = m.get("colors", {})
        m_hl = m.get("matched_text_hl_colors", {})
        
        color_sel = (self.live_colors.get("when_selected") or 
                     m.get("when_selected") or 
                     m_colors.get("when_selected") or 
                     m_hl.get("when_selected") or 
                     "#ffffff")
                     
        color_nosel = (self.live_colors.get("when_not_selected") or 
                       m.get("when_not_selected") or 
                       m_colors.get("when_not_selected") or 
                       m_hl.get("when_not_selected") or 
                       "#888888")

        # Icons
        spotify_path = self.resolve_system_icon("spotify")
        spectacle_path = self.resolve_system_icon("spectacle")

        spotify_img = f'<img src="{spotify_path}" class="item-icon">' if spotify_path else f'<div class="item-icon" style="background:#1db954;border-radius:50%;"></div>'
        spectacle_img = f'<img src="{spectacle_path}" class="item-icon">' if spectacle_path else f'<div class="item-icon" style="background:#31363b;border-radius:4px;"></div>'

        # Highlight Labels
        query = "sptf"
        spotify_label = self._highlight_match("Spotify", query, color_sel)
        spectacle_label = self._highlight_match("Spectacle", query, color_nosel)

        # Main Content using official Ulauncher classes
        content = f"""
        <div class="app">
            <div class="input">
                <div class="input-text">{query}<span class="caret">|</span></div>
            </div>

            <div class="results">
                <!-- Selected -->
                <div class="selected item-box">
                    <div class="item-icon-container">{spotify_img}</div>
                    <div class="item-text-container">
                        <div class="item-name">{spotify_label}</div>
                        <div class="item-text">Music Player</div>
                    </div>
                    <div class="item-shortcut">Alt+1</div>
                </div>

                <!-- Normal -->
                <div class="item-box">
                    <div class="item-icon-container">{spectacle_img}</div>
                    <div class="item-text-container">
                        <div class="item-name">{spectacle_label}</div>
                        <div class="item-text">Capturas y grabaciones de pantalla</div>
                    </div>
                    <div class="item-shortcut">Alt+2</div>
                </div>
            </div>
        </div>
        """
        
        return self.dimension_html(content, scale, bg_color, border_color, injected_css)

    def dimension_html(self, content: str, scale: float, bg_color: str, border_color: str, injected_css: str) -> str:
        """Separate function to dimension and scale the resulting HTML."""
        # Fixed base values for design standard.
        # CSS scale() will decrease/increase these proportionally.
        shadow_blur = 50
        shadow_y = 25
        
        c = self.calced
        l = self.layout
        
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
                .scaler {{
                    padding: {shadow_blur}px; 
                    transform: scale({scale});
                    transform-origin: top center;
                    display: inline-block;
                }}
                
                /* Injected Theme CSS */
                {injected_css}
                
                /* Layout Fixes for Preview (The "Nosotros" part) */
                .app {{
                    width: {l['window_width']}px;
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
                }}
                .input-text {{
                    font-size: {c['input_font_size']}px;
                    font-weight: 300; /* Light is standard for Ulauncher input */
                }}
                .item-name {{
                    font-size: {c['item_name_font_size']}px;
                    font-weight: 500; /* Medium instead of bold */
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
    import sys
    import argparse

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
