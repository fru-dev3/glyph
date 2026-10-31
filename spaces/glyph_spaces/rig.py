"""glyph rig: making a machine able to do the work, not only saying it cannot.

`plan` prints what would change here and what only a person can do, and writes
nothing. `apply` does the automatable part, and refuses without `--yes`.

Every action is named for a check in `fleet.py`'s `setup` block. The plan is
generated from those checks as they answer right now, and the same check is
what proves the action worked afterwards, so there is no second list here of
the things that can go wrong. A check with no action says why it has none.

Four rules, each of them paid for on one day when eight separate things looked
exactly like success while never touching what they named:

- **A step without a check is not done.** Every action is read back twice: each
  thing it says it wrote is looked for on the disk, and the check it is named
  for is asked again. `done` needs both. Nothing here believes an exit code: in
  a worktree with a submodule, `git reset --hard` has printed a fatal error,
  exited 0, moved the working tree and left HEAD where it was.
- **Dry run is the default.** `plan` writes nothing, and `apply` without
  `--yes` prints the plan and changes nothing. One function both describes and
  does each action, so a plan cannot drift from what apply would run.
- **A human step is never counted as done.** Three permissions cannot be
  granted from a shell at all, so they are named, left, and keep the machine
  not ready. They are printed apart from everything else, because naming the
  clicks is the feature and implying they were handled is the worst outcome.
- **Nothing is made worse.** Every change says how to reverse it, a file is
  backed up before it is edited, nothing a person put there is deleted, no
  keychain is touched, no lock another process holds is removed, and the whole
  `setup` block is read again at the end, so an action that fixed its own check
  and broke another one is reported rather than missed.

Everything written lands under the home folder of the account running it, which
is also why `apply` refuses to act on any machine but this one. There is no
remote half: changing PATH or `DEVELOPER_DIR` underneath work already running
somewhere else is the damage this exists to prevent.
"""
import os, shutil

from glyph_spaces import core, fleet

HOME = fleet.HOME
# One marked block in one file, so every line this owns can be found and taken
# out again, and writing it twice changes nothing.
MARK_TOP = "# >>> glyph rig >>>"
MARK_END = "# <<< glyph rig <<<"
# ~/.zshenv is the one file a non-interactive shell reads, which is the whole
# reason the block goes there: `ssh machine 'cmd'` reads /etc/zshenv and this,
# and a folder added in ~/.zprofile or ~/.zshrc is simply not there.
ZSHENV = os.path.join(HOME, ".zshenv")
SUFFIX = ".glyph-rig.bak"
LOCKS_CONF = os.path.join(HOME, ".config", "glyph", "locks.conf")
# The same three folders fleet.path_check asks about. Named here because the
# check builds them inline; test_rig keeps the two from drifting apart.
PATH_WANT = ("/opt/homebrew/bin", "/usr/local/bin", "~/.local/bin")
# Build output wants more room than the floor a build dies under, or moving it
# has bought nothing.
SCRATCH_WANT = fleet.DISK_FLOOR * 4
# Why a check that is not ok has no action. Each one is a rule, not a gap.
NO_ACTION = {
    "tcc.microphone": "no shell can grant a permission",
    "tcc.speech": "no shell can grant a permission",
    "tcc.screen-recording": "no shell can grant a permission",
    "signing.identity": "nothing here touches a keychain",
    "disk.boot-free": "freeing space deletes files; build.scratch moves "
                      "build output instead",
    "xcode.devicesupport": "xcode.developer-dir covers the Xcode half, a "
                           "cable covers the rest",
    "repo.access": "signing in is a browser and a person; a token written "
                   "from here would be a secret this never handles",
    "repo.one-account": "signing an identity out of a machine is somebody's "
                        "own account, not this tool's call",
}


# --- the context an action works through -------------------------------------
# Every action is one function and runs twice over its life: once to describe
# itself and once to do the work. The difference is this object's `dry` and
# nothing else, so a plan is the apply with its hands tied rather than a second
# description of it that can disagree.
#
# An action says one line about itself. The writers below say nothing: they
# record how to reverse what they did and what to look for on the disk
# afterwards, and nothing else, because a plan needing a paragraph per row has
# failed before anyone reads it.

