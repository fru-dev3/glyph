#!/usr/bin/env python3
"""glyph rig, checked against a machine made up for the purpose.

    python3 spaces/test_rig.py

No framework and no fixtures on disk. Every test runs in a temporary home
folder with the environment rig reads stripped out, so nothing here can reach
the machine it runs on, and the four rules are what is checked: a plan writes
nothing, apply refuses without the flag, an action that cannot be read back is
never done, and a step only a person can do is never counted.
"""
import contextlib, io, os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from glyph_spaces import core, fleet, rig

# Everything rig takes from the environment, cleared for every test, so a
# suite run on a machine that has any of these set answers the same.
RIG_ENV = ("GLYPH_BUILD_SCRATCH", "GLYPH_ASC_KEY", "GLYPH_ASC_KEY_ID",
           "GLYPH_ASC_ISSUER_ID", "GLYPH_ENGINE", "GLYPH_ENGINE_SRC",
           "GLYPH_GLYPHCORE", "GLYPH_GLYPHCORE_SRC", "GLYPH_SIGN_IDENTITY")


def sand(fn):
    """Run fn(home) with a temporary home, and everything rig derives from it."""
    tmp = tempfile.mkdtemp(prefix="glyph-rig-test-")
    home = os.path.join(tmp, "home")
    os.makedirs(home)
    keep = (os.environ.get("HOME"), fleet.HOME, rig.HOME, rig.ZSHENV,
            rig.LOCKS_CONF)
    env = dict((k, os.environ.get(k)) for k in RIG_ENV)
    try:
        os.environ["HOME"] = home
        fleet.HOME = rig.HOME = home
        rig.ZSHENV = os.path.join(home, ".zshenv")
        rig.LOCKS_CONF = os.path.join(home, ".config", "glyph", "locks.conf")
        for k in RIG_ENV:
            os.environ.pop(k, None)
        return fn(home)
    finally:
        if keep[0] is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = keep[0]
        fleet.HOME, rig.HOME, rig.ZSHENV, rig.LOCKS_CONF = keep[1:]
        for k, v in env.items():
            if v is not None:
                os.environ[k] = v
        shutil.rmtree(tmp, ignore_errors=True)


def tree(path):
    """Every path under a folder with its size and time, for comparing later."""
    out = {}
    for base, dirs, files in os.walk(path):
        for n in list(dirs) + files:
            p = os.path.join(base, n)
            try:
                st = os.lstat(p)
                out[p] = (st.st_mode, st.st_size, st.st_mtime_ns)
            except OSError:
                out[p] = "gone"
    return out


def rows(*states):
    """A setup block's jobs, answering whatever this test needs them to."""
    given = dict(states)
    return dict((n, (lambda cid: lambda roots: [
        fleet.chk(c, given.get(c, "broken"), "made up")
        for c in fleet.SETUP_ORDER if fleet.owner(c) == cid])(n))
        for n in fleet.SETUP_JOBS)


def with_jobs(jobs, fn):
    keep = dict(fleet.SETUP_JOBS)
    try:
        fleet.SETUP_JOBS.clear()
        fleet.SETUP_JOBS.update(jobs)
        return fn()
    finally:
        fleet.SETUP_JOBS.clear()
        fleet.SETUP_JOBS.update(keep)


def quiet(fn):
    """Run a command and keep what it printed, so the suite prints only its
    own lines and an assertion can read the output rather than trust it."""
    was, held = sys.stdout, io.StringIO()
    try:
        sys.stdout = held
        got = fn()
    finally:
        sys.stdout = was
    return got, held.getvalue()


class Args:
    def __init__(self, **kw):
        self.machine, self.yes = None, False
        self.__dict__.update(kw)


# --- the actions are the checks, and nothing else ----------------------------

def test_every_action_is_named_for_a_check():
    """There is no second list of what can go wrong. An action whose id is not
    a check could never be proved, which is the whole failure this guards."""
    for cid in rig.ACTIONS:
        assert cid in fleet.SETUP_ORDER, cid
        assert fleet.owner(cid) in fleet.SETUP_JOBS, cid
    assert rig.ORDER == [c for c in fleet.SETUP_ORDER if c in rig.ACTIONS]


def test_a_check_with_no_action_says_why():
    """Six checks have no action, and each one is a rule rather than a gap, so
    a reader is never left to wonder whether it was forgotten."""
    silent = [c for c in fleet.SETUP_ORDER
              if c not in rig.ACTIONS and c not in rig.NO_ACTION]
    assert not silent, silent


