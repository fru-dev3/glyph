"""What Glyph Rig reads and sets on each Mac beyond the core report: power, traffic, open ports,
displays, sound, and the settings a template can hold (knobs).

Reading needs no admin. Changing runs only from a card the owner clicked in Rig, through the fixed
subcommands at the end of this file: every value is checked against the knob table before anything
runs, and settings that need root go through glyph-rig-helper (install-rig-helper.sh), never sudo
with a free command line.
"""
import json
import os
import re
import shutil
import subprocess
import time

HELPER = "/usr/local/libexec/glyph-rig-helper"
AWAKE_LABEL = "dev.fru.rig-awake"


def run(cmd, timeout=10, input=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL if input is None else None, input=input)
    except Exception:
        return None
    return r.stdout if r.returncode == 0 else None


def ok(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except Exception as e:
        return False, str(e)
    return r.returncode == 0, (r.stderr or r.stdout or "").strip().splitlines()[-1:] and (r.stderr or r.stdout).strip().splitlines()[-1] or ""


# --- power ------------------------------------------------------------------

def pmset_custom(text):
    """`pmset -g custom` as {"battery": {...}, "ac": {...}}, numbers as ints."""
    out, cur = {}, None
    for line in (text or "").splitlines():
        if line.startswith("Battery Power"):
            cur = out.setdefault("battery", {})
        elif line.startswith("AC Power"):
            cur = out.setdefault("ac", {})
        elif cur is not None:
            mo = re.match(r"\s+(\w+)\s+(-?\d+)", line)
            if mo:
                cur[mo.group(1)] = int(mo.group(2))
    return out


def assertions(text):
    """Who is keeping the Mac awake: one row per process holding a sleep assertion."""
    rows = []
    for line in (text or "").splitlines():
        mo = re.search(r"pid \d+\(([^)]+)\): \[[^\]]*\] ([\d:]+) (\w+) named: \"?([^\"]*)\"?", line)
        if mo and mo.group(3) in ("PreventUserIdleSystemSleep", "PreventSystemSleep",
                                  "PreventUserIdleDisplaySleep", "PreventDisplaySleep", "NoIdleSleepAssertion"):
            rows.append({"process": mo.group(1), "for": mo.group(2), "kind": mo.group(3),
                         "name": mo.group(4).strip()})
    return rows[:12]


def restarts(text):
    """`last reboot` and `last shutdown` lines, newest first."""
    rows = []
    for line in (text or "").splitlines():
        mo = re.match(r"(reboot|shutdown)\s+time\s+(.+?)\s*$", line)
        if mo:
            rows.append({"kind": mo.group(1), "at": mo.group(2)})
    return rows[:8]


def power_block():
    batt = run(["ioreg", "-rc", "AppleSmartBattery", "-d1"], timeout=3) or ""

    def num(key):
        mo = re.search(r'"%s"\s*=\s*(\d+)' % key, batt)
        return int(mo.group(1)) if mo else None

    adapter = run(["pmset", "-g", "adapter"], timeout=3) or ""
    watts = re.search(r"Wattage\s*=\s*(\d+)W", adapter)
    health = None
    if num("AppleRawMaxCapacity") and num("DesignCapacity"):
        health = round(100.0 * num("AppleRawMaxCapacity") / num("DesignCapacity"))
    temp = num("Temperature")
    out = {
        "has_battery": bool(batt.strip()),
        "adapter_watts": int(watts.group(1)) if watts else None,
        "on_adapter": bool(watts) or "AC Power" in (run(["pmset", "-g", "ps"], timeout=3) or ""),
        "battery_health_percent": health,
        "battery_max_mah": num("AppleRawMaxCapacity"),
        "battery_design_mah": num("DesignCapacity"),
        "battery_temp_c": round(temp / 100.0, 1) if temp else None,
        "settings": pmset_custom(run(["pmset", "-g", "custom"], timeout=3)),
        "awake_holders": assertions(run(["pmset", "-g", "assertions"], timeout=3)),
        "restarts": restarts(run(["last", "reboot", "shutdown"], timeout=5)),
        "rig_awake": awake_state(),
    }
    return out


# --- traffic and ports --------------------------------------------------------

def netstat_bytes(text):
    """Bytes in and out per interface since it came up, from `netstat -ib` (one Link row each)."""
    out = {}
    for line in (text or "").splitlines()[1:]:
        f = line.split()
        if len(f) >= 10 and f[2].startswith("<Link") and re.match(r"(en|utun|bridge)\d", f[0]):
            try:
                ib, ob = int(f[6]), int(f[9])
            except ValueError:
                continue
            if f[0] not in out:
                out[f[0]] = {"in_bytes": ib, "out_bytes": ob}
    return out


def traffic_block():
    a = netstat_bytes(run(["netstat", "-ib"], timeout=3))
    time.sleep(1.0)
    b = netstat_bytes(run(["netstat", "-ib"], timeout=3))
    rows = []
    for name, v in b.items():
        if not (v["in_bytes"] or v["out_bytes"]):
            continue
        p = a.get(name, v)
        rows.append({"interface": name, "in_bytes": v["in_bytes"], "out_bytes": v["out_bytes"],
                     "in_mbps": round((v["in_bytes"] - p["in_bytes"]) * 8 / 1e6, 2),
                     "out_mbps": round((v["out_bytes"] - p["out_bytes"]) * 8 / 1e6, 2)})
    rows.sort(key=lambda r: -(r["in_bytes"] + r["out_bytes"]))
    return {"interfaces": rows[:6]}


def scope(addr):
    """Who can reach a listening address: this Mac, the tailnet, the home network, or every network."""
    host = addr.rsplit(":", 1)[0].strip("[]")
    if host in ("127.0.0.1", "::1", "localhost"):
        return "local"
    if host == "*":
        return "all"
    if host.startswith("100.") or host.startswith("fd7a:115c"):
        return "tailscale"
    return "lan"


def listeners(text):
    seen, rows = set(), []
    for line in (text or "").splitlines()[1:]:
        f = line.split()
        if len(f) < 9:
            continue
        proc, addr = f[0].replace("\\x20", " "), f[8]
        port = addr.rsplit(":", 1)[-1]
        key = (proc, port, scope(addr))
        if key in seen:
            continue
        seen.add(key)
        rows.append({"process": proc, "port": int(port) if port.isdigit() else port, "scope": key[2]})
    order = {"all": 0, "lan": 1, "tailscale": 2, "local": 3}
    rows.sort(key=lambda r: (order[r["scope"]], str(r["process"]).lower()))
    return rows


def ports_block():
    rows = listeners(run(["lsof", "+c", "0", "-nP", "-iTCP", "-sTCP:LISTEN"], timeout=8))
    return {"listening": len(rows), "open": [r for r in rows if r["scope"] != "local"][:40],
            "local": len([r for r in rows if r["scope"] == "local"])}


# --- displays and sound -------------------------------------------------------

def profiler(kind):
    try:
        return json.loads(run(["system_profiler", kind, "-json"], timeout=20) or "{}").get(kind) or []
    except ValueError:
        return []


def displays_block():
    rows = []
    for gpu in profiler("SPDisplaysDataType"):
        for d in gpu.get("spdisplays_ndrvs") or []:
            res = d.get("_spdisplays_resolution") or d.get("spdisplays_resolution") or ""
            mo = re.match(r"(\d+) x (\d+)(?: @ ([\d.]+)Hz)?", res)
            rows.append({"name": d.get("_name"),
                         "width": int(mo.group(1)) if mo else None, "height": int(mo.group(2)) if mo else None,
                         "hz": float(mo.group(3)) if mo and mo.group(3) else None,
                         "main": d.get("spdisplays_main") == "spdisplays_yes",
                         "builtin": d.get("spdisplays_connection_type") == "spdisplays_internal",
                         "virtual": "virtual" in str(d.get("spdisplays_display_type", "")).lower()
                                    or "Jump" in str(d.get("_name", ""))})
    return {"displays": rows}


def audio_block():
    outs, ins = [], []
    for group in profiler("SPAudioDataType"):
        for d in group.get("_items") or []:
            name = d.get("_name")
            virtual = d.get("coreaudio_device_transport") == "coreaudio_device_type_virtual"
            if d.get("coreaudio_device_output"):
                outs.append({"name": name, "default": bool(d.get("coreaudio_default_audio_output_device")), "virtual": virtual})
            if d.get("coreaudio_device_input"):
                ins.append({"name": name, "default": bool(d.get("coreaudio_default_audio_input_device")), "virtual": virtual})
    vol = run(["osascript", "-e", "get volume settings"], timeout=4) or ""
    num = lambda k: int(re.search(k + r":(\d+)", vol).group(1)) if re.search(k + r":(\d+)", vol) else None
    return {"outputs": outs, "inputs": ins, "output_volume": num("output volume"),
            "input_volume": num("input volume"), "can_switch": switcher() is not None}


def switcher():
    for p in ("/opt/homebrew/bin/SwitchAudioSource", "/usr/local/bin/SwitchAudioSource"):
        if os.access(p, os.X_OK):
            return p
    return None


# --- knobs: the settings a template holds --------------------------------------
# id: (label, group, type, how, where, default, restart, admin, laptop_only, shareable)
# type: bool | int:<lo>-<hi> | folder | minutes ; how: defaults | pmset:<source>:<setting> | firewall:<what>
KNOBS = {
    "dock.autohide": ("Hide the Dock", "Dock", "bool", "defaults", ("com.apple.dock", "autohide"), "off", "Dock", False, False, True),
    "dock.tilesize": ("Dock icon size", "Dock", "int:16-128", "defaults", ("com.apple.dock", "tilesize"), "48", "Dock", False, False, True),
    "dock.show_recents": ("Show recent apps in the Dock", "Dock", "bool", "defaults", ("com.apple.dock", "show-recents"), "on", "Dock", False, False, True),
    "finder.show_extensions": ("Show every file extension", "Finder", "bool", "defaults", ("NSGlobalDomain", "AppleShowAllExtensions"), "off", "Finder", False, False, True),
    "finder.show_pathbar": ("Path bar in Finder", "Finder", "bool", "defaults", ("com.apple.finder", "ShowPathbar"), "off", "Finder", False, False, True),
    "finder.show_hidden": ("Show hidden files", "Finder", "bool", "defaults", ("com.apple.finder", "AppleShowAllFiles"), "off", "Finder", False, False, True),
    "keyboard.key_repeat": ("Key repeat speed (lower is faster)", "Keyboard", "int:1-120", "defaults", ("NSGlobalDomain", "KeyRepeat"), "6", None, False, False, True),
    "keyboard.initial_key_repeat": ("Delay before repeat (lower is shorter)", "Keyboard", "int:10-120", "defaults", ("NSGlobalDomain", "InitialKeyRepeat"), "25", None, False, False, True),
    "screenshots.folder": ("Screenshots go to", "Screenshots", "folder", "defaults", ("com.apple.screencapture", "location"), "~/Desktop", "SystemUIServer", False, False, True),
    "power.battery.displaysleep": ("Display sleeps on battery (minutes, 0 never)", "Power", "minutes", "pmset", ("battery", "displaysleep"), None, None, True, True, True),
    "power.battery.sleep": ("Mac sleeps on battery (minutes, 0 never)", "Power", "minutes", "pmset", ("battery", "sleep"), None, None, True, True, True),
    "power.ac.displaysleep": ("Display sleeps on charger (minutes, 0 never)", "Power", "minutes", "pmset", ("ac", "displaysleep"), None, None, True, False, True),
    "power.ac.sleep": ("Mac sleeps on charger (minutes, 0 never)", "Power", "minutes", "pmset", ("ac", "sleep"), None, None, True, False, True),
    "power.ac.womp": ("Wake for network on charger", "Power", "bool", "pmset", ("ac", "womp"), None, None, True, False, True),
    "firewall.on": ("Firewall", "Security", "bool", "firewall", ("global",), None, None, True, False, True),
    "firewall.stealth": ("Stealth mode", "Security", "bool", "firewall", ("stealth",), None, None, True, False, True),
}


def knob_info(kid):
    k = KNOBS[kid]
    return {"id": kid, "label": k[0], "group": k[1], "type": k[2], "restart": k[6], "admin": k[7],
            "laptop_only": k[8], "shareable": k[9]}


def boolword(v):
    return "on" if str(v).strip().lower() in ("1", "true", "yes", "on") else "off"


def read_knob(kid, custom=None, fw=None):
    label, group, typ, how, where, default, restart, admin, laptop, share = KNOBS[kid]
    if how == "defaults":
        v = run(["defaults", "read", where[0], where[1]], timeout=3)
        if v is None:
            return default
        v = v.strip()
        if typ == "bool":
            return boolword(v)
        if typ == "folder":
            return v.replace(os.path.expanduser("~"), "~", 1) if v.startswith(os.path.expanduser("~")) else v
        return v
    if how == "pmset":
        custom = custom if custom is not None else pmset_custom(run(["pmset", "-g", "custom"], timeout=3))
        v = (custom.get(where[0]) or {}).get(where[1])
        if v is None:
            return None
        return boolword(v) if typ == "bool" else str(v)
    if how == "firewall":
        fw_bin = "/usr/libexec/ApplicationFirewall/socketfilterfw"
        out = run([fw_bin, "--getglobalstate" if where[0] == "global" else "--getstealthmode"], timeout=3) or ""
        if not out:
            return None
        return "on" if re.search(r"enabled|is on", out, re.I) else "off"
    return None


def knobs_block():
    custom = pmset_custom(run(["pmset", "-g", "custom"], timeout=3))
    vals = {}
    for kid in KNOBS:
        try:
            vals[kid] = read_knob(kid, custom=custom)
        except Exception:
            vals[kid] = None
    return {"values": vals, "helper": helper_ready()}


def helper_ready():
    try:
        r = subprocess.run(["sudo", "-n", HELPER, "version"], capture_output=True, text=True, timeout=5,
                           stdin=subprocess.DEVNULL)
        return r.returncode == 0
    except Exception:
        return False


def check_value(kid, value):
    """The value in the knob's own form, or a ValueError saying why not."""
    typ = KNOBS[kid][2]
    v = str(value).strip()
    if typ == "bool":
        if v.lower() not in ("on", "off", "true", "false", "1", "0", "yes", "no"):
            raise ValueError("%s is on or off, not %r" % (kid, value))
        return boolword(v)
    if typ.startswith("int:") or typ == "minutes":
        lo, hi = (0, 180) if typ == "minutes" else map(int, typ[4:].split("-"))
        if not re.fullmatch(r"\d{1,4}", v) or not lo <= int(v) <= hi:
            raise ValueError("%s is a whole number from %d to %d, not %r" % (kid, lo, hi, value))
        return str(int(v))
    if typ == "folder":
        if not v.startswith(("~/", "/")) or ".." in v.split("/") or any(c in v for c in "\n\r\0"):
            raise ValueError("%s is a folder path, not %r" % (kid, value))
        return v
    raise ValueError("unknown type for %s" % kid)


def write_knob(kid, value):
    label, group, typ, how, where, default, restart, admin, laptop, share = KNOBS[kid]
    if how == "defaults":
        if typ == "bool":
            cmd = ["defaults", "write", where[0], where[1], "-bool", "true" if value == "on" else "false"]
        elif typ.startswith("int:"):
            cmd = ["defaults", "write", where[0], where[1], "-int", value]
        else:
            path = os.path.expanduser(value)
            os.makedirs(path, exist_ok=True)
            cmd = ["defaults", "write", where[0], where[1], "-string", path]
        return ok(cmd)
    if not helper_ready():
        return False, "the helper for power and firewall settings is not set up on this Mac (Settings, Set up)"
    if how == "pmset":
        return ok(["sudo", "-n", HELPER, "pmset", where[0], where[1], value])
    if how == "firewall":
        args = [value] if where[0] == "global" else ["stealth", value]
        return ok(["sudo", "-n", HELPER, "firewall"] + args)
    return False, "no way to set %s" % kid


# --- templates -------------------------------------------------------------------

def read_template(path):
    """A template file: frontmatter (extends, machines) and `- knob = value` lines."""
    meta, values = {}, {}
    try:
        text = open(path).read()
    except OSError:
        return None
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = parts[2]
    for line in body.splitlines():
        mo = re.match(r"\s*-\s*([a-z0-9_.]+)\s*=\s*(.+?)\s*$", line)
        if mo and mo.group(1) in KNOBS:
            try:
                values[mo.group(1)] = check_value(mo.group(1), mo.group(2))
            except ValueError:
                pass
    title = re.search(r"^#\s+(.+)$", body, re.M)
    return {"id": os.path.splitext(os.path.basename(path))[0], "title": title.group(1).strip() if title else None,
            "extends": meta.get("extends") or None,
            "machines": [m.strip() for m in (meta.get("machines") or "").split(",") if m.strip()],
            "values": values}


def templates(folder):
    out = {}
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return out
    for n in names:
        if n.endswith(".md") and not n.startswith("."):
            t = read_template(os.path.join(folder, n))
            if t:
                out[t["id"]] = t
    return out


def resolve(all_t, mid):
    """The template a machine follows: one that names it, else every-mac. Its chain is merged, leaf wins."""
    leaf = next((t for t in all_t.values() if mid in t["machines"]), None) or all_t.get("every-mac")
    if not leaf:
        return None
    chain, t, seen = [], leaf, set()
    while t and t["id"] not in seen:
        seen.add(t["id"])
        chain.append(t)
        t = all_t.get(t["extends"]) if t["extends"] else None
    want = {}
    for t in reversed(chain):
        want.update(t["values"])
    return {"id": leaf["id"], "title": leaf["title"] or leaf["id"], "chain": [t["id"] for t in chain], "want": want}


def template_block(mid, folder, values, laptop):
    all_t = templates(folder)
    r = resolve(all_t, mid)
    if not r:
        return {"name": None, "drift": []}
    drift = []
    for kid, want in sorted(r["want"].items()):
        if KNOBS[kid][8] and not laptop:
            continue
        have = values.get(kid)
        if have is not None and have != want:
            drift.append(dict(knob_info(kid), have=have, want=want))
    return {"name": r["id"], "title": r["title"], "chain": r["chain"], "want": r["want"], "drift": drift}


# --- actions (each only from a card the owner clicked) ------------------------------

def cmd_knobs(args):
    """Read every knob; --apply id=value,... sets them (checked, re-read after, restarts batched);
    --capture prints the shareable ones as template lines."""
    if args.capture:
        vals = knobs_block()["values"]
        lines = ["- %s = %s" % (k, v) for k, v in sorted(vals.items()) if v is not None and KNOBS[k][9]]
        print("\n".join(lines))
        return 0
    if not args.apply:
        print(json.dumps({"knobs": [dict(knob_info(k), value=v) for k, v in knobs_block()["values"].items()]}, indent=2))
        return 0
    want = {}
    for pair in args.apply.split(","):
        if "=" not in pair:
            continue
        k, v = pair.split("=", 1)
        k = k.strip()
        if k not in KNOBS:
            print(json.dumps({"error": "not a setting Rig knows: %s" % k}))
            return 2
        try:
            want[k] = check_value(k, v)
        except ValueError as e:
            print(json.dumps({"error": str(e)}))
            return 2
    rows, restart = [], set()
    for k, v in want.items():
        before = read_knob(k)
        if before == v:
            rows.append({"id": k, "before": before, "after": before, "ok": True, "note": "already so"})
            continue
        good, why = write_knob(k, v)
        if good and KNOBS[k][6]:
            restart.add(KNOBS[k][6])
        rows.append({"id": k, "before": before, "want": v, "ok": good, "why": None if good else why})
    for proc in sorted(restart):
        run(["killall", proc], timeout=5)
    time.sleep(0.5 if restart else 0)
    for r in rows:
        if "want" in r:
            r["after"] = read_knob(r["id"])
            r["ok"] = r["ok"] and r["after"] == r["want"]
    print(json.dumps({"taken": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "changes": rows,
                      "restarted": sorted(restart)}, indent=2))
    return 0 if all(r["ok"] for r in rows) else 1


def awake_state():
    out = run(["launchctl", "list", AWAKE_LABEL], timeout=3)
    if not out:
        return None
    plist = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % AWAKE_LABEL)
    mode = None
    try:
        args = subprocess.run(["plutil", "-extract", "ProgramArguments", "json", "-o", "-", plist],
                              capture_output=True, text=True, timeout=3).stdout
        a = json.loads(args or "[]")
        mode = "plugged" if "-s" in a else ("until %s" % a[a.index("-t") + 1] if "-t" in a else "on")
    except Exception:
        pass
    return {"on": '"PID"' in out, "mode": mode}


