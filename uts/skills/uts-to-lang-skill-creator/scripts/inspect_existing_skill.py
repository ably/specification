#!/usr/bin/env python3
"""Static inventory of an existing uts-to-* skill, its UTS infra and its UTS-derived tests.

Usage: inspect_existing_skill.py <repo> [<skill-dir>] [--records <dir>]

A read-only first pass for STOP-13 and the gap audit. It finds uts-to-* skills
in the agent skill directories (detect_liveobjects.SKILL_ROOTS) and any other
SKILL.md whose directory or `name:` starts with uts-to-, and runs checks keyed
to acceptance-checklist items, mostly regex (R-spec-sync compares a copied
script by hash): a "pass" is a pattern hit, not a review.
`--records <dir>` reads the working records from <dir> instead of
<skill>/generation/ (for the named <skill-dir> only, when one is given). It
never runs the skill's scripts and never writes.

Prints one JSON object: `ok`, `repo`, `head`, `skills` (per skill: installs,
origin, records (with the acceptance checklist's progress, `checklist`), `capabilityProfile`, language, frontmatter, files, mapping,
infra (with `selfTestCandidates` and `ciSources`), checks, summary), `namedSkill`, `workingRecords`, `brokenInstalls`,
`orphanRecords`, `otherRepoSkills`, `repoLanguages`, `infraCandidates`,
`userLevelInstalls`, `derivedTests`, `note` and `found`. Exit 0 on success; 1
with {"ok": false} on an error (INSPECT_ERROR); 2 on a usage error.

Rules: references/orient.md 13.3 (origin, S4), 13.8 (the recorded capability
profile); references/upgrade-existing-skill.md 11.2 (the gap audit).
"""
import collections, filecmp, hashlib, importlib.util, json, os, pathlib, re, subprocess, sys

_spec = importlib.util.spec_from_file_location("detect_liveobjects",
                                                pathlib.Path(__file__).resolve().parent / "detect_liveobjects.py")
lo = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lo)

HERE = pathlib.Path(__file__).resolve().parent
SKILL_ROOTS = lo.SKILL_ROOTS  # one list for every script
SELF = "uts-to-lang-skill-creator"
NON_PORTABLE = ["argument-hint", "model", "disable-model-invocation", "user-invocable", "when_to_use", "context",
                "agent", "hooks", "effort", "paths", "shell"]
SOURCE_EXT = lo.SOURCE_EXT  # one list for every script
EXCLUDED_DIRS = {".git", "node_modules", "vendor", "Pods", "Carthage", ".build", "build", "dist", "out", "target",
                  "bin", "obj", "DerivedData", ".gradle", "__pycache__", ".venv", "venv", ".claude", ".agents",
                  ".codex", ".cursor"}
TAG = re.compile(r"^\s*(?:(//|#|--)\s*UTS:\s*(\S+)|/\*\*?\s*@UTS:?\s+(\S+)|(?:\*\s*)?@UTS:?\s+(\S+))")
HEADER_SHA = re.compile(r"ably/specification(?:@|/blob/|/tree/)([0-9a-f]{7,40})\b")
HEADER_UNPINNED = re.compile(r"ably/specification/(blob|tree)/main/")

