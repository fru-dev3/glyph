<img src="assets/glyph.svg" width="132" align="right" alt="Glyph">

# glyph

**One identity for every coding agent you run.**

Open your agent sessions on a phone, or list the tmux windows on a machine you
walked away from an hour ago, and you get this:

```
tims-macbook-pro-4-local-transient
fru-5e
doc-9b
zsh
```

Which machine? Which project? Started when? You cannot tell without opening each
one. Claude Code names a session from your first message or auto-derives one,
and most other agents do not name sessions at all.

`glyph` cuts one mark into every session before it starts:

```
billing·Acme API·mbp·2026-09-12·0556
```

Your label, the project, the machine, the moment. A glyph is an incised mark,
and the oldest thing anyone ever did with one was say *this is mine, and I was
here.*

## Install

```sh
git clone https://github.com/<you>/glyph.git
cd glyph && ./install.sh
exec zsh
```

zsh, and at least one agent CLI. The installer copies one file to
`~/.config/glyph/` and adds one line to `~/.zshrc`.

## Use

Nothing new to learn. Keep typing what you already type:

```sh
claude                    # Acme API·mbp·2026-09-12·0556
claude billing            # billing·Acme API·mbp·2026-09-12·0556
claude billing "fix X"    # same, and "fix X" is the first prompt
claude "fix the bug"      # a quoted phrase is a prompt, not a label
agy billing               # Antigravity, same mark on the window
codex billing             # Codex, same mark
```

A single bare word is your label. Anything with a space in it is a prompt.

```sh
glyph agents      # which agents are installed, and their auto-approve flags
glyph ls          # recent sessions: when, agent, mark, machine
glyph name deploy # print the mark this directory would produce
```

## Agents

Only Claude Code can name its own session, via `-n`. For every other agent the
glyph lands on the terminal title, the tmux window name, and the local registry,
so `glyph ls` and your window list stay readable regardless.

| Agent | Names session | Auto-approve flag `glyph` knows |
|---|---|---|
| Claude Code | yes (`-n` + `--remote-control`) | `--dangerously-skip-permissions` |
| Antigravity (`agy`) | title only | `--dangerously-skip-permissions` |
| Codex | title only | `--dangerously-bypass-approvals-and-sandbox` |
| Gemini CLI | title only | `--yolo` |
| Cursor (`cursor-agent`) | title only | `--force` |
| Crush | title only | `--yolo` |
| Cortex | title only | `--dangerously-allow-all-tool-calls` |
| OpenCode, pi | title only | — |

Wrappers are only defined for agents actually on your `PATH`.

Auto-approve is **off** by default. `GLYPH_YOLO=1` turns it on and each agent
gets its own correct flag, so you stop remembering which one spells it `--yolo`
and which spells it `--dangerously-bypass-approvals-and-sandbox`.

## Configuration

| Variable | Effect |
|---|---|
| `GLYPH_OFF=1` | Keep the label, drop the machine and time |
| `GLYPH_FMT` | `date(1)` format for the stamp (default `%Y-%m-%d·%H%M`) |
| `GLYPH_MACHINE` | Machine tag, when the hostname does not map well |
| `GLYPH_SEP` | Separator (default `·`) |
| `GLYPH_YOLO=1` | Auto-approve tool calls, per-agent flag |
| `GLYPH_RC=0` | Do not add Claude's `--remote-control` |
| `GLYPH_TITLE=0` | Do not retitle the terminal or tmux window |
| `GLYPH_LOG=0` | Do not record sessions locally |
| `GLYPH_DRYRUN=1` | Print the argv instead of launching |

The machine tag comes from `hostname -s`: a MacBook Pro becomes `mbp`, a Mac
mini `mini`, a MacBook Air `air`. Project names come from the git repo's
directory name, title-cased (`acme-api` → `Acme API`); override any of them in
`~/.config/glyph/names.tsv`, one `directory<TAB>Display Name` per line.

## What it leaves alone

`-p` / `--print`, and subcommands like `claude mcp`, `codex resume`, and
`opencode export`, pass through untouched, so scripts and CI behave exactly as
before. An explicit `--remote-control <name>` is respected as given.

`glyph` does not manage worktrees, panes, or fleets. It is an identity layer,
not a multiplexer, and it composes with whatever you already use.

## Why a shell wrapper and not a plugin

A session name has to exist before the process starts, so it can only come from
argv. Plugins and `SessionStart` hooks run after that point and cannot set it.

Two things that cost real debugging time, written down so they cost you none:

- Claude Code's `--remote-control <name>` opens the bridge but does **not** name
  the session. It comes back as `nameSource: "derived"` with an auto-generated
  name. Only `-n` sets it, so `glyph` passes both.
- In zsh, `argv` **is** `$@`. Declaring `local -a argv` inside a function
  silently empties the positional parameters and every argument disappears.

To see what a running Claude session is actually called, read
`~/.claude/sessions/<pid>.json` and look at `name` and `nameSource`. The startup
banner prints neither.

## License

MIT
