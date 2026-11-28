#!/bin/bash
# The hourly Glyph Rig reading: this Mac's report every hour, a speed test every sixth hour.
# Glyph Rig ships this file inside the app with the collector, copies both to
# ~/Library/Application Support/dev.fru.rig/collector and installs it from its Settings (Set up):
#   rig-reading.sh --install     a LaunchAgent at minute 7 of every hour, then one reading now
#   rig-reading.sh --uninstall   unloads it and removes the LaunchAgent
#   rig-reading.sh [--speed]     one reading (what the LaunchAgent runs)
# Each run has a ceiling: a reading that hangs (a folder listing waiting on a privacy prompt no one
# answers) is stopped and Python prints where it was stuck into the log, so the next hour still runs.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
set -o pipefail
here="$(cd "$(dirname "$0")" && pwd)"
fleet="$here/glyph-fleet"
label=dev.fru.rig-reading
plist="$HOME/Library/LaunchAgents/$label.plist"
log="$HOME/Library/Logs/rig-reading.log"

case "${1:-}" in
  --install)
    mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
    cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$here/rig-reading.sh</string></array>
  <key>StartCalendarInterval</key><dict><key>Minute</key><integer>7</integer></dict>
  <key>RunAtLoad</key><false/>
  <key>Nice</key><integer>10</integer>
  <key>StandardOutPath</key><string>$log</string>
  <key>StandardErrorPath</key><string>$log</string>
</dict>
</plist>
PLIST
    plutil -lint "$plist" >/dev/null || { echo "the LaunchAgent did not check out"; exit 1; }
    launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$plist"
    launchctl kickstart "gui/$(id -u)/$label"
    echo "installed $label"
    exit 0;;
  --uninstall)
    launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || true
    rm -f "$plist"
    echo "uninstalled $label"
    exit 0;;
esac

[ -f "$fleet" ] || { echo "$(date '+%F %T') no glyph-fleet beside this script"; exit 1; }
limit() { perl -e '$p=fork; if(!$p){exec @ARGV[1..$#ARGV]} $SIG{ALRM}=sub{kill "ABRT",$p}; alarm $ARGV[0]; waitpid($p,0); exit($? & 127 ? 124 : $?>>8)' "$@"; }
status=0
echo "$(date '+%F %T') report"
out=$(limit 600 python3 -X faulthandler "$fleet" report 2>&1) || status=1
printf '%s\n' "$out" | head -3
[ $status -eq 0 ] || printf '%s\n' "$out" | tail -400
if [ $(( 10#$(date +%H) % 6 )) -eq 0 ] || [ "${1:-}" = "--speed" ]; then
  echo "$(date '+%F %T') speed"
  out=$(limit 300 python3 -X faulthandler "$fleet" speed 2>&1) || status=1
  printf '%s\n' "$out" | tail -1
fi
exit $status
