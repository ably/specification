# Channel Properties Tests

Spec points: `RTL15`, `RTL15a`, `RTL15b`, `RTL15b1`

## Test Type
Unit test with mocked WebSocket

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTL15a - attachSerial is updated from ATTACHED message

| Spec | Requirement |
|------|-------------|
| RTL15 | `RealtimeChannel#properties` is a `ChannelProperties` object with `attachSerial` and `channelSerial` |
| RTL15a | `attachSerial` is unset when instantiated, and updated with the `channelSerial` from each ATTACHED ProtocolMessage received |

Tests that the channel's `attachSerial` property is initially unset, is set from the `channelSerial` field of the ATTACHED response, and is updated on subsequent ATTACHED messages (e.g. after reattach).

### Setup
```pseudo
channel_name = "test-RTL15a-${random_id()}"
attach_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel,
        channelSerial: "attach-serial-${attach_count}"
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
# Before connecting, attachSerial should be unset
ASSERT channel.properties.attachSerial IS null

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Attach
AWAIT channel.attach()
```

### Assertions
```pseudo
# attachSerial set from ATTACHED response
ASSERT channel.properties.attachSerial == "attach-serial-1"

# Detach and reattach to get a new attachSerial
AWAIT channel.detach()
AWAIT channel.attach()

# attachSerial updated from second ATTACHED response
ASSERT channel.properties.attachSerial == "attach-serial-2"
```

---

## RTL15a - attachSerial updated on server-initiated reattach

**Spec requirement:** `attachSerial` is updated with the `channelSerial` from each ATTACHED ProtocolMessage received.

Tests that when the server sends an unsolicited ATTACHED message (e.g. RTL2g update), the `attachSerial` is updated.

### Setup
```pseudo
channel_name = "test-RTL15a-update-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel,
        channelSerial: "initial-serial"
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
ASSERT channel.properties.attachSerial == "initial-serial"

# Server sends unsolicited ATTACHED (e.g. RTL2g update)
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: channel_name,
  channelSerial: "updated-serial"
))
AWAIT_STATE channel.properties.attachSerial == "updated-serial"
```

### Assertions
```pseudo
ASSERT channel.properties.attachSerial == "updated-serial"
```

---

## RTL15b - channelSerial updated from ATTACHED message

| Spec | Requirement |
|------|-------------|
| RTL15b | `channelSerial` is updated whenever a ProtocolMessage with MESSAGE, PRESENCE, ANNOTATION, OBJECT, or ATTACHED action is received, set to the `channelSerial` of that message, if and only if that field is populated |

Tests that `channelSerial` is set from the ATTACHED response's `channelSerial` field.

### Setup
```pseudo
channel_name = "test-RTL15b-attached-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel,
        channelSerial: "serial-001"
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
# Before attach, channelSerial should be unset
ASSERT channel.properties.channelSerial IS null

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT channel.properties.channelSerial == "serial-001"
```

---

## RTL15b - channelSerial updated from MESSAGE and PRESENCE actions

**Spec requirement:** `channelSerial` is updated whenever a ProtocolMessage with MESSAGE, PRESENCE, ANNOTATION, OBJECT, or ATTACHED action is received.

Tests that receiving MESSAGE and PRESENCE protocol messages with a `channelSerial` field updates the channel's `channelSerial` property.

### Setup
```pseudo
channel_name = "test-RTL15b-messages-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel,
        channelSerial: "serial-001"
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
ASSERT channel.properties.channelSerial == "serial-001"

# Server sends MESSAGE with channelSerial
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  channelSerial: "serial-002",
  messages: [
    Message(name: "event", data: "data")
  ]
))
AWAIT_STATE channel.properties.channelSerial == "serial-002"

# Server sends PRESENCE with channelSerial
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: PRESENCE,
  channel: channel_name,
  channelSerial: "serial-003"
))
AWAIT_STATE channel.properties.channelSerial == "serial-003"
```

### Assertions
```pseudo
ASSERT channel.properties.channelSerial == "serial-003"
```

---

## RTL15b - channelSerial not updated when field is not populated

**Spec requirement:** `channelSerial` is set to the channelSerial of the ProtocolMessage, if and only if that field is populated.

Tests that receiving a protocol message without a `channelSerial` field does not clear or change the channel's existing `channelSerial`.

