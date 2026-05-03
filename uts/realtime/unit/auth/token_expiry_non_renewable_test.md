# Token Expiry with Non-Renewable Token Tests

Spec points: `RSA4a`, `RSA4a1`, `RSA4a2`

## Test Type
Unit test with mocked WebSocket client

## Mock Infrastructure

See `realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Purpose

These tests verify the behaviour when a token or tokenDetails is used to instantiate the library without any means to renew the token (no API key, authCallback, or authUrl). The library should warn at instantiation time and treat subsequent token errors as fatal (no retry, transition to FAILED).

---

## RSA4a1 - Instantiation with non-renewable token logs info-level warning

| Spec | Requirement |
|------|-------------|
| RSA4a | When a token or tokenDetails is used to instantiate the library, and no means to renew the token is provided (either an API key, authCallback or authUrl) |
| RSA4a1 | At instantiation time, a message at info log level with error code 40171 should be logged indicating that no means has been provided to renew the supplied token, including an associated url per TI5 |

Tests that when a client is instantiated with only a token (no key, authCallback, or authUrl), an info-level log message with error code 40171 is emitted, including a help URL per TI5.

### Setup

```pseudo
captured_log_messages = []

log_handler = FUNCTION(level, message):
  captured_log_messages.append({level: level, message: message})

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
```

### Test Steps

```pseudo
# Instantiate with token only — no key, no authCallback, no authUrl
client = Realtime(options: ClientOptions(
  token: "non-renewable-token",
  autoConnect: false,
  useBinaryProtocol: false,
  logHandler: log_handler,
  logLevel: LOG_INFO
))
```

### Assertions

```pseudo
# A log message at info level with error code 40171 should have been emitted
info_messages = captured_log_messages.filter(m => m.level == LOG_INFO)
has_40171_message = info_messages.any(m =>
  m.message CONTAINS "40171"
  OR m.message CONTAINS "no means" AND m.message CONTAINS "renew"
)
ASSERT has_40171_message == true

# TI5: log message should include the help URL
has_help_url = info_messages.any(m =>
  m.message CONTAINS "https://help.ably.io/error/40171"
)
ASSERT has_help_url == true

CLOSE_CLIENT(client)
```

---

## RSA4a2 - Server token error with non-renewable token transitions to FAILED

| Spec | Requirement |
|------|-------------|
| RSA4a | When a token or tokenDetails is used to instantiate the library, and no means to renew the token is provided |
| RSA4a2 | If the server responds with a token error (401 HTTP status code and an Ably error value 40140 <= code < 40150), then the client library should indicate an error with error code 40171, not retry the request and, in the case of the realtime library, transition the connection to the FAILED state |

Tests that when the server responds with a token error (e.g. 40142 "Token expired") and the client has no means to renew the token, the connection transitions to FAILED with error code 40171.

### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    # Server responds with token error (40142 = token expired)
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

# Client with token only — no means to renew
client = Realtime(options: ClientOptions(
  token: "expired-token",
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

AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# Connection transitioned to FAILED (not DISCONNECTED — no retry)
ASSERT client.connection.state == ConnectionState.failed

# Error reason has code 40171 (non-renewable token error)
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 40171

# State change event also carries the error
failed_changes = state_changes.filter(c => c.current == ConnectionState.failed)
ASSERT failed_changes.length == 1
ASSERT failed_changes[0].reason IS NOT null
ASSERT failed_changes[0].reason.code == 40171

CLOSE_CLIENT(client)
```

---

## RSA4a2 - Server token error with non-renewable token does not retry

| Spec | Requirement |
|------|-------------|
| RSA4a2 | The client library should not retry the request when a token error is received and no means to renew the token is provided |

Tests that when a non-renewable token receives a token error, only one connection attempt is made (no retry).

### Setup

```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count = connection_attempt_count + 1
    conn.respond_with_success()
    # Always respond with token error
    conn.send_to_client_and_close(ProtocolMessage(
      action: ERROR,
      error: ErrorInfo(
        code: 40140,
        statusCode: 401,
        message: "Token error"
      )
    ))
  }
)
install_mock(mock_ws)

# Client with token only — no means to renew
client = Realtime(options: ClientOptions(
  token: "non-renewable-token",
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
client.connect()

AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# Only one connection attempt was made (no retry)
ASSERT connection_attempt_count == 1

# Connection is in FAILED state
ASSERT client.connection.state == ConnectionState.failed

# Error code is 40171
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 40171

CLOSE_CLIENT(client)
```

---

## Notes

- These tests complement the token renewal tests in `rest/unit/auth/token_renewal.md` (RSA4b) which cover the case where the client DOES have a means to renew tokens.
- For realtime auth callback error handling (when authCallback/authUrl IS provided but fails), see `connection_auth_test.md` (RSA4c, RSA4d).
- The error code 40171 indicates "Token expired with no means of renewal" and is distinct from the server's token error codes (40140-40149).
