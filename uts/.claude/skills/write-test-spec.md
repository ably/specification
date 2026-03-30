---
skill: write-test-spec
description: Guidelines for writing Ably SDK test specifications with modern mock infrastructure patterns
tags: [testing, specifications, ably]
---

# Writing Ably SDK Test Specifications

This skill provides comprehensive guidance for writing portable test specifications for Ably SDK implementations.

## Test Types

### Unit Tests (Mocked HTTP/WebSocket)
- Use mock HTTP client to verify request formation and response parsing
- Use mock WebSocket client for Realtime connection tests
- Test client-side validation and error handling
- Token strings are opaque - any arbitrary string works for unit tests
- No network calls - fast and deterministic

### Integration Tests (Ably Sandbox)
- Run against `https://sandbox.realtime.ably-nonprod.net`
- Provision apps via `POST /apps` with body from `ably-common/test-resources/test-app-setup.json`
- Use `endpoint: "sandbox"` in ClientOptions

## Mock Infrastructure Patterns

### HTTP Mock Infrastructure

**Reference the canonical specification:**
```markdown
## Mock HTTP Infrastructure

See `uts/test/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.
```

**Key interfaces:**
```pseudo
interface MockHttpClient:
  await_connection_attempt(timeout?: Duration): Future<PendingConnection>
  await_request(timeout?: Duration): Future<PendingRequest>
  reset()

interface PendingConnection:
  host: String
  port: Int
  tls: Boolean
  respond_with_success()
  respond_with_refused()
  respond_with_timeout()
  respond_with_dns_error()

interface PendingRequest:
  url: URL
  method: String
  headers: Map<String, String>
  body: Bytes
  respond_with(status: Int, body: Any, headers?: Map<String, String>)
  respond_with_delay(delay: Duration, status: Int, body: Any)
  respond_with_timeout()
```

### Handler-Based Pattern (Simple Tests)

Use for tests with predetermined responses:

```pseudo
captured_request = null

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_request = req
    req.respond_with(200, {"time": 1234567890000})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Handler-Based with State (Complex Tests)

Use for tests needing different responses based on request count or conditions:

```pseudo
request_count = 0
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    request_count++
    IF request_count == 1:
      req.respond_with(401, {"error": {"code": 40142}})
    ELSE:
      req.respond_with(200, {"result": "success"})
  }
)
install_mock(mock_http)
```

### Await-Based Pattern (Advanced Control)

Use when test needs to coordinate responses with test execution state.

**Important:** The await pattern has a subtle timing requirement - when awaiting multiple sequential connection attempts, you must set up the await for the next attempt BEFORE responding to the current one:

```pseudo
# Correct pattern for sequential awaits
first_conn = AWAIT mock_ws.await_connection_attempt()
second_future = mock_ws.await_connection_attempt()  # Set up BEFORE responding
first_conn.respond_with_error(...)  # This triggers retry
second_conn = AWAIT second_future
```

This avoids race conditions where the retry happens before the await is set up.

### When to Use Each Pattern

**Handler pattern** (recommended for most tests):
- Response is predetermined based on request count or content
- Simple "first attempt fails, second succeeds" scenarios
- No need to coordinate with external test state
- More universally safe across different language runtimes

**Await pattern** (for advanced scenarios only):
- Need to inspect connection/request details before deciding how to respond
- Test logic depends on external state not known at setup time
- Complex coordination between multiple async operations

Example using await pattern:

```pseudo
mock_http = MockHttpClient()
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "..."))

# Start operation
request_future = client.time()

# Wait for and handle connection
connection = AWAIT mock_http.await_connection_attempt()
connection.respond_with_success()

# Wait for and handle request
request = AWAIT mock_http.await_request()
ASSERT request.headers["X-Ably-Version"] IS NOT null
request.respond_with(200, {"time": 1234567890000})

# Complete operation
result = AWAIT request_future
```

### WebSocket Mock Infrastructure

For Realtime tests, reference the WebSocket mock:

```markdown
## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.
```

**Key interfaces:**
```pseudo
interface MockWebSocket:
  events: List<MockEvent>  # Unified timeline
  await_connection_attempt(timeout?: Duration): Future<PendingConnection>
  await_request(timeout?: Duration): Future<PendingRequest>
  send_to_client(message: ProtocolMessage)
  send_to_client_and_close(message: ProtocolMessage)  # Send then close
  simulate_disconnect()  # Close without message
  reset()

interface PendingConnection:
  host: String
  port: Int
  tls: Boolean
  respond_with_success()
  respond_with_refused()
  respond_with_timeout()
  respond_with_dns_error()
```

