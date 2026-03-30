# Heartbeat Tests (RTN23)

Spec points: `RTN23`, `RTN23a`, `RTN23b`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Overview

RTN23 defines how the client detects connection liveness:

- **RTN23a**: The client must disconnect if no activity is received for `maxIdleInterval + realtimeRequestTimeout`. Any received message (or ping frame, per RTN23b) resets this timer.

- **RTN23b**: The client may use either:
  1. **HEARTBEAT protocol messages** (`heartbeats=true` in connection URL) - for platforms where the WebSocket client does NOT surface ping events
  2. **WebSocket ping frames** (`heartbeats=false` or omitted) - for platforms where the WebSocket client CAN surface ping events

A concrete implementation should implement either RTN23a with HEARTBEAT messages OR RTN23b with ping frames, depending on platform capabilities. The test cases below cover both approaches.

---

# RTN23a Tests (HEARTBEAT Protocol Messages)

These tests apply to platforms where the WebSocket client does NOT surface ping frame events. The client must send `heartbeats=true` in the connection URL.

---

## RTN23a - Client sends heartbeats=true when ping frames not observable

**Spec requirement:** If the client cannot observe WebSocket ping frames, it should send `heartbeats=true` in the connection query parameters.

Tests that the client requests HEARTBEAT protocol messages.

### Setup

```pseudo
captured_url = null

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    captured_url = conn.url
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Test Steps

```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions

```pseudo
# Client should request heartbeats if it cannot observe ping frames
ASSERT captured_url.query_params["heartbeats"] == "true"
```

---

## RTN23a - Disconnect after maxIdleInterval + realtimeRequestTimeout

**Spec requirement:** If no message is received from the server for `maxIdleInterval + realtimeRequestTimeout` milliseconds, the connection is considered lost and the client transitions to DISCONNECTED state.

Tests that the client disconnects and closes the WebSocket when no server activity is detected.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 5000,  # 5 seconds
        connectionStateTtl: 120000
      )
    ))
    # Server sends CONNECTED but then no further messages
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeRequestTimeout: 2000,  # 2 seconds
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Advance time past maxIdleInterval + realtimeRequestTimeout
# = 5000 + 2000 = 7000ms
ADVANCE_TIME(7100)

AWAIT_STATE client.connection.state == ConnectionState.disconnected
```

### Assertions

```pseudo
ASSERT client.connection.state == ConnectionState.disconnected
ASSERT client.connection.errorReason IS NOT null

# Verify the client closed the WebSocket connection
client_close_events = mock_ws.events.filter(e => e.type == CLIENT_CLOSE)
ASSERT client_close_events.length == 1
```

---

## RTN23a - HEARTBEAT message resets idle timer

**Spec requirement:** Any message from the server, including HEARTBEAT messages, resets the idle timer.

Tests that receiving HEARTBEAT messages keeps the connection alive, and that the client closes the WebSocket when it eventually times out.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 3000,  # 3 seconds
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeRequestTimeout: 1000,  # 1 second
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Advance time (not enough to trigger timeout: 3000 + 1000 = 4000ms)
ADVANCE_TIME(2000)

# Send HEARTBEAT from server - resets timer
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: HEARTBEAT
))

# Advance time again (2000ms since HEARTBEAT, still within threshold)
ADVANCE_TIME(2000)

# Connection should still be alive
ASSERT client.connection.state == ConnectionState.connected

# Advance time past the timeout window (4100ms since last HEARTBEAT)
ADVANCE_TIME(2100)

AWAIT_STATE client.connection.state == ConnectionState.disconnected
```

### Assertions

```pseudo
ASSERT client.connection.state == ConnectionState.disconnected

# Verify the client closed the WebSocket connection
client_close_events = mock_ws.events.filter(e => e.type == CLIENT_CLOSE)
ASSERT client_close_events.length == 1
```

---

## RTN23a - Any protocol message resets idle timer

**Spec requirement:** Any message from the server resets the idle timer, not just HEARTBEAT messages.

Tests that receiving any protocol message (e.g., ACK, MESSAGE) keeps the connection alive, and that the client closes the WebSocket when it eventually times out.

### Setup

