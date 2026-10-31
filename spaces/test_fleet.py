#!/usr/bin/env python3
"""glyph fleet, checked against facts made up for the purpose.

    python3 spaces/test_fleet.py

No framework and no fixtures on disk: the machines here are invented, and the
one test that runs the real collector first takes away its ability to run a
command, which is the whole promise worth checking. A reader that cannot read
has to become a line in `errors` rather than a traceback, because a caller
losing a whole machine over one unreadable fact is the failure that matters.
"""
import contextlib, io, json, os, shutil, sys, tempfile, time

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

def test_a_folder_reachable_down_two_roots_is_counted_once():
    """`home: ~` and `code: ~/code` both reach `~/code/wt/Packages/GlyphCore`.
    It counted twice, printed the same path twice in the check's detail, and
    inflated every "N of M checkouts" number on a machine whose roots overlap.
    """
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "code", "wt", "Packages", "GlyphCore"))
        roots = {"home": d, "code": os.path.join(d, "code")}
        assert len(fleet.found_under(roots, "Packages/GlyphCore")) == 1
        # a link to the same real folder is still the same checkout
        os.symlink(os.path.join(d, "code", "wt"), os.path.join(d, "wt-link"))
        assert len(fleet.found_under(roots, "Packages/GlyphCore")) == 1


# --- capabilities: what a machine can therefore do ---------------------------
# Derived from the checks above, so what is checked here is the derivation: a
# `no` has to lead back to the check that caused it, and a check that could
# not answer must never come out the other side as a machine you can hand a
# build to.


def capability(cid, states, spaces=None):
    """One capability, from states invented for the checks it rests on."""
    checks = [fleet.chk(k, v, "made up") for k, v in states.items()]
    return dict((c["id"], c) for c in fleet.capabilities(checks, spaces))[cid]


def test_a_capability_is_yes_only_when_every_check_it_needs_is_ok():
    got = capability("swift-build", {"xcode.developer-dir": "ok",
                                     "build.scratch": "ok"})
    assert got["can"] == "yes", got
    assert got["from"] == ["xcode.developer-dir", "build.scratch"], got


def test_an_unknown_check_makes_a_capability_unknown_not_yes():
    """The one that matters most here, and the same rule the block keeps. A
    machine that might be able to build is not a machine you give a build to,
    and a capability is read by something choosing where work goes."""
    for state in ("unknown",):
        got = capability("swift-build", {"xcode.developer-dir": "ok",
                                         "build.scratch": state})
        assert got["can"] == "unknown", got
        assert got["from"] == ["build.scratch"], "name the one that could not answer"
    # A check that is simply not in the block at all is the same thing: a
    # missing row must not read as nothing to report.
    got = capability("mac-screen", {})
    assert got["can"] == "unknown", got
    got = capability("iphone-sim", {"xcode.devicesupport": "ok"})
    assert got["can"] == "unknown", got


def test_a_capability_no_names_the_check_that_caused_it():
    """A no is traceable: it names the checks that are not ok, and those
    carry the proof. It never names the ones that were fine."""
    got = capability("iphone-sim", {"xcode.devicesupport": "ok",
                                    "xcode.appleid": "missing"})
    assert got["can"] == "no", got
    assert got["from"] == ["xcode.appleid"], got
    got = capability("swift-build", {"xcode.developer-dir": "broken",
                                     "build.scratch": "broken"})
    assert got["can"] == "no", got
    assert got["from"] == ["xcode.developer-dir", "build.scratch"], got
    # A broken check beside one that could not answer is still a no: broken is
    # the definite half, and the no is what a caller can act on.
    got = capability("swift-build", {"xcode.developer-dir": "broken",
                                     "build.scratch": "unknown"})
    assert got["can"] == "no", got
    assert got["from"] == ["xcode.developer-dir"], got


