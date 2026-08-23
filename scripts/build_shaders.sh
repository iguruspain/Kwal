#!/bin/bash
# Kwal — Shader Build Script
# Compiles every GLSL fragment shader in src/qml/components/shaders/ into a
# precompiled Qt 6 shader package (.qsb) using the qsb tool.
#
# Qt 6's ShaderEffect does not accept raw GLSL; it requires .qsb packages.
# Run this script after editing any .frag file:
#
#   ./scripts/build_shaders.sh
#
# Requirements:
#   - qsb from the qt6-shadertools package (Arch: sudo pacman -S qt6-shadertools)

set -e

# Resolve the project root from the script location so it works from any CWD.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SHADER_DIR="$PROJECT_ROOT/src/qml/components/shaders"

# ANSI Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

# Locate the qsb binary (Qt 6).
QSB_BIN="$(command -v qsb || true)"
if [ -z "$QSB_BIN" ] && [ -x /usr/lib/qt6/bin/qsb ]; then
    QSB_BIN="/usr/lib/qt6/bin/qsb"
fi

if [ -z "$QSB_BIN" ]; then
    echo -e "${RED}[ERROR] qsb not found.${NC}"
    echo -e "${YELLOW}    Arch: sudo pacman -S qt6-shadertools${NC}"
    exit 1
fi
echo "    qsb: $QSB_BIN"

if [ ! -d "$SHADER_DIR" ]; then
    echo -e "${RED}[ERROR] Shader directory not found: $SHADER_DIR${NC}"
    exit 1
fi

count=0
for frag in "$SHADER_DIR"/*.frag; do
    [ -e "$frag" ] || continue
    name="$(basename "$frag")"
    out="${frag%.frag}.qsb"
    echo -e "${GREEN}[BUILD]${NC} $name -> $(basename "$out")"
    "$QSB_BIN" --qt6 -o "$out" "$frag"
    count=$((count + 1))
done

if [ "$count" -eq 0 ]; then
    echo -e "${YELLOW}[WARN] No .frag files found in $SHADER_DIR${NC}"
    exit 0
fi

echo -e "${GREEN}Done: $count shader(s) compiled.${NC}"
