#!/usr/bin/env python3
"""glyph fleet, checked against facts made up for the purpose.

    python3 spaces/test_fleet.py

No framework and no fixtures on disk: the machines here are invented, and the
one test that runs the real collector first takes away its ability to run a
command, which is the whole promise worth checking. A reader that cannot read
has to become a line in `errors` rather than a traceback, because a caller
losing a whole machine over one unreadable fact is the failure that matters.
"""
import os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from glyph_spaces import core, fleet


def test_machine_id():
    """A machine is keyed by its computer name, lowercase and hyphenated."""
    os.environ["GLYPH_SPACES_MACHINE"] = "Ben's Laptop"
    assert core.machine_id() == "ben-s-laptop", core.machine_id()
    os.environ["GLYPH_SPACES_MACHINE"] = "studio-2."
    assert core.machine_id() == "studio-2", core.machine_id()
    os.environ["GLYPH_SPACES_MACHINE"] = "Ben's Laptop"


def test_peer_id():
    """A phone calls itself localhost, so the tailnet name is the one to use."""
    assert fleet.peer_id({"HostName": "localhost",
                          "DNSName": "bens-phone.tailnet.ts.net."}) == "bens-phone"
    assert fleet.peer_id({"HostName": "Ben's Laptop", "DNSName": ""}) == "ben-s-laptop"


def test_guard_collects_the_failure():
    del fleet.ERRORS[:]
    assert fleet.guard("made up", lambda: 1 / 0) is None
    assert len(fleet.ERRORS) == 1, fleet.ERRORS
    assert fleet.ERRORS[0]["what"] == "made up"
    assert "ZeroDivisionError" in fleet.ERRORS[0]["why"]


def test_report_survives_a_machine_that_answers_nothing():
    """Every command fails, and a whole report still comes out."""
    os.environ["GLYPH_SPACES_MACHINE"] = "Ben's Laptop"
    fleet.run = lambda *a, **k: None        # no command on this machine answers
    fleet.save_cache = lambda: None         # and nothing is written anywhere
    fleet.CACHE["_"] = 1                    # and nothing is read from one either
    rep = fleet.collect()
    assert rep["schema"] == 1
    assert rep["machine"]["id"] == "ben-s-laptop"
    assert rep["took_ms"] >= 0
    assert isinstance(rep["config"], dict)
    assert rep["errors"], "a machine that answers nothing has something to say"
    for name in ("tailscale", "compute", "storage", "setup", "agents", "sessions",
                 "inference", "backends", "spaces"):
        assert name in rep, name
    # The checks that need a command report unknown rather than ok, and the
    # machine is not ready. The ones that only read the disk still answer,
    # which is the point of keeping each check on its own.
    assert rep["setup"]["ready"] is False
    states = dict((c["id"], c["state"]) for c in rep["setup"]["checks"])
    for cid in ("tcc.microphone", "tcc.speech", "tcc.screen-recording",
                "signing.identity", "xcode.appleid"):
        assert states[cid] == "unknown", (cid, states[cid])


def test_full_volumes_warn():
    vols = [{"mount": "/", "used_percent": 95},
            {"mount": "/Volumes/studio", "used_percent": 80},
            {"mount": "/Volumes/spare", "used_percent": None}]
    assert fleet.over_full(vols) == ["/ is 95 percent full"]
    assert fleet.over_full([{"mount": "/", "used_percent": 90}]) == ["/ is 90 percent full"]
    assert fleet.over_full([{"mount": "/", "used_percent": 89}]) == []


def test_diff_finds_what_one_machine_has():
    reps = {"laptop": {"config": {"tool.claude": "2.1.1", "tool.node": "24.3.0",
                                  "tool.git": "2.55.0"}},
            "studio": {"config": {"tool.claude": "2.1.1", "tool.uv": "0.5.11",
                                  "tool.git": "2.50.1"}}}
    rows = dict((key, (vals, odd)) for key, vals, odd in fleet.config_diff(reps))
    assert "tool.claude" not in rows, "what matches everywhere is not a difference"
    assert rows["tool.node"][0] == {"laptop": "24.3.0", "studio": None}
    assert rows["tool.node"][1] == "laptop"
    assert rows["tool.uv"][1] == "studio"
    assert rows["tool.git"][1] is None, "two versions, neither one the odd one"


def test_diff_names_the_odd_machine():
    cfg = lambda v: {"config": {"tool.uv": v}}
    reps = {"laptop": cfg("0.5.11"), "studio": cfg("0.5.11"), "air": cfg("0.4.0")}
    rows = dict((key, odd) for key, _, odd in fleet.config_diff(reps))
    assert rows["tool.uv"] == "air", rows


def test_etime():
    assert fleet.etime_s("20:07") == 20 * 60 + 7
    assert fleet.etime_s("01:55:31") == 3600 + 55 * 60 + 31
    assert fleet.etime_s("3-01:00:00") == 3 * 86400 + 3600


