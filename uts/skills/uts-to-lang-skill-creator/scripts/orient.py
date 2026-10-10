#!/usr/bin/env python3
"""Step 0 of the skill: orient. Classify the target repository and recommend a mode.

Usage: orient.py <repo> [--spec-clone PATH] [--skill-dir PATH] [--records PATH]
                  [--include-submodules] [--full]

Runs, in order and by subprocess, this skill's read-only scripts:
  1. spec_clone_info.py         (resolves the spec clone the others read; STOP-1 preconditions;
                                a bad explicit path stops Orient with NOT_A_SPEC_CLONE)
  2. check_repo_eligibility.py  (STOP-16; on reject nothing else runs)
  3. inspect_existing_skill.py  (skills, origin, records, harness, UTS-tagged tests)
  4. detect_liveobjects.py      (the one-line LiveObjects verdict; STOP-14 decides later)
  5. detect_capabilities.py     (REST and Realtime capability profile, sides and scope; STOP-17, D-31),
                                with eligibility's `capabilityOverride` (from the whitelist) if any
The spec clone spec_clone_info.py resolved is passed
to the scripts that read names from the spec; if they fall back to the data
file's names (`namesSource` "fallback"), the State summary says so loudly, in
its first line. The current capability profile is compared with the one the
skill recorded (inspector `capabilityProfile`: the D-31 line, completed by the
mapping's `unsupported`/`capabilityInapplicable`): levels, scope kind, unsupported
modules and side; a difference is `capabilityDelta` and sets `stop17`, as do a
profile that isn't full, an unclear realtime, a capability override, doors
(the side question) and a wrapper over native SDKs (section 13.8).
then classifies the repo state and prints one JSON object with `state` (class,
re-entry, reasons, recommended option, options), `stateSummaryText` (the State
summary shown at STOP-13) and the facts behind them. `--full` embeds the raw
outputs of the four scripts.

State classes, first match wins (section 13.3 of the skill):
  INELIGIBLE  the repo isn't an Ably Pub/Sub SDK repository (hard stop)
  S4          ambiguous: several distinct uts-to-* skills, a broken install, a skill
              whose language isn't in the repo, or finished records with no skill
  S2          one skill, made by this procedure (its records), last run finished
  S3          one skill of unknown origin (hand-written, or records not kept)
  S1          no skill, but UTS-tagged tests or harness code exist
  S0          nothing
Re-entry (an unfinished run's records) is an overlay on the class; if the spec
clone's SHA differs from the records', it adds "spec moved since the records:
ask about restarting (13.6)". With --skill-dir only the named skill is
classified (after S4, to Upgrade/Fix one candidate); the other skills, broken
installs and orphan records are listed under Problems, not made S4.

Read-only: it writes nothing and never touches the network. Exit 0 whenever it
classifies; 2 on a usage error; 1 with {"ok": false} if it can't run at all.
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
                              timeout=TIMEOUT)
        return json.loads(out.stdout), None
    except subprocess.TimeoutExpired:
        return None, f"{script} timed out after {TIMEOUT} s"
    except (ValueError, OSError) as exc:
        return None, f"{script} failed: {type(exc).__name__}: {exc}"


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
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
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
    tiers = sorted({t for m in s.get("mapping", {}).get("modules", {}).values() for t in m if t in
                    ("unit", "integration", "proxy")})
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
        "harness": ("from mapping" if harness.get("readme") else
                    ("candidates: " + ", ".join(r["path"] for r in harness.get("readmes", [])) if harness.get("readmes")
                      else "none found")),
        "smokeOrSelfTestFiles": len(smoke) if isinstance(smoke, list) else None,
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


def side_question(sides):
    """The STOP-17 side question's options, from the sides present (section 13.8). None without doors."""
    doors = [d for d in DOOR_SIDES if d in (sides or {})]
    if not doors:
        return None
    opts = ["core/internal constructor (the sanctioned internal-access route)"] + [f"{d} door" for d in doors]
    opts.append(("both doors" if len(doors) == 2 else f"core and the {doors[0]} door") + " as a harness parameter")
    return ("STOP-17 must ask which side the UTS tests construct clients through: "
            + ", ".join(f"({chr(97 + i)}) {o}" for i, o in enumerate(opts)) + "; the scope follows the side (D-31)")


def stop17_reasons(caps, delta, added, lowered):
    """Why STOP-17 must be asked (section 13.8); empty when the user confirms the profile with STOP-13."""
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
    q = side_question(caps.get("sides"))
    if q:
        why.append(q)
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
        stop1.append(f"spec clone: {(spec or {}).get('code', 'unknown error')}: ask for the clone's path")
    else:
        if spec.get("skillMatchesClone") is False:
            stop1.append("the installed skill differs from the clone's copy: refresh the install or confirm")
        if spec.get("foundBy") != "argument":
            stop1.append(f"confirm the spec clone found by {spec.get('foundBy')}: {spec.get('specClone')}")
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


