# Realtime Authorize Tests

Spec points: `RTC8`, `RTC8a`, `RTC8a1`, `RTC8a2`, `RTC8a3`, `RTC8b`, `RTC8b1`, `RTC8c`

## Test Type
Unit test with mocked WebSocket client and authCallback

## Mock Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Purpose

These tests verify in-band reauthorization via `auth.authorize()` on a realtime client.
When called on a connected client, `authorize()` obtains a new token and sends an `AUTH`
protocol message to Ably. Ably responds with either a `CONNECTED` message (success,
emitting an UPDATE event) or an `ERROR` message (failure). The behaviour varies based
on the current connection state when `authorize()` is called.

---

## RTC8a - authorize() on CONNECTED sends AUTH protocol message

| Spec | Requirement |
|------|-------------|
| RTC8 | `auth.authorize` instructs the library to obtain a token and alter the current connection to use it |
| RTC8a | If CONNECTED, obtain a new token then send an AUTH ProtocolMessage with an auth attribute containing the token string |

Tests that calling `authorize()` while connected obtains a new token via the
authCallback and sends an AUTH protocol message containing the new token.

### Setup
```pseudo
auth_callback_count = 0
captured_auth_messages = []

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  RETURN TokenDetails(
    token: "token-" + str(auth_callback_count),
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
AWAIT_STATE client.connection.state == ConnectionState.connected

# Track state changes during reauth
state_changes = []
client.connection.on((change) => {
  state_changes.append(change)
})

# When client sends AUTH, record it and respond with new CONNECTED
mock_ws.on_client_message((msg) => {
  IF msg.action == AUTH:
    captured_auth_messages.append(msg)
    mock_ws.active_connection.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key-2",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key-2",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
})

token_details = AWAIT client.auth.authorize()
```

### Assertions
```pseudo
# authCallback was called twice (initial connect + authorize)
ASSERT auth_callback_count == 2

# An AUTH protocol message was sent
ASSERT captured_auth_messages.length == 1

# AUTH message contains the new token
ASSERT captured_auth_messages[0].auth IS NOT null
ASSERT captured_auth_messages[0].auth.accessToken == "token-2"

# authorize() resolved with the new token
ASSERT token_details.token == "token-2"

# No state changes occurred — connection stayed CONNECTED throughout
ASSERT state_changes.length == 0
ASSERT client.connection.state == ConnectionState.connected
```

---

## RTC8a1 - Successful reauth emits UPDATE event

**Spec requirement:** If the authentication token change is successful, Ably sends a new CONNECTED ProtocolMessage. The connectionDetails must override existing defaults (RTN21). The Connection should emit an UPDATE event per RTN24.

Tests that a successful in-band reauthorization emits an UPDATE event (not a
CONNECTED state change) and updates connection details.

### Setup
```pseudo
auth_callback_count = 0

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  RETURN TokenDetails(
    token: "token-" + str(auth_callback_count),
    expires: now() + 3600000
  )

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id-1",
      connectionKey: "connection-key-1",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key-1",
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

# Track events
update_events = []
connected_events = []
state_changes = []

client.connection.on(ConnectionEvent.update, (change) => {
  update_events.append(change)
})
client.connection.on(ConnectionState.connected, (change) => {
  connected_events.append(change)
})
client.connection.on((change) => {
  state_changes.append(change)
})

# When client sends AUTH, respond with new CONNECTED (updated details)
mock_ws.on_client_message((msg) => {
  IF msg.action == AUTH:
    mock_ws.active_connection.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id-2",
      connectionKey: "connection-key-2",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key-2",
        maxIdleInterval: 20000,
        connectionStateTtl: 180000
      )
    ))
})

AWAIT client.auth.authorize()
```

### Assertions
```pseudo
# UPDATE event was emitted
ASSERT update_events.length == 1
ASSERT update_events[0].previous == ConnectionState.connected
ASSERT update_events[0].current == ConnectionState.connected

# No additional CONNECTED state event was emitted
ASSERT connected_events.length == 0

# No state changes occurred (stayed CONNECTED throughout)
ASSERT state_changes.length == 0

# Connection details were updated (RTN21)
ASSERT client.connection.id == "connection-id-2"
ASSERT client.connection.key == "connection-key-2"
```

---

## RTC8a1 - Capability downgrade causes channel FAILED