# (id, acceptance-checklist item it informs, regex over SKILL.md body, what a hit means)
BODY_CHECKS = [
    ("B-infra-reference", "SKILL.md: usage guard ... 3.4 outline incl. the Infra reference",
      r"(?im)^#+\s.*(?:infra|harness) reference", "an Infra (formerly Harness) reference heading"),
    ("B-preflight", "Steps 0 and A–F: the four questions and the infra preflight (stop on red)",
      r"(?i)preflight|step\s+F\b", "an infra preflight (step F)"),
    ("B-resync", "Re-sync mode; fix the cause, then regenerate", r"(?i)--resync|re-sync|resync", "a re-sync mode"),
    ("B-final-report", "Final report format", r"(?i)final report", "a final report"),
    ("B-lint", "Compile (or collect), lint, CI-strict compile, filtered run", r"(?i)\blint", "a lint step"),
    ("B-run-deviations", "Three end states; runtime skip and fail-fast idioms; `RUN_DEVIATIONS` command",
      r"RUN_DEVIATIONS", "the RUN_DEVIATIONS reproduction command"),
    ("B-deviations-deferred", "`deviations.md` location; format deferred; written at the right time",
      r"writing-derived-tests\.md", "a link to writing-derived-tests.md"),
    ("B-model", "Skill and UTS infra created on an Opus-class model (MUST); model stated for runs ...",
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
    ("X-fetch-main", "Required reading incl. features specs, from the same clone, synced first",
      r"(?i)(raw\.githubusercontent\.com/ably/specification|github\.com/ably/specification/(blob|tree)/main|"
      r"gh\s+api\b[^\n]*ably/specification|api\.github\.com/repos/ably/specification|"
      r"repos/ably/specification/contents|fetch first)",
      "fetches docs or specs from GitHub instead of the local clone"),
]
UNPINNED = re.compile(r"(?i)gh\s+api|api\.github\.com|/contents|/(blob|tree)/main|specification/(refs/heads/)?main/")
# A usage guard (guide 3.3 MUST): a usage line, and the skill never guesses a module: either a stop when the
# argument is missing (the older form), or, with the optional argument, a question asking which module.
USAGE_LINE = re.compile(r"(?i)\busage:|usage line")
USAGE_STOP = re.compile(r"(?i)(\bno\b|missing|empty|blank|without)[^\n]{0,80}\bstop|\bstop[^\n]{0,60}"
                        r"(no|missing|empty|without)\b[^\n]{0,20}(argument|module|path)")
MODULE_QUESTION = re.compile(
    r"(?i)\bask(s|ing)?\b[^\n]{0,40}\bwhich (uts )?module|never guess(es)?\b[^\n]{0,20}\bmodule"
    r"|module (question|selection|listing)|--list-modules")
# The UTS infra's tier directories (guide 2.2, MUST): `<root>/unit`, `<root>/integration`, `<root>/integration/proxy`.
TIER_DIRS = {"unit": ("unit",), "integration": ("integration",), "proxy": ("integration", "proxy")}
TEST_NAME = re.compile(r"(?i)(tests?|spec)\.[a-z]+$|^test_|_test\.[a-z]+$")
TYPE_DECL = re.compile(r"\b(?:class|struct|interface|protocol|object|enum|record|type)\s+([A-Z][A-Za-z0-9_]{3,})")
CI_SCRIPT = re.compile(r"(?:^|[\s\"'=(])(\.{0,2}/?[\w./-]+\.(?:sh|bash|ps1|cake|py|rb|js|mjs|mk|gradle|kts|bat|cmd))\b")
# Build tools named without a file: the entrypoint each reads by default (`make -C dir` / `-f file` respected).
CI_TOOL = re.compile(r"(?:^|[\s;&|(`\"'])(make|gmake|rake|cake|dotnet\s+cake)(?=[\s\"';&|)`]|$)([^\n;&|)]*)")
CI_PROSE = re.compile(r"^\s*(#|-?\s*name:)")  # comments and step names: "make sure ..." is not a command
TOOL_FILES = {"make": ["GNUmakefile", "makefile", "Makefile"], "gmake": ["GNUmakefile", "makefile", "Makefile"],
              "rake": ["Rakefile", "rakefile", "Rakefile.rb"], "cake": ["build.cake"]}


def git_lines(repo, *args):
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    return [l for l in out.stdout.decode("utf-8", "replace").split("\0" if "-z" in args else "\n") if l] \
        if out.returncode == 0 else None


def frontmatter(text):
    """Return (fields, body). A small YAML subset: top-level keys and one nested map."""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end < 0:
        return None, text
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
    return fields, text[end + 4:]


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1], True
    return value, False


