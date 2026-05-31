#!/usr/bin/env bash
# Build Verbic Mac Lite into a .app bundle.
# Run this on macOS only.
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip wheel
pip install -r requirements.txt
pip install pyinstaller

rm -rf build dist

pyinstaller \
  --windowed \
  --name Verbic \
  --osx-bundle-identifier com.fhintegrant.verbic \
  --noconfirm \
  --clean \
  main.py

echo
echo "✓ Built dist/Verbic.app"
echo "  Drag it to /Applications, then launch it once to grant Accessibility permission."
