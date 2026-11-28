"""glyph-rig-helper accepts only its fixed verbs and checked values (run in dry mode, never as root)."""
import os, subprocess

H = os.path.join(os.path.dirname(os.path.abspath(__file__)), "glyph-rig-helper")


def run(*args):
    r = subprocess.run(["sh", H, *args], capture_output=True, text=True,
                       env={"GLYPH_RIG_HELPER_DRY": "1", "PATH": "/usr/bin:/bin"})
    return r.returncode, r.stdout.strip()


def main():
    ok = [
        (("pmset", "battery", "displaysleep", "10"), "pmset -b displaysleep 10"),
        (("pmset", "ac", "sleep", "0"), "pmset -c sleep 0"),
        (("pmset", "all", "womp", "on"), "pmset -a womp 1"),
        (("firewall", "on"), "/usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on"),
        (("firewall", "stealth", "off"), "/usr/libexec/ApplicationFirewall/socketfilterfw --setstealthmode off"),
        (("version",), "glyph-rig-helper 1"),
    ]
    for args, want in ok:
        code, out = run(*args)
        assert code == 0 and out == want, (args, code, out)
    refused = [
        ("pmset", "battery", "displaysleep", "181"),
        ("pmset", "battery", "displaysleep", "10; rm -rf /"),
        ("pmset", "battery", "displaysleep", "-1"),
        ("pmset", "wall", "sleep", "5"),
        ("pmset", "ac", "hibernatemode", "0"),
        ("pmset", "ac", "womp", "yes"),
        ("pmset", "ac", "sleep"),
        ("pmset", "ac", "sleep", "5", "extra"),
        ("firewall", "maybe"),
        ("firewall", "stealth", "on", "x"),
        ("sh", "-c", "id"),
        (),
    ]
    for args in refused:
        code, out = run(*args)
        assert code == 2 and out == "", (args, code, out)
    print("ok   glyph-rig-helper: %d allowed, %d refused" % (len(ok), len(refused)))


if __name__ == "__main__":
    main()
