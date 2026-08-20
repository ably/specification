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

Write the test as closely as possible to the UTS spec. The UTS spec defines what to test — don't second-guess it, optimise it, or skip steps on a first pass. In particular, translation is purely mechanical. Spec-correctness is checked later, during evaluation (section 2a).

- **Match the spec's structure**: one test per spec point, same assertions, same setup
- **Use the spec's naming**: test names must include the spec point (e.g. `RSL1a - publish sends POST to correct path`)
- **Include the test ID**: add a `// UTS: <id>` comment immediately above each test function, using the test ID from the UTS spec (see `docs/writing-test-specs.md` § Test IDs for the format)
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
| `poll_until(condition, ...)` | Shared polling helper (wall-clock deadline — see below). Two forms, per the reference definition in `writing-test-specs.md`: a bare condition (re-evaluated until true), or a producer whose first truthy result is **returned** — a value-assigned poll (`x = poll_until(...)`) yields the settled value and later assertions run on **it**, never on a re-read (a refetch of an eventually-consistent read can under-return) |
| `poll_until_success(condition)` | Error-tolerant polling helper (see the pseudocode conventions in `uts/README.md`) |
| `random_id()` | The language's native UUID/GUID generator (`UUID.randomUUID()`, `UUID().uuidString`, `crypto.randomUUID()`) |

Check the SDK's existing test infrastructure and conventions before writing anything. Reuse existing helpers, mock classes, and patterns. For steps the spec does not time — including plumbing the port has to add itself, such as an explicit connect-and-await where the spec relies on auto-connect — use the harness's default wait; don't invent a tighter per-call timeout.

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