**Spec requirement:** A test should exist where the capabilities are downgraded resulting in Ably sending an ERROR ProtocolMessage with a channel property, causing the channel to enter the FAILED state. The reason must be included in the channel state change event.

Tests that after a successful reauth with reduced capabilities, Ably sends a
channel-level ERROR that causes the affected channel to enter FAILED state.

### Setup
```pseudo
auth_callback_count = 0

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  RETURN TokenDetails(
    token: "token-" + str(auth_callback_count),
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
AWAIT_STATE client.connection.state == ConnectionState.connected

# Attach a channel
channel = client.channels.get("private-channel")

mock_ws.on_client_message((msg) => {
  IF msg.action == ATTACH AND msg.channel == "private-channel":
    mock_ws.active_connection.send_to_client(ProtocolMessage(
      action: ATTACHED,
      channel: "private-channel",
      flags: 0
    ))
})

channel.attach()
AWAIT_STATE channel.state == ChannelState.attached

# Track channel state changes
channel_state_changes = []
channel.on((change) => {
  channel_state_changes.append(change)
})

# When client sends AUTH, respond with CONNECTED then channel-level ERROR
mock_ws.on_client_message((msg) => {
  IF msg.action == AUTH:
    # Reauth succeeds at connection level
    mock_ws.active_connection.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key-2",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key-2",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
    # Then server sends channel-level ERROR (capability downgrade)
    mock_ws.active_connection.send_to_client(ProtocolMessage(
      action: ERROR,
      channel: "private-channel",
      error: ErrorInfo(
        code: 40160,
        statusCode: 401,
        message: "Channel denied access based on given capability"
      )
    ))
})

# Call authorize (to downgrade capabilities)
AWAIT client.auth.authorize()
AWAIT_STATE channel.state == ChannelState.failed
```

### Assertions
```pseudo
# Channel entered FAILED state
ASSERT channel.state == ChannelState.failed

# Channel state change event includes the error reason
failed_changes = channel_state_changes.filter(c => c.current == ChannelState.failed)
ASSERT failed_changes.length == 1
ASSERT failed_changes[0].reason IS NOT null
ASSERT failed_changes[0].reason.code == 40160
ASSERT failed_changes[0].reason.statusCode == 401

# Connection remains CONNECTED (channel-level ERROR doesn't close connection)
ASSERT client.connection.state == ConnectionState.connected
```

---

## RTC8a2 - Failed reauth transitions connection to FAILED

**Spec requirement:** If the authentication token change fails, Ably will send an ERROR ProtocolMessage triggering the connection to transition to the FAILED state. A test should exist for a token change that fails (such as sending a new token with an incompatible clientId).

Tests that a failed in-band reauthorization (e.g. incompatible clientId) causes
the connection to transition to FAILED.

### Setup
```pseudo
auth_callback_count = 0

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  RETURN TokenDetails(
    token: "token-" + str(auth_callback_count),
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
AWAIT_STATE client.connection.state == ConnectionState.connected

# Track state changes
state_changes = []
client.connection.on((change) => {
  state_changes.append(change)
})

# When client sends AUTH, respond with connection-level ERROR (incompatible clientId)
mock_ws.on_client_message((msg) => {
  IF msg.action == AUTH:
    mock_ws.active_connection.send_to_client_and_close(ProtocolMessage(
      action: ERROR,
      error: ErrorInfo(
        code: 40012,
        statusCode: 400,
        message: "Incompatible clientId"
      )
    ))
})

AWAIT client.auth.authorize() FAILS WITH error
ASSERT error.code == 40012
```

### Assertions
```pseudo
# Connection transitioned to FAILED
ASSERT client.connection.state == ConnectionState.failed

# Error reason is set on the connection
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 40012

# State changes include FAILED
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.failed
]
```

---

## RTC8a3 - authorize() completes only after server response

**Spec requirement:** The authorize call should be indicated as completed with the new token or error only once realtime has responded to the AUTH with either a CONNECTED or ERROR respectively.

Tests that the Future/Promise returned by `authorize()` does not resolve until
the server responds to the AUTH message.