### Setup
```pseudo
channel_name = "test-RTL15b-noupdate-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel,
        channelSerial: "serial-001"
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
ASSERT channel.properties.channelSerial == "serial-001"

# Server sends MESSAGE without channelSerial
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "event", data: "data")
  ]
))
```

### Assertions
```pseudo
# channelSerial should remain unchanged
ASSERT channel.properties.channelSerial == "serial-001"
```

---

## RTL15b - channelSerial not updated from irrelevant actions

**Spec requirement:** `channelSerial` is updated only for MESSAGE, PRESENCE, ANNOTATION, OBJECT, or ATTACHED actions.

Tests that receiving a protocol message with a different action (e.g. ERROR, DETACHED) does not update `channelSerial`, even if the message happens to contain a `channelSerial` field.

### Setup
```pseudo
channel_name = "test-RTL15b-irrelevant-${random_id()}"
attach_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel,
        channelSerial: "serial-001"
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
ASSERT channel.properties.channelSerial == "serial-001"

# Server sends DETACHED with a channelSerial field
# (RTL13a will trigger reattach, but the DETACHED itself should not update channelSerial)
# Record channelSerial before the DETACHED
serial_before = channel.properties.channelSerial

mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: DETACHED,
  channel: channel_name,
  channelSerial: "serial-should-not-apply",
  error: ErrorInfo(code: 90198, statusCode: 500, message: "Detached")
))

# Wait for the reattach to complete (RTL13a)
AWAIT_STATE channel.state == ChannelState.attached
```

### Assertions
```pseudo
# channelSerial should be from the new ATTACHED, not from DETACHED
# The DETACHED action should not have updated channelSerial
# (RTL15b1 clears it on DETACHED/SUSPENDED/FAILED, then ATTACHED sets it fresh)
ASSERT attach_count == 2
ASSERT channel.properties.channelSerial == "serial-001"
```

---

## RTL15b1 - channelSerial cleared on DETACHED state

| Spec | Requirement |
|------|-------------|
| RTL15b1 | If the channel enters the DETACHED, SUSPENDED, or FAILED state, it must clear its channelSerial |

Tests that `channelSerial` is cleared when the channel transitions to DETACHED.

### Setup
```pseudo
channel_name = "test-RTL15b1-detached-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel,
        channelSerial: "serial-001"
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
ASSERT channel.properties.channelSerial == "serial-001"

AWAIT channel.detach()
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.detached
ASSERT channel.properties.channelSerial IS null
```

---

## RTL15b1 - channelSerial cleared on SUSPENDED state

**Spec requirement:** If the channel enters the SUSPENDED state, it must clear its `channelSerial`.

Tests that `channelSerial` is cleared when the channel transitions to SUSPENDED (e.g. due to attach timeout).

### Setup
```pseudo
channel_name = "test-RTL15b1-suspended-${random_id()}"
attach_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      IF attach_count == 1:
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: msg.channel,
          channelSerial: "serial-001"
        ))
      # Don't respond to second attach (causes timeout -> SUSPENDED)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  realtimeRequestTimeout: 100
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()
ASSERT channel.properties.channelSerial == "serial-001"

# Trigger server-initiated DETACHED -> reattach attempt that will timeout
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: DETACHED,
  channel: channel_name,
  error: ErrorInfo(code: 90198, statusCode: 500, message: "Detached")
))
AWAIT_STATE channel.state == ChannelState.attaching

# Let attach timeout -> SUSPENDED
ADVANCE_TIME(150)
AWAIT_STATE channel.state == ChannelState.suspended
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.suspended
ASSERT channel.properties.channelSerial IS null
```

---

## RTL15b1 - channelSerial cleared on FAILED state

**Spec requirement:** If the channel enters the FAILED state, it must clear its `channelSerial`.

Tests that `channelSerial` is cleared when the channel transitions to FAILED (e.g. due to channel ERROR).

### Setup
```pseudo
channel_name = "test-RTL15b1-failed-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel,
        channelSerial: "serial-001"
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
ASSERT channel.properties.channelSerial == "serial-001"

# Server sends channel ERROR -> FAILED
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ERROR,
  channel: channel_name,
  error: ErrorInfo(code: 40160, statusCode: 401, message: "Not permitted")
))
AWAIT_STATE channel.state == ChannelState.failed
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.failed
ASSERT channel.properties.channelSerial IS null
```
