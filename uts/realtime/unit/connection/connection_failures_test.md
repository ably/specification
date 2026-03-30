# Connection Failures When Connected Tests (RTN15)

Spec points: `RTN15`, `RTN15a`, `RTN15b`, `RTN15c`, `RTN15d`, `RTN15e`, `RTN15g`, `RTN15h`, `RTN15j`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTN15h1 - DISCONNECTED with token error, no means to renew

**Spec requirement:** If a DISCONNECTED message contains a token error and the library cannot renew the token, transition to FAILED state.

Tests that non-renewable token errors cause permanent failure.

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

# Use token directly (no way to renew)
client = Realtime(options: ClientOptions(
  token: "some_token_string",
  autoConnect: false
))
```

### Test Steps

```pseudo
# Connect successfully
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Get reference to the WebSocket connection
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection

# Server sends DISCONNECTED with token error and closes connection
ws_connection.send_to_client_and_close(ProtocolMessage(
  action: DISCONNECTED,
  error: ErrorInfo(
    code: 40142,
    statusCode: 401,
    message: "Token expired"
  )
))

# Should transition to FAILED (no means to renew)
AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 2 seconds
```

### Assertions

```pseudo
# Connection transitioned to FAILED
ASSERT client.connection.state == ConnectionState.failed

# Error reason is set
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 40142
ASSERT client.connection.errorReason.statusCode == 401
```

---

## RTN15h2 - DISCONNECTED with token error, renewable token

**Spec requirement:** If a DISCONNECTED message contains a token error and the library can renew the token, transition to CONNECTING, obtain new token, and attempt resume.

Tests that renewable token errors trigger token renewal and reconnection.

### Setup

```pseudo
token_request_count = 0
connection_attempt_count = 0

# Mock HTTP for token requests
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    IF req.url.path CONTAINS "/keys/":
      token_request_count++
      req.respond_with(200, {
        "token": "renewed_token_" + token_request_count,
        "keyName": "appId.keyId",
        "issued": time_now(),
        "expires": time_now() + 3600000,
        "capability": "{\"*\":[\"*\"]}"
      })
  }
)
install_mock(mock_http)

# Mock WebSocket
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    conn.respond_with_success()
    
    IF connection_attempt_count == 1:
      # First connection succeeds
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-1",
        connectionKey: "key-1",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-1",
          maxIdleInterval: 15000,
          connectionStateTtl: 120000
        )
      ))
    ELSE:
      # Resume after token renewal succeeds
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-1",  # Same ID = successful resume
        connectionKey: "key-1-renewed",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-1-renewed",
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
# Connect successfully
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

first_connection_id = client.connection.id
first_connection_key = client.connection.key

# Get WebSocket connection
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection

# Server sends DISCONNECTED with token error and closes connection
ws_connection.send_to_client_and_close(ProtocolMessage(
  action: DISCONNECTED,
  error: ErrorInfo(
    code: 40142,
    statusCode: 401,
    message: "Token expired"
  )
))

# Should transition to CONNECTING (to renew and resume)
AWAIT_STATE client.connection.state == ConnectionState.connecting
  WITH timeout: 2 seconds

# Should reconnect with renewed token
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# Successfully reconnected
ASSERT client.connection.state == ConnectionState.connected

# Token was renewed
ASSERT token_request_count == 2  # Initial + renewal

# Connection was resumed (same ID)
ASSERT client.connection.id == first_connection_id

# Connection key was updated
ASSERT client.connection.key != first_connection_key
ASSERT client.connection.key == "key-1-renewed"
```

---

## RTN15h2 - DISCONNECTED with token error, renewal fails

**Spec requirement:** If token renewal or reconnection fails after DISCONNECTED with token error, transition to DISCONNECTED with errorReason set.

Tests that failed token renewal leads to DISCONNECTED state.

### Setup

```pseudo
# Mock HTTP for token requests (returns error)
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    IF req.url.path CONTAINS "/keys/":
      req.respond_with(401, {
        "error": {
          "code": 40101,
          "statusCode": 401,
          "message": "Invalid credentials"
        }
      })
  }
)
install_mock(mock_http)

