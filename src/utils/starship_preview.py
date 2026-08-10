import getpass
import logging
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, cast

import tomlkit

from .color_utils import format_css_color

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Fallback ANSI colors (Gruvbox-style) for the preview
STANDARD_COLORS: Dict[str, str] = {
    "black": "#000000",
    "red": "#cc241d",
    "green": "#98971a",
    "yellow": "#d79921",
    "blue": "#458588",
    "purple": "#b16286",
    "cyan": "#689d6a",
    "white": "#a89984",
    "orange": "#fe8019",
    "gray": "#928374",
    "grey": "#928374",
}

# Nerd Font powerline glyphs used as visual connectors
POWERLINE_GLYPHS = ""

# Triangle connectors that get the `glyph2` CSS class for independent styling
TRIANGLE_CONNECTORS = ""

# Modules that may be expanded when encountered as `$module_name` in a format string
WHITELIST_MODULES = frozenset({
    "os", "username", "directory", "python",
    "time", "git_branch", "git_status", "character",
})

# Default format templates per module when `format` key is absent
DEFAULT_MODULE_FORMATS: Dict[str, str] = {
    "os": "[$symbol]($style)",
    "character": "$symbol",
}

# Placeholder text shown when the TOML is invalid or empty
LOADING_SPAN = '<span style="color: #666;">Cargando...</span>'

# Regex patterns (compiled once at module level for performance)
_RE_UNRESOLVED_VAR = re.compile(r"\$[a-zA-Z_0-9]+")
_RE_UNRESOLVED_VAR_BRACE = re.compile(r"\$\{[a-zA-Z_0-9]+\}")
_RE_EMPTY_GROUP = re.compile(r"(?<!\])\(\s*\)")
_RE_EMPTY_GROUP_SPACES = re.compile(r"(?<!\])\(\s+\)")
_RE_INTERNAL_GROUP = re.compile(r"(?<!\])\(([^()]*)\)")
_RE_VAR_IN_GROUP = re.compile(r"\$[a-zA-Z_0-9]+|\$\{[a-zA-Z_0-9]+\}")
_RE_DOUBLE_SPACES = re.compile(r"\s{2,}")
_RE_FG_COLOR = re.compile(r"fg:([a-zA-Z0-9_#]+)")
_RE_BG_COLOR = re.compile(r"bg:([a-zA-Z0-9_#]+)")
_RE_TRIANGLE_CONNECTOR = re.compile(r"[]")
_RE_VAR_NAME = re.compile(r"^\$([a-zA-Z0-9_]+)")

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

# Segment tuple returned by _find_* helpers: (type, content, style/var, start, end)
Segment = Tuple[str, str, str, int, int]

# Render element passed to _to_html
ElementDict = Dict[str, Any]


# ---------------------------------------------------------------------------
# HTML / CSS template
# ---------------------------------------------------------------------------

def _build_preview_css(scale: float, width: int) -> str:
    """Returns the <style> block for the preview HTML wrapper."""
    shadow_blur = 40
    shadow_y = 20
    return f"""\
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
                    font-family: 'CaskaydiaCove Nerd Font', monospace;
                }}
                body::-webkit-scrollbar {{ display: none; }}
                .scaler {{
                    padding: {shadow_blur}px;
                    transform: scale({scale});
                    transform-origin: top center;
                    display: inline-block;
                    }}
                .terminal {{
                    display: inline-block;
                    width: {width}px;
                    background: #181818;
                    border: 1px solid #303030;
                    border-radius: 8px;
                    padding: 15px 20px;
                    box-shadow: 0 {shadow_y}px {shadow_blur}px rgba(0,0,0,0.8);
                    white-space: nowrap;
                    overflow: hidden;
                }}
                .prompt-line {{ display: flex; align-items: stretch; height: 32px; line-height: 32px; }}
                span {{ display: flex; align-items: center; justify-content: center; height: 100%; }}
                .text-node {{ padding: 0 4px; font-size: 14px; white-space: pre; }}
                .glyph:not(.glyph2) {{ display: inline-flex; align-items: center; justify-content: center; font-size: 27px; margin: 0px -0.5px 0 -0.5px; line-height: 1; transform: translateY(0.5px); }}
                .glyph2 {{ display: inline-flex; align-items: center; justify-content: center; font-size: 27px; margin: 0 -0.5px; line-height: 1; transform: translateY(0px); }}
            </style>"""


