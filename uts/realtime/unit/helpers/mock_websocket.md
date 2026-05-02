# Mock WebSocket Infrastructure

This document specifies the mock WebSocket infrastructure for Realtime unit tests. All Realtime unit tests that need to intercept WebSocket connections should reference this document.

## Purpose

The mock infrastructure enables unit testing of Realtime client behavior without making real network calls. It supports:

1. **Intercepting connection attempts** - Capture the URL and query parameters used when connecting
2. **Injecting server messages** - Deliver protocol messages to the client as if from the server
3. **Capturing client messages** - Record protocol messages sent by the client
4. **Controlling connection outcomes** - Simulate various connection results including successful connections, connection refused, DNS errors, timeouts, and other network-level failures
5. **Simulating connection events** - Trigger disconnect and error conditions on established connections

## Installation Mechanism

The mechanism for injecting the mock is implementation-specific and not part of the public API. Possible approaches include:

- Package-level variable substitution (e.g., `var dialWebsocket = ...`)
- Build tag conditional compilation
- Internal test exports (`export_test.go` pattern in Go)
- Dependency injection via internal constructors

## Mock Interface

```pseudo
interface MockWebSocket:
  # Event sequence tracking - unified timeline of all events
  events: List<MockEvent>  # Ordered sequence of all connection and message events

  # Message injection (server -> client)
  send_to_client(message: ProtocolMessage)
  send_to_client_and_close(message: ProtocolMessage)  # Send then close connection
  simulate_disconnect(error?: ErrorInfo)  # Close without sending a message

  # WebSocket ping frame simulation (for RTN23b)
  # Simulates the server sending a WebSocket ping frame.
  # On platforms where the WebSocket client surfaces ping events,
  # this allows testing heartbeat behavior via ping frames instead of
  # HEARTBEAT protocol messages.
  send_ping_frame()

  # Awaitable event triggers for test code
  await_next_message_from_client(timeout?: Duration): Future<ProtocolMessage>
  await_connection_attempt(timeout?: Duration): Future<PendingConnection>
  await_client_close(timeout?: Duration): Future<ClientCloseEvent>  # Wait for client to close WebSocket

  # Test management
  reset()  # Clear all state

enum MockEventType:
  CONNECTION_ATTEMPT      # Client attempted to connect
  CONNECTION_SUCCESS      # Connection established successfully
  CONNECTION_FAILURE      # Connection failed (refused, timeout, DNS error, etc.)
  MESSAGE_FROM_CLIENT     # Client sent a protocol message
  MESSAGE_TO_CLIENT       # Server sent a protocol message (test injected)
  PING_FRAME              # WebSocket ping frame sent to client (test injected)
  SERVER_DISCONNECT       # Server closed the connection or transport failure
  CLIENT_CLOSE            # Client initiated WebSocket close

struct MockEvent:
  type: MockEventType
  timestamp: Time
  data: Any  # Event-specific data (PendingConnection, ProtocolMessage, ErrorInfo, etc.)

struct ClientCloseEvent:
  code: Int?              # WebSocket close code (e.g., 1000 for normal closure)
  reason: String?         # Optional close reason

interface PendingConnection:
  url: URL
  protocol: String  # "application/json" or "application/x-msgpack"
  timestamp: Time

  # Methods for test code to respond to the connection attempt
  respond_with_success(connected_message: ProtocolMessage)
  respond_with_refused()  # Connection refused at network level
  respond_with_timeout()  # Connection times out (unresponsive)
  respond_with_dns_error()  # DNS resolution fails
  respond_with_error(error_message: ProtocolMessage, then_close: bool = true)  # WebSocket connects but server sends ERROR
```

## Handler-Based Configuration

