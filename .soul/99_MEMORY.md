# Glyph project memory

## 2026-09-12

- Website: original app icons, three primary demo choices (Codex, AGI, Claude),
  all nine adapters restored as cards, visual before/after comparison, stronger
  demo headings, install and generator copy buttons, Fleet setup/config/preview/
  launch examples, and expandable settings with explanations.
- AGI is the requested website display label; its CLI command stays `agy`.
- AGY/Codex demo output says Terminal label. Glyph does not rename their internal
  conversations or app banners. An agent can overwrite OSC titles after launch;
  Fleet uses persistent tmux pane-border labels.
- AGY positional prompts now use --prompt-interactive. AGY management commands
  pass through. A stale _yolo_wrap in an old shell explains `agy billing` errors;
  fresh shells use Glyph. Updated the installed wrapper, keeping Fru's existing
  personal loader and project naming override.
- Fleet passes a short preset label, not the complete mark (which could become
  a prompt when the project name contains spaces). SSH uses interactive zsh to
  load Glyph and requires the matching project directory to exist.
- Validation: `zsh tests/smoke.zsh`, installed AGY help/parser check, installed
  wrapper dry runs, and local Chrome desktop/mobile checks for all copy controls,
  quoting, settings, nine cards and image loading. No live SSH agent sessions
  or paid model prompts were run. Gemini CLI is not installed on this machine.
- Existing website metadata/header/logo work was preserved. No deploy run.
