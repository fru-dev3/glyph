<div align="center">

<img src="assets/glyph-512.png" width="150" alt="glyph">

# glyph

**Every agent session, named before it starts.**

`billing·Acme API·mbp·2026-09-12·0556`

[Install](#install) · [Usage](#usage) · [Fleets](#fleets) · [glyph.fru.dev](https://glyph.fru.dev)

</div>

---

Five agents, five machines. This is what you come back to:

```
tims-macbook-pro-4-local-transient   ← Claude Code, auto-derived
fru-5e                               ← Claude Code, auto-derived
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
billing·Acme API·mbp·2026-09-12·0556        ← MacBook Pro
migration·Acme API·air·2026-09-12·0602      ← MacBook Air
docs·Website·mini·2026-09-12·0611           ← Mac mini
audit·Payments·win·2026-09-11·2247          ← Windows box, via WSL
scrape·Atlas·hetzner·2026-09-12·0640        ← cloud server
```

Label · project · machine · date · time. Every agent, every machine, set before
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
# → claude -n 'Acme API·mbp·2026-09-12·0648' --remote-control

claude billing
# → claude -n 'billing·Acme API·mbp·2026-09-12·0648' --remote-control

claude billing "fix the webhook retry"
# → claude -n 'billing·…·0648' --remote-control 'fix the webhook retry'
```

Open claude.ai/code or the phone app and that name is what you see in the list.

### Antigravity

`agy` has no session-name flag, so the mark goes on the terminal title, the tmux
window, and `glyph ls`.

```sh
agy migration
# → agy                      window + title: migration·Acme API·mbp·2026-09-12·0648

GLYPH_YOLO=1 agy migration
# → agy --dangerously-skip-permissions
```

### Codex

Same as Antigravity — title, tmux window and registry:

```sh
codex audit
# → codex                    window + title: audit·Acme API·mbp·2026-09-12·0648

codex "refactor auth"
# → codex 'refactor auth'    a phrase is a prompt, so only the project is marked

GLYPH_YOLO=1 codex audit
# → codex --dangerously-bypass-approvals-and-sandbox
```

### Everything else

```sh
glyph ls        # recent sessions: when, agent, mark, machine
glyph agents    # what is installed, and each one's auto-approve flag
glyph name x    # print the mark this directory would produce
glyph fleet ci  # a preset of agents, each in its own marked pane
```

## Agents

| Agent | Session name | `GLYPH_YOLO=1` sends |
|---|:-:|---|
| Claude Code | ✔ real name | `--dangerously-skip-permissions` |
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

Open a whole bench at once, each pane wearing the mark on its border:

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
- Remote panes `cd` to the same path, and fall back to a login shell if the
  agent is not installed there.

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

**Machine tags** come from `hostname -s`:

| Hostname | Tag |
|---|---|
| `laptop` | `mbp` |
| `air` | `air` |
| `Mac-mini` | `mini` |
| `Mac-Studio` | `studio` |
| `DESKTOP-8KQ2LM1` (Windows/WSL) | `desktop` |
| `ubuntu-prod-01` (cloud) | `ubuntu` |
| `hetzner-cx41` | `hetzner` |

Macs are recognised by model. Everything else takes the first word of the
hostname. When that is unhelpful — a Windows box called `DESKTOP-8KQ2LM1`, or a
fleet of identically-named cloud instances — name it yourself:

```sh
export GLYPH_MACHINE=win      # or ec2, gpu, prod, laptop…
```

**Project names** are the git repo's directory, title-cased (`acme-api` →
`Acme API`). Override in `~/.config/glyph/names.tsv` as
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
the way — pair it with workmux, herdr or plain tmux for the rest.

</details>

## License

MIT
