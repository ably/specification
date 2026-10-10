#!/usr/bin/env python3
"""Look for LiveObjects (UTS module `objects`) API evidence in an SDK repository (STOP-14).

Usage: detect_liveobjects.py <repo> [--spec-clone PATH] [--include-submodules]

A read-only regex heuristic. Every name it searches for comes from the spec
clone, read at run time by spec_names.py, plus the earlier-revision and
prose-only names in assets/capability-names.json. Its output is evidence for
the user's decision, not the decision: read the files it lists.

Prints one JSON object: `ok`, `repo`, `head`, `listing`, `namesSource`,
`specClone`, `specRevision`, `namesFrom`, `dataFile`, `warnings`, `summary`,
`recommendation`, `scanned`, `excluded`, `evidence` (per category:
publicApi, legacyPublicApi, shared, internalApi, wireOnly, plus accessor,
pluginKey, packaging, missingPublicNames), `stubMarkers` and `note`. Exit 0 on
success; 1 with {"ok": false} on an error (DATA_FILE_ERROR, NOT_A_SPEC_CLONE,
REPO_IS_SPEC_CLONE, DETECT_ERROR); 2 on a usage error. Never touches the
network.

Rules: references/liveobjects-support.md 12.1 (categories, matching,
exclusions) and 12.2 (the recommendation).
"""
import collections, importlib.util, json, os, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("spec_names", HERE / "spec_names.py")
sn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sn)
CATEGORIES = ("publicApi", "legacyPublicApi", "shared", "internalApi", "wireOnly")

SOURCE_EXT = {".cs", ".fs", ".py", ".pyi", ".go", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".rb",
              ".dart", ".rs", ".java", ".kt", ".kts", ".swift", ".m", ".mm", ".h", ".php"}
MANIFEST_NAMES = {"Package.swift", "Cartfile", "build.gradle", "build.gradle.kts", "settings.gradle",
                  "settings.gradle.kts", "pom.xml", "package.json", "pyproject.toml", "setup.py", "setup.cfg",
                  "go.mod", "Cargo.toml", "Gemfile", "pubspec.yaml"}
MANIFEST_EXT = {".podspec", ".csproj", ".fsproj", ".sln", ".gemspec"}
NESTED_PACKAGE_MANIFESTS = {"go.mod", "package.json", "Cargo.toml", "pubspec.yaml", "pyproject.toml", "setup.py"}
# Always skipped (compared lowercased): vendored code, and agent skill directories (an existing skill's notes
# would be false positives).
ALWAYS_EXCLUDED = {".git", "node_modules", "vendor", "vendored", "pods", "carthage", "third_party", "third-party",
                    "deps", "external", "extern", "bower_components", ".yarn", "site-packages",
                    ".claude", ".agents", ".codex", ".cursor"}
# Where agent skills are installed in a repository: the one list every script uses.
SKILL_ROOTS = [".claude/skills", ".agents/skills", ".codex/skills", ".cursor/skills", ".github/skills", "skills"]
# Also skipped when the repo isn't a git repo (in a git repo, .gitignore already drops build output).
WALK_EXCLUDED = ALWAYS_EXCLUDED | {".build", "build", "dist", "out", "target", "bin", "obj", "deriveddata",
                                    ".gradle", "__pycache__", ".venv", "venv", ".tox", ".nox", ".mypy_cache",
                                    ".pytest_cache", ".dart_tool", "coverage", "testresults", "test-results",
                                    "test-output", ".idea", ".vscode", ".swiftpm"}
SPEC_CLONE_MARKERS = ("specifications/objects-features.md", "uts/docs/writing-uts-spec-translator-skills.md")
SELF_SENTINEL = "detect_liveobjects.py <repo>"
MAX_BYTES = 2 * 1024 * 1024
MAX_FILES_LISTED = 5

TEST_SEGMENT = re.compile(r"^(?:.*[._-])?(tests?|specs?|testing|__tests__|androidtest|testfixtures)(?:[._-].*)?$",
                          re.I)
