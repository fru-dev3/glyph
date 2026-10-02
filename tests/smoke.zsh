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
unset GLYPH_ORDER GLYPH_MACHINE_ORDER GLYPH_SEP 2>/dev/null
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
# The account field says which login the agent runs under. It is read from
# Claude Code's own config, only when GLYPH_ORDER names it, and worked out from
# the address: initials and trailing digits, with accounts.tsv to overrule it.
mkdir -p "$test_dir/cfg" "$test_dir/cfg2"
print -r -- '{ "oauthAccount": { "emailAddress": "Foo.Dev3@example.com" } }' > "$test_dir/cfg/.claude.json"
print -r -- '{ "oauthAccount": { "emailAddress": "footech3@example.com" } }' > "$test_dir/cfg2/.claude.json"
export CLAUDE_CONFIG_DIR="$test_dir/cfg" GLYPH_ACCOUNTS="$test_dir/accounts-none.tsv" GLYPH_ME='Foo Bar'
# An address with no dot in it splits after the person's own first name.
assert_eq "$(CLAUDE_CONFIG_DIR="$test_dir/cfg2" glyph account)" 'ft3' 'an unbroken address splits after your own name'
assert_eq "$(CLAUDE_CONFIG_DIR="$test_dir/cfg2" GLYPH_ME=Someone glyph account)" 'f3' 'and stays one word when it is not your name'
assert_eq "$(_glyph_compose 'Fix Login' 'Acme API' claude)" \
  'fix-login·acme-api·claude-code·test·stamp' 'account stays out of the default order'
assert_eq "$(GLYPH_ORDER='label account' _glyph_compose 'Fix Login' 'Acme API' claude)" \
  'fix-login·fd3' 'account falls back to initials and digits'
assert_eq "$(GLYPH_ORDER='label account' _glyph_compose 'Fix Login' 'Acme API' codex)" \
  'fix-login' 'only Claude Code has a known account'
printf '# address\ttag\nfoo.dev3@example.com\tWork\n' > "$test_dir/accounts.tsv"
assert_eq "$(GLYPH_ACCOUNTS="$test_dir/accounts.tsv" GLYPH_ORDER='account label' _glyph_compose 'Fix Login' 'Acme API' claude)" \
  'work·fix-login' 'accounts.tsv names the account'
assert_eq "$(glyph account)" 'fd3' 'glyph account prints the tag by itself'
assert_eq "$(CLAUDE_CONFIG_DIR="$test_dir/nowhere" GLYPH_ORDER='label account' _glyph_compose 'Fix Login' 'Acme API' claude)" \
  'fix-login' 'no login, no account segment'
unset CLAUDE_CONFIG_DIR GLYPH_ACCOUNTS GLYPH_ME
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
_glyph_star_ask </dev/null >/dev/null
[[ ! -e "$GLYPH_STATE/star" ]] || { print -ru2 -- 'FAIL: star question must not run without a terminal'; exit 1; }

# glyph wake: the reset time comes from the quota, the nudge from the pane.
cat > "$test_dir/bin/herdr" <<'STUB'
#!/bin/zsh
print -r -- "${(j: :)@}" >> "$GLYPH_TEST_HERDR"
[[ "$1 $2" == 'pane read' ]] && print -r -- "${GLYPH_TEST_SCREEN:-}"
exit 0
STUB
chmod +x "$test_dir/bin/herdr"
export GLYPH_TEST_HERDR="$test_dir/herdr.log" GLYPH_WAKE_GRACE=0 GLYPH_WAKE_AWAKE=0
_glyph_claude_live() { print -r -- '{"five_hour":{"utilization":100.0,"resets_at":"2026-09-28T22:39:59.75+00:00"},"seven_day":{"utilization":66.0,"resets_at":"2026-10-01T12:00:00+00:00"},"limits":[{"kind":"weekly_scoped","percent":100,"resets_at":"2026-10-02T12:00:00.18+00:00","scope":{"model":{"display_name":"Fable"}}}]}' }
assert_eq "$(_glyph_wake_until)" 1790942400 'wake waits for the latest limit at 100%, percent included'
_glyph_claude_live() { print -r -- '{"five_hour":{"utilization":88.0,"resets_at":"2026-09-28T22:39:59+00:00"}}' }
assert_eq "$(_glyph_wake_until)" 0 'wake reads a limit under 100% as lifted'
_glyph_claude_live() { return 1 }
_glyph_wake_until >/dev/null && { print -ru2 -- 'FAIL: wake must fail when the quota cannot be read'; exit 1; }
_glyph_claude_live() { print -r -- '{"five_hour":{"utilization":3.0,"resets_at":"2026-09-28T22:39:59+00:00"}}' }

