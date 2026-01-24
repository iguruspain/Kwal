# 🎨 Kwal — KDE Wallpaper & Style Manager

**Kwal** is a modern utility for KDE Plasma designed to unify your desktop aesthetics. It manages your wallpapers and automatically tints your favorite tools (Fastfetch, Starship, Ulauncher) using palettes extracted from your background or custom colors.

Built with **Python**, **PySide6**, and **Kirigami**, Kwal offers a native and fluid experience integrated with the KDE ecosystem.

---

## ✨ Main Features

- **🖼️ Wallpaper Management**: Change your KDE Plasma wallpaper directly from the app.
- **🌈 Palette Generation**: Automatic color extraction using modern algorithms (Material You, Color Thief).
- **🚀 App Tinting**:
  - **Fastfetch**: Customize your fetch logo and colors.
  - **Starship**: Apply color themes to your terminal prompt.
  - **Ulauncher**: Generate matching themes for your application launcher.
- **📂 Template System**: Customize how colors are applied to each tool.
- **✨ KDE Integration**: Native Kirigami style with support for blur effects and dark mode.

---

## 🚀 Installation

Kwal is installed as a native user application without requiring root permissions.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/iguruspain/kwal.git
   cd kwal
   ```

2. **Run the installer**:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

The installer will create a virtual environment, install dependencies, and add **Kwal** to your KDE application menu.

---

## 🛠️ Requirements

- **Operating System**: Linux (Optimized for KDE Plasma).
- **Python**: 3.10 or higher.
- **System Dependencies**: `python3-pip`, `python3-venv`, `qdbus`.
- **Optional**: Fastfetch, Starship, or Ulauncher installed to use tinting features.

---

## 📖 Usage

Once installed, you can find **Kwal** in your application launcher (KRunner, Kickoff, etc.).

When launching the application for the first time, it will automatically install the necessary templates to your configuration directory: `~/.config/kwal/templates`. You can edit these files to customize the tinting results.

### Terminal Commands
If you prefer using the terminal (within the virtual environment):
- `kwal`: Launches the graphical interface.
- `kwal --install-templates`: Forces the re-installation of original templates.

---

## 🗑️ Uninstallation

To completely remove the application and its shortcuts from your system:
```bash
chmod +x uninstall.sh
./uninstall.sh
```

---

## 👨‍💻 Development

If you wish to contribute or test changes:
1. Create a virtual environment: `python -m venv .venv`
2. Install dependencies: `pip install -r requirements.txt`
3. Install in editable mode: `pip install -e .`
4. Run with: `python src/app.py`

---

*Developed with ❤️ for the KDE community.*