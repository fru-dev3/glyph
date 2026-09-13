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
#
# Already inside a session you started without glyph? `glyph mark [label]`
# applies everything glyph can still reach: the terminal title, the tmux
# window, the registry. Only the agent can rename itself, so it also hands
# you the /rename line to paste.
#   GLYPH_FLEET_BACKEND=auto|herdr|cmux|zellij|wezterm|tmux   fleet workspace backend
#   ~/.config/glyph/names.tsv    "<dir-name>\t<Display Name>" overrides

# The version belongs to this file, not the environment: an in-place reload
# after `glyph update` must report the file it just loaded.
typeset -g GLYPH_VERSION=0.4.0
typeset -g GLYPH_STATE=${GLYPH_STATE:-${XDG_STATE_HOME:-$HOME/.local/state}/glyph}

# --- agent adapters ---------------------------------------------------------
# name|yolo flag|name flag|extra flags
# Only Claude Code can name its own session; for everyone else the glyph lands
# on the terminal title, the tmux window, and the registry.
typeset -gA GLYPH_YOLO_FLAG GLYPH_NAME_FLAG GLYPH_EXTRA GLYPH_LABEL
GLYPH_YOLO_FLAG=(
  claude       "--dangerously-skip-permissions"
  agy          "--dangerously-skip-permissions"
  codex        "--dangerously-bypass-approvals-and-sandbox"
  cursor-agent "--force"
  crush        "--yolo"
  cortex       "--dangerously-allow-all-tool-calls"
  hermes       "--yolo"
  opencode     ""
  pi           ""
  omni         ""
)

