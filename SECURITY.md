# Security

## Reporting

Open a private security advisory on GitHub, or a normal issue if the problem
is not sensitive. Please do not post working exploits in a public issue.

## What glyph touches

Glyph is one zsh file that you source from `~/.zshrc`. It runs with your user's
privileges, in your interactive shell. What that means in practice:

- **It reads** `~/.config/glyph/*`, your git directory name, your computer name,
  and, for `glyph usage`, the local agent transcripts under `~/.claude` and
  `~/.codex`.
- **It writes** a session log to `${XDG_STATE_HOME:-~/.local/state}/glyph/`,
  your terminal title, and tmux or Herdr pane labels.
- **It goes to the network in exactly two places**: `glyph update`, and
  `glyph usage --live`. Nothing else makes a request. There is no telemetry.

## Credentials

`glyph usage --live` reads the Claude Code OAuth token from the macOS Keychain
item `Claude Code-credentials` and sends it to Anthropic's usage endpoint. The
token is passed to curl over stdin, never as a command line argument, because
anything in argv is readable by every other process on the machine. It is not
logged, cached, or written to disk.

Every other command works entirely offline and needs no credentials.

## The update trust model

`glyph update` fetches `glyph.zsh` over HTTPS from this repository and installs
it. It refuses a file that does not parse, and keeps the previous copy at
`~/.config/glyph/glyph.zsh.bak`.

Be clear about what that does and does not give you: the parse check is a
guard against a truncated download, **not a signature**. Updating trusts GitHub
and your TLS chain. If that is not a trust boundary you want, point
`GLYPH_UPDATE_URL` at a copy you control, or update the file by hand.

## Untrusted input

Session labels and project names are reduced to `[a-z0-9-]` before they are used
anywhere, so a label cannot break out into a command. Agent names from
`~/.config/glyph/agents.tsv` are used to define shell functions and are refused
unless they match `[A-Za-z0-9_.-]`. Remote slots quote the agent, preset, host
and working directory before building the SSH command.

## Auto-approve

`GLYPH_YOLO=1` sends the agent's own "stop asking me to approve each tool call"
flag. That is a real reduction in safety, it belongs to the agent rather than to
glyph, and it is off unless you set it on that command.
