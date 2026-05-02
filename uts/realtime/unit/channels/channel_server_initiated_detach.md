# Server-Initiated DETACHED and Channel Retry Tests

Spec points: `RTL13`, `RTL13a`, `RTL13b`, `RTL13c`

## Test Type
Unit test with mocked WebSocket and fake timers

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTL13a - Server DETACHED on ATTACHED channel triggers immediate reattach

| Spec | Requirement |
|------|-------------|
| RTL13 | If the channel receives a server-initiated DETACHED when ATTACHING, ATTACHED, or SUSPENDED, specific handling applies |
| RTL13a | If ATTACHED or SUSPENDED, an immediate reattach attempt should be made by sending ATTACH, transitioning to ATTACHING with the error from the DETACHED message |

Tests that receiving a server-initiated DETACHED while ATTACHED causes the channel to transition to ATTACHING with the error, send a new ATTACH message, and successfully reattach.

### Setup
```pseudo
channel_name = "test-RTL13a-attached-${random_id()}"
attach_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel
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
ASSERT channel.state == ChannelState.attached
ASSERT attach_count == 1

# Record channel state changes from this point
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Server sends unsolicited DETACHED with error
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: DETACHED,
  channel: channel_name,
  error: ErrorInfo(code: 90198, statusCode: 500, message: "Server detached channel")
))

# Channel should reattach automatically
AWAIT_STATE channel.state == ChannelState.attached
```

### Assertions
```pseudo
# Two ATTACH messages total: initial + reattach
ASSERT attach_count == 2

# State change sequence: ATTACHING (with error) -> ATTACHED
ASSERT length(channel_state_changes) >= 2
ASSERT channel_state_changes[0].current == ChannelState.attaching
ASSERT channel_state_changes[0].previous == ChannelState.attached
ASSERT channel_state_changes[0].reason IS NOT null
ASSERT channel_state_changes[0].reason.code == 90198
ASSERT channel_state_changes[1].current == ChannelState.attached
CLOSE_CLIENT(client)
```

---

## RTL13a - Server DETACHED on SUSPENDED channel triggers immediate reattach

**Spec requirement:** If the channel is in the SUSPENDED state and receives a server-initiated DETACHED, an immediate reattach attempt should be made.

Tests that receiving a server-initiated DETACHED while SUSPENDED causes the channel to transition to ATTACHING and reattach.

### Setup
```pseudo
channel_name = "test-RTL13a-suspended-${random_id()}"
attach_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      IF attach_count == 1:
        # First attach succeeds
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: msg.channel
        ))
      ELSE IF attach_count == 2:
        # Second attach (after timeout) - don't respond, causing timeout -> SUSPENDED
      ELSE:
        # Third attach (after server DETACHED) - succeed
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: msg.channel
        ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  realtimeRequestTimeout: 100,
  channelRetryTimeout: 60000
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

# Force channel into SUSPENDED state by triggering a reattach that times out:
# Send server-initiated DETACHED to trigger RTL13a reattach
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: DETACHED,
  channel: channel_name,
  error: ErrorInfo(code: 90198, statusCode: 500, message: "Detach 1")
))
AWAIT_STATE channel.state == ChannelState.attaching

# Let the reattach timeout -> SUSPENDED
ADVANCE_TIME(150)
AWAIT_STATE channel.state == ChannelState.suspended

# Now send another server-initiated DETACHED while SUSPENDED
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: DETACHED,
  channel: channel_name,
  error: ErrorInfo(code: 90199, statusCode: 500, message: "Detach 2")
))

# Channel should immediately attempt to reattach and succeed
AWAIT_STATE channel.state == ChannelState.attached
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
# 3 total ATTACH messages: initial + RTL13a reattach + RTL13a reattach from SUSPENDED
ASSERT attach_count == 3
CLOSE_CLIENT(client)
```

---

## RTL13b - Failed reattach transitions to SUSPENDED with automatic retry

| Spec | Requirement |
|------|-------------|
| RTL13b | If the reattach fails, or if the channel was already ATTACHING, channel transitions to SUSPENDED. An automatic re-attach attempt is made after channelRetryTimeout. If that also fails (timeout or DETACHED), the cycle repeats indefinitely. |

