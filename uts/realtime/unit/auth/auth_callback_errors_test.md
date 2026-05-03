# Auth Callback Error Handling Tests

Spec points: `RSA4c`, `RSA4c1`, `RSA4c2`, `RSA4c3`, `RSA4d`, `RSA4e`, `RSA4f`

## Test Type
Unit test with mocked WebSocket client and authCallback (realtime tests); unit test with mocked HTTP client (REST test for RSA4e)

## Mock Infrastructure

See `realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.
See `rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

## Purpose

These tests verify error handling when authentication via authCallback fails in various ways. The behaviour depends on:
- The type of error (generic error vs 403 vs invalid format vs timeout)
- The connection state when the error occurs (CONNECTING vs CONNECTED)
- Whether the context is realtime (connection state machine) or REST (request error)

Key behaviours:
- Generic auth errors while CONNECTING -> DISCONNECTED with code 80019 (RSA4c1, RSA4c2)
- Generic auth errors while CONNECTED -> stay CONNECTED, errorReason set (RSA4c1, RSA4c3)
- 403 errors -> FAILED with code 80019/statusCode 403 (RSA4d)
- Invalid token format -> treated as auth error per RSA4c (RSA4f)
- REST auth errors -> error with code 40170 (RSA4e)

---

## RSA4c1, RSA4c2 - authCallback error during CONNECTING transitions to DISCONNECTED

| Spec | Requirement |
|------|-------------|
| RSA4c | If an attempt to authenticate using authCallback results in an error, then RSA4c1-3 apply |
| RSA4c1 | An ErrorInfo with code 80019, statusCode 401, and cause set to the underlying cause should be emitted with the state change and set as the connection errorReason |
| RSA4c2 | If the connection is CONNECTING, then the connection attempt should be treated as unsuccessful, and the connection should transition to DISCONNECTED or SUSPENDED |

Tests that when authCallback throws an error during the initial connection (CONNECTING state), the connection transitions to DISCONNECTED with an ErrorInfo having code 80019, statusCode 401, and cause set to the underlying error.

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
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
state_changes = []
client.connection.on((change) => {
  state_changes.append(change)
})

client.connect()

# authCallback fails on first attempt — connection should go to DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# RSA4c2: Connection transitioned to DISCONNECTED (not FAILED — it's retriable)
ASSERT client.connection.state == ConnectionState.disconnected

# RSA4c1: errorReason has code 80019 wrapping the underlying cause
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 80019
ASSERT client.connection.errorReason.statusCode == 401

# RSA4c1: cause is set to the underlying error from authCallback
ASSERT client.connection.errorReason.cause IS NOT null
ASSERT client.connection.errorReason.cause.code == 50000

# State change event carries the same error
disconnected_changes = state_changes.filter(c => c.current == ConnectionState.disconnected)
ASSERT disconnected_changes.length >= 1
ASSERT disconnected_changes[0].reason IS NOT null
ASSERT disconnected_changes[0].reason.code == 80019

CLOSE_CLIENT(client)
```

---

## RSA4c1, RSA4c2 - authCallback timeout during CONNECTING transitions to DISCONNECTED

| Spec | Requirement |
|------|-------------|
| RSA4c | If the attempt times out after realtimeRequestTimeout, then RSA4c1-3 apply |
| RSA4c1 | An ErrorInfo with code 80019, statusCode 401, and cause set to the underlying cause should be emitted and set as the connection errorReason |
| RSA4c2 | If the connection is CONNECTING, then the connection attempt should be treated as unsuccessful |

Tests that when authCallback times out (exceeds realtimeRequestTimeout), the connection transitions to DISCONNECTED with error code 80019.

### Setup

```pseudo
enable_fake_timers()

auth_callback = FUNCTION(params):
  # Never returns — simulates a timeout
  RETURN NEVER_RESOLVING_FUTURE

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
  realtimeRequestTimeout: 10000,
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
state_changes = []
client.connection.on((change) => {
  state_changes.append(change)
})

client.connect()

# Advance time past realtimeRequestTimeout
ADVANCE_TIME(11000)

AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# RSA4c2: Connection transitioned to DISCONNECTED
ASSERT client.connection.state == ConnectionState.disconnected

# RSA4c1: errorReason has code 80019
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 80019
ASSERT client.connection.errorReason.statusCode == 401

CLOSE_CLIENT(client)
```

---

## RSA4c3 - authCallback error while CONNECTED leaves connection CONNECTED

| Spec | Requirement |
|------|-------------|
| RSA4c | If an attempt to authenticate using authCallback results in an error |
| RSA4c1 | An ErrorInfo with code 80019, statusCode 401, and cause set to the underlying cause should be set as the connection errorReason |
| RSA4c3 | If the connection is CONNECTED, then the connection should remain CONNECTED |

Tests that when authCallback fails during an RTN22 server-initiated reauth while the connection is CONNECTED, the connection stays CONNECTED and errorReason is set with code 80019.

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
    # Subsequent calls fail (reauth triggered by server)
    THROW ErrorInfo(code: 50000, statusCode: 500, message: "Auth server unavailable")

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
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Record state changes from this point
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

## RSA4d - authCallback returns 403 error during CONNECTING transitions to FAILED

| Spec | Requirement |
|------|-------------|
| RSA4d | If an authCallback results in an ErrorInfo with statusCode 403, the client library should transition to the FAILED state, with an ErrorInfo (code 80019, statusCode 403, cause set to the underlying cause) emitted with the state change and set as the connection errorReason |

Tests that a 403 from authCallback during initial connection is treated as fatal and causes the connection to transition directly to FAILED (not DISCONNECTED).

### Setup

```pseudo
connection_attempted = false

auth_callback = FUNCTION(params):
  THROW ErrorInfo(code: 40300, statusCode: 403, message: "Account disabled")

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

