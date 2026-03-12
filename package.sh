#!/bin/bash
# ClawDeck packaging script for Decky Loader developer mode installation.
# Builds the frontend and creates a ZIP file ready for "Install from ZIP".
#
# Usage:
#   chmod +x package.sh
#   ./package.sh
#
# Output: out/ClawDeck.zip

set -e

PLUGIN_NAME="ClawDeck"
OUT_DIR="out"
STAGING_DIR="${OUT_DIR}/${PLUGIN_NAME}"

echo "=== ClawDeck Packaging Script ==="

# 1. Clean previous output
echo "[1/4] Cleaning previous build..."
rm -rf "${OUT_DIR}"

# 2. Build frontend
echo "[2/4] Building frontend..."
pnpm install --frozen-lockfile 2>/dev/null || pnpm install
pnpm build

# 3. Stage files into plugin directory structure
echo "[3/4] Staging files..."
mkdir -p "${STAGING_DIR}"

# Required files
cp plugin.json "${STAGING_DIR}/"
cp main.py "${STAGING_DIR}/"
cp -r dist "${STAGING_DIR}/"
cp -r py_modules "${STAGING_DIR}/"
cp -r defaults "${STAGING_DIR}/"

# Optional: LICENSE if exists
[ -f LICENSE ] && cp LICENSE "${STAGING_DIR}/"

# 4. Create ZIP
echo "[4/4] Creating ZIP..."
cd "${OUT_DIR}"
zip -r "${PLUGIN_NAME}.zip" "${PLUGIN_NAME}/"
cd ..

echo ""
echo "=== Done! ==="
echo "Output: ${OUT_DIR}/${PLUGIN_NAME}.zip"
echo ""
echo "To install on Steam Deck:"
echo "  1. Copy ${PLUGIN_NAME}.zip to Steam Deck"
echo "  2. Open Quick Access Menu > Decky Loader > Settings"
echo "  3. Enable Developer Mode"
echo "  4. Click 'Install Plugin From ZIP'"
echo "  5. Select ${PLUGIN_NAME}.zip"