def test_the_vault_root_is_read_off_the_block_and_not_the_disk():
    """It rests on the spaces block the collector already built, so a machine
    that is not in the map is unknown rather than assumed to have no vault."""
    caps = {"vault": {"xcode.appleid": "ok"}}
    assert capability("vault", caps["vault"], None)["can"] == "unknown"
    assert capability("vault", {}, {"presets": []})["can"] == "unknown", \
        "no roots in the block is not the same as no vault root"
    assert capability("vault", {}, {"roots": {"home": "~"}})["can"] == "no"
    assert capability("vault", {}, {"roots": {"vault": "~/v"},
                                    "missing_roots": ["vault"]})["can"] == "no"
    got = capability("vault", {}, {"roots": {"vault": "~/v"}, "missing_roots": []})
    assert got["can"] == "yes", got
    assert fleet.root_check({"roots": {"vault": "~/v"}}, "vault")["proof"], \
        "a check without a proof is not a check, root or not"


def test_the_one_line_form_says_what_a_machine_can_do():
    caps = [{"id": "vault", "can": "yes", "from": []},
            {"id": "swift-build", "can": "no", "from": []},
            {"id": "mac-screen", "can": "unknown", "from": []}]
    assert fleet.can_line(caps) == "vault mac-screen?"
    assert fleet.can_line([{"id": "vault", "can": "no", "from": []}]) == "none"
    assert fleet.can_line(None) is None, "a report written before this gets no line"


# --- reachable is not a flag -------------------------------------------------
# `tailscale status --json` reported the hub Online false while an ssh session
# to its tailnet address was open, it had just written a full report and nine
# agents were running on it. A roster flag is the weakest evidence there is.


def test_a_machine_that_answered_is_up_whatever_the_roster_says():
    stale = {"online": False, "last_seen": "2026-10-31T09:00:00-05:00"}
    fresh = {"taken": fleet.stamp(time.time())}
    up, why = fleet.up_verdict(fresh, stale, answered=True)
    assert up is True and "answered this run" in why, (up, why)
    up, why = fleet.up_verdict(fresh, stale)
    assert up is True, "a reading a moment old outweighs the flag"
    assert "wrote a reading" in why and "ago" not in why, why
    up, why = fleet.up_verdict(None, {"online": False, "self": True})
    assert up is True and "machine asking" in why, (up, why)


def test_the_roster_is_believed_where_there_is_nothing_better():
    old = {"taken": "2026-10-01T09:00:00-05:00"}
    assert fleet.up_verdict(old, {"online": False}) == (False, None)
    assert fleet.up_verdict(None, {"online": False}) == (False, None)
    assert fleet.up_verdict(None, {"online": True}) == (True, None)
    assert fleet.up_verdict(None, None) == (False, None)
    # Agreement is never explained: a why on every row would be noise, and the
    # column is the conclusion.
    assert fleet.up_verdict({"taken": fleet.stamp(time.time())},
                            {"online": True})[1] is None


def test_a_mac_that_never_reported_is_unknown_not_blank():
    """Blank is for a row that is not a Mac at all. The two read the same in
    the column and they are different things."""
    assert fleet.setup_mark(None, {"os": "macOS"}) == "unknown"
    assert fleet.setup_mark(None, {}) == "unknown", "a machine only in the map"
    assert fleet.setup_mark(None, {"os": "iOS"}) == "-"
    assert fleet.setup_mark({"setup": {"ready": True, "checks": []}}) == "ok"
    assert fleet.setup_mark({"setup": {"ready": False, "checks": [
        fleet.chk("locks", "broken", "")]}}) == "1 bad"


