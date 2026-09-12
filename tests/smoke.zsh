#!/bin/zsh
set -eu
repo=${0:A:h:h}
test_dir=$(mktemp -d)
trap 'command rm -r -- "$test_dir"' EXIT
mkdir -p "$test_dir/bin"
cat > "$test_dir/bin/agy" <<'STUB'
#!/bin/zsh
printf '<%s>\n' "$@"
STUB
cat > "$test_dir/bin/tmux" <<'STUB'
#!/bin/zsh
print -r -- "${(j: :)@}" >> "$GLYPH_TEST_TMUX"
case $1 in new-session|split-window) print -r -- '%1';; esac
STUB
chmod +x "$test_dir/bin/agy" "$test_dir/bin/tmux"
export PATH="$test_dir/bin:$PATH"
export GLYPH_LOG=0 GLYPH_TITLE=0 GLYPH_MACHINE=test GLYPH_FMT=stamp
export GLYPH_STATE="$test_dir/state" GLYPH_TEST_TMUX="$test_dir/tmux.log"
unset GLYPH_YOLO GLYPH_DRYRUN GLYPH_OFF TMUX
source "$repo/glyph.zsh"
_glyph_project() { print -r -- 'Acme API' }
assert_eq() { [[ $1 == $2 ]] || { print -ru2 -- "FAIL: $3: got [$1], expected [$2]"; exit 1; } }
assert_eq "$(agy billing)" '<>' 'AGY consumes label'
assert_eq "$(agy billing 'fix the retry')" $'<--prompt-interactive>\n<fix the retry>' 'AGY interactive prompt'
assert_eq "$(agy 'fix the retry')" $'<--prompt-interactive>\n<fix the retry>' 'AGY phrase prompt'
assert_eq "$(agy -p 'fix the retry')" $'<-p>\n<fix the retry>' 'AGY print pass-through'
assert_eq "$(agy models)" '<models>' 'AGY management pass-through'
assert_eq "$(GLYPH_YOLO=1 agy billing)" '<--dangerously-skip-permissions>' 'AGY opt-in auto approval'
assert_eq "$(GLYPH_DRYRUN=1 _glyph_launch codex billing)" 'codex' 'Codex consumes label'
assert_eq "$(GLYPH_DRYRUN=1 _glyph_launch claude billing)" "claude -n billing·acme-api·claude-code·test·stamp --remote-control" 'Claude naming'
assert_eq "$(_glyph_compose 'Fix Login' 'Acme API' claude)" 'fix-login·acme-api·claude-code·test·stamp' 'canonical token format'
for adapter in gemini cursor-agent crush cortex opencode pi; do
  assert_eq "$(GLYPH_DRYRUN=1 _glyph_launch "$adapter" billing)" "$adapter" "$adapter consumes label"
done
out=$(GLYPH_DRYRUN=1 glyph fleet pi opencode)
[[ $out == *'pane 2  opencode on local'* ]] || { print -ru2 -- 'FAIL: ad-hoc agents without approval flags'; exit 1; }
export GLYPH_FLEET_CONF="$test_dir/fleet.conf"
printf 'ci = claude agy codex\nremote = agy:studio\n' > "$GLYPH_FLEET_CONF"
out=$(GLYPH_DRYRUN=1 glyph fleet ci)
[[ $out == *'pane 2  agy on local'* ]] || { print -ru2 -- 'FAIL: preset preview'; exit 1; }
glyph fleet ci
[[ $(< "$GLYPH_TEST_TMUX") == *'agy ci C-m'* ]] || { print -ru2 -- 'FAIL: fleet must send label, not full mark'; exit 1; }
glyph fleet remote
[[ $(< "$GLYPH_TEST_TMUX") == *'ssh -t studio'* ]] || { print -ru2 -- 'FAIL: remote fleet command'; exit 1; }
[[ ! -e "$GLYPH_STATE/sessions.tsv" ]] || { print -ru2 -- 'FAIL: disabled log wrote state'; exit 1; }
export GLYPH_FLEET_CONF="$test_dir/nested/new-fleet.conf"
GLYPH_DRYRUN=1 glyph fleet init >/dev/null
[[ ! -e $GLYPH_FLEET_CONF ]] || { print -ru2 -- 'FAIL: init dry run wrote config'; exit 1; }
glyph fleet init >/dev/null
assert_eq "$(_glyph_fleet_slots ci)" ' claude agy codex' 'init creates ci'
initial=$(< "$GLYPH_FLEET_CONF")
glyph fleet init >/dev/null
assert_eq "$(< "$GLYPH_FLEET_CONF")" "$initial" 'init is idempotent'
printf 'ci = pi' > "$GLYPH_FLEET_CONF"
glyph fleet init >/dev/null
assert_eq "$(_glyph_fleet_slots ci)" ' pi' 'init keeps customized preset without trailing newline'
assert_eq "$(_glyph_fleet_slots review)" ' claude codex' 'init adds missing preset'
print -r -- 'PASS: one-command fleet init, custom config path, existing definitions, repeat runs and dry run'
print -r -- 'PASS: AGY labels, prompts, print mode, management commands and opt-in flags'
print -r -- 'PASS: all nine adapter labels, local/SSH fleet construction and pi/OpenCode ad-hoc fleets'
