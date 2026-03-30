# Connection Ping Tests (RTN13)

Spec points: `RTN13`, `RTN13a`, `RTN13b`, `RTN13c`, `RTN13d`, `RTN13e`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Overview

RTN13 defines the `Connection#ping()` function:

- **RTN13a**: Sends a `ProtocolMessage` with action `HEARTBEAT` and expects a `HEARTBEAT` response. Returns the round-trip duration.
- **RTN13b**: Returns an error if in, or transitions to, `INITIALIZED`, `SUSPENDED`, `CLOSING`, `CLOSED`, or `FAILED`.
- **RTN13c**: Fails with a timeout error if no `HEARTBEAT` response is received within `realtimeRequestTimeout`.
- **RTN13d**: If connection state is `CONNECTING` or `DISCONNECTED`, the operation is deferred and executed once the state becomes `CONNECTED`.
- **RTN13e**: The sent `HEARTBEAT` includes an `id` property with a random string. Only a response `HEARTBEAT` with a matching `id` is considered a valid response — this disambiguates from normal heartbeats and other pings.

---

## RTN13a - Ping sends HEARTBEAT and returns round-trip duration

| Spec | Requirement |
|------|-------------|
| RTN13a | Sends HEARTBEAT when connected and expects HEARTBEAT response with round-trip time |

