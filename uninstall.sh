#!/bin/bash
# Kwal — Uninstall Script
# Removes Kwal installation, and optionally config and cache data.

set -e

INSTALL_DIR="$HOME/.local/share/kwal"
DESKTOP_FILE="org.kde.kwal.desktop"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/kwal"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/kwal"

# ANSI Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m'

# ── Helper ────────────────────────────────────────────────────────────────────
ask() {
    # ask <question>  →  returns 0 (yes) or 1 (no)
    local answer
    while true; do
        echo -en "$1 [y/N] "
        read -r answer
        case "${answer,,}" in
            y|yes) return 0 ;;
            n|no|"") return 1 ;;
            *) echo "  Please answer y or n." ;;
        esac
    done
}

echo ""
echo -e "${BLUE}${BOLD}=== Kwal — Uninstallation ===${NC}"
echo ""

# ── 1. Remove Application ─────────────────────────────────────────────────────
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${RED}[-] Removing installation ($INSTALL_DIR)...${NC}"
    rm -rf "$INSTALL_DIR"
else
    echo -e "${YELLOW}    Installation not found at $INSTALL_DIR${NC}"
fi

# ── 2. Remove Executable Symlink ──────────────────────────────────────────────
if [ -L "$HOME/.local/bin/kwal" ] || [ -f "$HOME/.local/bin/kwal" ]; then
    echo -e "${RED}[-] Removing executable symlink...${NC}"
    rm -f "$HOME/.local/bin/kwal"
fi

# ── 3. Remove Desktop Integration ────────────────────────────────────────────
echo -e "${RED}[-] Removing desktop integration...${NC}"
rm -f "$HOME/.local/share/applications/$DESKTOP_FILE"
rm -f "$HOME/.local/share/icons/hicolor/scalable/apps/kwal.svg"

# ── 4. Optional: Remove Configuration ────────────────────────────────────────
echo ""
if [ -d "$CONFIG_DIR" ]; then
    echo -e "${YELLOW}${BOLD}Configuration directory found:${NC} $CONFIG_DIR"
    echo    "  Contains: config.toml (folders, custom commands, settings)"
    echo    "  and any installed wallpaper templates."
    echo ""
    if ask "  Do you want to ${BOLD}delete your configuration${NC}?"; then
        echo -e "${RED}[-] Removing configuration ($CONFIG_DIR)...${NC}"
        rm -rf "$CONFIG_DIR"
        echo -e "${GREEN}    Done.${NC}"
    else
        echo -e "${YELLOW}    Configuration kept at $CONFIG_DIR${NC}"
    fi
else
    echo -e "${YELLOW}    No configuration directory found at $CONFIG_DIR${NC}"
fi

# ── 5. Optional: Remove Cache ─────────────────────────────────────────────────
echo ""
if [ -d "$CACHE_DIR" ]; then
    CACHE_SIZE=$(du -sh "$CACHE_DIR" 2>/dev/null | cut -f1)
    echo -e "${YELLOW}${BOLD}Cache directory found:${NC} $CACHE_DIR (${CACHE_SIZE})"
    echo    "  Contains: wallpaper thumbnails and color extraction cache."
    echo ""
    if ask "  Do you want to ${BOLD}delete the cache${NC}?"; then
        echo -e "${RED}[-] Removing cache ($CACHE_DIR)...${NC}"
        rm -rf "$CACHE_DIR"
        echo -e "${GREEN}    Done.${NC}"
    else
        echo -e "${YELLOW}    Cache kept at $CACHE_DIR${NC}"
    fi
else
    echo -e "${YELLOW}    No cache directory found at $CACHE_DIR${NC}"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}${BOLD}=== Uninstallation Complete ===${NC}"
[ -d "$CONFIG_DIR" ] && echo -e "  Configuration preserved at ${YELLOW}$CONFIG_DIR${NC}"
[ -d "$CACHE_DIR"  ] && echo -e "  Cache preserved at         ${YELLOW}$CACHE_DIR${NC}"
echo ""
