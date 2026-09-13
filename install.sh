#!/bin/sh
# glyph installer.
#
#   . ./install.sh      installs and loads glyph into this shell right away
#   ./install.sh        installs, then tells you how to load it
#
# A script run as a child process cannot define functions in the shell that
# started it, which is why the second form needs one reload. Sourcing it
# avoids that entirely. Re-running either form is safe.

_glyph_install() {
  _gi_sourced=0
  if [ -n "${ZSH_VERSION:-}" ]; then
    case "${ZSH_EVAL_CONTEXT:-}" in *:file*) _gi_sourced=1 ;; esac
    eval '_gi_self=${(%):-%x}'
  elif [ -n "${BASH_VERSION:-}" ]; then
    eval '_gi_self=${BASH_SOURCE:-$0}'
    [ "$_gi_self" != "$0" ] && _gi_sourced=1
  else
    _gi_self=$0
  fi

  _gi_dir=$(cd "$(dirname "$_gi_self")" 2>/dev/null && pwd) || {
    echo "glyph: cannot locate the installer directory" >&2; return 1; }
  _gi_src="$_gi_dir/glyph.zsh"
  _gi_dest="${XDG_CONFIG_HOME:-$HOME/.config}/glyph"
  _gi_line='[ -r "$HOME/.config/glyph/glyph.zsh" ] && . "$HOME/.config/glyph/glyph.zsh"'

  [ -r "$_gi_src" ] || {
    echo "glyph.zsh not found next to this script" >&2; return 1; }

  mkdir -p "$_gi_dest" || return 1
  # An install linked into a synced folder keeps its link.
  if [ -L "$_gi_dest/glyph.zsh" ]; then
    _gi_target=$(cd "$(dirname "$_gi_dest/glyph.zsh")" && pwd)/$(readlink "$_gi_dest/glyph.zsh")
    cp "$_gi_src" "$_gi_target" 2>/dev/null || cp "$_gi_src" "$_gi_dest/glyph.zsh" || return 1
  else
    cp "$_gi_src" "$_gi_dest/glyph.zsh" || return 1
  fi
  echo "installed $_gi_dest/glyph.zsh"

  if grep -qF 'glyph.zsh' "$HOME/.zshrc" 2>/dev/null; then
    echo "~/.zshrc already sources it"
  else
    printf '\n# glyph\n%s\n' "$_gi_line" >> "$HOME/.zshrc" || return 1
    echo "added the source line to ~/.zshrc"
  fi

  echo
  if [ "$_gi_sourced" = 1 ] && [ -n "${ZSH_VERSION:-}" ]; then
    . "$_gi_dest/glyph.zsh" || return 1
    echo "glyph is loaded in this shell. try:"
    echo "  glyph version"
    echo "  GLYPH_DRYRUN=1 claude billing"
  elif [ "$_gi_sourced" = 1 ]; then
    echo "glyph is a zsh wrapper, and this is not zsh. start zsh, then:"
    echo "  . $_gi_dest/glyph.zsh"
  else
    echo "load it into this shell with either of these:"
    echo "  exec zsh"
    echo "  . $_gi_dest/glyph.zsh"
    echo
    echo "then try:"
    echo "  glyph version"
    echo "  GLYPH_DRYRUN=1 claude billing"
    echo
    echo "(next time, 'source ./install.sh' installs and loads in one step)"
  fi
  return 0
}

_glyph_install
_gi_rc=$?
unset -f _glyph_install 2>/dev/null
unset _gi_sourced _gi_self _gi_dir _gi_src _gi_dest _gi_line _gi_target 2>/dev/null
( exit $_gi_rc )
