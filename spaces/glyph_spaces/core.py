"""The layout itself: machines, roots, spaces, tabs and marks.

Nothing here knows about Herdr, or tmux, or whatever comes next. A backend
under backends/ takes this description and builds it in one particular tool.
`check` and `names` read the description and the disk only, so they answer the
same on a machine where no backend is installed at all.

The description is the person's, not this repo's: it is read from
~/.config/glyph/spaces/ (or GLYPH_SPACES) and never kept here.
"""
import json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def machine_id():
    name = os.environ.get("GLYPH_SPACES_MACHINE")
    if not name:
        try:
            name = subprocess.run(["scutil", "--get", "ComputerName"],
                                  capture_output=True, text=True).stdout.strip()
        except Exception:
            name = ""
    if not name:
        name = os.uname().nodename
    name = name.split(".")[0].lower()
    return re.sub(r"-+$", "", re.sub(r"[^a-z0-9]+", "-", name))


def map_root():
    """The folder holding machines.json and spaces/."""
    return os.path.expanduser(os.environ.get("GLYPH_SPACES") or os.path.join(
        os.environ.get("XDG_CONFIG_HOME") or "~/.config", "glyph", "spaces"))


class MapMissing(Exception):
    pass


def load():
    root = map_root()
    if not os.path.exists(os.path.join(root, "machines.json")):
        raise MapMissing("no machines.json in %s" % root)
    with open(os.path.join(root, "machines.json")) as f:
        machines = json.load(f)["machines"]
    spaces = []
    sdir = os.path.join(root, "spaces")
    for fn in sorted(os.listdir(sdir)):
        if fn.endswith(".json"):
            with open(os.path.join(sdir, fn)) as f:
                spaces.append(json.load(f))
    return machines, spaces


def this_machine(args):
    """The machine record to work against, or None with the reason printed."""
    machines, spaces = load()
    mid = getattr(args, "machine", None) or machine_id()
    if mid not in machines:
        print("unknown machine: %s" % mid)
        print("known: %s" % ", ".join(sorted(machines)))
        return None, None, None
    return mid, machines[mid], spaces


def profiles(machine):
    """The profiles a machine takes. A list, so a hub can take `work` and `hub`."""
    return machine.get("profiles") or [machine.get("profile")]


def wants(machine, space):
    return any(p in space.get("profiles", []) for p in profiles(machine))


def space_label(machine, space):
    """The workspace label on this machine: its tag, then the space, st-work.

    The tag leads so a workspace says which machine it is on even when it is
    viewed from another one (`herdr --remote studio`).
    """
    tag = machine.get("tag")
    return "%s-%s" % (tag, space["space"]) if tag else space["space"]


LABEL, STAMP = "zzlabelzz", "zzstampzz"
_forms = {}


def glyph_form(agent):
    """(form, now) for an agent's session name, asked of glyph itself.

    `form` is a name with LABEL and STAMP standing where the label and the
    stamp go (zzlabelzz·laptop·claude-code·zzstampzz); `now` is the stamp glyph
    would cut this minute, "" when the name carries none. An interactive zsh
    answers, so the order, the separator, the agent label and the account all
    come from the settings the person's own shell loads, whoever called and
    from where. None when glyph is not there to ask.
    """
    if agent not in _forms:
        # ponytail: asked from /, so no project joins the name. Right while a
        # given label drops the project; a setup that keeps both needs this
        # asked once per tab, from the tab's folder.
        ask = ('print -r -- "@@1 $(GLYPH_FMT=%s GLYPH_AGENT=$1 glyph name %s)";'
               ' print -r -- "@@2 $(GLYPH_AGENT=$1 glyph name %s)"'
               % (STAMP, LABEL, LABEL))
        got = {}
        try:
            out = subprocess.run(["zsh", "-ic", ask, "glyph-spaces", agent], cwd="/",
                                 stdin=subprocess.DEVNULL, capture_output=True,
                                 text=True, timeout=30).stdout
            for line in out.splitlines():
                if line[:2] == "@@":
                    got[line[2:3]] = line[4:]
        except Exception:
            pass
        form, real = got.get("1", ""), got.get("2", "")
        if LABEL not in form:
            _forms[agent] = None
        else:
            left, cut, right = form.partition(STAMP)
            _forms[agent] = (form, real[len(left):len(real) - len(right)] if cut else "")
    return _forms[agent]