def digest(path):
    """sha256 of a text file with line endings normalised (a Windows copy compares equal)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def check(checks, cid, item, ok, evidence, warn=False):
    status = "pass" if ok else ("warn" if warn else "fail")
    checks.append({"id": cid, "item": item, "status": status, "evidence": evidence})


BROKEN = []
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
        if re.match(r"[a-z-]+\s*:?\s*<", low):  # a template placeholder not filled in yet: no value
            continue
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


CHECKLIST_HEADER = re.compile(r"^\|\s*Guide §13 item\s*\|")
PLACEHOLDER = re.compile(r"^<[^>]*>$|^(…|\.\.\.|-|—)?$")


def table_cells(line):
    """The cells of a Markdown table row, split at `|` outside code spans and not escaped."""
    cells, cur, code, i = [], "", False, 0
    body = line.strip()
    body = body[1:] if body.startswith("|") else body
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body) and body[i + 1] == "|":
            cur += "|"
            i += 2
            continue
        if ch == "`":
            code = not code
        if ch == "|" and not code:
            cells.append(cur.strip())
            cur = ""
        else:
            cur += ch
        i += 1
    if cur.strip():
        cells.append(cur.strip())
    return cells


def status_kind(status, evidence):
    """(kind, reason) of an acceptance-checklist Status cell: done, static ("✓ static; behaviour at first
    translation"), fail (✗), na, open (blank or "open"), or unknown. A ✗ or n/a reason may sit in the Evidence cell."""
    s = re.sub(r"\*\*|__", "", status or "").strip()
    low = s.lower()
    if not s or low in ("open", "?", "todo", "-", "—") or PLACEHOLDER.match(s):
        return "open", ""
    if low.startswith("n/a") or re.match(r"na\b", low):
        return "na", re.sub(r"^n/?a\W*", "", s, flags=re.I).strip(" ()—:-") or (evidence or "")
    if s[0] in "✗✘❌" or re.match(r"(no|not met)\b", low):
        return "fail", s.lstrip("✗✘❌").strip(" ()—:-") or (evidence or "")
    if s[0] in "✓✔✅":
        return ("static" if re.match(r"[✓✔✅]\s*static", s) else "done"), ""
    return "unknown", ""


def parse_checklist(text):
    """The acceptance-checklist table in `text` (the working record, or the Final report's section), or None.

    Returns `rows` (group, item, verified, evidence, status, kind, reason), `evidenceColumn`, and the
    "Automated check" and "Independent verification" lines (None when absent or still the template's)."""
    lines = text.splitlines()
    start = next((i for i, l in enumerate(lines) if CHECKLIST_HEADER.match(l)), None)
    if start is None:
        return None
    header = [c.lower() for c in table_cells(lines[start])]
    col = {name: header.index(name) for name in ("verified in", "evidence", "status") if name in header}
    rows, group = [], None
    for line in lines[start + 1:]:
        if not line.lstrip().startswith("|"):
            break
        cells = table_cells(line)
        if not cells or set("".join(cells)) <= set("-: "):
            continue
        cells += [""] * (len(header) - len(cells))
        m = re.fullmatch(r"\*\*(.+?)\*\*", cells[0])
        if m and not any(cells[1:]):
            group = m.group(1)
            continue
        evidence = cells[col["evidence"]] if "evidence" in col else ""
        evidence = "" if PLACEHOLDER.match(evidence) else evidence
        status = cells[col["status"]] if "status" in col else cells[-1]
        kind, reason = status_kind(status, evidence)
        verified = cells[col["verified in"]] if "verified in" in col else ""
        rows.append(dict(
            group=group, item=cells[0], verified=verified, evidence=evidence, status=status, kind=kind, reason=reason))

    def line_after(label):
        m = re.search(r"(?im)^-?\s*" + label + r"[^:\n]*:\s*(.+)$", "\n".join(lines[:start]))
        value = m.group(1).strip() if m else None
        return None if value is None or value.startswith("<") or value.lower().startswith("not run yet") else value
    return {"rows": rows, "evidenceColumn": "evidence" in col, "automatedCheck": line_after("Automated check"),
            "verification": line_after("Independent verification")}


def checklist_counts(rows):
    """Counts per status. A ✓ (or ✓ static) without evidence, and a ✗ or n/a without a reason, count as open."""
    c = collections.Counter()
    for r in rows:
        k = r["kind"]
        if k in ("done", "static") and not r["evidence"]:
            c["noEvidence"] += 1
        elif k in ("fail", "na") and not r["reason"]:
            c["noReason"] += 1
        else:
            c[k if k != "unknown" else "open"] += 1
    counts = {k: c.get(k, 0) for k in ("done", "static", "fail", "na", "open", "noEvidence", "noReason")}
    counts["openTotal"] = counts["open"] + counts["noEvidence"] + counts["noReason"]
    counts["rows"] = len(rows)
    return counts


def read_checklist(rec_dir):
    """The acceptance checklist in rec_dir: acceptance-checklist.md, else the Final report's "Acceptance checklist"
    section (older records). None if neither has the table."""
    for name, section in (("acceptance-checklist.md", None), ("final-report.md", "Acceptance checklist")):
        p = rec_dir / name
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        if section:
            m = re.search(r"(?ms)^##\s*" + section + r"\s*$(.*?)(?=^##\s|\Z)", text)
            text = m.group(1) if m else ""
        parsed = parse_checklist(text)
        if parsed:
            parsed["file"] = name
            return parsed
    return None


def read_records(rec_dir):
    """Working records of this procedure in rec_dir, or None: origin evidence, run status, recorded SHAs, D-31."""
    dr = rec_dir / "design-record.md"
    if not dr.is_file():
        return None
    text = dr.read_text(encoding="utf-8", errors="replace")
    ours = bool(re.match(r"#\s*Design record:\s*uts-to-", text)) and "uts-to-lang-skill-creator version" in text
    status = re.search(r"(?im)^-?\s*Run status:\s*(.+)$", text)
    # "Spec clone: <sha> (…)", or "Spec clone: <kind> <path>; <sha> on <branch> …" (13.9)
    spec = re.search(r"(?im)^-?\s*Spec clone:\s*(?:[^;\n]*;\s*)?([0-9a-f]{7,40})\b", text)
    repo_sha = re.search(r"(?im)^-?\s*Repo:\s*([0-9a-f]{7,40})", text)
    caps = re.search(r"(?im)^-?\s*Capabilities \(D-31\):\s*(.+)$", text)
    profile = None
    if caps:
        profile = parse_d31(caps.group(1))
        if not any(profile[k] for k in ("rest", "realtime", "liveobjects", "side", "scopeKind", "scopeModules",
                                        "unsupported", "names", "unparsed")) and profile["capabilityInapplicable"] is None:
            profile = None  # the template line, not filled in yet: no recorded profile
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
            "finalReport": final, "capabilityProfile": profile, "checklist": checklist_progress(rec_dir)}