def test_the_path_folders_are_the_ones_the_check_asks_about():
    """rig names the three folders again because the check builds them inline.
    This is the only thing standing between the two lists and drift."""
    want = [d for d in (os.path.expanduser(p) for p in rig.PATH_WANT)
            if os.path.isdir(d)]
    keep = fleet.noninteractive_path
    try:
        fleet.noninteractive_path = lambda: ("/usr/bin", "a stripped shell")
        got = fleet.path_check()[0]
        for d in want:
            assert fleet.tilde(d) in got["detail"], (d, got["detail"])
    finally:
        fleet.noninteractive_path = keep


# --- rule two: a plan writes nothing -----------------------------------------

def test_plan_writes_nothing():
    """Run with every check reporting broken, so every action describes itself
    in full, and the home folder must come out byte for byte the same."""
    def go(home):
        os.makedirs(os.path.join(home, "code"))
        with open(os.path.join(home, ".zshenv"), "w") as f:
            f.write("export EDITOR=vi\n")
        before = tree(home)
        block, acts = with_jobs(rows(), lambda: rig.plan({"code": home + "/code"}))
        assert len(block["checks"]) == len(fleet.SETUP_ORDER)
        assert acts, "every action describes itself"
        assert tree(home) == before, "plan wrote something"
        assert not os.path.exists(os.path.join(home, ".zshenv" + rig.SUFFIX))
    sand(go)


def test_apply_refuses_without_the_flag():
    """The difference between a tool you can point at a machine and one you
    cannot. It prints the plan, returns 2, and changes nothing."""
    def go(home):
        before = tree(home)
        got, said = with_jobs(rows(),
                              lambda: quiet(lambda: rig.cmd_apply(Args())))
        assert got == 2, got
        assert "apply needs --yes" in said, said
        assert "nothing was changed" in said.lower(), said
        assert tree(home) == before, "a refused apply wrote something"
    sand(go)


def test_apply_refuses_another_machine():
    """There is no remote half. Changing PATH underneath work running on
    another machine is the damage this exists to prevent."""
    for args in (Args(machine="bens-studio", yes=True),
                 Args(machine="bens-studio")):
        got, said = quiet(lambda: rig.cmd_apply(args))
        assert got == 2, got
        assert "never another over ssh" in said, said


# --- rule one: a step without a check is not done -----------------------------

def test_an_action_the_check_still_refuses_is_not_done():
    """It ran, it wrote what it said it would, and the check says no. That is
    why the check is asked again rather than the exit code believed."""
    def go(home):
        rig.ACTIONS["locks"] = lambda act: (act.write(rig.LOCKS_CONF, "x"),
                                            act.say("wrote it"))
        verdict, act, after, missing = with_jobs(
            rows(), lambda: rig.run_action("locks", None))
        assert os.path.isfile(rig.LOCKS_CONF), "the work was really done"
        assert not missing, "and its own proof held"
        assert after["state"] == "broken", after
        assert verdict == "failed", verdict
    keep = rig.ACTIONS["locks"]
    try:
        sand(go)
    finally:
        rig.ACTIONS["locks"] = keep


def test_an_action_that_wrote_nothing_is_failed_even_where_the_check_says_ok():
    """The second reading. A check can be ok for a reason that has nothing to
    do with this action, so what the action claims is looked for on the disk."""
    def go(home):
        gone = os.path.join(home, "never-written")
        rig.ACTIONS["locks"] = lambda act: (
            act.proof(fleet.tilde(gone), lambda: os.path.exists(gone)),
            act.say("claimed to write a file and did not"))
        verdict, act, after, missing = with_jobs(
            rows(("locks", "ok")), lambda: rig.run_action("locks", None))
        assert after["state"] == "ok", after
        assert missing == [fleet.tilde(gone)], missing
        assert verdict == "failed", "an ok check does not excuse a missing file"
    keep = rig.ACTIONS["locks"]
    try:
        sand(go)
    finally:
        rig.ACTIONS["locks"] = keep


