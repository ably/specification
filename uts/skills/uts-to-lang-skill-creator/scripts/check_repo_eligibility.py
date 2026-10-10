#!/usr/bin/env python3
"""Check that a repository is on the skill creator's whitelist of Ably Pub/Sub SDK repositories (Orient, STOP-16).

Usage: check_repo_eligibility.py <repo> [--spec-clone PATH]

A repository is eligible only if a remote is github.com/<owner>/<name> with
<name> in assets/eligibility.json's `repositories` (case-insensitive, without
`.git` or a trailing `/`), and the checkout defines a REST or Realtime client
(the definition gate). Every other repository is rejected. Decision rules and
codes: references/orient.md 13.2.

Prints one JSON object: `ok`, `decision` (accept, reject or ask), `eligible`,
`code`, `reason`, `message` (on a reject), `owner`, `repo`, `remote`,
`nameForm`, `canonical`, `plannedRename`, `capabilityOverride`, `fingerprint`,
`remotes` and `warnings`. Read-only; no network. A malformed data file gives
DATA_FILE_ERROR naming the file and the key. Exit 0 when it decides; 1 with
{"ok": false} on an error; 2 on a usage error.
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
SHAPE = {"owner": sn.STR, "repositories": [sn.STR], "capabilityOverride": {"*": {"*": LEVEL}},
          "canonical": {"*": sn.STR}, "plannedRename": {"*": sn.STR}, "definitionGate": {"minSourceFilesToReject": sn.INT}}


def normalise(name):
    """A repository name as the whitelist compares it: lower case, without a trailing `/` or `.git`."""
    name = name.strip().rstrip("/").lower()
    return name[:-len(".git")] if name.endswith(".git") else name


class Rules:
    """assets/eligibility.json, validated: every name it mentions must be on the whitelist."""

    def __init__(self):
        d = sn.load_json(DATA, SHAPE)
        where = DATA.name
        self.owner = d["owner"].lower()
        self.repos = {normalise(n) for n in d["repositories"]}
        for key in ("capabilityOverride", "canonical", "plannedRename"):
            for name, value in d[key].items():
                names = [name] + ([value] if isinstance(value, str) else [])
                for n in names:
                    if normalise(n) not in self.repos:
                        raise sn.DataFileError(f"{where}: key '{key}.{name}': {n} isn't in 'repositories'")
        for repo, entry in d["capabilityOverride"].items():
            for cap, level in entry.items():
                at = f"{where}: key 'capabilityOverride.{repo}.{cap}'"
                if cap not in dc.LEVELS:
                    raise sn.DataFileError(f"{at}: expected the capability rest or realtime, got {cap}")
                if level not in dc.LEVELS[cap]:
                    raise sn.DataFileError(f"{at}: expected a {cap} level ({', '.join(dc.LEVELS[cap])}), got {level}")
        self.override = {normalise(k): v for k, v in d["capabilityOverride"].items()}
        self.canonical = {normalise(k): v for k, v in d["canonical"].items()}
        self.planned = {normalise(k): v for k, v in d["plannedRename"].items()}
        self.planned_targets = {normalise(v) for v in d["plannedRename"].values()}
        self.min_files = d["definitionGate"]["minSourceFilesToReject"]

    def listed(self, repo):
        return normalise(repo) in self.repos

    def name_form(self, repo):
        key = normalise(repo)
        return "legacy" if key in self.canonical else "planned" if key in self.planned_targets else "current"


def message(owner, repo):
    return ("uts-to-lang-skill-creator supports only the Ably Pub/Sub SDK repositories listed in assets/eligibility.json. "
            f"{owner}/{repo} isn't one of them; supporting it requires updating the skill creator.")


def gate_message(owner, repo):
    return (f"{owner}/{repo} is on the whitelist in assets/eligibility.json, but this checkout defines no REST or "
            "Realtime client, so it can't be an SDK working tree. Check the path and the branch.")


def git(repo, *args):
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    return out.stdout if out.returncode == 0 else None


def redact(url):
    return re.sub(r"^([a-z+]+://)[^@/]+@", r"\1***@", url, flags=re.I)


def resolve_host(host):
    """Resolve an SSH host alias (git@github-work:owner/repo) through ssh config; no network."""
    if host.lower() in GITHUB or "." in host:
        return host.lower()
    try:
        # `ssh -G` only prints the resolved config and never connects, but it does evaluate any `Match exec` blocks
        # in the user's ssh config.
        out = subprocess.run(["ssh", "-G", host], capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=5)
        m = re.search(r"(?m)^hostname\s+(\S+)", out.stdout)
        return m.group(1).lower() if m else host.lower()
    except (OSError, subprocess.SubprocessError):
        return host.lower()


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


USAGE = "usage: check_repo_eligibility.py <repo> [--spec-clone PATH]"


def usage_error(message):
    print(f"{USAGE}\ncheck_repo_eligibility.py: error: {message}", file=sys.stderr)
    return 2


def main(argv):
    if "-h" in argv[1:] or "--help" in argv[1:]:
        print(__doc__.strip())
        return 0
    args, opts = [], {}
    it = iter(argv[1:])
    for a in it:
        if a == "--spec-clone":
            opts[a] = next(it, "")
            if not opts[a] or opts[a].startswith("-"):
                return usage_error(f"{a} needs a value")
        elif a.startswith("-"):
            return usage_error(f"unknown option {a}")
        else:
            args.append(a)
    if len(args) != 1:
        return usage_error(f"expected one <repo>, got {len(args)} arguments")
    path = pathlib.Path(args[0]).expanduser()
    if not path.is_dir():
        return usage_error(f"not a directory: {args[0]}")
    path = path.resolve()
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
                r.update(host=host, owner=m.group("owner"), repo=m.group("repo"), github=host in GITHUB,
                          whitelisted=rules.listed(m.group("repo")))
            remotes.append(r)
        result["remotes"] = remotes
        gh = [r for r in remotes if r.get("github")]
        ably = [r for r in gh if r["owner"].lower() == rules.owner]
        good = [r for r in ably if r["whitelisted"]]
        forks = [r for r in gh if r["owner"].lower() != rules.owner and r["whitelisted"]]
        if not remotes:
            pick, decision, code, reason = None, "ask", "NO_REMOTE", "no remote: ask which Ably repository this is"
        elif good:
            pick, decision, code = good[0], "accept", "ELIGIBLE"
            reason = f"remote {pick['name']} is github.com/{pick['owner']}/{pick['repo']}"
            if len(ably) > 1:
                result["warnings"].append(f"several {rules.owner} remotes: " + ", ".join(r["repo"] for r in ably))
        elif ably:
            pick, decision = ably[0], "reject"
            code = "NOT_WHITELISTED"
            reason = f"github.com/{pick['owner']}/{pick['repo']} isn't on the whitelist in {DATA.name}"
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
        key = normalise(pick["repo"]) if pick else None
        override = rules.override.get(key) if decision != "reject" else None
        if decision == "accept":
            defined, n_source, loaded, fp = fingerprint(top, opts.get("--spec-clone"))
            result["fingerprint"] = fp
            result["warnings"] += loaded["warnings"]
            if defined:
                fp["gate"] = "client definition found"
            elif override:
                fp["gate"] = "satisfied by the whitelist capabilityOverride (no client defined in this tree)"
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
            result["message"] = (gate_message if code == "NO_CLIENT_DEFINITION" else message)(pick["owner"], pick["repo"])
            override = None
        if override:
            result["capabilityOverride"] = override
        result.update(decision=decision, eligible={"accept": True, "reject": False}.get(decision), code=code,
                      reason=reason, owner=pick["owner"] if pick else None, repo=pick["repo"] if pick else None,
                      remote={"name": pick["name"], "url": pick["url"], "host": pick.get("host")} if pick else None,
                      nameForm=rules.name_form(key) if pick and rules.listed(key) else None,
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
