# 4. Phase 2: design the harness

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention). Links that climb out of the skill directory are spec-repo paths: resolve them against the spec clone, not against this file's installed location.

Contents:

- [4.1 Step 2a: list the required capabilities](#41-step-2a-list-the-required-capabilities)
- [4.2 Step 2b: assess each capability: reuse, wrap, extend or build](#42-step-2b-assess-each-capability-reuse-wrap-extend-or-build)
- [4.3 Step 2c: map each helper spec to native code](#43-step-2c-map-each-helper-spec-to-native-code)
- [4.4 Step 2d: design the wait and assertion helpers](#44-step-2d-design-the-wait-and-assertion-helpers)
- [4.5 Step 2e: design the sandbox and proxy helpers](#45-step-2e-design-the-sandbox-and-proxy-helpers)
- [4.6 Step 2f: propose the SDK test hooks](#46-step-2f-propose-the-sdk-test-hooks)
- [4.7 Step 2g: plan placement, harness tests and build order](#47-step-2g-plan-placement-harness-tests-and-build-order)
- [4.8 Step 2h: derive tier feasibility](#48-step-2h-derive-tier-feasibility)
- [4.9 Step 2i: STOP-3, approve the design and choose the scope](#49-step-2i-stop-3-approve-the-design-and-choose-the-scope)

**Goal:** a written design for the harness in this language, derived from the Repo profile: for every capability guide [section 2](../../../docs/writing-uts-spec-translator-skills.md#2-the-harness-uts-test-infrastructure) requires, whether to **reuse** what exists, **wrap** it, **extend** it or **build** it new; how each helper spec maps to native code; which SDK hooks are still needed; where the code lives; and how each piece will be accepted. The user approves the design before you build anything.

Design principles:

- **Follow guide [2.2](../../../docs/writing-uts-spec-translator-skills.md#22-a-shared-test-library-implementing-the-helper-specs-must)**: implement each helper spec once, and build the harness to look like the pseudocode. When an existing double has the right behaviour but a different shape, **wrap it in a pseudocode-shaped facade** rather than teaching the skill to translate into the old shape.
- **Reuse what is correct; don't reuse what is subtly wrong.** An existing double that misses a helper-spec guarantee (for example a synchronous `close()`) will make the UTS ports flaky. Extend or replace it for the UTS ports, leaving the native tests' behaviour unchanged.
- **Hooks** are injected at client construction, per-client where the SDK allows (guide [2.1](../../../docs/writing-uts-spec-translator-skills.md#21-sdk-test-hooks-must), [2.6](../../../docs/writing-uts-spec-translator-skills.md#26-understand-the-sdks-concurrency-model-must)).

## 4.1 Step 2a: list the required capabilities

Start the gap table from rows G-01 to G-20 of the [uts-infra-design template](../assets/templates/uts-infra-design.md), which cover every requirement of guide [2.1](../../../docs/writing-uts-spec-translator-skills.md#21-sdk-test-hooks-must) to [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must). Split a row where its parts get different approaches (e.g. `MockWebSocket` reused but its alternative API built). Rows for concurrency knowledge (G-18) come from the Repo profile (P-09 to P-14) and are "missing" if the profile left them unknown.

**Check:** every bullet and table row of guide section 2 maps to a gap-table row.

## 4.2 Step 2b: assess each capability: reuse, wrap, extend or build

This is the guide's "Reuse before you build" ([2.2](../../../docs/writing-uts-spec-translator-skills.md#22-a-shared-test-library-implementing-the-helper-specs-must)) applied to every row. For each row, record the status (`present`, `partial`, `missing`, `n/a`), the evidence (file and symbol, or what you searched for), and the **approach**:

| Approach | When |
|---|---|
| **Reuse** | An existing component already meets the requirement's semantics and shape (verified, not assumed) |
| **Wrap** | The semantics are right but the shape differs from the pseudocode; add a facade with the spec's names |
| **Extend** | The component is close but lacks capabilities (e.g. no WS-level timeout, no raw frames); add them without changing existing behaviour |
| **Build** | Nothing suitable exists, or what exists is semantically wrong for UTS |
| **n/a** | The SDK lacks the feature (e.g. `MockVCDiff*` when the SDK has no delta support); confirm against the features spec in the clone and give the reason |

Also record which tiers and modules each row blocks, whether closing it needs a production-code change, and a size (S/M/L). "Partial" always says what is missing.

If harness code already exists, **check it, don't trust it**: compile it, run its tests by filter, and compare its behaviour with the semantics in 4.3 and 4.4.

## 4.3 Step 2c: map each helper spec to native code

Read each helper spec in full, then design its native implementation. For each, produce a symbol table in `uts-infra-design.md`: every symbol the helper spec declares **and** every harness symbol the corpus uses (find them with the scanner in [7.4](phase-5-generate-skill.md#74-step-5d-fill-the-construct-catalogue); the corpus uses members the helper specs don't declare) → native type and member → approach (reuse, wrap, extend, build) → the existing component it builds on, if any.

| Helper spec | Design questions to answer | Requirements to check against |
|---|---|---|
| [`mock_http.md`](../../../rest/unit/helpers/mock_http.md) | Which HTTP hook does `install_mock` use? Does an existing HTTP double capture method, URL, headers and body? Can it fail at connection level separately from request level? Will the legacy `queue_*` calls be implemented, or mapped onto `onRequest` handlers in the skill? | The helper spec; guide 2.2 `mock_http.md` row |
| [`mock_websocket.md`](../../../realtime/unit/helpers/mock_websocket.md) | Which transport hook installs it? Does an existing transport double exist, and is its `close()` asynchronous? How are typed messages and raw untyped frames sent to the client? How are client frames captured? | The helper spec (including "Async Behavior and Event Loop Considerations"); guide 2.2 `mock_websocket.md` row and the notes below it |
| [`mock_vcdiff.md`](../../../realtime/unit/helpers/mock_vcdiff.md) | Does the SDK support deltas, and how is a decoder registered? | The helper spec; guide 2.2 |
| [`standard_test_pool.md`](../../../objects/helpers/standard_test_pool.md) (in scope only if D-28 chose full objects support, [12.3](liveobjects-support.md#123-what-each-choice-adds-phase-by-phase)) | Which channel and plugin setup does `setup_synced_channel` need? Where do module helpers live (where internals are visible, if white-box specs need them)? How is the plugin registered in a client-options builder? | The helper spec; guide 2.2 `standard_test_pool.md` row and "Document each fixture helper's scope" |
| *(no helper spec)* `MockNetworkListener` | Is there a network-monitor hook? | guide 2.2 last table row; `realtime/unit/connection/network_change_test.md` |

Where a design question can only be answered by a production change, it becomes a hook proposal (4.6).

## 4.4 Step 2d: design the wait and assertion helpers

Design these against the async and concurrency model from P-09 to P-12 and the existing helpers from P-17. For each, record the native symbol and whether you reuse an existing helper (only if it already meets the requirements), wrap it, or build it. The requirements are in the sources below; the self-tests that prove them (guide [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)) are in [5.2](phase-3-build-harness.md#52-step-3b-build-in-order-with-acceptance-checks), rows 2, 4 and 7.

| Helper | Requirements |
|---|---|
| `AWAIT_STATE` (connection and channel) | guide [5.7](../../../docs/writing-uts-spec-translator-skills.md#57-waits-must-catch-events); `writing-test-specs.md` "State Transitions" |
| `poll_until`, `poll_until_success` | `writing-test-specs.md`; `uts/README.md`; guide 5.7; `writing-derived-tests.md` "No real timers in unit tests" (deadlines) |
| `process_pending_events()` | `uts/README.md`; guide [2.6](../../../docs/writing-uts-spec-translator-skills.md#26-understand-the-sdks-concurrency-model-must) |
| Wall-clock timeout wrapper | `writing-derived-tests.md` "Integration timeouts are wall-clock"; guide [5.6](../../../docs/writing-uts-spec-translator-skills.md#56-time-and-waiting) |
| Fake clock driver (`enable_fake_timers`, `ADVANCE_TIME`) | guide [2.1](../../../docs/writing-uts-spec-translator-skills.md#21-sdk-test-hooks-must), [5.6](../../../docs/writing-uts-spec-translator-skills.md#56-time-and-waiting); covers every time source in P-11 |
| Thread-safe capture, log sink, caller-attributed failures | guide 2.2 |
| `assertContainsInOrder` | guide [6.7](../../../docs/writing-uts-spec-translator-skills.md#67-notes-on-the-catalogue) |

## 4.5 Step 2e: design the sandbox and proxy helpers

- **Sandbox** (guide [2.3](../../../docs/writing-uts-spec-translator-skills.md#23-sandbox-provisioning-and-fixtures-must-for-integration-tiers)): check the native integration tests' provisioning (P-18) against guide 2.3; reuse or wrap it if it meets every point, otherwise build `SandboxApp`. Decide how clients are pointed at the sandbox and how per-run vs per-test provisioning maps to the runner's suite fixtures (P-03).
- **Proxy** (guide [2.4](../../../docs/writing-uts-spec-translator-skills.md#24-the-proxy-must-for-the-proxy-tier), [`proxy.md`](../../../docs/proxy.md)): design `ProxyManager` and `ProxySession` to every point of guide 2.4. Checking that the pinned release has a binary for every developer OS in P-07 is a network read: ask first (**STOP-6**), or mark it unverified until Phase 3 row 10 and plan platform gating where it can't run. Include every operational requirement in guide 2.4. Default the session's endpoint to the sandbox, because two corpus specs pass only `rules:` (guide [6.7](../../../docs/writing-uts-spec-translator-skills.md#67-notes-on-the-catalogue)). Decide auth through the proxy (D-18).

## 4.6 Step 2f: propose the SDK test hooks

For every hook row that isn't `present`, write a proposal in `uts-infra-design.md`:

- the API (name, type, where it is set), modelled on the repo's existing test options if it has any (P-13);
- the default behaviour (unchanged for users);
- its visibility (test-only if the language allows);
- every production file it touches;
- how the harness installs it at client construction, and whether it is per-client;
- for the clock hook, the list of time sources from P-11 it covers, including timed blocking waits and the async runtime's timers.

These proposals are presented at STOP-3 and need individual approval at **STOP-4** before you implement them.

## 4.7 Step 2g: plan placement, harness tests and build order

- **Placement** (guide 2.2, "Placement" and "Recommended layout"): name the harness library and its per-tier directories, the directory and target for shared test-support code (importing no test framework), port-only harness code, and each module's helpers. Put white-box suites, and module helpers they need, where internals are visible (P-14; guide 2.6).
- **Harness tests:** the per-tier smoke tests and helper self-tests of guide [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must), item by item, for every tier you plan to support. They are permanent and run in CI; they carry no `UTS:` tag and are never copied by the skill; they live outside every directory the mapping will give the resolver as a `targetDir`. Name the command that runs each tier's set plus the common self-tests (guide 2.7 "Selectable"); it goes into the mapping's `harness` entry (D-03). Name the CI job that runs it (5.2 row 13). The acceptance checks in [5.2](phase-3-build-harness.md#52-step-3b-build-in-order-with-acceptance-checks) say what each must prove.
- **Build order:** follow the order in 5.2, dropping rows that are `present` or out of scope.

## 4.8 Step 2h: derive tier feasibility

Fill a module × tier matrix: for each of `rest`, `realtime`, `objects` and each of unit, integration, proxy, mark **ready**, **ready after building rows X, Y**, or **not possible** (with the reason, e.g. "not possible until the SDK has an objects API (placeholder notes; the skill refuses the module)"). A tier the corpus doesn't have for a module is `n/a` (check with `ls <spec-clone>/uts/<module>`). The `objects` rows follow D-28 ([12.3](liveobjects-support.md#123-what-each-choice-adds-phase-by-phase)). Modules and gap-table rows that need a capability the SDK (or the side chosen in D-31) lacks ([13.8](orient.md#138-capabilities-and-scope-stop-17-d-31)) are `n/a — capability absent: <capability> (D-31)`, not gaps:

- **REST-only:** every `realtime` and `objects` tier, and the G-rows 13.8 lists. Their G-19 and G-20 rows are built in their REST form: the sandbox smoke test publishes over REST and reads history; the proxy smoke test serves a REST request through an HTTP rule. The REST-only tests filed under `uts/realtime` (`extraTests`) run on these tiers.
- **Realtime-only:** every `rest` tier. No G-row is wholly n/a: G-02 (HTTP hook) and G-06 (`MockHttpClient`) are still needed, because the Realtime client uses HTTP for auth, time, history, `request()` and fallback. Only the `rest` tiers' smoke tests in G-19 are n/a.
- **Hooks unreachable** (P-13, an SDK that wraps native SDKs): the unit tiers are **not possible** until hooks exist in the SDK's language (guide [2.1](../../../docs/writing-uts-spec-translator-skills.md#21-sdk-test-hooks-must)); the integration and proxy tiers are assessed as usual.

A tier is **ready** only when its G-19 and G-20 rows (smoke tests and self-tests, guide 2.7) are present, green and wired into CI (or the CI change was declined at STOP-5 and is reported as unmet, so the skill doesn't yet conform to guide 2.5/2.7; see [5.4](phase-3-build-harness.md#54-step-3d-stop-7-confirm-the-harness)), or will be built in Phase 3. An objects tier whose smoke test ends SDK-blocked is **ready (translate-only)**, under the conditions of [12.5](liveobjects-support.md#125-an-sdk-blocked-objects-tier).

## 4.9 Step 2i: STOP-3, approve the design and choose the scope

Present `uts-infra-design.md`: the gap table, the helper-spec mappings, the wait-helper design, the sandbox and proxy design, the hook proposals, placement, the build order and the tier matrix. Ask the user to choose:

- **(a) Build the missing harness now**, all or a named subset. Recommend this option (the skill depends on the harness), but the user chooses. Continue with Phase 3.
- **(b) Plan it only.** Keep the build order, with each row's acceptance check and size, as the plan in `uts-infra-design.md`. Phase 3 is skipped for the planned rows; the skill is generated for the tiers that are already ready, and the unready tiers stay in the mapping but the skill must refuse them with a message naming the missing harness piece, as guide [4, step C](../../../docs/writing-uts-spec-translator-skills.md#phase-1-selection-steps-0-and-af) requires (see the readiness data in [7.1](phase-5-generate-skill.md#71-step-5a-create-the-layout-and-the-mapping-file)).
- **(c) Scope the skill to the tiers possible today.** As (b), without the plan.

Under (b) and (c), G-19 and G-20 for every tier the skill will offer can't be planned or scoped out; Phase 3 and STOP-7 still run for them.

In Upgrade/Fix (either sub-mode), the user chooses per row instead of (a)–(c): build, plan (defer) or skip, with the same exception for G-19 and G-20 ([11.4](upgrade-existing-skill.md#114-step-u3-stop-15-choose-per-item)). A tier the skill offers today whose smoke tests or self-tests won't be built becomes unready, and the skill refuses it until they exist.

Record the answer and any design changes the user asked for. Under (b) and (c), the skill's tier step (C) must offer only ready tiers, and the Final report lists the rest as known limitations.