class Act:
    """One action: its one line, how to undo it, and what proves it."""

    def __init__(self, cid, dry, roots):
        self.cid, self.dry, self.roots = cid, dry, roots
        self.lines, self.undos, self.blocked, self.proofs = [], [], [], []
        self.idle = None                 # the reason there is nothing to do
        self._backed_up = set()

    # --- what it says ---------------------------------------------------
    def say(self, text):
        """The one line this action gets in the table."""
        self.lines.append(text)

    def undo(self, text):
        if text not in self.undos:
            self.undos.append(text)

    def block(self, why):
        """Something only a person can supply. Never a failure, never a done."""
        self.blocked.append(why)

    def nothing(self, why):
        self.idle = why

    def proof(self, what, read):
        """Something to read off the disk afterwards, and how to read it."""
        self.proofs.append((what, read))

    def wanted(self):
        """Whether this would change anything, which is whether it left a proof."""
        return bool(self.proofs)

    def line(self):
        return "; ".join(self.lines) or (self.idle or "-")

    # --- what it does ---------------------------------------------------
    def mkdir(self, path, mode=0o755):
        if os.path.isdir(path):
            return
        self.undo("remove %s if it is still empty" % fleet.tilde(path))
        self.proof(fleet.tilde(path), lambda: os.path.isdir(path))
        if not self.dry:
            os.makedirs(path, mode=mode, exist_ok=True)
            os.chmod(path, mode)

    def link(self, target, link):
        """Point `link` at `target`, never over anything a person put there.

        A folder with something in it is left exactly as it is and reported: a
        build folder holding output is somebody's build, and a saved minute of
        linking is not worth losing it.
        """
        if points_at(link, target):
            return
        if os.path.islink(link):
            old = os.path.realpath(link)
            self.undo("ln -sfn %s %s" % (fleet.tilde(old), fleet.tilde(link)))
        elif os.path.isdir(link) and os.listdir(link):
            self.block("%s already holds output; move it when nothing is "
                       "building" % fleet.tilde(link))
            return
        elif os.path.isdir(link):
            self.undo("rm %s && mkdir %s" % (fleet.tilde(link),
                                             fleet.tilde(link)))
        elif os.path.exists(link):
            self.block("%s is a file, not a folder" % fleet.tilde(link))
            return
        else:
            self.undo("rm %s" % fleet.tilde(link))
        self.proof(fleet.tilde(link), lambda: points_at(link, target))
        if self.dry:
            return
        os.makedirs(target, exist_ok=True)
        os.makedirs(os.path.dirname(link), exist_ok=True)
        if os.path.isdir(link) and not os.path.islink(link):
            os.rmdir(link)                   # empty, checked above
        swap(target, link)

    def point(self, target, link):
        """A symlink to one file, for a binary that answers on PATH.

        A real file there is moved aside rather than thrown away: whatever
        installed it did so for a reason, and the move is one `mv` to reverse.
        Callers only ever hand this a path inside the home folder.
        """
        if points_at(link, target):
            return
        real = os.path.exists(link) and not os.path.islink(link)
        old = os.path.realpath(link) if os.path.islink(link) else None
        if real:
            self.undo("mv %s%s %s" % (fleet.tilde(link), SUFFIX,
                                      fleet.tilde(link)))
        else:
            self.undo("ln -sfn %s %s" % (fleet.tilde(old), fleet.tilde(link))
                      if old else "rm %s" % fleet.tilde(link))
        self.proof(fleet.tilde(link), lambda: points_at(link, target))
        if self.dry:
            return
        os.makedirs(os.path.dirname(link), exist_ok=True)
        if real:
            os.replace(link, link + SUFFIX)
        swap(target, link)

    def copy_file(self, src, dst, mode=0o755):
        if os.path.exists(dst):
            self.block("%s is already there" % fleet.tilde(dst))
            return
        self.undo("rm %s" % fleet.tilde(dst))
        self.proof(fleet.tilde(dst),
                   lambda: os.path.isfile(dst) and os.access(dst, os.X_OK))
        if self.dry:
            return
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        os.chmod(dst, mode)

    def copy_tree(self, src, dst):
        """A folder copied in, never linked.

        git refuses a symlinked submodule path with `expected submodule path
        not to be a symbolic link` while printing the commit it thinks it is
        on, so a copy is the only thing that works.
        """
        self.undo("rm -r %s, which this put there" % fleet.tilde(dst))
        self.proof(fleet.tilde(dst),
                   lambda: not os.path.islink(dst)
                   and os.path.isfile(os.path.join(dst, "Package.swift")))
        if self.dry:
            return
        if os.path.islink(dst):
            os.remove(dst)                   # a link, not anybody's folder
        elif os.path.isdir(dst):
            os.rmdir(dst)                    # empty, checked by the caller
        shutil.copytree(src, dst, symlinks=False,
                        ignore=shutil.ignore_patterns(".git", ".build"))
        # The copy carries no submodule identity, and git treats a .git file
        # naming a gitdir that is not there as a broken submodule.
        inner = os.path.join(dst, ".git")
        if os.path.isfile(inner):
            os.remove(inner)

    def write(self, path, text, mode=0o644):
        if file_is(path, text):
            return
        self.undo("rm %s" % fleet.tilde(path))
        self.proof(fleet.tilde(path), lambda: file_is(path, text))
        if self.dry:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(text)
        os.chmod(path, mode)

    def env(self, lines):
        """Add exports to the marked block in ~/.zshenv, backing it up first.

        Rewritten whole each time, so two actions adding a line each leave one
        block, and a second run leaves the same one.
        """
        have = read_block(ZSHENV)
        want = have + [l for l in lines if l not in have]
        if want == have:
            return
        self.undo("take the lines between %s and %s out of %s%s"
                  % (MARK_TOP, MARK_END, fleet.tilde(ZSHENV),
                     ", or put %s%s back" % (fleet.tilde(ZSHENV), SUFFIX)
                     if os.path.isfile(ZSHENV) else
                     ", which was not there before this"))
        self.proof("%s carries %s"
                   % (fleet.tilde(ZSHENV),
                      ", ".join(l.split("=")[0].split()[-1] for l in lines)),
                   lambda: all(l in read_block(ZSHENV) for l in lines))
        if self.dry:
            return
        self.backup(ZSHENV)
        write_block(ZSHENV, want)

    def backup(self, path):
        """A copy beside the file, once per run, before it is first edited."""
        if path not in self._backed_up and os.path.isfile(path):
            shutil.copy2(path, path + SUFFIX)
        self._backed_up.add(path)


