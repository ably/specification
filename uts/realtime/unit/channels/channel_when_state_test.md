# RealtimeChannel whenState Tests (RTL25)

Spec points: `RTL25`, `RTL25a`, `RTL25b`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## Purpose

`RealtimeChannel#whenState` is a convenience function for waiting on channel state:
- If the channel is already in the given state, it resolves immediately
  with a `null` value (RTL25a).
- Otherwise, it waits for the given state to be reached, and resolves
  with the `ChannelStateChange` when the state is reached (RTL25b).

This mirrors the `Connection#whenState` function (RTN26).

---

## RTL25a - whenState resolves immediately if already in state

**Spec requirement:** If the channel is already in the given state, resolves
immediately with a `null` value.

Tests that whenState resolves immediately when the channel is already
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
result = AWAIT channel.whenState(ChannelState.attached)
```

### Assertions
```pseudo
# whenState resolved immediately with null (already in target state)
ASSERT result IS null
CLOSE_CLIENT(client)
```

---

## RTL25b - whenState waits for state if not already in it

**Spec requirement:** If the channel is not in the given state, waits for the
state to be reached and resolves with the `ChannelStateChange`.

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

# Channel is in INITIALIZED state — start waiting for ATTACHED
when_state_promise = channel.whenState(ChannelState.attached)

# Attach the channel (this triggers the state transition)
AWAIT channel.attach()

# Now await the whenState result
result = AWAIT when_state_promise
```

### Assertions
```pseudo
# whenState resolved with a ChannelStateChange object (not null)
ASSERT result IS NOT null
ASSERT result.current == ChannelState.attached
ASSERT result.previous IN [ChannelState.initialized, ChannelState.attaching]
CLOSE_CLIENT(client)
```

---

## RTL25b - whenState only fires once

**Spec requirement:** whenState resolves only once, even if the state is entered
multiple times. Subsequent entries into the same state do not trigger additional
resolutions.

Tests that the whenState resolution is one-shot even if the state is entered
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

# Register a side-effect counter via a listener wrapping whenState
attach_count = 0
channel.once(ChannelState.attached, () => { attach_count++ })

# Also start a whenState that we'll use to verify one-shot behavior
when_state_promise = channel.whenState(ChannelState.attached)

# First attach
AWAIT channel.attach()
result = AWAIT when_state_promise
ASSERT result IS NOT null
ASSERT attach_count == 1

# Detach
AWAIT channel.detach()

# Second attach — a new whenState should be needed; the old one is consumed
AWAIT channel.attach()
WAIT(50)
```

### Assertions
```pseudo
# The once listener only fired once (confirming one-shot semantics)
ASSERT attach_count == 1
CLOSE_CLIENT(client)
```

---

## RTL25a - whenState for past state does not fire

**Spec requirement:** whenState checks the current state. If the channel has
already passed through a state but is no longer in it, whenState should NOT
resolve immediately.

Tests that whenState for a state that was previously visited but is no longer
current does not resolve.

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
resolved = false

# Start whenState but do NOT await — check that it does not resolve
when_state_promise = channel.whenState(ChannelState.attaching)
when_state_promise.then(() => { resolved = true })

# Wait to see if it resolves
WAIT(200)
```

### Assertions
```pseudo
# whenState should NOT have resolved (we're not in ATTACHING state anymore)
ASSERT resolved == false
CLOSE_CLIENT(client)
```
