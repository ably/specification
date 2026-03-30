# Realtime Connection Lifecycle Integration Tests

Spec points: `RTN4b`, `RTN4c`, `RTN11`, `RTN12`, `RTN21`

## Test Type
Integration test against Ably Sandbox endpoint

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox-rest.ably.io`.

### App Provisioning

```pseudo
BEFORE ALL TESTS:
  # Provision test app
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json
  
  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  # Clean up test app
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

---

## RTN4b, RTN21 - Successful connection establishment

| Spec | Requirement |
|------|-------------|
| RTN4b | When a connection is initiated, it transitions INITIALIZED → CONNECTING → CONNECTED |
| RTN21 | Connections are initiated via WebSocket transport |

Tests that a Realtime client can successfully connect to Ably via WebSocket.

### Setup

```pseudo
client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
```

### Test Steps

```pseudo
# Client starts in INITIALIZED state
ASSERT client.connection.state == ConnectionState.initialized

# Start connection
client.connect()

# Wait for CONNECTING state
AWAIT_STATE client.connection.state == ConnectionState.connecting

# Wait for CONNECTED state (with timeout)
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds

# Verify connection properties are set
ASSERT client.connection.id IS NOT null
ASSERT client.connection.key IS NOT null
```

### Assertions

```pseudo
# Final state is CONNECTED
ASSERT client.connection.state == ConnectionState.connected

# Connection ID is a non-empty string
ASSERT client.connection.id matches "[a-zA-Z0-9_-]+"

# Connection key is a non-empty string
ASSERT client.connection.key matches "[a-zA-Z0-9_!-]+"

# No error reason
ASSERT client.connection.errorReason IS null
```

---

## RTN4c, RTN12, RTN12a - Graceful connection close

| Spec | Requirement |
|------|-------------|
| RTN4c | Normal disconnection: CONNECTED → CLOSING → CLOSED |
| RTN12 | Connection.close() initiates close sequence |
| RTN12a | Sends CLOSE message and waits for confirmation |

Tests that a connected client can gracefully close the connection.

### Setup

```pseudo
client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

# Establish connection first
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Test Steps

```pseudo
# Close the connection
client.connection.close()

# Should transition through CLOSING
AWAIT_STATE client.connection.state == ConnectionState.closing

# Should reach CLOSED
AWAIT_STATE client.connection.state == ConnectionState.closed
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# Final state is CLOSED
ASSERT client.connection.state == ConnectionState.closed

# No error reason (clean close)
ASSERT client.connection.errorReason IS null

# Connection ID is cleared
ASSERT client.connection.id IS null

# Connection key is cleared
ASSERT client.connection.key IS null
```

---

## RTN11, RTN4b - Connect and reconnect cycle

| Spec | Requirement |
|------|-------------|
| RTN11 | Connection.connect() explicitly opens connection |
| RTN4b | Each connection follows CONNECTING → CONNECTED flow |

Tests that a client can be closed and reconnected multiple times.

### Setup

```pseudo
client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false  # Don't connect automatically
))
```

### Test Steps

```pseudo
# Initial state
ASSERT client.connection.state == ConnectionState.initialized

# First connection
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

first_connection_id = client.connection.id

# Close connection
client.connection.close()
AWAIT_STATE client.connection.state == ConnectionState.closed

# Reconnect
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

second_connection_id = client.connection.id
```

### Assertions

```pseudo
# Successfully connected twice
ASSERT second_connection_id IS NOT null

# Each connection gets a new ID (not a resume)
ASSERT first_connection_id != second_connection_id

# No errors
ASSERT client.connection.errorReason IS null
```

---

## Integration Test Notes

### Timeout Handling

All `AWAIT_STATE` calls should have reasonable timeouts:
- CONNECTING → CONNECTED: 10 seconds (allows for auth + transport setup)
- CONNECTED → CLOSING: 1 second (immediate transition)
- CLOSING → CLOSED: 5 seconds (allows for CLOSE message roundtrip)

### Error Handling

If any connection fails to reach CONNECTED state:
- Log the connection errorReason
- Log any emitted state changes with reasons
- Fail the test with diagnostic information

### Cleanup

Always close connections in test cleanup:

```pseudo
AFTER EACH TEST:
  IF client IS NOT null AND client.connection.state IN [CONNECTED, CONNECTING]:
    client.connection.close()
    # Wait briefly for close to complete
    AWAIT_STATE client.connection.state == ConnectionState.closed
      WITH timeout: 10 seconds
```