def _build_html_wrapper(inner_html: str, scale: float, width: int) -> str:
    """Wraps *inner_html* in a complete HTML document with the preview CSS."""
    return f"""\
        <html>
        <head>
{_build_preview_css(scale, width)}
        </head>
        <body>
            <div class="scaler"><div class="terminal"><div class="prompt-line">{inner_html}</div></div></div>
        </body>
        </html>
        """


class StarshipRenderer:
    """Renders a Starship TOML configuration as an HTML preview."""

    def __init__(
        self,
        toml_content: str | Dict[str, Any],
        palette_index: Optional[int] = None,
        scale: float = 1.0,
        width: int = 800,
    ) -> None:
        self.scale = scale
        self.width = width
        self.palette_index = palette_index

        self.doc: Dict[str, Any]
        self.valid: bool
        self.doc, self.valid = self._parse_toml(toml_content)

        self._active_palette = self._get_active_palette()
        self.runtime_context = self._build_runtime_context()

    @staticmethod
    def _parse_toml(content: str | Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
        """Parse TOML content. Accepts either a raw string or an already-parsed dict."""
        if isinstance(content, dict):
            return content, True

        if not content or not isinstance(content, str) or not content.strip():
            return {}, False

        try:
            return tomlkit.parse(content), True
        except Exception as exc:
            logger.error("Error parsing TOML: %s", exc)
            return {}, False

    @staticmethod
    def _build_runtime_context() -> Dict[str, str]:
        """Build the fake runtime context used for variable expansion in previews."""
        return {
            "os": "Arch",
            "username": getpass.getuser(),
            "directory": "~/dev/scripts",
            "python": f"v{sys.version_info.major}.{sys.version_info.minor}",
            "time": datetime.now().strftime("%R"),
            "git_branch": "main",
            "git_status": "",
        }

    def _get_active_palette(self) -> Dict[str, Any]:
        """Resolves the current palette to use based on index or document setting."""
        if not self.valid:
            return {}
        palettes = self.doc.get("palettes", {})
        p_name = self.doc.get("palette")
        
        if self.palette_index is not None:
            names = list(palettes.keys())
            if 0 <= self.palette_index < len(names):
                p_name = names[self.palette_index]
        
        active = palettes.get(p_name, {}) if p_name else {}
        return cast(Dict[str, Any], active)

    def _resolve_color(self, color_key: str) -> str:
        if not self.valid or not color_key:
            return "inherit"

        clean_key = str(color_key).replace("fg:", "").replace("bg:", "").strip().lower()
        
        # 1. Prioridad: Paleta activa del TOML > Colores ANSI estándar > Valor literal
        val = self._active_palette.get(clean_key)
        if val is None:
            # Fallback a colores ANSI predefinidos (estilo Gruvbox por defecto para el preview)
            val = self.STANDARD_COLORS.get(clean_key, clean_key)
        
        # 2. Formateo mediante utilidades globales (maneja hex, rgb, rgba y nombres)
        return format_css_color(str(val).strip())

    # ------------------------------------------------------------------
    # Content cleaning
    # ------------------------------------------------------------------

    @staticmethod
    def _remove_unresolved_vars(text: str) -> str:
        """Strip unresolved Starship variables like $var and ${var}."""
        text = _RE_UNRESOLVED_VAR.sub("", text)
        return _RE_UNRESOLVED_VAR_BRACE.sub("", text)

    @staticmethod
    def _unescape_starship(text: str) -> str:
        """Convert Starship escape sequences back to their literal characters."""
        text = text.replace("\\(", "(").replace("\\)", ")")
        text = text.replace("\\[", "[").replace("\\]", "]")
        return text.replace("\\ ", " ")

    @staticmethod
    def _strip_empty_optional_groups(text: str) -> str:
        """Remove residual empty optional groups `()` left after variable expansion.

        Starship uses `(...)` for optional groups that hide when empty.
        After substitution, groups like `( )` or `(v3.10 )` need special handling.
        """
        python_ver = f"v{sys.version_info.major}.{sys.version_info.minor}"
        for _ in range(4):
            text = _RE_EMPTY_GROUP.sub("", text)
            text = _RE_EMPTY_GROUP_SPACES.sub("", text)
            text = text.replace("()", "").replace("( )", "")
            text = text.replace("( )", "")
            text = text.replace(f"( {python_ver} )", f" ({python_ver} )")
        return text

    def clean_final_content(self, text: str) -> str:
        """Clean Starship formatting artifacts from rendered text."""
        if not text:
            return ""

        text = str(text)

        # 1. Remove unresolved variables
        text = self._remove_unresolved_vars(text)

        # 2. Unescape Starship escape sequences so empty groups can be detected
        text = self._unescape_starship(text)

        # 3. Strip residual empty optional groups
        text = self._strip_empty_optional_groups(text)

        # 4. Normalize whitespace
        text = _RE_DOUBLE_SPACES.sub(" ", text)
        return text.strip()

    # ------------------------------------------------------------------
    # Module format expansion
    # ------------------------------------------------------------------

    @staticmethod
    def _build_module_substitutions(
        module_name: str,
        module_cfg: Dict[str, Any],
        context: Dict[str, str],
    ) -> Dict[str, str]:
        """Build the variable substitution map for a single Starship module."""
        # Base: all scalar keys from the module config
        subs = {
            str(k): str(v)
            for k, v in module_cfg.items()
            if not isinstance(v, (dict, list))
        }

        # Fallback for missing `style` key
        if "style" not in subs:
            subs["style"] = str(
                module_cfg.get("style_user", "")
                if module_name == "username"
                else module_cfg.get("style", "")
            )

        # Runtime values derived from context
        v_val = context.get(module_name, "")
        if module_name == "os":
            v_val = ""  # Don't leak "Arch" as the OS module version

        runtime_values: Dict[str, str] = {
            "path": context.get("directory", ""),
            "user": context.get("username", ""),
            "username": context.get("username", ""),
            "time": context.get("time", ""),
            "version": v_val,
            "branch": context.get("git_branch", ""),
            "all_status": context.get("git_status", ""),
            "ahead_behind": "",
            "virtualenv": "",
        }

        # Module-specific symbol resolution
        if module_name == "character":
            runtime_values["symbol"] = str(
                module_cfg.get("success_symbol", module_cfg.get("symbol", "❯"))
            )

        if module_name == "os":
            os_val = context.get("os", "Arch")
            os_symbols = module_cfg.get("symbols", {})
            if isinstance(os_symbols, dict) and os_val in os_symbols:
                runtime_values["symbol"] = os_symbols[os_val]
            runtime_values["os"] = ""  # Hide the literal OS name

        subs.update(runtime_values)
        return subs

    @staticmethod
    def _substitute_variables(text: str, subs: Dict[str, str]) -> str:
        """Replace $var and ${var} placeholders with values from *subs*."""
        for var, val in subs.items():
            text = text.replace(f"${var}", str(val)).replace(f"${{{var}}}", str(val))
        return text

    @staticmethod
    def _evaluate_optional_groups(text: str) -> str:
        """Evaluate Starship optional groups `(...)`.

        A group is hidden if, after stripping variables and escape sequences,
        its contents are empty. Processed groups are temporarily marked with
        control characters to avoid re-processing nested patterns.
        """
        changed = True
        while changed:
            changed = False
            m = _RE_INTERNAL_GROUP.search(text)
            if m is None:
                break

            inner = m.group(1)
            # Check what remains after removing variables and escapes
            content_check = _RE_VAR_IN_GROUP.sub("", inner)
            content_check = content_check.replace("\\(", "").replace("\\)", "")
            content_check = content_check.replace("\\[", "").replace("\\]", "").strip()

            if not content_check:
                # Group is empty → remove entirely
                text = text[: m.start()] + text[m.end() :]
            else:
                # Group has content → mark with control chars to skip next iteration
                text = text[: m.start()] + "\u0001" + inner + "\u0002" + text[m.end() :]
            changed = True

        return text.replace("\u0001", "(").replace("\u0002", ")")

    def solve_module_format(
        self, module_name: str, module_cfg: Any, context: Dict[str, str]
    ) -> str:
        """Expand a module's format string into rendered text.

        Orchestrates: default format → substitutions → variable expansion
        → optional group evaluation → final cleanup.
        """
        if not isinstance(module_cfg, dict):
            return ""

        # 1. Resolve format template
        default_fmt = DEFAULT_MODULE_FORMATS.get(module_name, "$symbol$version")
        fmt = str(module_cfg.get("format", default_fmt))

        # 2. Build substitution map
        subs = self._build_module_substitutions(module_name, module_cfg, context)

        # 3. First pass: substitute variables
        result = self._substitute_variables(fmt, subs)

        # 4. Evaluate optional groups `(...)`
        result = self._evaluate_optional_groups(result)

        # 5. Final pass: catch any remaining variables from outer scope
        result = self._substitute_variables(result, subs)

        # 6. Cleanup
        result = _RE_DOUBLE_SPACES.sub(" ", result)
        if module_name == "os":
            result = result.strip()
        return result

    # ------------------------------------------------------------------
    # Segment parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _find_bracket_block(text: str, start: int) -> Optional[Tuple[int, int, str, str]]:
        """Find a `[content](style)` block starting at *start*.

        Returns (content, style, block_start, block_end) or None.
        """
        depth = 1
        j = start + 1
        while j < len(text) and depth > 0:
            if text[j] == "[":
                depth += 1
            elif text[j] == "]":
                depth -= 1
            j += 1

        if depth != 0 or j >= len(text) or text[j] != "(":
            return None

        content = text[start + 1 : j - 1]
        k = j + 1
        while k < len(text) and text[k] != ")":
            k += 1
        if k >= len(text):
            return None

        style = text[j + 1 : k]
        return content, style, start, k + 1

    @staticmethod
    def _find_variable(text: str, start: int) -> Optional[Tuple[str, int]]:
        """Find a `$var_name` at *start*. Returns (var_name, end_pos) or None."""
        m = _RE_VAR_NAME.match(text[start:])
        if m:
            return m.group(1), start + m.end()
        return None

    def get_segments(self, text: str) -> List[Segment]:
        """Tokenize a Starship format string into segments.

        Segment types:
        - ``'block'``: ``[content](style)``
        - ``'lb'``: ``$line_break``
        - ``'var'``: ``$module_name``
        """
        segments: List[Segment] = []
        i = 0
        text_len = len(text)

        while i < text_len:
            ch = text[i]

            if ch == "[":
                result = self._find_bracket_block(text, i)
                if result is not None:
                    content, style, block_start, block_end = result
                    segments.append(("block", content, style, block_start, block_end))
                    i = block_end
                    continue

            if text.startswith("$line_break", i):
                segments.append(("lb", "", "", i, i + 11))
                i += 11
                continue

            if ch == "$":
                result = self._find_variable(text, i)
                if result is not None:
                    var_name, end_pos = result
                    segments.append(("var", "", var_name, i, end_pos))
                    i = end_pos
                    continue

            i += 1

        return segments

    @staticmethod
    def _make_text_element(
        content: str, default_style: str, is_starship: bool
    ) -> Optional[ElementDict]:
        """Create a text element dict, or None if the content is insignificant."""
        cleaned = content.strip()
        if not cleaned and content != " ":
            return None
        return {
            "type": "starship" if is_starship else "custom",
            "style": default_style,
            "final_content": content,
        }

    def process_text_segment(
        self,
        text: str,
        default_style: str,
        group: str,
        is_starship: bool,
        elements: List[ElementDict],
    ) -> None:
        """Recursively process a text segment, expanding variables and blocks."""
        segments = self.get_segments(text)

        if not segments:
            el = self._make_text_element(text, default_style, is_starship)
            if el is not None:
                el["final_content"] = self.clean_final_content(text)
                elements.append(el)
            return

        last_idx = 0
        for stype, content, sval, start, end in segments:
            # Text before this segment
            pre = text[last_idx:start]
            pre_el = self._make_text_element(pre, default_style, is_starship)
            if pre_el is not None:
                pre_el["final_content"] = self.clean_final_content(pre)
                elements.append(pre_el)

            if stype == "block":
                inner_style = sval if sval not in ("$style", "${style}") else default_style
                self.process_text_segment(content, inner_style, group, is_starship, elements)

            elif stype == "lb":
                elements.append({"type": "line_break"})

            elif stype == "var":
                if sval in WHITELIST_MODULES:
                    module_cfg = self.doc.get(sval, {})
                    if not (isinstance(module_cfg, dict) and module_cfg.get("disabled") is True):
                        expanded = self.solve_module_format(
                            sval, module_cfg, self.runtime_context
                        )
                        self.process_text_segment(
                            expanded,
                            str(module_cfg.get("style", "")),
                            sval,
                            True,
                            elements,
                        )

            last_idx = end

        # Trailing text after the last segment
        post = text[last_idx:]
        post_el = self._make_text_element(post, default_style, is_starship)
        if post_el is not None:
            post_el["final_content"] = self.clean_final_content(post)
            elements.append(post_el)

    # ------------------------------------------------------------------
    # Rendering pipeline
    # ------------------------------------------------------------------

    def render(self) -> str:
        """Entry point: parse the TOML format string and produce HTML."""
        if not self.valid:
            return _build_html_wrapper(LOADING_SPAN, self.scale, self.width)

        format_str = str(self.doc.get("format", "")).replace("\\\n", "").replace("\n", "")
        elements: List[ElementDict] = []
        self.process_text_segment(format_str, "", "root", False, elements)
        return self._to_html(elements)

    @staticmethod
    def _resolve_style_to_css(style_str: str) -> List[str]:
        """Parse a Starship style string into a list of CSS declarations."""
        css: List[str] = []
        if "bold" in style_str.lower():
            css.append("font-weight: bold")
        return css

    def _build_element_css(self, style_str: str) -> List[str]:
        """Build the full CSS declaration list for a single element."""
        css = self._resolve_style_to_css(style_str)

        fg_match = _RE_FG_COLOR.search(style_str)
        bg_match = _RE_BG_COLOR.search(style_str)

        if bg_match:
            css.append(f"background-color: {self._resolve_color(bg_match.group(1))}")
        if fg_match:
            css.append(f"color: {self._resolve_color(fg_match.group(1))}")
        elif style_str and "bg:" not in style_str:
            bare_color = style_str.replace("bold", "").strip()
            if bare_color:
                css.append(f"color: {self._resolve_color(bare_color)}")

        return css

    @staticmethod
    def _classify_content_class(content: str) -> str:
        """Determine the CSS class for a content string (glyph vs text)."""
        if any(g in content for g in POWERLINE_GLYPHS):
            if _RE_TRIANGLE_CONNECTOR.search(content):
                return "glyph glyph2"
            return "glyph"
        return "text-node"

    def _to_html(self, elements: List[ElementDict]) -> str:
        """Convert a list of render elements into an HTML string."""
        html_segments: List[str] = []

        for el in elements:
            if el["type"] == "line_break":
                html_segments.append("</div><div class=\"prompt-line\">")
                continue

            content = el.get("final_content", "")
            if not content:
                continue

            css = self._build_element_css(str(el.get("style", "")))
            cls = self._classify_content_class(content)
            escaped = content.replace(" ", "&nbsp;")

            html_segments.append(
                f'<span class="{cls}" style="{"; ".join(css)}">{escaped}</span>'
            )

        return _build_html_wrapper("".join(html_segments), self.scale, self.width)

    # ------------------------------------------------------------------
    # Legacy alias (kept for backward compatibility)
    # ------------------------------------------------------------------

    def _wrap(self, inner_html: str) -> str:
        """Legacy wrapper — delegates to the module-level helper."""
        return _build_html_wrapper(inner_html, self.scale, self.width)


# ---------------------------------------------------------------------------
# Module entry point
# ---------------------------------------------------------------------------

def generate_preview_html(
    data: Any, palette_index: int | None = None, scale: float = 1.0, width: int = 800
) -> str:
    """Public entry point called by ``models.py`` to generate an HTML preview."""
    renderer = StarshipRenderer(data, palette_index, scale, width)
    return renderer.render()