### WebSocket Connection Closing Semantics

When simulating server behavior, use the correct method based on the scenario:

| Scenario | Method | Description |
|----------|--------|-------------|
| Server sends DISCONNECTED | `send_to_client_and_close()` | Server sends message then closes connection |
| Server sends ERROR (connection-level) | `send_to_client_and_close()` | ERROR without channel = fatal, closes connection |
| Server sends ERROR (channel-level) | `send_to_client()` | ERROR with channel = attachment failure, connection stays open |
| Server sends CONNECTED, HEARTBEAT, ACK, MESSAGE | `send_to_client()` | Normal messages, connection stays open |
| Unexpected transport failure | `simulate_disconnect()` | Connection drops without server message |

**Key rule:** Whenever the server sends DISCONNECTED, or ERROR without a specified channel, it will be accompanied by the server closing the WebSocket connection. An ERROR with a specified channel is an attachment failure and doesn't end the connection.

```pseudo
# Server-initiated disconnection (e.g., token expired)
mock_ws.active_connection.send_to_client_and_close(ProtocolMessage(
  action: DISCONNECTED,
  error: ErrorInfo(code: 40142, message: "Token expired")
))

# Connection-level error (fatal)
mock_ws.active_connection.send_to_client_and_close(ProtocolMessage(
  action: ERROR,
  error: ErrorInfo(code: 40101, message: "Invalid credentials")
))

# Channel attachment error (non-fatal, connection stays open)
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ERROR,
  channel: "private-channel",
  error: ErrorInfo(code: 40160, message: "Not permitted")
))

# Normal message (connection stays open)
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: CONNECTED,
  connectionId: "connection-id",
  connectionKey: "connection-key"
))

# Unexpected disconnect (no message, just closes)
mock_ws.active_connection.simulate_disconnect()
```

## Spec Requirement Summaries

**Every test must include a spec requirement summary immediately after the heading.**

### Single Spec Format

```markdown
## RSC7e - X-Ably-Version header

**Spec requirement:** All REST requests must include the `X-Ably-Version` header with the spec version.

Tests that all REST requests include the `X-Ably-Version` header.
```

### Multiple Specs Format (Use Table)

```markdown
## RSC7d, RSC7d1, RSC7d2 - Ably-Agent header

| Spec | Requirement |
|------|-------------|
| RSC7d | All requests must include Ably-Agent header |
| RSC7d1 | Header format: space-separated key/value pairs |
| RSC7d2 | Must include library name and version |

Tests that all REST requests include the `Ably-Agent` header with correct format.
```

## Pseudocode Conventions

### Type Assertions

Type assertions verify object types/interfaces. Implementation varies by language:

- **Strongly typed** (Dart, Swift, Kotlin, TypeScript): Use native type checks
- **Weakly typed** (JavaScript, Python, Ruby): Verify expected methods/properties exist

```pseudo
# Pseudocode
ASSERT client.connection IS Connection

# JavaScript - check interface compliance
assert(typeof client.connection.connect === 'function');
assert(typeof client.connection.close === 'function');

# Dart - native type check
expect(client.connection, isA<Connection>());
```

### State Transitions

State transitions may be synchronous or asynchronous. Use `AWAIT_STATE`:

```pseudo
# If already in state, proceed immediately
# Otherwise wait for state change event until condition is met
AWAIT_STATE client.connection.state == ConnectionState.connecting
```

This means implementations should:
- Check if condition is already true → proceed
- Otherwise wait for state change events with timeout
- Fail if timeout expires

## Timer Mocking

Tests verifying timeout behavior should use timer mocking where practical to avoid slow tests.

**Approaches (in order of preference):**

1. **Mock/fake timers** (JavaScript Jest, Python freezegun)
   ```pseudo
   enable_fake_timers()
   request_future = client.time()
   ADVANCE_TIME(1000)  # Instantly trigger timeout
   AWAIT request_future  # Should fail with timeout
   ```

2. **Dependency injection** (Go, Swift, Kotlin)
   - Library accepts clock interface in tests
   - Test provides controllable implementation

