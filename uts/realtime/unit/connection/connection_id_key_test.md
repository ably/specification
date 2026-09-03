# Connection ID and Key Tests

Spec points: `RTN8`, `RTN8a`, `RTN8b`, `RTN8c`, `RTN8d`, `RTN9`, `RTN9a`, `RTN9b`, `RTN9c`, `RTN9d`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTN8a - Connection ID is unset until connected

**Test ID**: `realtime/unit/RTN8a/id-unset-until-connected-0`

| Spec | Requirement |
|------|-------------|
| RTN8 | `Connection#id` attribute |
| RTN8a | Is unset until connected |

Tests that `connection.id` is null before the connection is established and is set after CONNECTED.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    CONNECTED_MESSAGE(connectionId: "unique-conn-id-1", connectionKey: "conn-key-1")
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
# Before connecting, id should be null
ASSERT client.connection.id IS null

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions
```pseudo
ASSERT client.connection.id == "unique-conn-id-1"
CLOSE_CLIENT(client)
```

---

## RTN9a - Connection key is unset until connected

**Test ID**: `realtime/unit/RTN9a/key-unset-until-connected-0`

| Spec | Requirement |
|------|-------------|
| RTN9 | `Connection#key` attribute |
| RTN9a | Is unset until connected |

Tests that `connection.key` is null before the connection is established and is set after CONNECTED.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    CONNECTED_MESSAGE(connectionId: "unique-conn-id-1", connectionKey: "conn-key-1")
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
# Before connecting, key should be null
ASSERT client.connection.key IS null

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions
```pseudo
ASSERT client.connection.key == "conn-key-1"
CLOSE_CLIENT(client)
```

---

## RTN8b - Connection ID is unique per connection

**Test ID**: `realtime/unit/RTN8b/id-unique-per-connection-0`

| Spec | Requirement |
|------|-------------|
| RTN8b | Is a unique string provided by Ably. Multiple connected clients have unique connection IDs |

Tests that two separate clients receive different connection IDs from the server.

### Setup
```pseudo
connection_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_count++
    conn.respond_with_success(
      CONNECTED_MESSAGE(
        connectionId: "conn-id-${connection_count}",
        connectionKey: "conn-key-${connection_count}"
      )
    )
  }
)
install_mock(mock_ws)

client1 = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

client2 = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Test Steps
```pseudo
client1.connect()
AWAIT_STATE client1.connection.state == ConnectionState.connected

client2.connect()
AWAIT_STATE client2.connection.state == ConnectionState.connected
```

### Assertions
```pseudo
ASSERT client1.connection.id != client2.connection.id
ASSERT client1.connection.id == "conn-id-1"
ASSERT client2.connection.id == "conn-id-2"
CLOSE_CLIENT(client1)
CLOSE_CLIENT(client2)
```

---

## RTN9b - Connection key is unique per connection

**Test ID**: `realtime/unit/RTN9b/key-unique-per-connection-0`

| Spec | Requirement |
|------|-------------|
| RTN9b | Is a unique private connection key. Multiple connected clients have unique connection keys |

Tests that two separate clients receive different connection keys from the server.

### Setup
```pseudo
connection_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_count++
    conn.respond_with_success(
      CONNECTED_MESSAGE(
        connectionId: "conn-id-${connection_count}",
        connectionKey: "conn-key-${connection_count}"
      )
    )
  }
)
install_mock(mock_ws)

client1 = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

client2 = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Test Steps
```pseudo
client1.connect()
AWAIT_STATE client1.connection.state == ConnectionState.connected

client2.connect()
AWAIT_STATE client2.connection.state == ConnectionState.connected
```

### Assertions
```pseudo
ASSERT client1.connection.key != client2.connection.key
ASSERT client1.connection.key == "conn-key-1"
ASSERT client2.connection.key == "conn-key-2"
CLOSE_CLIENT(client1)
CLOSE_CLIENT(client2)
```

