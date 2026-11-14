#!/usr/bin/env python3
"""Locate the shared ably/specification clone and, on approval, bring it up to date (the spec-clone sync).

Usage: ensure_spec_clone.py [--spec-clone PATH] [--status | --fetch | --update | --bootstrap [--path PATH]]
                            [--require RELPATH ...] [--timeout SECONDS]

The clone is the first candidate that exists of: --spec-clone PATH (a path
inside a clone is walked up to its root); the clone this script is installed
in (the skill creator's own clone); ABLY_SPEC_CLONE (UTS_SPEC_CLONE is read as
a deprecated alias); the shared default ~/.ably/specification. An explicit path
that isn't in a clone is NOT_A_SPEC_CLONE: it is never replaced by another
candidate. An ABLY_SPEC_CLONE path, or the default, that doesn't exist is
SPEC_CLONE_NOT_FOUND, with `bootstrapPath`.

The sync runs only when the clone in use is the shared clone (ABLY_SPEC_CLONE,
else ~/.ably/specification), however it was found: a path the user names, or
the clone this script is installed in, gets it only when it is that same
directory. Any other clone is never fetched or changed, whatever ABLY_SPEC_SYNC
says: --fetch and --update report NOT_SYNCED_NAMED_CLONE, and
`notSyncedWarning` asks the user to keep it up to date.

Actions (one of):
  --status      (the default) offline: the clone's git state, how stale it is,
                and what rules out a fast-forward (`fastForwardBlockedBy`)
  --fetch       git fetch origin main into refs/remotes/origin/main only: no
                branch and no file changes
  --update      fetch, then `git merge --ff-only --no-overwrite-ignore` of
                origin/main, only when main is checked out, has no tracked
                changes, no merge, rebase, cherry-pick, revert or bisect is in
                progress, and main is strictly behind origin/main; any other
                state is reported and left unchanged
  --bootstrap   clone https://github.com/ably/specification.git to --path, else
                ABLY_SPEC_CLONE, else ~/.ably/specification; refuses if the path
                exists
--require RELPATH (repeatable) adds files a usable clone must have, besides the
UTS docs, the helper specs and specifications/. --timeout bounds each network
command (default 120 s for a fetch, 600 s for a clone).

ABLY_SPEC_SYNC (ask, the default; auto; off) is the user's standing answer to
the sync question, reported as `syncPolicy`; with `off`, --fetch and --update
touch no network (SYNC_OFF). Only clone, fetch, merge --ff-only and read-only
git commands are run; never pull, reset, checkout, switch, stash, clean,
rebase, push or --force, and nothing is deleted except this script's own lock
(`ably-spec-sync.lock` in the clone's git directory, held only around the fetch
and the fast-forward). The fetch updates refs/remotes/origin/main as a default
`git fetch` does (it follows origin even after a force-push there, and the
previous value stays in that ref's reflog); no local branch is touched.

Prints one JSON object: `ok`, `action` (status, fetched, fast-forwarded,
up-to-date, not-updated, cloned), `code`, `message`, `specClone`, `kind`
(explicit, skill-clone, env, shared), `foundBy`, `isSharedClone`, `branch`,
`detached`, `head`, `from`, `to`, `upstream` {ref, sha, ahead, behind,
lastFetch, lastFetchDays}, `onOriginMain`, `trackedChanges`, `untrackedCount`,
`dirtyFiles`, `operationInProgress`, `originUrl`, `originIsAblySpecification`,
`fastForwardBlockedBy`, `syncEligible`, `notSyncedWarning`, `changed`,
`headAgeDays`, `staleWarning`,
`stalenessLine`, `syncPolicy`, `missing`, `bootstrapPath`, `partialLeftovers`
and `warnings`. Exit 0 when the clone is usable, whatever the sync outcome; 1
when it isn't (SPEC_CLONE_NOT_FOUND, NOT_A_SPEC_CLONE, SPEC_CLONE_INCOMPLETE,
SPEC_CLONE_ENV_CONFLICT, BOOTSTRAP_PATH_EXISTS, BOOTSTRAP_FAILED, GIT_ERROR,
INTERNAL_ERROR); 2 on a usage error. Python 3.8+, standard library only.

Rules: the skill creator's references/orient.md 13.9; guide 9.4.
"""
import datetime, json, os, pathlib, re, socket, subprocess, sys, time