def points_at(link, target):
    """Whether a symlink is there and resolves where it was pointed."""
    return (os.path.islink(link)
            and os.path.realpath(link) == os.path.realpath(target))


def swap(target, link):
    """Replace a symlink in one step, so there is no moment with no link."""
    tmp = link + ".glyph-rig.tmp"
    if os.path.lexists(tmp):
        os.remove(tmp)
    os.symlink(target, tmp)
    os.replace(tmp, link)


def file_is(path, text):
    try:
        with open(path) as f:
            return f.read() == text
    except OSError:
        return False


def dollar_home(path):
    """A path with $HOME where the home folder is, for a line in a file.

    Not a tilde, which inside the double quotes of an export stays a tilde and
    names nothing. Not the home path spelled out either, since the file would
    then be wrong for anybody else and would say whose machine this is.
    """
    return "$HOME" + path[len(HOME):] if path.startswith(HOME) else path


def read_block(path):
    """The lines this owns in a file, in order. Empty when there is no block."""
    out, inside = [], False
    try:
        with open(path) as f:
            for line in f:
                line = line.rstrip("\n")
                if line == MARK_TOP:
                    inside = True
                elif line == MARK_END:
                    inside = False
                elif inside and line.strip() and not line.startswith("#"):
                    out.append(line)
    except OSError:
        return []
    return out


def write_block(path, lines):
    """Replace the marked block, leaving every other line where it is."""
    keep, inside, seen = [], False, False
    try:
        with open(path) as f:
            for line in f:
                line = line.rstrip("\n")
                if line == MARK_TOP:
                    inside, seen = True, True
                    keep.append(None)        # where the block goes back
                elif line == MARK_END:
                    inside = False
                elif not inside:
                    keep.append(line)
    except OSError:
        pass
    if not seen:
        keep.append(None)
    block = ([MARK_TOP, "# glyph rig wrote this. Delete the block to undo it."]
             + lines + [MARK_END])
    out = []
    for line in keep:
        out.extend(block) if line is None else out.append(line)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write("\n".join(out).rstrip("\n") + "\n")


# --- the actions, one per check id -------------------------------------------

def act_path(act):
    """The PATH a command over ssh is given.

    xcodegen installed in /opt/homebrew/bin is not on a non-interactive PATH,
    so `xcodegen generate && xcodebuild` falls through without saying why, and
    the next session blames the signing certificate.
    """
    got, _ = fleet.noninteractive_path()
    have = set(p for p in (got or "").split(":") if p)
    if not have:
        act.block("the PATH a non-interactive shell gets could not be read")
        return
    want = [d for d in (os.path.expanduser(p) for p in PATH_WANT)
            if os.path.isdir(d) and d not in have]
    if not want:
        act.nothing("already on the non-interactive PATH")
        return
    act.env(['export PATH="%s:$PATH"'
             % ":".join(dollar_home(d) for d in want)])
    act.say("%d folder%s onto the PATH in %s"
            % (len(want), "" if len(want) == 1 else "s", fleet.tilde(ZSHENV)))


def act_devdir(act):
    """DEVELOPER_DIR, pointed at a full Xcode and not the Command Line Tools.

    Set in ~/.zshenv rather than with `xcode-select -s`, which wants sudo and
    changes the machine for everything on it. A build needs a full Xcode or
    the FoundationModels macro plugin fails with an error that reads like a
    source problem.

    The file reaches every build a script or an agent starts, since those come
    through a shell, and this check reads it back from one. A process that did
    not, a launchd job or an app, still gets `xcode-select -p`, and that is the
    sudo this does not run: it stays in `human` on the check.
    """
    path, kind = fleet.developer_dir()
    if kind == "xcode":
        act.nothing("already a full Xcode")
        return
    found = fleet.xcode_apps()
    if not found:
        act.block("no full Xcode here to point at; installing one is a "
                  "download and a licence prompt")
        return
    act.env(['export DEVELOPER_DIR="%s"' % dollar_home(found[0])])
    # The app bundle rather than its Contents/Developer, which is the same
    # thing said in nineteen fewer characters.
    act.say("DEVELOPER_DIR to %s"
            % fleet.tilde(found[0]).replace("/Contents/Developer", ""))


