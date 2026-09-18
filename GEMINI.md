# glyph

`glyph` is a zsh CLI that gives agent sessions a readable identity and reads
local agent state. When the user asks what is running, what a session is called,
or how much quota is left, run it rather than guessing or parsing agent files by
hand.

| Question | Command |
|---|---|
| What is running right now? | `glyph ps` |
| How much quota is left? | `glyph usage` |
| Detail for one agent | `glyph usage codex` |
| What would this session be called? | `glyph name` |
| Name a session already open | `glyph mark <label>` |
| Is the install healthy? | `glyph doctor` |
| Machine-readable | `glyph usage --json` |

A name is `label·project·agent·machine·date·time`, all lowercase.

Report each agent's quota honestly, because they differ:

- **Codex** writes its own rate limits to disk. Exact, offline, both the 5h and
  weekly windows with reset times.
- **Claude Code** does not persist quota. Token counts come from transcripts and
  are not billing figures; only `glyph usage --live` returns real percentages.
- **AGY** exposes no quota. Say "not exposed" rather than estimating it.

Auto-approve is separate from naming. `GLYPH_YOLO=1` sends each agent's own
"stop asking me to approve every tool call" flag, and is off unless the user
asks for it.

If `glyph` is not installed, say so and point at <https://glyph.fru.dev>.
