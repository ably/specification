#!/usr/bin/env python3
"""Detect which Ably Pub/Sub clients an SDK repository has, per side (Orient, STOP-17, D-31).

Usage: detect_capabilities.py <repo> [--spec-clone PATH] [--include-submodules]
                              [--capability-override rest=full,realtime=absent]

The harness and the skill's scope follow the SDK's capabilities, not its name
(section 13.8 of the skill): a REST client, and a Realtime client with its
connection, channels and presence. Names are read at run time from the spec
clone (spec_names.py: the features.md IDL, by spec-point prefix), plus the
aliases and door factories in assets/capability-names.json (update that file,
not the code). If the spec can't be parsed, `namesSource` is "fallback" with a
warning.

Matching (definitions, never usages):
  - type declarations of a spec name or its per-language forms: a short all-caps
    prefix (ART, I), spec_names.TRANSFORMS' word prefixes and suffixes, snake_case;
  - Go constructors New<Name> and type aliases (`type HTTPClient = ably.REST`);
  - a bare word (Client, Channel, Connection, Presence: a spec name without its
    Rest/Realtime prefix) only under a rest/realtime/http path segment;
  - members in any case, snake_case, without an Async suffix, including typed
    returns without a modifier (Dart `Future<void> enter(`, Java `void
    attach(`); a connection, channels or presence member counts only inside
    that sub-area's own type (the last type declared before it, or a Go
    receiver), or outside any recognised type in a file declaring one;
  - door factories (2.0 split SDKs), whose side (device, server) comes from the
    enclosing door type (PubSubDevice) or else the path (Ably.PubSub.Device),
    and whose capability comes from the return type or the name.
A client is public when its type is public, or when a public factory returns
it; constructor visibility is ignored. Sides come only from doors: when a door
has a device or server side, `sides` lists core (the client types themselves,
reached through the internal-access route) and each door side; otherwise it is
null. A client type under a `device` path (push LocalDevice code) isn't a side.

Levels: rest full | partial | absent; realtime full | partial | absent |
unclear, with connection, channels and presence (present: a declared name and
at least one key member; stub: names only, or not-implemented markers;
absent), transport evidence, and, only when realtime is partial, advisory
method-level gaps (spec members not found; naming variants make them noisy on
full SDKs). Realtime "unclear" (a client declared but not public) leaves
realtime undecided: scope kind "unclear", asked at STOP-17, never decided as
rest-only; so does a realtime client with no connection, no channels and no
REST client. It flags an SDK that wraps native SDKs (hooks unreachable from
its language); the bridge then counts as its transport evidence. With
presence absent (scope full or realtime-only), the corpus's presence specs
(spec_names.py) are capability-inapplicable. --capability-override levels are
validated (USAGE_ERROR). `clients.*.gateTypes` (internal) holds what the
eligibility definition gate counts: declared client types (not bindings or
functions, not under example(s)/sample(s)/demo(s)) and device/server doors.
Reuses detect_liveobjects.py's exclusions. Prints one JSON object with the
profile, a scope suggestion (modules, unsupported modules, capability-
inapplicable tests) and a summary. Read-only; never touches the network.
"""
import bisect, collections, importlib.util, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lo = _load("detect_liveobjects")
sn = _load("spec_names")
SOURCE_EXT = lo.SOURCE_EXT
WEBSOCKET = re.compile(r"websocket", re.I)
GO_ALIAS = re.compile(r"^\s*type\s+(\w+)\s*=\s*\w+\.(\w+)\b")
MEMBER_DECL = re.compile(r"^\s*(?:[-+]\s*\(|(?:(?:public|open|override|static|async|export|final|virtual|abstract|"
                          r"suspend|inline|func|fun|def|fn|function|pub|internal|private|protected)\b[^=]*?)|"
                          r"(?:async\s+)?\w+\s*\([^)]*\)\s*(?::[^={]*)?\{?\s*$|"
                          # a typed return without a modifier: Dart `Future<void> enter(`, Java package-private
                          # `void attach(`; not a statement keyword (`return foo(`, `if isReady(`)
                          r"(?:@\w+(?:\([^)]*\))?\s+)*(?!(?:return|new|await|throw|else|if|while|for|switch|guard|"
                          r"unless|until|when|case|yield|in|is|as|not|and|or|delete|typeof|echo|print|puts|raise|"
                          r"assert|go|defer|let|var|val|const)\b)[A-Za-z_][\w.]*(?:<[^()]*>)?[?*]?\s+\w+\s*\()")
