#!/usr/bin/env bash
# Freezes the Python backend with PyInstaller and places it where Tauri's
# externalBin expects it (target-triple suffixed, per Tauri sidecar naming).
set -euo pipefail
cd "$(dirname "$0")/.."

# use the project venv when present (dev machines); CI installs globally
if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

pyinstaller ohara-backend.spec --noconfirm

TRIPLE=$(rustc -Vv | awk '/^host:/ {print $2}')
mkdir -p frontend/src-tauri/binaries
cp dist/ohara-backend "frontend/src-tauri/binaries/ohara-backend-${TRIPLE}"
echo "sidecar ready: frontend/src-tauri/binaries/ohara-backend-${TRIPLE}"
