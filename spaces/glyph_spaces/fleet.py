"""glyph fleet: what this machine is, and how it compares to the others.

`report` collects one machine's facts and writes them where every machine can
read them. `status` lays the machines side by side with Tailscale's word on who
is up. `diff` prints only the configuration that is not the same everywhere.

Three rules hold this file together:

- Every reader is on its own. One that fails adds a line to `errors` and the
  rest of the report still comes out, so a caller never loses a machine over a
  fact that happened to be unreadable.
- Nothing is written outside the report folder. The collector runs on machines
  with a few gigabytes free, so there is no temp file and no scratch copy.
- Nothing is read twice from two places. The agents and their flags are read
  out of glyph.zsh, the machine's roots and profiles out of the spaces map.
"""
import json, os, re, subprocess, threading, time
from concurrent import futures

from glyph_spaces import core

HOME = os.path.expanduser("~")
SCHEMA = 1
# Every probe is bounded and they all run at once, so the slowest one is close
# to the whole command's wall time. A reader that runs out of time adds its
# reason to `errors` and the report comes out without it, which is the whole
# budget in one sentence: answer now, say what is missing. GLYPH_FLEET_TIMEOUT
# moves both: 1 gives a faster, thinner report on a loaded machine.
TIMEOUT = float(os.environ.get("GLYPH_FLEET_TIMEOUT") or 2.0)
# For the two that earn more, both asked once and then remembered: the model
# name, and a version from a CLI this machine has not been asked about before.
SLOW = TIMEOUT * 2.5
NETFS = ("smbfs", "afpfs", "nfs", "webdav", "ftp")
PSEUDOFS = ("devfs", "autofs", "map", "lifs", "fdesc")
# ps rows for an agent that is a background service, not somebody's session.
SERVICE_WORDS = ("app-server", "exec-server", "daemon", "mcp", "serve")

ERRORS = []
_LOCK = threading.Lock()


def note(what, why):
    """Record a fact that could not be read. Never raises, never prints."""
    with _LOCK:
        ERRORS.append({"what": what, "why": str(why)[:200]})


def guard(what, fn, *a):
    """Run a reader. A reader that throws becomes an error line, not a crash."""
    try:
        return fn(*a)
    except Exception as e:
        note(what, "%s: %s" % (type(e).__name__, e))
        return None


def run(cmd, timeout=None, strict=False):
    """A command's output, or None. Writes nothing and never raises.

    `strict` means a command that exits non-zero answered nothing: its stderr
    is a complaint, not a version.
    """
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=timeout or TIMEOUT)
    except Exception:
        return None
    if strict and r.returncode != 0:
        return None
    return r.stdout if r.stdout else (r.stderr or "")


def read_json(path):
    try:
        with open(os.path.expanduser(path)) as f:
            return json.load(f)
    except Exception:
        return None


def tilde(path):
    """A path with the home folder collapsed, so a report carries no home path."""
    if not path:
        return path
    return "~" + path[len(HOME):] if path.startswith(HOME) else path


def num(text):
    """The first version-shaped number in a line: 2.1.316, v0.46.2, 26.4.0."""
    mo = re.search(r"\d+(?:\.\d+)+[\w.+-]*", text or "")
    return mo.group(0).rstrip(".,)") if mo else None


def state_dir():
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(HOME, ".local", "state")
    return os.environ.get("GLYPH_STATE") or os.path.join(base, "glyph")


def rig_dir():
    """Where the reports live: GLYPH_RIG, else ~/.config/glyph/rig.

    Point GLYPH_RIG at a synced folder, or link ~/.config/glyph/rig to one, and
    every machine's last reading is readable from any of them with no network
    call, the way the spaces map is.
    """
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(HOME, ".config")
    return os.path.expanduser(os.environ.get("GLYPH_RIG")
                              or os.path.join(base, "glyph", "rig"))


# --- the shell's own tables -------------------------------------------------

def glyph_zsh():
    """The wrapper this clone installs, or the installed one."""
    for p in (os.path.join(os.path.dirname(core.ROOT), "glyph.zsh"),
              os.path.join(os.environ.get("XDG_CONFIG_HOME")
                           or os.path.join(HOME, ".config"), "glyph", "glyph.zsh")):
        if os.path.exists(p):
            return p
    return None


def _zsh_map(text, name):
    """One `NAME=( key value key value )` table out of glyph.zsh."""
    mo = re.search(r"^%s=\(\s*(.*?)^\)" % re.escape(name), text, re.S | re.M)
    if not mo:
        return {}
    words = re.findall(r'"([^"]*)"|(\S+)', re.sub(r"#.*", "", mo.group(1)))
    flat = [a or b for a, b in words]
    return dict(zip(flat[0::2], flat[1::2]))


def agent_table():
    """Every agent glyph wraps: id, label, auto-approve flag.

    Read out of glyph.zsh, which is where that table is written, plus the
    person's own agents.tsv. Keeping a second copy here is how the two drift.
    """
    path = glyph_zsh()
    agents = {}
    if path:
        with open(path) as f:
            text = f.read()
        flags = _zsh_map(text, "GLYPH_YOLO_FLAG")
        labels = _zsh_map(text, "GLYPH_LABEL")
        for k, v in flags.items():
            agents[k] = {"label": labels.get(k, k), "auto_approve_flag": v or None}
    else:
        note("agents", "glyph.zsh not found, so the agent table is unknown")
    extra = os.environ.get("GLYPH_AGENTS") or os.path.join(HOME, ".config/glyph/agents.tsv")
    if os.path.exists(extra):
        with open(extra) as f:
            for line in f:
                if line.startswith("#") or "\t" not in line:
                    continue
                cols = line.rstrip("\n").split("\t")
                cmd = cols[0].strip()
                if cmd:
                    flag = (cols[1] or None) if len(cols) > 1 else None
                    agents[cmd] = {"label": (cols[2] if len(cols) > 2 else "") or cmd,
                                   "auto_approve_flag": flag}
    return agents


def glyph_version():
    path = glyph_zsh()
    if not path:
        return None
    with open(path) as f:
        mo = re.search(r"^typeset -g GLYPH_VERSION=(\S+)", f.read(), re.M)
    return mo.group(1) if mo else None


# --- finding a binary over plain SSH ----------------------------------------
# `command -v claude` answers nothing in a non-interactive shell: the agents
# are installed in folders a login shell adds to PATH, and glyph itself is a
# zsh function. So every known install folder is checked as well as PATH.
BIN_DIRS = ["~/.local/bin", "/opt/homebrew/bin", "/usr/local/bin", "~/.bun/bin",
            "~/.npm-global/bin", "~/.codex/bin", "/usr/bin", "/opt/homebrew/opt",
            "/usr/local/opt", "~/.cargo/bin", "~/go/bin", "/Applications"]


def find_bin(name):
    for d in os.environ.get("PATH", "").split(":") + [os.path.expanduser(x) for x in BIN_DIRS]:
        p = os.path.join(d, name)
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


