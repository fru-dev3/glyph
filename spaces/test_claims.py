#!/usr/bin/env python3
"""glyph claims, checked against a race that is actually run.

    python3 spaces/test_claims.py

No framework and no fixtures on disk. The first check is the one worth having:
eight processes reach for the same area at the same instant, forty times over,
and exactly one of them may come away with it. Everything after that is a way
for a claim to fail, built out of the state that causes it: a session that is
gone, a holder nobody can read, a machine that is not this one.
"""
import json, os, shutil, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from glyph_spaces import claims, core

ROUNDS = int(os.environ.get("GLYPH_RACE_ROUNDS") or 40)
RACERS = int(os.environ.get("GLYPH_RACE_RACERS") or 8)


def sandbox():
    """A claims folder of its own, inside a folder of its own.

    The outer folder is the check that nothing is written outside the claims
    folder: whatever a claim does, it does in here.
    """
    outer = tempfile.mkdtemp()
    os.environ["GLYPH_CLAIMS"] = os.path.join(outer, "claims")
    os.environ["GLYPH_SPACES_MACHINE"] = "laptop"
    return outer


def test_an_area_cannot_name_a_folder_outside_the_claims_folder():
    """The area is a token, so there is nothing to escape with."""
    assert claims.area_name("Mac Screen Check") == "mac-screen-check"
    assert claims.area_name("../../.ssh/authorized_keys") == "ssh-authorized-keys"
    assert claims.area_name("a/b") == "a-b"
    for bad in ("", "   ", "///", "--", None):
        try:
            claims.area_name(bad)
        except ValueError:
            continue
        raise AssertionError("an area of %r was accepted" % (bad,))


def _racer(area, start_at):
    """One process reaching for an area at an agreed instant. `1` if it won."""
    while time.time() < start_at:
        pass                         # a spin, not a sleep: they must collide
    try:
        ok, _ = claims.take(area, session="racer-%d" % os.getpid(), pid=os.getpid())
    except Exception:
        return b"E"
    return b"1" if ok else b"0"


def race(area, racers=RACERS, before=None):
    """Every racer's answer as one string: `1` won, `0` lost, `E` threw.

    The racers are held alive until all of them have answered. Without that the
    first one to finish is reaped while the others are still reaching, its pid
    is genuinely gone, and what comes back is a takeover of a stale claim
    rather than a race. Both are worth proving, and the two have to be told
    apart; this measures the race.
    """
    say_r, say_w = os.pipe()                  # racers to here: the answers
    gate_r, gate_w = os.pipe()                # here to racers: the race is over
    start_at = time.time() + 0.08
    pids = []
    for _ in range(racers):
        pid = os.fork()
        if pid == 0:
            try:
                os.close(say_r)
                os.close(gate_w)
                if before:
                    before()
                os.write(say_w, _racer(area, start_at))
                os.read(gate_r, 1)
            finally:
                os._exit(0)
        pids.append(pid)
    os.close(say_w)
    os.close(gate_r)
    got = b""
    while len(got) < racers:
        chunk = os.read(say_r, racers - len(got))
        if not chunk:
            break
        got += chunk
    os.close(gate_w)
    for pid in pids:
        os.waitpid(pid, 0)
    os.close(say_r)
    return got.decode()


def test_only_one_of_eight_processes_can_take_the_same_area():
    """The whole point, run rather than argued.

    Eight processes spin until an agreed instant and then all call `take` on
    one area. One wins every round, seven are told who has it, and the holder
    file on disk belongs to the winner, whole and readable. Forty rounds,
    because a race that is only lost sometimes is a race that is not closed.
    """
    outer = sandbox()
    try:
        for n in range(ROUNDS):
            area = "race-%d" % n
            got = race(area)
            assert len(got) == RACERS, "round %d: %d answered of %d" % (
                n, len(got), RACERS)
            assert got.count("E") == 0, "round %d: a racer threw: %r" % (n, got)
            assert got.count("1") == 1, "round %d: %d winners (%r)" % (
                n, got.count("1"), got)
            holder = claims.holder_of(claims.dir_for(area))
            assert holder, "round %d: the winner left no holder" % n
            assert holder["session"].startswith("racer-"), holder
            assert holder["pid"] and holder["area"] == area and holder["at"], holder
        assert len(claims.rows(reports={})) == ROUNDS
        assert sorted(os.listdir(outer)) == ["claims"], \
            "a claim wrote outside the claims folder: %s" % os.listdir(outer)
    finally:
        shutil.rmtree(outer, ignore_errors=True)


