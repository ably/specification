# Connection errorReason Tests (RTN25)

Spec point: `RTN25`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTN25 - errorReason set on connection errors

**Spec requirement:** Connection#errorReason attribute is an optional ErrorInfo object which is set by the library when an error occurs on the connection, as described by RSA4c1, RSA4d, RTN11d, RTN14a, RTN14b, RTN14e, RTN14g, RTN15c7, RTN15c4, RTN15d, RTN15h, RTN15i, RTN16e.

Tests that errorReason is populated correctly across various error scenarios.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client_and_close(ProtocolMessage(
      action: ERROR,
      error: ErrorInfo(
        code: 40005,
        statusCode: 400,
        message: "Invalid API key"
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "invalid.key:secret",
  autoConnect: false
))
```

### Test Steps

```pseudo
# Initially errorReason should be null
ASSERT client.connection.errorReason IS null

# Start connection
client.connect()

# Wait for FAILED state
AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# errorReason is set with error details
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 40005
ASSERT client.connection.errorReason.statusCode == 400
ASSERT client.connection.errorReason.message == "Invalid API key"
CLOSE_CLIENT(client)
```

---

## RTN25 - errorReason on DISCONNECTED state (RTN14e)

**Spec requirement:** errorReason is set when connection enters DISCONNECTED state due to connection failure.

Tests that errorReason is populated when transitioning to DISCONNECTED.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    # Connection attempt fails
    conn.respond_with_refused()
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

# Wait for DISCONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# errorReason is set
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.message IS NOT null

# Error indicates connection failure
# (Exact error code/message depends on implementation)
CLOSE_CLIENT(client)
```

---

## RTN25 - errorReason on SUSPENDED state (RTN14e)

**Spec requirement:** errorReason is updated when connection enters SUSPENDED state after connectionStateTtl expires.

Tests that errorReason reflects suspension reason.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    # All connection attempts fail
    conn.respond_with_refused()
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  disconnectedRetryTimeout: 500,
  autoConnect: false
))

DEFAULT_CONNECTION_STATE_TTL = 5000  # 5 seconds
```

### Test Steps

```pseudo
enable_fake_timers()

# Start connection (will fail)
client.connect()

# Wait for DISCONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Advance time past connectionStateTtl
ADVANCE_TIME(DEFAULT_CONNECTION_STATE_TTL + 100)

# Wait for SUSPENDED state
AWAIT_STATE client.connection.state == ConnectionState.suspended
  WITH timeout: 1 second
```

### Assertions

```pseudo
# errorReason is set and indicates suspension
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.message IS NOT null

# Error should indicate timeout or suspension reason
# (Exact error code/message depends on implementation)
CLOSE_CLIENT(client)
```

---

## RTN25 - errorReason on token errors (RTN14b, RTN15h)

**Spec requirement:** errorReason is set when token errors occur during connection or while connected.

Tests that errorReason captures token-related errors.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
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
install_mock(mock_ws)

# Use token directly (no way to renew)
client = Realtime(options: ClientOptions(
  token: "expired_token",
  autoConnect: false
))
```

### Test Steps

```pseudo
# Start connection
client.connect()

# Wait for DISCONNECTED state (can't renew token)
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# errorReason contains token error details
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 40142
ASSERT client.connection.errorReason.statusCode == 401
ASSERT client.connection.errorReason.message CONTAINS "Token"
CLOSE_CLIENT(client)
```

---

## RTN25 - errorReason cleared on successful connection

**Spec requirement:** errorReason should be cleared when connection successfully recovers.

Tests that errorReason is reset after successful connection following a failure.

### Setup

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
  disconnectedRetryTimeout: 100,
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

# Start connection (will fail initially)
client.connect()

# Wait for DISCONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 5 seconds

# errorReason should be set after failure
ASSERT client.connection.errorReason IS NOT null
failure_error = client.connection.errorReason

# Advance time to trigger retry
ADVANCE_TIME(150)

# Wait for CONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# errorReason should be cleared after successful connection
# Note: Specification doesn't explicitly require this, but it's common practice
# Some implementations may keep the last error for debugging purposes
# Verify implementation behavior:

# Either:
# A) errorReason is cleared on successful connection
ASSERT client.connection.errorReason IS null

# Or:
# B) errorReason is kept but clearly not relevant to current state
# (Implementation-specific behavior)
CLOSE_CLIENT(client)
```

---

## RTN25 - errorReason on protocol-level ERROR message (RTN14g)

**Spec requirement:** errorReason is set when ERROR ProtocolMessage with empty channel is received.

Tests that connection-level protocol errors populate errorReason.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client_and_close(ProtocolMessage(
      action: ERROR,
      channel: null,  # Empty channel = connection-level error
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
# Start connection
client.connect()

# Wait for FAILED state
AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# errorReason is set from ERROR protocol message
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 50000
ASSERT client.connection.errorReason.statusCode == 500
ASSERT client.connection.errorReason.message == "Internal server error"
CLOSE_CLIENT(client)
```

---

## RTN25 - errorReason propagated to ConnectionStateChange events

**Spec requirement:** errorReason should be accessible through ConnectionStateChange events emitted during state transitions.

Tests that state change events include error information.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client_and_close(ProtocolMessage(
      action: ERROR,
      error: ErrorInfo(
        code: 40003,
        statusCode: 400,
        message: "Access token invalid"
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
# Track state changes
state_changes = []

client.connection.on(ConnectionState.failed, (change) => {
  state_changes.push(change)
})

# Start connection
client.connect()

# Wait for FAILED state
AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# State change event was emitted
ASSERT state_changes.length == 1

change = state_changes[0]

# State change has reason populated
ASSERT change.reason IS NOT null
ASSERT change.reason.code == 40003
ASSERT change.reason.statusCode == 400
ASSERT change.reason.message == "Access token invalid"

# Connection errorReason matches state change reason
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == change.reason.code
ASSERT client.connection.errorReason.message == change.reason.message
CLOSE_CLIENT(client)
```

---

## Note on errorReason Lifecycle

The errorReason attribute behavior across different implementations:

1. **Set on error**: Always populated when an error causes a state transition
2. **Cleared on success**: May or may not be cleared on successful connection (implementation-specific)
3. **Accessible via**: Both `Connection#errorReason` attribute and `ConnectionStateChange#reason`
4. **Persistence**: Some implementations keep the last error for debugging, others clear it
5. **NULL vs defined**: Initially null before any errors occur

Test implementations should verify their SDK's specific behavior regarding errorReason lifecycle.