TEST_SEGMENT_SUFFIX = re.compile(r"^[A-Za-z0-9_]*(Tests?|Testing|Specs?)$")  # case-sensitive: AblyTests, not latest
TEST_FILE = re.compile(r"(_test\.(go|py|dart|rb)|^test_.*\.py|\.(test|spec)\.[cm]?[jt]sx?"
                        r"|(Tests?|Specs?)\.(java|kt|swift|cs|m)|_spec\.rb)$")
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
COMMENT_LINE = re.compile(r"^\s*(//|#(?!(?:if|ifdef|ifndef|else|elif|endif|import|include|define|pragma|region|"
                          r"endregion)\b)|\*|/\*|--|<!--)")
# RTL27 use: a lowercase-initial channel-named receiver (so a class such as Django's Channel.objects manager doesn't
# match), or channels.get(...), reading .object / .objects / getObject(s)() / GetObject().
ACCESSOR_USE = re.compile(r"(?:\b(?:[a-z_]\w*Channel|channel)\w*|\bchannels\s*\.\s*get\s*\([^)]*\))\s*"
                          r"(?:\.|->|\?\.|!\.)\s*(?:[Gg]et_?)?([Oo]bjects?)\b(?!\s*=[^=])")


def accessor_decl(types):
    """RTL27 declaration: a member named object(s) / getObject(s) declared with the accessor's type (`types`, from the
    spec IDL: RealtimeChannel's `object: RealtimeObject`), singular or plural (the earlier RealtimeObjects)."""
    t = "(?:" + "|".join(sorted(map(re.escape, types), key=len, reverse=True)) + ")s?"
    return re.compile(
        rf"\b(?:[A-Z]{{1,4}})?{t}\b[\s?!>]*(?:\*\s*|\s+)(?:get\s+|get_?)?([Oo]bjects?)\b"
        rf"|\b(?:get_?)?([Oo]bjects?)\b\s*(?:\([^)]*\))?\s*(?::|->|=>)\s*(?:any\s+|some\s+|&\s*|[\"'])?"
        rf"(?:[A-Z]{{1,4}})?{t}\b"
        rf"|\bfunc\s*\([^)]*\)\s*(?:Get)?(Objects?)\s*\(\)\s*\(?\*?(?:[A-Z]{{1,4}})?{t}\b")


# Untyped declarations (a Ruby attr_reader, a JS getter) count only in a file named after the channel.
ACCESSOR_DECL_UNTYPED = re.compile(r"\battr_(?:reader|accessor)\s+:(objects?)\b"
                                    r"|^\s*(?:static\s+)?get\s+(objects?)\s*\(\)\s*\{")
PLUGIN_IDENT = re.compile(r"[A-Za-z0-9_]*(?:LiveObjects[A-Za-z0-9_]*Plugin|Plugin[A-Za-z0-9_]*LiveObjects)[A-Za-z0-9_]*")
PLUGIN_KEY = re.compile(r"\bPluginType\s*(?:\.|::)\s*(LiveObjects|Objects)\b"
                        r"|\b[Pp]lugins?\b.{0,40}?[\"'`:.](LiveObjects|Objects)\b")
PACKAGING = re.compile(r"live[-_ ]?objects", re.I)
DECL = re.compile(r"\b(class|struct|interface|protocol|enum|type|typealias|trait|record|object|def|func|fun|fn|module|"
                  r"var|let|val|const|property)\s+_*$|@(interface|protocol)\s+$")
PUBLIC_MOD = re.compile(r"\b(public|open|export|pub)\b(?!\s*\()")
NONPUBLIC_MOD = re.compile(r"\b(internal|private|fileprivate|protected)\b|\bpub\s*\((crate|super)\)")
PRIVATE_PATH = re.compile(r"(^|/)(internal|private|impl|[^/]*private[^/]*headers?)(/|$)", re.I)
STUB = re.compile(r"not[ _-]?(yet[ _-]?)?implemented|NotImplementedError|NotImplementedException|unimplemented!|"
                  r"todo!\(|UnimplementedError", re.I)
DEFAULT_PUBLIC_EXT = {".kt", ".kts", ".rb", ".py", ".pyi", ".dart"}


def snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def camel(constant, upper_first):
    parts = constant.lower().split("_")
    head = parts[0].capitalize() if upper_first else parts[0]
    return head + "".join(p.capitalize() for p in parts[1:])