def test_two_processes_finding_the_same_stale_claim_cannot_both_take_it_over():
    """The other half of the race, and the one that was wrong first.

    A stale claim never blocks, so the moment two sessions see one they both
    reach for it. An earlier version moved the whole claim directory aside on a
    decision read a moment earlier, and in forty rounds it twice moved aside a
    claim that had just been taken and handed the area to two sessions at once.
    The handover is now a rename of the holder file inside a directory that is
    never moved, decided from the file the rename actually took.
    """
    outer = sandbox()
    try:
        for n in range(ROUNDS):
            area = "handover-%d" % n
            dead = os.fork()
            if dead == 0:
                os._exit(0)
            os.waitpid(dead, 0)
            claims.take(area, session="gone-%d" % dead, pid=dead)
            assert claims.rows(reports={})[-1]["state"] == "stale"
            got = race(area)
            assert got.count("1") == 1, "round %d: %r" % (n, got)
            assert got.count("E") == 0, "round %d: %r" % (n, got)
            holder = claims.holder_of(claims.dir_for(area))
            assert holder and holder["session"].startswith("racer-"), holder
            assert sorted(os.listdir(claims.dir_for(area))) == ["holder"], \
                os.listdir(claims.dir_for(area))
    finally:
        shutil.rmtree(outer, ignore_errors=True)


def test_the_loser_is_told_who_holds_it():
    outer = sandbox()
    try:
        ok, _ = claims.take("provisioning", session="rig-session", pid=os.getpid(),
                            branch="glyph-provision")
        assert ok
        ok, row = claims.take("provisioning", session="other-session", pid=os.getpid())
        assert ok is False
        assert row["session"] == "rig-session", row
        assert row["machine"] == "laptop" and row["branch"] == "glyph-provision"
        assert row["state"] == "live", row
        assert "rig-session on laptop" in claims.describe(row)
    finally:
        shutil.rmtree(outer, ignore_errors=True)


def test_a_claim_whose_session_is_gone_is_stale_and_does_not_block():
    """Never silently released, and never blocking either. A pid that has gone
    is the one case this machine can settle by itself."""
    outer = sandbox()
    try:
        dead = os.fork()
        if dead == 0:
            os._exit(0)
        os.waitpid(dead, 0)          # now a pid that certainly is not running
        ok, _ = claims.take("docs-rewrite", session="gone-session", pid=dead)
        assert ok
        row = claims.rows(reports={})[0]
        assert row["state"] == "stale", row
        ok, mine = claims.take("docs-rewrite", session="next-session", pid=os.getpid())
        assert ok, "a stale claim must never block"
        assert mine["took_over"]["session"] == "gone-session", mine
        rows = claims.rows(reports={})
        assert len(rows) == 1 and rows[0]["state"] == "live", rows
        assert os.listdir(claims.dir_for("docs-rewrite")) == ["holder"], \
            "the claim it took over was left lying about"
    finally:
        shutil.rmtree(outer, ignore_errors=True)


def test_a_claim_with_no_readable_holder_is_unknown_and_still_blocks():
    """A holder that cannot be read has not been shown to be dead. This is the
    gap between taking the directory and writing the file, and the answer there
    has to be the safe one."""
    outer = sandbox()
    try:
        os.makedirs(claims.dir_for("mac-screen-check"))
        row = claims.rows(reports={})[0]
        assert row["state"] == "unknown", row
        ok, blocked = claims.take("mac-screen-check", session="mine", pid=os.getpid())
        assert ok is False, "unknown is never treated as stale"
        assert blocked["state"] == "unknown"
        # Half a holder file is no more readable than none.
        with open(os.path.join(claims.dir_for("mac-screen-check"), "holder"), "w") as f:
            f.write('{"session": "half')
        assert claims.rows(reports={})[0]["state"] == "unknown"
        ok, _ = claims.release("mac-screen-check", pid=os.getpid())
        assert ok is False, "it is not ours to release"
        ok, _ = claims.release("mac-screen-check", force=True)
        assert ok, "--force is what a holder nobody can read is for"
        assert claims.rows(reports={}) == []
    finally:
        shutil.rmtree(outer, ignore_errors=True)