def scratch_volume():
    """(folder, why) for build output: told, or the roomiest other volume.

    An external volume is what a boot disk at 101 MB free was fixed with, and
    choosing one rather than documenting a flag is the point: a build lands
    off the boot volume whether or not its script remembered anything.
    """
    told = os.environ.get("GLYPH_BUILD_SCRATCH")
    if told:
        return os.path.expanduser(told), "GLYPH_BUILD_SCRATCH"
    best = None
    for name in fleet.listnames("/Volumes"):
        mount = os.path.join("/Volumes", name)
        if fleet.on_boot(mount) is not False or not os.access(mount, os.W_OK):
            continue
        free = fleet.free_on(mount)
        if free and free >= SCRATCH_WANT and (not best or free > best[1]):
            best = (mount, free)
    if not best:
        return None, None
    return os.path.join(best[0], "glyph-build"), "%s free" % fleet.gbs(best[1])


def act_scratch(act):
    """Build output, pre-linked off the boot volume.

    One boot volume reached 101 MB free and broke builds with `ld: write()
    failed errno=28` and SwiftPM's "Could not resolve package dependencies",
    neither of which mentions a disk, and the failed extract left an
    xcframework SwiftPM then refused forever.
    """
    where, _ = fleet.derived_data()
    free = fleet.free_on(where)
    told = bool(os.environ.get("GLYPH_BUILD_SCRATCH"))
    if not told and free and free >= fleet.DISK_FLOOR:
        act.nothing("%s where build output already goes" % fleet.gbs(free))
        return
    scratch, _ = scratch_volume()
    if not scratch:
        act.block("no volume but the boot disk with %s free; attach one or "
                  "set GLYPH_BUILD_SCRATCH" % fleet.gbs(SCRATCH_WANT))
        return
    if fleet.on_boot(scratch):
        act.block("%s is on the boot volume too" % fleet.tilde(scratch))
        return
    act.mkdir(scratch)
    act.link(os.path.join(scratch, "derived-data"),
             os.path.expanduser("~/Library/Developer/Xcode/DerivedData"))
    # And the swift packages, so a `swift build` lands there too with no
    # caller remembering a flag. One of these machines carries 115 worktrees.
    pre, seen = 0, set()
    for d in fleet.project_dirs(act.roots):
        # One link per folder. Overlapping roots, say `~` and `~/code`, reach
        # the same package twice, and counting it twice would overstate the
        # work in the one line this gets.
        if os.path.realpath(d) in seen:
            continue
        seen.add(os.path.realpath(d))
        if not os.path.isfile(os.path.join(d, "Package.swift")):
            continue
        build = os.path.join(d, ".build")
        if os.path.lexists(build):
            continue                         # somebody's output, or already a link
        act.link(os.path.join(scratch, "build", os.path.basename(d)), build)
        pre += 1
    act.say("build output to %s, %d pre-linked" % (fleet.tilde(scratch), pre))


def act_appleid(act):
    """The App Store Connect key, which is how an iPhone install needs no sign-in.

    One machine had Xcode, a valid certificate and the key on disk but no
    Apple ID signed in, so -allowProvisioningUpdates had nothing to register a
    device with. The key block every install script carries,
    -authenticationKeyPath / -authenticationKeyID / -authenticationKeyIssuerID,
    works without an interactive sign-in, and it needs the key where
    xcodebuild looks for it.
    """
    if fleet.asc_keys():
        act.nothing("a key is already where xcodebuild looks")
        return
    key = os.environ.get("GLYPH_ASC_KEY")
    if not key or not os.path.isfile(os.path.expanduser(key)):
        act.block("set GLYPH_ASC_KEY to the AuthKey_<id>.p8; nothing here "
                  "goes looking for a secret")
        return
    key = os.path.expanduser(key)
    where = os.path.expanduser("~/.appstoreconnect/private_keys")
    act.mkdir(where, 0o700)
    # Linked, never copied: the key stays in one place, and this never holds a
    # second copy of a secret it would then have to be trusted to remove.
    act.point(key, os.path.join(where, os.path.basename(key)))
    ids = [n for n in ("GLYPH_ASC_KEY_ID", "GLYPH_ASC_ISSUER_ID")
           if os.environ.get(n)]
    if ids:
        act.env(['export %s="%s"' % (n, os.environ[n]) for n in ids])
    for name in ("GLYPH_ASC_KEY_ID", "GLYPH_ASC_ISSUER_ID"):
        if not os.environ.get(name):
            act.block("%s is unset, so a build still needs it another way"
                      % name)
    act.say("the key into %s, %d of 2 ids"
            % (fleet.tilde(where), len(ids)))


