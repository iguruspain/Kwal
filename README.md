# Aplicación Kwal con Python
# Kwal

Proyecto pequeño llamado Kwal. Contiene una aplicación Python con
componentes QML y una estructura mínima para comenzar a desarrollar.

Estado: trabajo en progreso.

Estructura
---------

- `src/` - Código fuente de la aplicación
  - `app.py` - Punto de entrada
  - `controllers/` - Controladores
  - `models/` - Modelos
  - `qml/` - Archivos QML
- `resources/` - Recursos y ejemplos

Requisitos
---------

- Python 3.8+

Instalación rápida
------------------

1. Crear y activar un entorno virtual (recomendado):

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias (si existiera `requirements.txt`):

```bash
pip install -r requirements.txt
```

Ejecutar la aplicación
----------------------

```bash
python src/app.py
```

Notas
-----

- El proyecto incluye QML en `src/qml/` y puede necesitar dependencias
  específicas del sistema para ejecutar interfaces QML.
- Añade un `requirements.txt` si quieres fijar dependencias Python.

Contribuir
----------

Por favor abre issues o pull requests con mejoras o correcciones.

Esta aplicación utiliza Kirigami como framework UI y Python para la lógica de negocio.

## Estructura del Proyecto

- `src/`: Código fuente principal
  - `app.py`: Punto de entrada de la aplicación
  - `qml/`: Archivos QML para la interfaz de usuario
    - `main.qml`: Diseño de la ventana principal
  - `controllers/`: Controladores para la lógica de la aplicación
  - `models/`: Modelos de datos
- `resources/`: Recursos como imágenes, iconos, plantillas, etc.
- `README.md`: Readme