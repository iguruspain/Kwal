#!/bin/bash
# Kwal — User Installation Script
# Installs Kwal as a self-contained user application in ~/.local/share/kwal/.
# The cloned repository can be safely deleted after installation.
# System dependencies (PySide6, Qt6 WebEngine, Kirigami) must already be installed.
# See README.md for distribution-specific package names.

set -e

APP_NAME="kwal"
DESKTOP_FILE="org.kde.kwal.desktop"
SOURCE_DIR=$(cd "$(dirname "$0")" && pwd)
INSTALL_DIR="$HOME/.local/share/kwal"
VENV_DIR="$INSTALL_DIR/venv"
BIN_DIR="$HOME/.local/bin"
ICON_SRC="$SOURCE_DIR/src/resources/icon/kwal.svg"
MIN_PYTHON_VERSION="3.10"

# ANSI Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${BLUE}=== Kwal — Installation ===${NC}"
echo "    Install path: $INSTALL_DIR"
echo ""

# ──────────────────────────────────────────────
# 1. Prerequisite Checks
# ──────────────────────────────────────────────
echo -e "${GREEN}[1/5] Checking prerequisites...${NC}"

# Check Python version
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERROR] python3 not found. Install Python 3.10+ from your package manager.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo -e "${RED}[ERROR] Python >= $MIN_PYTHON_VERSION required (found $PYTHON_VERSION).${NC}"
    exit 1
fi
echo "    Python $PYTHON_VERSION — OK"

# Check python3-venv availability
if ! python3 -m venv --help &>/dev/null; then
    echo -e "${RED}[ERROR] python3-venv module not available.${NC}"
    echo -e "${YELLOW}    Install it with your package manager:${NC}"
    echo "      Arch:   sudo pacman -S python"
    echo "      Fedora: sudo dnf install python3-venv"
    echo "      Debian: sudo apt install python3-venv"
    exit 1
fi

# Check PySide6 (must come from system packages)
if ! python3 -c "import PySide6" &>/dev/null; then
    echo -e "${RED}[ERROR] PySide6 not found in system Python.${NC}"
    echo -e "${YELLOW}    Install it with your package manager:${NC}"
    echo "      Arch:   sudo pacman -S pyside6"
    echo "      Fedora: sudo dnf install python3-pyside6"
    echo "      Debian: sudo apt install python3-pyside6"
    exit 1
fi
echo "    PySide6 — OK"

# Check Qt6 WebEngine
if ! python3 -c "from PySide6.QtWebEngineQuick import QtWebEngineQuick" &>/dev/null; then
    echo -e "${RED}[ERROR] Qt6 WebEngine not found.${NC}"
    echo -e "${YELLOW}    Install it with your package manager:${NC}"
    echo "      Arch:   sudo pacman -S qt6-webengine"
    echo "      Fedora: sudo dnf install qt6-qtwebengine"
    echo "      Debian: sudo apt install qt6-webengine-dev"
    exit 1
fi
echo "    Qt6 WebEngine — OK"

# Check Kirigami QML module
KIRIGAMI_FOUND=false
for QML_DIR in /usr/lib/qt6/qml /usr/lib64/qt6/qml /usr/lib/x86_64-linux-gnu/qt6/qml; do
    if [ -d "$QML_DIR/org/kde/kirigami" ]; then
        KIRIGAMI_FOUND=true
        break
    fi
done
if [ "$KIRIGAMI_FOUND" = false ]; then
    echo -e "${YELLOW}[WARN] Kirigami QML module not found in standard paths.${NC}"
    echo -e "${YELLOW}    If the app fails to start, install Kirigami:${NC}"
    echo "      Arch:   sudo pacman -S kirigami"
    echo "      Fedora: sudo dnf install kf6-kirigami"
    echo "      Debian: sudo apt install kirigami2-dev"
else
    echo "    Kirigami — OK"
fi

# ──────────────────────────────────────────────
# 2. Create Self-Contained Installation
# ──────────────────────────────────────────────
echo -e "${GREEN}[2/5] Creating installation directory...${NC}"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}    Existing installation found. Reinstalling...${NC}"
    rm -rf "$INSTALL_DIR"