Compare the UTS spec's claim against the relevant Ably **features spec** — the ultimate authority. Every spec lives under the repo's [`specifications/`](https://github.com/ably/specification/tree/main/specifications) directory; the raw, fetchable base is `https://raw.githubusercontent.com/ably/specification/refs/heads/main/specifications/`. Fetch the one for the module under test:

- Core / Realtime / REST — [`features.md`](https://raw.githubusercontent.com/ably/specification/refs/heads/main/specifications/features.md)
- LiveObjects (`objects`) — [`objects-features.md`](https://raw.githubusercontent.com/ably/specification/refs/heads/main/specifications/objects-features.md)
- Chat — [`chat-features.md`](https://raw.githubusercontent.com/ably/specification/refs/heads/main/specifications/chat-features.md)

Related authorities in the **same** `specifications/` directory back specific areas — e.g. [`protocol.md`](https://raw.githubusercontent.com/ably/specification/refs/heads/main/specifications/protocol.md) (wire protocol) and [`encryption.md`](https://raw.githubusercontent.com/ably/specification/refs/heads/main/specifications/encryption.md) — fetch them too when a test touches that area.

A UTS spec can be wrong two ways: it **contradicts the features spec**, or it is **internally inconsistent** (e.g. a replayed serial that doesn't match the value its own harness produces, or a test title that names a state its body never injects). Either way the **spec is the source of truth and must be fixed there** — do **not** silently rewrite the test to match the features spec and move on. Quietly "fixing the test" hides the spec bug, leaves the spec wrong for every other SDK to re-hit, and defeats the point of a single source of truth. Instead:

- Record the error in the **UTS Spec Errors** section of the deviations file, with the spec id, what the features spec says, and what the UTS spec gets wrong.
- Make the generated test **fail fast** (see "Spec-error fail-fast" under section 3, Test patterns for a diagnosed failure) so the defect is impossible to miss and the spec gets fixed early, at source.

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

- Keep the test and handle it as an SDK deviation using one of the two patterns in section 3 — an **env-gated skip** or an **adapted assertion** (see there for which to choose)
- Document exactly what the spec requires vs what the SDK does
- Record it in the deviations file

### 3. Test patterns for a diagnosed failure

Once you've diagnosed a failure (section 2), there are three patterns. Two are for an **SDK deviation** (section 2c): **env-gated skip** keeps the spec-correct assertion but skips it unless explicitly enabled, and **adapted assertion** asserts the SDK's actual behaviour with the spec expectation in a comment. The third, **spec-error fail-fast**, is for a **UTS spec error** (section 2a): the spec itself is wrong, so there are no spec-correct assertions to write — the test fails fast and points at the fix instead. (A translation bug, section 2b, isn't a pattern — you just fix the test.)

**Env-gated skip** (preferred *for a deviation you expect to be fixed*) — the test contains the correct spec assertion but is skipped by default. An environment variable enables it on demand:
```
it("RSA7b - clientId from TokenDetails", function() {
  // DEVIATION: see deviations.md
  if (!process.env.RUN_DEVIATIONS) this.skip();

  // ... spec-correct setup and assertions ...
  assert client.auth.clientId == "token-client-id"
})
```
This has four advantages:
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
Use this pattern when the SDK does *something* (just not the right thing) and you want to assert on the actual behaviour to prevent regressions. These tests pass in normal runs. **Prefer this over an env-gated skip when the divergence is permanent or intentional** (the actual behaviour is stable and worth guarding) — a test that runs and asserts real behaviour catches regressions, whereas a spec-correct assertion that is skipped indefinitely verifies nothing. (Distinguish this from *idiomatic naming* — a differently-spelled public API is not a deviation at all — and from *internal-API shape* adaptation in white-box unit tests; see [Idiomatic translation vs genuine deviations](#idiomatic-translation-vs-genuine-deviations) under Recording deviations.)

**Spec-error fail-fast** — for a **UTS spec error** (section 2a), *not* an SDK deviation. An SDK deviation is a fact about the SDK as it stands, so its test stays green — skipped (env-gated) or asserting actual behaviour — and never blocks the suite. A spec error is a bug in the source of truth, so the opposite applies: the test must **fail immediately** with a message pointing to the deviations entry, forcing the spec to be corrected first rather than papered over:
```
it("RTLC7c2 - LOCAL source does not write siteTimeserials", function() {
  // SPEC ERROR RTLC7c2: replayed ACK serial "t:1:0" contradicts the harness ("ack-0:0").
  // Fix the UTS spec first — see deviations.md (UTS Spec Errors).
  throw new Error("UTS spec error RTLC7c2 — fix the spec first; see deviations.md")
})
```

**Resolution — fix the spec, then re-translate.** This test is a placeholder that blocks on the source of truth: it stays red until the **UTS spec** is corrected (the source file under `<module>/...`, against the features spec). Once the spec is fixed, regenerate the test from the corrected spec — the fail-fast placeholder is replaced by a normal test (which passes, or becomes an SDK deviation per section 2c if the SDK then diverges), and the **UTS Spec Errors** entry is closed out. Do **not** "resolve" it by rewriting the test to match the broken spec or the SDK — that re-buries the bug the placeholder exists to surface.

**Avoid the accommodate-both pattern.** Tests that accept either the spec behaviour or the SDK behaviour (e.g. try/catch that passes regardless of which path is taken) provide no signal — they pass whether the SDK is compliant or not. Every test should either assert spec behaviour (and fail if non-compliant) or assert the SDK's actual behaviour (and document the deviation). Never both.

### 4. Decision tree

```
Test fails
  |
  +-- Does UTS spec match features spec? (and is it internally consistent?)
  |     |
  |     NO --> UTS SPEC ERROR: fix the spec at source, not the test.
  |     |        Record in deviations (UTS Spec Errors) + emit a fail-fast test pointing there.
  |     |
  |     YES
  |       |
  |       +-- Does test accurately translate UTS spec?
  |             |
  |             NO --> Fix the test
  |             |
  |             YES --> SDK deviation. Env-gated skip or adapted assertion (section 3); record in deviations file
```

---

## Recording deviations

When evaluating against an existing implementation, maintain a deviations file (e.g. `deviations.md`) as the single record of all known issues. Each entry must include:

1. **The spec point** (e.g. RSA4b4)
2. **What the spec says** — quote or paraphrase the features spec
3. **What the SDK does** — concrete observable behaviour
4. **Root cause** (if known) — file, function, mechanism
5. **Test impact** — which test(s) are affected and how each was handled (env-gated skip, adapted assertion, fail-fast, or skipped stub)
6. **Status** *(for an SDK deviation)* — *open bug* (to be fixed) vs *intentional / SDK-wide deviation* (and why it won't be), so it's clear whether an issue should be filed
7. **Resolution** *(once resolved)* — the outcome after the deviation is resolved by analysis or a spec change (e.g. reclassified as a cross-SDK design divergence, or a spec point revised upstream); omit until there is one

Where a suite has recurring *internal-shape* differences (see **Adapted Tests** below), define a short **shape-deviation vocabulary** once — e.g. `S-1…S-n`, as the objects unit suite does in its mapping reference — and cite the tag from each affected entry rather than re-explaining the same structural difference per test.

Deviations are grouped into four sections. **Keep all four headings present in every `deviations.md`, in this order** — and mark an empty category `*(none)*` rather than deleting its heading. This way every entry sits unambiguously under one category, and a reader can tell an empty category (nothing found) from a forgotten one:
- **UTS Spec Errors** — the UTS spec itself is wrong (contradicts the features spec, or is internally inconsistent). The test **fails fast** pointing here (see "Spec-error fail-fast"); the fix belongs in the spec, not the SDK. Unlike the categories below, this is not an SDK problem.
- **Failing Tests** — SDK non-compliance where the spec-correct test is present but skipped (env-gated). These are the primary output — each maps to a potential issue to file.
- **Adapted Tests** — SDK non-compliance where the test asserts the SDK's *actual* behaviour instead of the spec's. It passes, guards against regressions, and documents the deviation. **Whenever the actual behaviour is stable and assertable, prefer this and record the test here** — a running adapted test is worth more than a spec-correct assertion skipped indefinitely. (Reserve *Failing Tests* for deviations you expect to be fixed, where preserving the spec-correct assertion as the target matters.)
- **Mock Infrastructure Limitations** — tests that can't be implemented due to missing mock capabilities (e.g. msgpack support). These are skipped stubs, not SDK deviations — i.e. the case cannot run at all. A sanctioned harness stand-in under which the test runs is not a limitation and belongs in the test file's header comment, not here (see case 4 under *Idiomatic translation vs genuine deviations*).

This file is valuable output. It gives the SDK team a precise catalogue of spec gaps, each with a failing test that can be turned on once the fix lands.

### Idiomatic translation vs genuine deviations

A test that doesn't read word-for-word like the pseudocode is **not** automatically a deviation. Before recording anything, decide which of four situations you're in — only cases 2 and 3 are deviations:

**1. Idiomatic naming / rendering — not a deviation. Just translate it; record nothing.**
The public API is legitimately spelled differently in this language: a different method name, a property or getter where the spec writes a call, an idiomatic enum value (`MapSemantics.LWW` vs the wire string `'lww'`), `toJson()` rendered as `toMap()` / `to_dict()`, or a keyword that must be escaped (`channel.object` → `` channel.`object` `` in Kotlin). This is ordinary translation — see Phase 1 § *Map pseudocode to language idioms*, the naming rules in `writing-test-specs.md` § *Identifier Naming*, and the SDK's own mapping reference (e.g. ably-java's `objects-mapping.md`). The behaviour is identical; only the spelling changed, so there is nothing to record.

**2. Public behaviour differs — a deviation, at any tier.**
The SDK produces an observably different *value or effect* through its public surface — e.g. a different error code (`40106` vs `40160`). Assert the actual behaviour with the spec expectation in a comment (the *adapted assertion* pattern above), or env-gate the spec-correct assertion (a *Failing Test*). This is the ordinary deviation case and applies at unit, integration and proxy tiers alike.

**3. Internal-API shape differs — a deviation, at the unit tier only.**
Some *unit* specs are deliberately white-box: they drive internal classes and methods directly (an internal apply/operation method, the object pool, an internal "update" object). Unlike the public API, internal APIs are **not** standardised across SDKs — a boolean return where the spec models a returned object, an event where it models a return value, a missing accessor — so a white-box unit test adapts to the SDK's internal surface. Two rules keep it honest:
  - **Preserve the coverage** — assert the equivalent *observable* (the resulting object state, the emitted event, the tombstone flag, …). Adapting the *shape* of the check is fine; **dropping** it is not. If an internal difference genuinely removes an observable, that is a real deviation, not an adaptation.
  - **Name recurring differences once** as a shape-deviation vocabulary (`S-1…S-n`) and cite the tag per test, so each entry stays about *that* test rather than re-explaining the mechanism.

**4. Harness/infra substitution — not a deviation; record nothing in the deviations file.**
When a tier deliberately renders the spec's mock infrastructure differently (direct state seeding in place of a mock transport, fake timers where the spec uses real ones, an internal capture seam instead of reading sent frames) and the tests **run and assert the spec's observables**, that is an infra-driving choice, not a deviation. Document it in the test file's header comment (and the SDK's mapping reference, if it has one) — never as a deviations entry. Only when the substitution leaves a case **unable to run** does it become a *Mock Infrastructure Limitation* (a skipped stub).

Because **integration and proxy specs exercise only the public API**, case 3 never applies at those tiers — such a test must not reach into internal APIs to make itself pass. If one appears to need that, it is really case 2 (a public-behaviour deviation) or a translation bug. And never log case 1 (idiomatic naming) or case 4 (a sanctioned infra substitution) as a deviation — the deviations file is for behaviour the SDK gets *wrong*, not for how its API is spelled or how the harness renders the spec's mocks.

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

Not everything in the UTS pseudocode maps 1:1 to every SDK. Before writing tests, verify that the API exists. An API that is merely *named* differently is idiomatic translation — use the SDK's name and move on; there is nothing to record (see [Idiomatic translation vs genuine deviations](#idiomatic-translation-vs-genuine-deviations)). An API that is genuinely *missing* is different: note it — the test may be not-applicable to this SDK, or the absence may itself be a deviation to record.

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
- **For waiting on async event delivery** (mock message propagation, promise settlement): yield to the event loop with a zero-delay mechanism like `setImmediate`, `process.nextTick`, or equivalent. Define a `flushAsync()` helper and use it everywhere instead of `setTimeout(resolve, N)`. This is the rendering of the spec's `process_pending_events()` convention (see `uts/README.md`).
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

**Fake time and poll deadlines collide.** A safety timeout or a `poll_until` helper whose
deadline reads a clock the test's fake timers stub will never expire. This is easy to hit,
because mainstream fake-timer tools fake the wall clock by default (Jest's modern fake timers
and sinon's `useFakeTimers` both mock `Date`): a deadline computed from `Date.now()` freezes
while fake time is installed, so the poll spins until the runner's own timeout kills it with a
generic error instead of the poll's informative one. Two remedies, in order of preference:

1. **Restructure the test so the wall clock never needs stubbing**: backdate a fixture
   timestamp past the period under test instead of advancing a fake "now". For example,
   ably-js's derived RTO10/RTO10b1 GC tests render the spec's `ADVANCE_TIME`
   (`objects/unit/realtime_object.md`) by stamping the tombstone's `serialTimestamp` in the
   past (RTLO6a makes it `tombstonedAt`), so the object is already GC-eligible under the real
   clock and nothing is stubbed.
2. **Have the polling helper's deadline read a monotonic clock** that time stubbing cannot
   touch: `performance.now()` in JavaScript, `System.nanoTime()` on the JVM.

A *synchronous* stub window is exempt: stubbing the clock around a single non-awaiting call and
restoring it in a `finally` never overlaps a poll, so the trap cannot fire. Sometimes it is the
only option — the SDK reads the clock internally and the spec fixture is a fixed epoch, as in
RTLM19's GC-boundary test — and it should then be documented in the test file header (an infra
note per case 4 of *Idiomatic translation vs genuine deviations*, not a deviations-file entry).

### Integration timeouts are wall-clock (beware virtual-time frameworks)

The rule above is inverted for **integration and proxy tests**: every `WITH timeout`,
`poll_until` and `WAIT` in an integration spec is **wall-clock (real) time**, because the test
is waiting on a real server or proxy over a real network.

A spec-written `WAIT n` in an integration spec is **deliberate** — the spec's accompanying
comment says why (e.g. letting the server assign distinct timestamps between publish batches, or
a documented scheduler yield where no observable state exists to poll). Translate it as a real
sleep and carry the spec's comment; the anti-flake "no fixed sleeps" convention bans *invented*
waits used as synchronisation, not spec-mandated ones.

This is a trap in test frameworks that virtualise time by default. For example,
kotlinx-coroutines' `runTest` runs the test body on a virtual clock: a bare `withTimeout(15s)`
wrapping a real network await measures *virtual* time, which fast-forwards the moment the test
coroutine idles — the timeout fires almost instantly, long before the server can respond, with
a misleading "Timed out after 15s" error. The same applies to a bare `delay()`, which skips
instead of waiting.

Derived integration tests in such frameworks must run their waits against the real clock —
e.g. dispatch onto a real-thread dispatcher before applying the timeout
(`withContext(Dispatchers.Default.limitedParallelism(1)) { withTimeout(...) { ... } }` in
Kotlin), or use the framework's escape hatch for real time. Define shared helpers
(`awaitState`, `pollUntil`, `withRealTimeout`, ...) that encapsulate this once, and use them for
every wait in integration test bodies. Unit tests are unaffected — there, fake/virtual timers
remain the preferred mechanism.

### Cleanup with afterEach

Always restore mocks in `afterEach`, not just at the end of each test. If a test throws before its cleanup code, the next test inherits dirty state. Use the SDK's mock restoration mechanism (e.g. `restoreAll()`) in an `afterEach` hook.

The cleanup mechanism should cancel all SDK-internal timers, not just those reachable via the SDK's public API. Some SDKs have bugs where internal timers are orphaned (e.g. timer handles overwritten without cancelling the previous one). The test infrastructure should track all timer allocations and cancel any that survive `client.close()`.
