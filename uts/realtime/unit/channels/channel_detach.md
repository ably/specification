# RealtimeChannel Detach Tests

Spec points: `RTL5`, `RTL5a`, `RTL5b`, `RTL5d`, `RTL5e`, `RTL5f`, `RTL5i`, `RTL5j`, `RTL5k`, `RTL5l`

## Test Type
Unit test with mocked WebSocket

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTL5a - Detach when initialized is no-op

**Spec requirement:** If the channel state is INITIALIZED or DETACHED nothing is done.

Tests that detach on an initialized channel returns immediately.

### Setup
```pseudo
channel_name = "test-RTL5a-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE)
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
ASSERT channel.state == ChannelState.initialized

# Detach from initialized state - should be no-op
AWAIT channel.detach()
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.initialized OR channel.state == ChannelState.detached
# No state change events should have been emitted (or only to detached)
CLOSE_CLIENT(client)
```

---

## RTL5a - Detach when already detached is no-op

**Spec requirement:** If the channel state is INITIALIZED or DETACHED nothing is done.

Tests that detach on an already-detached channel returns immediately.

### Setup
```pseudo
channel_name = "test-RTL5a-detached-${random_id()}"
detach_message_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == DETACH:
      detach_message_count++
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Attach then detach
AWAIT channel.attach()
AWAIT channel.detach()
ASSERT channel.state == ChannelState.detached
ASSERT detach_message_count == 1

# Second detach - should be no-op
AWAIT channel.detach()
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.detached
ASSERT detach_message_count == 1  # No additional DETACH message sent
CLOSE_CLIENT(client)
```

---

## RTL5i - Detach while detaching waits for completion

**Spec requirement:** If the channel is in a pending state DETACHING, do the detach operation after the completion of the pending request.

Tests that calling detach while already detaching waits for the first detach to complete.

### Setup
```pseudo
channel_name = "test-RTL5i-${random_id()}"
detach_message_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == DETACH:
      detach_message_count++
      # Delay response to allow second detach call
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()

# Start first detach (don't await)
detach_future_1 = channel.detach()

# Wait for channel to enter detaching state
AWAIT_STATE channel.state == ChannelState.detaching

# Start second detach while first is pending
detach_future_2 = channel.detach()

# Now send the DETACHED response
mock_ws.send_to_client(ProtocolMessage(
  action: DETACHED,
  channel: channel_name
))

# Both should complete
AWAIT detach_future_1
AWAIT detach_future_2
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.detached
ASSERT detach_message_count == 1  # Only one DETACH message sent
CLOSE_CLIENT(client)
```

---

## RTL5i - Detach while attaching waits then detaches

**Spec requirement:** If the channel is in a pending state ATTACHING, do the detach operation after the completion of the pending request.

Tests that calling detach while attaching waits for attach to complete, then detaches.

> **Implementation note:** When detach is called while the channel is ATTACHING,
> the attach future/promise may be rejected in some implementations (since the
> intent has changed to detach). Other implementations may resolve the attach
> future when ATTACHED arrives, before proceeding to detach. Both behaviors are
> acceptable — implementations should handle both outcomes and suppress unhandled
> rejection errors from the superseded attach operation.

### Setup
```pseudo
channel_name = "test-RTL5i-attaching-${random_id()}"
messages_from_client = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    messages_from_client.append(msg)
    IF msg.action == ATTACH:
      # Delay response
    ELSE IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Start attach (don't await)
attach_future = channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching

# Start detach while attaching
detach_future = channel.detach()

# Send ATTACHED response - attach completes
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: channel_name
))

# Wait for both operations
AWAIT attach_future
AWAIT detach_future
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.detached
# Should have: ATTACH, DETACH
ASSERT length(messages_from_client) == 2
ASSERT messages_from_client[0].action == ATTACH
ASSERT messages_from_client[1].action == DETACH
CLOSE_CLIENT(client)
```

---

## RTL5b - Detach from failed state results in error

**Spec requirement:** If the channel state is FAILED, the detach request results in an error.

Tests that detach fails when channel is in failed state.

