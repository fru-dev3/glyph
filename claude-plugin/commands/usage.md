---
description: Quota and token usage across Claude Code, Codex and AGY
---

Run `glyph usage` and show the result.

Report each agent honestly and do not blend them:

- Codex rate limits are exact and come straight off disk, including both the 5h
  and weekly windows with their reset times.
- Claude token counts come from local transcripts and are NOT billing figures.
  The quota itself is server side; `glyph usage --live` fetches it.
- AGY exposes no quota at all. Say "not exposed" rather than estimating.

If the user asks about a single agent, run `glyph usage claude`, `glyph usage
codex` or `glyph usage agy` for the detail view instead.