# Some answers are slow to get and change only when the machine does: what a
# CLI says its version is, what Apple calls this model. They are kept against
# the thing they describe, which is the difference between a six second report
# and half a second. An upgrade changes the file, which changes the key.
CACHE, _DIRTY = {}, []
CACHE_FILE = "fleet.cache.json"


def cache():
    if not CACHE:
        CACHE.update(read_json(os.path.join(state_dir(), CACHE_FILE)) or {})
        CACHE.setdefault("_", 1)
    return CACHE


def remembered(key, fn):
    c = cache()
    if key in c:
        return c[key]
    got = fn()
    with _LOCK:
        c[key] = got
        _DIRTY.append(key)
    return got


def save_cache():
    if not _DIRTY:
        return
    try:
        os.makedirs(state_dir(), exist_ok=True)
        with open(os.path.join(state_dir(), CACHE_FILE), "w") as f:
            json.dump(CACHE, f)
    except Exception as e:
        note("cache", "%s" % e)


def version_of(path, flag="--version"):
    name = os.path.basename(path)
    try:
        st = os.stat(path)
        key = "v %s %d %d" % (os.path.realpath(path), st.st_mtime, st.st_size)
    except OSError:
        key = None
    kept = cache()
    if key and key in kept:
        got = kept[key]
        if got is None:
            note(name, "%s %s says no version for this build" % (name, flag))
        return got
    # Not run(): a timeout and a complaint mean different things here, and only
    # one of them is worth remembering. Generous, because a miss happens once
    # per installed version, and they all run at once.
    late, out = False, ""
    try:
        r = subprocess.run([path, flag], capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=SLOW)
        out = "" if r.returncode else (r.stdout or r.stderr or "")
        if r.returncode:
            note(name, "%s %s exits %d and says no version" % (name, flag, r.returncode))
    except subprocess.TimeoutExpired:
        late = True
        note(name, "%s %s answered nothing inside %.1fs" % (name, flag, SLOW))
    except Exception as e:
        note(name, "%s %s: %s" % (name, flag, e))
    line = (out.strip().splitlines() or [""])[0]
    got = num(line) or (line[:40] or None)
    # An answer is remembered, and so is a refusal: a CLI that exits with a
    # complaint will do the same next time, and waiting for that on every run
    # is the slowest thing this command does. A timeout is not remembered,
    # because that was about how busy the machine was, not about the binary.
    # Either way an upgrade changes the file and so the key, and it is asked
    # again.
    if key and not late:
        with _LOCK:
            kept[key] = got
            _DIRTY.append(key)
    return got


# --- identity ---------------------------------------------------------------

def sysctls(*names):
    out = run(["sysctl"] + list(names), timeout=1.0) or ""
    got = {}
    for line in out.splitlines():
        if ": " in line:
            k, v = line.split(": ", 1)
            got[k.strip()] = v.strip()
    return got


def machine_block(mid, record):
    s = sysctls("hw.model", "machdep.cpu.brand_string", "kern.boottime")
    vers = run(["sw_vers"], timeout=1.0) or ""
    sw = dict(re.findall(r"^(\w+):\s*(.+)$", vers, re.M))
    boot = re.search(r"sec = (\d+)", s.get("kern.boottime", ""))
    name = run(["scutil", "--get", "ComputerName"], timeout=1.0)
    return {
        "id": mid,
        "name": (name or "").strip() or os.uname().nodename,
        "model": s.get("hw.model"),
        "marketing": marketing_name(),
        "chip": s.get("machdep.cpu.brand_string"),
        "macos": sw.get("ProductVersion"),
        "build": sw.get("BuildVersion"),
        "uptime_s": int(time.time()) - int(boot.group(1)) if boot else None,
        "role": (record or {}).get("role"),
        "tag": (record or {}).get("tag"),
        "profiles": core.profiles(record) if record else None,
        "account_tag": account_tag(claude_email()),
    }


def marketing_name():
    """The name Apple prints for this model, as far as the Mac knows it.

    Apple's own lookup table stopped being shipped around the Intel models, so
    on Apple silicon this is the family (`MacBook Pro`), not the full
    `MacBook Pro (14-inch, 2023)`. The model identifier beside it is exact.

    `system_profiler` is seconds of work on a loaded machine for an answer that
    cannot change, so the answer is kept against the model identifier.
    """
    model = sysctls("hw.model").get("hw.model")
    return remembered("model %s" % model, lambda: _marketing_name(model))


def _marketing_name(model):
    plist = ("/System/Library/PrivateFrameworks/ServerInformation.framework"
             "/Versions/A/Resources/en.lproj/SIMachineAttributes.plist")
    if model and os.path.exists(plist):
        try:
            import plistlib
            with open(plist, "rb") as f:
                e = plistlib.load(f).get(model) or {}
            got = (e.get("_LOCALIZABLE_") or {}).get("marketingModel")
            if got:
                return got
        except Exception:
            pass
    out = run(["system_profiler", "-json", "SPHardwareDataType"],
              timeout=SLOW)
    try:
        return json.loads(out)["SPHardwareDataType"][0].get("machine_name")
    except Exception:
        return None


def claude_email():
    return ((read_json("~/.claude.json") or {}).get("oauthAccount") or {}).get("emailAddress")


def account_tag(email):
    """The short tag for an address, from the person's own accounts.tsv.

    Only the file is read. glyph.zsh derives a tag from the address when the
    file is silent, and guessing it a second way here would make two answers
    for one question.
    """
    if not email:
        return None
    path = os.environ.get("GLYPH_ACCOUNTS") or os.path.join(HOME, ".config/glyph/accounts.tsv")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        for line in f:
            cols = line.rstrip("\n").split("\t")
            if len(cols) > 1 and cols[0].strip().lower() == email.lower():
                return cols[1].strip() or None
    return None


# --- tailscale --------------------------------------------------------------

def tailscale_bin():
    """The app bundle's binary first: a bare `tailscale` on PATH can be a stub
    that answers with a bundle error instead of status, and it is absent from a
    non-interactive PATH anyway."""
    for b in [os.environ.get("GLYPH_TAILSCALE"),
              "/Applications/Tailscale.app/Contents/MacOS/Tailscale",
              "/opt/homebrew/bin/tailscale", "/usr/local/bin/tailscale"]:
        if b and os.access(b, os.X_OK):
            return b
    return find_bin("tailscale")


_TS = {}


def tailscale_status():
    """`tailscale status --json`, read once per run."""
    if "d" in _TS:
        return _TS["d"]
    _TS["d"] = None
    b = tailscale_bin()
    if not b:
        note("tailscale", "no tailscale binary found")
        return None
    # The ordinary budget, not the longer one: whoever is reading this report
    # has its own tailnet view, which is the one `fleet status` uses. A busy
    # machine is better off answering without this than waiting for it.
    out = run([b, "status", "--json"])
    if not out:
        note("tailscale", "tailscale status --json answered nothing")
        return None
    try:
        _TS["d"] = json.loads(out)
    except Exception as e:
        note("tailscale", "status json did not parse: %s" % e)
    return _TS["d"]


