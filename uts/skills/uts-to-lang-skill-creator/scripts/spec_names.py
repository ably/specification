#!/usr/bin/env python3
"""Read the names the detectors look for from the spec clone, at run time.

Usage: spec_names.py [--spec-clone PATH]     (prints the derived names as JSON)

Used as a module by detect_capabilities.py and detect_liveobjects.py, so the
names follow the spec when it renames things (RealtimeObjects became
RealtimeObject). It parses the IDL sections of specifications/features.md and
specifications/objects-features.md (heading "Interface Definition"): type
lines `    class|interface|enum Name: // PREFIX*[, internal]` and member lines
indented under them.

Rules (documented in section 13.8 of the skill):
  - Capability roles come from a type's spec-point prefix: RSC rest client,
    RTC realtime client, RSL rest channel, RTL/TH realtime channel, RTP
    realtime presence, RTN/TA connection. A client's base name is its type name
    without "Client" (RestClient -> Rest), as the UTS pseudocode writes it.
  - Key members are a role's method names, without the generic names in
    assets/capability-names.json; each keeps its spec point.
  - LiveObjects: objects-features.md types and members marked `internal` are
    internal; `PublicAPI::` types, and the types and enum values their members
    use, are shared (public and protocol); the other types are public. Members
    count only if their name has two or more words (compactJson), since
    single-word members (get, value) are too common to search for.
  - Protocol-only (wire) names: the features.md IDL types reachable from the
    shared types that aren't shared, and enum values starting OBJECT_.
  - The RTL27 accessor's type: the RealtimeChannel property whose type is a
    LiveObjects type (`object: RealtimeObject`).
The corpus-derived lists (capability-inapplicable tests, presence specs) don't
depend on the IDL: they are computed separately, so a fallback keeps them.
Names the spec can't give (SDK aliases, door factories, earlier-revision names,
names from spec prose) live in assets/capability-names.json: update that file,
not the code. Generic member names and the spelling transforms are code
constants below.

If the IDL can't be parsed, `source` is "fallback": the minimal names in the
data file's `fallback` are used, with a warning that the caller must show.
Never silent. A malformed data file is an error naming the file and the key,
never a fallback. Read-only; never touches the network.

Also the shared loader for the skill's data files (load_json): it ignores keys
starting with `_` (`_description`, `_comment`) and checks the shape.
"""
import json, os, pathlib, re, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE.parent / "assets" / "capability-names.json"
TYPE_LINE = re.compile(r"^    (class|interface|enum)\s+((?:PublicAPI::)?[A-Za-z_]\w*)(?:<[^>]*>)?(?:\s+extends\s+[\w, ]+)?:?\s*"
                        r"(?://\s*(.*))?$")
MEMBER_LINE = re.compile(r"^      ([a-zA-Z_]\w*)\s*(\(|:)")
ENUM_VALUE = re.compile(r"^      ([A-Z][A-Z0-9_]+)\b")
SPEC_POINT = re.compile(r"\b([A-Z]{2,6}\d\w*)")  # anywhere in the comment: `// internal, RTL27` or `// RTL27`
ROLE_BY_PREFIX = [("RSC", "restClient"), ("RTC", "realtimeClient"), ("RSL", "restChannel"), ("RTL", "channels"),
                  ("TH", "channels"), ("RTP", "presence"), ("RTN", "connection"), ("TA", "connection")]
# Member and type names too generic to search for (or to count as a method gap).
GENERIC_MEMBERS = {"get", "set", "on", "off", "once", "subscribe", "unsubscribe", "update", "release", "iterate",
                    "exists", "status", "device", "name", "objectId", "objectMessage"}
GENERIC_TYPE_NAMES = {"Instance"}
# How SDKs spell spec names: a short all-caps prefix (ART, I) is always tried, and these word prefixes and suffixes;
# members also in any case, snake_case and without these suffixes. A rest/realtime/http path segment qualifies a
# bare word (Client, Channel) as REST or Realtime.
TRANSFORMS = {"prefixes": ["Ably", "PubSub", "Base", "Default"], "suffixes": ["Protocol", "Interface"],
              "memberSuffixes": ["Async"], "qualifiedSegments": {"rest": "rest", "realtime": "realtime", "http": "rest"}}

STR, INT = "string", "integer"
NAMES = [STR]
ROLE_SHAPE = {"names": NAMES, "members": {"*": STR}, "from": NAMES}
SIDE_SHAPE = {"types": NAMES, "paths": NAMES}
DATA_SHAPE = {
    "aliases": {"rest": NAMES, "realtime": NAMES},
    "doorFactories": {"names": NAMES, "sides": {"*": SIDE_SHAPE}},
    "legacyPublicApi": NAMES, "legacyNowInternal": NAMES, "internalFromProse": NAMES,
    "fallback": {
        "capability": {"clients": {"rest": NAMES, "realtime": NAMES},
                        "roles": {r: ROLE_SHAPE for r in ("restClient", "realtimeClient", "restChannel", "channels",
                                                          "presence", "connection")}},
        "liveobjects": {k: NAMES for k in ("publicApi", "internalApi", "shared", "sharedConstants", "wireOnly",
                                            "wireConstants", "accessorTypes", "from")}},
}


