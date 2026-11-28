"""Checks for macs.py: the parsers, the knob values it refuses, templates and their layering."""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glyph_spaces import macs

fails = 0
def check(ok, what):
    global fails
    print(("  ok    " if ok else "  FAIL  ") + what)
    fails += 0 if ok else 1

c = macs.pmset_custom("Battery Power:\n displaysleep         0\n sleep                1\nAC Power:\n sleep                0\n womp                 1\n")
check(c == {"battery": {"displaysleep": 0, "sleep": 1}, "ac": {"sleep": 0, "womp": 1}}, "pmset custom by power source")

check([macs.scope(a) for a in ("127.0.0.1:5000", "[::1]:5000", "*:8791", "100.64.0.9:22", "10.0.0.5:80")]
      == ["local", "local", "all", "tailscale", "lan"], "who can reach a listening port")

ns = ("Name Mtu Network Address Ipkts Ierrs Ibytes Opkts Oerrs Obytes Coll\n"
      "en0 1500 <Link#11> aa:bb 10 0 2000 5 0 900 0\n"
      "en0 1500 10.0.0/24 10.0.0.4 10 - 2000 5 - 900 -\n"
      "lo0 16384 <Link#1> 1 0 50 1 0 50 0\n")
check(macs.netstat_bytes(ns) == {"en0": {"in_bytes": 2000, "out_bytes": 900}}, "traffic per interface, loopback left out")

r = macs.restarts("reboot    time                                Thu Nov 19 22:19\nshutdown  time                                Sat Oct 31 05:53\n\nwtmp begins")
check([x["kind"] for x in r] == ["reboot", "shutdown"], "restarts newest first")

for kid, bad in (("dock.tilesize", "500"), ("dock.tilesize", "1; rm -rf ~"), ("dock.autohide", "maybe"),
                 ("power.battery.sleep", "-1"), ("screenshots.folder", "~/../../etc"), ("screenshots.folder", "rel/path")):
    try:
        macs.check_value(kid, bad); check(False, "refuses %s = %r" % (kid, bad))
    except ValueError:
        check(True, "refuses %s = %r" % (kid, bad))
check(macs.check_value("dock.autohide", "TRUE") == "on" and macs.check_value("power.ac.sleep", "007") == "7",
      "values in the knob's own form")

with tempfile.TemporaryDirectory() as d:
    open(os.path.join(d, "every-mac.md"), "w").write("# Every Mac\n- dock.tilesize = 48\n- dock.autohide = off\n- nonsense.knob = 3\n- dock.show_recents = sometimes\n")
    open(os.path.join(d, "laptop.md"), "w").write("---\nextends: every-mac\nmachines: lap-1\n---\n# Laptop\n- dock.autohide = on\n- power.battery.sleep = 10\n")
    t = macs.templates(d)
    check(set(t["every-mac"]["values"]) == {"dock.tilesize", "dock.autohide"}, "unknown settings and bad values are left out")
    r = macs.resolve(t, "lap-1")
    check(r["chain"] == ["laptop", "every-mac"] and r["want"]["dock.autohide"] == "on" and r["want"]["dock.tilesize"] == "48",
          "a template layers on the one it extends, its own lines winning")
    check(macs.resolve(t, "other")["id"] == "every-mac", "a Mac no template names follows every-mac")
    b = macs.template_block("lap-1", d, {"dock.tilesize": "36", "dock.autohide": "on", "power.battery.sleep": "1"}, False)
    check([x["id"] for x in b["drift"]] == ["dock.tilesize"], "drift lists differences, battery settings only on a laptop")

out = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "glyph-fleet"),
                      "knobs", "--apply", "dock.tilesize=1;reboot"], capture_output=True, text=True)
check(out.returncode == 2 and "whole number" in out.stdout, "knobs --apply refuses a value before running anything")
out = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "glyph-fleet"),
                      "knobs", "--apply", "ssh.root=on"], capture_output=True, text=True)
check(out.returncode == 2 and "not a setting" in out.stdout, "knobs --apply refuses a setting it does not know")

print("macs: %s" % ("ok" if not fails else "%d FAILED" % fails))
sys.exit(1 if fails else 0)