def peer_id(node):
    """A node's machine id.

    From DNSName, not HostName: a phone reports its HostName as `localhost`,
    while the tailnet name is unique by construction.
    """
    dns = (node.get("DNSName") or "").rstrip(".")
    return core.token(dns.split(".")[0] if dns else node.get("HostName"))


def peer_row(node, is_self=False):
    dns = (node.get("DNSName") or "").rstrip(".")
    ips = node.get("TailscaleIPs") or []
    seen = node.get("LastSeen")
    if seen and seen.startswith("0001-"):
        seen = None            # never seen, rather than the year one
    return {"dns": dns or None, "ip": ips[0] if ips else None,
            "online": bool(node.get("Online")), "last_seen": seen,
            "os": node.get("OS"), "exit_node": bool(node.get("ExitNode")),
            "self": is_self}


def tailscale_block():
    d = tailscale_status()
    if not d:
        return None
    return peer_row(d.get("Self") or {}, True)


def tailnet():
    """Every node in the tailnet, by machine id."""
    d = tailscale_status() or {}
    out = {}
    if d.get("Self"):
        out[peer_id(d["Self"])] = peer_row(d["Self"], True)
    for p in (d.get("Peer") or {}).values():
        out[peer_id(p)] = peer_row(p)
    return out


# --- compute ----------------------------------------------------------------

def compute_block(ps):
    s = sysctls("hw.ncpu", "hw.perflevel0.logicalcpu", "hw.perflevel1.logicalcpu",
                "hw.memsize", "vm.swapusage")
    size, pages = core.vm_pages()
    total = int(s.get("hw.memsize") or 0) or None
    free = (pages.get("Pages free", 0) + pages.get("Pages inactive", 0)) * size
    # What Activity Monitor calls pressure: the pages that cannot simply be
    # handed to the next process, over the pages there are.
    held = (pages.get("Pages wired down", 0)
            + pages.get("Pages occupied by compressor", 0)) * size
    swap = re.search(r"used = ([\d.]+)([MGK])", s.get("vm.swapusage", ""))
    mult = {"K": 1024, "M": 1048576, "G": 1073741824}
    cores = int(s.get("hw.ncpu") or 0) or None
    busy = None
    if cores and (ps or {}).get("cpu_total") is not None:
        busy = min(100, round(ps["cpu_total"] / cores))
    return {
        "cores": {"total": cores,
                  "performance": int(s.get("hw.perflevel0.logicalcpu") or 0) or None,
                  "efficiency": int(s.get("hw.perflevel1.logicalcpu") or 0) or None},
        "gpu_cores": gpu_cores(),
        "memory_bytes": total,
        "memory_free_bytes": free or None,
        "memory_pressure_percent": round(100.0 * held / total) if total and held else None,
        "swap_used_bytes": int(float(swap.group(1)) * mult[swap.group(2)]) if swap else None,
        "load": [round(x, 2) for x in os.getloadavg()],
        "busy_percent": busy,
        "thermal": thermal(),
        "battery": battery(),
    }


def gpu_cores():
    out = run(["ioreg", "-rc", "AGXAccelerator", "-d1"], timeout=1.5) or ""
    mo = re.search(r'"gpu-core-count"\s*=\s*(\d+)', out)
    return int(mo.group(1)) if mo else None


def thermal():
    out = run(["pmset", "-g", "therm"], timeout=1.5) or ""
    if "No thermal warning" in out:
        return "nominal"
    mo = re.search(r"CPU_Speed_Limit\s*=\s*(\d+)", out)
    if mo and int(mo.group(1)) < 100:
        return "limited %s percent" % mo.group(1)
    return "nominal" if out else None


def battery():
    out = run(["pmset", "-g", "batt"], timeout=1.5) or ""
    mo = re.search(r"(\d+)%; ([a-zA-Z ]+);", out)
    if not mo:
        return None                      # a desktop, which is not an error
    state = mo.group(2).strip()
    cycles = re.search(r'"CycleCount"\s*=\s*(\d+)',
                       run(["ioreg", "-rc", "AppleSmartBattery", "-d1"], timeout=1.5) or "")
    return {"percent": int(mo.group(1)), "charging": state != "discharging",
            "state": state, "cycles": int(cycles.group(1)) if cycles else None}


# --- storage ----------------------------------------------------------------

def volume_roles(roots):
    """Mount point -> the name the spaces map gives what lives there.

    A root that resolves onto an external disk names that disk better than any
    rule could: the map already says this is where the studio or the vault is.
    """
    out = {}
    for key, val in (roots or {}).items():
        if not val:
            continue
        try:
            real = os.path.realpath(os.path.expanduser(val))
        except Exception:
            continue
        if real.startswith("/Volumes/"):
            out["/" + "/".join(real.split("/")[1:3])] = key
    return out


def over_full(volumes, limit=90):
    """Volumes with little room left, in words a person can act on."""
    return ["%s is %d percent full" % (v["mount"], v["used_percent"])
            for v in volumes
            if v.get("used_percent") is not None and v["used_percent"] >= limit]


def boot_name():
    """What the boot volume is called. macOS keeps a link to it in /Volumes."""
    try:
        for n in os.listdir("/Volumes"):
            if os.path.realpath(os.path.join("/Volumes", n)) == "/":
                return n
    except Exception:
        pass
    return None


def storage_block(roots):
    out = run(["mount"], timeout=1.5) or ""
    roles = volume_roles(roots)
    rows, boot_disk = [], None
    parsed = []
    for line in out.splitlines():
        mo = re.match(r"^(.+?) on (.+?) \(([^)]*)\)$", line)
        if not mo:
            continue
        dev, mount, flags = mo.group(1), mo.group(2), mo.group(3).split(", ")
        fs = flags[0]
        if fs in PSEUDOFS or dev.startswith("map "):
            continue
        parsed.append((dev, mount, fs, flags))
        if mount == "/":
            boot_disk = re.match(r"/dev/(disk\d+)", dev)
            boot_disk = boot_disk.group(1) if boot_disk else None
    for dev, mount, fs, flags in parsed:
        # nobrowse is macOS saying this is plumbing, not a disk anyone put
        # there: Preboot, VM, Update, a simulator image. Every volume in one
        # APFS container reports the same free space, so keeping them would
        # repeat the boot disk six times and warn about it six times.
        if "nobrowse" in flags and mount != "/":
            continue
        try:
            st = os.statvfs(mount)
        except Exception:
            continue
        total = st.f_blocks * st.f_frsize
        if not total:
            continue
        free = st.f_bavail * st.f_frsize
        disk = re.match(r"/dev/(disk\d+)", dev)
        if fs in NETFS or "://" in dev or (":" in dev and not dev.startswith("/")):
            kind = "network"
        elif disk and boot_disk and disk.group(1) == boot_disk:
            # ponytail: one internal disk per Mac, which is true of every
            # Apple silicon Mac. A second internal disk would read external.
            kind = "internal"
        elif disk:
            kind = "external"
        else:
            kind = "other"
        role = "boot" if mount == "/" else roles.get(mount)
        name = boot_name() if mount == "/" else os.path.basename(mount)
        rows.append({"mount": mount, "name": name or mount,
                     "device": dev, "fs": fs,
                     "total_bytes": total, "free_bytes": free,
                     "used_percent": round(100.0 * (total - free) / total),
                     "kind": kind, "network": kind == "network",
                     "read_only": "read-only" in flags, "role": role})
    rows.sort(key=lambda r: (r["kind"] != "internal", r["mount"]))
    return {"volumes": rows, "warnings": over_full(rows)}


