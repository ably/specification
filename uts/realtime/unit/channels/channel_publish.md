# RealtimeChannel Publish Tests

Spec points: `RTL6`, `RTL6a`, `RTL6c`, `RTL6c1`, `RTL6c2`, `RTL6c4`, `RTL6c5`, `RTL6i`, `RTL6i1`, `RTL6i2`, `RTL6i3`, `RTL6j`

## Test Type
Unit test with mocked WebSocket

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTL6i1 - Publish single message by name and data

**Spec requirement:** When `name` and `data` (or a `Message`) is provided, a single `ProtocolMessage` containing one `Message` is published to Ably.

Tests that publishing with name and data sends a single MESSAGE ProtocolMessage with one message entry.

### Setup
```pseudo
channel_name = "test-RTL6i1-${random_id()}"
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == MESSAGE:
      captured_messages.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

channel.publish(name: "greeting", data: "hello")
```

### Assertions
```pseudo
ASSERT length(captured_messages) == 1
ASSERT captured_messages[0].action == MESSAGE
ASSERT captured_messages[0].channel == channel_name
ASSERT length(captured_messages[0].messages) == 1
ASSERT captured_messages[0].messages[0].name == "greeting"
ASSERT captured_messages[0].messages[0].data == "hello"
```

---

## RTL6i2 - Publish array of Message objects

**Spec requirement:** When an array of `Message` objects is provided, a single `ProtocolMessage` is used to publish all `Message` objects in the array.

Tests that publishing an array of messages sends them in a single ProtocolMessage.

### Setup
```pseudo
channel_name = "test-RTL6i2-${random_id()}"
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == MESSAGE:
      captured_messages.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

channel.publish(messages: [
  Message(name: "event1", data: "data1"),
  Message(name: "event2", data: "data2"),
  Message(name: "event3", data: "data3")
])
```

### Assertions
```pseudo
ASSERT length(captured_messages) == 1  # Single ProtocolMessage
ASSERT length(captured_messages[0].messages) == 3
ASSERT captured_messages[0].messages[0].name == "event1"
ASSERT captured_messages[0].messages[1].name == "event2"
ASSERT captured_messages[0].messages[2].name == "event3"
```

---

## RTL6i3 - Null fields omitted from JSON wire encoding

**Spec requirement:** Allows `name` and or `data` to be `null`. If any of the values are `null`, then key is not sent to Ably i.e. a payload with a `null` value for `data` would be sent as follows `{ "name": "click" }`.

Tests that when using the JSON protocol, null `name` or `data` fields are omitted from the encoded JSON representation on the wire (not sent as `"name": null`).

### Setup
```pseudo
channel_name = "test-RTL6i3-json-${random_id()}"
captured_frames = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
  },
  onTextDataFrame: (text) => {
    decoded = JSON_DECODE(text)
    IF decoded["action"] == MESSAGE_ACTION_INT:
      captured_frames.append(decoded)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  useBinaryProtocol: false
))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Publish with name only (null data)
channel.publish(name: "click", data: null)

# Publish with data only (null name)
channel.publish(name: null, data: "payload")

# Publish with both null
channel.publish(name: null, data: null)
```

### Assertions
```pseudo
ASSERT length(captured_frames) == 3

# First message: name present, data key absent
msg0 = captured_frames[0]["messages"][0]
ASSERT msg0["name"] == "click"
ASSERT "data" NOT IN msg0

# Second message: data present, name key absent
msg1 = captured_frames[1]["messages"][0]
ASSERT "name" NOT IN msg1
ASSERT msg1["data"] == "payload"

# Third message: both keys absent
msg2 = captured_frames[2]["messages"][0]
ASSERT "name" NOT IN msg2
ASSERT "data" NOT IN msg2
```

---

## RTL6i3 - Null fields omitted from msgpack wire encoding

**Spec requirement:** Allows `name` and or `data` to be `null`. If any of the values are `null`, then key is not sent to Ably.

