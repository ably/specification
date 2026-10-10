# Glossary

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention). Links that climb out of the skill directory are spec-repo paths: resolve them against the spec clone, not against this file's installed location.

| Term | Meaning |
|---|---|
| **UTS** | Universal Test Suite: language-neutral pseudocode test specs in `uts/` of the spec repo |
| **Module** | A top-level corpus directory: `rest`, `realtime`, `objects` |
| **Tier** | `unit` (mocked transports), `integration` (direct sandbox), `proxy` (sandbox through `uts-proxy`), detected by path |
| **Spec** | One Markdown file of UTS tests; **features spec** means the Ably specification under `specifications/` |
| **Test ID / tag** | The `**Test ID**` of a spec test; the `UTS: <id>` comment above the derived test |
| **Helper spec** | A spec of harness behaviour (`mock_http.md`, `mock_websocket.md`, `mock_vcdiff.md`, `standard_test_pool.md`); implemented once, never translated |
| **Hook** | An injection point in SDK production code that the harness uses (transport, HTTP, clock, network monitor, randomness) |
| **Harness (UTS test infrastructure)** | The native test library implementing the helper specs, wait helpers, sandbox and proxy helpers and fixtures |
| **Reuse / wrap / extend / build** | The four ways to provide a harness capability from what the repo has ([4.2](phase-2-design-harness.md#42-step-2b-assess-each-capability-reuse-wrap-extend-or-build)) |
| **Shared / port-only** | Harness code used by native tests and UTS ports alike / used only by UTS ports |
| **Smoke test** | A per-tier harness test that drives one tier end to end through the real hooks (guide 2.7); permanent, in CI, not spec-derived, no tag, never a reference test |
| **Self-test** | A harness test that checks one helper obeys its helper-spec contract (guide 2.7); permanent, in CI, no tag |
| **Preflight** | The generated skill's step F: compile, run the tier's smoke tests and self-tests, check Known gaps; stop on red |
| **Reference test** | A reviewed, spec-derived test per tier that the skill reads before generating |
| **Reference implementations** | The existing `uts-to-swift` (ably-cocoa) and `uts-to-kotlin` (ably-java) skills and their harnesses, linked from the guide: a last-resort, read-only reference for patterns, never copied and never an authority ([2.1](../SKILL.md#21-your-inputs)). Not a reference test |
| **Opus-class model** | The most capable model tier available (Claude Opus or an equivalent); required for this procedure and its sub-agents ([2.8](../SKILL.md#28-model-tier-and-sub-agents)) |
| **Notes** | `references/<module>-mapping.md`: how ably-js-shaped pseudocode maps to this SDK for one module |
| **Resolver** | `resolve_uts.py`: validates a module and derives targets and names; its output is the single source of truth |
| **Audit** | `audit_translation.py`: compares a spec with its test file (IDs, ledger, counts) |
| **Ledger / shortfall** | The per-test list of spec lines by kind / spec count minus test count, for assertions and waits separately |
| **Translate-only / evaluate** | Generate and statically check / also run and diagnose |
| **Deviation** | An SDK behaviour that differs from a correct spec, recorded in `deviations.md` |
| **Stand-in** | A harness-level difference in how a test drives the SDK; disclosed in a comment, not a deviation |
| **White-box spec** | A unit spec that drives internal APIs; listed in the notes |
| **Delegating spec/test** | One that says to run another module's tests against this client |
| **Re-sync** | Re-auditing a module against a newer spec SHA and regenerating what changed |
| **Spec SHA** | The commit of the local spec clone that a test, or the skill, was derived from |
| **Phase N / generated-skill Phase 1–2** | "Phase N" (1–7) is a phase of this procedure. "Generated-skill Phase 1" (selection, steps 0 and A–F) and "generated-skill Phase 2" (per spec, steps 1–7) are the generated `uts-to-<lang>` skill's workflow (guide [4](../../../docs/writing-uts-spec-translator-skills.md#4-the-workflow-the-skill-must-implement)). `writing-derived-tests.md` Phase 1/2 is always named with that document |
| **Working records** | Repo profile, Harness design (with the gap table), Design record, Final report; in upgrade mode, also the gap audit |
| **Orient** | Step 0 of every run: eligibility, the state class and the recommended mode, before any phase ([section 13](orient.md#13-step-0-orient)) |
| **Run mode** | Create or Upgrade/Fix (diff-driven, full gap audit, or regenerate), chosen at STOP-13 (D-27); an interrupted run is resumed or restarted |
| **State class** | Orient's classification: INELIGIBLE, S0 (nothing), S1 (tests or harness, no skill), S2 (a skill this procedure built), S3 (a skill of unknown origin), S4 (ambiguous); re-entry is an overlay |
| **State summary** | The short report Orient shows at STOP-13 and copies into the Repo profile |
| **Origin** | Whether a skill was built by this procedure: `creator-records`, `creator-metadata` (the D-30 stamp) or `unknown` |
| **Run status** | The design record's line saying whether a run is in progress (and in which phase) or finished; drives re-entry |
| **Eligible repo** | An Ably Pub/Sub SDK repository on the whitelist in `assets/eligibility.json` (current and legacy names; every other repository is rejected) that passes the definition gate ([13.2](orient.md#132-repository-eligibility-stop-16)) |
| **Definition gate** | Eligibility's secondary check, after the whitelist, that a REST or Realtime client entry point is *defined* in non-test source, not merely used: no definition in a sizeable tree rejects (`NO_CLIENT_DEFINITION`), in a small one asks (`NO_SDK_FINGERPRINT`); a whitelist `capabilityOverride` satisfies it ([13.2](orient.md#132-repository-eligibility-stop-16)) |
| **Data files** | `assets/eligibility.json` (which repositories are accepted) and `assets/capability-names.json` (SDK aliases, door factories, legacy names, the names fallback): what maintainers update as the org and the SDKs change, instead of the scripts; each starts with `_description`, and `_comment` keys explain the entries that need it ([section 10](upgrade-diff-driven.md#10-upgradefix-diff-driven)) |
| **Names source** | Where the detectors' names came from: `spec` (parsed from the spec clone's IDL at run time, with `specRevision`) or `fallback` (the data file's minimal names, with a loud warning) ([13.8](orient.md#138-capabilities-and-scope-stop-17-d-31)) |
| **Capability profile** | The SDK's REST and Realtime clients (with connection, channels and presence) as `detect_capabilities.py` finds them, confirmed in Orient and recorded as D-31; it decides the skill's scope ([13.8](orient.md#138-capabilities-and-scope-stop-17-d-31)) |
| **Side, door** | In an SDK split into server and device packages, a *door* is a public factory that returns a client (`PubSubDevice.CreateClient`); a *side* is the set of clients reached through one door, or through the core constructors (`core`). D-31 records the side the UTS tests construct clients through, and the scope follows it ([13.8](orient.md#138-capabilities-and-scope-stop-17-d-31)) |
| **Not applicable (capability absent)** | A module, spec, gap-table row or checklist row that needs a capability the SDK (or the chosen side) lacks: not a gap and never ✗; it becomes a gap when the capability appears |
| **Unsupported** | The mapping marker (`"unsupported": "<reason>"`) on a whole module the SDK can't support, such as `realtime` for a REST-only SDK; the resolver and the skill refuse it with the reason, except any `extraTests` it lists |
| **Capability-inapplicable** | A test that needs a client the SDK lacks (a REST test that uses a Realtime client, in a REST-only SDK): guide 7.4 case (d), listed in the mapping's `capabilityInapplicable` or noted in the test file; not a deviation, and not language-inapplicable |
| **Partial skill** | A skill scoped to the SDK's capabilities (REST-only or realtime-only), extended later by Upgrade/Fix |
| **Gap audit** | Upgrade/Fix's list of each checklist item an existing skill, its harness or its UTS-derived tests don't meet, with the user's choice per item (add, skip, defer) and a preserve list ([section 11](upgrade-existing-skill.md#11-upgrade-mode-audit-and-upgrade-an-existing-skill)) |
| **SDK-blocked** | An objects tier whose smoke test fails only on SDK not-implemented paths while every self-test is green; listed in Known gaps, kept running under a strict expected-failure marker, translate-only until it passes ([12.5](liveobjects-support.md#125-an-sdk-blocked-objects-tier)) |
| **LiveObjects evidence** | `detect_liveobjects.py`'s spec-derived regex findings (public-API, legacy, shared, internal, wire-only names), from which STOP-14 recommends whether to add `objects` support ([section 12](liveobjects-support.md#12-liveobjects-objects-support)) |