wake=$GLYPH_STATE/wake rec=$GLYPH_STATE/wake/w1_p2.pane
mkdir -p "$test_dir/home/.claude/sessions"
print -r -- '{"pid":1,"sessionId":"abc-123","status":"idle"}' > "$test_dir/home/.claude/sessions/$$.json"
: > "$test_dir/t.jsonl"
hookjson="{\"session_id\":\"abc-123\",\"transcript_path\":\"$test_dir/t.jsonl\",\"hook_event_name\":\"StopFailure\",\"error\":\"rate_limit\"}"
park() { print -r -- "$hookjson" | HOME=$test_dir/home HERDR_PANE_ID=w1:p2 HERDR_SOCKET_PATH=/tmp/h.sock glyph wake park }
_glyph_wake_start() { : }                          # the waiter is driven by hand below
print -r -- "$hookjson" | env -u HERDR_PANE_ID -u TMUX_PANE zsh -fc ". ${(q)repo}/glyph.zsh; GLYPH_STATE=${(q)GLYPH_STATE} glyph wake park"
[[ ! -e $rec ]] || { print -ru2 -- 'FAIL: wake parked a session with no pane'; exit 1; }
park
assert_eq "$(sed -n '1p;3,7p' $rec | tr '\n' ' ')" "parked 1 herdr w1:p2 /tmp/h.sock $$ " 'wake parks the pane, socket and session pid'

# Nothing touched it since: continue is typed, then Enter, apart.
( HOME=$test_dir/home _glyph_wake_wait )
assert_eq "$(grep send $GLYPH_TEST_HERDR)" $'pane send-text w1:p2 continue\npane send-keys w1:p2 Enter' 'wake types continue'
assert_eq "$(head -1 $rec)" nudged 'wake marks the pane nudged'
# Limited again straight away: a second try, and after three it stops.
park; assert_eq "$(sed -n 3p $rec)" 2 'a quick second limit counts as another try'
print -rl -- nudged $EPOCHSECONDS 3 herdr w1:p2 > $rec; park
assert_eq "$(head -1 $rec)" gave-up 'wake gives up after three quick limits'

# Slept through the reset: Claude Code asks for Enter, and gets only that.
rm -f $rec $GLYPH_TEST_HERDR; park
( HOME=$test_dir/home GLYPH_TEST_SCREEN='Usage limit has reset · press enter to continue' _glyph_wake_wait )
assert_eq "$(grep send $GLYPH_TEST_HERDR)" 'pane send-keys w1:p2 Enter' 'wake presses enter on a stale prompt'
# Claude Code continued by itself: the transcript moved, so hands off.
rm -f $rec $GLYPH_TEST_HERDR; park
touch -t $(strftime '%Y%m%d%H%M.%S' $(( EPOCHSECONDS + 120 ))) "$test_dir/t.jsonl"
( HOME=$test_dir/home _glyph_wake_wait )
[[ ! -e $rec && ! -e $GLYPH_TEST_HERDR ]] || { print -ru2 -- 'FAIL: wake nudged a session that had continued'; exit 1; }
# The session is gone: nothing is typed into whatever holds the pane now.
: > "$test_dir/t.jsonl"; park
print -r -- '{"sessionId":"someone-else"}' > "$test_dir/home/.claude/sessions/$$.json"
( HOME=$test_dir/home _glyph_wake_wait )
[[ ! -e $rec && ! -e $GLYPH_TEST_HERDR ]] || { print -ru2 -- 'FAIL: wake typed into a closed session'; exit 1; }
# Its process is gone, even if the session file was left behind.
print -rl -- parked $EPOCHSECONDS 1 herdr w1:p2 '' 999999 abc-123 "$test_dir/t.jsonl" > $rec
print -r -- '{"sessionId":"abc-123"}' > "$test_dir/home/.claude/sessions/999999.json"
( HOME=$test_dir/home _glyph_wake_wait )
[[ ! -e $rec && ! -e $GLYPH_TEST_HERDR ]] || { print -ru2 -- 'FAIL: wake typed into a dead session'; exit 1; }
unset GLYPH_WAKE_GRACE GLYPH_WAKE_AWAKE
print -r -- 'PASS: wake reset time, parking, continue, enter, hands-off and give-up'
print -r -- 'PASS: one-command fleet init, custom config path, existing definitions, repeat runs and dry run'
print -r -- 'PASS: AGY labels, prompts, print mode, management commands and opt-in flags'
print -r -- 'PASS: all nine adapter labels, local/SSH fleet construction and pi/OpenCode ad-hoc fleets'
