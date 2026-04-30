# Message Field Population from ProtocolMessage

Spec points: `TM2a`, `TM2c`, `TM2f`

## Test Type
Unit test with mocked WebSocket

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## Purpose

When a realtime client receives a ProtocolMessage containing messages, certain
fields on individual messages may be absent. The spec requires the SDK to populate
these from the encapsulating ProtocolMessage before delivering to subscribers:

| Spec | Field | Fallback |
|------|-------|----------|
| TM2a | `id` | `protocolMsgId:index` (0-based index in messages array) |
| TM2c | `connectionId` | ProtocolMessage `connectionId` |
| TM2f | `timestamp` | ProtocolMessage `timestamp` |

This is critical for correct operation of features that depend on message IDs
(e.g., vcdiff delta decoding RTL20 uses `id` for continuity checks) and for
providing complete message metadata to subscribers.

These tests verify that the population happens before messages are delivered to
subscribers via `channel.subscribe()`.

---

## TM2a - Message id populated from ProtocolMessage id and index

**Spec requirement:** For messages received over Realtime, if the message does not
contain an `id`, it should be set to `protocolMsgId:index`, where `protocolMsgId`
is the id of the `ProtocolMessage` encapsulating it, and `index` is the index of
the message inside the `messages` array of the `ProtocolMessage`.

Tests that messages without an `id` field receive a computed ID in the format
`protocolMessageId:arrayIndex` before being delivered to subscribers.

### Setup
```pseudo
channel_name = "test-TM2a-id-${random_id()}"

received_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
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
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Send a ProtocolMessage with 3 messages that have no id field.
# The ProtocolMessage itself has id "connId:serial".
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "abc123:5",
  connectionId: "abc123",
  timestamp: 1700000000000,
  messages: [
    { name: "first", data: "a" },
    { name: "second", data: "b" },
    { name: "third", data: "c" }
  ]
))

AWAIT length(received_messages) == 3
```

### Assertions
```pseudo
# Each message id is computed as protocolMessageId:index
ASSERT received_messages[0].id == "abc123:5:0"
ASSERT received_messages[1].id == "abc123:5:1"
ASSERT received_messages[2].id == "abc123:5:2"
CLOSE_CLIENT(client)
```

---

## TM2a - Message with existing id is not overwritten

**Spec requirement:** The id should only be set if the message does not already
contain one.

Tests that a message that already has an `id` field retains its original value.

### Setup
```pseudo
channel_name = "test-TM2a-existing-${random_id()}"

received_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
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
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Message already has its own id — should not be overwritten
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "proto-id:0",
  messages: [
    { id: "my-custom-id", name: "msg", data: "hello" }
  ]
))

AWAIT length(received_messages) == 1
```

### Assertions
```pseudo
ASSERT received_messages[0].id == "my-custom-id"
CLOSE_CLIENT(client)
```

---

## TM2a - No id when ProtocolMessage has no id

**Spec requirement:** The id derivation only applies when the ProtocolMessage has
an `id` field. If the ProtocolMessage has no `id`, messages without their own `id`
should remain without one.

Tests that messages are not assigned a computed id when the ProtocolMessage itself
lacks an `id` field.

### Setup
```pseudo
channel_name = "test-TM2a-no-proto-id-${random_id()}"

received_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
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
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# ProtocolMessage has no id field — messages should not get computed ids
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  connectionId: "abc123",
  messages: [
    { name: "msg", data: "hello" }
  ]
))

AWAIT length(received_messages) == 1
```

### Assertions
```pseudo
ASSERT received_messages[0].id IS null
CLOSE_CLIENT(client)
```

---

## TM2c - Message connectionId populated from ProtocolMessage

**Spec requirement:** If a message received from Ably does not contain a
`connectionId`, it should be set to the `connectionId` of the encapsulating
`ProtocolMessage`.

Tests that messages without a `connectionId` field inherit the value from the
ProtocolMessage before being delivered to subscribers.