fi

mkdir -p "$INSTALL_DIR"

# Create venv with system-site-packages to inherit PySide6/Qt/Kirigami
python3 -m venv --system-site-packages "$VENV_DIR"
echo "    Venv created: $VENV_DIR"

# ──────────────────────────────────────────────
# 3. Install Python Package
# ──────────────────────────────────────────────
echo -e "${GREEN}[3/5] Installing Kwal into venv...${NC}"

source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet
pip install "$SOURCE_DIR" --quiet

# ──────────────────────────────────────────────
# 4. Desktop Integration
# ──────────────────────────────────────────────
echo -e "${GREEN}[4/5] Setting up desktop integration...${NC}"

USER_APPS_DIR="$HOME/.local/share/applications"
USER_ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

mkdir -p "$USER_APPS_DIR"
mkdir -p "$USER_ICONS_DIR"
mkdir -p "$BIN_DIR"

# Icon
if [ -f "$ICON_SRC" ]; then
    cp "$ICON_SRC" "$USER_ICONS_DIR/kwal.svg"
    echo "    Icon → $USER_ICONS_DIR/kwal.svg"
else
    echo -e "${YELLOW}    [WARN] Icon not found at $ICON_SRC${NC}"
fi

# Symlink executable to ~/.local/bin/ (should be in $PATH)
EXECUTABLE="$VENV_DIR/bin/kwal"
ln -sf "$EXECUTABLE" "$BIN_DIR/kwal"
echo "    Executable → $BIN_DIR/kwal"

# Desktop file with absolute path to the venv executable
cp "$SOURCE_DIR/$DESKTOP_FILE" "$USER_APPS_DIR/$DESKTOP_FILE"
sed -i "s|Exec=kwal|Exec=$EXECUTABLE|g" "$USER_APPS_DIR/$DESKTOP_FILE"
echo "    Desktop entry → $USER_APPS_DIR/$DESKTOP_FILE"

# ──────────────────────────────────────────────
# 5. Optional Dependencies Check
# ──────────────────────────────────────────────
echo -e "${GREEN}[5/5] Checking optional dependencies...${NC}"

if command -v matugen &>/dev/null; then
    echo "    matugen — OK (preferred wallpaper color extraction)"
else
    echo -e "${YELLOW}    [OPTIONAL] matugen not found.${NC}"
    echo "      Install it for KDE-native wallpaper color extraction:"
    echo "      Arch: sudo pacman -S matugen"
fi

if command -v magick &>/dev/null || command -v convert &>/dev/null; then
    echo "    ImageMagick — OK (advanced tinting & palette extraction)"
else
    echo -e "${YELLOW}    [OPTIONAL] ImageMagick not found.${NC}"
    echo "      Install it for advanced image tinting features:"
    echo "      Arch: sudo pacman -S imagemagick"
fi

for tool in fastfetch starship ulauncher; do
    if command -v "$tool" &>/dev/null; then
        echo "    $tool — OK (tinting target)"
    else
        echo -e "${YELLOW}    [OPTIONAL] $tool not found (tinting target).${NC}"
    fi
done

# Update KDE application database if kbuildsycoca6 is available
(which kbuildsycoca6 &>/dev/null) && kbuildsycoca6 --noincremental

# ──────────────────────────────────────────────
# Done
# ──────────────────────────────────────────────
echo ""
echo -e "${BLUE}=== Installation Complete ===${NC}"
echo ""
echo "Kwal is installed in: $INSTALL_DIR"
echo "You can safely delete the cloned repository now."
echo ""
echo "Launch Kwal from your application menu, or run:"
echo "    kwal"
echo ""
echo "To uninstall, run uninstall.sh or manually:"
echo "    rm -rf $INSTALL_DIR $BIN_DIR/kwal"
echo "    rm -f $USER_APPS_DIR/$DESKTOP_FILE"
echo "    rm -f $USER_ICONS_DIR/kwal.svg"