### Setup
```pseudo
auth_callback_count = 0

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  RETURN TokenDetails(
    token: "token-" + str(auth_callback_count),
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
AWAIT_STATE client.connection.state == ConnectionState.connected

# Start authorize — do NOT await
authorize_future = client.auth.authorize()
authorize_completed = false
authorize_future.then((_) => { authorize_completed = true })

# Wait for the client to send the AUTH message (confirms token was obtained
# and AUTH was sent, but server hasn't responded yet)
auth_msg = AWAIT mock_ws.await_client_message(action: AUTH)

# authorize() should NOT have completed yet (server hasn't responded)
ASSERT authorize_completed == false

# Now send the server response
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: CONNECTED,
  connectionId: "connection-id",
  connectionKey: "connection-key-2",
  connectionDetails: ConnectionDetails(
    connectionKey: "connection-key-2",
    maxIdleInterval: 15000,
    connectionStateTtl: 120000
  )
))

# Now await completion
token_details = AWAIT authorize_future
```

### Assertions
```pseudo
# authorize() completed after server response
ASSERT authorize_completed == true
ASSERT token_details.token == "token-2"
```

---

## RTC8b - authorize() while CONNECTING halts current attempt

**Spec requirement:** If the connection is in the CONNECTING state when auth.authorize is called, all current connection attempts should be halted, and after obtaining a new token the library should immediately initiate a connection attempt using the new token.

Tests that calling `authorize()` while in the CONNECTING state cancels the
current connection attempt and reconnects with the new token.

### Setup
```pseudo
auth_callback_count = 0
captured_ws_urls = []

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  RETURN TokenDetails(
    token: "token-" + str(auth_callback_count),
    expires: now() + 3600000
  )

connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count = connection_attempt_count + 1
    captured_ws_urls.append(conn.url)

    IF connection_attempt_count == 1:
      # First attempt: respond with success but delay CONNECTED
      # (simulating CONNECTING state)
      conn.respond_with_success()
      # Don't send CONNECTED — client stays in CONNECTING
    ELSE:
      # Second attempt (after authorize): complete normally
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
# Start connection — will enter CONNECTING
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connecting

# Call authorize while CONNECTING
token_details = AWAIT client.auth.authorize()
```

### Assertions
```pseudo
# authorize() completed successfully
ASSERT token_details.token == "token-2"

# Connection is now CONNECTED
ASSERT client.connection.state == ConnectionState.connected

# authCallback was called twice (initial + authorize)
ASSERT auth_callback_count == 2

# Two connection attempts were made
ASSERT connection_attempt_count == 2

# Second attempt used the new token
ASSERT captured_ws_urls[1].queryParameters["accessToken"] == "token-2"
```

---

## RTC8b1 - authorize() while CONNECTING fails on FAILED state

**Spec requirement:** The authorize call should be indicated as completed with the new token once the connection has moved to the CONNECTED state, or with an error if the connection instead moves to the FAILED, SUSPENDED, or CLOSED states.

Tests that if the connection transitions to FAILED after `authorize()` is called
while CONNECTING, the authorize future completes with an error.

### Setup
```pseudo
auth_callback_count = 0

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  RETURN TokenDetails(
    token: "token-" + str(auth_callback_count),
    expires: now() + 3600000
  )

connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count = connection_attempt_count + 1

    IF connection_attempt_count == 1:
      # First attempt: keep in CONNECTING
      conn.respond_with_success()
    ELSE:
      # Second attempt (after authorize): fail with fatal error
      conn.respond_with_success()
      conn.send_to_client_and_close(ProtocolMessage(
        action: ERROR,
        error: ErrorInfo(
          code: 40101,
          statusCode: 401,
          message: "Invalid credentials"
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
AWAIT_STATE client.connection.state == ConnectionState.connecting

# Call authorize while CONNECTING — should fail
AWAIT client.auth.authorize() FAILS WITH error
ASSERT error.code == 40101
```

### Assertions
```pseudo
# Connection is in FAILED state
ASSERT client.connection.state == ConnectionState.failed
```

---

## RTC8c - authorize() from DISCONNECTED initiates connection

**Spec requirement:** If the connection is in the DISCONNECTED, SUSPENDED, FAILED, or CLOSED state when auth.authorize is called, after obtaining a token the library should move to the CONNECTING state and initiate a connection attempt using the new token, and RTC8b1 applies.

Tests that calling `authorize()` from a non-connected state obtains a new token
and initiates a connection.