def checklist_progress(rec_dir):
    """The acceptance checklist's progress for Orient's re-entry (13.4, 13.6), or None without a checklist."""
    parsed = read_checklist(rec_dir)
    if not parsed:
        return None
    return {"file": parsed["file"], "evidenceColumn": parsed["evidenceColumn"], **checklist_counts(parsed["rows"]),
            "verification": parsed["verification"]}


LEGACY_UNSUPPORTED = re.compile(r"(?i)not applicable|rest-only|capability absent")


def mapping_profile(modules):
    """What the generated skill's mapping records about scope: `unsupported` modules and `capabilityInapplicable`
    entries (and the older keys `notApplicable`, `notApplicableSpecs`, and an `unready` reason saying "not
    applicable" or "REST-only"). None if the mapping says nothing about either. Any other module-level `unready`
    string (`objects` out of scope, D-28: guide 3.2) is readiness, not scope: it is never read as `unsupported`, so
    Orient never reports such a module as freed."""
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


TIERS = ("unit", "integration", "proxy")


INFRA_KEY, INFRA_ALIAS = "infra", "harness"  # the alias: the key's former name, read with a warning (guide 3.2)


def infra_key(mapping):
    """The mapping key holding the infra entry: `infra`, else the deprecated alias `harness`; None without either."""
    return next((k for k in (INFRA_KEY, INFRA_ALIAS) if isinstance(mapping, dict) and k in mapping), None)


def infra_entry(entry, key=INFRA_KEY):
    """The mapping's `infra` entry, read in the current shape {root, readme, testsRoot, testCommand} (guide 3.2)
    or an older one, accepted with a warning: under the alias key `harness` (in any shape), per-tier
    `tiers.<tier>.sources` and `tiers.<tier>.tests` (commands), and a string `tests` (read as testsRoot).
    Returns {older, warning, testsRoot, commands: {tier: command}}."""
    out = {"older": False, "warning": None, "testsRoot": None, "commands": {}}
    if not isinstance(entry, dict):
        return out
    old = [f"the key `{key}` (a deprecated alias of `{INFRA_KEY}`)"] if key != INFRA_KEY else []
    tests_root = entry.get("testsRoot")
    if not isinstance(tests_root, str) and isinstance(entry.get("tests"), str):
        tests_root = entry["tests"]
        old.append("a string `tests` (read as testsRoot)")
    out["testsRoot"] = tests_root if isinstance(tests_root, str) and tests_root else None
    command = entry.get("testCommand")
    per_tier = entry.get("tiers") if isinstance(entry.get("tiers"), dict) else {}
    for t in TIERS:
        if isinstance(command, str) and command:
            out["commands"][t] = command.replace("{tier}", t)
        v = per_tier.get(t)
        if isinstance(v, dict) and isinstance(v.get("tests"), str):
            out["commands"].setdefault(t, v["tests"])
    if per_tier:
        kinds = sorted({k for v in per_tier.values() if isinstance(v, dict) for k in v if k in ("sources", "tests")})
        old.append("per-tier `tiers.<tier>." + "/".join(kinds) + "`" if kinds else "per-tier `tiers`")
    if old:
        out["older"] = True
        out["warning"] = ("older mapping, accepted: " + "; ".join(old)
                          + f"; the current entry is `{INFRA_KEY}`: {{root, readme, testsRoot, testCommand}} (guide 3.2)")
    return out


OUT_OF_SCOPE = re.compile(r"(?i)out of scope")


def derivable_keys(mapping):
    """Mapping keys the resolver can derive, or that live elsewhere (guide 3.2): read, but reported for slimming."""
    found = [k for k in ("testProject", "namespaceRoot") if k in mapping]
    if INFRA_KEY in mapping and INFRA_ALIAS in mapping:
        found.append(f"both `{INFRA_KEY}` and the former key `{INFRA_ALIAS}` (`{INFRA_ALIAS}` is ignored: remove it)")
    entry = mapping.get(infra_key(mapping))
    if isinstance(entry, dict) and isinstance(entry.get("tiers"), dict) and any(
            isinstance(v, dict) and v.get("sources") for v in entry["tiers"].values()):
        found.append("per-tier source lists (derived from the tier layout)")
    packages = mapping.get("packages") if isinstance(mapping.get("packages"), dict) else {}
    for module, m in packages.items():
        if not isinstance(m, dict):
            continue
        if "whiteBox" in m:
            found.append(f"{module}.whiteBox (the notes hold the list)")
        paths = [t for t in TIERS if isinstance(m.get(t), str)]
        un = m.get("unready")
        whole = isinstance(un, str) or (isinstance(un, dict) and paths and set(paths) <= set(un)
                                        and all(OUT_OF_SCOPE.search(str(r)) for r in un.values()))
        if paths and whole and not m.get("extraTests"):
            found.append(f"{module}: tier paths beside an out-of-scope `unready` (one module-level reason is enough)")
    return found