def test_agent_table_comes_from_the_wrapper():
    """The agents and their flags are read out of glyph.zsh, not kept here."""
    os.environ["GLYPH_AGENTS"] = "/nonexistent/agents.tsv"
    table = fleet.agent_table()
    assert "claude" in table, table
    assert table["claude"]["auto_approve_flag"] == "--dangerously-skip-permissions"
    assert table["claude"]["label"]


# --- setup: the checks that say whether a machine can do the work ------------
# Every one of these is a check failing. A check nobody has seen fail is not
# known to work, so each state a check can report is built here out of the
# text or the folder that would cause it, with no keychain, no Xcode and no
# permission needed to run them.


def test_a_revoked_certificate_is_broken_not_rejected():
    """The marker is the finding. `spctl` rejecting a development signature is
    not: it rejects every one of them, since Gatekeeper wants a notarized
    build, and reading that as a failure would call every machine broken."""
    plain = ("probe: rejected\n"
             "source=Unnotarized Developer ID\n"
             "origin=Apple Development: Ben Carter (TEAM1234)\n")
    state, _, fix = fleet.signing_verdict("  1) ABC \"Apple Development\"\n",
                                          "probe: replacing existing signature\n",
                                          plain, "Apple Development")
    assert state == "ok", state
    assert fix is None
    state, detail, fix = fleet.signing_verdict(
        "  1) ABC \"Apple Development\"\n", "",
        plain + "probe: CSSMERR_TP_CERT_REVOKED\n", "Apple Development")
    assert state == "broken", state
    assert "revoked" in detail and "Trash" in detail
    assert "find-identity" in fix, "the selection bug it causes is the fix"


def test_codesign_refusing_is_broken():
    state, detail, _ = fleet.signing_verdict(
        "  1) ABC \"Apple Development\"\n",
        "probe: error: The specified item could not be found in the keychain.\n",
        "", "Apple Development")
    assert state == "broken", state
    assert "keychain" in detail


def test_a_permission_names_the_clicks_and_offers_no_fix():
    """These three cannot be granted from a shell: `xcrun simctl privacy ...
    grant speech-recognition` answers `Operation not permitted`. So naming the
    clicks is the whole of the answer, and a fix would be a lie."""
    rows = fleet.tcc_verdict({"microphone": "granted", "speech": "never asked",
                              "screen-recording": "not granted"}, "the terminal")
    by = dict((c["id"], c) for c in rows)
    assert by["tcc.microphone"]["state"] == "ok"
    for cid in ("tcc.speech", "tcc.screen-recording"):
        assert by[cid]["state"] == "missing", by[cid]
        assert by[cid]["fix"] is None, "nothing here can grant it"
        assert "System Settings" in by[cid]["human"]
        assert "the terminal" in by[cid]["human"], "say whose permission it is"


def test_a_permission_nobody_answered_for_is_unknown():
    rows = fleet.tcc_verdict(None, "the ssh service")
    assert [c["state"] for c in rows] == ["unknown"] * 3, rows
    assert all(c["proof"] for c in rows), "an unknown row still carries its proof"


def test_a_path_without_homebrew_is_broken():
    """A non-interactive ssh shell has no /opt/homebrew/bin, so `xcodegen
    generate && xcodebuild` falls through and the next session blames the
    signing certificate."""
    got = fleet.path_verdict("/usr/bin:/bin:/usr/sbin:/sbin", "a stripped shell",
                             ["/opt/homebrew/bin"])
    assert got["state"] == "broken", got
    assert "xcodegen" in got["detail"]
    assert got["human"] is None, "this one is automatable, so it is a fix"
    assert got["fix"]
    ok = fleet.path_verdict("/opt/homebrew/bin:/usr/bin", "a shell",
                            ["/opt/homebrew/bin"])
    assert ok["state"] == "ok", ok
    assert fleet.path_verdict("", "a shell that said nothing",
                              ["/opt/homebrew/bin"])["state"] == "unknown"


def test_a_lock_with_no_holder_is_unknown():
    """Never assumed stale: a build holding one has not always written its
    holder yet, and treating that as free is how two builds collide."""
    tmp = tempfile.mkdtemp()
    keep = fleet.LOCKS
    try:
        os.mkdir(os.path.join(tmp, "build.lock.d"))
        fleet.LOCKS = (("build", os.path.join(tmp, "build.lock.d")),
                       ("sim", os.path.join(tmp, "sim.lock")))
        got = fleet.locks_check()[0]
        assert got["state"] == "unknown", got
        with open(os.path.join(tmp, "build.lock.d", "holder"), "w") as f:
            f.write("ui-check on laptop\n")
        held = fleet.locks_check()[0]
        assert held["state"] == "ok", held
        assert "ui-check on laptop" in held["detail"]
        shutil.rmtree(os.path.join(tmp, "build.lock.d"))
        assert "free" in fleet.locks_check()[0]["detail"]
    finally:
        fleet.LOCKS = keep
        shutil.rmtree(tmp, ignore_errors=True)