def test_a_check_that_will_not_answer_is_unknown_not_done():
    def go(home):
        rig.ACTIONS["locks"] = lambda act: (act.write(rig.LOCKS_CONF, "x"),
                                            act.say("wrote it"))
        jobs = dict((n, lambda roots: []) for n in fleet.SETUP_JOBS)
        verdict, act, after, _ = with_jobs(
            jobs, lambda: rig.run_action("locks", None))
        assert after["state"] == "unknown", after
        assert after["proof"], "an unknown row still says what would have run"
        assert verdict == "unknown", verdict
    keep = rig.ACTIONS["locks"]
    try:
        sand(go)
    finally:
        rig.ACTIONS["locks"] = keep


def test_an_action_that_throws_is_failed_and_not_a_crash():
    def go(home):
        rig.ACTIONS["locks"] = lambda act: 1 / 0
        verdict, act, after, _ = with_jobs(
            rows(("locks", "ok")), lambda: rig.run_action("locks", None))
        assert verdict == "failed", verdict
        assert any("ZeroDivisionError" in w for w in act.blocked), act.blocked
    keep = rig.ACTIONS["locks"]
    try:
        sand(go)
    finally:
        rig.ACTIONS["locks"] = keep


def test_an_action_that_did_some_of_it_is_part_and_never_done():
    def go(home):
        def half(act):
            act.write(rig.LOCKS_CONF, "x")
            act.block("the other half needs a person")
            act.say("half of it")
        rig.ACTIONS["locks"] = half
        verdict, act, after, _ = with_jobs(
            rows(), lambda: rig.run_action("locks", None))
        assert verdict == "part", verdict
        assert verdict != "done"
    keep = rig.ACTIONS["locks"]
    try:
        sand(go)
    finally:
        rig.ACTIONS["locks"] = keep


# --- rule three: a human step is never counted -------------------------------

def test_a_permission_is_never_marked_done():
    """These cannot be granted from a shell at all, so rig has no action for
    one, the row says the person's name against it, and the machine stays not
    ready however much else was fixed."""
    for cid in ("tcc.microphone", "tcc.speech", "tcc.screen-recording"):
        assert cid not in rig.ACTIONS, cid
        assert rig.who(None, "missing") == "you"
    def go(home):
        block, acts = with_jobs(rows(*[(c, "ok") for c in fleet.SETUP_ORDER
                                       if not c.startswith("tcc.")]),
                                lambda: rig.plan(None))
        assert block["ready"] is False, "a missing permission is never ready"
        for c in block["checks"]:
            if c["id"].startswith("tcc."):
                assert c["id"] not in acts, "no action claims it"
    sand(go)


def test_a_human_only_check_is_asked_for_separately():
    """fleet.show_human prints them apart from everything else, and that is
    where rig leaves them: never among the automatable rows."""
    rows_ = [fleet.chk("tcc.speech", "missing", "x",
                       human="System Settings, Privacy and Security"),
             fleet.chk("locks", "broken", "x", fix="something automatable")]
    human = [c for c in rows_ if c.get("human")]
    assert len(human) == 1 and human[0]["fix"] is None


# --- rule four: nothing is made worse ----------------------------------------

def test_the_marked_block_is_rewritten_and_not_duplicated():
    def go(home):
        with open(rig.ZSHENV, "w") as f:
            f.write("export EDITOR=vi\n")
        act = rig.Act("path.noninteractive", False, None)
        act.env(['export PATH="/opt/acme/bin:$PATH"'])
        act.env(['export DEVELOPER_DIR="/Applications/Xcode.app"'])
        text = open(rig.ZSHENV).read()
        assert text.count(rig.MARK_TOP) == 1, text
        assert "export EDITOR=vi" in text, "somebody else's line is kept"
        assert len(rig.read_block(rig.ZSHENV)) == 2, rig.read_block(rig.ZSHENV)
        assert os.path.isfile(rig.ZSHENV + rig.SUFFIX), "backed up before editing"
        # Again, and nothing moves: one block, the same two lines.
        again = rig.Act("path.noninteractive", False, None)
        again.env(['export PATH="/opt/acme/bin:$PATH"'])
        assert open(rig.ZSHENV).read() == text
        assert not again.proofs, "a second run has nothing to prove"
    sand(go)


def test_a_folder_with_output_in_it_is_left_exactly_as_it_is():
    """A build folder holding output is somebody's build."""
    def go(home):
        mine = os.path.join(home, "build")
        os.makedirs(mine)
        with open(os.path.join(mine, "something.o"), "w") as f:
            f.write("output")
        act = rig.Act("build.scratch", False, None)
        act.link(os.path.join(home, "scratch"), mine)
        assert act.blocked and "holds output" in act.blocked[0]
        assert not act.proofs, "nothing was claimed"
        assert os.path.isfile(os.path.join(mine, "something.o"))
        assert not os.path.islink(mine)
    sand(go)


