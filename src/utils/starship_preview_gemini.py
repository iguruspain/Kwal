import re
import getpass
import sys
import logging
from datetime import datetime
import tomlkit
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class StarshipRenderer:
    def __init__(self, toml_content: str, palette_index: int | None = None, scale: float = 1.0, width: int = 800):
        # Accept either a parsed dict (from models) or a TOML string
        if isinstance(toml_content, dict):
            self.doc = toml_content
            self.valid = True
        else:
            if not toml_content or not isinstance(toml_content, str) or not toml_content.strip():
                self.doc = {}
                self.valid = False
            else:
                try:
                    self.doc = tomlkit.parse(toml_content)
                    self.valid = True
                except Exception as e:
                    if toml_content and toml_content.strip():
                        logger.error(f"Error parsing TOML: {e}")
                    self.doc = {}
                    self.valid = False

        self.scale = scale
        self.width = width
        self.palette_index = palette_index
        
        self.runtime_context = {
            "os": "Arch",
            "username": getpass.getuser(),
            "directory": "~/dev/scripts",
            "python": f"v{sys.version_info.major}.{sys.version_info.minor}",
            "time": datetime.now().strftime("%R"),
            "git_branch": "main",
            "git_status": "",
        }
        self.whitelist_modules = {"os", "username", "directory", "python", "time", "git_branch", "git_status", "character"}

    def clean_final_content(self, text: str) -> str:
        """Limpia el contenido de artefactos de formato de Starship."""
        if not text: return ""
        text = str(text)
        
        # 1. Eliminar variables no resueltas
        text = re.sub(r'\$[a-zA-Z_0-9]+', '', text)
        text = re.sub(r'\$\{[a-zA-Z_0-9]+\}', '', text)
        
        # 2. Primero unimos escapes para que los grupos vacíos resultantes se puedan limpiar
        text = text.replace('\\(', '(').replace('\\)', ')').replace('\\[', '[').replace('\\]', ']')
        text = text.replace('\\ ', ' ')

        # 3. Limpiar grupos opcionales vacíos residuales ( ) que no sean estilos
        for _ in range(4):
            text = re.sub(r'(?<!\])\(\s*\)', '', text)
            text = re.sub(r'(?<!\])\(\s+\)', '', text)
            text = text.replace('()', '').replace('( )', '')

        # 4. Normalizar espacios
        text = re.sub(r'\s{2,}', ' ', text)
        text = text.strip()
        
        return text

    def solve_module_format(self, module_name: str, module_cfg: Any, context: Dict) -> str:
        if not isinstance(module_cfg, dict): return ""
        
        # 1. Obtener el formato base o fallback inteligente
        default_fmt = "$symbol$version"
        if module_name == "os":
            default_fmt = "[$symbol]($style)" # OS normalmente solo muestra el icono
        elif module_name == "character":
            default_fmt = "$symbol"
            
        fmt = str(module_cfg.get("format", default_fmt))
        
        # 2. Construir mapa de sustitución dinámico
        subs = {str(k): str(v) for k, v in module_cfg.items() if not isinstance(v, (dict, list))}
        
        # 3. Mapeos inteligentes de alias de Starship
        if "style" not in subs:
            if module_name == "username":
                subs["style"] = str(module_cfg.get("style_user", ""))
            else:
                subs["style"] = str(module_cfg.get("style", ""))
        
        # 4. Añadir/Sobrescribir con valores reales del sistema (Runtime Context)
        v_val = str(context.get(module_name, ""))
        # No queremos "Arch" como versión del módulo OS si no se pide explícitamente
        if module_name == "os": v_val = ""

        runtime_values = {
            "path": context.get("directory", ""),
            "user": context.get("username", ""),
            "username": context.get("username", ""),
            "time": context.get("time", ""),
            "version": v_val,
            "branch": context.get("git_branch", ""),
            "all_status": context.get("git_status", ""),
            "ahead_behind": "", # Vacío por defecto
            "virtualenv": "", # Por defecto vacío
        }
        
        if module_name == "character":
            runtime_values["symbol"] = module_cfg.get("success_symbol", module_cfg.get("symbol", "❯"))
        
        if module_name == "os":
            os_val = context.get("os", "Arch")
            os_symbols = module_cfg.get("symbols", {})
            if isinstance(os_symbols, dict) and os_val in os_symbols:
                runtime_values["symbol"] = os_symbols[os_val]
            # Limpiar la variable literal 'os' para evitar que salga el nombre (ej: Arch)
            runtime_values["os"] = ""

        subs.update(runtime_values)

        # 5. Sustitución de variables (Primer pase)
        result = fmt
        for var, val in subs.items():
            result = result.replace(f"${var}", str(val)).replace(f"${{{var}}}", str(val))

        # 6. Lógica de Grupos Opcionales de Starship (...)
        # Un grupo (...) se oculta si su contenido resultante (tras expansión) 
        # no contiene caracteres alfanuméricos o símbolos importantes.
        def cleanup_groups(text):
            changed = True
            while changed:
                changed = False
                # Encontrar el grupo más interno que NO sea un bloque de estilo [text](style)
                # La expresión [^()]* asegura que no haya paréntesis anidados dentro
                m = re.search(r'(?<!\])\(([^()]*)\)', text)
                if m:
                    inner = m.group(1)
                    # content_check: lo que queda tras quitar variables $var, escapes de Starship y espacios
                    content_check = re.sub(r'\$[a-zA-Z_0-9]+|\$\{[a-zA-Z_0-9]+\}', '', inner)
                    # También quitamos los escapes de la comprobación para que \(\) se considere vacío
                    content_check = content_check.replace('\\(', '').replace('\\)', '').replace('\\[', '').replace('\\]', '').strip()
                    
                    if not content_check:
                        # Eliminar el grupo entero
                        text = text[:m.start()] + text[m.end():]
                    else:
                        # Marcar como procesado con caracteres que no choque con el resto de la lógica
                        text = text[:m.start()] + "\u0001" + inner + "\u0002" + text[m.end():]
                    changed = True
            
            return text.replace("\u0001", "(").replace("\u0002", ")")

        result = cleanup_groups(result)

        # 7. Último pase de limpieza de variables (por si quedaron de niveles superiores)
        for var, val in subs.items():
            result = result.replace(f"${var}", str(val)).replace(f"${{{var}}}", str(val))

        # Limpiar espacios dobles que puedan haber quedado dentro del módulo
        result = re.sub(r'\s{2,}', ' ', result)
        if module_name == "os": result = result.strip()
        
        return result

    def get_segments(self, text: str):
        segments = []
        i = 0
        while i < len(text):
            if text[i] == '[':
                start_idx = i
                depth = 1
                j = i + 1
                while j < len(text) and depth > 0:
                    if text[j] == '[': depth += 1
                    elif text[j] == ']': depth -= 1
                    j += 1
                if depth == 0 and j < len(text) and text[j] == '(':
                    content = text[start_idx+1:j-1]
                    s_start = j
                    k = j + 1
                    while k < len(text) and text[k] != ')':
                        k += 1
                    if k < len(text):
                        style = text[s_start+1:k]
                        segments.append(('block', content, style, start_idx, k+1))
                        i = k + 1
                        continue
            
            if text.startswith("$line_break", i):
                segments.append(('lb', '', '', i, i + 11))
                i += 11
                continue
            
            if text[i] == '$':
                var_match = re.match(r'^\$([a-zA-Z0-9_]+)', text[i:])
                if var_match:
                    var_name = var_match.group(1)
                    segments.append(('var', '', var_name, i, i + len(var_name) + 1))
                    i += len(var_name) + 1
                    continue
            i += 1
        return segments

    def process_text_segment(self, text: str, default_style: str, group: str, is_starship: bool, elements: List):
        segments = self.get_segments(text)
        if not segments:
            if text.strip() or text == " ":
                elements.append({
                    'type': 'starship' if is_starship else 'custom',
                    'style': default_style,
                    'final_content': self.clean_final_content(text)
                })
            return

        last_idx = 0
        for stype, content, sval, start, end in segments:
            pre = text[last_idx:start]
            if pre.strip() or pre == " ":
                elements.append({
                    'type': 'starship' if is_starship else 'custom',
                    'style': default_style,
                    'final_content': self.clean_final_content(pre)
                })
            
            if stype == 'block':
                inner_style = sval
                if inner_style in ("$style", "${style}"):
                    inner_style = default_style
                self.process_text_segment(content, inner_style, group, is_starship, elements)
            elif stype == 'lb':
                elements.append({'type': 'line_break'})
            elif stype == 'var':
                if sval in self.whitelist_modules:
                    module_cfg = self.doc.get(sval, {})
                    if not (isinstance(module_cfg, dict) and module_cfg.get("disabled") is True):
                        expanded = self.solve_module_format(sval, module_cfg, self.runtime_context)
                        self.process_text_segment(expanded, str(module_cfg.get("style", "")), sval, True, elements)
            
            last_idx = end
        
        post = text[last_idx:]
        if post.strip() or post == " ":
            elements.append({
                'type': 'starship' if is_starship else 'custom',
                'style': default_style,
                'final_content': self.clean_final_content(post)
            })

    def _resolve_color(self, color_key: str) -> str:
        if not self.valid or not color_key: return "inherit"
        palettes = self.doc.get("palettes", {})
        names = list(palettes.keys())
        p_name = self.doc.get("palette")
        
        if self.palette_index is not None and 0 <= self.palette_index < len(names):
            p_name = names[self.palette_index]
        
        palette = palettes.get(p_name, {}) if p_name else {}
        clean_key = str(color_key).replace("fg:", "").replace("bg:", "").strip().lower()
        
        if clean_key in palette:
            return str(palette[clean_key])
            
        standard_colors = {
            "black": "#000000", "red": "#cc241d", "green": "#98971a", "yellow": "#d79921",
            "blue": "#458588", "purple": "#b16286", "cyan": "#689d6a", "white": "#a89984",
            "orange": "#fe8019", "gray": "#928374", "grey": "#928374"
        }
        return standard_colors.get(clean_key, clean_key)

    def render(self) -> str:
        if not self.valid:
            return self._wrap('<span style="color: #666;">Cargando...</span>')

        format_str = str(self.doc.get("format", "")).replace("\\\n", "").replace("\n", "")
        elements = []
        self.process_text_segment(format_str, "", "root", False, elements)
        return self._to_html(elements)

    def _to_html(self, elements: List[Dict]) -> str:
        html_segments = []
        for el in elements:
            if el['type'] == 'line_break':
                html_segments.append('</div><div class="prompt-line">')
                continue
            
            content = el.get('final_content', '')
            # Si el contenido está vacío tras la limpieza, NO renderizamos nada
            if not content:
                continue

            style_str = str(el.get('style', ''))
            
            css = []
            if 'bold' in style_str.lower(): css.append("font-weight: bold")
            
            fg = re.search(r'fg:([a-zA-Z0-9_#]+)', style_str)
            bg = re.search(r'bg:([a-zA-Z0-9_#]+)', style_str)
            
            if bg: css.append(f"background-color: {self._resolve_color(bg.group(1))}")
            if fg: css.append(f"color: {self._resolve_color(fg.group(1))}")
            elif style_str and "bg:" not in style_str:
                c = style_str.replace("bold", "").strip()
                if c: css.append(f"color: {self._resolve_color(c)}")

            is_glyph = any(g in str(content) for g in '')
            if is_glyph:
                # Si es uno de los conectores triangulares específicos,
                # añadimos también la clase `glyph2` para poder estilizarlo
                if re.search(r'[]', content):
                    cls = "glyph glyph2"
                else:
                    cls = "glyph"
            else:
                cls = "text-node"
            txt = content.replace(" ", "&nbsp;")
            html_segments.append(f'<span class="{cls}" style="{"; ".join(css)}">{txt}</span>')

        return self._wrap("".join(html_segments))

    def _wrap(self, inner_html: str) -> str:
        return f"""
        <html>
        <head>
            <style>
                body {{ background: transparent; margin: 0; padding: 10px; font-family: 'CaskaydiaCove Nerd Font', monospace; overflow: hidden; }}
                .scaler {{ transform: scale({self.scale}); transform-origin: top left; display: inline-block; }}
                .terminal {{
                    display: inline-block;
                    background: #181818;
                    border: 1px solid #303030;
                    border-radius: 8px;
                    padding: 15px 20px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
                    white-space: nowrap;
                }}
                .prompt-line {{ display: flex; align-items: stretch; height: 32px; line-height: 32px; }}
                span {{ display: flex; align-items: center; justify-content: center; height: 100%; }}
                .text-node {{ padding: 0 4px; font-size: 14px; white-space: pre; }}
                /* Styles for glyphs that are NOT the special triangle connectors */
                .glyph:not(.glyph2) {{ display: inline-flex; align-items: center; justify-content: center; font-size: 27px; margin: 0px -0.5px 0 -0.5px; line-height: 1; transform: translateY(0.5px); }}
                /* Triangle connectors (editable independently) */
                .glyph2 {{ display: inline-flex; align-items: center; justify-content: center; font-size: 27px; margin: 0 -0.5px; line-height: 1; transform: translateY(0px); }}
            </style>
        </head>
        <body>
            <div class="scaler"><div class="terminal"><div class="prompt-line">{inner_html}</div></div></div>
        </body>
        </html>
        """

def generate_preview_html(data: Any, palette_index: int | None = None, scale: float = 1.0, width: int = 800) -> str:
    # Esta es la función que llama models.py
    renderer = StarshipRenderer(data, palette_index, scale, width)
    return renderer.render()