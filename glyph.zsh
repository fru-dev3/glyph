# glyph - one identity for every coding agent you run.
#
#   claude billing   ->  billing·acme-api·claude-code·mbp·2026-09-12·0556
#   agy billing      ->  same name, on the terminal and tmux window
#   codex billing    ->  same
#
# A glyph is an incised mark. This cuts one into every agent session you start,
# so a session list - on your phone, in tmux, across machines - tells you what
# it is, whose project, which machine, and when it began.
#
# Why a shell wrapper: the name must exist before the process starts, so it can
# only come from argv. Plugins and SessionStart hooks run too late.
#
# Knobs:
#   GLYPH_OFF=1       keep the name, drop the machine and time
#   GLYPH_FMT         date(1) format for the stamp (default %Y-%m-%d·%H%M)
#   GLYPH_MACHINE     machine tag, when the hostname does not map well
#   GLYPH_SEP         separator (default ·)
#   GLYPH_YOLO=1      auto-approve tool calls (each agent's own flag; off by default)
#   GLYPH_RC=0        do not add Claude's --remote-control
#   GLYPH_TITLE=0     do not retitle the terminal / tmux window
#   GLYPH_LOG=0       do not record sessions to the local registry
#   GLYPH_DRYRUN=1    print the argv instead of launching
#   GLYPH_FLEET_BACKEND=auto|herdr|cmux|zellij|wezterm|tmux   fleet workspace backend
#   ~/.config/glyph/names.tsv    "<dir-name>\t<Display Name>" overrides

typeset -g GLYPH_STATE=${GLYPH_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/glyph}

# --- agent adapters ---------------------------------------------------------
# name|yolo flag|name flag|extra flags
# Only Claude Code can name its own session; for everyone else the glyph lands
# on the terminal title, the tmux window, and the registry.
typeset -gA GLYPH_YOLO_FLAG GLYPH_NAME_FLAG GLYPH_EXTRA GLYPH_LABEL
GLYPH_YOLO_FLAG=(
  claude       "--dangerously-skip-permissions"
  agy          "--dangerously-skip-permissions"
  gemini       "--yolo"
  codex        "--dangerously-bypass-approvals-and-sandbox"
  cursor-agent "--force"
  crush        "--yolo"
  cortex       "--dangerously-allow-all-tool-calls"
  opencode     ""
  pi           ""
)
GLYPH_NAME_FLAG=( claude "-n" )
GLYPH_LABEL=(
  claude "claude-code"  agy "agy"  gemini "gemini-cli"
  codex "codex"  cursor-agent "cursor"  crush "crush"
  cortex "cortex"  opencode "opencode"  pi "pi"
)

# --- pieces of the mark -----------------------------------------------------
_glyph_token() {
  local value=${1:-}
  value=${(L)value}
  print -r -- "$value" | command sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//'
}

_glyph_machine() {
  local h=${GLYPH_MACHINE:-}
  if [[ -n $h ]]; then _glyph_token "$h"; return; fi
  local os=$(command uname -s 2>/dev/null)
  if [[ $os == Darwin ]] && command -v scutil >/dev/null 2>&1; then
    h=$(command scutil --get ComputerName 2>/dev/null)
  fi
  [[ -n $h ]] || h=$(command hostname 2>/dev/null)
  [[ -n $h ]] || h=$(command hostname -s 2>/dev/null)
  _glyph_token "$h"
}

_glyph_project() {
  local dir=${1:-$PWD} root slug line
  root=$(command git -C "$dir" rev-parse --show-toplevel 2>/dev/null) || return 0
  slug=${root:t}
  local map=${GLYPH_MAP:-$HOME/.config/glyph/names.tsv}
  if [[ -r $map ]]; then
    line=$(command grep -m1 -E "^${slug}"$'\t' "$map" 2>/dev/null)
    [[ -n $line ]] && { _glyph_token "${line#*$'\t'}"; return 0; }
  fi
  _glyph_token "$slug"
}

