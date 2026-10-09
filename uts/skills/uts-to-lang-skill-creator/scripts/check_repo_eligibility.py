#!/usr/bin/env python3
"""Check that a repository is an Ably Pub/Sub SDK repository (Orient, STOP-16).

Usage: check_repo_eligibility.py <repo> [--spec-clone PATH]

The skill creator supports only Ably Pub/Sub SDK repositories. The rules' data
lives in assets/eligibility.json (update that file, not this script): the
GitHub owner (`ably`), the name pattern ^ably-(pubsub-[a-z0-9]+|[a-z0-9]+)$
(case-insensitive, without `.git`), the deny-list of known non-SDK names, the
allow-list with capability overrides, the canonical and planned-rename tables,
and the definition gate's threshold.

Ably is renaming its SDK repositories from ably-<lang> to ably-pubsub-<lang>
(ably-js is now ably-pubsub-js, ably-java ably-pubsub-java); both names are the
same repository, local clones often keep the old remote URL (GitHub redirects
it), and both are accepted. `nameForm` says which form the remote uses:
"legacy" (ably-<lang>), "pubsub" (ably-pubsub-<lang>) or "allow-list".
`canonical` reports the current name of a renamed repository, and
`plannedRename` a rename in preparation (either name is accepted). A legacy
name whose current name fails the pattern is rejected (ably-nativescript is now
ably-js-nativescript, a wrapper).

Every remote is checked, not only `origin`, so a fork with an `upstream` remote
pointing at ably/<name> is accepted. Decision, first match wins:
  0. not a git repo, or no remote                       -> ask    (NOT_GIT_REPO, NO_REMOTE)
  1. a github.com/ably/<eligible name> remote           -> accept (then the definition gate below)
  2. another github.com/ably/<name> remote              -> reject (NOT_PUBSUB_SDK_NAME, DENIED_NON_SDK)
  3. a github.com/<other owner>/<eligible name> remote  -> ask    (FORK_CONFIRM)
  4. another GitHub remote                              -> reject (NOT_ABLY_REPO)
  5. only non-GitHub remotes                            -> ask    (NON_GITHUB_REMOTE)
After an accept, the definition gate: a REST or Realtime client entry point must
be *defined* in non-test source (detect_capabilities.py's scan: a declared
client type or Go type alias, or a door entry point on a device or server
side), not merely used, as a load tool or a server that imports the SDK does:
functions returning a client, `const`/`let`/`var`/`val` bindings and code under
example(s)/sample(s)/demo(s) directories don't count. With no definition the decision becomes
reject (NO_CLIENT_DEFINITION) when there are at least the data file's
minSourceFilesToReject non-test source files, else ask (NO_SDK_FINGERPRINT:
wrong path or sparse checkout?). An allow-listed repo's capabilityOverride
satisfies the gate.

A reject is a hard stop with the exact `message`; there is no override.
Eligibility isn't scope: an allow-listed repo's `capabilityOverride` (ably-ruby-
rest: rest full, realtime absent) is passed by orient.py to
detect_capabilities.py, which reports it as the profile's source.

Prints exactly one JSON object. Read-only; never touches the network (`git
ls-remote --get-url` and `ssh -G` only read local configuration). Credentials
in remote URLs are redacted. A malformed data file is a structured error
(DATA_FILE_ERROR) naming the file and the key.
"""
import collections, importlib.util, json, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE.parent / "assets" / "eligibility.json"
REMOTE = re.compile(r"^(?:(?:https?|git|ssh)://(?:[^@/]+@)?(?P<h1>[^/:]+)(?::\d+)?/|(?:[^@/]+@)?(?P<h2>[^/:]+):)"
                    r"(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/*$", re.I)  # schemes in any case (HTTPS://)
GITHUB = {"github.com", "www.github.com"}


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dc = _load("detect_capabilities")
sn, lo = dc.sn, dc.lo
LEVEL = sn.STR
SHAPE = {"owner": sn.STR, "namePattern": sn.STR, "deny": {"names": [sn.STR]},
          "allow": {"*": {"capabilityOverride": {"*": LEVEL}}}, "canonical": {"*": sn.STR},
          "plannedRename": {"*": sn.STR}, "definitionGate": {"minSourceFilesToReject": sn.INT}}