# --- agents and accounts ----------------------------------------------------

def claude_mcp():
    return sorted((read_json("~/.claude.json") or {}).get("mcpServers") or {})


def codex_mcp():
    path = os.path.expanduser("~/.codex/config.toml")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        # The head of each table, not its sub-tables: [mcp_servers.acme.env]
        # is one more line about acme, not a second server.
        return sorted(set(re.findall(r"^\[mcp_servers\.([A-Za-z0-9_-]+)[.\]]",
                                     f.read(), re.M)))


def claude_plugins():
    d = read_json("~/.claude/plugins/installed_plugins.json") or {}
    plugins = d.get("plugins") or {}
    return sum(len(v) if isinstance(v, (list, dict)) else 1 for v in plugins.values())


def claude_account():
    a = (read_json("~/.claude.json") or {}).get("oauthAccount") or {}
    if not a:
        return None
    return {"label": account_tag(a.get("emailAddress")) or a.get("displayName"),
            "name": a.get("displayName"), "email": a.get("emailAddress"),
            "plan": a.get("planDisplayName"), "org_type": a.get("organizationType"),
            "uuid": (a.get("accountUuid") or "")[:8] or None,
            "source": "~/.claude.json oauthAccount"}


def codex_account():
    """What the Codex credential file says, and nothing more.

    The file also holds an API key and refresh tokens. They are never read into
    a report: a report is written to disk and read over the wire.
    """
    a = read_json("~/.codex/auth.json") or {}
    if not a:
        return None
    return {"label": None, "mode": a.get("auth_mode"),
            "last_refresh": a.get("last_refresh"),
            "source": "~/.codex/auth.json auth_mode"}


def claude_usage():
    """The token counts glyph already cached. Percentages are server side.

    Where a window starts and ends is Anthropic's to say and is never written
    to disk, so nothing here guesses it: `glyph usage --live` asks.
    """
    path = os.path.join(state_dir(), "usage.cache")
    if not os.path.exists(path):
        note("usage", "no cached claude token scan yet, run glyph usage")
        return None
    with open(path) as f:
        lines = f.read().splitlines()
    age = int(time.time()) - int(lines[0]) if lines and lines[0].isdigit() else None
    out = {"source": "transcripts", "age_s": age}
    for line in lines[1:]:
        f5 = line.split()
        if len(f5) == 5:
            out["window_%s" % ("5h" if f5[0] == "5h" else "7d")] = {
                "percent": None, "resets_at": None,
                "tokens_in": int(f5[1]), "tokens_out": int(f5[2]),
                "cache": int(f5[3]), "calls": int(f5[4])}
    note("usage", "claude usage needs --live for real percentages")
    return out


def codex_usage():
    """Codex writes its own rate limits down, so its windows are exact.

    Only the newest few rollouts are read: a session that never hit a limit
    writes none, and reading every one of several thousand files takes seconds.
    """
    root = os.path.expanduser("~/.codex/sessions")
    if not os.path.isdir(root):
        return None
    files = []
    for dirpath, _, names in os.walk(root):
        for n in names:
            if n.endswith(".jsonl"):
                p = os.path.join(dirpath, n)
                try:
                    files.append((os.stat(p).st_mtime, p))
                except OSError:
                    pass
    out = {"source": "~/.codex/sessions"}
    for _, p in sorted(files, reverse=True)[:40]:
        try:
            with open(p, "rb") as f:
                f.seek(max(0, os.stat(p).st_size - 65536))
                tail = f.read().decode("utf-8", "replace")
        except Exception:
            continue
        if '"primary":{' not in tail:
            continue
        for key in ("primary", "secondary"):
            mo = None
            for mo in re.finditer(r'"%s":\{([^}]*)\}' % key, tail):
                pass
            if not mo:
                continue
            blk = mo.group(1)
            pct = re.search(r'"used_percent":([\d.]+)', blk)
            win = re.search(r'"window_minutes":(\d+)', blk)
            rst = re.search(r'"resets_at":(\d+)', blk)
            if not pct or not win:
                continue
            mins = int(win.group(1))
            name = {300: "window_5h", 10080: "window_7d"}.get(mins, "window_%dm" % mins)
            out[name] = {"percent": round(float(pct.group(1))),
                         "window_minutes": mins,
                         "resets_at": stamp(int(rst.group(1))) if rst else None}
        plan = re.search(r'"plan_type":"([^"]*)"', tail)
        if plan:
            out["plan"] = plan.group(1)
        out["at"] = stamp(os.stat(p).st_mtime)
        return out
    note("usage", "no rate limit record in the newest codex sessions")
    return None


ACCOUNTS = {"claude": claude_account, "codex": codex_account}
MCP = {"claude": claude_mcp, "codex": codex_mcp}
USAGE = {"claude": claude_usage, "codex": codex_usage}


def agents_block():
    table = agent_table()
    found = {}
    for aid in table:
        p = find_bin(aid)
        if p:
            found[aid] = p
    # Every version at once: serially this is ten seconds, and one agent that
    # hangs on --version must not hold up the rest of the report.
    versions = {}
    if found:
        with futures.ThreadPoolExecutor(max_workers=min(12, len(found))) as ex:
            jobs = dict((ex.submit(version_of, p), a) for a, p in found.items())
            for f in futures.as_completed(jobs):
                versions[jobs[f]] = guard("version %s" % jobs[f], f.result)
    out = []
    for aid in sorted(table):
        row = {"id": aid, "label": table[aid]["label"],
               "installed": aid in found, "version": versions.get(aid),
               "path": tilde(found.get(aid)),
               "auto_approve_flag": table[aid]["auto_approve_flag"]}
        if aid in found:
            if aid in ACCOUNTS:
                row["account"] = guard("account %s" % aid, ACCOUNTS[aid])
            if aid in MCP:
                row["mcp_servers"] = guard("mcp %s" % aid, MCP[aid])
            if aid == "claude":
                row["plugins"] = guard("plugins", claude_plugins)
            if aid in USAGE:
                row["usage"] = guard("usage %s" % aid, USAGE[aid])
        out.append(row)
    return out


# --- sessions ---------------------------------------------------------------