_glyph_compose() {
  local g=$1 pj=$2 agent=${3:-} sep=${GLYPH_SEP:-·}
  local -a parts
  [[ -n $g ]] && parts+=("$(_glyph_token "$g")")
  [[ -n $pj && ${(L)pj} != ${(L)g} ]] && parts+=("$(_glyph_token "$pj")")
  [[ -n $agent ]] && parts+=("$(_glyph_token "${GLYPH_LABEL[$agent]:-$agent}")")
  if [[ -z ${GLYPH_OFF:-} ]]; then
    parts+=("$(_glyph_machine)")
    parts+=("$(command date +${GLYPH_FMT:-%Y-%m-%d${sep}%H%M})")
  fi
  print -r -- "${(pj:$sep:)parts}"
}

_glyph_title() {
  [[ ${GLYPH_TITLE:-1} == 1 ]] || return 0
  printf '\033]2;%s\007\033]1;%s\007' "$1" "$1"
  [[ -n ${TMUX:-} ]] && command tmux rename-window "$1" 2>/dev/null
  return 0
}

_glyph_log() {
  [[ ${GLYPH_LOG:-1} == 1 ]] || return 0
  [[ -z ${GLYPH_DRYRUN:-} ]] || return 0   # a dry run must leave no trace
  command mkdir -p "$GLYPH_STATE" 2>/dev/null || return 0
  printf '%s\t%s\t%s\t%s\t%s\n' \
    "$(command date +%Y-%m-%dT%H:%M:%S)" "$1" "$2" "$PWD" "$(_glyph_machine)" \
    >> "$GLYPH_STATE/sessions.tsv" 2>/dev/null
  return 0
}