NATIVE_BRIDGE = re.compile(r"\bMethodChannel\b|\binvokeMethod\s*\(|\bNativeModules\b|\bplatform channel", re.I)
ROLES = ("restClient", "realtimeClient", "restChannel", "connection", "channels", "presence")
# The type a member belongs to: the last type declared before it (Go: `type X struct`, or a method's receiver).
ENCLOSING = re.compile(r"\b(?:class|struct|object|interface|protocol|enum|extension|trait|impl|record)\s+"
                        r"([A-Za-z_][\w.:]*)|^type\s+(\w+)\s+(?:struct|interface)\b|^func\s*\(\s*\w*\s*\*?\s*(\w+)\s*\)",
                        re.M)
SUB_AREAS = ("connection", "channels", "presence")
BINDINGS = {"var", "let", "val", "const", "property"}
EXAMPLE_SEGMENT = re.compile(r"^(examples?|samples?|demos?)$", re.I)
TYPE_DECL = re.compile(r"\b(?:class|struct|object|module|interface|protocol|enum|extension|namespace|trait|impl)\s+"
                        r"([A-Za-z_][\w.:]*)")


class Names:
    """The classifier, built from spec_names.load() and the data file."""

    def __init__(self, loaded):
        data = sn.load_data()
        cap = loaded["capability"]
        self.clients = {c: set(n) for c, n in cap["clients"].items()}
        self.roles = cap["roles"]
        t = sn.TRANSFORMS
        self.prefix = re.compile(r"^(?:[A-Z]{1,4}(?=[A-Z][a-z])|" + "|".join(t["prefixes"]) + ")")
        self.suffix = re.compile("(?:" + "|".join(t["suffixes"]) + ")$")
        self.member_suffix = re.compile("(?:" + "|".join(t["memberSuffixes"]) + ")$")
        self.segments = t["qualifiedSegments"]
        self.area_names = {r: set(self.roles[r]["names"]) for r in ("restChannel", "connection", "channels", "presence")}
        # Bare words: a spec name without its Rest/Realtime prefix, or a single-word spec name.
        self.bare = {}
        for role in ROLES:
            for n in self.roles[role]["names"]:
                cap_seg = "rest" if role.startswith("rest") else "realtime"
                stripped = re.sub(r"^(Rest|Realtime)", "", n)
                if stripped != n or not re.search(r"[a-z][A-Z]", n):
                    self.bare[(cap_seg, stripped)] = role
        self.members = collections.defaultdict(set)
        for role in ROLES:
            for m in self.roles[role]["members"]:
                self.members[m.lower()].add(role)
                self.members[sn_snake(m)].add(role)
        self.doors = data["doorFactories"]
        self.door_re = re.compile(r"\b(" + "|".join(sorted(map(re.escape, self.doors["names"]), key=len, reverse=True))
                                  + r")\b")

    def candidates(self, token):
        out, t = {token}, token
        m = self.prefix.match(t)
        if m and len(t) > m.end():
            t = t[m.end():]
            out.add(t)
        s = self.suffix.sub("", t)
        if s and s != t:
            out.add(s)
        if token.startswith("New") and len(token) > 3:
            out.add(token[3:])
        return out

    def classify(self, token, segs):
        cands = self.candidates(token)
        folded = {c.lower() for c in cands}
        for cap, names in self.clients.items():
            if cands & names or (token.isupper() or token.startswith("New")) and folded & {n.lower() for n in names}:
                return "client", cap
        for role, names in self.area_names.items():
            if cands & names and not any((seg, c) in self.bare for seg in ("rest", "realtime") for c in cands
                                          if c in names and c == token):
                return "area", role
        for seg_name in segs:
            seg = self.segments.get(seg_name)
            for c in cands:
                role = self.bare.get((seg, c)) if seg else None
                if role in ("restClient", "realtimeClient"):
                    return "client", "rest" if role == "restClient" else "realtime"
                if role:
                    return "area", role
        return None, None

    def member_roles(self, token):
        t = self.member_suffix.sub("", token.lstrip("_"))
        return self.members.get(t.lower()) or self.members.get(t) or set()

    def door(self, name):
        cap = "rest" if re.search(r"http|rest", name, re.I) else "realtime"
        return cap


