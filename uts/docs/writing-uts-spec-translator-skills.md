# Writing UTS Spec Translator Skills

This guide explains how to build a per-language agent skill (Claude Code and Codex) — `uts-to-python`, `uts-to-csharp`, `uts-to-go`, and so on — that translates UTS specs into native tests for one SDK. It is written for an SDK engineer building `uts-to-<lang>` in their own repo. Its rules were distilled from two existing skills, `uts-to-swift` (ably-cocoa) and `uts-to-kotlin` (ably-java), which appear here only as short examples, as the origin of a lesson, or as patterns to avoid ([Appendix](#appendix-existing-skills-background-and-patterns-to-avoid)). You shouldn't need to read these skills: this guide and the UTS docs are the authority, and they are meant to be complete. If they don't answer a question while you create or maintain a skill or its harness, the existing skills and harnesses MAY be consulted as a last resort, under the rules in [Reference implementations (last resort)](#reference-implementations-last-resort).

If you are an LLM agent asked to create a `uts-to-<lang>` skill for an SDK repo, use the [`uts-to-lang-skill-creator` skill](../skills/uts-to-lang-skill-creator/SKILL.md) (installation: [`uts/README.md`](../README.md#installing-the-skill-creator)), on an Opus-class model ([Model tier](#model-tier)). It is the step-by-step procedure for building the skill and its harness; this guide remains the authority on what the skill must contain.

**Intent.** A translator skill exists so that translation is near-mechanical: the same spec, translated twice, gives the same test.

- **Harness and skill are one deliverable.** The skill translates onto a harness built in the same repo from its existing test setup, and it isn't complete until that harness's smoke tests and self-tests are green, in CI, at every tier the skill supports ([section 2](#2-the-harness-uts-test-infrastructure)).
- **Easy to use.** One command (`/uts-to-<lang> <module-dir>` in Claude Code, `$uts-to-<lang> <module-dir>` in Codex) and four questions; the skill does the rest.
- **Context-complete.** Every run gathers the full context: the spec, the translation manual, the sources and README of the UTS test infrastructure (the **harness**), the module notes and the resolver output. A good test doesn't depend on anyone's memory.
- **Tests are reproducible artifacts.** The UTS spec plus the skill is the source of truth; the generated test is an output. When a translation is wrong or the spec changes, regenerate it ([section 9](#9-keeping-in-sync-with-spec-changes)) rather than hand-maintain it.
- **Fix the cause, then regenerate.** Fix the skill, the module notes or the harness, never only the generated file. Only DEVIATION gates, adapted assertions, UTS-spec-error fail-fast placeholders and `deviations.md` entries survive regeneration.

**How to read this guide.** Requirements use three levels:

- **MUST**: required for a skill that conforms to this guide. Most MUSTs protect translation fidelity (without them a skill produces tests that silently check less than the spec); the rest protect repeatability and reviewability.
- **SHOULD**: strongly recommended. Both existing skills learned these the hard way.
- **MAY**: optional, useful in some SDKs.

Facts about the existing skills and SDKs are **as of 2026-10-07**: spec commit `12540dcf`; ably-cocoa at `b5074d9b` and ably-java at `0ff24017` (the checkouts reviewed). Remote `main`, fetched the same day (ably-cocoa `2072e0cd`, ably-java `8b7d3f5f`), has no changes to either skill or UTS harness since those commits. They illustrate patterns, and some may since have been fixed.

## Contents

1. [Purpose and scope](#1-purpose-and-scope)
2. [The harness (UTS test infrastructure)](#2-the-harness-uts-test-infrastructure)
3. [Skill anatomy](#3-skill-anatomy)
4. [The workflow the skill must implement](#4-the-workflow-the-skill-must-implement)
5. [Translation rules](#5-translation-rules)
6. [Pseudocode construct catalogue](#6-pseudocode-construct-catalogue)
7. [Evaluation and deviations](#7-evaluation-and-deviations)
8. [Deterministic tooling](#8-deterministic-tooling)
9. [Keeping in sync with spec changes](#9-keeping-in-sync-with-spec-changes)
10. [Verification and CI](#10-verification-and-ci)
11. [Final report format](#11-final-report-format)
12. [Lessons learned](#12-lessons-learned)
13. [Checklist for a new `uts-to-<lang>` skill](#13-checklist-for-a-new-uts-to-lang-skill)
- [Appendix: Existing skills (background and patterns to avoid)](#appendix-existing-skills-background-and-patterns-to-avoid)

---

## 1. Purpose and scope

### What a translator skill is

A translator skill is a packaged procedure (`SKILL.md` plus a few scripts and notes) that an agent (Claude Code or Codex) follows to turn the pseudocode specs in one UTS module directory (`uts/rest`, `uts/realtime`, `uts/objects`) into runnable tests in your SDK's test suite. It optionally runs them and diagnoses failures. It is built on, and delivered with, a harness in the same repo: the native test library that implements the UTS helper specs, with its own smoke tests and self-tests (section 2).

### How it relates to the other UTS docs

| Document | Owns |
|---|---|
| [`uts/README.md`](../README.md) | Pseudocode conventions: identifier naming, absent values, property access, enum values, `poll_until_success`, `process_pending_events()`, language-inapplicable inputs |
| [`writing-test-specs.md`](writing-test-specs.md) | The pseudocode reference: Test IDs, mock patterns, `AWAIT_STATE`, `poll_until`, record-and-verify, error pattern, unique channel names |
| [`writing-derived-tests.md`](writing-derived-tests.md) | **Translation and evaluation semantics.** Faithful translation, the evaluation decision tree, the three test patterns, `deviations.md` format, idiomatic translation vs deviation, timer and timeout traps |
| [`integration-testing.md`](integration-testing.md), [`proxy.md`](proxy.md) | Integration and proxy tiers: sandbox setup, timeouts, protocol variants, the proxy session and rule API |
| **This guide** | How to package all of the above into a repeatable, scripted agent skill (Claude Code and Codex) for one SDK |
| Existing skills and harnesses ([Reference implementations](#reference-implementations-last-resort)) | Nothing normative: a last-resort, read-only reference for patterns when creating a skill, below every document above |

`writing-derived-tests.md` is the **source of truth for semantics**. This guide never redefines what a faithful translation is, or how a deviation is classified and recorded; it says how a skill enforces those rules. If the two ever disagree, `writing-derived-tests.md` wins.

### What the skill owns, and what it defers

| The skill owns (harness mechanics) | The skill defers (semantics) |
|---|---|
| Resolving where each test file goes and what it is called | What counts as faithful translation → `writing-derived-tests.md` Phase 1 |
| The pseudocode → SDK/test-framework mapping table | The three causes of a failure and the decision tree → `writing-derived-tests.md` Phase 2 |
| Per-module API notes (ably-js-shaped pseudocode → your SDK's API) | The `deviations.md` sections and entry fields → `writing-derived-tests.md` "Recording deviations" |
| The language rendering of each test pattern (skip idiom, fail-fast idiom) | `poll_until` / `poll_until_success` reference definitions → `writing-test-specs.md` |
| Build, run, lint and audit commands | Pseudocode meaning → `uts/README.md`, `writing-test-specs.md` |

A skill **SHOULD** keep only the language rendering of a rule and link to the source for its meaning. Inline copies of semantic rules drift. Both existing skills replaced their inline `deviations.md` format with a pointer to the manual for this reason, although they still inline the decision tree and test patterns.

### Model tier

Creating a skill and its harness, and running the skill, are long, multi-file reasoning tasks in which a silent omission costs far more than compute. Use **the most capable model tier available (Claude Opus or an equivalent Opus-class model)**. "Opus-class" means that tier, whatever its current version, not a particular release; in another tool (for example Codex), it means that tool's most capable tier, recorded by name.

| Task | Level | Why |
|---|---|---|
| Creating the skill and building its harness (the [procedure](../skills/uts-to-lang-skill-creator/SKILL.md)) | **MUST** | The agent must hold this guide, the procedure, the UTS docs, the helper specs and the SDK's source in context at once; design hooks, mocks, fixtures and CI wiring that span many files; and decide rules that every later run inherits, so one silent omission becomes a defect in every generated test |
| Translating and evaluating with the finished skill (`/uts-to-<lang>` or `$uts-to-<lang>`) | **SHOULD** | The resolver and the audit ([section 8](#8-deterministic-tooling)) make paths, names, ID coverage and assertion counts mechanical, but not the rest. Matching wait predicates and timeouts, copying comments verbatim, setup fidelity, and diagnosing a failure as SDK, spec or translation ([7](#7-evaluation-and-deviations), [8.3](#83-review-checklist-must-after-the-audit)) remain model judgement, and a count can't catch a changed predicate ([8.2](#82-audit-audit_translationpy-must)) |
| Sub-agents spawned during either (review, validation; pilot runs during creation serve creation) | **The level of the task they serve** | A reviewer weaker than the author misses what the author missed. A cheaper model MAY be used only for a clearly mechanical step whose result a script verifies (for example, running the audit over the corpus and collecting its JSON), if at all |

The deterministic scripts reduce the dependence on the model; they don't remove it. State the model tier in the skill, pin it only where a tool supports that ([3.3](#33-frontmatter-and-arguments)), and record the model used in every run's final report ([section 11](#11-final-report-format)).

---

## 2. The harness (UTS test infrastructure)

The harness is part of the deliverable, not an optional prerequisite: a `uts-to-<lang>` skill is delivered together with its harness, and it isn't complete until the harness's smoke tests and self-tests ([2.7](#27-harness-smoke-tests-and-self-tests-must)) are green, in CI, at every tier the skill supports. A skill can't make translation mechanical if the harness it translates onto doesn't exist or doesn't keep its contracts.

**Design the harness from the repo's existing test setup.** For every capability in 2.1–2.7, first find what the SDK's native tests already have, then decide to **reuse** it, **wrap** it in a pseudocode-shaped facade, **extend** it, or **build** new (2.2, "Reuse before you build"). Build the harness, and its tests, **before** writing the skill. In both existing SDKs this took several iterations, and the harness co-evolved with the first real translation run.

### 2.1 SDK test hooks (MUST)

The unit tier needs injection points in production code:

| Hook | Purpose | Examples |
|---|---|---|
| WebSocket transport factory | Install `MockWebSocket` | ably-java `DebugOptions.webSocketEngineFactory`; ably-cocoa `testOptions.transportFactory` |
| HTTP client/executor | Install `MockHttpClient` | ably-java `DebugOptions.httpEngine`; ably-cocoa `testOptions.httpExecutor` |
| Clock / timer source | `enable_fake_timers()`, `ADVANCE_TIME` | ably-java `DebugOptions.clock` (a `Clock` abstraction retrofitted across `Auth`, `Presence`, `Hosts`, `WebSocketTransport`); ably-cocoa `testOptions.timeProvider` |
| Reachability / network monitor | Keep the unit tier hermetic; drive `MockNetworkListener` (`realtime/unit/connection/network_change_test.md`) | ably-cocoa `testOptions.reachabilityClass` |
| Randomness | Jitter (`get_jitter_coefficient()`, `backoff_jitter_test.md`), fallback-host shuffle (RTN17j, `fallback_hosts_test.md`) | ably-cocoa `testOptions.jitterCoefficientGenerator`, `testOptions.shuffleArray` |

Mocks and the fake clock are injected **at client construction**, so the harness must install them before the client is created.

**The clock hook must cover every time source the SDK uses**: timers, and also blocking waits (condition variables, timed `wait`, dispatch-after). If any wait runs on the real clock, retries fire on wall-clock time regardless of `ADVANCE_TIME`, and "nothing happened before the advance" becomes unassertable. (ably-java found this when a retry ran on wall-clock time through `FakeClock.waitOn`, which does a real timed wait, commit `c4502c67`.) Likewise, check that the fake clock drives your async runtime's timers: in asyncio, for example, faking the wall clock doesn't fire `loop.call_later` callbacks; in .NET, route `Task.Delay` and timers through a `TimeProvider`-style abstraction. Two workable shapes: route every SDK delay (`sleep`, `call_later`, timeouts) through the clock hook, so `ADVANCE_TIME` runs them; or run unit tests on a virtual-time event loop whose `time()` the fake clock controls, in which case the wall-clock timeout wrapper must not use the loop's clock (it measures virtual time).

If a hook doesn't exist, add it to the SDK first. Without these hooks, the unit tier is impossible.

### 2.2 A shared test library implementing the helper specs (MUST)

Implement each helper spec **once**, as a native library that every derived test calls. Derived tests never hand-roll mock setup, protocol messages or serials.

| Helper spec | Must implement | Watch for |
|---|---|---|
| `rest/unit/helpers/mock_http.md` | `MockHttpClient`, `PendingConnection`, `PendingRequest`, `install_mock` / `uninstall_mock`, `reset()`, connection-level vs request-level failures | The injection mechanism is implementation-specific. The corpus still uses a legacy API that the helper spec doesn't define and `writing-test-specs.md` "Common Mistakes to Avoid" deprecates: the queue calls (`queue_response`, `queue_responses`, `queue_response_for_host`, `queue_response_for_url`, `queue_timeout`, `queue_delayed_response`; in `rest/unit/fallback.md`, `request.md`, `rest_client.md`) and the mock-owned request log `mock_http.captured_requests` (in `fallback.md`, `request_endpoint.md`, `request.md`, `rest_client.md`): implement them, or map them onto `onRequest` handlers and a local capture list in the skill |
| `realtime/unit/helpers/mock_websocket.md` | `MockWebSocket`, handler and await styles, raw-frame hooks (`onTextDataFrame` / `onBinaryDataFrame`), `respond_with_*`, `send_to_client`, `send_to_client_and_close`, `simulate_disconnect`, ping frames, templates (`CONNECTED_MESSAGE`, `CLOSED_MESSAGE`, `DISCONNECTED_MESSAGE`, `HEARTBEAT_MESSAGE`, `ERROR_MESSAGE(code, message)`, `PING_MESSAGE(id)`) | See the notes below the table |
| `realtime/unit/helpers/mock_vcdiff.md` | `MockVCDiffEncoder`, `MockVCDiffDecoder`, `FailingMockVCDiffDecoder` | Deterministic, not a real codec |
| `objects/helpers/standard_test_pool.md` | The standard pool, `STANDARD_POOL_OBJECTS`, `setup_synced_channel` (and the no-ack variant), every `build_*` builder, serial helpers (`ack_serial`, `remote_serial`, `below_ack_serial`, `SITE_CODE`, `POOL_SERIAL`), quiescence helper, `provision_objects_via_rest` | Serials compare as strings, so hand-written literals sort wrongly. REST provisioning uses the V2 format with the singular `/object` path, and any REST client used must be closed |
| *(no helper spec)* | `MockNetworkListener` with `simulate_network_lost()` / `simulate_network_available()`, installed via `install_mock` | Used by `realtime/unit/connection/network_change_test.md`; needs the network-monitor hook (2.1) |

`mock_websocket.md` notes:

- `close()` **must** call `onClose` **asynchronously**; `respond_with_success` **must** complete the connection **first**, then deliver CONNECTED asynchronously.
- `mock_ws.active_connection` is used in the helper spec's own examples but isn't declared in its interface. `connect_attempts`, `last_connect_url` and `create_mock_websocket()` aren't declared in any helper spec (`connect_attempts` is used in the corpus and in a `writing-test-specs.md` example; the other two only in the corpus). Support them anyway.
- The corpus also uses an alternative API: `on_connect(respond_with:)`, `on_message(action:, respond_with:)`, `on_client_message(…)`, `await_client_message(action:)`, `respond_with_connected()`, `close_from_server()`, and `send_to_client_raw(json)`. The last sends an untyped frame (`forwards_compatibility_test.md`), which even a typed SDK's harness must be able to produce.
- State, in the harness README and the skill, whether handler and await styles can be mixed for one event type, and on which thread handlers run. (ably-java's can't be mixed: a set handler consumes the event, so the matching `await_*` never returns; handlers run synchronously on the SDK's thread, so they must not block or await.)

The library also needs:

- **Wait helpers:** an event-latched `AWAIT_STATE`, value-returning `poll_until`, `poll_until_success`, `process_pending_events()`, and (for virtual-time runners) a wall-clock timeout wrapper. See [section 5](#5-translation-rules).
- **Thread-safe capture** for lists appended from SDK callbacks (ably-java `CopyOnWriteArrayList`; ably-cocoa `Captured<T>`).
- **A log sink** for "an error is logged" assertions.
- **An in-order subsequence assertion** for `CONTAINS_IN_ORDER`.
- **Caller-attributed failures:** helpers that time out or receive an unexpected error report the failure at the calling test line (Swift `sourceLocation:`, pytest `__tracebackhide__`, C# caller-info attributes), not inside the helper.
- **Per-tier smoke tests and helper self-tests (MUST)**, permanent and run in CI: the minimum set, and the rules for where they live and how they run, are in [2.7](#27-harness-smoke-tests-and-self-tests-must).

**Placement.** Separate **shared** test-support code (used by both the SDK's native tests and the UTS ports, importing no test framework) from **port-only** harness code (doubles and fixtures used only by UTS ports); keep port-only code with the ports. Module-specific helpers (for example the `standard_test_pool.md` implementation) live next to that module's suites; the shared library stays module-agnostic. For a plugin-backed module such as LiveObjects, provide a client-options builder in the module helpers that registers the plugin, so tests never wire it by hand.

**Recommended layout (SHOULD).** One harness library (a test-support module, target or package) that every target hosting UTS tests consumes as a test dependency, organised by tier, with its smoke tests and self-tests beside it and the generated tests kept separate:

```
<harness>/                      # the harness library; one per SDK
  README.md                     # what exists, how to run each tier's harness tests, Known gaps (3.1)
  common/                       # wait and poll helpers, capture, log sink, assertContainsInOrder, caller attribution
  unit/                         # client factory, MockWebSocket, MockHttpClient, fake clock, message templates, optional mocks
  integration/                  # SandboxApp, suite fixture with guaranteed teardown
  proxy/                        # ProxyManager, ProxySession, rule builders
  tests/                        # smoke tests and helper self-tests (2.7), by tier:
    common/ unit/ integration/ proxy/
<generated tests>               # the mapping's target directories (3.2), outside <harness>/
  unit/<module>/  integration/standard/<module>/  integration/proxy/<module>/
<module helpers>                # next to each module's suites, depending on <harness>, never the reverse;
                                # a module's smoke test lives beside its helpers (outside every target dir)
                                # and is selected by the unit tier's harness command
```

Where the SDK already has a test-options type, add the hooks to it, and implement the SDK's own transport and HTTP abstractions rather than patching internals. Keep the harness tests where one per-tier filter selects them (2.5), and where no generated test can collide with or overwrite them. (ably-java's `:uts` Gradle module is one example of this shape: per-tier harness packages, with the smoke tests in the module's own test set.)

**Document each fixture helper's scope** in the module notes: which client messages it auto-answers, which spec branches it doesn't wire (a DETACH reply, fake timers), the local pattern tests use for those gaps, and any option tweaks the gap needs. (ably-java: the fake-clock variant of `setupSyncedChannel` needs a large `maxIdleInterval`, or virtual-time advances trip the idle timer.)

**Reuse before you build.** If the SDK's native tests already have transport doubles, a fake clock or sandbox helpers, assess whether to reuse, wrap or extend them against the helper specs' semantics before writing new ones; never change their behaviour for the native tests that use them. Existing doubles bound to another test framework, or built for real-network interception rather than the helper specs' in-process semantics, are usually better left alone: build pseudocode-shaped doubles on the same SDK hooks instead, and extract shared plumbing (such as sandbox retries) for both. (One SDK kept its legacy doubles for its native suite and built new framework-free UTS doubles on the same transport and HTTP seams.)

**Build the harness to look like the pseudocode.** Callback-style mocks with the spec's handler names, and a client factory that mirrors `Realtime(options: …)`, turn translation into transliteration. ably-java's first generation run replaced a "wrap every callback in a coroutine" rule with callback-style mocks for exactly this reason.

### 2.3 Sandbox provisioning and fixtures (MUST for integration tiers)

- A `SandboxApp` helper that creates an app from `ably-common/test-resources/test-app-setup.json` against `sandbox.realtime.ably-nonprod.net` and deletes it best-effort. **Retry only idempotent requests** (fetching the app setup); never retry `POST /apps`, which can create duplicate apps when the response is lost. Check the HTTP status before parsing the body.
- `ably-common` as a submodule. It also provides `msgpack_test_fixtures.json` (`rest/unit/encoding/msgpack_interop.md`) and `encoding.json` (`load_fixtures`, `rest/unit/encoding/message_encoding.md`).
- A way to point the client at the sandbox. The docs use `endpoint: "nonprod:sandbox"`; an SDK without `endpoint` sets `realtimeHost`/`restHost` instead. Explicit hosts disable fallbacks: REC2c6 for `realtimeHost`/`restHost`, REC2c2 for an `endpoint` hostname.

### 2.4 The proxy (MUST for the proxy tier)

- A `ProxyManager` that downloads, caches and starts [`ably/uts-proxy`](https://github.com/ably/uts-proxy). Pin the version, and check that the pinned release publishes a binary for every developer OS (its GitHub release assets). An environment override pointing at a locally built binary (`UTS_PROXY_LOCAL_PATH` in both existing harnesses; ably-java also accepts `-Duts.proxy.localPath`) is useful; keep it a configuration override, not a test gate. Operationally, the manager also verifies the downloaded archive (a checksum), serialises the download across concurrent test processes, waits for the proxy's control endpoint to report healthy before returning, reaps the proxy process when the test process exits, and handles the port: proxy suites share one control port, so run them in one process (one fork or worker), or give each worker its own port.
- A native `ProxySession` implementing [`proxy.md`](proxy.md): `create_proxy_session`, `add_rules`, `trigger_action`, `get_log`, `close`, plus rule-builder helpers and a typed event log.
- **The `action` inside a frame `match` (`ws_frame_to_client` / `ws_frame_to_server`) must be a JSON string**: a name (`"ATTACHED"`) or a numeric string (`"11"`), never a number (the proxy rejects a number with HTTP 400). uts-proxy v0.3.0 resolves names only up to `AUTH` (17), so use numeric strings for `OBJECT` (`"19"`), `OBJECT_SYNC` (`"20"`) and `ANNOTATION` (`"21"`); an unresolvable name silently never matches. This applies only to `match.action`: a rule's own `action` is an object (`{"type": "suppress"}`), and the `action` inside an injected message stays a number. Rule builders should take an integer and stringify it, as both existing harnesses do.
- Proxy tests always use JSON: the proxy supports text frames only (`integration-testing.md`, "Protocol Variants").
- **Auth through the proxy.** The proxy hop is plain HTTP/WS (`tls: false`), and RSA1 and RSC18 say Basic Auth over HTTP without TLS results in an error (`writing-test-specs.md` "RSC18 only applies to Basic auth configurations": checked at construction). `proxy.md`, `integration-testing.md` and `writing-test-specs.md` nonetheless show `key: api_key` with `tls: false`. In practice, ably-cocoa authenticates proxied clients with a locally signed `TokenRequest`; ably-java does the same where the spec observes auth (`AuthReauthTest`), but its objects proxy suite (`ObjectsFaultsTest`) uses `key` over the plain hop, which ably-java permits. Token auth is the option valid under RSA1 for every SDK; whichever you use, say why in a comment.
- Platform gating where the proxy can't run (ably-cocoa wraps proxy files in `#if os(macOS)`).

### 2.5 Build and CI wiring (MUST)

- Test tasks or filters that select each tier (unit, direct integration, proxy), each with a single-class/single-test filter, and, per tier, a filter and the complete command that runs that tier's harness smoke tests and self-tests ([2.7](#27-harness-smoke-tests-and-self-tests-must)). The harness tests run ungated in their tier's CI job. Check the repo's existing test commands and jobs: a bare `pytest`, `dotnet test` on the solution, or a Gradle `test` that aggregates every module also collects the new harness and UTS tests (including network tiers). Exclude them there (`testpaths`/`--ignore`, a solution filter, a separate project or task), or include them deliberately in that job as their one CI home.
- **Every suite runs in exactly one CI job per platform it targets, and nothing runs green without executing** (MUST). Splitting by tier (unit in the fast check job; integration and proxy in a networked job) is recommended (SHOULD): ably-java does this, while ably-cocoa runs all UTS tiers from one job definition, one job per platform (an iOS / tvOS / macOS matrix; proxy suites compile only on macOS).
- Integration jobs need network access, the `ably-common` submodule and the proxy binary.

### 2.6 Understand the SDK's concurrency model (MUST)

Most flakiness in both existing SDKs came from concurrency, not from translation. Before writing the skill, know:

- Which thread or queue SDK callbacks fire on, and whether listeners can run concurrently with the test body.
- How to drain the SDK's internal work queue (this becomes `process_pending_events()`). One zero-delay yield (e.g. one `await asyncio.sleep(0)`) may not drain chained callbacks; loop until the queue is empty if you can observe it (`writing-derived-tests.md` "No real timers in unit tests"). One yield is usually enough for a single JavaScript macrotask queue (unless the SDK re-queues work from within a callback), but not where the SDK chains work across queues, threads or loop iterations (both existing SDKs needed explicit queue drains). Use one yield only where you have shown it drains everything.
- Whether the test runner virtualises time (kotlinx `runTest` does; this breaks real-network timeouts), and, for async runners, the plugin mode and event-loop scope that suite-level fixtures need (e.g. pytest-asyncio).
- **Whether the runner runs tests in parallel** (xUnit does by default; pytest-xdist and NUnit `[Parallelizable]` when enabled; Swift Testing unless `.serialized`). If any injected mock, fake clock or log sink is process-global, serialise the UTS suites or make the hooks per-client, and say which in the skill. ably-cocoa marks its core realtime/rest and integration suites `@Suite(.serialized)`; its objects unit suites, which inject nothing process-global, are plain parallel `struct`s.
- Whether the language enforces concurrency safety at compile time (Swift 6 `Sendable` drove ably-cocoa's capture types).
- Where white-box unit specs can see internals (Swift `@testable import`, Objective-C private headers, C# `InternalsVisibleTo`, Kotlin `internal` within the owning module). This decides **where tests live**.

### 2.7 Harness smoke tests and self-tests (MUST)

The harness has two kinds of test of its own, both permanent and both required:

- **Per-tier smoke tests:** end-to-end wiring of one tier through the real SDK hooks (unit with mocks and the fake clock; direct sandbox; proxy).
- **Helper self-tests:** contract tests that each harness helper obeys its helper spec, or this guide's rule for it.

**Why both.** Spec-derived tests can't be the harness's acceptance gate. They are regenerated, they may legitimately be red (a UTS spec error), and a failing one has to be triaged as SDK, spec or harness. A smoke-test or self-test failure is unambiguously a harness or environment fault. Scenario-only smoke tests aren't enough: they follow a happy path, so a helper that breaks its contract (a mock `close()` that notifies synchronously, a declared mock event that is never emitted, a state wait that samples) still passes, and the defect surfaces later as a flaky spec-derived test. Both existing SDKs hit this (as of 2026-10-07). One had connect-only smoke tests, env-gated and never run in CI, then removed them; its sampling state wait, error-swallowing polls and teardown hangs were later found only through flaky spec-derived tests. The other's scenario smoke tests, run in CI, caught a fake clock that waited on the real clock, but not its synchronous mock `close()` or a mock event type it declares and never emits.

**Rules (MUST):**

- **Permanent.** Don't retire them when spec-derived tests cover a tier.
- **In CI, ungated.** They run, ungated, in whichever CI job runs their tier ([2.5](#25-build-and-ci-wiring-must)); no environment variable may skip them (compile-time platform gating per 2.4 aside).
- **Untagged and structural.** No `UTS:` tag; each is named after the capability it proves; each passes on its own under the single-class filter.
- **Never copied.** The skill never copies their shape and never names them as reference tests. Its Harness reference ([3.4](#34-recommended-outlines-should)) may cite a smoke test as a wiring example only (client construction, suite fixtures, teardown).
- **Separate.** They live with the harness (layout in 2.2), outside every directory the mapping gives the resolver as a target, so generated tests can't collide with or overwrite them.
- **Selectable.** One complete command per tier runs that tier's smoke tests and self-tests (plus the common self-tests). The mapping declares it ([3.2](#32-the-mapping-file)), and the skill's preflight runs it ([4](#4-the-workflow-the-skill-must-implement), step F).
- **Explicit.** Each item below is an explicit assertion. One scenario test may cover several items; an item covered only implicitly doesn't count. Every event type the harness declares is emitted and asserted (or the type is removed). A helper-spec contract point the harness doesn't meet is listed in the harness README's Known gaps ([3.1](#31-layout)), not left untested.

**Minimum set per tier** (a tier the skill doesn't support needs none of its entries):

**Common (every tier)**

- Self-tests:
  - `assertContainsInOrder` has subsequence semantics (interleaving passes, a repeated state passes, wrong order fails)
  - `poll_until` returns the settled value and aborts on an error
  - `poll_until_success` rethrows the last error on timeout
  - The wall-clock timeout wrapper bounds a wait, including under a virtual-time runner
  - Capture lists are safe under concurrent appends
  - A failing helper reports the caller's line
  - Every state-wait helper (unit and integration) latches a state entered and left within one scheduling tick and fails fast on FAILED
  - Teardown closes clients and cancels timers when the body throws, and, from a state where the SDK's `close()` can't reach CLOSED ([5.4](#54-setup-and-teardown)), doesn't wait for CLOSED

**Unit, realtime (mock WebSocket and fake clock)**

- Smoke test:
  - A factory-built client with the mock installed reaches CONNECTED via `respond_with_success` and `CONNECTED_MESSAGE`, and a template field (e.g. the connection id) reaches the client
  - The connection attempt exposes host, port, TLS and query params
  - A client→server frame (ATTACH, with a non-ASCII channel name) is captured and decoded
  - A server→client frame (ATTACHED) changes state
  - `simulate_disconnect` yields DISCONNECTED, observed by record-and-verify
  - A timer-driven retry doesn't happen before `ADVANCE_TIME` and does after it
  - The await style drives refused attempts through to SUSPENDED
- Self-tests:
  - Mock `close()` calls `onClose` asynchronously
  - CONNECTED is delivered after the connection completes
  - A raw untyped frame can be sent
  - WS-level timeout and DNS-error outcomes exist
  - Handler and await styles both work, and the documented mixing rule holds
  - Every declared mock event type is emitted, in order
  - `process_pending_events()` runs a queued callback with no real delay

**Unit, fake clock**

- Smoke test: (driven by the realtime smoke test)
- Self-tests:
  - One `ADVANCE_TIME` runs cascaded work to quiescence (zero-delay reschedules, timers created mid-advance)
  - The fake clock never waits on the real clock (the SDK's timed blocking waits and the async runtime's timers follow it)
  - A poll deadline still expires with the fake clock installed

**Unit, REST (mock HTTP)**

- Smoke test:
  - A request is captured with method, path, headers and body
  - `respond_with` status, body and headers are decoded by the SDK
  - A realtime-driven HTTP request (e.g. token auth via `authUrl`) is served by the HTTP mock while the WS mock serves the connection
- Self-tests:
  - Connection-level and request-level failures are distinguishable
  - Handler and await styles both work

**Unit, optional mocks**

- Smoke test:
  - `MockNetworkListener` (if the SDK has a network monitor) and `MockVCDiff*` (if it supports deltas) each drive the SDK once

**Unit, objects (each module with a fixture helper)**

- Smoke test:
  - `setup_synced_channel` (or its sanctioned stand-in) completes and one pool object reads its seeded value
- Self-tests:
  - Serial helpers sort as the helper spec requires

**Direct sandbox**

- Smoke test:
  - An app is provisioned once per suite (or per test where 5.4 allows it, disclosed) and deleted in teardown, and its keys look right
  - A client connects to the sandbox (the recorded state sequence ends CONNECTED)
  - Attach, subscribe and ack-awaited publish on a unique channel, with messages received in order
  - A REST read (history) returns them via `poll_until`
  - It runs once per protocol variant
  - Every wait is wall-clock and bounded
- Self-tests:
  - `SandboxApp` creates and deletes an app, and never retries `POST /apps`

**Proxy**

- Smoke test:
  - The pinned proxy (or the local override) is fetched, verified, started and healthy
  - A pass-through session connects a client with the chosen proxy auth
  - The typed log shows `ws_connect` and a server→client CONNECTED frame
  - `trigger_action(disconnect)` is followed by a recorded DISCONNECTED, then recovery
  - A frame-match rule with a string `match.action` (e.g. `"11"`) fires once, then the client recovers
  - Sessions and clients close in teardown, even on failure
- Self-tests:
  - Rule builders stringify `match.action`
  - A session with `rules:` only defaults its endpoint to the sandbox ([6.7](#67-notes-on-the-catalogue))

---

## 3. Skill anatomy

### 3.1 Layout

```
<skill-dir>/                         # .claude/skills/uts-to-<lang>/ (linked from .agents/skills/uts-to-<lang>/)
├── SKILL.md                         # the procedure
├── uts-package-mapping.json         # spec module → target dir/package per tier, + notes pointer
├── scripts/
│   ├── resolve_uts.py               # deterministic selection
│   ├── audit_translation.py         # deterministic faithfulness audit
│   └── scan_constructs.py           # corpus construct scanner (SHOULD, section 6)
└── references/
    └── <module>-mapping.md          # module notes (e.g. objects-mapping.md)
```

| File | Purpose | Level |
|---|---|---|
| `SKILL.md` | The two-phase procedure, construct table, a file template per tier, evaluation patterns, tier wiring. Keep it **module-generic**: the core realtime/rest mapping may live here; plugin or typed-module specifics go in notes | MUST |
| `uts-package-mapping.json` | Maps each source module (`rest`, `realtime`, `objects`) and tier (`unit`, `integration`, `proxy`) to one target directory, plus an optional `notes` path; declares the harness (root, README, per-tier sources and harness-test command) | MUST |
| `scripts/resolve_uts.py` | Validates the module dir, reads the mapping, lists specs and derives file/class/package names; prints one JSON object | MUST |
| `scripts/audit_translation.py` | Compares one spec file with its generated test file; prints one JSON object | MUST |
| `scripts/scan_constructs.py` | Lists the uppercase keywords and snake_case calls in a module's `pseudo` fences, so unmapped constructs are found mechanically ([section 6](#6-pseudocode-construct-catalogue)) | SHOULD |
| `references/<module>-mapping.md` | Maps ably-js-shaped pseudocode to your SDK's API for one module; may override parts of the generic flow | MUST wherever the SDK surface diverges from the pseudocode (in practice `objects` for every typed SDK) |

Both existing skills use Python for scripts. Any language works, but the scripts must run on every developer platform (see [8.1](#81-resolver-resolve_utspy-must) and [section 10](#10-verification-and-ci)).

**Install for both Claude Code and Codex (SHOULD).** Claude Code loads project skills from `.claude/skills/`; Codex loads them from `.agents/skills/`. Keep one copy and link the other location to it, so both tools load the same files:

```sh
mkdir -p .agents/skills
ln -s ../../.claude/skills/uts-to-<lang> .agents/skills/uts-to-<lang>
git add .agents/skills/uts-to-<lang>
```

Both tools follow directory symlinks. On Windows, Git needs `core.symlinks=true` (and Developer Mode); if that isn't available to your contributors, commit a copy instead, and add a CI check that the two directories are identical. Everything in the skill refers to its own files relative to the skill directory ([3.3](#33-frontmatter-and-arguments)), so either location works. Users invoke it as `/uts-to-<lang> <module-dir>` in Claude Code and `$uts-to-<lang> <module-dir>` in Codex.

Keep two documents with separate roles: the test library's README describes **what exists** (helpers, seams, layout); `SKILL.md` describes **how to author** tests. Refer to the README by its full repo path, so it can't be confused with the spec repo's `uts/README.md`. The harness README MUST include a **Known gaps** section: every helper-spec member or contract point, and every corpus construct, that the harness doesn't implement, by tier, in a form the skill's preflight can match against the selected specs (construct or helper name → status and workaround). Write it as a table whose first column is the exact pseudocode token as it appears in `pseudo` fences (for example `respond_with_timeout`, `PING_MESSAGE`, `AWAIT_ALL`), so the preflight matches mechanically: for each row, grep the selected specs' `pseudo` fences for the token; any hit is a conflict. The corpus scanner (section 6) MAY accept spec files as well as a module directory for this. It SHOULD also cover: the SDK hooks used, each helper-spec symbol → harness symbol, the wait helpers and their default timeouts, the threading and time model, how to run each tier and its smoke tests and self-tests (2.7), and one index of every module's fixture helpers (even those in a separate test-support module).

**The notes are a map, not an authority.** Where the notes, the spec's IDL and the SDK disagree about the SDK's API, the SDK source is the ground truth: fix the notes.

### 3.2 The mapping file

Each tier value is **one path**, relative to the repo or to a declared root (Swift's `testRoot`), never machine-absolute. Derive everything else (namespace, package, build target) from it in the resolver, never by hand.

```json
{
  "_comment": "Maps each UTS module to its target test dir per tier. Used by scripts/resolve_uts.py.",
  "harness": {
    "root": "<harness>",
    "readme": "<harness>/README.md",
    "tiers": {
      "unit":        { "sources": ["<harness>/common", "<harness>/unit"], "tests": "<command: unit smoke tests and self-tests>" },
      "integration": { "sources": ["<harness>/common", "<harness>/integration"], "tests": "<command>" },
      "proxy":       { "sources": ["<harness>/common", "<harness>/integration", "<harness>/proxy"], "tests": "<command>" }
    }
  },
  "packages": {
    "realtime": { "unit": "<path>/unit/realtime", "integration": "<path>/integration/standard/realtime", "proxy": "<path>/integration/proxy/realtime" },
    "objects":  { "unit": "...", "integration": "...", "proxy": "...", "notes": "references/objects-mapping.md" }
  }
}
```

- **Make every derived namespace unique**: keep a module segment after the tier (`unit/realtime`, never bare `unit`), or use a module-specific prefix (ably-java's objects tests use `io.ably.lib.liveobjects.uts.unit`).
- **`notes`** is relative to the skill directory, not the repo root.
- **`harness`** (MUST): the harness root and README, and per tier the helper sources to read and the complete command, run from the repo root, that runs that tier's smoke tests and self-tests (e.g. `dotnet test tests/Uts --filter "Category=UtsHarness.Unit|Category=UtsHarness.Common"`, `pytest test/uts/harness/tests/common test/uts/harness/tests/unit`) ([2.7](#27-harness-smoke-tests-and-self-tests-must)). Paths are repo-relative. The resolver reports it, with paths validated (still repo-relative) ([8.1](#81-resolver-resolve_utspy-must)), so `SKILL.md` never hard-codes harness paths.
- **Language-specific derivations live in the resolver.** Swift has no package, so the directory is the full story. Kotlin derives `package` from the path after `src/test/kotlin/` and the Gradle module from the first segment. A C# resolver might map `tests/IO.Ably.Tests.Uts/Unit/Realtime` to namespace `IO.Ably.Tests.Uts.Unit.Realtime` (PascalCase segments) and to the nearest ancestor `.csproj`; a Python resolver derives a dotted package path.
- **Hand-maintained entries.** `--create` scaffolds only the repo's default layout. A module whose tests live elsewhere (ably-java's `objects`, in `:liveobjects`) is hand-maintained: the skill MUST say which entries are, and must not offer `--create` to "fix" them.
- You MAY store per-module defaults as data, e.g. `"evaluate": true` or a list of white-box specs, instead of prose in the notes.

### 3.3 Frontmatter and arguments

Write the skill so the same directory loads in Claude Code and in OpenAI Codex. Both implement the open [Agent Skills](https://agentskills.io/specification) format. Put only the portable fields in `SKILL.md`:

```yaml
---
name: uts-to-<lang>
description: "Translates Ably UTS (Universal Test Suite) pseudocode specs into runnable LANG tests in REPO. Use when asked to translate, port, derive, generate or re-sync tests from a UTS spec or module (uts/rest, uts/realtime, uts/objects), to evaluate UTS-derived tests against the SDK, or to check UTS coverage. Takes a UTS module directory, validates it, resolves the target test directories, asks for a tier (unit, integration, proxy) and specs, then derives one LANG test per spec Test ID. Not for creating the skill or its harness (use uts-to-lang-skill-creator), or for writing UTS specs."
license: "<the repo's licence>"
compatibility: "Claude Code or Codex. Needs git, python3 and a local clone of ably/specification; run on an Opus-class model."
allowed-tools: Bash Read Edit Write
metadata:
  version: "1.0.0"
  short-description: "Translate UTS specs into LANG tests"
---
```

- **`name`** MUST be `uts-to-<lang>`, equal to the skill's directory name: lowercase letters, digits and hyphens, at most 64 characters. (`uts-to-kotlin` omits `name` and relies on the directory name; both tools accept that, but the Agent Skills format requires the field.)
- **`description`** MUST be at most 1,024 characters and contain no `<` or `>`. Write `LANG` and `REPO`, not `<lang>`: skill packaging validators (for example skill-creator's `quick_validate.py`) reject angle brackets, and Anthropic's skill-authoring best practices also say no XML tags in descriptions. It SHOULD be "pushy" and written in the third person: front-load the trigger phrases a user might type ("translate this UTS spec", "port uts/objects to LANG", "re-sync UTS tests") and end with a "Not for …" boundary. Put the usage line in the body, not in the description. Both existing skills' descriptions are procedural, which suits explicit invocation but triggers poorly otherwise.
- **`metadata`** values MUST be strings (quote `"1.0.0"` and `"false"`). Codex shows `metadata.short-description` in its skill list.
- **`allowed-tools`** is space-separated. Claude Code pre-approves the listed tools while the skill runs; Codex ignores the field. Both existing skills declare `Bash, Read, Edit, Write, WebFetch` and search with `grep` through `Bash`. Add `Grep`/`Glob` only if your workflow uses those tools, and `WebFetch` only if the skill fetches anything remotely (see [9.4](#94-local-clone-vs-fetching-main)).
- **Claude Code-only fields** (`argument-hint`, `model`, `disable-model-invocation`, `when_to_use`, `context`, …) MAY be added only if the team accepts that they aren't portable: Codex ignores them, and they make claude.ai upload and standard packaging fail. Put Codex-only settings (display name, implicit-invocation policy) in an optional `agents/openai.yaml` in the skill directory.
- **Argument:** a single UTS **module** directory, directly under `uts/`. Both skills started with single-spec-file input and moved to modules; spec selection happens interactively. Don't depend on argument substitution (`$ARGUMENTS` works only in Claude Code): say in words where the argument comes from ("the module directory given after `/uts-to-LANG` in Claude Code or `$uts-to-LANG` in Codex, or named in the user's message"). If there is none, the skill MUST print the usage line and stop.
- **Paths to the skill's own files** MUST be relative to the skill directory (the directory containing `SKILL.md`), for example "run `scripts/resolve_uts.py` from this skill's directory". Never write `.claude/skills/uts-to-<lang>/scripts/…`: Codex loads the skill from `.agents/skills/`, and `${CLAUDE_SKILL_DIR}` is Claude Code-only. The scripts follow the same rule: they locate the mapping file and the notes relative to their own file (for example `Path(__file__).parent.parent`), never relative to the working directory.
- **Model (SHOULD):** no portable frontmatter field pins a model. State in the opening lines of `SKILL.md` (and in `compatibility`) that the skill should run on an Opus-class model ([Model tier](#model-tier)). Claude Code's `model` field is a non-portable option (see above). Either way, the skill records the model in its final report ([section 11](#11-final-report-format)).
- **Placeholders, not personal paths,** in examples and usage text: `<cloned-ably-specification-repo-path>/uts/objects` in the body (angle brackets are fine in the body, but not in `description`).

### 3.4 Recommended outlines (SHOULD)

The outlines are SHOULD; the Harness reference section within the `SKILL.md` outline is MUST (below). Use these shapes (both existing skills converged on them independently of language):

```
SKILL.md
  Required reading (local clone, 9.4)
  Harness reference: per tier, from the resolver's harness output: harness root and README path,
      helper sources to read, smoke-test and self-test locations and run commands, the
      generated-test run command, the README's Known gaps
  Phase 1, selection: usage guard; step 0; A resolve; B mapping; C tier; D specs;
      E translate vs evaluate; F harness preflight
  Phase 2, per spec: 1 read spec + notes; 2 output path; 3 read harness + reference test;
      4 generate (construct table, client construction, mocks, timers, assertions, naming,
        file template per tier); 5 compile; 6 run + diagnose (evaluate only); 7 audit + review
  Integration tiers: direct-sandbox wiring; proxy wiring (session, connect through proxy, auth,
      rule builders, event log); file templates
  Final report (section 11)
```

`SKILL.md` MUST have the **Harness reference** section. It points at the harness sources, README and harness tests; it doesn't copy helper signatures inline (inlined copies drift). A construct that relies on a listed known gap is a stop-and-ask or a Mock Infrastructure Limitation, never a substitution (5.2). A smoke test may be named as a wiring example only, never as a reference test (2.7).

A module notes file should cover:

1. **Source of truth and runtime status:** the spec's IDL that the notes apply, including any typed-SDK variant (for objects, the proposed `RTTS` points (RTTS1–RTTS11 at the branch tip, `c5cc6b8a`) that both existing skills' notes follow; as of `12540dcf` they are on the unmerged `feature/liveobjects-cross-sdk-types-spec` branch, not in `objects-features.md`), and whether the module is implemented (whether evaluate mode is possible).
2. **Layers:** spec names that denote several things (e.g. `LiveMap` as a creation value type, a public view and an internal node).
3. **Entry point and setup:** plugin registration, channel modes.
4. **Async model:** how `AWAIT`, deferred futures and errors render.
5. **Type mapping:** polymorphic spec objects → typed views (which conversions throw and which degrade to null); write values → union/wrapper types; enums and string tags → constants; numeric types.
6. **Mutations, subscriptions and events.**
7. **Messages and errors:** codes, nested `error.cause`, timestamp units.
8. **Internal access:** the ladder ([5.9](#59-internal-access-white-box-unit-specs)), the list of white-box specs, the placement boundary.
9. **Helper-spec coverage table:** every helper-spec symbol → native file and symbol, with each fixture helper's scope (2.2), sanctioned shape differences ("use the pattern; don't add the shorthand") and sanctioned stand-ins ([7.2](#72-harness-stand-ins-are-not-deviations)).
10. **Overrides of the generic flow:** reading list, naming, deviations location, expected audit shortfalls.
11. **Integration helpers.**
12. **A worked example** naming each mechanical rewrite, and a **symbol index**.
13. **Shape-deviation vocabulary** (`S-1…S-n`), if any.

A generated test file:

```
header: "Derived from uts/<path> at ably/specification@<full-sha>" (plus "(locally modified; blob <hash>)"
        when 9.1 applies), tier, disclosures
        (harness stand-ins, deviations); integration/proxy: the corresponding unit spec
imports; suite/class (serialised if hooks are process-global)
per test: UTS: <id> tag → test attribute → name with spec point →
          // Setup … // Test Steps … // Assertions … (spec comments verbatim) → teardown via scope/hook
file-local helpers: before the first test or in a separate file (the audit attributes anything
        after the last tag to the last test; see the audit contract, 8.2)
```

---

## 4. The workflow the skill must implement

The workflow has two phases. Implement both. Runs SHOULD use an Opus-class model ([Model tier](#model-tier)); the final report records the model used ([section 11](#11-final-report-format)).

### Phase 1: selection (steps 0 and A–F)

| Step | What happens | Interaction |
|---|---|---|
| **0. Required reading** | Read `writing-derived-tests.md` and the "Pseudocode Conventions" section of `uts/README.md` once per run (plus `proxy.md` for the proxy tier; in evaluate mode, the features specs as needed), from the same spec clone as the module ([9.4](#94-local-clone-vs-fetching-main)). Read `writing-test-specs.md` whenever the construct table defers a meaning to it. Don't rely on memory or inlined summaries | — |
| **A. Resolve the module** | Run `resolve_uts.py "<module-dir>"`. If `ok` is false, relay `message` and stop. Treat the output as the **single source of truth**: never recompute a path or name by hand | Stop on error |
| **B. Confirm or create the mapping** | If mapped, show each tier's target dir verbatim and ask the user to confirm. If unmapped, ask for the target base name (default: the source module name; suggest a rename only when the SDK uses different terminology) and run `resolve_uts.py --create <name>`. If the user says an entry is wrong, re-run `--create <name>` to overwrite it (keeping its `notes`), unless it is hand-maintained (3.2), in which case edit it by hand | **Ask** |
| **C. Choose the tier** | Offer only tiers that are present. Where the mapping records a tier as not ready (per-module data, 3.2), refuse it and name what blocks it. The tier fixes the target dir, the spec list **and** the translation flow (mocked / sandbox / proxy). Don't re-detect it per spec | **Ask** |
| **D. Choose specs** | All specs in the tier, or a subset | **Ask** |
| **E. Translate-only, or translate and evaluate?** | Translate-only: generate, compile, and run the step 7 audit and review, but don't run the tests (the SDK feature may not exist yet). Translate and evaluate: also run and diagnose. If unsure whether the implementation exists, ask rather than guess | **Ask** |
| **F. Harness preflight** | Before generating anything, for the chosen tier and specs, in both modes: compile (or collect) the harness and the test target; run the tier's smoke tests and self-tests with the resolver's `harness` command ([2.7](#27-harness-smoke-tests-and-self-tests-must)); check the harness README's Known gaps against the selected specs. Integration and proxy tiers need network (and the proxy binary or platform) for this. If anything is red, **stop** and report it as a harness or environment problem, never as an SDK deviation or a spec error; don't generate tests on a red harness. If a selected spec needs a known gap, stop and ask: extend the harness (a harness change, section 5), deselect the spec, or proceed recording a Mock Infrastructure Limitation for the affected lines. Never substitute. Record the result in the final report | Stop on red |

If the module's notes file exists but is only a placeholder, the skill MUST tell the user the module's mapping hasn't been authored and treat the module as not yet translatable, rather than guess a mapping.

### Phase 2: per spec (steps 1–7)

**Batching (SHOULD):** run steps 1–4 for every selected spec, then step 5 once for the module, then steps 6–7 per file.

1. **Read the spec and the notes.** Read the module notes first (once per run); where they override the generic flow (reading list, internal-access ladder, naming, deviations location), the notes win. Then identify per spec: test cases and IDs, protocol (WS or HTTP), timer use, `## Protocol Variants`, and any delegating, fixture-driven or ID-less structure.
2. **Determine the output path.** Use the resolver's `targetDir` and class name. Flatten spec sub-directories. If a suitable suite already exists, add to it rather than create a duplicate.
3. **Read the harness for exact signatures.** Read the harness README, then **all** helper sources for the tier (both from the resolver's `harness` output), before generating code. The source wins where the README disagrees; list each disagreement in the final report. Guessed signatures are the most common compile failure. `SKILL.md` SHOULD also name one reviewed, spec-derived test file per tier to read first (ably-cocoa: `ChannelHistoryTests.swift` for direct sandbox, `AuthReauthTests.swift` for proxy; ably-java names `ChannelHistoryTest` (realtime) and `ObjectsLifecycleTest` (objects), both direct sandbox, and no proxy reference). Never name a smoke test as the reference test.
4. **Generate** using the rules in [section 5](#5-translation-rules) and the table in [section 6](#6-pseudocode-construct-catalogue). A construct the skill can't map is a **stop-and-ask** condition (section 6).
5. **Compile once per module.** Fix and recompile until clean.
6. **Run (evaluate mode only).** Run each class by filter, then diagnose per [section 7](#7-evaluation-and-deviations).
7. **Scripted review (both modes).** Run `audit_translation.py <spec> <test-file>` using the resolver's paths, then walk the review checklist ([8.3](#83-review-checklist-must-after-the-audit)). Any fix means re-audit, recompile and, in evaluate mode, re-run.

---

## 5. Translation rules

Every rule below is a MUST unless marked otherwise.

**When a generated test is wrong, fix the cause, then regenerate.** The cause is a rule in `SKILL.md`, a mapping in the module notes, or a harness helper. A fix made only in the generated file is silently reverted by the next regeneration. The only per-test state that survives regeneration is listed in [9.2](#92-a-re-sync-mode-should).

**Changing the harness during a run** (extending a mock, adding a message template or a helper), by the skill or the user, is a harness change, not a translation step. Make it only within the harness scope the user approved. Add or extend a self-test for the new capability, update the harness README (and its Known gaps), and re-run the tier's smoke tests and self-tests ([2.7](#27-harness-smoke-tests-and-self-tests-must)) before continuing; stop if they are red. Then regenerate the affected tests (fix the cause, then regenerate). The final report lists harness changes separately (section 11).

### 5.1 Traceability

- **Exactly one `UTS:` tag per test**, equal to the spec's `**Test ID**`, copied **verbatim**: `// UTS: <id>` immediately above the test function (`writing-test-specs.md` "Placement in derived tests"). Where `//` isn't a comment, use the line-comment marker (`# UTS: <id>` in Python or Ruby); cross-SDK tooling should grep for `UTS: <id>` without the marker. Never hand-build the prefix: proxy files use `<module>/proxy/…` IDs although they live under `integration/proxy/`, and objects IDs can join spec points (`objects/unit/RTO5c9-RTO20/…`).
  - *Divergence:* `uts-to-kotlin` uses a KDoc `/** @UTS <id> */` marker. It works inside ably-java, but a cross-SDK grep for `UTS: <id>` misses it. New skills should use the documented form.
- **Never invent a tag.** When one test covers several spec points (e.g. `## Test 26: RTN22/RTC8a -- Server-initiated re-authentication` in `realtime/integration/proxy/auth_reauth.md`), put the extra points in the test name, not in a second tag. Invented tags show up as audit orphans.
- **Test names include the spec point** (`writing-derived-tests.md` Phase 1), as a valid identifier the runner collects:
  - Swift `test_RTN16g_<description>`; Kotlin backtick names `` `RTN16g - <description>` ``;
  - C# `RTN16g_<Description>`, optionally with a `DisplayName`;
  - pytest: file `test_<stem>.py`, class `Test<Stem>`, function `test_rtn16g_<description>` (default collection requires these prefixes);
  - a module's notes may change how the name is rendered, but the name always includes the spec point (`writing-derived-tests.md` Phase 1 says it *must*). Bare descriptive names that rely on the tag alone are a pattern to avoid.
- **A standard file header** naming the source spec path, its tier, the spec-repo commit translated from ([9.1](#91-record-what-you-translated-from-must)), and any disclosures (harness stand-ins, deviations). Integration and proxy headers also name the corresponding unit spec where the spec gives one (`proxy.md` convention 1). See the file outline in [3.4](#34-recommended-outlines-should).
- **Keep the spec's test order** and its section headings as comments (`Setup`, `Test Steps`, `Assertions`, `Test Steps and Assertions`, `Teardown`/`Cleanup`).

### 5.2 Fidelity

- **Copy every pseudocode comment verbatim** to the matching step. Don't paraphrase.
- **Keep spec variable names**, adapted to the language's case convention. Name new variables concretely (`attachFrames`, not `fields` or `result2`).
- **Every `ASSERT` and `AWAIT` is either translated at the same place or annotated, never dropped.** If one has no equivalent in the language or SDK, keep the spec line as a comment and add a note explaining why no assertion is emitted. An unannotated drop is a bug.
- **Wait conditions and timeouts must match the spec.** A `poll_until(auth_callback_count > n)` rendered as a poll on a different predicate is a silent semantic change. Any deliberate difference carries a `// NOTE:` (ambiguity, `writing-derived-tests.md` "Flag ambiguity") or `// DEVIATION:` comment.
- **Never substitute a similar mock outcome for one the harness lacks.** If a spec uses a capability the harness doesn't have (e.g. a WS-level `respond_with_timeout()`), extend the mock (preferred, usually small) or record a Mock Infrastructure Limitation. Don't silently use `respond_with_refused()` instead. A designed-in stand-in ([7.2](#72-harness-stand-ins-are-not-deviations)) is not a limitation.
- **Set only the options the spec sets.** The client factory may pre-seed a dummy key; set `key` only when the spec does. Force the protocol format the mocks understand (`writing-derived-tests.md` "Required options vary by SDK").
- **Helpers return ready-to-assert values** (typed, non-optional unless the spec expects absence), so test bodies stay free of casts and parsing. Helpers used by one suite live before its first test or in a sibling file (8.2: anything after the last tag is attributed to the last test); helpers shared across a module's suites live in the module helpers.
- **Use SDK API values, not wire values**, when asserting on decoded objects, and convert units where the SDK's API differs from the wire (e.g. ms on the wire, seconds in the API).
- **Translate spec-local functions** (e.g. `function token_auth_callback(api_key)` in `rest/integration/proxy/rest_fallback.md`) as file-local helpers.

### 5.3 Structural variants

| Spec shape | Rule |
|---|---|
| **One ID, several H3 sub-cases** (e.g. `realtime/unit/client/realtime_client.md`, `### RTC1a_1`, `### RTC1a_2`) | One test carrying the one tag; translate every sub-case inside it, in order, or as a parameterised test that keeps the single tag |
| **Group heading with no ID, H3 tests with their own IDs** (e.g. `rest/unit/auth/revoke_tokens.md`) | The H2 is a grouper only. One test per H3 ID. MAY mirror the group as a comment or nested suite |
| **`### Test Cases` table driving `FOR EACH test_case`** | `test_cases` is the table. Render as a table-driven or parameterised test under the one tag. Rows that are language-inapplicable are omitted with a comment ([7.4](#74-language-inapplicable-inputs)) |
| **Delegating test or spec**: a whole file (`realtime/unit/channels/channel_get_message.md`) or a single test inside a mixed spec (RTAN3a in `channel_annotations.md`, a section with no Test ID; RTL10a in `channel_history.md`) that says "the tests in `uts/rest/unit/…` should be used to verify … on a `RealtimeChannel`" | The skill MUST define one policy and apply it everywhere. Recommended: one test with the delegating tag (where the section has no Test ID, as RTAN3a, follow the no-Test-ID row: no invented ID, a `// NOTE:` naming the heading) that runs the referenced REST cases against the realtime client through a shared helper. If that isn't feasible yet, mark the test pending (not commented out) with a `// NOTE:`. **This is new policy proposed by this guide**: the UTS docs don't yet cover delegation, and neither existing skill has implemented it |
| **Tests with no Test ID** (`rest/unit/encoding/msgpack_interop.md`) | Translate them; don't invent an ID. Add a `// NOTE:` naming the source heading, and review by hand (the audit can't verify them). *Divergence:* `uts-to-swift` expects a `// UTS:` tag here, which the audit then reports as an orphan |
| **`## Protocol Variants` section (body `json, msgpack`)** | Parameterise over the protocol (`useBinaryProtocol: PROTOCOL == "msgpack"`). The tag and the name stay singular. Specs without the section are JSON only. Proxy tests are always JSON |
| **Spec filed under another module's tree** (e.g. REST faults in `realtime/integration/proxy/rest_faults.md`) | Translate it with the module directory it sits in; the mapping decides the target, not the spec's subject |
| **Inline SDK hints in spec prose** (Dart, ably-js or ably-java names) | Hints for interpretation, not prescriptions. Don't copy them |

### 5.4 Setup and teardown

- **Close every client even when the test fails.** `CLOSE_CLIENT(client)` (added to the specs so internal timers stop) must land in `finally`, a teardown hook, or a scoped-resource helper, not only at the end of the body.
- **Restore mocks and cancel SDK timers in teardown**, not at the end of the test (`writing-derived-tests.md` "Cleanup with afterEach").
- **Never hand-roll teardown** where the harness provides a scope. ably-cocoa uses `with…` scopes because Swift Testing has no async teardown.
- `BEFORE ALL TESTS` / `AFTER ALL TESTS` sandbox provisioning maps to suite-level fixtures where the runner supports them (ably-java `@BeforeAll` with `@TestInstance(PER_CLASS)`; xUnit `IClassFixture`/`IAsyncLifetime`; NUnit `[OneTimeSetUp]`; pytest class- or module-scoped fixtures). Provision once per run wherever the runner supports suite-level fixtures. If it doesn't, per-test provisioning is an acceptable harness adaptation; say so in a comment (ably-cocoa does this). *Divergence from `writing-test-specs.md`* ("Sandbox App Management": create apps once per test run): per-test provisioning is slower and creates more apps, but it doesn't change what the test asserts, so it is allowed only as a harness stand-in disclosed in the file header ([7.2](#72-harness-stand-ins-are-not-deviations)).
- **Stop on a failed wait.** If a wait times out, record the failure and stop driving the client in the wrong state; teardown must still run.
- Close only from states where your SDK's `close()` can reach CLOSED; don't await CLOSED from the others (in ably-cocoa: FAILED and INITIALIZED).

### 5.5 Integration-tier hygiene

- **Unique channel names** in every integration test: a descriptive part plus a random part (`writing-test-specs.md` "Unique Channel Names").
- **Each test creates and closes its own proxy session.**
- **No fixed sleeps.** A spec `WAIT` at integration tier is wall-clock; keep it only when the spec has it, with a comment.

### 5.6 Time and waiting

- **Unit tier: no real timers** (`writing-derived-tests.md` "No real timers in unit tests"). Use the fake clock for time-dependent behaviour and `process_pending_events()` (a zero-delay yield or internal-queue drain) for async delivery. The only allowed real timer is a safety timeout.
- **Integration and proxy tiers: every timeout is wall-clock** (`writing-derived-tests.md` "Integration timeouts are wall-clock"). In virtual-time runners (kotlinx `runTest`), wrap every real-network wait, including bare future awaits, in a real-clock helper (ably-java `withRealTimeout`).
- **Poll deadlines must not freeze under fake time**: preferably restructure the test so the wall clock needn't be stubbed; otherwise read a monotonic clock (`writing-derived-tests.md` "No real timers in unit tests").
- **Every wait is bounded.** Use the spec's timeout where it states one. Otherwise, per `integration-testing.md` "Timeout Strategy": pass an explicit timeout on every integration `poll_until` call (10–30 s), and let state waits use helper defaults of 10–15 s. (`poll_until`'s reference interval is 500 ms and its default timeout 10 s; ably-cocoa's integration helpers default to 15 s.)
- **Prefer state waits.** Map `AWAIT_STATE` to the state-wait helper; use a generic condition poll only when no state applies or the spec itself polls.
- **Keep the spec's `LOOP up to N times: ADVANCE_TIME … BREAK`** as a loop; don't compute exact jumps.
- **Advance fake time, then flush** the async runtime before asserting.

### 5.7 Waits must catch events

- **`AWAIT_STATE` must be event-latched and race-free**: subscribe first, then check the current state, and complete exactly once (whichever of the listener and the immediate check wins), as `writing-test-specs.md` "State Transitions" requires. Checking before subscribing leaves a window in which the transition is missed. ably-java's `awaitState` does this, with an atomic single-winner resume. The helper also removes its listener on success, timeout and cancellation; leaked listeners keep firing into later tests.
- **A state wait fails fast on FAILED.** If the connection enters FAILED while waiting for another state, fail immediately with the error reason instead of running out the timeout (ably-cocoa's integration `awaitState`). Don't treat a state that is already FAILED at the start of the wait as a failure when the test has just requested a transition out of it (`connect()`, or `authorize()` from FAILED per RTC8c); latch the next transition instead.
- **Transient states use record-and-verify** (`writing-test-specs.md` "Verifying Transient States"): record all state changes, let the cycle finish, then assert `CONTAINS_IN_ORDER`. Even a correct latch misses a state entered and left before the call. Don't insert an intermediate `AWAIT_STATE disconnected`.
- **Polls return the settled value.** For a value-assigned `x = poll_until(…)`, the helper returns the value and later assertions use it. Don't re-read afterwards: an eventually-consistent store can return fewer items on the second read.
- **`poll_until` aborts on an error; `poll_until_success` keeps polling and rethrows the last error on timeout.** Implement them as two helpers; don't emulate `poll_until_success` with a reader that swallows errors to `null`, because the final error is lost.
- **Await the observable effect** of one step before triggering the next. The pseudocode assumes synchronous mock delivery; real SDKs don't.

### 5.8 Assertions

- **No "accept either behaviour" assertions** (`writing-derived-tests.md` "Avoid the accommodate-both pattern"). Assert the spec or, as a documented deviation, the SDK's actual behaviour. Never both.
- `FAILS WITH error` asserts the `ErrorInfo` fields (`code`, `statusCode`, `message`), not exception type names.
- **`IS <Type>`**: a native type check in statically typed languages; in weakly typed ones (Python, Ruby, JavaScript), `isinstance` or a check that the expected members exist (`writing-test-specs.md` "Type Assertions"). Where the static type already guarantees it, see [7.4](#74-language-inapplicable-inputs) case (b).
- Use a hard assertion (stop the test) where later lines depend on the value, and a soft one elsewhere.
- Normalise numeric types where the language compares `Int`, `Long` and `Double` as unequal.

### 5.9 Internal access (white-box unit specs)

**Public-API specs use only the public API.** Even where the test target can see internals, unit specs that exercise the public API use only the public API plus harness helpers; so do fixture helpers such as REST provisioning. Only the module's listed white-box specs, and documented deviations, may reach internals. List the white-box specs in the notes or the mapping file.

For white-box specs, use this ladder, documented in the skill or in the module notes:

1. Use an existing internal exposure. **Check first; never duplicate.**
2. Otherwise add a minimal, test-only exposure in the SDK's sanctioned way (ably-cocoa core: a private header registered in both modulemaps, used via `import Ably.Private`; ably-cocoa objects: a `testsOnly_` accessor in the shared test-support module; C#: `InternalsVisibleTo`). Accessors stay dumb; no logic.
3. If more than a visibility raise is needed, **stop and escalate** to a maintainer.
4. If the symbol is unreachable, keep the spec line as a comment and record a Mock Infrastructure Limitation.

When a white-box spec asserts on the value an internal call returns, assert on that return value, not on a side channel such as emitted events. Integration and proxy specs use only the public API (`writing-derived-tests.md`, case 3).

---

## 6. Pseudocode construct catalogue

Fill in the last column for your language; the skill MUST map every construct its specs use. Each row's "meaning" comes from the UTS docs where one exists; rows marked *(undocumented)* are used in the corpus but not defined in the docs, and the meaning is inferred from usage. The Swift and Kotlin cells name only methods and patterns that exist in each skill, its notes, its harness or its generated tests; "—" means that SDK has no rule for the construct, so follow the meaning column. The cells illustrate; they aren't templates. Write your own column from your harness and SDK, and don't copy theirs, or anything seen in the [reference implementations](#reference-implementations-last-resort).

**This catalogue is not exhaustive**: the corpus keeps growing and has no grammar. The skill MUST treat any uppercase keyword or snake_case helper it can't map as a **stop condition**: tell the user, propose a rendering, and add a row to its own table rather than improvising per test. Re-scan the corpus for new keywords on every re-sync ([9.2](#92-a-re-sync-mode-should)). The skill SHOULD ship a **corpus scanner** (`scripts/scan_constructs.py`, [3.1](#31-layout)) that lists every uppercase keyword and `snake_case(` call in a module's `pseudo` fences, outside comments and string literals, with counts, so the re-scan is mechanical; compare its output with the construct table.

### 6.1 Async, waiting and state

| Construct | Meaning | Swift (ably-cocoa) | Kotlin (ably-java) | Your language |
|---|---|---|---|---|
| `AWAIT expr` | Await an async call | `try await op`, or a continuation-bridged helper for callback APIs | `.await()` on a future, or `suspendCancellableCoroutine` around a callback | |
| `f = op()` … later `AWAIT f` (incl. `AWAIT f FAILS WITH error`) | Deferred future: start an operation, act, then await it | `let t = Task { try await op() }` … `try await t.value` (objects module notes) | Hold the `CompletableFuture` (``val getFuture = channel.`object`.get()``) … `getFuture.await()` (generated tests, e.g. `RealtimeObjectTest`) | |
| `AWAIT_STATE x.state == ConnectionState.connected` (also `ChannelState.attached`, bare `CONNECTED`) | Subscribe, then proceed if already true, otherwise wait for the state event; fail on timeout (`writing-test-specs.md` "State Transitions"; [5.7](#57-waits-must-catch-events)) | `awaitConnectionState(client, .connected)` (unit); `await awaitState(client, .connected)` (integration) | `awaitState(client, ConnectionState.connected)` | |
| `… WITH timeout: N seconds` (`Ns`, `N second`) | Bound on the wait; wall-clock at integration tier | `timeout:` parameter on helpers; no per-call timeout on native `await` (note it in a comment) | `awaitState(client, state, 10.seconds)`; `withRealTimeout` for integration futures | |
| `AWAIT UNTIL <cond>`, `WAIT_FOR <cond>` *(undocumented)* | Wait until the condition holds | — | — | |
| `AWAIT_ERROR future` *(undocumented)* | Await a future expected to fail; bind its error | — | — | |
| `AWAIT_ALL futures` *(undocumented)* | Await all futures | — | — | |
| `x.once("connected")` awaited | JS-flavoured one-shot wait; treat as `AWAIT_STATE` | — | — | |
| `poll_until(cond, interval, timeout)`; also the `POLL_UNTIL(timeout:, interval:):` block and `AWAIT pollUntil(CONDITION: …, timeout:)` *(undocumented spellings)* | Re-evaluate until truthy; return the value; an error aborts (`writing-test-specs.md`) | `poll("desc") { … }` (unit, Bool); `pollUntil("desc") { … }` (integration, value-returning) | `pollUntil(10.seconds, 500.milliseconds) { … }` | |
| `poll_until_success(condition: FUNCTION() => …)`; bare form `poll_until_success(<expr>, timeout: 15s)` | Errors mean "keep polling"; on timeout rethrow the last error (`uts/README.md`) | — (ports used `pollUntil` with a reader that maps errors to `nil`) | — | |
| `process_pending_events()` | Let queued async work finish; no real delay (`uts/README.md`) | — (objects ports drain the collector queue) | Objects module notes: `` (channel.`object` as DefaultRealtimeObject).asyncFuture { }.await() `` | |
| `WAIT 500ms` | Real delay; discouraged, present at integration tier | `Task.sleep` with a comment (generated tests) | — | |
| `RETURN NEVER_RESOLVING_FUTURE` *(undocumented)* | A callback that never completes | — | — | |
| Quiescence / control-listener (`assert_unchanged_after_quiescence`) | Objects negative assertion (`standard_test_pool.md`) | Objects module notes | Inline control listener in generated tests (e.g. `InstanceTest.kt`); no notes rule | |

### 6.2 Time

| Construct | Meaning | Swift | Kotlin | Your language |
|---|---|---|---|---|
| `enable_fake_timers()` | Install the fake clock **before** constructing the client | `enableFakeTimers()` before `makeRealtime`/`makeRest` | `FakeClock()` + `enableFakeTimers(fakeClock)` | |
| `ADVANCE_TIME(ms)` | Advance fake time and fire due timers | `advanceTime(byMilliseconds:)` | `fakeClock.advance(…)`, then `yield()` | |
| `LOOP up to N times: ADVANCE_TIME … IF … BREAK` | Time-advancement loop, then a final `AWAIT_STATE` | Keep the loop | Keep the loop | |
| `TestClock()`, `WITH_CLOCK(test_clock):`, `test_clock.advance(…)`, `test_clock.now()` *(undocumented)* | A DI clock scoped to a block | — | — | |
| `SCHEDULE_AFTER(100ms):` inside a mock handler *(undocumented)* | Run the block after fake time advances by the delay | — | — | |
| `NOW()` / `now()`, `now_millis`, `time_now`, `current_time`, `current_fake_time` | Current time (fake, where installed) | — | — | |

### 6.3 Assertions and matchers

| Construct | Meaning | Swift | Kotlin | Your language |
|---|---|---|---|---|
| `ASSERT a == b` | Equality (deep where appropriate) | `#expect(a == b)` | `assertEquals(b, a)` (expected first) | |
| `IS null` / `IS NOT null` (also `IS NULL`, `IS NOT NULL`, `IS undefined`) | Language-appropriate absent value (`uts/README.md`) | `#expect(x == nil)` / `try #require(x)` | `assertNull` / `assertNotNull` | |
| `IS null OR … IS NOT SET` *(undocumented)* | Field absent or null | — | — | |
| `IS <Type>` | Native type check; member check in weakly typed languages ([5.8](#58-assertions)) | `#expect(x is T)` | `assertIs<T>(x)` | |
| `IS SAME AS` / `IS NOT SAME AS` *(undocumented)* | Reference identity | — | — | |
| `IN` / `NOT IN` | Membership or key presence | `#expect(map["k"] != nil)` | `assertContains(map, "key")` | |
| `x HAS member` *(undocumented)* | Member exists | — | — | |
| `CONTAINS` (optionally `(case insensitive)`) | Substring or element | — | — | |
| `STARTS WITH` / `STARTS_WITH`, `ENDS WITH` / `ENDS_WITH` | Prefix / suffix (both spellings occur) | — | — | |
| `matches pattern "regex"`, `MATCHES /regex/` | Regex match | `range(of:options: .regularExpression)` | `assertTrue(x.matches(Regex(…)))` | |
| `CONTAINS_IN_ORDER [a, b, c]` | **In-order subsequence**: the items appear in this order; other items may be interleaved (`writing-test-specs.md`) | See the first note in 6.7 | See the first note in 6.7 | |
| `ASSERT ALL x IN xs: pred`, `ASSERT ALL x == y FOR x IN xs`, `ASSERT ANY …` *(undocumented)* | Universal / existential check | — | — | |
| `ARE all unique` *(undocumented)* | No duplicates | — | — | |
| `IS EMPTY` / `IS NOT EMPTY` (also lowercase `IS empty` / `IS NOT empty`) | Empty / non-empty | — | — | |
| `IS NOT complete` *(undocumented)* | A deferred future hasn't settled yet (`objects/unit/realtime_object.md`) | — | — | |
| `IS valid`, `IS valid base64url string` *(undocumented)* | Well-formed value of the named kind (`rest/unit/fallback.md`, `objects/unit/object_id.md`) | — | — | |
| `.length == N`, `>=` | Size comparison | `#expect(list.count == N)` | `assertEquals(N, list.size)` | |
| `FAIL("msg")` | Unconditional failure | `Issue.record("msg")` (as in the skill's fail-fast pattern) | `fail("msg")` (kotlin.test; as in the skill's fail-fast pattern) | |

### 6.4 Errors

| Construct | Meaning | Swift | Kotlin | Your language |
|---|---|---|---|---|
| `AWAIT op() FAILS WITH error` / sync `op() FAILS WITH error` | Bind the failure's `ErrorInfo`; assert its fields | Capture the error, then `#expect(error.code == …)` | `assertFailsWith<AblyException> { … }` then `error.errorInfo.code` | |
| `error.cause.code` | Nested cause of an `ErrorInfo` (e.g. RTO23c1 in `objects/unit/realtime_object.md`: 92008 caused by 90000; RTO20e1 requires the same cause) | Objects module notes: check what the implementation populates; else assert the top level and flag a deviation | Objects module notes: read the Java exception cause | |
| `… THROWS error`, `THROWS AblyException WITH:` *(undocumented)* | Same as `FAILS WITH` | — | — | |
| `EXPECT THROW creating Realtime(…)` *(undocumented)* | Construction must fail | — | — | |
| `THROW ErrorInfo(…)` / `THROW AblyException(…)` / `THROW Error(…)` inside a test-supplied callback *(undocumented)* | Raise an error from the callback (e.g. an `authCallback` that fails), so the SDK sees a callback failure | — | — | |
| `TRY: … CATCH` | Discouraged in specs but present; translate literally, but assert error fields | — | — | |

### 6.5 Control flow, data and parameterisation

| Construct | Meaning | Swift | Kotlin | Your language |
|---|---|---|---|---|
| `IF / ELSE IF / ELSE`, `IF … THEN`, `… END`, `WHILE`, `PASS` | Ordinary control flow; `END` closes a block; `PASS` is a no-op | native | native | |
| `AND`, `OR`, `NOT` | Boolean operators | native | native | |
| `LOG "…"` *(undocumented)* | Informational output: render as a test log line or comment, never an assertion | — | — | |
| `FOR EACH test_case IN test_cases:` + `### Test Cases` table | Table-driven test; `test_cases` is the table | — | — | |
| `FOR x IN [..]`, `FOR i IN 0..n-1`, `FOR [k, v] IN x.entries()` | Loops | native | native | |
| `FIND x IN xs WHERE …`, `FILTER xs WHERE …` *(undocumented)*, `.filter(…)`, `.any(…)`, `.map(…)` | First match / filtered list / predicates | native | native | |
| `FUNCTION(params): … RETURN`, `(x) => {…}`, spec-local `function name(…)` | Local function / lambda / file-local helper | native | native | |
| `LISTEN`, `SET()` | Event subscription; set literal | — | — | |
| `"${…}"`, `+` on strings | Interpolation / concatenation | native | native | |
| `PROTOCOL` | Protocol-variant variable | `@Test(arguments: [false, true])` | `@ParameterizedTest @ValueSource(booleans = [false, true])` | |
| `#` and `//` comments | Spec comments: copy verbatim | `//` | `//` | |

### 6.6 Mocks, fixtures and harness

| Construct | Meaning | Swift | Kotlin | Your language |
|---|---|---|---|---|
| `MockHttpClient(onConnectionAttempt:, onRequest:)` + `install_mock()`; `req.respond_with(…)`, `respond_with_delay(ms, status, body)` | `mock_http.md` | Handler-pattern mock, installed before client creation | `install(mock)` | |
| `mock_http.queue_response(…)` and the other `queue_*` calls; `mock_http.captured_requests` *(legacy; deprecated in `writing-test-specs.md` "Common Mistakes to Avoid")* | Pre-queued responses; mock-owned request log ([2.2](#22-a-shared-test-library-implementing-the-helper-specs-must)) | — | — | |
| `mock_http.reset()`, `mock_ws.reset()` | Clear all mock state (`mock_http.md`, `mock_websocket.md`) | — | — | |
| `MockWebSocket(onConnectionAttempt:, onMessageFromClient:, onTextDataFrame:, onBinaryDataFrame:)` | `mock_websocket.md` | Handler pattern, `onConnectionAttempt` only | `onConnectionAttempt`, `onMessageFromClient`, `onTextDataFrame`, `onBinaryDataFrame` callbacks (preferred over the await style) | |
| `on_connect(respond_with:)`, `on_message(action:, respond_with:)`, `on_client_message(…)`, `await_client_message(action:)` *(undocumented alternative API)* | Shorthand handlers | — | — | |
| `conn.respond_with_success/_refused/_timeout/_dns_error/_error`, `respond_with_connected()` | Connection outcomes | `respondWithSuccess`, `respondWithRefused`; no WS-level timeout or DNS error (a known gap: extend the mock or record a limitation) | `respondWithRefused()`, `respondWithTimeout()`, `respondWithDnsError()` | |
| `CONNECTED_MESSAGE`, `CLOSED_MESSAGE`, `DISCONNECTED_MESSAGE`, `HEARTBEAT_MESSAGE`, `ERROR_MESSAGE(code, message)`, `PING_MESSAGE(id)` | Message templates (`mock_websocket.md`) | `.connectedMessage`, `.connected(…)`, `.attached`, `.error`, `.ack`, `.closed()` factories (`connectionStateTtl` in seconds, not wire ms); no `PING_MESSAGE` factory | `CONNECTED_MESSAGE`; `ErrorInfo(message, statusCode, code)` argument order | |
| `mock_ws.active_connection.send_to_client(…)`, `send_to_client_and_close`, `simulate_disconnect`, `close_from_server()`, `send_to_client_raw(json)`, `send_ping_frame` | Server-side actions | `sendToClient`, `sendToClientAndClose`, `simulateDisconnect`; no ping-frame method | `sendToClient`, `sendToClientAndClose`, `simulateDisconnect`; no ping-frame method | |
| await API: `await_connection_attempt()`, `await_request()`, `await_next_message_from_client()`, `await_client_close()` | Await style; set up the next await **before** responding to the current one | — (not implemented; handler style + attempt counter + `sentMessages` instead) | `awaitConnectionAttempt()`, `awaitRequest()`, `awaitNextMessageFromClient()`, `awaitClientClose()` | |
| `mock_ws.events.filter(…)` with event types `CONNECTION_ATTEMPT`, `CONNECTION_SUCCESS`, `CONNECTION_FAILURE`, `MESSAGE_FROM_CLIENT`, `MESSAGE_TO_CLIENT`, `CLIENT_CLOSE`, `SERVER_DISCONNECT`, `PING_FRAME` (`mock_websocket.md`); `mock_ws.connect_attempts` *(no helper spec; used in a `writing-test-specs.md` example)*, `mock_ws.last_connect_url` *(undocumented)* | Mock event log; connection attempts and the last connect URL | `ws.sentMessages` (client → server frames) | `events: List<MockEvent>` | |
| `mock_ws.onConnectionAttempt = …` | Reassign a handler mid-test | — | — | |
| `create_mock_websocket()`, `create_realtime_client(…)` *(undocumented aliases)* | Same as `MockWebSocket()` / `Realtime(…)` | — | — | |
| `MockNetworkListener()`, `simulate_network_lost()` / `simulate_network_available()` *(no helper spec)* | Network-change mock ([2.2](#22-a-shared-test-library-implementing-the-helper-specs-must)) | — | — | |
| `CLOSE_CLIENT(client)` *(undocumented)* | Close the client so its internal timers stop | `closeClient(client)`; integration scopes own it | `client.close()`; in `finally` for proxy tests | |
| `captured_requests.append` / `.push`, `request.url.path` / `request.path`, `.url.query_params` / `.query_params` / `.queryParams` | Request capture (spellings vary) | `Captured<T>` | `CopyOnWriteArrayList` | |
| `parse_json` / `JSON_PARSE` / `JSON_DECODE` / `json_decode`, `json_encode`, `MSGPACK_DECODE` / `msgpack_decode` / `msgpack_deserialize`, `msgpack_encode`, `base64_decode` / `base64_encode`, `load_json`, `load_fixtures`, `toJson()` / `fromJson()`, `encode_uri_component()` / `decode_uri_component`, `base64url_encode` / `base64url_decode`, `encode_utf8` / `utf8_encode` / `utf8_decode`, `parse_query_string`, `parse_form_urlencoded`, `extract_between`, `byte_array([…])`, `to_json`, `msgpack_serialize`, `as_list`, `DateTime(…)` | Data helpers; `toJson`/`fromJson` map to the SDK's idiomatic names (not a deviation) | `[String: Any]` | — | |
| `random_id()`, `random_string`, `unique_channel_name()`, `base64(random_bytes(6))` | Random / unique names | UUID channel names | `UUID.randomUUID()` | |
| `COUNT_UNIQUE(…)`, `EXTRACT_FALLBACK_ID(…)` *(undocumented)* | Spec-level helpers (`fallback_hosts_test.md`) | — | — | |
| `generate_jwt(…)` / `generateJWT(…)`, `extract_key_name(api_key)`, `extract_key_secret(key)`, `get_key_parts`, `request_token_from_sandbox(api_key, params)` *(the last two undocumented)* | Auth helpers | Locally signed `TokenRequest` instead of JWT, with a comment | Locally signed `TokenRequest` | |
| `BEFORE ALL TESTS`, `AFTER ALL TESTS`, `BEFORE EACH TEST`, `AFTER EACH TEST`, `AFTER TEST:` | Fixtures | `with…` scopes, per test | `@BeforeAll` / `@AfterAll` | |
| `POST https://…/apps WITH body from …`, `DELETE … WITH Authorization: Basic …` | Sandbox provisioning | `SandboxApp` | `SandboxApp.create()` / `delete()` | |
| `create_proxy_session(endpoint:, rules:)` (or `rules:` only; see 6.7), `add_rules`, `trigger_action`, `get_log()` / `session.getLog()`, `proxy_port` | `proxy.md` | `withProxySession(rules:)`; typed `ProxyEvent` log | `ProxySession.create(…)`, `finally { session.close() }`; typed log | |
| `"__PASSTHROUGH__"` as a field value in a `replace` action's message *(undocumented)* | A placeholder string, not a uts-proxy feature: uts-proxy v0.3.0 sends a `replace` message verbatim, so the SDK receives the literal value (used in `realtime/integration/proxy/connection_resume.md` Test 22, whose assertions don't depend on it). Treat it as an ordinary string; don't implement a substitution | — | — | |
| `MockVCDiffEncoder()`, `MockVCDiffDecoder`, `FailingMockVCDiffDecoder` | `mock_vcdiff.md` | — | — | |
| `setup_synced_channel`, `setup_synced_channel_no_ack`, `STANDARD_POOL_OBJECTS`, `build_*`, serial helpers, `provision_objects_via_rest` | `standard_test_pool.md` | Unit tier seeds the pool directly (sanctioned stand-in); helpers in the test-support target | `setupSyncedChannel("test")`, `build*` in module `Helpers.kt` | |
| White-box access: `applyOperation`, `channel.object.objectsPool`, `processChannelState`, direct construction, `get_backoff_coefficient(n)`, `get_jitter_coefficient()`, `encode_recovery_key(…)`, `CLEAR channel._lastPayload.messageId` | Internal access ([5.9](#59-internal-access-white-box-unit-specs)). `CLEAR …` in `delta_decoding_test.md` is a private-field write inside an *integration* spec | Core: `import Ably.Private` + private headers; objects: `@testable import` + `testsOnly_` accessors | `internal` within `:liveobjects` | |
| `logLevel: LOG_INFO`, `logHandler: (level, message) => …` (with `level == WARN` / `info` / `debug`), `captured_log_messages.filter(…)`, `captured_logs`, `log_messages` | Log capture; log levels | `CapturingLog`, `log.contains(level:message:)` | — | |
| `MESSAGE_ACTION_INT`, `HAS_OBJECTS`, `HAS_PRESENCE`, protocol actions | Wire constants | — | — | |
| `DEFAULT_REST_HOST`, `SANDBOX_ENDPOINT` *(undefined in the docs)*, spec-local constants such as `DEFAULT_CONNECTION_STATE_TTL = 5000` | Named constants: the SDK's default, the harness's sandbox endpoint, or a value the spec defines | — | — | |
| Reserved words (`channel.object`) | Escape idiomatically; not a deviation | — | `` channel.`object` `` | |

### 6.7 Notes on the catalogue

- **`CONTAINS_IN_ORDER` is an in-order subsequence, not a contiguous prefix or an exact filtered list.** `[connecting, disconnected, connecting, connected]` satisfies `CONTAINS_IN_ORDER [disconnected, connecting, connected]`. Kotlin's iterator-`next()` mapping asserts a contiguous prefix. Swift's `filter { [a, b, c].contains($0) } == [a, b, c]` fails when a listed state occurs more than once; its alternative ("walk an index as the spec does") is correct but unspecified. Ship an `assertContainsInOrder` helper in the harness and map to it. (ably-java's `ObjectsFaultsTest.kt` has a correct file-local one; the gap is that it isn't in the harness.)
- **Enum spellings vary**: `ConnectionState.connected`, `ChannelState.attached` and bare `CONNECTED` mean the same.
- **`writing-derived-tests.md` writes `AWAIT_STATE(connection, "connected")`**; the corpus form is `AWAIT_STATE client.connection.state == ConnectionState.connected`. Support both.
- **Proxy session:** `writing-test-specs.md` shows `create_proxy_session(target: TargetConfig(…))`; `proxy.md` and 41 of the 43 corpus calls take `endpoint:`. The other two (`realtime/integration/proxy/presence_reentry.md`) pass only `rules:`, so the session helper must default the endpoint to the sandbox. No corpus call uses `target:`. Follow `proxy.md`.
- **Proxy msgpack:** `proxy.md` gives "SDK doesn't implement msgpack" as the JSON reason; the real reason is that the proxy only supports text frames (`integration-testing.md`).
- **Dart, ably-js and ably-java residue** in specs (`Uint8List`, `fromMap`, `.once(…)`, `undefined`) is a hint, not a prescription.

---

## 7. Evaluation and deviations

Follow `writing-derived-tests.md` Phase 2 and "Recording deviations" exactly. The skill adds only the language rendering and the stopping rules.

### 7.1 Three acceptable end states

Every evaluated test ends in exactly one of these. Never an unexplained red.

| Outcome | Test state | Rendering the skill must specify |
|---|---|---|
| **Pass** | Green | — |
| **SDK deviation** (`writing-derived-tests.md` 2c) | Green: **env-gated skip** on `RUN_DEVIATIONS`, or **adapted assertion** (preferred when the divergence is permanent or intentional), with a `// DEVIATION: see deviations.md` comment | A **runtime** skip idiom (below) and the reproduction command (`RUN_DEVIATIONS=1 <runner> <filter>`) |
| **UTS spec error** (`writing-derived-tests.md` 2a) | **Red, fails fast** with a message pointing at `deviations.md`. The one acceptable red | The fail idiom (Swift `Issue.record("UTS spec error <id> — fix the spec first; see deviations.md")`, Kotlin `fail(…)`) |

A translation error (2b) is not an outcome: fix the cause ([section 5](#5-translation-rules)) and regenerate.

Runtime skip idioms (the gate must read the environment in the test process; a pytest `skipif` decorator does, a compile-time attribute doesn't):

- Swift Testing: `@Test(.enabled(if: ProcessInfo.processInfo.environment["RUN_DEVIATIONS"] != nil))`
- Kotlin: `if (System.getenv("RUN_DEVIATIONS") == null) return@runTest`
- pytest: `@pytest.mark.skipif(not os.environ.get("RUN_DEVIATIONS"), reason=…)`
- C#: xUnit v2 `[SkippableFact]` + `Skip.If(…)` (Xunit.SkippableFact), xUnit v3 `Assert.Skip(…)`, NUnit `Assert.Ignore(…)`

**SDK lacks the API entirely**, so the spec-correct test can't compile. First decide, per `writing-derived-tests.md` "Check the SDK's API surface", whether the test is not applicable to this SDK ([7.4](#74-language-inapplicable-inputs) case (c)) or the absence is itself a deviation. If it is a deviation: register the test, keep the uncompilable spec lines as comments with a `// NOTE:`, and mark it skipped (not commented out; `writing-derived-tests.md` "Test-first considerations"). In evaluate mode, record it under **Failing Tests** with the test impact "skipped stub" (one of the test-impact values in `writing-derived-tests.md` "Recording deviations"). *Divergence from `writing-derived-tests.md`*, whose Failing Tests are env-gated: a test that can't compile can't be env-enabled, so it stays a skipped stub until the API exists. In translate-only mode, list it in the final report ([section 11](#11-final-report-format)).

### 7.2 Harness stand-ins are not deviations

Using fake timers where the spec uses real ones, a queue-ordering workaround, per-test sandbox provisioning, or seeding state directly instead of driving the spec's mock transport changes *how the test drives the SDK*, not what the SDK does. Explain it in a code comment or the file header. Don't record it in `deviations.md`. This extends `writing-derived-tests.md` case 1 (idiomatic translation) to the harness; the docs don't state it for harness stand-ins explicitly.

### 7.3 `deviations.md`

- Use the format in `writing-derived-tests.md` "Recording deviations"; **don't define a home-grown format in the skill**. That means:
  - all four headings, in order, with `*(none)*` for an empty one: **UTS Spec Errors**, **Failing Tests**, **Adapted Tests**, **Mock Infrastructure Limitations**;
  - the entry fields: spec point, what the spec says, what the SDK does, root cause, test impact, status (for SDK deviations) and resolution (once resolved);
  - where internal-shape differences recur, an `S-1…S-n` vocabulary.
- The skill specifies only **where** the file lives (one per owning test module) and that new entries go **into their category's section**, never appended at the end.
- **When it is written.** Per `writing-derived-tests.md` "Test-first considerations", the file is created during evaluation. In translate-only mode, list mock-capability gaps (Mock Infrastructure Limitations) and missing APIs in the final report ([section 11](#11-final-report-format)) instead, and record them on the first evaluate run. When the file is created, it has all four headings.

### 7.4 Language-inapplicable inputs

Per `uts/README.md`, an input that can't be constructed in your language makes that test or table row **not applicable**: note it **in the derived test file**, not in `deviations.md`, and don't count it as a coverage gap. Three cases:

| Case | Example | Rule |
|---|---|---|
| **(a) Inexpressible input** | A wrong-typed argument a static type system rejects (`increment("10")`); a non-string key in JavaScript | Not applicable. Omit the test or row with a comment at the omission |
| **(b) Assertion guaranteed by the static type** *(extends the README)* | `ASSERT keys IS Array` on a method whose declared return type is a list | Keep the spec line as a comment noting the compile-time guarantee: an annotated omission, not a deviation |
| **(c) Missing API** | The SDK has no such method | Not one of the README's cases: decide not-applicable vs deviation per `writing-derived-tests.md` "Check the SDK's API surface" ([7.1](#71-three-acceptable-end-states)) |

- Not every type mismatch is inapplicable. Calling `increment` on a map is still expressible by casting to the counter view and asserting the throw; translate it.
- Dynamic languages rarely have case (a): translate wrong-type rows as runtime assertions.
- *Divergence:* both existing skills' objects module notes record compile-time-unrepresentable inputs (case a) as deviations, and ably-java's first audit run also filed case (b) type assertions as deviations. New skills should follow the README.

### 7.5 Stopping rules for evaluate mode (SHOULD)

"Fix until green" needs a bound. The skill should:

- Stop and ask the user after a fixed number of fix attempts per test (pick one, e.g. three).
- Stop and ask when a failure looks like a sandbox or network problem rather than SDK behaviour (passes alone but fails in the suite; provisioning errors).
- Stop and report each suspected **UTS spec error**, with the features-spec quote and a draft spec fix, rather than only recording it. Several upstream spec fixes came out of evaluation runs.
- Report undocumented helper contracts the port had to invent (e.g. the element type of `mock_ws.connect_attempts`, which no helper spec declares) as suspected spec gaps.
- Never fix a test by weakening an assertion, re-reading after a poll, or accepting both behaviours.

---

## 8. Deterministic tooling

Path validation, mapping, spec discovery, naming and faithfulness checking are mechanical. **Scripts do them identically every run; a model eyeballing two files does them inconsistently.** In ably-java the audit's first use found three undocumented omissions in already-reviewed tests.

### 8.1 Resolver (`resolve_uts.py`): MUST

| Requirement | Detail |
|---|---|
| Validate the module | Expand a leading `~`. The parent directory is named `uts` (compare path parts, so it works on Windows); the directory exists; it has `unit/` or `integration/` |
| Errors | One JSON object with `ok: false`, a code and a `message`. Example codes (ably-cocoa): `NOT_A_UTS_MODULE_PATH`, `DIR_NOT_FOUND`, `NO_TIER_DIRS`, `MAPPING_NOT_FOUND`, `BAD_MAPPING`, `BAD_TARGET_NAME` |
| Output contract | On success: `{ok: true, sourceModule, mapped, testRoot?, specRepo?, translationNotes, harness, tiers: {unit, integration, proxy: {present, sourceDir, targetDir, <namespace/package>, <build target>, specs: [{file, className, testFile?}]}}}`. `testFile` (the target file name) is required wherever it isn't `<className>.<ext>`, e.g. pytest `test_<stem>.py` with class `Test<Stem>`. `present` says whether the source tier directory exists; `targetDir` is `null` and `mapped` false when the module has no mapping entry. `testRoot` appears when the mapping declares a root. `specRepo` (`{sha, dirty, dirtyFiles}`, MAY) gives the spec clone's state (`dirtyFiles`: the modified or untracked files under `uts/` and `specifications/`, 9.1) for the file headers and the report (9.1, 9.4). `harness` (`{root, readme, tiers: {<tier>: {sources, tests}}}`) echoes the mapping's harness entry with paths validated (repo-relative), for the Harness reference and the preflight (3.2, 4 step F). Downstream steps read only these fields |
| Tier detection by path | `unit/**`; `integration/**` excluding `integration/proxy/**`; `integration/proxy/**`. Every tier can have sub-directories (e.g. `realtime/integration/channels/`). Use the path only. (Both existing skills also describe content-based proxy detection in their integration sections; drop it.) |
| Exclusions | `helpers/` (implement as harness, never translate), `README.md`, `PLAN.md`, `*_SUMMARY.md`. Match them **relative to the tier base**, so an ancestor directory in the checkout path can't trip them. *(New, defensive; nothing matches today:)* also skip any non-spec notes left inside a tier directory |
| Deterministic naming | Strip a trailing `_test`, convert to the language's convention, add the suffix or prefix the runner needs (`objects_lifecycle_test.md` → Swift `ObjectsLifecycleTests`, Kotlin `ObjectsLifecycleTest`, pytest `test_objects_lifecycle.py` with class `TestObjectsLifecycle`) |
| Collision detection *(new)* | Fail loudly if flattening sub-directories maps two specs to one class. Generated names can also collide with native test classes in another target (ably-cocoa `ObjectsPoolTests`); detect this, or always run generated suites with a target-qualified filter (`UTS.<Class>`). Runners that import test files by basename (pytest's default import mode) also collide when two tiers or modules produce the same file name (`rest/integration/auth.md` and `realtime/integration/auth.md` → `test_auth.py`): make the target directories packages (`__init__.py`) or use `--import-mode=importlib`, and check file-name uniqueness across the whole mapping |
| `--create` | Validate the existing mapping **before** writing, so a corrupt file is never written back. Add or replace the named module's entry, and preserve every other entry and the replaced entry's `notes`. Write UTF-8 with LF line endings explicitly. On a bad name, ask again |
| Notes | Resolve `notes` against the skill directory. *(New:)* return an error, not a silent `null`, when the declared notes file is missing |

### 8.2 Audit (`audit_translation.py`): MUST

| Check | Why |
|---|---|
| **Test-ID coverage**: spec `**Test ID**` set vs test-file `UTS:` set → `missing`, `orphan`, `duplicate`; a distinct non-zero exit when any is non-empty | A missing ID is a missing test; an orphan is a stale, renamed or invented tag; a duplicate tag hides a method from the ledger |
| **Per-test ledger**: every spec code line, grouped by section, tagged `assert` / `await` / `step` | Setup, operations and assertions are all enumerated |
| **Count assertions and waits separately** | Summed counts let surplus waits mask dropped assertions (ably-cocoa showed this by deleting RTN16f's two assertions; the ably-java audit still sums them) |
| **Ignore commented-out assertions** on the test side | A commented `// assertEquals(…)` isn't an assertion |
| **Never crash** | Always emit one parseable JSON object. Both references use exit 0 for clean, 2 for ID problems and 64 for "couldn't run"; any distinct codes will do |
| **Report what it can't see** *(new)* | A spec with no `**Test ID**` lines (fixture-driven specs) must be reported as "not verifiable", not as zero tests |

**Parsing contract.** Implement exactly this, or say where yours differs:

- **Spec side.** A test starts at each `` **Test ID**: `<id>` `` line (the backticks are part of the marker) and ends at the next one. *(New, SHOULD:)* also end it at the next heading at or above the test's own level, so trailing notes or appendix sections aren't attributed to the last test.
- **Headings.** Section headings are any `#`–`####` line **outside** a fence; inside a fence, `#` starts a pseudocode comment. Combined headings such as `### Test Steps and Assertions` are sections too.
- **Fences.** Read ` ```pseudo ` fences. You MAY also read untagged fences (four in spec files today, all in file preambles before the first test, plus one each in `objects/PLAN.md` and the `standard_test_pool.md` helper, which aren't translated; so this changes nothing yet; the Swift audit reads `pseudo` only). Skip ` ```json ` and other payload fixtures.
- **Classification.** Skip blank and comment lines. Tag `ASSERT` / `ASSERT_*` as `assert`, and also *(new; both existing audits tag these as `step` or `await`)* any line containing, outside a trailing comment, `FAILS WITH`, `THROWS`, `EXPECT THROW` or `AWAIT_ERROR`, whether or not it is awaited: the test side counts their native rendering (an expected-failure assertion) as an assertion call, so the spec side must too, or a dropped failure assertion goes unreported and the surplus can mask another dropped `ASSERT`. These failure forms take precedence over the await keywords. Tag `AWAIT` / `AWAIT_STATE` / `AWAIT_ALL` / `AWAIT UNTIL` and the poll forms `poll_until` / `poll_until_success` / `POLL_UNTIL` / `WAIT_FOR` as `await` (whether or not the line starts with `AWAIT`), so spec polls and the test's poll helpers are counted alike; everything else as `step`. Match the longest keyword first, on both sides (`poll_until_success` before `poll_until`; `pollUntil` before `poll`).
- **Test side.** A test's block runs from its `UTS:` tag to the next tag (or end of file). Helpers placed after the last test are attributed to it, and assertions inside shared helpers are invisible to their callers: keep shared helpers in a separate file or before the first test, and annotate call sites that hide spec assertions.

Only the test-side regexes change per language (tag marker, assertion calls, wait calls, comment syntax); the spec side is the same for every SDK.

**Output shape (SHOULD).** The guide fixes the checks, not the field names; a shape that covers them: `{ok, spec, test, idCoverage: {specCount, testCount, missing, orphan, duplicate}, perTest: [{id, title, sections, specAsserts, specAwaits, testAssertCount, testWaitCount, assertionShortfall, awaitShortfall}], summary: {testsWithAssertionShortfall, testsWithAwaitShortfall}, notVerifiable?}`, or `{ok: false, error}`.

SHOULD, beyond the existing audits:

- **Report the await shortfall separately, as a soft signal** ([8.3](#83-review-checklist-must-after-the-audit)).
- **Condition matching:** compare each `AWAIT` / `poll_until` predicate and timeout with the test's, at least as a side-by-side listing. A count can't catch a changed predicate.
- **Verbatim comment check:** flag spec comments that don't appear verbatim in the test.
- **Stale or renamed IDs:** pair each missing ID with an orphan that shares the descriptive name ([9.3](#93-renamed-merged-and-added-ids)).
- **Structural validation of the spec:** every test heading has an ID or is a recognised grouper or sub-case; the ID category matches the path; `## Test Type` is present; helper references point at files that exist. The spec repo has no automated UTS validation, so the skill is the only check.

**Test the tooling itself (SHOULD).** Mutation-test the audit: delete an assertion, or duplicate a tag, in a known-good test and confirm the audit flags it. Run it over the whole spec corpus after every script change and confirm zero crashes and no unexpected ledger changes. ably-cocoa did both for each audit change.

### 8.3 Review checklist (MUST, after the audit)

The review is static, so it runs in both modes.

- **Coverage:** `missing`, `orphan` and `duplicate` are empty, or each is explained. These, and a positive assertion shortfall, are the hard checks.
- **Line by line:** every positive assertion shortfall is accounted for by an annotated omission. A negative shortfall (more native assertions than spec `assert` lines, e.g. from type or number normalisation) is fine. A multi-line spec construct (a mock definition, a `ClientOptions(...)` block) appears as several `step` lines; reconcile them as one group.
- **Await shortfall is a soft signal.** The wait counter sees only the harness's wait helpers. Continuation-bridged helpers, native `await` on an async SDK API, and fixture builders legitimately replace them, so a positive await shortfall is expected on natively-async modules. Account for each spec `AWAIT` rather than treating the count as a gate.
- **Setup fidelity:** client options, mock responses, timer use and channel-operation order match the spec.
- **Wait fidelity:** every wait condition and timeout matches, or carries a `NOTE`/`DEVIATION`.
- **Deviation honesty** (evaluate mode): every gated or adapted test has a `deviations.md` entry, and no harness stand-in is recorded as a deviation.

---

## 9. Keeping in sync with spec changes

UTS has no version number or changelog, and **Test IDs are not stable**: they are renamed when spec points are replaced, and spec and UTS changes land in the same commit. A translation that was correct last month can be stale today.

### 9.1 Record what you translated from (MUST)

Stamp each generated file's header with the spec-repo commit SHA it was derived from:

```
// Derived from uts/realtime/unit/connection/connection_recovery_test.md
// at ably/specification@<full-sha>
```

A per-module manifest (spec file → SHA → test file) MAY be kept as well. Link source specs at the pinned SHA, not `blob/main`.

**A SHA identifies only committed content.** If a translated spec file differs from the recorded SHA (`git status --porcelain -- <file>` is non-empty: staged, unstaged or untracked), stop and ask. If the user proceeds, add `(locally modified; blob <git hash-object <file>>)` to that file's header, list the file in the final report, and have re-sync compare the file with that blob rather than with the SHA. Local changes elsewhere in the clone (for example untracked notes outside the tier directories) only need recording, as 9.4 says.

**Record the model.** The run's final report, which is the run record, records the model (name and ID) that generated or regenerated each file ([section 11](#11-final-report-format); part of that MUST format). A header line such as `// Generated with <model ID>` MAY be added as well. It changes whenever a different model regenerates the file, which adds diff noise, so prefer the run record.

### 9.2 A re-sync mode (SHOULD)

Neither existing skill has one; both have stale suites as a result. Add a mode (for example `/uts-to-<lang> <module-dir> --resync` in Claude Code, `$uts-to-<lang> <module-dir> --resync` in Codex) that:

1. Runs the audit over **every** mapped spec in the module, not only the ones selected.
2. Lists changed spec files against each file's recorded state, including uncommitted changes: `git diff --name-status -M <recorded-sha> -- uts/<module>` (the working tree, staged and unstaged, against the SHA; group files by the SHA in their headers), or `git hash-object` for a file stamped with a blob (9.1). Untracked spec files have no committed state: compare one stamped with a blob (9.1) with that blob, and treat one with no test file as **new**; untracked files outside the tier directories are local notes and are ignored. Decide new and removed by comparing the resolver's spec list with the existing test files. Then re-scan the corpus for constructs the skill can't map (section 6).
3. Classifies each spec as **new**, **changed** (any change to the spec file since its recorded state; report the kind: ID set, pseudocode, fixtures, or other content such as `## Protocol Variants`, `## Test Type` or prose), **unchanged** or **removed**. Review each changed file's diff to decide which tests to regenerate, and say why when a changed file is not regenerated. A spec whose helper specs or the UTS docs it relies on changed is reviewed too ([procedure section 10](../skills/uts-to-lang-skill-creator/references/maintenance.md#10-maintenance)).
4. Regenerates the affected tests, **preserving only** DEVIATION gates, adapted assertions, UTS-spec-error fail-fast placeholders (they stay until the spec is fixed; `writing-derived-tests.md` "Resolution") and `deviations.md` entries, and updating those entries.
5. Updates the SHA in each regenerated file's header, and its blob note (9.1): re-stamped if the spec is still locally modified, removed if not (and in the manifest, if kept).
6. Reports the classification ([section 11](#11-final-report-format)).

Regenerate the whole file when most tests changed; otherwise regenerate only the affected tests. Say which in the report. A re-sync is also needed when the shared harness or module helpers change shape (ably-cocoa reset and regenerated its objects ports after aligning them with `standard_test_pool.md`). After any harness change, re-run every affected tier's smoke tests and self-tests ([2.7](#27-harness-smoke-tests-and-self-tests-must)) first, then regenerate the tests whose rendering depends on the changed helper.

### 9.3 Renamed, merged and added IDs

Treat a removed ID plus an added ID as a **possible rename**, keyed on the descriptive name and position, and **re-check the assertions**: a renamed point can invert its semantics (`RTL15b1/serial-cleared-suspended-1` became `RTL15b2/serial-retained-suspended-1`).

Examples of the pattern, as of 2026-10-07 (spec `12540dcf`):

- **Rename not followed.** Both SDKs carried `realtime/unit/RTN16g2/recovery-key-null-inactive-0` after the spec renamed it to `realtime/unit/RTN16g3/recovery-key-null-inactive-0` (spec commit `d0d1c02f`): ably-cocoa `Test/UTS/unit/realtime/ConnectionRecoveryTests.swift` and ably-java `lib/src/test/kotlin/io/ably/lib/uts/unit/realtime/ConnectionRecoveryTest.kt`. The audit reports one missing and one orphan, but nothing prompted a re-run.
- **Additions not followed.** In ably-java `RealtimeObjectTest.kt`, two `RTO27` tests remained where the spec has a single `RTO27/channel-state-data-lifecycle-0` (the only `RTO27` Test ID in the spec's history, added in `65e6dd5e`), and `RTO20d4/mixed-null-serials-applies-non-null-0` (added in `6425db00`) had no test.

### 9.4 Local clone vs fetching `main`

Pick **one** source for docs and specs, and pin it. This guide recommends **reading everything from the local spec clone** the module directory came from:

- the UTS docs (`<module-dir>/../docs/writing-derived-tests.md`, `proxy.md`);
- in evaluate mode, the features specs the decision tree needs (`<module-dir>/../../specifications/features.md`, `objects-features.md`, `protocol.md`), rather than fetching them from GitHub.

Record the clone's HEAD SHA, whether it is dirty and which files are; a translated spec that is locally modified is handled as in 9.1. You MAY warn when the clone is behind `origin/main`.

- Read the features specs from the same clone as the UTS specs: the UTS spec and the features spec it is judged against must come from one revision (`writing-derived-tests.md` Phase 2, "2a. Is the UTS spec wrong?"), and the clone's SHA is recorded in every header and report (9.1). Fetching `main` gives a revision that nothing records.
- *Divergence (existing skills):* both existing skills fetch `writing-derived-tests.md` from GitHub `main`, and tell the model to "fetch" the features spec with no pinned source, while reading specs from the local clone, so the two can skew.

---

## 10. Verification and CI

Escalate in this order:

1. **Compile the tests** for the module (`swift build --build-tests`; `./gradlew :<module>:compileTestKotlin`; `dotnet build`). For every runner, check that every tagged test is collected (or executed): the number of distinct collected test functions, counting a parameterised or protocol-variant test once, equals the number of `UTS:` tags (the runner lists each parameter case separately, so group by function): a misnamed pytest class, or a JVM test annotated for an engine the task doesn't run (JUnit 4 vs JUnit Platform), is silently skipped. For pytest use `pytest --collect-only` (plus `mypy` if the repo uses it); for .NET, `dotnet test --list-tests`; for Gradle, compare the task's test-report count. In dynamic languages a missing SDK API surfaces only at run time: run a type checker (`mypy`/`pyright`) over the generated tests where the SDK ships type hints, or report missing APIs as unverified in translate-only mode. MUST, in both modes.
2. **Lint and format** with the repo's gates (EditorConfig, checkstyle, eslint, ruff…). MUST. Neither existing skill runs lint; both repos needed it.
3. **Compile as strictly as CI does.** If CI treats warnings as errors, so must the skill. (ably-cocoa's LiveObjects CI failed on a redundant typed-throws cast the local build accepted.) In TypeScript, the test runner may strip types without checking them (`writing-derived-tests.md` "Build pipeline and CI checks").
4. **Run the generated classes by filter** (evaluate mode): per class, then per tier. Use target-qualified filters where names can collide.
5. **Run the full tier** only when asked; integration tiers are slow and hit the sandbox.
6. **CI:** each suite has exactly one CI home ([2.5](#25-build-and-ci-wiring-must)). Don't gate integration tests behind an env var in the generated code; select them by filter or task.
7. **Commits (SHOULD).** By default the skill doesn't commit: it lists the files it changed (tests, `deviations.md`, mapping, notes) for the user to review. It also lists any project files the build doesn't discover automatically, which the user must update by hand (for example an Xcode project).

The skill's scripts MUST pin UTF-8 and LF when they write tracked files.

---

## 11. Final report format

Neither existing skill defines one; define it. The skill MUST end each run with a report like this:

```
UTS translation: <module>/<tier> @ ably/specification@<sha> (clone clean|dirty: <files>)  (mode: translate-only | evaluate | resync)
Model: <model name and ID>; sub-agents: <role → model, or none>

| Spec file | Test file | IDs (spec/test) | Audit | Shortfall accounted | Compile | Run | Deviations added |
|---|---|---|---|---|---|---|---|
| connection_recovery_test.md | ConnectionRecoveryTests.<ext> | 6/6 | clean | 1/1 | ok | 5 pass, 1 gated | Failing Tests: RTN16f |

Skipped specs (and why): …
Locally modified specs translated (9.1): <spec file> — blob <hash>
Re-sync classification (9.2): new …; changed (<kind>) …; unchanged …; removed …; changed but not regenerated: <file> — <why>
Not-applicable omissions (7.4): <id / row> — <reason>
Missing APIs found in translate-only mode: <id> — <API>
Mock-capability gaps found in translate-only mode: <id> — <capability>
Harness stand-ins disclosed in file headers: …
Constructs the skill couldn't map (stopped and asked): …
Harness preflight (step F): <tier> compile ok | smoke n/n | self-tests n/n | known-gap check ok (or the stop reason)
Harness changes made during this run, and the self-tests added or extended: …
Suspected UTS spec errors or gaps (need an upstream fix): <id> — <one line>, draft fix: …
Mapping or notes changes: …
Changed files for review: …
Next steps: …
```

---

## 12. Lessons learned

From the git histories of both existing skills. Most lessons are already rules in sections 2–10; these are the ones that aren't, or that are easy to forget.

| Lesson | Where it came from |
|---|---|
| **Build the harness to look like the pseudocode.** Callback mocks and a builder DSL make translation mechanical | ably-java's first generation run |
| **Move everything mechanical into scripts.** Paths, names, mapping and coverage checks drift when the model does them | Both: resolver, then audit |
| **Lessons must reach `SKILL.md`**, not only harness comments or commit messages | ably-java: several flake fixes stayed in KDoc |
| **Defer formats to the manual**; inline copies drift | The existing skills' inline `deviations.md` format, since replaced by a pointer to the manual (section 1) |
| **Don't cite line numbers in skill text**; they drift. Cite symbols or headings | ably-cocoa |
| **Compile the examples in the skill**, or take them from real, compiling files in your own repo | ably-cocoa: an example helper doesn't compile |
| **Placement follows visibility**: put white-box tests where internals are visible; share the harness as a library | ably-java tests moved to `:liveobjects` |
| **Evaluation finds spec bugs**; fix them at source | Evaluation runs of the existing skills |
| **Concurrency is the main source of flakiness**: thread-safe recording lists, await the seed before subscribing, flush before injecting a stimulus, a fake clock that runs to quiescence | ably-java CI fixes |
| **Keep the harness smoke tests and self-tests permanently, in CI**; scenario-only smoke tests miss contract violations, and without them harness defects surface as flaky spec-derived tests that must be triaged as SDK, spec or harness | Both: one SDK's env-gated smoke tests never ran in CI and were removed; the other's scenario smoke tests missed two helper contract violations |
| **Keep generic rules separate from per-language renderings**: write every rule language-neutrally first, then give its rendering for your SDK | Both: the Swift skill began as a port of the Kotlin one, and the generic parts had to be separated afterwards |

---

## 13. Checklist for a new `uts-to-<lang>` skill

The skill and its harness are one deliverable: the skill isn't done until every MUST item below, harness items included, is met for each tier it supports. An item whose source section is SHOULD (marked here or in the linked section) is met, or its omission is explained (✗ with a reason) in the final report. A MUST item that can't be met yet (for example, the repo owner declines the CI change that would run the harness tests) is also marked ✗ with the reason, and the skill doesn't conform to this guide until it is met.

**Harness**

- [ ] SDK test hooks: WebSocket factory, HTTP client, clock (covering blocking waits and the async runtime's timers), reachability/network monitor, randomness; injected at construction
- [ ] Shared test library: `mock_http.md` (+ legacy `queue_*` and `mock_http.captured_requests`), `mock_websocket.md` (async close, CONNECTED ordering, raw frames, alternative API, undocumented members), `mock_vcdiff.md`, `standard_test_pool.md`, `MockNetworkListener`
- [ ] Wait helpers: race-free event-latched `AWAIT_STATE` failing fast on FAILED, value-returning `poll_until`, `poll_until_success`, `process_pending_events()`, wall-clock timeout wrapper, deadlines safe under fake time
- [ ] Thread-safe capture, log sink, `assertContainsInOrder`, caller-attributed failures
- [ ] Harness designed from the repo's existing test setup (reuse, wrap, extend or build, 2.2); shared vs port-only placement; recommended harness layout; fixture-helper scope documented
- [ ] Harness README with a Known gaps section (MUST)
- [ ] Harness smoke tests per tier and helper self-tests (2.7): permanent, in CI, ungated, untagged, outside generated-test directories (MUST)
- [ ] `SandboxApp` (retries idempotent reads only); `ably-common` submodule
- [ ] `ProxyManager` with a pinned `uts-proxy` version for every developer OS, verified download, health check and port handling; `ProxySession`; string `match.action`; auth through the proxy decided and commented
- [ ] One CI home per suite (MUST); per-tier jobs (SHOULD)
- [ ] Concurrency, time, runner-parallelism and internal-visibility models documented

**Skill files**

- [ ] `SKILL.md` frontmatter portable across Claude Code and Codex: `name` equal to the directory; a pushy third-person description of at most 1,024 characters with no `<` or `>` and a "Not for" boundary; string-valued `metadata`; Claude Code-only fields only if accepted as non-portable ([3.3](#33-frontmatter-and-arguments))
- [ ] `SKILL.md`: a usage guard that doesn't rely on `$ARGUMENTS`; the skill's own files referred to relative to the skill directory, in `SKILL.md` and in the scripts; placeholder paths; follows the [3.4](#34-recommended-outlines-should) outline, including the Harness reference
- [ ] Installed for both tools from one source: `.claude/skills/` and `.agents/skills/`, by in-repo symlink or a CI-checked copy ([3.1](#31-layout)) (SHOULD)
- [ ] `uts-package-mapping.json`: one path per tier, unique namespaces, `notes` relative to the skill dir, hand-maintained entries marked, `harness` entry
- [ ] `resolve_uts.py`: validation, errors, output contract, path-based tiers, relative exclusions, runner-collectable naming, collision detection, validate-then-write `--create` preserving entries, `harness` output
- [ ] `audit_translation.py`: the parsing contract, ID coverage, duplicates, separate assert/await counts, ignores commented assertions, never crashes, flags unverifiable specs; itself mutation-tested
- [ ] Per-module notes for every module whose API diverges from the pseudocode (at least `objects`, if the SDK implements it)
- [ ] Scripts run on every developer platform (path handling, UTF-8, LF)

**Workflow**

- [ ] Required reading, including features specs, from the same clone as the specs
- [ ] Steps 0 and A–F: the four user questions (mapping, tier, specs, translate vs evaluate) and the harness preflight, which stops on red
- [ ] Steps 1–7 with batching; a reference test per tier; review in both modes
- [ ] Unmapped constructs stop and ask; corpus scanner in `scripts/` (SHOULD)
- [ ] Re-sync mode; fix the cause, then regenerate
- [ ] Mid-run harness changes re-run the smoke tests and self-tests and are reported separately

**Translation rules in `SKILL.md`**

- [ ] One `UTS: <id>` per test, verbatim; no invented tags; spec point in a collectable test name
- [ ] File header with source spec, tier, spec SHA, disclosures and (integration/proxy) the corresponding unit spec
- [ ] Verbatim comments, spec variable names, section headings, spec order
- [ ] Annotate, never drop, every `ASSERT`/`AWAIT`; never substitute a similar mock outcome
- [ ] Policies for sub-cases, groupers, test-case tables, delegating tests (new policy) and ID-less tests
- [ ] Protocol variants parameterised; tag singular; proxy JSON only
- [ ] Clients closed in teardown; mocks restored; stop on a failed wait
- [ ] Unique channel names; own proxy session per test
- [ ] Unit: fake time and flushes, no real timers. Integration: wall-clock everything
- [ ] Record-and-verify for transient states; polls return the settled value
- [ ] No accommodate-both assertions; `IS <Type>` per typing discipline
- [ ] Public-API specs stay public; internal-access ladder with an escalation stop
- [ ] Construct table ([section 6](#6-pseudocode-construct-catalogue)) filled in for every row

**Evaluation**

- [ ] Three end states with the language's runtime skip and fail-fast idioms; `RUN_DEVIATIONS` reproduction command
- [ ] `deviations.md` location per owning module; format deferred to `writing-derived-tests.md`; written at the right time
- [ ] Harness stand-ins disclosed in comments, not in `deviations.md`
- [ ] Language-inapplicable inputs (cases a–c) noted in the test file
- [ ] Stopping rules and spec-error escalation

**Verification**

- [ ] Compile (or collect), lint, CI-strict compile, filtered run
- [ ] No commits by default; changed files listed
- [ ] Final report format
- [ ] The skill's own examples compile

**Creation process**

- [ ] Skill and harness created on an Opus-class model (MUST); the skill states the model for its runs, or pins it where the tool supports that (SHOULD), and records it in its final report ([Model tier](#model-tier))
- [ ] Reads of the [reference implementations](#reference-implementations-last-resort), if any, made only as a last resort, recorded, and reported as guide gaps

---

## Appendix: Existing skills (background and patterns to avoid)

You shouldn't need to read these skills: this guide and the UTS docs are the authority. They are named so that the examples and lessons above can be traced, and as a last-resort reference for creating a skill and its harness ([Reference implementations (last resort)](#reference-implementations-last-resort)).

| Skill | Repo and paths | Lessons this guide drew from it |
|---|---|---|
| `uts-to-swift` | ably-cocoa, `.claude/skills/uts-to-swift/`; tests under `Test/UTS/` | Strict compile-time concurrency checking (Swift 6); a callback-based core plus a natively async plugin; scoped-resource teardown without async `tearDown`; separate assertion and wait counts in the audit; "a harness stand-in is not a deviation"; the internal-access ladder; module notes overriding the generic flow |
| `uts-to-kotlin` | ably-java, `.claude/skills/uts-to-kotlin/`; tests in the `lib/` (built by the `:java` Gradle module) and `liveobjects/` (`:liveobjects`) test source sets, harness in the `:uts` Gradle module (path `uts/`) | Deriving a package and build module from the target path; callback- and await-style mocks; race-free `awaitState`; virtual-time pitfalls and real-clock timeouts; idempotent-only sandbox retries; the `S-n` shape-deviation vocabulary |

Both contain a `SKILL.md`, a mapping file, a resolver and an audit script, and an objects module notes file.

### Reference implementations (last resort)

This guide and the UTS docs are meant to be complete. If they don't answer a question while you create or maintain a skill and its harness, you MAY consult the existing skills and harnesses, read-only, at the commits this guide reviewed:

| Repo @ commit | Skill | Harness | Harness smoke tests | Generated tests |
|---|---|---|---|---|
| [ably-java](https://github.com/ably/ably-java) @ `0ff24017` | [`.claude/skills/uts-to-kotlin`](https://github.com/ably/ably-java/tree/0ff24017d2692accb4acf66217fd42000543cc37/.claude/skills/uts-to-kotlin) | The `:uts` Gradle module (path `uts/`): [`uts/src/main/kotlin/io/ably/lib/uts`](https://github.com/ably/ably-java/tree/0ff24017d2692accb4acf66217fd42000543cc37/uts/src/main/kotlin/io/ably/lib/uts); README `uts/README.md` | [`uts/src/test/kotlin/io/ably/lib/uts`](https://github.com/ably/ably-java/tree/0ff24017d2692accb4acf66217fd42000543cc37/uts/src/test/kotlin/io/ably/lib/uts): one scenario smoke test per tier (unit, direct sandbox, proxy); no helper self-tests ([Patterns to avoid](#patterns-to-avoid)) | [`lib/src/test/kotlin/io/ably/lib/uts`](https://github.com/ably/ably-java/tree/0ff24017d2692accb4acf66217fd42000543cc37/lib/src/test/kotlin/io/ably/lib/uts) (rest, realtime; built by `:java`); [`liveobjects/src/test/kotlin/io/ably/lib/liveobjects/uts`](https://github.com/ably/ably-java/tree/0ff24017d2692accb4acf66217fd42000543cc37/liveobjects/src/test/kotlin/io/ably/lib/liveobjects/uts) (objects; `:liveobjects`) |
| [ably-cocoa](https://github.com/ably/ably-cocoa) @ `b5074d9b` | [`.claude/skills/uts-to-swift`](https://github.com/ably/ably-cocoa/tree/b5074d9b25f0b6d502835b027fc407e698cd5802/.claude/skills/uts-to-swift) | The `UTS` test target, [`Test/UTS`](https://github.com/ably/ably-cocoa/tree/b5074d9b25f0b6d502835b027fc407e698cd5802/Test/UTS) (helpers in `Test/UTS/infra`; README `Test/UTS/README.md`), plus the shared test-support targets it depends on: [`Test/AblyTesting`](https://github.com/ably/ably-cocoa/tree/b5074d9b25f0b6d502835b027fc407e698cd5802/Test/AblyTesting) and [`Test/AblyLiveObjectsTesting`](https://github.com/ably/ably-cocoa/tree/b5074d9b25f0b6d502835b027fc407e698cd5802/Test/AblyLiveObjectsTesting) | None: they were retired, a [pattern to avoid](#patterns-to-avoid) | [`Test/UTS/unit`](https://github.com/ably/ably-cocoa/tree/b5074d9b25f0b6d502835b027fc407e698cd5802/Test/UTS/unit), [`Test/UTS/integration`](https://github.com/ably/ably-cocoa/tree/b5074d9b25f0b6d502835b027fc407e698cd5802/Test/UTS/integration) |

Rules:

1. **The authority doesn't change.** Consult the references only after this guide, the UTS docs and the helper specs fail to answer the question. On any conflict, this guide (and, for semantics, the UTS docs, per [How it relates to the other UTS docs](#how-it-relates-to-the-other-uts-docs)) wins; record the conflict.
2. **Learn the pattern; never copy.** Don't copy, port or translate code, scripts, prose, tables or examples verbatim. Take how a problem was structured or solved, and write your own version in your language's idioms, on your SDK's hooks and harness.
3. **Check against [Patterns to avoid](#patterns-to-avoid)** before adopting anything. Both skills and both harnesses have documented defects, often in exactly the files you would consult.
4. **Read the pinned commits** linked above, where Patterns to avoid applies exactly. `main` may since have improved; if you consult `main`, re-check what you take against Patterns to avoid, and record which revision you used.
5. **Record each consultation**: the repo, commit and path, the question, what you learned, and how you checked it. Report each one as a gap in this guide: a candidate guide improvement.
6. **Creation only.** This applies to creating or maintaining a skill and its harness. A generated skill, at run time, never consults another SDK's skill (it reads only the local spec clone, [9.4](#94-local-clone-vs-fetching-main)), and neither does the pilot run that validates it.

Reading GitHub is network access: the [procedure](../skills/uts-to-lang-skill-creator/SKILL.md#21-your-inputs) gates it, or offers local clones that contain the pinned commits instead.

### Patterns to avoid

Observed in the existing skills and their harnesses as of 2026-10-07 (the reviewed checkouts, ably-cocoa `b5074d9b` and ably-java `0ff24017`; unchanged on remote `main` as fetched that day); some may since be fixed. Each is a pattern a new skill shouldn't copy. Check anything taken from the [reference implementations](#reference-implementations-last-resort) against this list. When the "as of" commits in the introduction move, update the links in that table and this list together.

**In both skills**

- **Fetching the manual from `main`, and telling the model to "fetch" the features spec with no pinned source,** while reading specs from a local clone ([9.4](#94-local-clone-vs-fetching-main)).
- **Two sources of tier truth**: path-based in the resolver, content-based in the `SKILL.md` integration section.
- **A `CONTAINS_IN_ORDER` mapping that isn't a subsequence check** ([6.7](#67-notes-on-the-catalogue)).
- **No re-sync mode, no final report, no lint step, no collision detection**, and a silent `null` when a declared notes file is missing.
- **Claude Code-only packaging** ([3.3](#33-frontmatter-and-arguments)): script paths hard-coded as `python3 .claude/skills/<name>/scripts/…` and reliance on `$ARGUMENTS`, both of which break under Codex; angle-bracket placeholders (`<…>`) in `description`, which skill packaging validators reject.

**In the harnesses**

- **Smoke tests env-gated and never run in CI, then retired** (ably-cocoa) once spec-derived tests covered their scenarios ([2.7](#27-harness-smoke-tests-and-self-tests-must)).
- **Scenario-only smoke tests** (ably-java) that stay green while a helper breaks its helper-spec contract.
- **A mock `close()` that notifies synchronously** (ably-java), although `mock_websocket.md` requires `onClose` to be called asynchronously.
- **A declared mock event type that is never emitted** (ably-java), so an assertion that filters the event log for it passes on an empty list.

**Seen in `uts-to-swift`**

- **Example code that doesn't compile**: the callback-bridging helper in "Assertions (Swift Testing)" has a `guard` body that doesn't exit and doesn't resume the continuation. (The real helper in `TimeTests.swift` is correct.)
- **Describing features that don't exist**: a per-tier class-name suffix the resolver doesn't implement, and a suite that doesn't exist.
- **Contradictory timeout guidance**: "pass an explicit `timeout:` only when the spec states one" alongside "generous timeouts (10–30s)" examples.
- **Pointing to rules in the wrong doc**: it says the value-assigned `poll_until` rule lives in `writing-derived-tests.md`; the reference definition is in `writing-test-specs.md`.
- **Deviations-file rules that contradict the manual**: it says to add the *UTS Spec Errors* heading "on first use if absent"; the manual requires all four headings always present.
- **A harness narrower than the helper spec**: the mock WebSocket lacks the await style, `onMessageFromClient` and raw-frame handlers, ping frames, a PING template, and WS-level `respond_with_timeout` / `respond_with_dns_error`. The harness README documents the first two, the skill documents only the last, and ping is documented nowhere.
- **A sample-based state wait** at the unit tier (`awaitConnectionState`).
- **Test names without the spec point**: the objects module notes override the naming rule so that objects unit tests have bare descriptive names, relying on the `// UTS:` tag alone; `writing-derived-tests.md` requires the spec point in the name.
- **Retrying a non-idempotent provisioning request**: `SandboxApp.create()` retries `POST /apps`. `integration-testing.md` says sandbox apps auto-expire, which justifies best-effort deletion, not retrying creation: a lost response still leaves duplicate apps until they expire. Retry only idempotent requests (2.3).
- **Writing `deviations.md` before evaluation**: it records Mock Infrastructure Limitations at generation time, including in translate-only mode; the manual creates the file during evaluation (7.3).
- **Citing the wrong spec point**: it attributes the fallback-disabling behaviour of explicit `realtimeHost`/`restHost` to REC2c2; it is REC2c6 (REC2c2 covers an `endpoint` hostname).
- **Citing spec points where they don't exist**: the objects module notes place `RTTS1–RTTS10` in `objects-features.md`; they exist only on the unmerged `feature/liveobjects-cross-sdk-types-spec` branch.
- **No rules for** `process_pending_events()`, `poll_until_success`, `CLOSE_CLIENT`, `WAIT` or `BEFORE ALL`; stale statements in the objects module notes and in `Test/UTS/README.md`, which the skill tells the model to read first.

**Seen in `uts-to-kotlin`**

- **An audit weaker than its sibling**: it counts `awaitState` / `awaitChannelState` / `pollUntil` as assertions (so surplus waits can mask dropped assertions), counts commented-out assertions, silently collapses duplicate `@UTS` tags, and reads every fenced block rather than only pseudocode. Build the audit from the 8.2 contract instead.
- **A non-documented tag marker**: `/** @UTS <id> */` instead of `// UTS: <id>`.
- **A resolver that can crash**: a malformed `uts-package-mapping.json` raises a Python traceback instead of a structured `ok: false` error.
- **Cleanup at the end of the body**: the unit template closes the client there, not in `finally` or `@AfterEach`.
- **Hard-won rules left out of `SKILL.md`**: `withRealTimeout` and record-and-verify exist in the harness but not in the skill, so some integration tests still await network futures unbounded.
- **Ambiguous or stale references**: a "Proxy integration tests" section that doesn't exist; "`uts/README.md`" meaning either repo's README.
- **Invented tags and silent predicate changes in generated tests**: one proxy and one direct-sandbox test added extra `@UTS` tags for secondary spec points, and one `pollUntil` predicate differs from the spec's with no comment.