# --- the wrapper ------------------------------------------------------------
# $1 is the agent command; the rest is the user's argv.
_glyph_launch() {
  emulate -L zsh
  local agent=$1; shift
  local -a pre
  local given="" proj="" yolo=${GLYPH_YOLO_FLAG[$agent]:-}

  _glyph_run() {
    if [[ -n ${GLYPH_DRYRUN:-} ]]; then print -r -- "$agent" ${(q-)@}; return 0; fi
    command "$agent" "$@"
  }

  # Subcommands manage the install or address existing sessions: never decorate.
  case ${1:-} in
    mcp|auth|login|logout|plugin|plugins|install|update|upgrade|doctor|agents|setup-token|daemon|import|export|config|resume|fork|queue|archive|unarchive|delete|session|sessions|ls|migrate-rollouts|migrate-installer)
      _glyph_run "$@"; return ;;
  esac
  # AGY has its own management commands; none is a session label.
  if [[ $agent == agy ]]; then
    case ${1:-} in
      agent|changelog|help|mic-serve|models|remote-control)
        _glyph_run "$@"; return ;;
    esac
  fi
  # Non-interactive runs pass straight through.
  if [[ " $* " == *" -p "* || " $* " == *" --print "* || " $* " == *" --headless "* ]]; then
    _glyph_run "$@"; return
  fi

  [[ -n ${GLYPH_YOLO:-} && -n $yolo && " $* " != *" $yolo "* ]] && pre+=("$yolo")
  proj=$(_glyph_project "$PWD")

  local nameflag=${GLYPH_NAME_FLAG[$agent]:-}
  local -a cargs; cargs=("$@")   # never call this `argv`: in zsh that IS $@
  local i

  # An explicit -n / --name: stamp the value in place (Claude only).
  if [[ -n $nameflag ]]; then
    for (( i = 1; i <= $#cargs; i++ )); do
      if [[ $cargs[i] == (-n|--name) && -n ${cargs[i+1]:-} ]]; then
        cargs[i+1]=$(_glyph_compose "$cargs[i+1]" "$proj" "$agent")
        [[ ${GLYPH_RC:-1} == 1 && " $* " != *" --remote-control "* && " $* " != *" --rc "* ]] \
          && pre+=(--remote-control)
        _glyph_title "$cargs[i+1]"; _glyph_log "$agent" "$cargs[i+1]"
        _glyph_run $pre "${cargs[@]}"; return
      fi
    done
    if [[ " $* " == *" --remote-control "* || " $* " == *" --rc "* ]]; then
      _glyph_run $pre "$@"; return
    fi
  fi

  # A bare first argument is the label - but only a single bare word. Anything
  # containing whitespace is a prompt ("fix the login bug") and is left alone.
  if [[ -n ${1:-} && ${1:-} != -* && ${1:-} != *[[:space:]]* ]]; then
    given=$1; shift
  fi

  # AGY rejects positional prompts; interactive prompts need its explicit flag.
  if [[ $agent == agy && -n ${1:-} && ${1:-} != -* ]]; then
    set -- --prompt-interactive "$@"
  fi

  local mark=$(_glyph_compose "$given" "$proj" "$agent")
  if [[ -n $mark ]]; then
    [[ -n $nameflag ]] && pre+=("$nameflag" "$mark")
    _glyph_title "$mark"; _glyph_log "$agent" "$mark"
  fi
  [[ -n $nameflag && ${GLYPH_RC:-1} == 1 ]] && pre+=(--remote-control)

  _glyph_run $pre "$@"
}

# Define a wrapper for each agent that is actually installed.
for _g_agent in ${(k)GLYPH_YOLO_FLAG}; do
  if command -v "$_g_agent" >/dev/null 2>&1; then
    eval "${_g_agent//-/_}() { _glyph_launch ${(q)_g_agent} \"\$@\" }"
    [[ $_g_agent == *-* ]] && eval "function ${_g_agent}() { _glyph_launch ${(q)_g_agent} \"\$@\" }"
  fi
done
unset _g_agent

# glyph itself: a tiny front door.
glyph() {
  case ${1:-help} in
    ls|log)
      [[ -r $GLYPH_STATE/sessions.tsv ]] || { print -r -- "no sessions recorded yet"; return 0; }
      command tail -${2:-20} "$GLYPH_STATE/sessions.tsv" | command awk -F'\t' \
        '{printf "%-20s %-13s %-52s %s\n", $1, $2, $3, $5}' ;;
    agents)
      local a
      for a in ${(ok)GLYPH_YOLO_FLAG}; do
        command -v "$a" >/dev/null 2>&1 \
          && printf "%-14s %-14s %s\n" "$a" "${GLYPH_LABEL[$a]}" "${GLYPH_YOLO_FLAG[$a]:-(no yolo flag)}"
      done ;;
    name) shift; _glyph_compose "${1:-}" "$(_glyph_project "$PWD")" ;;
    fleet) shift; glyph-fleet "$@" ;;
    presets)
      local conf=$(_glyph_fleet_conf)
      [[ -r $conf ]] && command grep -E "^[[:space:]]*[a-zA-Z0-9_-]+[[:space:]]*=" "$conf" \
        || print -r -- "no presets yet: write them to $conf" ;;
    *) print -r -- "glyph ls [n]   recent sessions
glyph agents   installed agents and their auto-approve flags
glyph name [x] print the mark this directory would produce
glyph fleet init create example fleets without replacing existing presets
glyph fleet [p] launch a preset of agents, each in its own marked tmux pane
glyph presets  list the presets in ~/.config/glyph/fleet.conf" ;;
  esac
}

# --- fleet: several marked agents at once ------------------------------------
# A preset is a line in ~/.config/glyph/fleet.conf:
#
#   default = claude agy codex
#   review  = claude claude:mini
#   pair    = claude:mini agy
#
# Each slot is <agent>[:<machine>]. A machine is an ssh host, or "local".
# Every pane is launched through the same wrapper, so every pane carries the
# mark - and the pane border shows it.
_glyph_fleet_conf() { print -r -- "${GLYPH_FLEET_CONF:-$HOME/.config/glyph/fleet.conf}"; }

