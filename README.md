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
migration·acme-api·agy·studio·2026-09-12·0602           ← Mac Studio
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

It matters most when panes stop being distinguishable: several agents at once,
or [tmux](https://github.com/tmux/tmux), [herdr](https://herdr.dev) and
[workmux](https://github.com/raine/workmux) grids where every pane is a
lookalike shell.

## Install

```sh
git clone https://github.com/fru-dev3/glyph.git
cd glyph && source ./install.sh
```

One file into `~/.config/glyph/`, one line into `~/.zshrc`. zsh and at least one
agent CLI.

`source` matters. Run as `./install.sh` it is a child process, and a child
cannot define functions in the shell that started it, so you would have to
reload before glyph exists. Sourcing installs and loads in one step. If you
already ran it the other way, `. ~/.config/glyph/glyph.zsh` catches you up.

## Usage

Keep typing the command you already type. The rule is the same everywhere:

> **one bare word is your label. anything with a space is a prompt.**

### Claude Code

Claude is the one agent that can name its own session, so the mark becomes the
real session name and rides Remote Control to your phone.

```sh
claude
# launches:  claude -n 'acme-api·claude-code·mbp·2026-09-12·0648' --remote-control

claude billing
# launches:  claude -n 'billing·acme-api·claude-code·mbp·2026-09-12·0648' --remote-control

claude billing "fix the webhook retry"
# launches:  claude -n 'billing·…' --remote-control 'fix the webhook retry'
```

Open claude.ai/code or the phone app and that name is what you see in the list.

### Antigravity

`agy` has no session-name flag, so the label does not go into the command at
all. It goes on the terminal title, the tmux window and `glyph ls`:

```sh
agy migration
# launches:  agy
# titles:    migration·acme-api·agy·mbp·2026-09-12·0648
```

`GLYPH_YOLO=1` is separate from naming. Every agent has a flag meaning "stop
asking me to approve each tool call", and they all spell it differently. This is
one switch that sends the right one:

```sh
GLYPH_YOLO=1 agy migration
# launches:  agy --dangerously-skip-permissions
# titles:    migration·acme-api·agy·mbp·2026-09-12·0648
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
# titles:    audit·acme-api·codex·mbp·2026-09-12·0648

GLYPH_YOLO=1 codex audit
# launches:  codex --dangerously-bypass-approvals-and-sandbox

codex "refactor auth"
# launches:  codex 'refactor auth'
# a phrase is a prompt, so only the project is marked
```

### A session that is already open

Glyph names a session from argv, so one you started without it never got a
name. `glyph mark` applies everything Glyph can still reach from outside the
agent, and prints the one line only the agent itself can run:

```sh
glyph mark hotfix
# hotfix·acme-api·claude-code·mbp·2026-09-12·2107
#   set the terminal title
#   renamed the Herdr pane
#   recorded it in glyph ls
#
# this Claude session is still called 'fru-3e'
#
# an agent can only rename itself. paste this into it:
#   /rename hotfix·acme-api·claude-code·mbp·2026-09-12·2107
#   /remote-control
```

It reports only the surfaces it actually reached. Remote Control cannot be
switched on from outside the session, but Claude Code can do it from inside with
`/remote-control`, so Glyph offers that line whenever the bridge is off.

Glyph reads the agent out of the environment, which today means Claude Code.
From a plain shell, or beside an agent it cannot detect, the agent field reads
`shell` rather than going missing; name it properly with `glyph mark <label>
<agent>` or `GLYPH_AGENT`. Either way the mark keeps its shape, which is what
lets `glyph ps` line them up in a column.

### Everything else

```sh
glyph ls        # recent sessions: when, agent, mark, machine
glyph ps        # every agent session alive right now, named or not
glyph usage     # quota and token counts across agents
glyph doctor    # check the install and say what is wrong
glyph mark x    # name a session that is already open
glyph agents    # what is installed, and each one's auto-approve flag
glyph name x    # print the mark this directory would produce
glyph fleet ci  # a preset of agents, each in its own marked pane
```

## Agents

| Agent | Carries the mark as | `GLYPH_YOLO=1` sends |
|---|:-:|---|
| Claude Code | ✔ real session name | `--dangerously-skip-permissions` |
| Antigravity (`agy`) | title | `--dangerously-skip-permissions` |
| Hermes | title | `--yolo` |
| omni | title | none |
| Codex | title | `--dangerously-bypass-approvals-and-sandbox` |
| Cursor | title | `--force` |
| Crush | title | `--yolo` |
| Cortex | title | `--dangerously-allow-all-tool-calls` |
| OpenCode | title | `--dangerously-skip-permissions` |
| pi | ✔ real session name | none |

Six agents, five spellings of *"stop asking me to approve every tool call"*.
`GLYPH_YOLO=1` sends whichever one is right. It is off unless you ask.

Tired of typing it? `export GLYPH_YOLO=1` in your `~/.zshrc` makes it the default
for every agent. That means every tool call runs without asking you, in every
project, which is exactly why glyph will not set it for you.

## Updating

```sh
glyph update   # fetch the latest glyph.zsh from GitHub, and load it here
glyph version
```

It loads the new file into the shell you ran it in, so there is nothing to
reload. Other shells you already have open keep the old one until `exec zsh`.

Refuses to install a file that does not parse, backs up the previous copy to
`~/.config/glyph/glyph.zsh.bak`, and never touches your config.

## Adding an agent

Any CLI, without waiting for a release. One tab-separated line per agent in
`~/.config/glyph/agents.tsv`:

```
openclaw	--yolo	OpenClaw
grok	--force	Grok
```

Columns are command, auto-approve flag, label. These merge over the built-ins,
so you can correct a flag too.

## Fleets

One preset launches several agents at once, each in its own marked pane:

```ini
# ~/.config/glyph/fleet.conf
solo   = claude                        # one agent, named
review = claude codex                  # two vendors on the same diff
duo    = claude agy                    # Anthropic and Google side by side
ci     = claude agy codex              # the three-up bench
bench  = claude codex agy cursor-agent # everything local
pair   = claude cursor-agent           # terminal agent + editor-native
deep   = claude cortex                 # coding agent + warehouse-native
light  = crush opencode                # cheap, quick passes
split  = claude codex:mini             # one local, one remote
spread = claude claude:mini            # same agent, two machines
cloud  = claude:mini codex:mini        # both on the remote box
```

```sh
glyph fleet init     # write the presets above, keeping any you already have
glyph presets        # list them
glyph fleet review   # launch one
```

Fleet on tmux is one session, one window, one tiled pane per slot. Glyph leaves
you in the first pane and turns the mouse on for that session so a click moves
between them (`ctrl-b o` and `ctrl-b` plus an arrow also work). Set
`GLYPH_FLEET_MOUSE=0` to leave the mouse alone.

### Usage and quota

```sh
glyph usage           # summary across agents
glyph usage codex     # both windows, plan, credits
glyph usage claude    # token counts for 5h and 7d
glyph usage --live    # the real percentages, from Anthropic
```

Codex writes its own rate limits to disk, so its 5h and weekly windows are
exact and offline. Claude does not: token counts come from your transcripts,
and the quota itself needs `--live`, which reads the Keychain token and asks
Anthropic. That is the only network request glyph makes besides `glyph update`.
AGY exposes nothing and is reported as such rather than guessed.

### Herdr plugin

Herdr shows which agents are running. It has no view of what is left to run
them with, so glyph ships one as a plugin:

```sh
herdr plugin install fru-dev3/glyph/herdr-plugin
```

An **Agent usage** pane with both Codex windows, Claude token counts and AGY
reported honestly as not exposed, plus an action to name the current pane.
Needs Herdr 0.7.4. See [herdr-plugin/](herdr-plugin/).

### Remote agents

A slot is `<agent>` or `<agent>:<machine>`. Glyph opens SSH in that pane, cds to
the same directory, and launches the agent through the remote wrapper so it gets
its own flags and its own mark.

`glyph hosts` lists everything you can put after the colon. A machine name
resolves in this order:

1. **SSH config**: a `Host` entry in `~/.ssh/config` always wins
2. **known_hosts**: a name SSH already trusts, so the pane never stalls on a
   fingerprint prompt
3. **Tailscale**: a short machine name is expanded to its MagicDNS name
4. **Literal**: anything else (`user@10.0.0.5`) goes to SSH untouched

Tailscale is optional and detected automatically. Accept a new host's key by
hand once (`ssh mini`) before using it in a fleet.

Remote slots work on **every** backend (Herdr, tmux, cmux, Zellij, WezTerm)
because they all build the same SSH command. Glyph is not tied to any one
workspace tool; with none running, Fleet falls back to tmux.

<details>
<summary><b>Configuration</b></summary>

| Variable | Effect |
|---|---|
| `GLYPH_YOLO=1` | Auto-approve tool calls, per-agent flag |
| `GLYPH_OFF=1` | Keep the label, drop the machine and time |
| `GLYPH_FMT` | `date(1)` format for the stamp (default `%Y-%m-%d·%H%M`) |
| `GLYPH_SEP` | Separator (default `·`) |
| `GLYPH_ORDER` | Field order (default `label project agent machine stamp`); naming fewer leaves the rest out |
| `GLYPH_MACHINE` | Machine tag, when the hostname does not map well |
| `GLYPH_AGENT` | Agent for the mark, when Glyph cannot tell which one owns the shell |
| `GLYPH_AGENT_FALLBACK` | What to call a shell no agent owns (default `shell`) |
| `GLYPH_FLEET_BACKEND` | `auto` (Herdr, cmux, Zellij, WezTerm, then tmux), or an explicit backend |
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
  the session. It comes back as `nameSource: "derived"`. Only `-n` sets it, so
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
