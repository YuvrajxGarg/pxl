#!/bin/bash
# Builds "dist/PXL.app". Run on a Mac.
#   ./build_mac.sh             build
#   ./build_mac.sh --install   build and copy to ~/Applications
#   ./build_mac.sh --release   build and make the update zip + .sha256 for a GitHub release
set -e
cd "$(dirname "$0")"

PY=""
if command -v uv >/dev/null 2>&1; then
  uv python install 3.12 >/dev/null
  PY="$(uv python find 3.12)"
else
  for cand in /Library/Frameworks/Python.framework/Versions/3.*/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if [ -x "$cand" ] && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
      PY="$cand"; break
    fi
  done
fi
if [ -z "$PY" ]; then
  echo "Need Python 3.9+. Install uv (brew install uv) or Python from python.org."
  exit 1
fi
echo "Building PXL $(cat VERSION) with $PY"

rm -rf .venv-build build dist
"$PY" -m venv .venv-build
source .venv-build/bin/activate
pip install --quiet --upgrade pip
pip install --quiet pyinstaller -r requirements.txt
pyinstaller --noconfirm --log-level WARN PXL.spec
rm -rf "dist/PXL"   # the .app is the deliverable on macOS

if [ "$1" = "--release" ]; then
  (cd dist && ditto -c -k --keepParent PXL.app PXL-mac.zip \
    && shasum -a 256 PXL-mac.zip > PXL-mac.zip.sha256)
  echo "Release files: dist/PXL-mac.zip (+ .sha256)"
fi
if [ "$1" = "--install" ]; then
  mkdir -p ~/Applications
  rm -rf ~/Applications/PXL.app
  ditto dist/PXL.app ~/Applications/PXL.app
  echo "Installed to ~/Applications/PXL.app"
fi
echo
echo "Done: dist/PXL.app"