_glyph_fleet_slots() {              # $1 = preset name -> slots on stdout
  local conf=$(_glyph_fleet_conf) line
  [[ -r $conf ]] || return 1
  line=$(command grep -m1 -E "^[[:space:]]*$1[[:space:]]*=" "$conf" 2>/dev/null) || return 1
  print -r -- "${line#*=}"
}

_glyph_fleet_init() {
  emulate -L zsh
  local conf=$(_glyph_fleet_conf) preset line added=0
  if [[ -n ${GLYPH_DRYRUN:-} ]]; then
    print -r -- "would add missing ci, review and cloud presets to $conf"
    return 0
  fi
  command mkdir -p "${conf:h}" || return 1
  command touch "$conf" || return 1
  for line in 'ci = claude agy codex' 'review = claude codex' 'cloud = claude:studio codex:studio'; do
    preset=${line%% *}
    if ! command grep -qE "^[[:space:]]*${preset}[[:space:]]*=" "$conf"; then
      printf '\n%s\n' "$line" >> "$conf" || return 1
      (( added += 1 ))
    fi
  done
  print -r -- "fleet config: $conf ($added presets added; existing definitions kept)"
  print -r -- "start a local fleet: glyph fleet ci"
  print -r -- "cloud is an example: replace studio with your SSH host before using it"
}

_glyph_fleet_backend() {
  case ${GLYPH_FLEET_BACKEND:-auto} in
    herdr|cmux|zellij|wezterm|tmux) print -r -- "$GLYPH_FLEET_BACKEND" ;;
    auto)
      [[ -n ${HERDR_ENV:-} ]] && { print -r -- herdr; return; }
      [[ -n ${CMUX_SOCKET_PATH:-} || -n ${CMUX_WORKSPACE_ID:-} ]] && { print -r -- cmux; return; }
      [[ -n ${ZELLIJ_SESSION_NAME:-} ]] && { print -r -- zellij; return; }
      [[ -n ${WEZTERM_PANE:-} ]] && { print -r -- wezterm; return; }
      print -r -- tmux ;;
    *) print -ru2 -- "glyph: unknown fleet backend '$GLYPH_FLEET_BACKEND' (use auto, herdr, cmux, zellij, wezterm or tmux)"; return 1 ;;
  esac
}

