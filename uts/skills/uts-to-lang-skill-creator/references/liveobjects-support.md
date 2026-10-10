# 12. LiveObjects (`objects`) support

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention). Links that climb out of the skill directory are spec-repo paths: resolve them against the spec clone, not against this file's installed location.

**Goal:** an explicit decision, made by the user from evidence in the SDK's source, on whether the skill covers `uts/objects`. Guide [3.1](../../../docs/writing-uts-spec-translator-skills.md#31-layout) ("Decide `objects` from evidence") is the requirement. You ask this question (**STOP-14**) in every run and every mode (Create and Upgrade/Fix, including regenerate and diff-driven), even when the evidence is unambiguous, and even when an existing skill already covers `objects`. Orient's State summary has already shown a one-line verdict. A resumed run asks it only if D-28 isn't recorded yet (13.6). For an SDK without a Realtime client (D-31, [13.8](orient.md#138-capabilities-and-scope-stop-17-d-31)), still ask, and recommend (c) with the reason "capability absent: no realtime client".

Contents:

- [12.1 Gather the evidence (step 1b, P-15)](#121-gather-the-evidence-step-1b-p-15)
- [12.2 STOP-14: recommend, then ask](#122-stop-14-recommend-then-ask)
- [12.3 What each choice adds, phase by phase](#123-what-each-choice-adds-phase-by-phase)
- [12.4 What the objects notes typically cover](#124-what-the-objects-notes-typically-cover)
- [12.5 An SDK-blocked objects tier](#125-an-sdk-blocked-objects-tier)

## 12.1 Gather the evidence (step 1b, P-15)

During the discovery checklist (P-15), run `python3 <skill-dir>/scripts/detect_liveobjects.py <repo> --spec-clone <spec-clone>` (Orient already has). It is a read-only regex heuristic, and it prints one JSON object: a one-paragraph `summary`, the `recommendation`, and the evidence. Every name it searches for comes from the spec in the clone, never from another SDK's code. `spec_names.py` parses them from the objects IDL at run time; the legacy and prose-only names are in `assets/capability-names.json`. `namesSource` says which: `fallback` means the IDL couldn't be parsed, and the verdict isn't reliable until that is fixed ([13.8](orient.md#138-capabilities-and-scope-stop-17-d-31)):

| Category | Names (from the spec) | What it shows |
|---|---|---|
| `publicApi` | The types and members of the [objects IDL](../../../../specifications/objects-features.md) that aren't marked `internal` and aren't also protocol types (`RealtimeObject`, `PathObject`, `LiveMap`, `LiveCounter`, `ObjectsEvent`, `ObjectsSyncState`, `StatusSubscription`, the subscription event and options types, `compactJson`; `Instance` is left out because the bare word is too common, and is covered by `InstanceSubscriptionEvent`) | The public API is exposed. Declarations carry a visibility heuristic for each language, and `publicDeclaredAt` gives up to three declaration sites per name; `missingPublicNames` lists the current-spec names with no public declaration |
| `accessor` | The `RealtimeChannel#object` accessor (RTL27), used on a channel-named receiver or declared with the accessor's type (`RealtimeObject` today; `accessorTypes`, read from the IDL's `RealtimeChannel` property of a LiveObjects type); the earlier spec's `channel.objects` form is counted here too (form `objects`) | The entry point exists. A public declaration alone is enough for a `yes` (medium) |
| `legacyPublicApi` | Public names from earlier revisions of that spec, before the entry point became `channel.object.get()` and the value types became `LiveMap` and `LiveCounter`: `RealtimeObjects`, `getRoot`, `createMap`, `createCounter`, `LiveObjectSubscription`, `LiveMapValueType`, `LiveCounterValueType`; and `LiveObject` and its `*Update` interfaces, which were public then and are internal now, when declared public | The SDK may follow an earlier spec revision, which notes item 1 must name. These names often survive in comments or internal code: public declarations count fully, and other uses in source only toward the medium rule. Members written in another case (`CreateMap`) count only as declarations, so an unrelated library call doesn't |
| `shared` | Public message types that are also protocol types (`PublicAPI::ObjectMessage`, `PublicAPI::ObjectOperation`, the operation types and the operation actions) | Neither for nor against a public API |
| `internalApi` | Names that are internal in the current spec: IDL types and members marked `internal` (`InternalLiveMap`, `InternalLiveCounter`, `LiveObject`, `publishAndApply`, …) and `ObjectsPool` from the spec prose | An implementation exists, but this alone doesn't show the public API |
| `wireOnly` | Protocol-only names from `features.md`: `OBJECT_SYNC`, `ObjectState`, `ObjectData`, `ObjectsMap`, `ObjectsCounter` and their parts, the object channel modes | Protocol-level support, not the public API |
| `pluginKey`, `packaging` | Identifiers naming the `LiveObjects` plugin (PC5, PT2b) in [`features.md`](../../../../specifications/features.md); `live[-_ ]objects` in build manifests and directory names; a bare `objects` directory as weak evidence; `nestedPackages`, directories with their own package manifest that hold public-API names | A plugin or module that may hold the API. Confirm each nested package is the SDK's own, not a vendored copy |

Names are matched as whole identifiers: the spec name, the same name behind a short all-caps prefix (such as an Objective-C `ART` or a C# `I`), its snake_case form, and, for members, any capitalisation (`GetRoot`, `CompactJSON`). Hits on comment lines and in test files are counted apart from the rest, and don't drive the recommendation.

It skips the following, and reports what it skipped:

- vendored directories (`vendor`, `node_modules`, `Pods`, `Carthage`, `third_party`, `deps`, `external` and the like, in any case);
- agent skill directories (an existing skill's notes would be false positives);
- git submodules (pass `--include-submodules` if the SDK keeps code in one);
- any copy of the spec repo, and copies of this script;
- in a git repo, ignored files, such as build output and test results, which never reach the scan (without git, it skips them by directory name and counts them);
- untracked files, which it counts apart.

It also reports not-implemented markers found in files that hold public-API names.

Then **read** what it lists: the declaration sites, the accessor and the manifests. The heuristic can't see everything. For example, it misses re-exports, `__all__` and generated code, and it can't tell a stub from a real implementation. Its `suggestedMode` is advisory: the translate-only or evaluate choice is made below and at the skill's step E. If the user says the LiveObjects API lives in another repository or package, run the script on that path too (read-only, with the user's path). Record the summary (recommendation, confidence, reasons, the public symbols found, and a few files) in the Repo profile's P-15 objects line.

Also establish whether the implementation is complete enough to evaluate. Use the not-implemented markers, the public types compared with the IDL's list, the SDK's own objects tests, and the user's answer. If you're unsure, ask. This decides translate-only or evaluate for `objects` (guide [4, step E](../../../docs/writing-uts-spec-translator-skills.md#phase-1-selection-steps-0-and-af); notes item 1).

## 12.2 STOP-14: recommend, then ask

Present:

- the script's `summary`, verbatim;
- a table with one row per category: the symbols, their counts (source and test), and where the public ones are declared (`publicDeclaredAt`), plus `missingPublicNames`;
- the script's recommendation (`yes`, `no` or `unclear`), its confidence and reasons, and your own reading after reading the files;
- the options below, with your recommendation.

| Option | When to recommend it | Result |
|---|---|---|
| **(a) Full objects support** | The SDK exposes the LiveObjects public API, even if the implementation is incomplete | Objects notes, the `objects` mapping entry and the objects harness pieces ([12.3](#123-what-each-choice-adds-phase-by-phase)). If the implementation is incomplete, objects runs default to translate-only (the skill's step E); once evaluated, a failing test is an SDK deviation, gated, or a skipped stub where the API is missing (guide [7.1](../../../docs/writing-uts-spec-translator-skills.md#71-three-acceptable-end-states)) |
| **(b) Placeholder** | Only internal, wire-level or packaging evidence; or the public API is planned but not yet in the source | A placeholder notes file and mapping entry. The skill refuses the module until the notes are written (guide [4](../../../docs/writing-uts-spec-translator-skills.md#phase-1-selection-steps-0-and-af)) |
| **(c) No objects support now** | No evidence, or the user doesn't want it | An `objects` mapping entry with the D-03 default path for each tier, every tier marked not ready ("out of scope, D-28"), and no notes. The skill's step C then refuses the module with that reason; without an entry, its step B would offer to create one and translate with no notes |

If the result is `unclear`, ask the user where the public API lives before you recommend anything. When an existing skill already has full objects notes (Upgrade/Fix: full gap audit or diff-driven), the options become:

- (a) keep the objects support and upgrade it with the gap audit's objects items ([11.3](upgrade-existing-skill.md#113-step-u2-write-the-gap-audit)): D-28 full;
- (b) keep it as it is: D-28 full, recorded as "kept as is", with the gap audit's objects rows defaulting to skip;
- (c) take it out of scope: D-28 none. This never deletes files without the user's approval for each one.

An existing placeholder notes file gets the normal options above.

Ask this after STOP-2 (step 1e, [3.5](phase-1-understand-repo.md#35-step-1e-decide-liveobjects-support-stop-14)). Record the answer as D-28 (with the detector's recommendation and the mode, translate-only or evaluate), add it to the Repo profile's objects line, and log it in the decision log. A later run that finds new evidence asks again (see [section 10](upgrade-diff-driven.md#10-upgradefix-diff-driven)).

## 12.3 What each choice adds, phase by phase

| Phase | (a) Full | (b) Placeholder | (c) None |
|---|---|---|---|
| 1 | The P-15 objects divergence list (IDL followed, plugin or built-in, typed or dynamic). Read a plugin test in step 1c ([3.3](phase-1-understand-repo.md#33-step-1c-study-how-the-existing-tests-drive-the-sdk)) | P-15 says why it's a placeholder | P-15 says why there's no objects support |
| 2 | G-10 in scope: the [`standard_test_pool.md`](../../../objects/helpers/standard_test_pool.md) symbol map ([4.3](phase-2-design-harness.md#43-step-2c-map-each-helper-spec-to-native-code)) and a plugin client-options builder. Place the module helpers where white-box specs can see internals (P-14). Fill the objects rows of the tier matrix ([4.8](phase-2-design-harness.md#48-step-2h-derive-tier-feasibility)) | G-10 `n/a` (D-28). The objects rows read "not possible: placeholder notes" | G-10 and the objects rows `n/a` |
| 3 | [5.2](phase-3-build-harness.md#52-step-3b-build-in-order-with-acceptance-checks) row 11 (the objects unit smoke test and the serial-helper self-test). The objects REST provisioning helper is built with row 9. If the implementation is incomplete, the smoke test may end SDK-blocked ([12.5](#125-an-sdk-blocked-objects-tier)) | — | — |
| 4 | D-03 gets an `objects` entry (hand-maintained if the module lives in a separate plugin package or build module). D-12 lists the white-box specs, D-23 says full, and D-25 has an objects pilot | D-03 entry with placeholder notes. D-23 says placeholder | D-03 entry with every tier not ready. D-23: none |
| 5 | Notes per [7.5](phase-5-generate-skill.md#75-step-5e-write-the-module-notes) and 12.4. Catalogue rows for the constructs `scan_constructs.py` finds in `uts/objects` | A placeholder notes file saying why, and what would unblock it | — |
| 6 | An objects pilot ([8.3](phase-6-validate-skill.md#83-pilot-translate-one-spec-per-available-tier)), translate-only when D-28 says so, and always for an SDK-blocked tier (12.5) | 8.5 path 3 (placeholder refused) | 8.5 path 4 (unready tier refused, with the reason) |

## 12.4 What the objects notes typically cover

The requirement is guide [3.4](../../../docs/writing-uts-spec-translator-skills.md#34-recommended-outlines-should)'s thirteen items, in order, as [7.5](phase-5-generate-skill.md#75-step-5e-write-the-module-notes) says. For `objects`, they usually amount to the following. Use this list to know where to look, not as text to fill in. Write every mapping from the SDK source and the harness as built: the notes are a map, and the SDK source is the authority (guide 3.1).

1. **Source of truth:** which IDL the SDK follows. It may be the current [`objects-features.md`](../../../../specifications/objects-features.md) (`channel.object.get()` returning a `PathObject`, RTO23), an earlier revision (the detector's legacy names, such as `channel.objects.getRoot()`), or the typed-SDK variant that guide 3.4 item 1 names. Also say whether the module is implemented: this is the translate-only or evaluate decision (D-28).
2. **Layers:** `LiveMap` and `LiveCounter` as creation value types (RTLMV, RTLCV), the public views (`PathObject`, `Instance`) and the internal nodes (`InternalLiveMap`, `InternalLiveCounter`). The specs use all three.
3. **Entry point and setup:** plugin registration in the client options (PC5, PT2b); the RTL27 accessor, and its error when the plugin is missing (RTL27b); the object channel modes.
4. **Async model:** `get()` waiting for sync (RTO23c); how operations marked `=> io` render.
5. **Type mapping:** the API map from the ably-js-shaped pseudocode to the SDK. This covers `PathObject` and `Instance` navigation and reads, which conversions throw and which return null, the write-value union and its wrapper type, enums, and numeric types.
6. **Mutations, subscriptions and events:** subscribe and unsubscribe, `StatusSubscription`, the subscription event types and their options.
7. **Messages and errors:** the public `ObjectMessage` fields, the error codes the objects spec defines (for example 92005, 92007 and 92008) with `statusCode` and `cause`, and timestamp units.
8. **Internal access:** the white-box specs. These are typically the `internal_*` specs and `objects_pool.md`, but confirm each one by reading it ([7.5](phase-5-generate-skill.md#75-step-5e-write-the-module-notes) item 8). Also the ladder (D-12) and the placement boundary.
9. **Helper coverage:** every `standard_test_pool.md` symbol mapped to its native symbol, and each fixture helper's scope (which client messages `setup_synced_channel` answers, and any option the fake-clock variant needs).
10. **Overrides:** the reading list (the `objects-features.md` sections), naming (never dropping the spec point, guide [5.1](../../../docs/writing-uts-spec-translator-skills.md#51-traceability)), the `deviations.md` location in the owning module, and expected audit shortfalls.
11. **Integration helpers:** REST provisioning (`provision_objects_via_rest`, closing its client) and sync waits.
12. **A worked example and a symbol index.**
13. **Shape deviations** (`S-1…S-n`), if the SDK is typed.

The `objects` notes of the existing `uts-to-swift` and `uts-to-kotlin` skills are reference implementations: read them only as a last resort, under [2.1](../SKILL.md#21-your-inputs), for a pattern, never to copy. The guide's [Patterns to avoid](../../../docs/writing-uts-spec-translator-skills.md#patterns-to-avoid) lists defects found in exactly those files (a naming override that drops the spec point, and spec points cited where they don't exist).

## 12.5 An SDK-blocked objects tier

Guide [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must) ("SDK-blocked objects smoke test") and guide [4, step F](../../../docs/writing-uts-spec-translator-skills.md#phase-1-selection-steps-0-and-af) are the requirement. When the SDK exposes the LiveObjects public API but doesn't implement it yet, the objects unit smoke test (`setup_synced_channel` completes and a pool object reads its seeded value) can't pass. Without this rule, the objects tiers would stay unready, and objects specs could never be translated.

**When it applies.** Only when all of these hold. Any other red stays a harness or environment stop, as everywhere else.

1. D-28 is full objects support.
2. The objects harness compiles.
3. Every helper self-test of that tier is green.
4. Every failing smoke-test assertion traces to an SDK not-implemented path. Record the evidence for each: the error or stack trace naming the SDK symbol (for example a `NotImplementedError` or a `TODO` throw), with its file and line.

**What you do:**

- **Known gaps.** List each one in the harness README's Known gaps as `SDK-blocked: <feature> (<evidence>)`.
- **Keep the test running.** Keep the failing assertion running in CI under the runner's *strict* expected-failure marker (or as an assertion that the not-implemented error occurs). It is never skipped, and once the SDK passes it, the marker fails, which forces the gap to be cleared (guide 2.7 "In CI, ungated").
- **Readiness data.** Mark the tier in the mapping as translate-only, not unready. *Procedure recommendation:* a `translateOnly` object per module, for example `"translateOnly": {"unit": "SDK-blocked: RTO23 get()"}`, which the resolver reports as `tiers.<tier>.translateOnly` with the reason ([7.1](phase-5-generate-skill.md#71-step-5a-create-the-layout-and-the-mapping-file)).
- **Generated skill, step E.** Don't offer evaluate for that tier.
- **Generated skill, step F.** Pass only when the SDK-blocked items listed in Known gaps (under their expected-failure marker) are the only failures, and print them clearly in the preflight output. Re-check them in every preflight. When the smoke test passes, clear the Known gap and the `translateOnly` entry; evaluate then becomes available.
- **Records.**
  - D-28: "full; SDK-blocked: …".
  - The Final report: its own "SDK-blocked" line.
  - In upgrade mode, gap-audit section E.
- **Acceptance checklist.** The row "Harness smoke tests per tier and helper self-tests …" is ✗ with the reason "SDK-blocked: objects unit smoke test (<feature>)". This is the same pattern as the declined-CI case in [5.4](phase-3-build-harness.md#54-step-3d-stop-7-confirm-the-harness). Other rows aren't affected.
- **Pilot.** The objects pilot for that tier runs translate-only, and the report says so (8.3).