# Mock WebSocket
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-1",
      connectionKey: "key-1",
      connectionDetails: ConnectionDetails(
        connectionKey: "key-1",
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
# Connect successfully
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Get WebSocket connection
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection

# Server sends DISCONNECTED with token error and closes connection
ws_connection.send_to_client_and_close(ProtocolMessage(
  action: DISCONNECTED,
  error: ErrorInfo(
    code: 40142,
    statusCode: 401,
    message: "Token expired"
  )
))

# Should transition to CONNECTING (to attempt renewal)
AWAIT_STATE client.connection.state == ConnectionState.connecting

# Renewal fails, should transition to DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# Connection is DISCONNECTED (will retry later)
ASSERT client.connection.state == ConnectionState.disconnected

# Error reason is set (from token renewal failure)
ASSERT client.connection.errorReason IS NOT null
```

---

## RTN15h3 - DISCONNECTED with non-token error

**Spec requirement:** If a DISCONNECTED message contains an error other than a token error, initiate immediate reconnect with resume attempt.

Tests that non-token disconnection triggers immediate resume.

### Setup

```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    
    IF connection_attempt_count == 1:
      # First connection succeeds
      conn.respond_with_success()
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-1",
        connectionKey: "key-1",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-1",
          maxIdleInterval: 15000,
          connectionStateTtl: 120000
        )
      ))
    ELSE:
      # Resume succeeds
      conn.respond_with_success()
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-1",  # Same ID = resumed
        connectionKey: "key-1",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-1",
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
# Connect successfully
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

original_connection_id = client.connection.id

# Get WebSocket connection
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection

# Server sends DISCONNECTED with non-token error and closes connection
ws_connection.send_to_client_and_close(ProtocolMessage(
  action: DISCONNECTED,
  error: ErrorInfo(
    code: 80003,
    statusCode: 503,
    message: "Service unavailable"
  )
))

# Should transition to CONNECTING immediately (no token renewal)
AWAIT_STATE client.connection.state == ConnectionState.connecting

# Should reconnect and resume
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# Successfully reconnected
ASSERT client.connection.state == ConnectionState.connected

# Connection was resumed (same ID)
ASSERT client.connection.id == original_connection_id

# Two connection attempts total
ASSERT connection_attempt_count == 2

# Second connection attempt included resume parameter
ASSERT mock_ws.events[1].url.query_params["resume"] == "key-1"
```

---

## RTN15j - ERROR protocol message with empty channel

**Spec requirement:** If an ERROR ProtocolMessage with empty channel is received when CONNECTED, transition to FAILED state and set errorReason.

Tests that fatal connection errors cause FAILED state.

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

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Test Steps

```pseudo
# Connect successfully
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Get WebSocket connection
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection

# Server sends ERROR with empty channel (connection-level error) and closes connection
ws_connection.send_to_client_and_close(ProtocolMessage(
  action: ERROR,
  channel: null,  # Empty = connection-level error
  error: ErrorInfo(
    code: 50000,
    statusCode: 500,
    message: "Internal error"
  )
))

# Should transition to FAILED
AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 2 seconds
```

### Assertions

```pseudo
# Connection transitioned to FAILED
ASSERT client.connection.state == ConnectionState.failed

# Error reason is set
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 50000
ASSERT client.connection.errorReason.statusCode == 500
```

---

## RTN15a - Unexpected transport disconnect

**Spec requirement:** If transport is disconnected unexpectedly (without DISCONNECTED or ERROR), respond as if receiving non-token DISCONNECTED message.

Tests that transport failures trigger resume attempts.

### Setup

```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    
    IF connection_attempt_count == 1:
      # First connection succeeds
      conn.respond_with_success()
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-1",
        connectionKey: "key-1",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-1",
          maxIdleInterval: 15000,
          connectionStateTtl: 120000
        )
      ))
    ELSE:
      # Resume succeeds
      conn.respond_with_success()
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-1",  # Same ID = resumed
        connectionKey: "key-1",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-1",
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
# Connect successfully
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

