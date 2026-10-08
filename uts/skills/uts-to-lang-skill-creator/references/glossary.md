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
| **Reference implementations** | The existing `uts-to-swift` (ably-cocoa) and `uts-to-kotlin` (ably-java) skills and their harnesses, at the commits the guide pins: a last-resort, read-only reference for patterns, never copied and never an authority ([2.1](../SKILL.md#21-your-inputs)). Not a reference test |
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
| **Phase N / generated-skill Phase 1–2** | "Phase N" (1–7) is a phase of this procedure. "Generated-skill Phase 1" (selection, steps 0 and A–F) and "generated-skill Phase 2" (per spec, steps 1–7) are the generated `uts-to-<lang>` skill's workflow (guide [4](../../../docs/translator-skills/writing-translator-skills.md#4-the-workflow-the-skill-must-implement)). `writing-derived-tests.md` Phase 1/2 is always named with that document |
| **Working records** | Repo profile, Harness design (with the gap table), Design record, Final report |