### Setup
```pseudo
channel_name = "test-RTL5b-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Fail the attachment
      mock_ws.send_to_client(ProtocolMessage(
        action: ERROR,
        channel: channel_name,
        error: ErrorInfo(code: 40160, message: "Not permitted")
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Attach fails - channel enters failed state
AWAIT channel.attach() FAILS WITH attach_error
ASSERT channel.state == ChannelState.failed

# Try to detach from failed state
AWAIT channel.detach() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
ASSERT channel.state == ChannelState.failed  # State unchanged
CLOSE_CLIENT(client)
```

---

## RTL5j - Detach from suspended transitions to detached

**Spec requirement:** If the channel state is SUSPENDED, the detach request transitions the channel immediately to the DETACHED state.

Tests that detach from suspended state transitions directly to detached without sending DETACH message.

### Setup
```pseudo
channel_name = "test-RTL5j-${random_id()}"
detach_message_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Don't respond - let it timeout to suspended
    ELSE IF msg.action == DETACH:
      detach_message_count++
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  realtimeRequestTimeout: 100  # Short timeout
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Start attach
attach_future = channel.attach()

# Let it timeout to suspended
ADVANCE_TIME(150)
AWAIT attach_future FAILS WITH error
ASSERT channel.state == ChannelState.suspended

# Detach from suspended
AWAIT channel.detach()
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.detached
ASSERT detach_message_count == 0  # No DETACH message sent - immediate transition
CLOSE_CLIENT(client)
```

---

## RTL5l - Detach when connection not connected transitions immediately

**Spec requirement:** If the connection state is anything other than CONNECTED and none of the preceding channel state conditions apply, the channel transitions immediately to the DETACHED state.

Tests that detach transitions immediately to detached when connection is not connected.

### Setup
```pseudo
channel_name = "test-RTL5l-${random_id()}"
detach_message_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    # Delay connection
  },
  onMessageFromClient: (msg) => {
    IF msg.action == DETACH:
      detach_message_count++
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Start connecting but don't complete
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connecting

# Put channel into attaching state
attach_future = channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching

# Now detach while connection is still connecting
AWAIT channel.detach()
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.detached
ASSERT detach_message_count == 0  # No DETACH message sent
CLOSE_CLIENT(client)
```

---

### RTL5l - Detach ATTACHED channel when connection disconnected

When an ATTACHED channel is detached while the connection is DISCONNECTED,
the channel transitions directly to DETACHED without sending a DETACH message
(since the transport is unavailable).

#### Setup

```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) =>
    mock_ws.active_connection = conn
    conn.respond_with_connected()
)
install_mock(mock_ws)

client = create_realtime_client(ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

channel = client.channels.get("test-channel")
```

#### Test Steps

```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Attach the channel
mock_ws.onMessageFromClient = (msg) =>
  IF msg.action == ATTACH:
    mock_ws.active_connection.send_to_client(ProtocolMessage(
      action: ATTACHED,
      channel: msg.channel
    ))
channel.attach()
AWAIT_STATE channel.state == ChannelState.attached

# Disconnect the transport
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Now detach while disconnected
messages_sent = []
mock_ws.onMessageFromClient = (msg) => messages_sent.push(msg)

channel.detach()
AWAIT_STATE channel.state == ChannelState.detached
```

#### Assertions

```pseudo
# Channel transitions directly to DETACHED
ASSERT channel.state == ChannelState.detached

# No DETACH message was sent (transport is unavailable)
detach_messages = messages_sent.filter(m => m.action == DETACH)
ASSERT detach_messages.length == 0
```

---

## RTL5d - Normal detach flow

**Spec requirement:** A DETACH ProtocolMessage is sent to the server, the state transitions to DETACHING and the channel becomes DETACHED when the confirmation DETACHED ProtocolMessage is received.

Tests the normal detach flow when connection is connected.

### Setup
```pseudo
channel_name = "test-RTL5d-${random_id()}"
captured_detach_message = null

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == DETACH:
      captured_detach_message = msg
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()

state_during_detach = null
channel.on(ChannelEvent.detaching).listen((change) => {
  state_during_detach = channel.state
})

AWAIT channel.detach()
```