For simple test scenarios, implementations may support handler-based configuration:

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED_MESSAGE)
  },
  onMessageFromClient: (msg) => {
    # Handle decoded messages from client
  },
  onTextDataFrame: (text) => {
    # Handle raw text WebSocket data frame (JSON protocol)
  },
  onBinaryDataFrame: (bytes) => {
    # Handle raw binary WebSocket data frame (msgpack protocol)
  }
)
```

Handlers are called automatically when connection attempts or messages occur. The await-based API should always be available for tests that need to coordinate responses with test state.

### Raw Data Frame Hooks

The `onTextDataFrame` and `onBinaryDataFrame` handlers provide access to the raw WebSocket data frames before they are decoded into `ProtocolMessage` objects. This is useful for tests that need to verify the wire encoding (e.g., that null fields are omitted from the encoded representation).

- **`onTextDataFrame(text: String)`** — Called when the client sends a text WebSocket frame. This occurs when using the JSON protocol (`useBinaryProtocol: false`). The `text` parameter is the raw JSON string.
- **`onBinaryDataFrame(bytes: Bytes)`** — Called when the client sends a binary WebSocket frame. This occurs when using the msgpack protocol (`useBinaryProtocol: true`). The `bytes` parameter is the raw msgpack-encoded bytes.

Both raw frame handlers are called **in addition to** `onMessageFromClient` (which receives the decoded `ProtocolMessage`). If only `onMessageFromClient` is provided, raw frames are not surfaced to the test.

### When to Use Each Pattern

**Handler pattern** (recommended for most tests):
- Response is predetermined based on request count or content
- Simple "first attempt fails, second succeeds" scenarios
- No need to coordinate with external test state

**Await pattern** (for advanced scenarios):
- Need to inspect connection details before deciding how to respond
- Test logic depends on external state not known at setup time
- Complex coordination between multiple async operations

**Important note on await pattern**: When awaiting multiple sequential connection attempts, you must set up the await for the next attempt BEFORE responding to the current one to avoid race conditions:

```pseudo
# Correct pattern for sequential awaits
first_conn = AWAIT mock_ws.await_connection_attempt()
second_future = mock_ws.await_connection_attempt()  # Set up BEFORE responding
first_conn.respond_with_error(...)  # This triggers retry
second_conn = AWAIT second_future
```

## Connection Closing Semantics

### Server-Initiated Close (Test Simulating Server)

When simulating server behavior, use the correct method based on the scenario:

| Scenario | Method | Event Recorded |
|----------|--------|----------------|
| Server sends DISCONNECTED | `send_to_client_and_close()` | `SERVER_DISCONNECT` |
| Server sends ERROR (connection-level) | `send_to_client_and_close()` | `SERVER_DISCONNECT` |
| Server sends ERROR (channel-level) | `send_to_client()` | (none - connection stays open) |
| Server sends CONNECTED, HEARTBEAT, ACK, MESSAGE | `send_to_client()` | (none - connection stays open) |
| Unexpected transport failure | `simulate_disconnect()` | `SERVER_DISCONNECT` |

**Key rule:** Whenever the server sends DISCONNECTED, or ERROR without a specified channel, it will be accompanied by the server closing the WebSocket connection. An ERROR with a specified channel is an attachment failure and doesn't end the connection.

### Client-Initiated Close (Library Closing Connection)

When the Ably library closes the WebSocket connection (e.g., due to heartbeat timeout, explicit close, or fatal error), a `CLIENT_CLOSE` event is recorded. Tests can:

1. **Inspect events list:** Check `mock_ws.events` for `CLIENT_CLOSE` event
2. **Await the close:** Use `await_client_close()` to wait for the library to close

```pseudo
# Example: Assert client closed the connection after heartbeat timeout
AWAIT mock_ws.await_client_close(timeout: 1000)

# Or inspect the events list
client_close_events = mock_ws.events.filter(e => e.type == CLIENT_CLOSE)
ASSERT client_close_events.length == 1
```

The `ClientCloseEvent` contains:
- `code`: WebSocket close code (e.g., 1000 for normal, 1001 for going away)
- `reason`: Optional human-readable close reason

## WebSocket Ping Frame Simulation (RTN23b)

Some WebSocket client implementations surface ping frame events to the application layer. Per RTN23b, if the WebSocket client can observe ping frames, the Ably library can use them as heartbeat indicators instead of requiring HEARTBEAT protocol messages.

Use `send_ping_frame()` to simulate the server sending a WebSocket ping frame:

```pseudo
# Simulate server sending a ping frame (transport-level heartbeat)
mock_ws.active_connection.send_ping_frame()
```

**When to use ping frames vs HEARTBEAT messages:**

| Scenario | Method | Use Case |
|----------|--------|----------|
| Platform surfaces ping events | `send_ping_frame()` | RTN23b - Test heartbeat via ping frames |
| Platform doesn't surface pings | `send_to_client(HEARTBEAT_MESSAGE)` | RTN23a - Test heartbeat via protocol messages |

**Connection URL query parameter:**
- If the client sends `heartbeats=true`, it expects HEARTBEAT protocol messages
- If the client sends `heartbeats=false` (or omits it), the server may use ping frames
- The test should verify which parameter the client sends based on platform capabilities

## Protocol Message Templates

Common protocol messages for testing:

```pseudo
CONNECTED_MESSAGE = ProtocolMessage(
  action: CONNECTED,
  connectionId: "test-connection-id",
  connectionDetails: ConnectionDetails(
    connectionKey: "test-connection-key",
    clientId: null,
    connectionStateTtl: 120000,
    maxIdleInterval: 15000
  )
)

CLOSED_MESSAGE = ProtocolMessage(
  action: CLOSED
)

DISCONNECTED_MESSAGE = ProtocolMessage(
  action: DISCONNECTED,
  error: ErrorInfo(code: 80003, message: "Connection disconnected")
)

ERROR_MESSAGE(code, message) = ProtocolMessage(
  action: ERROR,
  error: ErrorInfo(code: code, statusCode: code / 100, message: message)
)

