# Realtime Connection Authentication Tests

Spec points: `RTN2e`, `RTN27b`, `RSA4`, `RSA4c`, `RSA4c1`, `RSA4c2`, `RSA4c3`, `RSA4d`, `RSA8d`, `RSA12a`

## Test Type
Unit test with mocked WebSocket client and authCallback

## Mock Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Purpose

These tests verify realtime-specific authentication behavior for establishing and maintaining WebSocket connections. While general auth behavior (RSA1-17) is tested in `rest/unit/auth/`, these tests focus on how token authentication integrates with the realtime connection lifecycle.

Key behaviors tested:
- Token acquisition occurs **before** WebSocket connection attempts (RTN2e, RTN27b)
- Token is included in WebSocket URL query parameters (RTN2e)
- Token caching and expiry handling for connection attempts
- authCallback integration with connection state machine

---

## RTN2e/RTN27b - Token obtained before WebSocket connection

**Spec requirement:** When `authCallback` is configured but no token is provided, the library must obtain a token via the callback **before** opening the WebSocket connection. The token is then included in the WebSocket URL as the `accessToken` query parameter.

This is implied by:
- RTN2e: "Depending on the authentication scheme, either `accessToken` contains the token string, or `key` contains the API key"
- RTN27b: "CONNECTING - the state whenever the library is actively attempting to connect to the server (whether trying to obtain a token, trying to open a transport, or waiting for a CONNECTED event)"

Tests that when `authCallback` is configured without an existing token, the library:
1. Transitions to CONNECTING state
2. Invokes the authCallback to obtain a token
3. Opens WebSocket connection with the token in the URL
4. Does NOT make a connection attempt before obtaining the token

### Setup

```pseudo
callback_invoked = false
callback_invoked_time = null
connection_attempt_time = null
captured_ws_url = null

auth_callback = FUNCTION(params):
  callback_invoked = true
  callback_invoked_time = current_time()
  RETURN TokenDetails(
    token: "callback-provided-token",
    expires: now() + 3600000
  )

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_time = current_time()
    captured_ws_url = conn.url
    
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

# Client with authCallback but NO existing token
client = Realtime(options: ClientOptions(
  authCallback: auth_callback,
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
```

### Assertions

```pseudo
# authCallback was invoked
ASSERT callback_invoked == true

# authCallback was invoked BEFORE WebSocket connection attempt
ASSERT callback_invoked_time < connection_attempt_time

# WebSocket URL contains the token from authCallback
ASSERT captured_ws_url.queryParameters["accessToken"] == "callback-provided-token"

# WebSocket URL does NOT contain a key parameter (using token auth, not basic auth)
ASSERT captured_ws_url.queryParameters["key"] IS null

# Connection succeeded
ASSERT client.connection.state == ConnectionState.connected
CLOSE_CLIENT(client)
```

---

## RTN2e/RTN27b - authCallback error prevents connection attempt

**Spec requirement:** If `authCallback` fails during the initial token acquisition, the library should NOT attempt to open a WebSocket connection.

Tests that authCallback errors are handled before any connection attempt is made.

### Setup

```pseudo
connection_attempted = false

auth_callback = FUNCTION(params):
  THROW Error("Auth callback failed")

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempted = true
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key"
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  authCallback: auth_callback,
  autoConnect: false
))
```

### Test Steps

```pseudo
# Start connection
client.connect()

# Wait for DISCONNECTED or FAILED state
AWAIT_STATE client.connection.state IN [ConnectionState.disconnected, ConnectionState.failed]
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# No WebSocket connection was attempted
ASSERT connection_attempted == false

# Error reason is set
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.statusCode == 401
  OR client.connection.errorReason.code == 40170
CLOSE_CLIENT(client)
```

---

## RTN2e - authCallback TokenParams include clientId

**Spec requirement:** When invoking `authCallback`, the library passes `TokenParams` that include any configured `clientId`.

Tests that clientId is passed to authCallback via TokenParams (per RSA12a).

### Setup

```pseudo
received_params = null

auth_callback = FUNCTION(params):
  received_params = params
  RETURN TokenDetails(
    token: "token-for-client",
    expires: now() + 3600000,
    clientId: "my-client-id"
  )

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key"
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  authCallback: auth_callback,
  clientId: "my-client-id",
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
```

### Assertions

```pseudo
# authCallback received TokenParams with clientId
ASSERT received_params IS NOT null
ASSERT received_params.clientId == "my-client-id"
CLOSE_CLIENT(client)
```

---

## RTN2e - Multiple connections reuse valid token

**Spec requirement:** If a valid (non-expired) token exists from a previous authCallback invocation, it should be reused for subsequent connection attempts without invoking authCallback again.

Tests that valid tokens are cached and reused.

### Setup

```pseudo
callback_count = 0

auth_callback = FUNCTION(params):
  callback_count++
  RETURN TokenDetails(
    token: "reusable-token",
    expires: now() + 3600000  # Valid for 1 hour
  )

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key"
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  authCallback: auth_callback,
  autoConnect: false
))
```

### Test Steps

