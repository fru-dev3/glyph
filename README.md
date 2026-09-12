<div align="center">

<img src="assets/glyph-512.png" width="150" alt="glyph">

# glyph

**Every agent session, named before it starts.**

`billing·acme-api·claude-code·mbp·2026-09-12·0556`

[![stars](https://img.shields.io/github/stars/fru-dev3/glyph?style=flat&label=stars&color=C4A35A&labelColor=1c1712)](https://github.com/fru-dev3/glyph/stargazers)
[![license](https://img.shields.io/badge/license-MIT-C4A35A?style=flat&labelColor=1c1712)](LICENSE)

[Install](#install) · [Usage](#usage) · [Fleets](#fleets) · [glyph.fru.dev](https://glyph.fru.dev)

</div>

---

**Why now:** a year ago you ran one assistant in one terminal. Now agents run in
parallel, on machines you are not sitting at, and answer permission prompts on
your phone. Identity stopped being cosmetic.

Without a name, five running agents look like this:

```
rivers-macbook-pro-4-local-transient ← Claude Code, auto-derived
agent-5e                             ← Claude Code, auto-derived
doc-9b                               ← Claude Code, a different machine
zsh                                  ← Codex. no session name at all
node                                 ← Antigravity. same
```

- Two are the same project. You cannot tell which two.
- One is on a machine you are not sitting at.
- One has been idle since yesterday.
- Two are not named at all, because their agent has no such concept.

Turn glyph on and the same five read:

```
billing·acme-api·claude-code·laptop·2026-09-12·0556     ← MacBook Pro
migration·acme-api·agi·studio·2026-09-12·0602           ← Mac Studio
docs·website·codex·mini·2026-09-12·0611                ← Mac mini
audit·payments·claude-code·windows·2026-09-11·2247      ← Windows box, via WSL
scrape·atlas·codex·hetzner·2026-09-12·0640              ← cloud server
```

Label · project · agent · machine · date · time. Every field is lowercase; hyphens join words, and `·` separates fields. Every agent, every machine, set before
the first token.

**You could do this by hand.** Rename a Claude session with `/rename`, or
long-press it in the mobile app. glyph's argument is only that it happens
automatically:

- at launch, so a session is never briefly nameless
- on every agent, not just the one that supports naming
- on every machine, with the machine baked into the name
- with no step to forget and nothing to tidy up afterwards

It matters most when panes stop being distinguishable — several agents at once,
or [tmux](https://github.com/tmux/tmux), [herdr](https://herdr.dev) and
[workmux](https://github.com/raine/workmux) grids where every pane is a
lookalike shell.

## Install

```sh
git clone https://github.com/fru-dev3/glyph.git
cd glyph && ./install.sh && exec zsh
```

One file into `~/.config/glyph/`, one line into `~/.zshrc`. zsh and at least one
agent CLI.

## Usage

Keep typing the command you already type. The rule is the same everywhere:

> **one bare word is your label. anything with a space is a prompt.**

### Claude Code

Claude is the one agent that can name its own session, so the mark becomes the
real session name and rides Remote Control to your phone.

```sh
claude
# launches:  claude -n 'Acme API·mbp·2026-09-12·0648' --remote-control

claude billing
# launches:  claude -n 'billing·acme-api·claude-code·mbp·2026-09-12·0648' --remote-control

claude billing "fix the webhook retry"
# launches:  claude -n 'billing·…' --remote-control 'fix the webhook retry'
```

Open claude.ai/code or the phone app and that name is what you see in the list.

### Antigravity

`agy` has no session-name flag, so the label does not go into the command at
all — it goes on the terminal title, the tmux window and `glyph ls`:

```sh
agy migration
# launches:  agy
# titles:    migration·Acme API·mbp·2026-09-12·0648
```

`GLYPH_YOLO=1` is separate from naming. Every agent has a flag meaning "stop
asking me to approve each tool call", and they all spell it differently. This is
one switch that sends the right one:

```sh
GLYPH_YOLO=1 agy migration
# launches:  agy --dangerously-skip-permissions
# titles:    migration·Acme API·mbp·2026-09-12·0648
```

AGY requires an explicit flag for interactive prompts. Glyph supplies it:

```sh
agy billing "fix the retry"
# launches: agy --prompt-interactive 'fix the retry'
```

If `agy billing` reports an unexpected argument, the terminal may still have
an older wrapper loaded. Run `exec zsh` to reload the installed Glyph wrapper.
The mark appears in the terminal/tmux title and `glyph ls`, not AGY's app banner
or conversation name. Agents may overwrite terminal titles after launch; Fleet
keeps its own pane-border labels.

### Codex

Same shape, different spelling of the same flag:

```sh
codex audit
# launches:  codex
# titles:    audit·Acme API·mbp·2026-09-12·0648

GLYPH_YOLO=1 codex audit
# launches:  codex --dangerously-bypass-approvals-and-sandbox

codex "refactor auth"
# launches:  codex 'refactor auth'
# a phrase is a prompt, so only the project is marked
```

### Everything else

```sh
glyph ls        # recent sessions: when, agent, mark, machine
glyph agents    # what is installed, and each one's auto-approve flag
glyph name x    # print the mark this directory would produce
glyph fleet ci  # a preset of agents, each in its own marked pane
```

## Agents

| Agent | Carries the mark as | `GLYPH_YOLO=1` sends |
|---|:-:|---|
| Claude Code | ✔ real session name | `--dangerously-skip-permissions` |
| Antigravity | title | `--dangerously-skip-permissions` |
| Codex | title | `--dangerously-bypass-approvals-and-sandbox` |
| Gemini CLI | title | `--yolo` |
| Cursor | title | `--force` |
| Crush | title | `--yolo` |
| Cortex | title | `--dangerously-allow-all-tool-calls` |
| OpenCode · pi | title | — |

Six agents, five spellings of *"stop asking me to approve every tool call"*.
`GLYPH_YOLO=1` sends whichever one is right. It is off unless you ask.

## Fleets

Set up example fleets with one command (existing definitions are kept):

```sh
glyph fleet init
```

Then run `glyph fleet ci` from your project folder. Fleet uses the current
workspace automatically: Herdr creates one Herdr tab per local agent, cmux
creates one cmux workspace per local agent, and standalone shells use tmux.
Set `GLYPH_FLEET_BACKEND=tmux|herdr|cmux` to choose explicitly. Fleet needs
the selected workspace manager and the agent CLIs installed. Customize the
generated config when needed:

```ini
# ~/.config/glyph/fleet.conf
ci      = claude agy codex
review  = claude claude:studio
cloud   = claude:hetzner codex:hetzner
```

```sh
glyph fleet review
```

- A slot is `<agent>` or `<agent>:<ssh-host>`.
- The part after `:` is an **ssh host**, not the machine tag — the tag is
  whatever that machine reports for itself.
- Remote panes require Glyph and the agent installed on the SSH host, with
  Glyph sourced in its zsh config. They `cd` to the same project path and stop
  if that path is missing.
- Herdr and cmux backends support local slots. Use the tmux backend for
  `<agent>:<ssh-host>` slots.

<details>
<summary><b>Configuration</b></summary>

| Variable | Effect |
|---|---|
| `GLYPH_YOLO=1` | Auto-approve tool calls, per-agent flag |
| `GLYPH_OFF=1` | Keep the label, drop the machine and time |
| `GLYPH_FMT` | `date(1)` format for the stamp (default `%Y-%m-%d·%H%M`) |
| `GLYPH_SEP` | Separator (default `·`) |
| `GLYPH_MACHINE` | Machine tag, when the hostname does not map well |
| `GLYPH_FLEET_BACKEND` | `auto` (Herdr, cmux, then tmux), or explicit `herdr`, `cmux`, `tmux` |
| `GLYPH_RC=0` | Skip Claude's `--remote-control` |
| `GLYPH_TITLE=0` | Do not retitle the terminal or tmux window |
| `GLYPH_LOG=0` | Do not record sessions locally |
| `GLYPH_DRYRUN=1` | Print the argv instead of launching |

**Machine tags** come from the system computer name when available. On macOS,
Glyph reads `scutil --get ComputerName`; Windows/WSL and Linux use the system
hostname. Every result is normalized to lowercase hyphenated form:

| System computer name | Tag |
|---|---|
| `Rivers MacBook Pro` | `rivers-macbook-pro` |
| `Studio Air` | `studio-air` |
| `DESKTOP-8KQ2LM1` | `desktop-8kq2lm1` |
| `ubuntu-prod-01` | `ubuntu-prod-01` |
| `hetzner-cx41` | `hetzner-cx41` |

Glyph does not guess a model or operating-system release. If the computer name
is missing or generic, or if you need a tablet/device role, set the tag yourself:

```sh
export GLYPH_MACHINE=windows-10   # or ipad, ubuntu-gpu, prod, laptop…
```

**Project names** are lowercase git repo directory tokens (`acme-api` stays
`acme-api`; `Acme API` becomes `acme-api`). Overrides in
`~/.config/glyph/names.tsv` are normalized the same way.

`-p` / `--print` and subcommands (`claude mcp`, `codex resume`) pass through
untouched, so scripts and CI behave exactly as before.

</details>

<details>
<summary><b>Why a shell wrapper and not a plugin</b></summary>

A session name has to exist before the process starts, so it can only come from
argv. Plugins and `SessionStart` hooks run after that and cannot set it.

Two things that cost real debugging time:

- Claude Code's `--remote-control <name>` opens the bridge but does **not** name
  the session — it comes back as `nameSource: "derived"`. Only `-n` sets it, so
  glyph passes both. To see a session's real name, read
  `~/.claude/sessions/<pid>.json`; the startup banner shows neither.
- In zsh, `argv` **is** `$@`. Declaring `local -a argv` in a function silently
  empties the positional parameters.

glyph is an identity layer, not a multiplexer. Herdr is the recommended outer
workspace when you use it every day: launch `claude`, `codex`, or `agy` inside
an existing Herdr tab and Glyph labels that tab. `glyph fleet` currently creates
a standalone tmux session, so running it inside Herdr creates nested tmux. Use
Fleet outside Herdr, or keep using separate Herdr tabs until a native Herdr Fleet
backend is added.

</details>

## License

MIT