Tests that when using the msgpack protocol, null `name` or `data` fields are omitted from the encoded msgpack representation on the wire.

### Setup
```pseudo
channel_name = "test-RTL6i3-msgpack-${random_id()}"
captured_frames = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
  },
  onBinaryDataFrame: (bytes) => {
    decoded = MSGPACK_DECODE(bytes)
    IF decoded["action"] == MESSAGE_ACTION_INT:
      captured_frames.append(decoded)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  useBinaryProtocol: true
))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Publish with name only (null data)
channel.publish(name: "click", data: null)

# Publish with data only (null name)
channel.publish(name: null, data: "payload")

# Publish with both null
channel.publish(name: null, data: null)
```

### Assertions
```pseudo
ASSERT length(captured_frames) == 3

# First message: name present, data key absent
msg0 = captured_frames[0]["messages"][0]
ASSERT msg0["name"] == "click"
ASSERT "data" NOT IN msg0

# Second message: data present, name key absent
msg1 = captured_frames[1]["messages"][0]
ASSERT "name" NOT IN msg1
ASSERT msg1["data"] == "payload"

# Third message: both keys absent
msg2 = captured_frames[2]["messages"][0]
ASSERT "name" NOT IN msg2
ASSERT "data" NOT IN msg2
```

---

## RTL6c1 - Publish immediately when CONNECTED and channel ATTACHED

| Spec | Requirement |
|------|-------------|
| RTL6c1 | If the connection is `CONNECTED` and the channel is neither `SUSPENDED` nor `FAILED` then the messages are published immediately |

Tests that messages are sent immediately to the server when the connection is CONNECTED and the channel is ATTACHED.

### Setup
```pseudo
channel_name = "test-RTL6c1-${random_id()}"
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == MESSAGE:
      captured_messages.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

ASSERT client.connection.state == ConnectionState.connected
ASSERT channel.state == ChannelState.attached

channel.publish(name: "test", data: "immediate")
```

### Assertions
```pseudo
# Message should have been sent immediately (synchronously captured by mock)
ASSERT length(captured_messages) == 1
ASSERT captured_messages[0].messages[0].name == "test"
ASSERT captured_messages[0].messages[0].data == "immediate"
```

---

## RTL6c1 - Publish immediately when CONNECTED and channel ATTACHING

**Spec requirement:** If the connection is `CONNECTED` and the channel is neither `SUSPENDED` nor `FAILED` then the messages are published immediately.

Tests that messages are sent immediately even when the channel is in the ATTACHING state (which is neither SUSPENDED nor FAILED).

### Setup
```pseudo
channel_name = "test-RTL6c1-attaching-${random_id()}"
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Don't respond — leave channel in ATTACHING
    ELSE IF msg.action == MESSAGE:
      captured_messages.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Start attach but don't complete it — channel stays ATTACHING
attach_future = channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching

channel.publish(name: "while-attaching", data: "data")
```

### Assertions
```pseudo
# Message should have been sent immediately (ATTACHING is neither SUSPENDED nor FAILED)
ASSERT length(captured_messages) == 1
ASSERT captured_messages[0].messages[0].name == "while-attaching"
```

---

## RTL6c1 - Publish immediately when CONNECTED and channel INITIALIZED

**Spec requirement:** If the connection is `CONNECTED` and the channel is neither `SUSPENDED` nor `FAILED` then the messages are published immediately.

Tests that messages are sent immediately when the channel is in the INITIALIZED state (which is neither SUSPENDED nor FAILED).

### Setup
```pseudo
channel_name = "test-RTL6c1-init-${random_id()}"
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == MESSAGE:
      captured_messages.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

ASSERT channel.state == ChannelState.initialized

channel.publish(name: "before-attach", data: "data")
```

### Assertions
```pseudo
# Message should have been sent immediately
ASSERT length(captured_messages) == 1
ASSERT captured_messages[0].messages[0].name == "before-attach"
```

