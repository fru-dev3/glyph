"""glyph claims: one session owns an area of work, so another does not start it.

Two agents built the same feature in the same worktree on the same morning and
committed over each other, and a second feature was built twice because the
agent that built it again did not know it was already done. A claim is the
smallest thing that would have stopped both: take the area, and the next
session that reaches for it is told who has it and where.

Honest about the reach: a claim would not have helped the three sessions that
reasoned from a stale branch, which is a reading problem, and the overlapping
screen checks already have a `mkdir` lock of their own.

Four decisions worth keeping:

- **`mkdir`, never a lock file.** macOS has no `flock`, and a plain file of the
  same name is worse than nothing: `mkdir` can never take it, so every waiter
  falls through and believes it won. A 0-byte `/tmp/glyph-mac-ui.lock` cost a
  day here. `mkdir` either creates the directory or raises, for exactly one
  caller, and the holder is written into it on the next line.
- **The state is the person's, not this repo's.** It lives where
  `GLYPH_CLAIMS` points, the way `GLYPH_SPACES` holds the layout and
  `GLYPH_RIG` the reports. An area, a session name, a machine and a branch are
  all personal, and none of them belongs in a public repo.
- **A session that is gone is `stale`; a holder that cannot be read is
  `unknown`.** Stale never blocks: it is taken over, out loud, naming the
  holder it replaced. Unknown does block, because a holder nobody can read has
  not been shown to be dead. Same rule as the setup block's `locks` check, for
  the same reason.
- **The collector hangs the holder on the session row.** Ownership shows up
  next to the session actually doing the work, on every machine at once, which
  is why this belongs in Rig rather than standing alone.
"""
import json, os, shutil, time

from glyph_spaces import core

# The claim is the directory; the holder is the one file inside it. `holder` is
# the name the setup block's lock check already looks for, so the two
# conventions stay one convention.
SUFFIX = ".claim.d"
HOLDER = "holder"


def _fleet():
    """`fleet`, imported late on purpose.

    `fleet` imports this module to hang a holder on a session row, so importing
    it back at the top would be a cycle. Everything borrowed from it here is a
    formatter or the report reader, never a second copy of either.
    """
    from glyph_spaces import fleet
    return fleet


_ME = {}


def me():
    """This machine's id, asked once.

    `core.machine_id()` shells out to `scutil`, about 6 ms, and every claim in
    the folder is settled against this, so a dozen claims were a dozen calls
    and 30 ms on the report. Measured; it is the only reason this exists. The
    answer is kept against the override that can change it, so naming another
    machine still works.
    """
    key = os.environ.get("GLYPH_SPACES_MACHINE") or ""
    if _ME.get("key") != key:
        _ME.update({"key": key, "id": core.machine_id()})
    return _ME["id"]


def claims_dir():
    """Where the claims live: `GLYPH_CLAIMS`, else `~/.config/glyph/claims`.

    Point it at a synced folder, or link `~/.config/glyph/claims` to one, and a
    claim taken on one machine is readable on all of them with no network call,
    exactly as the layout and the reports already are.
    """
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(
        os.path.expanduser("~"), ".config")
    return os.path.expanduser(os.environ.get("GLYPH_CLAIMS")
                              or os.path.join(base, "glyph", "claims"))


def area_name(area):
    """An area as a folder name, normalised the way every glyph name is.

    Also the only validation this needs: a token has no dots and no slashes in
    it, so an area can never name a folder outside the claims folder. The
    leading hyphens go too, since an area is typed back on a command line.
    """
    got = core.token(area or "").strip("-")
    if not got:
        raise ValueError("an area needs a name with a letter or a digit in it")
    return got


def dir_for(area):
    return os.path.join(claims_dir(), area_name(area) + SUFFIX)


def holder_of(area_dir):
    """What the holder file says, or None when there is nothing to read.

    None is the whole of `unknown`: a missing file, half a file, a file written
    by something else. None of those is proof the holder is gone.
    """
    try:
        with open(os.path.join(area_dir, HOLDER)) as f:
            got = json.load(f)
    except Exception:
        return None
    return got if isinstance(got, dict) else None