HEARTBEAT_MESSAGE = ProtocolMessage(
  action: HEARTBEAT
)
```

## Example: Handler Pattern with State

```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    
    IF connection_attempt_count == 1:
      # First attempt fails
      conn.respond_with_refused()
    ELSE:
      # Second attempt succeeds
      conn.respond_with_success(CONNECTED_MESSAGE)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

client.connect()

AWAIT_STATE client.connection.state == ConnectionState.connected

ASSERT connection_attempt_count == 2
```

## Example: Server Sends Token Error

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    # Server sends token error and closes connection
    conn.send_to_client_and_close(ProtocolMessage(
      action: ERROR,
      error: ErrorInfo(
        code: 40142,
        statusCode: 401,
        message: "Token expired"
      )
    ))
  }
)
```

## Test Isolation

Each test should:

1. Create a fresh mock WebSocket
2. Install the mock
3. Create the Realtime client
4. Perform test steps and assertions
5. Close the client
6. Restore/cleanup the mock

```pseudo
BEFORE EACH TEST:
  mock_ws = MockWebSocket()
  install_mock(mock_ws)

AFTER EACH TEST:
  IF client IS NOT null:
    client.close()
  uninstall_mock()
```

## Timer Mocking

Tests that verify timeout behavior should use timer mocking where practical. See the Timer Mocking section below.

**Pseudocode convention:**

```pseudo
enable_fake_timers()

# Start operation
client.connect()

# Advance time to trigger timeout
ADVANCE_TIME(15000)  # Advance 15 seconds instantly

# Assert timeout behavior
ASSERT client.connection.state == ConnectionState.disconnected
```

**Implementation guidance:**

- **Preferred**: Mock/fake the timer/clock mechanism (e.g., `jest.advanceTimersByTime()` in JavaScript)
- **Alternative**: Use dependency injection of clock/timer abstractions
- **Fallback**: Use actual time delays with short timeout values

## Async Behavior and Event Loop Considerations

### Mock close() Must Be Asynchronous

The mock WebSocket's `close()` method must call `listener.onClose()` **asynchronously** (e.g., via `scheduleMicrotask` or `setTimeout(..., 0)`), not synchronously. This matches the behavior of real WebSocket implementations where `onClose` is triggered via the stream's `onDone` callback.

```pseudo
# CORRECT - matches real WebSocket behavior
close(code, reason):
  IF already_closed: RETURN
  closed = true
  record_event(CLIENT_CLOSE, {code, reason})
  schedule_microtask(() => listener.onClose(code, reason))

# WRONG - would cause issues with state machine timing
close(code, reason):
  IF already_closed: RETURN
  closed = true
  listener.onClose(code, reason)  # Synchronous - BAD
```

### respondWithSuccess() Ordering

When a connection attempt succeeds, `respondWithSuccess()` must:
1. **First** - Complete the connection future (so `connect()` returns)
2. **Then** - Deliver the CONNECTED message asynchronously

This ensures the library has stored the WebSocket connection reference before processing the CONNECTED message (which may start timers that reference the connection).

```pseudo
respond_with_success(connected_message):
  connection = create_mock_connection(listener)
  completer.complete(connection)  # 1. Connection established
  schedule_microtask(() => {
    listener.onMessage(connected_message)  # 2. Then deliver message
  })
```

### Avoiding Arbitrary Real-Time Delays

Tests should **never** use fixed real-time delays like `await Future.delayed(Duration(milliseconds: 100))`. These cause:
- Slow tests
- Flaky tests (timing varies by machine load)
- Non-deterministic behavior

Instead:
- Use fake timers with `ADVANCE_TIME()`
- Wait for specific state changes with `AWAIT_STATE`

```pseudo
# BAD - arbitrary real-time delay
ADVANCE_TIME(3000)
WAIT 100ms  # Real-time delay - flaky!
ASSERT state == disconnected

# GOOD - advance time and wait for state
ADVANCE_TIME(3000)
AWAIT_STATE state == disconnected
```

## Verifying State Transitions with Event Sequences

When testing behavior that involves transient states (e.g., DISCONNECTED during reconnection), **do not** try to catch the state at a specific moment. Instead, record the full sequence of state changes and verify it at the end:

```pseudo
state_changes = []
client.connection.on().listen((change) => {
  state_changes.append(change.current)
})

# Trigger the behavior
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Trigger disconnect and reconnect
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Verify the sequence included the expected states
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.connecting,
  ConnectionState.connected,
  ConnectionState.disconnected,
  ConnectionState.connecting,
  ConnectionState.connected
]
```

This approach is more robust because:
- It doesn't depend on catching a transient state at exactly the right moment
- It works even when immediate reconnection (RTN15a) causes rapid state transitions
- It verifies the complete behavior, not just the final state