def test_a_colliding_tailnet_id_is_the_same_on_every_run():
    """Two nodes can normalise to one id. Which one takes the suffix is
    decided by the node's own stable id, never by the order the peers came
    out of the status object: an id that moves between runs splits one
    machine's history across two files. An earlier version kept neither, it
    overwrote, and one of the two machines left the roster altogether."""
    a = {"HostName": "Ben Air", "DNSName": "", "ID": "n2", "TailscaleIPs": ["100.0.0.2"]}
    b = {"HostName": "Ben-Air", "DNSName": "", "ID": "n1", "TailscaleIPs": ["100.0.0.1"]}
    me = {"HostName": "Ben Air", "DNSName": "", "ID": "n9"}
    try:
        for peers in ({"1": a, "2": b}, {"1": b, "2": a}):
            fleet._TS["d"] = {"Self": me, "Peer": peers}
            got = fleet.tailnet()
            assert sorted(got) == ["ben-air", "ben-air-1", "ben-air-2"], got
            assert got["ben-air"]["self"] is True, "self keeps the bare id"
            assert got["ben-air-1"]["ip"] == "100.0.0.1", got
            assert got["ben-air-2"]["ip"] == "100.0.0.2", got
        assert fleet.node_key({"PublicKey": "k"}) == "k"
        assert fleet.node_key({}) == ""
    finally:
        fleet._TS.clear()


# --- narrowing a run to one space --------------------------------------------
# `--space` is the one flag that makes the run smaller, which is the direction
# that does damage quietly: a name that selects nothing prints what a machine
# with nothing left to build prints.

LAPTOP = {"role": "dev", "tag": "lt", "profiles": ["work"],
          "roots": {"home": "~", "code": "~/code"}}
LAYOUT = [{"id": "work", "space": "work", "profiles": ["work"], "tabs": []},
          {"id": "site-and-notes", "space": "site", "profiles": ["work"], "tabs": []},
          {"id": "ops", "space": "ops", "profiles": ["hub"], "tabs": []}]


def narrow(*names):
    """(the spaces selected, what it printed). The refusal is half of what
    this flag does, so the text it prints is part of what is checked."""
    class Args(object):
        space = list(names) or None
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        got = core.narrowed(Args(), "laptop", LAPTOP, LAYOUT)
    return got, said.getvalue()


def test_no_space_flag_is_every_space_this_machine_takes():
    got, said = narrow()
    assert [s["id"] for s in got] == ["work", "site-and-notes"]
    assert said == "", "the ordinary run says nothing extra"


def test_a_space_is_named_by_its_id_or_by_its_workspace():
    ids = lambda *n: [s["id"] for s in narrow(*n)[0]]
    assert ids("site-and-notes") == ["site-and-notes"]
    assert ids("site") == ["site-and-notes"]
    assert ids("work", "site") == ["work", "site-and-notes"]
    assert ids("work", "work") == ["work"], "named twice is once"


def test_a_space_this_machine_does_not_take_is_refused():
    """Not a silent no-op. `apply --space ops` on a machine whose profiles do
    not select ops would otherwise print nothing to do, which is exactly what
    a machine with everything already built prints."""
    got, said = narrow("ops")
    assert got is None
    assert "does not take ops" in said and "profile hub" in said, said
    assert narrow("work", "ops")[0] is None, "one bad name refuses the whole run"


def test_a_space_that_does_not_exist_lists_the_ones_that_do():
    got, said = narrow("nothing-of-the-kind")
    assert got is None
    assert "no space named nothing-of-the-kind" in said, said
    for line in ("SPACE", "work", "site-and-notes", "lt-work", "lt-site"):
        assert line in said, (line, said)
    assert "ops" not in said, "a space this machine does not take is not on offer"


