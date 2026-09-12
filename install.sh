#!/bin/sh
# claude-nametag installer. Copies nametag.zsh into ~/.config/nametag/ and
# sources it from ~/.zshrc. Re-running it is safe.
set -e

SRC="$(cd "$(dirname "$0")" && pwd)/nametag.zsh"
DEST="${XDG_CONFIG_HOME:-$HOME/.config}/nametag"
LINE='[ -r "$HOME/.config/nametag/nametag.zsh" ] && . "$HOME/.config/nametag/nametag.zsh"'

[ -r "$SRC" ] || { echo "nametag.zsh not found next to this script" >&2; exit 1; }

mkdir -p "$DEST"
cp "$SRC" "$DEST/nametag.zsh"
echo "installed $DEST/nametag.zsh"

if grep -qF 'nametag.zsh' "$HOME/.zshrc" 2>/dev/null; then
  echo "~/.zshrc already sources it"
else
  printf '\n# claude-nametag\n%s\n' "$LINE" >> "$HOME/.zshrc"
  echo "added the source line to ~/.zshrc"
fi

echo
echo "Open a new shell (or run: exec zsh), then try:"
echo "  NAMETAG_DRYRUN=1 claude billing"