class Rules:
    """assets/eligibility.json, validated."""

    def __init__(self):
        d = sn.load_json(DATA, SHAPE)
        try:
            self.name = re.compile(d["namePattern"], re.I)
        except re.error as exc:
            raise sn.DataFileError(f"{DATA.name}: key 'namePattern': not a valid regular expression: {exc}") from None
        for repo, entry in d["allow"].items():
            for cap, level in entry["capabilityOverride"].items():
                where = f"{DATA.name}: key 'allow.{repo}.capabilityOverride.{cap}'"
                if cap not in dc.LEVELS:
                    raise sn.DataFileError(f"{where}: expected the capability rest or realtime, got {cap}")
                if level not in dc.LEVELS[cap]:
                    raise sn.DataFileError(f"{where}: expected a {cap} level ({', '.join(dc.LEVELS[cap])}), got {level}")
        self.owner = d["owner"].lower()
        self.deny = {n.lower() for n in d["deny"]["names"]}
        self.allow = {k.lower(): v["capabilityOverride"] for k, v in d["allow"].items()}
        self.canonical = {k.lower(): v for k, v in d["canonical"].items()}
        self.planned = {k.lower(): v for k, v in d["plannedRename"].items()}
        self.min_files = d["definitionGate"]["minSourceFilesToReject"]


def message(owner, repo):
    return ("uts-to-lang-skill-creator currently supports only Ably Pub/Sub SDK repositories (ably-pubsub-<lang> or "
            f"ably-<lang>). No workflow exists yet for {owner}/{repo}; the skill creator needs to be upgraded to "
            "support it.")


def git(repo, *args):
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else None


def redact(url):
    return re.sub(r"^([a-z+]+://)[^@/]+@", r"\1***@", url, flags=re.I)


def resolve_host(host):
    """Resolve an SSH host alias (git@github-work:owner/repo) through ssh config; no network."""
    if host.lower() in GITHUB or "." in host:
        return host.lower()
    try:
        out = subprocess.run(["ssh", "-G", host], capture_output=True, text=True, timeout=5)
        m = re.search(r"(?m)^hostname\s+(\S+)", out.stdout)
        return m.group(1).lower() if m else host.lower()
    except (OSError, subprocess.SubprocessError):
        return host.lower()


def name_status(repo, rules):
    """(name eligible, denied, reason)."""
    if repo.lower() in rules.allow:
        return True, False, f"{repo} is on the allow-list"
    canon = rules.canonical.get(repo.lower())
    if canon and not rules.name.match(canon):
        return False, False, f"{repo} is now {canon}, which isn't a Pub/Sub SDK name"
    m = rules.name.match(repo)
    if not m:
        return False, False, "the name doesn't match ably-pubsub-<lang> or ably-<lang>"
    tail = m.group(1).lower()
    if tail in rules.deny:
        return False, True, f"ably-{tail} is a known non-SDK repository"
    return True, False, "the name matches"


def fingerprint(top, spec_clone=None):
    """The definition gate (section 13.2): a REST or Realtime client entry point *defined* in non-test source.

    Uses detect_capabilities.py's scan (and detect_liveobjects.py's file tables). Only declared client types count
    (a class, struct, interface or protocol of a client name, or a Go type alias), plus door entry points on a device
    or server side. Not a function returning a client (`createClient(): Realtime`, Go `NewClient() (*ably.Realtime,
    error)`), not a binding (`const Realtime = require('ably').Realtime`), and nothing under an example(s), sample(s)
    or demo(s) directory: code that only *uses* the SDK (a load tool, a server, an app) isn't accepted. Also reports
    source counts, build manifests and a test root, for context.
    """
    files, _, _ = dc.list_files(top, False)
    counts, build, test_root = collections.Counter(), [], False
    for f in files:
        parts = f.split("/")
        ext = pathlib.PurePosixPath(f).suffix
        test = lo.is_test(f)
        test_root = test_root or test
        if len(parts) <= 2 and (parts[-1] in lo.MANIFEST_NAMES or ext in lo.MANIFEST_EXT):
            build.append(f)
        if ext in lo.SOURCE_EXT and not test:
            counts[ext] += 1
    loaded = sn.load(spec_clone)
    clients = dc.scan(top, False, dc.Names(loaded))["clients"]
    defined = {cap: sorted(c["gateTypes"])[:3] for cap, c in clients.items()}
    return any(defined.values()), sum(counts.values()), loaded, {
        "sourceFiles": dict(counts.most_common(5)), "buildFiles": sorted(build, key=len)[:5], "testRoot": test_root,
        "clientDefinitions": defined}