# Any agent not listed above can be declared in ~/.config/glyph/agents.tsv as
#   <command><TAB><auto-approve flag><TAB><label>
# so a new CLI works without waiting for a Glyph release. Blank flag is fine.
_glyph_load_extra_agents() {
  local f=${GLYPH_AGENTS:-$HOME/.config/glyph/agents.tsv} line cmd flag lbl
  [[ -r $f ]] || return 0
  while IFS=$'\t' read -r cmd flag lbl; do
    [[ -z $cmd || $cmd == \#* ]] && continue
    GLYPH_YOLO_FLAG[$cmd]=$flag
    [[ -n $lbl ]] && GLYPH_LABEL[$cmd]=$lbl
  done < "$f"
}
_glyph_load_extra_agents
GLYPH_NAME_FLAG=( claude "-n" )
GLYPH_LABEL=(
  claude "claude-code"  agy "agy"
  codex "codex"  cursor-agent "cursor"  crush "crush"
  cortex "cortex"  hermes "hermes"  omni "omni"  opencode "opencode"  pi "pi"
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

# Which agent owns this shell, when the agent says so in the environment.
# Only Claude Code is verified; pass the name explicitly for anything else.
_glyph_current_agent() {
  [[ -n ${CLAUDECODE:-} ]] && { print -r -- claude; return 0; }
  return 1
}

# The session file Claude Code keeps for this shell, if there is one.
_glyph_claude_session() {
  local pid=${CLAUDE_PID:-$PPID}
  [[ -n $pid && -r $HOME/.claude/sessions/$pid.json ]] || return 1
  print -r -- "$HOME/.claude/sessions/$pid.json"
}

# "name" out of that file, without needing jq.
_glyph_session_field() {
  command sed -n "s/.*\"$2\"[[:space:]]*:[[:space:]]*\"\\([^\"]*\\)\".*/\\1/p" "$1" 2>/dev/null | head -1
}

# Records what it actually reached in GLYPH_TITLE_DID, and returns 0 only if
# that is something. `glyph mark` reports exactly this and nothing more.
typeset -g GLYPH_TITLE_DID=""
_glyph_title() {
  GLYPH_TITLE_DID=""
  [[ ${GLYPH_TITLE:-1} == 1 ]] || return 1
  # Straight to the controlling terminal: the escape must not land in stdout,
  # where a pipe or a redirect would capture it as garbage. The subshell keeps
  # the "device not configured" error quiet when there is no terminal at all.
  ( printf '\033]2;%s\007\033]1;%s\007' "$1" "$1" > /dev/tty ) 2>/dev/null \
    && GLYPH_TITLE_DID="terminal"
  [[ -n ${TMUX:-} ]] && command tmux rename-window "$1" 2>/dev/null \
    && GLYPH_TITLE_DID="${GLYPH_TITLE_DID:+$GLYPH_TITLE_DID }tmux"
  [[ -n $GLYPH_TITLE_DID ]]
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
    mark)
      # Name a session that is already open. Sets everything glyph can still
      # reach from outside the agent, and prints the one line only the agent
      # itself can run.
      shift
      local mklabel=${1:-} mkagent=${2:-} mkmark mksf mkcur
      [[ -n $mkagent ]] || mkagent=$(_glyph_current_agent) || mkagent=""
      mkmark=$(_glyph_compose "$mklabel" "$(_glyph_project "$PWD")" "$mkagent")
      if [[ -n ${GLYPH_DRYRUN:-} ]]; then
        print -r -- "$mkmark"
        print -r -- "  dry run: nothing set, nothing recorded"
        return 0
      fi
      _glyph_title "$mkmark"
      print -r -- "$mkmark"
      [[ $GLYPH_TITLE_DID == *terminal* ]] && print -r -- "  set the terminal title"
      [[ $GLYPH_TITLE_DID == *tmux* ]]     && print -r -- "  renamed the tmux window"
      [[ -n ${TMUX:-} ]] && command tmux set-option -p @label "$mkmark" >/dev/null 2>&1
      _glyph_log "mark" "$mkmark"
      [[ ${GLYPH_LOG:-1} == 1 ]] && print -r -- "  recorded it in glyph ls"
      if mksf=$(_glyph_claude_session); then
        mkcur=$(_glyph_session_field "$mksf" name)
        print -r -- ""
        print -r -- "this Claude session is still called '${mkcur:-unnamed}'"
      fi
      print -r -- ""
      print -r -- "an agent can only rename itself. paste this into it:"
      print -r -- "  /rename $mkmark" ;;
    version) print -r -- "glyph ${GLYPH_VERSION}" ;;
    update)
      local dest=${XDG_CONFIG_HOME:-$HOME/.config}/glyph/glyph.zsh
      # Follow a symlink and write the file it points at. Installs that link
      # ~/.config/glyph/glyph.zsh into a synced folder must keep the link.
      [[ -L $dest ]] && dest=${dest:A}
      local url=${GLYPH_UPDATE_URL:-https://raw.githubusercontent.com/fru-dev3/glyph/main/glyph.zsh}
      local tmp=${TMPDIR:-/tmp}/glyph.update.$$
      print -r -- "fetching $url"
      if ! command curl -fsSL "$url" -o "$tmp"; then
        print -ru2 -- "glyph: download failed"; command rm -f "$tmp"; return 1
      fi
      if ! command zsh -n "$tmp" 2>/dev/null; then
        print -ru2 -- "glyph: refusing to install, the downloaded file does not parse"
        command rm -f "$tmp"; return 1
      fi
      if [[ -r $dest ]] && command cmp -s "$tmp" "$dest"; then
        command rm -f "$tmp"; print -r -- "already up to date (${GLYPH_VERSION})"; return 0
      fi
      command mkdir -p "${dest:h}"
      [[ -r $dest ]] && command cp "$dest" "$dest.bak"
      command mv "$tmp" "$dest" || return 1
      print -r -- "updated $dest"
      [[ -r $dest.bak ]] && print -r -- "previous version kept at $dest.bak"
      # Load the new file into this shell straight away. zsh has already copied
      # the body of the function we are running, so redefining it here is safe.
      if source "$dest" 2>/dev/null; then
        print -r -- "loaded in this shell, now ${GLYPH_VERSION}"
        print -r -- "other open shells keep the old one until you run: exec zsh"
      else
        print -ru2 -- "glyph: could not load the new file, reload with: exec zsh"
        return 1
      fi ;;
    hosts)
      local h line ts
      print -r -- "ssh config (~/.ssh/config)"
      for h in ${(f)"$(_glyph_ssh_hosts)"}; do printf '  %-22s %s\n' "$h" "ssh host"; done
      if ts=$(_glyph_tailscale_bin); then
        print -r -- "tailscale"
        for line in ${(f)"$(_glyph_tailscale_peers)"}; do
          printf '  %-22s %-38s %s\n' "${line%%$'\t'*}" "${${line#*$'\t'}%%$'\t'*}" "${line##*$'\t'}"
        done
      else
        print -r -- "tailscale: not detected"
      fi
      print -r -- "use any of these after a colon, e.g. glyph fleet cloud with codex:mini" ;;
    fleet) shift; glyph-fleet "$@" ;;
    presets)
      local conf=$(_glyph_fleet_conf)
      [[ -r $conf ]] && command grep -E "^[[:space:]]*[a-zA-Z0-9_-]+[[:space:]]*=" "$conf" \
        || print -r -- "no presets yet: write them to $conf" ;;
    *) print -r -- "glyph ls [n]   recent sessions
