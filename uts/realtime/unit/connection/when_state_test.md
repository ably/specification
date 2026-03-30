# Connection whenState Tests (RTN26)

Spec points: `RTN26`, `RTN26a`, `RTN26b`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/client/realtime_client.md` for the full Mock WebSocket Infrastructure specification.

---

## RTN26a - whenState calls listener immediately if already in state

**Spec requirement:** If the connection is already in the given state, calls the listener with a null argument.

Tests that whenState invokes callback immediately when the connection is already in the target state.

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
# Start connection
client.connect()

# Wait for CONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds

# Now call whenState for the current state
callback_invoked = false
callback_arg = undefined

client.connection.whenState(ConnectionState.connected, (change) => {
  callback_invoked = true
  callback_arg = change
})

# Callback should be invoked synchronously or very quickly
WAIT(50)
```

### Assertions

```pseudo
# Callback was invoked immediately
ASSERT callback_invoked == true

# Callback was invoked with null argument (not a StateChange object)
ASSERT callback_arg IS null
```

---

## RTN26b - whenState waits for state if not already in it

**Spec requirement:** Else, calls #once with the given state and listener.

Tests that whenState waits for state transition when not currently in the target state.

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
# Connection is in INITIALIZED state
ASSERT client.connection.state == ConnectionState.initialized

# Set up whenState before connecting
callback_invoked = false
callback_arg = undefined

client.connection.whenState(ConnectionState.connected, (change) => {
  callback_invoked = true
  callback_arg = change
})

# Callback should not be invoked yet
ASSERT callback_invoked == false

# Start connection
client.connect()

# Wait for CONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds

# Give callback a moment to execute
WAIT(50)
```

### Assertions

```pseudo
# Callback was invoked after state transition
ASSERT callback_invoked == true

# Callback was invoked with a ConnectionStateChange object (not null)
ASSERT callback_arg IS NOT null
ASSERT callback_arg.previous IN [ConnectionState.initialized, ConnectionState.connecting]
ASSERT callback_arg.current == ConnectionState.connected
```

---

## RTN26b - whenState only fires once

**Spec requirement:** whenState uses #once, meaning it should only fire once, not on every subsequent occurrence of the state.

Tests that whenState callback is invoked only once even if state is entered multiple times.

### Setup

```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    
    IF connection_attempt_count == 1:
      # First attempt: connect then disconnect
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
    ELSE:
      # Second attempt: connect again
      conn.respond_with_success()
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-id-2",
        connectionKey: "connection-key-2",
        connectionDetails: ConnectionDetails(
          connectionKey: "connection-key-2",
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

# Set up whenState listener
callback_count = 0

client.connection.whenState(ConnectionState.connected, (change) => {
  callback_count++
})

# Start connection
client.connect()

# Wait for first CONNECTED
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds

WAIT(50)

# Verify callback was invoked once
ASSERT callback_count == 1

# Force a disconnection
mock_ws.active_connection.close()

# Wait for DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 2 seconds

# Advance time to trigger reconnection
ADVANCE_TIME(150)

# Wait for second CONNECTED
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds

WAIT(50)
```

### Assertions

```pseudo
# Callback was still only invoked once (not again on reconnection)
ASSERT callback_count == 1
```

---

## RTN26a - Multiple whenState calls

**Spec requirement:** Multiple calls to whenState should each be handled independently.

Tests that multiple whenState listeners can be registered and each behaves correctly.

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
# Set up multiple whenState listeners before connecting
callback1_invoked = false
callback2_invoked = false
callback3_invoked = false

client.connection.whenState(ConnectionState.connected, (change) => {
  callback1_invoked = true
})

client.connection.whenState(ConnectionState.connected, (change) => {
  callback2_invoked = true
})

client.connection.whenState(ConnectionState.connecting, (change) => {
  callback3_invoked = true
})

# Start connection
client.connect()

# Wait for CONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds

WAIT(50)
```

### Assertions

```pseudo
# All whenState callbacks were invoked
ASSERT callback1_invoked == true
ASSERT callback2_invoked == true
ASSERT callback3_invoked == true
```

---

## RTN26a - whenState with already-passed state

**Spec requirement:** whenState should invoke immediately with null if already in the target state.

Tests that whenState for a state that was passed but is no longer current does NOT fire immediately.

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
# Start connection
client.connect()

# Wait for CONNECTED state
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds

# Now call whenState for a past state (CONNECTING)
callback_invoked = false

client.connection.whenState(ConnectionState.connecting, (change) => {
  callback_invoked = true
})

# Wait to see if callback is invoked
WAIT(200)
```

### Assertions

```pseudo
# Callback should NOT be invoked (we're not in CONNECTING state anymore)
ASSERT callback_invoked == false

# This demonstrates whenState checks current state, not historical states
```

---

## RTN26 - whenState with different states

**Spec requirement:** whenState should work correctly for all connection states.

Tests that whenState functions correctly across different state transitions.

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
# Set up whenState listeners for various states
initialized_fired = false
connecting_fired = false
disconnected_fired = false

client.connection.whenState(ConnectionState.initialized, (change) => {
  initialized_fired = true
})

client.connection.whenState(ConnectionState.connecting, (change) => {
  connecting_fired = true
})

client.connection.whenState(ConnectionState.disconnected, (change) => {
  disconnected_fired = true
})

# Initially in INITIALIZED
WAIT(50)

# Should fire immediately for current state
ASSERT initialized_fired == true
ASSERT connecting_fired == false
ASSERT disconnected_fired == false

# Start connection
client.connect()

# Wait for DISCONNECTED (connection will fail)
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 5 seconds

WAIT(50)
```

### Assertions

```pseudo
# All states were reached and callbacks invoked
ASSERT initialized_fired == true
ASSERT connecting_fired == true
ASSERT disconnected_fired == true
```

---

## Implementation Notes

The `whenState` function is a convenience utility that:

1. **Immediate invocation**: If `connection.state == targetState`, invoke callback with `null` immediately
2. **Deferred invocation**: Otherwise, it's equivalent to `connection.once(targetState, callback)`
3. **One-time only**: Each `whenState` call fires at most once
4. **Multiple calls**: Multiple `whenState` calls with same state are independent
5. **Return value**: Some implementations may return a way to unregister the listener (implementation-specific)

Implementations may differ in:
- Whether immediate invocation is synchronous or scheduled for next tick
- Whether a cleanup/unregister function is returned
- Exact behavior with edge cases like rapid state changes