def build_tables(names):
    """Exact table: identifier -> (category, spec name). Folded table: lowercased member names (any case).

    `names` is spec_names.load()["liveobjects"]. Legacy names that are internal now (LiveObject) are looked up as
    internal; a public declaration of one counts as legacy (see main)."""
    exact, folded = {}, {}
    legacy = names["legacyPublicApi"]
    internal = sorted(set(names["internalApi"]) | set(names["legacyNowInternal"]))
    for category, group in (("publicApi", names["publicApi"]), ("legacyPublicApi", legacy),
                            ("shared", names["shared"]), ("internalApi", internal), ("wireOnly", names["wireOnly"])):
        for name in group:
            exact.setdefault(name, (category, name))
            exact.setdefault(snake(name), (category, name))
            if name[0].islower():  # a member: GetRoot (C#, Go), CompactJSON (Go initialisms)
                folded.setdefault(name.lower(), (category, name))
    for category, constants in (("shared", names["sharedConstants"]), ("wireOnly", names["wireConstants"])):
        for constant in constants:
            for form in (constant, camel(constant, True), camel(constant, False)):
                exact.setdefault(form, (category, constant))
    return exact, folded


def match_identifier(token, exact, folded):
    """Return ((category, name), how) with how in exact | underscored | folded | prefixed; or (None, None)."""
    stripped = token.lstrip("_")
    if stripped in exact:
        return exact[stripped], ("underscored" if stripped != token else "exact")
    if stripped.lower() in folded and stripped[:1].isupper():
        return folded[stripped.lower()], "folded"
    prefix = re.match(r"[A-Z]{1,4}(?=[A-Z][a-z])", stripped)
    if prefix:
        rest = stripped[prefix.end():]
        if rest in exact and exact[rest][1][0].isupper():
            return exact[rest], "prefixed"
    return None, None


def git_files(repo, *extra):
    out = subprocess.run(["git", "-C", str(repo), "ls-files", "-z", *extra], capture_output=True)
    if out.returncode != 0:
        return None
    return [f for f in out.stdout.decode("utf-8", "replace").split("\0") if f]


WALK_SKIPPED = set()


def walk_files(repo):
    files = []
    for root, dirs, names in os.walk(repo):
        WALK_SKIPPED.update(d.lower() for d in dirs if d.lower() in WALK_EXCLUDED)
        dirs[:] = [d for d in dirs if d.lower() not in WALK_EXCLUDED]
        files += [pathlib.Path(root, n).relative_to(repo).as_posix() for n in names]
    return sorted(files)  # os.walk order varies: keep the output deterministic