### Setup
```pseudo
auth_callback_count = 0
captured_ws_urls = []

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  RETURN TokenDetails(
    token: "token-" + str(auth_callback_count),
    expires: now() + 3600000
  )

connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count = connection_attempt_count + 1
    captured_ws_urls.append(conn.url)
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

# Client starts in INITIALIZED (autoConnect: false, connect() not called)
client = Realtime(options: ClientOptions(
  authCallback: auth_callback,
  autoConnect: false
))
```

### Test Steps
```pseudo
# Verify client is not connected
ASSERT client.connection.state == ConnectionState.initialized

# Track state changes
state_changes = []
client.connection.on((change) => {
  state_changes.append(change.current)
})

# Call authorize from non-connected state
token_details = AWAIT client.auth.authorize()
```

### Assertions
```pseudo
# authorize() completed successfully
ASSERT token_details.token == "token-1"

# Connection is now CONNECTED
ASSERT client.connection.state == ConnectionState.connected

# State transitions included CONNECTING
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.connecting,
  ConnectionState.connected
]

# Connection used the token from authorize
ASSERT captured_ws_urls[0].queryParameters["accessToken"] == "token-1"
```

---

## RTC8c - authorize() from FAILED initiates connection

**Spec requirement:** If the connection is in the FAILED state when auth.authorize is called, after obtaining a token the library should move to the CONNECTING state and initiate a connection attempt using the new token.

Tests that `authorize()` can recover a FAILED connection by obtaining a new token
and reconnecting.

### Setup
```pseudo
auth_callback_count = 0
captured_ws_urls = []

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  RETURN TokenDetails(
    token: "token-" + str(auth_callback_count),
    expires: now() + 3600000
  )

connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count = connection_attempt_count + 1
    captured_ws_urls.append(conn.url)
    conn.respond_with_success()

    IF connection_attempt_count == 1:
      # First attempt: fail with fatal error
      conn.send_to_client_and_close(ProtocolMessage(
        action: ERROR,
        error: ErrorInfo(
          code: 40101,
          statusCode: 401,
          message: "Invalid credentials"
        )
      ))
    ELSE:
      # Second attempt (after authorize): succeed
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
# Connect — will fail
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.failed

# Track state changes from FAILED onwards
state_changes = []
client.connection.on((change) => {
  state_changes.append(change.current)
})

# Call authorize from FAILED state
token_details = AWAIT client.auth.authorize()
```

### Assertions
```pseudo
# authorize() completed successfully
ASSERT token_details.token == "token-2"

# Connection recovered to CONNECTED
ASSERT client.connection.state == ConnectionState.connected

# State transitions went through CONNECTING
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.connecting,
  ConnectionState.connected
]

# Second connection used the new token
ASSERT captured_ws_urls[1].queryParameters["accessToken"] == "token-2"
```

---

## RTC8c - authorize() from CLOSED initiates connection

**Spec requirement:** If the connection is in the CLOSED state when auth.authorize is called, after obtaining a token the library should move to the CONNECTING state and initiate a connection attempt using the new token.

Tests that `authorize()` from CLOSED state opens a new connection.

### Setup
```pseudo
auth_callback_count = 0

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  RETURN TokenDetails(
    token: "token-" + str(auth_callback_count),
    expires: now() + 3600000
  )

connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count = connection_attempt_count + 1
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id-" + str(connection_attempt_count),
      connectionKey: "connection-key-" + str(connection_attempt_count),
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key-" + str(connection_attempt_count),
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
# Connect, then close
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

client.close()
AWAIT_STATE client.connection.state == ConnectionState.closed

# Call authorize from CLOSED state
token_details = AWAIT client.auth.authorize()
```

### Assertions
```pseudo
# authorize() completed successfully
ASSERT token_details.token == "token-2"

# Connection is now CONNECTED again
ASSERT client.connection.state == ConnectionState.connected
```

---

## Notes

- **RTC8a4** (tests for both Ably token string and JWT token string) is covered implicitly: all tests above use opaque token strings. For unit tests, token format is irrelevant since tokens are passed through to the server without client-side parsing. Integration tests should verify both formats against the sandbox.
- For token **acquisition** before the initial connection, see `connection_auth_test.md` (RTN2e, RTN27b).
- For server-initiated reauthorization (RTN22), see `connection_failures_test.md`.
