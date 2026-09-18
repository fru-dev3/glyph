# Glyph Usage, a Herdr plugin

Herdr tells you which agents are running. This tells you what is left to run
them with.

```
codex   plus   5h      ████████████████   98%  resets in 10m
codex   plus   weekly  █████░░░░░░░░░░░   31%  resets in 5d 20h
claude  -      5h/wk   quota is server side, add --live
agy     not exposed
```

## Install

Needs Herdr 0.7.4 or newer, and the [glyph](https://glyph.fru.dev) CLI, which
the plugin drives rather than reimplements.

```sh
git clone https://github.com/fru-dev3/glyph.git
cd glyph && source ./install.sh          # the CLI
herdr plugin install fru-dev3/glyph/herdr-plugin
```

## What it adds

| Surface | What it does |
|---|---|
| **Agent usage** pane | Both Codex windows with bars and reset times, Claude token counts, refreshed on a timer |
| **Glyph: agent usage** action | The same snapshot, printed once |
| **Glyph: new agent pane** action | Splits a pane and starts an agent through glyph, already named and already auto-approving |
| **Glyph: name this pane** action | Labels the pane `label·project·agent·machine·date·time` |

## Where the numbers come from

Nothing is guessed, and each agent is a different story:

- **Codex** writes its own rate limits to disk. Both the 5h and weekly windows
  are exact and offline.
- **Claude Code** does not. Token counts are read back out of your transcripts;
  the quota itself is decided server side, so `glyph usage --live` asks
  Anthropic for it. That is the only network request anything here makes.
- **AGY** exposes no quota at all, and is reported as `not exposed` rather than
  filled in with a plausible number.

## Trust

Two `/bin/sh` scripts and a manifest. No build step, nothing compiled, nothing
downloaded at install time. It shells out to `glyph`, which reads local agent
files under `~/.claude` and `~/.codex`. No telemetry.

Configure the refresh interval with `GLYPH_HERDR_INTERVAL` (seconds, default
60) and pass extra flags with `GLYPH_HERDR_ARGS`, for example `--live`.

## Auto-approve

Agents you start in a Herdr pane run in your login shell, so the glyph wrapper
already applies: they are named, and they get their own auto-approve flag when
`GLYPH_YOLO=1` is set. Herdr does not bypass any of that.

The **new agent pane** action forces `GLYPH_YOLO=1` for that pane specifically,
so you get it there without exporting it everywhere. Which agent it starts comes
from `agent` in the plugin config directory, and defaults to `claude`.

MIT, same as glyph.
