# 13. Step 0: Orient

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention). Links that climb out of the skill directory are spec-repo paths: resolve them against the spec clone, not against this file's installed location.

**Goal:** before anything else, in every run, establish five things:

- that the repository is one this procedure supports;
- what it already has;
- its REST and Realtime capability profile and the skill's scope (STOP-17, D-31);
- which mode to run in (**Create** or **Upgrade/Fix**);
- for Upgrade/Fix, which existing skill to work on.

Orient is read-only and quick. It builds nothing, runs no tests, touches no network and writes no file. The spec-clone sync after STOP-16 (13.9) is separate. The working records are created only after STOP-13, because their location depends on the answer (D-24).

Contents:

- [13.1 Run it](#131-run-it)
- [13.2 Repository eligibility (STOP-16)](#132-repository-eligibility-stop-16)
- [13.3 State classes](#133-state-classes)
- [13.4 The State summary and STOP-13](#134-the-state-summary-and-stop-13)
- [13.5 Routing](#135-routing)
- [13.6 Re-entry: resume or restart](#136-re-entry-resume-or-restart)
- [13.7 Provenance (D-30)](#137-provenance-d-30)
- [13.8 Capabilities and scope (STOP-17, D-31)](#138-capabilities-and-scope-stop-17-d-31)
- [13.9 Sync the spec clone](#139-sync-the-spec-clone)

## 13.1 Run it

Run `python3 <skill-dir>/scripts/orient.py <repo> [--spec-clone <path>]`. Pass the spec clone the user named, if any. Add `--skill-dir <path>` when the user names the skill, `--capability-override rest=<level>,realtime=<level>` or `--side <core|server|device|both>` when the user corrects a capability or chooses the side at STOP-17 (13.8), `--records <dir>` when they say where its working records are (with `--skill-dir`, it applies to the named skill only), `--include-submodules` to scan submodule sources too, and `--full` for the raw script outputs. The script runs this skill's read-only scripts in order and prints one JSON object:

1. `spec_clone_info.py`: resolves the spec clone every other script reads, offline ([2.6](../SKILL.md#26-pin-the-spec-clone)).
2. `check_repo_eligibility.py`, with or without a clone: on a reject, nothing else runs.
3. `inspect_existing_skill.py`: skills, their origin and records, harness, UTS-tagged tests.
4. `detect_liveobjects.py`: a one-line LiveObjects verdict.
5. `detect_capabilities.py`: the REST and Realtime capability profile, the sides, and the suggested scope (13.8), with eligibility's `capabilityOverride` if the whitelist gives one.

The clone `spec_clone_info.py` resolved (the argument, walked up to the clone root, else the clone this skill is installed from, else `ABLY_SPEC_CLONE`, else the shared default `~/.ably/specification`; 13.9) is passed to the eligibility check and to both detectors, which read their names from it (13.8); the State summary's Spec clone line shows that path. An explicit path (the argument or `ABLY_SPEC_CLONE`) that isn't in a clone stops Orient with `NOT_A_SPEC_CLONE`: it is never replaced by another clone. When no clone is found, Orient still runs the eligibility check, so STOP-16 is settled before any offer to clone one. A malformed data file in `assets/` (`DATA_FILE_ERROR`, naming the file and the key) stops Orient with `ok: false`: fix the file before anything else ([Maintaining this skill](../SKILL.md#maintaining-this-skill)).

`spec_clone_info.py [<spec-clone> | --spec-clone <path>]` checks that the guide, this skill, the UTS docs and the helper specs exist, reads the clone's git state offline (`ensure_spec_clone.py`'s status: branch, tracked changes, the last fetch of `origin/main`), and runs `git log -1 --format='%H %cd'` on the guide and this skill ([2.6](../SKILL.md#26-pin-the-spec-clone) says what to record). Its outcomes:

- `SPEC_CLONE_NOT_FOUND` (nothing at `ABLY_SPEC_CLONE`, or at the default): after STOP-16, the STOP-1 bootstrap offer (13.9).
- `SPEC_CLONE_INCOMPLETE` (a revision that predates the guide or this skill): STOP-1, with the script's message (13.9).
- Any other `ok: false` (`NOT_A_SPEC_CLONE`, `SPEC_CLONE_ENV_CONFLICT`, `GIT_ERROR`): STOP-1; ask for the clone's path.
- `foundBy` other than `argument`: shown in the State summary (with the clone's kind) and confirmed with the STOP-13 answer.
- `skillMatchesClone: false` (an installed copy that differs from this clone's copy of the skill, also reported in `warnings`): STOP-1; ask the user to refresh the install, or to confirm which version to follow.

The JSON has `state` (class, re-entry, reasons, recommended option, options), the State summary in two forms (`stateSummaryMarkdown`, shown before the questions, and `stateSummaryText`, pasted into the Repo profile; 13.4), `specCloneWarning`, `stop17` (why STOP-17 may be asked) and `infraPlan` (13.8). It also has Orient's questions, ready to ask in the [asking.md](asking.md) format:

- `questions.now`: STOP-13, then any STOP-17 question needed whatever the run mode;
- `questions.followUp`: STOP-17 questions only some run modes need, each with `askIf`, the STOP-13 options that need it;
- `questionsMarkdown`, the Markdown form of `questions.now`, and `askUserQuestion`, its Claude Code tool form (null where it doesn't fit);
- `followUpByOption`: for each STOP-13 option in an `askIf`, the follow-up message with only the questions that option needs, numbered from 1, in both forms.

The facts behind them are in the other fields.

If Orient stopped with `NOT_A_SPEC_CLONE`, settle the clone's path (STOP-1) and rerun Orient first. Then show the State summary and settle the stops in this order, as [asking.md](asking.md) lays out: one question per decision, numbered in the order asked, in plain words, with one reply line at the end of each message:

1. **STOP-16** (13.2), if the repo isn't plainly eligible.
2. **The spec-clone sync** (13.9), as `specSync` describes; rerun Orient if it moved HEAD or created the clone.
3. **STOP-1** for the model (2.8) and for anything listed in `stop1`, such as the spec clone's path or a stale install of this skill.
4. **STOP-13** (13.4), the run mode: always.
5. **STOP-17** (13.8), the UTS infrastructure plan, only while it is open: the capability profile needs confirming, or the side isn't settled. The run mode decides whether the plan matters (an Upgrade/Fix run audits the existing harness; Create and Regenerate plan a new one), so a STOP-17 question that depends on the STOP-13 answer goes in a follow-up message (`followUpByOption`, for the option chosen), asked only if the answer needs it. One that doesn't depend on it follows STOP-13 in the same message (`questions.now`). Clarity comes before saving a round trip.

Ask the stops that come first in the same message as STOP-13 when they don't change Orient's output, and renumber its questions to follow them.

If the user's request conflicts with the state (for example "create a skill" when one exists), say so at STOP-13.

## 13.2 Repository eligibility (STOP-16)

This procedure applies only to the Ably Pub/Sub SDK repositories on the whitelist in [`assets/eligibility.json`](../assets/eligibility.json). Every other repository is rejected. Adding a new SDK repository means adding its name there, not changing the script. `check_repo_eligibility.py <repo> [--spec-clone P]` decides from the repo's remotes, all of them, not only `origin`.

- **Whitelist.** A `github.com/ably/<name>` remote is eligible when `<name>` is in `repositories` (case-insensitive, without `.git` or a trailing `/`).
  - The list holds both names of a renamed repository: Ably is renaming its SDK repositories from `ably-<lang>` to `ably-pubsub-<lang>` (`ably-js` is now `ably-pubsub-js`), and old clones keep the old URL, which GitHub redirects.
  - It also holds the target of a rename in preparation, so a clone keeps working after the rename.
  - `nameForm` reports `current`, `legacy` (a key of `canonical`) or `planned` (a value of `plannedRename`).
  - The script parses HTTPS, `ssh://` and scp-style (`git@github.com:ably/ably-js.git`) URLs, with the scheme and host in any case, resolves SSH host aliases from the local ssh config, and redacts credentials.
  - The data file is checked on load: every name in `capabilityOverride`, `canonical` and `plannedRename` must be in `repositories`.
- **Canonical names**, reported only. `canonical` gives a renamed repository's current name (`ably-java` → `ably-pubsub-java`, `ably-ios` → `ably-cocoa`). `plannedRename` gives a rename in preparation (`ably-cocoa` → `ably-pubsub-cocoa`).
- **Capability override.** `ably-ruby-rest`, the REST-only Ruby SDK, carries a `capabilityOverride` of REST `full` and realtime `absent`. The repository is a gem wrapping an `ably-ruby` git submodule whose entry point loads only `ably/rest`, so its own tree defines no client, and neither the gate nor the capability detector can see one. The override:
  - is reported as `capabilityOverride`;
  - satisfies the definition gate;
  - is passed by Orient to `detect_capabilities.py --capability-override`, whose profile then shows `source: override (whitelist)`, and drops the detected reasons for each level it sets;
  - is still confirmed by the user at STOP-17.
- **Definition gate**, a secondary check after the whitelist. A REST or Realtime client entry point must be *defined* in non-test source, not merely used. The gate counts only the scan's `gateTypes` (`detect_capabilities.py`, 13.8): client types declared in the repo (public or internal, including Go type aliases), plus door factories on a device or server side. It excludes functions (`def`, `func`, `fun`, `fn`, or any function that only returns or constructs another library's client), bindings (`var`, `let`, `const`, `val`, properties), and code under an `example(s)`, `sample(s)` or `demo(s)` path segment. `fingerprint` reports `sourceFiles`, `buildFiles`, `testRoot`, `clientDefinitions` (REST and Realtime) and `gate`. With no definition:
  - with at least `definitionGate.minSourceFilesToReject` (20) non-test source files, the decision is reject, `NO_CLIENT_DEFINITION`;
  - with fewer, it is ask, `NO_SDK_FINGERPRINT`: the wrong path, or a sparse checkout?
- **Eligibility isn't scope.** Only a capability override touches the capability profile. The scope comes from the SDK's capabilities ([13.8](#138-capabilities-and-scope-stop-17-d-31)).

| `decision` (`code`) | What you do |
|---|---|
| `accept` (`ELIGIBLE`) | Continue; nothing to ask. Show `canonical`, `plannedRename` and `capabilityOverride` in the State summary |
| `reject` (`NOT_WHITELISTED`, `NOT_ABLY_REPO`, `NO_CLIENT_DEFINITION`) | **STOP-16, hard stop.** Show `message` exactly, for example "uts-to-lang-skill-creator supports only the Ably Pub/Sub SDK repositories listed in assets/eligibility.json. ably/ably-chat-swift isn't one of them; supporting it requires updating the skill creator." Then end the run. There is no override |
| `ask` (`FORK_CONFIRM`) | **STOP-16.** Only a fork's remote matches (`<user>/ably-js`). Ask the user to confirm it is a fork of `ably/<name>`; record the answer in the decision log once records exist |
| `ask` (`NO_REMOTE`, `NON_GITHUB_REMOTE`, `NOT_GIT_REPO`) | **STOP-16.** Ask which `github.com/ably` repository this is, and check the answer by the same rule. Adding a remote is the user's action |
| `ask` (`NO_SDK_FINGERPRINT`) | **STOP-16.** The repository is on the whitelist, but the few source files define no client: is this the right path, or a sparse checkout? |

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

**Re-entry** is an overlay on any class: records from a run that didn't finish (their `Run status` is "in progress"). It is offered first (13.6). Records written before the `Run status` line existed count as unfinished when there is no `final-report.md`; `inspect_existing_skill.py` also reads the older mapping keys `notApplicable` and `notApplicableSpecs`, reported as `legacyKeys`.

Some situations don't make a repo ambiguous:

- A skill installed only for one tool (only `.claude/skills`) isn't S4. It is a gap-audit row ("Installed for both tools").
- `uts-to-*` skills installed at user level are only reported.
- Other skills in the repo are listed by name only, so the user can say "that one is our translator" (then rerun with `--skill-dir`).

`origin` comes from evidence this procedure writes:

- `creator-records`: a Design record (in `<skill>/generation/`, or the `--records` directory) whose header is "Design record: uts-to-…" and that names "uts-to-lang-skill-creator version".
- `creator-metadata`: the skill's `metadata.generated-by` stamp (13.7).

A version number alone proves nothing.

## 13.4 The State summary and STOP-13

Show `stateSummaryMarkdown`, completed with the session's model, before the questions. It is Orient's facts as a two-column table that wraps cleanly in a terminal, in plain words ([asking.md](asking.md)), with each warning first, as a bold line starting with ⚠:

- **Spec clone not synced** (`specCloneWarning`, for a clone that isn't the shared clone, 13.9). It says what this run reads from that clone (the guide, UTS docs, helper specs, corpus and features specs) and that it won't be updated. It has two forms:
  - a *notice* when the clone has `main` checked out, with no tracked changes and no local commits: where it is, and how far behind `origin/main` it was at the last fetch;
  - a *warning* ("…, and not on main", "…, and not on origin/main", "…, and has tracked changes") when the clone is on another branch or a detached HEAD, carries commits not on `origin/main`, or has tracked changes. It gives the branch and the ahead/behind counts, says the harness, the construct catalogue and the records will follow that clone, and that the STOP-13 answer confirms using it. Untracked files don't count: notes in the clone aren't specs (2.6).
- **Stale spec clone**, for the shared clone only: the last fetch is over 30 days old, or unknown (13.9).
- **Spec names fallback** (below).

The table's rows, in order: Repo, Eligibility, Spec clone, Sync, Creator, Model, Spec names, Capabilities, Method gaps, Native SDK, Sides, Client setup, Scope, Plan, Capability change, Skill, Skill hints, Harness, Records (or Skills and Harness when there is no skill), Problems, Changes, UTS tests, LiveObjects, User-level, State, Recommended. Optional rows appear only when they apply, as in the text form below. Each line of a value is at most 70 characters, so the table wraps less in a narrow terminal: a longer value continues on the next rows with an empty Field, broken at a "; ", a ", " or a space (never inside a code span), and never cut; only a single word or code span longer than that stays whole on its line. An empty value shows "—". The State row shows the first reason with "(+N more)"; the text form and `state.reasons` have them all. For an ineligible repo, `stateSummaryMarkdown` is the single bold line "⚠ Not eligible." with the script's message.

The table carries every fact in short form; the fixed-width text, `stateSummaryText`, spells each one out (for example every module and tier count, the deviations.md paths, the LiveObjects summary), and it is what the Repo profile records. Its layout:

```
WARNING      SPEC CLONE NOT SYNCED[, AND <NOT ON MAIN | NOT ON ORIGIN/MAIN | HAS TRACKED CHANGES>[ AND HAS TRACKED CHANGES]]: <what this run reads from <the spec clone you named | the clone this skill is installed from> (<path>), its branch and drift>     (only for a clone that isn't the shared clone, 13.9)
WARNING      STALE SPEC CLONE: <staleWarning>; offer the sync at STOP-6 (13.9) | the sync is off (ABLY_SPEC_SYNC=off)     (only for the shared clone, when the last fetch is over 30 days old, or unknown)
WARNING      SPEC NAMES FALLBACK: the spec clone's IDL wasn't parsed; the LiveObjects and capability verdicts below are unreliable; settle it at STOP-1 first     (only on fallback)
Repo         <name> @ <sha8> (clean|dirty); languages: <counts>
Eligibility  accept: <owner>/<repo> via <remote> (<current|legacy|planned> name)[; canonical <name>][; planned rename <name>][; capability override rest <level>, realtime <level>]
              | ask: <no remote | no github.com remote | not a git repo | a fork? | no client definition in few files>[ <owner>/<repo>] (<reason>); STOP-16
Spec clone   <path> @ <sha8> (clean|dirty); <shared clone | named clone | skill clone (not the shared clone) | …>; branch <name> | detached; found by <how>; creator <version> (matches clone: <yes|no|unknown>)
              HEAD committed <n> days ago; <a> ahead / <b> behind origin/main as of the last fetch (<n> days ago)  |  origin/main: unknown (never fetched); sync: <what 13.9 will offer> | not synced (not the shared clone)
              | NOT FOUND (SPEC_CLONE_NOT_FOUND): no clone at <path>; after STOP-16, offer to clone it there …  |  NOT USABLE (<code>): <message>; settle it at STOP-1  |  <path> (not usable: <code>: <message>)
Model        <name and ID> (Opus-class: yes|no)
Spec names   from the spec clone's IDL @ <sha8> | from the spec clone's IDL (revision unknown: not a git checkout)  |  FALLBACK, don't rely on the LiveObjects or capability verdicts: <warning>
Capabilities rest <full|partial|absent> (<clients>); realtime <full|partial|absent|unclear> (<clients>; connection …, channels …, presence …); <WebSocket transport | transport in the wrapped native SDKs | no WebSocket code>[; sides: <side> (rest yes|no, realtime yes|no), …][; source: override (whitelist)]
Method gaps  advisory, realtime partial (<n>): <spec point> <role>.<member>, …; likely deviations or not-implemented, decided per test, never out of scope     (only when realtime is partial)
Native SDK   wraps native SDKs over a platform bridge: hooks probably unreachable from the SDK language: unit tier only if hooks exist (P-13); integration and proxy still offered     (only if wrapsNativeSdk)
Side         <side>: rest <entry points | none>; realtime <entry points | none>     (one line per side; only for an SDK with doors)
              side: <chosen side (from --side | records (D-31) | existing UTS code)>; provisional, re-confirmed at STOP-3 | asked at STOP-17 (13.8)
Scope        <full|rest-only|realtime-only|unclear|none>: <modules> (objects per STOP-14)[; undecided: realtime, objects (ask at STOP-17)][; unsupported: <module> (<reason>)][; <n> capability-inapplicable test(s) or path(s)][; plus <n> REST-only test(s) under realtime][; partial skill, extendable by Upgrade/Fix]; confirm <with STOP-13 | at STOP-17>
Plan         confirm <at STOP-17 | with STOP-13>: <tiers>; smoke tests and self-tests per tier | existing harness (<where>), audited at U1 and STOP-15; side: <side | asked at STOP-17 | one side>; left out: <modules or tests | nothing>
Capability   changed since the recorded run: <item old -> new>, …[; added: <capabilities>][; lower than recorded: <capabilities>]     (only if it changed)
Skill        <path> [installs: …] name <name|missing>, version <v|none>, origin <creator-records|creator-metadata|unknown>     (one per skill)
              inspector hints: <f> fail, <w> warn, <p> pass (regex, not a review); mapping: <modules>; objects notes: <present|placeholder|none>
Harness      <from mapping | candidates: …>; smoke/self-test files: <n>[ by name; <n> candidate(s) by location (read to confirm)][; offered tiers lacking them: <list> | unknown (some files don't name a tier)]
Records      <dir>: run <finished|in progress (Phase n)>; recorded spec <sha8>, repo <sha8>[; checklist ✓ <n>, ✓ static <n>, ✗ <n>, n/a <n>, open <n>[ (no Evidence column)]]     (only if the skill has records; the checklist part only if they have one)
Skills       none[; other repo skills: …]     (instead of the Skill lines, when there is no skill)
Harness      <candidates: … | none found>     (with "Skills none")
Problems     <broken installs, orphan records>          (only if any)
Changes      since recorded spec <sha8>: guide <n>, UTS docs <n>, helper specs <n>, corpus <n> files; checklist changed: <yes|no>[; repo <n> files]
              | recorded spec <sha8> isn't in this clone: fetch it (STOP-6, 13.9) | the user fetches it (this clone isn't synced), or run a full gap audit  |  the records name no spec SHA: run a full gap audit
UTS tests    <n> tags in <n> files (<dedicated|nativeSuite|mixed>); <module/tier counts>; header SHAs …; deviations.md: …
LiveObjects  <yes|no|unclear> (<confidence>): <summary> (decided at STOP-14)
User-level   <uts-to-* installs | none>
State        <class>[ + re-entry]: <reasons>
Recommended  <option>  |  none (S4): ask which skill
```

The **Spec names** line says where the detectors' names came from (13.8). "FALLBACK" means the spec clone's IDL couldn't be parsed, so the detectors used the data file's minimal names: the LiveObjects and capability verdicts are unreliable. Orient then also puts the **WARNING** line first, and adds the problem to `stop1` and `warnings`. Settle it at STOP-1 (fix the clone, or report the parser gap) before relying on either verdict; never go on silently with fallback names. "(revision unknown: not a git checkout)" means the names came from the IDL, but the clone isn't a git checkout, so the records can't pin its SHA: settle that at STOP-1 too.

The **Spec clone** line's second line (in the table, the **Sync** row) is offline: how old HEAD is, and how far ahead of and behind `origin/main` it was at the last fetch; after the sync, replace its `sync:` part (the Sync row's last part) with the sync's outcome (13.9), as you complete the Model row. For a clone that isn't the shared clone it says "not synced", and the SPEC CLONE NOT SYNCED warning comes first: nothing suggests syncing it. **Changes** says so when the recorded spec SHA isn't in the clone: then Orient recommends the full gap audit, because diff-driven can't diff (13.9, "Reproducibility"). A **Harness** candidate found by location is an untagged test file under the harness root or the harness-tests tree (the mapping's `testsRoot`; for an older mapping without it, also beside the root) that uses a harness type: read it before counting it as a self-test. An older `harness` entry (per-tier lists, or a string `tests`) is read, and the inspector's `M-harness` check warns about it.

The other optional lines: **Method gaps** (only when realtime is `partial`) and **Native SDK** (only when `wrapsNativeSdk`) come from the capability detector (13.8). The **Side** lines appear only when the SDK has device or server doors; the side question itself is part of STOP-17 (13.8). In the table they are two rows: **Sides** lists them, and **Client setup** says how the harness creates clients and what settled it (the existing UTS code, with a file and a count; the records; or the user's choice), or that it is asked below. The **Plan** line is the UTS infrastructure plan in one line (13.8): when STOP-17 isn't asked, the STOP-13 answer confirms it. With an existing harness, the table's Plan row shows only the recommended run mode's plan, in one or two lines: for Upgrade/Fix the existing harness (its path shortened to the last two parts) and what the run does with it, for Create or Regenerate the new one's tiers. Another mode's plan comes only if the user picks that mode, with its follow-up (`followUpByOption`). The **Capability** line appears only when the profile differs from the recorded one (13.8, "When the capability or the side changes later"). On an `ask`, the Eligibility line names the question and ends with STOP-16 (13.2).

Then **STOP-13**, always, in every run: `questions.now[0]`, Question 1 of Orient's questions ([asking.md](asking.md)). It gives the options for the class in plain words, the recommended one first and marked, with one short sentence of why ("The skill wasn't made by this procedure, so its gaps against the guide are unknown."). When the client setup was settled without asking (detected from the existing UTS code, or taken from the records), one more plain sentence names it, in both forms, so the assumption is visible: "Keeps the existing client setup (core constructors) and audits the existing harness." Its answer also confirms the capability profile and the Plan when STOP-17 wasn't asked (the Plan row says "accepted with your run-mode answer"), and the spec clone when Orient shows the stronger not-synced warning (the warning says so). The table below gives the options by their internal names, which the decision log records; the question words them plainly (for example "Upgrade/Fix, full audit").

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
| Upgrade/Fix, full gap audit (S3, or S2 by choice) | `upgrade: full audit` | [Section 11](upgrade-existing-skill.md#11-upgradefix-full-gap-audit): U1 alongside Phase 1, STOP-2, STOP-14, U2 and STOP-15, then 11.5 and 11.6, then Phase 7 |
| Upgrade/Fix, diff-driven (S2) | `upgrade: diff-driven` | [Section 10](upgrade-diff-driven.md#10-upgradefix-diff-driven): the recorded state, a scoped Phase 1, STOP-2, STOP-14, the detected changes as STOP-15 items, the targeted phases, Phase 7. It hands off to the full audit when the checklist changed or the user asks |
| S4: Upgrade/Fix one named candidate | `upgrade: diff-driven` if its origin is `creator-records`, else `upgrade: full audit` | As the matching row above, for that skill only (rerun Orient with `--skill-dir` to show its own State summary) |
| S4: Repair the installs first | — | Propose each change (relink, reconcile copies; never delete without asking), apply only the ones the user approves, then rerun Orient |
| S4: Create a new skill | `create` | As Create |
| Regenerate from scratch | `upgrade: regenerate` | U1, then the create flow, staged ([11.5](upgrade-existing-skill.md#115-step-u4-run-the-phases-scoped)) |
| Resume or restart | the recorded D-27, plus "resumed" or "restarted" with the date | 13.6 |

The records for Upgrade/Fix go where Orient found them; otherwise to `<existing-skill-dir>/generation/` (D-24). At the start of Phase 1, copy the design-record and repo-profile templates to the working-records directory if they aren't there yet, copy the State summary into the Repo profile, and copy the eligibility result into the Design record's Inputs.

## 13.6 Re-entry: resume or restart

When Orient finds records with `Run status: in progress`, offer:

- **Resume:** read the records and continue from the phase their Run status names. D-27 keeps its recorded value. STOP-14 is asked again only if D-28 isn't recorded yet. If the spec clone's SHA has moved since the records were written (a sync, or another run's fast-forward of a shared clone, 13.9), Orient adds the re-entry reason "spec moved since the records: ask about restarting (13.6)"; ask whether to restart from the new SHA (2.6). The Records row shows the acceptance checklist's progress (✓, ✓ static, ✗, n/a and open counts; a ✓ without evidence counts as open): re-read the checklist with the records, and continue updating its rows from where they stand.
- **Restart:** supersede the recorded decisions in the decision log, keep every file, and start again from Phase 1 in the mode chosen now. Picking one of the class's options instead of Resume means Restart in that mode.

## 13.7 Provenance (D-30)

So that a later Orient can tell this procedure's skills from others (S2 vs S3), the procedure writes two kinds of evidence. Both are a *procedure recommendation*.

- **The skill's frontmatter** carries `metadata.generated-by: "uts-to-lang-skill-creator <version> @ <spec-sha8>"`, and `metadata.records: "<repo-relative records dir>"` (or `"not kept"`). Both are strings, so they stay portable (guide 3.3). Phase 7 refreshes them.
- **The Design record** carries a `Run status` line: "in progress (Phase n)" from STOP-13 on, updated at each phase end, and "finished" at Phase 7.

## 13.8 Capabilities and scope (STOP-17, D-31)

The harness and the skill cover what the SDK can do, not what its name suggests (guide [section 2](../../../docs/writing-uts-spec-translator-skills.md#2-the-harness-uts-test-infrastructure)). `detect_capabilities.py <repo> [--spec-clone P] [--include-submodules] [--capability-override rest=full,realtime=absent]` (Orient runs it; an unknown capability or a level not valid for it is a usage error naming the valid levels: usage on stderr, exit 2) finds:

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
- **`source`:** `detected`, `override (whitelist)` (13.2), or, after the user's correction at STOP-17, `override (your correction, --capability-override)`.

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

For example, the three RSC24 tests in `rest/integration/batch_presence.md` need a Realtime client; `spec_names.py` prints the current lists. A REST-only skill also translates the REST-only tests filed under `uts/realtime` (`extraTests`).

**Wrappers over native SDKs** (`wrapsNativeSdk`, such as a Flutter plugin). The capability is full, but the hooks live in the wrapped native SDKs. Phase 1 checks whether they are reachable from the SDK's language (P-13); if they aren't, that is a harness gap, and the unit tier is offered only once hooks exist ([4.8](phase-2-design-harness.md#48-step-2h-derive-tier-feasibility)). The integration and proxy tiers are still offered.

**STOP-17: the UTS infrastructure plan.** This skill's deliverable is the `uts-to-<lang>` skill and the harness it runs on, so STOP-17 doesn't ask about "capabilities" in the abstract: it shows the plan the capability profile implies, and the user confirms or adjusts it. Orient derives it as `infraPlan`, and asks it through the STOP-17 questions in `questions` (13.1, [asking.md](asking.md)):

- **Per tier, the harness pieces,** with their gap-table rows ([`uts-infra-design.md`](../assets/templates/uts-infra-design.md)):
  - REST unit: the HTTP hook, `MockHttpClient`, the fake clock and the randomness hooks (G-02, G-06, G-03, G-05);
  - Realtime unit: the WebSocket hook, `MockWebSocket`, the fake clock, the network monitor, the randomness hooks, `MockVCDiff`, `MockNetworkListener` and the wait helpers (G-01, G-07, G-03, G-04, G-05, G-08, G-09, G-11), plus G-02 and G-06 when REST is out of scope (a Realtime client still uses HTTP);
  - the sandbox and proxy integration tiers: `SandboxApp` (G-15), `ProxyManager` and `ProxySession` (G-16);
  - on every tier, G-12, G-13, G-14, G-17 and G-18.
- **The smoke tests and self-tests per tier** (G-19, G-20; guide [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)).
- **What's left out, and why:** `unsupported` modules (capability absent, or not on the chosen side), `undecided` modules (an `unclear` scope: ask at STOP-17 what the SDK offers; never decided as REST-only), the count of capability-inapplicable tests, and `objects`, which STOP-14 decides.
- **How the harness creates clients** (the side), when the SDK has device or server doors: below.

`infraPlan` keeps the gap-table rows; the question shows each tier as one plain bullet (what the harness gets, and its smoke test and self-tests), without them.

The plan is an outline from detection. Phase 2 designs it in full, from the Phase 1 facts Orient doesn't have (P-13 injection points, P-14 the internal-access mechanism, P-15 the API surface, P-16 existing mocks and test support), and STOP-3 presents that design against this outline ([4.9](phase-2-design-harness.md#49-step-2i-stop-3-approve-the-design-and-choose-the-scope)).

**When STOP-17 is asked.** Only while it is open; this is the one list of its triggers:

- **The capability profile needs confirming:** `confirmAtStop17` is set (the profile isn't full, is unclear, wraps native SDKs, comes from a capability override, or its names come from the fallback), or it differs from the recorded D-31 (below). `stop17` lists those reasons.
- **The side is open:** the SDK has doors, and nothing settled it. The side is settled by `--side` (the user's answer), else by a recorded D-31 side that is still among the doors, else by the existing UTS code when it uses exactly one side (the evidence below). That last case is a detected fact, not a question: the State summary's Client setup row shows it with its evidence, and in Upgrade/Fix the audit checks it.

Otherwise there is no STOP-17, even in Create: the State summary's Plan row shows the outline, and the STOP-13 answer accepts it, as it confirms the profile.

When it is open, STOP-17 is up to two questions, each its own question with one option list ([asking.md](asking.md)):

1. **"Is this harness plan right?"**, with the plan as short plain bullets: per tier, what the harness gets and its smoke test and self-tests; what's left out, and why; and, when the profile needs confirming, what was found (the client names, the Realtime sub-areas, the transport) and what to check, in plain words. Options: (1) yes (recommended); (2) change something: the user says what, with evidence; (3) stop. It is needed when the profile needs confirming, and, when the side is open, for a run mode that plans a new harness: Create, Regenerate, or Upgrade/Fix when no harness was found.
2. **"How should the harness create clients?"**, only when the side is open (the options are below).

Orient schedules each question against the STOP-13 options (13.1). A question that every run mode needs goes in `questions.now`, after STOP-13. One that only some modes need goes in `questions.followUp`, with those modes in `askIf`, and is asked in a follow-up message once the STOP-13 answer picks one of them. Stop and "Repair the installs first" don't count: after a repair, Orient runs again. The plan question's content follows the mode. In Upgrade/Fix, when the repo already has a harness (from the skill's mapping, or a candidate the inspector found), it names that harness and says the audit checks it, instead of the per-tier bullets; the harness is assessed against the guide in the gap audit ([11.3](upgrade-existing-skill.md#113-step-u2-write-the-gap-audit)), not re-planned here. Create and Regenerate get the per-tier plan. When both kinds of mode need the question, each gets its own version, and `followUpByOption` gives each STOP-13 option only its own.

**Adjusting the plan.** "Change something" and any answer that corrects a capability or chooses the side rerun Orient: `--capability-override rest=<level>,realtime=<level>` for a capability (it wins over a whitelist one) or `--side <side>` for the side. Show the new plan, and record the change in D-31 with the evidence. A follow-up is asked from the first Orient output, without a rerun: its plan says what each client-setup answer would drop. Once every question is answered, rerun Orient once with the answers, so that `infraPlan`, the Plan row and D-31 match them; don't ask again what was answered. Only "Change something" asks again, with the new plan.

**The side question**, when the SDK has a server or device door and the side is open: through which entry point does the harness create clients? The options are numbered from the doors found, in plain words, with the recommended one, if any, first. With both doors:

1. the core constructors, through the sanctioned internal-access route (guide [5.9](../../../docs/writing-uts-spec-translator-skills.md#59-internal-access-white-box-unit-specs); for example `InternalsVisibleTo` for the UTS test project);
2. the server entry point (the server door);
3. the device entry point (the device door);
4. both, as a harness setting: one suite, run once per side;
5. stop.

With one door, the options are the core constructors, that door, the core and that door as a harness setting, and stop. Each option names its entry points; a door without a REST or Realtime client says that those tests are dropped.

The evidence: Orient looks in the repo's tracked source under a `uts` path segment for the core constructors (`new <Client>(`) and the doors' entry points, and finds a side only when exactly one side is used there; it names up to three files, with a count. When the side is open, that evidence can only be missing or conflicting, so no option is marked recommended; `infraPlan.side.recommended` holds the detected side for the cases above. The side is **provisional**, whether detected or chosen: Phase 1 reads the test support (P-13, P-14, P-16), and STOP-3 re-confirms it. A different side then adds a decision-log entry that supersedes D-31 (2.5). Another SDK's per-side switch (on a branch, ably-cocoa runs its UTS through either its core or its device factory, chosen by an environment variable) is only evidence that a harness-parameter option works. Design this SDK's own; never copy it ([2.1](../SKILL.md#21-your-inputs)).

**The scope follows the chosen side.** A side without a REST client (usually the device door) gives a `realtime-only` scope, and a side with both clients gives `full`. With the harness-parameter option, the scope is the union, and a test one side can't run is capability-inapplicable on that side's run.

Record the result as **D-31**, as one parseable line in the Design record, whether STOP-17 was asked or the STOP-13 answer accepted the plan; a side detected from the existing UTS code is recorded with that evidence. Record the levels detected for the whole repository, not for the chosen side, so that a later Orient compares like with like; the side and the scope carry the choice. For example:

```
- Capabilities (D-31): rest full; realtime absent; liveobjects no; side: none; scope: rest-only (rest + 3 REST-only tests under realtime); unsupported: realtime, objects (capability absent); capability-inapplicable: 13 tests (listed in the rest notes); names: spec
- Capabilities (D-31): rest full; realtime full; liveobjects no; side: device (no REST client); scope: realtime-only (realtime); unsupported: rest (not on the device side); capability-inapplicable: 4 tests (listed in the realtime notes); names: spec
```

**What `unsupported` and capability-inapplicable mean:**

- **Mapping.** A module the scope excludes keeps its entry (so the skill's step B never offers `--create`), with tier paths only where its `extraTests` need them, and carries `"unsupported": "<reason>"`, for example `"capability absent: no realtime client (D-31)"`. Tests or specs that need a client the SDK (or the chosen side) lacks go under the module's `"capabilityInapplicable": {"<Test ID or spec path relative to the module>": "<reason>"}`. A REST-only skill's `realtime` entry also lists the `"extraTests"`. The resolver's behaviour for each key is in [7.1](phase-5-generate-skill.md#71-step-5a-create-the-layout-and-the-mapping-file).
- **Tests.** A capability-inapplicable test is guide [7.4](../../../docs/writing-uts-spec-translator-skills.md#74-language-inapplicable-inputs) case (d). It is noted in the test file, or left out of the selection by the mapping, and listed in the module notes. It isn't a deviation, never goes in `deviations.md`, and doesn't count as a coverage gap.
- **Harness.** Gap-table rows that need an absent capability are `n/a — capability absent: <capability> (D-31)`. For a REST-only SDK these are:
  - wholly n/a: G-01 (WebSocket hook), G-04 (network monitor), G-07 (`MockWebSocket`), G-08 (`MockVCDiff`), G-09 (`MockNetworkListener`), G-10 (objects pool);
  - partly n/a: G-05 (jitter; host shuffle still applies), G-11 (`AWAIT_STATE`), G-16 (WebSocket frame rules; the HTTP rules apply), and G-19/G-20 (built in their REST form, [4.8](phase-2-design-harness.md#48-step-2h-derive-tier-feasibility)).

  For a realtime-only SDK, no row is wholly n/a: the Realtime client still uses HTTP (auth, time, history, `request()`, fallback), so G-02 (HTTP hook) and G-06 (`MockHttpClient`) are still needed. Only the `rest` tiers' smoke tests in G-19 are n/a.
- **Harness README.** Its Known gaps lists the constructs of the unsupported modules, so the skill's preflight refuses a spec that uses them ([5.3](phase-3-build-harness.md#53-step-3c-write-the-harness-readme)).
- **Acceptance checklist.** A row that wholly needs the absent capability is `n/a — capability absent: <capability> (D-31)`. A row with only some parts affected is ✓ with those parts named as n/a. n/a never counts as ✗; a scope the user chose to cut still is ✗.
- **LiveObjects.** STOP-14 is still asked. With no Realtime client it recommends "no", with the reason "capability absent: no realtime client".

**When the capability or the side changes later.** Orient compares the current profile with the recorded one (the D-31 line, completed by the mapping's `unsupported` markers). `inspect_existing_skill.py` reports that recorded profile as `capabilityProfile`: it parses the D-31 line and reads each mapping module's `unsupported`, `capabilityInapplicable` and `extraTests`; if there is no D-31 line, it infers the levels from the mapping and sets `levelsInferred`. It reports `capabilityDelta` as `{changes, added, lowered}`, or null when nothing changed:

- `changes`: each differing item, `"old -> new"`. The REST and Realtime levels are always compared, because D-31 records the whole repository's levels. `side` changes when doors appear, disappear, or the recorded side is no longer among them. The scope kind (`scope`) and the `unsupported` modules depend on the chosen side, so they are compared only when no side was recorded and the repo has no doors now.
- `added`: capabilities now higher than recorded, or modules no longer unsupported (not `objects`, which follows realtime and STOP-14 decides).
- `lowered`: capabilities lower than recorded, or modules newly unsupported: a detector miss, or removed? Ask for evidence at STOP-17.

Any change makes STOP-17 ask, and the State summary shows the Capability line. On S2 (not re-entry), a change recommends Upgrade/Fix, diff-driven, never "Stop". The change item "capability added: <capability>" ([section 10](upgrade-diff-driven.md#10-upgradefix-diff-driven)):

- supersedes D-31;
- removes the module's `unsupported` marker, and the `capabilityInapplicable` entries the new client makes runnable, maps the new tiers and adds the module notes;
- turns the G-rows and checklist parts that were n/a for that capability into gaps (gap-audit sections B and C, marked "newly applicable"), and adds the guide 2.7 sets for the new tiers;
- asks STOP-14 again.

A removed capability is its own change item; tests are never deleted without asking.

A change of side (the SDK gains doors, or the user now wants another side, or both) is the change item "side changed: <old> -> <new>": ask STOP-17's side question again, supersede D-31, and make the scope, the mapping markers and the harness's construction path follow the new side. In the generated skill, a scope change is a mapping edit (`unsupported`, `capabilityInapplicable`, `extraTests`), not a resolver change ([7.1](phase-5-generate-skill.md#71-step-5a-create-the-layout-and-the-mapping-file)).

## 13.9 Sync the spec clone

Every run reads the guide, the UTS docs, the helper specs, the corpus and the features specs from one local clone of `ably/specification`, pinned at one SHA (2.6). By default this is a clone shared by every run and every SDK repo, kept current by the **spec-clone sync**: Step 0's only network use, and the only change this procedure makes to a spec clone. The sync runs only when the clone in use is the shared clone, however it was found. Any other clone (one the user names, or the clone this skill is installed from, when it isn't the shared clone) is never fetched or changed, whatever `ABLY_SPEC_SYNC` says, and no sync question is asked for it: there is a static warning instead, and keeping it current is the user's responsibility. `ensure_spec_clone.py` reports it as `notSyncedWarning` ("Using the spec clone you named (`<path>`). It isn't synced; make sure its UTS specs are up to date.", or "Using the clone this skill is installed from (`<path>`). …"), the form generated skills show. Orient builds a fuller form from the same offline facts (`specCloneWarning`, 13.4): what this run reads from that clone, its branch and drift, and, when the clone is off `main` or has tracked changes, the stronger warning that the STOP-13 answer confirms. `orient.py` and `spec_clone_info.py` stay offline; `scripts/ensure_spec_clone.py` does the sync, and only with approval. The sync is settled after STOP-16, so an ineligible repo is never asked a network question, and before STOP-1. Orient's `specSync` says what to offer, and the command to run.

### Which clone

The first candidate that exists wins:

| # | Candidate | `kind` / `foundBy` | If it doesn't exist | Synced |
|---|---|---|---|---|
| 1 | The path the user names (`--spec-clone <path>`, or a path in their words; a path inside a clone is walked up to its root) | `explicit` / `argument` | `NOT_A_SPEC_CLONE`: STOP-1 | Only if it is the shared clone's directory |
| 2 | The clone this skill is installed from (`<clone>/uts/skills/uts-to-lang-skill-creator`) | `skill-clone` / `skill location` | Skipped | Only if it is the shared clone's directory |
| 3 | `ABLY_SPEC_CLONE` (`UTS_SPEC_CLONE` is read as a deprecated alias, with a warning; both set and different is `SPEC_CLONE_ENV_CONFLICT`: STOP-1, unless row 1 or 2 already found a clone) | `env` / `ABLY_SPEC_CLONE` or `UTS_SPEC_CLONE (deprecated)` | `SPEC_CLONE_NOT_FOUND`, with `bootstrapPath`: the bootstrap offer, there | Yes: it is the shared clone |
| 4 | The shared default, `~/.ably/specification` (`%USERPROFILE%\.ably\specification` on Windows) | `shared` / `shared default` | `SPEC_CLONE_NOT_FOUND`: the bootstrap offer | Yes |

A path from row 1 or 3 that exists but isn't a clone is `NOT_A_SPEC_CLONE`: it is never replaced by another candidate. The skill's own clone comes before the variable and the default because `SKILL.md` links into the guide by section, and the two change together: read the guide from the revision this skill was loaded from. Whether a clone is the shared clone is decided by comparing directories (symlinks resolved, case-insensitive where the filesystem is), so a named path into the shared clone, or a skill installed from it, is the shared clone. With the recommended install (a symlink from the shared clone, [`uts/README.md`](../../../README.md#installing-the-skill-creator)), rows 2 and 3 or 4 are the same clone, and the State summary says "skill clone, the shared clone". A skill installed from another clone or worktree (to test a spec-repo branch) reads that clone, on its branch, untouched and never synced ("skill clone (not the shared clone)", with the static warning). To test a branch without a second full clone, add a worktree of the shared clone (`git -C ~/.ably/specification worktree add <dir> <branch>`) and install the skill from it, or pass `--spec-clone <dir>`; the shared clone stays on `main`, and the worktree isn't synced.

A clone that exists but whose checkout lacks a file this skill needs (the guide, this skill, a UTS doc or helper spec) is `SPEC_CLONE_INCOMPLETE`: that revision predates it. This is the case for a clone on `main` until the skill creator is merged there. The message says whether `origin/main`, as last fetched, has the files: if it does, the sync fixes it for the shared clone (the user updates any other clone); if not, use a clone or worktree of a branch that has them (the clone you installed the skill from does), named with `--spec-clone` or by installing from it. Never fetch the missing files from GitHub instead.

### No clone: the bootstrap offer

When nothing is found, after STOP-16 ask (STOP-1, with STOP-6's content, because cloning is network): (1) give the path of an existing clone; (2) clone to `bootstrapPath` (the command, about 30 MiB, from github.com); (3) stop. On (2), run `python3 <skill-dir>/scripts/ensure_spec_clone.py --bootstrap`, then rerun Orient. It clones `https://github.com/ably/specification.git` in full (not shallow or partial: Upgrade/Fix and re-sync diff against recorded SHAs, and a partial clone would make Orient's offline diffs fetch), without submodules, with `core.autocrlf=false` in the new clone, into a temporary sibling (`<path>.partial-<pid>`) that it renames into place, so an interrupted clone never sits at the well-known path. It refuses a path that exists. A leftover `.partial-*` directory is reported for the user to remove; nothing is deleted on their behalf.

### The question, once per run

This applies to the shared clone only; for any other clone there is no question, only the static warning. `ABLY_SPEC_SYNC` is the user's standing answer: `ask` (the default), `auto` or `off`. The user sets it (in their shell, or the tool's environment settings); both it and `ABLY_SPEC_CLONE` are read from the agent's environment at run time, so a variable set only in the shell used to install the skill has no effect (with `ABLY_SPEC_CLONE` unseen, a clone at that path isn't recognised as the shared clone and isn't synced). Never write it to their shell profile, the tool's settings or any file yourself: a stored preference would be a write outside the repo (2.2) and invisible state.

- **`off`:** no question and no network. Use the clone as it is, and report "not updated (ABLY_SPEC_SYNC=off)" with the staleness line. `off` covers the sync only: with no clone at all, the bootstrap offer is still made, and cloning needs the user's explicit approval.
- **`auto`:** no question. Run `--update` when nothing rules out a fast-forward; otherwise use the clone as it is and report why ("not on main: not updated"). `auto` only ever fast-forwards the shared clone's clean, checked-out `main`; a clone the user names, or the clone this skill is installed from, when it isn't the shared clone, is never fetched. When `origin` isn't `ably/specification`, nothing is fetched and the user is still asked: use it as it is, or stop.
- **`ask`:** one question, at STOP-6, built from the offline status (`fastForwardBlockedBy`, the branch, the staleness line), so it is asked once and never repeated after the fetch. When nothing rules out a fast-forward, the options are: (1) yes, this run: fetch and fast-forward `main` (`--update`); (2) no, use it as it is; (3) always: the user sets `ABLY_SPEC_SYNC=auto`; (4) never ask: the user sets `ABLY_SPEC_SYNC=off`. When something does (not on `main`, detached, tracked changes, an operation in progress, `main` ahead or diverged), the options are: (1) use it as it is (the default for a deliberate branch); (2) fetch only (`--fetch`: updates `origin/main`, no branch or file changes), so the ahead and behind counts are current; (3) stop, so the user can change the clone themselves. When `origin` isn't `github.com/ably/specification` in any URL form, nothing is fetched: use it as it is, or stop.

The fetch and the fast-forward write under the clone's `.git`, outside the SDK repo. In a sandbox, the user may need to allow that directory (in Claude Code, `/add-dir` or `permissions.additionalDirectories`) and network access (in Codex, a writable root and network). Say so in the question, so that a denial reads as "not updated: sandbox", not as a failure.

### The update rule

`ensure_spec_clone.py --update` applies to the shared clone only: fast-forwarding its clean, checked-out `main` with consent loses nothing. For any other clone, `--fetch` and `--update` change nothing and use no network: they report `NOT_SYNCED_NAMED_CLONE` with the static warning (`notSyncedWarning`).

1. Take the sync lock (below).
2. Check that `origin` is `github.com/ably/specification` (`ORIGIN_NOT_ABLY_SPEC` otherwise; no remote is added).
3. Fetch `+refs/heads/main:refs/remotes/origin/main` only, with credential and SSH prompts suppressed and a timeout. This changes no local branch and no file. Like a default `git fetch`, it updates the remote-tracking ref `origin/main` even if `main` was force-pushed on GitHub (the previous value stays in that ref's reflog); local branches, including `main`, are only ever fast-forwarded in step 5.
4. Leave the clone alone unless HEAD is the branch `main`, there are no tracked changes (staged or unstaged), no merge, rebase, cherry-pick, revert or bisect is in progress, and `main` is strictly behind `origin/main`.
5. Fast-forward with `git merge --ff-only --no-overwrite-ignore`. Untracked files don't block it, but git refuses rather than overwrite one; `--no-overwrite-ignore` makes it refuse for ignored files too, which git would otherwise silently overwrite (the spec repo ignores `/output/` and `/build/content/`). A refusal changes nothing (`FF_REFUSED`).

It never runs `pull`, `reset`, `checkout`, `switch`, `stash`, `clean`, `rebase`, `push` or `--force`, never adds a remote, and changes no git configuration. On a branch the user chose (testing an unmerged spec change), it reports "on branch `<name>` @ `<sha8>`, `<n>` ahead / `<m>` behind `origin/main` as of the last fetch; not updated", and never switches back.

| `code` | What happens | What the user sees |
|---|---|---|
| `UP_TO_DATE` | Nothing to do | "up to date (fetched now)" |
| `FAST_FORWARDED` | HEAD moves; `changed` says whether the guide and this skill changed, and counts the UTS docs, helper specs and corpus files changed | "fast-forwarded `<old8>..<new8>` (`<n>` commits)", with whether the guide and the skill changed |
| `FETCHED` | Fetch only: `origin/main` moves | the new ahead and behind counts |
| `NOT_SYNCED_NAMED_CLONE` | Not the shared clone: no network, nothing changes | the static warning |
| `SYNC_OFF`, or the user declined | No network | "not updated", with the staleness line |
| `FETCH_FAILED` | Offline, DNS, timeout, a suppressed auth prompt, a sandbox denial (including a git directory the sync can't write its lock in) | "not updated: fetch failed (`<first line of git's error>`)", with the staleness line |
| `LOCKED` | Another sync of this clone holds the lock for more than 30 seconds | "not updated: another sync in progress (pid, host, started)" |
| `NOT_ON_MAIN`, `DETACHED`, `DIRTY`, `OP_IN_PROGRESS`, `AHEAD`, `DIVERGED`, `FF_REFUSED`, `ORIGIN_NOT_ABLY_SPEC` | Nothing changes | the reason, with the branch, the files or the counts |

All of these leave a usable clone (exit 0): use it as it is unless the user chooses to stop. `SPEC_CLONE_NOT_FOUND`, `NOT_A_SPEC_CLONE`, `SPEC_CLONE_INCOMPLETE`, `SPEC_CLONE_ENV_CONFLICT`, a failed bootstrap (`BOOTSTRAP_PATH_EXISTS`, `BOOTSTRAP_FAILED`), `GIT_ERROR` and `INTERNAL_ERROR` exit 1: STOP-1.

### After the sync

- If HEAD moved (a fast-forward or a bootstrap), rerun `orient.py`, so the capability names, the LiveObjects evidence and the Changes line reflect the synced revision. If `changed.skill` is true and this skill is installed from that clone, read this `SKILL.md` again first: the copy in your context is stale.
- Add the outcome to the State summary's Spec clone line, and record it (below).
- **Staleness**, offline, from data on disk: HEAD's age, and how many commits `origin/main` was ahead at the last fetch (the latest of: an update of `origin/main` in its reflog, a fetch of `main` in `FETCH_HEAD`, which a fetch that changes nothing also renews, and the clone itself); "unknown (never fetched)" when there is none. Over 30 days since the last fetch, or unknown, Orient puts a STALE SPEC CLONE WARNING line at the top of the State summary for the shared clone; for any other clone, the static warning takes that place, and the staleness facts are still shown and recorded.

### Reproducibility

Record in the Design record's Inputs, the Repo profile, the gap audit and the Final report:

```
Spec clone: <shared|env|explicit|skill-clone> <path>; <sha> on <branch|detached> (clean | dirty: <files>); on origin/main: <yes|no>; sync: <fast-forwarded <old8>..<new8> | up to date | not updated: <reason>, behind <n> as of last fetch | not synced (not the shared clone)>; guide/skill: <sha of last change>; uts-to-lang-skill-creator version <metadata.version>
```

- A SHA that isn't on `origin/main` (a branch run) is listed in the Final report: the provenance stamp and any test headers that carry it may stop resolving once that branch is deleted.
- Upgrade/Fix diff-driven, and the generated skill's re-sync, diff against a recorded SHA. After a fast-forward, every earlier `main` SHA is an ancestor of HEAD, so those diffs keep working. When the recorded SHA isn't in the shared clone (Orient's Changes line says so), fetching it is part of the sync: ask it in the same STOP-6 question (under `auto`, fetch it without asking; under `off`, run the full gap audit instead): `git -C <spec-clone> fetch --no-tags origin <sha>` (GitHub serves any commit reachable from a ref; it changes no branch or file), then rerun Orient. If it is still missing, run the full gap audit instead. In any other clone, never fetch it: tell the user to fetch it themselves, and offer the full gap audit.

### Concurrency

- **Two syncs at once** (two SDK repos sharing the clone): the lock, `ably-spec-sync.lock` in the clone's git directory (never a working-tree change), is held only around the fetch and the fast-forward. A second sync waits up to 30 seconds, then reports `LOCKED` and uses the clone as it is. A lock older than 10 minutes whose process is gone, on this host, is removed (POSIX only); any other lock is reported, and the user may remove it.
- **Another run's fast-forward mid-run** switches the files this run reads to a new revision. Detect it: check `git -C <spec-clone> rev-parse HEAD` against the pinned SHA at each phase end, before Phase 7, and before writing any SHA into a record, a stamp or a test header. If it moved, stop and ask whether to restart from the new SHA, or abandon the run (2.6).