def offered_tiers(modules):
    """Tiers some module offers: a target path, and neither the module nor that tier marked not ready."""
    out = set()
    for m in modules.values():
        un = m.get("unready")
        if isinstance(un, str) or (m.get("unsupported") and not m.get("extraTests")):
            continue
        out |= {t for t in TIERS if isinstance(m.get(t), str) and not (isinstance(un, dict) and t in un)}
    return [t for t in TIERS if t in out]


def tier_layout(repo, root, tiers):
    """Guide 2.2 (MUST): a directory per offered tier under the infra root, proxy nested under integration
    (`unit/`, `integration/`, `integration/proxy/`; names compared case-insensitively). Returns (ok, evidence, warn)."""
    base = repo / root if root else None
    if base is None or not base.is_dir():
        return False, f"root {root or '(none declared)'} not found: the tier layout can't be checked", True

    def child(d, name):
        return next((c for c in sorted(d.iterdir()) if c.is_dir() and c.name.lower() == name), None) if d else None

    found, missing = [], []
    for t in tiers or list(TIERS):
        d = base
        for part in TIER_DIRS[t]:
            d = child(d, part)
        (found if d else missing).append("/".join(TIER_DIRS[t]) + "/")
    top = [c.name + "/" for c in sorted(base.iterdir()) if c.is_dir()]
    evidence = (f"tier directories under {root}: {', '.join(found) or 'none'}"
                + (f"; missing: {', '.join(missing)}" if missing else "")
                + f"; top-level folders: {', '.join(top) or 'none'}")
    if missing and "integration/proxy/" in missing and child(base, "proxy"):
        evidence += ("; proxy/ is a sibling of integration/: nest it" if child(base, "integration") else
                      "; a top-level proxy/: nest it under integration/")
    if missing:
        evidence += " (guide 2.2 MUST: restructure by tier, gap-table row G-13)"
    return not missing, evidence, False


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


def display(path, repo):
    """`path` relative to the repo when it is inside it, else as given."""
    try:
        inside = os.path.commonpath([str(path), str(repo)]) == str(repo)
    except ValueError:
        inside = False
    return os.path.relpath(path, repo) if inside else str(path)


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
            rel = display(c, repo)
            if c.is_symlink() and not c.exists():
                BROKEN.append({"path": rel, "problem": f"dangling symlink to {os.readlink(c)}"})
            elif c.is_dir() and not (c / "generation" / "design-record.md").is_file():
                BROKEN.append({"path": rel, "problem": "uts-to-* directory without SKILL.md"})
            continue
        real = str(c.resolve())
        rel = display(c, repo)
        if rel not in [i["path"] for i in groups.get(real, [])]:  # the named <skill-dir> is also found by the scan
            groups.setdefault(real, []).append({"path": rel, "symlink": c.is_symlink()})
    return groups