class DataFileError(ValueError):
    """A data file in assets/ is missing, isn't valid JSON, or has the wrong shape. Never falls back."""


def _strip(value):
    if isinstance(value, dict):
        return {k: _strip(v) for k, v in value.items() if not k.startswith("_")}
    if isinstance(value, list):
        return [_strip(v) for v in value]
    return value


def _check(value, shape, where, name):
    """Shape language: STR/INT, [item shape], {key: shape} (all keys required; "*" = any key, each value checked)."""
    def bad(expected):
        got = type(value).__name__ if value is not None else "null"
        raise DataFileError(f"{name}: key '{where or '(top level)'}': expected {expected}, got {got}")
    if shape == STR:
        if not isinstance(value, str):
            bad("a string")
    elif shape == INT:
        if not isinstance(value, int) or isinstance(value, bool):
            bad("an integer")
    elif isinstance(shape, list):
        if not isinstance(value, list):
            bad("a list")
        for i, item in enumerate(value):
            _check(item, shape[0], f"{where}[{i}]", name)
    else:
        if not isinstance(value, dict):
            bad("an object")
        for key, sub in shape.items():
            if key == "*":
                for k, v in value.items():
                    _check(v, sub, f"{where}.{k}" if where else k, name)
            elif key not in value:
                raise DataFileError(f"{name}: key '{f'{where}.{key}' if where else key}' is missing")
            else:
                _check(value[key], sub, f"{where}.{key}" if where else key, name)


def load_json(path, shape):
    """Load one of the skill's data files: ignore `_` keys, check the shape, raise DataFileError naming file and key."""
    path = pathlib.Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DataFileError(f"{path.name}: can't read {path}: {exc.strerror or exc}") from None
    except json.JSONDecodeError as exc:
        raise DataFileError(f"{path.name}: not valid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from None
    if not isinstance(raw, dict) or not isinstance(raw.get("_description"), str):
        raise DataFileError(f"{path.name}: key '_description': expected a string as the first key (what the file is "
                            "for and who updates it)")
    data = _strip(raw)
    _check(data, shape, "", path.name)
    return data


def load_data():
    return load_json(DATA, DATA_SHAPE)


def locate(spec_clone=None):
    """The spec clone: the argument, else UTS_SPEC_CLONE, else the clone this skill lives in."""
    for cand in (spec_clone, os.environ.get("UTS_SPEC_CLONE"), str(HERE.parents[3])):
        if cand and (pathlib.Path(cand).expanduser() / "specifications" / "features.md").is_file():
            return pathlib.Path(cand).expanduser().resolve()
    return None


def revision(clone):
    def git(*a):
        out = subprocess.run(["git", "-C", str(clone), *a], capture_output=True, text=True)
        return out.stdout.strip() if out.returncode == 0 else None
    sha = git("rev-parse", "HEAD")
    dirty = git("--no-optional-locks", "status", "--porcelain", "--", "specifications")
    return {"sha": sha, "dirty": bool(dirty) if dirty is not None else None}


def parse_idl(path):
    """Return ({type name: {kind, comment, internal, members: {name: {kind, specPoint, internal}}, values}}, heading)."""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"(?m)^#+\s*Interface Definition.*$", text)
    if not m:
        raise ValueError(f"{path.name}: no 'Interface Definition' heading")
    heading = m.group(0).lstrip("#").strip()
    types, cur, lines = {}, None, text[m.end():].splitlines()
    for i, line in enumerate(lines):
        t = TYPE_LINE.match(line)
        if t:
            name = t.group(2).replace("PublicAPI::", "")
            comment = t.group(3) or ""
            cur = types.setdefault(name, {"kind": t.group(1), "comment": comment, "publicApi": "PublicAPI::" in t.group(2),
                                          "internal": bool(re.search(r"\binternal\b", comment)), "members": {},
                                          "values": [], "uses": set()})
            continue
        if cur is None or not line.startswith("      "):
            if line.strip() and not line.startswith(" "):
                cur = None
            continue
        e = ENUM_VALUE.match(line)
        if e and cur["kind"] == "enum":
            cur["values"].append(e.group(1))
            continue
        mm = MEMBER_LINE.match(line)
        if mm and mm.group(1) not in ("constructor", "embeds"):
            spec_point = SPEC_POINT.search(line.split("//", 1)[1]) if "//" in line else None
            if not spec_point and mm.group(2) == "(" and ")" not in line:
                for nxt in lines[i + 1:i + 12]:
                    if nxt.startswith("      )"):
                        spec_point = SPEC_POINT.search(nxt.split("//", 1)[1]) if "//" in nxt else None
                        break
            ptype = re.match(r"\s*([A-Za-z_]\w*)", line[mm.end():].split("//")[0]) if mm.group(2) == ":" else None
            cur["members"].setdefault(mm.group(1), {
                "kind": "method" if mm.group(2) == "(" else "property",
                "specPoint": spec_point.group(1) if spec_point else None,
                "type": ptype.group(1) if ptype else None,
                "internal": bool(re.search(r"//.*\binternal\b", line))})
        cur["uses"].update(re.findall(r"\b([A-Z][A-Za-z]+)\b", line.split("//")[0]))
    if not types:
        raise ValueError(f"{path.name}: no IDL type definitions under '{heading}'")
    return types, heading