---

## RTL6c2 - Publish queued when connection is CONNECTING

| Spec | Requirement |
|------|-------------|
| RTL6c2 | If the connection is `INITIALIZED`, `CONNECTING` or `DISCONNECTED`; and the channel is neither `SUSPENDED` nor `FAILED`; and `ClientOptions#queueMessages` is `true`; then the message will be placed in a connection-wide message queue |

Tests that messages published while the connection is CONNECTING are queued and sent once the connection becomes CONNECTED.

### Setup
```pseudo
channel_name = "test-RTL6c2-connecting-${random_id()}"
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    # Don't respond yet — leave connection in CONNECTING
  },
  onMessageFromClient: (msg) => {
    IF msg.action == MESSAGE:
      captured_messages.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connecting

# Publish while CONNECTING — should be queued
channel.publish(name: "queued", data: "waiting")

# Message should NOT have been sent yet
ASSERT length(captured_messages) == 0

# Complete the connection
pending_conn = AWAIT mock_ws.await_connection_attempt()
pending_conn.respond_with_success(CONNECTED_MESSAGE)
AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions
```pseudo
# Queued message should now have been sent
ASSERT length(captured_messages) == 1
ASSERT captured_messages[0].messages[0].name == "queued"
ASSERT captured_messages[0].messages[0].data == "waiting"
```

---

## RTL6c2 - Publish queued when connection is DISCONNECTED

**Spec requirement:** Messages are queued when connection is `DISCONNECTED` and `queueMessages` is true.

Tests that messages published while the connection is DISCONNECTED are queued and sent once the connection reconnects.

### Setup
```pseudo
channel_name = "test-RTL6c2-disconnected-${random_id()}"
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == MESSAGE:
      captured_messages.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Simulate disconnect
mock_ws.active_connection.simulate_disconnect()

# Record state changes to verify DISCONNECTED was reached
state_changes = []
client.connection.on((change) => {
  state_changes.append(change.current)
})

AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Publish while DISCONNECTED — should be queued
channel.publish(name: "during-disconnect", data: "queued")

# Message should NOT have been sent yet (no active connection)
message_count_before = length(captured_messages)
```

### Assertions
```pseudo
# After reconnection, the queued message should be sent
AWAIT_STATE client.connection.state == ConnectionState.connected

ASSERT length(captured_messages) > message_count_before
# Find the queued message in captured messages
queued = filter(captured_messages, (m) => m.messages[0].name == "during-disconnect")
ASSERT length(queued) == 1
```

---

## RTL6c2 - Publish queued when connection is INITIALIZED

**Spec requirement:** Messages are queued when connection is `INITIALIZED` and `queueMessages` is true.

Tests that messages published before `connect()` is called are queued and sent once the connection becomes CONNECTED.

### Setup
```pseudo
channel_name = "test-RTL6c2-init-${random_id()}"
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == MESSAGE:
      captured_messages.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
ASSERT client.connection.state == ConnectionState.initialized

# Publish before connecting — should be queued
channel.publish(name: "pre-connect", data: "early")

# Message should NOT have been sent
ASSERT length(captured_messages) == 0

# Now connect
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions
```pseudo
# Queued message should now have been sent
ASSERT length(captured_messages) == 1
ASSERT captured_messages[0].messages[0].name == "pre-connect"
```

---

## RTL6c4 - Publish fails when connection is SUSPENDED

**Spec requirement:** In any other case the operation should result in an error.

Tests that publishing fails immediately when the connection is SUSPENDED.

### Setup
```pseudo
channel_name = "test-RTL6c4-suspended-${random_id()}"

enable_fake_timers()

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_refused()
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  disconnectedRetryTimeout: 1000,
  connectionStateTtl: 5000
))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()

# Advance time until connection enters SUSPENDED
LOOP up to 15 times:
  ADVANCE_TIME(2000)
  IF client.connection.state == ConnectionState.suspended:
    BREAK

AWAIT_STATE client.connection.state == ConnectionState.suspended

# Publish should fail
channel.publish(name: "fail", data: "should-error") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
ASSERT error.code IS NOT null
```