3. **Short timeouts** (fallback if mocking unavailable)
   ```pseudo
   client = Rest(options: ClientOptions(httpRequestTimeout: 50))
   ```

4. **Actual delays** (last resort)

Use `ADVANCE_TIME(milliseconds)` in pseudocode to indicate time progression.

## Sandbox App Management

Create apps **once** per test run, **explicitly delete** when complete:

```pseudo
BEFORE ALL TESTS:
  app_config = POST https://sandbox.realtime.ably-nonprod.net/apps
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox.realtime.ably-nonprod.net/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

## Unique Channel Names

Construct channel names with:
1. **Descriptive part** - test name or spec ID
2. **Random part** - base64-encoded random bytes (e.g., 6 bytes = 48 bits)

Example: `test-RSL1-publish-${base64(random_bytes(6))}`

Tests using channels should use uniquely-named channels to avoid:
- Collisions between concurrent tests
- Server-side side-effects from previous test runs
- State leakage between test cases

## Authentication Testing

### Do NOT use `time()` for auth testing

The `/time` endpoint does NOT require authentication (RSC16). Using it for auth tests will give misleading results.

**Key behaviors of `time()`:**
- Does not send Authorization header, even when client has credentials
- Works over non-TLS connections (RSC18 doesn't apply)
- Does not trigger token acquisition

**Use `channel.status()` instead** for testing authentication:
```pseudo
# For auth tests, use channel status which requires authentication
status = AWAIT client.channels.get("test").status()

# Verify auth header was sent
ASSERT request.headers["Authorization"] == "Bearer token"
```

### Constructor still requires authentication credentials

While `time()` doesn't require auth, the **client constructor still requires credentials**. You must provide one of:
- `key` (API key)
- `authCallback`
- `authUrl`  
- `token` or `tokenDetails`

**Wrong - constructor will reject:**
```pseudo
# This fails with 40106 "No authentication method provided"
client = Rest(options: ClientOptions(tls: false))
```

**Correct - provide credentials, but time() won't use them:**
```pseudo
# Constructor accepts credentials, time() doesn't send them
client = Rest(options: ClientOptions(key: "app.key:secret"))
result = AWAIT client.time()
ASSERT "Authorization" NOT IN request.headers  # time() doesn't send auth
```

### RSC18 only applies to Basic auth configurations

The RSC18 restriction (no Basic auth over non-TLS) is checked at **client construction time**. The error is thrown immediately when creating a client that would use Basic auth over non-TLS.

**RSC18 check triggers when:**
- API key is provided AND
- `tls: false` AND
- No `clientId` (which would force token auth) AND
- No `useTokenAuth: true` AND
- No authCallback/authUrl/token

**Testing RSC18:**
```pseudo
# RSC18 test - Basic auth over HTTP rejected at construction
TRY:
  client = Rest(options: ClientOptions(key: "app.key:secret", tls: false))
  FAIL("Expected exception at construction")
CATCH AblyException as e:
  ASSERT e.code == 40103

# Token auth over HTTP allowed - client can be constructed
client = Rest(options: ClientOptions(token: "token", tls: false))
status = AWAIT client.channels.get("test").status()  # Works fine
ASSERT request.url.scheme == "http"
ASSERT request.headers["Authorization"] == "Bearer token"
```

**Why `time()` works over non-TLS with any client:**
Since `time()` uses `authenticated: false`, it never sends credentials, so RSC18 doesn't apply to it. A client configured for Basic auth can still call `time()` - it just can't make authenticated requests.

## Token Testing

Test with **both** token formats:
1. **JWTs** (primary) - Use a third-party JWT library for integration tests
2. **Ably native tokens** - Obtained via `requestToken()`

For unit tests, any string works as a token value since tokens are opaque to the library.

## Avoiding Flaky Tests

**Never use fixed WAITs or arbitrary real-time delays.**

```pseudo
# Bad - flaky
WAIT 5 seconds
ASSERT condition

# Bad - arbitrary delay that may not be enough (or may be too slow)
ADVANCE_TIME(3000)
WAIT 100ms  # Real-time delay - flaky!
ASSERT state == disconnected

# Good - poll until condition
poll_until(
  condition,
  interval: 500ms,
  timeout: 10s
)