def etime_s(text):
    """ps etime, [[dd-]hh:]mm:ss, as seconds."""
    days, _, rest = text.partition("-")
    if not rest:
        rest, days = days, "0"
    parts = [int(x) for x in rest.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    return int(days) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]


def stamp(epoch):
    """An instant as ISO 8601, offset included, with the colon in it.

    `%z` writes -0500 and the strict readers, Swift's among them, want -05:00.
    """
    out = time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(epoch))
    return out[:-2] + ":" + out[-2:] if re.search(r"[+-]\d{4}$", out) else out


def ps_rows(agent_ids):
    """One ps call: the agent processes, and how busy the machine is.

    The busy figure is every process's share added up over the cores, which is
    the number Activity Monitor shows. It comes free with a list we need
    anyway, where asking `top` for it would cost a second.
    """
    out = run(["ps", "-A", "-o", "pid=,%cpu=,rss=,etime=,command="], timeout=2.0) or ""
    rows, cpu_total = [], 0.0
    for line in out.splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5:
            continue
        pid, cpu, rss, et, cmd = parts
        try:
            cpu_total += float(cpu)
        except ValueError:
            pass
        argv = cmd.split()
        base = os.path.basename(argv[0])
        if base not in agent_ids:
            continue
        if len(argv) > 1 and argv[1] in SERVICE_WORDS:
            continue                     # a background service, not a session
        try:
            rows.append({"agent": base, "pid": int(pid), "cpu_percent": float(cpu),
                         "rss_bytes": int(rss) * 1024,
                         "started_at": stamp(time.time() - etime_s(et))})
        except ValueError:
            continue
    return {"agents": rows, "cpu_total": cpu_total if out else None}


def claude_sessions():
    """Claude Code keeps a file per live session: its name, folder and pid."""
    d = os.path.expanduser("~/.claude/sessions")
    rows = []
    if not os.path.isdir(d):
        return rows
    for n in sorted(os.listdir(d)):
        if not n.endswith(".json"):
            continue
        s = read_json(os.path.join(d, n)) or {}
        pid = s.get("pid")
        if not pid:
            continue
        try:
            os.kill(pid, 0)
        except OSError:
            continue
        began = s.get("startedAt")
        if isinstance(began, (int, float)):
            began = stamp(began / 1000.0 if began > 1e11 else began)
        rows.append({"name": s.get("name"), "agent": "claude", "pid": pid,
                     "cwd": tilde(s.get("cwd")), "started_at": began,
                     "status": s.get("status"),
                     "remote_control": bool(s.get("bridgeSessionId"))})
    return rows


def cwds(pids):
    """Each pid's working folder, from one lsof call."""
    if not pids:
        return {}
    out = run(["lsof", "-a", "-d", "cwd", "-Fn", "-p", ",".join(str(p) for p in pids)],
              timeout=2.0) or ""
    got, pid = {}, None
    for line in out.splitlines():
        if line.startswith("p"):
            pid = int(line[1:])
        elif line.startswith("n") and pid:
            got[pid] = line[1:]
    return got


def recent_sessions():
    path = os.path.join(state_dir(), "sessions.tsv")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        lines = f.read().splitlines()[-10:]
    out = []
    for line in lines:
        c = line.split("\t")
        if len(c) >= 5:
            out.append({"at": c[0], "agent": c[1], "mark": c[2], "machine": c[4]})
    return out


def sessions_block(ps):
    live = claude_sessions()
    named = dict((r["pid"], r) for r in live)
    others = [r for r in ps if r["pid"] not in named]
    folders = cwds([r["pid"] for r in others]) if others else {}
    for r in others:
        r["cwd"] = tilde(folders.get(r["pid"]))
        live.append(r)
    for r in live:                       # the numbers ps has, for a claude row too
        got = next((p for p in ps if p["pid"] == r["pid"]), None)
        if got:
            r.setdefault("cpu_percent", got["cpu_percent"])
            r.setdefault("rss_bytes", got["rss_bytes"])
            r.setdefault("started_at", got["started_at"])
        if r.get("name") and "·" in r["name"]:
            r["mark"] = r["name"].split("·")[0]
    return {"live": live, "recent": recent_sessions()}


# --- local inference and backends -------------------------------------------

def http_json(url, port, timeout=0.8):
    """A local service's JSON, or None. The port is knocked on first: a closed
    one answers instantly, while an HTTP call to it waits out its timeout."""
    import socket, urllib.request
    try:
        socket.create_connection(("127.0.0.1", port), 0.3).close()
    except OSError:
        return None
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.load(r)
    except Exception:
        return None


def inference_block():
    tags = http_json("http://127.0.0.1:11434/api/tags", 11434)
    ollama = {"running": tags is not None, "endpoint": "127.0.0.1:11434"}
    if tags:
        ollama["models"] = [{"name": m.get("name"), "size_bytes": m.get("size")}
                            for m in (tags.get("models") or [])]
    lm = http_json("http://127.0.0.1:1234/v1/models", 1234, 0.5)
    return {"ollama": ollama,
            "lmstudio": {"running": lm is not None, "endpoint": "127.0.0.1:1234"}}


BACKENDS = {"herdr": "--version", "tmux": "-V", "zellij": "--version"}
TOOLS = {"node": "--version", "python3": "--version", "uv": "--version",
         "git": "--version", "rustc": "--version", "go": "version"}


def probe_versions(wanted):
    """Several `--version` calls at once.

    None means the tool is not on this machine, which is a difference worth
    showing. `installed` means it is here but would not say which version, so
    that it does not read as missing.
    """
    found = dict((n, find_bin(n)) for n in wanted)
    out = dict((n, None) for n in wanted)
    live = dict((n, p) for n, p in found.items() if p)
    if not live:
        return out
    with futures.ThreadPoolExecutor(max_workers=min(12, len(live))) as ex:
        jobs = dict((ex.submit(version_of, p, wanted[n]), n) for n, p in live.items())
        for f in futures.as_completed(jobs):
            out[jobs[f]] = guard("version %s" % jobs[f], f.result) or "installed"
    return out


# --- spaces -----------------------------------------------------------------

def presets():
    path = os.environ.get("GLYPH_FLEET_CONF") or os.path.join(HOME, ".config/glyph/fleet.conf")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return re.findall(r"^\s*([A-Za-z0-9_-]+)\s*=", f.read(), re.M)


def spaces_block(record, spaces):
    if record is None:
        return {"presets": presets()}
    roots = record.get("roots") or {}
    mine = [s for s in (spaces or []) if core.wants(record, s)]
    missing = [k for k, v in roots.items()
               if not v or not os.path.isdir(os.path.expanduser(v))]
    return {"profiles": core.profiles(record),
            "spaces": [s["space"] for s in mine],
            "roots": dict((k, tilde(os.path.expanduser(v)) if v else None)
                          for k, v in roots.items()),
            "missing_roots": sorted(missing),
            "tabs": sum(len(s.get("tabs") or []) for s in mine),
            "backend": record.get("backend"),
            "presets": presets()}


# --- the diff surface -------------------------------------------------------

