# Writing Derived Tests from UTS Specs

This guide covers the process of translating UTS (Universal Test Specification) portable test specs into working tests for a specific language and SDK. It also covers the optional evaluation step when an existing implementation is available to run the tests against.

## Overview

UTS specs are the source of truth for *what* to test. They define test structure, setup, assertions, and mock patterns in language-neutral pseudocode. A derived test translates that spec into a concrete, runnable test for a specific SDK.

The process has two phases:

1. **Translation** — always required. Produce a test file that faithfully implements the UTS spec.
2. **Evaluation** — optional. When an existing implementation is available, run the tests and diagnose any failures.

Not every situation has an existing implementation. Tests may be written ahead of the implementation (test-first development), or for a new SDK that doesn't yet exist. In those cases, only the translation phase applies.

---

## Phase 1: Translation

### 1. Translate the UTS spec faithfully

Write the test as closely as possible to the UTS spec. The UTS spec defines what to test — don't second-guess it, optimise it, or skip steps on a first pass.

- **Match the spec's structure**: one test per spec point, same assertions, same setup
- **Use the spec's naming**: test names must include the spec point (e.g. `RSL1a - publish sends POST to correct path`)
- **Preserve the spec's intent**: if the spec says "assert X", assert X, even if it seems redundant

### 2. Map pseudocode to language idioms

UTS specs use generic pseudocode. You need to map this onto the SDK's actual API and the language's test framework. Common mappings:

| UTS pseudocode | What to figure out |
|---|---|
| `Rest(options: ...)` | SDK constructor syntax |
| `ASSERT x == y` | Test framework assertion style |
| `mock_http = MockHttpClient(...)` | SDK's mock infrastructure |
| `install_mock(mock_http)` | How mocks are injected (DI, platform patching, etc.) |
| `enable_fake_timers()` | Timer control mechanism |
| `ADVANCE_TIME(ms)` | Fake timer tick method |
| `AWAIT_STATE(connection, "connected")` | State waiting helper |

Check the SDK's existing test infrastructure and conventions before writing anything. Reuse existing helpers, mock classes, and patterns.

### 3. Flag ambiguity

If the UTS spec is ambiguous — unclear what value to assert, unclear what "should" means in context, unclear whether a step is required or illustrative — add a comment in the test and continue with your best interpretation. Don't block on it; flag it for review.

```
// NOTE: UTS spec says "assert the response contains the field" but doesn't
// specify the value. Interpreting as: field must be present and non-null.
```

### 4. Verify the test compiles/parses

Before moving to evaluation (or declaring the test done in a test-first scenario), make sure the test at least compiles, parses, or passes linting. Syntax errors in the translation are not interesting failures.

---

## Phase 2: Evaluation (optional)

This phase applies when you have an existing SDK implementation to run the tests against. If you're writing tests before the implementation exists, skip to [Test-first considerations](#test-first-considerations).

### 1. Run the test

Run the translated test against the current SDK build.

If it passes, you're done with that test.

### 2. If it fails, diagnose

A test failure has exactly three possible causes. Work through them in order:

#### 2a. Is the UTS spec wrong?

Compare the UTS spec's claim against the Ably features spec (`specification/specifications/features.md`). The features spec is the ultimate authority. If the UTS spec contradicts it:

- Fix the test to match the features spec
- Add a comment explaining the UTS spec error
- Record the error in the **UTS Spec Errors** section of the deviations file

Examples:
- UTS spec claimed RSA4b means "clientId triggers token auth" — actual RSA4b is about token renewal on error
- UTS spec claimed expired tokens must not make HTTP requests — actual spec says local expiry detection is optional

#### 2b. Is the test translation wrong?

Re-read the UTS spec and your test side by side. Common translation errors:

- Wrong assertion (e.g. strict equality vs deep equality, null vs undefined/nil)
- Missing setup step (e.g. protocol format options, TLS settings)
- Wrong API mapping (SDK method name differs from spec pseudocode)
- Mock response doesn't match what the SDK expects

If the translation is wrong, fix the test. No deviation entry needed.

#### 2c. Is the SDK non-compliant?

If the UTS spec is correct per the features spec, and the test accurately translates it, then the SDK has a deviation. In this case:

- Keep the test, but adapt it to pass against the SDK's current behaviour
- Document exactly what the spec requires vs what the SDK does
- Record it in the deviations file

### 3. Deviation test patterns