Tests that when a server-initiated DETACHED triggers a reattach that times out, the channel transitions to SUSPENDED and then automatically retries after the suspended retry timeout.

### Setup
```pseudo
channel_name = "test-RTL13b-${random_id()}"
attach_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      IF attach_count == 1:
        # First attach succeeds
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: msg.channel
        ))
      ELSE IF attach_count == 2:
        # Reattach after server DETACHED - don't respond (timeout)
      ELSE IF attach_count == 3:
        # Automatic retry after channelRetryTimeout - succeed
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: msg.channel
        ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  realtimeRequestTimeout: 100,
  channelRetryTimeout: 200
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

# Record state changes
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Server sends unsolicited DETACHED
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: DETACHED,
  channel: channel_name,
  error: ErrorInfo(code: 90198, statusCode: 500, message: "Server detached")
))

# Channel should be in ATTACHING (RTL13a)
AWAIT_STATE channel.state == ChannelState.attaching
ASSERT attach_count == 2

# Let reattach timeout -> SUSPENDED (RTL13b)
ADVANCE_TIME(150)
AWAIT_STATE channel.state == ChannelState.suspended

# Wait for channelRetryTimeout to trigger automatic retry and succeed
ADVANCE_TIME(250)
AWAIT_STATE channel.state == ChannelState.attached
ASSERT attach_count == 3
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT attach_count == 3

# Verify state sequence: ATTACHING -> SUSPENDED -> ATTACHING -> ATTACHED
ASSERT channel_state_changes CONTAINS_IN_ORDER [
  ChannelState.attaching,
  ChannelState.suspended,
  ChannelState.attaching,
  ChannelState.attached
]
CLOSE_CLIENT(client)
```

---

## RTL13b - Server DETACHED while already ATTACHING transitions directly to SUSPENDED

**Spec requirement:** If the channel was already in the ATTACHING state when the server-initiated DETACHED is received, the channel transitions directly to SUSPENDED (with automatic retry).

Tests that a server-initiated DETACHED received while ATTACHING goes directly to SUSPENDED without another reattach attempt first.

### Setup
```pseudo
channel_name = "test-RTL13b-attaching-${random_id()}"
attach_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      IF attach_count == 1:
        # First attach - don't respond immediately, leave channel in ATTACHING
      ELSE IF attach_count == 2:
        # Automatic retry from SUSPENDED - succeed
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: msg.channel
        ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  realtimeRequestTimeout: 500,
  channelRetryTimeout: 200
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Start attach but don't await it (mock won't respond)
channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching

# Record state changes
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Server sends DETACHED while channel is still ATTACHING
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: DETACHED,
  channel: channel_name,
  error: ErrorInfo(code: 90198, statusCode: 500, message: "Server detached")
))

# Channel should go directly to SUSPENDED (RTL13b), not try another reattach
AWAIT_STATE channel.state == ChannelState.suspended
ASSERT attach_count == 1  # Only the original attach, no second attempt

# Wait for channelRetryTimeout — automatic retry should succeed
ADVANCE_TIME(250)
AWAIT_STATE channel.state == ChannelState.attached
ASSERT attach_count == 2
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached

# Verify direct transition to SUSPENDED (no intermediate ATTACHING)
ASSERT channel_state_changes[0].current == ChannelState.suspended
ASSERT channel_state_changes[0].previous == ChannelState.attaching
ASSERT channel_state_changes[0].reason IS NOT null
ASSERT channel_state_changes[0].reason.code == 90198
CLOSE_CLIENT(client)
```

---

## RTL13b - Repeated failures cycle SUSPENDED -> ATTACHING indefinitely

**Spec requirement:** If the re-attach also fails (timeout or DETACHED), the SUSPENDED -> retry cycle repeats indefinitely.

Tests that repeated reattach failures produce repeated SUSPENDED -> ATTACHING cycles.

