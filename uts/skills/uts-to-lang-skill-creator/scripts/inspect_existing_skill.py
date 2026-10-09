#!/usr/bin/env python3
"""Static inventory of an existing uts-to-* skill, its harness and its UTS-derived tests.

Usage: inspect_existing_skill.py <repo> [<skill-dir>]

A read-only first pass for STOP-13 and the gap audit (section 11 of the skill).
It finds uts-to-* skills in the usual agent skill directories (.claude/skills,
.agents/skills, .codex/skills, .cursor/skills, .github/skills, skills) and any
other SKILL.md whose directory or `name:` starts with uts-to-, groups installs
that are the same directory (symlinks), and for each skill runs regex checks
against the guide's requirements: frontmatter portability, the files the
layout requires, the mapping's harness entry and notes, and SKILL.md sections.
Without a mapping `harness` entry it lists harness candidates (README
files near MockWebSocket / SandboxApp / ProxyManager definitions, smoke and
self-test files by name, CI workflow lines). It compares copies installed for
both tools, finds working records, counts UTS-derived test tags (and those
outside the mapped tier directories), the spec SHAs in their headers, and
deviations.md and other deviation-like records, and lists uts-to-* skills
installed at user level.

Each skill's `capabilityProfile` (also under `records`) is the design record's
parseable "Capabilities (D-31):" line (levels, liveobjects, side, scope kind and
modules, unsupported modules, capability-inapplicable count, names source),
completed by the mapping's `unsupported`, `capabilityInapplicable` and
`extraTests` keys (and the older `notApplicable`, `notApplicableSpecs`, and an
`unready` reason saying "not applicable" or "REST-only"). Without a D-31 line,
levels are inferred from the mapping's unsupported modules (`levelsInferred`).
Orient compares it with the current profile (section 13.8).

It never runs the skill's scripts and never writes. Each check names the
acceptance-checklist item it informs; a "pass" is a regex hit, not a review:
confirm every row by reading the files. Prints exactly one JSON object.
"""
import collections, filecmp, json, os, pathlib, re, subprocess, sys

SKILL_ROOTS = [".claude/skills", ".agents/skills", ".codex/skills", ".cursor/skills", ".github/skills", "skills"]
SELF = "uts-to-lang-skill-creator"
NON_PORTABLE = ["argument-hint", "model", "disable-model-invocation", "user-invocable", "when_to_use", "context",
                "agent", "hooks", "effort", "paths", "shell"]
SOURCE_EXT = {".cs", ".fs", ".py", ".go", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".rb", ".dart", ".rs",
              ".java", ".kt", ".kts", ".swift", ".m", ".mm", ".h"}
EXCLUDED_DIRS = {".git", "node_modules", "vendor", "Pods", "Carthage", ".build", "build", "dist", "out", "target",
                  "bin", "obj", "DerivedData", ".gradle", "__pycache__", ".venv", "venv", ".claude", ".agents",
                  ".codex", ".cursor"}
TAG = re.compile(r"^\s*(?:(//|#|--)\s*UTS:\s*(\S+)|/\*\*?\s*@UTS:?\s+(\S+)|(?:\*\s*)?@UTS:?\s+(\S+))")
HEADER_SHA = re.compile(r"ably/specification(?:@|/blob/|/tree/)([0-9a-f]{7,40})\b")
HEADER_UNPINNED = re.compile(r"ably/specification/(blob|tree)/main/")

# (id, acceptance-checklist item it informs, regex over SKILL.md body, what a hit means)
BODY_CHECKS = [
    ("B-harness-reference", "SKILL.md: usage guard ... 3.4 outline incl. the Harness reference",
      r"(?im)^#+\s.*harness reference", "a Harness reference heading"),
    ("B-preflight", "Steps 0 and A–F: the four questions and the harness preflight (stop on red)",
      r"(?i)preflight|step\s+F\b", "a harness preflight (step F)"),
    ("B-resync", "Re-sync mode; fix the cause, then regenerate", r"(?i)--resync|re-sync|resync", "a re-sync mode"),
    ("B-final-report", "Final report format", r"(?i)final report", "a final report"),
    ("B-lint", "Compile (or collect), lint, CI-strict compile, filtered run", r"(?i)\blint", "a lint step"),
    ("B-run-deviations", "Three end states; runtime skip and fail-fast idioms; `RUN_DEVIATIONS` command",
      r"RUN_DEVIATIONS", "the RUN_DEVIATIONS reproduction command"),
    ("B-deviations-deferred", "`deviations.md` location; format deferred; written at the right time",
      r"writing-derived-tests\.md", "a link to writing-derived-tests.md"),
    ("B-model", "Skill and harness created on an Opus-class model (MUST); model stated for runs ...",
      r"(?i)opus", "a model-tier statement"),
    ("B-reference-tests", "Steps 1–7 with batching; a reference test per tier; review in both modes",
      r"(?i)reference (test|example)|read (this|it) first", "named reference tests"),
    ("B-unmapped-construct-stop", "Unmapped constructs stop and ask; corpus scanner in `scripts/` (SHOULD)",
      r"(?i)(can'?t|cannot|unable to) map|unmapped construct|stop and ask", "a stop for unmapped constructs"),
    ("B-contains-in-order", "Record-and-verify for transient states; polls return the settled value",
      r"(?i)subsequence", "CONTAINS_IN_ORDER as a subsequence"),
]
# Checks whose regex can't tell a full implementation from a mention: reported as warnings.
WARN_ONLY = {"B-reference-tests", "B-contains-in-order", "B-unmapped-construct-stop"}
# (id, item, regex, meaning) where a hit is a defect
BODY_DEFECTS = [
    ("X-arguments", "SKILL.md: usage guard that doesn't rely on `$ARGUMENTS` ...", r"\$ARGUMENTS",
      "relies on $ARGUMENTS (Claude Code only)"),
    ("X-claude-path", "SKILL.md: usage guard ... own files referred to relative to the skill directory ...",
      r"\.claude/skills/", "hard-codes a .claude/skills/ path (breaks under Codex)"),
    ("X-fetch-main", "Required reading incl. features specs, from the same clone",
      r"(?i)(raw\.githubusercontent\.com/ably/specification|github\.com/ably/specification/(blob|tree)/main|fetch first)",
      "fetches docs or specs from GitHub main instead of the local clone"),
]


