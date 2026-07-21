# Universal Test Specifications (UTS)

Portable test specifications for Ably client library implementations. Each spec defines what to test in language-neutral pseudocode, which is then translated into runnable tests for each SDK.

## Directory Structure

```
uts/
├── rest/
│   ├── unit/                          # REST unit tests (mocked HTTP)
│   │   ├── helpers/
│   │   │   └── mock_http.md           # Mock HTTP infrastructure spec
│   │   ├── auth/                      # RSA — authentication
│   │   ├── channel/                   # RSL — channel operations
│   │   ├── encoding/                  # RSL4/RSL6 — message encoding
│   │   ├── presence/                  # RSP — REST presence
│   │   ├── push/                      # RSH — push admin
│   │   └── types/                     # T* — type definitions
│   └── integration/                   # REST integration tests (Ably sandbox)
├── realtime/
│   ├── unit/                          # Realtime unit tests (mocked WebSocket)
│   │   ├── helpers/
│   │   │   ├── mock_websocket.md      # Mock WebSocket infrastructure spec
│   │   │   └── mock_vcdiff.md         # Mock VCDiff decoder spec
│   │   ├── auth/                      # RSA/RTC8 — realtime auth
│   │   ├── channels/                  # RTL/RTS — channels and messages
│   │   ├── client/                    # RTC — realtime client
│   │   ├── connection/                # RTN — connection management
│   │   └── presence/                  # RTP — realtime presence
│   └── integration/                   # Realtime integration tests
│       ├── proxy/                     # Proxy-based fault injection tests
│       └── *.md                       # Direct sandbox tests
├── docs/                              # Guides and reference
│   ├── writing-test-specs.md          # How to write UTS specs
│   ├── writing-derived-tests.md       # How to translate specs into SDK tests
│   ├── integration-testing.md         # Integration testing policy
│   ├── proxy.md                       # Proxy infrastructure spec (cross-module)
│   └── completion-status.md           # Spec coverage matrix
└── README.md                          # This file
```

## Spec File Counts

| Category | Count | Description |
|----------|-------|-------------|
| REST unit | 40 | Mocked HTTP client tests |
| REST integration | 11 | Ably sandbox tests |
| Realtime unit | 54 | Mocked WebSocket tests |
| Realtime integration (direct) | 13 | Direct sandbox tests |
| Realtime integration (proxy) | 7 | Fault injection via Go proxy |
| Helper specs | 4 | Mock infrastructure definitions |
| **Total** | **129** | |

## Three Test Tiers

**Unit tests** use mocked transports (MockHttpClient, MockWebSocket) to verify client-side logic: state machines, request formation, response parsing, timer behaviour, error handling. They are fast and deterministic.

**Integration tests** (direct) run against the Ably sandbox to verify that the SDK interoperates correctly with the real service. No fault injection — these test happy-path behaviour and real error responses.

**Integration tests** (proxy) run against the Ably sandbox through a programmable Go proxy that can inject faults: connection drops, suppressed frames, replaced responses, HTTP error injection. These test behaviour that can't be verified without controlling the network path.

## Pseudocode Conventions

Test specs use a consistent pseudocode syntax:

```pseudo
# Setup
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, {"result": "ok"})
)
install_mock(mock_http)
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# Test
result = AWAIT client.operation()

# Assertions
ASSERT result.field == "ok"
ASSERT request.url.path == "/channels/" + encode_uri_component(name) + "/messages"

# Error testing
AWAIT client.badOperation() FAILS WITH error
ASSERT error.code == 40160

# State transitions
AWAIT_STATE client.connection.state == ConnectionState.connected
```

Pseudocode maps to language idioms rather than prescribing exact syntax:

- **Absent values**: `== null` means the language-appropriate "absent" value — `undefined` in
  JavaScript, `null` in Java/Kotlin/Swift. Assertions like `ASSERT x.value() == null` are
  satisfied by `undefined` in SDKs where that is the idiomatic absent value.
- **Property access**: member access written as a call (e.g. `instance.id()`) is satisfied by a
  property or getter (`instance.id`) where the SDK's feature spec defines the member as a
  property (e.g. `Instance#id`, RTINS3).
- **Enum values**: a symbolic enum value in pseudo-code (e.g. `"LWW"` for
  `ObjectsMapSemantics.LWW`, wire-encoded as an integer per OMP2) is satisfied by the SDK's
  idiomatic public rendering of that enum member — the enum member itself in typed SDKs
  (`MapSemantics.LWW` in ably-java), or a string-literal union value in ably-js (`'lww'`).
- **`poll_until_success(condition)`**: a `poll_until` (interval 500ms, timeout 10s) that keeps
  polling until the condition succeeds — returns a truthy result without raising. Any error raised by
  the condition — not-found for a not-yet-visible write, or a transient service/network error —
  means "keep polling" rather than failure; if the timeout expires, the most recent error is
  raised so the failure stays diagnosable (a plain timeout error if the condition never raised).
  Use only where an error genuinely means "not ready yet", e.g. reads of the eventually-consistent
  message store (`getMessage`, `getMessageVersions`, `annotations.get`), or LiveObjects value
  reads polled across a fault-injection/recovery window, where the channel is transiently
  DETACHED and reads raise by design; where an error should fail the test, use `poll_until`.
  Implementations typically provide this as a shared helper wrapping their `poll_until`
  (e.g. `pollUntilSuccess` in ably-js); the reference definition lives in
  [docs/writing-test-specs.md](docs/writing-test-specs.md).
- **`flush_async()`**: drain pending event-loop work (microtasks and zero-delay callbacks)
  without any real delay — used at unit tier to let mock events propagate before asserting,
  especially for negative assertions ("nothing happened"). Never rendered as a timed sleep;
  implementations define a shared helper (e.g. `flushAsync()` in ably-js, awaiting a
  `setImmediate`) — see the timer guidance in
  [docs/writing-derived-tests.md](docs/writing-derived-tests.md).
- **Language-inapplicable inputs**: a test input that cannot be constructed in a given language
  (e.g. a non-string map key in JavaScript, where object keys are always coerced to strings; or a
  `null` argument where the SDK's signature makes null indistinguishable from "omitted") makes
  that test — or that table row — not applicable to that SDK. Such omissions are sanctioned and
  should be noted in the derived test file rather than counted as coverage gaps.

See [docs/writing-test-specs.md](docs/writing-test-specs.md) for the full pseudocode reference, mock patterns, and conventions.

## Guides

- **[Writing Test Specs](docs/writing-test-specs.md)** — How to author UTS specs: mock patterns, pseudocode conventions, proxy test structure, common mistakes
- **[Writing Derived Tests](docs/writing-derived-tests.md)** — How to translate UTS specs into SDK-specific tests, diagnose failures, and record deviations
- **[Integration Testing Policy](docs/integration-testing.md)** — When to write integration vs unit tests, proxy test design principles, test structure conventions
- **[Completion Status](docs/completion-status.md)** — Coverage matrix tracking which spec items have UTS test specs

## Go Test Proxy

The programmable proxy for integration testing lives in a separate repository: [ably/uts-proxy](https://github.com/ably/uts-proxy). It sits between the SDK and the Ably sandbox, transparently forwarding traffic while allowing rule-based fault injection.

See `uts/docs/proxy.md` for the proxy infrastructure specification used by test specs in this repository.