def sn_snake(name):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def list_files(repo, include_submodules):
    files = lo.git_files(repo, "-co", "--exclude-standard")
    excluded = lo.ALWAYS_EXCLUDED
    if files is None:
        files, excluded = lo.walk_files(repo), lo.WALK_EXCLUDED
    clones = sorted({f[: -len(m)].rstrip("/") or "." for f in files for m in lo.SPEC_CLONE_MARKERS
                      if f == m or f.endswith("/" + m)})
    subs = [] if include_submodules else lo.submodule_paths(repo)
    keep, skipped = [], collections.Counter()
    for rel in files:
        parts = rel.split("/")
        hit = next((p for p in parts[:-1] if p.lower() in excluded), None)
        if hit or any(rel == p or rel.startswith(p + "/") for p in clones + subs if p != "."):
            skipped[hit or "spec clone or submodule"] += 1
            continue
        keep.append(rel)
    return keep, dict(skipped), subs


def visibility(line, rel, ext, name, text):
    """detect_liveobjects.py's heuristic, plus PHP, whose classes are public unless marked otherwise."""
    if ext == ".php" and not lo.NONPUBLIC_MOD.search(line) and not lo.PRIVATE_PATH.search(rel):
        return "public"
    return lo.visibility(line, rel, ext, name, text)


def door_side(rel, text, pos, names, paths=True):
    """The side of a door at `pos`: its enclosing door type (the last type declared before it, matched whole), else a
    path segment (when `paths`); "core" if neither. Only doors have sides."""
    enclosing = None
    for m in TYPE_DECL.finditer(text, 0, pos):
        enclosing = m.group(1)
    if enclosing:
        last = re.split(r"[.:]+", enclosing)[-1].lower()
        for side, marks in names.doors["sides"].items():
            if last in {mk.lower() for mk in marks["types"]}:
                return side
    if paths:
        for seg in (s.lower().replace("_", "-") for s in rel.split("/")[:-1]):
            for side, marks in names.doors["sides"].items():
                if any(seg == mk.lower() or seg.endswith("." + mk.lower()) for mk in marks["paths"]):
                    return side
    return "core"