```pseudo
channel_name = "test-RTN23a-message-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 2000,  # 2 seconds
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeRequestTimeout: 1000,  # 1 second
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Advance time
ADVANCE_TIME(1500)

# Send ACK message from server - resets timer
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ACK,
  msgSerial: 0
))

# Advance time again
ADVANCE_TIME(1500)

# Connection should still be alive (timer was reset)
ASSERT client.connection.state == ConnectionState.connected

# Send MESSAGE from server - resets timer again
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "event", data: "data")
  ]
))

# Advance time again
ADVANCE_TIME(1500)

# Still connected
ASSERT client.connection.state == ConnectionState.connected

# Advance time past timeout without any message
ADVANCE_TIME(1600)

AWAIT_STATE client.connection.state == ConnectionState.disconnected
```

### Assertions

```pseudo
ASSERT client.connection.state == ConnectionState.disconnected

# Verify the client closed the WebSocket connection
client_close_events = mock_ws.events.filter(e => e.type == CLIENT_CLOSE)
ASSERT client_close_events.length == 1
```

---

## RTN23a - Heartbeat timeout triggers immediate reconnection

**Spec requirement:** When a heartbeat timeout causes disconnection, the client should immediately attempt to reconnect (per RTN15a - DISCONNECTED state triggers reconnection).

Tests that the client attempts to reconnect after a heartbeat timeout.

### Setup

```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id-" + connection_attempt_count,
      connectionKey: "connection-key-" + connection_attempt_count,
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key-" + connection_attempt_count,
        maxIdleInterval: 2000,  # 2 seconds
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeRequestTimeout: 1000,  # 1 second
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

ASSERT connection_attempt_count == 1

# Advance time past maxIdleInterval + realtimeRequestTimeout to trigger timeout
# = 2000 + 1000 = 3000ms
ADVANCE_TIME(3100)

# Client should disconnect
AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Client should immediately attempt to reconnect (RTN15a)
# Allow time for the reconnection attempt
ADVANCE_TIME(100)

AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions

```pseudo
# Verify two connection attempts were made (initial + reconnect)
ASSERT connection_attempt_count == 2

# Verify the client is now connected with new connection details
ASSERT client.connection.state == ConnectionState.connected
ASSERT client.connection.id == "connection-id-2"

# Verify the first connection was closed by the client
client_close_events = mock_ws.events.filter(e => e.type == CLIENT_CLOSE)
ASSERT client_close_events.length == 1
```

---

## RTN23a - Reconnection after heartbeat timeout uses resume

**Spec requirement:** When reconnecting after a heartbeat timeout, the client should attempt to resume the connection using the previous connectionKey (per RTN15c).

Tests that the reconnection attempt includes the resume parameters.

### Setup

```pseudo
connection_attempts = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempts.append({
      url: conn.url,
      attempt_number: connection_attempts.length + 1
    })
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id-" + connection_attempts.length,
      connectionKey: "connection-key-" + connection_attempts.length,
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key-" + connection_attempts.length,
        maxIdleInterval: 2000,  # 2 seconds
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeRequestTimeout: 1000,  # 1 second
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Advance time past timeout to trigger disconnection
ADVANCE_TIME(3100)

AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Allow reconnection
ADVANCE_TIME(100)

AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions

```pseudo
ASSERT connection_attempts.length == 2

# First connection should not have resume parameter
first_url = connection_attempts[0].url
ASSERT "resume" NOT IN first_url.query_params

# Second connection should include resume parameter with first connectionKey
second_url = connection_attempts[1].url
ASSERT second_url.query_params["resume"] == "connection-key-1"
```

---

# RTN23b Tests (WebSocket Ping Frames)

These tests apply to platforms where the WebSocket client CAN surface ping frame events. The client should send `heartbeats=false` (or omit the parameter) in the connection URL.

---

## RTN23b - Client sends heartbeats=false when ping frames observable

**Spec requirement:** If the client can observe WebSocket ping frames, it should send `heartbeats=false` (or omit the parameter) in the connection query parameters.

Tests that the client does not request HEARTBEAT protocol messages when it can observe ping frames.

### Setup

```pseudo
captured_url = null

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    captured_url = conn.url
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Test Steps

```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions

```pseudo
# Client should NOT request heartbeats if it can observe ping frames
ASSERT captured_url.query_params["heartbeats"] == "false"
  OR "heartbeats" NOT IN captured_url.query_params
```

---

## RTN23b - Disconnect after maxIdleInterval + realtimeRequestTimeout (no ping frames)

**Spec requirement:** If no activity (including ping frames) is received for `maxIdleInterval + realtimeRequestTimeout`, disconnect.

