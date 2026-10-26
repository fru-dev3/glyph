#!/usr/bin/env bash
#
# Copy the app icons from assets/family/ (the one source, made by build.py) into the site,
# so docs/ never carries its own copy of the artwork. Run by ship.sh before every build;
# run it by hand to preview the site locally. The copies are git-ignored.
# Every size is rendered from SVG by build.py; nothing here scales a PNG down.
set -euo pipefail
cd "$(dirname "$0")/.."
src=assets/family; out=docs/family
rm -rf "$out"; mkdir -p "$out"
for a in glyph studio jot dictate record cast code rig knowledge arena; do
  cp "$src/$a-tile.svg" "$src/$a-small.svg" "$src/$a-512.png" "$src/$a-192.png" "$src/$a-180.png" "$out/"
done
cp "$src/glyph-small.svg" docs/favicon.svg
cp "$src/glyph-512.png" docs/icon-512.png
cp "$src/glyph-192.png" docs/icon-192.png
cp "$src/glyph-180.png" docs/apple-touch-icon.png
cp "$src/glyph.ico" docs/favicon.ico
echo "icons: copied from $src"
