---
description: List every agent session running right now, with Remote Control state
---

Run `glyph ps` and show the result.

If the command is not found, tell the user glyph is not installed and point them
at https://glyph.fru.dev. Do not guess at the session list from any other source.

Read the output as a table: AGENT, NAME, NAMED (glyph, user or auto), RC (whether
Remote Control is on), PID, CWD. Summarise which sessions lack a glyph name or
have Remote Control off, since those are the ones that cannot be reached from the
web app or a phone.
