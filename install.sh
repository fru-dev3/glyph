#!/bin/sh
# glyph installer. Copies glyph.zsh into ~/.config/glyph/ and
# sources it from ~/.zshrc. Re-running it is safe.
set -e

SRC="$(cd "$(dirname "$0")" && pwd)/glyph.zsh"
DEST="${XDG_CONFIG_HOME:-$HOME/.config}/glyph"
LINE='[ -r "$HOME/.config/glyph/glyph.zsh" ] && . "$HOME/.config/glyph/glyph.zsh"'

[ -r "$SRC" ] || { echo "glyph.zsh not found next to this script" >&2; exit 1; }

mkdir -p "$DEST"
cp "$SRC" "$DEST/glyph.zsh"
echo "installed $DEST/glyph.zsh"

if grep -qF 'glyph.zsh' "$HOME/.zshrc" 2>/dev/null; then
  echo "~/.zshrc already sources it"
else
  printf '\n# glyph\n%s\n' "$LINE" >> "$HOME/.zshrc"
  echo "added the source line to ~/.zshrc"
fi

echo
echo "Open a new shell (or run: exec zsh), then try:"
echo "  GLYPH_DRYRUN=1 claude billing"
