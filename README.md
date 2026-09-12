# claude-nametag

Readable names for Claude Code Remote Control sessions.

Open Remote Control on your phone with a few sessions running and you get a list
like this:

```
tims-macbook-pro-4-local-transient
fru-5e
doc-9b
```

Which machine is that on? Which project? Started when? You cannot tell without
opening each one. Claude Code names a session from your first message, or
auto-derives one, and neither happens until after the session is up.

`claude-nametag` names it before it starts:

```
billing·Acme API·mbp·2026-09-12·0556
```

Your label, the project, the machine, and when you started it.

## Install

```sh
git clone https://github.com/<you>/claude-nametag.git
cd claude-nametag && ./install.sh
exec zsh
```

Requires zsh and Claude Code. The installer copies one file to
`~/.config/nametag/` and adds a source line to `~/.zshrc`. Nothing else.

## Use

```sh
claude                    # Acme API·mbp·2026-09-12·0556
claude billing            # billing·Acme API·mbp·2026-09-12·0556
claude billing "fix X"    # same, and "fix X" is the first prompt
claude -n billing         # same - an explicit -n is stamped too
```

The name you give always leads. The project is appended unless it would just
repeat your label, and is omitted outside a git repo. Remote Control is enabled
for every interactive session, so they all reach your phone.

Check what a command would do without launching:

```sh
NAMETAG_DRYRUN=1 claude billing
```

## Configuration

| Variable | Effect |
|---|---|
| `NAMETAG_OFF=1` | Keep the name, drop the machine and time |
| `NAMETAG_FMT` | `date(1)` format for the stamp (default `%Y-%m-%d·%H%M`) |
| `NAMETAG_MACHINE` | Machine tag, when the hostname does not map well |
| `NAMETAG_SEP` | Separator (default `·`) |
| `NAMETAG_RC=0` | Do not add `--remote-control` |
| `NAMETAG_YOLO=1` | Add `--dangerously-skip-permissions` (off by default) |
| `NAMETAG_DRYRUN=1` | Print the argv instead of launching |

The machine tag comes from `hostname -s`: a MacBook Pro becomes `mbp`, a Mac
mini `mini`, a MacBook Air `air`. Set `NAMETAG_MACHINE` for anything else.

Project names come from the git repo's directory name, title-cased
(`acme-api` becomes `Acme API`). Override any of them in
`~/.config/nametag/names.tsv`, one `directory<TAB>Display Name` per line:

```
acme-api	Acme API (prod)
internal-tools	Tools
```

## What it does not touch

`claude -p`, `claude --print`, and subcommands like `claude mcp` pass through
unchanged, so scripts and CI behave exactly as before. An explicit
`--remote-control <name>` is left alone.

## Why a shell wrapper

A session name has to exist before the process starts, so it can only come from
argv. Plugins and `SessionStart` hooks run after that point and cannot set it.
Hence a `claude` shell function rather than a plugin.

Two things worth knowing if you build on this:

- `--remote-control <name>` enables the bridge but does **not** name the
  session. It comes back as `nameSource: "derived"` with an auto-generated
  name. Only `-n` sets it. `nametag` passes both.
- In zsh, `argv` **is** `$@`. Declaring `local -a argv` inside a function
  silently empties the positional parameters.

To see what a running session is actually called, read
`~/.claude/sessions/<pid>.json` and look at `name` and `nameSource`. The startup
banner prints neither.

## Related

Anthropic's own docs suggest renaming from the mobile app by long-pressing a
session, and `CLAUDE_REMOTE_CONTROL_SESSION_NAME_PREFIX` can set a fixed prefix
for auto-generated names. Neither gives you a per-session name at launch.

## License

MIT