def test_a_real_file_is_moved_aside_rather_than_lost():
    def go(home):
        was = os.path.join(home, "prevail")
        with open(was, "w") as f:
            f.write("whatever installed this")
        target = os.path.join(home, "engine")
        with open(target, "w") as f:
            f.write("the engine")
        act = rig.Act("engine.version", False, None)
        act.point(target, was)
        assert os.path.islink(was)
        assert open(was + rig.SUFFIX).read() == "whatever installed this"
        assert any("mv" in u for u in act.undos), act.undos
        assert not rig.unproved(act)
    sand(go)


def test_a_link_where_git_needs_a_folder_is_replaced_by_a_copy():
    """git refuses a symlinked submodule path while printing the commit it
    thinks it is on, so the folder is copied in and read back."""
    def go(home):
        src = os.path.join(home, "good", "Packages", "GlyphCore")
        os.makedirs(os.path.join(src, "Sources"))
        open(os.path.join(src, "Package.swift"), "w").close()
        bad = os.path.join(home, "wt", "Packages", "GlyphCore")
        os.makedirs(os.path.dirname(bad))
        os.symlink("/nowhere", bad)
        fleet._TREES.clear()
        act = rig.Act("submodule.glyphcore", False, {"code": home})
        rig.act_glyphcore(act)
        assert not os.path.islink(bad), "a link is what git refuses"
        assert os.path.isfile(os.path.join(bad, "Package.swift"))
        assert not os.path.exists(os.path.join(bad, ".git")), "no stale gitdir"
        assert not rig.unproved(act)
        fleet._TREES.clear()
    sand(go)


def test_glyphcore_tells_a_link_an_empty_folder_and_a_partial_one_apart():
    """The partial one is somebody's half-finished checkout, and nothing here
    replaces one of those, however broken the check reads."""
    def go(home):
        for name, make in (("a", "good"), ("b", "link"), ("c", "empty"),
                           ("d", "partial")):
            p = os.path.join(home, "wt-" + name, "Packages", "GlyphCore")
            if make == "link":
                os.makedirs(os.path.dirname(p))
                os.symlink("/nowhere", p)
                continue
            os.makedirs(p)
            if make == "good":
                open(os.path.join(p, "Package.swift"), "w").close()
            elif make == "partial":
                open(os.path.join(p, "README.md"), "w").close()
        fleet._TREES.clear()
        bad, good = rig.bad_glyphcore({"code": home})
        assert sorted(k for _, k in bad) == ["empty", "link", "partial"], bad
        assert len(good) == 1
        act = rig.Act("submodule.glyphcore", False, {"code": home})
        rig.act_glyphcore(act)
        left = os.path.join(home, "wt-d", "Packages", "GlyphCore")
        assert os.listdir(left) == ["README.md"], "the partial one is untouched"
        assert act.blocked, "and it is said out loud"
        fleet._TREES.clear()
    sand(go)


def test_the_same_checkout_reached_by_two_roots_is_one_row():
    """Overlapping roots reach a folder twice, and copying into it twice fails
    on the second: the folder is no longer empty."""
    def go(home):
        p = os.path.join(home, "code", "wt", "Packages", "GlyphCore")
        os.makedirs(p)
        fleet._TREES.clear()
        bad, _ = rig.bad_glyphcore({"home": home, "code": home + "/code"})
        assert len(bad) == 1, bad
        fleet._TREES.clear()
    sand(go)


def test_the_lock_conventions_are_written_and_no_lock_is_taken():
    """A lock this created would stop the first real build, so the action
    writes the convention down and reads the three paths rather than taking
    one."""
    def go(home):
        act = rig.Act("locks", False, None)
        rig.act_locks(act)
        assert os.path.isfile(rig.LOCKS_CONF)
        for _, path in fleet.LOCKS:
            assert "glyph-" in path
        text = open(rig.LOCKS_CONF).read()
        for name, path in fleet.LOCKS:
            assert path in text, path
        again = rig.Act("locks", False, None)
        rig.act_locks(again)
        assert not again.proofs, "already written, nothing to do"
    sand(go)