def git_lines(repo, *args):
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    return [l for l in out.stdout.decode("utf-8", "replace").split("\0" if "-z" in args else "\n") if l] \
        if out.returncode == 0 else None


def frontmatter(text):
    """Return (fields, raw lines, body). A small YAML subset: top-level keys and one nested map."""
    if not text.startswith("---"):
        return None, [], text
    end = text.find("\n---", 3)
    if end < 0:
        return None, [], text
    raw = text[3:end].strip("\n").splitlines()
    fields, current, block = {}, None, None
    for line in raw:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if m and not line.startswith((" ", "\t")):
            key, value = m.group(1), m.group(2)
            fields[key] = value if value else {}
            current = key if not value else None
            block = key if value.strip() in (">", ">-", ">+", "|", "|-", "|+") else None
            if block:
                fields[key] = ""
            continue
        if block and line.startswith((" ", "\t")):
            fields[block] = (fields[block] + " " + line.strip()).strip()
            continue
        m = re.match(r"^\s+([A-Za-z0-9_.-]+):\s*(.*)$", line)
        if m and current is not None and isinstance(fields[current], dict):
            fields[current][m.group(1)] = m.group(2)
    return fields, raw, text[end + 4:]


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1], True
    return value, False


def check(checks, cid, item, ok, evidence, warn=False):
    status = "pass" if ok else ("warn" if warn else "fail")
    checks.append({"id": cid, "item": item, "status": status, "evidence": evidence})


BROKEN = []
RECORDS_DIR = None
REPO_EXT_COUNTS = {}
LANG_EXT = {"csharp": {".cs"}, "dotnet": {".cs"}, "python": {".py"}, "go": {".go"}, "golang": {".go"},
            "js": {".js", ".ts"}, "javascript": {".js", ".ts"}, "typescript": {".ts"}, "ruby": {".rb"},
            "dart": {".dart"}, "flutter": {".dart"}, "rust": {".rs"}, "java": {".java", ".kt"},
            "kotlin": {".kt", ".java"}, "swift": {".swift", ".m"}, "objc": {".m", ".swift"}, "cocoa": {".swift", ".m"},
            "php": {".php"}}
LANG_NAMES = {".cs": "C#", ".py": "Python", ".go": "Go", ".js": "JavaScript", ".ts": "TypeScript", ".rb": "Ruby",
              ".dart": "Dart", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".swift": "Swift", ".m": "Objective-C",
              ".php": "PHP"}


MODULES = ("rest", "realtime", "objects")
SCOPE_KINDS = ("full", "rest-only", "realtime-only", "unclear", "none")


def scope_kind(modules):
    """The scope kind a recorded module list implies (records that list modules, not a kind)."""
    m = set(modules)
    if {"rest", "realtime"} <= m:
        return "full"
    if "rest" in m:
        return "rest-only"
    if "realtime" in m:
        return "realtime-only"
    return None


def parse_d31(line):
    """The design record's parseable "Capabilities (D-31):" line, as a profile (section 13.8 of the skill).

    Segments are separated by ";": "rest <level>", "realtime <level>[ (<sub-areas>)]", "liveobjects <yes|no>",
    "side: <side>[ (...)]", "scope: <kind>[ (<modules>)]" (older records: "scope: <modules>"),
    "unsupported: <modules> (<reason>)" (older records: "n/a: ..."), "capability-inapplicable: <n> tests ...",
    "names: <spec|fallback>". Unknown segments are kept in `unparsed`.
    """
    prof = {"raw": line.strip(), "from": "design record (D-31)", "rest": None, "realtime": None,
            "liveobjects": None, "side": None, "scopeKind": None, "scopeModules": [], "unsupported": [],
            "capabilityInapplicable": None, "names": None, "unparsed": []}
    for seg in (x.strip() for x in line.split(";")):
        low = seg.lower()
        m = re.match(r"(rest|realtime|liveobjects)\s+(full|partial|absent|unclear|yes|no)\b", low)
        if m:
            prof[m.group(1)] = m.group(2)
            continue
        key, _, val = low.partition(":")
        key, val = key.strip(), val.strip()
        head = re.split(r"[\s(]", val, maxsplit=1)[0] if val else ""
        inner = re.search(r"\(([^)]*)\)", val)
        if key == "side":
            prof["side"] = None if head in ("", "none", "n/a") else head
        elif key == "scope":
            mods = [x for x in re.findall(r"[a-z]+", val) if x in MODULES]
            if head in SCOPE_KINDS:
                prof["scopeKind"] = head
                # "(rest + 3 REST-only tests under realtime)": only the bare module names count
                mods = [x.strip() for x in re.split(r"[,+]", inner.group(1)) if x.strip() in MODULES] if inner else []
            prof["scopeModules"] = list(dict.fromkeys(mods))
            prof["scopeKind"] = prof["scopeKind"] or scope_kind(mods)
        elif key in ("unsupported", "n/a"):
            prof["unsupported"] = list(dict.fromkeys(
                x for x in re.findall(r"[a-z]+", val.split("(")[0]) if x in MODULES))
        elif key == "capability-inapplicable":
            n = re.match(r"(\d+)", val)
            prof["capabilityInapplicable"] = int(n.group(1)) if n else (0 if head in ("none", "0") else val)
        elif key == "names":
            prof["names"] = head or None
        elif seg:
            prof["unparsed"].append(seg)
    return prof