client = Realtime(options: ClientOptions(
  authCallback: auth_callback,
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
state_changes = []
client.connection.on((change) => {
  state_changes.append(change)
})

client.connect()

# authCallback returns 403 — connection should go directly to FAILED
AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# RSA4d: Connection went to FAILED (not DISCONNECTED)
ASSERT client.connection.state == ConnectionState.failed

# No WebSocket connection was attempted (auth failed before transport)
ASSERT connection_attempted == false

# RSA4d: ErrorInfo has code 80019 and statusCode 403
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 80019
ASSERT client.connection.errorReason.statusCode == 403

# Cause is the original 403 error
ASSERT client.connection.errorReason.cause IS NOT null
ASSERT client.connection.errorReason.cause.code == 40300
ASSERT client.connection.errorReason.cause.statusCode == 403

# State change event carries the error
failed_changes = state_changes.filter(c => c.current == ConnectionState.failed)
ASSERT failed_changes.length == 1
ASSERT failed_changes[0].reason IS NOT null
ASSERT failed_changes[0].reason.code == 80019
ASSERT failed_changes[0].reason.statusCode == 403

# No DISCONNECTED state was reached (went directly to FAILED)
disconnected_changes = state_changes.filter(c => c.current == ConnectionState.disconnected)
ASSERT disconnected_changes.length == 0

CLOSE_CLIENT(client)
```

---

## RSA4d - authCallback 403 during RTN22 reauth transitions CONNECTED to FAILED

| Spec | Requirement |
|------|-------------|
| RSA4d | If an authCallback results in an ErrorInfo with statusCode 403 as part of an attempt to authenticate, the client library should transition to the FAILED state |
| RSA4d1 | An "attempt to authenticate" includes an RTN22 online reauth |

Tests that a 403 from authCallback during server-initiated reauth (RTN22) causes the connection to transition from CONNECTED to FAILED, overriding RSA4c3.

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
  autoConnect: false,
  useBinaryProtocol: false
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

## RSA4f - authCallback returns invalid type treated as invalid format error

| Spec | Requirement |
|------|-------------|
| RSA4f | The following conditions imply that the token is in an invalid format: the object passed by authCallback is neither a String, JsonObject, TokenRequest object, nor TokenDetails object |
| RSA4c | If the provided token is in an invalid format (as defined in RSA4f), then RSA4c1-3 apply |
| RSA4c1 | An ErrorInfo with code 80019, statusCode 401, and cause set to the underlying cause should be set as the connection errorReason |
| RSA4c2 | If the connection is CONNECTING, the connection should transition to DISCONNECTED or SUSPENDED |

Tests that when authCallback returns an object that is not a String, JsonObject, TokenRequest, or TokenDetails (e.g. an integer or a list), it is treated as an invalid format error per RSA4f, and the connection transitions to DISCONNECTED with error code 80019 per RSA4c.

### Setup

```pseudo
auth_callback = FUNCTION(params):
  # Return an invalid type — an integer is not a valid token format
  RETURN 12345

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
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
client.connect()

# Invalid format from authCallback — connection should go to DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# RSA4c2: Connection transitioned to DISCONNECTED
ASSERT client.connection.state == ConnectionState.disconnected

# RSA4c1: errorReason has code 80019
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 80019
ASSERT client.connection.errorReason.statusCode == 401

CLOSE_CLIENT(client)
```

---

## RSA4f - authCallback returns token string exceeding 128KiB treated as invalid format

| Spec | Requirement |
|------|-------------|
| RSA4f | The token string or the JSON stringified JsonObject, TokenRequest or TokenDetails is greater than 128KiB implies the token is in an invalid format |
| RSA4c | If the provided token is in an invalid format (as defined in RSA4f), then RSA4c1-3 apply |

Tests that when authCallback returns a token string larger than 128KiB, it is treated as an invalid format error per RSA4f and the connection transitions to DISCONNECTED with error code 80019.

### Setup

```pseudo
# Generate a token string larger than 128KiB (131072 bytes)
oversized_token = "x" * 131073

auth_callback = FUNCTION(params):
  RETURN oversized_token

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
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
client.connect()

# Oversized token — connection should go to DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# RSA4c2: Connection transitioned to DISCONNECTED
ASSERT client.connection.state == ConnectionState.disconnected

# RSA4c1: errorReason has code 80019
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 80019
ASSERT client.connection.errorReason.statusCode == 401

CLOSE_CLIENT(client)
```

---

## RSA4e - REST authCallback error produces error with code 40170

| Spec | Requirement |
|------|-------------|
| RSA4e | If in the course of a REST request an attempt to authenticate using authCallback fails due to a timeout, network error, a token in an invalid format (per RSA4f), or some other auth error condition other than an explicit ErrorInfo from Ably, the request should result in an error with code 40170, statusCode 401, and a suitable error message |

Tests that when a REST client's authCallback fails with a non-Ably error (e.g. a generic exception), the resulting request error has code 40170 and statusCode 401.

### Setup

```pseudo
auth_callback = FUNCTION(params):
  # Generic error — not an explicit ErrorInfo from Ably
  THROW Error("Network failure connecting to auth server")

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  authCallback: auth_callback,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
# Attempt a REST request that requires authentication
channel = client.channels.get("test-channel")
AWAIT channel.status() FAILS WITH error
```

### Assertions

```pseudo
# RSA4e: Error has code 40170 and statusCode 401
ASSERT error.code == 40170
ASSERT error.statusCode == 401

# Error message should be descriptive
ASSERT error.message IS NOT null
ASSERT error.message.length > 0
```

---

## Notes

- **RSA4c vs RSA4d precedence:** RSA4d (403 -> FAILED) takes precedence over RSA4c (generic error -> DISCONNECTED). The spec says RSA4c applies "unless RSA4d applies."
- **RSA4d1 scope:** The 403 -> FAILED behaviour applies to connect sequence auth, RTN22 reauth, and explicit `authorize()` calls, but NOT to explicit `requestToken` calls.
- **RSA4e context:** RSA4e applies specifically to REST requests and explicit `requestToken` calls. For realtime, RSA4c applies instead.
- **Overlap with connection_auth_test.md:** The existing `connection_auth_test.md` already covers RSA4c2 (authCallback error -> DISCONNECTED), RSA4c3 (authCallback error while CONNECTED), and RSA4d (403 -> FAILED). The tests in this file provide additional coverage for timeout scenarios, invalid format handling (RSA4f), and REST-specific behaviour (RSA4e).