def main(argv):
    args, opts = [], {}
    it = iter(argv[1:])
    for a in it:
        if a == "--spec-clone":
            opts[a] = next(it, None)
        else:
            args.append(a)
    if len(args) != 1 or not pathlib.Path(args[0]).is_dir() or None in opts.values():
        print("usage: check_repo_eligibility.py <repo> [--spec-clone PATH]", file=sys.stderr)
        return 2
    path = pathlib.Path(args[0]).expanduser().resolve()
    result = {"ok": True, "path": str(path), "warnings": []}
    try:
        rules = Rules()
        result["dataFile"] = str(DATA)
        top = git(path, "rev-parse", "--show-toplevel")
        if top is None:
            result.update(decision="ask", eligible=None, code="NOT_GIT_REPO", owner=None, repo=None, remote=None,
                          nameForm=None, canonical=None, plannedRename=None, remotes=[],
                          reason="not a git repository: ask the user for the SDK repo path")
            print(json.dumps(result, indent=2))
            return 0
        top = pathlib.Path(top.strip())
        if top != path:
            result["warnings"].append(f"{path} is inside {top}; checked the repository root")
        result["toplevel"] = str(top)
        remotes = []
        for name in (git(top, "remote") or "").split():
            url = (git(top, "ls-remote", "--get-url", name) or "").strip()
            m = REMOTE.match(url)
            r = {"name": name, "url": redact(url)}
            if m:
                host = resolve_host(m.group("h1") or m.group("h2"))
                ok, denied, why = name_status(m.group("repo"), rules)
                r.update(host=host, owner=m.group("owner"), repo=m.group("repo"), github=host in GITHUB,
                          nameEligible=ok, denied=denied, nameReason=why)
            remotes.append(r)
        result["remotes"] = remotes
        gh = [r for r in remotes if r.get("github")]
        ably = [r for r in gh if r["owner"].lower() == rules.owner]
        good = [r for r in ably if r["nameEligible"]]
        forks = [r for r in gh if r["owner"].lower() != rules.owner and r["nameEligible"]]
        if not remotes:
            pick, decision, code, reason = None, "ask", "NO_REMOTE", "no remote: ask which Ably repository this is"
        elif good:
            pick, decision, code = good[0], "accept", "ELIGIBLE"
            reason = f"remote {pick['name']} is github.com/{pick['owner']}/{pick['repo']}"
            if len(ably) > 1:
                result["warnings"].append(f"several {rules.owner} remotes: " + ", ".join(r["repo"] for r in ably))
        elif ably:
            pick, decision = ably[0], "reject"
            code = "DENIED_NON_SDK" if pick["denied"] else "NOT_PUBSUB_SDK_NAME"
            reason = f"github.com/{pick['owner']}/{pick['repo']}: {pick['nameReason']}"
        elif forks:
            pick, decision, code = forks[0], "ask", "FORK_CONFIRM"
            reason = (f"only a fork matches (github.com/{pick['owner']}/{pick['repo']}): ask the user to confirm it is "
                      f"a fork of {rules.owner}/{pick['repo']}")
        elif gh:
            pick, decision, code = gh[0], "reject", "NOT_ABLY_REPO"
            reason = (f"github.com/{pick['owner']}/{pick['repo']} isn't an {rules.owner} repository (if this is a fork, "
                      f"add an upstream remote for the {rules.owner} repository and run again)")
        else:
            pick, decision, code = None, "ask", "NON_GITHUB_REMOTE"
            reason = f"no GitHub remote: ask the user for the github.com/{rules.owner} repository this tracks"
        key = pick["repo"].lower() if pick else None
        override = rules.allow.get(key) if decision != "reject" else None
        if decision == "accept":
            defined, n_source, loaded, fp = fingerprint(top, opts.get("--spec-clone"))
            result["fingerprint"] = fp
            result["warnings"] += loaded["warnings"]
            if defined:
                fp["gate"] = "client definition found"
            elif override:
                fp["gate"] = "satisfied by the allow-list capabilityOverride (no client defined in this tree)"
            elif n_source >= rules.min_files:
                decision, code = "reject", "NO_CLIENT_DEFINITION"
                fp["gate"] = "failed"
                reason += (f"; but no REST or Realtime client is defined in {n_source} non-test source files (code "
                            "that only uses an Ably client, such as a tool or server, isn't an SDK)")
            else:
                decision, code = "ask", "NO_SDK_FINGERPRINT"
                fp["gate"] = "not met (few source files)"
                reason += (f"; but no REST or Realtime client definition in {n_source} non-test source file(s): wrong "
                            "path or sparse checkout? Ask the user")
        if decision == "reject":
            result["message"] = message(pick["owner"], pick["repo"])
            override = None
        if override:
            result["capabilityOverride"] = override
        result.update(decision=decision, eligible={"accept": True, "reject": False}.get(decision), code=code,
                      reason=reason, owner=pick["owner"] if pick else None, repo=pick["repo"] if pick else None,
                      remote={"name": pick["name"], "url": pick["url"], "host": pick.get("host")} if pick else None,
                      nameForm=(None if not pick else "allow-list" if key in rules.allow else
                                ("pubsub" if key.startswith("ably-pubsub-") else "legacy") if rules.name.match(key)
                                else None),
                      canonical=rules.canonical.get(key) if key else None,
                      plannedRename=rules.planned.get(key) if key else None)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:  # never crash: report a structured error
        print(json.dumps({"ok": False, "code": sn.error_code(exc, "ELIGIBILITY_ERROR"),
                          "message": f"{type(exc).__name__}: {exc}"}))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
