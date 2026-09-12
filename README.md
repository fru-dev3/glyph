<div align="center">

<img src="assets/glyph-512.png" width="150" alt="glyph">

# glyph

**Every agent session, named before it starts.**

`billing·Acme API·mbp·2026-09-12·0556`

[Install](#install) · [Usage](#usage) · [Agents](#agents) · [glyph.fru.dev](https://glyph.fru.dev)

</div>

---

You have four agent sessions open. This is your list:

```
tims-macbook-pro-4-local-transient
fru-5e
doc-9b
zsh
```

Which machine? Which project? Started when? You have to open each one to find
out. Claude Code names a session from your first message, and most other agents
never name one at all.

With glyph, the same four:

```
billing·Acme API·mbp·2026-09-12·0556
migration·Acme API·mini·2026-09-12·0602
docs·Website·mbp·2026-09-12·0611
review·Payments·mini·2026-09-11·2247
```

Label, project, machine, moment. Every agent, every machine, before the first
token.

## Install

```sh
git clone https://github.com/fru-dev3/glyph.git
cd glyph && ./install.sh && exec zsh
```

One file into `~/.config/glyph/`, one line into `~/.zshrc`. zsh and at least one
agent CLI.

## Usage

Nothing new to type. Keep using the command you already use:

```sh
claude                  # Acme API·mbp·2026-09-12·0556
claude billing          # billing·Acme API·mbp·2026-09-12·0556
claude billing "fix X"  # ...and "fix X" is the first prompt
claude "fix the bug"    # a quoted phrase is a prompt, not a label
agy billing             # Antigravity, same mark
codex billing           # Codex, same mark
```

One bare word is your label. Anything with a space is a prompt.

```sh
glyph ls        # recent sessions: when, agent, mark, machine
glyph agents    # what is installed, and each one's auto-approve flag
glyph fleet ci  # a preset of agents, each in its own marked pane
```

## Agents

Claude Code takes the mark as a real session name, so it reaches your phone
through Remote Control. Every other agent gets it on the terminal title, the
tmux window, and `glyph ls`.

| Agent | Session name | `GLYPH_YOLO=1` sends |
|---|:-:|---|
| Claude Code | ✔ | `--dangerously-skip-permissions` |
| Antigravity | title | `--dangerously-skip-permissions` |
| Codex | title | `--dangerously-bypass-approvals-and-sandbox` |
| Gemini CLI | title | `--yolo` |
| Cursor | title | `--force` |
| Crush | title | `--yolo` |
| Cortex | title | `--dangerously-allow-all-tool-calls` |
| OpenCode · pi | title | — |

Five agents, five spellings of the same idea. `GLYPH_YOLO=1` remembers them for
you. It is off unless you ask.

## Fleets

Open a whole bench at once, local or over ssh, each pane wearing the mark:

```ini
# ~/.config/glyph/fleet.conf
ci     = claude agy codex
review = claude claude:mini
```

```sh
glyph fleet review
```

<details>
<summary><b>Configuration</b></summary>

| Variable | Effect |
|---|---|
| `GLYPH_YOLO=1` | Auto-approve tool calls, per-agent flag |
| `GLYPH_OFF=1` | Keep the label, drop the machine and time |
| `GLYPH_FMT` | `date(1)` format for the stamp (default `%Y-%m-%d·%H%M`) |
| `GLYPH_SEP` | Separator (default `·`) |
| `GLYPH_MACHINE` | Machine tag, when the hostname does not map well |
| `GLYPH_RC=0` | Skip Claude's `--remote-control` |
| `GLYPH_TITLE=0` | Do not retitle the terminal or tmux window |
| `GLYPH_LOG=0` | Do not record sessions locally |
| `GLYPH_DRYRUN=1` | Print the argv instead of launching |

The machine tag comes from `hostname -s`: a MacBook Pro becomes `mbp`, a Mac
mini `mini`. Projects are the git repo's directory name, title-cased
(`acme-api` → `Acme API`); override either in `~/.config/glyph/names.tsv` as
`directory<TAB>Display Name`.

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

glyph is an identity layer, not a multiplexer. It launches panes and gets out of
the way — pair it with [workmux](https://github.com/raine/workmux) or plain tmux
for the rest.

</details>

## License

MIT
