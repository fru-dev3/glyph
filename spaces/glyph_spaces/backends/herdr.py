"""The Herdr backend: build the layout as Herdr workspaces, tabs and panes.

Everything that speaks the Herdr socket API lives here. Herdr has no
declarative layout of its own — checked on 0.6.0 and 0.9.0 — so this replays
the space files through `herdr` one call at a time.
"""
import glob, json, os, re, subprocess, time

import shlex

from glyph_spaces.core import (carries_name, free_gb, is_trusted, norm, renamed, resolve, session_name,
                        space_label, this_machine, token, trust_table, wants)


def herdr(*args):
    r = subprocess.run(["herdr"] + list(args), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("herdr %s failed: %s" % (" ".join(args), r.stderr.strip()))
    out = r.stdout.strip()
    try:
        return json.loads(out)["result"]
    except (ValueError, KeyError):
        return out


def existing_workspaces():
    try:
        ws = herdr("workspace", "list")["workspaces"]
    except Exception:
        return {}
    return dict((w.get("label"), w["workspace_id"]) for w in ws if w.get("label"))


def first_pane_of(tab_id):
    for p in herdr("pane", "list")["panes"]:
        if p.get("tab_id") == tab_id:
            return p["pane_id"]
    return None


def workspace_contents(wsid):
    """Existing tab labels, and the cwd each of that workspace's panes sits in."""
    tabs = herdr("tab", "list", "--workspace", wsid)["tabs"]
    labels = set(norm(t.get("label")) for t in tabs if t.get("label"))
    cwds = set()
    for pane in herdr("pane", "list")["panes"]:
        if pane.get("workspace_id") == wsid and pane.get("cwd"):
            cwds.add(os.path.realpath(pane["cwd"]))
    return labels, cwds


def cmd_apply(args):
    mid, m, spaces = this_machine(args)
    if not mid:
        return 2
    roots = m["roots"]
    have = existing_workspaces()
    dry = args.dry_run
    trust = trust_table()
    built = skipped = missing = added = renamed = 0

    # An agent started in a folder Claude Code has not been trusted with stops
    # on its trust prompt and never registers a session, so it is never named
    # and never reachable. Better to say so than to launch into a wall.
    blocked = []
    for sp in spaces:
        if not wants(m, sp):
            continue
        for tab in sp["tabs"]:
            try:
                path = resolve(tab["path"], roots)
            except KeyError:
                continue
            if tab.get("agent") and os.path.isdir(path) and not is_trusted(path, trust):
                blocked.append((sp["space"], tab["label"], path))
    if blocked and not args.allow_untrusted and not args.no_agents:
        print("Claude Code has not been trusted with these folders:")
        for space, label, path in blocked:
            print("  %-18s %-16s %s" % (space, label, path))
        print("")
        print("An agent started there stops on the trust prompt and never registers,")
        print("so it gets no name and no Remote Control. Open each one once and answer,")
        print("or re-run with --allow-untrusted to start them and answer the prompts.")
        return 1

    # A space this machine does not take, still open under any of its names.
    # A space kept to one machine is opened from the others with herdr --remote.
    for sp in spaces:
        if wants(m, sp):
            continue
        names = set(norm(x) for x in [sp["space"]] + sp.get("previous", []))
        names |= set(norm("%s-%s" % (m.get("tag"), x)) for x in names)
        for label, wsid in list(have.items()):
            if norm(label) not in names:
                continue
            if args.prune and not dry:
                herdr("workspace", "close", wsid)
                print("%-18s closed, %s does not run %s" % (label, mid, sp["space"]))
            else:
                print("%-18s not for this machine; --prune closes it" % label)

    for sp in sorted(spaces, key=lambda s: s["id"]):
        if not wants(m, sp):
            continue
        want_label = space_label(m, sp)
        tabs = []
        for tab in sp["tabs"]:
            try:
                path = resolve(tab["path"], roots)
            except KeyError:
                path = None
            if not path or not os.path.isdir(path):
                print("%-18s skip tab %-16s no such path" % (want_label, tab["label"]))
                missing += 1
                continue
            tabs.append((tab, path))
        if not tabs:
            print("%-18s nothing resolves here, not creating it" % want_label)
            continue

        # The workspace under its current name, or under any name it had before.
        wsid = have.get(want_label)
        if not wsid:
            olds = set(norm(x) for x in [sp["space"]] + sp.get("previous", []))
            for label, w in have.items():
                if norm(label) in olds:
                    wsid = w
                    print("%-18s rename workspace %s" % (want_label, label))
                    if not dry:
                        herdr("workspace", "rename", wsid, want_label)
                    renamed += 1
                    break

        if wsid and not args.force:
            renamed += relabel_tabs(wsid, sp, dry)
            labels, cwds = workspace_contents(wsid)
            todo = [(t, path) for t, path in tabs
                    if norm(t["label"]) not in labels
                    and not (dry and any(norm(x) in labels for x in t.get("previous", [])))]
            if not todo:
                print("%-18s complete, nothing to add" % want_label)
                skipped += 1
                continue
            print("%-18s adding %d" % (want_label, len(todo)))
            for tab, path in todo:
                if dry:
                    print("    + %-16s %s%s" % (tab["label"], path,
                          "" if is_trusted(path, trust) else "   UNTRUSTED"))
                    continue
                t = herdr("tab", "create", "--workspace", wsid, "--cwd", path,
                          "--label", tab["label"], "--no-focus")["tab"]
                launch(t["tab_id"], tab, path, args.no_agents)
                print("    + %s" % tab["label"])
            added += len(todo)
            continue

        first, first_path = tabs[0]
        if dry:
            print("%-18s workspace + %d tabs" % (want_label, len(tabs)))
            for tab, path in tabs:
                print("    %-16s %s" % (tab["label"], path))
            built += 1
            continue

        ws = herdr("workspace", "create", "--cwd", first_path,
                   "--label", want_label, "--no-focus")["workspace"]
        wsid = ws["workspace_id"]
        tab_ids = [t["tab_id"] for t in herdr("tab", "list", "--workspace", wsid)["tabs"]]
        if tab_ids:
            herdr("tab", "rename", tab_ids[0], first["label"])
            launch(tab_ids[0], first, first_path, args.no_agents)
        for tab, path in tabs[1:]:
            t = herdr("tab", "create", "--workspace", wsid, "--cwd", path,
                      "--label", tab["label"], "--no-focus")["tab"]
            launch(t["tab_id"], tab, path, args.no_agents)
        print("%-18s built with %d tabs" % (want_label, len(tabs)))
        built += 1

    print("")
    print("%d built, %d renamed, %d tabs added, %d complete, %d tabs skipped for missing paths"
          % (built, renamed, added, skipped, missing))
    return 0


def relabel_tabs(wsid, sp, dry):
    """Give every tab in the workspace its current name.

    A tab is matched by its label, current or previous, not by its folder: a
    pane opened by hand often sits in a parent folder. A tab the map does not
    describe is still brought into the same form, lowercase with hyphens.
    """
    by = {}
    for tab in sp["tabs"]:
        for x in [tab["label"]] + tab.get("previous", []):
            by.setdefault(norm(x), tab["label"])
    n = 0
    for t in herdr("tab", "list", "--workspace", wsid)["tabs"]:
        cur = t.get("label") or ""
        want = by.get(norm(cur)) or token(cur)
        if want and want != cur:
            print("    tab %-18s -> %s" % (cur, want))
            if not dry:
                herdr("tab", "rename", t["tab_id"], want)
            n += 1
    return n


def launch(tab_id, tab, path, no_agents=False):
    """Start the agent in the tab's own pane, through the glyph wrapper."""
    agent = tab.get("agent")
    if not agent or no_agents:
        return
    pane = first_pane_of(tab_id)
    if not pane:
        print("    no pane for %s, left as a shell" % tab["label"])
        return
    herdr("pane", "run", pane, agent_command(tab, path))


def agent_command(tab, path, resume=False):
    # cd first: a tab opened by hand often sits in a parent folder, and the
    # agent should open in the folder the tab is for. --continue picks up the
    # last conversation in that folder, so a relaunch keeps its context.
    return "cd %s && %s %s%s" % (shlex.quote(path), tab["agent"], tab["mark"],
                                 " --continue" if resume and tab["agent"] == "claude" else "")


def described_panes(m, spaces):
    """(space, tab, path, pane) for every pane sitting in a tab the map describes."""
    roots = m["roots"]
    ws = dict((w["workspace_id"], w.get("label")) for w in herdr("workspace", "list")["workspaces"])
    tabs = dict((t["tab_id"], (ws.get(t["workspace_id"]), t.get("label")))
                for t in herdr("tab", "list")["tabs"])
    want = {}
    for sp in spaces:
        if not wants(m, sp):
            continue
        for tab in sp["tabs"]:
            try:
                path = resolve(tab["path"], roots)
            except KeyError:
                continue
            want[(norm(space_label(m, sp)), norm(tab["label"]))] = (sp, tab, path)
    out = []
    for pane in herdr("pane", "list")["panes"]:
        wl, tl = tabs.get(pane.get("tab_id"), (None, None))
        hit = want.get((norm(wl), norm(tl)))
        if hit:
            out.append(hit + (pane,))
    return out


def pane_text(pane, lines="14"):
    r = subprocess.run(["herdr", "pane", "read", pane, "--source", "visible",
                        "--lines", lines], capture_output=True, text=True)
    return r.stdout


def answer_trust(pane, deadline):
    """Wait for Claude Code's first-run prompt, then say yes.

    Polling, not a fixed sleep: under load the prompt can take well over ten
    seconds to draw, and keys sent before it appears land in the shell as
    literal text. An earlier version slept seven seconds and counted the launch
    regardless, which is how 34 launches produced 16 sessions.
    """
    while time.time() < deadline:
        text = pane_text(pane).lower()
        if "trust this folder" in text:
            subprocess.run(["herdr", "pane", "send-keys", pane, "Down"],
                           capture_output=True)
            time.sleep(0.4)
            subprocess.run(["herdr", "pane", "send-keys", pane, "Enter"],
                           capture_output=True)
            return True
        if "\u2500" in text and "\u00b7" in text:
            return False          # already past the prompt, session is drawing
        time.sleep(1.5)
    return False


def live_session_pids():
    """Pids of the sessions Claude Code currently has registered.

    Pids, not names: a session registers before glyph renames it, so its name
    is empty at first. Keying on names made a set that already held an empty
    string show no difference, and every good launch was reported as a failure.
    """
    pids = set()
    for f in glob.glob(os.path.expanduser("~/.claude/sessions/*.json")):
        try:
            pid = int(os.path.basename(f)[:-5])
            os.kill(pid, 0)
            pids.add(pid)
        except Exception:
            continue
    return pids


def cmd_start(args):
    """Start agents in the tabs that are still shells, in map order."""
    mid, m, spaces = this_machine(args)
    if not mid:
        return 2
    started = failed = 0
    seen_tabs = set()
    only = set(args.space or [])
    for sp, tab, path, pane in described_panes(m, spaces):
        if only and sp["space"] not in only:
            continue
        # One agent per tab: a tab split into panes gets it in its first shell.
        if not tab.get("agent") or pane.get("agent") or pane["tab_id"] in seen_tabs:
            seen_tabs.add(pane["tab_id"])
            continue
        seen_tabs.add(pane["tab_id"])
        if args.max and started >= args.max:
            print("stopping at --max %d" % args.max)
            break
        free = free_gb()
        if free < args.floor:
            print("stopping: %.1f GB free, floor is %.1f" % (free, args.floor))
            break
        name = session_name(m, tab)
        if args.dry_run:
            print("  would start %-24s (%.1f GB free)" % (name, free))
            started += 1
            continue
        before = live_session_pids()
        herdr("pane", "run", pane["pane_id"], agent_command(tab, path, args.resume))
        trusted = answer_trust(pane["pane_id"], time.time() + args.wait)
        # Count a session, not a command. Wait for one to register before
        # calling it started, and say so plainly when none does.
        deadline = time.time() + args.wait
        arrived = False
        while time.time() < deadline:
            if live_session_pids() - before:
                arrived = True
                break
            time.sleep(1.5)
        note = "trust confirmed " if trusted else ""
        if arrived:
            started += 1
        else:
            failed += 1
            note += "NO SESSION "
        print("  %-24s %s(%.1f GB free)" % (name, note, free))
        time.sleep(1)
    print("")
    print("%d started, %d did not register, %.1f GB free now"
          % (started, failed, free_gb()))
    return 0


def cmd_remark(args):
    """Rename running agents to the name glyph gives their tab, in place,
    keeping their context.

    The current name is the pane label glyph set at launch. A name that
    differs only in its stamp is already right: the stamp is when the session
    began, and a renamed session keeps the one it has. A busy agent is left
    alone: the rename is typed into its prompt, and typing into a session
    mid-task is how a half-written instruction gets sent.
    """
    mid, m, spaces = this_machine(args)
    if not mid:
        return 2
    done = skipped = busy = 0
    for sp, tab, path, pane in described_panes(m, spaces):
        if not pane.get("agent"):
            continue
        have = pane.get("label") or ""
        if carries_name(m, tab, have):
            skipped += 1
            continue
        want = renamed(m, tab, have)
        if pane.get("agent_status") not in ("idle", "done") and not args.busy:
            print("  busy, left   %-40s (want %s)" % (have, want))
            busy += 1
            continue
        if args.dry_run:
            print("  %-40s -> %s" % (have, want))
        else:
            pid = pane["pane_id"]
            subprocess.run(["herdr", "pane", "send-text", pid, "/rename " + want],
                           capture_output=True)
            time.sleep(0.5)
            subprocess.run(["herdr", "pane", "send-keys", pid, "Enter"],
                           capture_output=True)
            subprocess.run(["herdr", "pane", "rename", pid, want], capture_output=True)
            print("  %-40s -> %s" % (have, want))
            time.sleep(1.2)
        done += 1
    print("")
    print("%d renamed, %d already current, %d busy and left alone" % (done, skipped, busy))
    return 0
