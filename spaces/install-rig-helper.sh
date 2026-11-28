#!/bin/sh
# Installs glyph-rig-helper on this Mac: the one file Glyph Rig may run as root, for power and firewall
# settings from a template. Run it once per Mac, as yourself, with sudo:
#
#   sudo sh install-rig-helper.sh
#
# It copies the helper root-owned to /usr/local/libexec, and adds /etc/sudoers.d/glyph-rig letting you (the
# user who ran sudo) run that one file without a password. The sudoers line is checked with visudo before it
# is put in place. Every folder above the helper must be root-owned, or anyone could swap the file.
#   sudo sh install-rig-helper.sh --remove     takes both away again
set -eu
PATH=/usr/bin:/bin:/usr/sbin:/sbin
[ "$(id -u)" = 0 ] || { echo "run it with sudo: sudo sh $0" >&2; exit 1; }
user=${SUDO_USER:-}
[ -n "$user" ] && [ "$user" != root ] || { echo "run it with sudo from your own account, not as root" >&2; exit 1; }
here=$(cd "$(dirname "$0")" && pwd)
dest=/usr/local/libexec/glyph-rig-helper
rule=/etc/sudoers.d/glyph-rig

if [ "${1:-}" = --remove ]; then
  rm -f "$rule" "$dest"
  echo "removed $dest and $rule"
  exit 0
fi

mkdir -p /usr/local/libexec
for d in /usr /usr/local /usr/local/libexec; do
  [ "$(stat -f %Su "$d")" = root ] || { echo "$d is not owned by root: the helper would not be safe there" >&2; exit 1; }
  chown root:wheel "$d" 2>/dev/null || true
  chmod go-w "$d"
done
install -o root -g wheel -m 0755 "$here/glyph-rig-helper" "$dest"

tmp=$(mktemp)
printf '# Glyph Rig: %s may run this one root helper without a password (install-rig-helper.sh)\n%s ALL=(root) NOPASSWD: %s\n' \
  "$user" "$user" "$dest" > "$tmp"
visudo -cf "$tmp" >/dev/null || { rm -f "$tmp"; echo "the sudoers line did not check out; nothing changed" >&2; exit 1; }
install -o root -g wheel -m 0440 "$tmp" "$rule"
rm -f "$tmp"
sudo -u "$user" sudo -n "$dest" version
echo "installed: $user can run $dest without a password"
