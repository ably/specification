# Connection Opening Failures Tests (RTN14)

Spec points: `RTN14`, `RTN14a`, `RTN14b`, `RTN14c`, `RTN14d`, `RTN14e`, `RTN14f`, `RTN14g`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTN14a - Invalid API key causes FAILED state

**Spec requirement:** If an API key is invalid, the connection transitions to FAILED state and Connection.errorReason is set.

Tests that connecting with an invalid API key results in immediate failure.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    # WebSocket connects successfully
    conn.respond_with_success()
    
    # But server immediately sends ERROR for invalid key and closes connection
    conn.send_to_client_and_close(ProtocolMessage(
      action: ERROR,
      error: ErrorInfo(
        code: 40005,
        statusCode: 400,
        message: "Invalid key"
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
# Start connection
client.connect()

# Wait for CONNECTING state
AWAIT_STATE client.connection.state == ConnectionState.connecting

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
ASSERT client.connection.errorReason.code == 40005
ASSERT client.connection.errorReason.statusCode == 400

# Connection ID/key not set
ASSERT client.connection.id IS null
ASSERT client.connection.key IS null
CLOSE_CLIENT(client)
```

---

## RTN14b - Token error during connection with renewal

**Spec requirement:** If a token error occurs during connection and the token is renewable, attempt to obtain a new token and retry the connection.

Tests that token errors trigger renewal and retry when possible.

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
      # First attempt: token error, close connection
      conn.send_to_client_and_close(ProtocolMessage(
        action: ERROR,
        error: ErrorInfo(
          code: 40142,
          statusCode: 401,
          message: "Token expired"
        )
      ))
    ELSE:
      # Second attempt: success
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
# Start connection
client.connect()

# Wait for CONNECTED (should retry after token renewal)
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
```

### Assertions

```pseudo
# Successfully connected after retry
ASSERT client.connection.state == ConnectionState.connected

# Token was renewed
ASSERT token_request_count == 2  # Initial + renewal

# Connection was attempted twice
ASSERT connection_attempt_count == 2
CLOSE_CLIENT(client)
```

---

## RSA4a - Token error during connection without renewal

**Spec requirement (RSA4a2):** If the server responds with a token error and there is no means to renew the token, the connection transitions to FAILED with error code 40171.

Tests that non-renewable token errors cause FAILED state.

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
  token: "expired_token_string",
  autoConnect: false
))
```

### Test Steps

```pseudo
# Start connection
client.connect()

# Wait for FAILED state (RSA4a2: no means to renew → FAILED)
AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# Connection transitioned to FAILED (RSA4a2: not DISCONNECTED)
ASSERT client.connection.state == ConnectionState.failed

# Error reason is set with 40171 (RSA4a2)
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 40171
CLOSE_CLIENT(client)
```

---

## RTN14c - Connection timeout

**Spec requirement:** A connection attempt fails if not connected within realtimeRequestTimeout.

Tests that connections time out if no CONNECTED message is received.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    # WebSocket connects but server never sends CONNECTED
    # (simulates unresponsive server)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeRequestTimeout: 1000,  # 1 second timeout
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

# Start connection
client.connect()

# Wait for CONNECTING state
AWAIT_STATE client.connection.state == ConnectionState.connecting

# Advance time past timeout
ADVANCE_TIME(1100)

# Should transition to DISCONNECTED (will retry)
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 1 second
```

### Assertions

```pseudo
# Connection timed out
ASSERT client.connection.state == ConnectionState.disconnected

# Error indicates timeout
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.message CONTAINS "timeout"
  OR client.connection.errorReason.code IN [50003, 80003]
CLOSE_CLIENT(client)
```

---

## RTN14d - Retry after recoverable failure

**Spec requirement:** After a recoverable connection failure, the client transitions to DISCONNECTED and automatically retries after disconnectedRetryTimeout.

Tests that recoverable failures trigger automatic retry.

### Setup

```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    
    IF connection_attempt_count == 1:
      # First attempt fails (network error)
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
  disconnectedRetryTimeout: 1000,  # 1 second
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

# Start connection
client.connect()

# Should transition to DISCONNECTED after first failure
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 2 seconds

# Advance time to trigger retry
ADVANCE_TIME(1100)

# Should reconnect automatically
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# Successfully connected on retry
ASSERT client.connection.state == ConnectionState.connected

# Two connection attempts were made
ASSERT connection_attempt_count == 2
CLOSE_CLIENT(client)
```

---

## RTN14e - DISCONNECTED to SUSPENDED after connectionStateTtl

**Spec requirement:** Once the connection has been DISCONNECTED for longer than connectionStateTtl, transition to SUSPENDED state.

Tests that prolonged disconnection leads to suspension.

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
  disconnectedRetryTimeout: 1000,  # Retry every 1 second
  autoConnect: false
))