glyph agents   installed agents and their auto-approve flags
glyph name [x] print the mark this directory would produce
glyph mark [x] name a session that is already open, as far as glyph can reach
glyph fleet init create example fleets without replacing existing presets
glyph fleet [p] launch a preset of agents, each in its own marked tmux pane
glyph presets  list the presets in ~/.config/glyph/fleet.conf
glyph hosts    machines you can put after a colon in a fleet slot
glyph update   fetch the latest glyph.zsh from GitHub
glyph version  print the installed version" ;;
  esac
}

# --- remote slots -------------------------------------------------------------
# A slot may name a machine: <agent>:<host>. The host can be
#   * an ssh config Host entry        (Host mini ...)
#   * a Tailscale machine, short name (mini -> mini.tailnet.ts.net)
#   * any hostname, IP or user@host
# Resolution never guesses over an explicit ssh config entry.
_glyph_tailscale_bin() {
  local b
  # The macOS app bundle binary is tried first: a bare `tailscale` on PATH can be
  # a stub that aborts with a bundle-identifier error instead of printing status.
  for b in ${GLYPH_TAILSCALE:-} /Applications/Tailscale.app/Contents/MacOS/Tailscale \
           /opt/homebrew/bin/tailscale /usr/local/bin/tailscale tailscale; do
    [[ -n $b ]] || continue
    command -v "$b" >/dev/null 2>&1 || continue
    command "$b" status --json 2>/dev/null | command head -c 1 | command grep -q '{' \
      && { print -r -- "$b"; return 0 }
  done
  return 1
}

_glyph_ssh_hosts() {                      # Host entries from ~/.ssh/config
  local cfg=${GLYPH_SSH_CONFIG:-$HOME/.ssh/config}
  [[ -r $cfg ]] || return 0
  command awk 'tolower($1)=="host"{for(i=2;i<=NF;i++) if($i !~ /[*?]/) print $i}' "$cfg" 2>/dev/null
}

_glyph_tailscale_peers() {                # "<short>\t<magicdns>\t<online>"
  local ts; ts=$(_glyph_tailscale_bin) || return 0
  command "$ts" status --json 2>/dev/null | command python3 -c '
import sys,json
try: d=json.load(sys.stdin)
except Exception: raise SystemExit
def row(p):
    dns=(p.get("DNSName") or "").rstrip(".")
    if not dns: return
    print("\t".join([dns.split(".")[0],dns,"online" if p.get("Online") else "offline"]))
for p in (d.get("Peer") or {}).values(): row(p)
' 2>/dev/null
}

_glyph_known_hosts() {                    # names already trusted by ssh
  local kh=${GLYPH_KNOWN_HOSTS:-$HOME/.ssh/known_hosts}
  [[ -r $kh ]] || return 0
  command awk '{split($1,a,","); for(i in a){gsub(/\[|\]:[0-9]+/,"",a[i]); print a[i]}}' \
    "$kh" 2>/dev/null
}