def scan(repo, include_submodules=False, names=None):
    names = names or Names(sn.load())
    files, skipped, subs = list_files(repo, include_submodules)
    clients = {c: {"publicTypes": collections.Counter(), "internalTypes": collections.Counter(),
                    "factories": collections.Counter(), "publicAt": [], "testOrCommentHits": 0,
                    "doors": collections.defaultdict(set), "gateTypes": collections.Counter()}
                for c in ("rest", "realtime")}
    areas = {r: {"names": collections.Counter(), "members": collections.Counter(), "files": set(),
                  "testOrCommentHits": 0} for r in ROLES}
    declared_members = collections.defaultdict(set)  # file -> member names declared there
    member_hits = []  # (file, enclosing role or None, token, roles): credited to the sub-areas after the scan
    stub_files, transport, transport_manifests, bridge = set(), 0, [], 0
    native_dirs = any(f.split("/")[0] in ("android", "ios") and pathlib.PurePosixPath(f).suffix in
                      (".java", ".kt", ".swift", ".m") for f in files)
    texts = {}
    for rel in files:
        ext = pathlib.PurePosixPath(rel).suffix
        name = rel.rsplit("/", 1)[-1]
        if name in lo.MANIFEST_NAMES or ext in lo.MANIFEST_EXT:
            try:
                if WEBSOCKET.search((repo / rel).read_text(encoding="utf-8", errors="replace")):
                    transport_manifests.append(rel)
            except OSError:
                pass
        if ext not in SOURCE_EXT:
            continue
        try:
            path = repo / rel
            if not path.is_file() or path.stat().st_size > lo.MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if lo.SELF_SENTINEL in text or "detect_capabilities.py <repo>" in text:
            continue
        texts[rel] = text
        test = lo.is_test(rel)
        segs = [p.lower() for p in rel.split("/")[:-1] if p.lower() in names.segments]
        if "pubsub" not in [p.lower() for p in rel.split("/")] and "http" in segs:
            segs.remove("http")
        example = any(EXAMPLE_SEGMENT.match(p) for p in rel.split("/")[:-1])  # not a definition for the gate
        starts = [0] + [m.end() for m in re.finditer("\n", text)]
        enclosing = []  # (offset, role or None) of each type declaration, in order
        for e in ENCLOSING.finditer(text):
            tname = re.split(r"[.:]+", next(g for g in e.groups() if g))[-1]
            kind, what = names.classify(tname, segs) if tname[:1].isupper() else (None, None)
            enclosing.append((e.start(), {"client": {"rest": "restClient", "realtime": "realtimeClient"}.get(what),
                                          "area": what}.get(kind)))
        offsets = [o for o, _ in enclosing]
        for n, line in enumerate(text.splitlines(), 1):
            comment = bool(lo.COMMENT_LINE.match(line))
            if not (test or comment):
                if lo.STUB.search(line):
                    stub_files.add(rel)
                if WEBSOCKET.search(line):
                    transport += 1
                if ext in (".dart", ".js", ".ts") and NATIVE_BRIDGE.search(line):
                    bridge += 1
                g = GO_ALIAS.match(line)
                if g and ext == ".go":
                    kind, what = names.classify(g.group(2), segs)
                    if kind == "client":
                        clients[what]["publicTypes"][g.group(1)] += 1
                        if not example:
                            clients[what]["gateTypes"][g.group(1)] += 1
                        if len(clients[what]["publicAt"]) < 3:
                            clients[what]["publicAt"].append(f"{rel}:{n}")
                for m in names.door_re.finditer(line):
                    before = line[: m.start()]
                    if (lo.DECL.search(before) or re.search(r"(public|static|export|^\s*[-+]\s*\(.*\))\s*[^=]*$", before)
                            or re.match(r"^\s*(def|func|fun|function|async def)\s", line)) \
                            and not lo.NONPUBLIC_MOD.search(line):
                        cap = names.door(m.group(1))
                        rt = re.search(r"\b(\w+)\s*[*?]?\s*$", before)
                        if rt:
                            k, w = names.classify(rt.group(1), segs)
                            cap = w if k == "client" else cap
                        clients[cap]["factories"][f"{rel}:{n}"] += 1
                        side = door_side(rel, text, starts[min(n, len(starts)) - 1] + m.start(), names)
                        clients[cap]["doors"][side].add(m.group(1))
                        if side != "core" and not example:  # a door entry on a device or server side defines a client
                            clients[cap]["gateTypes"][f"{side} door {m.group(1)}"] += 1
            for m in lo.IDENT.finditer(line):
                tok = m.group(0)
                decl = None if comment else lo.DECL.search(line[: m.start()])
                declared = bool(decl)
                kind, what = names.classify(tok, segs) if tok[:1].isupper() else (None, None)
                if kind:
                    if test or comment:
                        (clients[what] if kind == "client" else areas[what])["testOrCommentHits"] += 1
                        continue
                    if kind == "client" and declared:
                        vis = visibility(line, rel, ext, tok, text)
                        clients[what]["publicTypes" if vis == "public" else "internalTypes"][tok] += 1
                        # The definition gate counts declared types only: not a binding (`const Realtime = require(
                        # 'ably').Realtime`), a function (`def create_client`), or code under examples/samples/demos.
                        if not example and (decl.group(1) or "") not in BINDINGS | {"def", "func", "fun", "fn"}:
                            clients[what]["gateTypes"][tok] += 1
                        areas["restClient" if what == "rest" else "realtimeClient"]["files"].add(rel)
                        if vis == "public":
                            if len(clients[what]["publicAt"]) < 3:
                                clients[what]["publicAt"].append(f"{rel}:{n}")
                    elif kind == "area" and declared:
                        areas[what]["names"][tok] += 1
                        areas[what]["files"].add(rel)
                elif not (test or comment) and re.match(r"\s*(?:<[^>()]*>)?\s*[(:]", line[m.end():]) \
                        and MEMBER_DECL.match(line):
                    roles = names.member_roles(tok)
                    for role in roles - set(SUB_AREAS):  # clients and the REST channel: from any file
                        areas[role]["members"][tok] += 1
                    if roles & set(SUB_AREAS):
                        i = bisect.bisect_right(offsets, starts[min(n, len(starts)) - 1] + m.start()) - 1
                        member_hits.append((rel, enclosing[i][1] if i >= 0 else None, tok, roles & set(SUB_AREAS)))
                    declared_members[rel].add(names.member_suffix.sub("", tok.lstrip("_")).lower().replace("_", ""))
    # Sub-area members count only where that sub-area's type declares them: in a type of that role, or, outside any
    # recognised type, in a file declaring one (so RealtimeChannel.history isn't a presence member, and an empty
    # `RealtimePresence: RealtimePresenceProtocol {}` has no members).
    for rel, owner, tok, roles in member_hits:
        for role in roles:
            if owner == role or (owner is None and rel in areas[role]["files"]):
                areas[role]["members"][tok] += 1
    # Factories in other forms: a public function or property returning a client type.
    for rel, text in texts.items():
        if lo.is_test(rel):
            continue
        for cap in clients:
            types = set(clients[cap]["publicTypes"]) | set(clients[cap]["internalTypes"]) | names.clients[cap]
            for t in types:
                pat = re.compile(rf"(?:\bpublic\b[^=;{{]*\b{re.escape(t)}\s*\??\s+\w+\s*[({{]|"
                                  rf"\)\s*(?:->|:)\s*[*&]?\s*{re.escape(t)}\b|"
                                  rf"^func\s+(?:\([^)]*\)\s*)?[A-Z]\w*\s*\([^)]*\)\s*\(?\*?{re.escape(t)}\b|"
                                  rf"^\s*\+\s*\(\s*{re.escape(t)}\s*\*\s*\))", re.M)
                for m in pat.finditer(text):
                    line = text[text.rfind("\n", 0, m.start()) + 1: text.find("\n", m.end())]
                    if lo.COMMENT_LINE.match(line) or lo.NONPUBLIC_MOD.search(line):
                        continue
                    clients[cap]["factories"][f"{rel}:{text.count(chr(10), 0, m.start()) + 1}"] += 1
                    side = door_side(rel, text, m.start(), names, paths=False)
                    if side != "core":  # a public factory of another name inside a door type
                        clients[cap]["doors"][side].add(t)
    return {"clients": clients, "areas": areas, "stubFiles": stub_files, "transport": transport,
            "transportManifests": transport_manifests, "skipped": skipped, "submodules": subs,
            "declaredMembers": declared_members, "nativeBridge": bridge, "nativeDirs": native_dirs}


