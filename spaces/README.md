# glyph spaces

Your working layout as data: which folders are open, on which machine, with
which agent. A *space* is one workspace and the tabs inside it; a *profile*
decides which spaces a machine takes. The same files open the same working set
on every machine, each tab resolved to whatever that machine calls the folder.

## Where the layout lives

Never in this repo. It is personal, so it sits with your own config:

    ~/.config/glyph/spaces/machines.json     roots per machine, its tag, profiles, backend
    ~/.config/glyph/spaces/spaces/*.json     one space per file: a workspace and its tabs

`GLYPH_SPACES` points at another folder. Make it a synced one, or link
`~/.config/glyph/spaces` to one, and a new space reaches every machine with no
commit and no push. `glyph spaces check` prints which folder it read.
[example/](example/) is a complete layout to copy from.

## machines.json

    "laptop": {
      "role": "dev",
      "backend": "herdr",
      "tag": "lt",
      "profiles": ["work"],
      "roots": { "home": "~", "code": "~/code" }
    }

A machine is keyed by its computer name, lowercase with hyphens (`Ben's
Laptop` reads `ben-s-laptop`). `GLYPH_SPACES_MACHINE`, or `--machine` on any
command, says which one this is when the name does not match.

- `roots` are the folders a tab's path may start from. A root missing on a
  machine (`null`) skips the tabs that need it there.
- `tag` leads every workspace name (`lt-work`), so a workspace says which
  machine it is on even when you look at it from another one.
- `profiles` pick the spaces. A hub can take `work` and `hub`; a laptop only
  `work`.
- `backend` names the tool that builds it. Herdr is the only one today.

## A space

    {
      "id": "work",
      "space": "work",
      "profiles": ["work"],
      "previous": ["Work"],
      "tabs": [
        { "label": "api", "mark": "work-api", "path": "{code}/acme-api", "agent": "claude" }
      ]
    }

- `path` names a root, never an absolute folder, so one file serves every
  machine.
- `mark` is the label glyph gives the tab's agent; glyph adds the rest of the
  session name. `glyph spaces names` prints the result and flags a name used
  twice, since two agents answering to one name is how a message reaches the
  wrong one.
- `previous` lists names a space or tab had before, so `apply` renames in
  place instead of building a second copy.
- A tab with no `agent` stays a shell.

## Commands

    glyph spaces check     resolve every path for this machine; writes nothing
    glyph spaces names     the session name each tab's agent answers to
    glyph spaces apply     build the spaces; rename old workspaces and tabs in place
    glyph spaces start     start agents in tabs that are still shells
    glyph spaces remark    rename running agents to their tab's name

`check` and `names` read the layout and the disk only, so they answer anywhere,
over ssh too, and on a machine with no backend installed. The other three go
through the backend.

`apply` refuses to start an agent in a folder Claude Code has not been trusted
with: such an agent stops on the trust prompt, never registers, and so never
gets its name. Claude Code asks once per folder, not per tree. `start` answers
that prompt itself, checks free memory before every launch and stops at
`--floor` rather than take the machine down.

## Code

    glyph-spaces                 argument parsing and dispatch
    glyph-fleet                  the same, for glyph fleet report, status and diff
    glyph_spaces/core.py         the layout itself; no terminal tool is named here
    glyph_spaces/fleet.py        what a machine is, and how machines differ
    glyph_spaces/backends/       one file per tool: herdr.py
    test_fleet.py                asserts over invented machines; python3 spaces/test_fleet.py

Supporting another tool is one new file under `backends/` and one word in
`machines.json`; no space file changes.

`fleet.py` is here rather than beside the wrapper because it needs what this
package already knows: which machine this is, what the map calls its roots and
profiles, and how a name is normalised. Both commands are executable files on
purpose, so `ssh laptop glyph-fleet report --json` reaches one where a shell
function cannot be reached at all.

Two rules the collector keeps. Every reader stands alone: one that fails adds a
line to `errors` and the report still comes out, so `glyph fleet report` has no
non-zero exit for an unreadable fact. And nothing is read twice from two
places: the agents and their auto-approve flags are parsed out of `glyph.zsh`,
where that table is written, and the account tag is handed in by the shell that
works it out, because a second set of rules here would be a second answer.