def cmd_awake(args):
    """Keep this Mac awake: --minutes N, --until-stopped, --while-plugged; --stop ends it.

    A LaunchAgent runs caffeinate, so it lasts after the SSH session that asked for it has gone."""
    plist = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % AWAKE_LABEL)
    uid = str(os.getuid())
    subprocess.run(["launchctl", "bootout", "gui/%s/%s" % (uid, AWAKE_LABEL)], capture_output=True)
    if args.stop:
        if os.path.exists(plist):
            os.unlink(plist)
        print(json.dumps({"awake": False}))
        return 0
    if args.minutes is not None:
        if not 1 <= args.minutes <= 24 * 60:
            print(json.dumps({"error": "minutes from 1 to 1440"}))
            return 2
        cmd = ["/usr/bin/caffeinate", "-dims", "-t", str(args.minutes * 60)]
    elif args.while_plugged:
        cmd = ["/usr/bin/caffeinate", "-s"]
    else:
        cmd = ["/usr/bin/caffeinate", "-dims"]
    os.makedirs(os.path.dirname(plist), exist_ok=True)
    items = "".join("<string>%s</string>" % c for c in cmd)
    with open(plist, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0"><dict>'
                '<key>Label</key><string>%s</string><key>ProgramArguments</key><array>%s</array>'
                '<key>RunAtLoad</key><true/></dict></plist>\n' % (AWAKE_LABEL, items))
    good, why = ok(["launchctl", "bootstrap", "gui/%s" % uid, plist])
    print(json.dumps({"awake": good, "why": None if good else why, "command": " ".join(cmd)}))
    return 0 if good else 1