There are two patterns for deviation tests. Both should write the **spec-correct assertions** in the test body — the test should fail when run, proving the deviation exists.

**Env-gated skip** (preferred) — the test contains the correct spec assertion but is skipped by default. An environment variable enables it on demand:
```
it("RSA7b - clientId from TokenDetails", function() {
  // DEVIATION: see deviations.md
  if (!process.env.RUN_DEVIATIONS) this.skip();

  // ... spec-correct setup and assertions ...
  assert client.auth.clientId == "token-client-id"
})
```
This has three advantages:
- Normal test runs stay green (deviations are skipped)
- Each deviation is individually reproducible: `RUN_DEVIATIONS=1 <test runner> --grep "RSA7b"`
- Issues filed against the SDK can link to a concrete reproduction command
- When the SDK is fixed, removing the skip guard is the only change needed

Use a consistent env var name across all deviation tests in the suite (e.g. `RUN_DEVIATIONS`).

**Adapted assertion** — when the deviation changes observable behaviour but the test can still validate something useful, assert the SDK's actual behaviour and comment the spec expectation:
```
it("RSC1b - no credentials raises error", function() {
  // DEVIATION: see deviations.md
  // Spec says error code 40106, ably-js uses 40160
  assert error.code == 40160
})
```
Use this pattern when the SDK does *something* (just not the right thing) and you want to assert on the actual behaviour to prevent regressions. These tests pass in normal runs.

**Avoid the accommodate-both pattern.** Tests that accept either the spec behaviour or the SDK behaviour (e.g. try/catch that passes regardless of which path is taken) provide no signal — they pass whether the SDK is compliant or not. Every test should either assert spec behaviour (and fail if non-compliant) or assert the SDK's actual behaviour (and document the deviation). Never both.

### 4. Decision tree

```
Test fails
  |
  +-- Does UTS spec match features spec?
  |     |
  |     NO --> Fix test, record UTS spec error in deviations file
  |     |
  |     YES
  |       |
  |       +-- Does test accurately translate UTS spec?
  |             |
  |             NO --> Fix the test
  |             |
  |             YES --> SDK deviation. Adapt test, record in deviations file
```

---

## Recording deviations

When evaluating against an existing implementation, maintain a deviations file (e.g. `deviations.md`) as the single record of all known issues. Each entry must include:

1. **The spec point** (e.g. RSA4b4)
2. **What the spec says** — quote or paraphrase the features spec
3. **What the SDK does** — concrete observable behaviour
4. **Root cause** (if known) — file, function, mechanism
5. **Test impact** — which test(s) are affected and how they were adapted

Deviations are grouped into three sections:
- **Failing Tests** — SDK non-compliance where the spec-correct test is present but skipped (env-gated). These are the primary output — each maps to a potential issue to file.
- **Adapted Tests** — SDK non-compliance where the test was adapted to assert actual behaviour. The test passes but documents a genuine deviation.
- **Mock Infrastructure Limitations** — tests that can't be implemented due to missing mock capabilities (e.g. msgpack support). These are skipped stubs, not SDK deviations.

This file is valuable output. It gives the SDK team a precise catalogue of spec gaps, each with a failing test that can be turned on once the fix lands.

### Filing issues from deviations

Once the test suite is complete, classify the deviations into distinct issues grouped by root cause or theme — not one issue per test. For example, five tests that all fail because `auth.clientId` isn't derived from token details are one issue, not five.

Each issue should include:
- The spec point(s) affected
- What the spec says vs what the SDK does
- A reproduction command: `RUN_DEVIATIONS=1 <test runner> --grep "<pattern>" <test file>`
- A link to the PR containing the test suite

This makes the issues actionable: a developer can check out the branch, run the command, see the failure, and know exactly what to fix.

---

## Test-first considerations

When writing tests before an implementation exists:

- **Write the test to match the spec exactly.** Don't preemptively accommodate likely implementation gaps — you don't know what they are yet.
- **Use the skip/pending mechanism** of your test framework liberally. Tests that can't run yet should be marked as pending, not commented out.
- **Mock infrastructure may not exist yet.** You may need to build it. Follow the mock patterns defined in the UTS spec (`rest/unit/helpers/mock_http.md`, `realtime/unit/helpers/mock_websocket.md`).
- **The deviations file is created during evaluation**, not during translation. If there's no implementation to evaluate against, there are no deviations to record yet.

---

## Practical notes

