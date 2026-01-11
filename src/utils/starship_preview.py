"""
Starship Preview Generator.
Combines parsing logic and HTML generation for QML display.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Mapping

# Configure Logger
logger = logging.getLogger(__name__)

# Default Palette Fallback
DEFAULT_PALETTE = {
    "accent": "#88C0D0",
    "accent_text": "#2E3440",
    "dir_fg": "#A3BE8C"
}

class StarshipRenderer:
    """
    Renders Starship prompt configuration to HTML for QML Text Item.
    """
    
    # Common Default Formats for modules to ensure something renders
    # when the user hasn't overridden the format in their config.
    MODULE_DEFAULTS = {
        "username": "[$user]($style)",
        "hostname": "[$ssh_symbol$hostname]($style)",
        "directory": "[$path]($style)[$read_only]($read_only_style)",
        "git_branch": "[$symbol$branch]($style)",
        "git_status": "([$all_status$ahead_behind]($style))",
        "python": "[$symbol$version]($style)",
        "docker_context": "[$symbol$context]($style)",
        "time": "[$time]($style)",
        "os": "[$symbol]($style)",
        "character": "$symbol"
    }
    
    # Whitelist of modules to display in preview to avoid clutter.
    # We only want to simulate a specific scenario (Python + Docker project).
    PREVIEW_WHITELIST = {
        "os", "username", "hostname", "directory", 
        "git_branch", "git_status", 
        "python", 
        "line_break", "character", "time"
    }

    def __init__(self, config: Mapping[str, Any], palette_index: int | None = None):
        import getpass
        current_user = getpass.getuser()
        
        self.config = config
        self.palette = self._resolve_palette(palette_index)
        
        # Sample data to populate variables
        # Note: We avoid putting top-level module names (like 'os', 'directory') here
        # so that they are processed as modules, not simple string replacements.
        self.context = {
            # Core variables
            "user": current_user,
            "hostname": "archlinux",
            "path": "~/dev/kwal",
            "read_only": " ",
            "branch": "main",
            "all_status": "●",
            "ahead_behind": "",
            "version": "v3.12", # Python version
            # "time": "14:20", # REMOVED to allow module processing
            
            # Module specific symbols (default overrides or internal usage)
            "ssh_symbol": " ",
            "symbol": "❯ ", # Default Char symbol
        }

    def _resolve_palette(self, index: int | None) -> dict[str, str]:
        """Extracts and flattens the selected palette from config."""
        palettes = self.config.get("palettes")
        if not isinstance(palettes, dict) or not palettes:
            return DEFAULT_PALETTE.copy()

        names = list(palettes.keys())
        if not names:
            return DEFAULT_PALETTE.copy()

        # Determine which palette to use
        # 1. Start with the one defined in 'palette' key in root config
        default_palette_name = self.config.get("palette") 
        selected_name = default_palette_name if isinstance(default_palette_name, str) else names[0]

        # 2. If index is provided, override it
        if index is not None and 0 <= index < len(names):
            selected_name = names[index]
            
        # 3. Fetch data
        selected_palette = palettes.get(selected_name)
        # Fallback if name from 'palette' key doesn't exist in [palettes]
        if not isinstance(selected_palette, dict):
            # Fallback to first
            selected_palette = palettes.get(names[0], {})
            
        return {str(k): str(v) for k, v in selected_palette.items()}

    def _resolve_color(self, color_key: str) -> str:
        """Resolves config color keys to actual hex codes."""
        if not color_key:
            return "inherit"
        
        # Check if it's a variable in our palette
        if color_key in self.palette:
            return self.palette[color_key]
            
        # Standard keywords
        if color_key.lower() in ("transparent", "none", "bg:none"):
            return "transparent"
            
        return color_key

    def _parse_style_string(self, style_str: str) -> dict:
        """Parses a style string (e.g., 'bold red bg:blue') into dict."""
        base = {}
        if not style_str:
            return base
            
        parts = style_str.split()
        for part in parts:
            if part == "bold":
                base["bold"] = True
            elif part == "italic":
                base["italic"] = True
            elif part.startswith("bg:"):
                base["bg"] = part[3:]
            elif part.startswith("fg:"):
                base["fg"] = part[3:]
            else:
                # Assuming simple color name is foreground
                base["fg"] = part
        return base
        
    def _render_span(self, text: str, style_def: str | dict) -> str:
        """Renders text inside an HTML span with inline styles."""
        if not text:
            return ""
        
        style = style_def if isinstance(style_def, dict) else self._parse_style_string(style_def)    
        
        fg = self._resolve_color(style.get("fg", ""))
        bg = self._resolve_color(style.get("bg", ""))
        bold = style.get("bold", False)
        italic = style.get("italic", False)
        
        # Glyph detection
        clean_text = text.strip()
        is_glyph = len(clean_text) == 1 and ord(clean_text[0]) > 127
        
        styles = []
        if fg and fg != "inherit":
            styles.append(f"color: {fg}")
        if bg and bg != "transparent":
            # Ensure background renders nicely in QML
            styles.append(f"background-color: {bg}")
        if bold:
            styles.append("font-weight: bold")
        if italic:
            styles.append("font-style: italic")
            
        # Fix for spaces with background color in some renderers:
        display_text = text
        if text == " " and bg != "transparent":
            display_text = "&nbsp;"

        # Font adjustments for glyphs to align better
        if is_glyph:
             styles.append("font-size: 1.2em")
             styles.append("vertical-align: middle")
        
        style_attr = "; ".join(styles)
        return f'<span style="{style_attr}">{display_text}</span>'

    def _get_module_config(self, module_name: str) -> dict:
        cfg = self.config.get(module_name)
        if isinstance(cfg, dict):
            return cfg
        return {}
    
    def _process_groups(self, fmt: str, module_context: str | None) -> str:
        """
        Handle Starship's Grouping syntax: ( content ).
        If any variable $var inside content is undefined/empty, the whole group is removed.
        Handles nested groups by regex? Simple greedy match might fail nesting.
        We'll use a simple recursive parser for parentheses.
        """
        if "(" not in fmt:
            return fmt
            
        result = []
        i = 0
        n = len(fmt)
        
        while i < n:
            char = fmt[i]
            
            if char == '\\' and i + 1 < n and fmt[i+1] == '(':
                # Escaped open paren `\(` -> literal `(`
                result.append('(')
                i += 2
                continue
            elif char == '\\' and i + 1 < n and fmt[i+1] == ')':
                # Escaped close paren `\)` -> literal `)`
                result.append(')')
                i += 2
                continue
                
            if char == '(':
                # Check for preceding ']' -> indicates style definition [text](style), NOT a group
                if i > 0 and fmt[i-1] == ']':
                    result.append('(')
                    i += 1
                    continue

                # Start of a group
                # Find matching closing paren, handling nesting
                balance = 1
                inner_start = i + 1
                j = inner_start
                while j < n:
                    if fmt[j] == '\\' and j + 1 < n:
                        j += 2
                        continue
                        
                    if fmt[j] == '(':
                        balance += 1
                    elif fmt[j] == ')':
                        balance -= 1
                        if balance == 0:
                            break
                    j += 1
                
                if balance == 0:
                    # Found group content: fmt[inner_start:j]
                    group_content = fmt[inner_start:j]
                    
                    # Process nested groups inside first
                    processed_inner = self._process_groups(group_content, module_context)
                    
                    # Validate variables in this group
                    # If any whitelist/context check fails for variables in processed_inner, drop the group.
                    if self._validate_group_variables(processed_inner, module_context):
                        result.append(processed_inner)
                    else:
                        # Drop group
                        pass
                        
                    i = j + 1
                    continue
                else:
                    # Unbalanced, treat as literal
                    result.append(char)
            else:
                result.append(char)
            i += 1
            
        return "".join(result)

    def _validate_group_variables(self, text: str, module_context: str | None) -> bool:
        """
        Returns False if any $var in text resolves to empty/hidden.
        """
        # Find all variables
        vars_found = re.findall(r'\$([a-zA-Z0-9_]+)', text)
        for var_name in vars_found:
            # Check logic similar to _resolve_variables but just for validity
            if var_name == "line_break": continue
            
            # 1. Context check
            if var_name in self.context:
                continue # Valid
            
            # 2. Module check
            mod_cfg = self._get_module_config(var_name)
            is_allowed = var_name in self.PREVIEW_WHITELIST
            is_disabled = mod_cfg.get("disabled", False)
            
            if (var_name in self.MODULE_DEFAULTS or mod_cfg) and is_allowed and not is_disabled:
                 continue # Valid (module will produce output)
            
            # Undefined or hidden -> Group Fail
            return False
            
        return True

    def _process_format(self, fmt: str, module_context: str | None = None) -> str:
        """
        Parses the format string using an Innermost-First strategy.
        """
        if not fmt:
            return ""

        # 1. First, handle Groups ( ... )
        # This removes blocks like (\($virtualenv\)) if $virtualenv is effectively empty.
        fmt_grouped = self._process_groups(fmt, module_context)
        
        current_fmt = fmt_grouped
        
        # Regex for innermost [text](style). 
        # [([^\[\]]*)] -> Matches brackets containing no other brackets
        # \(([^()]*)\) -> Matches parenthesis containing no other parens
        pattern = re.compile(r'\[([^\[\]]*)\]\(([^()]*)\)')
        
        while True:
            match = pattern.search(current_fmt)
            if not match:
                break
            
            full_match = match.group(0)
            text_content = match.group(1)
            style_str = match.group(2)
            
            # Resolve $style inside brackets
            if "$style" in style_str:
                resolved_style_val = ""
                if module_context:
                    mod_cfg = self._get_module_config(module_context)
                    if module_context == "username":
                        resolved_style_val = mod_cfg.get("style_user", mod_cfg.get("style", "bold yellow"))
                    else:
                        resolved_style_val = mod_cfg.get("style", "")
                
                style_str = style_str.replace("$style", resolved_style_val)

            # Resolve variables inside the text content
            resolved_text = self._resolve_variables(text_content, module_context)
            
            # If resolved text is empty (module hidden), render nothing to avoid [] artifacts
            if not resolved_text.strip() and not is_glyph(text_content):
                 rendered_span = ""
            else:
                 rendered_span = self._render_span(resolved_text, style_str)
            
            # Replace in current_fmt
            start, end = match.span()
            current_fmt = current_fmt[:start] + rendered_span + current_fmt[end:]

        # Resolve top-level variables 
        final_output = self._resolve_variables(current_fmt, module_context)
        return final_output

    def _resolve_variables(self, text: str, module_context: str | None) -> str:
        """Replace $vars in text. Handles module recursion if var is a module."""
        
        def replace_var(m):
            var_name = m.group(1)
            if var_name == "line_break":
                return "<br>"
            
            # 1. Check valid context
            if var_name in self.context:
                return str(self.context[var_name])
            
            # 2. Check Module
            mod_cfg = self._get_module_config(var_name)
            
            # Whitelist / Disabled check
            is_allowed = var_name in self.PREVIEW_WHITELIST
            is_disabled = mod_cfg.get("disabled", False)
            
            is_valid_module = (var_name in self.MODULE_DEFAULTS or mod_cfg)
            
            if is_valid_module and is_allowed and not is_disabled:
                # Prevent infinite recursion if a module refers to a variable with same name (e.g. [time] uses $time)
                if module_context and var_name == module_context:
                    if var_name == "time":
                        return "14:20"
                    return ""

                default_fmt = self.MODULE_DEFAULTS.get(var_name, f"${var_name}")
                target_fmt = mod_cfg.get("format", default_fmt)
                
                sym = mod_cfg.get("symbol", "")
                if sym:
                    target_fmt = target_fmt.replace("$symbol", sym)
                elif module_context == "os" and var_name == "symbol": 
                        pass

                return self._process_format(target_fmt, module_context=var_name)
            
            # 3. Not found/allowed -> Empty
            return ""

        return re.sub(r'\$([a-zA-Z0-9_]+)', replace_var, text)

    def render(self) -> str:
        try:
            # Default to generic complex format if not specified
            raw_fmt = self.config.get("format", "$username$directory$git_branch$git_status$character")
            
            # Heavy cleanup of the raw format before processing
            # 1. Handle TOML multiline string escapes
            raw_fmt = raw_fmt.replace("\\\n", "").replace("\\\r\n", "")
            
            rendered_content = self._process_format(raw_fmt)
            
            # Wrap in reasonable defaults for preview visibility
            return (
                f'<div style="font-family: \'CaskaydiaCove Nerd Font\', \'CaskaydiaCove NF\', \'Cascadia Code NF\', \'FiraCode Nerd Font\', \'JetBrainsMono Nerd Font\', monospace; font-size: 10pt; white-space: pre-wrap;">'
                f'{rendered_content}'
                f'</div>'
            )
        except Exception as e:
            logger.error(f"Starship Preview Render Error: {e}")
            return f'<span style="color: #ff5555;">Preview Error: {e}</span>'

def is_glyph(text):
    return len(text.strip()) == 1 and ord(text.strip()[0]) > 127

def generate_preview_html(data: Mapping[str, Any], palette_index: int | None = None) -> str:
    """
    Generate QML-compatible HTML preview for a specific config and palette.
    """
    renderer = StarshipRenderer(data, palette_index)
    return renderer.render()

# --- CLI for Testing ---
if __name__ == "__main__":
    import argparse
    import sys
    try:
        import tomlkit
    except ImportError:
        print("tomlkit required for CLI usage")
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("config_file", help="Path to starship.toml")
    args = parser.parse_args()
    
    try:
        with open(args.config_file, "r", encoding="utf-8") as f:
            data = tomlkit.parse(f.read())
        
        html = generate_preview_html(data)
        print("<!-- Generated Preview Fragment -->")
        print(html)
    except Exception as e:
        print(f"Error: {e}")