```pseudo
# First connection
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Disconnect
client.close()
AWAIT_STATE client.connection.state == ConnectionState.closed

# Second connection
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions

```pseudo
# authCallback was only invoked once (token was reused)
ASSERT callback_count == 1
CLOSE_CLIENT(client)
```

---

## RSA4c2 - authCallback error during CONNECTING causes DISCONNECTED

**Spec requirement (RSA4c):** If an attempt to authenticate using authCallback results in an error, then:
- **(RSA4c1)** An ErrorInfo with code 80019, statusCode 401, and cause set to the underlying cause should be emitted and set as the connection errorReason.
- **(RSA4c2)** If the connection is CONNECTING, the connection attempt should be treated as unsuccessful, transitioning to DISCONNECTED.

Tests that when authCallback fails during initial connection, the client transitions to DISCONNECTED with error code 80019, and the underlying cause is preserved.

### Setup
```pseudo
auth_callback_count = 0

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  IF auth_callback_count == 1:
    THROW ErrorInfo(code: 50000, statusCode: 500, message: "Auth server unavailable")
  ELSE:
    RETURN TokenDetails(
      token: "valid-token-" + str(auth_callback_count),
      expires: now() + 3600000
    )

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
  authCallback: auth_callback,
  autoConnect: false
))
```

### Test Steps
```pseudo
client.connect()

# authCallback fails on first attempt — connection should go to DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 5 seconds
```

### Assertions
```pseudo
# RSA4c1: errorReason has code 80019 wrapping the underlying cause
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 80019
ASSERT client.connection.errorReason.statusCode == 401
ASSERT client.connection.errorReason.cause IS NOT null
ASSERT client.connection.errorReason.cause.code == 50000
CLOSE_CLIENT(client)
```

---

## RSA4c3 - authCallback error while CONNECTED leaves connection CONNECTED

**Spec requirement (RSA4c3):** If the connection is CONNECTED when an auth attempt fails, then the connection should remain CONNECTED.

Tests that when authCallback fails during an RTN22 server-initiated reauth, the connection stays CONNECTED and errorReason is set with code 80019.

### Setup
```pseudo
auth_callback_count = 0

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  IF auth_callback_count == 1:
    # First call succeeds (initial connection)
    RETURN TokenDetails(
      token: "initial-token",
      expires: now() + 3600000
    )
  ELSE:
    # Subsequent calls fail (reauth)
    THROW ErrorInfo(code: 50000, statusCode: 500, message: "Auth server unavailable")

captured_auth_messages = []

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
  authCallback: auth_callback,
  autoConnect: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Record state changes
state_changes = []
client.connection.on((change) => state_changes.append(change))

# Server requests re-authentication (RTN22)
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: AUTH
))

# Wait for errorReason to be set (auth failure propagates asynchronously)
AWAIT UNTIL client.connection.errorReason IS NOT null
  WITH timeout: 5 seconds
```

### Assertions
```pseudo
# RSA4c3: Connection remains CONNECTED
ASSERT client.connection.state == ConnectionState.connected

# No state transitions away from connected occurred
non_connected_changes = state_changes.filter(
  c => c.current != ConnectionState.connected
)
ASSERT non_connected_changes.length == 0

# RSA4c1: errorReason has code 80019 wrapping the underlying cause
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 80019
ASSERT client.connection.errorReason.statusCode == 401
ASSERT client.connection.errorReason.cause IS NOT null
ASSERT client.connection.errorReason.cause.code == 50000

CLOSE_CLIENT(client)
```

---

## RSA4d - authCallback 403 error causes FAILED

**Spec requirement (RSA4d):** If an authCallback results in an ErrorInfo with statusCode 403, the client library should transition to the FAILED state, with an ErrorInfo (code 80019, statusCode 403, cause set to the underlying cause).

Tests that a 403 from authCallback is treated as fatal and causes FAILED state.

### Setup
```pseudo
auth_callback = FUNCTION(params):
  THROW ErrorInfo(code: 40300, statusCode: 403, message: "Account disabled")

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
  authCallback: auth_callback,
  autoConnect: false
))
```

### Test Steps
```pseudo
client.connect()

# authCallback returns 403 — connection should go to FAILED
AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 5 seconds
```

### Assertions
```pseudo
# RSA4d: FAILED with code 80019 and statusCode 403
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 80019
ASSERT client.connection.errorReason.statusCode == 403
ASSERT client.connection.errorReason.cause IS NOT null
ASSERT client.connection.errorReason.cause.code == 40300

CLOSE_CLIENT(client)
```

---

## RSA4d - authCallback 403 during RTN22 reauth causes FAILED

**Spec requirement (RSA4d):** If an authCallback results in an ErrorInfo with statusCode 403 during an attempt to re-authenticate, the connection transitions to FAILED.

Tests that a 403 from authCallback during server-initiated reauth (RTN22) causes FAILED, even though the connection was previously CONNECTED.

### Setup
```pseudo
auth_callback_count = 0

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  IF auth_callback_count == 1:
    # First call succeeds (initial connection)
    RETURN TokenDetails(
      token: "initial-token",
      expires: now() + 3600000
    )
  ELSE:
    # Reauth fails with 403
    THROW ErrorInfo(code: 40300, statusCode: 403, message: "Account suspended")

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
  authCallback: auth_callback,
  autoConnect: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Server requests re-authentication (RTN22)
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: AUTH
))

# authCallback returns 403 — connection should go to FAILED
AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 5 seconds
```

### Assertions
```pseudo
# RSA4d: FAILED with code 80019 and statusCode 403
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 80019
ASSERT client.connection.errorReason.statusCode == 403
ASSERT client.connection.errorReason.cause IS NOT null
ASSERT client.connection.errorReason.cause.code == 40300

CLOSE_CLIENT(client)
```

---

## Notes

These tests verify the **pre-connection** token acquisition flow and **auth failure handling** during the connection lifecycle. For token **renewal** after connection failures (e.g., 401 errors from server), see:
- `../connection/connection_open_failures_test.md` (RTN14b)
- `../connection/connection_failures_test.md` (RTN15h2)
