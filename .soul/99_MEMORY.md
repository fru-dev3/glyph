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

- Hosting verified: glyph.fru.dev points to GitHub Pages, which publishes main's
  /docs automatically on push. netlify.toml is not the active hosting setup.
  Fru explicitly authorized deployment in this session. HTTPS certificate was
  not provisioned when checked; the HTTP site served the committed page.
- Simplified the opening: one logo with wordmark in the header, removed the
  duplicate hero logo, and moved creator attribution to the footer. Checked
  desktop and 375/320px mobile layouts with no overflow.

## Active hosting (supersedes GitHub Pages note above)

- Moved production to Netlify at Fru's request after the GitHub custom-domain
  certificate failure. Site: glyph-fru, ID 43596603-ee22-490c-958d-d97b4a2ccab0.
- Production deploy: 6aa555d0b05d025d44962a65, serving website commit e1ffbdd.
  Fallback URL: https://glyph-fru.netlify.app.
- glyph.fru.dev now uses Netlify-managed DNS in zone 676ed2114e30745448e3330d.
  Replaced the old CNAME fru-dev3.github.io (record 6aa538169a24fc78dd75653b,
  TTL 3600) with Netlify's managed record. Other DNS records were untouched.
- Netlify has an issued certificate covering *.fru.dev and forces HTTPS.
  Verified certificate validation and exact HTML content against Netlify's IP;
  public DNS resolver 1.1.1.1 returned Netlify while the local resolver still
  cached GitHub. Old DNS answers may persist for their one-hour TTL.
- No Git repository connected to Netlify, so pushes do not deploy to production.
  Deploy only with explicit session authorization, using:
  netlify deploy --site 43596603-ee22-490c-958d-d97b4a2ccab0 --dir docs --no-build --prod
- CLI validation: real installed claude, agy, codex, cursor-agent, crush, cortex,
  opencode and pi all accepted `billing --help` through Glyph, exit 0. This is
  parser/argument smoke coverage, not full interactive-session certification.
  Gemini CLI is absent (exit 127); do not describe all nine as verified locally.

- Added `glyph fleet init`: adds missing ci/review/cloud examples, respects
  GLYPH_FLEET_CONF, preserves existing definitions, and is safe to repeat.
  Website setup is one copyable command, with config details collapsed.
  Verified fresh/existing configs, no trailing newline, dry run, custom path,
  browser clipboard and mobile layout. Installed wrapper updated locally.
