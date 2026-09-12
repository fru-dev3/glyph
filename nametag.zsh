# claude-nametag - readable names for Claude Code Remote Control sessions.
#
# Wraps `claude` so every interactive session is named before it starts:
#
#   <given>·<project>·<machine>·<date>·<time>
#
#   claude                  Acme API·mbp·2026-09-12·0556
#   claude billing          billing·Acme API·mbp·2026-09-12·0556
#   claude billing "fix X"  same, and "fix X" is the first prompt
#   claude -n billing       same - an explicit -n is stamped too
#
# Why a shell wrapper and not a plugin: the name has to exist before the
# process starts, so SessionStart hooks are too late. Only argv can do it.
#
# Knobs (all optional):
#   NAMETAG_OFF=1        pass names through untouched
#   NAMETAG_FMT          date(1) format for the stamp (default %Y-%m-%d·%H%M)
#   NAMETAG_MACHINE      machine tag, when the hostname does not map well
#   NAMETAG_SEP          separator (default ·)
#   NAMETAG_RC=0         do not add --remote-control
#   NAMETAG_YOLO=1       add --dangerously-skip-permissions (off by default)
#   NAMETAG_DRYRUN=1     print the argv instead of launching
#   ~/.config/nametag/names.tsv    "<dir-name>\t<Display Name>" overrides

# mymachine-MacBook-Pro -> mbp, work-Mac-mini -> mini, air -> air
_nametag_machine() {
  local h=${NAMETAG_MACHINE:-}
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

# Display name for the project containing $PWD: override map, else the git
# repo's directory name, title-cased. Empty when not in a repo.
_nametag_project() {
  local dir=${1:-$PWD} root slug line
  root=$(command git -C "$dir" rev-parse --show-toplevel 2>/dev/null) || return 0
  slug=${root:t}
  local map=${NAMETAG_MAP:-$HOME/.config/nametag/names.tsv}
  if [[ -r $map ]]; then
    line=$(command grep -m1 -E "^${slug}"$'\t' "$map" 2>/dev/null)
    [[ -n $line ]] && { print -r -- "${line#*$'\t'}"; return 0; }
  fi
  local base=${slug//[-_]/ } w
  local -a out
  for w in ${=base}; do
    case ${(L)w} in
      cli|api|mcp|ai|ui|os|db|sdk|ios|tv) out+=( ${(U)w} ) ;;
      *) out+=( "${(C)w}" ) ;;
    esac
  done
  print -r -- "${(j: :)out}"
}

claude() {
  emulate -L zsh
  local sep=${NAMETAG_SEP:-·}
  local -a pre
  local given="" proj=""

  _nametag_run() {                 # one launch point, so DRYRUN always applies
    if [[ -n ${NAMETAG_DRYRUN:-} ]]; then print -r -- claude ${(q-)@}; return 0; fi
    command claude "$@"
  }

  _nametag_compose() {
    local g=$1 pj=$2
    local -a parts
    [[ -n $g ]] && parts+=("$g")
    [[ -n $pj && ${(L)pj} != ${(L)g} ]] && parts+=("$pj")
    if [[ -z ${NAMETAG_OFF:-} ]]; then
      parts+=("$(_nametag_machine)")
      parts+=("$(command date +${NAMETAG_FMT:-%Y-%m-%d${sep}%H%M})")
    fi
    print -r -- "${(pj:$sep:)parts}"
  }

  # Subcommands manage the install; never decorate them.
  case ${1:-} in
    mcp|auth|plugin|plugins|install|update|upgrade|doctor|agents|project|setup-token|daemon|import|config|migrate-installer)
      _nametag_run "$@"; return ;;
  esac

  # Non-interactive runs pass straight through.
  if [[ " $* " == *" -p "* || " $* " == *" --print "* ]]; then
    _nametag_run "$@"; return
  fi

  if [[ -n ${NAMETAG_YOLO:-} \
     && " $* " != *" --dangerously-skip-permissions "* \
     && " $* " != *" --permission-mode "* ]]; then
    pre+=(--dangerously-skip-permissions)
  fi

  proj=$(_nametag_project "$PWD")

  # An explicit -n / --name: stamp the value in place.
  # NB: never call this array `argv` - in zsh that name IS $@, and declaring it
  # local silently empties the positional parameters.
  local -a cargs; cargs=("$@")
  local i
  for (( i = 1; i <= $#cargs; i++ )); do
    if [[ $cargs[i] == (-n|--name) && -n ${cargs[i+1]:-} ]]; then
      cargs[i+1]=$(_nametag_compose "$cargs[i+1]" "$proj")
      [[ ${NAMETAG_RC:-1} == 1 && " $* " != *" --remote-control "* && " $* " != *" --rc "* ]] \
        && pre+=(--remote-control)
      _nametag_run $pre "${cargs[@]}"; return
    fi
  done

  # An explicit RC flag already carries its own name.
  if [[ " $* " == *" --remote-control "* || " $* " == *" --rc "* ]]; then
    _nametag_run $pre "$@"; return
  fi

  # A bare first argument is the session name.
  if [[ -n ${1:-} && ${1:-} != -* ]]; then given=$1; shift; fi

  local name=$(_nametag_compose "$given" "$proj")
  [[ -n $name ]] && pre+=(-n "$name")
  [[ ${NAMETAG_RC:-1} == 1 ]] && pre+=(--remote-control)

  _nametag_run $pre "$@"
}