Tests that the client disconnects and closes the WebSocket when no ping frames or messages are received.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 5000,  # 5 seconds
        connectionStateTtl: 120000
      )
    ))
    # Server sends CONNECTED but then no further messages or ping frames
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeRequestTimeout: 2000,  # 2 seconds
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Advance time past maxIdleInterval + realtimeRequestTimeout
# = 5000 + 2000 = 7000ms
ADVANCE_TIME(7100)

AWAIT_STATE client.connection.state == ConnectionState.disconnected
```

### Assertions

```pseudo
ASSERT client.connection.state == ConnectionState.disconnected
ASSERT client.connection.errorReason IS NOT null

# Verify the client closed the WebSocket connection
client_close_events = mock_ws.events.filter(e => e.type == CLIENT_CLOSE)
ASSERT client_close_events.length == 1
```

---

## RTN23b - Ping frame resets idle timer

**Spec requirement:** WebSocket ping frames count as activity indication and reset the idle timer.

Tests that receiving ping frames keeps the connection alive, and that the client closes the WebSocket when it eventually times out.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 3000,  # 3 seconds
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeRequestTimeout: 1000,  # 1 second
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Advance time (not enough to trigger timeout: 3000 + 1000 = 4000ms)
ADVANCE_TIME(2000)

# Server sends ping frame - resets timer
mock_ws.active_connection.send_ping_frame()

# Advance time again (2000ms since ping, still within threshold)
ADVANCE_TIME(2000)

# Connection should still be alive
ASSERT client.connection.state == ConnectionState.connected

# Advance time past the timeout window (4100ms since last ping)
ADVANCE_TIME(2100)

AWAIT_STATE client.connection.state == ConnectionState.disconnected
```

### Assertions

```pseudo
ASSERT client.connection.state == ConnectionState.disconnected

# Verify the client closed the WebSocket connection
client_close_events = mock_ws.events.filter(e => e.type == CLIENT_CLOSE)
ASSERT client_close_events.length == 1
```

---

## RTN23b - Any protocol message also resets idle timer

**Spec requirement:** Any message from the server resets the idle timer, not just ping frames.

Tests that both ping frames AND protocol messages reset the timer, and that the client closes the WebSocket when it eventually times out.

### Setup

```pseudo
channel_name = "test-RTN23b-message-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 2000,  # 2 seconds
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeRequestTimeout: 1000,  # 1 second
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Advance time
ADVANCE_TIME(1500)

# Send ping frame - resets timer
mock_ws.active_connection.send_ping_frame()

# Advance time
ADVANCE_TIME(1500)

# Still connected
ASSERT client.connection.state == ConnectionState.connected

# Send MESSAGE from server - also resets timer
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "event", data: "data")
  ]
))

# Advance time
ADVANCE_TIME(1500)

# Still connected
ASSERT client.connection.state == ConnectionState.connected

# Send another ping frame
mock_ws.active_connection.send_ping_frame()

# Advance time
ADVANCE_TIME(1500)

# Still connected
ASSERT client.connection.state == ConnectionState.connected

# Advance time past timeout without any activity
ADVANCE_TIME(1600)

AWAIT_STATE client.connection.state == ConnectionState.disconnected
```

### Assertions

```pseudo
ASSERT client.connection.state == ConnectionState.disconnected

# Verify the client closed the WebSocket connection
client_close_events = mock_ws.events.filter(e => e.type == CLIENT_CLOSE)
ASSERT client_close_events.length == 1
```

---

## RTN23b - Ping frame timeout triggers immediate reconnection

**Spec requirement:** When a ping frame timeout causes disconnection, the client should immediately attempt to reconnect (per RTN15a - DISCONNECTED state triggers reconnection).

Tests that the client attempts to reconnect after a ping frame timeout.

### Setup

```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id-" + connection_attempt_count,
      connectionKey: "connection-key-" + connection_attempt_count,
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key-" + connection_attempt_count,
        maxIdleInterval: 2000,  # 2 seconds
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeRequestTimeout: 1000,  # 1 second
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

ASSERT connection_attempt_count == 1

# Advance time past maxIdleInterval + realtimeRequestTimeout to trigger timeout
# = 2000 + 1000 = 3000ms
ADVANCE_TIME(3100)

# Client should disconnect
AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Client should immediately attempt to reconnect (RTN15a)
# Allow time for the reconnection attempt
ADVANCE_TIME(100)

AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions

```pseudo
# Verify two connection attempts were made (initial + reconnect)
ASSERT connection_attempt_count == 2