# Good - advance time and wait for state
ADVANCE_TIME(3000)
AWAIT_STATE state == disconnected
```

### Verifying Transient States (Record-and-Verify Pattern)

**When testing disconnect/reconnect behavior, always use the record-and-verify pattern.** Do not use intermediate `AWAIT_STATE` calls to observe transient states like DISCONNECTED or SUSPENDED mid-test. The Ably spec mandates immediate reconnection on unexpected disconnect (RTN15a), which means transient states pass too quickly to be reliably observed between test steps.

**The pattern:**

1. Start recording state changes before triggering the behavior
2. Let the full cycle play out (disconnect → reconnect)
3. Assert the recorded sequence at the end with `CONTAINS_IN_ORDER`

```pseudo
# 1. Record state changes
state_changes = []
client.connection.on((change) => {
  state_changes.append(change.current)
})

# 2. Trigger disconnect and let cycle complete
ws_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# 3. Verify the full sequence at the end
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.disconnected,
  ConnectionState.connecting,
  ConnectionState.connected
]
```

**`CONTAINS_IN_ORDER` semantics:** This assertion verifies that the listed states appear in the recorded sequence in the correct order, but does not require them to be the *only* states present. This allows for implementation-specific intermediate states (e.g., additional CONNECTING states between retries) without causing false failures.

**Why NOT intermediate `AWAIT_STATE`:**

```pseudo
# BAD - unreliable, DISCONNECTED may pass before this line executes
ws_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.disconnected  # May miss it!
ADVANCE_TIME(6000)
AWAIT_STATE client.connection.state == ConnectionState.connected

# GOOD - record everything, verify at the end
state_changes = []
client.connection.on((change) => { state_changes.append(change.current) })
ws_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.connected
ASSERT state_changes CONTAINS_IN_ORDER [disconnected, connecting, connected]
```

### Time-Advancement Loops for Retry Scenarios

When tests involve multiple retries with fake timers (e.g., reconnection attempts that fail before eventually succeeding, or waiting for TTL expiry), use a **time-advancement loop** rather than calculating exact `ADVANCE_TIME` durations. This is more robust because:

- The exact timing of retries, backoff, and state transitions is implementation-dependent
- A loop naturally accommodates varying numbers of retries
- It mirrors what the real-world clock does: time passes continuously, not in exact jumps

```pseudo
enable_fake_timers()

# Trigger disconnect, then advance time in increments
# until the client reconnects or we give up
ws_connection.simulate_disconnect()

LOOP up to 15 times:
  ADVANCE_TIME(2500)
  IF client.connection.state == ConnectionState.connected:
    BREAK

AWAIT_STATE client.connection.state == ConnectionState.connected
```

Use this pattern when:
- Reconnection attempts may fail multiple times before succeeding
- The test needs to advance through multiple retry/backoff cycles
- State transitions depend on cumulative elapsed time (e.g., `connectionStateTtl` expiry triggering SUSPENDED)

The final `AWAIT_STATE` after the loop acts as a safety net in case the loop iterations weren't quite enough.

## Test Structure

Each test should have three sections:

### Setup
```pseudo
request_count = 0
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    request_count++
    req.respond_with(200, {...})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.operation()
```

### Assertions
```pseudo
ASSERT result.field == expected
ASSERT request_count == 1
ASSERT captured_requests[0].headers["Authorization"] == "Bearer token"
```

## Common Mock Patterns

### Capturing All Requests

```pseudo
captured_requests = []

onRequest: (req) => {
  captured_requests.append(req)
  req.respond_with(200, {...})
}
```

### Different Responses by Count

```pseudo
request_count = 0

onRequest: (req) => {
  request_count++
  IF request_count == 1:
    req.respond_with(500, {...})
  ELSE:
    req.respond_with(200, {...})
}
```

### Different Responses by URL

```pseudo
onRequest: (req) => {
  IF req.url.path CONTAINS "/time":
    req.respond_with(200, {"time": ...})
  ELSE IF req.url.path CONTAINS "/channels":
    req.respond_with(200, [...])
}
```

### Connection-Level Failures

```pseudo
connection_count = 0

