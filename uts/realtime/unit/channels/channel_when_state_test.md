# RealtimeChannel whenState Tests (RTL25)

Spec points: `RTL25`, `RTL25a`, `RTL25b`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## Purpose

`RealtimeChannel#whenState` is a convenience function for waiting on channel state:
- If the channel is already in the given state, the listener is called immediately
  with a `null` argument (RTL25a).
- Otherwise, the listener is registered with `#once` for the given state, and
  called with the `ChannelStateChange` when the state is reached (RTL25b).

This mirrors the `Connection#whenState` function (RTN26).

---

## RTL25a - whenState calls listener immediately if already in state

**Spec requirement:** If the channel is already in the given state, calls the
listener with a `null` argument.

Tests that whenState invokes the callback immediately when the channel is already
in the target state.

### Setup
```pseudo
channel_name = "test-RTL25a-immediate-${random_id()}"

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
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: 0
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Channel is now ATTACHED — call whenState for current state
callback_invoked = false
callback_arg = undefined

channel.whenState(ChannelState.attached, (change) => {
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

# Callback was invoked with null argument (not a ChannelStateChange object)
ASSERT callback_arg IS null
```

---

## RTL25b - whenState waits for state if not already in it

**Spec requirement:** Else, calls `#once` with the given state and listener.

Tests that whenState waits for a state transition when the channel is not currently
in the target state.

### Setup
```pseudo
channel_name = "test-RTL25b-deferred-${random_id()}"

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
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: 0
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Channel is in INITIALIZED state — register whenState for ATTACHED
callback_invoked = false
callback_arg = undefined

channel.whenState(ChannelState.attached, (change) => {
  callback_invoked = true
  callback_arg = change
})

# Callback should not be invoked yet
ASSERT callback_invoked == false

# Attach the channel
AWAIT channel.attach()

# Give callback a moment to execute
WAIT(50)
```

### Assertions
```pseudo
# Callback was invoked after state transition
ASSERT callback_invoked == true

# Callback was invoked with a ChannelStateChange object (not null)
ASSERT callback_arg IS NOT null
ASSERT callback_arg.current == ChannelState.attached
ASSERT callback_arg.previous IN [ChannelState.initialized, ChannelState.attaching]
```

---

## RTL25b - whenState only fires once

**Spec requirement:** whenState uses `#once`, meaning it should only fire once,
not on every subsequent occurrence of the state.

Tests that the whenState callback is invoked only once even if the state is entered
multiple times.

### Setup
```pseudo
channel_name = "test-RTL25b-once-${random_id()}"

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
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: 0
      ))
    IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Register whenState for ATTACHED
callback_count = 0

channel.whenState(ChannelState.attached, (change) => {
  callback_count++
})

# First attach
AWAIT channel.attach()
WAIT(50)

# Verify callback was invoked once
ASSERT callback_count == 1

# Detach
AWAIT channel.detach()

# Second attach
AWAIT channel.attach()
WAIT(50)
```

### Assertions
```pseudo
# Callback was still only invoked once (not again on second attach)
ASSERT callback_count == 1
```

---

## RTL25a - whenState for past state does not fire

**Spec requirement:** whenState checks the current state. If the channel has
already passed through a state but is no longer in it, whenState should NOT
invoke the callback immediately.

Tests that whenState for a state that was previously visited but is no longer
current does not fire.

### Setup
```pseudo
channel_name = "test-RTL25a-past-${random_id()}"

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
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: 0
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Attach — channel passes through ATTACHING to reach ATTACHED
AWAIT channel.attach()
ASSERT channel.state == ChannelState.attached

# Now call whenState for ATTACHING — a past state, not the current one
callback_invoked = false

channel.whenState(ChannelState.attaching, (change) => {
  callback_invoked = true
})

# Wait to see if callback is invoked
WAIT(200)
```

### Assertions
```pseudo
# Callback should NOT be invoked (we're not in ATTACHING state anymore)
ASSERT callback_invoked == false
```
