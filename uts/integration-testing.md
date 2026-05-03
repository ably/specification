# Integration Testing Policy

This document defines the policy for integration tests in the UTS test suite. It covers what to test, how tests are organised, and the distinction between direct sandbox tests and proxy-based tests.

## Relationship to Unit Tests

Unit tests use mocked transports (MockWebSocket, MockHttpClient) to verify client-side logic: state machines, request formation, response parsing, timer behaviour, error handling. They are fast and deterministic.

Integration tests verify that the SDK interoperates correctly with the real Ably service. They run against the Ably sandbox and exercise the actual network path.

**Integration tests do not replace unit tests.** Every spec point that has an integration test should also have a unit test. The integration test adds confidence that the mocked behaviour in the unit test matches reality.

## What to Test

Integration tests should cover spec points where correctness depends on agreement between client and server. Not every spec point needs an integration test — only those where a unit test alone leaves meaningful doubt.

### Selection Criteria

Choose spec points for integration testing when they fall into one or more of these categories:

#### 1. Request/Response Shape Interop

The SDK constructs a request (HTTP or protocol message) and the server must accept it, or the server sends a response and the SDK must parse it correctly.

Examples:
- Auth token obtained via `createTokenRequest` is accepted by the server (RSA9)
- WebSocket connection URL parameters are accepted (RTN2)
- Channel attach/detach protocol messages round-trip correctly (RTL4, RTL13)
- Publish with various data types round-trips through the server (RSL1, RTL6)

#### 2. Error Response Interop

The server rejects invalid requests with specific error codes, and the SDK must surface those errors correctly.

Examples:
- Invalid API key produces the correct error code and state transition (RTN14b)
- Token expiry triggers renewal flow (RSA4b)
- Insufficient capability produces channel FAILED (RTL4e)

#### 3. Data Encoding Round-Trips

Data passes through the SDK's encoding layer, through the server, and back. The round-trip must preserve data integrity.

Examples:
- String, binary, and JSON data types are preserved through publish/subscribe (RSL4, RSL6)
- Presence data encoding round-trips (RTP8)
- Message extras survive the round-trip

#### 4. Stateful Protocol Sequences

Multi-step interactions where the server's state machine and the client's state machine must agree.

Examples:
- Connection resume after disconnect (RTN15) — proxy required
- Presence SYNC protocol (RTP2) — server-initiated, can't be mocked faithfully
- Channel reattach after server-initiated detach (RTL13) — proxy required
- Heartbeat timeout detection (RTN23) — proxy required to starve heartbeats

### What NOT to Test

