#!/usr/bin/env python3
"""Step 0 of the skill: orient. Classify the target repository and recommend a mode.

Usage: orient.py <repo> [--spec-clone PATH] [--skill-dir PATH] [--records PATH]
                  [--capability-override rest=LEVEL,realtime=LEVEL] [--side core|server|device|both]
                  [--include-submodules] [--full]

Runs five of this skill's read-only scripts by subprocess, in order:
spec_clone_info.py (which resolves the spec clone the others read),
check_repo_eligibility.py (on a reject nothing else runs),
inspect_existing_skill.py, detect_liveobjects.py and detect_capabilities.py.
It then classifies the repo state (INELIGIBLE, S4, S2, S3, S1, S0, first match
wins, with re-entry as an overlay) and compares the current capability profile
with the recorded one.

Runs the eligibility check even when no spec clone is found, so STOP-16 is
settled before any offer to clone one. Never syncs the clone: `specSync` says
what Step 0's sync (ensure_spec_clone.py, after STOP-16) should offer; only the
shared clone is synced, and any other clone gets a static warning.

It also derives the UTS infrastructure plan outline for STOP-17 (`infraPlan`):
per tier the harness pieces with their gap-table rows, the smoke tests and
self-tests, what's left out, and how the harness creates clients (the side).
`--capability-override` (the user's correction, with evidence; it wins over a
whitelist override) and `--side` (the user's answer to the side question) rerun
Orient with a decision made at STOP-17; record both in D-31.

Prints one JSON object: `ok`, `repo`, `eligibility`, `warnings`, `state`
(class, re-entry, reasons, recommended option, options),
`stateSummaryMarkdown` (the State summary shown before the questions: warnings
as bold lines, then a table), `stateSummaryText` (the same as fixed-width text,
for the Repo profile), `specCloneWarning`, `stop1`, `stop16`, `stop17` (why
STOP-17 may be asked, or null), `infraPlan`, `questions` (STOP-13 and STOP-17
as questions: `now` for the first message, `followUp` for those asked only
after the STOP-13 answer picks one of their `askIf` options),
`questionsMarkdown` (their Markdown form), `askUserQuestion` (the Claude Code
tool form, or null where it doesn't fit), `followUpByOption` (per STOP-13
option, the follow-up message in both forms),
`specSync`, `capabilityDelta` and the facts behind them. `--full` adds `raw`: the outputs
of spec_clone_info, inspect_existing_skill and the two detectors (the
eligibility output is always under `eligibility`). Exit 0 whenever it
classifies; 1 with {"ok": false} on NOT_A_SPEC_CLONE, DATA_FILE_ERROR or
ORIENT_ERROR; 2 on a usage error. Read-only; never touches the network.

Rules: references/orient.md 13.1 (what runs), 13.3 (state classes), 13.4 (the
State summary), 13.6 (re-entry), 13.8 (capability delta, the UTS infrastructure
plan and STOP-17), 13.9 (the spec-clone sync); references/asking.md (the
question blocks).
"""
import json, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
TIMEOUT = 300
GROUPS = {
    "guide": ["uts/docs/writing-uts-spec-translator-skills.md", "uts/skills/uts-to-lang-skill-creator"],
    "utsDocs": ["uts/README.md", "uts/docs/writing-derived-tests.md", "uts/docs/writing-test-specs.md",
                "uts/docs/integration-testing.md", "uts/docs/proxy.md"],
    "helperSpecs": ["uts/rest/unit/helpers", "uts/realtime/unit/helpers", "uts/objects/helpers"],
    "corpus": ["uts/rest", "uts/realtime", "uts/objects"],
}


