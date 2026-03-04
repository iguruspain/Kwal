#!/bin/bash
# Kwal — Uninstall Script
# Removes Kwal installation from ~/.local/share/kwal/ and desktop integration.
# User configuration in ~/.config/kwal is preserved.

set -e

INSTALL_DIR="$HOME/.local/share/kwal"
DESKTOP_FILE="org.kde.kwal.desktop"

# ANSI Colors
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${BLUE}=== Kwal — Uninstallation ===${NC}"

# 1. Remove Application
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${RED}[-] Removing installation ($INSTALL_DIR)...${NC}"
    rm -rf "$INSTALL_DIR"
else
    echo -e "${YELLOW}    Installation not found at $INSTALL_DIR${NC}"
fi

# 2. Remove Executable Symlink
if [ -L "$HOME/.local/bin/kwal" ] || [ -f "$HOME/.local/bin/kwal" ]; then
    echo -e "${RED}[-] Removing executable symlink...${NC}"
    rm -f "$HOME/.local/bin/kwal"
fi

# 3. Remove Desktop Integration
echo -e "${RED}[-] Removing desktop integration...${NC}"
rm -f "$HOME/.local/share/applications/$DESKTOP_FILE"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/kwal.svg"

echo ""
echo -e "${BLUE}=== Uninstallation Complete ===${NC}"
echo "Kwal has been removed. User configuration in ~/.config/kwal was preserved."