---

## RTL6c4 - Publish fails when connection is CLOSED

**Spec requirement:** In any other case the operation should result in an error.

Tests that publishing fails when the connection is CLOSED.

### Setup
```pseudo
channel_name = "test-RTL6c4-closed-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE)
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT client.close()
ASSERT client.connection.state == ConnectionState.closed

channel.publish(name: "fail", data: "should-error") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
ASSERT error.code IS NOT null
```

---

## RTL6c4 - Publish fails when connection is FAILED

**Spec requirement:** In any other case the operation should result in an error.

Tests that publishing fails when the connection is FAILED.

### Setup
```pseudo
channel_name = "test-RTL6c4-failed-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_error(
      ProtocolMessage(
        action: ERROR,
        error: ErrorInfo(code: 80000, message: "Fatal error")
      ),
      thenClose: true
    )
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.failed

channel.publish(name: "fail", data: "should-error") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
ASSERT error.code IS NOT null
```

---

## RTL6c4 - Publish fails when channel is SUSPENDED

**Spec requirement:** If the channel is SUSPENDED, publish results in an error regardless of connection state.

Tests that publishing fails when the channel is in SUSPENDED state even though the connection is CONNECTED.

### Setup
```pseudo
channel_name = "test-RTL6c4-ch-suspended-${random_id()}"
captured_messages = []

enable_fake_timers()

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Don't respond on second attach — will timeout to SUSPENDED
    ELSE IF msg.action == MESSAGE:
      captured_messages.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  realtimeRequestTimeout: 100
))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Start attach — will timeout and channel enters SUSPENDED
attach_future = channel.attach()
ADVANCE_TIME(150)
AWAIT attach_future FAILS WITH attach_error

AWAIT_STATE channel.state == ChannelState.suspended

# Publish should fail because channel is SUSPENDED
channel.publish(name: "fail", data: "should-error") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
ASSERT length(captured_messages) == 0  # No MESSAGE sent to server
```

---

## RTL6c4 - Publish fails when channel is FAILED

**Spec requirement:** Publishing to a FAILED channel results in an error (RTL6c3/RTL6c4).

Tests that publishing fails when the channel is in FAILED state.

### Setup
```pseudo
channel_name = "test-RTL6c4-ch-failed-${random_id()}"
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ERROR,
        channel: channel_name,
        error: ErrorInfo(code: 40160, statusCode: 401, message: "Not permitted")
      ))
    ELSE IF msg.action == MESSAGE:
      captured_messages.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Attach fails → channel enters FAILED
AWAIT channel.attach() FAILS WITH attach_error
ASSERT channel.state == ChannelState.failed

# Publish should fail because channel is FAILED
channel.publish(name: "fail", data: "should-error") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
ASSERT length(captured_messages) == 0  # No MESSAGE sent to server
```

---

## RTL6c2 - Publish fails when queueMessages is false and connection not CONNECTED

**Spec requirement:** Messages are queued only when `queueMessages` is true. When false and connection is not CONNECTED, publish should fail.

Tests that publishing fails immediately when queueMessages is false and the connection is not CONNECTED.

### Setup
```pseudo
channel_name = "test-RTL6c2-noqueue-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    # Don't respond — leave connection in CONNECTING
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  queueMessages: false
))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connecting

channel.publish(name: "fail", data: "should-error") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
ASSERT error.code IS NOT null
```

---

## RTL6c5 - Publish does not trigger implicit attach

**Spec requirement:** A publish should not trigger an implicit attach (in contrast to earlier version of this spec).

Tests that publishing on an INITIALIZED channel does not cause the channel to begin attaching.

