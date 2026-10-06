#!/bin/bash
# Kwal — Development Environment Setup
# Creates a venv with --system-site-packages to inherit PySide6/Qt/Kirigami
# from the system, then installs Python-only deps and the package in editable mode.

set -e

VENV_DIR=".venv"
MIN_PYTHON_VERSION="3.10"

# ANSI Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${BLUE}=== Kwal — Development Environment Setup ===${NC}"

# ──────────────────────────────────────────────
# 1. Check System Prerequisites
# ──────────────────────────────────────────────
echo -e "${GREEN}[1/3] Checking system prerequisites...${NC}"

# Python version
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERROR] python3 not found.${NC}"
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

# PySide6 from system
if ! python3 -c "import PySide6" &>/dev/null; then
    echo -e "${RED}[ERROR] PySide6 not found in system Python.${NC}"
    echo -e "${YELLOW}    Arch: sudo pacman -S pyside6${NC}"
    exit 1
fi
echo "    PySide6 (system) — OK"

# Qt6 WebEngine
if ! python3 -c "from PySide6.QtWebEngineQuick import QtWebEngineQuick" &>/dev/null; then
    echo -e "${RED}[ERROR] Qt6 WebEngine not found.${NC}"
    echo -e "${YELLOW}    Arch: sudo pacman -S qt6-webengine${NC}"
    exit 1
fi
echo "    Qt6 WebEngine — OK"

# Kirigami (warning only — may work from non-standard paths)
KIRIGAMI_FOUND=false
for QML_DIR in /usr/lib/qt6/qml /usr/lib64/qt6/qml /usr/lib/x86_64-linux-gnu/qt6/qml; do
    if [ -d "$QML_DIR/org/kde/kirigami" ]; then
        KIRIGAMI_FOUND=true
        break
    fi
done
if [ "$KIRIGAMI_FOUND" = false ]; then
    echo -e "${YELLOW}    [WARN] Kirigami QML module not found.${NC}"
    echo -e "${YELLOW}    Arch: sudo pacman -S kirigami${NC}"
else
    echo "    Kirigami — OK"
fi

# Optional: matugen (preferred wallpaper color extraction)
if command -v matugen &>/dev/null; then
    echo "    matugen — OK (preferred wallpaper color extraction)"
else
    echo -e "${YELLOW}    [WARN] matugen not found (optional, preferred color extraction).${NC}"
    echo -e "${YELLOW}    Arch: sudo pacman -S matugen${NC}"
fi

# ──────────────────────────────────────────────
# 2. Create Virtual Environment
# ──────────────────────────────────────────────
echo -e "${GREEN}[2/3] Setting up virtual environment (--system-site-packages)...${NC}"

if [ -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}    Existing venv found. Removing and recreating...${NC}"
    rm -rf "$VENV_DIR"
fi

python3 -m venv --system-site-packages "$VENV_DIR"
echo "    Created: $VENV_DIR"

# ──────────────────────────────────────────────
# 3. Install in Editable Mode
# ──────────────────────────────────────────────
echo -e "${GREEN}[3/3] Installing Kwal in editable mode...${NC}"

source "$VENV_DIR/bin/activate"
pip install --upgrade pip --quiet
pip install -e . --quiet

echo ""
echo -e "${BLUE}=== Development Environment Ready ===${NC}"
echo ""
echo "Activate the environment:"
echo "    source $VENV_DIR/bin/activate"
echo ""
echo "Run Kwal:"
echo "    kwal            # via entry point"
echo "    python -m kwal  # via module"