original_connection_id = client.connection.id

# Get WebSocket connection
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection

# Simulate unexpected disconnect (no protocol message)
ws_connection.simulate_disconnect()

# Should transition to DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 1 second

# Should automatically attempt reconnect
AWAIT_STATE client.connection.state == ConnectionState.connecting

# Should resume successfully
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# Successfully reconnected
ASSERT client.connection.state == ConnectionState.connected

# Connection was resumed (same ID)
ASSERT client.connection.id == original_connection_id

# Two connection attempts made
ASSERT connection_attempt_count == 2
```

---

## RTN15b, RTN15c6 - Successful resume

| Spec | Requirement |
|------|-------------|
| RTN15b | Resume is attempted with connectionKey in query parameter |
| RTN15c6 | Successful resume indicated by same connectionId in CONNECTED |

Tests that connection resume works correctly.

### Setup

```pseudo
connection_attempt_count = 0
captured_connection_attempts = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    captured_connection_attempts.append(conn)
    
    conn.respond_with_success()
    
    IF connection_attempt_count == 1:
      # Initial connection
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-1",
        connectionKey: "key-1",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-1",
          maxIdleInterval: 15000,
          connectionStateTtl: 120000
        )
      ))
    ELSE:
      # Resume succeeds (same connectionId)
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-1",  # Same ID indicates successful resume
        connectionKey: "key-1-updated",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-1-updated",
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
# Initial connection
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

original_connection_id = client.connection.id
ASSERT original_connection_id == "connection-1"

# Force disconnect
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection
ws_connection.simulate_disconnect()

# Wait for reconnection
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# Connection resumed (same ID)
ASSERT client.connection.id == "connection-1"

# Connection key was updated (RTN15e)
ASSERT client.connection.key == "key-1-updated"

# Second connection attempt included resume parameter (RTN15b1)
ASSERT captured_connection_attempts[1].url.query_params["resume"] == "key-1"

# Two connection attempts total
ASSERT connection_attempt_count == 2
```

---

## RTN15c7 - Failed resume (new connectionId)

**Spec requirement:** If resume fails, server sends CONNECTED with new connectionId and error. Client should reset msgSerial to 0.

Tests that failed resume is handled correctly.

### Setup

```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    
    conn.respond_with_success()
    
    IF connection_attempt_count == 1:
      # Initial connection
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-1",
        connectionKey: "key-1",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-1",
          maxIdleInterval: 15000,
          connectionStateTtl: 120000
        )
      ))
    ELSE:
      # Resume failed (new connectionId + error)
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-2",  # Different ID = failed resume
        connectionKey: "key-2",
        error: ErrorInfo(
          code: 80008,
          statusCode: 400,
          message: "Unable to recover connection"
        ),
        connectionDetails: ConnectionDetails(
          connectionKey: "key-2",
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
# Initial connection
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

original_connection_id = client.connection.id

# Force disconnect
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection
ws_connection.simulate_disconnect()

# Wait for reconnection
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# New connection (different ID)
ASSERT client.connection.id == "connection-2"
ASSERT client.connection.id != original_connection_id

# Connection key updated
ASSERT client.connection.key == "key-2"

# Error reason set (indicates why resume failed)
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 80008

# Connection is still CONNECTED (despite error)
ASSERT client.connection.state == ConnectionState.connected
```

---

## RTN15e - Connection key updated on resume

**Spec requirement:** When connection is resumed, Connection.key may change and is provided in CONNECTED message connectionDetails.

Tests that connection key is updated after resume.

This is covered by the RTN15b, RTN15c6 test above. The key assertion is:

```pseudo
ASSERT client.connection.key == "key-1-updated"
```

---

## RTN15g - Connection state cleared after connectionStateTtl

**Spec requirement:** If disconnected longer than connectionStateTtl, don't attempt resume. Clear local state and make fresh connection.

Tests that stale connections don't attempt resume.

### Setup

```pseudo
connection_attempt_count = 0
captured_connection_attempts = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    captured_connection_attempts.append(conn)
    
    conn.respond_with_success()
    
    IF connection_attempt_count == 1:
      # Initial connection
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-1",
        connectionKey: "key-1",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-1",
          maxIdleInterval: 15000,
          connectionStateTtl: 5000  # 5 seconds TTL
        )
      ))
    ELSE:
      # Fresh connection (no resume)
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-2",  # New ID
        connectionKey: "key-2",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-2",
          maxIdleInterval: 15000,
          connectionStateTtl: 120000
        )
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  disconnectedRetryTimeout: 1000,
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