### Setup
```pseudo
channel_name = "test-RTL6c5-${random_id()}"
attach_message_count = 0
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_message_count++
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == MESSAGE:
      captured_messages.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

ASSERT channel.state == ChannelState.initialized

channel.publish(name: "no-attach", data: "test")
```

### Assertions
```pseudo
# Publish should have been sent (RTL6c1 — CONNECTED, channel not SUSPENDED/FAILED)
ASSERT length(captured_messages) == 1

# Channel should remain INITIALIZED — no implicit attach
ASSERT channel.state == ChannelState.initialized
ASSERT attach_message_count == 0
```

---

## RTL6c2 - Multiple queued messages sent in order after connection

**Spec requirement:** Messages queued while not connected are delivered once the connection becomes CONNECTED.

Tests that multiple messages queued before connection are all sent in the correct order once connected.

### Setup
```pseudo
channel_name = "test-RTL6c2-order-${random_id()}"
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    # Don't respond yet — leave in CONNECTING
  },
  onMessageFromClient: (msg) => {
    IF msg.action == MESSAGE:
      captured_messages.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connecting

# Queue multiple messages
channel.publish(name: "first", data: "1")
channel.publish(name: "second", data: "2")
channel.publish(name: "third", data: "3")

ASSERT length(captured_messages) == 0

# Complete the connection
pending_conn = AWAIT mock_ws.await_connection_attempt()
pending_conn.respond_with_success(CONNECTED_MESSAGE)
AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions
```pseudo
# All messages should have been sent in order
ASSERT length(captured_messages) == 3
ASSERT captured_messages[0].messages[0].name == "first"
ASSERT captured_messages[1].messages[0].name == "second"
ASSERT captured_messages[2].messages[0].name == "third"
```

---

## RTL6i1 - Publish Message object

**Spec requirement:** When a `Message` is provided, a single `ProtocolMessage` containing one `Message` is published to Ably.

Tests that publishing a Message object directly sends it correctly.

### Setup
```pseudo
channel_name = "test-RTL6i1-obj-${random_id()}"
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == MESSAGE:
      captured_messages.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

