'''
Paleta de colores autogenerada en JSON usando el conjunto de colores de Kirigami y los colores del tema actual.
--------------------------------

Obtiene la ruta de archivo desde el la config de starship
Extraeremos los grupos y colores del archivo, asi sabremos el orden de aparicion y los nombres de los colores utilizados por el grupo.

Categorizaremos los grupos por bloques:
Bloque 1:
os, username
Bloque 2:
shell, directory
Bloque 3:
git_branch, git_status
Bloque 4:
time
Bloque 5:
line_break y lo que venga despues.
Bloque 6:
resto de grupos no categorizados.

Recopila todos los colores y conjuntos de colores disponibles del Theme de Kirigami.

los colores de cada bloque tendran el mismo color de fondo y color de texto.
el mapeo (interno) de bloques a colores y su correspondecia con su color kirigami sera el siguiente:
Bloque 1:
fondo: color_1_background --> por determinar
texto: color_1_foreground --> por determinar
Bloque 2:
fondo: color_2_background --> Theme.View hoverColor
texto: color_2_foreground --> Theme.View focusColor
Bloque 3:
fondo: color_3_background --> Theme.Window alternateBackgroundColor
texto: color_3_foreground --> Theme.Window disabledTextColor
Bloque 4:
fondo: color_4_background --> Theme.View hoverColor
texto: color_4_foreground --> Theme.View focusColor
Bloque 5:
fondo: color_5_background --> por determinar
texto: color_5_foreground --> por determinar
Bloque 6:
fondo: color_6_background --> Theme.View focusColor
texto: color_6_foreground --> Theme.Window backgroundColor

Resolvemos los nombres de los colores internos con los nombres de colores de starhip.
Genera el JSON con los colores mapeados y devuelve los valores para cargar en la paleta actual de Starship.
'''
'''
Paleta de colores autogenerada en JSON usando el conjunto de colores de Kirigami y los colores del tema actual.
--------------------------------

Obtiene la ruta de archivo desde el la config de starship
Extraeremos los grupos y colores del archivo, asi sabremos el orden de aparicion y los nombres de los colores utilizados por el grupo.

Categorizaremos los grupos por bloques:
Bloque 1:
os, username
Bloque 2:
shell, directory
Bloque 3:
git_branch, git_status
Bloque 4:
time
Bloque 5:
line_break y lo que venga despues.
Bloque 6:
resto de grupos no categorizados.

Recopila todos los colores y conjuntos de colores disponibles del Theme de Kirigami.

los colores de cada bloque tendran el mismo color de fondo y color de texto.
el mapeo (interno) de bloques a colores y su correspondecia con su color kirigami sera el siguiente:
Bloque 1:
fondo: color_1_background --> por determinar
texto: color_1_foreground --> por determinar
Bloque 2:
fondo: color_2_background --> Theme.View hoverColor
texto: color_2_foreground --> Theme.View focusColor
Bloque 3:
fondo: color_3_background --> Theme.Window alternateBackgroundColor
texto: color_3_foreground --> Theme.Window disabledTextColor
Bloque 4:
fondo: color_4_background --> Theme.View hoverColor
texto: color_4_foreground --> Theme.View focusColor
Bloque 5:
fondo: color_5_background --> por determinar
texto: color_5_foreground --> por determinar
Bloque 6:
fondo: color_6_background --> Theme.View focusColor
texto: color_6_foreground --> Theme.Window backgroundColor

Resolvemos los nombres de los colores internos con los nombres de colores de starhip.
Genera el JSON con los colores mapeados y devuelve los valores para cargar en la paleta actual de Starship.
'''
import json
import os
import tomlkit
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor

class KirigamiTheme:
    def __init__(self):
        # QApplication es necesario para inicializar el motor de estilos de Qt
        self.app = QApplication.instance() or QApplication([])
        self.palette = self.app.palette()

    def get_color(self, kirigami_name: str) -> str:
        """
        Mapea conceptos de Kirigami a QPalette de Qt.
        """
        # Mapeo de roles de Kirigami a QPalette de PySide6
        map_roles = {
            'Theme.Highlight': QPalette.ColorRole.Highlight,
            'Theme.HighlightedText': QPalette.ColorRole.HighlightedText,
            'Theme.Window.backgroundColor': QPalette.ColorRole.Window,
            'Theme.Window.alternateBackgroundColor': QPalette.ColorRole.AlternateBase,
            'Theme.Window.disabledTextColor': QPalette.ColorRole.PlaceholderText, # Lo más cercano a disabled
            'Theme.View.hoverColor': QPalette.ColorRole.Link, # Aproximación habitual en temas KDE
            'Theme.View.focusColor': QPalette.ColorRole.Highlight,
            'Theme.Button.hoverColor': QPalette.ColorRole.Button,
            'Theme.Button.focusColor': QPalette.ColorRole.Highlight,
        }

        role = map_roles.get(kirigami_name, QPalette.ColorRole.WindowText)
        color = self.palette.color(role)
        return color.name() # Devuelve el formato #RRGGBB

def generate_starship_palette(starship_config_path: str):
    theme = KirigamiTheme()

    # Definición de bloques según tu lógica
    blocks_def = {
        1: ['os', 'username'],
        2: ['shell', 'directory'],
        3: ['git_branch', 'git_status'],
        4: ['time'],
        5: ['line_break'],
    }

    # Mapeo de Bloques a los colores obtenidos vía PySide6
    block_colors = {
        1: (theme.get_color('Theme.Highlight'), theme.get_color('Theme.HighlightedText')),
        2: (theme.get_color('Theme.View.hoverColor'), theme.get_color('Theme.View.focusColor')),
        3: (theme.get_color('Theme.Window.alternateBackgroundColor'), theme.get_color('Theme.Window.disabledTextColor')),
        4: (theme.get_color('Theme.View.hoverColor'), theme.get_color('Theme.View.focusColor')),
        5: (theme.get_color('Theme.Button.hoverColor'), theme.get_color('Theme.Button.focusColor')),
        6: (theme.get_color('Theme.View.focusColor'), theme.get_color('Theme.Window.backgroundColor')),
    }

    if not os.path.exists(starship_config_path):
        raise FileNotFoundError(f"No se encontró: {starship_config_path}")

    with open(starship_config_path, 'r') as f:
        config_data = tomlkit.parse(f.read())

    starship_palette = {}

    # Iterar sobre los módulos configurados en tu Starship
    for module_name, settings in config_data.items():
        if not isinstance(settings, dict):
            continue

        # Identificar bloque
        block_id = 6
        for b_id, modules in blocks_def.items():
            if module_name in modules:
                block_id = b_id
                break
        
        bg, fg = block_colors[block_id]
        
        # Guardar con el sufijo para que lo uses en el .toml
        starship_palette[f"{module_name}_bg"] = bg
        starship_palette[f"{module_name}_fg"] = fg

    return starship_palette

if __name__ == "__main__":
    path = os.path.expanduser("~/.config/starship.toml")
    try:
        palette = generate_starship_palette(path)
        print(json.dumps(palette, indent=4))
    except Exception as e:
        print(f"Error: {e}")