def capability_names(features, heading, data):
    generic = GENERIC_MEMBERS
    roles = {r: {"names": [], "members": {}, "from": []} for _, r in ROLE_BY_PREFIX}
    for name, t in features.items():
        first = re.match(r"\s*([A-Z]{2,4})(?=\d|\*)", t["comment"])
        role = next((r for p, r in ROLE_BY_PREFIX if first and first.group(1) == p), None)
        if not role:
            continue
        roles[role]["names"].append(name)
        roles[role]["from"].append(f"features.md, {heading}: {t['kind']} {name} // {t['comment'].strip()}")
        for mname, mem in t["members"].items():
            if mem["kind"] == "method" and mname not in generic:
                roles[role]["members"].setdefault(mname, mem["specPoint"])
    clients = {}
    for cap, role in (("rest", "restClient"), ("realtime", "realtimeClient")):
        names = roles[role]["names"]
        clients[cap] = sorted(set(names) | {n[:-len("Client")] for n in names if n.endswith("Client")})
    missing = [r for r in ("restClient", "realtimeClient", "connection", "channels", "presence") if not roles[r]["names"]]
    if missing:
        raise ValueError(f"features.md IDL: no types for roles {missing}")
    return clients, roles


def liveobjects_names(objects, features, heading_o, heading_f, data):
    def multiword(n):
        return bool(re.search(r"[a-z][A-Z]", n))
    public, internal, shared, shared_consts = set(), set(), set(), set()
    for name, t in objects.items():
        if t["publicApi"]:
            shared.add(name)
            shared.update(u for u in t["uses"] if u in features)
            continue
        (internal if t["internal"] else public).add(name)
        for mname, mem in t["members"].items():
            if multiword(mname) and mname not in GENERIC_MEMBERS:
                (internal if (mem["internal"] or t["internal"]) else public).add(mname)
    for name in list(shared):
        if name in features and features[name]["kind"] == "enum":
            shared_consts.update(features[name]["values"])
    reach, todo = set(), [n for n in shared if n in features]
    while todo:
        n = todo.pop()
        if n in reach:
            continue
        reach.add(n)
        todo += [u for u in features[n]["uses"] if u in features and u not in reach]
    wire = {n for n in reach if n not in shared and features[n]["internal"]}
    wire_consts = {v for t in features.values() if t["kind"] == "enum" for v in t["values"]
                    if v.startswith("OBJECT_")} - shared_consts
    public -= GENERIC_TYPE_NAMES
    if not public:
        raise ValueError("objects-features.md IDL: no public LiveObjects types")
    # The RTL27 channel accessor's type: the RealtimeChannel property whose type is a LiveObjects type.
    channel = features.get("RealtimeChannel", {}).get("members", {})
    accessor_types = sorted({m["type"] for m in channel.values() if m["kind"] == "property" and m.get("type") in objects})
    if not accessor_types:
        raise ValueError("features.md IDL: no RealtimeChannel property of a LiveObjects type (the RTL27 accessor)")
    return {"publicApi": sorted(public), "internalApi": sorted(internal | set(data["internalFromProse"])),
            "shared": sorted(shared), "sharedConstants": sorted(shared_consts), "wireOnly": sorted(wire),
            "wireConstants": sorted(wire_consts), "accessorTypes": accessor_types,
            "legacyPublicApi": data["legacyPublicApi"],
            "legacyNowInternal": data["legacyNowInternal"],
            "from": [f"objects-features.md, {heading_o}", f"features.md, {heading_f} (protocol types, enums)",
                      "assets/capability-names.json (earlier-revision and prose names)"]}