def session_name(machine, tab, stamp="<when>"):
    """What glyph will call the agent in this tab.

    The stamp is the minute the session begins, so until it has begun the name
    is known only up to that. Everything in front of it stays put, and is what
    another agent looks a session up by.
    """
    g = glyph_form(tab.get("agent") or "shell")
    if not g:
        tag = machine.get("tag")
        return "%s-%s" % (tag, tab["mark"]) if tag else tab["mark"]
    return g[0].replace(LABEL, token(tab["mark"])).replace(STAMP, stamp)


def carries_name(machine, tab, have):
    """Whether `have` is already this tab's name, whenever it was stamped."""
    left, cut, right = session_name(machine, tab, "\0").partition("\0")
    if not cut:
        return have == left
    return (have.startswith(left) and have.endswith(right)
            and len(have) > len(left) + len(right))


def renamed(machine, tab, have):
    """The name to give a session that is already running.

    It keeps the stamp `have` ends with, so a session keeps the time it
    started; a name with no stamp to keep is stamped now, the time of the
    rename, since nothing here records when the session began.
    """
    g = glyph_form(tab.get("agent") or "shell")
    now = g[1] if g else ""
    old = have[-len(now):] if now else ""
    same_shape = re.sub(r"\d", "0", old) == re.sub(r"\d", "0", now)
    return session_name(machine, tab, old if now and same_shape else now)


def backend_for(machine):
    """The module that builds this machine's layout in whatever tool it runs.

    A machine names its backend in machines.json. Moving to another tool is a
    new file under backends/ and one word changed there; the space files never
    learn which tool is in use.
    """
    name = machine.get("backend", "herdr")
    sys.path.insert(0, ROOT)
    try:
        return __import__("glyph_spaces.backends." + name, fromlist=["*"]), name
    except ImportError:
        return None, name


def resolve(path, roots):
    def sub(m):
        key = m.group(1)
        val = roots.get(key)
        if val is None:
            raise KeyError(key)
        return val
    return os.path.expanduser(re.sub(r"\{(\w+)\}", sub, path))


def trust_table():
    """Paths Claude Code has recorded, and whether each was trusted."""
    try:
        with open(os.path.expanduser("~/.claude.json")) as f:
            projects = json.load(f).get("projects", {})
    except Exception:
        return {}
    return dict((k, bool(v.get("hasTrustDialogAccepted"))) for k, v in projects.items())


def is_trusted(path, table):
    """Trusted only if this exact folder was trusted.

    Claude Code asks per folder, not per tree: a trusted parent does nothing
    for a repo inside it. Measured, after an earlier version assumed
    inheritance and predicted two prompts where ten were waiting.
    """
    # Both spellings, because Claude Code keys trust by the cwd it was handed:
    # where a folder is reached through a symlink, a trust recorded under one
    # spelling says nothing about the other.
    return bool(table.get(path) or table.get(os.path.realpath(path)))