---

## RTN8d - Connection ID is null in terminal/non-connected states

**Test ID**: `realtime/unit/RTN8d/id-null-after-closed-0`

| Spec | Requirement |
|------|-------------|
| RTN8d | Is null when the SDK is in the CLOSED, CLOSING, or FAILED states |

Tests that `connection.id` is cleared when the connection enters CLOSED or FAILED states. (As of specification version 6.1.0, RTN8c has been replaced by RTN8d: the id is no longer cleared in the SUSPENDED state.)

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
ASSERT client.connection.id == "conn-id-1"

# Close the connection
AWAIT client.close()
AWAIT_STATE client.connection.state == ConnectionState.closed
```

### Assertions
```pseudo
ASSERT client.connection.id IS null
CLOSE_CLIENT(client)
```

---

## RTN9d - Connection key is null in terminal/non-connected states

**Test ID**: `realtime/unit/RTN9d/key-null-after-closed-0`

| Spec | Requirement |
|------|-------------|
| RTN9d | Is null when the SDK is in the CLOSED, CLOSING, or FAILED states |

Tests that `connection.key` is cleared when the connection enters CLOSED or FAILED states. (As of specification version 6.1.0, RTN9c has been replaced by RTN9d: the key is no longer cleared in the SUSPENDED state.)

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
ASSERT client.connection.key == "conn-key-1"

# Close the connection
AWAIT client.close()
AWAIT_STATE client.connection.state == ConnectionState.closed
```

### Assertions
```pseudo
ASSERT client.connection.key IS null
CLOSE_CLIENT(client)
```

---

## RTN8d, RTN9d - ID and key null after FAILED

**Test ID**: `realtime/unit/RTN8d/id-key-null-after-failed-1`

**Spec requirement:** Connection ID and key are null in FAILED state.

Tests that both `connection.id` and `connection.key` are cleared when the connection transitions to FAILED (e.g. due to a fatal error).

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
```

### Assertions
```pseudo
ASSERT client.connection.id IS null
ASSERT client.connection.key IS null
CLOSE_CLIENT(client)
```

---

## RTN8d, RTN9d - ID and key retained in SUSPENDED

**Test ID**: `realtime/unit/RTN8d/id-key-retained-in-suspended-2`

**Spec requirement:** Connection ID and key are retained in the SUSPENDED state.

As of specification version 6.1.0 (RTN8d/RTN9d, replacing RTN8c/RTN9c) the connection id and key are cleared only in the terminal states (CLOSED, CLOSING, FAILED). They are retained through SUSPENDED, since the client always attempts to resume on reconnecting (RTN14h) and lets the server decide whether continuity can be preserved.

Tests that both `connection.id` and `connection.key` are retained when the connection transitions to SUSPENDED.

### Setup
```pseudo
enable_fake_timers()

# Connect successfully on the first attempt, then refuse all reconnection
# attempts so the connection ends up suspended.
attempt = 0
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    IF attempt == 0 THEN
      conn.respond_with_success(
        CONNECTED_MESSAGE(connectionId: "conn-id-1", connectionKey: "conn-key-1")
      )
    ELSE
      conn.respond_with_refused()
    END
    attempt = attempt + 1
  }
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
AWAIT_STATE client.connection.state == ConnectionState.connected
ASSERT client.connection.id == "conn-id-1"
ASSERT client.connection.key == "conn-key-1"

# Drop the transport; subsequent attempts are refused, moving to DISCONNECTED
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Advance past connectionStateTtl to reach SUSPENDED
ADVANCE_TIME(121s)
AWAIT_STATE client.connection.state == ConnectionState.suspended
```

### Assertions
```pseudo
# RTN8d, RTN9d: id and key are retained, not cleared
ASSERT client.connection.id == "conn-id-1"
ASSERT client.connection.key == "conn-key-1"
CLOSE_CLIENT(client)
```