### Setup
```pseudo
channel_name = "test-TM2c-connId-${random_id()}"

received_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
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
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Message has no connectionId — should inherit from ProtocolMessage
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg:0",
  connectionId: "server-conn-xyz",
  messages: [
    { name: "msg", data: "hello" }
  ]
))

AWAIT length(received_messages) == 1
```

### Assertions
```pseudo
ASSERT received_messages[0].connectionId == "server-conn-xyz"
CLOSE_CLIENT(client)
```

---

## TM2c - Message with existing connectionId is not overwritten

**Spec requirement:** The connectionId should only be set if the message does not
already contain one.

Tests that a message that already has a `connectionId` retains its original value.

### Setup
```pseudo
channel_name = "test-TM2c-existing-${random_id()}"

received_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
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
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Message already has its own connectionId — should not be overwritten
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg:0",
  connectionId: "proto-conn",
  messages: [
    { connectionId: "msg-conn", name: "msg", data: "hello" }
  ]
))

AWAIT length(received_messages) == 1
```

### Assertions
```pseudo
ASSERT received_messages[0].connectionId == "msg-conn"
CLOSE_CLIENT(client)
```

---

## TM2f - Message timestamp populated from ProtocolMessage

**Spec requirement:** If a message received from Ably over a realtime transport does
not contain a `timestamp`, the SDK must set it to the `timestamp` of the
encapsulating `ProtocolMessage`.

Tests that messages without a `timestamp` field inherit the value from the
ProtocolMessage before being delivered to subscribers.

### Setup
```pseudo
channel_name = "test-TM2f-timestamp-${random_id()}"

received_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
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
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Message has no timestamp — should inherit from ProtocolMessage
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg:0",
  timestamp: 1700000000000,
  messages: [
    { name: "msg", data: "hello" }
  ]
))

AWAIT length(received_messages) == 1
```

### Assertions
```pseudo
ASSERT received_messages[0].timestamp == 1700000000000
CLOSE_CLIENT(client)
```

---

## TM2f - Message with existing timestamp is not overwritten

**Spec requirement:** The timestamp should only be set if the message does not
already contain one.

Tests that a message that already has a `timestamp` retains its original value.

### Setup
```pseudo
channel_name = "test-TM2f-existing-${random_id()}"

received_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
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
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Message already has its own timestamp — should not be overwritten
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg:0",
  timestamp: 1700000000000,
  messages: [
    { timestamp: 1600000000000, name: "msg", data: "hello" }
  ]
))

AWAIT length(received_messages) == 1
```

### Assertions
```pseudo
ASSERT received_messages[0].timestamp == 1600000000000
CLOSE_CLIENT(client)
```

---

## TM2a, TM2c, TM2f - All fields populated together

**Spec requirement:** All three fields (id, connectionId, timestamp) should be
populated from the ProtocolMessage when absent from the message.

Tests that all three fields are populated in a single ProtocolMessage containing
multiple messages, with correct per-message index for the id field.

### Setup
```pseudo
channel_name = "test-TM2-all-fields-${random_id()}"

received_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
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
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# ProtocolMessage with all parent fields set, messages with none
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "connId:7",
  connectionId: "connId",
  timestamp: 1700000000000,
  messages: [
    { name: "first", data: "a" },
    { name: "second", data: "b" }
  ]
))

AWAIT length(received_messages) == 2
```

### Assertions
```pseudo
# First message
ASSERT received_messages[0].id == "connId:7:0"
ASSERT received_messages[0].connectionId == "connId"
ASSERT received_messages[0].timestamp == 1700000000000
ASSERT received_messages[0].name == "first"
ASSERT received_messages[0].data == "a"

# Second message — same connectionId and timestamp, different id index
ASSERT received_messages[1].id == "connId:7:1"
ASSERT received_messages[1].connectionId == "connId"
ASSERT received_messages[1].timestamp == 1700000000000
ASSERT received_messages[1].name == "second"
ASSERT received_messages[1].data == "b"
CLOSE_CLIENT(client)
```
