#!/bin/bash

# Exit on error
set -e

APP_NAME="kwal"
DESKTOP_FILE="org.kde.kwal.desktop"
INSTALL_DIR=$(pwd)
VENV_DIR="$INSTALL_DIR/.venv"
ICON_SRC="$INSTALL_DIR/src/resources/icon/kwal.svg"

# ANSI Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Installing Kwal ===${NC}"

# 1. Setup Virtual Environment
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${GREEN}[+] Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
else
    echo -e "${GREEN}[+] Virtual environment found.${NC}"
fi

# 2. Install Dependencies
echo -e "${GREEN}[+] Installing dependencies and application...${NC}"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install .

# 3. Setup Desktop Integration
echo -e "${GREEN}[+] Setting up desktop integration...${NC}"
USER_APPS_DIR="$HOME/.local/share/applications"
USER_ICONS_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

mkdir -p "$USER_APPS_DIR"
mkdir -p "$USER_ICONS_DIR"

# Copy Icon
if [ -f "$ICON_SRC" ]; then
    cp "$ICON_SRC" "$USER_ICONS_DIR/kwal.svg"
    echo "    Icon installed to $USER_ICONS_DIR/kwal.svg"
else
    echo "    Warning: Icon not found at $ICON_SRC"
fi

# Generate & Install Desktop File (fixing Exec path)
# We use the absolute path to the venv python executable to run the module directly
# or the binary wrapper. The binary wrapper is arguably cleaner.
EXECUTABLE="$VENV_DIR/bin/kwal"

echo "    Generating desktop file..."
cp "$DESKTOP_FILE" "$USER_APPS_DIR/$DESKTOP_FILE"

# Use sed to replace Exec=kwal with Exec=/full/path/to/kwal
# We use | as delimiter to avoid issues with / in paths
sed -i "s|Exec=kwal|Exec=$EXECUTABLE|g" "$USER_APPS_DIR/$DESKTOP_FILE"

# Update generic Icon name to look for system icon or local one if themes support it
# But we installed it as 'kwal.svg', so Icon=kwal is correct for hicolor theme.

echo -e "${BLUE}=== Installation Complete ===${NC}"
echo "You can now launch Kwal from your application menu."
echo "Or run it directly via: $EXECUTABLE"