# Verify the client is now connected with new connection details
ASSERT client.connection.state == ConnectionState.connected
ASSERT client.connection.id == "connection-id-2"

# Verify the first connection was closed by the client
client_close_events = mock_ws.events.filter(e => e.type == CLIENT_CLOSE)
ASSERT client_close_events.length == 1
```

---

## RTN23b - Reconnection after ping frame timeout uses resume

**Spec requirement:** When reconnecting after a ping frame timeout, the client should attempt to resume the connection using the previous connectionKey (per RTN15c).

Tests that the reconnection attempt includes the resume parameters.

### Setup

```pseudo
connection_attempts = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempts.append({
      url: conn.url,
      attempt_number: connection_attempts.length + 1
    })
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id-" + connection_attempts.length,
      connectionKey: "connection-key-" + connection_attempts.length,
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key-" + connection_attempts.length,
        maxIdleInterval: 2000,  # 2 seconds
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeRequestTimeout: 1000,  # 1 second
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Advance time past timeout to trigger disconnection
ADVANCE_TIME(3100)

AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Allow reconnection
ADVANCE_TIME(100)

AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions

```pseudo
ASSERT connection_attempts.length == 2

# First connection should not have resume parameter
first_url = connection_attempts[0].url
ASSERT "resume" NOT IN first_url.query_params

# Second connection should include resume parameter with first connectionKey
second_url = connection_attempts[1].url
ASSERT second_url.query_params["resume"] == "connection-key-1"
```

---

## RTN23b - Multiple ping frames keep connection alive

**Spec requirement:** Continuous ping frame activity keeps the connection alive indefinitely.

Tests that regular ping frames prevent timeout.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 2000,  # 2 seconds
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeRequestTimeout: 1000,  # 1 second
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Simulate regular ping frames every 1.5 seconds for 10 seconds
FOR i IN 1..7:
  ADVANCE_TIME(1500)
  mock_ws.active_connection.send_ping_frame()
  ASSERT client.connection.state == ConnectionState.connected
```

### Assertions

```pseudo
# Connection stayed alive through all ping frames
ASSERT client.connection.state == ConnectionState.connected
```

---

# Implementation Notes

## Choosing Between RTN23a and RTN23b

A concrete SDK implementation should:

1. **Determine platform capability**: Can the WebSocket client surface ping frame events?

2. **If YES (ping frames observable)**:
   - Send `heartbeats=false` (or omit) in connection URL
   - Listen for ping frame events as heartbeat indicators
   - Implement RTN23b tests

3. **If NO (ping frames not observable)**:
   - Send `heartbeats=true` in connection URL
   - Expect HEARTBEAT protocol messages from server
   - Implement RTN23a tests

### Platform-Specific Notes

**Dart:** The standard `dart:io` WebSocket does **not** surface ping frames to the application layer. The ping/pong mechanism is handled automatically and internally - there is no `onPing` callback. Therefore, Dart implementations must use **RTN23a** (HEARTBEAT protocol messages) for idle timeout detection. The RTN23b tests do not apply to Dart.

## Timer Mocking

These tests use `enable_fake_timers()` and `ADVANCE_TIME()` to avoid slow tests. Implementations should:

1. **Prefer fake timers** (JavaScript Jest, Python freezegun, Go testing.Clock)
2. **Or use dependency injection** for timer/clock interfaces
3. **Or use very short timeout values** (e.g., 50ms instead of 5s)
4. **Last resort:** Use actual delays with generous test timeouts

## Verifying Transient States

When testing heartbeat timeout behavior, the connection may pass through DISCONNECTED state very quickly due to immediate reconnection (RTN15a). Do not attempt to catch the DISCONNECTED state directly - instead, record the full sequence of state changes and verify it at the end:

```pseudo
state_changes = []
client.connection.on().listen((change) => {
  state_changes.append(change.current)
})

# Trigger timeout and reconnection
ADVANCE_TIME(maxIdleInterval + realtimeRequestTimeout + buffer)
PUMP_EVENT_QUEUE()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Verify the sequence included DISCONNECTED
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.connecting,
  ConnectionState.connected,
  ConnectionState.disconnected,
  ConnectionState.connecting,
  ConnectionState.connected
]
```

See `mock_websocket.md` for more details on event sequence verification.

See the "Timer Mocking" section in `write-test-spec.md` for detailed guidance.