def test_a_reading_is_taken_again_rather_than_remembered():
    """Every version and every folder walk is remembered for the run, which is
    right for a report and wrong the moment something has been changed."""
    fleet.CACHE["made up"] = 1
    fleet._TREES["d"] = ["nowhere"]
    rig.forget()
    assert "made up" not in fleet.CACHE
    assert not fleet._TREES
    assert fleet.cache() is fleet.CACHE, "and it does not reload from disk"
    assert "made up" not in fleet.cache()


def test_a_path_written_into_a_file_carries_no_home_folder():
    def go(home):
        assert rig.dollar_home(os.path.join(home, ".local", "bin")) \
            == "$HOME/.local/bin"
        assert rig.dollar_home("/Applications/Xcode.app") \
            == "/Applications/Xcode.app"
        assert rig.dollar_home("/Volumes/studio/glyph-build") \
            == "/Volumes/studio/glyph-build"
    sand(go)


def test_who_says_whose_job_each_row_is():
    act = rig.Act("locks", True, None)
    assert rig.who(act, "broken") == "you", "nothing to do and nothing blocked"
    act.proof("x", lambda: True)
    assert rig.who(act, "broken") == "rig"
    act.block("needs a person")
    assert rig.who(act, "broken") == "rig+you"
    assert rig.who(None, "ok") == "-"
    assert rig.who(None, "missing") == "you"


def test_a_summary_never_reports_the_before_state_as_the_after_state():
    """Putting a folder on the PATH in ~/.zshenv is true for the next shell
    and invisible to the one that wrote it, so the whole-block re-read still
    called it broken and the closing line said nine of fifteen when the
    machine was already at eight. The action's own verification wins for the
    check it acted on, and the disagreement is printed rather than hidden."""
    was = {"checks": [{"id": "path.noninteractive", "state": "broken"},
                      {"id": "locks", "state": "ok"}]}
    after = {"id": "path.noninteractive", "state": "ok", "detail": "on the PATH"}
    results = {"path.noninteractive": ("done", after)}
    # The re-read is stubbed. Letting it run for real made this check depend on
    # the machine it ran on: it passed where the host's own PATH check happened
    # to be broken and failed where it was not, which is a check that tests the
    # room rather than the code.
    keep = fleet.setup_block
    try:
        fleet.setup_block = lambda record=None: {
            "ready": False,
            "checks": [{"id": "path.noninteractive", "state": "broken", "detail": "not on it"},
                       {"id": "locks", "state": "ok", "detail": "free"}],
        }
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rig.finish("bens-air", was, results, {}, {"roots": {}})
    finally:
        fleet.setup_block = keep
    said = out.getvalue()
    assert "stale" in said, said        # the disagreement is named
    assert "a new shell reads ok" in said, said
    # and the closing headline counts it as fixed, not as still broken
    assert "path.noninteractive" in said


# --- installing what the other machines have ---------------------------------
# Fru's requirement, and the one thing it must never do: every app installed on
# a new Mac, and not one of them copied from another machine. So these check
# the source, the leftovers and the accounts, with a brew that is a shell
# script in a temporary folder and no network anywhere near it.


def brewery(home, fails=()):
    """A Homebrew prefix with a `brew` that installs by making the folder.

    A stand-in, because the real one is a network call and minutes of work.
    What is checked through it is what rig does and does not run: the command
    it builds, that it builds no other, and that nothing is believed until the
    folder it names is on the disk.
    """
    prefix = os.path.join(home, "brew")
    os.makedirs(os.path.join(prefix, "bin"))
    log = os.path.join(home, "brew.log")
    with open(os.path.join(prefix, "bin", "brew"), "w") as f:
        f.write("#!/bin/sh\n"
                "echo \"$@\" >> %s\n"
                "name=$3; dir=Caskroom\n"
                "[ \"$2\" = --cask ] || { name=$2; dir=Cellar; }\n"
                "for bad in %s; do [ \"$name\" = \"$bad\" ] && exit 1; done\n"
                "mkdir -p %s/$dir/$name/1.0\n"
                % (log, " ".join(fails) or "''", prefix))
    os.chmod(os.path.join(prefix, "bin", "brew"), 0o755)
    for d in ("Cellar", "Caskroom"):
        os.makedirs(os.path.join(prefix, d))
    return prefix, log


def inst(casks=(), formulae=(), apps=(), brew="/opt/homebrew"):
    return {"brew": brew, "casks": [{"name": n, "version": "1"} for n in casks],
            "formulae": [{"name": n, "version": "1", "asked": True}
                         for n in formulae],
            "apps": [dict(a) for a in apps]}