def area_level(a, stub_files):
    """A realtime sub-area: present needs a declared name and at least one of its key (non-generic) members declared
    in its own type; names alone (an empty protocol and class) are a stub."""
    if not a["names"]:
        return "absent"
    if not a["members"]:
        return "stub"
    return "stub" if a["files"] & stub_files else "present"


def profile(res, names, override=None):
    clients, areas = res["clients"], res["areas"]
    reasons = []

    def client_view(cap):
        c = clients[cap]
        return {"public": bool(c["publicTypes"] or c["factories"]),
                "via": "type" if c["publicTypes"] else ("factory" if c["factories"] else None),
                "names": sorted(set(c["publicTypes"]) | set(c["internalTypes"])), "publicAt": c["publicAt"],
                "factories": list(c["factories"])[:3],
                "internalOnly": bool(c["internalTypes"]) and not (c["publicTypes"] or c["factories"]),
                "testOrCommentHits": c["testOrCommentHits"]}

    rest_c, rt_c = client_view("rest"), client_view("realtime")
    rest_members = sorted(areas["restClient"]["members"])
    rc = areas["restChannel"]
    rest_channel = len(rc["names"]) >= 2 or (len(rc["names"]) >= 1 and len(rc["members"]) >= 1) or len(rc["members"]) >= 2
    rest_reasons, rt_reasons = [], []
    if rest_c["public"] and len(rest_members) >= 2 and rest_channel:
        rest_level = "full"
    elif rest_c["public"]:
        rest_level = "partial"
        rest_reasons.append("REST client found, but not two of its key members and a REST channel")
    else:
        rest_level = "absent"
    subareas = {}
    for a in ("connection", "channels", "presence"):
        subareas[a] = {"level": area_level(areas[a], res["stubFiles"]), "names": sorted(areas[a]["names"]),
                        "members": sorted(areas[a]["members"]), "stubFiles": sorted(areas[a]["files"] & res["stubFiles"])[:3]}
    present = [a for a, v in subareas.items() if v["level"] == "present"]
    wraps = bool(res["nativeBridge"] and res["nativeDirs"])
    # A wrapper over native SDKs has its transport in them: the bridge is the transport evidence (13.8).
    transport = bool(res["transport"] or res["transportManifests"] or wraps)
    if rt_c["public"] and len(present) == 3 and transport:
        rt_level = "full"
    elif rt_c["public"] or any(v["level"] != "absent" for v in subareas.values()):
        rt_level = "partial"
        missing = [a for a in subareas if a not in present]
        rt_reasons.append("realtime partial: " + (f"sub-areas absent or stub: {', '.join(missing)}" if missing else
                                                    "no WebSocket transport evidence")
                          + ("" if rt_c["public"] else "; no public realtime client"))
    elif rt_c["internalOnly"]:
        rt_level = "unclear"
        rt_reasons.append("a realtime client is declared, but not public and not returned by a public factory")
    else:
        rt_level = "absent"
    # Advisory method-level gaps, only for partial realtime: spec members of the realtime roles not declared in their
    # files. On full SDKs naming variants (whenState, getMessage) make them noise.
    gaps = []
    if rt_level == "partial":
        for role in ("connection", "channels", "presence"):
            files = areas[role]["files"]
            if not files:
                continue
            here = set().union(*(res["declaredMembers"].get(f, set()) for f in files))
            for m, point in names.roles[role]["members"].items():
                if m.lower() not in here and sn_snake(m).replace("_", "") not in here:
                    gaps.append(f"{point or '?'} {role}.{m}")
    source = "detected"
    if override:  # the override's levels win; what was detected for them is kept only as labelled context
        source = "override (whitelist)"
        if "rest" in override:
            rest_reasons = [f"detected before override: {r}" for r in rest_reasons]
        if "realtime" in override:
            rt_reasons = [f"detected before override: {r}" for r in rt_reasons]
        rest_level, rt_level = override.get("rest", rest_level), override.get("realtime", rt_level)
    reasons += rest_reasons + rt_reasons
    if override:
        reasons.append(f"capability override from the eligibility whitelist: {override}")
    door_sides = set(clients["rest"]["doors"]) | set(clients["realtime"]["doors"])
    sides = None
    if door_sides & {"device", "server"}:  # core: the client types themselves (and any side-less door); then each door
        sides = {}
        for s in ["core"] + sorted(door_sides - {"core"}):
            sides[s] = {}
            for cap in ("rest", "realtime"):
                found = set(clients[cap]["doors"].get(s, set()))
                if s == "core":
                    found |= set(clients[cap]["publicTypes"]) | set(clients[cap]["internalTypes"])
                sides[s][cap] = sorted(found)
    return {"rest": {"level": rest_level, "client": rest_c, "members": rest_members, "channel": rest_channel},
            "realtime": {"level": rt_level, "client": rt_c, "subAreas": subareas,
                          "transport": {"nonTestHits": res["transport"], "manifests": res["transportManifests"][:5]},
                          "methodGapsAdvisory": gaps[:12]},
            "source": source, "sides": sides, "reasons": reasons,
            "wrapsNativeSdk": wraps}