def repo_state(path):
    """plain, a short commit for a healthy repo, or broken."""
    if not os.path.exists(os.path.join(path, ".git")):
        return "plain"
    r = subprocess.run(["git", "-C", path, "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "broken"


def norm(label):
    return re.sub(r"[^a-z0-9]+", "", (label or "").lower())


def token(value):
    return re.sub(r"-+$", "", re.sub(r"[^a-z0-9]+", "-", (value or "").lower()))


def tabs_for(machine, spaces):
    """Every tab this machine's profile asks for, with its path resolved."""
    roots = machine["roots"]
    out = []
    for sp in sorted(spaces, key=lambda s: s["id"]):
        if not wants(machine, sp):
            continue
        for tab in sp["tabs"]:
            try:
                out.append((sp, tab, resolve(tab["path"], roots)))
            except KeyError:
                out.append((sp, tab, None))
    return out


def free_gb():
    """Free plus inactive memory, which is what a new session can actually use."""
    try:
        out = subprocess.run(["vm_stat"], capture_output=True, text=True).stdout
    except Exception:
        return 99.0
    pages = {}
    size = 4096
    head = out.splitlines()[0] if out else ""
    mo = re.search(r"page size of (\d+)", head)
    if mo:
        size = int(mo.group(1))
    for line in out.splitlines()[1:]:
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip().rstrip(".")
        if v.isdigit():
            pages[k.strip()] = int(v)
    return (pages.get("Pages free", 0) + pages.get("Pages inactive", 0)) * size / 1073741824.0


def cmd_check(args):
    mid, m, spaces = this_machine(args)
    if not mid:
        return 2
    roots = m["roots"]
    _, backend = backend_for(m)
    print("machine  %s  (tag %s, role %s, profiles %s, backend %s %s)"
          % (mid, m.get("tag"), m["role"], ",".join(profiles(m)), backend, m.get(backend, "")))
    print("map      %s" % map_root())
    for k in sorted(roots):
        v = roots[k] and os.path.expanduser(roots[k])
        state = "missing" if v and not os.path.isdir(v) else ("unset" if not v else "ok")
        print("  root %-10s %-7s %s" % (k, state, v or "-"))
    print("")
    ok = bad = skipped = untrusted = 0
    trust = trust_table()
    for sp in spaces:
        if not wants(m, sp):
            skipped += len(sp.get("tabs", []))
            continue
        print("%s  [%s]" % (space_label(m, sp), sp["id"]))
        for tab in sp["tabs"]:
            try:
                p = resolve(tab["path"], roots)
            except KeyError as e:
                print("  %-18s NO ROOT  {%s} is unset here" % (tab["label"], e.args[0]))
                bad += 1
                continue
            if not os.path.isdir(p):
                print("  %-18s MISSING  %s" % (tab["label"], p))
                bad += 1
                continue
            # A directory existing is not proof a repo arrived intact: a copy
            # that dies partway leaves the folder and a .git with no HEAD.
            state = repo_state(p)
            note = "" if state == "plain" else "  [%s]" % state
            if not is_trusted(p, trust):
                note += "  UNTRUSTED"
                untrusted += 1
            if state == "broken":
                print("  %-18s BROKEN   %s (git repo with no HEAD)" % (tab["label"], p))
                bad += 1
            else:
                print("  %-18s ok       %s%s" % (tab["label"], p, note))
                ok += 1
        print("")
    print("%d ok, %d missing, %d tabs in other profiles" % (ok, bad, skipped))
    if untrusted:
        print("%d would stop on Claude Code's trust prompt before starting" % untrusted)
    return 1 if bad else 0


def cmd_names(args):
    """Print the session name glyph gives every tab here, `<when>` for its stamp.

    A name used twice is reported: two agents answering to one name is how a
    message reaches the wrong one.
    """
    mid, m, spaces = this_machine(args)
    if not mid:
        return 2
    seen = {}
    print("%-14s %-18s %s" % ("SPACE", "TAB", "SESSION NAME"))
    for sp, tab, path in tabs_for(m, spaces):
        name = session_name(m, tab)
        seen.setdefault(name, []).append("%s/%s" % (sp["space"], tab["label"]))
        note = "" if tab.get("agent") else "  (no agent)"
        print("%-14s %-18s %s%s" % (space_label(m, sp), tab["label"], name, note))
    dupes = dict((k, v) for k, v in seen.items() if len(v) > 1)
    print("")
    for name, where in sorted(dupes.items()):
        print("DUPLICATE name %s: %s" % (name, ", ".join(where)))
    return 1 if dupes else 0