### Setup
```pseudo
channel_name = "test-RTL13b-repeat-${random_id()}"
attach_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      IF attach_count == 1:
        # First attach succeeds
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: msg.channel
        ))
      ELSE IF attach_count <= 3:
        # Reattach attempts 2 and 3 - don't respond (timeout)
      ELSE:
        # Fourth attempt succeeds
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: msg.channel
        ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  realtimeRequestTimeout: 100,
  channelRetryTimeout: 200
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()
ASSERT attach_count == 1

# Record state changes
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Server sends DETACHED
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: DETACHED,
  channel: channel_name,
  error: ErrorInfo(code: 90198, statusCode: 500, message: "Detach")
))

# Cycle 1: ATTACHING (reattach) -> timeout -> SUSPENDED -> retry
AWAIT_STATE channel.state == ChannelState.attaching
ADVANCE_TIME(150)
AWAIT_STATE channel.state == ChannelState.suspended
ADVANCE_TIME(250)
AWAIT_STATE channel.state == ChannelState.attaching
ASSERT attach_count == 3

# Cycle 2: ATTACHING (retry) -> timeout -> SUSPENDED -> retry
ADVANCE_TIME(150)
AWAIT_STATE channel.state == ChannelState.suspended
ADVANCE_TIME(250)

# Fourth attempt succeeds
AWAIT_STATE channel.state == ChannelState.attached
ASSERT attach_count == 4
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT attach_count == 4

# Verify repeated cycling
ASSERT channel_state_changes CONTAINS_IN_ORDER [
  ChannelState.attaching,
  ChannelState.suspended,
  ChannelState.attaching,
  ChannelState.suspended,
  ChannelState.attaching,
  ChannelState.attached
]
CLOSE_CLIENT(client)
```

---

## RTL13c - Retry cancelled when connection is no longer CONNECTED

| Spec | Requirement |
|------|-------------|
| RTL13c | If the connection is no longer CONNECTED, the automatic re-attach attempts described in RTL13b must be cancelled, as any implicit channel state changes will be covered by RTL3 |

Tests that when the connection leaves the CONNECTED state, any pending automatic channel retry is cancelled.

### Setup
```pseudo
channel_name = "test-RTL13c-${random_id()}"
attach_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      IF attach_count == 1:
        # First attach succeeds
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: msg.channel
        ))
      ELSE:
        # Don't respond to reattach attempts (timeout)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  realtimeRequestTimeout: 100,
  channelRetryTimeout: 200
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()
ASSERT attach_count == 1

# Server sends DETACHED
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: DETACHED,
  channel: channel_name,
  error: ErrorInfo(code: 90198, statusCode: 500, message: "Detach")
))

# Reattach triggered (RTL13a) but will timeout
AWAIT_STATE channel.state == ChannelState.attaching
ADVANCE_TIME(150)
AWAIT_STATE channel.state == ChannelState.suspended

# Now disconnect the connection BEFORE the channelRetryTimeout fires
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE client.connection.state != ConnectionState.connected

# Record attach_count at this point
attach_count_after_disconnect = attach_count

# Advance time well past the channelRetryTimeout
ADVANCE_TIME(500)
```

### Assertions
```pseudo
# No additional ATTACH messages should have been sent after disconnect
ASSERT attach_count == attach_count_after_disconnect

# Channel state is now governed by RTL3, not RTL13
# (connection DISCONNECTED does not affect channel state per RTL3e,
# so channel should still be SUSPENDED)
ASSERT channel.state == ChannelState.suspended
CLOSE_CLIENT(client)
```

---

## RTL13a - DETACHED while DETACHING is not server-initiated

**Spec requirement:** RTL13 applies when the channel receives a server-initiated DETACHED when it is in ATTACHING, ATTACHED, or SUSPENDED. A channel in the DETACHING state has explicitly requested a detach, so a DETACHED response in that state is handled by the normal detach flow (RTL5), not RTL13.

Tests that receiving a DETACHED while DETACHING completes the normal detach flow rather than triggering a reattach.

### Setup
```pseudo
channel_name = "test-RTL13-detaching-${random_id()}"
attach_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel
      ))
    ELSE IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: msg.channel
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
ASSERT channel.state == ChannelState.attached

AWAIT channel.detach()
```

### Assertions
```pseudo
# Channel should be cleanly DETACHED, not re-attached
ASSERT channel.state == ChannelState.detached

# Only one ATTACH message (the initial attach, no reattach)
ASSERT attach_count == 1
CLOSE_CLIENT(client)
```
