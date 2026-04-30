# Realtime Connection Authentication Tests

Spec points: `RTN2e`, `RTN27b`, `RSA4`, `RSA8d`, `RSA12a`

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

## RTN2e - Expired token triggers new authCallback invocation

**Spec requirement:** If the cached token has expired, `authCallback` must be invoked again to obtain a fresh token before connecting.

Tests that expired tokens trigger re-authentication.

### Setup

```pseudo
callback_count = 0

auth_callback = FUNCTION(params):
  callback_count++
  RETURN TokenDetails(
    token: "token-" + callback_count,
    expires: now() + 100  # Expires in 100ms
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

# Wait for token to expire
WAIT 200ms

# Second connection (token expired, should get new one)
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions

```pseudo
# authCallback was invoked twice (once per connection due to expiry)
ASSERT callback_count == 2
CLOSE_CLIENT(client)
```

---

## Notes

These tests verify the **pre-connection** token acquisition flow. For token **renewal** after connection failures (e.g., 401 errors from server), see:
- `../connection/connection_open_failures_test.md` (RTN14b)
- `../connection/connection_failures_test.md` (RTN15h2)