def with_fleet(prefix, mine, reps, fn):
    """rig, run against a fleet invented for the purpose."""
    keep = (fleet.brew_prefix, fleet.load_reports, dict(fleet._INSTALLED))
    try:
        fleet.brew_prefix = lambda: prefix
        fleet.load_reports = lambda: dict(
            (k, {"installed": v}) for k, v in reps.items())
        fleet._INSTALLED["d"] = mine
        return fn()
    finally:
        fleet.brew_prefix, fleet.load_reports = keep[0], keep[1]
        fleet._INSTALLED.clear()
        fleet._INSTALLED.update(keep[2])


def test_an_install_comes_from_homebrew_and_never_from_another_machine():
    """The requirement in one test. An app copied off another Mac carries that
    machine's signature and its login, cannot update itself, and macOS moves
    one it does not trust to the Trash on launch. So the only thing rig runs
    is the `brew install` a person could type, and the proof is the folder
    brew made, read off the disk."""
    def go(home):
        prefix, log = brewery(home)
        act = rig.Act("apps.missing", False, None)
        with_fleet(prefix, inst(brew=prefix),
                   {"studio": inst(casks=["obsidian"], formulae=["eza"]),
                    "air": inst(casks=["obsidian"], formulae=["eza"])},
                   lambda: quiet(lambda: rig.act_install(act)))
        ran = sorted(open(log).read().split("\n")[:-1])
        assert ran == ["install --cask obsidian", "install eza"], ran
        assert not rig.unproved(act), rig.unproved(act)
        assert os.path.isdir(os.path.join(prefix, "Cellar", "eza"))
        assert all("brew uninstall" in u for u in act.undos), act.undos
        # Nothing was copied from anywhere: the only source named is brew.
        assert "cp" not in " ".join(act.undos)
    sand(go)


def test_a_cask_homebrew_does_not_know_is_a_download_and_never_a_skip():
    """A silent skip is how a machine ends up half set up while every check
    reads ok. The app is named, the download is somebody's, and the run says
    so out loud."""
    def go(home):
        prefix, log = brewery(home)
        act = rig.Act("apps.missing", False, None)
        mine = inst(brew=prefix)
        reps = dict((m, inst(apps=[{"name": "Acme Notes", "id": "com.acme.notes"},
                                   {"name": "Pages",
                                    "id": "com.apple.iWork.Pages"}]))
                    for m in ("studio", "air"))
        with_fleet(prefix, mine, reps,
                   lambda: quiet(lambda: rig.act_install(act)))
        assert not os.path.exists(log), "nothing was installed"
        said = " ".join(act.blocked)
        assert "Acme Notes" in said and "download" in said, said
        assert "Pages" in said and "App Store" in said, said
        assert not act.proofs, "and nothing was claimed"
        assert rig.who(act, "missing") == "you"
    sand(go)


def test_a_partial_install_reports_part_and_exits_non_zero():
    """A new Mac is two hundred names behind, and one command that then runs
    unattended for an hour is not something to hand somebody. So a run
    installs a fixed number, says how many are left, and never reads done
    while any of them are."""
    def go(home):
        prefix, log = brewery(home)
        keep = rig.INSTALL_MAX
        try:
            rig.INSTALL_MAX = 2
            mine = inst(brew=prefix)
            reps = dict((m, inst(formulae=["a", "b", "c", "d"]))
                        for m in ("studio", "air"))
            verdict, act, after, missing = with_fleet(
                prefix, mine, reps,
                lambda: with_jobs(rows(), lambda: quiet(
                    lambda: rig.run_action("apps.missing", None))[0]))
            assert sorted(os.listdir(os.path.join(prefix, "Cellar"))) == \
                ["a", "b"], os.listdir(os.path.join(prefix, "Cellar"))
            assert not missing, "what it did claim, it did"
            assert verdict == "part", verdict
            assert any("2 more" in w for w in act.blocked), act.blocked
        finally:
            rig.INSTALL_MAX = keep
    sand(go)
    # And the whole command says so: `part` in the table, how many are left
    # beneath it, how to undo every one, and a non-zero exit, which is the
    # half a script notices.
    def whole(home):
        prefix, log = brewery(home)
        keep = (rig.INSTALL_MAX, rig.ORDER)
        try:
            rig.INSTALL_MAX, rig.ORDER = 2, ["apps.missing"]
            reps = dict((m, inst(formulae=["a", "b", "c", "d"]))
                        for m in ("studio", "air"))
            got, said = with_fleet(
                prefix, inst(brew=prefix), reps,
                lambda: with_jobs(rows(), lambda: quiet(
                    lambda: rig.cmd_apply(Args(yes=True)))))
        finally:
            rig.INSTALL_MAX, rig.ORDER = keep
        assert got == 1, said
        assert "install  formula a" in said, "it says where it got to"
        assert "part" in said, said
        assert "2 more to install" in said, said
        assert "brew uninstall a" in said, "every change says how to reverse it"
        assert "0 of 1 verified" in said, said
    sand(whole)