Do not write integration tests for:
- Pure client-side logic (option parsing, state machine transitions that don't depend on server responses)
- Behaviour that is fully exercised by unit tests with high confidence (e.g. event emitter semantics, channel name validation)
- Timing-sensitive retry logic where the integration test would be flaky without the proxy
- Features that require server-side configuration not available in the sandbox

## Directory Structure

Integration test specs are organised to mirror the unit test structure:

```
realtime/
  unit/                                    # Unit tests (mock transport)
    auth/
      connection_auth_test.md
      realtime_authorize_test.md
    channels/
      channel_attach_test.md
      channel_publish_test.md
      ...
    connection/
      auto_connect_test.md
      connection_failures_test.md
      ...
    presence/
      realtime_presence_enter_test.md
      ...
  integration/                             # Direct sandbox tests (no proxy)
    auth/
      connection_auth_test.md
      realtime_authorize_test.md
    channels/
      channel_attach_test.md
      channel_publish_test.md
      ...
    connection/
      connection_lifecycle_test.md
      ...
    presence/
      presence_lifecycle_test.md
      ...
  integration-proxy/                       # Proxy-based tests (sandbox + proxy)
    connection/
      connection_resume_test.md
      connection_failures_test.md
      heartbeat_test.md
    channels/
      channel_faults_test.md
      ...
```

### Segregation Rationale

Tests that require the proxy are segregated into `integration-proxy/` because:

1. **Different infrastructure requirements** — proxy tests need the proxy binary running, port allocation, and proxy session lifecycle management. Direct sandbox tests need only network access to the sandbox.
2. **Different CI configuration** — proxy tests can run on a different schedule or be gated on proxy availability, without affecting direct integration tests.
3. **Different failure modes** — proxy test failures may indicate proxy bugs, port conflicts, or proxy/SDK version mismatches, not just SDK issues.
4. **Clear authoring signal** — when writing a test, the file location encodes whether the proxy is needed. No conditional skip logic inside test files.

### Shared Spec Points

A single spec point may have tests in multiple tiers. For example, RTN15 (connection resume):

- `unit/connection/connection_failures_test.md` — mock transport verifies client-side state transitions and retry logic
- `integration-proxy/connection/connection_resume_test.md` — proxy verifies the resume protocol works against the real server

This is expected and correct. The unit test verifies client logic; the integration test verifies client-server agreement.

## Test Structure Conventions

### Sandbox Setup

Every integration test file includes the standard sandbox provisioning:

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

### Proxy Setup (integration-proxy only)

Proxy tests additionally set up a proxy session per test or group of tests. See `realtime/integration/helpers/proxy.md` for the proxy infrastructure API.

```pseudo
BEFORE EACH TEST:
  session = create_proxy_session(
    endpoint: "sandbox",
    port: allocated_port,
    rules: [ ...initial rules... ]
  )

AFTER EACH TEST:
  session.close()
```

### Client Options

Integration test clients use:

```pseudo
client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",          # Direct sandbox tests
  useBinaryProtocol: false,
  autoConnect: false
))
```

Proxy test clients use:

```pseudo
client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))
```

### Channel Names

Channel names must be unique per test to avoid cross-test interference:

```pseudo
channel_name = "test-RTL4-attach-${base64(random_bytes(6))}"
```

### Spec Point References

Each test section references the spec points it covers, just like unit tests:

```pseudo
## RTN4b - Successful connection establishment

| Spec | Requirement |
|------|-------------|
| RTN4b | Connection transitions INITIALIZED → CONNECTING → CONNECTED |
```

### Timeout Strategy

Integration tests interact with real services over real networks, so timeouts need more thought than unit tests. Apply two levels of timeout:

**Suite timeout** — the mocha `this.timeout()` on the `describe` block. This must accommodate the sum of all tests in the suite plus setup and teardown. For suites with many tests or slow sandbox operations, 120 seconds is a reasonable default. Suites with only 1–3 fast tests can use 30–60 seconds.

**Operation timeout** — individual operations that may hang (HTTP requests, WebSocket state waits, sandbox provisioning/teardown) should each have their own timeout, shorter than the suite timeout. This ensures a single stuck operation produces a clear error message rather than silently consuming the suite budget until mocha kills the entire suite with a generic "timeout exceeded."

Guidelines:

- Sandbox provisioning and teardown HTTP requests: 30 seconds (via `AbortSignal.timeout()` or equivalent). Sandbox teardown (app deletion) should be best-effort — catch and ignore timeout errors, since sandbox apps auto-expire.
- `connectAndWait`, `closeAndWait`, channel attach waits: 10–15 seconds.
- Proxy tests with `realtimeRequestTimeout` set low (e.g. 3 seconds for timeout tests): give the suite timeout at least `realtimeRequestTimeout + 12 seconds` headroom per such test.
- `pollUntil` calls: explicit timeout parameter, typically 10–30 seconds.

The goal is: every await in the test is bounded, and the suite timeout is generous enough that it only fires if something truly unexpected happens. When a test fails, the error should say *what* timed out, not just "suite timeout exceeded."

### Avoiding Flaky Tests

- Use polling with timeouts instead of fixed waits (see `README.md` polling conventions)
- For token expiry tests, use short TTLs and poll for rejection
- For state transition assertions, wait for the target state event rather than asserting after a delay
- Proxy tests should use proxy event logs for verification rather than timing-dependent assertions
- When tests pass in isolation but fail in the full suite, suspect sandbox rate limiting or connection exhaustion — increase the suite timeout rather than adding retries

## Writing Proxy Tests

The proxy mediates between the SDK and the real Ably server. It is not a mock server. Tests should be written to rely on actual server responses as much as possible, with the proxy intervening only where necessary to create the specific fault or error condition under test.

The more a proxy constructs or replaces server responses, the more likely it is that the test exercises a scenario that diverges from real server behaviour. This undermines the value of integration testing over unit testing.

### Prefer Late Fault Injection

Wherever possible, structure tests so that the fault injected by the proxy occurs as the **final interaction** between client and server, with the test verifying the client's behaviour in response. All preceding interactions should pass through to the real server unmodified, establishing genuine client and server state.

For example, to test that the SDK handles a connection-level ERROR correctly:
1. Let the real connection handshake complete through the proxy (real CONNECTED from server).
2. After the SDK is connected, use the proxy to inject or trigger the error condition.
3. Assert that the SDK transitions to the correct state.

This maximises the proportion of the test that exercises real client-server interaction.

### When Earlier Fault Injection Is Needed

Sometimes the fault must occur at an earlier point — for example, replacing the server's response to the first CONNECTED, or suppressing an ATTACH before it reaches the server. When this is unavoidable, there are two approaches, each with a trade-off:

**Approach A: Modify the server's response.** The proxy forwards the request to the server, receives the real response, but modifies it before forwarding to the client. The server believes the operation succeeded; the client sees an error.

**Approach B: Handle the request without forwarding.** The proxy intercepts the request, generates a response itself, and never forwards to the server. Client and server state remain consistent (both believe the operation did not happen), but the response is entirely synthetic.

**Prefer Approach A** (modify real server responses) when the resulting client-server state drift does not affect the validity of subsequent actions or assertions in the test. This preserves the integration testing value: the response structure, timing, and ancillary fields come from the real server, with only the specific fault injected.

Use Approach B only when the state drift from Approach A would invalidate later parts of the test — for example, if the server's belief that a channel is attached would cause it to send unsolicited messages that interfere with subsequent assertions.

### Example: Simulating a Rejected Attach

To test that the SDK handles a channel attach rejection correctly, after a successful real connection:

**Approach A (preferred):** The proxy forwards the ATTACH to the server, receives the real ATTACHED response, but replaces it with an ERROR before forwarding to the client. The server now believes the channel is attached, but the client sees FAILED. This is acceptable when the test ends here — the state drift doesn't matter because there are no subsequent server interactions that depend on consistent channel state.

**Approach B:** The proxy intercepts the ATTACH, does not forward it, and generates an ERROR response. Client and server agree the channel is not attached. But the error response is entirely synthetic — we might as well have written a unit test.

### Implications for Test Design

This principle influences test structure:

- **Keep proxy tests focused.** Each test should verify one fault condition. Avoid multi-phase tests where an early proxy intervention creates state drift that compounds through later phases.
- **Use imperative actions for late injection.** The proxy's imperative action API (`trigger_action`) is ideal for injecting faults after the SDK has reached a stable state through real server interaction.
- **Use rules for response modification.** When a rule must fire during the protocol handshake (e.g., replacing the CONNECTED response), use `times: 1` so the proxy returns to passthrough for subsequent interactions.
- **Verify via proxy event logs.** Assert against the proxy's event log to confirm that the expected real server interactions occurred, rather than relying solely on SDK state.

## Coverage Tracking

Integration test coverage is tracked in `completion-status.md` alongside unit test coverage. Each spec point entry indicates which tiers have coverage:

```
RTN4b  unit:✓  integration:✓
RTN15a unit:✓  integration-proxy:✓
RTL4   unit:✓  integration:✓
```

## Adding New Integration Tests

1. **Check whether an integration test adds value** — apply the selection criteria above. If the unit test already provides high confidence, skip the integration test.
2. **Choose the right tier** — if the test needs fault injection (dropped connections, delayed frames, modified responses), it goes in `integration-proxy/`. Otherwise, `integration/`.
3. **Mirror the unit test structure** — use the same category directory and a similar file name.
4. **Write the UTS spec first** — just like unit tests, the portable test spec comes before the language-specific implementation.
5. **Reference spec points** — every test section must cite the spec points it covers.
