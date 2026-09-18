---
name: glyph-sessions
description: Use when the user asks which agent sessions are running, what a session is called, how much quota or token budget is left, or when a usage window resets. Covers Claude Code, Codex and AGY through the glyph CLI.
---

# Agent sessions and quota, via glyph

`glyph` is a zsh CLI that names agent sessions and reads local agent state. Use it
instead of guessing, and instead of reading `~/.claude` or `~/.codex` by hand.

## What to run

| Question | Command |
|---|---|
| What is running right now? | `glyph ps` |
| How much quota is left? | `glyph usage` |
| Detail for one agent | `glyph usage claude` / `codex` / `agy` |
| The real Claude quota | `glyph usage --live` |
| What would this session be called? | `glyph name` |
| Name a session already open | `glyph mark <label>` |
| Is the install healthy? | `glyph doctor` |
| Machine-readable | `glyph usage --json` |

## Reading the output honestly

Each agent exposes a different amount, and the difference matters:

- **Codex** writes its own rate limits to disk. Percentages, window lengths and
  reset times are exact and need no network.
- **Claude Code** does not persist quota. Token counts come from transcripts and
  are what was recorded locally, not what the plan is billed for. Only `--live`
  returns real percentages.
- **AGY** exposes nothing. Report "not exposed"; never estimate it.

A first `glyph usage` after a while can take several seconds because it scans
transcripts; the result is cached for ten minutes. `--refresh` forces a rescan.

## Naming

A glyph name is `label·project·agent·machine·date·time`, all lowercase. In
`glyph ps`, the NAMED column says where a name came from: `glyph` means it has
that shape, `user` means someone set it by hand, `auto` means the agent derived
it. RC shows whether Remote Control is on, which is what decides if a session is
reachable from the web app or a phone.

Only the agent can rename itself, so `glyph mark` prints a `/rename` line to
paste. `glyph mark <label> --send` types it into the pane for you, and only works
from inside an agent session.

## If glyph is missing

Do not fall back to parsing agent files directly. Say it is not installed and
point at <https://glyph.fru.dev>.