def inspect_skill(repo, real, installs, records_dir=None):
    d = pathlib.Path(real)
    text = (d / "SKILL.md").read_text(encoding="utf-8", errors="replace")
    fields, body = frontmatter(text)
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
    has_usage, has_stop = bool(USAGE_LINE.search(body)), bool(USAGE_STOP.search(body))
    has_question = bool(MODULE_QUESTION.search(body))
    guarded = has_stop or has_question
    guards = [x for x, ok in (("a module question", has_question), ("a stop when the argument is missing", has_stop))
              if ok]
    check(checks, "B-usage-guard", "SKILL.md: usage guard that doesn't rely on `$ARGUMENTS` ...", has_usage and guarded,
          "a usage line " + ("found" if has_usage else "not found") + "; never guessing a module: "
          + (" and ".join(guards) or "not found"), warn=has_usage != guarded)
    # X-* checks read only the skill's own files (guide 13): SKILL.md, references/ and scripts/.
    defect_sources = {"SKILL.md": body}
    for sub in ("references", "scripts"):
        for ref in sorted(x for x in (d / sub).rglob("*") if x.is_file() and "__pycache__" not in x.parts
                          and x.suffix in (".md", ".py", ".sh", ".js", ".ts", ".rb", ".json")) \
                if (d / sub).is_dir() else []:
            defect_sources[ref.relative_to(d).as_posix()] = ref.read_text(encoding="utf-8", errors="replace")
    lines = text.count("\n") + 1
    check(checks, "B-length", "SKILL.md: ... 3.4 outline incl. the Infra reference", lines <= 500,
          f"{lines} lines (agent-skill guidance: keep SKILL.md under 500; move detail to references)", warn=True)

    files = {"SKILL.md": True}
    for rel in ("uts-package-mapping.json", "scripts/resolve_uts.py", "scripts/audit_translation.py",
                "scripts/scan_constructs.py", "scripts/ensure_spec_clone.py"):
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
                                      ("S-resolver-infra", r"[\"'](?:infra|harness)[\"']",
                                        "infra output (or its former name, harness)"),
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

    mapping, modules, notes, infra, ikey = None, {}, {}, None, None
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
        ikey = infra_key(mapping)
        infra = mapping.get(ikey) if ikey else None
        ientry = infra_entry(infra, ikey)
        check(checks, "M-infra", "`uts-package-mapping.json`: ... `infra` entry",
              isinstance(infra, dict) and not ientry["older"],
              (f"entry present under `{ikey}`" + (f"; {ientry['warning']}" if ientry["older"] else ""))
              if isinstance(infra, dict) else "no infra entry (guide 3.2 MUST)",
              warn=isinstance(infra, dict))
        derivable = derivable_keys(mapping)
        check(checks, "M-minimal", "`uts-package-mapping.json`: ... nothing the resolver can derive", not derivable,
              "only what the resolver can't derive" if not derivable else
              "read, but the resolver can derive or another file holds (slim at the next Upgrade/Fix, guide 3.2): "
              + "; ".join(derivable), warn=True)
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

    infra_info = None
    layout_item = "... organised by tier (MUST; names SHOULD) ..."
    if isinstance(infra, dict):
        readme = repo / str(infra.get("readme", ""))
        root = str(infra.get("root") or "").strip("/")
        tests_root = (ientry["testsRoot"] or "").strip("/") or None
        infra_info = {
            "mappingKey": ikey,
            "root": infra.get("root"), "rootExists": bool(root) and (repo / root).exists(),
            "readme": infra.get("readme"), "readmeExists": readme.is_file(),
            "knownGaps": readme.is_file() and bool(re.search(r"(?im)^#+\s*known gaps",
                                                              readme.read_text(encoding="utf-8", errors="replace"))),
            "testsRoot": ientry["testsRoot"], "testsRootExists": bool(tests_root) and (repo / tests_root).is_dir(),
            "shape": "older" if ientry["older"] else "current", "shapeWarning": ientry["warning"],
            "tiers": {t: {"tests": c} for t, c in ientry["commands"].items()},
        }
        if root:
            listed = git_lines(repo, "ls-files", "-co", "--exclude-standard", "-z") or []
            # Smoke tests and self-tests: in the infra-tests tree (testsRoot), or under the root (`<root>/tests/`);
            # for an older mapping without testsRoot, also beside the root (a separate tier tree, guide 2.2).
            roots = [root] + ([tests_root] if tests_root else [])
            parent = root.rsplit("/", 1)[0] if "/" in root else ""
            if not tests_root and parent:
                roots.append(parent)
            by_name = smoke_by_name(listed, roots)
            infra_info.update(smokeOrSelfTestFiles=by_name, smokeSearchRoots=roots,
                                selfTestCandidates=self_test_candidates(repo, listed, roots, by_name))
        check(checks, "H-readme-known-gaps", "Infra README with a Known gaps section (MUST)",
              infra_info["knownGaps"], f"README {infra.get('readme')}: Known gaps "
              + ("found" if infra_info["knownGaps"] else "not found"))
        ok, evidence, warn = tier_layout(repo, root, offered_tiers(modules))
        check(checks, "T-tier-layout", layout_item, ok, evidence, warn=warn)
    else:
        infra_info = find_infra(repo)
        readmes = infra_info["readmes"]
        gaps = [r for r in readmes if r["knownGaps"]]
        check(checks, "H-readme-known-gaps", "Infra README with a Known gaps section (MUST)", bool(gaps),
              "no infra entry; candidate infra READMEs: "
              + (", ".join(f"{r['path']} (Known gaps {'found' if r['knownGaps'] else 'not found'})" for r in readmes)
                  or "none found"), warn=not readmes)
        # The candidate root: the common ancestor of the directories declaring the core doubles and fixtures.
        cand_dirs = list(infra_info.get("candidateDirs") or {})
        cand = os.path.commonpath(cand_dirs).replace(os.sep, "/") if cand_dirs else None
        ok, evidence, _ = tier_layout(repo, cand, offered_tiers(modules)) if cand and cand != "." else (False, "", 0)
        check(checks, "T-tier-layout", layout_item, False,
              "no root declared in the mapping; candidate: " + (evidence or "none found")
              + (" (tier-shaped: declare it in the mapping)" if ok else ""), warn=True)
    if infra_info:
        by_name, cands = infra_info.get("smokeOrSelfTestFiles"), infra_info.get("selfTestCandidates")
        check(checks, "H-smoke-self-tests", "Infra smoke tests per tier and helper self-tests ... (MUST)",
              bool(by_name),
              f"smoke/self-test files: {by_name or 'none found by name'}"
              + (f"; {len(cands)} candidate(s) by location, read to confirm: {cands}" if cands else "")
              + f"; CI lines ({infra_info.get('ciSources') or 'workflow files only'}): "
              f"{infra_info.get('ciLines') or 'none'}", warn=not by_name and bool(cands))
    for cid, item, pattern, meaning in BODY_DEFECTS:
        per_file, unpinned = {}, 0
        for k, v in defect_sources.items():
            hits = list(re.finditer(pattern, v))
            if hits:
                per_file[k] = len(hits)
            if cid == "X-fetch-main":  # an API fetch without ?ref=, or a URL on main, reads the default branch
                for m in hits:
                    end = v.find("\n", m.end())
                    line = v[v.rfind("\n", 0, m.start()) + 1:end if end != -1 else len(v)]
                    unpinned += bool(UNPINNED.search(v[m.start():m.end() + 20])) and "ref=" not in line
        check(checks, cid, item, not per_file,
              "none" if not per_file else f"{meaning}: " + ", ".join(f"{k} ×{v}" for k, v in per_file.items())
              + (f" ({unpinned} unpinned: no ref=)" if unpinned else ""))

    ours, theirs = HERE / "ensure_spec_clone.py", d / "scripts" / "ensure_spec_clone.py"
    synced = theirs.is_file() and digest(theirs) == digest(ours)
    sync_state = ("matches the skill creator's copy" if synced else
                  "differs from the skill creator's copy: a change item (refresh it, D-32)" if theirs.is_file() else
                  "missing (guide 9.4 SHOULD, D-32)")
    check(checks, "R-spec-sync", "Required reading incl. features specs, from the same clone, synced first", synced,
          f"scripts/ensure_spec_clone.py {sync_state}", warn=True)
    codex = [i for i in installs if i["path"].startswith(".agents/")]
    claude = [i for i in installs if i["path"].startswith(".claude/")]
    for other in find_copies(repo, real, installs):
        check(checks, "I-copy-in-sync", "Installed for both tools from one source ... (SHOULD)", other["identical"],
              f"{other['path']} is a separate copy, " + ("identical" if other["identical"] else
                                                          f"differs: {other['differences'][:5]}"))
    check(checks, "I-both-tools", "Installed for both tools from one source ... (SHOULD)", bool(codex and claude),
          f"installs: {[i['path'] for i in installs]}", warn=True)

    records = read_records(records_dir) if records_dir else read_records(d / "generation")
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
        "infra": infra_info,
        "checks": checks,
        "summary": dict(collections.Counter(c["status"] for c in checks)),
    }