URL = "https://github.com/ably/specification.git"
MARKER = "specifications/features.md"
REQUIRED = ["uts/README.md", "uts/docs/writing-derived-tests.md", "uts/docs/writing-test-specs.md",
            "uts/docs/integration-testing.md", "uts/docs/proxy.md", "uts/rest/unit/helpers/mock_http.md",
            "uts/realtime/unit/helpers/mock_websocket.md", "uts/realtime/unit/helpers/mock_vcdiff.md",
            "uts/objects/helpers/standard_test_pool.md", "specifications"]
CREATOR_DIR = ("uts", "skills", "uts-to-lang-skill-creator")
GROUPS = {
    "skill": ["uts/skills/uts-to-lang-skill-creator"],
    "guide": ["uts/docs/writing-uts-spec-translator-skills.md"],
    "utsDocs": ["uts/README.md", "uts/docs/writing-derived-tests.md", "uts/docs/writing-test-specs.md",
                "uts/docs/integration-testing.md", "uts/docs/proxy.md"],
    "helperSpecs": ["uts/rest/unit/helpers", "uts/realtime/unit/helpers", "uts/objects/helpers"],
    "corpus": ["uts/rest", "uts/realtime", "uts/objects"],
}
OPERATIONS = {"MERGE_HEAD": "merge", "CHERRY_PICK_HEAD": "cherry-pick", "REVERT_HEAD": "revert",
              "BISECT_LOG": "bisect", "rebase-merge": "rebase", "rebase-apply": "rebase or am"}
ORIGIN_MAIN = "refs/remotes/origin/main"
POLICIES = ("ask", "auto", "off")
STALE_DAYS = 30
LOCK_NAME = "ably-spec-sync.lock"
LOCK_WAIT = 30
LOCK_STALE = 600
# Per-command settings, never written to the clone's config: no submodules, no automatic gc or maintenance, no stash.
SAFE = ["-c", "submodule.recurse=false", "-c", "gc.auto=0", "-c", "maintenance.auto=false",
        "-c", "merge.autoStash=false"]
REMOTE = re.compile(r"^(?:(?:https?|git|ssh)://(?:[^@/]+@)?(?P<h1>[^/:]+)(?::\d+)?/|(?:[^@/]+@)?(?P<h2>[^/:]+):)"
                    r"(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/*$", re.I)
GITHUB = {"github.com", "www.github.com"}
USAGE = ("usage: ensure_spec_clone.py [--spec-clone PATH] [--status | --fetch | --update | --bootstrap [--path PATH]] "
        "[--require RELPATH ...] [--timeout SECONDS]")


class GitError(RuntimeError):
    pass


def git(clone, *args, timeout=60, network=False):
    """Run git in clone; return stdout. Raises GitError (with git's stderr) on failure or timeout."""
    env = dict(os.environ)
    if network:
        env["GIT_TERMINAL_PROMPT"] = "0"
        env.setdefault("GCM_INTERACTIVE", "never")
        if "GIT_SSH_COMMAND" not in env:  # keep the user's core.sshCommand; only add BatchMode
            ssh = try_git(clone, "config", *([] if clone else ["--global"]), "--get", "core.sshCommand")
            env["GIT_SSH_COMMAND"] = (ssh.strip() if ssh and ssh.strip() else "ssh") + " -o BatchMode=yes"
    cmd = ["git"] + (["-C", str(clone)] if clone else []) + list(args)
    verb = next((a for i, a in enumerate(args) if a != "-c" and (i == 0 or args[i - 1] != "-c")), "")
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
                            timeout=timeout)
    except subprocess.TimeoutExpired:
        raise GitError(f"git {verb} timed out after {timeout} s")
    except OSError as exc:
        raise GitError(f"git couldn't run: {exc}")
    if out.returncode != 0:
        raise GitError(out.stderr.strip() or f"git {' '.join(args)} exited {out.returncode}")
    return out.stdout