def act_engine(act):
    """The engine, and whatever answers to its name on PATH.

    One machine had no engine at all, which is why Studio could never be built
    or tested there. On another, the name on PATH was a build from source three
    minor versions behind everything else, so anyone typing it got the old one.
    """
    engine, onpath = fleet.engine_paths()
    said = []
    if not engine:
        src = os.environ.get("GLYPH_ENGINE_SRC")
        if not src or not os.path.isfile(os.path.expanduser(src)):
            act.block("no engine here and no GLYPH_ENGINE_SRC naming one")
            return
        engine = os.path.expanduser(os.environ.get("GLYPH_ENGINE")
                                    or "~/.local/lib/glyph/prevail")
        act.copy_file(os.path.expanduser(src), engine)
        said.append("the engine installed")
    if onpath and not points_at(onpath, engine):
        mine = os.path.join(HOME, ".local", "bin")
        if os.path.dirname(onpath) != mine:
            act.block("the stale one is at %s, which a package manager owns; "
                      "put %s earlier on PATH"
                      % (fleet.tilde(onpath), fleet.tilde(mine)))
        else:
            act.point(engine, onpath)
            said.append("%s to %s" % (fleet.tilde(onpath),
                                      "it" if said else "the installed engine"))
    if not act.wanted():
        act.nothing("the engine and the name on PATH are the same build")
        return
    act.say(", ".join(said))


def act_locks(act):
    """The three shared-resource locks, written down rather than taken.

    Each is a directory taken with mkdir, its holder written in the same
    breath, released by a trap, and per machine. Nothing here takes one: a
    lock this created would stop the first real build. What a new machine is
    missing is the convention, so every script on it agrees which path is
    which, and `glyph fleet setup` is what reports who holds one.
    """
    if file_is(LOCKS_CONF, LOCKS_TEXT):
        act.nothing("the conventions are written down")
        return
    act.write(LOCKS_CONF, LOCKS_TEXT)
    act.say("the 3 lock conventions into %s" % fleet.tilde(LOCKS_CONF))


LOCKS_TEXT = """# The shared resources on this machine, one lock each.
#
# Written by glyph rig apply. Each lock is a directory taken with mkdir, which
# fails when it exists, so taking one is the test. Write the holder in the same
# breath and release it from a trap:
#
#   if mkdir /tmp/glyph-build.lock.d 2>/dev/null; then
#     print -r -- "$branch on $(scutil --get ComputerName)" \\
#       > /tmp/glyph-build.lock.d/holder
#     trap 'rm -rf /tmp/glyph-build.lock.d' EXIT INT TERM
#   fi
#
# A lock with no holder file is reported unknown, never assumed stale: a build
# that has taken one has not always written its holder yet, and reading that as
# free is how two builds collide. `glyph fleet setup` says who holds what.

build   /tmp/glyph-build.lock.d    any xcodebuild or release swift build
sim     /tmp/glyph-sim.lock        the iPhone simulator
mac-ui  /tmp/glyph-mac-ui.lock.d   the Mac screen
"""


def bad_glyphcore(roots):
    """(path, kind) for every GlyphCore that cannot be used, and the good ones.

    The same two tests fleet.glyphcore_check applies, told apart one step
    further: a folder with files in it but no Package.swift is a checkout
    somebody started, and nothing here replaces one of those.
    """
    paths = [os.path.expanduser(p) for p in
             (os.environ.get("GLYPH_GLYPHCORE") or "").split(":") if p]
    paths += fleet.found_under(roots, "Packages/GlyphCore")
    # One row per folder. Where a machine's roots overlap, say `~` and
    # `~/code`, the same checkout is reached twice, and copying into it twice
    # fails on the second: the folder is no longer empty.
    seen, once = set(), []
    for p in paths:
        key = os.path.realpath(p) if not os.path.islink(p) else p
        if key not in seen:
            seen.add(key)
            once.append(p)
    bad, good = [], []
    for p in once:
        if os.path.islink(p):
            bad.append((p, "link"))
        elif not os.path.isfile(os.path.join(p, "Package.swift")):
            bad.append((p, "empty" if not fleet.listnames(p) else "partial"))
        else:
            good.append(p)
    return bad, good


def act_glyphcore(act):
    """The GlyphCore submodule in a worktree that cannot init it.

    Do not symlink it: `git checkout origin/<branch> -- <path>` then fails
    with `expected submodule path not to be a symbolic link` while printing
    the commit it thinks it is on. Copy instead, and drop the .git file the
    copy would otherwise carry.
    """
    bad, good = bad_glyphcore(act.roots)
    if not bad:
        act.nothing("every checkout has sources" if good
                    else "no GlyphCore checkout under this machine's roots")
        return
    told = os.environ.get("GLYPH_GLYPHCORE_SRC")
    src = os.path.expanduser(told) if told else (good[0] if good else None)
    if not src or not os.path.isfile(os.path.join(src, "Package.swift")):
        act.block("no healthy GlyphCore to copy from; set GLYPH_GLYPHCORE_SRC")
        return
    waiting = 0
    for p, kind in bad:
        if kind == "partial":
            waiting += 1
            continue
        act.copy_tree(src, p)
    if waiting:
        act.block("%d checkout%s %s files but no Package.swift, so nothing "
                  "here touches %s"
                  % (waiting, "" if waiting == 1 else "s",
                     "has" if waiting == 1 else "have",
                     "it" if waiting == 1 else "them"))
    act.say("GlyphCore copied into %d of %d checkouts"
            % (len(bad) - waiting, len(bad)))


