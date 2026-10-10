# 13. Step 0: orient

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention). Links that climb out of the skill directory are spec-repo paths: resolve them against the spec clone, not against this file's installed location.

**Goal:** before anything else, in every run, establish four things:

- that the repository is one this procedure supports;
- what it already has;
- which mode to run in (**Create** or **Upgrade/Fix**);
- for Upgrade/Fix, which existing skill to work on.

Orient is read-only and quick. It builds nothing, runs no tests, touches no network and writes no file. The working records are created only after STOP-13, because their location depends on the answer (D-24).

Contents:

- [13.1 Run it](#131-run-it)
- [13.2 Repository eligibility (STOP-16)](#132-repository-eligibility-stop-16)
- [13.3 State classes](#133-state-classes)
- [13.4 The State summary and STOP-13](#134-the-state-summary-and-stop-13)
- [13.5 Routing](#135-routing)
- [13.6 Re-entry: resume or restart](#136-re-entry-resume-or-restart)
- [13.7 Provenance (D-30)](#137-provenance-d-30)
- [13.8 Capabilities and scope (STOP-17, D-31)](#138-capabilities-and-scope-stop-17-d-31)

## 13.1 Run it

Run `python3 <skill-dir>/scripts/orient.py <repo> [--spec-clone <path>]`. Pass the spec clone the user named, if any. Add `--skill-dir <path>` when the user names the skill, and `--records <dir>` when they say where its working records are. The script runs this skill's read-only scripts in order and prints one JSON object:

1. `check_repo_eligibility.py`: on a reject, nothing else runs.
2. `spec_clone_info.py`: settles STOP-1 ([2.6](../SKILL.md#26-pin-the-spec-clone)).
3. `inspect_existing_skill.py`: skills, their origin and records, harness, UTS-tagged tests.
4. `detect_liveobjects.py`: a one-line LiveObjects verdict.
5. `detect_capabilities.py`: the REST and Realtime capability profile, the sides, and the suggested scope (13.8), with eligibility's `capabilityOverride` if the repo is allow-listed.

The spec clone (the argument, else the one `spec_clone_info.py` found) is passed to the eligibility check and to both detectors, which read their names from it (13.8). A malformed data file in `assets/` (`DATA_FILE_ERROR`, naming the file and the key) stops Orient with `ok: false`: fix the file before anything else.

The JSON has `state` (class, re-entry, reasons, recommended option, options) and `stateSummaryText`. It gives a structured result that is the same under Claude Code and Codex. The facts behind it are in the other fields; `--full` adds the raw script outputs.

Settle the stops in this order, in as few messages as possible:

1. **STOP-16** (13.2), if the repo isn't plainly eligible.
2. **STOP-1** for the model (2.8) and for anything listed in `stop1`, such as the spec clone's path or a stale install of this skill.
3. **STOP-17** (13.8), when `stop17` is set: the capability profile needs confirming.
4. **STOP-13** (13.4).

If the user's request conflicts with the state (for example "create a skill" when one exists), say so at STOP-13.

## 13.2 Repository eligibility (STOP-16)

This procedure applies only to Ably Pub/Sub SDK repositories. `check_repo_eligibility.py <repo> [--spec-clone P]` decides from the repo's remotes, all of them, not only `origin`. Its rules are data in [`assets/eligibility.json`](../assets/eligibility.json) (owner, name pattern, deny-list, allow-list, canonical and planned names, the definition gate's threshold): when Ably adds, renames or retires a repository, update that file, not the script.

- **Name rule.** A `github.com/ably/<name>` remote whose name matches `^ably-(pubsub-[a-z0-9]+|[a-z0-9]+)$` (case-insensitive, without `.git` or a trailing `/`) is eligible.
  - Ably is renaming its SDK repositories from `ably-<lang>` to `ably-pubsub-<lang>` (`ably-js` is now `ably-pubsub-js`, and `ably-java` is now `ably-pubsub-java`). Both names are the same repository, and both are accepted. Old clones keep the old URL, which GitHub redirects.
  - `nameForm` reports `legacy`, `pubsub` or `allow-list`.
  - The script parses HTTPS, `ssh://` and scp-style (`git@github.com:ably/ably-js.git`) URLs, with the scheme and host in any case, resolves SSH host aliases from the local ssh config, and redacts credentials.
- **Canonical names**, reported only. `canonical` gives a renamed repository's current name: `ably-js`, `ably-java`, `ably-dotnet`, `ably-php`, `ably-python`, `ably-ruby`, `ably-flutter` and `ably-dart` are now `ably-pubsub-<lang>`, and `ably-ios` is now `ably-cocoa`. `plannedRename` gives a rename in preparation (`ably-cocoa` → `ably-pubsub-cocoa`, `ably-go` → `ably-pubsub-go`); either name is accepted. The one exception: a legacy name whose current name fails the name rule is rejected (`NOT_PUBSUB_SDK_NAME`). `ably-nativescript` is now `ably-js-nativescript`, a wrapper that re-exports ably-js.
- **Deny-list** (legacy single-token names only; `ably-pubsub-<x>` is never denied, but still has to pass the definition gate):
  - `common`, `specification`, `spec`, `cli`, `docs`, `ui`, `boomer`, `chat`, `spaces`, `objects`, `liveobjects`, `livesync`, `sandbox`, `proxy`;
  - `examples`, `example`, `website`, `www`, `laravel`, `terraform`, `pubsub`, `labs`, `demo`, `demos`, `dashboard`, `infra`, `control`, `mcp`, `status`;
  - `benchmark`, `benchmarks`, `test`, `tests`, `tools`, `scripts`, `ai`, `asset`, `assets`;
  - `brand`, `comply`, `jmeter`, `os`, `research`, `rss`, `scan`, `server`, `titanium`, `roku`, `nativescript`. These are tools, docs repositories and stubs that the name rule alone accepts. `ably-jmeter`, `ably-os` and `ably-server` *use* a client, so a usage-based check would accept them. `ably-titanium` is a README-only stub, and `ably-roku` implements no spec. `server` blocks only `ably-server`, never a server door inside an SDK repository (13.8). `nativescript` is a second guard for the wrapper above.

  These are known non-SDK `ably-<x>` repositories. Names with more hyphens, such as `ably-chat-swift`, `ably-chat-kotlin` and `ably-ai-transport-js`, already fail the name rule.
- **Allow-list:** `ably-ruby-rest` (the REST-only Ruby SDK) and its renamed form `ably-pubsub-ruby-rest`. These are explicit exceptions to the name rule. Each carries a `capabilityOverride` of REST `full` and realtime `absent`. The repository is a gem wrapping an `ably-ruby` git submodule whose entry point loads only `ably/rest`, so its own tree defines no client, and neither the gate nor the capability detector can see one. The override:
  - is reported as `capabilityOverride`;
  - satisfies the definition gate;
  - is passed by Orient to `detect_capabilities.py --capability-override`, whose profile then shows `source: override (allow-list)`, and drops the detected reasons for each level it sets;
  - is still confirmed by the user at STOP-17.
- **Definition gate**, checked after the name passes. A REST or Realtime client entry point must be *defined* in non-test source, not merely used. The gate counts only the scan's `gateTypes` (`detect_capabilities.py`, 13.8): client types declared in the repo (public or internal, including Go type aliases), plus door factories on a device or server side. It excludes functions (`def`, `func`, `fun`, `fn`, or any function that only returns or constructs another library's client), bindings (`var`, `let`, `const`, `val`, properties), and code under an `example(s)`, `sample(s)` or `demo(s)` path segment. Load tools and servers that import an SDK use a client but define none. `fingerprint` reports `sourceFiles`, `buildFiles`, `testRoot`, `clientDefinitions` (REST and Realtime) and `gate`. With no definition:
  - with at least `definitionGate.minSourceFilesToReject` (20) non-test source files, the decision is reject, `NO_CLIENT_DEFINITION`;
  - with fewer, it is ask, `NO_SDK_FINGERPRINT`: the wrong path, or a sparse checkout?
- **Eligibility isn't scope.** Only an allow-list override touches the capability profile. The scope comes from the SDK's capabilities ([13.8](#138-capabilities-and-scope-stop-17-d-31)).

| `decision` (`code`) | What you do |
|---|---|
| `accept` (`ELIGIBLE`) | Continue; nothing to ask. Show `canonical`, `plannedRename` and `capabilityOverride` in the State summary |
| `reject` (`NOT_PUBSUB_SDK_NAME`, `DENIED_NON_SDK`, `NOT_ABLY_REPO`, `NO_CLIENT_DEFINITION`) | **STOP-16, hard stop.** Show `message` exactly, for example "uts-to-lang-skill-creator currently supports only Ably Pub/Sub SDK repositories (ably-pubsub-&lt;lang&gt; or ably-&lt;lang&gt;). No workflow exists yet for ably/ably-chat-swift; the skill creator needs to be upgraded to support it." Then end the run. There is no override |
| `ask` (`FORK_CONFIRM`) | **STOP-16.** Only a fork's remote matches (`<user>/ably-js`). Ask the user to confirm it is a fork of `ably/<name>`; record the answer in the decision log once records exist |
| `ask` (`NO_REMOTE`, `NON_GITHUB_REMOTE`, `NOT_GIT_REPO`) | **STOP-16.** Ask which `github.com/ably` repository this is, and check the answer by the same rule. Adding a remote is the user's action |
| `ask` (`NO_SDK_FINGERPRINT`) | **STOP-16.** The name passes, but the few source files define no client: is this the right path, or a sparse checkout? |

## 13.3 State classes

The first match wins:

| Class | Rule (from `orient.py`) | Recommended |
|---|---|---|
| **INELIGIBLE** | `check_repo_eligibility.py` rejected the repo | Nothing: STOP-16 ends the run |
| **S4** ambiguous | More than one distinct `uts-to-*` skill; or a broken install (a dangling symlink, a `uts-to-*` directory without `SKILL.md`); or a skill whose language has no files in the repo; or finished records with no skill | No pre-selection: ask which skill is the target, and whether to repair the install first. With `--skill-dir`, Orient classifies only the named skill and lists the others under Problems |
| **S2** | One skill, with records from this procedure (`origin: creator-records`) | Upgrade/Fix, diff-driven; "Stop" if nothing changed since the recorded run |
| **S3** | One skill of unknown origin (hand-written, an older tool, or records not kept: `origin: unknown` or `creator-metadata`) | Upgrade/Fix, full gap audit |
| **S1** | No skill, but UTS-tagged tests or harness code (for example tagged tests in the SDK's native suite) | Create, keeping and matching the existing tests and harness |
| **S0** | Nothing | Create |

**Re-entry** is an overlay on any class: records from a run that didn't finish (their `Run status` is "in progress", or, for older records, there is a design record but no final report). It is offered first (13.6).

Some situations don't make a repo ambiguous:

- A skill installed only for one tool (only `.claude/skills`) isn't S4. It is a gap-audit row ("Installed for both tools").
- `uts-to-*` skills installed at user level are only reported.
- Other skills in the repo are listed by name only, so the user can say "that one is our translator" (then rerun with `--skill-dir`).

`origin` comes from evidence this procedure writes:

- `creator-records`: a design record (in `<skill>/generation/`, or the `--records` directory) whose header is "Design record: uts-to-…" and that names "uts-to-lang-skill-creator version".
- `creator-metadata`: the skill's `metadata.generated-by` stamp (13.7).

A version number alone proves nothing.

## 13.4 The State summary and STOP-13

Show `stateSummaryText`, completed with the session's model. Its layout:

```
WARNING      SPEC NAMES FALLBACK: the spec clone's IDL wasn't parsed; the LiveObjects and capability verdicts below are unreliable; settle it at STOP-1 first     (only on fallback)
Repo         <name> @ <sha8> (clean|dirty); languages: <counts>
Eligibility  accept: <owner>/<repo> via <remote> (<legacy|pubsub|allow-list> name)[; canonical <name>][; planned rename <name>][; capability override rest <level>, realtime <level>]
              | ask: <no remote | no github.com remote | not a git repo | a fork? | no client definition in few files>[ <owner>/<repo>] (<reason>); STOP-16
Spec clone   <path> @ <sha8> (clean|dirty); found by <how>; creator <version> (matches clone: <yes|no|unknown>)
Model        <name and ID> (Opus-class: yes|no)
Spec names   from the spec clone's IDL @ <sha8> | from the spec clone's IDL (revision unknown: not a git checkout)  |  FALLBACK, don't rely on the LiveObjects or capability verdicts: <warning>
Capabilities rest <full|partial|absent> (<clients>); realtime <full|partial|absent|unclear> (<clients>; connection …, channels …, presence …); <WebSocket transport | transport in the wrapped native SDKs | no WebSocket code>[; sides: <side> (rest yes|no, realtime yes|no), …][; source: override (allow-list)]
Method gaps  advisory, realtime partial (<n>): <spec point> <role>.<member>, …; likely deviations or not-implemented, decided per test, never out of scope     (only when realtime is partial)
Native SDK   wraps native SDKs over a platform bridge: hooks probably unreachable from the SDK language: unit tier only if hooks exist (P-13); integration and proxy still offered     (only if wrapsNativeSdk)
Side         <side>: rest <entry points | none>; realtime <entry points | none>     (one line per side; only for an SDK with doors)
              STOP-17 must ask which side the UTS tests construct clients through: (a) core/internal constructor (the sanctioned internal-access route), (b) server door, (c) device door, (d) both doors as a harness parameter; the scope follows the side (D-31)
Scope        <full|rest-only|realtime-only|unclear|none>: <modules> (objects per STOP-14)[; undecided: realtime, objects (ask at STOP-17)][; unsupported: <module> (<reason>)][; <n> capability-inapplicable test(s) or path(s)][; plus <n> REST-only test(s) under realtime][; partial skill, extendable by Upgrade/Fix]; confirm <with STOP-13 | at STOP-17>
Capability   changed since the recorded run: <item old -> new>, …[; added: <capabilities>][; lower than recorded: <capabilities>]     (only if it changed)
Skill        <path> [installs: …] name <name|missing>, version <v|none>, origin <creator-records|creator-metadata|unknown>     (one per skill)
              inspector hints: <f> fail, <w> warn, <p> pass (regex, not a review); mapping: <modules>; objects notes: <present|placeholder|none>
Harness      <from mapping | candidates: …>; smoke/self-test files: <n>[; offered tiers lacking them: <list> | unknown (some files don't name a tier)]
Records      <dir>: run <finished|in progress (Phase n)>; recorded spec <sha8>, repo <sha8>     (only if the skill has records)
Skills       none[; other repo skills: …]     (instead of the Skill lines, when there is no skill)
Harness      <candidates: … | none found>     (with "Skills none")
Problems     <broken installs, orphan records>          (only if any)
Changes      since recorded spec <sha8>: guide <n>, UTS docs <n>, helper specs <n>, corpus <n> files; checklist changed: <yes|no>[; repo <n> files]
UTS tests    <n> tags in <n> files (<dedicated|nativeSuite|mixed>); <module/tier counts>; header SHAs …; deviations.md: …
LiveObjects  <yes|no|unclear> (<confidence>): <summary> (decided at STOP-14)
User-level   <uts-to-* installs | none>
State        <class>[ + re-entry]: <reasons>
Recommended  <option>  |  none (S4): ask which skill
```

The **Spec names** line says where the detectors' names came from (13.8). "FALLBACK" means the spec clone's IDL couldn't be parsed, so the detectors used the data file's minimal names: the LiveObjects and capability verdicts are unreliable. Orient then also puts the **WARNING** line first, and adds the problem to `stop1` and `warnings`. Settle it at STOP-1 (fix the clone, or report the parser gap) before relying on either verdict; never go on silently with fallback names. "(revision unknown: not a git checkout)" means the names came from the IDL, but the clone isn't a git checkout, so the records can't pin its SHA: settle that at STOP-1 too.

The other optional lines: **Method gaps** (only when realtime is `partial`) and **Native SDK** (only when `wrapsNativeSdk`) come from the capability detector (13.8). The **Side** lines, and the side question under them, appear only when the SDK has device or server doors; the question's options depend on which doors exist (13.8). The **Capability** line appears only when the profile differs from the recorded one (13.8, "When the capability or the side changes later"). On an `ask`, the Eligibility line names the question and ends with STOP-16 (13.2).

Then **STOP-13**, always, in every run: the options for the class, with the recommended one marked, and a one-line reason ("Recommended: (1) Upgrade/Fix, full gap audit, because uts-to-kotlin has no records or provenance from this procedure"). Present the options as plain numbered text, so it works the same in Claude Code and Codex.

| Class | Options |
|---|---|
| S0 | (1) Create; (2) Stop |
| S1 | (1) Create, keeping and matching the existing tests and harness; (2) Stop |
| S2 | (1) Upgrade/Fix, diff-driven; (2) Upgrade/Fix, full gap audit; (3) Regenerate from scratch; (4) Stop |
| S3 | (1) Upgrade/Fix, full gap audit; (2) Regenerate from scratch (staged); (3) Stop |
| S4 | Upgrade/Fix one named candidate; Create a new skill; Repair the installs first (relink, reconcile copies; never delete without asking); Stop |
| + re-entry | (1) Resume from the phase the records show; (2) Restart (supersede the recorded decisions, keep the files); then the class's options |

Record the answer as D-27, with the state class.

## 13.5 Routing

| Choice | D-27 | Path |
|---|---|---|
| Create (S0, S1) | `create` | Phase 1 (STOP-2, then STOP-14) through Phase 7. Records at `.claude/skills/uts-to-<lang>/generation/`. For S1, P-20 records the existing tests and harness, and D-03, D-06 and D-07 are proposed to match them ([11.1](upgrade-existing-skill.md#111-when-this-mode-applies)) |
| Upgrade/Fix, full gap audit (S3, or S2 by choice) | `upgrade: full audit` | [Section 11](upgrade-existing-skill.md#11-upgrade-mode-audit-and-upgrade-an-existing-skill): U1 alongside Phase 1, STOP-2, STOP-14, U2 and STOP-15, then 11.5 and 11.6, then Phase 7 |
| Upgrade/Fix, diff-driven (S2) | `upgrade: diff-driven` | [Section 10](maintenance.md#10-maintenance): the recorded state, a scoped Phase 1, STOP-2, STOP-14, the detected changes as STOP-15 items, the targeted phases, Phase 7. It hands off to the full audit when the checklist changed or the user asks |
| S4: Upgrade/Fix one named candidate | `upgrade: diff-driven` if its origin is `creator-records`, else `upgrade: full audit` | As the matching row above, for that skill only (rerun Orient with `--skill-dir` to show its own State summary) |
| S4: Repair the installs first | — | Propose each change (relink, reconcile copies; never delete without asking), apply only the ones the user approves, then rerun Orient |
| S4: Create a new skill | `create` | As Create |
| Regenerate from scratch | `upgrade: regenerate` | U1, then the create flow, staged ([11.5](upgrade-existing-skill.md#115-step-u4-run-the-phases-scoped)) |
| Resume or restart | the recorded D-27, plus "resumed" or "restarted" with the date | 13.6 |

The records for Upgrade/Fix go where Orient found them; otherwise to `<existing-skill-dir>/generation/` (D-24). Copy the State summary into the Repo profile when the records are created.

## 13.6 Re-entry: resume or restart

When Orient finds records with `Run status: in progress`, offer:

- **Resume:** read the records and continue from the phase their Run status names. D-27 keeps its recorded value. STOP-14 is asked again only if D-28 isn't recorded yet. If the spec clone's SHA has moved since the records were written, Orient adds the re-entry reason "spec moved since the records: ask about restarting (13.6)"; ask whether to restart from the new SHA (2.6).
- **Restart:** supersede the recorded decisions in the decision log, keep every file, and start again from Phase 1 in the mode chosen now. Picking one of the class's options instead of Resume means Restart in that mode.

## 13.7 Provenance (D-30)

So that a later Orient can tell this procedure's skills from others (S2 vs S3), the procedure writes two kinds of evidence. Both are a *procedure recommendation*.

- **The skill's frontmatter** carries `metadata.generated-by: "uts-to-lang-skill-creator <version> @ <spec-sha8>"`, and `metadata.records: "<repo-relative records dir>"` (or `"not kept"`). Both are strings, so they stay portable (guide 3.3). Phase 7 refreshes them.
- **The design record** carries a `Run status` line: "in progress (Phase n)" from STOP-13 on, updated at each phase end, and "finished" at Phase 7.

## 13.8 Capabilities and scope (STOP-17, D-31)

The harness and the skill cover what the SDK can do, not what its name suggests (guide [section 2](../../../docs/writing-uts-spec-translator-skills.md#2-the-harness-uts-test-infrastructure)). `detect_capabilities.py <repo> [--spec-clone P] [--include-submodules] [--capability-override rest=full,realtime=absent]` (Orient runs it; an unknown capability or a level not valid for it is `USAGE_ERROR`, naming the valid levels) finds:

- **The REST client**, with its key members (`request`, `stats`, `time`, …) and a REST channel (`publish`, `history`, …).
- **The Realtime client**, with three sub-areas, each `present`, `stub` or `absent`. A sub-area is `present` only when its own files declare at least one of its key members (not a generic one); its names declared with no such member are `stub`:
  - connection (`Connection`, `ConnectionStateChange`, `ping`, `createRecoveryKey`, …);
  - channels (`RealtimeChannel`, `ChannelStateChange`, `attach`, `detach`, …);
  - presence (`RealtimePresence`, `enter`, `enterClient`, …).

  It also looks for WebSocket transport evidence.

**Names come from the spec, at run time.** `spec_names.py` reads them from the spec clone, so the detectors follow the spec when it renames something. It parses the IDL sections ("Interface Definition") of `specifications/features.md` and `specifications/objects-features.md`:

- a type's role comes from its spec-point prefix: `RSC` REST client, `RTC` Realtime client, `RSL` REST channel, `RTL` and `TH` Realtime channel, `RTP` presence, `RTN` and `TA` connection;
- a client's base name drops `Client` (`RestClient` → `Rest`), as the UTS pseudocode writes it;
- each role's key members are its methods, each with its spec point; names too generic to search for (`get`, `subscribe`, …) are left out.

Both detectors report `namesSource` (`spec` or `fallback`), `specRevision` (the clone's SHA and whether it is dirty), `namesFrom` (the IDL line each role came from), `dataFile` and `warnings`. If the IDL can't be parsed, `namesSource` is `fallback`: the minimal names in the data file's `fallback` are used, with a warning, `confirmAtStop17` is set, and Orient's Spec names line says FALLBACK (13.4). The corpus-derived test lists (below) are computed separately, so they survive a fallback, with their own warning if the corpus can't be read. A clone outside git gives an unknown `specRevision`, with a warning. `spec_names.py [--spec-clone P]` prints every derived name.

Names the spec can't give live in [`assets/capability-names.json`](../assets/capability-names.json):

- SDK aliases for renamed clients (`PubSubHttpClient`, `PubSubRealtimeClient`, `PubSubClient`, from ably-dotnet's 2.0 split SDK);
- door factories, and how their sides are recognised;
- LiveObjects names from earlier spec revisions, or given only in the spec's prose ([12.1](liveobjects-support.md#121-gather-the-evidence-step-1b-p-15)).

When an SDK adds an alias or a door, or the spec renames something its IDL doesn't show, update that file, not the code.

**How the scan matches.** It counts definitions, never usages, in non-test, non-example, non-vendored source (submodules only with `--include-submodules`):

- spec names in their per-language spellings: a short all-caps prefix (`ART`, `I`), the prefixes `Ably`, `PubSub`, `Base` and `Default`, the suffixes `Protocol` and `Interface`, and snake_case;
- Go constructors (`NewREST`) and type aliases (`type HTTPClient = ably.REST`);
- members in any case, in snake_case, and without an `Async` suffix, including typed-return declarations (Dart's `Future<void> enter(`, Java's package-private `void attach()`);
- a bare `Client`, `Channel`, `Connection` or `Presence`, only under a `rest`, `realtime` or `http` path segment (Ruby's `Ably::Realtime::Client`);
- door factories (below).

**Public reachability.** A client counts as public if its type is public, or if a public function, factory or property returns it (dotnet 2.0's `PubSubServer.CreateHttpClient`). Constructor visibility doesn't matter: a client whose constructor is internal, or refuses direct construction, still counts when a public factory returns it.

**Sides and doors.** SDKs split for 2.0 expose their clients through **door factories**: a server door (in ably-dotnet's 2.0 branch, `PubSubServer.CreateHttpClient` and `CreateRealtimeClient`) and a device door (`PubSubDevice.CreateClient`, Realtime only). Each side reaches a different set of clients.

- A door's side comes from its enclosing door type (`PubSubDevice`, `PubSubServer`), or else from a path segment (`Ably.PubSub.Device`, `pubsub-device`). Its capability comes from its return type, or else its name (`Http` or `Rest` means REST).
- Sides come only from doors. A client type under a `device` path (push `LocalDevice` code, as in ably-cocoa and ably-dotnet 1.x) isn't a side.
- When a device or server door exists, `sides` lists `core` (the client types themselves, reached through the sanctioned internal-access route) and each door side, with the REST and Realtime entry points it reaches. Otherwise `sides` is null, and there is no side question.

For example, ably-dotnet's 2.0 branch reports core (REST and Realtime), server (REST and Realtime) and device (Realtime only).

**Levels:**

- **rest:** `full` (a public client, two of its key members, and a REST channel), `partial` or `absent`.
- **realtime:** `full` (a public client, all three sub-areas present, and transport evidence: WebSocket code, or `wrapsNativeSdk`), `partial`, `absent`, or `unclear` (a client is declared, but it isn't public and no public factory returns it). A weak realtime, `partial` with connection and channels both absent and no REST client (a Python-like SDK whose naming the scan misses, or a bare `Realtime` class with nothing around it), gets scope kind `unclear` too, never `realtime-only` (unless an override sets realtime).
- **`methodGapsAdvisory`**, only when realtime is `partial`: the spec members of connection, channels and presence that weren't found, with their spec points (for example `RTN13 connection.ping`). Naming variants make it noisy, so it is advisory only.
- **`wrapsNativeSdk`:** the SDK wraps native SDKs over a platform bridge (a Flutter plugin's `MethodChannel`), so its test hooks are probably unreachable from its own language (P-13). It counts as transport evidence, because the native SDK carries the transport.
- **`source`:** `detected`, or `override (allow-list)` (13.2).

**The scope suggestion.** `scopeSuggestion` has `kind`, `modules`, `unsupported` (module → reason), `capabilityInapplicable` (Test IDs or spec paths), `extraTests` (Test IDs), `undecided` (only when `unclear`) and `confirmAtStop17`. The test lists are derived at run time from the corpus (each test's `Rest(...)` and `Realtime(...)` constructions), so read them from the output, not from this page.

| Profile | `kind` | Scope suggestion |
|---|---|---|
| rest and realtime `full` | `full` | `rest` and `realtime`; `objects` per STOP-14 |
| realtime `absent` (a REST-only SDK, such as `ably-ruby-rest`, PHP or Rust) | `rest-only` | **Partial skill**: `rest`, plus the `extraTests`, with a REST-only harness. `unsupported`: `realtime` and `objects`. `capabilityInapplicable`: the REST tests that need a Realtime client |
| rest `absent`, realtime present (a realtime-only SDK, such as a device build) | `realtime-only` | **Partial skill**: `realtime`, and `objects` per STOP-14, with the realtime harness. `unsupported`: `rest`. `capabilityInapplicable`: the realtime tests that need a REST client |
| realtime `partial`, presence `absent` | `full` (or `realtime-only`) | `rest` and `realtime` (or `realtime` alone), with the presence spec paths in `capabilityInapplicable`: the presence specs under `uts/realtime` (`presenceSpecs`: `presence/` directories and files named for presence), found in the corpus at run time. A `stub` presence is flagged at STOP-17, where the user can treat it the same way |
| realtime `full`, with method-level gaps the detector doesn't report (as in Python) | `full` | `rest` and `realtime`. The gaps (for example RTP12, RTN16, RTL25, RTB1) are decided per test (guide [7.4](../../../docs/writing-uts-spec-translator-skills.md#74-language-inapplicable-inputs) case (c), Missing API): likely deviations or not-implemented features, never out of scope |
| realtime `partial` with connection or channels absent or stubbed | `full` | Flag it at STOP-17: mark `realtime` unsupported, or keep it and let Phase 2 mark the tiers unready |
| realtime `unclear` (internal-only) | `unclear` | `rest`; `undecided`: `realtime` and `objects`. Ask at STOP-17 whether the declared client is reachable (public elsewhere, or through the sanctioned internal-access route). Never decided as REST-only |
| rest `absent`, realtime `partial` with connection and channels absent (weak realtime) | `unclear` | No modules; `undecided`: `realtime` and `objects`. Ask at STOP-17 what the SDK offers (the scan may miss its naming); never decided as realtime-only |
| no public client | `none` | Probably the wrong path: STOP-16 ask |

On the current corpus, the lists are:

- **REST tests that need a Realtime client** (13): the three RSC24 tests in `rest/integration/batch_presence.md`; RSP4, RSP4b1, RSP4b2, RSP4b3 and RSP5 in `rest/integration/presence.md`; RSA17g and RSA17c in `rest/integration/revoke_tokens.md`; REC3a, REC3b and REC3 in `rest/unit/fallback.md`.
- **Realtime tests that need a REST client** (4): RSA9a and RSA9 in `realtime/integration/auth/token_request_test.md`; RTN15h1 in `realtime/integration/proxy/connection_resume.md`; RTL6 in `realtime/integration/proxy/rest_faults.md`.
- **REST-only tests filed under `uts/realtime`** (`extraTests`, 3): RSC10 and RSC15m in `realtime/integration/proxy/rest_faults.md`, and RSA4e in `realtime/unit/auth/auth_callback_errors_test.md`. A REST-only skill translates these too.

**Wrappers over native SDKs** (`wrapsNativeSdk`, such as a Flutter plugin). The capability is full, but the hooks live in the wrapped native SDKs. Phase 1 checks whether they are reachable from the SDK's language (P-13); if they aren't, that is a harness gap, and the unit tier is offered only once hooks exist ([4.8](phase-2-design-harness.md#48-step-2h-derive-tier-feasibility)). The integration and proxy tiers are still offered.

**STOP-17** is asked, in the same message as STOP-13 and before the mode options, when `confirmAtStop17` is set or the profile differs from the recorded D-31. `confirmAtStop17` is set when the profile isn't full, is unclear, has sides, wraps native SDKs, comes from an allow-list override, or its names come from the fallback. Otherwise the user confirms the profile with their STOP-13 answer. Show the profile with its evidence, the suggested scope, the `reasons`, and the delta if any. The options are:

- (1) accept the suggested scope;
- (2) correct a capability, giving evidence, and rerun;
- (3) stop.

**The side question**, asked at STOP-17 only when `sides` has a server or device door: through which side do the UTS tests construct clients? Orient prints it under the Side lines, and in `stop17`, with options lettered from the doors found. With both doors:

- (a) the core/internal constructor, through the sanctioned internal-access route (guide [5.9](../../../docs/writing-uts-spec-translator-skills.md#59-internal-access-white-box-unit-specs); for example `InternalsVisibleTo` for the UTS test project);
- (b) the server door;
- (c) the device door;
- (d) both doors, as a harness parameter: one suite, run once per side.

With one door, the options are (a) the core/internal constructor, (b) that door, and (c) the core and that door as a harness parameter.

Show each side's entry points from the Side lines, and let the user choose. Another SDK's per-side switch (on a branch, ably-cocoa runs its UTS through either its core or its device factory, chosen by an environment variable) is only evidence that a harness-parameter option works. Design this SDK's own; never copy it ([2.1](../SKILL.md#21-your-inputs)).

**The scope follows the chosen side.** A side without a REST client (usually the device door) gives a `realtime-only` scope, and a side with both clients gives `full`. With the harness-parameter option, the scope is the union, and a test one side can't run is capability-inapplicable on that side's run.

Record the result as **D-31**, as one parseable line in the design record. Record the levels detected for the whole repository, not for the chosen side, so that a later Orient compares like with like; the side and the scope carry the choice. For example:

```
- Capabilities (D-31): rest full; realtime absent; liveobjects no; side: none; scope: rest-only (rest + 3 REST-only tests under realtime); unsupported: realtime, objects (capability absent); capability-inapplicable: 13 tests (listed in the rest notes); names: spec
- Capabilities (D-31): rest full; realtime full; liveobjects no; side: device (no REST client); scope: realtime-only (realtime); unsupported: rest (not on the device side); capability-inapplicable: 4 tests (listed in the realtime notes); names: spec
```

**What `unsupported` and capability-inapplicable mean:**

- **Mapping.** A module the scope excludes keeps its entry with the D-03 default paths (so the skill's step B never offers `--create`), and carries `"unsupported": "<reason>"`, for example `"capability absent: no realtime client (D-31)"`. Tests or specs that need a client the SDK (or the chosen side) lacks go under the module's `"capabilityInapplicable": {"<Test ID or spec path relative to the module>": "<reason>"}`. A REST-only skill's `realtime` entry also lists the `"extraTests"`. The resolver's behaviour for each key is in [7.1](phase-5-generate-skill.md#71-step-5a-create-the-layout-and-the-mapping-file).
- **Tests.** A capability-inapplicable test is guide [7.4](../../../docs/writing-uts-spec-translator-skills.md#74-language-inapplicable-inputs) case (d). It is noted in the test file, or left out of the selection by the mapping, and listed in the module notes. It isn't a deviation, never goes in `deviations.md`, and doesn't count as a coverage gap.
- **Harness.** Gap-table rows that need an absent capability are `n/a — capability absent: <capability> (D-31)`. For a REST-only SDK these are:
  - wholly n/a: G-01 (WebSocket hook), G-04 (network monitor), G-07 (`MockWebSocket`), G-08 (`MockVCDiff`), G-09 (`MockNetworkListener`), G-10 (objects pool);
  - partly n/a: G-05 (jitter; host shuffle still applies), G-11 (`AWAIT_STATE`), G-16 (WebSocket frame rules; the HTTP rules apply), and G-19/G-20 (built in their REST form, [4.8](phase-2-design-harness.md#48-step-2h-derive-tier-feasibility)).

  For a realtime-only SDK, no row is wholly n/a: the Realtime client still uses HTTP (auth, time, history, `request()`, fallback), so G-02 (HTTP hook) and G-06 (`MockHttpClient`) are still needed. Only the `rest` tiers' smoke tests in G-19 are n/a.
- **Harness README.** Its Known gaps lists the constructs of the unsupported modules, so the skill's preflight refuses a spec that uses them ([5.3](phase-3-build-harness.md#53-step-3c-write-the-harness-readme)).
- **Acceptance checklist.** A row that wholly needs the absent capability is `n/a — capability absent: <capability> (D-31)`. A row with only some parts affected is ✓ with those parts named as n/a. n/a never counts as ✗; a scope the user chose to cut still is ✗.
- **LiveObjects.** STOP-14 is still asked. With no Realtime client it recommends "no", with the reason "capability absent: no realtime client".

**When the capability or the side changes later.** Orient compares the current profile with the recorded one (the D-31 line, completed by the mapping's `unsupported` markers; for records with no D-31 line, the levels inferred from the mapping). `inspect_existing_skill.py` reports that recorded profile as `capabilityProfile`: it parses the D-31 line and reads each mapping module's `unsupported`, `capabilityInapplicable` and `extraTests`, and also the legacy keys `notApplicable` and `notApplicableSpecs` (listed as `legacyKeys`); `levelsInferred` says the levels came from the mapping, not from D-31. It reports `capabilityDelta` as `{changes, added, lowered}`, or null when nothing changed:

- `changes`: each differing item, `"old -> new"`. The REST and Realtime levels are always compared, because D-31 records the whole repository's levels. `side` changes when doors appear, disappear, or the recorded side is no longer among them. The scope kind (`scope`) and the `unsupported` modules depend on the chosen side, so they are compared only when no side was recorded and the repo has no doors now.
- `added`: capabilities now higher than recorded, or modules no longer unsupported (not `objects`, which follows realtime and STOP-14 decides).
- `lowered`: capabilities lower than recorded, or modules newly unsupported: a detector miss, or really removed? Ask for evidence at STOP-17.

Any change makes STOP-17 ask, and the State summary shows the Capability line. On S2 (not re-entry), a change recommends Upgrade/Fix, diff-driven, never "Stop". The change item "capability added: <capability>" ([section 10](maintenance.md#10-maintenance)):

- supersedes D-31;
- removes `unsupported`, and the `capabilityInapplicable` entries the new client makes runnable, and maps the new tiers;
- turns the G-rows and checklist parts that were n/a for that capability into gaps;
- asks STOP-14 again.

A change of side (for example, the user now wants the server door, or both) is a change item of the same kind: it supersedes D-31, and the scope follows the new side.