def try_git(clone, *args):
    try:
        return git(clone, *args)
    except GitError:
        return None


def default_path():
    return pathlib.Path.home() / ".ably" / "specification"


def policy():
    value = os.environ.get("ABLY_SPEC_SYNC", "").strip().lower()
    return value if value in POLICIES else "ask"


def clone_root(path):
    """The ably/specification clone containing path (path itself or a parent), or None."""
    return next((p for p in [path, *path.parents] if (p / MARKER).is_file()), None)


def own_clone():
    """The clone this script is installed in: <clone>/uts/skills/uts-to-lang-skill-creator/scripts/. Else None."""
    here = pathlib.Path(__file__).resolve().parent
    parents = list(here.parents)
    if here.name == "scripts" and len(parents) > 3 and tuple(parents[i].name for i in (2, 1, 0)) == CREATOR_DIR:
        return parents[3] if (parents[3] / MARKER).is_file() else None
    return None


def env_clone(warnings):
    """(path, how) from ABLY_SPEC_CLONE or the deprecated UTS_SPEC_CLONE; raises ValueError if both differ."""
    new, old = os.environ.get("ABLY_SPEC_CLONE", "").strip(), os.environ.get("UTS_SPEC_CLONE", "").strip()
    if old:
        warnings.append("UTS_SPEC_CLONE is deprecated: rename it to ABLY_SPEC_CLONE")
    if new and old and expand(new) != expand(old):
        raise ValueError(f"ABLY_SPEC_CLONE ({new}) and the deprecated UTS_SPEC_CLONE ({old}) name different "
                        "clones: unset UTS_SPEC_CLONE, or make them agree")
    if new:
        return new, "ABLY_SPEC_CLONE"
    if old:
        return old, "UTS_SPEC_CLONE (deprecated)"
    return None, None


def expand(raw):
    return pathlib.Path(os.path.expanduser(str(raw))).resolve()


def shared_target():
    """Where the shared clone is: ABLY_SPEC_CLONE (or its alias), else the default."""
    raw = os.environ.get("ABLY_SPEC_CLONE", "").strip() or os.environ.get("UTS_SPEC_CLONE", "").strip()
    return expand(raw) if raw else default_path().resolve()


def same_path(a, b):
    """Whether two paths are the same directory (symlinks resolved; case-insensitive where the filesystem is)."""
    try:
        return os.path.samefile(str(a), str(b))
    except OSError:
        return os.path.normcase(str(pathlib.Path(a).resolve())) == os.path.normcase(str(pathlib.Path(b).resolve()))


def shared_root():
    target = shared_target()
    return clone_root(target) or target


def not_synced_warning(loc):
    """The static warning for a clone that isn't the shared clone (None for the shared clone)."""
    if loc.get("isSharedClone") or not loc.get("specClone"):
        return None
    who = "the spec clone you named" if loc.get("kind") == "explicit" else "the clone this skill is installed from"
    return f"Using {who} ({loc['specClone']}). It isn't synced; make sure its UTS specs are up to date."


def leftovers(target):
    parent = target.parent
    return sorted(str(p) for p in parent.glob(target.name + ".partial-*")) if parent.is_dir() else []