def cmd_audio(args):
    """Use a sound device by its exact name, one this Mac lists."""
    sw = switcher()
    if not sw:
        print(json.dumps({"error": "switching needs SwitchAudioSource (brew install switchaudio-osx)"}))
        return 2
    kind = "input" if args.input else "output"
    names = (run([sw, "-a", "-t", kind], timeout=5) or "").splitlines()
    if args.use not in names:
        print(json.dumps({"error": "no %s called %s on this Mac" % (kind, args.use)}))
        return 2
    good, why = ok([sw, "-t", kind, "-s", args.use])
    print(json.dumps({"ok": good, "why": None if good else why, "now": (run([sw, "-c", "-t", kind]) or "").strip()}))
    return 0 if good else 1


def cmd_move(args):
    """Move a folder or file to the archive: copied with rsync and checked, then the originals removed
    file by file (rsync --remove-source-files), never a blanket removal. Prints where it went, for undo.

    --dest is a folder on this Mac, or host:folder over SSH."""
    src = os.path.abspath(os.path.expanduser(args.path))
    home = os.path.expanduser("~")
    if not os.path.exists(src) or src in ("/", home) or not src.startswith((home + "/", "/Volumes/")):
        print(json.dumps({"error": "only a folder or file inside your home folder or on a drive can be moved"}))
        return 2
    dest = args.dest.rstrip("/") + "/"
    stamp = time.strftime("%Y-%m-%d")
    rel = src[len(home) + 1:] if src.startswith(home + "/") else src.lstrip("/")
    target = dest + stamp + "/" + rel
    parent = os.path.dirname(target.split(":", 1)[-1])
    if ":" in dest:
        host = dest.split(":", 1)[0]
        good, why = ok(["ssh", "-o", "BatchMode=yes", host, "mkdir -p '%s'" % parent.replace("'", "'\\''")])
    else:
        os.makedirs(parent, exist_ok=True)
        good, why = True, ""
    if not good:
        print(json.dumps({"error": "could not reach the archive: %s" % why}))
        return 1
    srcarg = src + ("/" if os.path.isdir(src) else "")
    good, why = ok(["rsync", "-a", srcarg, target + ("/" if os.path.isdir(src) else "")], timeout=24 * 3600)
    if not good:
        print(json.dumps({"error": "copy failed, nothing removed: %s" % why}))
        return 1
    check = subprocess.run(["rsync", "-an", "--checksum", "--itemize-changes", srcarg,
                            target + ("/" if os.path.isdir(src) else "")], capture_output=True, text=True)
    if check.returncode != 0 or check.stdout.strip():
        print(json.dumps({"error": "the copy does not match yet, nothing removed"}))
        return 1
    subprocess.run(["rsync", "-a", "--remove-source-files", srcarg, target + ("/" if os.path.isdir(src) else "")],
                   capture_output=True)
    if os.path.isdir(src):
        subprocess.run(["find", src, "-depth", "-type", "d", "-empty", "-delete"], capture_output=True)
    rec = {"moved": src.replace(home, "~", 1), "to": target, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    # The undo list (the rule: every move can be put back). Beside the reports, so every Mac reads it.
    log = os.path.join(os.path.expanduser(os.environ.get("GLYPH_RIG") or "~/.config/glyph/rig"), "moves.jsonl")
    try:
        with open(log, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError:
        rec["unlogged"] = log
    print(json.dumps(rec))
    return 0


def cmd_updates(args):
    """What is waiting: Homebrew (offline, from its last fetch) and, with --macos, Apple's list."""
    out = {"brew": [], "macos": None}
    brew = shutil.which("brew") or ("/opt/homebrew/bin/brew" if os.path.exists("/opt/homebrew/bin/brew") else None)
    if brew:
        try:
            j = json.loads(run([brew, "outdated", "--json=v2"], timeout=60) or "{}")
            out["brew"] = [{"name": f["name"], "have": (f.get("installed_versions") or ["?"])[-1],
                            "new": f.get("current_version"), "cask": False} for f in j.get("formulae", [])] + \
                          [{"name": c["name"], "have": (c.get("installed_versions") or ["?"])[-1] if isinstance(c.get("installed_versions"), list) else c.get("installed_versions"),
                            "new": c.get("current_version"), "cask": True} for c in j.get("casks", [])]
        except ValueError:
            pass
    if args.macos:
        text = run(["softwareupdate", "-l"], timeout=180) or ""
        out["macos"] = [m.group(1).strip() for m in re.finditer(r"\* Label: (.+)", text)]
    print(json.dumps(out, indent=2))
    return 0


def add_commands(sub):
    k = sub.add_parser("knobs", help="settings a template can hold; --apply id=value,... sets them")
    k.add_argument("--apply")
    k.add_argument("--capture", action="store_true", help="the shareable ones, as template lines")
    k.set_defaults(func=cmd_knobs)
    a = sub.add_parser("awake", help="keep this Mac awake: --minutes N, --until-stopped, --while-plugged, --stop")
    a.add_argument("--minutes", type=int)
    a.add_argument("--until-stopped", action="store_true")
    a.add_argument("--while-plugged", action="store_true")
    a.add_argument("--stop", action="store_true")
    a.set_defaults(func=cmd_awake)
    s = sub.add_parser("audio", help="use a sound device by name")
    s.add_argument("--use", required=True)
    s.add_argument("--input", action="store_true")
    s.set_defaults(func=cmd_audio)
    m = sub.add_parser("move", help="move a folder to the archive, checked, with a record to undo it")
    m.add_argument("path")
    m.add_argument("--dest", required=True)
    m.set_defaults(func=cmd_move)
    u = sub.add_parser("updates", help="updates waiting: Homebrew, and Apple's with --macos")
    u.add_argument("--macos", action="store_true")
    u.set_defaults(func=cmd_updates)
