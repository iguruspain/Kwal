#!/bin/bash

# Exit on error
set -e

APP_NAME="kwal"
DESKTOP_FILE="org.kde.kwal.desktop"
INSTALL_DIR=$(pwd)
VENV_DIR="$INSTALL_DIR/.venv"

# ANSI Colors
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Uninstalling Kwal ===${NC}"

# 1. Remove Desktop Integration
echo -e "${RED}[-] Removing desktop integration...${NC}"
rm -f "$HOME/.local/share/applications/$DESKTOP_FILE"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/kwal.svg"

# 2. Remove Virtual Environment
if [ -d "$VENV_DIR" ]; then
    echo -e "${RED}[-] Removing virtual environment...${NC}"
    rm -rf "$VENV_DIR"
fi

# 3. Remove Build Artifacts
echo -e "${RED}[-] Cleaning build artifacts...${NC}"
rm -rf "$INSTALL_DIR/build" "$INSTALL_DIR/dist" "$INSTALL_DIR/kwal.egg-info"
find "$INSTALL_DIR" -type d -name "__pycache__" -exec rm -rf {} +

echo -e "${BLUE}=== Uninstallation Complete ===${NC}"
echo "Kwal has been removed from your system (user configurations in ~/.config/kwal were kept)."