def locate(explicit=None, require=()):
    """Resolve the clone by precedence. Returns a dict: ok, code, message, specClone, kind, foundBy, missing, ..."""
    warnings = []

    def candidates():
        if explicit is not None and str(explicit).strip():
            yield "explicit", "argument", explicit
        own = own_clone()
        if own is not None:
            yield "skill-clone", "skill location", str(own)
        env, env_how = env_clone(warnings)  # a conflict matters only once the candidates above are exhausted
        if env:
            yield "env", env_how, env
        yield "shared", "shared default", str(default_path())

    found = candidates()
    while True:
        try:
            kind, how, raw = next(found)
        except ValueError as exc:
            return {"ok": False, "code": "SPEC_CLONE_ENV_CONFLICT", "message": str(exc), "warnings": warnings}
        path = expand(raw)
        if kind in ("env", "shared") and not path.exists():
            return {"ok": False, "code": "SPEC_CLONE_NOT_FOUND", "kind": kind, "foundBy": how,
                    "bootstrapPath": str(path), "partialLeftovers": leftovers(path), "warnings": warnings,
                    "message": f"No ably/specification clone at {path} (from {how}). After STOP-16, offer to clone "
                              f"it there (ensure_spec_clone.py --bootstrap; network), or ask for the path of an "
                              "existing clone (STOP-1)."}
        root = clone_root(path)
        if root is None:
            return {"ok": False, "code": "NOT_A_SPEC_CLONE", "kind": kind, "foundBy": how, "warnings": warnings,
                    "missing": [MARKER], "message": f"{path} (from {how}) is not an ably/specification clone: no "
                                                    f"{MARKER} in it or a parent directory"}
        missing = [rel for rel in list(REQUIRED) + list(require) if not (root / rel).exists()]
        shared = same_path(root, shared_root())
        loc = dict(
            ok=not missing, code="SPEC_CLONE_INCOMPLETE" if missing else "FOUND", specClone=str(root), kind=kind,
            foundBy=how, isSharedClone=shared, syncEligible=shared, missing=missing, warnings=warnings)
        loc["notSyncedWarning"] = not_synced_warning(loc)
        return loc


def last_fetch(clone):
    """Seconds since the epoch of the latest of: an update of origin/main (its reflog), a fetch of main (FETCH_HEAD's
    mtime, which a fetch that changes nothing also renews) and the clone itself (HEAD's "clone:" reflog entry)."""
    times = []
    out = try_git(clone, "reflog", "show", "-n1", "--date=unix", "--format=%gd", ORIGIN_MAIN, "--")
    times += [int(t) for t in re.findall(r"@\{(\d+)\}", out or "")]
    path = try_git(clone, "rev-parse", "--git-path", "FETCH_HEAD")
    if path:
        p = pathlib.Path(path.strip())
        p = p if p.is_absolute() else pathlib.Path(clone) / p
        url = (try_git(clone, "remote", "get-url", "origin") or "").strip().rstrip("/")  # as FETCH_HEAD writes it
        url = url[:-len(".git")] if url.endswith(".git") else url
        try:
            if url and f"branch 'main' of {url}\n" in p.read_text(encoding="utf-8", errors="replace") + "\n":
                times.append(int(p.stat().st_mtime))
        except OSError:
            pass
    out = try_git(clone, "reflog", "show", "--date=unix", "--format=%gd %gs", "HEAD", "--")
    times += [int(m.group(1)) for m in re.finditer(r"@\{(\d+)\} clone:", out or "")]
    return max(times) if times else None


