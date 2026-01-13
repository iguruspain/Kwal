import logging
import re
import getpass
import sys
from typing import Any, Mapping

logger = logging.getLogger(__name__)

class StarshipRenderer:
    MODULE_DEFAULTS = {
        "username": "[$os_symbol$user]($style)",
        "hostname": "[$ssh_symbol$hostname]($style)",
        "directory": "[$path]($style)[$read_only]($read_only_style)",
        "git_branch": "[$symbol$branch]($style)",
        "git_status": "([$all_status$ahead_behind]($style))",
        "python": "[$symbol$version]($style)",
        "docker_context": "[$symbol$context]($style)",
        "time": "[$time]($style)",
        "character": "$symbol"
    }
    
    PREVIEW_WHITELIST = {
        "username", "hostname", "directory", 
        "git_branch", "git_status", "python", 
        "line_break", "character", "time"
    }

    def __init__(self, config: Mapping[str, Any], palette_index: int | None = None):
        self.config = config
        self.palette = self._resolve_palette(palette_index)
        self.context = {
            "os_symbol": "󰣇 ",
            "user": getpass.getuser(),
            "hostname": "archlinux",
            "path": "~/dev/kwal",
            "read_only": " ",
            "branch": "main",
            "all_status": "●",
            "ahead_behind": "",
            "version": f"v{sys.version_info.major}.{sys.version_info.minor}",
            "ssh_symbol": " ",
            "symbol": "❯ ",
        }

    def _resolve_palette(self, index: int | None) -> dict:
        palettes = self.config.get("palettes", {})
        if not palettes: return {}
        names = list(palettes.keys())
        name = self.config.get("palette")
        if index is not None and 0 <= index < len(names):
            name = names[index]
        elif not name or name not in palettes:
            name = names[0]
        return palettes.get(name, {})

    def _resolve_color(self, color_key: str) -> str:
        if not color_key: return "inherit"
        clean_key = color_key.lstrip('$')
        if clean_key in self.palette:
            return str(self.palette[clean_key])
        if color_key.lower() in ("none", "transparent"): return "transparent"
        return color_key

    def _render_span(self, text: str, style_def: str) -> str:
        if not text: return ""
        parts = style_def.split()
        styles = []
        for p in parts:
            if p == "bold": styles.append("font-weight: bold")
            elif p == "italic": styles.append("font-style: italic")
            elif p.startswith("bg:"): styles.append(f"background-color: {self._resolve_color(p[3:])}")
            elif p.startswith("fg:"): styles.append(f"color: {self._resolve_color(p[3:])}")
            else: styles.append(f"color: {self._resolve_color(p)}")

        # Forzamos que los glifos tengan un bloque de color sólido
        if any(ord(c) > 127 for c in text):
             styles.append("display: inline-block; vertical-align: middle; line-height: 1.2; padding: 0 2px;")
        
        return f'<span style="{"; ".join(styles)}">{text}</span>'

    def _process_groups(self, fmt: str, module_context: str | None) -> str:
        if "(" not in fmt: return fmt
        result, i, n = [], 0, len(fmt)
        while i < n:
            char = fmt[i]
            if char == '(' and (i == 0 or fmt[i-1] != ']'):
                balance, inner_start, j = 1, i + 1, i + 1
                while j < n and balance > 0:
                    if fmt[j] == '(': balance += 1
                    elif fmt[j] == ')': balance -= 1
                    j += 1
                if balance == 0:
                    group_content = fmt[inner_start:j-1]
                    processed_inner = self._process_groups(group_content, module_context)
                    if self._validate_group_variables(processed_inner, module_context):
                        result.append(processed_inner)
                    i = j
                    continue
            result.append(char)
            i += 1
        return "".join(result) 

    def _validate_group_variables(self, text: str, module_context: str | None) -> bool:
        if not text.strip(): return False
        vars_found = re.findall(r'\$([a-zA-Z0-9_]+)', text)
        for v in vars_found:
            if v == "line_break" or v in self.context: continue
            cfg = self.config.get(v, {})
            if (v in self.MODULE_DEFAULTS or cfg) and v in self.PREVIEW_WHITELIST:
                if not cfg.get("disabled", False): continue
            return False
        return True

    def _process_format(self, fmt: str, module_context: str | None = None) -> str:
        if not fmt: return ""
        fmt = self._process_groups(fmt, module_context)
        
        pattern = re.compile(r'\[(.*?)\]\s*\((.*?)\)', re.UNICODE | re.DOTALL)
        
        current_fmt = fmt
        while True:
            match = pattern.search(current_fmt)
            if not match: break
            
            text_content, style_str = match.groups()
            
            if "$style" in style_str and module_context:
                mod_cfg = self.config.get(module_context, {})
                style_val = mod_cfg.get("style_user") if module_context == "username" else mod_cfg.get("style", "")
                style_str = style_str.replace("$style", style_val or "")

            resolved_text = self._resolve_variables(text_content, module_context)
            rendered = self._render_span(resolved_text, style_str)
                
            start, end = match.span()
            current_fmt = current_fmt[:start] + rendered + current_fmt[end:]

        return self._resolve_variables(current_fmt, module_context).replace("\\ ", " ").replace("\\", "")

    def _resolve_variables(self, text: str, module_context: str | None) -> str:
        def replace_var(m):
            var_name = m.group(1)
            if var_name == "line_break": return "<br>"
            if var_name in self.context: return str(self.context[var_name])
            
            if var_name == module_context:
                return "14:20" if var_name == "time" else ""

            mod_cfg = self.config.get(var_name, {})
            if (var_name in self.MODULE_DEFAULTS or mod_cfg) and var_name in self.PREVIEW_WHITELIST:
                if mod_cfg.get("disabled", False): return ""
                
                # Leemos el formato del TOML
                target_fmt = mod_cfg.get("format", self.MODULE_DEFAULTS.get(var_name, f"${var_name}"))
                
                # INYECCIÓN: Si es username y el TOML no incluye el icono de OS, lo añadimos
                if var_name == "username" and "$os_symbol" not in target_fmt:
                    target_fmt = target_fmt.replace("$user", "$os_symbol$user")

                symbol = mod_cfg.get("symbol", "")
                if target_fmt == "$symbol": return symbol
                target_fmt = target_fmt.replace("$symbol", symbol)
                return self._process_format(target_fmt, var_name)
            return ""
        return re.sub(r'\$([a-zA-Z0-9_]+)', replace_var, text)

    def render(self) -> str:
        font_family = (
            "'CaskaydiaCove Nerd Font', 'CaskaydiaCove NF', 'Caskaydia Cove Nerd Font', "
            "'Cascadia Code NF', 'JetBrainsMono Nerd Font', monospace, 'Fira Code', 'FiraCode Nerd Font'"
        )
        font_size ="10pt"
        line_height = "1.2"
        raw_fmt = self.config.get("format", "$username$directory$git_branch$git_status$character")
        raw_fmt = raw_fmt.replace("\\\n", "").replace("\\\r\n", "")
        rendered = self._process_format(raw_fmt)
        return (
            f'<div style="font-family: {font_family}; font-size: {font_size}; '
            f'white-space: pre; line-height: {line_height};">{rendered}</div>'
        )

def generate_preview_html(data: Mapping[str, Any], palette_index: int | None = None) -> str:
    return StarshipRenderer(data, palette_index).render()