# Simulate short connectionStateTtl
# In real implementation, this comes from server in CONNECTED message
# For this test, we'll use a short default value
DEFAULT_CONNECTION_STATE_TTL = 5000  # 5 seconds
```

### Test Steps

```pseudo
enable_fake_timers()

# Start connection (will fail)
client.connect()

# Should transition to DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Advance time past connectionStateTtl
ADVANCE_TIME(DEFAULT_CONNECTION_STATE_TTL + 100)

# Should transition to SUSPENDED
AWAIT_STATE client.connection.state == ConnectionState.suspended
  WITH timeout: 1 second
```

### Assertions

```pseudo
# Connection is SUSPENDED
ASSERT client.connection.state == ConnectionState.suspended

# Error reason is set (indicates why suspended)
ASSERT client.connection.errorReason IS NOT null
CLOSE_CLIENT(client)
```

---

## RTN14f - SUSPENDED state retries indefinitely

**Spec requirement:** The connection remains in SUSPENDED state indefinitely, periodically attempting to reestablish connection.

Tests that SUSPENDED state continues retry attempts.

### Setup

```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    
    IF connection_attempt_count < 3:
      # First 2 attempts fail
      conn.respond_with_refused()
    ELSE:
      # Third attempt succeeds
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
  disconnectedRetryTimeout: 500,
  suspendedRetryTimeout: 1000,  # 1 second
  autoConnect: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

# Start connection (will fail repeatedly)
client.connect()

# Wait for SUSPENDED state
# (after initial failure + connectionStateTtl expiry)
AWAIT_STATE client.connection.state == ConnectionState.suspended

recorded_suspended_time = current_fake_time()

# Advance time to trigger first SUSPENDED retry
ADVANCE_TIME(1100)

# Should attempt reconnection (but still fail)
WAIT_FOR connection_attempt_count >= 2

# Advance time to trigger second SUSPENDED retry
ADVANCE_TIME(1100)

# Should reconnect successfully on third attempt
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# Successfully connected after multiple SUSPENDED retries
ASSERT client.connection.state == ConnectionState.connected

# Multiple connection attempts were made from SUSPENDED state
ASSERT connection_attempt_count >= 3
CLOSE_CLIENT(client)
```

---

## RTN14g - ERROR protocol message with empty channel

**Spec requirement:** If an ERROR ProtocolMessage with empty channel attribute is received, transition to FAILED state and set errorReason.

Tests that fatal protocol errors cause FAILED state.

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
# Connection transitioned to FAILED
ASSERT client.connection.state == ConnectionState.failed

# Error reason is set from protocol message
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 50000
ASSERT client.connection.errorReason.statusCode == 500
ASSERT client.connection.errorReason.message == "Internal server error"
CLOSE_CLIENT(client)
```

---

## Timer Mocking Note

These tests use `enable_fake_timers()` and `ADVANCE_TIME()` to avoid slow tests. Implementations should:

1. **Prefer fake timers** (JavaScript Jest, Python freezegun, Go testing.Clock)
2. **Or use dependency injection** for timer/clock interfaces
3. **Or use very short timeout values** (e.g., 50ms instead of 15s)
4. **Last resort:** Use actual delays with generous test timeouts

See the "Timer Mocking" section in `write-test-spec.md` for detailed guidance.
