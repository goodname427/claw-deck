# ClawDeck packaging script for Windows (PowerShell).
# Builds the frontend and creates a ZIP file ready for Decky Loader "Install from ZIP".
#
# Usage:
#   .\package.ps1
#
# Output: out\ClawDeck.zip

$ErrorActionPreference = "Stop"
$PLUGIN_NAME = "ClawDeck"
$OUT_DIR = "out"
$STAGING_DIR = Join-Path $OUT_DIR $PLUGIN_NAME

Write-Host "=== ClawDeck Packaging Script ===" -ForegroundColor Cyan

# 1. Clean previous output
Write-Host "[1/4] Cleaning previous build..." -ForegroundColor Yellow
if (Test-Path $OUT_DIR) { Remove-Item -Recurse -Force $OUT_DIR }

# 2. Build frontend
Write-Host "[2/4] Building frontend..." -ForegroundColor Yellow
pnpm install
pnpm build

# 3. Stage files into plugin directory structure
Write-Host "[3/4] Staging files..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path $STAGING_DIR | Out-Null

Copy-Item "plugin.json" -Destination $STAGING_DIR
Copy-Item "main.py" -Destination $STAGING_DIR
Copy-Item -Recurse "dist" -Destination (Join-Path $STAGING_DIR "dist")
Copy-Item -Recurse "py_modules" -Destination (Join-Path $STAGING_DIR "py_modules")
Copy-Item -Recurse "defaults" -Destination (Join-Path $STAGING_DIR "defaults")

if (Test-Path "LICENSE") {
    Copy-Item "LICENSE" -Destination $STAGING_DIR
}

# 4. Create ZIP
Write-Host "[4/4] Creating ZIP..." -ForegroundColor Yellow
$zipPath = Join-Path $OUT_DIR "$PLUGIN_NAME.zip"
Compress-Archive -Path $STAGING_DIR -DestinationPath $zipPath -Force

Write-Host ""
Write-Host "=== Done! ===" -ForegroundColor Green
Write-Host "Output: $zipPath"
Write-Host ""
Write-Host "To install on Steam Deck:"
Write-Host "  1. Copy $PLUGIN_NAME.zip to Steam Deck"
Write-Host "  2. Open Quick Access Menu > Decky Loader > Settings"
Write-Host "  3. Enable Developer Mode"
Write-Host "  4. Click 'Install Plugin From ZIP'"
Write-Host "  5. Select $PLUGIN_NAME.zip"
