import re
import tomlkit
from typing import List, Dict, Any

def clean_final_content(text: str) -> str:
    """Limpia el contenido de artefactos de formato de Starship."""
    if not text: return ""
    text = str(text)
    
    # 1. Eliminar bloques de estilo restantes [content](style) -> content
    text = re.sub(r'\[([^\]]*)\]\([^)]+\)', r'\1', text)
    
    # 2. Eliminar variables no resueltas
    text = re.sub(r'\$[a-zA-Z_0-9]+', '', text)
    text = re.sub(r'\$\{[a-zA-Z_0-9]+\}', '', text)
    
    # 3. Limpiar grupos opcionales vacíos o que solo contienen basura de expansión
    for _ in range(3):
        text = re.sub(r'\(\s*\\?[\(\)]?\s*\\?[\(\)]?\s*\)', '', text)
        text = text.replace('()', '').replace('( )', '')

    # 4. Eliminar escapes de Starship
    text = text.replace('\\(', '(').replace('\\)', ')').replace('\\[', '[').replace('\\]', ']')
    text = text.replace('\\ ', ' ')
    
    # 5. Si el texto resultante es solo ruido de puntuación (ej: "()"), limpiarlo
    if text.strip() in ("()", "[]", "( )", "[ ]"):
        return ""

    return text

def solve_module_format(module_name: str, module_cfg: Dict, context: Dict) -> str:
    if not isinstance(module_cfg, dict): return ""
    
    # 1. Obtener el formato base o fallback inteligente
    default_fmt = "$symbol$version"
    if module_name == "os":
        default_fmt = "[$symbol]($style)"
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
    if module_name == "os": v_val = ""

    runtime_values = {
        "path": context.get("directory", ""),
        "user": context.get("username", ""),
        "username": context.get("username", ""),
        "time": context.get("time", ""),
        "version": v_val,
        "branch": context.get("git_branch", ""),
        "all_status": context.get("git_status", ""),
        "ahead_behind": " ", 
        "virtualenv": "",
    }
    
    if module_name == "character":
        runtime_values["symbol"] = module_cfg.get("success_symbol", module_cfg.get("symbol", "❯"))
    
    if module_name == "os":
        os_val = context.get("os", "Arch")
        os_symbols = module_cfg.get("symbols", {})
        if isinstance(os_symbols, dict) and os_val in os_symbols:
            runtime_values["symbol"] = os_symbols[os_val]

    subs.update(runtime_values)

    # 5. Manejo de Grupos Opcionales de Starship: ( ... $var ... )
    def handle_groups(f, s):
        while True:
            m = re.search(r'\(([^()]*)\)', f)
            if not m: break
            inner = m.group(1)
            vars_in = re.findall(r'\$([a-zA-Z0-9_]+)', inner)
            if vars_in:
                if any(s.get(v) for v in vars_in):
                    f = f[:m.start()] + "\u0001" + inner + "\u0002" + f[m.end():]
                else:
                    f = f[:m.start()] + f[m.end():]
            else:
                f = f[:m.start()] + "\u0001" + inner + "\u0002" + f[m.end():]
        return f.replace("\u0001", "(").replace("\u0002", ")")

    result = handle_groups(fmt, subs)

    # 6. Sustitución iterativa de variables
    for _ in range(3):
        changed = False
        for var, val in subs.items():
            p1, p2 = f"${var}", f"${{{var}}}"
            if p1 in result or p2 in result:
                result = result.replace(p1, str(val)).replace(p2, str(val))
                changed = True
        if not changed: break

    return result

def parse_and_render(toml_content: str, context: Dict[str, Any], whitelist: set) -> List[Dict[str, Any]]:
    doc = tomlkit.parse(toml_content)
    format_str = str(doc.get("format", "")).replace("\\\n", "").replace("\n", "")

    results = []

    def get_segments(text: str):
        """Encuentra bloques [content](style), $variables y $line_break."""
        segments = []
        i = 0
        while i < len(text):
            # 1. Detectar Bloque [content](style)
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
            
            # 2. Detectar $line_break
            if text.startswith("$line_break", i):
                segments.append(('lb', '', '', i, i + 11))
                i += 11
                continue
            
            # 3. Detectar $variable o ${variable}
            if text[i] == '$':
                var_match = re.match(r'^\$([a-zA-Z0-9_]+)', text[i:])
                if var_match:
                    var_name = var_match.group(1)
                    segments.append(('var', '', var_name, i, i + len(var_name) + 1))
                    i += len(var_name) + 1
                    continue
                var_match_brushed = re.match(r'^\$\{([a-zA-Z0-9_]+)\}', text[i:])
                if var_match_brushed:
                    var_name = var_match_brushed.group(1)
                    segments.append(('var', '', var_name, i, i + len(var_name) + 3))
                    i += len(var_name) + 3
                    continue
            
            i += 1
        return segments

    def process_text_segment(text: str, default_style: str, group: str, is_starship: bool = True):
        segments = get_segments(text)
        if not segments:
            if text.strip() or text == " ":
                results.append({
                    'type': 'starship' if is_starship else 'custom',
                    'group': group,
                    'style': default_style,
                    'final_content': clean_final_content(text)
                })
            return

        last_idx = 0
        for stype, content, sval, start, end in segments:
            # Texto antes del segmento
            pre = text[last_idx:start]
            if pre.strip() or pre == " ":
                results.append({
                    'type': 'starship' if is_starship else 'custom',
                    'group': group,
                    'style': default_style,
                    'final_content': clean_final_content(pre)
                })
            
            if stype == 'block':
                inner_style = sval
                if inner_style in ("$style", "${style}"):
                    inner_style = default_style
                # Llamada recursiva para el contenido del bloque
                process_text_segment(content, inner_style, group, is_starship)
            elif stype == 'lb':
                results.append({'type': 'line_break', 'group': 'line_break', 'final_content': '\n'})
            elif stype == 'var':
                # En este punto las variables ya deberían estar expandidas si vienen de solve_module_format,
                # pero si vienen del format raíz, las tratamos.
                if sval in whitelist:
                    module_cfg = doc.get(sval, {})
                    if not (isinstance(module_cfg, dict) and module_cfg.get("disabled") is True):
                        expanded = solve_module_format(sval, module_cfg, context)
                        process_text_segment(expanded, str(module_cfg.get("style", "")), sval, True)
            
            last_idx = end
        
        # Texto restante
        post = text[last_idx:]
        if post.strip() or post == " ":
            results.append({
                'type': 'starship' if is_starship else 'custom',
                'group': group,
                'style': default_style,
                'final_content': clean_final_content(post)
            })

    # Iniciamos el proceso con el string de formato raíz
    process_text_segment(format_str, "", "root", False)
        
    return results

