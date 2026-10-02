# glyph: instructions for coding agents

## This repository is public

Everything committed here is published at github.com/fru-dev3/glyph, history
included. Commit nothing about any one person's setup:

- no machine names, hostnames, usernames, home paths or IP addresses
- no real session names, workspace or tab names, or account tags
- no personal notes, task logs or project memory
- no layouts: `machines.json` and `spaces/*.json` belong in
  `~/.config/glyph/spaces/`, never here

The same goes for commit messages. Examples use made-up names: `acme-api`,
`laptop`, `studio`, `mini`, `sam.lee4@example.com`.

A maintainer's own setup stays outside the repo and is linked in locally.
`.soul/` (project notes) is git-ignored for that reason; read it if it is
there, and never add it.

If a hook stops a commit or a push for personal details, take them out. Never
pass `--no-verify` to get past it.

## Layout

- `glyph.zsh`: the whole shell tool, one file, installed by `install.sh` and
  `glyph update`
- `spaces/`: `glyph spaces`, in Python. `core.py` names no terminal tool;
  everything that talks to one is in `backends/<tool>.py`
- `tests/smoke.zsh`: run `zsh tests/smoke.zsh` before calling a change done
- `docs/`: the site at glyph.fru.dev
- `GEMINI.md`: context for the Gemini extension, not instructions for you
