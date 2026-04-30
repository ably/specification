# Server-Initiated Re-authentication Tests

Spec points: `RTN22`, `RTN22a`

## Test Type
Unit test with mocked WebSocket client and authCallback

## Mock Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Purpose

These tests verify that when Ably sends an `AUTH` protocol message to a connected client,
the client immediately starts a new authentication process as described in RTC8: it obtains
a new token via the configured auth mechanism and sends an `AUTH` protocol message back to
Ably containing the new token.

RTN22a covers the fallback: if the client does not re-authenticate within an acceptable
period, Ably forcibly disconnects via a `DISCONNECTED` message with a token error code
(40140–40149), triggering RTN15h token-error recovery.

---

## RTN22 - Server sends AUTH, client re-authenticates

**Spec requirement:** Ably can request that a connected client re-authenticates by sending the client an `AUTH` ProtocolMessage. The client must then immediately start a new authentication process as described in RTC8.

Tests that receiving an `AUTH` message from the server triggers the client to obtain a new token and send an `AUTH` message back.

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

# Record state changes during reauth
state_changes = []
client.connection.on((change) => {
  state_changes.append(change)
})

# When client sends AUTH back, record it and respond with CONNECTED (update)
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

# Server requests re-authentication
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: AUTH
))

# Wait for the UPDATE event that signals reauth completion
AWAIT UNTIL state_changes.any(c => c.event == ConnectionEvent.update)
```

### Assertions
```pseudo
# authCallback was called twice: once for initial connect, once for reauth
ASSERT auth_callback_count == 2

# Client sent AUTH message back with new token
ASSERT captured_auth_messages.length == 1
ASSERT captured_auth_messages[0].auth IS NOT null
ASSERT captured_auth_messages[0].auth.accessToken == "token-2"

# Connection stayed CONNECTED throughout (no state transitions, only UPDATE)
connected_to_other = state_changes.filter(c => c.current != ConnectionState.connected)
ASSERT connected_to_other.length == 0

# UPDATE event was emitted (RTN24)
update_events = state_changes.filter(c => c.event == ConnectionEvent.update)
ASSERT update_events.length == 1
CLOSE_CLIENT(client)
```

---

## RTN22 - Connection remains CONNECTED during server-initiated reauth

**Spec requirement:** The re-authentication triggered by the server's AUTH message must follow the RTC8 flow — if the connection is CONNECTED, an AUTH message is sent without disconnecting.

Tests that the connection state does not change during server-initiated re-authentication.

### Setup
```pseudo
auth_callback_count = 0

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  RETURN TokenDetails(
    token: "reauth-token-" + str(auth_callback_count),
    expires: now() + 3600000
  )

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "conn-1",
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

# Auto-respond to AUTH with CONNECTED
mock_ws.on_client_message((msg) => {
  IF msg.action == AUTH:
    mock_ws.active_connection.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "conn-1",
      connectionKey: "key-1-updated",
      connectionDetails: ConnectionDetails(
        connectionKey: "key-1-updated",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
})

client = Realtime(options: ClientOptions(
  authCallback: auth_callback,
  autoConnect: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

state_changes = []
client.connection.on((change) => {
  state_changes.append(change)
})

# Server sends AUTH
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: AUTH
))

# Wait for UPDATE event
AWAIT UNTIL state_changes.length >= 1
```

### Assertions
```pseudo
# Connection never left CONNECTED
ASSERT client.connection.state == ConnectionState.connected

# Only an UPDATE event, no state change events
ASSERT state_changes.length == 1
ASSERT state_changes[0].event == ConnectionEvent.update
ASSERT state_changes[0].current == ConnectionState.connected
ASSERT state_changes[0].previous == ConnectionState.connected
CLOSE_CLIENT(client)
```

---

## RTN22a - Forced disconnect on reauth failure

**Spec requirement:** Ably reserves the right to forcibly disconnect a client that does not re-authenticate within an acceptable period. A client is forcibly disconnected following a `DISCONNECTED` message containing an error code in the range 40140–40149. This forces the client to re-authenticate and resume via RTN15h.

Tests that when the server sends a `DISCONNECTED` message with a token error code after requesting reauth, the client transitions to DISCONNECTED and initiates token-error recovery.

### Setup
```pseudo
auth_callback_count = 0

auth_callback = FUNCTION(params):
  auth_callback_count = auth_callback_count + 1
  RETURN TokenDetails(
    token: "recovery-token-" + str(auth_callback_count),
    expires: now() + 3600000
  )

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "conn-1",
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
  authCallback: auth_callback,
  autoConnect: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

state_changes = []
client.connection.on((change) => {
  state_changes.append(change)
})

# Server forcibly disconnects with token error (simulating reauth timeout)
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: DISCONNECTED,
  error: ErrorInfo(
    message: "Token expired",
    code: 40142,
    statusCode: 401
  )
))

# Wait for client to transition to DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected
```

### Assertions
```pseudo
# Client transitioned to DISCONNECTED with the token error
disconnected_change = state_changes.find(c => c.current == ConnectionState.disconnected)
ASSERT disconnected_change IS NOT null
ASSERT disconnected_change.reason.code == 40142

# The client should attempt to reconnect (RTN15h token-error recovery
# will obtain a new token and reconnect)
CLOSE_CLIENT(client)
```

### Note
The full RTN15h recovery flow (obtain new token, reconnect) is tested in `connection_failures_test.md`. This test only verifies that the forced disconnect with a token error code is handled correctly as the entry point for that recovery.