# Initial connection
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

original_connection_id = client.connection.id

# Force disconnect
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection
ws_connection.simulate_disconnect()

# Wait for DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Advance time past connectionStateTtl
ADVANCE_TIME(6000)  # Past the 5s TTL

# Trigger reconnection
ADVANCE_TIME(1000)  # Past disconnectedRetryTimeout

# Wait for reconnection
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# New connection (different ID, not resumed)
ASSERT client.connection.id == "connection-2"
ASSERT client.connection.id != original_connection_id

# Second connection did NOT include resume parameter
ASSERT "resume" NOT IN captured_connection_attempts[1].url.query_params

# Fresh connection key
ASSERT client.connection.key == "key-2"
```

---

## RTN15c5 - ERROR with token error during resume

**Spec requirement:** If resume attempt receives ERROR with token error, follow RTN15h spec for token error handling.

Tests that token errors during resume trigger renewal.

### Setup

```pseudo
token_request_count = 0
connection_attempt_count = 0

# Mock HTTP for token requests
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    IF req.url.path CONTAINS "/keys/":
      token_request_count++
      req.respond_with(200, {
        "token": "renewed_token",
        "keyName": "appId.keyId",
        "issued": time_now(),
        "expires": time_now() + 3600000,
        "capability": "{\"*\":[\"*\"]}"
      })
  }
)
install_mock(mock_http)

# Mock WebSocket
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    
    conn.respond_with_success()
    
    IF connection_attempt_count == 1:
      # Initial connection
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-1",
        connectionKey: "key-1",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-1",
          maxIdleInterval: 15000,
          connectionStateTtl: 120000
        )
      ))
    ELSE IF connection_attempt_count == 2:
      # Resume attempt fails with token error
      conn.send_to_client(ProtocolMessage(
        action: ERROR,
        error: ErrorInfo(
          code: 40142,
          statusCode: 401,
          message: "Token expired"
        )
      ))
    ELSE:
      # Retry with renewed token succeeds
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-2",
        connectionKey: "key-2",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-2",
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
# Initial connection
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Force disconnect (will trigger resume attempt)
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection
ws_connection.simulate_disconnect()

# Wait for final CONNECTED (after token renewal)
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
```

### Assertions

```pseudo
# Successfully reconnected after token renewal
ASSERT client.connection.state == ConnectionState.connected

# Token was renewed
ASSERT token_request_count == 2  # Initial + renewal

# Three connection attempts (initial, failed resume, retry with new token)
ASSERT connection_attempt_count == 3
```

---

## RTN15c4 - ERROR with fatal error during resume

**Spec requirement:** If resume attempt receives ERROR with fatal error, transition to FAILED state.

Tests that fatal errors during resume cause permanent failure.

### Setup

```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    
    conn.respond_with_success()
    
    IF connection_attempt_count == 1:
      # Initial connection
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-1",
        connectionKey: "key-1",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-1",
          maxIdleInterval: 15000,
          connectionStateTtl: 120000
        )
      ))
    ELSE:
      # Resume attempt fails with fatal error
      conn.send_to_client(ProtocolMessage(
        action: ERROR,
        error: ErrorInfo(
          code: 50000,
          statusCode: 500,
          message: "Internal server error"
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
# Initial connection
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Force disconnect (will trigger resume attempt)
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection
ws_connection.simulate_disconnect()

# Wait for FAILED state
AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# Connection transitioned to FAILED
ASSERT client.connection.state == ConnectionState.failed

# Error reason is set
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 50000

# Only two connection attempts (no retry after fatal error)
ASSERT connection_attempt_count == 2
```