def launchd_jobs():
    """Services loaded for this login, Apple's own left out.

    `application.*` is left out too: those are windows a running app
    registered, not something installed.
    """
    out = run(["launchctl", "list"], timeout=2.0) or ""
    jobs = {}
    for line in out.splitlines()[1:]:
        c = line.split("\t")
        if len(c) < 3:
            continue
        label = c[2].strip()
        if label.startswith(("com.apple.", "application.", "0x")):
            continue
        jobs["launchd.%s" % label] = "loaded" if c[0].strip() not in ("-", "") else "idle"
    return jobs


def skills():
    d = os.path.expanduser("~/.claude/skills")
    if not os.path.isdir(d):
        return {}
    return dict(("skill.%s" % n, "present") for n in sorted(os.listdir(d))
                if os.path.isdir(os.path.join(d, n)))


def config_map(rep, tools):
    """The flat map the app diffs across machines.

    Comparable strings only: no nesting, and no path or address, since a
    difference in where a folder lives is not a difference worth a row.
    """
    cfg = {}
    for a in rep.get("agents") or []:
        if a.get("installed"):
            cfg["tool.%s" % a["id"]] = a.get("version") or "installed"
        for name in a.get("mcp_servers") or []:
            cfg["mcp.%s" % name] = "present"
    for name, v in sorted((tools or {}).items()):
        if v:
            cfg["tool.%s" % name] = v
    cfg["tool.glyph"] = glyph_version() or "unknown"
    m = rep.get("machine") or {}
    for k in ("macos", "build"):
        if m.get(k):
            cfg["os.%s" % k] = m[k]
    sp = rep.get("spaces") or {}
    if sp.get("profiles"):
        cfg["spaces.profiles"] = ",".join(sp["profiles"])
    if sp.get("backend"):
        cfg["spaces.backend"] = sp["backend"]
    for k, v in os.environ.items():
        if k.startswith("GLYPH_") and v and "/" not in v and len(v) < 40:
            cfg["env.%s" % k] = v
    cfg.update(guard("skills", skills) or {})
    cfg.update(guard("launchd", launchd_jobs) or {})
    return dict(sorted(cfg.items()))


# --- collect ----------------------------------------------------------------

def collect(account_tag_given=None):
    """This machine, as one object. Returns a report whatever fails inside it."""
    t0 = time.time()
    del ERRORS[:]
    mid = core.machine_id()
    record, spaces = None, None
    try:
        machines, spaces = core.load()
        record = machines.get(mid)
        if record is None:
            note("spaces", "no machine %s in the spaces map" % mid)
    except Exception as e:
        note("spaces", "%s" % e)

    table = guard("agents", agent_table) or {}
    got = {}
    # Every reader at once. The process list is one of them rather than a step
    # before them: on a busy machine `ps -A` is a second or two, and the two
    # readers that need it can wait for it while the other eight get on.
    with futures.ThreadPoolExecutor(max_workers=12) as ex:
        procs = ex.submit(guard, "processes", ps_rows, set(table))
        jobs = {
            "machine": lambda: machine_block(mid, record),
            "tailscale": tailscale_block,
            "compute": lambda: compute_block(procs.result() or {}),
            "storage": lambda: storage_block((record or {}).get("roots")),
            "agents": agents_block,
            "sessions": lambda: sessions_block((procs.result() or {}).get("agents") or []),
            "inference": inference_block,
            "backends": lambda: probe_versions(BACKENDS),
            "spaces": lambda: spaces_block(record, spaces),
            "tools": lambda: probe_versions(TOOLS),
        }
        running = dict((ex.submit(guard, name, fn), name) for name, fn in jobs.items())
        for f in futures.as_completed(running):
            got[running[f]] = f.result()
    rep = {"schema": SCHEMA,
           "taken": stamp(time.time()),
           "took_ms": None}
    for name in ("machine", "tailscale", "compute", "storage", "agents",
                 "sessions", "inference", "backends", "spaces"):
        rep[name] = got.get(name)
    if not rep.get("machine"):
        rep["machine"] = {"id": mid}
    if account_tag_given and rep.get("machine"):
        rep["machine"]["account_tag"] = account_tag_given
    rep["config"] = guard("config", config_map, rep, got.get("tools")) or {}
    save_cache()
    rep["took_ms"] = int((time.time() - t0) * 1000)
    rep["errors"] = list(ERRORS)
    return rep


# --- reading what every machine wrote ---------------------------------------

def load_reports():
    d = os.path.join(rig_dir(), "machines")
    out = {}
    if not os.path.isdir(d):
        return out
    for n in sorted(os.listdir(d)):
        if not n.endswith(".json"):
            continue
        rep = read_json(os.path.join(d, n))
        if rep:
            out[((rep.get("machine") or {}).get("id")) or n[:-5]] = rep
    return out


def write_report(rep):
    """One file per machine, plus a line of history. Written in place, since a
    machine with a few gigabytes free has no room for a second copy."""
    mid = (rep.get("machine") or {}).get("id") or core.machine_id()
    base = rig_dir()
    mdir, hdir = os.path.join(base, "machines"), os.path.join(base, "history")
    os.makedirs(mdir, exist_ok=True)
    os.makedirs(hdir, exist_ok=True)
    path = os.path.join(mdir, "%s.json" % mid)
    with open(path, "w") as f:
        json.dump(rep, f, indent=2)
        f.write("\n")
    hist = os.path.join(hdir, "%s.%s.jsonl" % (time.strftime("%Y-%m"), mid))
    with open(hist, "a") as f:
        f.write(json.dumps(history_line(rep)) + "\n")
    return path, hist


def history_line(rep):
    """One line a trend can be drawn from later, not the whole report again."""
    c, s = rep.get("compute") or {}, rep.get("storage") or {}
    vols = dict((v["mount"], v.get("free_bytes")) for v in (s.get("volumes") or []))
    return {"at": rep.get("taken"), "took_ms": rep.get("took_ms"),
            "uptime_s": (rep.get("machine") or {}).get("uptime_s"),
            "memory_free_bytes": c.get("memory_free_bytes"),
            "memory_pressure_percent": c.get("memory_pressure_percent"),
            "busy_percent": c.get("busy_percent"), "load": (c.get("load") or [None])[0],
            "free_bytes": vols,
            "live": len(((rep.get("sessions") or {}).get("live")) or []),
            "errors": len(rep.get("errors") or [])}