ACTIONS = {
    "path.noninteractive": act_path,
    "xcode.developer-dir": act_devdir,
    "build.scratch": act_scratch,
    "xcode.appleid": act_appleid,
    "engine.version": act_engine,
    "locks": act_locks,
    "submodule.glyphcore": act_glyphcore,
}
# Worst first, the order fleet.SETUP_ORDER puts them in, so the thing that
# breaks a build soonest is both planned and applied first.
ORDER = [c for c in fleet.SETUP_ORDER if c in ACTIONS]
# Two actions have work to do on a machine whose check already reads `ok`, and
# every other one is only planned when its check does not. The lock
# conventions are missing on a bare Mac while all three locks are free, and
# build output moves on request even where the boot disk still has room.
RUN_WHEN_OK = ("locks", "build.scratch")


# --- reading the state back --------------------------------------------------

def forget():
    """Drop every answer kept from before an action ran.

    A version is remembered against a file's path, size and time, and a folder
    walk is remembered for the run. Both are right for a report and wrong
    here: the whole question after an action is whether the disk changed.
    """
    fleet._TREES.clear()
    fleet.CACHE.clear()
    fleet.CACHE["_"] = 1                     # loaded, and deliberately empty


def verify(cid, roots):
    """The check this action is named for, asked again, from the disk.

    Never the exit code of whatever the action ran. `git reset --hard` has
    printed a fatal error, exited 0, moved the working tree and left HEAD
    unmoved, and eight things in one day looked like success while never
    touching what they named. A check that will not answer is `unknown`.

    Two of them are asked through a fresh shell, because what they read is
    exactly what this process cannot have changed: a line written to
    ~/.zshenv reaches the next non-interactive shell and nothing in this one.
    """
    forget()
    kept = {"SSH_CONNECTION": os.environ.get("SSH_CONNECTION")}
    try:
        if cid == "xcode.developer-dir":
            # Kept for the rest of the run rather than put back, because it is
            # now what the machine hands a new shell, and the reading at the
            # end has to be about the machine and not about this process.
            got = shell_var("DEVELOPER_DIR")
            if got:
                os.environ["DEVELOPER_DIR"] = got
        if cid == "path.noninteractive":
            # Over ssh the check answers with this session's own PATH, handed
            # down before anything was written. Asked without that, it starts
            # a fresh shell, which is the thing being verified.
            os.environ.pop("SSH_CONNECTION", None)
        job = fleet.SETUP_JOBS.get(fleet.owner(cid))
        rows = fleet.guard("verify %s" % cid, job, roots) if job else None
    finally:
        for k, v in kept.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    row = dict((r["id"], r) for r in (rows or [])).get(cid)
    return row or fleet.chk(cid, "unknown",
                            "the check would not answer when it was asked "
                            "again, so whether this worked is unknown")


def shell_var(name):
    """What a non-interactive shell exports for one variable.

    The question fleet.noninteractive_path asks about PATH, for one name: the
    login shell with its environment stripped to what sshd hands it, so
    ~/.zshenv is read and nothing else is.
    """
    import pwd
    shell = pwd.getpwuid(os.getuid()).pw_shell or "/bin/zsh"
    out = fleet.run(["env", "-i", "HOME=%s" % HOME,
                     "PATH=/usr/bin:/bin:/usr/sbin:/sbin", "SHELL=%s" % shell,
                     shell, "-c", 'printf %%s "${%s}"' % name],
                    timeout=3.0, strict=True)
    return (out or "").strip()


def unproved(act):
    """Which of an action's own claims the disk does not bear out."""
    out = []
    for what, read in act.proofs:
        try:
            if not read():
                out.append(what)
        except Exception as e:
            out.append("%s (%s)" % (what, type(e).__name__))
    return out


# --- planning ----------------------------------------------------------------

def describe(cid, roots, state):
    """One action, run with its hands tied. Writes nothing."""
    act = Act(cid, True, roots)
    if state == "ok" and cid not in RUN_WHEN_OK:
        return act                           # nothing to say, and no column
    try:
        ACTIONS[cid](act)
    except Exception as e:
        act.block("could not work out what it would do: %s: %s"
                  % (type(e).__name__, e))
    return act


def plan(roots=None, record=None):
    """(the setup block, one Act per action). Nothing is written.

    The checks are the same `setup_block` that `glyph fleet report` prints, so
    there is no list of problems here to fall behind it. The one thing on disk
    any of this touches is the signing check's throwaway, signed inside a
    folder it makes and removes under the temp folder, exactly as the report
    does.
    """
    forget()
    block = fleet.setup_block(record if record is not None else {"roots": roots})
    states = dict((c["id"], c["state"]) for c in block.get("checks") or [])
    return block, dict((cid, describe(cid, roots, states.get(cid)))
                       for cid in ORDER)