def test_a_renamed_tailnet_node_folds_onto_the_machine_it_is():
    """A tailnet name is renamed freely; a machine's key in the map is not.
    When the Macs were renamed to `...-16in-m2-16gb-01`, every one appeared
    twice, once as a node that had never reported and once as a machine that
    was never up, and the machine running the command called itself down."""
    machines = {"laptop": {"role": "dev"}, "studio": {"role": "hub"}}
    reps = {"laptop": {}, "studio": {}}
    net = {"laptop-16in-m2-16gb-01": {"online": True},
           "studio-m4-16gb-01": {"online": True},
           "phone-15-pro-01": {"online": True}}
    out = fleet.fold_roster(net, machines, reps)
    assert set(out) == {"laptop", "studio", "phone-15-pro-01"}, out

    # The map may say so outright, which wins over the name.
    said = {"mini": {"role": "hub", "tailnet": "Studio m4 16gb 01"}}
    assert set(fleet.fold_roster({"studio-m4-16gb-01": {}}, said, {})) == {"mini"}

    # A node two ids could claim is left alone: a wrong join is worse than two rows.
    two = {"air": {}, "air-2": {}}
    assert set(fleet.fold_roster({"air-2-m5-01": {}}, two, {})) == {"air-2"}
    amb = {"a": {}, "a-b": {}}
    assert set(fleet.fold_roster({"a-b-c": {}}, amb, {})) == {"a-b"}


def test_a_machine_that_will_not_answer_says_what_to_do_about_it():
    """The first new Mac tried was on the tailnet and refused ssh, because
    Remote Login was off. "no answer over ssh" sends someone hunting for a key
    or a PATH; it was one switch in System Settings."""
    assert "Remote Login" in fleet.why_no_answer(
        "ssh: connect to host 192.0.2.9 port 22: Operation timed out")
    assert "Remote Login" in fleet.why_no_answer("ssh: connect to port 22: Connection refused")
    assert "ssh-copy-id" in fleet.why_no_answer("Permission denied (publickey).")
    assert "trusted" in fleet.why_no_answer("Host key verification failed.")
    assert "install.sh" in fleet.why_no_answer("zsh: command not found: glyph-fleet")
    assert fleet.why_no_answer("") == "no answer over ssh"
    assert fleet.why_no_answer(None) == "no answer over ssh"
    # Anything it has no words for is passed through rather than swallowed.
    assert fleet.why_no_answer("kex_exchange_identification: read: broken pipe") \
        == "kex_exchange_identification: read: broken pipe"


def test_what_a_status_says_is_not_what_a_clone_does():
    """Three green signals and a broken capability, all on one machine: a
    status named the right account while its token answered 401, the git setup
    completed while a clone could not read a username, and the credential
    helper was right with a dead token behind it. So the check asks the host
    who we are and then lists a private repo, and when nothing says which
    account to expect it answers unknown rather than ok."""
    keep = dict(os.environ)
    try:
        for k in ("GLYPH_GIT_ACCOUNT", "GLYPH_GIT_PROBE"):
            os.environ.pop(k, None)
        with tempfile.TemporaryDirectory() as d:
            os.environ["GLYPH_SPACES"] = d          # a map with no git block
            os.makedirs(os.path.join(d, "spaces"), exist_ok=True)
            with open(os.path.join(d, "machines.json"), "w") as f:
                json.dump({"machines": {}}, f)
            row = fleet.repo_access_check()[0]
            assert row["state"] == "unknown", row
            assert row["proof"], "an unknown row still says what would have been run"
    finally:
        os.environ.clear()
        os.environ.update(keep)


def test_a_second_github_account_on_a_machine_is_reported():
    """Two identities on a machine agents drive is two chances to commit as
    the wrong one, and on a public repo that is permanent. Read off the local
    config, never by asking the network, and never reading a token."""
    keep = dict(os.environ)
    try:
        with tempfile.TemporaryDirectory() as d:
            os.environ["GH_CONFIG_DIR"] = d
            with open(os.path.join(d, "hosts.yml"), "w") as f:
                f.write("github.com:\n    git_protocol: https\n    users:\n"
                        "        bens-other:\n        bendev:\n    user: bendev\n")
            names, active = fleet.git_accounts()
            assert names == ["bens-other", "bendev"], names
            assert active == "bendev", active
            os.environ["GLYPH_GIT_ACCOUNT"] = "bendev"
            row = fleet.one_account_check()[0]
            assert row["state"] == "missing", row
            assert "bens-other" in row["detail"], row
            assert row["human"] and "logout" in row["human"], row
            # One account is fine, and says which.
            with open(os.path.join(d, "hosts.yml"), "w") as f:
                f.write("github.com:\n    users:\n        bendev:\n    user: bendev\n")
            assert fleet.one_account_check()[0]["state"] == "ok"
            # No gh config at all is unknown, never ok.
            os.environ["GH_CONFIG_DIR"] = os.path.join(d, "nope")
            assert fleet.one_account_check()[0]["state"] == "unknown"
    finally:
        os.environ.clear()
        os.environ.update(keep)