def age(iso):
    """How long ago a reading was taken, in words."""
    if not iso:
        return "none"
    try:
        then = time.mktime(time.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return "?"
    s = max(0, int(time.time() - then))
    if s < 90:
        return "just now"
    for n, unit in ((86400, "d"), (3600, "h"), (60, "m")):
        if s >= n:
            return "%d%s" % (s // n, unit)
    return "%ds" % s


def gb(n):
    if not n:
        return "-"
    return "%.0fG" % (n / 1e9) if n < 1e12 else "%.1fT" % (n / 1e12)


# --- commands ---------------------------------------------------------------

def cmd_report(args):
    rep = collect(getattr(args, "account_tag", None))
    if args.json:
        print(json.dumps(rep, indent=2))
        return 0
    try:
        path, hist = write_report(rep)
    except Exception as e:
        print("glyph fleet: could not write the report: %s" % e)
        print("set GLYPH_RIG to a folder you can write to (now %s)" % rig_dir())
        return 2
    m, s = rep.get("machine") or {}, rep.get("storage") or {}
    live = len(((rep.get("sessions") or {}).get("live")) or [])
    agents = [a for a in (rep.get("agents") or []) if a.get("installed")]
    vols = len(s.get("volumes") or [])
    print("%s  %s  %d volume%s, %d agents, %d live, %d ms"
          % (m.get("id"), m.get("name"), vols, "" if vols == 1 else "s", len(agents),
             live, rep.get("took_ms") or 0))
    print("  %s" % tilde(path))
    print("  %s" % tilde(hist))
    for w in s.get("warnings") or []:
        print("  warning  %s" % w)
    for e in rep.get("errors") or []:
        print("  missed   %s: %s" % (e["what"], e["why"]))
    return 0


def ssh_config_hosts():
    """Each Host in ~/.ssh/config, with the address it dials."""
    cfg = os.path.expanduser(os.environ.get("GLYPH_SSH_CONFIG") or "~/.ssh/config")
    out, aliases = {}, []
    if not os.path.exists(cfg):
        return out
    with open(cfg) as f:
        for line in f:
            words = line.replace("=", " ").split()
            if len(words) < 2:
                continue
            if words[0].lower() == "host":
                aliases = [h for h in words[1:] if "*" not in h and "?" not in h]
                for a in aliases:
                    out.setdefault(a, a)
            elif words[0].lower() == "hostname":
                for a in aliases:
                    out[a] = words[1]
    return out


def known_hosts():
    kh = os.path.expanduser(os.environ.get("GLYPH_KNOWN_HOSTS") or "~/.ssh/known_hosts")
    names = set()
    if not os.path.exists(kh):
        return names
    with open(kh) as f:
        for line in f:
            for n in (line.split() or [""])[0].split(","):
                names.add(re.sub(r"\[|\]:\d+", "", n).rstrip("."))
    return names


def ssh_target(mid, record, net):
    """Something ssh can dial for a machine.

    The order is the one `glyph hosts` already follows: an ssh config entry
    wins, then a name ssh has a key for, then the tailnet name. A name that is
    in neither stops on the host key question, and under BatchMode that is a
    refusal rather than a prompt. An entry is matched on its address too, so a
    `Host laptop` that dials this machine's tailnet name or address is found
    and brings its own user with it.
    """
    short = mid.split(".")[0]
    net = net or {}
    addresses = set(x for x in (net.get("dns"), net.get("ip"), short) if x)
    for alias, address in sorted(ssh_config_hosts().items()):
        if alias == short or address.rstrip(".") in addresses:
            return alias
    user = (record or {}).get("user")
    trusted = known_hosts()
    for name in (short, net.get("dns"), net.get("ip")):
        if name and name in trusted:
            return "%s@%s" % (user, name) if user else name
    name = net.get("dns") or short
    return "%s@%s" % (user, name) if user else name


def probe_live(ids, machines, net):
    """Ask every reachable machine for a fresh report, all at once."""
    mine = core.machine_id()
    out = {}

    def ask(mid):
        if mid == mine:
            return collect()      # no ssh to oneself
        target = ssh_target(mid, machines.get(mid), net.get(mid))
        # The path is spelled out because ~/.local/bin is not on a
        # non-interactive PATH, and generous because a machine in the middle of
        # a build can take twenty seconds just to open the session.
        got = run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", target,
                   "~/.local/bin/glyph-fleet report --json"], timeout=45)
        # A login shell may print a banner before the report; take the object
        # and leave the rest, and say so plainly when there is no object at all.
        if not got or "{" not in got:
            note("ssh %s" % mid, (got or "no answer").strip().splitlines()[-1][:120]
                 if got else "no answer over ssh")
            return None
        return json.loads(got[got.index("{"):])

    with futures.ThreadPoolExecutor(max_workers=max(1, len(ids))) as ex:
        jobs = dict((ex.submit(ask, mid), mid) for mid in ids)
        for f in futures.as_completed(jobs):
            mid = jobs[f]
            try:
                rep = f.result()
            except Exception as e:
                rep = None
                print("  %-16s no answer: %s" % (mid, str(e)[:60]))
            if rep:
                out[mid] = rep
                try:
                    write_report(rep)
                except Exception as e:
                    print("  %-16s read but not saved: %s" % (mid, e))
            elif mid not in out:
                print("  %-16s no answer over ssh" % mid)
    return out


def cmd_status(args):
    net = guard("tailscale", tailnet) or {}
    try:
        machines, _ = core.load()
    except Exception:
        machines = {}
    reps = load_reports()
    ids = sorted(set(list(reps) + list(net) + list(machines)))
    if args.machine:
        ids = [m for m in ids if m == args.machine]
        if not ids:
            print("unknown machine: %s" % args.machine)
            return 2
    if args.live:
        mac = [m for m in ids if (net.get(m, {}).get("online") or m == core.machine_id())
               and (net.get(m, {}).get("os") in (None, "macOS"))]
        print("asking %d machines..." % len(mac))
        reps.update(probe_live(mac, machines, net))
    if args.machine and len(ids) == 1:
        return show_machine(ids[0], reps.get(ids[0]), net.get(ids[0]), machines.get(ids[0]))
    if not reps and not net:
        print("no readings in %s and no tailnet." % tilde(rig_dir()))
        print("run: glyph fleet report")
        return 1

    def sort_key(mid):
        up = (net.get(mid) or {}).get("online")
        return (not up, age(((reps.get(mid) or {}).get("taken"))) == "none", mid)

    print("%-16s %-5s %-4s %-9s %-12s %-6s %-11s %-12s %s"
          % ("MACHINE", "ROLE", "UP", "READING", "CHIP", "CORES", "FREE MEM",
             "BOOT DISK", "LIVE"))
    for mid in sorted(ids, key=sort_key):
        rep, n = reps.get(mid) or {}, net.get(mid) or {}
        m = rep.get("machine") or {}
        c = rep.get("compute") or {}
        cores = c.get("cores") or {}
        boot = next((v for v in ((rep.get("storage") or {}).get("volumes") or [])
                     if v.get("role") == "boot"), {})
        mem = "-"
        if c.get("memory_bytes"):
            mem = "%s of %s" % (gb(c.get("memory_free_bytes")), gb(c["memory_bytes"]))
        disk = "-"
        if boot.get("total_bytes"):
            disk = "%d%% of %s" % (boot["used_percent"], gb(boot["total_bytes"]))
        live = (rep.get("sessions") or {}).get("live")
        print("%-16s %-5s %-4s %-9s %-12s %-6s %-11s %-12s %s"
              % (mid[:16],
                 (m.get("role") or (machines.get(mid) or {}).get("role") or "-")[:5],
                 "yes" if n.get("online") else "no",
                 age(rep.get("taken")),
                 (m.get("chip") or n.get("os") or "-")[:12],
                 "%s+%s" % (cores.get("performance") or "-", cores.get("efficiency") or "-")
                 if cores.get("total") else "-",
                 mem, disk, len(live) if live is not None else "-"))
    for mid in sorted(ids):
        for w in ((reps.get(mid) or {}).get("storage") or {}).get("warnings") or []:
            print("warning  %-16s %s" % (mid, w))
    for mid in sorted(ids):
        n = net.get(mid) or {}
        if not n.get("online") and n.get("last_seen"):
            print("offline  %-16s last seen %s ago" % (mid, age(n["last_seen"])))
    print("")
    print("%d machines, %d online, readings from %s"
          % (len(ids), sum(1 for m in ids if (net.get(m) or {}).get("online")),
             tilde(rig_dir())))
    print("glyph fleet status --live    ask every reachable machine now")
    print("glyph fleet status --machine <id>    one machine in full")
    return 0