# --- printing ----------------------------------------------------------------
# The shape glyph fleet status already uses: aligned columns, one line per
# thing, and whatever needs more said about it on its own line beneath rather
# than stacked under every row. Nothing is coloured and nothing is drawn.
ROW = "%-21s %-8s %-60s %s"
DID = "%-21s %-8s %-8s %-49s %s"
SHOWN = 6


def head(mid, block, taken=None):
    checks = block.get("checks") or []
    bad = [c for c in checks if c["state"] != "ok"]
    print("%s  %s%s"
          % (mid, "ready, %d checks" % len(checks) if block.get("ready")
             else "not ready, %d of %d checks" % (len(bad), len(checks)),
             "  read %s" % fleet.age(taken) if taken else ""))


def who(act, state):
    """One word at the right of the row: whose job this is."""
    if act and act.wanted():
        return "rig+you" if act.blocked else "rig"
    if act and act.blocked:
        return "you"
    return "-" if state == "ok" else "you"


def beneath(label, rows, cap=SHOWN):
    """Lines needing more than a column, beneath the table, one per line.

    Capped, except for the two groups where a missing line would be a lie:
    what the disk did not bear out, and how to reverse what was done. The
    same text from two actions is said once.
    """
    seen, out = set(), []
    for cid, text in rows:
        if text not in seen:
            seen.add(text)
            out.append((cid, text))
    for cid, text in out if cap is None else out[:cap]:
        print("%-8s %-20s %s" % (label, cid, text))
    if cap is not None and len(out) > cap:
        print("%-8s %d more" % (label, len(out) - cap))


def table(mid, block, acts):
    """Every check on its own line, worst first, and who it is waiting on."""
    head(mid, block)
    print("")
    print(ROW % ("CHECK", "STATE", "WOULD CHANGE", "WHO"))
    for c in fleet.worst_first(block.get("checks")):
        act = acts.get(c["id"])
        line = act.line() if act else (
            "-" if c["state"] == "ok" else (NO_ACTION.get(c["id"]) or "-"))
        print(ROW % (c["id"], c["state"], line[:60], who(act, c["state"])))
    print("")
    beneath("waiting", [(cid, w) for cid in ORDER for w in acts[cid].blocked])
    fleet.show_human(block.get("checks"), "", mid)
    print("")


def cmd_plan(args):
    """What would change here, and what only a person can do. Writes nothing."""
    if getattr(args, "machine", None) and args.machine != core.machine_id():
        return plan_elsewhere(args.machine)
    roots, record = this_machine()
    block, acts = plan(roots, record)
    table(core.machine_id(), block, acts)
    todo = [cid for cid in ORDER if acts[cid].wanted()]
    print("nothing was changed. %s"
          % ("glyph rig apply --yes does the %d marked rig" % len(todo) if todo
             else "nothing here for glyph rig apply to do"))
    return 0


def plan_elsewhere(mid):
    """Another machine, from the reading it wrote. Still writes nothing.

    There is no remote half on purpose: which volume, which Xcode and which
    folders are facts about that machine's own disks, so the steps are worked
    out there. What is honest from here is which checks are failing, which of
    them this has an action for, and which nobody but a person at that
    keyboard can touch.
    """
    rep = fleet.load_reports().get(mid)
    if not rep or not rep.get("setup"):
        print("no reading with a setup block for %s in %s"
              % (mid, fleet.tilde(fleet.rig_dir())))
        print("glyph fleet status --machine %s --live    ask it for one" % mid)
        return 2
    block = rep["setup"]
    head(mid, block, rep.get("taken"))
    print("")
    print(ROW % ("CHECK", "STATE", "WHAT IT NEEDS", "WHO"))
    for c in fleet.worst_first(block.get("checks")):
        if c["state"] == "ok":
            line, mark = "-", "-"
        elif c["id"] in ACTIONS:
            line, mark = (c.get("fix") or c.get("detail") or "-"), "rig"
        else:
            line, mark = (NO_ACTION.get(c["id"]) or "-"), "you"
        print(ROW % (c["id"], c["state"], line[:60], mark))
    print("")
    fleet.show_human(block.get("checks"), "", mid)
    print("")
    print("ssh %s '~/.local/bin/glyph-fleet rig plan'    the steps, worked out there"
          % mid)
    print("apply runs on the machine it changes, never over ssh.")
    return 0


# --- applying ----------------------------------------------------------------

def this_machine():
    """(roots, record) from the spaces map, or (None, None) without one.

    A machine with no map still has every check that reads only its own disks,
    which is the same bargain `glyph fleet report` makes.
    """
    try:
        machines, _ = core.load()
        record = machines.get(core.machine_id())
        return (record or {}).get("roots"), record
    except Exception:
        return None, None


