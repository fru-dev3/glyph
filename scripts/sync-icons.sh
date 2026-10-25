#!/usr/bin/env bash
#
# Copy the app icons from assets/family/ (the one source, made by build.py) into the site,
# so docs/ never carries its own copy of the artwork. Run by ship.sh before every build;
# run it by hand to preview the site locally. The copies are git-ignored.
set -euo pipefail
cd "$(dirname "$0")/.."
src=assets/family; out=docs/family
rm -rf "$out"; mkdir -p "$out"
for a in glyph studio dictate record cast code rig knowledge; do
  cp "$src/$a-tile.svg" "$src/$a-512.png" "$out/"
  sips -Z 192 "$src/$a-512.png" --out "$out/$a-192.png" >/dev/null
  # iOS rounds the home-screen icon itself: start from the full-bleed one where there is one
  full="$src/$a-ios-1024.png"; [ -f "$full" ] || full="$src/$a-512.png"
  sips -Z 180 "$full" --out "$out/$a-180.png" >/dev/null
done
cp "$src/glyph-tile.svg" docs/favicon.svg
cp "$src/glyph-512.png" docs/icon-512.png
cp "$out/glyph-192.png" docs/icon-192.png
cp "$out/glyph-180.png" docs/apple-touch-icon.png
sips -Z 48 -s format ico "$src/glyph-512.png" --out docs/favicon.ico >/dev/null 2>&1 || true
echo "icons: copied from $src"