LEVELS = {"rest": ("full", "partial", "absent"), "realtime": ("full", "partial", "absent", "unclear")}


def parse_override(text):
    """`rest=full,realtime=absent` -> dict; ValueError naming the bad part."""
    out = {}
    for kv in (x.strip() for x in text.split(",") if x.strip()):
        cap, _, level = kv.partition("=")
        cap, level = cap.strip(), level.strip()
        if cap not in LEVELS:
            raise ValueError(f"--capability-override: unknown capability {cap!r} in {kv!r} (rest or realtime)")
        if level not in LEVELS[cap]:
            raise ValueError(f"--capability-override: {cap} level must be one of {', '.join(LEVELS[cap])}, got {level!r}")
        out[cap] = level
    if not out:
        raise ValueError("--capability-override: expected rest=<level>,realtime=<level>")
    return out


def scope_for(rest_level, rt_level, inapplicable, weak_realtime=False):
    rest, rt = rest_level in ("full", "partial"), rt_level in ("full", "partial")
    if rt_level == "unclear" or (weak_realtime and not rest):  # never decided as rest-only: the user decides at STOP-17
        return {"kind": "unclear", "modules": ["rest"] if rest else [], "undecided": ["realtime", "objects"],
                "unsupported": {}, "capabilityInapplicable": [], "extraTests": []}
    if rest and rt:
        return {"kind": "full", "modules": ["rest", "realtime"], "unsupported": {}, "capabilityInapplicable": [],
                "extraTests": []}
    if rest:
        why = "capability absent: no realtime client (D-31)"
        return {"kind": "rest-only", "modules": ["rest"], "unsupported": {"realtime": why, "objects": why},
                "capabilityInapplicable": [t["id"] for t in inapplicable.get("restTestsNeedingRealtime", [])],
                "extraTests": [t["id"] for t in inapplicable.get("restOnlyTestsUnderRealtime", [])]}
    if rt:
        return {"kind": "realtime-only", "modules": ["realtime"],
                "unsupported": {"rest": "capability absent: no REST client (D-31)"},
                "capabilityInapplicable": [t["id"] for t in inapplicable.get("realtimeTestsNeedingRest", [])],
                "extraTests": []}
    return {"kind": "none", "modules": [], "unsupported": {}, "capabilityInapplicable": [], "extraTests": []}