_glyph_fleet_herdr() {
  local preset=$1 mark=$2; shift 2
  command -v herdr >/dev/null 2>&1 || { print -ru2 -- 'glyph: Herdr backend needs herdr'; return 1; }
  local slot agent machine label tab_output tab_id command_text
  for slot in "$@"; do
    agent=${slot%%:*}; machine=${slot#*:}
    [[ $machine == $slot ]] && machine=local
    [[ $machine == local ]] || { print -ru2 -- "glyph: Herdr backend does not support SSH slot '$slot'; use tmux backend"; return 1; }
    label="${GLYPH_LABEL[$agent]:-$agent} · $mark"
    if [[ -n ${GLYPH_DRYRUN:-} ]]; then
      print -r -- "herdr tab  $label  ($agent $preset)"
      continue
    fi
    tab_output=$(command herdr tab create --cwd "$PWD" --label "$label" --no-focus 2>/dev/null) || return 1
    tab_id=$(print -r -- "$tab_output" | command sed -n 's/.*"tab_id":"\([^"]*\)".*/\1/p')
    [[ -n $tab_id ]] || { print -ru2 -- 'glyph: could not read Herdr tab id'; return 1; }
    # Start through an interactive zsh so the installed Glyph wrapper supplies
    # the agent-specific flags and title. The tab itself carries the full mark.
    command_text="${agent} ${(q)preset}"
    command herdr agent start "$agent" --cwd "$PWD" --tab "$tab_id" --no-focus -- zsh -lic "$command_text" >/dev/null || return 1
  done
}

_glyph_fleet_cmux() {
  local preset=$1 mark=$2; shift 2
  command -v cmux >/dev/null 2>&1 || { print -ru2 -- 'glyph: cmux backend needs cmux'; return 1; }
  local slot agent machine label command_text
  for slot in "$@"; do
    agent=${slot%%:*}; machine=${slot#*:}
    [[ $machine == $slot ]] && machine=local
    [[ $machine == local ]] || { print -ru2 -- "glyph: cmux backend does not support SSH slot '$slot'; use tmux backend"; return 1; }
    label="${GLYPH_LABEL[$agent]:-$agent} · $mark"
    command_text="zsh -lic ${(q)agent}\ ${(q)preset}"
    if [[ -n ${GLYPH_DRYRUN:-} ]]; then
      print -r -- "cmux workspace  $label  ($command_text)"
    else
      command cmux new-workspace --command "$command_text" >/dev/null || return 1
      command cmux log --source glyph --level info -- "$label" >/dev/null 2>&1 || true
    fi
  done
}

_glyph_fleet_zellij() {
  local preset=$1 mark=$2; shift 2
  [[ -n ${GLYPH_DRYRUN:-} ]] || command -v zellij >/dev/null 2>&1 || { print -ru2 -- 'glyph: zellij backend needs zellij'; return 1; }
  local slot agent machine label command_text
  for slot in "$@"; do
    agent=${slot%%:*}; machine=${slot#*:}
    [[ $machine == $slot ]] && machine=local
    [[ $machine == local ]] || { print -ru2 -- "glyph: zellij backend does not support SSH slot '$slot'; use tmux backend"; return 1; }
    label="${GLYPH_LABEL[$agent]:-$agent} · $mark"
    command_text="${agent} ${(q)preset}"
    if [[ -n ${GLYPH_DRYRUN:-} ]]; then
      print -r -- "zellij pane  $label  (zellij run --cwd $PWD --name $label -- zsh -lic $command_text)"
    else
      command zellij run --cwd "$PWD" --name "$label" -- zsh -lic "$command_text" >/dev/null || return 1
    fi
  done
}

_glyph_fleet_wezterm() {
  local preset=$1 mark=$2; shift 2
  [[ -n ${GLYPH_DRYRUN:-} ]] || command -v wezterm >/dev/null 2>&1 || { print -ru2 -- 'glyph: wezterm backend needs wezterm'; return 1; }
  local slot agent machine label command_text
  for slot in "$@"; do
    agent=${slot%%:*}; machine=${slot#*:}
    [[ $machine == $slot ]] && machine=local
    [[ $machine == local ]] || { print -ru2 -- "glyph: wezterm backend does not support SSH slot '$slot'; use tmux backend"; return 1; }
    label="${GLYPH_LABEL[$agent]:-$agent} · $mark"
    command_text="${agent} ${(q)preset}"
    if [[ -n ${GLYPH_DRYRUN:-} ]]; then
      print -r -- "wezterm tab  $label  (wezterm cli spawn --cwd $PWD -- zsh -lic $command_text)"
    else
      command wezterm cli spawn --cwd "$PWD" -- zsh -lic "$command_text" >/dev/null || return 1
    fi
  done
}

glyph-fleet() {
  emulate -L zsh
  if [[ ${1:-} == init ]]; then _glyph_fleet_init; return; fi
  local preset=${1:-default}; shift 2>/dev/null
  local -a slots
  if [[ $preset == *:* || ${+GLYPH_YOLO_FLAG[${preset%%:*}]} == 1 ]]; then
    slots=("$preset" "$@")          # slots given directly on the command line
    preset="ad-hoc"
  else
    slots=(${=$(_glyph_fleet_slots "$preset")}) || true
    if (( ! $#slots )); then
      print -ru2 -- "glyph: no preset '$preset' in $(_glyph_fleet_conf)"
      return 1
    fi
  fi

  command -v tmux >/dev/null 2>&1 || { print -ru2 -- "glyph: fleet needs tmux"; return 1; }

  local mark=$(_glyph_compose "$preset" "$(_glyph_project "$PWD")")
  local backend=$(_glyph_fleet_backend) || return 1
  local session="glyph-${preset}-$(command date +%H%M%S)"
  local n=$#slots i agent machine cmd label
  local -a panes

  if [[ -n ${GLYPH_DRYRUN:-} ]]; then
    print -r -- "backend $backend  session $session  ($n panes)  mark: $mark"
    for i in {1..$n}; do
      agent=${slots[i]%%:*}; machine=${slots[i]#*:}
      [[ $machine == $slots[i] ]] && machine=local
      print -r -- "  pane $i  $agent on $machine"
    done
    [[ $backend == herdr ]] && _glyph_fleet_herdr "$preset" "$mark" "${slots[@]}"
    [[ $backend == cmux ]] && _glyph_fleet_cmux "$preset" "$mark" "${slots[@]}"
    [[ $backend == zellij ]] && _glyph_fleet_zellij "$preset" "$mark" "${slots[@]}"
    [[ $backend == wezterm ]] && _glyph_fleet_wezterm "$preset" "$mark" "${slots[@]}"
    return 0
  fi

  [[ $backend == herdr ]] && { _glyph_fleet_herdr "$preset" "$mark" "${slots[@]}"; _glyph_log "fleet:$preset" "$mark"; return; }
  [[ $backend == cmux ]] && { _glyph_fleet_cmux "$preset" "$mark" "${slots[@]}"; _glyph_log "fleet:$preset" "$mark"; return; }
  [[ $backend == zellij ]] && { _glyph_fleet_zellij "$preset" "$mark" "${slots[@]}"; _glyph_log "fleet:$preset" "$mark"; return; }
  [[ $backend == wezterm ]] && { _glyph_fleet_wezterm "$preset" "$mark" "${slots[@]}"; _glyph_log "fleet:$preset" "$mark"; return; }

  panes[1]=$(command tmux new-session -d -s "$session" -c "$PWD" -PF '#{pane_id}')
  for (( i = 2; i <= n; i++ )); do
    panes[i]=$(command tmux split-window -t "$session" -c "$PWD" -PF '#{pane_id}')
    command tmux select-layout -t "$session" tiled >/dev/null 2>&1
  done
  command tmux select-layout -t "$session" tiled >/dev/null 2>&1
  command tmux set-option -t "$session" pane-border-status top >/dev/null 2>&1
  # #{@label}, not #{pane_title}: an agent sets its own OSC title and would
  # overwrite anything we put in pane_title.
  command tmux set-option -t "$session" pane-border-format ' #{@label} ' >/dev/null 2>&1

  for (( i = 1; i <= n; i++ )); do
    agent=${slots[i]%%:*}; machine=${slots[i]#*:}
    [[ $machine == $slots[i] ]] && machine=local
    label="${GLYPH_LABEL[$agent]:-$agent}"
    if [[ $machine == local ]]; then
      cmd="${(q)agent} ${(q)preset}"
    else
      label="$label @$machine"
      local remote_script="cd ${(q)PWD} && ${(q)agent} ${(q)preset}"
      # Interactive zsh loads the remote Glyph wrapper from .zshrc.
      local remote_cmd="zsh -ic ${(q)remote_script}"
      cmd="ssh -t ${(q)machine} ${(q)remote_cmd}"
    fi
    command tmux set-option -p -t "$panes[i]" @label "$label · $mark" >/dev/null 2>&1
    command tmux send-keys -t "$panes[i]" "$cmd" C-m
  done

  _glyph_log "fleet:$preset" "$mark"
  if [[ -n ${TMUX:-} ]]; then command tmux switch-client -t "$session"
  else command tmux attach -t "$session"; fi
}