def test_a_linked_submodule_is_broken():
    """git refuses a symlinked submodule path while printing the commit it
    thinks it is on, so the folder has to be read rather than believed."""
    tmp = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(tmp, "worktree", "Packages"))
        os.symlink("/nowhere", os.path.join(tmp, "worktree", "Packages", "GlyphCore"))
        fleet._TREES.clear()
        got = fleet.glyphcore_check({"trees": tmp})[0]
        assert got["state"] == "broken", got
        assert "symbolic link" in got["detail"]
        fleet._TREES.clear()
        assert fleet.glyphcore_check({"trees": os.path.join(tmp, "worktree")})[0][
            "state"] == "broken", "an empty folder is not a submodule either"
    finally:
        fleet._TREES.clear()
        shutil.rmtree(tmp, ignore_errors=True)


def test_nothing_to_check_is_unknown_not_ok():
    tmp = tempfile.mkdtemp()
    try:
        fleet._TREES.clear()
        got = fleet.glyphcore_check({"trees": tmp})[0]
        assert got["state"] == "unknown", got
    finally:
        fleet._TREES.clear()
        shutil.rmtree(tmp, ignore_errors=True)


def test_a_full_disk_is_broken():
    """101 MB free is the real number one of these machines reached. It broke
    builds with `ld: write() failed errno=28`, which never mentions a disk."""
    keep = fleet.free_on
    try:
        fleet.free_on = lambda path: 101 * 1024 * 1024
        got = fleet.disk_check()[0]
        assert got["state"] == "broken", got
        assert "errno=28" in got["detail"]
        assert fleet.scratch_check(None)[0]["state"] == "broken"
    finally:
        fleet.free_on = keep


def test_unknown_never_makes_a_machine_ready():
    """The one that matters most. A check that could not run must not read as
    health, so `ready` is false while any check is unknown, not only when one
    is broken."""
    keep = dict(fleet.SETUP_JOBS)
    try:
        for name in list(fleet.SETUP_JOBS):
            fleet.SETUP_JOBS[name] = lambda roots: []
        fleet.SETUP_JOBS["locks"] = lambda roots: [
            fleet.chk("locks", "unknown", "made up")]
        del fleet.ERRORS[:]
        block = fleet.setup_block(None)
        states = dict((c["id"], c["state"]) for c in block["checks"])
        assert states["locks"] == "unknown", states
        assert block["ready"] is False, "unknown is never ok"
        fleet.SETUP_JOBS["locks"] = lambda roots: [
            fleet.chk("locks", "ok", "made up")]
        assert fleet.setup_block(None)["ready"] is False, \
            "the other twelve are still unknown, since they answered nothing"
    finally:
        fleet.SETUP_JOBS.clear()
        fleet.SETUP_JOBS.update(keep)


def test_a_check_that_throws_becomes_an_unknown_row_with_its_reason():
    """Every check stands alone, like every other reader: one that fails is a
    line in `errors` and a row that says so, never a missing row. A missing
    row would read as nothing to report."""
    keep = dict(fleet.SETUP_JOBS)
    try:
        fleet.SETUP_JOBS["locks"] = lambda roots: 1 / 0
        del fleet.ERRORS[:]
        block = fleet.setup_block(None)
        assert [c["id"] for c in block["checks"]] == list(fleet.SETUP_ORDER)
        row = dict((c["id"], c) for c in block["checks"])["locks"]
        assert row["state"] == "unknown", row
        assert "ZeroDivisionError" in row["detail"], row
        assert row["proof"], "an unknown row still says what would have been run"
        assert any(e["what"] == "setup locks" for e in fleet.ERRORS)
    finally:
        fleet.SETUP_JOBS.clear()
        fleet.SETUP_JOBS.update(keep)


def test_worst_first():
    rows = [fleet.chk("locks", "ok", ""), fleet.chk("tcc.speech", "missing", ""),
            fleet.chk("disk.boot-free", "broken", ""),
            fleet.chk("tcc.microphone", "unknown", "")]
    assert [c["id"] for c in fleet.worst_first(rows)] == [
        "disk.boot-free", "tcc.speech", "tcc.microphone", "locks"]


def test_every_check_carries_a_proof():
    """A check without a proof is not a check, so the table has every id in
    it, including the ones only an `unknown` row ever reaches for."""
    assert sorted(fleet.SETUP_PROOF) == sorted(fleet.SETUP_ORDER)
    assert sorted(fleet.SETUP_JOBS) == sorted(
        set(fleet.owner(c) for c in fleet.SETUP_ORDER))

def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok   %s" % t.__name__)
    print("%d checks passed" % len(tests))
    return 0


if __name__ == "__main__":
    sys.exit(main())
