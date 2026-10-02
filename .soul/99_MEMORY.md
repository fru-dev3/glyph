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

- Agent identity is now included in launch marks: label, project, agent, machine,
  date/time. Claude uses `Claude Code`; AGI uses `AGI`; other adapters use their
  display labels. Herdr remains the recommended outer workspace manager; avoid
  nested Glyph tmux fleets inside Herdr unless a standalone fleet is intended.
- Updated the vault-linked installed shell wrapper and verified the composed mark
  plus the existing smoke suite. Website/docs examples updated; no deploy made
  for this change yet.

- Standardized all mark fields to lowercase hyphenated tokens separated by `·`:
  label, project, agent, machine, timestamp. Project overrides normalize too.
- Machine identity now comes from the configured macOS ComputerName via
  `scutil --get ComputerName`, otherwise the system hostname. GLYPH_MACHINE is
  the explicit override for Windows releases, tablets, or custom roles. Glyph
  no longer guesses Mac model abbreviations or OS names.
- Herdr guidance: use Herdr as the outer workspace and launch individual agents
  in its tabs. `glyph fleet` still creates standalone tmux; inside Herdr it
  nests tmux. Documented this behavior and recommendation; no Herdr Fleet
  backend added without a clear API/UX decision.

- Added native Fleet backends. `GLYPH_FLEET_BACKEND=auto` selects Herdr when
  `HERDR_ENV` is present, cmux when its workspace environment is present, and
  standalone tmux otherwise. Explicit `herdr`, `cmux`, and `tmux` values are
  supported. Herdr creates one tab per local slot and starts the wrapper through
  interactive zsh; cmux creates one workspace per local slot. SSH slots remain
  tmux-only. Dry-run output covers both new backends.
- Herdr and cmux backend commands were inspected against installed CLIs. No live
  agent fleet was launched during tests. The installed vault-linked wrapper was
  updated.
- Added Zellij and WezTerm Fleet backends with explicit selection and dry-run
  output; neither CLI is installed on this machine, so live launches remain
  untested. Refreshed the website around a wider Herdr-inspired product layout
  with a workspace preview while preserving all generator and copy controls.

## 2026-09-21: moved from Netlify to Vercel

glyph.fru.dev is hosted on Vercel now (team fru-dev3, project glyph-fru).
Netlify is being shut down, so there is no netlify.toml any more.

- The site is the static `docs/` folder. No build, no functions, no secrets.
  `vercel.json` publishes `docs/`, rewrites `/docs` to `docs.html` (Netlify's
  pretty URL did this before) and carries the nosniff, Referrer-Policy and
  PNG cache headers. Deploy with `./scripts/ship.sh`.
- GitHub Pages is also switched on for this repo (main, /docs, CNAME
  glyph.fru.dev), but DNS never pointed there: at the time of the move
  glyph.fru.dev had A records to Netlify in the fru.dev zone (Netlify DNS),
  and fru-dev3.github.io/glyph only redirected to glyph.fru.dev.
- DNS cutover is the chief session's job: a CNAME `glyph` to the Vercel value
  from `vercel domains verify glyph.fru.dev`.

## 2026-09-21: star prompt after install and update (0.7.4)

- `_glyph_star_ask` asks "If glyph has been useful, would you like to star it?
  [Y/n]" once, modeled on herdr's post-update prompt. It runs at the end of
  `glyph update` (only when a new file was installed) and at the end of
  install.sh (a plain sh run borrows `zsh -c` to call it).
- It stars through `gh api -X PUT /user/starred/fru-dev3/glyph` when gh is
  signed in, and prints the repo link otherwise. It skips the question when
  gh says the repo is already starred.
- The answer is written to `$GLYPH_STATE/star` (yes/no/starred), so it never
  asks twice. EOF writes nothing and it asks again next time. It never asks
  without a TTY on stdin and stdout. `GLYPH_STAR=0` opts out.
- The smoke tests pick up the caller's GLYPH_SEP, GLYPH_ORDER and similar
  variables and fail on this machine unless you run them under `env -u ...`.
  This was already true before this change.

## 2026-10-02: the account field

- A sixth field, `account`, left out of the default order. Naming it in
  GLYPH_ORDER ends (or starts) the mark with a short tag for the login Claude
  Code is signed into, read from `${CLAUDE_CONFIG_DIR:-$HOME}/.claude.json`
  (`oauthAccount.emailAddress`). `glyph account` prints the tag by itself.
- The tag is worked out, never looked up: the initial of each word before the
  `@`, then the trailing digits (`foo.dev3` reads `fd3`). An address with no
  separator (`footech3`) splits after the person's own first name, taken from
  `GLYPH_ME`, else `id -F` (macOS), else `$USER`; names under three letters are
  ignored. `accounts.tsv` can overrule a tag, and Fru's setup does not use it:
  no address may be written into code or config.
- Claude Code only. Codex and the rest get no account segment.
- The name is cut at launch, so a `/login` inside a running session leaves the
  old tag. `aidev remark` (or `/rename`) refreshes it.
- tests/smoke.zsh now unsets GLYPH_SEP, so it passes under a personal
  environment without `env -u`.
- First pushed by itself on top of 0.7.3 (baac2af), because the star prompt
  and `glyph wake` work in the tree belonged to earlier sessions. That went
  wrong within minutes; see the 0.8.0 entry below.
- Fru's own order (vault `glyph-personal.zsh`) is now
  `label project machine agent account stamp` with `·` and `%y%m%d-%H%M`:
  fapps-glyph·mbp·cc·fd3·261002-0535. The 09-21 mesh form is retired.

## 2026-10-02: 0.8.0 published (star prompt, glyph wake, account field)

- `glyph wake` was written on 2026-09-28 and ran from the vault copy without
  being committed. A `StopFailure` hook (`glyph wake park`) records the pane of
  a session stopped by a usage limit; one waiter per machine asks Anthropic
  when the limit lifts, gives Claude Code `GLYPH_WAKE_GRACE` seconds, then
  presses Enter or types `continue` into each parked pane (Herdr or tmux).
  Three early nudges in a row and it gives up on that pane.
- Same batch: `_glyph_timeout` (macOS has no timeout(1)) so a locked Keychain
  cannot hang the quota call, with `~/.claude/.credentials.json` as the
  fallback; and the agent wrappers run the agent unmarked when `_glyph_launch`
  is missing, which is what Claude Code's command snapshot leaves behind.
- Lesson: the public file must be a superset of what Fru's Macs load.
  `~/.config/glyph/glyph.zsh` is a symlink to the vault copy, so `glyph update`
  writes the public file over it. With only the account field pushed, an
  update at 06:10 removed wake and the star prompt from both Macs while the
  wake hook was installed. Restored from `glyph.zsh.bak`, then everything was
  committed as 0.8.0 and the vault copy made byte-identical to the repo file.
- Not done: no v0.8.0 tag or GitHub release (the latest release is v0.7.0), and
  the site does not mention wake or the account field.
