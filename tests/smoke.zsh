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
# Point every lookup at the sandbox. Without this the suite reads whatever
# agents.tsv and names.tsv the person running it happens to have, and a
# personal 'cc' label fails an assertion about the shipped default.
export GLYPH_AGENTS="$test_dir/agents-none.tsv" GLYPH_MAP="$test_dir/names-none.tsv"
unset GLYPH_ORDER GLYPH_MACHINE_ORDER 2>/dev/null
unset GLYPH_YOLO GLYPH_DRYRUN GLYPH_OFF TMUX CLAUDECODE GLYPH_AGENT GLYPH_AGENT_FALLBACK
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
# The agent segment is never dropped, so every mark has the same field count and
# `glyph ps` lines up. With no agent to name and none owning the shell, the
# honest answer is the shell itself.
assert_eq "$(_glyph_compose 'Fix Login' 'Acme API')" \
  'fix-login·acme-api·shell·test·stamp' 'agent segment falls back to shell'
assert_eq "$(CLAUDECODE=1 _glyph_compose 'Fix Login' 'Acme API')" \
  'fix-login·acme-api·claude-code·test·stamp' 'agent segment read from the environment'
assert_eq "$(GLYPH_AGENT=codex _glyph_compose 'Fix Login' 'Acme API')" \
  'fix-login·acme-api·codex·test·stamp' 'GLYPH_AGENT declares the agent'
assert_eq "$(GLYPH_AGENT_FALLBACK=unknown _glyph_compose 'Fix Login' 'Acme API')" \
  'fix-login·acme-api·unknown·test·stamp' 'fallback is overridable'
assert_eq "$(GLYPH_AGENT=codex glyph name 'Fix Login')" \
  'fix-login·acme-api·codex·test·stamp' 'glyph name carries the agent too'
# The fleet mark is the one place that opts out: each slot prints its own agent
# in front of the shared mark, so a segment here would say it twice.
assert_eq "$(_glyph_compose 'ci' 'Acme API' none)" \
  'ci·acme-api·test·stamp' 'none leaves the segment out'
# GLYPH_ORDER names the fields, so a setup can put the machine before the agent
# without overriding _glyph_compose from outside.
assert_eq "$(GLYPH_ORDER='label project machine agent stamp' _glyph_compose 'Fix Login' 'Acme API' claude)" \
  'fix-login·acme-api·test·claude-code·stamp' 'GLYPH_ORDER reorders the fields'
assert_eq "$(GLYPH_ORDER='label stamp' _glyph_compose 'Fix Login' 'Acme API' claude)" \
  'fix-login·stamp' 'GLYPH_ORDER can leave fields out'
# agents.tsv may rename an agent, not only add one. The loader used to run
# before GLYPH_LABEL was assigned, so a label set there was wiped a line later.
printf 'claude\t--dangerously-skip-permissions\tcc\n' > "$test_dir/agents.tsv"
GLYPH_AGENTS="$test_dir/agents.tsv" source "$repo/glyph.zsh"
_glyph_project() { print -r -- 'Acme API' }
assert_eq "$(_glyph_compose 'Fix Login' 'Acme API' claude)" \
  'fix-login·acme-api·cc·test·stamp' 'agents.tsv overrides a built-in label'
assert_eq "$(GLYPH_YOLO=1 GLYPH_DRYRUN=1 _glyph_launch claude billing)" \
  'claude --dangerously-skip-permissions -n billing·acme-api·cc·test·stamp --remote-control' \
  'overriding the label keeps the auto-approve flag'
unset GLYPH_AGENTS
source "$repo/glyph.zsh"
_glyph_project() { print -r -- 'Acme API' }
# Adapters with no session-name flag swallow the label into the title only.
for adapter in gemini cursor-agent crush cortex opencode; do
  assert_eq "$(GLYPH_DRYRUN=1 _glyph_launch "$adapter" billing)" "$adapter" "$adapter consumes label"
done
# pi names its own session with -n, like Claude. It must NOT inherit Claude's
# --remote-control: that flag belongs to the agent, not to "has a name flag".
assert_eq "$(GLYPH_DRYRUN=1 _glyph_launch pi billing)" \
  'pi -n billing·acme-api·pi·test·stamp' 'pi names its session, without remote-control'
# Auto-approve reaches every adapter that has a flag for it.
assert_eq "$(GLYPH_YOLO=1 GLYPH_DRYRUN=1 _glyph_launch opencode billing)" \
  'opencode --dangerously-skip-permissions' 'opencode auto-approve'
assert_eq "$(GLYPH_YOLO=1 GLYPH_DRYRUN=1 _glyph_launch codex billing)" \
  'codex --dangerously-bypass-approvals-and-sandbox' 'codex auto-approve'
assert_eq "$(GLYPH_YOLO=1 GLYPH_DRYRUN=1 _glyph_launch agy billing)" \
  'agy --dangerously-skip-permissions' 'agy auto-approve'
out=$(GLYPH_DRYRUN=1 glyph fleet pi opencode)
[[ $out == *'pane 2  opencode on local'* ]] || { print -ru2 -- 'FAIL: ad-hoc agents without approval flags'; exit 1; }
export GLYPH_FLEET_CONF="$test_dir/fleet.conf"
export GLYPH_FLEET_BACKEND=tmux
printf 'ci = claude agy codex\nremote = agy:studio\n' > "$GLYPH_FLEET_CONF"
out=$(GLYPH_DRYRUN=1 glyph fleet ci)
[[ $out == *'pane 2  agy on local'* ]] || { print -ru2 -- 'FAIL: preset preview'; exit 1; }
glyph fleet ci
[[ $(< "$GLYPH_TEST_TMUX") == *'agy ci C-m'* ]] || { print -ru2 -- 'FAIL: fleet must send label, not full mark'; exit 1; }
glyph fleet remote
[[ $(< "$GLYPH_TEST_TMUX") == *'ssh -t studio'* ]] || { print -ru2 -- 'FAIL: remote fleet command'; exit 1; }
[[ ! -e "$GLYPH_STATE/sessions.tsv" ]] || { print -ru2 -- 'FAIL: disabled log wrote state'; exit 1; }
unset GLYPH_FLEET_BACKEND
export HERDR_ENV=1
out=$(GLYPH_DRYRUN=1 glyph fleet ci)
[[ $out == *'backend herdr'* && $out == *'herdr tab'* ]] || { print -ru2 -- 'FAIL: Herdr fleet backend'; exit 1; }
unset HERDR_ENV
export CMUX_SOCKET_PATH=/tmp/cmux-test.sock
out=$(GLYPH_DRYRUN=1 glyph fleet ci)
[[ $out == *'backend cmux'* && $out == *'cmux workspace'* ]] || { print -ru2 -- 'FAIL: cmux fleet backend'; exit 1; }
unset CMUX_SOCKET_PATH
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