def summary_text(repo_name, head, dirty, elig, spec, insp, skills, lo, changes, state, caps=None, delta=None,
                  added=(), lowered=(), stop17=None, others=None):
    if state["class"] == "INELIGIBLE":
        return state["reasons"][0]
    dt = insp.get("derivedTests", {})
    langs = ", ".join(f"{k} {v}" for k, v in list(insp.get("repoLanguages", {}).items())[:4]) or "none"
    names_warnings = [w for src in (lo, caps) if src for w in src.get("warnings", [])]
    sources = {src.get("namesSource") for src in (lo, caps) if src and src.get("namesSource")}
    fallback = bool(sources) and sources != {"spec"}
    lines = []
    if fallback:
        lines.append("WARNING      SPEC NAMES FALLBACK: the spec clone's IDL wasn't parsed; the LiveObjects and capability "
                      "verdicts below are unreliable; settle it at STOP-1 first")
    lines += [
        f"Repo         {repo_name} @ {(head or '?')[:8]} ({'dirty' if dirty else 'clean'}); languages: {langs}",
        eligibility_line(elig),
        (f"Spec clone   {spec.get('specClone')} @ {(spec.get('sha') or '?')[:8]} "
         f"({'dirty' if spec.get('dirty') else 'clean'}); found by {spec.get('foundBy')}; "
         f"creator {spec.get('skillVersion')} (matches clone: "
         f"{ {True: 'yes', False: 'no'}.get(spec.get('skillMatchesClone'), 'unknown')})"
         if (spec or {}).get("ok") else
         f"Spec clone   NOT FOUND ({(spec or {}).get('code', 'unknown error')}): ask for its path at STOP-1"),
        "Model        (state the session's model; Opus-class required)",
    ]
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
        q = side_question(caps.get("sides"))
        if q:
            lines.append(f"             {q}")
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
                          + (f"; offered tiers lacking them: {lack if isinstance(lack, str) else ', '.join(lack)}"
                            + (" (some files don't name a tier)" if lack == "unknown" else "") if lack else ""))
            if s["records"]:
                r = s["records"]
                lines.append(f"Records      {r['dir']}: run {run_status(r)}; recorded spec "
                              f"{(r['recordedSpecSha'] or '?')[:8]}, repo {(r['recordedRepoSha'] or '?')[:8]}")
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
    if changes and changes.get("anchorPresent"):
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


def main(argv):
    args, opts, flags = [], {}, set()
    it = iter(argv[1:])
    for a in it:
        if a in ("--spec-clone", "--skill-dir", "--records"):
            opts[a] = next(it, None)
        elif a in ("--include-submodules", "--full"):
            flags.add(a)
        else:
            args.append(a)
    if len(args) != 1 or not pathlib.Path(args[0]).is_dir() or None in opts.values():
        print("usage: orient.py <repo> [--spec-clone PATH] [--skill-dir PATH] [--records PATH] "
              "[--include-submodules] [--full]", file=sys.stderr)
        return 2
    repo = pathlib.Path(args[0]).expanduser().resolve()
    warnings = []
    try:
        # Resolve the spec clone first, so every script reads the same one; a bad explicit path is an error.
        spec, w = run("spec_clone_info.py", *([opts["--spec-clone"]] if "--spec-clone" in opts else []))
        warnings += [w] if w else []
        if spec and spec.get("code") == "NOT_A_SPEC_CLONE":
            print(json.dumps({"ok": False, "code": "NOT_A_SPEC_CLONE", "message": spec.get("message"),
                              "missing": spec.get("missing"),
                              "fix": "pass the path of a local ably/specification clone (or a directory inside "
                                     "one) with --spec-clone, or correct UTS_SPEC_CLONE, then run again"}, indent=2))
            return 1
        clone = spec["specClone"] if spec and spec.get("ok") else None
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
            result.update(state=state, stop16=elig.get("message"), stateSummaryText=elig.get("message"))
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
        override = (elig or {}).get("capabilityOverride")
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
        stop17 = "; ".join(stop17_reasons(caps, delta, added, lowered)) or None
        if state["class"] == "S2" and changes and changes.get("anchorPresent") and not delta and not any(
                changes.get(k) for k in ("guide", "utsDocs", "helperSpecs", "corpus", "repo")):
            state["reasons"].append("nothing changed since the recorded run")
            state["recommended"] = "Stop"
        head = (git(repo, "rev-parse", "HEAD") or "").strip() or None
        dirty = bool((git(repo, "--no-optional-locks", "status", "--porcelain") or "").strip())
        stop16 = None if not elig or elig.get("decision") == "accept" else (elig.get("reason") or elig.get("message"))
        result.update(
            head=head, dirty=dirty, stop16=stop16,
            stop1=stop1, spec={k: (spec or {}).get(k) for k in ("ok", "code", "specClone", "foundBy", "sha", "dirty",
                                                                "skillVersion", "skillMatchesClone")},
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
            liveObjects=({"addLiveObjects": "no", "confidence": "high",
                          "summary": "capability absent: no realtime client (D-31)"} if rt_level == "absent" else
                          {"addLiveObjects": (lo or {}).get("recommendation", {}).get("addLiveObjects"),
                          "confidence": (lo or {}).get("recommendation", {}).get("confidence"),
                          "summary": (lo or {}).get("summary")}),
            changesSinceRecorded=changes, state=state)
        result["stateSummaryText"] = summary_text(repo.name, head, dirty, elig, spec, insp, skills, lo, changes, state,
                                                  caps, delta, added, lowered, stop17, others)
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