onConnectionAttempt: (conn) => {
  connection_count++
  IF connection_count == 1:
    conn.respond_with_refused()  # Or timeout, dns_error
  ELSE:
    conn.respond_with_success()
}
```

## Common Assertion Patterns

```pseudo
ASSERT value == expected
ASSERT value IS Type
ASSERT value IN list
ASSERT value matches pattern "regex"
ASSERT "key" IN object
ASSERT "key" NOT IN object
ASSERT value STARTS WITH "prefix"
ASSERT value CONTAINS "substring"
```

## Error Testing Pattern

Use the `FAILS WITH error` pattern to test operations that should fail. This pattern:
- Explicitly ties the error to the specific operation that caused it
- Is language-agnostic (works for exceptions, Result types, error returns, etc.)
- Focuses on ErrorInfo fields rather than exception type names

```pseudo
# Synchronous operation that fails
client.channels.get("channel", invalidOptions) FAILS WITH error
ASSERT error.code == 40000

# Async operation that fails
AWAIT client.auth.authorize(invalidParams) FAILS WITH error
ASSERT error.code == 40160
ASSERT error.statusCode == 401
```

**Do NOT use language-specific exception patterns:**
```pseudo
# BAD - assumes exceptions, names specific exception types
TRY:
  AWAIT operation_that_fails()
  FAIL("Expected exception")
CATCH AblyException as e:
  ASSERT e.code == 40160
```

The error object in `FAILS WITH error` represents the ErrorInfo associated with the failure. Implementations should verify the appropriate ErrorInfo fields (code, statusCode, message) regardless of how errors are propagated in that language.

## Key Spec Points to Remember

| Spec | Behavior |
|------|----------|
| RSA4b | key + clientId triggers token auth (not basic auth) |
| RSA4b4 | Token renewal on 40140-40149 errors |
| RSA8d | authCallback returns TokenDetails, TokenRequest, or JWT string |
| RSC16 | time() does NOT require authentication - doesn't send auth headers even with credentials |
| RSC18 | Basic auth requires TLS - only applies to authenticated operations (not time()) |
| RSC15l | Fallback on: host unreachable, timeout, HTTP 5xx |
| 40103 | Cannot use Basic auth over non-TLS |
| 40106 | No authentication method configured (constructor rejects) |
| 40171 | Token expired with no means of renewal |
| 40160 | Not permitted (capability error) |
| 40012 | Incompatible clientId |
| 40142 | Token expired |
| 40140 | Token error |

## File Organization

```
uts/test/
├── rest/
│   ├── unit/
│   │   ├── helpers/
│   │   │   └── mock_http.md        # Mock HTTP infrastructure spec
│   │   ├── auth/
│   │   │   ├── auth_callback.md    # RSA8c, RSA8d
│   │   │   ├── auth_scheme.md      # RSA1-4, RSA4b
│   │   │   ├── authorize.md        # RSA10
│   │   │   ├── token_renewal.md    # RSA4b4, RSA14
│   │   │   └── client_id.md        # RSA7, RSC17
│   │   ├── channel/
│   │   │   ├── publish.md          # RSL1
│   │   │   ├── history.md          # RSL2
│   │   │   └── idempotency.md      # RSL1k
│   │   ├── rest_client.md          # RSC7, RSC8, RSC13, RSC18
│   │   ├── fallback.md             # RSC15, REC1, REC2
│   │   ├── time.md                 # RSC16
│   │   ├── stats.md                # RSC6
│   │   ├── request.md              # RSC19
│   │   ├── batch_publish.md        # RSC22, BSP, BPR, BPF
│   │   ├── presence/
│   │   │   └── rest_presence.md    # RSP1, RSP3, RSP4
│   │   ├── encoding/
│   │   │   └── message_encoding.md # RSL4, RSL5, RSL6
│   │   └── types/
│   │       ├── message_types.md    # TM2, TM3, TM4
│   │       ├── error_types.md      # TI1-5
│   │       ├── token_types.md      # TD1-5, TK1-6, TE1-6
│   │       ├── options_types.md    # TO3, AO2
│   │       └── paginated_result.md # TG1-5
│   └── integration/
│       ├── auth.md
│       ├── publish.md
│       ├── history.md
│       ├── presence.md
│       ├── pagination.md
│       └── time_stats.md
├── realtime/
│   ├── unit/
│   │   ├── helpers/
│   │   │   └── mock_websocket.md   # Mock WebSocket infrastructure spec
│   │   ├── client/
│   │   │   ├── realtime_client.md  # RTC1, RTC2, RTC15, RTC16
│   │   │   └── client_options.md   # TO3 (Realtime-specific)
│   │   └── connection/
│   │       ├── connection_failures_test.md
│   │       ├── connection_open_failures_test.md
│   │       └── ...
│   └── integration/
│       └── (future Realtime integration tests)
└── README.md
```

## Completion Status Matrix

When adding a new test spec, update the completion status matrix at `uts/test/completion-status.md` to reflect the newly covered spec items. This matrix tracks which spec items have UTS test specs and which do not.

## Writing Tips

1. **Reference spec points** in test names and file headers
2. **Add spec requirement summaries** at the start of each test
3. **One concept per test** - don't combine unrelated assertions
4. **Describe what you're testing** - not implementation details
5. **Include error codes** when testing error conditions
6. **Mock responses realistically** - include all fields the real API returns
7. **Test both success and failure paths**
8. **Verify request formation** - check headers, path, body, query params
9. **Consider edge cases** - empty results, pagination boundaries, expired tokens
10. **Use handler pattern for simple tests**, await pattern for complex coordination
11. **Distinguish connection-level vs request-level failures**
12. **Use unique channel names** to avoid test interference
13. **Update `uts/test/completion-status.md`** when adding new test specs

## Example Test Spec (Modern Pattern)

```markdown
# Feature Name Tests