channel.publish(message: Message(name: "custom", data: {"key": "value"}))
```

### Assertions
```pseudo
ASSERT length(captured_messages) == 1
ASSERT length(captured_messages[0].messages) == 1
ASSERT captured_messages[0].messages[0].name == "custom"
ASSERT captured_messages[0].messages[0].data == {"key": "value"}
```

---

## RTL6j - Publish returns PublishResult with serials from ACK

| Spec | Requirement |
|------|-------------|
| RTL6j | On success, returns a `PublishResult` object containing the serials of the published messages. The serials are obtained from the `ACK` `ProtocolMessage` response (see TR4s). |
| PBR1 | Contains the result of a publish operation |
| PBR2a | `serials` array of `String?` — an array of message serials corresponding 1:1 to the messages that were published |
| TR4s | `res` Array of `PublishResult` objects — present in `ACK` `ProtocolMessages`, contains one `PublishResult` per acknowledged `ProtocolMessage` in order |
| TR4g | `count` integer — number of `ProtocolMessages` being acknowledged |
| RTN7b | Every `ProtocolMessage` that expects an ACK must contain a unique serially incrementing `msgSerial` integer value starting at zero |

Tests that `publish()` returns a `PublishResult` whose `serials` array contains the message serials from the ACK response.

### Setup
```pseudo
channel_name = "test-RTL6j-${random_id()}"
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == MESSAGE:
      captured_messages.append(msg)
      # Respond with ACK containing PublishResult with serials
      mock_ws.send_to_client(ProtocolMessage(
        action: ACK,
        msgSerial: msg.msgSerial,
        count: 1,
        res: [PublishResult(serials: ["abc123"])]
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

result = AWAIT channel.publish(name: "greeting", data: "hello")
```

### Assertions
```pseudo
# Publish should have been sent with msgSerial
ASSERT length(captured_messages) == 1
ASSERT captured_messages[0].msgSerial == 0

# Result should be a PublishResult with serials from the ACK
ASSERT result IS PublishResult
ASSERT length(result.serials) == 1
ASSERT result.serials[0] == "abc123"
```

---

## RTL6j - Publish returns PublishResult with multiple serials for batch publish

**Spec requirement:** When an array of messages is published, the `PublishResult` `serials` array contains one serial per message, corresponding 1:1 to the published messages (PBR2a). A serial may be null if the message was discarded due to a configured conflation rule.

Tests that a batch publish of multiple messages returns a `PublishResult` with a serial for each message.

### Setup
```pseudo
channel_name = "test-RTL6j-batch-${random_id()}"
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == MESSAGE:
      captured_messages.append(msg)
      # Respond with ACK containing serials for each message
      mock_ws.send_to_client(ProtocolMessage(
        action: ACK,
        msgSerial: msg.msgSerial,
        count: 1,
        res: [PublishResult(serials: ["serial-1", null, "serial-3"])]
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

result = AWAIT channel.publish(messages: [
  Message(name: "event1", data: "data1"),
  Message(name: "event2", data: "data2"),
  Message(name: "event3", data: "data3")
])
```

### Assertions
```pseudo
# Single ProtocolMessage with 3 messages
ASSERT length(captured_messages) == 1
ASSERT length(captured_messages[0].messages) == 3

# Result should contain serials 1:1 with published messages
ASSERT result IS PublishResult
ASSERT length(result.serials) == 3
ASSERT result.serials[0] == "serial-1"
ASSERT result.serials[1] == null  # Conflated message
ASSERT result.serials[2] == "serial-3"
```

---

## RTL6j - Sequential publishes get incrementing msgSerial

**Spec requirement:** Every ProtocolMessage that expects an ACK must contain a unique serially incrementing `msgSerial` integer value starting at zero (RTN7b).

Tests that successive publish calls assign incrementing `msgSerial` values to the outgoing ProtocolMessages, and that each publish resolves with the correct `PublishResult` from its corresponding ACK.

### Setup
```pseudo
channel_name = "test-RTL6j-serial-${random_id()}"
captured_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == MESSAGE:
      captured_messages.append(msg)
      # Respond with ACK, using msgSerial to generate distinct serials
      mock_ws.send_to_client(ProtocolMessage(
        action: ACK,
        msgSerial: msg.msgSerial,
        count: 1,
        res: [PublishResult(serials: ["serial-${msg.msgSerial}"])]
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

result1 = AWAIT channel.publish(name: "first", data: "1")
result2 = AWAIT channel.publish(name: "second", data: "2")
result3 = AWAIT channel.publish(name: "third", data: "3")
```

### Assertions
```pseudo
# Each outgoing MESSAGE should have incrementing msgSerial
ASSERT length(captured_messages) == 3
ASSERT captured_messages[0].msgSerial == 0
ASSERT captured_messages[1].msgSerial == 1
ASSERT captured_messages[2].msgSerial == 2

# Each publish should resolve with the correct PublishResult
ASSERT result1.serials[0] == "serial-0"
ASSERT result2.serials[0] == "serial-1"
ASSERT result3.serials[0] == "serial-2"
```

---

## RTL6j - Publish NACK results in error

| Spec | Requirement |
|------|-------------|
| RTN7a | All MESSAGE ProtocolMessages sent to Ably expect either an ACK or NACK to confirm success or failure |

Tests that when the server responds with a NACK instead of an ACK, the publish future completes with an error.

### Setup
```pseudo
channel_name = "test-RTL6j-nack-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == MESSAGE:
      # Respond with NACK
      mock_ws.send_to_client(ProtocolMessage(
        action: NACK,
        msgSerial: msg.msgSerial,
        count: 1,
        error: ErrorInfo(code: 40160, statusCode: 401, message: "Publish rejected")
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

AWAIT channel.publish(name: "rejected", data: "data") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
ASSERT error.code == 40160
ASSERT error.message == "Publish rejected"
```
