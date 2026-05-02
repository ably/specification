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

### Avoiding Flaky Tests

- Use polling with timeouts instead of fixed waits (see `README.md` polling conventions)
- For token expiry tests, use short TTLs and poll for rejection
- For state transition assertions, wait for the target state event rather than asserting after a delay
- Proxy tests should use proxy event logs for verification rather than timing-dependent assertions

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
