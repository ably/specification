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

  # Awaitable event triggers for test code
  await_next_message_from_client(timeout?: Duration): Future<ProtocolMessage>
  await_connection_attempt(timeout?: Duration): Future<PendingConnection>
  await_close_request(timeout?: Duration): Future<void>

  # Test management
  reset()  # Clear all state

enum MockEventType:
  CONNECTION_ATTEMPT
  CONNECTION_SUCCESS
  CONNECTION_FAILURE
  MESSAGE_FROM_CLIENT
  MESSAGE_TO_CLIENT
  DISCONNECT
  CLOSE_REQUEST

struct MockEvent:
  type: MockEventType
  timestamp: Time
  data: Any  # Event-specific data (PendingConnection, ProtocolMessage, ErrorInfo, etc.)

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
    # Handle messages from client
  }
)
```

Handlers are called automatically when connection attempts or messages occur. The await-based API should always be available for tests that need to coordinate responses with test state.

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

When simulating server behavior, use the correct method based on the scenario:

| Scenario | Method | Description |
|----------|--------|-------------|
| Server sends DISCONNECTED | `send_to_client_and_close()` | Server sends message then closes connection |
| Server sends ERROR (connection-level) | `send_to_client_and_close()` | ERROR without channel = fatal, closes connection |
| Server sends ERROR (channel-level) | `send_to_client()` | ERROR with channel = attachment failure, connection stays open |
| Server sends CONNECTED, HEARTBEAT, ACK, MESSAGE | `send_to_client()` | Normal messages, connection stays open |
| Unexpected transport failure | `simulate_disconnect()` | Connection drops without server message |

**Key rule:** Whenever the server sends DISCONNECTED, or ERROR without a specified channel, it will be accompanied by the server closing the WebSocket connection. An ERROR with a specified channel is an attachment failure and doesn't end the connection.

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