# --- what is installed, and what a new Mac is missing ------------------------
# Fru's requirement in one line: every app the other machines have, installed
# on a new one, and never copied from another machine. So what is checked here
# is the arithmetic that decides which half is which: a name Homebrew can
# install, a name only a person can, and a sign-in that is never either.


def inst(casks=(), formulae=(), deps=(), apps=(), brew="/opt/homebrew",
         known=None):
    """An `installed` block, invented. `deps` are formulae nobody asked for."""
    return {"brew": brew, "casks_known": known,
            "casks": [{"name": n, "version": "1"} for n in casks],
            "formulae": [{"name": n, "version": "1", "asked": True}
                         for n in formulae]
            + [{"name": n, "version": "1"} for n in deps],
            "apps": [dict(a) for a in apps]}


def with_reports(reps, fn):
    keep = fleet.load_reports
    try:
        fleet.load_reports = lambda: reps
        return fn()
    finally:
        fleet.load_reports = keep


def with_installed(block, fn):
    keep = dict(fleet._INSTALLED)
    try:
        fleet._INSTALLED["d"] = block
        return fn()
    finally:
        fleet._INSTALLED.clear()
        fleet._INSTALLED.update(keep)


def rows_for(mine, reps, mid="laptop"):
    return with_reports(dict((k, {"installed": v}) for k, v in reps.items()),
                        lambda: fleet.install_rows(mine, mid))


def test_a_dependency_is_nothing_anybody_installs():
    """`brew install imagemagick` brings fifty formulae with it, and a list of
    all fifty-one is a wall nobody reads. The receipt says which were asked
    for, and brew's own definition of a leaf drops the ones that are a
    dependency of something else that was asked for too."""
    with tempfile.TemporaryDirectory() as d:
        cellar = os.path.join(d, "Cellar")
        for name, asked, needs in (("imagemagick", True, ["libpng", "freetype"]),
                                   ("freetype", True, ["libpng"]),
                                   ("libpng", True, []),
                                   ("libtiff", False, [])):
            keg = os.path.join(cellar, name, "1.0")
            os.makedirs(keg)
            with open(os.path.join(keg, "INSTALL_RECEIPT.json"), "w") as f:
                json.dump({"installed_on_request": asked,
                           "source": {"tap": "homebrew/core"},
                           "runtime_dependencies":
                               [{"full_name": n} for n in needs]}, f)
        rows = fleet.brew_formulae(d)
        assert len(rows) == 4, rows
        asked = sorted(r["name"] for r in rows if r.get("asked"))
        assert asked == ["imagemagick"], asked
        assert fleet.listed({"formulae": rows}, "formula") == \
            [("imagemagick", "1.0", None)]


def test_a_tap_is_a_row_only_when_it_is_not_the_obvious_one():
    """`brew install <name>` finds homebrew/core and homebrew/cask without
    being told, and two hundred rows saying so is two hundred rows of noise."""
    assert "tap" not in fleet.keg_row("git", "2.5", "homebrew/core", True)
    assert fleet.keg_row("workmux", "1", "ben/tap", True)["tap"] == "ben/tap"
    assert "asked" not in fleet.keg_row("libpng", "1", None, False)