def days(ts, now):
    return None if ts is None else max(0, int((now - ts) // 86400))


def iso(ts):
    return None if ts is None else datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def origin_is_ably_spec(url):
    m = REMOTE.match((url or "").strip())
    if not m or m.group("owner").lower() != "ably" or m.group("repo").lower() != "specification":
        return False
    host = (m.group("h1") or m.group("h2") or "").lower()
    if host in GITHUB:
        return True
    if "." in host:
        return False
    try:  # an SSH host alias: `ssh -G` prints the resolved config and never connects
        out = subprocess.run(["ssh", "-G", host], capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=5)
        hm = re.search(r"(?m)^hostname\s+(\S+)", out.stdout)
        return bool(hm) and hm.group(1).lower() in GITHUB
    except (OSError, subprocess.SubprocessError):
        return False


def redact(url):
    return re.sub(r"^([a-z+]+://)[^@/]+@", r"\1***@", url or "", flags=re.I) or None


def status(clone):
    """The clone's git state, offline. Raises GitError if the clone isn't a usable git checkout."""
    now = time.time()
    head = git(clone, "rev-parse", "HEAD").strip()
    branch = try_git(clone, "symbolic-ref", "-q", "--short", "HEAD")
    branch = branch.strip() if branch else None
    ops = []
    for name, what in OPERATIONS.items():
        p = try_git(clone, "rev-parse", "--git-path", name)
        if p:
            p = pathlib.Path(p.strip())
            if (p if p.is_absolute() else pathlib.Path(clone) / p).exists():
                ops.append(what)
    porcelain = git(clone, "--no-optional-locks", "status", "--porcelain", "--untracked-files=normal").splitlines()
    tracked = [line[3:] for line in porcelain if not line.startswith("??")]
    untracked = sum(1 for line in porcelain if line.startswith("??"))
    dirty = git(clone, "--no-optional-locks", "status", "--porcelain", "--untracked-files=all", "--", "uts",
                "specifications").splitlines()
    url = try_git(clone, "config", "--get", "remote.origin.url")
    url = url.strip() if url else None
    up_sha = try_git(clone, "rev-parse", "-q", "--verify", ORIGIN_MAIN + "^{commit}")
    up_sha = up_sha.strip() if up_sha else None
    ahead = behind = None
    on_main = None
    if up_sha:
        counts = git(clone, "rev-list", "--left-right", "--count", f"HEAD...{ORIGIN_MAIN}").split()
        ahead, behind = int(counts[0]), int(counts[1])
        on_main = ahead == 0
    fetched = last_fetch(clone) if up_sha else None
    head_ts = try_git(clone, "log", "-1", "--format=%ct", "HEAD")
    head_age = days(int(head_ts.strip()), now) if head_ts and head_ts.strip().isdigit() else None
    ably = origin_is_ably_spec(url)
    blocked = []
    if not ably:
        blocked.append("ORIGIN_NOT_ABLY_SPEC")
    if branch is None:
        blocked.append("DETACHED")
    elif branch != "main":
        blocked.append("NOT_ON_MAIN")
    if ops:
        blocked.append("OP_IN_PROGRESS")
    if tracked:
        blocked.append("DIRTY")
    if branch == "main" and ahead:
        blocked.append("DIVERGED" if behind else "AHEAD")
    fetch_days = days(fetched, now)
    stale = None
    if fetched is None:
        stale = "the spec clone's last fetch is unknown (never fetched): it may be far behind origin/main"
    elif fetch_days > STALE_DAYS:
        stale = f"the spec clone was last fetched {fetch_days} days ago: it may be well behind origin/main"
    line = (f"HEAD committed {head_age if head_age is not None else '?'} days ago; "
            + ("origin/main: unknown (never fetched)" if fetched is None else
              f"origin/main as last fetched {fetch_days} days ago was {behind} commit(s) ahead; the real gap may be "
              "larger"))
    return {
        "head": head, "branch": branch, "detached": branch is None,
        "upstream": {"ref": ORIGIN_MAIN, "sha": up_sha, "ahead": ahead, "behind": behind, "lastFetch": iso(fetched),
                    "lastFetchDays": fetch_days},
        "onOriginMain": on_main, "trackedChanges": tracked, "untrackedCount": untracked,
        "dirtyFiles": [line[3:] for line in dirty], "operationInProgress": ops, "originUrl": redact(url),
        "originIsAblySpecification": ably, "fastForwardBlockedBy": blocked, "headAgeDays": head_age,
        "staleWarning": stale, "stalenessLine": line,
    }


def upstream_has(clone, paths):
    """Whether origin/main as last fetched has every path (offline), or None if it isn't known."""
    if try_git(clone, "rev-parse", "-q", "--verify", ORIGIN_MAIN) is None:
        return None
    return all(try_git(clone, "cat-file", "-e", f"{ORIGIN_MAIN}:{p}") is not None for p in paths)


def incomplete_message(loc, st, clone):
    where = f"branch {st['branch']}" if st.get("branch") else "a detached HEAD"
    msg = (f"{loc['specClone']} ({loc['kind']}, found by {loc['foundBy']}) is an ably/specification clone, but its "
          f"checkout ({where} @ {st['head'][:8]}) lacks {len(loc['missing'])} file(s) this skill needs, such as "
          f"{loc['missing'][0]}: that revision predates them. ")
    has = upstream_has(clone, loc["missing"])
    if has:
        return msg + ("origin/main as last fetched has them: the spec-clone sync (fast-forward) fixes this."
                      if loc.get("isSharedClone") else "origin/main as last fetched has them: this clone isn't "
                      "synced, so update it yourself, or use the shared clone.")
    yours = "" if loc.get("isSharedClone") else "; this clone isn't synced, so that fetch is yours"
    known = (f"origin/main as last fetched doesn't have them either (a fetch may show whether it has since{yours}). "
            if has is False else "origin/main was never fetched, so whether it has them is unknown. ")
    return msg + known + ("Meanwhile, use a clone or worktree of a branch that has them: pass --spec-clone <path>, or "
                          "install the skill from that clone (STOP-1).")


def changed(clone, old, new):
    out = {}
    corpus_skip = set()
    for name, paths in GROUPS.items():
        files = [f for f in git(clone, "diff", "--name-only", old, new, "--", *paths).splitlines() if f]
        if name == "helperSpecs":
            corpus_skip = set(files)
        if name == "corpus":
            files = [f for f in files if f not in corpus_skip]
        out[name] = len(files) if name not in ("skill", "guide") else bool(files)
    return out


def lock_path(clone):
    common = pathlib.Path(git(clone, "rev-parse", "--git-common-dir").strip())
    return (common if common.is_absolute() else pathlib.Path(clone) / common) / LOCK_NAME


def acquire(path):
    """Take the sync lock; return None when held, else the holder's details (LOCKED), or {"error": …} when the git
    directory can't be written (a sandbox)."""
    deadline = time.time() + LOCK_WAIT
    while True:
        try:
            fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump({"pid": os.getpid(), "host": socket.gethostname(), "started": time.time()}, f)
            except OSError:
                release(path)  # never leave an empty lock behind
                raise
            return None
        except FileExistsError:
            try:
                holder = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                holder = {}
            if stale_lock(path, holder):
                try:
                    path.unlink()
                    continue
                except OSError:
                    pass
            if time.time() >= deadline:
                if isinstance(holder.get("started"), (int, float)):
                    holder["started"] = iso(holder["started"])
                holder["lock"] = str(path)
                return holder
            time.sleep(1)
        except OSError as exc:
            return {"error": f"can't write the lock {path} ({exc.strerror or exc})"}


def stale_lock(path, holder):
    """Older than LOCK_STALE, on this host, and its process is gone (POSIX only; anything else is asked)."""
    try:
        age = time.time() - path.stat().st_mtime
    except OSError:
        return False
    if age < LOCK_STALE or os.name == "nt" or holder.get("host") != socket.gethostname():
        return False
    try:
        os.kill(int(holder.get("pid")), 0)
    except ProcessLookupError:
        return True
    except (OSError, TypeError, ValueError):
        return False
    return False


def release(path):
    try:
        path.unlink()
    except OSError:
        pass


def sync(clone, action, timeout):
    """--fetch or --update under the lock. Returns (action, code, message, from, to)."""
    st = status(clone)
    if not st["originIsAblySpecification"]:
        return ("not-updated", "ORIGIN_NOT_ABLY_SPEC",
                f"origin is {st['originUrl'] or 'not set'}, not github.com/ably/specification: not fetched", None, None)
    lock = lock_path(clone)
    holder = acquire(lock)
    if holder is not None and "error" in holder:
        return ("not-updated", "FETCH_FAILED", f"not updated: {holder['error']}: the clone's git directory isn't "
                "writable here (a sandbox?); the clone is used as it is", None, None)
    if holder is not None:
        return ("not-updated", "LOCKED", "not updated: another sync of this clone is in progress (pid "
                f"{holder.get('pid')}, host {holder.get('host')}, started {holder.get('started')}); if no other run "
                f"is syncing, the lock {holder['lock']} is stale: the user may remove it", None, None)
    try:
        try:
            git(clone, *SAFE, "fetch", "--no-tags", "--no-recurse-submodules", "origin",
                f"+refs/heads/main:{ORIGIN_MAIN}", timeout=timeout, network=True)
        except GitError as exc:
            first = str(exc).strip().splitlines()[0] if str(exc).strip() else "unknown error"
            return ("not-updated", "FETCH_FAILED", f"not updated: fetch failed ({first}); offline, a sandbox "
                    "denial, or an auth prompt suppressed: the clone is used as it is", None, None)
        if action == "fetch":
            return ("fetched", "FETCHED", "fetched origin/main; no branch or file changed", None, None)
        st = status(clone)
        blocked = [b for b in st["fastForwardBlockedBy"] if b != "ORIGIN_NOT_ABLY_SPEC"]
        up = st["upstream"]
        where = f"on branch {st['branch']}" if st["branch"] else "detached"
        counts = f"{up['ahead']} ahead / {up['behind']} behind origin/main"
        if "DETACHED" in blocked or "NOT_ON_MAIN" in blocked:
            return ("not-updated", blocked[0], f"{where} @ {st['head'][:8]}, {counts}: not updated (the sync never "
                    "switches branches)", None, None)
        if "OP_IN_PROGRESS" in blocked:
            return ("not-updated", "OP_IN_PROGRESS", f"a {', '.join(st['operationInProgress'])} is in progress: "
                    "not updated", None, None)
        if "DIRTY" in blocked:
            return ("not-updated", "DIRTY", f"{len(st['trackedChanges'])} tracked file(s) changed (such as "
                    f"{st['trackedChanges'][0]}): not updated", None, None)
        if "DIVERGED" in blocked or "AHEAD" in blocked:
            code = "DIVERGED" if "DIVERGED" in blocked else "AHEAD"
            return ("not-updated", code, f"main is {counts}: local commits are left alone; not updated"
                    + ("; HEAD isn't on GitHub's main" if code == "AHEAD" else ""), None, None)
        if not up["behind"]:
            return ("up-to-date", "UP_TO_DATE", "up to date (fetched now)", st["head"], st["head"])
        old = st["head"]
        try:
            git(clone, *SAFE, "merge", "--ff-only", "--no-overwrite-ignore", "-q", ORIGIN_MAIN, timeout=timeout)
        except GitError as exc:
            return ("not-updated", "FF_REFUSED", f"fast-forward refused, nothing changed: {exc}", None, None)
        new = git(clone, "rev-parse", "HEAD").strip()
        return ("fast-forwarded", "FAST_FORWARDED", f"fast-forwarded {old[:8]}..{new[:8]} ({up['behind']} "
                "commit(s))", old, new)
    finally:
        release(lock)


def bootstrap(target, timeout):
    """Clone into a temporary sibling, then rename it into place. Returns (ok, code, message)."""
    if target.exists():
        return False, "BOOTSTRAP_PATH_EXISTS", (f"{target} already exists: pass it as the spec clone, or choose "
                                                "another path; nothing is overwritten")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f"{target.name}.partial-{os.getpid()}"
    try:
        git(None, "clone", "-c", "core.autocrlf=false", "--no-recurse-submodules", "-q", URL, str(tmp),
            timeout=timeout, network=True)
    except GitError as exc:
        left = f"; remove the partial clone {tmp}" if tmp.exists() else ""
        first = str(exc).strip().splitlines()[0] if str(exc).strip() else "unknown error"
        return False, "BOOTSTRAP_FAILED", f"clone failed ({first}){left}"
    if target.exists():
        return False, "BOOTSTRAP_FAILED", f"{target} appeared while cloning; the new clone is at {tmp}"
    os.rename(str(tmp), str(target))
    return True, "CLONED", f"cloned {URL} to {target}"


def usage_error(message):
    print(f"{USAGE}\nensure_spec_clone.py: error: {message}", file=sys.stderr)
    return 2


def parse(argv):
    opts = {"action": None, "spec": None, "path": None, "require": [], "timeout": None}
    it = iter(argv)
    for a in it:
        if a in ("--status", "--fetch", "--update", "--bootstrap"):
            if opts["action"]:
                raise ValueError("give one action")
            opts["action"] = a[2:]
        elif a in ("--spec-clone", "--path", "--require", "--timeout"):
            value = next(it, "")
            if not value or value.startswith("-"):
                raise ValueError(f"{a} needs a value")
            if a == "--require":
                opts["require"].append(value)
            elif a == "--timeout":
                try:
                    opts["timeout"] = int(value)
                except ValueError:
                    raise ValueError(f"--timeout needs a number of seconds, got {value}")
                if opts["timeout"] <= 0:
                    raise ValueError("--timeout must be positive")
            else:
                opts[a[2:].replace("-clone", "")] = value
        else:
            raise ValueError(f"unknown argument {a}")
    opts["action"] = opts["action"] or "status"
    if opts["path"] and opts["action"] != "bootstrap":
        raise ValueError("--path goes with --bootstrap")
    if opts["spec"] and opts["action"] == "bootstrap":
        raise ValueError("--bootstrap clones to --path; --spec-clone names an existing clone")
    return opts


def emit(result):
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


def main(argv):
    if "-h" in argv[1:] or "--help" in argv[1:]:
        print(__doc__.strip())
        return 0
    try:
        opts = parse(argv[1:])
    except ValueError as exc:
        return usage_error(str(exc))
    action = opts["action"]
    base = {"ok": False, "action": "status", "from": None, "to": None, "changed": None, "syncPolicy": policy(),
            "warnings": []}
    if os.environ.get("ABLY_SPEC_SYNC", "").strip() and os.environ["ABLY_SPEC_SYNC"].strip().lower() not in POLICIES:
        base["warnings"].append(f"ABLY_SPEC_SYNC={os.environ['ABLY_SPEC_SYNC']} isn't ask, auto or off: read as ask")
    if action == "bootstrap":
        loc = {"warnings": []}
        try:
            env, _ = env_clone(loc["warnings"])
        except ValueError as exc:
            return emit({**base, "code": "SPEC_CLONE_ENV_CONFLICT", "message": str(exc)})
        target = expand(opts["path"] or env or default_path())
        base.update(bootstrapPath=str(target), partialLeftovers=leftovers(target))
        base["warnings"] += loc["warnings"]
        ok, code, message = bootstrap(target, opts["timeout"] or 600)
        if not ok:
            return emit({**base, "action": "not-updated", "code": code, "message": message})
        base["action"] = "cloned"
        if target != shared_target() or own_clone() is not None:
            opts["spec"] = str(target)
    loc = locate(opts["spec"], opts["require"])
    base["warnings"] += loc.pop("warnings", [])
    result = {**base, **loc}
    if "specClone" not in loc:
        return emit(result)
    clone = loc["specClone"]
    try:
        if action in ("fetch", "update"):
            if not loc.get("syncEligible"):
                result.update(action="not-updated", code="NOT_SYNCED_NAMED_CLONE",
                              message=f"not synced: {loc['notSyncedWarning']} No network is used.")
            elif base["syncPolicy"] == "off":
                result.update(action="not-updated", code="SYNC_OFF",
                              message="not updated: ABLY_SPEC_SYNC=off, so no network is used")
            else:
                act, code, message, old, new = sync(clone, action, opts["timeout"] or 120)
                result.update(action=act, code=code, message=message, **{"from": old, "to": new})
                if old and new and old != new:
                    result["changed"] = changed(clone, old, new)
                    again = locate(opts["spec"] or clone, opts["require"])  # keep the original kind and foundBy
                    loc.update(ok=again["ok"], missing=again.get("missing", []))
                    result.update(ok=loc["ok"], missing=loc["missing"])
        result.update(status(clone))
        if action == "bootstrap":
            result.update(code="CLONED" if loc["ok"] else loc["code"], message=f"cloned {URL} to {clone}")
        if not result["ok"]:
            result["code"] = "SPEC_CLONE_INCOMPLETE"
            result["message"] = (result.get("message", "") + ". " if action != "status" else "") + \
                incomplete_message(loc, result, clone)
        elif action == "status":
            result.update(code="STATUS", message="status only; no network used")
    except GitError as exc:
        result.update(ok=False, code="GIT_ERROR", message=str(exc))
    return emit(result)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except Exception as exc:  # never crash: report as JSON
        print(json.dumps({"ok": False, "code": "INTERNAL_ERROR", "message": f"{type(exc).__name__}: {exc}"}, indent=2))
        sys.exit(1)