def run_action(cid, roots):
    """Do one action, then read it back. Returns (verdict, act, after, missing).

    Two readings, and both have to agree before anything is called done: each
    thing the action claims it wrote is looked for on the disk, and the check
    this action is named for is asked again. `done` is the check answering
    `ok` with nothing missing. An action that did some of its work and named
    what it waits on is `part`. A check that will not answer is `unknown`.
    Nothing is done on the strength of having run.
    """
    act = Act(cid, False, roots)
    try:
        ACTIONS[cid](act)
    except Exception as e:
        act.block("stopped partway: %s: %s" % (type(e).__name__, e))
        return "failed", act, verify(cid, roots), unproved(act)
    missing = unproved(act)
    after = verify(cid, roots)
    if missing:
        return "failed", act, after, missing
    if after["state"] == "ok":
        return "done", act, after, missing
    if act.blocked:
        return "part", act, after, missing
    if after["state"] == "unknown":
        return "unknown", act, after, missing
    return "failed", act, after, missing


def cmd_apply(args):
    """Do the automatable part, and only with --yes.

    Dry run is the default because that is the difference between a tool that
    can be pointed at a machine and one that cannot be.
    """
    mid = core.machine_id()
    if getattr(args, "machine", None) and args.machine != mid:
        print("apply changes the machine it runs on, never another over ssh.")
        print("ssh %s '~/.local/bin/glyph-fleet rig apply --yes'" % args.machine)
        print("glyph rig plan --machine %s    see it from here first" % args.machine)
        return 2
    if not args.yes:
        cmd_plan(args)
        print("apply needs --yes. Nothing was changed.")
        return 2
    roots, record = this_machine()
    block, acts = plan(roots, record)
    before = dict((c["id"], c) for c in block.get("checks") or [])
    todo = [cid for cid in ORDER if acts[cid].wanted()]
    if not todo:
        # Still the whole table, because what is left over is the answer: a
        # machine with nothing left to automate is not the same as a ready one.
        table(mid, block, acts)
        print("nothing to change.")
        return 0
    head(mid, block)
    print("")
    print(DID % ("CHECK", "WAS", "NOW", "DID", "RESULT"))
    results, undos, waits, gone = {}, [], [], []
    for cid in todo:
        verdict, act, after, missing = run_action(cid, roots)
        results[cid] = (verdict, after)
        print(DID % (cid, before[cid]["state"], after["state"],
                     act.line()[:49], verdict))
        undos += [(cid, u) for u in act.undos]
        waits += [(cid, w) for w in act.blocked]
        gone += [(cid, m) for m in missing]
        if verdict not in ("done", "part"):
            waits.append((cid, "the check says: %s"
                          % (after.get("detail") or "")[:70]))
    print("")
    beneath("missing", gone, None)
    beneath("waiting", waits)
    beneath("undo", undos, None)
    print("")
    return finish(mid, block, results, roots, record)


def finish(mid, was, results, roots, record):
    """Read every check again, and say what the machine is now.

    The whole block rather than only the ones that were touched, because an
    action that fixed its own check and broke another one is exactly the
    damage worth catching, and nothing else in this run would see it.
    """
    forget()
    now = fleet.setup_block(record if record is not None else {"roots": roots})
    # An action's own verification outranks this re-read for the check it
    # acted on. Some changes cannot be seen from inside the process that made
    # them: putting a folder on the PATH in ~/.zshenv is true for the next
    # shell and invisible to this one, so the whole-block read still called it
    # broken and the closing line said nine of fifteen when the machine was
    # already at eight. A summary that reports the before state as the after
    # state is the failure this tool exists to catch.
    stale = []
    byid = dict((c["id"], c) for c in now.get("checks") or [])
    for cid, (_, after) in (results or {}).items():
        seen = byid.get(cid)
        if after and seen and seen["state"] != after["state"]:
            stale.append((cid, "this process still reads %s; a new shell reads %s"
                          % (seen["state"], after["state"])))
            seen.update(after)
    old = dict((c["id"], c["state"]) for c in was.get("checks") or [])
    moved, worse = [], []
    for c in now.get("checks") or []:
        then = old.get(c["id"], "?")
        if then != c["state"]:
            moved.append((c["id"], then, c["state"]))
        if fleet.WORST.get(c["state"], 9) < fleet.WORST.get(then, 9):
            worse.append((c["id"], "was %s, now %s" % (then, c["state"])))
    print("%-20s %-8s %s" % ("CHECK", "WAS", "NOW"))
    for cid, then, got in moved:
        print("%-20s %-8s %s" % (cid, then, got))
    if not moved:
        print("nothing moved")
    print("")
    beneath("stale", stale)
    beneath("worse", worse)
    done = [c for c, (v, _) in sorted(results.items()) if v == "done"]
    print("%d of %d verified by their own checks: %s"
          % (len(done), len(results), ", ".join(done) or "none"))
    head(mid, now)
    # The permissions are why a machine can be fully provisioned and still not
    # ready, and saying so here is the point: they are never counted as done.
    fleet.show_human(now.get("checks"), "", mid)
    print("")
    print("glyph fleet report    write this reading down for the other machines")
    return 0 if len(done) == len(results) and not worse else 1
