
# Kwal — Python Application

Kwal is a small Python application that includes QML components and a
minimal structure to start development.

Status: work in progress.

Requirements
------------

- Python 3.10+

Quick installation
------------------

1. Create and activate a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies (if a `requirements.txt` is provided):

```bash
pip install -r requirements.txt
```

Running the application
-----------------------

```bash
python src/app.py
```

Notes
-----

- The project includes QML files under `src/qml/` and may require system
  packages to run QML-based UIs (Qt, PySide6, Kirigami runtime, etc.).
- Add a `requirements.txt` if you want to pin Python dependencies.

Contributing
------------

Please open issues or pull requests with improvements or fixes.

This application uses Kirigami for the UI and Python for business logic.

Project layout
--------------

- `src/`: Main source code
  - `app.py`: Application entry point
  - `qml/`: QML files for the user interface
    - `main.qml`: Main window layout
  - `controllers/`: Controllers bridging Python and QML
  - `models/`: Data models and business logic
- `resources/`: Assets such as images, icons, and templates
- `README.md`: This file