def read_records(rec_dir):
    """Working records of this procedure in rec_dir, or None: origin evidence, run status, recorded SHAs, D-31."""
    dr = rec_dir / "design-record.md"
    if not dr.is_file():
        return None
    text = dr.read_text(encoding="utf-8", errors="replace")
    ours = bool(re.match(r"#\s*Design record:\s*uts-to-", text)) and "uts-to-lang-skill-creator version" in text
    status = re.search(r"(?im)^-?\s*Run status:\s*(.+)$", text)
    spec = re.search(r"(?im)^-?\s*Spec clone:\s*([0-9a-f]{7,40})", text)
    repo_sha = re.search(r"(?im)^-?\s*Repo:\s*([0-9a-f]{7,40})", text)
    caps = re.search(r"(?im)^-?\s*Capabilities \(D-31\):\s*(.+)$", text)
    profile = None
    if caps:
        profile = parse_d31(caps.group(1))
    elif re.search(r"(?i)scope:\s*rest-only|not applicable: REST-only", text):
        profile = {"raw": None, "from": "older records (REST-only scope, before D-31)", "rest": "full",
                    "realtime": "absent", "liveobjects": None, "side": None, "scopeKind": "rest-only",
                    "scopeModules": ["rest"], "unsupported": ["realtime", "objects"], "capabilityInapplicable": None,
                    "names": None, "unparsed": []}
    final = (rec_dir / "final-report.md").is_file()
    if status:
        run = "finished" if status.group(1).strip().lower().startswith("finished") else "in progress"
    else:
        run = "finished" if final else "in progress"  # records from before the Run status line existed
    return {"dir": str(rec_dir), "creatorRecords": ours, "files": sorted(p.name for p in rec_dir.glob("*.md")),
            "runStatus": run, "runStatusLine": status.group(1).strip() if status else None,
            "recordedSpecSha": spec.group(1) if spec else None, "recordedRepoSha": repo_sha.group(1) if repo_sha else None,
            "finalReport": final, "capabilityProfile": profile}


LEGACY_UNSUPPORTED = re.compile(r"(?i)not applicable|rest-only|capability absent")


def mapping_profile(modules):
    """What the generated skill's mapping records about scope: `unsupported` modules and `capabilityInapplicable`
    entries (and the older keys `notApplicable`, `notApplicableSpecs`, and an `unready` reason saying "not
    applicable" or "REST-only"). None if the mapping says nothing about either."""
    unsupported, inapplicable, legacy = {}, {}, []
    for module, m in modules.items():
        if m.get("unsupported"):
            unsupported[module] = m["unsupported"] if isinstance(m["unsupported"], str) else "unsupported"
        elif m.get("notApplicable"):
            unsupported[module] = m["notApplicable"] if isinstance(m["notApplicable"], str) else "not applicable"
            legacy.append(f"{module}.notApplicable")
        elif isinstance(m.get("unready"), str) and LEGACY_UNSUPPORTED.search(m["unready"]):
            unsupported[module] = m["unready"]
            legacy.append(f"{module}.unready")
        for key in ("capabilityInapplicable", "notApplicableSpecs"):
            entries = m.get(key)
            if entries:
                inapplicable.setdefault(module, [])
                inapplicable[module] += list(entries) if isinstance(entries, (dict, list)) else [str(entries)]
                if key == "notApplicableSpecs":
                    legacy.append(f"{module}.notApplicableSpecs")
    if not unsupported and not inapplicable:
        return None
    return {"unsupported": unsupported, "capabilityInapplicable": {k: len(v) for k, v in inapplicable.items()},
            "capabilityInapplicableEntries": inapplicable, "legacyKeys": legacy}


def merge_profile(records, mprof):
    """The skill's capability profile: the records' D-31 line, completed by the mapping. Without a D-31 line, the
    levels are inferred from the mapping's `unsupported` modules (marked `levelsInferred`)."""
    prof = dict(records["capabilityProfile"]) if records and records.get("capabilityProfile") else None
    if mprof is None:
        return prof
    if prof is None:
        un = mprof["unsupported"]
        side_choice = any(re.search(r"(?i)\bside\b|\bdoor\b", r) for r in un.values())
        prof = {"raw": None, "from": "mapping (no D-31 line)", "levelsInferred": True,
                "rest": "absent" if "rest" in un and not side_choice else None,
                "realtime": "absent" if "realtime" in un and not side_choice else None,
                "liveobjects": None, "side": None, "scopeKind": None, "scopeModules": [], "unsupported": sorted(un),
                "capabilityInapplicable": None, "names": None, "unparsed": []}
        if not side_choice and prof["rest"] != prof["realtime"]:
            prof["scopeKind"] = "rest-only" if prof["realtime"] == "absent" else "realtime-only"
    prof["mapping"] = mprof
    return prof