def test_an_install_that_fails_is_not_done_however_brew_exited():
    """Nothing is believed on the strength of having run. brew has printed a
    warning, exited 0 and installed nothing where a cask was already there
    under another name, so the folder is looked for afterwards."""
    def go(home):
        prefix, log = brewery(home, fails=("eza",))
        act = rig.Act("apps.missing", False, None)
        with_fleet(prefix, inst(brew=prefix),
                   dict((m, inst(formulae=["eza"])) for m in ("studio", "air")),
                   lambda: quiet(lambda: rig.act_install(act)))
        assert rig.unproved(act) == ["formula eza"], rig.unproved(act)
        assert "brew uninstall eza" in act.undos, act.undos
    sand(go)


def test_a_sign_in_is_named_every_time_and_never_counted():
    """1Password is exactly the line rig must not cross. It can put the app on
    a machine and must never read as having signed into it, so the account is
    in `blocked` and never in `proofs`, whether the app is here yet or not."""
    def go(home):
        prefix, log = brewery(home)
        act = rig.Act("apps.missing", False, None)
        with_fleet(prefix, inst(brew=prefix),
                   dict((m, inst(casks=["1password"])) for m in ("studio", "air")),
                   lambda: quiet(lambda: rig.act_install(act)))
        said = " ".join(act.blocked)
        assert "signed in by you, never by this" in said, said
        assert [w for w, _ in act.proofs] == ["cask 1password"], act.proofs
        assert "sign" not in " ".join(w for w, _ in act.proofs)
        # Already installed here and nothing missing: still named, still not
        # a thing anybody claimed.
        act = rig.Act("apps.missing", False, None)
        with_fleet(prefix, inst(brew=prefix, casks=["1password"]),
                   dict((m, inst(casks=["1password"])) for m in ("studio", "air")),
                   lambda: quiet(lambda: rig.act_install(act)))
        assert not act.proofs, "nothing to install"
        assert any("1password" in w for w in act.blocked), act.blocked
    sand(go)


def test_no_homebrew_is_the_blocker_and_rig_does_not_install_it():
    """A download piped into a shell, a password prompt and the Command Line
    Tools. The same class of thing as installing Xcode, and the honest answer
    is to name it rather than to do it quietly."""
    def go(home):
        act = rig.Act("apps.missing", False, None)
        with_fleet(None, inst(brew=None), {"studio": inst(formulae=["eza"])},
                   lambda: rig.act_install(act))
        assert not act.proofs, act.proofs
        assert any("brew.sh" in w for w in act.blocked), act.blocked
        assert rig.who(act, "broken") == "you"
    sand(go)


def test_the_view_writes_nothing_and_says_what_cannot_be_installed():
    """`glyph rig apps` is the question a new machine asks, and it is a view:
    it reads the readings every machine wrote and changes nothing at all."""
    def go(home):
        prefix, log = brewery(home)
        before = tree(home)
        reps = dict((m, inst(casks=["obsidian"], formulae=["eza"],
                             apps=[{"name": "Acme Notes", "id": "com.acme.notes"}]))
                    for m in ("studio", "air"))
        got, said = with_fleet(
            prefix, inst(brew=prefix), reps,
            lambda: quiet(lambda: rig.cmd_apps(Args(all=False))))
        assert got == 0, said
        assert "brew install --cask obsidian" in said, said
        assert "Acme Notes" in said and "download it" in said, said
        assert "2 of the 3" in said, said
        assert tree(home) == before, "a view wrote something"
        assert not os.path.exists(log), "and ran brew"
    sand(go)

def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print("ok   %s" % t.__name__)
    print("%d checks passed" % len(tests))
    return 0


if __name__ == "__main__":
    sys.exit(main())