def test_an_app_is_matched_to_a_cask_by_the_receipt_then_by_name():
    """The receipt is certain, the name is a guess, and no cask at all is a
    download. The guess is what makes a Chrome nobody installed with brew
    installable on the next machine, and a miss reads as a download, which is
    the direction that cannot do any harm."""
    with tempfile.TemporaryDirectory() as d:
        where = os.path.join(d, "Applications")
        for name, ident in (("Obsidian.app", "md.obsidian"),
                            ("Google Chrome.app", "com.google.Chrome")):
            os.makedirs(os.path.join(where, name, "Contents"))
            with open(os.path.join(where, name, "Contents", "Info.plist"), "wb") as f:
                import plistlib
                plistlib.dump({"CFBundleIdentifier": ident,
                               "CFBundleShortVersionString": "4.2"}, f)
        # A bundle with no Info.plist at all: a fact about the bundle, so it is
        # a row with what is known and never a missing row.
        os.makedirs(os.path.join(where, "Half Copied.app"))
        keep = fleet.APP_DIRS
        try:
            fleet.APP_DIRS = (where,)
            rows = dict((r["name"], r) for r in fleet.app_rows(
                {"Obsidian.app": "obsidian"}, set(["google-chrome"])))
            # With no cask index on the machine, whether a cask exists is
            # unknown, so the name match is not made at all: brew is never
            # told to install something on the strength of nothing.
            blind = dict((r["name"], r) for r in fleet.app_rows({}, None))
            assert "cask" not in blind["Google Chrome"], blind
        finally:
            fleet.APP_DIRS = keep
    assert rows["Obsidian"]["cask"] == "obsidian", rows["Obsidian"]
    assert rows["Obsidian"]["version"] == "4.2"
    assert rows["Google Chrome"]["cask"] == "google-chrome", "matched by name"
    assert "cask" not in rows["Half Copied"], "no cask knows it"
    assert rows["Half Copied"]["id"] is None
    # And an app no cask knows is a download, never a silent skip, which is
    # the whole difference between a machine that is set up and one that reads
    # as though it were.
    assert fleet.install_how("app", "Half Copied", None)[0] == "you"
    assert "download" in fleet.install_how("app", "Half Copied", None)[1]
    assert "App Store" in fleet.install_how("app", "Pages", "com.apple.iWork.Pages")[1]


def test_only_what_every_other_machine_has_is_the_baseline():
    """A name on one machine out of three is somebody trying something out. A
    name on both of the others is what the new Mac is missing."""
    rows, others = rows_for(inst(), {"studio": inst(formulae=["git", "eza"]),
                                     "air": inst(formulae=["git"])})
    assert others == ["air", "studio"]
    by = dict((r["name"], r) for r in rows)
    assert by["git"]["all"] is True and by["git"]["on"] == ["air", "studio"]
    assert by["eza"]["all"] is False, by["eza"]
    assert [r["name"] for r in rows] == ["git", "eza"], "the baseline first"
    # And what this machine already has is not missing, whichever way it got
    # there: a cask on one machine and a hand-installed app here is one thing.
    rows, _ = rows_for(inst(apps=[{"name": "Obsidian", "cask": "obsidian"}]),
                       {"studio": inst(casks=["obsidian"])})
    assert rows == [], rows


def test_one_app_is_one_row_however_much_each_machine_knew():
    """A machine whose brew has never fetched the cask index cannot say which
    cask installs an app. Before the fleet pooled its answers, Chrome was two
    rows, a cask on the machine that knew and an app on the machine that did
    not, and neither of them read 2 of 2."""
    knows = inst(apps=[{"name": "Google Chrome", "id": "com.google.Chrome",
                        "cask": "google-chrome"}])
    blind = inst(apps=[{"name": "Google Chrome", "id": "com.google.Chrome"}])
    rows, others = rows_for(inst(), {"studio": knows, "air": blind})
    assert len(rows) == 1, rows
    assert rows[0]["kind"] == "cask" and rows[0]["name"] == "google-chrome"
    assert rows[0]["on"] == ["air", "studio"], "both of them have it"
    assert rows[0]["who"] == "rig"


