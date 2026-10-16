# 5. Phase 3: build and verify the harness

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention). Links that climb out of the skill directory are spec-repo paths: resolve them against the spec clone, not against this file's installed location.

**Goal:** the approved harness exists, compiles under the repo's strictest settings, and each supported tier has green smoke tests and helper self-tests (guide [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)), wired into CI. This is part of the skill's deliverable, not a preliminary. Skip the rows the user didn't choose to build at STOP-3. At STOP-7, update the acceptance checklist's Harness rows with their evidence (the commands and results, the CI jobs).

## 5.1 Step 3a: rules while building

- **Scope is UTS only.** Change only the harness, the skill and the approved hooks. Don't fix, skip, retry or rewrite native tests, even flaky or failing ones. Record each one with its evidence (Repo profile; Final report, "Native test findings (not fixed)"). An SDK bug found while building is an observation for the Final report, never a fix.
- **Production hooks only after STOP-4 approval**, one proposal at a time, in the smallest form that works.
- **The approved proposal bounds the change.** Touch only the production files the STOP-4 proposal listed, in the shape approved. Another file, a new type in a different place, or a change to the default path needs a new STOP-4. Never restructure to avoid a stop (for example, putting new types in unrelated files to skip a project-file edit).
- Record the production diffstat in the build log, next to the proposal's file list.
- **Don't change existing behaviour** of doubles or helpers the native tests use; extend, wrap or add new code instead (see [2.2](../SKILL.md#22-what-you-may-change)).
- Follow the repo's test style (P-03, P-04, P-08): naming, file headers, assertion library, formatting.
- Run the existing tests that touch anything you changed, by filter, before and after the change. If that means the whole native suite (a cross-cutting hook), ask for that run in the same STOP-4 question (STOP-6).
- Move files with a plain `mv` (or the language tool's equivalent). Use `git mv` only if the user asked for staging ([2.2](../SKILL.md#22-what-you-may-change)): it stages the change.
- Log every design change you make while building in the decision log; update `uts-infra-design.md`.
- **Builds and test runs stay serial**, because the build output and its locks are shared. Self-tests for doubles already built, or tiers with disjoint new files, can be drafted in parallel sub-agents, in disjoint files or separate worktrees; you integrate them ([parallel-work.md](parallel-work.md)).

## 5.2 Step 3b: build in order, with acceptance checks

For a REST-only SDK (D-31), skip rows 6, 8 and 11, and drive row 4's fake-clock check with a REST timer (for example a fallback retry); the guide 2.7 items that need a WebSocket are n/a ([13.8](orient.md#138-capabilities-and-scope-stop-17-d-31)). For a realtime-only SDK or side, row 5 still builds `MockHttpClient`, with its self-tests driven through the Realtime client's HTTP requests (for example `time()` or token auth); only the REST unit smoke test is n/a.

Each step has an acceptance check; don't start the next step until it passes (or the user accepts a documented exception). **Bound:** if a row's check still fails after three fix attempts, stop (**STOP-10**) with a summary: the failure, what you tried, your diagnosis, and the options (change the design and log it, accept a documented exception, or descope the tiers the row blocks).

The smoke tests and self-tests in the checks below are the permanent harness tests of guide [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must) (MUST): build them as this phase's gates, and keep them in the repo and in CI afterwards, where the generated skill's preflight runs them. Each row's check is an explicit assertion in a harness test, not a manual observation.

Rows 4–7 depend on each other: build them in order, but run an acceptance item that needs a component from a later row as soon as that component exists (the fake-clock check needs a transport mock; the REST row's realtime-driven request needs `MockWebSocket`; the realtime row's state waits need row 7), and don't leave row 7 until every row 4–7 item passes. Common items that need an integration component (the integration state-wait helper, integration teardown) run at row 9, once that component exists; they are part of row 9's acceptance.

| Order | Build | Acceptance check |
|---|---|---|
| 1 | UTS test target/project and its tier selection (directories or filters per tier), wired so that `build-tests` compiles it; the harness's tier directories (root, `unit/`, `integration/`, `integration/proxy/`) and the harness-tests tree with the same tier folders, as Placement names them ([4.7](phase-2-design-harness.md#47-step-2g-plan-placement-harness-tests-and-build-order)) | A minimal harness test (one trivial passing test, in the harness-tests tree; delete it once row 2's self-tests exist) compiles, is collected and passes under the single-class filter and under the harness-test command with `{tier}` expanded |
| 2 | Library core: thread-safe capture, log sink, `assertContainsInOrder`, caller-attributed failure helper | Tests of the helpers themselves: `assertContainsInOrder` passes on `[connecting, disconnected, connecting, connected]` vs `[disconnected, connecting, connected]` and fails when the order is broken, and a repeated state passes (guide [6.7](../../../docs/writing-uts-spec-translator-skills.md#67-notes-on-the-catalogue)); capture lists are safe under concurrent appends; a failing helper reports the caller's line |
| 3 | Approved SDK hooks | Each hook replaces the real implementation for one client without affecting another client created afterwards (or, if process-global, that fact is recorded for decision D-14); the existing tests still pass |
| 4 | Fake clock wired through the clock hook | A timer-driven SDK behaviour doesn't happen before `ADVANCE_TIME` and does happen after it; a timed blocking wait in the SDK (if P-11 found any) is also driven by the fake clock; the async runtime's timers fire under it, and nothing waits on the real clock (guide [2.1](../../../docs/writing-uts-spec-translator-skills.md#21-sdk-test-hooks-must)); one advance runs cascaded work to quiescence (zero-delay reschedules and timers created mid-advance) |
| 5 | `MockHttpClient` per `mock_http.md`, plus the legacy `queue_*` API or its documented mapping | **REST unit smoke test and self-tests:** Every item in guide [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)'s Unit, REST entry, each as an explicit assertion |
| 6 | `MockWebSocket` per `mock_websocket.md`, including the alternative API, undocumented members and raw frames | **Realtime unit smoke test and self-tests:** Every item in guide [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)'s Unit, realtime entry, each as an explicit assertion |
| 7 | Wait helpers per [4.4](phase-2-design-harness.md#44-step-2d-design-the-wait-and-assertion-helpers) | **Helper self-tests:** every item in guide [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)'s Common and Unit, fake clock entries, each as an explicit assertion; in addition, `AWAIT_STATE` completes for a state reached before or during the wait (the teardown self-test follows your SDK's `close()` behaviour, guide 5.4) |
| 8 | `MockNetworkListener` (if the SDK has a network monitor), `MockVCDiff*` (if the SDK supports deltas) | A smoke test drives each one |
| 9 | `SandboxApp`, `ably-common` access (after **STOP-6**); if D-28 chose full objects support, `provision_objects_via_rest` | **Direct integration smoke test and self-tests:** Every item in guide [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)'s Direct sandbox entry, each as an explicit assertion |
| 10 | `ProxyManager` and `ProxySession` (pinned version; every developer OS) (after **STOP-6**) | **Proxy smoke test and self-tests:** Every item in guide [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)'s Proxy entry, each as an explicit assertion; clients authenticate as decided in D-18 |
| 11 | Module helpers, e.g. the `standard_test_pool.md` implementation and a plugin client-options builder (for `objects`, only if D-28 chose full support) | **Objects unit smoke test and self-tests:** Every item in guide [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)'s Unit, objects entry, each as an explicit assertion. The smoke test lives beside the module helpers (outside every `targetDir`) and is selected by the unit tier's harness command. If it fails only on SDK not-implemented paths, with green self-tests, record it as SDK-blocked under [12.5](liveobjects-support.md#125-an-sdk-blocked-objects-tier) instead of spending the three fix attempts |
| 12 | Harness README describing what exists, with its Known gaps | See [5.3](#53-step-3c-write-the-harness-readme) |
| 13 | CI wiring (needs **STOP-5** approval), or a suggested change for the Final report | Each suite runs in exactly one CI job per platform it targets; nothing reports green without executing; each tier's smoke tests and self-tests run, ungated, in that tier's job (guide [2.5](../../../docs/writing-uts-spec-translator-skills.md#25-build-and-ci-wiring-must), [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)); the repo's existing test commands and jobs (e.g. bare `pytest`, `dotnet test` on the solution) don't also collect the UTS or harness tests (exclude them via `testpaths`/`--ignore`, a solution filter or a separate project), unless that job is deliberately their one CI home |

Then compile all test targets as strictly as CI does (P-06) and run the repo's lint gates over the new code.

**Layout check** (guide [2.2](../../../docs/writing-uts-spec-translator-skills.md#22-a-shared-test-library-implementing-the-helper-specs-must), "Harness layout", MUST): every harness file sits in the directory the Placement table gives it, under its tier; no harness test sits in the harness library (except under `<harness>/tests/` where Placement chose that); and no tier references a sibling: grep each tier directory for the other's namespace, package or path (`unit/` files never name `integration/` symbols, and the reverse; only `integration/proxy/` may use `integration/`). A hit moves the shared piece up to the lowest directory both tiers see, or is a design change logged in the decision log.

## 5.3 Step 3c: write the harness README

Write a README next to the harness covering everything guide [3.1](../../../docs/writing-uts-spec-translator-skills.md#31-layout) and [2.2](../../../docs/writing-uts-spec-translator-skills.md#22-a-shared-test-library-implementing-the-helper-specs-must) say it should cover (3.1's list, and 2.2's threading facts for `mock_websocket.md`). Procedure detail:

- take the symbol map from the [4.3](phase-2-design-harness.md#43-step-2c-map-each-helper-spec-to-native-code) tables as built, and the known gaps from the gap table's `partial` and `missing` rows;
- add the layout: the tier directories and what each holds (guide 2.2), the harness-tests tree with its smoke-test and self-test files per tier, the shared and port-only code, module helpers and test targets; and the complete command that runs each tier's smoke tests and self-tests;
- write the **Known gaps** section (MUST): every helper-spec member, contract point or corpus construct the harness doesn't implement, by tier, as a table whose first column is the exact pseudocode token, matched by grepping the selected specs' `pseudo` fences (guide 3.1), then status and workaround, so the skill's preflight can match it against selected specs. It also lists the constructs of every module D-31 makes unsupported, with the status "unsupported: <reason> (D-31)": for a REST-only SDK the realtime and objects constructs (`Realtime(`, `AWAIT_STATE`, `mock_ws`, `CONNECTED_MESSAGE`, `MockNetworkListener`, …); for a realtime-only SDK the REST-only ones (`Rest(`); and "hooks unreachable from the SDK language" when P-13 found it;
- index every module's fixture helpers in one place, even those in a separate test-support module;
- link each fixture helper's scope to the module notes (item 9), where guide 2.2 puts it;
- record the README's full repo path in the Design record.

## 5.4 Step 3d: STOP-7, confirm the harness

Re-run the assessment of [4.2](phase-2-design-harness.md#42-step-2b-assess-each-capability-reuse-wrap-extend-or-build) and the tier matrix of [4.8](phase-2-design-harness.md#48-step-2h-derive-tier-feasibility), and update `uts-infra-design.md` with the build log. Show the user the smoke-test and self-test results per tier (each run by its tier's filter), their CI wiring, the files created or changed, and the updated tier matrix. Only then continue to the skill.

**Done when:**

- every row the user chose to build is `present`;
- each supported tier has green smoke tests and self-tests covering guide 2.7, wired into CI;
- if the user declined the CI change at STOP-5: the Final report lists it as an unmet requirement (the skill doesn't conform to guide 2.5/2.7 until CI runs the harness tests), the acceptance-checklist rows "Harness smoke tests per tier and helper self-tests …" and "One CI home per suite …" are ✗ with that reason, and the harness README states that CI doesn't yet run them. The tier stays ready, because the skill's preflight still runs the harness tests locally on every run;
- an objects smoke test that fails only on SDK not-implemented paths, with green self-tests, is recorded as SDK-blocked under [12.5](liveobjects-support.md#125-an-sdk-blocked-objects-tier): the tier is translate-only, and the smoke-test checklist row is ✗ "SDK-blocked";
- the strict compile, lint and the layout check pass;
- the harness README exists;
- the user has confirmed at STOP-7.

If the user declines network access at STOP-6, the integration and proxy tiers aren't supported: mark them unready in the mapping (their `unready` reason, which the resolver reports as `blockedBy`: harness tests not run) and list them in the Final report.