def corpus_client_needs(clone):
    """Per UTS test (by Test ID): which clients its pseudocode constructs. Gives the capability-inapplicable lists:
    rest tests that need a Realtime client, realtime/objects tests that need a REST client, and realtime tests
    that construct only a REST client (REST-only tests filed under uts/realtime)."""
    needs_rt, needs_rest, rest_only_in_rt, presence = [], [], [], []
    for path in sorted((clone / "uts").glob("**/*.md")):
        rel = path.relative_to(clone / "uts").as_posix()
        if "/helpers/" in rel or rel.split("/")[0] not in ("rest", "realtime", "objects"):
            continue
        if rel.startswith("realtime/"):  # presence specs: a presence/ directory, else a file named for presence
            parts = rel.split("/")
            hit = next((i for i, seg in enumerate(parts[:-1]) if seg.lower() == "presence"), None)
            spec = "/".join(parts[:hit + 1]) + "/" if hit is not None else rel if "presence" in parts[-1].lower() else None
            if spec and spec not in presence:
                presence.append(spec)
        parts = re.split(r"\*\*Test ID\*\*:\s*`([^`]+)`", path.read_text(encoding="utf-8"))
        for tid, body in zip(parts[1::2], parts[2::2]):
            body = body.split("\n## ")[0]
            code = "\n".join(re.findall(r"```pseudo\n(.*?)```", body, re.S))
            rt = bool(re.search(r"\bRealtime\s*\(", code))
            rest = bool(re.search(r"\bRest\s*\(", code))
            if rel.startswith("rest/") and rt:
                needs_rt.append({"id": tid, "spec": rel})
            elif not rel.startswith("rest/") and rest:
                (needs_rest if rt else rest_only_in_rt).append({"id": tid, "spec": rel})
    return {"restTestsNeedingRealtime": needs_rt, "realtimeTestsNeedingRest": needs_rest,
            "restOnlyTestsUnderRealtime": rest_only_in_rt, "presenceSpecs": presence,
            "from": "uts/**/*.md: Rest(...) and Realtime(...) constructions in each test's pseudo blocks; presence "
                    "specs: uts/realtime presence/ directories and files named for presence"}


def load(spec_clone=None):
    """Names for both detectors, with where they came from. Falls back loudly, never silently."""
    data = load_data()
    clone = locate(spec_clone)
    result = {"source": "spec", "specClone": str(clone) if clone else None, "warnings": [], "data": str(DATA)}
    try:
        if clone is None:
            raise ValueError("no spec clone found (pass --spec-clone, or set UTS_SPEC_CLONE)")
        result["revision"] = revision(clone)
        features, hf = parse_idl(clone / "specifications" / "features.md")
        objects, ho = parse_idl(clone / "specifications" / "objects-features.md")
        clients, roles = capability_names(features, hf, data)
        result["capability"] = {"clients": clients, "roles": roles}
        result["liveobjects"] = liveobjects_names(objects, features, ho, hf, data)
    except (OSError, ValueError, KeyError) as exc:
        fb = data["fallback"]
        result.update(source="fallback", capability=fb["capability"], liveobjects=fb["liveobjects"])
        result["liveobjects"].update(legacyPublicApi=data["legacyPublicApi"], legacyNowInternal=data["legacyNowInternal"])
        result["liveobjects"]["internalApi"] = sorted(set(fb["liveobjects"]["internalApi"]) | set(data["internalFromProse"]))
        result["warnings"].append(f"spec names unavailable ({exc}); using the fallback names in {DATA.name}, which may "
                                  "be stale: fix the parser or the clone path, and don't rely on this result")
    # The corpus lists don't depend on the IDL: computed on their own, so a broken IDL doesn't lose them.
    result["capabilityInapplicable"] = {}
    if clone is not None:
        try:
            result["capabilityInapplicable"] = corpus_client_needs(clone)
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            result["warnings"].append(f"capability-inapplicable lists unavailable ({exc}): the uts/ corpus couldn't be "
                                      "read; work them out from the corpus by hand at STOP-17")
        if not (result.get("revision") or {}).get("sha"):
            result["warnings"].append(f"spec revision unknown: {clone} isn't a git checkout (or git failed), so the "
                                      "names can't be pinned to a spec SHA; use a git clone of ably/specification")
    for cap, extra in data["aliases"].items():
        result["capability"]["clients"][cap] = sorted(set(result["capability"]["clients"][cap]) | set(extra))
    return result


def error_code(exc, default):
    """The structured-error code a script reports: DATA_FILE_ERROR for a bad data file, else its own."""
    return "DATA_FILE_ERROR" if isinstance(exc, DataFileError) else default


def main(argv):
    clone = argv[argv.index("--spec-clone") + 1] if "--spec-clone" in argv[:-1] else None
    try:
        print(json.dumps(load(clone), indent=2, default=sorted))
        return 0
    except Exception as exc:  # never crash: report a structured error
        print(json.dumps({"ok": False, "code": error_code(exc, "SPEC_NAMES_ERROR"),
                          "message": f"{type(exc).__name__}: {exc}"}))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
