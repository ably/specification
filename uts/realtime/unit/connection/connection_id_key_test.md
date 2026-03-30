# Connection ID and Key Tests

Spec points: `RTN8`, `RTN8a`, `RTN8b`, `RTN8c`, `RTN9`, `RTN9a`, `RTN9b`, `RTN9c`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTN8a - Connection ID is unset until connected

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
```

---

## RTN9a - Connection key is unset until connected

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
```

---

## RTN8b - Connection ID is unique per connection

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
```

---

## RTN9b - Connection key is unique per connection

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
```

---

## RTN8c - Connection ID is null in terminal/non-connected states

| Spec | Requirement |
|------|-------------|
| RTN8c | Is null when the SDK is in CLOSED, CLOSING, FAILED, or SUSPENDED states |

Tests that `connection.id` is cleared when the connection enters CLOSED or FAILED states.

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
```

---

## RTN9c - Connection key is null in terminal/non-connected states

| Spec | Requirement |
|------|-------------|
| RTN9c | Is null when the SDK is in CLOSED, CLOSING, FAILED, or SUSPENDED states |

Tests that `connection.key` is cleared when the connection enters CLOSED or FAILED states.

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
```

---

## RTN8c, RTN9c - ID and key null after FAILED

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
```

---

## RTN8c, RTN9c - ID and key null after SUSPENDED

**Spec requirement:** Connection ID and key are null in SUSPENDED state.

Tests that both `connection.id` and `connection.key` are null when the connection transitions to SUSPENDED.

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
```

### Assertions
```pseudo
ASSERT client.connection.id IS null
ASSERT client.connection.key IS null
```