def show_machine(mid, rep, net, record):
    if not rep:
        print("%s  no reading in %s" % (mid, tilde(rig_dir())))
        if net:
            print("  tailscale  %s, %s" % (net.get("os") or "?",
                                           "online" if net.get("online") else "offline"))
        print("  run: glyph fleet status --machine %s --live" % mid)
        return 1
    m, c = rep.get("machine") or {}, rep.get("compute") or {}
    print("%s  %s" % (m.get("name") or mid, m.get("id")))
    print("  model      %s  %s  %s" % (m.get("marketing") or "-", m.get("model") or "-",
                                       m.get("chip") or "-"))
    print("  macos      %s (%s)" % (m.get("macos") or "-", m.get("build") or "-"))
    print("  role       %s, tag %s, profiles %s" % (m.get("role") or "-", m.get("tag") or "-",
                                                    ",".join(m.get("profiles") or []) or "-"))
    print("  uptime     %s, read %s" % (age(stamp(time.time() - (m.get("uptime_s") or 0))),
                                        age(rep.get("taken"))))
    if net:
        print("  tailscale  %s  %s  %s" % (net.get("dns") or "-", net.get("ip") or "-",
                                           "online" if net.get("online") else "offline"))
    cores = c.get("cores") or {}
    print("  compute    %s cores (%s performance, %s efficiency), %s gpu, load %s, busy %s%%"
          % (cores.get("total"), cores.get("performance"), cores.get("efficiency"),
             c.get("gpu_cores"), (c.get("load") or ["-"])[0], c.get("busy_percent")))
    print("  memory     %s free of %s, pressure %s%%, swap %s"
          % (gb(c.get("memory_free_bytes")), gb(c.get("memory_bytes")),
             c.get("memory_pressure_percent"), gb(c.get("swap_used_bytes")) ))
    b = c.get("battery")
    if b:
        print("  battery    %s%%, %s, %s cycles" % (b.get("percent"), b.get("state"),
                                                    b.get("cycles")))
    print("")
    print("  %-28s %-9s %-7s %-8s %s" % ("VOLUME", "KIND", "ROLE", "FREE", "USED"))
    for v in ((rep.get("storage") or {}).get("volumes") or []):
        print("  %-28s %-9s %-7s %-8s %s%%" % (v["mount"][:28], v.get("kind") or "-",
                                               v.get("role") or "-", gb(v.get("free_bytes")),
                                               v.get("used_percent")))
    print("")
    print("  %-14s %-10s %-20s %s" % ("AGENT", "VERSION", "ACCOUNT", "USAGE"))
    for a in rep.get("agents") or []:
        if not a.get("installed"):
            continue
        acc = a.get("account") or {}
        who = acc.get("label") or acc.get("name") or acc.get("mode") or "-"
        u = a.get("usage") or {}
        w5 = (u.get("window_5h") or {}).get("percent")
        use = "%s%% of the 5h window" % w5 if w5 is not None else (u.get("source") or "-")
        print("  %-14s %-10s %-20s %s" % (a["id"], a.get("version") or "?", who, use))
    live = (rep.get("sessions") or {}).get("live") or []
    print("")
    for s in live:
        print("  live  %-46s %-7s %s" % ((s.get("name") or s.get("agent") or "?")[:46],
                                         s.get("pid"), s.get("cwd") or "-"))
    if not live:
        print("  no agent sessions running")
    inf = (rep.get("inference") or {}).get("ollama") or {}
    if inf.get("running"):
        print("")
        print("  ollama  %s" % ", ".join(m["name"] for m in (inf.get("models") or [])[:8]))
    for w in ((rep.get("storage") or {}).get("warnings") or []):
        print("  warning  %s" % w)
    for e in rep.get("errors") or []:
        print("  missed   %s: %s" % (e["what"], e["why"]))
    return 0


def config_diff(reps):
    """Rows for the config keys that are not the same on every machine.

    Each row is (key, {machine: value}, the odd machine out or None).
    """
    ids = sorted(reps)
    rows = []
    keys = set()
    for rep in reps.values():
        keys |= set((rep.get("config") or {}).keys())
    for key in sorted(keys):
        vals = dict((mid, (reps[mid].get("config") or {}).get(key)) for mid in ids)
        if len(set(vals.values())) == 1:
            continue
        odd = None
        counted = {}
        for mid, v in vals.items():
            counted.setdefault(v, []).append(mid)
        alone = [mids for mids in counted.values() if len(mids) == 1]
        if len(counted) == 2 and len(alone) == 1 and len(ids) > 2:
            odd = alone[0][0]
        elif len(ids) == 2:
            odd = next((mid for mid, v in vals.items() if v is None), None)
            odd = next(m for m in ids if m != odd) if odd else None
        rows.append((key, vals, odd))
    return rows


def cmd_diff(args):
    reps = load_reports()
    if len(reps) < 2:
        print("%d machine reading in %s. two is the fewest a diff can use."
              % (len(reps), tilde(rig_dir())))
        print("run glyph fleet report on the other machine, or: glyph fleet status --live")
        return 1
    ids = sorted(reps)
    rows = config_diff(reps)
    w = max(20, max(len(m) for m in ids) + 2)
    print("%-38s %s" % ("KEY", "".join("%-*s" % (w, m) for m in ids)))
    for key, vals, odd in rows:
        line = "%-38s %s" % (key[:38], "".join("%-*s" % (w, (vals[m] or "-")[:w - 1])
                                               for m in ids))
        print("%s%s" % (line, "  only %s" % odd if odd and sum(
            1 for v in vals.values() if v) == 1 else ("  %s differs" % odd if odd else "")))
    print("")
    print("%d of %d keys differ across %d machines"
          % (len(rows), len(set().union(*[set((r.get("config") or {}).keys())
                                          for r in reps.values()])), len(ids)))
    return 0