def named_path(repo, explicit):
    """The <skill-dir> argument: as given (absolute, or relative to the working directory), else relative to the repo."""
    p = pathlib.Path(explicit).expanduser()
    p = p if p.is_absolute() or p.exists() or not (repo / p).exists() else repo / p
    return pathlib.Path(os.path.abspath(p))  # absolute, symlinks kept (an install may be a symlink)


def find_skills(repo, explicit):
    candidates = []
    if explicit:
        candidates.append(named_path(repo, explicit))
    for root in SKILL_ROOTS:
        base = repo / root
        if base.is_dir():
            candidates += sorted(p for p in base.iterdir() if p.name.startswith("uts-to-") and p.name != SELF)
    listed = git_lines(repo, "ls-files", "-co", "--exclude-standard", "-z") or []
    for rel in listed:
        if rel.endswith("SKILL.md") and not any(rel.startswith(r + "/") for r in SKILL_ROOTS):
            p = (repo / rel).parent
            head = (repo / rel).read_text(encoding="utf-8", errors="replace")[:600] if (repo / rel).is_file() else ""
            if (p.name.startswith("uts-to-") or re.search(r"(?m)^name:\s*[\"']?uts-to-", head)) and p.name != SELF:
                candidates.append(p)
    groups = collections.OrderedDict()
    for c in candidates:
        if not (c / "SKILL.md").is_file():
            rel = os.path.relpath(c, repo) if str(c).startswith(str(repo)) else str(c)
            if c.is_symlink() and not c.exists():
                BROKEN.append({"path": rel, "problem": f"dangling symlink to {os.readlink(c)}"})
            elif c.is_dir() and not (c / "generation" / "design-record.md").is_file():
                BROKEN.append({"path": rel, "problem": "uts-to-* directory without SKILL.md"})
            continue
        real = str(c.resolve())
        rel = os.path.relpath(c, repo) if str(c).startswith(str(repo)) else str(c)
        if rel not in [i["path"] for i in groups.get(real, [])]:  # the named <skill-dir> is also found by the scan
            groups.setdefault(real, []).append({"path": rel, "symlink": c.is_symlink()})
    return groups