def epoch(iso):
    try:
        return time.mktime(time.strptime((iso or "")[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return None


def alive(pid):
    """Whether a pid on this machine is running. None when it cannot be said."""
    try:
        os.kill(int(pid), 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True              # it exists, it is simply not ours to signal
    except (TypeError, ValueError):
        return None


def verdict(row, reports=None):
    """`live`, `stale` or `unknown` for one holder.

    A holder on this machine is settled by its pid. A holder on another machine
    is settled by that machine's last report: its session in `sessions.live[]`
    is live, and a report taken after the claim that does not list it is stale.
    Everything else is unknown, and unknown is never read as dead.
    """
    if not row:
        return "unknown"
    if row.get("machine") == me():
        got = alive(row.get("pid")) if row.get("pid") is not None else None
        return "unknown" if got is None else ("live" if got else "stale")
    rep = (_reports() if reports is None else reports).get(row.get("machine"))
    if not rep:
        return "unknown"
    for s in (rep.get("sessions") or {}).get("live") or []:
        if row.get("session") and s.get("name") == row["session"]:
            return "live"
        if row.get("pid") is not None and s.get("pid") == row["pid"]:
            return "live"
    taken, at = epoch(rep.get("taken")), epoch(row.get("at"))
    return "stale" if taken and at and taken > at else "unknown"


def _reports():
    """Every machine's last reading, or nothing. A claim is never lost over it."""
    try:
        return _fleet().load_reports()
    except Exception:
        return {}


def rows(reports=None):
    """Every claim, oldest first, each one the holder plus its state."""
    d = claims_dir()
    if not os.path.isdir(d):
        return []
    if reports is None:
        reports = _reports()
    out = []
    for n in sorted(os.listdir(d)):
        if not n.endswith(SUFFIX):
            continue
        got = holder_of(os.path.join(d, n))
        row = dict(got or {})
        # The folder is the area, whatever the file inside it claims to be.
        row["area"] = n[:-len(SUFFIX)]
        row["state"] = verdict(got, reports)
        out.append(row)
    return sorted(out, key=lambda r: (r.get("at") or "", r["area"]))


def write_holder(area_dir, row):
    """The holder, written whole.

    Under another name and then renamed into place, which is one step, so a
    reader never finds half a holder where a whole one was a moment ago. Half a
    file reads as `unknown`, and a live claim flickering to unknown is the sort
    of thing a table shows and nobody can explain.
    """
    tmp = os.path.join(area_dir, "%s.writing.%d" % (HOLDER, os.getpid()))
    with open(tmp, "w") as f:
        json.dump(row, f, indent=2)
        f.write("\n")
    os.rename(tmp, os.path.join(area_dir, HOLDER))


def hand_over(area_dir, mine):
    """Take a stale claim's place. The holder it replaced, or None if not ours.

    The claim directory is made once and never moved; the atomic step here is
    renaming the holder file out of the way, which succeeds for one caller and
    raises for the next, so two sessions that both find the same stale claim
    cannot both replace it. Two things make it safe rather than merely atomic.

    The holder is read back out of the file this call moved, not out of the one
    it read a moment ago, because the claim may have changed hands in between:
    deciding from the earlier read is how a takeover ends up throwing away a
    claim that had just been taken, which it did, twice in forty rounds.

    And a holder that turns out not to be stale after all is put back exactly
    as it was. Nothing can have written a holder in the meantime: a directory
    that exists cannot be made again, and the only other way to write one is to
    win the rename this call has already won.
    """
    taking = os.path.join(area_dir, "%s.taking.%d.%d"
                          % (HOLDER, os.getpid(), int(time.time() * 1000)))
    try:
        os.rename(os.path.join(area_dir, HOLDER), taking)
    except OSError:
        return None
    try:
        with open(taking) as f:
            got = json.load(f)
        got = got if isinstance(got, dict) else None
    except Exception:
        got = None
    if verdict(got) != "stale":
        os.rename(taking, os.path.join(area_dir, HOLDER))
        return None
    write_holder(area_dir, mine)
    os.remove(taking)
    return got


def take(area, session=None, pid=None, branch=None):
    """Take an area. `(True, mine)`, or `(False, the row that stopped us)`.

    The directory is the claim. `mkdir` creates it for exactly one caller and
    raises for every other, which is the whole of the race; the holder is
    written on the next line. The one moment a claim exists without a holder is
    the gap between those two lines, and a reader that lands in it says
    `unknown` rather than guessing, which is why that is the safe answer.
    """
    d = dir_for(area)
    mine = {"area": area_name(area), "session": session,
            "machine": me(),
            "pid": int(pid) if pid else None, "branch": branch,
            "at": _fleet().stamp(time.time())}
    os.makedirs(claims_dir(), exist_ok=True)
    try:
        os.mkdir(d)
    except FileExistsError:
        pass
    else:
        try:
            write_holder(d, mine)
        except OSError:
            # A claim with no holder blocks everyone until it is forced, so a
            # holder that cannot be written gives the directory back instead.
            shutil.rmtree(d, ignore_errors=True)
            raise
        return True, mine
    if verdict(holder_of(d)) == "stale":
        gone = hand_over(d, mine)
        if gone is not None:
            mine["took_over"] = gone
            return True, mine
    # Read again rather than report what was true a moment ago.
    got = holder_of(d)
    row = dict(got or {})
    row["area"], row["state"] = area_name(area), verdict(got)
    return False, row


def release(area, session=None, pid=None, force=False):
    """Give an area back.

    `(True, the holder)` when it was let go, `(False, None)` when nothing
    claimed it, `(False, the holder)` when it belongs to somebody else. Only
    the session that took it may give it back, since one agent releasing
    another's area is the failure this exists to prevent; `--force` is for a
    holder nobody can read.
    """
    d = dir_for(area)
    if not os.path.isdir(d):
        return False, None
    got = holder_of(d)
    row = dict(got or {})
    row["area"], row["state"] = area_name(area), verdict(got)
    if not force:
        ours = got and ((pid and got.get("pid") == int(pid))
                        or (session and got.get("session") == session))
        if not ours:
            return False, row
    shutil.rmtree(d, ignore_errors=True)
    return True, row


def attach(live):
    """Hang each claim on the live session row that holds it. The rows, changed.

    Only this machine's claims, because only here can a pid be matched; a row
    in `sessions.live[]` is by definition a live session, so a claim found on
    one needs no state beside it.
    """
    mine = me()
    by_name, by_pid = {}, {}
    for c in rows(reports={}):
        if c.get("machine") != mine:
            continue
        if c.get("session"):
            by_name[c["session"]] = c
        if c.get("pid") is not None:
            by_pid[c["pid"]] = c
    for r in live or []:
        c = by_name.get(r.get("name")) or by_pid.get(r.get("pid"))
        if c:
            r["claim"] = {"area": c["area"], "branch": c.get("branch"),
                          "at": c.get("at")}
    return live


# --- commands ---------------------------------------------------------------
# One line per claim, in columns, with the state as a mark at the right rather
# than a word in the middle, the way `glyph fleet status` reads. A table that
# has rows says nothing but its rows: what a state means belongs in the README,
# and the only place a next command is named is an empty folder or a refusal.
MARK = {"live": "ok", "stale": "x", "unknown": "?"}


def describe(row):
    """One line naming a holder: who, where, and how long they have had it."""
    if not any(row.get(k) for k in ("session", "machine", "pid", "at")):
        return "no readable holder"
    bits = ["%s on %s" % (row.get("session") or "a session with no name",
                          row.get("machine") or "an unnamed machine")]
    if row.get("pid"):
        bits.append("pid %s" % row["pid"])
    if row.get("branch"):
        bits.append("branch %s" % row["branch"])
    if row.get("at"):
        bits.append("taken %s" % _fleet().age(row["at"]))
    return ", ".join(bits)


def why_unknown(row):
    """Which of the three ways a claim can be unreadable this one is.

    Worth the three lines: "no readable holder" and "that machine has not
    reported since" are different problems with different answers, and one
    wording for both would send a reader to the wrong one.
    """
    if not row.get("machine"):
        return "no readable holder"
    if row["machine"] == me():
        return "the holder names no pid to look for"
    return "no reading from %s since the claim" % row["machine"]


def short(name, width):
    """A name cut to fit, without leaving half a separator at the end."""
    return (name or "-")[:width].rstrip("·-") or "-"


def cmd_claim(args):
    try:
        ok, row = take(args.area, args.session, args.pid, args.branch)
    except ValueError as e:
        print("glyph claim: %s" % e)
        return 2
    except OSError as e:
        print("glyph claim: cannot write to %s: %s" % (_fleet().tilde(claims_dir()), e))
        print("set GLYPH_CLAIMS to a folder you can write to")
        return 2
    if ok:
        print("claimed  %s" % row["area"])
        print("  holder   %s" % describe(row))
        if row.get("took_over") is not None:
            print("  was      %s" % describe(row["took_over"]))
        print("  folder   %s" % _fleet().tilde(dir_for(args.area)))
        return 0
    print("glyph claim: %s is claimed" % row["area"])
    print("  holder   %s" % describe(row))
    print("  held     %s" % MARK[row["state"]])
    if row["state"] == "unknown":
        print("  folder   %s" % _fleet().tilde(dir_for(args.area)))
        print("  glyph release %s --force    let go of a claim nobody can read"
              % row["area"])
    return 1


def cmd_claims(args):
    got = rows()
    if not got:
        print("no claims in %s" % _fleet().tilde(claims_dir()))
        print("glyph claim <area>    take one")
        return 0
    row = "%-22s %-46s %-14s %-16s %-9s %s"
    print(row % ("AREA", "HOLDER", "MACHINE", "BRANCH", "AGE", "HELD"))
    for r in got:
        print(row % (short(r["area"], 22), short(r.get("session"), 46),
                     short(r.get("machine"), 14), short(r.get("branch"), 16),
                     _fleet().age(r.get("at")), MARK[r["state"]]))
    for r in got:
        if r["state"] == "stale":
            print("stale    %-22s %s is gone"
                  % (r["area"], short(r.get("session"), 46)))
        elif r["state"] == "unknown":
            print("unknown  %-22s %s" % (r["area"], why_unknown(r)))
    print("")
    print("%d claim%s, %d held, read from %s"
          % (len(got), "" if len(got) == 1 else "s",
             sum(1 for r in got if r["state"] == "live"),
             _fleet().tilde(claims_dir())))
    return 0


def cmd_release(args):
    try:
        ok, row = release(args.area, args.session, args.pid, args.force)
    except ValueError as e:
        print("glyph release: %s" % e)
        return 2
    if ok:
        print("released  %s" % row["area"])
        return 0
    if row is None:
        print("glyph release: nothing claims %s" % area_name(args.area))
        return 1
    print("glyph release: %s is held by another session" % row["area"])
    print("  holder   %s" % describe(row))
    print("  glyph release %s --force    let go of it anyway" % row["area"])
    return 1