def derived_tests(repo):
    listed = git_lines(repo, "ls-files", "-co", "--exclude-standard", "-z")
    if listed is None:
        listed = sorted(p.relative_to(repo).as_posix() for p in repo.rglob("*") if p.is_file())
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


INFRA_DECL = re.compile(r"\b(class|struct|object|interface|protocol|def|func|fun)\s+(MockWebSocket|MockHttpClient|"
                          r"SandboxApp|ProxyManager|ProxySession)\b")
SMOKE_NAME = re.compile(r"(?i)(smoke|selftest|self_test|self-test)")


def find_infra(repo):
    """Without a mapping `infra` entry: candidate infra directories, READMEs, smoke/self-test files, CI lines."""
    listed = git_lines(repo, "ls-files", "-co", "--exclude-standard", "-z") or []
    dirs = collections.Counter()
    for rel in listed:
        if pathlib.PurePosixPath(rel).suffix not in SOURCE_EXT or any(p in EXCLUDED_DIRS for p in rel.split("/")[:-1]):
            continue
        try:
            text = (repo / rel).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if INFRA_DECL.search(text):
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
    smoke = smoke_by_name(listed)
    roots = [r["path"].rsplit("/", 1)[0] if "/" in r["path"] else "." for r in readmes]
    if not roots and dirs:
        roots = [os.path.commonpath(list(dirs)).replace(os.sep, "/")]
    ci, sources = ci_evidence(repo, listed)
    return {"fromMapping": False, "candidateDirs": dict(dirs.most_common(10)), "readmes": readmes,
            "smokeOrSelfTestFiles": smoke, "selfTestCandidates": self_test_candidates(repo, listed, roots, smoke),
            "ciLines": ci[:20], "ciSources": sources}


def smoke_by_name(listed, roots=None):
    """Source files named smoke or self-test (under roots, if given)."""
    return [f for f in listed if SMOKE_NAME.search(f.rsplit("/", 1)[-1]) and pathlib.PurePosixPath(f).suffix in
            SOURCE_EXT and (roots is None or any(under(f, r) for r in roots))][:20]


def under(path, root):
    return root in ("", ".") or path == root or path.startswith(root.rstrip("/") + "/")


def has_tag(text):
    return any(TAG.match(line) for line in text.splitlines())


