# Heartbeat Tests (RTN23)

Spec points: `RTN23`, `RTN23a`, `RTN23b`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTN23a - Disconnect after maxIdleInterval + realtimeRequestTimeout

**Spec requirement:** If no message is received from the server for maxIdleInterval + realtimeRequestTimeout milliseconds, the connection is considered lost and the client transitions to DISCONNECTED state.

Tests that the client disconnects when no server activity is detected.

### Setup

```pseudo
channel_name = "test-RTN23a-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
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

# Start connection
client.connect()

# Wait for CONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds

# Advance time past maxIdleInterval + realtimeRequestTimeout
# = 5000 + 2000 = 7000ms
ADVANCE_TIME(7100)

# Should transition to DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 1 second
```

### Assertions

```pseudo
# Connection transitioned to DISCONNECTED
ASSERT client.connection.state == ConnectionState.disconnected

# Error reason indicates timeout/inactivity
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.message CONTAINS "idle" 
  OR client.connection.errorReason.message CONTAINS "heartbeat"
  OR client.connection.errorReason.message CONTAINS "timeout"
```

---

## RTN23a - HEARTBEAT message resets idle timer

**Spec requirement:** Any message from the server, including HEARTBEAT messages, resets the idle timer.

Tests that receiving HEARTBEAT messages keeps the connection alive.

### Setup

```pseudo
channel_name = "test-RTN23a-heartbeat-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
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

# Start connection
client.connect()

# Wait for CONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.connected

# Advance time (not enough to trigger timeout)
ADVANCE_TIME(2000)  # 2 seconds

# Send HEARTBEAT from server
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: HEARTBEAT
))

# Advance time again (should still be connected)
ADVANCE_TIME(2000)  # Total 4 seconds, but timer reset at 2 seconds

# Connection should still be alive
WAIT(500)

ASSERT client.connection.state == ConnectionState.connected

# Advance time past the new timeout window
ADVANCE_TIME(2100)  # Now 2100ms since last HEARTBEAT

# Should disconnect now
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 1 second
```

### Assertions

```pseudo
# Connection stayed alive after HEARTBEAT
# Then disconnected after no more messages
ASSERT client.connection.state == ConnectionState.disconnected

# Error reason indicates timeout
ASSERT client.connection.errorReason IS NOT null
```

---

## RTN23a - Any protocol message resets idle timer

**Spec requirement:** Any message from the server resets the idle timer, not just HEARTBEAT messages.

Tests that receiving any protocol message (e.g., ACK, MESSAGE) keeps the connection alive.

### Setup

```pseudo
channel_name = "test-RTN23a-message-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
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

# Start connection
client.connect()

# Wait for CONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.connected

# Advance time
ADVANCE_TIME(1500)

# Send ACK message from server
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ACK,
  msgSerial: 0
))

# Advance time again
ADVANCE_TIME(1500)

# Connection should still be alive (timer was reset)
ASSERT client.connection.state == ConnectionState.connected

# Send MESSAGE from server
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

# Should disconnect now
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 1 second
```

### Assertions

```pseudo
# Connection stayed alive with various message types
# Then disconnected after no more messages
ASSERT client.connection.state == ConnectionState.disconnected
```

---

## RTN23b - Client can request heartbeats in query params

**Spec requirement:** The client can request heartbeats by including heartbeats=true in the connection query parameters.

Tests that the client can enable/disable heartbeats via query parameters.

### Setup

```pseudo
connection_urls = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    # Record the connection URL
    connection_urls.push(conn.url)
    
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
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

# Client with default behavior (heartbeats enabled)
client1 = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

# Client with heartbeats explicitly disabled
client2 = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  closeOnUnload: false,  # Or another option that disables heartbeats
  autoConnect: false
))
```

### Test Steps

```pseudo
# Connect first client (default, heartbeats enabled)
client1.connect()

AWAIT_STATE client1.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds

# Check URL includes heartbeats=true
url1 = connection_urls[0]

await client1.close()

# Connect second client (heartbeats disabled)
client2.connect()

AWAIT_STATE client2.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds

# Check URL includes heartbeats=false
url2 = connection_urls[1]
```

### Assertions

```pseudo
# First client requested heartbeats
ASSERT url1.query_params CONTAINS "heartbeats=true"
  OR "heartbeats" NOT IN url1.query_params  # Default is true

# Second client disabled heartbeats
ASSERT url2.query_params CONTAINS "heartbeats=false"
  OR (implementation specific way to disable)
```

---

## RTN23b - Server respects heartbeats=false

**Spec requirement:** If the client sends heartbeats=false, the server should not send HEARTBEAT messages and the client should not expect them.

Tests that disabling heartbeats prevents timeout when no HEARTBEATs are sent.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 2000,  # 2 seconds
        connectionStateTtl: 120000
      )
    ))
    # Server sends no HEARTBEAT messages
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  # Configure to disable heartbeats (implementation-specific)
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

# Start connection
client.connect()

# Wait for CONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.connected

# Advance time well past maxIdleInterval
ADVANCE_TIME(10000)  # 10 seconds

# Connection should remain CONNECTED (no heartbeat expectation)
# Note: This test may vary by implementation - some SDKs always
# expect some server activity even with heartbeats=false
```

### Assertions

```pseudo
# Connection behavior when heartbeats disabled is implementation-specific
# Either:
# A) Connection stays alive indefinitely without messages
# B) Connection has a much longer timeout
# C) Connection still times out but with different threshold

# Verify the implementation's documented behavior
ASSERT client.connection.state IN [ConnectionState.connected, ConnectionState.disconnected]
```

---

## Timer Mocking Note

These tests use `enable_fake_timers()` and `ADVANCE_TIME()` to avoid slow tests. Implementations should:

1. **Prefer fake timers** (JavaScript Jest, Python freezegun, Go testing.Clock)
2. **Or use dependency injection** for timer/clock interfaces
3. **Or use very short timeout values** (e.g., 50ms instead of 5s)
4. **Last resort:** Use actual delays with generous test timeouts

See the "Timer Mocking" section in `write-test-spec.md` for detailed guidance.