def test_no_homebrew_is_the_blocker_and_says_so_rather_than_fixing_it():
    """Installing Homebrew is a download piped into a shell, a password and
    the Command Line Tools. It is the same class of thing as installing Xcode,
    and a tool that quietly did all three would be the worst version of this."""
    got = with_installed(inst(brew=None), lambda: fleet.install_check()[0])
    assert got["state"] == "broken", got
    assert got["fix"] is None, "nothing here installs Homebrew"
    assert "brew.sh" in got["human"], got
    assert got["proof"], "a check without a proof is not a check"


def test_nothing_saying_what_a_machine_should_have_is_unknown_not_ok():
    """The same rule the rest of the block keeps. One machine on its own
    cannot answer this, and silence must not read as having everything."""
    got = with_installed(inst(), lambda: with_reports(
        {}, lambda: fleet.install_check()[0]))
    assert got["state"] == "unknown", got
    assert "GLYPH_INSTALL" in got["proof"], got
    # With another machine to compare against and nothing missing, it is ok.
    got = with_installed(inst(formulae=["git"]), lambda: with_reports(
        {"studio": {"installed": inst(formulae=["git"])}},
        lambda: fleet.install_check()[0]))
    assert got["state"] == "ok", got
    got = with_installed(inst(), lambda: with_reports(
        {"studio": {"installed": inst(formulae=["git"])}},
        lambda: fleet.install_check()[0]))
    assert got["state"] == "missing", got
    assert "git" in got["detail"], got


def test_a_sign_in_is_named_whether_the_app_is_here_yet_or_not():
    """Nothing this can read says whether somebody signed in, so a sign-in is
    named and never counted: an app about to be installed needs one, and one
    already installed may still be waiting for it."""
    rows, _ = rows_for(inst(), {"studio": inst(casks=["1password"])})
    assert rows[0]["sign_in"] and "sign in" in rows[0]["sign_in"]
    named = dict(fleet.sign_ins(rows, inst()))
    assert "1password" in named, named
    # Already installed here, so not a row at all, and still named.
    named = dict(fleet.sign_ins([], inst(casks=["1password", "eza"])))
    assert sorted(named) == ["1password"], named


def test_your_own_config_narrows_the_set_and_this_repo_never_holds_it():
    """The set is what the other machines have, and a list in the person's own
    config narrows it, the way GLYPH_SPACES and the git block already work.
    Nothing about anybody's machine belongs in this repo."""
    keep = dict(os.environ)
    try:
        os.environ["GLYPH_INSTALL"] = "git, eza"
        assert fleet.wanted_names() == set(["git", "eza"])
        rows, _ = rows_for(inst(), {"studio": inst(formulae=["git", "btop"])})
        assert [r["name"] for r in rows] == ["git"], rows
        os.environ.pop("GLYPH_INSTALL")
        with tempfile.TemporaryDirectory() as d:
            os.environ["GLYPH_SPACES"] = d
            os.makedirs(os.path.join(d, "spaces"), exist_ok=True)
            with open(os.path.join(d, "machines.json"), "w") as f:
                json.dump({"machines": {}, "install": ["btop"]}, f)
            assert fleet.wanted_names() == set(["btop"])
            with open(os.path.join(d, "machines.json"), "w") as f:
                json.dump({"machines": {}}, f)
            assert fleet.wanted_names() is None, "no list is every name"
    finally:
        os.environ.clear()
        os.environ.update(keep)


def test_the_installed_list_is_read_once_per_run():
    """Two things ask for it, the reader that writes it into the report and
    the check that compares it with the other machines, and reading the same
    folders twice is how one question gets two answers."""
    fleet._INSTALLED.clear()
    keep = fleet._installed
    try:
        calls = []
        fleet._installed = lambda: calls.append(1) or {"brew": None}
        fleet.installed_block()
        fleet.installed_block()
        assert len(calls) == 1, calls
    finally:
        fleet._installed = keep
        fleet._INSTALLED.clear()

def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok   %s" % t.__name__)
    print("%d checks passed" % len(tests))
    return 0


if __name__ == "__main__":
    sys.exit(main())