def inspect_skill(repo, real, installs):
    d = pathlib.Path(real)
    text = (d / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    fields, raw, body = frontmatter(text)
    checks = []
    fm_item = "`SKILL.md` frontmatter portable across Claude Code and Codex ..."
    dir_name = pathlib.Path(installs[0]["path"]).name
    if fields is None:
        check(checks, "F-frontmatter", fm_item, False, "no YAML frontmatter")
        fields = {}
    name = unquote(fields.get("name", ""))[0] if isinstance(fields.get("name"), str) else ""
    check(checks, "F-name", fm_item, name == dir_name,
          f"name: {name!r}; directory: {dir_name!r}" if name else "no name field (required by the Agent Skills format)")
    desc = unquote(fields["description"])[0] if isinstance(fields.get("description"), str) else ""
    check(checks, "F-description-length", fm_item, 0 < len(desc) <= 1024, f"{len(desc)} characters")
    check(checks, "F-description-brackets", fm_item, not re.search(r"[<>]", desc),
          "no < or >" if not re.search(r"[<>]", desc) else "contains < or > (packaging validators reject it)")
    check(checks, "F-not-for", fm_item, bool(re.search(r"(?i)\bnot for\b", desc)),
          "has a 'Not for' boundary" if re.search(r"(?i)\bnot for\b", desc) else "no 'Not for' boundary", warn=True)
    check(checks, "F-third-person", fm_item, not re.match(r"(?i)\s*(translate|create|use|run)\b", desc),
          f"starts: {desc[:40]!r}", warn=True)
    meta = fields.get("metadata") if isinstance(fields.get("metadata"), dict) else {}
    bad_meta = [k for k, v in meta.items() if not unquote(v)[1] and re.fullmatch(r"(true|false|yes|no|null|[0-9.]+)", v.strip(), re.I)]
    check(checks, "F-metadata-strings", fm_item, not bad_meta,
          "metadata values are strings" if not bad_meta else f"unquoted non-string metadata: {bad_meta}")
    check(checks, "F-short-description", fm_item, "short-description" in meta,
          "metadata.short-description present" if "short-description" in meta else "no metadata.short-description (Codex list)",
          warn=True)
    non_portable = [k for k in NON_PORTABLE if k in fields]
    check(checks, "F-portable-fields", fm_item, not non_portable,
          "only portable fields" if not non_portable else f"Claude Code-only fields: {non_portable} (need D-26 acceptance)",
          warn=True)
    tools = fields.get("allowed-tools", "")
    tools = tools if isinstance(tools, str) else ""
    check(checks, "F-allowed-tools", fm_item, "," not in tools and "WebFetch" not in tools,
          f"allowed-tools: {tools!r}" + (" (comma-separated)" if "," in tools else "")
          + (" (WebFetch: remote reads, guide 9.4)" if "WebFetch" in tools else ""))
    for key in ("license", "compatibility"):
        check(checks, f"F-{key}", fm_item, key in fields, f"{key} {'present' if key in fields else 'missing'}", warn=True)

    body_no_urls = "\n".join(l for l in body.splitlines() if not re.search(r"https?://", l))
    for cid, item, pattern, meaning in BODY_CHECKS:
        hit = re.search(pattern, body_no_urls)
        check(checks, cid, item, bool(hit), meaning + (" found" if hit else " not found") + " (outside URLs)",
              warn=cid in WARN_ONLY)
    defect_sources = {"SKILL.md": body}
    for ref in sorted((d / "references").glob("*.md")) if (d / "references").is_dir() else []:
        defect_sources[f"references/{ref.name}"] = ref.read_text(encoding="utf-8", errors="replace")
    lines = text.count("\n") + 1
    check(checks, "B-length", "SKILL.md: ... follows the 3.4 outline", lines <= 500,
          f"{lines} lines (agent-skill guidance: keep SKILL.md under 500; move detail to references)", warn=True)

    files = {"SKILL.md": True}
    for rel in ("uts-package-mapping.json", "scripts/resolve_uts.py", "scripts/audit_translation.py",
                "scripts/scan_constructs.py"):
        files[rel] = (d / rel).is_file()
    check(checks, "L-mapping", "`uts-package-mapping.json`: ...", files["uts-package-mapping.json"], "present"
          if files["uts-package-mapping.json"] else "missing")
    check(checks, "L-resolver", "`resolve_uts.py`: ...", files["scripts/resolve_uts.py"],
          "present" if files["scripts/resolve_uts.py"] else "missing")
    check(checks, "L-audit", "`audit_translation.py`: ...", files["scripts/audit_translation.py"],
          "present" if files["scripts/audit_translation.py"] else "missing")
    check(checks, "L-scanner", "Unmapped constructs stop and ask; corpus scanner in `scripts/` (SHOULD)",
          files["scripts/scan_constructs.py"], "present" if files["scripts/scan_constructs.py"] else "missing", warn=True)
    if files["scripts/resolve_uts.py"]:
        src = (d / "scripts/resolve_uts.py").read_text(encoding="utf-8", errors="replace")
        for cid, pattern, meaning in (("S-resolver-create", r"--create", "--create"),
                                      ("S-resolver-collision", r"(?i)collision", "collision detection"),
                                      ("S-resolver-harness", r"[\"']harness[\"']", "harness output"),
                                      ("S-resolver-guarded-json", r"except\s*(\(?[^:\n]*(JSONDecodeError|ValueError|Exception))",
                                        "a guarded mapping load (no traceback on a malformed mapping)"),
                                      ("S-resolver-notes-error", r"(?i)notes_not_found|notes.*not.*(found|exist)",
                                        "an error for a missing notes file")):
            check(checks, cid, "`resolve_uts.py`: ...", bool(re.search(pattern, src)),
                  meaning + (" found" if re.search(pattern, src) else " not found"))
    if files["scripts/audit_translation.py"]:
        src = (d / "scripts/audit_translation.py").read_text(encoding="utf-8", errors="replace")
        for cid, pattern, meaning in (("S-audit-duplicate", r"(?i)duplicate", "duplicate-ID detection"),
                                      ("S-audit-orphan", r"(?i)orphan", "orphan-ID detection"),
                                      ("S-audit-unverifiable", r"(?i)notVerifiable|not.verifiable|unverifiable",
                                        "unverifiable-spec reporting"),
                                      ("S-audit-pseudo-only", r"(?m)^[^#\n]*re\.compile\([^\n]*```[^\n]*pseudo",
                                        "a fence regex that selects ```pseudo blocks (not every fenced block)")):
            check(checks, cid, "`audit_translation.py`: ...", bool(re.search(pattern, src)),
                  meaning + (" found" if re.search(pattern, src) else " not found"))

    mapping, modules, notes, harness = None, {}, {}, None
    if files["uts-package-mapping.json"]:
        try:
            mapping = json.loads((d / "uts-package-mapping.json").read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            check(checks, "M-valid-json", "`uts-package-mapping.json`: ...", False, f"invalid JSON: {exc}")
    if isinstance(mapping, dict):
        packages = mapping.get("packages") if isinstance(mapping.get("packages"), dict) else {}
        for module, entry in packages.items():
            if not isinstance(entry, dict):
                continue
            modules[module] = {t: entry.get(t) for t in ("unit", "integration", "proxy") if t in entry}
            for key in ("unready", "unsupported", "capabilityInapplicable", "extraTests", "notApplicable",
                        "notApplicableSpecs"):
                if entry.get(key):
                    modules[module][key] = entry[key]
            if entry.get("notes"):
                note = d / entry["notes"]
                size = note.stat().st_size if note.is_file() else None
                head = note.read_text(encoding="utf-8", errors="replace")[:2000] if note.is_file() else ""
                notes[module] = {"path": entry["notes"], "exists": note.is_file(), "bytes": size,
                                  "placeholder": bool(re.search(r"(?i)placeholder|not yet authored", head))}
        harness = mapping.get("harness")
        check(checks, "M-harness", "`uts-package-mapping.json`: ... `harness` entry", isinstance(harness, dict),
              "harness entry present" if isinstance(harness, dict) else "no harness entry (guide 3.2 MUST)")
        for module in ("rest", "realtime", "objects"):
            check(checks, f"M-module-{module}", "`uts-package-mapping.json`: ...", module in modules,
                  f"{module} {'mapped' if module in modules else 'not mapped'}", warn=True)
        missing_notes = [m for m, n in notes.items() if not n["exists"]]
        check(checks, "M-notes-exist", "Module notes for every diverging module ...", not missing_notes,
              "every declared notes file exists" if not missing_notes else f"declared but missing: {missing_notes}")
        check(checks, "M-objects-notes", "Module notes for every diverging module ...",
              "objects" in notes and notes["objects"]["exists"] and not notes["objects"]["placeholder"],
              f"objects notes: {notes.get('objects')}", warn=True)
    other_notes = sorted(p.name for p in (d / "references").glob("*-mapping.md")) if (d / "references").is_dir() else []

    harness_info = None
    if isinstance(harness, dict):
        readme = repo / str(harness.get("readme", ""))
        tiers = harness.get("tiers") if isinstance(harness.get("tiers"), dict) else {}
        harness_info = {
            "root": harness.get("root"), "rootExists": bool(harness.get("root")) and (repo / harness["root"]).exists(),
            "readme": harness.get("readme"), "readmeExists": readme.is_file(),
            "knownGaps": readme.is_file() and bool(re.search(r"(?im)^#+\s*known gaps",
                                                              readme.read_text(encoding="utf-8", errors="replace"))),
            "tiers": {t: {"tests": (v or {}).get("tests") if isinstance(v, dict) else None} for t, v in tiers.items()},
        }
        check(checks, "H-readme-known-gaps", "Harness README with a Known gaps section (MUST)",
              harness_info["knownGaps"], f"README {harness.get('readme')}: Known gaps "
              + ("found" if harness_info["knownGaps"] else "not found"))
    else:
        harness_info = find_harness(repo)
        readmes = harness_info["readmes"]
        gaps = [r for r in readmes if r["knownGaps"]]
        check(checks, "H-readme-known-gaps", "Harness README with a Known gaps section (MUST)", bool(gaps),
              "no harness entry; candidate harness READMEs: "
              + (", ".join(f"{r['path']} (Known gaps {'found' if r['knownGaps'] else 'not found'})" for r in readmes)
                  or "none found"), warn=not readmes)
    if harness_info:
        for r in ([harness_info["readme"]] if harness_info.get("readmeExists") else []) + \
                [x["path"] for x in harness_info.get("readmes", [])]:
            defect_sources[r] = (repo / r).read_text(encoding="utf-8", errors="replace")
        check(checks, "H-smoke-self-tests", "Harness smoke tests per tier and helper self-tests ... (MUST)",
              bool(harness_info.get("smokeOrSelfTestFiles")),
              f"smoke/self-test files: {harness_info.get('smokeOrSelfTestFiles') or 'none found by name'}; "
              f"CI lines: {harness_info.get('ciLines') or 'none'}")
    for cid, item, pattern, meaning in BODY_DEFECTS:
        per_file = {k: len(re.findall(pattern, v)) for k, v in defect_sources.items()}
        per_file = {k: v for k, v in per_file.items() if v}
        check(checks, cid, item, not per_file,
              "none" if not per_file else f"{meaning}: " + ", ".join(f"{k} ×{v}" for k, v in per_file.items()))

    codex = [i for i in installs if i["path"].startswith(".agents/")]
    claude = [i for i in installs if i["path"].startswith(".claude/")]
    for other in find_copies(repo, real, installs):
        check(checks, "I-copy-in-sync", "Installed for both tools from one source ... (SHOULD)", other["identical"],
              f"{other['path']} is a separate copy, " + ("identical" if other["identical"] else
                                                          f"differs: {other['differences'][:5]}"))
    check(checks, "I-both-tools", "Installed for both tools from one source ... (SHOULD)", bool(codex and claude),
          f"installs: {[i['path'] for i in installs]}", warn=True)

    records = read_records(pathlib.Path(RECORDS_DIR)) if RECORDS_DIR else read_records(d / "generation")
    mprof = mapping_profile(modules)
    profile = merge_profile(records, mprof)
    if records:
        records["capabilityProfile"] = profile
    generated_by = unquote(meta.get("generated-by", ""))[0] if isinstance(meta.get("generated-by"), str) else ""
    if records and records["creatorRecords"]:
        origin = "creator-records"
    elif generated_by.startswith("uts-to-lang-skill-creator"):
        origin = "creator-metadata"
    else:
        origin = "unknown"
    lang = re.sub(r"^uts-to-", "", name or dir_name).lower()
    exts = LANG_EXT.get(lang)
    return {
        "realPath": real, "installs": installs, "origin": origin, "generatedBy": generated_by or None,
        "records": records, "capabilityProfile": profile, "language": lang,
        "languageMatchesRepo": None if exts is None else bool(exts & set(REPO_EXT_COUNTS)),
        "frontmatter": {"fields": sorted(fields), "name": name, "descriptionLength": len(desc),
                        "allowedTools": tools, "metadata": meta},
        "skillMdLines": lines,
        "headings": re.findall(r"(?m)^#{1,3} .+$", body)[:80],
        "files": files,
        "references": sorted(p.relative_to(d).as_posix() for p in d.rglob("*") if p.is_file()
                              and "__pycache__" not in p.parts),
        "mapping": {"modules": modules, "notes": notes, "otherNotesFiles": other_notes,
                    "testRoot": mapping.get("testRoot") if isinstance(mapping, dict) else None},
        "harness": harness_info,
        "checks": checks,
        "summary": dict(collections.Counter(c["status"] for c in checks)),
    }


def derived_tests(repo):
    listed = git_lines(repo, "ls-files", "-co", "--exclude-standard", "-z")
    if listed is None:
        listed = [str(p.relative_to(repo)) for p in repo.rglob("*") if p.is_file()]
    per_dir, styles, shas, no_sha, deviations, tagged_files = (collections.Counter(), collections.Counter(),
                                                                collections.Counter(), [], [], 0)
    unpinned, other_records, by_mt, layouts = 0, [], collections.Counter(), collections.Counter()
    for rel in listed:
        parts = rel.split("/")
        if any(p in EXCLUDED_DIRS for p in parts[:-1]):
            continue
        if parts[-1] == "deviations.md":
            deviations.append(rel)
            continue
        if rel.endswith(".md") and re.search(r"(?i)(deviation|spec_?issue|spec-issue)", parts[-1]):
            other_records.append(rel)
            continue
        if pathlib.PurePosixPath(rel).suffix not in SOURCE_EXT:
            continue
        try:
            text = (repo / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "UTS" not in text:
            continue
        tags = 0
        for line in text.splitlines():
            m = TAG.match(line)
            if m:
                tags += 1
                tag_id = next(g for g in m.groups()[1:] if g)
                mt = re.match(r"([a-z]+)/([a-z]+)/", tag_id)
                by_mt[f"{mt.group(1)}/{mt.group(2)}" if mt else "other"] += 1
                styles[f"{m.group(1)} UTS:" if m.group(2) else "@UTS"] += 1
        if not tags:
            continue
        tagged_files += 1
        layouts["dedicated" if any(p.lower() == "uts" for p in parts[:-1]) else "nativeSuite"] += 1
        per_dir["/".join(parts[:-1])] += tags
        head_lines = []
        for line in text.splitlines()[:80]:
            if re.match(r"\s*(@Test|@Suite|\[Fact|\[Test|def test_|func test|class |public class |struct |describe\()", line):
                break
            head_lines.append(line)
        header = "\n".join(head_lines)
        found = HEADER_SHA.findall(header)
        if found:
            shas.update(found[:1])
        else:
            no_sha.append(rel)
            unpinned += 1 if HEADER_UNPINNED.search(header) else 0
    return {
        "taggedFiles": tagged_files, "tags": sum(per_dir.values()),
        "tagsByDirectory": dict(per_dir.most_common(40)), "tagStyles": dict(styles),
        "headerShas": dict(shas.most_common(20)), "filesWithoutHeaderSha": no_sha[:40],
        "filesWithoutHeaderShaCount": len(no_sha), "headersLinkingMain": unpinned, "deviationsFiles": deviations,
        "otherDeviationLikeRecords": other_records[:20],
        "byModuleTier": dict(by_mt.most_common()),
        "layout": (next(iter(layouts)) if len(layouts) == 1 else ("mixed" if layouts else None)),
    }


HARNESS_SYMBOL = re.compile(r"\b(MockWebSocket|MockHttpClient|SandboxApp|ProxyManager|ProxySession)\b")
SMOKE_NAME = re.compile(r"(?i)(smoke|selftest|self_test|self-test)")


def find_harness(repo):
    """Without a mapping `harness` entry: candidate harness directories, READMEs, smoke/self-test files, CI lines."""
    listed = git_lines(repo, "ls-files", "-co", "--exclude-standard", "-z") or []
    dirs = collections.Counter()
    for rel in listed:
        if pathlib.PurePosixPath(rel).suffix not in SOURCE_EXT or any(p in EXCLUDED_DIRS for p in rel.split("/")[:-1]):
            continue
        try:
            text = (repo / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if re.search(r"\b(class|struct|object|interface|protocol|def|func|fun)\s+(MockWebSocket|MockHttpClient|"
                      r"SandboxApp|ProxyManager|ProxySession)\b", text):
            dirs[rel.rsplit("/", 1)[0] if "/" in rel else "."] += 1
    readmes = []
    for d in dirs:
        parts = d.split("/")
        for i in range(len(parts), 0, -1):
            cand = "/".join(parts[:i]) + "/README.md"
            if (repo / cand).is_file():
                if cand not in [r["path"] for r in readmes]:
                    text = (repo / cand).read_text(encoding="utf-8", errors="replace")
                    readmes.append({"path": cand, "knownGaps": bool(re.search(r"(?im)^#+\s*known gaps", text))})
                break
    smoke = [f for f in listed if SMOKE_NAME.search(f.rsplit("/", 1)[-1])
              and pathlib.PurePosixPath(f).suffix in SOURCE_EXT][:20]
    ci = []
    for f in listed:
        if f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml")):
            for n, line in enumerate((repo / f).read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if re.search(r"(?i)\buts\b|smoke|self-?test", line):
                    ci.append(f"{f}:{n}: {line.strip()[:100]}")
    return {"fromMapping": False, "candidateDirs": dict(dirs.most_common(10)), "readmes": readmes,
            "smokeOrSelfTestFiles": smoke, "ciLines": ci[:20]}


def find_copies(repo, real, installs):
    """Same-named skill directories in other tool locations that are copies, not symlinks to this one."""
    real = pathlib.Path(real)
    seen = {str(repo / i["path"]) for i in installs}
    out = []
    for root in SKILL_ROOTS:
        cand = repo / root / real.name
        if str(cand) in seen or not cand.is_dir() or cand.resolve() == real:
            continue
        cmp = filecmp.dircmp(str(real), str(cand), ignore=["__pycache__", "generation"])
        diffs = cmp.diff_files + cmp.left_only + cmp.right_only
        stack = list(cmp.subdirs.values())
        while stack:
            c = stack.pop()
            diffs += c.diff_files + c.left_only + c.right_only
            stack += list(c.subdirs.values())
        out.append({"path": f"{root}/{real.name}", "identical": not diffs, "differences": diffs})
    return out


def mapped_target_dirs(skills):
    dirs = set()
    for s in skills:
        root = s["mapping"].get("testRoot")
        for tiers in s["mapping"]["modules"].values():
            for t in ("unit", "integration", "proxy"):
                if isinstance(tiers.get(t), str):
                    dirs.add(f"{root.rstrip('/')}/{tiers[t]}" if root else tiers[t])
    return dirs


def user_level_installs():
    """uts-to-* skills installed for the user (reported only: they apply to every repo)."""
    found = []
    for base in ("~/.claude/skills", "~/.agents/skills", "~/.codex/skills"):
        root = pathlib.Path(base).expanduser()
        if root.is_dir():
            found += [f"{base}/{p.name}" + (" (symlink)" if p.is_symlink() else "")
                      for p in sorted(root.glob("uts-to-*")) if p.name != SELF]
    return found


def main(argv):
    global RECORDS_DIR
    if "--records" in argv:
        i = argv.index("--records")
        RECORDS_DIR = argv[i + 1] if i + 1 < len(argv) else None
        argv = argv[:i] + argv[i + 2:]
    if len(argv) not in (2, 3) or not pathlib.Path(argv[1]).is_dir():
        print("usage: inspect_existing_skill.py <repo> [<skill-dir>] [--records <dir>]", file=sys.stderr)
        return 2
    skill_arg = argv[2] if len(argv) == 3 else None
    repo = pathlib.Path(argv[1]).expanduser().resolve()
    try:
        for f in git_lines(repo, "ls-files", "-z") or []:
            ext = pathlib.PurePosixPath(f).suffix
            if ext in LANG_NAMES:
                REPO_EXT_COUNTS[ext] = REPO_EXT_COUNTS.get(ext, 0) + 1
        groups = find_skills(repo, skill_arg)
        head = git_lines(repo, "rev-parse", "HEAD")
        skills = [inspect_skill(repo, real, installs) for real, installs in groups.items()]
        named = str(named_path(repo, skill_arg).resolve()) if skill_arg else None
        for sk in skills:  # orient.py --skill-dir classifies only the named skill
            sk["named"] = named is not None and sk["realPath"] == named
        records = set()
        for real in groups:
            for p in pathlib.Path(real).glob("generation/*.md"):
                try:
                    records.add(str(p.relative_to(repo)))
                except ValueError:
                    records.add(str(p))
        listed = git_lines(repo, "ls-files", "-co", "--exclude-standard", "-z") or []
        records.update(f for f in listed if f.endswith(("/design-record.md", "/skill-gap-audit.md"))
                        and "uts-to-lang-skill-creator/assets/templates/" not in f)
        orphans = []
        for root in (".claude/skills", ".agents/skills", ".codex/skills", ".cursor/skills"):
            for dr in sorted((repo / root).glob("*/generation/design-record.md")) if (repo / root).is_dir() else []:
                if not (dr.parent.parent / "SKILL.md").is_file():
                    rec = read_records(dr.parent)
                    if rec:
                        rec["dir"] = str(dr.parent.relative_to(repo))
                        orphans.append(rec)
                        records.add(str(dr.relative_to(repo)))
        working_records = sorted(records)
        other_skills = sorted({p.name for root in SKILL_ROOTS if (repo / root).is_dir()
                                for p in (repo / root).iterdir() if p.is_dir() and not p.name.startswith("uts-to-")})
        derived = derived_tests(repo)
        mapped_dirs = mapped_target_dirs(skills)
        derived["tagsOutsideMappedTiers"] = {d: n for d, n in derived["tagsByDirectory"].items()
                                              if mapped_dirs and not any(d == m or d.startswith(m + "/")
                                                                        for m in mapped_dirs)}
        result = {
            "ok": True, "repo": str(repo), "head": head[0] if head else None,
            "skills": skills, "namedSkill": named,
            "workingRecords": working_records,
            "brokenInstalls": BROKEN,
            "orphanRecords": orphans,
            "otherRepoSkills": other_skills,
            "repoLanguages": {LANG_NAMES[e]: n for e, n in sorted(REPO_EXT_COUNTS.items(), key=lambda x: -x[1])
                              if e in LANG_NAMES},
            "harnessCandidates": None if skills else find_harness(repo),
            "userLevelInstalls": user_level_installs(),
            "derivedTests": derived,
            "note": "Regex checks only: a pass is a pattern hit, not a review. Confirm each gap-audit row by reading "
                    "the files (section 11).",
        }
        result["found"] = {"skill": bool(result["skills"]), "derivedTests": bool(result["derivedTests"]["tags"]),
                            "workingRecords": bool(working_records)}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:  # never crash: report a structured error
        print(json.dumps({"ok": False, "code": "INSPECT_ERROR", "message": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
