#!/usr/bin/env python3
"""glyph fleet, checked against facts made up for the purpose.

    python3 spaces/test_fleet.py

No framework and no fixtures on disk: the machines here are invented, and the
one test that runs the real collector first takes away its ability to run a
command, which is the whole promise worth checking. A reader that cannot read
has to become a line in `errors` rather than a traceback, because a caller
losing a whole machine over one unreadable fact is the failure that matters.
"""
import os, sys

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
    for name in ("tailscale", "compute", "storage", "agents", "sessions",
                 "inference", "backends", "spaces"):
        assert name in rep, name


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


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok   %s" % t.__name__)
    print("%d checks passed" % len(tests))
    return 0


if __name__ == "__main__":
    sys.exit(main())