### Assertions
```pseudo
ASSERT state_during_detach == ChannelState.detaching
ASSERT channel.state == ChannelState.detached
ASSERT captured_detach_message IS NOT null
ASSERT captured_detach_message.action == DETACH
ASSERT captured_detach_message.channel == channel_name
CLOSE_CLIENT(client)
```

---

## RTL5f - Detach timeout returns to previous state

**Spec requirement:** If a DETACHED ProtocolMessage is not received within realtimeRequestTimeout, the detach request should be treated as though it has failed and the channel will return to its previous state.

Tests detach timeout behavior.

### Setup
```pseudo
channel_name = "test-RTL5f-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == DETACH:
      # Don't respond - simulate timeout
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  realtimeRequestTimeout: 100  # Short timeout
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()
ASSERT channel.state == ChannelState.attached

detach_future = channel.detach()

# Advance time past timeout
ADVANCE_TIME(150)

AWAIT detach_future FAILS WITH error
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached  # Returns to previous state
ASSERT error IS NOT null
CLOSE_CLIENT(client)
```

---

## RTL5k - ATTACHED received while detaching sends new DETACH

**Spec requirement:** If the channel receives an ATTACHED message while in the DETACHING or DETACHED state, it should send a new DETACH message and remain in (or transition to) the DETACHING state.

Tests that unexpected ATTACHED message during detach triggers new DETACH.

### Setup
```pseudo
channel_name = "test-RTL5k-${random_id()}"
detach_message_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == DETACH:
      detach_message_count++
      IF detach_message_count == 1:
        # First DETACH: server sends ATTACHED instead of DETACHED
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: channel_name
        ))
      ELSE:
        # Second DETACH: respond correctly
        mock_ws.send_to_client(ProtocolMessage(
          action: DETACHED,
          channel: channel_name
        ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()

# Start detach
AWAIT channel.detach()
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.detached
ASSERT detach_message_count == 2  # Two DETACH messages sent
CLOSE_CLIENT(client)
```

---

## RTL5k - ATTACHED received while detached sends DETACH

**Spec requirement:** If the channel receives an ATTACHED message while in the DETACHED state, it should send a new DETACH message.

Tests that unexpected ATTACHED message while detached triggers DETACH.

### Setup
```pseudo
channel_name = "test-RTL5k-detached-${random_id()}"
detach_message_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == DETACH:
      detach_message_count++
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()
AWAIT channel.detach()
ASSERT channel.state == ChannelState.detached
ASSERT detach_message_count == 1

# Server unexpectedly sends ATTACHED while detached
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: channel_name
))

# Wait for client to respond
WAIT 100ms
```

### Assertions
```pseudo
ASSERT detach_message_count == 2  # Client sent another DETACH
ASSERT channel.state == ChannelState.detached
CLOSE_CLIENT(client)
```

---

## RTL5 - Detach emits state change events

**Spec requirement:** Channel emits state change events during detach.

Tests that appropriate state change events are emitted during detach.

### Setup
```pseudo
channel_name = "test-RTL5-events-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)

state_changes = []
channel.on().listen((change) => state_changes.append(change))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()
state_changes.clear()  # Clear attach state changes

AWAIT channel.detach()
```

### Assertions
```pseudo
ASSERT length(state_changes) >= 2

# First event: detaching
ASSERT state_changes[0].current == ChannelState.detaching
ASSERT state_changes[0].previous == ChannelState.attached
ASSERT state_changes[0].event == ChannelEvent.detaching

# Second event: detached
ASSERT state_changes[1].current == ChannelState.detached
ASSERT state_changes[1].previous == ChannelState.detaching
ASSERT state_changes[1].event == ChannelEvent.detached
CLOSE_CLIENT(client)
```

---

## [REMOVED] RTL5 - Detach clears errorReason

**This test has been removed.** The features spec (RTL5a through RTL5l) does not specify that detach clears errorReason. Channel errorReason is cleared by a successful attach (RTL4c) and by connection reconnect (RTN11d). Detach is not among them. The original test scenario (FAILED → re-attach → detach → assert null) was accidentally correct because the re-attach cleared errorReason via RTL4c, not because detach did anything.
