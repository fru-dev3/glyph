# glyph - one identity for every coding agent you run.
#
#   claude billing   ->  billing·Acme API·mbp·2026-09-12·0556
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
  claude "Claude Code"  agy "Antigravity"  gemini "Gemini CLI"
  codex "Codex"  cursor-agent "Cursor"  crush "Crush"
  cortex "Cortex"  opencode "OpenCode"  pi "pi"
)

# --- pieces of the mark -----------------------------------------------------
_glyph_machine() {
  local h=${GLYPH_MACHINE:-}
  if [[ -n $h ]]; then print -r -- "$h"; return; fi
  h=$(command hostname -s 2>/dev/null); h=${h%%.*}
  case ${(L)h} in
    *mini*)        print -r -- mini ;;
    *air*)         print -r -- air ;;
    *macbook*pro*) print -r -- mbp ;;
    *macbook*)     print -r -- mb ;;
    *imac*)        print -r -- imac ;;
    *studio*)      print -r -- studio ;;
    *) h=${h#[A-Za-z][0-9]-}; print -r -- "${${(L)h}//[^a-z0-9]/}[1,8]" ;;
  esac
}

_glyph_project() {
  local dir=${1:-$PWD} root slug line
  root=$(command git -C "$dir" rev-parse --show-toplevel 2>/dev/null) || return 0
  slug=${root:t}
  local map=${GLYPH_MAP:-$HOME/.config/glyph/names.tsv}
  if [[ -r $map ]]; then
    line=$(command grep -m1 -E "^${slug}"$'\t' "$map" 2>/dev/null)
    [[ -n $line ]] && { print -r -- "${line#*$'\t'}"; return 0; }
  fi
  local base=${slug//[-_]/ } w; local -a out
  for w in ${=base}; do
    case ${(L)w} in
      cli|api|mcp|ai|ui|os|db|sdk|ios|tv) out+=( ${(U)w} ) ;;
      *) out+=( "${(C)w}" ) ;;
    esac
  done
  print -r -- "${(j: :)out}"
}

_glyph_compose() {
  local g=$1 pj=$2 sep=${GLYPH_SEP:-·}
  local -a parts
  [[ -n $g ]] && parts+=("$g")
  [[ -n $pj && ${(L)pj} != ${(L)g} ]] && parts+=("$pj")
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
        cargs[i+1]=$(_glyph_compose "$cargs[i+1]" "$proj")
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

  local mark=$(_glyph_compose "$given" "$proj")
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
    *) print -r -- "glyph ls [n]   recent sessions
glyph agents   installed agents and their auto-approve flags
glyph name [x] print the mark this directory would produce" ;;
  esac
}