_glyph_resolve_host() {                   # short name -> something ssh can dial
  local want=$1 host line
  [[ -n $want ]] || return 1
  # 1. an explicit ssh config Host always wins
  for host in ${(f)"$(_glyph_ssh_hosts)"}; do
    [[ $host == $want ]] && { print -r -- "$want"; return 0 }
  done
  # 2. a name ssh already trusts. Prefer it over MagicDNS: the tailnet FQDN is
  #    usually absent from known_hosts, and the pane would stall on the
  #    "continue connecting (yes/no)?" prompt.
  for host in ${(f)"$(_glyph_known_hosts)"}; do
    [[ $host == $want ]] && { print -r -- "$want"; return 0 }
  done
  # 3. a Tailscale machine, matched on the short name
  for line in ${(f)"$(_glyph_tailscale_peers)"}; do
    [[ ${line%%$'\t'*} == $want ]] && { print -r -- "${${line#*$'\t'}%%$'\t'*}"; return 0 }
  done
  # 4. take it literally: hostname, IP or user@host
  print -r -- "$want"
}

# The command a pane runs for one slot, local or remote. Every backend uses this
# so SSH is not tied to any one workspace tool.
_glyph_slot_command() {
  local agent=$1 machine=$2 preset=$3 target remote_script remote_cmd
  if [[ $machine == local ]]; then
    print -r -- "${agent} ${(q)preset}"
    return 0
  fi
  target=$(_glyph_resolve_host "$machine")
  # An interactive remote zsh loads the remote Glyph wrapper, which adds that
  # agent's own flags. Fall back to a login shell instead of closing the pane.
  remote_script="cd ${(q)PWD} 2>/dev/null; ${(q)agent} ${(q)preset} || exec \$SHELL -l"
  remote_cmd="zsh -ic ${(q)remote_script}"
  print -r -- "ssh -t ${(q)target} ${(q)remote_cmd}"
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
  line=${line#*=}
  print -r -- "${line%%\#*}"
}

_glyph_fleet_init() {
  emulate -L zsh
  local conf=$(_glyph_fleet_conf) preset body note added=0 wrote_header=0

  # name|slots|what it is for. Only presets whose agents you have installed will
  # launch; the rest are here as a starting point to edit.
  local -a examples=(
    'solo|claude|one agent, named. the everyday case'
    'review|claude codex|two vendors on the same diff, for a second opinion'
    'duo|claude agy|Anthropic and Google side by side'
    'ci|claude agy codex|the three-up bench: Claude, AGY, Codex'
    'bench|claude codex agy cursor-agent|everything local, one pane each'
    'pair|claude cursor-agent|a terminal agent beside an editor-native one'
    'deep|claude cortex|a coding agent next to a warehouse-native one'
    'light|crush opencode|lightweight runners for cheap, quick passes'
    'split|claude codex:studio|one local, one on a remote box'
    'spread|claude claude:studio|the same agent on two machines'
    'cloud|claude:studio codex:studio|both agents on the remote box'
  )

  if [[ -n ${GLYPH_DRYRUN:-} ]]; then
    print -r -- "would add up to $#examples presets to $conf:"
    for line in $examples; do
      printf '  %-11s %s\n' "${line%%|*}" "${${line#*|}%%|*}"
    done
    return 0
  fi

  command mkdir -p "${conf:h}" || return 1
  command touch "$conf" || return 1
  if [[ ! -s $conf ]]; then
    printf '%s\n%s\n' '# glyph fleets: <name> = <agent>[:<ssh-host>] ...' \
                       '# launch one with: glyph fleet <name>' >> "$conf" || return 1
    wrote_header=1
  fi

  local line
  for line in $examples; do
    preset=${line%%|*}
    body=${${line#*|}%%|*}
    note=${line##*|}
    if ! command grep -qE "^[[:space:]]*${preset}[[:space:]]*=" "$conf"; then
      printf '\n# %s\n%s = %s\n' "$note" "$preset" "$body" >> "$conf" || return 1
      (( added += 1 ))
    fi
  done

  print -r -- "fleet config: $conf ($added presets added; existing definitions kept)"
  print -r -- "see them all:  glyph presets"
  print -r -- "start one:     glyph fleet review"
  print -r -- "presets with a host after ':' (split, spread, cloud) are examples -"
  print -r -- "replace 'studio' with one of your own SSH hosts before using them."
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
  local slot agent machine label tab_output tab_id pane_id command_text plist entry
  for slot in "$@"; do
    agent=${slot%%:*}; machine=${slot#*:}
    [[ $machine == $slot ]] && machine=local
    label="${GLYPH_LABEL[$agent]:-$agent} · $mark"
    [[ $machine == local ]] || label="${GLYPH_LABEL[$agent]:-$agent} @$machine · $mark"
    if [[ -n ${GLYPH_DRYRUN:-} ]]; then
      print -r -- "herdr tab  $label  ($agent $preset)"
      continue
    fi

    tab_output=$(command herdr tab create --cwd "$PWD" --label "$label" --no-focus 2>/dev/null) || return 1
    tab_id=$(print -r -- "$tab_output" | command sed -n 's/.*"tab_id":"\([^"]*\)".*/\1/p')
    [[ -n $tab_id ]] || { print -ru2 -- 'glyph: could not read Herdr tab id'; return 1; }

    # A fresh Herdr tab already owns one shell pane. Run the agent IN that pane.
    # `herdr agent start --tab` would add a second pane, leaving every tab with
    # an idle shell sitting next to the agent.
    plist=$(command herdr pane list 2>/dev/null) || return 1
    pane_id=""
    plist=${plist//\},\{/$'\n'}
    for entry in ${(f)plist}; do
      if [[ $entry == *"\"tab_id\":\"$tab_id\""* ]]; then
        pane_id=${${entry##*\"pane_id\":\"}%%\"*}
        break
      fi
    done
    [[ -n $pane_id ]] || { print -ru2 -- "glyph: could not find the pane for Herdr tab $tab_id"; return 1; }

    command_text=$(_glyph_slot_command "$agent" "$machine" "$preset")
    command herdr pane run "$pane_id" "$command_text" >/dev/null || return 1
  done
}

_glyph_fleet_cmux() {
  local preset=$1 mark=$2; shift 2
  command -v cmux >/dev/null 2>&1 || { print -ru2 -- 'glyph: cmux backend needs cmux'; return 1; }
  local slot agent machine label command_text
  for slot in "$@"; do
    agent=${slot%%:*}; machine=${slot#*:}
    [[ $machine == $slot ]] && machine=local
    [[ $machine == local ]] || label="$label @$machine"
    label="${GLYPH_LABEL[$agent]:-$agent} · $mark"
    command_text="zsh -lic ${(q)$(_glyph_slot_command "$agent" "$machine" "$preset")}"
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
    [[ $machine == local ]] || label="$label @$machine"
    label="${GLYPH_LABEL[$agent]:-$agent} · $mark"
    command_text=$(_glyph_slot_command "$agent" "$machine" "$preset")
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
    [[ $machine == local ]] || label="$label @$machine"
    label="${GLYPH_LABEL[$agent]:-$agent} · $mark"
    command_text=$(_glyph_slot_command "$agent" "$machine" "$preset")
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
    [[ $machine == local ]] || label="$label @$machine"
    cmd=$(_glyph_slot_command "$agent" "$machine" "$preset")
    command tmux set-option -p -t "$panes[i]" @label "$label · $mark" >/dev/null 2>&1
    command tmux send-keys -t "$panes[i]" "$cmd" C-m
  done

  _glyph_log "fleet:$preset" "$mark"
  if [[ -n ${TMUX:-} ]]; then command tmux switch-client -t "$session"
  else command tmux attach -t "$session"; fi
}