def self_test_candidates(repo, listed, roots, by_name):
    """Untagged test files under the infra roots that use a type the infra declares: self-test candidates found
    by location, not by name (read them to confirm)."""
    files = [f for f in listed if pathlib.PurePosixPath(f).suffix in SOURCE_EXT and any(under(f, r) for r in roots)
            and not any(p in EXCLUDED_DIRS for p in f.split("/")[:-1])]
    texts = {}
    for f in files:
        try:
            texts[f] = (repo / f).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    texts = {f: t for f, t in texts.items() if not has_tag(t)}
    tests = [f for f in texts if TEST_NAME.search(f.rsplit("/", 1)[-1]) and f not in by_name]
    declared = {f: set(TYPE_DECL.findall(t)) for f, t in texts.items() if f not in tests}
    infra_types = set().union(*declared.values()) if declared else set()
    found = []
    for f in tests:
        own = set(TYPE_DECL.findall(texts[f]))
        names = infra_types - own
        if names and re.search(r"\b(" + "|".join(sorted(map(re.escape, names))) + r")\b", texts[f]):
            found.append(f)
    return found[:20]


def ci_evidence(repo, listed):
    """UTS, smoke and self-test lines in the CI workflows and in the scripts they call (followed to depth 3)."""
    tracked = set(listed)
    queue = [f for f in listed if f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml"))]
    seen, scripts, ci = set(queue), [], []
    depth = {f: 0 for f in queue}
    while queue:
        f = queue.pop(0)
        try:
            text = (repo / f).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if re.search(r"(?i)\buts\b|smoke|self-?test", line):
                ci.append(f"{f}:{n}: {line.strip()[:100]}")
        if depth[f] >= 3:
            continue
        base = f.rsplit("/", 1)[0] if "/" in f else ""
        refs = CI_SCRIPT.findall(text)
        commands = "\n".join(line for line in text.splitlines() if not CI_PROSE.match(line))
        for tool, opts in CI_TOOL.findall(commands):
            tool = tool.split()[-1]
            where = re.search(r"(?:^|(?<=\s))(?:-C\s*|--directory[= ])([\w./-]+)", opts)  # an option, not a target
            given = re.search(r"(?:^|(?<=\s))(?:-f\s*|--(?:make)?file[= ])([\w./-]+)", opts)
            folder = where.group(1).rstrip("/") + "/" if where else ""
            refs += [folder + given.group(1)] if given else [folder + name for name in TOOL_FILES[tool]]
        for ref in refs:
            ref = ref[2:] if ref.startswith("./") else ref
            for cand in (os.path.normpath(ref).replace(os.sep, "/"),
                        os.path.normpath(f"{base}/{ref}").replace(os.sep, "/") if base else None):
                if cand and cand in tracked and cand not in seen:
                    seen.add(cand)
                    depth[cand] = depth[f] + 1
                    scripts.append(cand)
                    queue.append(cand)
    return ci, ("workflow files only" if not scripts else
                f"workflow files and {len(scripts)} script(s) they call: {', '.join(scripts[:8])}"
                + (", …" if len(scripts) > 8 else ""))


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
    """Every tier target directory the mappings declare (a tagged test in a mirrored sub-directory of one is inside
    it). A module marked not ready as a whole has no tier paths (guide 3.2); an older mapping's dummy paths for it
    are counted too, which only widens what counts as inside."""
    dirs = set()
    for s in skills:
        root = s["mapping"].get("testRoot")
        for tiers in s["mapping"]["modules"].values():
            for t in TIERS:
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


USAGE = "usage: inspect_existing_skill.py <repo> [<skill-dir>] [--records <dir>]"


def usage_error(message):
    print(f"{USAGE}\ninspect_existing_skill.py: error: {message}", file=sys.stderr)
    return 2


def main(argv):
    if "-h" in argv[1:] or "--help" in argv[1:]:
        print(__doc__.strip())
        return 0
    args, records_arg = [], None
    it = iter(argv[1:])
    for a in it:
        if a == "--records":
            records_arg = next(it, "")
            if not records_arg or records_arg.startswith("-"):
                return usage_error(f"{a} needs a value")
        elif a.startswith("-"):
            return usage_error(f"unknown option {a}")
        else:
            args.append(a)
    if len(args) not in (1, 2):
        return usage_error(f"expected <repo> and an optional <skill-dir>, got {len(args)} arguments")
    repo = pathlib.Path(args[0]).expanduser()
    if not repo.is_dir():
        return usage_error(f"not a directory: {args[0]}")
    repo = repo.resolve()
    skill_arg = args[1] if len(args) == 2 else None
    records_dir = pathlib.Path(records_arg).expanduser() if records_arg else None
    try:
        for f in git_lines(repo, "ls-files", "-z") or []:
            ext = pathlib.PurePosixPath(f).suffix
            if ext in LANG_NAMES:
                REPO_EXT_COUNTS[ext] = REPO_EXT_COUNTS.get(ext, 0) + 1
        groups = find_skills(repo, skill_arg)
        head = git_lines(repo, "rev-parse", "HEAD")
        named = str(named_path(repo, skill_arg).resolve()) if skill_arg else None
        # --records belongs to the named skill when one is given, else to every skill found.
        skills = [inspect_skill(repo, real, installs, records_dir if named is None or real == named else None)
                  for real, installs in groups.items()]
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
        for root in SKILL_ROOTS:
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
            "infraCandidates": None if skills else find_infra(repo),
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
