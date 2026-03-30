# Channel ERROR Protocol Message Tests

Spec points: `RTL14`

## Test Type
Unit test with mocked WebSocket

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTL14 - Channel ERROR transitions ATTACHED channel to FAILED

**Spec requirement:** If an ERROR ProtocolMessage is received for this channel (the channel attribute matches this channel's name), then the channel should immediately transition to the FAILED state, and the RealtimeChannel.errorReason should be set.

Tests that receiving a channel-scoped ERROR while ATTACHED causes the channel to transition to FAILED with the error.

### Setup
```pseudo
channel_name = "test-RTL14-attached-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
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

# Record channel state changes
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Server sends channel-scoped ERROR (e.g., permission revoked)
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ERROR,
  channel: channel_name,
  error: ErrorInfo(code: 40160, statusCode: 401, message: "Not permitted")
))
AWAIT_STATE channel.state == ChannelState.failed
```

### Assertions
```pseudo
# Channel transitioned to FAILED
ASSERT channel.state == ChannelState.failed

# errorReason is set
ASSERT channel.errorReason IS NOT null
ASSERT channel.errorReason.code == 40160
ASSERT channel.errorReason.statusCode == 401
ASSERT channel.errorReason.message CONTAINS "Not permitted"

# State change event emitted
ASSERT length(channel_state_changes) == 1
ASSERT channel_state_changes[0].current == ChannelState.failed
ASSERT channel_state_changes[0].previous == ChannelState.attached
ASSERT channel_state_changes[0].reason IS NOT null
ASSERT channel_state_changes[0].reason.code == 40160

# Connection stays open (channel-scoped ERROR does NOT close connection)
ASSERT client.connection.state == ConnectionState.connected
```

---

## RTL14 - Channel ERROR transitions ATTACHING channel to FAILED

**Spec requirement:** If an ERROR ProtocolMessage is received for this channel, the channel should immediately transition to FAILED.

Tests that receiving a channel-scoped ERROR while ATTACHING causes the channel to transition to FAILED and the pending attach operation to fail.

### Setup
```pseudo
channel_name = "test-RTL14-attaching-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Respond with channel ERROR instead of ATTACHED
      mock_ws.send_to_client(ProtocolMessage(
        action: ERROR,
        channel: msg.channel,
        error: ErrorInfo(code: 40160, statusCode: 401, message: "Not permitted")
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

# Attach should fail
AWAIT channel.attach() FAILS WITH error
```

### Assertions
```pseudo
# Channel is in FAILED state
ASSERT channel.state == ChannelState.failed

# errorReason is set
ASSERT channel.errorReason IS NOT null
ASSERT channel.errorReason.code == 40160

# The error from attach() matches the channel error
ASSERT error.code == 40160

# Connection stays open
ASSERT client.connection.state == ConnectionState.connected
```

---

## RTL14 - Channel ERROR completes pending detach with error

**Spec requirement:** If an ERROR ProtocolMessage is received for this channel, the channel should immediately transition to FAILED.

Tests that if a channel ERROR is received while a detach is pending (DETACHING state), the channel transitions to FAILED and the pending detach operation fails with the error.

### Setup
```pseudo
channel_name = "test-RTL14-detaching-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel
      ))
    ELSE IF msg.action == DETACH:
      # Respond with ERROR instead of DETACHED
      mock_ws.send_to_client(ProtocolMessage(
        action: ERROR,
        channel: msg.channel,
        error: ErrorInfo(code: 90198, statusCode: 500, message: "Detach failed")
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

# Detach should fail
AWAIT channel.detach() FAILS WITH error
```

### Assertions
```pseudo
# Channel is in FAILED state (not DETACHED)
ASSERT channel.state == ChannelState.failed

# errorReason is set
ASSERT channel.errorReason IS NOT null
ASSERT channel.errorReason.code == 90198

# The error from detach() matches
ASSERT error.code == 90198

# Connection stays open
ASSERT client.connection.state == ConnectionState.connected
```

---

## RTL14 - Channel ERROR does not affect other channels

**Spec requirement:** The ERROR ProtocolMessage with a channel attribute only affects that specific channel.

Tests that a channel-scoped ERROR only transitions the target channel to FAILED, leaving other channels unaffected.

### Setup
```pseudo
channel_name_a = "test-RTL14-a-${random_id()}"
channel_name_b = "test-RTL14-b-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
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
channel_a = client.channels.get(channel_name_a)
channel_b = client.channels.get(channel_name_b)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel_a.attach()
AWAIT channel_b.attach()
ASSERT channel_a.state == ChannelState.attached
ASSERT channel_b.state == ChannelState.attached

# Send ERROR only for channel A
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ERROR,
  channel: channel_name_a,
  error: ErrorInfo(code: 40160, statusCode: 401, message: "Not permitted")
))
AWAIT_STATE channel_a.state == ChannelState.failed
```

### Assertions
```pseudo
# Channel A is FAILED
ASSERT channel_a.state == ChannelState.failed
ASSERT channel_a.errorReason IS NOT null

# Channel B is unaffected
ASSERT channel_b.state == ChannelState.attached
ASSERT channel_b.errorReason IS null

# Connection stays open
ASSERT client.connection.state == ConnectionState.connected
```

---

## RTL14 - Channel ERROR cancels pending timers

**Spec requirement:** When the channel transitions to FAILED, any pending timers (attach timeout, channel retry) should be cancelled.

Tests that receiving a channel ERROR while a channel retry timer is pending cancels the timer.

### Setup
```pseudo
channel_name = "test-RTL14-timers-${random_id()}"
attach_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      IF attach_count == 1:
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: msg.channel
        ))
      # Don't respond to subsequent attaches
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  realtimeRequestTimeout: 100,
  suspendedRetryTimeout: 200
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

# Trigger server-initiated DETACHED -> reattach -> timeout -> SUSPENDED
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: DETACHED,
  channel: channel_name,
  error: ErrorInfo(code: 90198, statusCode: 500, message: "Detach")
))
ADVANCE_TIME(150)
AWAIT_STATE channel.state == ChannelState.suspended

# Channel retry timer is now pending (suspendedRetryTimeout = 200ms)
# Send ERROR before the retry fires
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ERROR,
  channel: channel_name,
  error: ErrorInfo(code: 40160, statusCode: 401, message: "Not permitted")
))
AWAIT_STATE channel.state == ChannelState.failed

attach_count_after_error = attach_count

# Advance time well past the suspendedRetryTimeout
ADVANCE_TIME(500)
```

### Assertions
```pseudo
# Channel remains FAILED - no retry was attempted
ASSERT channel.state == ChannelState.failed
ASSERT attach_count == attach_count_after_error
```