def submodule_paths(repo):
    out = subprocess.run(["git", "-C", str(repo), "config", "--file", ".gitmodules", "--get-regexp", r"\.path$"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [line.split(" ", 1)[1].strip() for line in out.stdout.splitlines() if " " in line]


def is_test(rel):
    parts = rel.split("/")
    return (any(TEST_SEGMENT.match(p) or TEST_SEGMENT_SUFFIX.match(p) for p in parts[:-1])
            or bool(TEST_FILE.search(parts[-1])))


def visibility(line, rel, ext, name, file_text):
    if NONPUBLIC_MOD.search(line) or PRIVATE_PATH.search(rel):
        return "nonPublic"
    if PUBLIC_MOD.search(line):
        return "public"
    if ext in DEFAULT_PUBLIC_EXT and not name.startswith("_"):
        return "public"
    if ext == ".go" and name[:1].isupper():
        return "public"
    if ext in (".h", ".js", ".mjs", ".cjs") and not name.startswith("_"):
        return "public"  # headers outside private paths; JS has no visibility keywords
    if ext in (".ts", ".tsx", ".mts", ".cts") and not name.startswith("_") and not re.search(r"#\w", line) \
            and re.match(r"\s+(readonly\s+|get\s+|static\s+)*\w", line) and re.search(r"\bexport\s+(class|interface)\b",
                                                                                        file_text):
        return "public"  # members of an exported TS class or interface are public by default
    if ext == ".swift" and re.search(r"\bpublic\s+extension\b", file_text):
        return "public"  # members of a public extension default to public
    return "nonPublic"


def new_bucket():
    return {"hits": 0, "nonTestHits": 0, "commentHits": 0, "untrackedHits": 0, "declarations": 0,
            "publicDeclarations": 0, "publicDeclaredAt": [], "files": []}


def add(bucket, rel, line_no, test, comment, untracked, declared=False, public_decl=False):
    bucket["hits"] += 1
    bucket["commentHits"] += 1 if comment else 0
    bucket["untrackedHits"] += 1 if untracked else 0
    bucket["nonTestHits"] += 0 if (test or comment) else 1
    bucket["declarations"] += 1 if declared else 0
    bucket["publicDeclarations"] += 1 if public_decl else 0
    tags = [t for t, on in (("test", test), ("comment", comment), ("untracked", untracked)) if on]
    entry = f"{rel}:{line_no}" + (f" ({', '.join(tags)})" if tags else "")
    if public_decl and len(bucket["publicDeclaredAt"]) < 3:
        bucket["publicDeclaredAt"].append(entry)
    if len(bucket["files"]) < MAX_FILES_LISTED and not any(f.split(":")[0] == rel for f in bucket["files"]):
        bucket["files"].append(entry)


def summarise(symbols):
    return {
        "distinctSymbols": len(symbols),
        "distinctNonTestSymbols": sum(1 for s in symbols.values() if s["nonTestHits"]),
        "distinctPublicDeclarations": sum(1 for s in symbols.values() if s["publicDeclarations"]),
        "hits": sum(s["hits"] for s in symbols.values()),
        "nonTestHits": sum(s["nonTestHits"] for s in symbols.values()),
        "commentHits": sum(s["commentHits"] for s in symbols.values()),
        "untrackedHits": sum(s["untrackedHits"] for s in symbols.values()),
        "symbols": dict(sorted(symbols.items())),
    }


def recommend(ev, stub_count):
    pub, legacy, internal, wire = (ev["publicApi"], ev["legacyPublicApi"], ev["internalApi"], ev["wireOnly"])
    accessor_src = ev["accessor"]["nonTestHits"]
    accessor_pub = ev["accessor"]["publicDeclarations"]
    packaging = bool(ev["packaging"]["manifests"] or ev["packaging"]["moduleDirs"] or ev["pluginKey"]["nonTestHits"])
    decl = pub["distinctPublicDeclarations"] + legacy["distinctPublicDeclarations"]
    refs = pub["distinctNonTestSymbols"] + legacy["distinctNonTestSymbols"]
    reasons = []
    if decl >= 2 or (decl >= 1 and (accessor_src or packaging)):
        answer, confidence = "yes", "high"
        reasons.append(f"{decl} spec public-API name(s) declared with public visibility in non-test source"
                        + (", plus the RTL27 channel accessor" if accessor_src else ""))
    elif accessor_pub or (accessor_src and refs) or (refs >= 2 and packaging):
        answer, confidence = "yes", "medium"
        reasons.append("the RTL27 channel accessor is declared, or used together with spec public-API names, or "
                        "several public-API names appear with LiveObjects packaging, in non-test source")
    elif refs or accessor_src or internal["nonTestHits"] or packaging or pub["hits"] or legacy["hits"]:
        answer, confidence = "unclear", "low"
        causes = []
        test_only = sorted(n for c in (pub, legacy) for n, b in c["symbols"].items()
                            if b["hits"] and not b["nonTestHits"])
        if test_only:
            causes.append(f"public-API names only in tests or comments ({', '.join(test_only[:5])})")
        if refs:
            causes.append(f"{refs} public-API name(s) used in source but not declared public there")
        if accessor_src and not refs:
            causes.append("a channel .object/.objects access with no other public-API name (could be unrelated)")
        if internal["nonTestHits"]:
            causes.append(f"{internal['distinctNonTestSymbols']} internal name(s) in source")
        if packaging:
            causes.append("LiveObjects packaging or plugin names")
        reasons.append("only weak evidence: " + "; ".join(causes) + ". Read the files, and ask whether the public "
                        "API lives elsewhere (another package or repo)")
    else:
        answer, confidence = "no", "high"
        reasons.append("no spec public-API, internal or packaging names in non-test source"
                        + (" (protocol-level object names only)" if wire["hits"] or ev["shared"]["hits"] else ""))
    if answer == "yes" and not refs and (wire["nonTestHits"] or ev["shared"]["nonTestHits"]):
        reasons.append("protocol-level object names alone don't expose the public API")
    if legacy["distinctPublicDeclarations"]:
        reasons.append("public names from an earlier spec revision (before channel.object.get() and the LiveMap and "
                        "LiveCounter value types): the objects notes must name the revision the SDK follows (item 1)")
    elif legacy["nonTestHits"]:
        reasons.append("earlier-revision names also appear in non-public code (internal names or leftovers); "
                        "advisory only")
    if answer == "yes" and stub_count:
        reasons.append(f"{stub_count} not-implemented marker(s) in files with public-API names: possibly incomplete")
    mode = None
    if answer == "yes":
        mode = "translate-only (advisory)" if stub_count else "evaluate if implemented (advisory)"
    return {"addLiveObjects": answer, "confidence": confidence, "suggestedMode": mode, "reasons": reasons}


def first_site(bucket):
    return bucket["publicDeclaredAt"][0].split(" (")[0] if bucket["publicDeclaredAt"] else None


def summary_text(ev, rec, stub_count, n_public):
    declared = [f"{n} at {first_site(b)}" for n, b in ev["publicApi"]["symbols"].items() if b["publicDeclaredAt"]]
    parts = [f"Public API: {len(declared)} of {n_public} current-spec names declared public"
              + (f" ({'; '.join(declared[:3])}{'; ...' if len(declared) > 3 else ''})" if declared else "")]
    acc = ev["accessor"]
    parts.append(f"RTL27 accessor declared at {first_site(acc)}" if first_site(acc)
                  else ("RTL27 accessor used in source" if acc["nonTestHits"] else "no RTL27 accessor found"))
    if ev["pluginKey"]["sourceNames"]:
        parts.append("plugin names: " + ", ".join(list(ev["pluginKey"]["sourceNames"])[:3]))
    src_dirs = [d for d in ev["packaging"]["moduleDirs"] if not is_test(d + "/x")]
    if src_dirs:
        parts.append("LiveObjects modules: " + ", ".join(src_dirs[:3]))
    legacy = ev["legacyPublicApi"]
    if legacy["distinctPublicDeclarations"]:
        parts.append(f"{legacy['distinctPublicDeclarations']} earlier-spec name(s) declared public")
    elif legacy["hits"]:
        parts.append("earlier-spec names only in non-public code, comments or tests")
    parts.append(f"internal implementation names in source: {ev['internalApi']['distinctNonTestSymbols']}")
    parts.append(f"not-implemented markers: {stub_count}")
    return "; ".join(parts) + f". Recommendation: {rec['addLiveObjects']} ({rec['confidence']})."


def fail(code, message):
    print(json.dumps({"ok": False, "code": code, "message": message}, indent=2))
    return 1


USAGE = "usage: detect_liveobjects.py <repo> [--spec-clone PATH] [--include-submodules]"


def usage_error(message):
    print(f"{USAGE}\ndetect_liveobjects.py: error: {message}", file=sys.stderr)
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
        elif a == "--include-submodules":
            opts[a] = True
        elif a.startswith("-"):
            return usage_error(f"unknown option {a}")
        else:
            args.append(a)
    include_submodules = bool(opts.get("--include-submodules"))
    if len(args) != 1:
        return usage_error(f"expected one <repo>, got {len(args)} arguments")
    repo = pathlib.Path(args[0]).expanduser()
    if not repo.is_dir():
        return usage_error(f"not a directory: {args[0]}")
    repo = repo.resolve()
    try:
        loaded = sn.load(opts.get("--spec-clone"))
        names = loaded["liveobjects"]
        public_names, legacy_now_internal = names["publicApi"], set(names["legacyNowInternal"])
        accessor_re = accessor_decl(names.get("accessorTypes") or ["RealtimeObject"])
        files = git_files(repo, "-co", "--exclude-standard")
        head, excluded_names = None, ALWAYS_EXCLUDED
        if files is None:
            files, listing, tracked, excluded_names = walk_files(repo), "filesystem walk", None, WALK_EXCLUDED
        else:
            listing = "git ls-files (tracked, and untracked but not ignored)"
            tracked = set(git_files(repo) or [])
            out = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace")
            head = out.stdout.strip() or None

        spec_clones = sorted({f[: -len(m)].rstrip("/") or "." for f in files for m in SPEC_CLONE_MARKERS
                              if f == m or f.endswith("/" + m)})
        if "." in spec_clones:
            return fail("REPO_IS_SPEC_CLONE", "the path is a copy of the specification repo, not an SDK repo")
        submodules = [] if include_submodules else submodule_paths(repo)
        skipped_prefixes = spec_clones + submodules
        nested_roots = sorted({f.rsplit("/", 1)[0] for f in files
                                if "/" in f and f.rsplit("/", 1)[1] in NESTED_PACKAGE_MANIFESTS}, key=len)
        exact, folded = build_tables(names)
        categories = {c: {} for c in CATEGORIES}
        accessor, plugin_key = new_bucket(), new_bucket()
        accessor_forms, plugin_names, plugin_src = collections.Counter(), collections.Counter(), collections.Counter()
        manifests, module_dirs, weak_dirs = [], collections.Counter(), collections.Counter()
        nested_pkgs, scanned, excluded = collections.Counter(), collections.Counter(), collections.Counter()
        stub_count, stub_files = 0, []

        for rel in sorted(files):
            parts = rel.split("/")
            hit_dir = next((p for p in parts[:-1] if p.lower() in excluded_names), None)
            if hit_dir or any(rel == p or rel.startswith(p + "/") for p in skipped_prefixes):
                excluded[hit_dir or "spec clone or submodule"] += 1
                continue
            path = repo / rel
            name, ext = parts[-1], pathlib.PurePosixPath(rel).suffix
            is_manifest = name in MANIFEST_NAMES or ext in MANIFEST_EXT
            if ext not in SOURCE_EXT and not is_manifest:
                continue
            test = is_test(rel)
            untracked = tracked is not None and rel not in tracked
            for i, p in enumerate(parts[:-1]):
                if PACKAGING.search(p):
                    module_dirs["/".join(parts[: i + 1])] += 1
                    break
            else:
                lowered = [p.lower() for p in parts[:-1]]
                if "objects" in lowered and not test:
                    weak_dirs["/".join(parts[: lowered.index("objects") + 1])] += 1
            try:
                if not path.is_file() or path.stat().st_size > MAX_BYTES:
                    excluded["missing, not a file, or over 2 MB"] += 1
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                excluded["unreadable"] += 1
                continue
            if SELF_SENTINEL in text:
                excluded["copy of this script"] += 1
                continue
            scanned[ext or name] += 1
            if is_manifest:
                for n, line in enumerate(text.splitlines(), 1):
                    if PACKAGING.search(line):
                        manifests.append(f"{rel}:{n}: {line.strip()[:120]}")
                        break
                if ext not in SOURCE_EXT:
                    continue
            channel_file = "channel" in name.lower()
            nested_root = next((r for r in reversed(nested_roots) if rel.startswith(r + "/")), None)
            file_has_public, file_stubs = False, 0
            for n, line in enumerate(text.splitlines(), 1):
                comment = bool(COMMENT_LINE.match(line))
                if STUB.search(line) and not comment:
                    file_stubs += 1
                for m in ACCESSOR_USE.finditer(line):
                    accessor_forms[m.group(1).lower()] += 1
                    add(accessor, rel, n, test, comment, untracked)
                    file_has_public = file_has_public or not (test or comment)
                decls = list(accessor_re.finditer(line))
                if channel_file:
                    decls += list(ACCESSOR_DECL_UNTYPED.finditer(line))
                for m in decls:
                    member = next(g for g in m.groups() if g)
                    accessor_forms[member.lower() + " (declared)"] += 1
                    public_decl = (not (test or comment)
                                    and visibility(line, rel, ext, member, text) == "public")
                    add(accessor, rel, n, test, comment, untracked, True, public_decl)
                    file_has_public = file_has_public or not (test or comment)
                for m in PLUGIN_IDENT.finditer(line):
                    plugin_names[m.group(0)] += 1
                    plugin_src[m.group(0)] += 0 if (test or comment) else 1
                    add(plugin_key, rel, n, test, comment, untracked)
                for m in PLUGIN_KEY.finditer(line):
                    plugin_names[m.group(0)[:60]] += 1
                    add(plugin_key, rel, n, test, comment, untracked)
                for m in IDENT.finditer(line):
                    found, how = match_identifier(m.group(0), exact, folded)
                    if not found:
                        continue
                    category, canonical = found
                    declared = not comment and bool(DECL.search(line[: m.start()]))
                    if how == "folded" and category == "legacyPublicApi" and not declared:
                        continue  # e.g. a CreateMap(...) call in an unrelated library: count only declarations
                    public_decl = (declared and not test and how != "underscored"
                                    and visibility(line, rel, ext, m.group(0), text) == "public")
                    if canonical in legacy_now_internal and public_decl:
                        category = "legacyPublicApi"
                    add(categories[category].setdefault(canonical, new_bucket()), rel, n, test, comment, untracked,
                        declared, public_decl)
                    if category in ("publicApi", "legacyPublicApi") and not (test or comment):
                        file_has_public = True
                        if nested_root:
                            nested_pkgs[nested_root] += 1
            if file_has_public and file_stubs:
                stub_count += file_stubs
                if len(stub_files) < MAX_FILES_LISTED:
                    stub_files.append(rel)

        evidence = {c: summarise(s) for c, s in categories.items()}
        evidence["accessor"] = dict(accessor, forms=dict(accessor_forms),
                                    rule="RTL27: a channel-named receiver reading .object(s) or getObject(s)(), or a "
                                          "member named object(s)/getObject(s) declared with the spec's accessor type ("
                                          + "/".join(f"{t}(s)" for t in names.get("accessorTypes") or []) + ") "
                                          "(untyped Ruby/JS declarations only in a file named after the channel)")
        evidence["pluginKey"] = dict(plugin_key, names=dict(plugin_names.most_common(10)),
                                      sourceNames={k: v for k, v in plugin_src.most_common(10) if v})
        evidence["packaging"] = {
            "manifests": manifests[:20],
            "moduleDirs": dict(module_dirs.most_common(15)),
            "weakObjectsDirs": dict(weak_dirs.most_common(10)),
            "nestedPackages": dict(nested_pkgs.most_common(10)),
            "nestedPackagesNote": "directories with their own package manifest that hold public-API names: confirm "
                                  "each is the SDK's own plugin or module, not a vendored copy",
        }
        evidence["missingPublicNames"] = [n for n in public_names
                                          if not categories["publicApi"].get(n, {}).get("publicDeclarations")]
        rec = recommend(evidence, stub_count)
        summary = summary_text(evidence, rec, stub_count, len(public_names))
        if loaded["source"] != "spec":
            summary += " Warning: spec names unavailable; fallback names used (see warnings)."
        result = {
            "ok": True,
            "repo": str(repo),
            "head": head,
            "listing": listing,
            "namesSource": loaded["source"], "specClone": loaded.get("specClone"), "specRevision": loaded.get("revision"),
            "namesFrom": names.get("from", []), "dataFile": loaded["data"], "warnings": loaded["warnings"],
            "summary": summary,
            "recommendation": rec,
            "scanned": {"files": sum(scanned.values()), "byExtension": dict(scanned.most_common())},
            "excluded": {"files": dict(excluded), "specClones": spec_clones, "submodules": submodules,
                          "walkSkippedDirNames": sorted(WALK_SKIPPED),
                          "gitIgnoredFiles": "not scanned (git ls-files --exclude-standard)" if tracked is not None else None,
                          "dirNames": sorted(excluded_names)},
            "evidence": evidence,
            "stubMarkers": {"count": stub_count, "files": stub_files},
            "note": "Regex heuristic. Read the listed files before relying on it; the user decides at STOP-14.",
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:  # never crash: report a structured error
        return fail(sn.error_code(exc, "DETECT_ERROR"), f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