def test_another_machine_sees_the_claim_and_who_has_it():
    """A claim is one folder, so every machine reads the same one. A holder
    somewhere else cannot be settled by a pid, so that machine's own last
    report settles it: in `sessions.live[]` is live, a reading taken after the
    claim without it is stale, and no reading at all is unknown."""
    outer = sandbox()
    try:
        os.environ["GLYPH_SPACES_MACHINE"] = "studio"
        ok, _ = claims.take("provisioning", session="rig·studio·2026", pid=9100,
                            branch="glyph-provision")
        assert ok
        os.environ["GLYPH_SPACES_MACHINE"] = "laptop"
        seen = claims.rows(reports={})[0]
        assert seen["machine"] == "studio", "a claim says which machine holds it"
        assert seen["state"] == "unknown", "no reading from studio to go on"
        live = {"studio": {"taken": claims._fleet().stamp(time.time() + 60),
                           "sessions": {"live": [{"name": "rig·studio·2026",
                                                  "pid": 9100}]}}}
        assert claims.rows(reports=live)[0]["state"] == "live"
        after = {"studio": {"taken": claims._fleet().stamp(time.time() + 60),
                            "sessions": {"live": []}}}
        assert claims.rows(reports=after)[0]["state"] == "stale"
        before = {"studio": {"taken": claims._fleet().stamp(time.time() - 60),
                             "sessions": {"live": []}}}
        assert claims.rows(reports=before)[0]["state"] == "unknown", \
            "a reading older than the claim cannot say the session has gone"
    finally:
        shutil.rmtree(outer, ignore_errors=True)


def test_release_refuses_another_session_and_takes_force():
    outer = sandbox()
    try:
        claims.take("build-scratch", session="first", pid=os.getpid())
        ok, row = claims.release("build-scratch", session="second", pid=4242)
        assert ok is False and row["session"] == "first", row
        ok, row = claims.release("build-scratch", session="first")
        assert ok, "the session that took it may give it back by name"
        ok, row = claims.release("build-scratch", session="first")
        assert ok is False and row is None, "nothing claims it now"
        claims.take("build-scratch", session="first", pid=os.getpid())
        assert claims.release("build-scratch", pid=os.getpid())[0], "or by pid"
    finally:
        shutil.rmtree(outer, ignore_errors=True)


def test_the_holder_shows_up_on_the_live_session_row():
    """Why this belongs in Rig: ownership next to the session doing the work,
    in the report every machine and the app already read."""
    outer = sandbox()
    try:
        claims.take("docs-rewrite", session="docs·laptop·2026", pid=os.getpid(),
                    branch="glyph-docs")
        claims.take("provisioning", session="rig·laptop·2026", pid=4242)
        os.environ["GLYPH_SPACES_MACHINE"] = "studio"
        claims.take("elsewhere", session="other·studio·2026", pid=4242)
        os.environ["GLYPH_SPACES_MACHINE"] = "laptop"
        live = [{"name": "docs·laptop·2026", "pid": os.getpid()},
                {"name": None, "pid": 4242},
                {"name": "idle·laptop·2026", "pid": 777}]
        claims.attach(live)
        assert live[0]["claim"] == {"area": "docs-rewrite", "branch": "glyph-docs",
                                   "at": live[0]["claim"]["at"]}
        assert live[1]["claim"]["area"] == "provisioning", "matched on the pid"
        assert "claim" not in live[2], "a session with no claim says nothing"
        assert claims.attach([]) == [] and claims.attach(None) is None
    finally:
        shutil.rmtree(outer, ignore_errors=True)


def test_the_report_carries_the_holder_and_survives_a_folder_it_cannot_read():
    """The collector's own rule: this reader stands alone. A claims folder that
    cannot be read costs the holder on a row, not the row and not the report."""
    outer = sandbox()
    from glyph_spaces import fleet
    mine = lambda block: [r for r in block["live"] if r["pid"] == os.getpid()]
    ps = lambda: [{"agent": "claude", "pid": os.getpid(), "cpu_percent": 0.0,
                   "rss_bytes": 0, "started_at": None}]
    try:
        claims.take("docs-rewrite", session="docs·laptop·2026", pid=os.getpid())
        got = mine(fleet.sessions_block(ps()))
        assert got and got[0]["claim"]["area"] == "docs-rewrite", got
        # Now the claims folder is a file, so the reader cannot read it.
        os.environ["GLYPH_CLAIMS"] = os.path.join(outer, "claims", "holder")
        with open(os.environ["GLYPH_CLAIMS"], "w") as f:
            f.write("not a folder at all")
        del fleet.ERRORS[:]
        got = mine(fleet.sessions_block(ps()))
        assert got, "the row still comes out"
        assert "claim" not in got[0], got
    finally:
        shutil.rmtree(outer, ignore_errors=True)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok   %s" % t.__name__)
    print("%d checks passed (%d rounds of %d racers)" % (len(tests), ROUNDS, RACERS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