### Check the SDK's API surface

Not everything in the UTS pseudocode maps 1:1 to every SDK. Before writing tests, verify that the API exists. If an API is missing or named differently, note it and adapt the test.

### Required options vary by SDK

Some SDKs have defaults that conflict with mock infrastructure. For example, an SDK may default to binary protocol (msgpack) while mocks return JSON. Check what options are needed to make mocks work.

### Wire values vs decoded values

SDKs often convert between wire format and developer-facing types. For example, presence actions may be integers on the wire but strings or enums in the SDK's public API. Tests asserting on decoded objects must use the SDK's representation. Tests asserting on outgoing request bodies must use the wire format.

### Pagination and Link headers

If the SDK parses pagination `Link` headers, check the expected URL format. Some SDKs expect relative URLs with specific prefixes (e.g. `./messages?...`).

### Idempotent ID format

ID generation (base64 encoding, URL-safe variants, batch behaviour) varies between SDKs. Check the SDK's implementation before asserting on generated ID formats.

### Build pipeline and CI checks

Run the full build pipeline, not just the tests. Many SDKs have:
- **Type checking** (e.g. `tsc`, `mypy`) — catches type errors the test runner ignores
- **Linting** (e.g. `eslint`, `prettier`) — catches formatting issues
- **Bundling** (e.g. webpack, rollup) — may use stricter settings than the test runner

In TypeScript projects, the test runner (e.g. mocha with `tsx`) often **strips types without checking them**. The bundler (e.g. webpack with `ts-loader`) does full type checking. Both must pass. Run the CI checks locally before pushing.

Common type errors to watch for in test files:
- `let captured = []` needs `let captured: SomeType[] = []` (noImplicitAny)
- Callback parameters need type annotations: `(req) =>` -> `(req: any) =>`
- `catch (error)` needs `catch (error: any)` for property access
- Partial mock objects need `as any` casts when passed to typed constructors
- Optional method parameters may need explicit `null` or `{}` arguments

### Timer and platform type mismatches

SDKs that abstract platform APIs (timers, HTTP, WebSocket) behind an interface often have type mismatches between the interface definition and the concrete platform types. For example, `setTimeout` returns `number` in browsers but `NodeJS.Timeout` in Node. When installing mock timers, you may need explicit casts:

```
Platform.Config.setTimeout = mockSetTimeout as unknown as typeof Platform.Config.setTimeout;
```

These casts are an SDK wart, not a test problem — apply them as needed and move on.

### No real timers in unit tests

Unit tests must not use real timers (`setTimeout`, `setInterval`, `sleep`, `delay`) to wait for asynchronous events. Real timers make tests slow, flaky, and prevent the process from exiting cleanly.

- **For time-dependent SDK behaviour** (timeouts, retries, heartbeats): use fake timers that replace the SDK's timer API and can be advanced deterministically.
- **For waiting on async event delivery** (mock message propagation, promise settlement): yield to the event loop with a zero-delay mechanism like `setImmediate`, `process.nextTick`, or equivalent. Define a `flushAsync()` helper and use it everywhere instead of `setTimeout(resolve, N)`.
- **For "prove a negative" assertions** (confirming something did NOT happen): a single event-loop yield is sufficient — if the event hasn't fired after one pass through the macrotask queue, it won't fire from the current stimulus.

The only acceptable use of a real timer is a **safety timeout on test execution** — a long deadline (e.g. 5 seconds) that fails the test if an expected event never arrives, preventing the test from hanging indefinitely. This is a test-level safeguard, not a delay mechanism.

```
// BAD: real timer delay
await new Promise(resolve => setTimeout(resolve, 50));

// GOOD: event-loop flush
await flushAsync();

// OK: safety timeout to prevent hanging
const timer = setTimeout(() => reject(new Error('Timed out')), 5000);
connection.once('connected', () => { clearTimeout(timer); resolve(); });
```

### Cleanup with afterEach

Always restore mocks in `afterEach`, not just at the end of each test. If a test throws before its cleanup code, the next test inherits dirty state. Use the SDK's mock restoration mechanism (e.g. `restoreAll()`) in an `afterEach` hook.

The cleanup mechanism should cancel all SDK-internal timers, not just those reachable via the SDK's public API. Some SDKs have bugs where internal timers are orphaned (e.g. timer handles overwritten without cancelling the previous one). The test infrastructure should track all timer allocations and cancel any that survive `client.close()`.
