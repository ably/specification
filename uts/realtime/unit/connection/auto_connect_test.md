# Connection Auto Connect Tests (RTN3)

Spec points: `RTN3`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## Purpose

When the `autoConnect` option is true (the default), a connection should be
initiated immediately when the Realtime client is created. When false, no
connection should be made until `connect()` is explicitly called.

---

## RTN3 - autoConnect true initiates connection immediately

**Spec requirement:** If connection option `autoConnect` is true, a connection is
initiated immediately.

Tests that creating a Realtime client with `autoConnect: true` (or default)
initiates a WebSocket connection without requiring an explicit `connect()` call.

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
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)
```

### Test Steps
```pseudo
# Create client with default autoConnect (true) — do NOT call connect()
client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret"
))

# Wait for connection to complete
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds
```

### Assertions
```pseudo
# Connection was established automatically
ASSERT client.connection.state == ConnectionState.connected
ASSERT client.connection.id == "connection-id"
```

---

## RTN3 - autoConnect false does not initiate connection

**Spec requirement:** Otherwise a connection is only initiated following an explicit
call to `connect()`.

Tests that creating a Realtime client with `autoConnect: false` does not initiate
a WebSocket connection.

### Setup
```pseudo
connection_attempted = false

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempted = true
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
```

### Test Steps
```pseudo
# Create client with autoConnect: false
client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

# Wait briefly to confirm no connection attempt is made
WAIT(500)
```

### Assertions
```pseudo
# No connection was attempted
ASSERT connection_attempted == false

# State remains INITIALIZED
ASSERT client.connection.state == ConnectionState.initialized
```

---

## RTN3 - explicit connect after autoConnect false

**Spec requirement:** A connection is only initiated following an explicit call to
`connect()`.

Tests that after creating a client with `autoConnect: false`, calling `connect()`
initiates the connection.

### Setup
```pseudo
connection_attempted = false

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempted = true
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
```

### Test Steps
```pseudo
# Create client with autoConnect: false
client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

# Verify no connection yet
ASSERT client.connection.state == ConnectionState.initialized
ASSERT connection_attempted == false

# Explicitly connect
client.connect()

# Wait for connection to complete
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds
```

### Assertions
```pseudo
# Connection was established after explicit connect()
ASSERT connection_attempted == true
ASSERT client.connection.state == ConnectionState.connected
```