Spec points: `RSA4`, `RSA8`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/test/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

---

## RSA4 - Descriptive test name

**Spec requirement:** Brief description of what the spec requires.

Tests that [specific behavior being tested].

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {"result": "success"})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.operation()
```

### Assertions
```pseudo
ASSERT result.field == "success"
ASSERT captured_requests[0].method == "GET"
ASSERT captured_requests[0].headers["Authorization"] IS NOT null
```
```

## Pattern Decision Tree

**Choose handler pattern when:**
- Response is predetermined
- Simple pass-through scenarios
- No need to inspect request before responding

**Choose await pattern when:**
- Need to respond based on test execution state
- Need to coordinate timing with other operations
- Complex scenarios requiring request inspection before response
- Testing connection-level failures separately from request handling

## Common Mistakes to Avoid

1. ❌ Using `mock_http.queue_response()` (old pattern)
   ✅ Use `onRequest: (req) => req.respond_with(...)`

2. ❌ Referencing `mock_http.captured_requests`
   ✅ Use local `captured_requests` array

3. ❌ Referencing `mock_http.request_count`
   ✅ Use local `request_count` variable

4. ❌ Not installing mock: Missing `install_mock(mock_http)`
   ✅ Always call `install_mock(mock_http)` after creating mock

5. ❌ Passing mock to client: `Rest(..., httpClient: mock_http)`
   ✅ Mock is installed globally via `install_mock()`

6. ❌ Missing spec requirement summary
   ✅ Every test must have `**Spec requirement:**` or table

7. ❌ Using fixed WAITs for async operations
   ✅ Use polling with timeout or `AWAIT_STATE`

8. ❌ Not using unique channel names
   ✅ Generate unique names with random component

9. ❌ Synchronous state assertions: `ASSERT state == connecting`
   ✅ Use `AWAIT_STATE state == connecting`

10. ❌ Missing connection handler: Only defining `onRequest`
    ✅ Always include `onConnectionAttempt: (conn) => conn.respond_with_success()`

11. ❌ Using `send_to_client()` for DISCONNECTED or connection-level ERROR
    ✅ Use `send_to_client_and_close()` - server closes connection after these messages

12. ❌ Using `send_to_client_and_close()` for channel-level ERROR
    ✅ Use `send_to_client()` - ERROR with channel doesn't close connection

13. ❌ Using `time()` to test authentication behavior
    ✅ Use `channel.status()` - time() doesn't require or send auth

14. ❌ Creating client without credentials for time() tests: `ClientOptions(tls: false)`
    ✅ Constructor requires credentials - use `ClientOptions(key: "...", tls: false, useTokenAuth: true)`

15. ❌ Using intermediate `AWAIT_STATE disconnected` to observe transient states mid-test
    ✅ Record all state changes and use `CONTAINS_IN_ORDER` to verify the sequence at the end

16. ❌ Using exact `ADVANCE_TIME` calculations for multi-retry scenarios: `ADVANCE_TIME(6000); ADVANCE_TIME(1000)`
    ✅ Use a time-advancement loop: `LOOP up to N times: ADVANCE_TIME(increment)`
