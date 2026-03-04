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

## �️ Requirements

### System Dependencies (installed via package manager)

These **must** be installed from your distribution's package manager — they cannot be installed via pip.

| Dependency | Arch Linux | Fedora | Debian/Ubuntu |
|---|---|---|---|
| Python ≥ 3.10 | `python` | `python3` | `python3` |
| PySide6 | `pyside6` | `python3-pyside6` | `python3-pyside6` |
| Qt6 WebEngine | `qt6-webengine` | `qt6-qtwebengine` | `qt6-webengine-dev` |
| Kirigami | `kirigami` | `kf6-kirigami` | `kirigami2-dev` |

**Arch Linux (one-liner):**
```bash
sudo pacman -S python pyside6 qt6-webengine kirigami
```

### Python Dependencies (installed automatically via pip)

These are pure Python libraries installed automatically during setup:

`json5` · `materialyoucolor` · `modern_colorthief` · `Pillow` · `pywal16` · `tomlkit`

### Optional Dependencies

| Tool | Purpose | Arch Linux |
|---|---|---|
| ImageMagick | Advanced image tinting & palette extraction | `imagemagick` |

### Target Applications (user-installed)

Kwal configures the following tools — install them if you want to use tinting:

- [Fastfetch](https://github.com/fastfetch-cli/fastfetch) — Terminal system info
- [Starship](https://starship.rs/) — Terminal prompt
- [Ulauncher](https://ulauncher.io/) — Application launcher

---

## 🚀 Installation

### Option 1: Arch Linux (PKGBUILD) — Recommended

```bash
git clone https://github.com/iguruspain/kwal.git
cd kwal
makepkg -si
```

All dependencies are handled by `pacman`. No virtual environment needed.

### Option 2: Generic Linux (install.sh)

```bash
git clone https://github.com/iguruspain/kwal.git
cd kwal
chmod +x install.sh
./install.sh
```

The installer will:
1. Verify all system prerequisites are present.
2. Create a self-contained installation in `~/.local/share/kwal/` (venv with `--system-site-packages`).
3. Install Python-only dependencies via pip.
4. Symlink the executable to `~/.local/bin/kwal`.
5. Add Kwal to your application menu (desktop entry + icon).

> **Important:** System dependencies must be installed **before** running `install.sh`. The script will check and tell you exactly what's missing.
>
> After installation, **you can safely delete the cloned repository**.

---

## 📖 Usage

Once installed, find **Kwal** in your application launcher (KRunner, Kickoff, etc.).

On first launch, Kwal automatically installs templates to `~/.config/kwal/templates/`. Edit these files to customize tinting results.

### Terminal Commands
```bash
kwal                      # Launch the graphical interface
kwal --install-templates  # Force re-installation of original templates
```

---

## 🗑️ Uninstallation

### install.sh users:
```bash
chmod +x uninstall.sh
./uninstall.sh
```
Or manually: `rm -rf ~/.local/share/kwal ~/.local/bin/kwal ~/.local/share/applications/org.kde.kwal.desktop ~/.local/share/icons/hicolor/scalable/apps/kwal.svg`

### PKGBUILD users:
```bash
sudo pacman -R kwal-git
```

User configuration in `~/.config/kwal` is preserved in both cases.

---

## 👨‍💻 Development

1. **Install system dependencies** (see Requirements above).
2. **Set up the dev environment:**
   ```bash
   chmod +x setup_dev_env.sh
   ./setup_dev_env.sh
   ```
3. **Activate and run:**
   ```bash
   source .venv/bin/activate
   kwal            # via entry point
   python -m kwal  # via module
   ```

The dev environment uses `--system-site-packages` to inherit PySide6/Qt/Kirigami from the system, and installs the package in editable mode (`pip install -e .`).

---

*Developed with ❤️ for the KDE community.*