def main(argv):
    args, opts = [], {}
    it = iter(argv[1:])
    for a in it:
        if a in ("--spec-clone", "--capability-override"):
            opts[a] = next(it, None)
        elif a == "--include-submodules":
            opts[a] = True
        else:
            args.append(a)
    if len(args) != 1 or not pathlib.Path(args[0]).is_dir():
        print("usage: detect_capabilities.py <repo> [--spec-clone PATH] [--include-submodules] "
              "[--capability-override rest=full,realtime=absent]", file=sys.stderr)
        return 2
    repo = pathlib.Path(args[0]).expanduser().resolve()
    try:
        loaded = sn.load(opts.get("--spec-clone"))
        names = Names(loaded)
        override = None
        if opts.get("--capability-override"):
            try:
                override = parse_override(opts["--capability-override"])
            except ValueError as exc:
                print(json.dumps({"ok": False, "code": "USAGE_ERROR", "message": str(exc)}))
                return 2
        res = scan(repo, bool(opts.get("--include-submodules")), names)
        prof = profile(res, names, override)
        inapplicable = loaded.get("capabilityInapplicable", {})
        rest_level, rt_level = prof["rest"]["level"], prof["realtime"]["level"]
        sub = {a: v["level"] for a, v in prof["realtime"]["subAreas"].items()}
        # A realtime client with no connection and no channels found (python-like naming the scan misses, or a
        # mislabelled type), and no REST client: too weak to decide realtime-only.
        weak = (rt_level == "partial" and sub["connection"] == "absent" and sub["channels"] == "absent"
                and not (override and "realtime" in override))
        scope = scope_for(rest_level, rt_level, inapplicable, weak)
        reasons = prof["reasons"]
        if weak and scope["kind"] == "unclear" and rt_level != "unclear":
            reasons.append("a realtime client, but no connection or channels found and no REST client: ask at STOP-17 "
                            "what this SDK offers (the scan may miss its naming); don't decide realtime-only")
        if scope["kind"] == "none":
            reasons.append("no public REST or Realtime client: wrong path? (STOP-16 ask)")
        if scope["kind"] == "unclear" and rt_level == "unclear":
            reasons.append("realtime undecided: ask at STOP-17 whether the declared realtime client is reachable "
                            "(public elsewhere, or through the sanctioned internal-access route); don't decide "
                            "rest-only")
        if rt_level == "partial" and sub["presence"] == "absent" and scope["kind"] in ("full", "realtime-only"):
            presence = inapplicable.get("presenceSpecs") or []  # from the corpus (spec_names.py)
            scope["capabilityInapplicable"] += [p for p in presence if p not in scope["capabilityInapplicable"]]
            if not presence:
                reasons.append("presence absent, but the corpus's presence specs couldn't be listed: list them from "
                                "uts/realtime at STOP-17")
        gaps = prof["realtime"]["methodGapsAdvisory"]
        if gaps:
            reasons.append("possible method-level gaps (likely deviations or not-implemented, not out of scope): "
                            + "; ".join(gaps[:6]) + ("; …" if len(gaps) > 6 else ""))
        if prof["wrapsNativeSdk"]:
            reasons.append("wraps native SDKs over a platform bridge: test hooks are probably unreachable from the "
                            "SDK language; the unit tier only if hooks exist (P-13), integration and proxy still apply")
        confirm = bool(scope["kind"] != "full" or rest_level != "full" or rt_level != "full" or prof["sides"]
                        or override or prof["wrapsNativeSdk"] or loaded["source"] == "fallback")
        side_text = ""
        if prof["sides"]:
            side_text = "; sides: " + ", ".join(
                f"{s} (rest {'yes' if v['rest'] else 'no'}, realtime {'yes' if v['realtime'] else 'no'})"
                for s, v in prof["sides"].items())
        summary = (f"rest {rest_level}" + (f" ({', '.join(prof['rest']['client']['names'][:2])})"
                                          if prof["rest"]["client"]["names"] else "")
                    + f"; realtime {rt_level}"
                    + (f" ({', '.join(prof['realtime']['client']['names'][:2])}; "
                      + ", ".join(f"{a} {v['level']}" for a, v in prof["realtime"]["subAreas"].items()) + ")"
                      if rt_level not in ("absent",) else "")
                    + ("; WebSocket transport" if prof["realtime"]["transport"]["nonTestHits"] or
                      prof["realtime"]["transport"]["manifests"] else
                      "; transport in the wrapped native SDKs" if prof["wrapsNativeSdk"] else "; no WebSocket code")
                    + side_text + (f"; source: {prof['source']}" if override else ""))
        result = {
            "ok": True, "repo": str(repo),
            "namesSource": loaded["source"], "specClone": loaded.get("specClone"), "specRevision": loaded.get("revision"),
            "namesFrom": {r: v.get("from", [])[:1] for r, v in loaded["capability"]["roles"].items()},
            "dataFile": loaded["data"], "warnings": loaded["warnings"],
            "excluded": {"files": res["skipped"], "submodules": res["submodules"]},
            "capabilities": {k: prof[k] for k in ("rest", "realtime")}, "source": prof["source"],
            "sides": prof["sides"], "wrapsNativeSdk": prof["wrapsNativeSdk"],
            "scopeSuggestion": dict(scope, confirmAtStop17=confirm),
            "reasons": reasons, "summary": summary,
            "note": "Regex heuristic over definitions: read the evidence; the user confirms at STOP-13 or STOP-17.",
        }
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:  # never crash: report a structured error
        print(json.dumps({"ok": False, "code": sn.error_code(exc, "CAPABILITY_ERROR"),
                          "message": f"{type(exc).__name__}: {exc}"}))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