def run(script, *args):
    """Run one of this skill's scripts; return (parsed JSON or None, warning or None)."""
    try:
        out = subprocess.run([sys.executable, str(HERE / script), *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, f"{script} timed out after {TIMEOUT} s"
    except OSError as exc:
        return None, f"{script} failed: {type(exc).__name__}: {exc}"
    try:
        return json.loads(out.stdout), None
    except ValueError as exc:  # no JSON: a usage error or a traceback; show the exit code and the end of stderr
        tail = out.stderr.strip()[-500:]
        return None, (f"{script} failed (exit {out.returncode}): no JSON output ({type(exc).__name__}: {exc})"
                      + (f"; stderr: {tail}" if tail else ""))


def data_file_error(*outs):
    """A broken data file in assets/ (DATA_FILE_ERROR from any script) stops Orient: nothing it says can be trusted."""
    bad = [o for o in outs if o and o.get("code") == "DATA_FILE_ERROR"]
    if not bad:
        return None
    print(json.dumps({"ok": False, "code": "DATA_FILE_ERROR", "message": bad[0].get("message"),
                      "fix": "repair the named data file in assets/ (or restore it from the spec clone), then run again"},
                      indent=2))
    return 1


def git(repo, *args):
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    return out.stdout if out.returncode == 0 else None


def changes_since(spec_clone, spec_sha, repo, repo_sha):
    if not spec_clone or not spec_sha or git(spec_clone, "cat-file", "-e", spec_sha + "^{commit}") is None:
        return {"anchorSpec": spec_sha, "anchorPresent": False}
    res = {"anchorSpec": spec_sha, "anchorPresent": True}
    helpers = set()
    for name, paths in GROUPS.items():
        files = [f for f in (git(spec_clone, "diff", "--name-only", spec_sha, "--", *paths) or "").splitlines() if f]
        if name == "helperSpecs":
            helpers = set(files)
        if name == "corpus":
            files = [f for f in files if f not in helpers]
        res[name] = len(files)
    guide_diff = git(spec_clone, "diff", spec_sha, "--", GROUPS["guide"][0]) or ""
    res["checklistChanged"] = any(l.startswith(("+- [ ]", "-- [ ]")) for l in guide_diff.splitlines())
    if repo_sha and git(repo, "cat-file", "-e", repo_sha + "^{commit}") is not None:
        res["repo"] = len([f for f in (git(repo, "diff", "--name-only", repo_sha) or "").splitlines() if f])
    return res


def skill_view(s, repo):
    fm = s.get("frontmatter", {})
    rec = dict(s["records"]) if s.get("records") else None
    if rec:
        try:
            rec["dir"] = str(pathlib.Path(rec["dir"]).resolve().relative_to(repo))
        except ValueError:
            pass
    harness = s.get("harness") or {}
    smoke = harness.get("smokeOrSelfTestFiles")
    # Offered tiers: a target path, and neither the module (a module-level `unready`, e.g. objects out of scope;
    # `unsupported` without `extraTests`) nor that tier marked not ready (guide 3.2).
    tiers = sorted({t for m in s.get("mapping", {}).get("modules", {}).values()
                    if not isinstance(m.get("unready"), str) and not (m.get("unsupported") and not m.get("extraTests"))
                    for t in m if t in ("unit", "integration", "proxy") and isinstance(m[t], str)
                    and not (isinstance(m.get("unready"), dict) and t in m["unready"])})
    return {
        "dir": s["installs"][0]["path"], "installs": [i["path"] + (" (symlink)" if i["symlink"] else "")
                                                      for i in s["installs"]],
        "name": fm.get("name") or None, "version": str((fm.get("metadata") or {}).get("version") or "").strip("\"'") or None,
        "language": s.get("language"), "languageMatchesRepo": s.get("languageMatchesRepo"),
        "origin": s.get("origin"), "generatedBy": s.get("generatedBy"), "records": rec,
        "capabilityProfile": s.get("capabilityProfile"),
        "checks": s.get("summary", {}), "mappedModules": sorted(s.get("mapping", {}).get("modules", {})),
        "objectsNotes": ("placeholder" if (s.get("mapping", {}).get("notes", {}).get("objects") or {}).get("placeholder")
                          else "present" if s.get("mapping", {}).get("notes", {}).get("objects") else "none"),
        "mappingShape": harness.get("shape"),  # "older": an older mapping entry, read with the inspector's warning
        "harness": ("from mapping" if harness.get("readme") or harness.get("root") else
                    ("candidates: " + ", ".join(r["path"] for r in harness.get("readmes", [])) if harness.get("readmes")
                      else "none found")),
        "smokeOrSelfTestFiles": len(smoke) if isinstance(smoke, list) else None,
        "selfTestCandidates": len(harness.get("selfTestCandidates") or []),
        "tiersLackingSmoke": tiers_lacking_smoke(tiers, smoke),
        "named": bool(s.get("named")),
    }


def tiers_lacking_smoke(tiers, smoke):
    """Offered tiers with no smoke/self-test file, by the tier named in each file's path; "unknown" when some files
    don't name a tier (they might cover the rest)."""
    if not isinstance(smoke, list):
        return []
    covered, unmapped = set(), 0
    for f in smoke:
        words = set(re.split(r"[/_.\-]+", f.lower())) | set(re.findall(r"unit|integration|proxy", f.lower()))
        hit = words & {"unit", "integration", "proxy"}
        covered |= hit
        unmapped += not hit
    lacking = [t for t in tiers if t not in covered]
    return "unknown" if lacking and unmapped else lacking


RANK = {"absent": 0, "unclear": 1, "partial": 2, "full": 3}
DOOR_SIDES = ("server", "device")


def capability_delta(recorded, caps):
    """Differences between the recorded profile (D-31, completed by the mapping) and the current one.

    Returns (delta {item: "old -> new"}, added [capabilities or modules now available], lowered [...]).
    The levels are always compared (D-31 records the whole repository's levels). The scope kind and the
    unsupported modules depend on the chosen side, so they are compared only when no side was recorded and the
    repo has no doors now; for levels inferred from a mapping (no D-31 line), only the kind and modules are.
    """
    delta, added, lowered = {}, [], []
    if not recorded or not caps:
        return delta, added, lowered
    sc = caps.get("scopeSuggestion", {})
    inferred = recorded.get("levelsInferred")
    for k in ("rest", "realtime"):
        old, new = recorded.get(k), caps["capabilities"][k]["level"]
        if old and old != new and old in RANK and new in RANK:
            delta[k] = f"{old} -> {new}" + (" (recorded level inferred from the mapping)" if inferred else "")
            (added if RANK[new] > RANK[old] else lowered).append(k)
    side, doors = recorded.get("side"), sorted(caps.get("sides") or {})
    door_now = [d for d in doors if d in DOOR_SIDES]
    if side and not door_now:
        delta["side"] = f"{side} -> no doors"
    elif not side and door_now:
        delta["side"] = "none recorded -> doors: " + ", ".join(door_now) + " (ask the side question)"
    elif side and side not in ("core", "both") and side not in doors:
        delta["side"] = f"{side} -> not among the current sides: " + ", ".join(doors)
    if not side and not door_now:
        kind, old_kind = sc.get("kind"), recorded.get("scopeKind")
        if old_kind and kind and old_kind != kind and kind not in ("unclear", "none"):
            delta["scope"] = f"{old_kind} -> {kind}"
        old_un = set(recorded.get("unsupported") or []) | set(((recorded.get("mapping") or {}).get("unsupported")
                                                              or {}).keys())
        now_un = set(sc.get("unsupported") or {})
        freed = sorted(m for m in old_un - now_un if m in sc.get("modules", []) or
                        (m == "objects" and "realtime" in sc.get("modules", [])))
        if freed:  # objects isn't a capability: it follows realtime, and STOP-14 decides it
            delta["unsupported"] = f"{', '.join(sorted(old_un))} -> {', '.join(sorted(now_un)) or 'none'}"
            added += [m for m in freed if m not in added and m != "objects"]
        newly = sorted(now_un - old_un)
        if newly and old_un | set(recorded.get("scopeModules") or []):
            delta.setdefault("unsupported", f"{', '.join(sorted(old_un)) or 'none'} -> {', '.join(sorted(now_un))}")
            lowered += [m for m in newly if m not in lowered]
    return delta, added, lowered


def stop17_reasons(caps, delta, added, lowered):
    """Why the capability profile needs confirming at STOP-17 (13.8); empty when the user confirms it with STOP-13.
    The side question is separate (infra_plan)."""
    if not caps:
        return []
    why = []
    sc, c = caps.get("scopeSuggestion", {}), caps["capabilities"]
    rest, rt = c["rest"]["level"], c["realtime"]["level"]
    if rest != "full" or rt != "full":
        why.append(f"profile not full: rest {rest}, realtime {rt}")
    if sc.get("kind") != "full":
        why.append(f"scope {sc.get('kind')}" + (": " + ", ".join(f"{m} unsupported ({r})" for m, r in
                                                                (sc.get("unsupported") or {}).items())
                                                if sc.get("unsupported") else ""))
    if rt == "unclear":
        why.append("realtime unclear: is the declared realtime client reachable (public elsewhere, or through the "
                    "sanctioned internal-access route)? never decide rest-only")
    if caps.get("source") and caps["source"] != "detected":
        why.append(f"capability profile from {caps['source']}: confirm")
    if caps.get("wrapsNativeSdk"):
        why.append("wraps native SDKs: hooks probably unreachable from the SDK language: unit tier only if hooks "
                    "exist (P-13); integration and proxy still apply")
    if delta:
        why.append("changed since the recorded profile (D-31, or the mapping): "
                    + ", ".join(f"{k} {v}" for k, v in delta.items())
                    + (f"; capability added: {', '.join(added)} (Upgrade/Fix, diff-driven change item, section 10)"
                      if added else "")
                    + (f"; lower than recorded: {', '.join(lowered)} (a detector miss, or really removed? evidence)"
                      if lowered else ""))
    if sc.get("confirmAtStop17") and not why:
        why.append("confirm the capability profile")
    for r in caps.get("reasons", []):
        if r not in why and not r.startswith(("wraps native SDKs", "realtime undecided", "capability override")):
            why.append(r)
    return why


def classify(elig, spec, insp, skills, named_only=False):
    """named_only: --skill-dir was given, so only that skill is classified; the other skills, broken installs and
    orphan records are listed under Problems instead of making the state S4."""
    reasons, stop1 = [], []
    if elig and elig.get("decision") == "reject":
        return {"class": "INELIGIBLE", "reentry": False, "reasons": [elig.get("message")], "recommended": None,
                "options": []}, stop1
    if not spec or not spec.get("ok"):
        code = (spec or {}).get("code", "unknown error")
        if code == "SPEC_CLONE_NOT_FOUND":
            stop1.append(f"spec clone not found: after STOP-16, offer to clone it to {spec.get('bootstrapPath')} "
                        "(with STOP-6, 13.9), or ask for the path of an existing clone"
                        + (f"; partial clone(s) left by an interrupted bootstrap, for the user to remove: "
                            f"{', '.join(spec['partialLeftovers'])}" if spec.get("partialLeftovers") else ""))
        elif code == "SPEC_CLONE_INCOMPLETE":
            stop1.append(f"spec clone too old for this skill: {spec.get('message')}")
        else:
            stop1.append(f"spec clone: {code}: ask for the clone's path")
    elif spec.get("skillMatchesClone") is False:
        stop1.append("the installed skill differs from the clone's copy: refresh the install or confirm")
    broken, orphans = insp.get("brokenInstalls", []), insp.get("orphanRecords", [])
    mismatch = [s for s in skills if s["languageMatchesRepo"] is False]
    finished_orphans = [o for o in orphans if o["runStatus"] == "finished"]
    if named_only:
        broken, finished_orphans = [], []
    reentry = any(s["records"] and s["records"]["runStatus"] == "in progress" for s in skills) or \
        any(o["runStatus"] == "in progress" for o in orphans)
    tags = insp.get("derivedTests", {}).get("tags", 0)
    hc = insp.get("harnessCandidates") or {}
    if len(skills) > 1 or broken or mismatch or finished_orphans:
        cls = "S4"
        if len(skills) > 1:
            reasons.append(f"{len(skills)} distinct uts-to-* skills: " + ", ".join(s["dir"] for s in skills))
        reasons += [f"{b['path']}: {b['problem']}" for b in broken]
        reasons += [f"{s['dir']}: a {s['language']} skill, but the repo has no {s['language']} files" for s in mismatch]
        reasons += [f"{o['dir']}: finished records with no skill" for o in finished_orphans]
        options = [f"Upgrade/Fix {s['dir']}" for s in skills] + ["Create a new skill",
                    "Repair the installs first (relink, reconcile copies; nothing deleted without asking)", "Stop"]
        recommended = None
    elif skills and skills[0]["origin"] == "creator-records":
        cls = "S2"
        reasons.append(f"{skills[0]['dir']} was made by this procedure (records in {skills[0]['records']['dir']}), "
                        + ("and its last run finished" if not reentry else "and a run is in progress"))
        options = ["Upgrade/Fix, diff-driven (section 10)", "Upgrade/Fix, full gap audit (section 11)",
                    "Regenerate from scratch (staged, 11.5)", "Stop"]
        recommended = options[0]
    elif skills:
        cls = "S3"
        origin = skills[0]["origin"]
        reasons.append(f"{skills[0]['dir']} has " + ("this procedure's provenance stamp but no records"
                                                      if origin == "creator-metadata" else
                                                      "no records or provenance from this procedure"))
        options = ["Upgrade/Fix, full gap audit (section 11)", "Regenerate from scratch (staged, 11.5)", "Stop"]
        recommended = options[0]
    elif tags or hc.get("readmes") or hc.get("candidateDirs") or hc.get("smokeOrSelfTestFiles"):
        cls = "S1"
        reasons.append(f"no uts-to-* skill, but {tags} UTS-tagged test(s) and "
                        + ("harness candidates" if hc.get("candidateDirs") else "no harness code"))
        options = ["Create, keeping and matching the existing tests and harness", "Stop"]
        recommended = options[0]
    else:
        cls = "S0"
        reasons.append("no uts-to-* skill, no harness code and no UTS-tagged tests")
        options = ["Create", "Stop"]
        recommended = options[0]
    if reentry:
        reasons.insert(0, "an earlier run of this procedure didn't finish (records in progress)")
        now = (spec or {}).get("sha") or ""
        recorded = [r["recordedSpecSha"] for r in [s["records"] for s in skills if s["records"]] + list(orphans)
                    if r["runStatus"] == "in progress" and r.get("recordedSpecSha")]
        if now and any(not now.startswith(r) for r in recorded):
            reasons.insert(1, "spec moved since the records: ask about restarting (13.6)")
        options = ["Resume from the phase the records show", "Restart (supersede the recorded decisions, keep files)"] \
            + options
        recommended = options[0]
    return {"class": cls, "reentry": reentry, "reasons": reasons, "recommended": recommended, "options": options}, stop1


def eligibility_line(elig):
    """The State summary's Eligibility line: accept with name form and names; ask with its code and reason."""
    if not elig:
        return "Eligibility  (not run)"
    if not elig.get("ok"):
        return f"Eligibility  ERROR {elig.get('code')}: {elig.get('message')}"
    names = ((f"; canonical {elig['canonical']}" if elig.get("canonical") else "")
              + (f"; planned rename {elig['plannedRename']}" if elig.get("plannedRename") else "")
              + (f"; capability override {', '.join(f'{k} {v}' for k, v in elig['capabilityOverride'].items())}"
                if isinstance(elig.get("capabilityOverride"), dict) else ""))
    if elig.get("decision") == "accept":
        return (f"Eligibility  accept: {elig.get('owner')}/{elig.get('repo')} via {(elig.get('remote') or {}).get('name')}"
                f" ({elig.get('nameForm')} name){names}")
    what = {"NO_REMOTE": "no remote", "NON_GITHUB_REMOTE": "no github.com remote", "NOT_GIT_REPO": "not a git repo",
            "FORK_CONFIRM": "a fork?", "NO_SDK_FINGERPRINT": "no client definition in few files"}.get(
        elig.get("code"), elig.get("code"))
    repo = f" {elig['owner']}/{elig['repo']}" if elig.get("owner") and elig.get("repo") else ""
    reason = elig.get("reason") or elig.get("code") or ""
    if reason.lower().startswith(what.lower() + ":"):
        reason = reason[len(what) + 1:].strip()
    return f"Eligibility  {elig.get('decision')}: {what}{repo} ({reason}){names}; STOP-16"


def clone_label(spec):
    """How the State summary names the clone's kind (13.4)."""
    shared = spec.get("isSharedClone")
    return {"shared": "shared clone", "env": f"shared clone ({spec.get('foundBy')})",
            "explicit": "named clone" + (", the shared clone" if shared else ""),
            "skill-clone": "skill clone" + (", the shared clone" if shared else " (not the shared clone)")}.get(
        spec.get("kind"), spec.get("kind") or "?")


def sync_plan(spec):
    """What Step 0's spec-clone sync offers after STOP-16 (13.9), from the offline status. Never runs it."""
    if not spec:
        return None
    script = "python3 <skill-dir>/scripts/ensure_spec_clone.py"
    if spec.get("code") == "SPEC_CLONE_NOT_FOUND" and spec.get("bootstrapPath"):
        path = spec["bootstrapPath"]
        return {"step": "bootstrap", "ask": "STOP-1 with STOP-6, after STOP-16", "bootstrapPath": path,
                "partialLeftovers": spec.get("partialLeftovers") or [],
                "command": f"{script} --bootstrap",
                "options": ["give the path of an existing clone",
                            f"clone ably/specification to {path} (network: about 30 MiB from github.com)", "stop"],
                "summary": "bootstrap offered after STOP-16"}
    if not spec.get("specClone") or spec.get("code") not in (None, "SPEC_CLONE_INCOMPLETE"):
        return {"step": "none", "summary": "none until the clone is settled at STOP-1"}
    if not spec.get("syncEligible"):  # only the shared clone is synced, however it was found
        return {"step": "none", "synced": False, "warning": spec.get("notSyncedWarning"),
                "summary": "not synced (not the shared clone)"}
    policy, blocked = spec.get("syncPolicy") or "ask", spec.get("fastForwardBlockedBy") or []
    arg = f" --spec-clone {spec['specClone']}" if spec.get("kind") == "explicit" else ""
    if policy == "off":
        return {"step": "none", "policy": "off", "summary": "not updated (ABLY_SPEC_SYNC=off)"}
    if "ORIGIN_NOT_ABLY_SPEC" in blocked:
        return {"step": "ask", "policy": policy, "blockedBy": blocked, "ask": "STOP-6, after STOP-16",
                "options": ["use it as it is", "stop"], "command": None,
                "summary": "origin isn't ably/specification: no fetch; ask"}
    if blocked:
        return {"step": "ask" if policy == "ask" else "none", "policy": policy, "blockedBy": blocked,
                "ask": "STOP-6, after STOP-16" if policy == "ask" else None, "command": f"{script} --fetch{arg}",
                "options": ["use it as it is", "fetch only (network: updates origin/main; no branch or file changes)",
                            "stop"] if policy == "ask" else None,
                "summary": f"no fast-forward ({', '.join(blocked)}): "
                          + ("ask: use as is, fetch only, or stop" if policy == "ask" else "used as is (auto)")}
    return {"step": "ask" if policy == "ask" else "update", "policy": policy, "blockedBy": [],
            "ask": "STOP-6, after STOP-16" if policy == "ask" else None, "command": f"{script} --update{arg}",
            "options": ["yes, this run: fetch and fast-forward main", "no, use it as it is",
                        "always: the user sets ABLY_SPEC_SYNC=auto", "never ask: the user sets ABLY_SPEC_SYNC=off"]
            if policy == "ask" else None,
            "summary": "ask at STOP-6 after STOP-16" if policy == "ask" else "fetch and fast-forward (auto)"}


def clone_warning(spec, md=False):
    """The State summary's warning for a clone that isn't the shared clone (13.9): {level, title, text}, else None.

    Offline facts only. A notice for a clean, checked-out `main`; the stronger warning for another branch, a detached
    HEAD, local commits not on origin/main, or tracked changes (untracked notes don't count, 2.6)."""
    if not spec or not spec.get("specClone") or spec.get("syncEligible") is not False:
        return None
    q = (lambda x: f"`{x}`") if md else (lambda x: x)
    who = "the spec clone you named" if spec.get("kind") == "explicit" else "the clone this skill is installed from"
    up = spec.get("upstream") or {}
    behind, ahead = up.get("behind"), up.get("ahead")
    tracked = spec.get("trackedChanges") or []
    off_branch = bool(spec.get("detached")) or spec.get("branch") != "main"
    counted = up.get("sha") and behind is not None and ahead is not None
    parts = (["is on a detached HEAD"] if spec.get("detached") else
            [f"is on branch {q(spec.get('branch'))}"] if off_branch else
            [f"carries {ahead} local commit(s) not on {q('origin/main')}"] if ahead else [])
    parts += [f"has tracked changes in {len(tracked)} file(s)"] if tracked else []
    reads = "the guide, UTS docs, helper specs, corpus and features specs"
    where = (f"{behind} behind {q('origin/main')} as of the last fetch" if counted else
            f"{q('origin/main')} never fetched" if not up.get("sha") else
            f"ahead/behind {q('origin/main')} unknown")
    if not parts:
        return {"level": "notice", "title": "Spec clone not synced",
                "text": f"This run reads {reads} from {who} ({q(spec['specClone'])}, {q('main')}, {where}) and records "
                        "its SHA. It won't be updated: keep it current yourself, or use the shared clone."}
    bits = (["not on main"] if off_branch else ["not on origin/main"] if ahead else []) + \
        (["has tracked changes"] if tracked else [])
    drift = f"{ahead} ahead / {behind} behind {q('origin/main')} as of the last fetch" if counted else where
    gone = (", and its SHA may not resolve once that branch is gone" if off_branch else
            ", and its SHA may not resolve once those local commits are gone" if ahead else "")
    return {"level": "warning", "title": "Spec clone not synced, and " + " and ".join(bits),
            "text": f"{who[0].upper() + who[1:]} ({q(spec['specClone'])}) {', and '.join(parts)} ({drift}). This run "
                    f"reads {reads} from it, so the harness, the construct catalogue and the records will follow it"
                    f"{gone}. It won't be updated. "
                    + ("Answering the run-mode question confirms you want to use it." if md else
                        "Your STOP-13 answer confirms you want to use it.")}


SIDE_VALUES = ("core", "server", "device", "both")
CAP_NAMES = {"rest": "REST", "realtime": "Realtime"}
TIER_ROWS = {  # (tier, harness pieces, gap-table rows, smoke tests and self-tests): uts-infra-design.md, guide 2.7
    "rest": ("REST unit", "HTTP hook, MockHttpClient, fake clock, randomness hooks", ["G-02", "G-06", "G-03", "G-05"],
            "REST unit smoke test; MockHttpClient and fake-clock self-tests"),
    "realtime": ("Realtime unit", "WebSocket hook, MockWebSocket, fake clock, network monitor, randomness hooks, "
                                  "MockVCDiff, MockNetworkListener, wait helpers",
                ["G-01", "G-07", "G-03", "G-04", "G-05", "G-08", "G-09", "G-11"],
                "Realtime unit smoke test; MockWebSocket, fake-clock and wait-helper self-tests"),
}
COMMON_ROWS = ["G-12", "G-13", "G-14", "G-17", "G-18", "G-19", "G-20"]
SOURCE_SUFFIXES = (".cs", ".java", ".kt", ".swift", ".m", ".py", ".go", ".js", ".ts", ".rb", ".dart", ".rs", ".php")


def scope_for_side(sc, sides, side):
    """The suggested scope (13.8) for the chosen side: a door without a REST or Realtime client drops that module."""
    sc = dict(sc or {})
    if side not in (sides or {}) or side == "core":
        return sc
    mods = [m for m in sc.get("modules", []) if (sides[side] or {}).get(m)]
    un = dict(sc.get("unsupported") or {})
    for m in sc.get("modules", []):
        if m not in mods:
            un[m] = f"not on the {side} side (D-31)"
    sc.update(modules=mods, unsupported=un, kind={("rest", "realtime"): "full", ("rest",): "rest-only",
                                                  ("realtime",): "realtime-only"}.get(tuple(mods), "none"))
    return sc


def door_types():
    """The door types per side, from assets/capability-names.json (doorFactories.sides.*.types); {} if unreadable."""
    try:
        data = json.loads((HERE.parent / "assets" / "capability-names.json").read_text(encoding="utf-8"))
        return {s: v.get("types", []) for s, v in data["doorFactories"]["sides"].items() if not s.startswith("_")}
    except (OSError, ValueError, KeyError, AttributeError):
        return {}


def side_evidence(repo, sides):
    """Which side the repo's UTS code already constructs clients through: {side: [files]} (heuristic, 13.8).

    Reads tracked source files under a `uts` path segment. Core: `new <Client>(` (or `= <Client>(`); a door: a call to
    its entry point in a file that also names the door's type (so a helper with the same name doesn't count)."""
    core = [n for n in (sides.get("core") or {}).get("rest", []) + (sides.get("core") or {}).get("realtime", [])
            if not re.match(r"I[A-Z]", n)]
    pats = {"core": re.compile(r"(?:\bnew\s+|[=(,]\s*)(?:" + "|".join(map(re.escape, core)) + r")\s*[(<]")} if core \
        else {}
    types = door_types()
    need = {d: re.compile(r"\b(?:" + "|".join(map(re.escape, t)) + r")\b") for d, t in types.items() if t}
    for side in DOOR_SIDES:
        names = {n for n in (sides.get(side) or {}).get("rest", []) + (sides.get(side) or {}).get("realtime", [])
                if n not in core and not re.match(r"I[A-Z]", n)}
        if names:
            pats[side] = re.compile(r"\b(?:" + "|".join(map(re.escape, sorted(names))) + r")\s*\(")
    files = [f for f in (git(repo, "ls-files", "-z") or "").split("\0")
            if f.endswith(SOURCE_SUFFIXES) and any(p.lower() == "uts" for p in f.split("/")[:-1])][:600]
    hits = {}
    for f in files:
        try:
            text = (repo / f).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for side, pat in pats.items():
            if pat.search(text) and (side not in need or need[side].search(text)):
                hits.setdefault(side, []).append(f)
    for side in hits:  # files that name clients first: they show the construction most plainly
        hits[side].sort(key=lambda f: ("client" not in f.rsplit("/", 1)[-1].lower(), f))
    return hits


def infra_plan(caps, state_class, insp, skills, side, recorded_side, repo, lo):
    """The UTS infrastructure plan outline for STOP-17 (13.8): per tier the harness pieces with their gap-table rows,
    the smoke tests and self-tests, what's left out and why, and how the harness creates clients (the side).

    The side comes from --side, else a recorded D-31 side still among the doors, else the existing UTS code when it
    uses exactly one side (detected, not asked); otherwise it is open and STOP-17 asks it."""
    if not caps:
        return None
    sides = caps.get("sides") or {}
    doors = [d for d in DOOR_SIDES if d in sides]
    chosen = side or (recorded_side if recorded_side in SIDE_VALUES and (recorded_side in ("core", "both") or
                                                                        recorded_side in doors) else None)
    chosen_by = "--side" if side else ("records (D-31)" if chosen else None)
    side_info = None
    if doors:
        ev = side_evidence(repo, sides)
        found = [s for s in ("core",) + DOOR_SIDES if ev.get(s)]
        options = []
        core_names = [n for n in sides.get("core", {}).get("rest", []) + sides.get("core", {}).get("realtime", [])
                      if not re.match(r"I[A-Z]", n)]
        options.append({"value": "core", "names": core_names,
                        "text": f"Core constructors ({', '.join(f'`{n}`' for n in core_names)}), through the "
                                "sanctioned internal-access route such as `InternalsVisibleTo`"})
        for d in doors:
            entry = [n for n in sides[d].get("rest", []) + sides[d].get("realtime", []) if n not in core_names]
            lacks = [m for m in ("rest", "realtime") if m in caps.get("scopeSuggestion", {}).get("modules", [])
                    and not sides[d].get(m)]
            options.append({"value": d, "names": entry, "lacks": lacks,
                            "text": f"{d.capitalize()} door: {', '.join(f'`{n}`' for n in entry)}"
                            + (f" (no {' or '.join(CAP_NAMES[m] for m in lacks)} client: the plan drops those tiers)"
                              if lacks else "")})
        options.append({"value": "both", "names": [],
                        "text": ("Both doors" if len(doors) == 2 else f"Core and the {doors[0]} door")
                        + " as a harness parameter (one suite, run once per side)"})
        recommended = found[0] if len(found) == 1 else None
        if recommended:  # the recommended option comes first (asking.md)
            options.sort(key=lambda opt: opt["value"] != recommended)
        if not chosen and recommended:  # the existing UTS code uses exactly one side: detected, not asked (13.8)
            chosen, chosen_by = recommended, "existing UTS code"
        side_info = {
            "doors": doors, "chosen": chosen, "chosenBy": chosen_by, "options": options, "recommended": recommended,
            "evidence": {s: ev[s][:3] + ([f"… {len(ev[s]) - 3} more"] if len(ev[s]) > 3 else []) for s in found},
            "evidenceCount": {s: len(ev[s]) for s in found}, "provisional": True}
    sc = scope_for_side(caps.get("scopeSuggestion"), sides, chosen)
    mods = sc.get("modules", [])
    tiers = []
    for m in ("rest", "realtime"):
        if m in mods:
            name, pieces, rows, tests = TIER_ROWS[m]
            if m == "realtime" and "rest" not in mods:  # a Realtime client still uses HTTP (13.8)
                pieces, rows = pieces + ", plus the HTTP hook and MockHttpClient", rows + ["G-02", "G-06"]
            tiers.append({"tier": name, "modules": [m], "harness": pieces, "rows": rows, "tests": tests})
    if mods:
        tiers.append({"tier": "Integration (sandbox)", "modules": list(mods), "harness": "SandboxApp and fixtures",
                      "rows": ["G-15"], "tests": "sandbox smoke test and self-tests"})
        tiers.append({"tier": "Integration (proxy)", "modules": list(mods), "harness": "ProxyManager, ProxySession",
                      "rows": ["G-16"], "tests": "proxy smoke test and self-tests"})
    rt_absent = caps.get("capabilities", {}).get("realtime", {}).get("level") == "absent"
    undecided = sc.get("undecided") or []
    objects = ("no: capability absent, no realtime client" if rt_absent else
              "undecided with realtime: ask at STOP-17, then STOP-14" if "objects" in undecided else
              "no: realtime isn't in scope" if "realtime" not in mods else
              f"decided at STOP-14 (detector: {((lo or {}).get('recommendation') or {}).get('addLiveObjects') or '?'})")
    left = [{"what": m, "why": r, "plain": plain(r)} for m, r in (sc.get("unsupported") or {}).items()]
    left += [{"what": m, "why": "undecided: ask at STOP-17 what the SDK offers",
              "plain": "undecided: tell me whether the SDK offers it"} for m in undecided]
    if sc.get("capabilityInapplicable"):
        left.append({"what": f"{len(sc['capabilityInapplicable'])} capability-inapplicable test(s) or path(s)",
                    "why": "they need a client this SDK (or side) lacks; guide 7.4 case (d)",
                    "plain": "they need a client this SDK lacks"})
    existing = None
    if state_class in ("S2", "S3", "S4") and skills:  # an Upgrade/Fix run: name the harness it audits, if any
        found_h = sorted({("declared in the skill's mapping" if s["harness"] == "from mapping" else
                          s["harness"].replace("candidates: ", "") + " (candidate)") for s in skills
                          if s["harness"] != "none found"})
        existing = ", ".join(found_h) or None
    return {"modules": mods, "scopeKind": sc.get("kind"), "tiers": tiers, "commonRows": COMMON_ROWS,
            "objects": objects, "leftOut": left, "existingHarness": existing, "side": side_info}


def profile_evidence(caps):
    """The capability levels with what they rest on: client names, Realtime sub-areas, transport (13.8)."""
    c = caps.get("capabilities", {})

    def names(cap):
        n = (c.get(cap, {}).get("client") or {}).get("names") or []
        return ", ".join(f"`{x}`" for x in n[:3]) or "no client found"
    subs = ", ".join(f"{a} {v.get('level')}" for a, v in (c.get("realtime", {}).get("subAreas") or {}).items())
    transport = re.search(r"; (WebSocket transport|transport in the wrapped native SDKs|no WebSocket code)",
                          caps.get("summary") or "")
    return (f"REST {c.get('rest', {}).get('level')} ({names('rest')}); Realtime {c.get('realtime', {}).get('level')} "
            f"({names('realtime')}{'; ' + subs if subs else ''})" + (f"; {transport.group(1)}" if transport else "")
            + (f"; source: {caps['source']}" if caps.get("source") not in (None, "detected") else ""))


def plain(text):
    """User-facing wording (asking.md): drop internal references such as (D-31), (P-13), (13.9) or (section 10)."""
    ref = r"(?:[DPGU]-?\d+|STOP-\d+|\d+\.\d+|section \d+(?:\.\d+)?|staged, 11\.5)"
    text = re.sub(rf"\s*\({ref}(?:,\s*{ref})*\)", "", str(text))
    text = re.sub(r"[,;:]?\s*(?:a change item, )?section \d+(?:\.\d+)?\b", "", text)
    return re.sub(r";?\s*guide \d+\.\d+ case \([a-z]\)", "", text)


def profile_checks(caps, delta, added, lowered):
    """What the user should check in the capability profile, in plain words (STOP-17 question 1, 13.8)."""
    c, sc = caps.get("capabilities", {}), caps.get("scopeSuggestion", {})
    rest, rt = c.get("rest", {}).get("level"), c.get("realtime", {}).get("level")
    found = re.sub(r"; source: .*$", "", profile_evidence(caps))
    out = [f"Found: {found}"]
    if rest == "partial":
        out.append("REST: a client was found, but not enough of its methods, or no REST channel.")
    missing = [a for a, v in (c.get("realtime", {}).get("subAreas") or {}).items() if v.get("level") != "present"]
    if rt == "partial" and sc.get("kind") != "unclear":
        out.append("Realtime: " + (f"missing or only stubbed: {', '.join(missing)}." if missing else
                                  "no WebSocket transport found."))
    if rt == "unclear":
        out.append("Realtime: a client is declared, but it isn't public and nothing public returns it. Can the tests "
                  "reach it?")
    elif sc.get("kind") == "unclear":
        out.append("Realtime: no connection or channels found, and no REST client. What does this SDK offer?")
    if sc.get("kind") == "none":
        out.append("No public REST or Realtime client found. Is this the right repository path?")
    gaps = c.get("realtime", {}).get("methodGapsAdvisory") or []
    if gaps:
        out.append(f"Some Realtime methods weren't found ({len(gaps)}, for example {', '.join(gaps[:2])}): likely "
                  "deviations, decided test by test.")
    if caps.get("wrapsNativeSdk"):
        out.append("It wraps native SDKs, so the unit-test hooks may be out of reach; integration tests still apply.")
    if caps.get("source", "detected") != "detected":
        out.append("These levels are your correction." if "your correction" in caps["source"] else
                  "These levels come from this skill's list of supported repos, not from the scan.")
    if delta:
        out.append("Changed since the last run: " + ", ".join(
            f"{k} {re.sub(r' [(](ask the side question|recorded level inferred from the mapping)[)]', '', v)}"
            for k, v in delta.items())
            + (f"; newly available: {', '.join(added)}" if added else "")
            + (f"; lower than before: {', '.join(lowered)} (a detection miss, or really removed?)" if lowered else "")
            + ".")
    if caps.get("namesSource") == "fallback":
        out.append("The spec's names couldn't be read, so this detection is less reliable.")
    return out


MODES = (  # STOP-13 option prefix -> (mode, plain label, plain detail); asking.md
    ("Upgrade/Fix, diff-driven", "upgrade", "Upgrade/Fix, changes only",
      "update the skill for what changed since its last run"),
    ("Upgrade/Fix, full gap audit", "upgrade", "Upgrade/Fix, full audit",
      "check the skill, harness and tests against the guide, then choose what to fix"),
    ("Upgrade/Fix ", "upgrade", None, "work on this skill"),
    ("Regenerate", "regenerate", "Regenerate from scratch", "rebuild the skill and harness, approving each replacement"),
    ("Create, keeping", "create", "Create, keeping what's here",
      "build the skill around the UTS tests and harness already here"),
    ("Create a new skill", "create", "Create a new skill", "leave the existing skills as they are"),
    ("Create", "create", "Create", "build the skill and its UTS test harness"),
    ("Repair", "repair", "Repair the installs first", "fix the broken links or copies, asking before each change"),
    ("Resume", "resume", "Resume", "continue from where the last run stopped"),
    ("Restart", "restart", "Restart", "start over, replacing earlier decisions and keeping files"),
    ("Stop", "stop", "Stop", ""),
)


def mode_of(option):
    """(mode, plain label, plain detail) for a STOP-13 option (13.4)."""
    for prefix, mode, label, detail in MODES:
        if option.startswith(prefix):  # S4's "Upgrade/Fix <dir>" names the skill by its directory's last part
            return mode, label or prefix + option[len(prefix):].rstrip("/").rsplit("/", 1)[-1], detail
    return "other", plain(option), ""


def is_stop(o):
    return o.get("mode") == "stop" or str(o.get("value")).lower() == "stop"


def option(label, detail="", value=None, recommended=False):
    return {"label": label, "detail": detail, "value": value or label, "recommended": recommended}


def stop13_question(state, skills, insp, delta, changes, repo_name, plan=None):
    """STOP-13, the run mode, as a question (asking.md; 13.4). With a side detected from the existing UTS code, a
    `note` names that client setup in one plain sentence, shown in both forms."""
    cls, d = state["class"], (skills[0]["dir"] if len(skills) == 1 else None)
    target = f"`{d}`" if d else "this repo"
    if state["reentry"]:
        q, why = f"How should this run continue on {target}?", "An earlier run didn't finish" + (
            ", and the spec has moved since." if any("spec moved" in r for r in state["reasons"]) else ".")
    elif cls in ("S0", "S1"):
        q = f"Should I create a UTS translator skill for {repo_name}?"
        why = ("There's no translator skill, harness or UTS test here yet." if cls == "S0" else
                "There's no translator skill yet, but UTS tests or harness code are already here, and I'll keep them.")
    elif cls == "S4":
        q, why = "Which skill should this run work on?", "There's more than one skill here, or a broken install."
    else:
        q = f"How should this run work on {target}?"
        if cls == "S3":
            why = ("The skill has this procedure's stamp but no records, so its gaps against the guide are unknown."
                    if skills and skills[0]["origin"] == "creator-metadata" else
                    "The skill wasn't made by this procedure, so its gaps against the guide are unknown.")
        elif state["recommended"] == "Stop":
            why = "Nothing has changed since the skill's last run."
        elif changes and not changes.get("anchorPresent"):
            why = "The records don't show which spec the skill was built from, so a full audit is the safe choice."
        elif delta:
            why = "The SDK's capabilities changed since the skill's last run."
        else:
            why = "This procedure made the skill, so I can update it for what changed since its last run."
    opts = []
    for o in state["options"]:
        mode, label, detail = mode_of(o)
        opts.append(dict(option(label, detail, o, o == state["recommended"]), mode=mode))
    labels = [x["label"] for x in opts]
    for x in opts:  # two skills with the same last path part: name them by their directory
        if labels.count(x["label"]) > 1 and x["value"].startswith("Upgrade/Fix "):
            x["label"] = x["value"]
    out = {"stop": "STOP-13", "header": "Run mode", "question": q, "why": why, "details": [], "options": opts}
    side = (plan or {}).get("side") or {}
    if side.get("chosenBy") in ("existing UTS code", "records (D-31)"):  # what the run assumes, one sentence (13.4)
        o = next((x for x in side["options"] if x["value"] == side["chosen"]), {"value": side["chosen"]})
        name = side_view(o, dict(side, recommended=None))[0].lower()
        rec = state.get("recommended") or ""
        harness = ("" if not plan.get("existingHarness") or mode_of(rec)[0] != "upgrade" else
                    " and audits the existing harness" if "full gap audit" in rec else
                    " and updates the existing harness for what changed")
        out["note"] = (f"Keeps the existing client setup ({name})" if side["chosenBy"] == "existing UTS code" else
                        f"Keeps the last run's client setup ({name})") + harness + "."
    return out


def side_view(o, side):
    """A side option in plain words (asking.md): (label, detail)."""
    names = ", ".join(f"`{n}`" for n in o.get("names", []))
    lacks = " and ".join(CAP_NAMES[m] for m in o.get("lacks", []))
    if o["value"] == "core":
        label, parts = "Core constructors", [names, "through internal access"]
    elif o["value"] == "both":
        label = "Both"
        parts = [(" and ".join(side["doors"]) + " entry points" if len(side["doors"]) == 2 else
                  f"core constructors and the {side['doors'][0]} entry point")
                  + " as a harness setting; the suite runs once for each"]
    else:
        label, parts = f"{o['value'].capitalize()} entry point", [names, f"no {lacks} client, so the {lacks} tests are "
                                                                          "dropped" if lacks else ""]
    detail = ("; " if o["value"] not in ("core", "both") else ", ").join(x for x in parts if x)
    if o["value"] == side.get("recommended"):
        files = [f for f in side["evidence"].get(o["value"], []) if not f.startswith("…")]
        n = side.get("evidenceCount", {}).get(o["value"], len(files))
        if files:
            detail += f": the existing UTS code already does this (`{files[0].rsplit('/', 1)[-1]}`" + (
                f" +{n - 1})" if n > 1 else ")")
    return label, detail


def client_setup(plan, where="asked below"):
    """The State summary's Client setup row (13.4), for an SDK with doors; None without doors."""
    side = (plan or {}).get("side")
    if not side:
        return None
    if not side.get("chosen"):
        return where
    o = next((x for x in side["options"] if x["value"] == side["chosen"]), {"value": side["chosen"], "names": []})
    label, detail = side_view(o, dict(side, recommended=None))
    text = f"{label.lower()}: {detail}"
    by = side.get("chosenBy")
    if by == "existing UTS code":
        files = [f for f in side["evidence"].get(side["chosen"], []) if not f.startswith("…")]
        n = side.get("evidenceCount", {}).get(side["chosen"], len(files))
        text += f" (existing harness: `{files[0].rsplit('/', 1)[-1]}`" + (f" +{n - 1})" if n > 1 else ")")
    else:
        text += " (your choice)" if by == "--side" else " (from the last run's records)"
    return text


def plan_details(plan, checks, ask_side, new_harness):
    """The plan as short plain bullets (STOP-17 question 1; asking.md)."""
    out = list(checks)
    if plan.get("existingHarness") and not new_harness:
        out.append(f"Harness: the existing one, {plain(plan['existingHarness'])}; the audit checks it against the "
                    "guide.")
    else:
        for t in plan["tiers"]:
            tier = {"Integration (sandbox)": "Sandbox integration", "Integration (proxy)": "Proxy integration"}.get(
                t["tier"], t["tier"])
            tests = re.sub(r"^(REST unit|Realtime unit|sandbox|proxy) ", "", t["tests"])
            out.append(f"{tier} tests: {t['harness']}; {tests}.")
        if plan["tiers"]:
            out.append("Every tier: log capture, file placement, a harness README with known gaps, the test target "
                        "and CI, and a concurrency model.")
    if ask_side:
        drops = [f"the {o['value']} entry point has no {' or '.join(CAP_NAMES[m] for m in o['lacks'])} client, so "
                  f"choosing it drops those tests" for o in plan["side"]["options"] if o.get("lacks")]
        out.append("Client setup: your answer to the client-setup question" + ("; " + "; ".join(drops) if drops
                                                                                else "") + ".")
    elif (plan.get("side") or {}).get("chosen"):
        out.append(f"Client setup: {client_setup(plan)}.")
    out.append("Left out: " + ("; ".join(f"{x['what'].replace(' capability-inapplicable test(s) or path(s)', ' tests')}"
                                          f" ({x['plain']})" for x in plan["leftOut"]) or "nothing") + ".")
    obj = plan.get("objects", "")
    out.append("LiveObjects: " + ("no, there's no Realtime client." if "capability absent" in obj else
                                  "decided with Realtime." if "undecided" in obj else
                                  "no, Realtime isn't in scope." if obj.startswith("no:") else
                                  "a separate question later."))
    return out


PLAN_MODES = ("create", "regenerate")  # modes that plan a new harness; Upgrade/Fix too when none was found


def stop17_questions(plan, caps, checks, ask_side, cap_reasons, stop13):
    """STOP-17 as up to two questions, each scheduled against the STOP-13 answer (13.1, 13.8).

    The plan question is needed for a mode when the profile needs confirming, or when the side is open and the mode
    plans a new harness. The side question is needed for every mode when the side is open. A question needed for
    every mode is asked now, after STOP-13; one needed for some modes only is a follow-up, asked only after the
    STOP-13 answer picks one of them (askIf)."""
    if not plan:
        return [], []
    considered = [o for o in stop13["options"] if o["mode"] not in ("stop", "repair")]

    def new_harness(mode):
        return mode in PLAN_MODES or not plan.get("existingHarness")

    now, later = [], []
    needed = [o for o in considered if cap_reasons or (ask_side and new_harness(o["mode"]))]
    variants = sorted({new_harness(o["mode"]) for o in needed})
    for nh in variants:
        q = {"stop": "STOP-17", "part": "plan", "header": "Harness plan", "question": "Is this harness plan right?",
              "why": ("I'll build this harness, and the skill can translate only the tests it covers." if nh else
                      "This sets what the skill covers; the audit checks the existing harness."),
              "details": plan_details(plan, checks, ask_side, nh),
              "options": [option("Yes", "go ahead with this plan", "accept", True),
                          option("Change something", "tell me what", "adjust"), option("Stop", "", "stop")]}
        if len(needed) == len(considered) and len(variants) == 1:
            if ask_side:  # the side question follows in the same message: no need to repeat what it drops
                q["details"] = [("Client setup: the next question." if x.startswith("Client setup: your answer")
                                  else x) for x in q["details"]]
            now.append(q)
        else:
            later.append(dict(q, askIf=[o["value"] for o in needed if new_harness(o["mode"]) == nh]))
    if ask_side:
        side = plan["side"]
        opts = []
        for o in side["options"]:
            label, detail = side_view(o, side)
            opts.append(option(label, detail, o["value"], o["value"] == side.get("recommended")))
        q = {"stop": "STOP-17", "part": "side", "header": "Client setup",
              "question": "How should the harness create clients?",
              "why": "Every generated test sets up its clients this way.", "details": [],
              "options": opts + [option("Stop", "", "stop")]}
        if considered:
            now.append(q)
    return now, later


def question_markdown(q, n):
    """One question block (asking.md): bold numbered question with the stop ID, why, details, one option list."""
    out = [f"**Question {n}: {q['question']}** *({q['stop']})*", q["why"]] + ([q["note"]] if q.get("note") else [])
    if q["details"]:
        out += [""] + [f"- {x}" for x in q["details"]]
    out.append("")
    opts = sorted(q["options"], key=lambda o: (not o["recommended"], is_stop(o)))
    for i, o in enumerate(opts, 1):
        out.append(f"{i}. {o['label']}" + (" (recommended)" if o["recommended"] else "")
                    + (f": {o['detail']}" if o["detail"] else ""))
    return "\n".join(out)


def reply_line(qs, start=1):
    """The last line of a message with questions (asking.md)."""
    if not qs:
        return None
    open_ = [start + i for i, q in enumerate(qs) if not any(o["recommended"] for o in q["options"])]
    if len(qs) == 1:
        return ("Reply with a number." if open_ else "Reply with a number, or `ok` to accept the recommendation.")
    line = "Reply with a number per question, or `ok` to accept all recommendations"
    if open_:
        line += (f" (Question {open_[0]} has no recommendation, so it needs a number)" if len(open_) == 1 else
                  f" (Questions {', '.join(map(str, open_))} have no recommendation, so they need a number)")
    return line + "."


def questions_markdown(qs, start=1):
    if not qs:
        return None
    return "\n\n".join([question_markdown(q, start + i) for i, q in enumerate(qs)] + [reply_line(qs, start)])


def follow_up_by_option(later):
    """The follow-up message for each STOP-13 option that needs one: {option: {questions, markdown,
    askUserQuestion}}, numbered from 1, holding only the questions whose askIf names that option (asking.md)."""
    out = {}
    for opt in dict.fromkeys(v for q in later for v in q["askIf"]):
        qs = [q for q in later if opt in q["askIf"]]
        out[opt] = {"questions": qs, "markdown": questions_markdown(qs), "askUserQuestion": ask_user_question(qs)}
    return out


def ask_user_question(qs):
    """The AskUserQuestion form (Claude Code; asking.md): {context, questions}, or None when a question doesn't fit
    (more than four options even without Stop), so the whole message uses the Markdown blocks."""
    if not qs or len(qs) > 4:
        return None
    out, context = [], []
    for q in qs:
        opts = sorted(q["options"], key=lambda o: (not o["recommended"], is_stop(o)))
        if len(opts) > 4:  # the tool's own "Other" answer still takes "stop"
            opts = [o for o in opts if not is_stop(o)]
        if not 2 <= len(opts) <= 4:
            return None
        if q["details"]:
            context.append(f"**{q['header']}**\n" + "\n".join(f"- {x}" for x in q["details"]))
        out.append({"question": " ".join(x for x in (q["question"], q["why"], q.get("note")) if x),
                    "header": q["header"], "multiSelect": False,
                    "options": [{"label": o["label"] + (" (Recommended)" if o["recommended"] else ""),
                                  "description": o["detail"] or ("end the run here" if o["label"] == "Stop" else
                                                                  o["label"])} for o in opts]})
    return {"context": "\n\n".join(context) or None, "questions": out}


CELL_MAX = 70
LAYOUTS = {"nativeSuite": "native suite", "dedicated": "dedicated", "mixed": "mixed"}


def split_outside_ticks(text, sep):
    parts, cur, ticks = [], "", 0
    i = 0
    while i < len(text):
        if text.startswith(sep, i) and ticks % 2 == 0:
            parts.append(cur + sep.rstrip())
            cur, i = "", i + len(sep)
            continue
        ticks += text[i] == "`"
        cur += text[i]
        i += 1
    return parts + [cur]


def cell_lines(text):
    """A Markdown table value as lines of at most CELL_MAX characters, broken at "; ", then ", ", then spaces
    (never inside a code span) and never cut, so a long value continues on rows with an empty Field (13.4)."""
    text = " ".join(str(text).split()).replace("|", "\\|")
    for sep in ("; ", ", ", " "):
        if all(len(p) <= CELL_MAX for p in split_outside_ticks(text, sep)):
            break
    lines, cur = [], ""
    for part in split_outside_ticks(text, sep):
        part = part.strip()
        if cur and len(cur) + 1 + len(part) > CELL_MAX:
            lines.append(cur)
            cur = part
        else:
            cur = f"{cur} {part}".strip()
    return lines + ([cur] if cur else []) or ["—"]


def short_path(path):
    home = str(pathlib.Path.home())
    return "~" + path[len(home):] if path and path.startswith(home + "/") else path


def plan_row(plan, stop17, md=False, where=None):
    """The State summary's Plan row (13.4): the outline in one line, and where it is confirmed. The Markdown form is
    in plain words (asking.md), and `where` says where STOP-17's plan question is asked: {recommended, now,
    laterNew, laterExisting, newLabels} (the STOP-13 labels of the modes, main()). With an existing harness it shows
    only the recommended mode's plan; another mode's plan comes with that mode's follow-up."""
    if not plan:
        return None
    side = plan.get("side") or {}
    short = {"Integration (sandbox)": "sandbox", "Integration (proxy)": "proxy"}
    tiers = (", ".join(short.get(t["tier"], t["tier"]) for t in plan["tiers"]) or "nothing") + \
        "; smoke tests and self-tests per tier"
    if md:
        w = where or {}
        later = w.get("laterNew", []) + w.get("laterExisting", [])
        left = "; left out: " + (", ".join(x["what"].replace(" capability-inapplicable test(s) or path(s)",
                                                              " tests that need a missing client")
                                            for x in plan["leftOut"]) or "nothing")
        prefix = ("asked below: " if w.get("now") else f"asked next if you choose {' or '.join(later)}: " if later
                  else "accepted with your run-mode answer: ")
        if not plan.get("existingHarness"):
            return prefix + tiers + left
        # An existing harness: only the recommended mode's plan; another mode's plan comes with its follow-up.
        mode, label = mode_of(w["recommended"])[:2] if w.get("recommended") else (None, None)
        new = mode in PLAN_MODES
        if not w.get("now"):
            prefix = (f"asked next if you choose {label}: " if label in w.get("laterNew" if new else "laterExisting",
                                                                              []) else
                      "accepted with your run-mode answer: ")
        short = re.sub(r"(?:[^\s,/]+/)+([^\s,/]+/[^\s,/]+)", r"\1", plain(plan["existingHarness"]))
        how = "updated for what changed" if "diff-driven" in (w.get("recommended") or "") else "checked in the audit"
        return prefix + (tiers if new else f"existing harness {short}, {how}") + left
    side_text = (f"side: {side['chosen']}" if side.get("chosen") else
                  "side: asked at STOP-17" if side else "one side")
    body = (f"existing harness ({plan['existingHarness']}), audited at U1 and STOP-15" if plan.get("existingHarness")
            else tiers)
    left = [x["what"].replace(" test(s) or path(s)", "") for x in plan["leftOut"]]
    return (("confirm at STOP-17: " if stop17 else "confirm with STOP-13: ") + f"{body}; {side_text}; left out: "
            + (", ".join(left) or "nothing"))


def summary_markdown(repo_name, head, dirty, elig, spec, insp, skills, lo, changes, state, caps=None, delta=None,
                    added=(), lowered=(), plan_where=None, others=None, sync=None, plan=None):
    """The State summary shown before Orient's questions (13.4): warnings as bold ⚠ lines, then a two-column table
    in plain words (asking.md), each value in lines of at most CELL_MAX characters. plan_where: where STOP-17's plan
    question is asked (plan_row)."""
    if state["class"] == "INELIGIBLE":
        return f"**⚠ Not eligible.** {state['reasons'][0]}"
    warns, rows = [], []
    w = clone_warning(spec, md=True)
    if w:
        warns.append(f"**⚠ {w['title']}.** {w['text']}")
    elif (spec or {}).get("staleWarning"):
        warns.append(f"**⚠ Stale spec clone.** {spec['staleWarning']}; "
                    + ("the sync is off (ABLY_SPEC_SYNC=off)." if spec.get("syncPolicy") == "off" else
                        "I'll offer to update it."))
    sources = {src.get("namesSource") for src in (lo, caps) if src and src.get("namesSource")}
    if sources and sources != {"spec"}:
        warns.append("**⚠ Spec names fallback.** The spec clone's IDL wasn't parsed, so the LiveObjects and capability "
                    "verdicts below are unreliable: I'll ask about it first.")
    langs = ", ".join(f"{k} {v}" for k, v in list(insp.get("repoLanguages", {}).items())[:3]) or "none"
    rows.append(("Repo", f"{repo_name} @ `{(head or '?')[:8]}` ({'dirty' if dirty else 'clean'}); {langs}"))
    rows.append(("Eligibility", eligibility_line(elig)[len("Eligibility  "):].replace("; STOP-16", "; asked first")))
    if (spec or {}).get("ok"):
        rows.append(("Spec clone", f"`{short_path(spec.get('specClone'))}` @ `{(spec.get('sha') or '?')[:8]}` "
                                  f"({'dirty' if spec.get('dirty') else 'clean'}); {clone_label(spec)}; "
                                  + (f"branch `{spec['branch']}`" if spec.get("branch") else "detached")
                                  + f"; found by {spec.get('foundBy')}"))
        up = spec.get("upstream") or {}
        rows.append(("Sync", (f"{up.get('ahead')} ahead / {up.get('behind')} behind `origin/main` as of the last "
                              f"fetch ({up.get('lastFetchDays')} days ago)"
                              if up.get("sha") and up.get("ahead") is not None and up.get("behind") is not None else
                              "ahead/behind `origin/main` unknown" if up.get("sha") else
                              "`origin/main` never fetched") + "; "
                    + ((sync or {}).get("summary", "none") if spec.get("syncEligible") else
                        "not synced (not the shared clone)")))
        rows.append(("Creator", f"{spec.get('skillVersion')} ("
                                + {True: "matches the clone", False: "differs from the clone: I'll ask"}.get(
                                    spec.get("skillMatchesClone"), "match unknown") + ")"))
    elif (spec or {}).get("bootstrapPath"):
        rows.append(("Spec clone", f"not found: no clone at `{short_path(spec['bootstrapPath'])}`; I'll offer to "
                                  "clone it there"))
    else:
        rows.append(("Spec clone", f"not usable ({(spec or {}).get('code', 'unknown error')}): I'll ask for its path"))
    rows.append(("Model", "(state the session's model; Opus-class required)"))
    if sources:
        rev = ((caps or lo or {}).get("specRevision") or {}).get("sha")
        rows.append(("Spec names", (f"from the spec clone's IDL @ `{rev[:8]}`" if rev else
                                    "from the IDL (revision unknown: not a git checkout)") if sources == {"spec"} else
                    "FALLBACK: don't rely on the LiveObjects or capability verdicts"))
    if caps:
        c = caps.get("capabilities", {})
        rt = c.get("realtime", {})
        subs = [a for a, v in (rt.get("subAreas") or {}).items() if v.get("level") == "present"]
        transport = re.search(r"; (WebSocket transport|transport in the wrapped native SDKs|no WebSocket code)",
                              caps.get("summary") or "")
        rest_names = ", ".join(((c.get("rest", {}).get("client") or {}).get("names") or [])[:2])
        rt_names = ", ".join(((rt.get("client") or {}).get("names") or [])[:2])
        rows.append(("Capabilities", f"REST {c.get('rest', {}).get('level')}" + (f" ({rest_names})" if rest_names else "")
                    + f"; Realtime {rt.get('level')}" + (f" ({rt_names}" + (f"; {', '.join(subs)}" if subs else "") + ")"
                                                        if rt_names and rt.get("level") != "absent" else "")
                    + (f"; {transport.group(1)}" if transport else "")
                    + ("" if caps.get("source") in (None, "detected") else "; source: your correction"
                        if "your correction" in caps["source"] else "; source: this skill's list of supported repos")))
        gaps = rt.get("methodGapsAdvisory") or []
        if gaps:
            rows.append(("Method gaps", f"advisory ({len(gaps)}): {', '.join(gaps[:3])}" + (", …" if len(gaps) > 3
                                                                                          else "")))
        if caps.get("wrapsNativeSdk"):
            rows.append(("Native SDK", "wraps native SDKs: unit tests only if the hooks are reachable"))
        if caps.get("sides"):
            rows.append(("Sides", ", ".join(s + ("" if v.get("rest") else " (Realtime only)") +
                                            ("" if v.get("realtime") else " (REST only)")
                                            for s, v in caps["sides"].items())))
            cs = client_setup(plan)
            if cs:
                rows.append(("Client setup", cs))
        sc = scope_for_side(caps.get("scopeSuggestion"), caps.get("sides"), ((plan or {}).get("side") or {}).get(
            "chosen"))
        un = ", ".join(f"{m} ({plain(r)})" for m, r in (sc.get("unsupported") or {}).items())
        rows.append(("Scope", f"{sc.get('kind')}: {', '.join(sc.get('modules', [])) or 'none'}"
                    + ("; LiveObjects asked later" if "realtime" in sc.get("modules", []) else "")
                    + (f"; unsupported: {un}" if un else "")
                    + (f"; undecided: {', '.join(sc['undecided'])} (asked below)" if sc.get("undecided") else "")
                    + (f"; {len(sc['capabilityInapplicable'])} tests need a missing client"
                      if sc.get("capabilityInapplicable") else "")
                    + (f"; plus {len(sc['extraTests'])} REST-only test(s) under realtime" if sc.get("extraTests")
                      else "")))
        pr = plan_row(plan, None, md=True, where=plan_where)
        if pr:
            rows.append(("Plan", pr))
        if delta:
            rows.append(("Capability change", ", ".join(f"{k} {v}" for k, v in delta.items())
                        + (f"; added: {', '.join(added)}" if added else "")
                        + (f"; lower than recorded: {', '.join(lowered)}" if lowered else "")))
    for s in skills:
        ch = s["checks"]
        rows.append(("Skill", f"`{s['dir']}`, name {s['name'] or 'missing'}, {len(s['installs'])} install(s), origin "
                              f"{s['origin']}, version {s['version'] or 'none'}; mapping: "
                              f"{', '.join(s['mappedModules']) or 'none'}; objects notes: {s['objectsNotes']}"))
        rows.append(("Skill hints", f"inspector: {ch.get('fail', 0)} fail, {ch.get('warn', 0)} warn, "
                                    f"{ch.get('pass', 0)} pass"))
        rows.append(("Harness", f"{s['harness']}; {s['smokeOrSelfTestFiles']} self-test file(s) by name"
                                + (f", {s['selfTestCandidates']} candidate(s) by location" if s.get("selfTestCandidates")
                                  else "")))
        if s["records"]:
            r = s["records"]
            rows.append(("Records", f"`{r['dir']}`: run {run_status(r)}; recorded spec "
                                    f"`{(r['recordedSpecSha'] or '?')[:8]}`" + checklist_progress(r)))
    if not skills:
        hc = insp.get("harnessCandidates") or {}
        rows.append(("Skills", "none" + (f"; other repo skills: {', '.join(insp.get('otherRepoSkills', []))}"
                                        if insp.get("otherRepoSkills") else "")))
        rows.append(("Harness", ("candidates: " + ", ".join(hc.get("candidateDirs", {}))) if hc.get("candidateDirs")
                    else "none found"))
    problems = [f"{b['path']}: {b['problem']}" for b in insp.get("brokenInstalls", [])]
    problems += [f"{o['dir']}: records with no skill" for o in insp.get("orphanRecords", [])]
    problems += [f"{d}: not classified (you named another skill)" for d in others or []]
    if problems:
        rows.append(("Problems", "; ".join(problems)))
    if changes and not changes.get("anchorPresent"):
        rows.append(("Changes", (f"recorded spec `{changes['anchorSpec'][:8]}` isn't in this clone: "
                                + ("fetch it" if (spec or {}).get("syncEligible") else
                                    "the user fetches it (this clone isn't synced)") + ", or run a full gap audit")
                    if changes.get("anchorSpec") else "the records name no spec SHA: run a full gap audit"))
    elif changes:
        rows.append(("Changes", f"since `{changes['anchorSpec'][:8]}`: guide {changes['guide']}, UTS docs "
                                f"{changes['utsDocs']}, helper specs {changes['helperSpecs']}, corpus "
                                f"{changes['corpus']} files; checklist changed: "
                                f"{'yes' if changes['checklistChanged'] else 'no'}"))
    dt = insp.get("derivedTests", {})
    mt = ", ".join(f"{k} {v}" for k, v in list(dt.get("byModuleTier", {}).items())[:3])
    rows.append(("UTS tests", f"{dt.get('tags', 0)} tags in {dt.get('taggedFiles', 0)} files "
                              f"({LAYOUTS.get(dt.get('layout'), dt.get('layout') or 'none')}{'; ' + mt if mt else ''}); "
                              f"{sum(dt.get('headerShas', {}).values())} header SHAs; deviations.md: "
                            f"{'yes' if dt.get('deviationsFiles') else 'none'}"))
    if lo or caps:
        rt_absent = bool(caps) and caps.get("capabilities", {}).get("realtime", {}).get("level") == "absent"
        rec = (lo or {}).get("recommendation", {})
        rows.append(("LiveObjects", "no: no realtime client" if rt_absent else
                    f"{rec.get('addLiveObjects')} ({rec.get('confidence')}); asked later"))
    rows.append(("User-level", ", ".join(insp.get("userLevelInstalls", [])) or "none"))
    more = len(state["reasons"]) - 1
    rows.append(("State", f"**{state['class']}**{' + re-entry' if state['reentry'] else ''}: "
                          + plain(state["reasons"][0] if state["reasons"] else "") + (f" (+{more} more)" if more > 0
                                                                                      else "")))
    rows.append(("Recommended", f"**{mode_of(state['recommended'])[1]}**" if state["recommended"] else
                "none: choose a skill below" if state["class"] == "S4" else "—"))
    table = ["| Field | Value |", "|---|---|"]
    for k, v in rows:
        for i, line in enumerate(cell_lines(v)):
            table.append(f"| {k if i == 0 else ''} | {line} |")
    return "\n\n".join(warns + ["\n".join(table)])


def summary_text(repo_name, head, dirty, elig, spec, insp, skills, lo, changes, state, caps=None, delta=None,
                  added=(), lowered=(), stop17=None, others=None, sync=None, plan=None):
    if state["class"] == "INELIGIBLE":
        return state["reasons"][0]
    dt = insp.get("derivedTests", {})
    langs = ", ".join(f"{k} {v}" for k, v in list(insp.get("repoLanguages", {}).items())[:4]) or "none"
    names_warnings = [w for src in (lo, caps) if src for w in src.get("warnings", [])]
    sources = {src.get("namesSource") for src in (lo, caps) if src and src.get("namesSource")}
    fallback = bool(sources) and sources != {"spec"}
    lines = []
    cw = clone_warning(spec)
    if cw:
        lines.append(f"WARNING      {cw['title'].upper()}: {cw['text']}")
    elif (spec or {}).get("staleWarning"):
        lines.append(f"WARNING      STALE SPEC CLONE: {spec['staleWarning']}; "
                    + ("the sync is off (ABLY_SPEC_SYNC=off)" if spec.get("syncPolicy") == "off" else
                        "offer the sync at STOP-6 (13.9)"))
    if fallback:
        lines.append("WARNING      SPEC NAMES FALLBACK: the spec clone's IDL wasn't parsed; the LiveObjects and capability "
                      "verdicts below are unreliable; settle it at STOP-1 first")
    lines += [
        f"Repo         {repo_name} @ {(head or '?')[:8]} ({'dirty' if dirty else 'clean'}); languages: {langs}",
        eligibility_line(elig),
        (f"Spec clone   {spec.get('specClone')} @ {(spec.get('sha') or '?')[:8]} "
          f"({'dirty' if spec.get('dirty') else 'clean'}); {clone_label(spec)}; "
          f"{'branch ' + spec['branch'] if spec.get('branch') else 'detached'}; found by {spec.get('foundBy')}; "
          f"creator {spec.get('skillVersion')} (matches clone: "
          f"{ {True: 'yes', False: 'no'}.get(spec.get('skillMatchesClone'), 'unknown')})"
          if (spec or {}).get("ok") else
          f"Spec clone   {spec['specClone']} (not usable: {spec.get('code')}: {spec.get('message')}); settle it at "
          "STOP-1" if (spec or {}).get("specClone") else
          f"Spec clone   {'NOT FOUND' if (spec or {}).get('code') == 'SPEC_CLONE_NOT_FOUND' else 'NOT USABLE'} "
          f"({(spec or {}).get('code', 'unknown error')}): "
          + (f"no clone at {spec['bootstrapPath']}; after STOP-16, offer to clone it there (STOP-1 with STOP-6, 13.9) "
            "or ask for its path" if (spec or {}).get("bootstrapPath") else
            ((spec or {}).get("message") or "") + "; settle it at STOP-1")),
    ]
    if (spec or {}).get("stalenessLine"):
        up = spec.get("upstream") or {}
        stale = spec["stalenessLine"]
        if up.get("sha") and up.get("ahead") is not None and up.get("behind") is not None:  # ahead/behind too (13.4)
            stale = (f"HEAD committed {spec.get('headAgeDays')} days ago; {up['ahead']} ahead / {up['behind']} behind "
                    f"origin/main as of the last fetch ({up.get('lastFetchDays')} days ago)")
        lines.append(f"             {stale}; "
                    + (f"sync: {(sync or {}).get('summary', 'none')}" if spec.get("syncEligible") else
                        "not synced (not the shared clone)"))
    lines.append("Model        (state the session's model; Opus-class required)")
    if sources:
        rev = ((caps or lo or {}).get("specRevision") or {}).get("sha")
        read = (caps or lo or {}).get("specClone")
        where = "the spec clone's IDL" if read and read == (spec or {}).get("specClone") else f"the IDL in {read}"
        lines.append("Spec names   " + (f"from {where}" + (f" @ {rev[:8]}" if rev else
                                                          " (revision unknown: not a git checkout)")
                                        if sources == {"spec"} else
                                        "FALLBACK, don't rely on the LiveObjects or capability verdicts: "
                                        + "; ".join(dict.fromkeys(names_warnings))))
    if caps:
        sc = caps.get("scopeSuggestion", {})
        src = caps.get("source") or "detected"
        lines.append(f"Capabilities {caps.get('summary')}"
                      + (f"; source: {src}" if src != "detected" and "source:" not in (caps.get("summary") or "") else ""))
        gaps = caps.get("capabilities", {}).get("realtime", {}).get("methodGapsAdvisory") or []
        if gaps:
            lines.append(f"Method gaps  advisory, realtime partial ({len(gaps)}): {', '.join(gaps[:8])}"
                          + (", …" if len(gaps) > 8 else "") + "; likely deviations or not-implemented, decided per "
                          "test, never out of scope")
        if caps.get("wrapsNativeSdk"):
            lines.append("Native SDK   wraps native SDKs over a platform bridge: hooks probably unreachable from the SDK "
                          "language: unit tier only if hooks exist (P-13); integration and proxy still offered")
        for side, v in (caps.get("sides") or {}).items():
            lines.append(f"Side         {side}: rest {', '.join(v['rest']) or 'none'}; realtime "
                          f"{', '.join(v['realtime']) or 'none'}")
        if (plan or {}).get("side"):
            lines.append("             side: " + (f"{plan['side']['chosen']} (from {plan['side']['chosenBy']})"
                                                  if plan["side"].get("chosen") else "asked at STOP-17 (13.8)")
                          + ("; provisional, re-confirmed at STOP-3" if plan["side"].get("chosen") else ""))
        sc = scope_for_side(sc, caps.get("sides"), ((plan or {}).get("side") or {}).get("chosen"))
        un = ", ".join(f"{m} ({r})" for m, r in sc.get("unsupported", {}).items())
        ci, extra, undecided = sc.get("capabilityInapplicable", []), sc.get("extraTests", []), sc.get("undecided", [])
        lines.append("Scope        " + (sc.get("kind", "?") + ": ") + (", ".join(sc.get("modules", [])) or "none")
                      + (" (objects per STOP-14)" if "realtime" in sc.get("modules", []) else "")
                      + (f"; undecided: {', '.join(undecided)} (ask at STOP-17)" if undecided else "")
                      + (f"; unsupported: {un}" if un else "")
                      + (f"; {len(ci)} capability-inapplicable test(s) or path(s)" if ci else "")
                      + (f"; plus {len(extra)} REST-only test(s) under realtime" if extra else "")
                      + ("; partial skill, extendable by Upgrade/Fix" if un or ci else "")
                      + ("; confirm at STOP-17" if stop17 else "; confirm with STOP-13"))
        pr = plan_row(plan, stop17)
        if pr:
            lines.append(f"Plan         {pr}")
        if delta:
            lines.append("Capability   changed since the recorded run: " + ", ".join(f"{k} {v}" for k, v in delta.items())
                          + (f"; added: {', '.join(added)}" if added else "")
                          + (f"; lower than recorded: {', '.join(lowered)}" if lowered else ""))
    if skills:
        for s in skills:
            c = s["checks"]
            lines.append(f"Skill        {s['dir']} [installs: {', '.join(s['installs'])}] name {s['name'] or 'missing'}, "
                          f"version {s['version'] or 'none'}, origin {s['origin']}")
            lines.append(f"             inspector hints: {c.get('fail', 0)} fail, {c.get('warn', 0)} warn, "
                          f"{c.get('pass', 0)} pass (regex, not a review); mapping: {', '.join(s['mappedModules']) or 'none'};"
                          f" objects notes: {s['objectsNotes']}")
            lack = s["tiersLackingSmoke"]
            lines.append(f"Harness      {s['harness']}; smoke/self-test files: {s['smokeOrSelfTestFiles']}"
                          + (f" by name; {s['selfTestCandidates']} candidate(s) by location (read to confirm)"
                            if s.get("selfTestCandidates") else "")
                          + (f"; offered tiers lacking them: {lack if isinstance(lack, str) else ', '.join(lack)}"
                            + (" (some files don't name a tier)" if lack == "unknown" else "") if lack else ""))
            if s["records"]:
                r = s["records"]
                lines.append(f"Records      {r['dir']}: run {run_status(r)}; recorded spec "
                              f"{(r['recordedSpecSha'] or '?')[:8]}, repo {(r['recordedRepoSha'] or '?')[:8]}"
                              + checklist_progress(r))
    else:
        hc = insp.get("harnessCandidates") or {}
        lines.append("Skills       none" + (f"; other repo skills: {', '.join(insp.get('otherRepoSkills', []))}"
                                            if insp.get("otherRepoSkills") else ""))
        lines.append("Harness      " + (("candidates: " + ", ".join(hc.get("candidateDirs", {}))) if hc.get("candidateDirs")
                                        else "none found"))
    problems = [f"{b['path']}: {b['problem']}" for b in insp.get("brokenInstalls", [])]
    problems += [f"{o['dir']}: records ({run_status(o)}) with no skill" for o in insp.get("orphanRecords", [])]
    problems += [f"{d}: another uts-to-* skill, not classified (--skill-dir)" for d in others or []]
    if problems:
        lines.append("Problems     " + "; ".join(problems))
    if changes and not changes.get("anchorPresent"):
        if changes.get("anchorSpec"):  # a recorded SHA this clone lacks; None when the records name no SHA
            fetch = ("fetch it (STOP-6, 13.9)" if (spec or {}).get("syncEligible") else
                    "the user fetches it (this clone isn't synced)")
            lines.append(f"Changes      recorded spec {changes['anchorSpec'][:8]} isn't in this clone: {fetch}, or "
                        "run a full gap audit")
        else:
            lines.append("Changes      the records name no spec SHA: run a full gap audit")
    elif changes:
        lines.append(f"Changes      since recorded spec {changes['anchorSpec'][:8]}: guide {changes['guide']}, UTS docs "
                      f"{changes['utsDocs']}, helper specs {changes['helperSpecs']}, corpus {changes['corpus']} files; "
                      f"checklist changed: {'yes' if changes['checklistChanged'] else 'no'}"
                      + (f"; repo {changes['repo']} files" if "repo" in changes else ""))
    mt = ", ".join(f"{k} {v}" for k, v in list(dt.get("byModuleTier", {}).items())[:6])
    lines.append(f"UTS tests    {dt.get('tags', 0)} tags in {dt.get('taggedFiles', 0)} files ({dt.get('layout') or 'none'})"
                  + (f"; {mt}" if mt else "") + f"; header SHAs: {sum(dt.get('headerShas', {}).values())} "
                  f"(without: {dt.get('filesWithoutHeaderShaCount', 0)}); deviations.md: "
                  f"{', '.join(dt.get('deviationsFiles', [])) or 'none'}")
    rt_absent = bool(caps) and caps.get("capabilities", {}).get("realtime", {}).get("level") == "absent"
    if lo and rt_absent:
        lines.append("LiveObjects  no: capability absent, no realtime client (decided at STOP-14)")
    elif lo:
        rec = lo.get("recommendation", {})
        lines.append(f"LiveObjects  {rec.get('addLiveObjects')} ({rec.get('confidence')}): "
                      f"{lo.get('summary', '').split('. Recommendation')[0][:220]} (decided at STOP-14)")
    lines.append(f"User-level   {', '.join(insp.get('userLevelInstalls', [])) or 'none'}")
    lines.append(f"State        {state['class']}{' + re-entry' if state['reentry'] else ''}: {'; '.join(state['reasons'])}")
    if state["recommended"]:
        lines.append(f"Recommended  {state['recommended']}")
    elif state["class"] == "S4":
        lines.append("Recommended  none (S4): ask which skill")
    return "\n".join(lines)


def run_status(rec):
    """`finished`, or `in progress (Phase n)` from the design record's Run status line."""
    m = re.search(r"Phase\s*(\d+)", rec.get("runStatusLine") or "")
    return rec["runStatus"] + (f" (Phase {m.group(1)})" if m and rec["runStatus"] == "in progress" else "")


def checklist_progress(rec):
    """"; checklist ✓ n, ✓ static n, ✗ n, n/a n, open n" from the inspector's records (13.4, 13.6), or ""."""
    c = rec.get("checklist")
    if not c:
        return ""
    return (f"; checklist ✓ {c['done']}, ✓ static {c['static']}, ✗ {c['fail']}, n/a {c['na']}, open {c['openTotal']}"
            + ("" if c.get("evidenceColumn") else " (no Evidence column)"))


USAGE = ("usage: orient.py <repo> [--spec-clone PATH] [--skill-dir PATH] [--records PATH] "
          "[--capability-override rest=LEVEL,realtime=LEVEL] [--side core|server|device|both] "
          "[--include-submodules] [--full]")


def usage_error(message):
    print(f"{USAGE}\norient.py: error: {message}", file=sys.stderr)
    return 2


def main(argv):
    if "-h" in argv[1:] or "--help" in argv[1:]:
        print(__doc__.strip())
        return 0
    args, opts, flags = [], {}, set()
    it = iter(argv[1:])
    for a in it:
        if a in ("--spec-clone", "--skill-dir", "--records", "--capability-override", "--side"):
            opts[a] = next(it, "")
            if not opts[a] or opts[a].startswith("-"):
                return usage_error(f"{a} needs a value")
        elif a in ("--include-submodules", "--full"):
            flags.add(a)
        elif a.startswith("-"):
            return usage_error(f"unknown option {a}")
        else:
            args.append(a)
    if len(args) != 1:
        return usage_error(f"expected one <repo>, got {len(args)} arguments")
    if "--side" in opts and opts["--side"] not in SIDE_VALUES:
        return usage_error(f"--side must be one of {', '.join(SIDE_VALUES)}, got {opts['--side']}")
    user_override = {}
    for item in filter(None, opts.get("--capability-override", "").split(",")):
        cap, _, level = item.partition("=")
        valid = {"rest": ("full", "partial", "absent"), "realtime": ("full", "partial", "absent", "unclear")}
        if cap not in valid or level not in valid[cap]:
            return usage_error(f"--capability-override takes rest=full|partial|absent and "
                              f"realtime=full|partial|absent|unclear, got {item}")
        user_override[cap] = level
    repo = pathlib.Path(args[0]).expanduser()
    if not repo.is_dir():
        return usage_error(f"not a directory: {args[0]}")
    repo = repo.resolve()
    warnings = []
    try:
        # Resolve the spec clone first, so every script reads the same one; a bad explicit path is an error.
        spec, w = run("spec_clone_info.py", *([opts["--spec-clone"]] if "--spec-clone" in opts else []))
        warnings += [w] if w else []
        if spec and spec.get("code") == "NOT_A_SPEC_CLONE":
            print(json.dumps({"ok": False, "code": "NOT_A_SPEC_CLONE", "message": spec.get("message"),
                              "missing": spec.get("missing"),
                              "fix": "pass the path of a local ably/specification clone (or a directory inside "
                                      "one) with --spec-clone, or correct ABLY_SPEC_CLONE, then run again"}, indent=2))
            return 1
        # Set on success, and on GIT_ERROR (a spec copy that isn't a git checkout): never drop an explicit clone.
        clone = (spec or {}).get("specClone")
        clone_args = ["--spec-clone", clone] if clone else []
        elig, w = run("check_repo_eligibility.py", str(repo), *clone_args)
        warnings += [w] if w else []
        if data_file_error(elig):
            return 1
        if elig and not elig.get("ok"):
            warnings.append(f"check_repo_eligibility.py: {elig.get('code')}: {elig.get('message')}")
        result = {"ok": True, "repo": str(repo), "eligibility": elig, "warnings": warnings}
        if elig and elig.get("decision") == "reject":
            state, _ = classify(elig, None, {}, [])
            result.update(state=state, stop16=elig.get("message"), stateSummaryText=elig.get("message"),
                          stateSummaryMarkdown=f"**⚠ Not eligible.** {elig.get('message')}",
                          questions={"now": [], "followUp": []}, questionsMarkdown=None, askUserQuestion=None,
                          followUpByOption={})
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        insp_args = [str(repo)] + ([opts["--skill-dir"]] if "--skill-dir" in opts else []) + \
            (["--records", opts["--records"]] if "--records" in opts else [])
        insp, w = run("inspect_existing_skill.py", *insp_args)
        warnings += [w] if w else []
        insp = insp if insp and insp.get("ok") else {}
        lo, w = run("detect_liveobjects.py", str(repo), *clone_args,
                    *(["--include-submodules"] if "--include-submodules" in flags else []))
        warnings += [w] if w else []
        override = dict((elig or {}).get("capabilityOverride") or {}, **user_override) or None
        caps, w = run("detect_capabilities.py", str(repo), *clone_args,
                      *(["--capability-override", ",".join(f"{k}={v}" for k, v in override.items())] if override else []),
                      *(["--include-submodules"] if "--include-submodules" in flags else []))
        warnings += [w] if w else []
        if data_file_error(lo, caps):
            return 1
        for name, out in (("detect_liveobjects.py", lo), ("detect_capabilities.py", caps)):
            if out and not out.get("ok"):
                warnings.append(f"{name}: {out.get('code')}: {out.get('message')}")
            elif out and out.get("namesSource") == "fallback":
                warnings += [f"{name}: {x}" for x in out.get("warnings", [])]
        caps = caps if caps and caps.get("ok") else None
        if caps and user_override:  # the user's correction at STOP-17, not the whitelist's
            caps["source"] = "override (your correction, --capability-override)"
            caps["summary"] = (caps.get("summary") or "").replace("override (whitelist)", caps["source"])
        lo = lo if lo and lo.get("ok") else None
        used = {out.get("specClone") for out in (lo, caps) if out and out.get("specClone")}
        if clone and used - {clone}:
            warnings.append(f"the detectors read names from {', '.join(sorted(used - {clone}))}, not the spec clone "
                            f"{clone}")
        skills = [skill_view(s, repo) for s in insp.get("skills", [])]
        others = None
        if "--skill-dir" in opts:  # classify only the named skill; list the others under Problems
            named = [s for s in skills if s["named"]]
            if named:
                others = [s["dir"] for s in skills if not s["named"]]
                skills = named
            else:
                warnings.append(f"--skill-dir {opts['--skill-dir']}: no uts-to-* skill with a SKILL.md there; "
                                "classified every skill found")
        changes = None
        if len(skills) == 1 and skills[0]["records"] and spec and spec.get("ok"):
            r = skills[0]["records"]
            changes = changes_since(spec.get("specClone"), r.get("recordedSpecSha"), repo, r.get("recordedRepoSha"))
        state, stop1 = classify(elig, spec, insp, skills, named_only=others is not None)
        recorded = skills[0]["capabilityProfile"] if len(skills) == 1 else None
        delta, added, lowered = capability_delta(recorded, caps)
        if delta:
            state["reasons"].append("capability changed since the recorded run: "
                                    + ", ".join(f"{k} {v}" for k, v in delta.items())
                                    + (f" (capability added: {', '.join(added)}: a change item, section 10)"
                                      if added else ""))
            if state["class"] == "S2" and not state["reentry"]:
                state["recommended"] = "Upgrade/Fix, diff-driven (section 10)"
        rt_level = caps["capabilities"]["realtime"]["level"] if caps else None
        if (lo or {}).get("namesSource") == "fallback" or (caps or {}).get("namesSource") == "fallback":
            stop1.append("spec names fell back to the data file's built-in names: fix the spec clone or parser first")
        side_arg = opts.get("--side")
        if side_arg and side_arg not in ("core", "both") and side_arg not in ((caps or {}).get("sides") or {}):
            warnings.append(f"--side {side_arg}: this repo has no {side_arg} door; ignored")
            side_arg = None
        plan = infra_plan(caps, state["class"], insp, skills, side_arg, (recorded or {}).get("side"), repo, lo)
        cap_reasons = stop17_reasons(caps, delta, added, lowered)
        ask_side = bool((plan or {}).get("side")) and not plan["side"].get("chosen")
        stop17 = "; ".join(cap_reasons + (["choose how the harness creates clients (the side)"] if ask_side else [])) \
            or None
        if state["class"] == "S2" and changes and changes.get("anchorPresent") and not delta and not any(
                changes.get(k) for k in ("guide", "utsDocs", "helperSpecs", "corpus", "repo")):
            state["reasons"].append("nothing changed since the recorded run")
            state["recommended"] = "Stop"
        if state["class"] == "S2" and not state["reentry"] and changes and not changes.get("anchorPresent"):
            if changes.get("anchorSpec"):
                fetch = "fetch it (STOP-6)" if (spec or {}).get("syncEligible") else \
                    "the user fetches it (this clone isn't synced)"
                state["reasons"].append(f"recorded spec {changes['anchorSpec'][:8]} isn't in this clone: diff-driven "
                                        f"can't diff; {fetch} and rerun, or run the full gap audit")
            else:
                state["reasons"].append("the records name no spec SHA: diff-driven can't diff; run the full gap audit")
            state["recommended"] = "Upgrade/Fix, full gap audit (section 11)"
        questions = {"now": [], "followUp": []}
        if state["class"] != "INELIGIBLE":
            stop13 = stop13_question(state, skills, insp, delta, changes, repo.name, plan)
            checks = profile_checks(caps, delta, added, lowered) if cap_reasons else []
            now17, later17 = stop17_questions(plan, caps, checks, ask_side, cap_reasons, stop13)
            questions = {"now": [stop13] + now17, "followUp": later17}
        later = [q for q in questions["followUp"] if q.get("part") == "plan"]
        plan_where = {  # where STOP-17's plan question is asked, by kind of run mode (13.4 Plan row)
            "recommended": state.get("recommended"),
            "now": any(q.get("part") == "plan" for q in questions["now"]),
            "laterNew": [mode_of(v)[1] for q in later if "build this harness" in q["why"] for v in q["askIf"]],
            "laterExisting": [mode_of(v)[1] for q in later if "build this harness" not in q["why"]
                              for v in q["askIf"]],
            "newLabels": [o["label"] for o in (questions["now"] or [{"options": []}])[0]["options"]
                          if o.get("mode") in PLAN_MODES]}
        plan_asked = bool(plan_where["now"] or later)
        sync = sync_plan(spec)
        cw = clone_warning(spec)
        if cw:
            warnings.append(f"spec clone: {cw['title']}: {cw['text']}")
            if sync and sync.get("synced") is False:
                sync["warning"] = cw["text"]
        if (spec or {}).get("staleWarning"):
            warnings.append(f"spec clone: {spec['staleWarning']}")
        warnings += [f"spec clone: {w}" for w in (spec or {}).get("warnings", [])]
        head = (git(repo, "rev-parse", "HEAD") or "").strip() or None
        dirty = bool((git(repo, "--no-optional-locks", "status", "--porcelain") or "").strip())
        stop16 = None if not elig or elig.get("decision") == "accept" else (elig.get("reason") or elig.get("message"))
        result.update(
            head=head, dirty=dirty, stop16=stop16,
            stop1=stop1, spec={k: (spec or {}).get(k) for k in (
                "ok", "code", "specClone", "kind", "foundBy", "isSharedClone", "syncEligible", "notSyncedWarning",
                "sha", "branch", "detached", "dirty", "trackedChanges",
                "upstream", "onOriginMain", "fastForwardBlockedBy", "staleWarning", "syncPolicy", "bootstrapPath",
                "partialLeftovers",
                "missing", "skillVersion", "skillMatchesClone")}, specSync=sync,
            repoLanguages=insp.get("repoLanguages"), skills=skills, brokenInstalls=insp.get("brokenInstalls"),
            orphanRecords=insp.get("orphanRecords"), otherRepoSkills=insp.get("otherRepoSkills"),
            unclassifiedSkills=others,
            userLevelInstalls=insp.get("userLevelInstalls"),
            derivedTests={k: insp.get("derivedTests", {}).get(k) for k in
                          ("tags", "taggedFiles", "layout", "byModuleTier", "headerShas", "filesWithoutHeaderShaCount",
                            "deviationsFiles", "tagsOutsideMappedTiers")},
            harnessCandidates=insp.get("harnessCandidates"),
            capabilities=(caps or {}).get("capabilities"), capabilitySummary=(caps or {}).get("summary"),
            sides=(caps or {}).get("sides"), capabilitySource=(caps or {}).get("source"),
            namesSource={"liveObjects": (lo or {}).get("namesSource"), "capabilities": (caps or {}).get("namesSource")},
            wrapsNativeSdk=(caps or {}).get("wrapsNativeSdk"), recordedCapabilityProfile=recorded,
            scope=(caps or {}).get("scopeSuggestion"),
            capabilityDelta=({"changes": delta, "added": added, "lowered": lowered} if delta else None), stop17=stop17,
            infraPlan=plan, questions=questions, questionsMarkdown=questions_markdown(questions["now"]),
            askUserQuestion=ask_user_question(questions["now"]),
            followUpByOption=follow_up_by_option(questions["followUp"]),
            specCloneWarning=clone_warning(spec, md=True),
            liveObjects=({"addLiveObjects": "no", "confidence": "high",
                          "summary": "capability absent: no realtime client (D-31)"} if rt_level == "absent" else
                          {"addLiveObjects": (lo or {}).get("recommendation", {}).get("addLiveObjects"),
                          "confidence": (lo or {}).get("recommendation", {}).get("confidence"),
                          "summary": (lo or {}).get("summary")}),
            changesSinceRecorded=changes, state=state)
        result["stateSummaryText"] = summary_text(repo.name, head, dirty, elig, spec, insp, skills, lo, changes, state,
                                                  caps, delta, added, lowered, plan_asked, others, sync, plan)
        result["stateSummaryMarkdown"] = summary_markdown(repo.name, head, dirty, elig, spec, insp, skills, lo, changes,
                                                          state, caps, delta, added, lowered, plan_where, others, sync,
                                                          plan)
        if "--full" in flags:
            result["raw"] = {"spec": spec, "inspect": insp, "liveObjects": lo, "capabilities": caps}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:  # never crash: report a structured error
        print(json.dumps({"ok": False, "code": "ORIENT_ERROR", "message": f"{type(exc).__name__}: {exc}",
                          "warnings": warnings}))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
