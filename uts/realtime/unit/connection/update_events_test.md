# UPDATE Events Tests (RTN24)

Spec point: `RTN24`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTN24 - CONNECTED message while already CONNECTED emits UPDATE event

**Spec requirement:** A connected client may receive a CONNECTED ProtocolMessage from Ably at any point (typically triggered by reauth). The connectionDetails must override stored details. The Connection should emit an UPDATE event with ConnectionStateChange having both previous and current attributes set to CONNECTED, and reason set to the error member of the CONNECTED ProtocolMessage (if any). The library must NOT emit a CONNECTED event if already connected.

Tests that receiving CONNECTED while CONNECTED emits UPDATE, not CONNECTED.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id-1",
      connectionKey: "connection-key-1",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key-1",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000,
        clientId: "client-123"
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
# Track events
connected_events = []
update_events = []

client.connection.on(ConnectionState.connected, (change) => {
  connected_events.push(change)
})

client.connection.on(ConnectionEvent.update, (change) => {
  update_events.push(change)
})

# Start connection
client.connect()

# Wait for initial CONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds

# Verify initial connection
ASSERT connected_events.length == 1
ASSERT update_events.length == 0

# Server sends another CONNECTED message (e.g., after reauth)
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: CONNECTED,
  connectionId: "connection-id-2",
  connectionKey: "connection-key-2",
  connectionDetails: ConnectionDetails(
    connectionKey: "connection-key-2",
    maxIdleInterval: 20000,  # Different value
    connectionStateTtl: 120000,
    clientId: "client-123"
  )
))

# Wait for event to be processed
WAIT(100)
```

### Assertions

```pseudo
# State remains CONNECTED
ASSERT client.connection.state == ConnectionState.connected

# No additional CONNECTED event was emitted
ASSERT connected_events.length == 1

# UPDATE event was emitted
ASSERT update_events.length == 1

# UPDATE event has correct structure
update_change = update_events[0]
ASSERT update_change.previous == ConnectionState.connected
ASSERT update_change.current == ConnectionState.connected
ASSERT update_change.reason IS null  # No error in this case

# Connection details were updated
ASSERT client.connection.id == "connection-id-2"
ASSERT client.connection.key == "connection-key-2"
```

---

## RTN24 - UPDATE event with error reason

**Spec requirement:** The UPDATE event's reason attribute should be set to the error member of the CONNECTED ProtocolMessage (if any).

Tests that UPDATE events include error information when present.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id-1",
      connectionKey: "connection-key-1",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key-1",
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
# Track UPDATE events
update_events = []

client.connection.on(ConnectionEvent.update, (change) => {
  update_events.push(change)
})

# Start connection
client.connect()

# Wait for CONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds

# Server sends CONNECTED with error (e.g., token was renewed due to expiry)
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: CONNECTED,
  connectionId: "connection-id-2",
  connectionKey: "connection-key-2",
  connectionDetails: ConnectionDetails(
    connectionKey: "connection-key-2",
    maxIdleInterval: 15000,
    connectionStateTtl: 120000
  ),
  error: ErrorInfo(
    code: 40142,
    statusCode: 401,
    message: "Token expired; renewed automatically"
  )
))

# Wait for event to be processed
WAIT(100)
```

### Assertions

```pseudo
# UPDATE event was emitted
ASSERT update_events.length == 1

# UPDATE event has error reason
update_change = update_events[0]
ASSERT update_change.previous == ConnectionState.connected
ASSERT update_change.current == ConnectionState.connected
ASSERT update_change.reason IS NOT null
ASSERT update_change.reason.code == 40142
ASSERT update_change.reason.statusCode == 401
ASSERT update_change.reason.message CONTAINS "Token expired"
```

---

## RTN24 - ConnectionDetails override

**Spec requirement:** The connectionDetails in the ProtocolMessage must override any stored details (see RTN21).

Tests that receiving a new CONNECTED message updates connection details.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id-1",
      connectionKey: "connection-key-1",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key-1",
        maxIdleInterval: 10000,
        connectionStateTtl: 60000,
        maxMessageSize: 16384,
        serverId: "server-1",
        clientId: "client-original"
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
# Start connection
client.connect()

# Wait for CONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds

# Verify initial connection details
initial_id = client.connection.id
initial_key = client.connection.key
ASSERT initial_id == "connection-id-1"
ASSERT initial_key == "connection-key-1"

# Server sends new CONNECTED with different details
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: CONNECTED,
  connectionId: "connection-id-2",
  connectionKey: "connection-key-2",
  connectionDetails: ConnectionDetails(
    connectionKey: "connection-key-2",
    maxIdleInterval: 20000,  # Changed
    connectionStateTtl: 120000,  # Changed
    maxMessageSize: 32768,  # Changed
    serverId: "server-2",  # Changed
    clientId: "client-updated"  # Changed
  )
))

# Wait for update to be processed
WAIT(100)
```

### Assertions

```pseudo
# Connection details were updated
ASSERT client.connection.id == "connection-id-2"
ASSERT client.connection.key == "connection-key-2"

# All connection details should be overridden
# (The exact accessors for these details may vary by implementation)
# Verify that the implementation stores and uses the new values

# State remains CONNECTED
ASSERT client.connection.state == ConnectionState.connected
```

---

## RTN24 - No duplicate CONNECTED event

**Spec requirement:** The library must not emit a CONNECTED event if the client was already connected (see RTN4h).

Tests that only UPDATE events are emitted, not CONNECTED events, when receiving CONNECTED while already connected.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id-1",
      connectionKey: "connection-key-1",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key-1",
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
# Track all events
all_events = []

# Subscribe to all connection events
FOR EACH state IN [ConnectionState.initialized, ConnectionState.connecting, 
                   ConnectionState.connected, ConnectionState.disconnected,
                   ConnectionState.suspended, ConnectionState.closing,
                   ConnectionState.closed, ConnectionState.failed]:
  client.connection.on(state, (change) => {
    all_events.push({type: "state", state: state, change: change})
  })

# Also subscribe to UPDATE
client.connection.on(ConnectionEvent.update, (change) => {
  all_events.push({type: "update", change: change})
})

# Start connection
client.connect()

# Wait for CONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds

# Record event count after initial connection
initial_event_count = all_events.length

# Send multiple CONNECTED messages
FOR i IN [1, 2, 3]:
  mock_ws.active_connection.send_to_client(ProtocolMessage(
    action: CONNECTED,
    connectionId: "connection-id-" + (i + 1),
    connectionKey: "connection-key-" + (i + 1),
    connectionDetails: ConnectionDetails(
      connectionKey: "connection-key-" + (i + 1),
      maxIdleInterval: 15000,
      connectionStateTtl: 120000
    )
  ))
  WAIT(50)
```

### Assertions

```pseudo
# Exactly 3 UPDATE events were added (one per subsequent CONNECTED message)
new_events = all_events[initial_event_count:]
ASSERT new_events.length == 3

# All new events are UPDATE events, not CONNECTED state events
FOR EACH event IN new_events:
  ASSERT event.type == "update"
  ASSERT event.change.previous == ConnectionState.connected
  ASSERT event.change.current == ConnectionState.connected

# No additional CONNECTED state events were emitted
connected_state_events = FILTER all_events WHERE event.type == "state" 
                                              AND event.state == ConnectionState.connected
ASSERT connected_state_events.length == 1  # Only the initial one
```
