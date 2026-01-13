import os
import re
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

def generate_preview_html(theme_path: str | Path, live_colors: dict[str, str] | None = None, scale: float = 0.75) -> str:
    """Helper to quickly render a preview."""
    renderer = UlauncherRendererV2(theme_path, live_colors)
    return renderer.render(scale=scale)

class UlauncherRendererV2:
    """Enhanced Ulauncher preview renderer that interprets theme CSS and manifest files."""

    def __init__(self, theme_path: str | Path, live_colors: dict[str, str] | None = None):
        self.theme_path = Path(theme_path)
        self.live_colors = live_colors or {}
        self.variables: dict[str, str] = {}
        self.manifest: dict[str, Any] = {}
        
        self._load_data()

    def _load_data(self):
        """Parse manifest.json and theme.css to extract UI properties."""
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
                content = css_file.read_text(encoding="utf-8")
                
                # Extract @define-color
                color_matches = re.findall(r"@define-color\s+([\w-]+)\s+([^;]+);", content)
                for name, val in color_matches:
                    self.variables[name] = val.strip()

            except Exception:
                logger.exception(f"Failed to parse CSS: {css_file}")

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
            if base_color.startswith("#"):
                from . import color_utils
                rgba = color_utils.hex_to_rgba(base_color)
                if rgba:
                    r, g, b, _ = rgba
                    return f"rgba({r}, {g}, {b}, {opacity})"
            return base_color

        # 3. Handle darker(color)
        darker_match = re.match(r"darker\s*\(([^)]+)\)", val)
        if darker_match:
            base_color = self._resolve_value(darker_match.group(1).strip())
            # For preview purposes, we just return the color or a slightly shaded version if we had a util
            return base_color

        return val

    def resolve_system_icon(self, name: str) -> str:
        """Resolve a system icon path for a given app name."""
        # Common hicolor paths
        base_paths = [
            "/usr/share/icons/hicolor/128x128/apps/",
            "/usr/share/icons/breeze/apps/48/"
        ]
        
        candidates = []
        if name.lower() == "spotify":
            candidates = ["spotify.png"]
        elif name.lower() == "spectacle":
            candidates = ["spectacle.svg"]

        for bp in base_paths:
            for cand in candidates:
                full_path = Path(bp) / cand
                if full_path.exists():
                    uri = full_path.as_uri()
                    logger.info(f"Resolved Ulauncher icon {name}: {uri}")
                    return uri
        
        logger.warning(f"Failed to resolve Ulauncher icon {name} in {base_paths}")
        return ""

    def render(self, scale: float = 0.75) -> str:
        # Resolve Colors with more robust mapping
        # window_bg is usually @bg_color in Ulauncher themes
        bg_color = self._get_color("window_bg", self._get_color("bg_color", "#1a1a1a"))
        border_color = self._get_color("window_border_color", "#333333")
        input_color = self._get_color("input_color", "#ffffff")
        
        # Selection
        item_box_selected = self._get_color("item_box_selected", "#4a90e2")
        item_name_selected = self._get_color("item_name_selected", "#ffffff")
        item_text_selected = self._get_color("item_text_selected", "#eeeeee")
        
        # Normal
        item_name = self._get_color("item_name", "#dddddd")
        item_text = self._get_color("item_text", "#aaaaaa")
        
        # Shortcuts
        shortcut_color = self._get_color("item_shortcut_color", "#888888")

        # Icons
        spotify_path = self.resolve_system_icon("spotify")
        spectacle_path = self.resolve_system_icon("spectacle")

        spotify_img = f'<img src="{spotify_path}" width="48" height="48">' if spotify_path else '<div style="width:48px;height:48px;background:#1db954;border-radius:24px;"></div>'
        spectacle_img = f'<img src="{spectacle_path}" width="48" height="48">' if spectacle_path else '<div style="width:48px;height:48px;background:#31363b;border-radius:4px;"></div>'

        # Main Content
        content = f"""
        <div class="container">
            <!-- Input Area -->
            <div style="padding: 35px 45px;">
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td style="font-size: 50px; color: {input_color}; font-weight: 300; letter-spacing: 1px;">
                            sptf<span style="color: {item_box_selected};">|</span>
                        </td>
                        <td align="right" valign="bottom" style="padding-bottom: 20px; opacity: 0.7; color: {item_text}; font-size: 28px;">
                            ⚙
                        </td>
                    </tr>
                </table>
            </div>

            <!-- Results -->
            <div style="padding-bottom: 25px;">
                <!-- Selected -->
                <div style="background-color: {item_box_selected}; 
                            border-radius: 12px; 
                            margin: 0 16px;
                            padding: 22px 30px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td width="70" valign="middle">{spotify_img}</td>
                            <td valign="middle" style="padding-left: 25px;">
                                <div style="font-size: 26px; font-weight: 600; color: {item_name_selected};">Spotify</div>
                                <div style="font-size: 16px; color: {item_text_selected}; opacity: 0.9;">Music Player</div>
                            </td>
                            <td align="right" valign="middle" style="font-size: 20px; color: {item_name_selected}; opacity: 0.7;">Alt+1</td>
                        </tr>
                    </table>
                </div>

                <!-- Normal -->
                <div style="margin: 8px 16px; padding: 22px 30px;">
                    <table width="100%" cellpadding="0" cellspacing="0">
                        <tr>
                            <td width="70" valign="middle">{spectacle_img}</td>
                            <td valign="middle" style="padding-left: 25px;">
                                <div style="font-size: 26px; font-weight: 500; color: {item_name};">Spectacle</div>
                                <div style="font-size: 16px; color: {item_text};">Capturas y grabaciones de pantalla</div>
                            </td>
                            <td align="right" valign="middle" style="font-size: 20px; color: {shortcut_color}; opacity: 0.9;">Alt+2</td>
                        </tr>
                    </table>
                </div>
            </div>
        </div>
        """
        
        return self.dimension_html(content, scale, bg_color, border_color)

    def dimension_html(self, content: str, scale: float, bg_color: str, border_color: str) -> str:
        """Separate function to dimension and scale the resulting HTML."""
        # Calculate scalable values to avoid "muddy" or "ghostly" renders at small scales
        # Even with transform: scale, some values feel better when adjusted
        shadow_y = int(25 * scale)
        shadow_blur = int(50 * scale)
        border_radius = int(16 * scale)
        
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
                    align-items: flex-start; /* Sit at the top */
                    width: 100vw;
                    overflow: hidden;
                }}
                body::-webkit-scrollbar {{
                    display: none;
                }}
                .scaler {{
                    /* We use scale to shrink most elements, but we sit the container inside */
                    /* to ensure the shadow doesn't get clipped by its own parent */
                    padding: {shadow_blur}px; 
                    transform: scale({scale});
                    transform-origin: top center;
                    margin-top: 0px;
                    display: inline-block;
                }}
                .container {{
                    background-color: {bg_color}; 
                    border: 2px solid {border_color}; 
                    border-radius: 16px; 
                    padding: 8px;
                    width: 650px;
                    /* Dynamic shadows change with scale for premium feel */
                    box-shadow: 0 {shadow_y}px {shadow_blur}px rgba(0,0,0,0.8);
                    text-align: left;
                    font-family: sans-serif;
                    overflow: hidden;
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