Tests that `connection.ping()` sends a HEARTBEAT protocol message and resolves with the elapsed duration when a matching HEARTBEAT response is received.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    CONNECTED_MESSAGE(connectionId: "conn-id-1", connectionKey: "conn-key-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == HEARTBEAT:
      # Echo back a HEARTBEAT with matching id
      mock_ws.active_connection.send_to_client(ProtocolMessage(
        action: HEARTBEAT,
        id: msg.id
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

duration = AWAIT client.connection.ping()
```

### Assertions
```pseudo
# Ping should resolve successfully
ASSERT duration IS NOT null
ASSERT duration >= Duration.zero

# Verify a HEARTBEAT was sent by the client
heartbeats_sent = mock_ws.events.filter(
  e => e.type == MESSAGE_FROM_CLIENT AND e.message.action == HEARTBEAT
)
ASSERT heartbeats_sent.length == 1
```

---

## RTN13e - HEARTBEAT includes random id for disambiguation

| Spec | Requirement |
|------|-------------|
| RTN13e | Sent HEARTBEAT includes random id; only matching response counts |

Tests that the sent HEARTBEAT includes a random `id` and that only a response with the same `id` is accepted.

### Setup
```pseudo
captured_heartbeat_id = null

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    CONNECTED_MESSAGE(connectionId: "conn-id-1", connectionKey: "conn-key-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == HEARTBEAT:
      captured_heartbeat_id = msg.id
      # First send a HEARTBEAT with a DIFFERENT id (should be ignored)
      mock_ws.active_connection.send_to_client(ProtocolMessage(
        action: HEARTBEAT,
        id: "wrong-id"
      ))
      # Then send a HEARTBEAT with the matching id (should resolve ping)
      mock_ws.active_connection.send_to_client(ProtocolMessage(
        action: HEARTBEAT,
        id: msg.id
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

duration = AWAIT client.connection.ping()
```

### Assertions
```pseudo
# Ping should resolve (matched the correct id)
ASSERT duration IS NOT null
ASSERT duration >= Duration.zero

# The sent HEARTBEAT should have had a non-empty id
ASSERT captured_heartbeat_id IS NOT null
ASSERT captured_heartbeat_id.length > 0
```

---

## RTN13e - HEARTBEAT with no id is ignored as ping response

| Spec | Requirement |
|------|-------------|
| RTN13e | Only a HEARTBEAT with matching id counts as a ping response |

Tests that a server-initiated HEARTBEAT (no `id` field) does not resolve a pending ping.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    CONNECTED_MESSAGE(connectionId: "conn-id-1", connectionKey: "conn-key-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == HEARTBEAT:
      # Send a HEARTBEAT without an id (like a server-initiated heartbeat)
      mock_ws.active_connection.send_to_client(ProtocolMessage(
        action: HEARTBEAT
      ))
      # Then send the correct response
      mock_ws.active_connection.send_to_client(ProtocolMessage(
        action: HEARTBEAT,
        id: msg.id
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

duration = AWAIT client.connection.ping()
```

### Assertions
```pseudo
# Ping should resolve (ignored the no-id heartbeat, matched the correct one)
ASSERT duration IS NOT null
ASSERT duration >= Duration.zero
```

---

## RTN13e - Multiple concurrent pings each get their own response

| Spec | Requirement |
|------|-------------|
| RTN13e | Each ping has a unique random id for disambiguation |

Tests that two concurrent pings each resolve independently via their unique ids.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    CONNECTED_MESSAGE(connectionId: "conn-id-1", connectionKey: "conn-key-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == HEARTBEAT:
      # Echo back with matching id
      mock_ws.active_connection.send_to_client(ProtocolMessage(
        action: HEARTBEAT,
        id: msg.id
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

# Start two pings concurrently
ping1_future = client.connection.ping()
ping2_future = client.connection.ping()

duration1 = AWAIT ping1_future
duration2 = AWAIT ping2_future
```

### Assertions
```pseudo
# Both pings should resolve
ASSERT duration1 IS NOT null
ASSERT duration2 IS NOT null

# Verify two separate HEARTBEAT messages were sent
heartbeats_sent = mock_ws.events.filter(
  e => e.type == MESSAGE_FROM_CLIENT AND e.message.action == HEARTBEAT
)
ASSERT heartbeats_sent.length == 2

# The two HEARTBEATs should have different ids
ASSERT heartbeats_sent[0].message.id != heartbeats_sent[1].message.id
```

---

## RTN13c - Ping times out if no HEARTBEAT response

| Spec | Requirement |
|------|-------------|
| RTN13c | Fails if HEARTBEAT not received within realtimeRequestTimeout |

Tests that `ping()` fails with a timeout error if the server does not respond within `realtimeRequestTimeout`.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    CONNECTED_MESSAGE(connectionId: "conn-id-1", connectionKey: "conn-key-1")
  )
  # No onMessageFromClient handler — server never responds to HEARTBEAT
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeRequestTimeout: 2000,
  autoConnect: false
))
```

### Test Steps
```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

ping_future = client.connection.ping()

# Advance time past realtimeRequestTimeout
ADVANCE_TIME(2100)

error = AWAIT_ERROR ping_future
```

### Assertions
```pseudo
ASSERT error IS NOT null
# The error should indicate a timeout
ASSERT error.message CONTAINS "timeout" (case insensitive)
```

---

## RTN13b - Ping errors in INITIALIZED state

| Spec | Requirement |
|------|-------------|
| RTN13b | Error if in INITIALIZED, SUSPENDED, CLOSING, CLOSED, or FAILED state |

Tests that `ping()` returns an error immediately when the connection is in INITIALIZED state.

### Setup
```pseudo
client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Test Steps
```pseudo
ASSERT client.connection.state == ConnectionState.initialized

error = AWAIT_ERROR client.connection.ping()
```

### Assertions
```pseudo
ASSERT error IS NOT null
```

---

## RTN13b - Ping errors in SUSPENDED state

| Spec | Requirement |
|------|-------------|
| RTN13b | Error if in INITIALIZED, SUSPENDED, CLOSING, CLOSED, or FAILED state |

Tests that `ping()` returns an error when the connection is in SUSPENDED state.

### Setup
```pseudo
enable_fake_timers()

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_refused()
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  disconnectedRetryTimeout: 1000,
  suspendedRetryTimeout: 100,
  fallbackHosts: []
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Advance past connectionStateTtl to reach SUSPENDED
ADVANCE_TIME(121s)
AWAIT_STATE client.connection.state == ConnectionState.suspended

error = AWAIT_ERROR client.connection.ping()
```

### Assertions
```pseudo
ASSERT error IS NOT null
```

---

## RTN13b - Ping errors in CLOSED state

| Spec | Requirement |
|------|-------------|
| RTN13b | Error if in INITIALIZED, SUSPENDED, CLOSING, CLOSED, or FAILED state |

Tests that `ping()` returns an error when the connection is in CLOSED state.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    CONNECTED_MESSAGE(connectionId: "conn-id-1", connectionKey: "conn-key-1")
  )
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

AWAIT client.close()
AWAIT_STATE client.connection.state == ConnectionState.closed

error = AWAIT_ERROR client.connection.ping()
```

### Assertions
```pseudo
ASSERT error IS NOT null
```

---

## RTN13b - Ping errors in FAILED state

| Spec | Requirement |
|------|-------------|
| RTN13b | Error if in INITIALIZED, SUSPENDED, CLOSING, CLOSED, or FAILED state |

Tests that `ping()` returns an error when the connection is in FAILED state.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_error(
    ProtocolMessage(
      action: ERROR,
      error: ErrorInfo(code: 80000, statusCode: 400, message: "Fatal error")
    )
  )
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
AWAIT_STATE client.connection.state == ConnectionState.failed

error = AWAIT_ERROR client.connection.ping()
```

### Assertions
```pseudo
ASSERT error IS NOT null
```

---

## RTN13d - Ping deferred from CONNECTING state until CONNECTED

| Spec | Requirement |
|------|-------------|
| RTN13d | If CONNECTING or DISCONNECTED, execute ping once CONNECTED |

Tests that calling `ping()` while CONNECTING defers the operation until the connection becomes CONNECTED, then sends the HEARTBEAT and resolves.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    # Delay the CONNECTED response so we can call ping() while CONNECTING
    SCHEDULE_AFTER(100ms):
      conn.respond_with_success(
        CONNECTED_MESSAGE(connectionId: "conn-id-1", connectionKey: "conn-key-1")
      )
  },
  onMessageFromClient: (msg) => {
    IF msg.action == HEARTBEAT:
      mock_ws.active_connection.send_to_client(ProtocolMessage(
        action: HEARTBEAT,
        id: msg.id
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
enable_fake_timers()

client.connect()
ASSERT client.connection.state == ConnectionState.connecting

# Call ping() while still CONNECTING
ping_future = client.connection.ping()

# Advance time so the connection completes
ADVANCE_TIME(200ms)
AWAIT_STATE client.connection.state == ConnectionState.connected

duration = AWAIT ping_future
```

### Assertions
```pseudo
# Ping should resolve after connection was established
ASSERT duration IS NOT null
ASSERT duration >= Duration.zero

# Verify HEARTBEAT was sent (only after CONNECTED)
heartbeats_sent = mock_ws.events.filter(
  e => e.type == MESSAGE_FROM_CLIENT AND e.message.action == HEARTBEAT
)
ASSERT heartbeats_sent.length == 1
```

---

## RTN13d - Ping deferred from DISCONNECTED state until CONNECTED

| Spec | Requirement |
|------|-------------|
| RTN13d | If CONNECTING or DISCONNECTED, execute ping once CONNECTED |

Tests that calling `ping()` while DISCONNECTED defers the operation until the connection reconnects, then sends the HEARTBEAT and resolves.

### Setup
```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    IF connection_attempt_count == 1:
      # First attempt: connect successfully
      conn.respond_with_success(
        CONNECTED_MESSAGE(connectionId: "conn-id-1", connectionKey: "conn-key-1")
      )
    ELSE:
      # Subsequent attempts: also connect successfully
      conn.respond_with_success(
        CONNECTED_MESSAGE(connectionId: "conn-id-2", connectionKey: "conn-key-2")
      )
  },
  onMessageFromClient: (msg) => {
    IF msg.action == HEARTBEAT:
      mock_ws.active_connection.send_to_client(ProtocolMessage(
        action: HEARTBEAT,
        id: msg.id
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  disconnectedRetryTimeout: 500,
  autoConnect: false
))
```

### Test Steps
```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Force disconnect by closing the transport
mock_ws.active_connection.close_from_server()
AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Call ping() while DISCONNECTED
ping_future = client.connection.ping()

# Advance time past disconnectedRetryTimeout so reconnection happens
ADVANCE_TIME(600ms)
AWAIT_STATE client.connection.state == ConnectionState.connected

duration = AWAIT ping_future
```

### Assertions
```pseudo
# Ping should resolve after reconnection
ASSERT duration IS NOT null
ASSERT duration >= Duration.zero

# Verify HEARTBEAT was sent
heartbeats_sent = mock_ws.events.filter(
  e => e.type == MESSAGE_FROM_CLIENT AND e.message.action == HEARTBEAT
)
ASSERT heartbeats_sent.length == 1
```

---

## RTN13b - Deferred ping errors if connection transitions to FAILED

| Spec | Requirement |
|------|-------------|
| RTN13b | Error if has transitioned to INITIALIZED, SUSPENDED, CLOSING, CLOSED, or FAILED |
| RTN13d | Deferred ping from CONNECTING state |

Tests that a ping deferred from CONNECTING state fails with an error if the connection transitions to FAILED instead of CONNECTED.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    # Respond with fatal error instead of CONNECTED
    SCHEDULE_AFTER(100ms):
      conn.respond_with_error(
        ProtocolMessage(
          action: ERROR,
          error: ErrorInfo(code: 80000, statusCode: 400, message: "Fatal error")
        )
      )
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
enable_fake_timers()

client.connect()
ASSERT client.connection.state == ConnectionState.connecting

# Call ping() while CONNECTING
ping_future = client.connection.ping()

# Advance time so the error response arrives
ADVANCE_TIME(200ms)
AWAIT_STATE client.connection.state == ConnectionState.failed

error = AWAIT_ERROR ping_future
```

### Assertions
```pseudo
ASSERT error IS NOT null
```

---

## RTN13b - Deferred ping errors if connection transitions to SUSPENDED

| Spec | Requirement |
|------|-------------|
| RTN13b | Error if has transitioned to INITIALIZED, SUSPENDED, CLOSING, CLOSED, or FAILED |
| RTN13d | Deferred ping from CONNECTING/DISCONNECTED state |

Tests that a ping deferred from DISCONNECTED state fails with an error if the connection transitions to SUSPENDED instead of reconnecting.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_refused()
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  disconnectedRetryTimeout: 1000,
  suspendedRetryTimeout: 100,
  fallbackHosts: []
))
```

### Test Steps
```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Call ping() while DISCONNECTED
ping_future = client.connection.ping()

# Advance past connectionStateTtl to reach SUSPENDED
ADVANCE_TIME(121s)
AWAIT_STATE client.connection.state == ConnectionState.suspended

error = AWAIT_ERROR ping_future
```

### Assertions
```pseudo
ASSERT error IS NOT null
```

---

## RTN13c - Deferred ping times out after realtimeRequestTimeout from CONNECTED

| Spec | Requirement |
|------|-------------|
| RTN13c | Fails if HEARTBEAT not received within realtimeRequestTimeout |
| RTN13d | Deferred ping from CONNECTING state |

Tests that a ping deferred from CONNECTING state still times out based on `realtimeRequestTimeout` after the connection becomes CONNECTED (the timeout starts when the HEARTBEAT is actually sent, not when `ping()` is called).

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    SCHEDULE_AFTER(100ms):
      conn.respond_with_success(
        CONNECTED_MESSAGE(connectionId: "conn-id-1", connectionKey: "conn-key-1")
      )
  }
  # No onMessageFromClient — server never responds to HEARTBEAT
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeRequestTimeout: 2000,
  autoConnect: false
))
```

### Test Steps
```pseudo
enable_fake_timers()

client.connect()
ASSERT client.connection.state == ConnectionState.connecting

# Call ping() while CONNECTING
ping_future = client.connection.ping()

# Advance time so connection completes
ADVANCE_TIME(200ms)
AWAIT_STATE client.connection.state == ConnectionState.connected

# Advance time past realtimeRequestTimeout
ADVANCE_TIME(2100)

error = AWAIT_ERROR ping_future
```

### Assertions
```pseudo
ASSERT error IS NOT null
ASSERT error.message CONTAINS "timeout" (case insensitive)
```
