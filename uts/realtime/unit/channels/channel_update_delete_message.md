# RealtimeChannel UpdateMessage/DeleteMessage/AppendMessage Tests

Spec points: `RTL32`, `RTL32a`, `RTL32b`, `RTL32b1`, `RTL32b2`, `RTL32c`, `RTL32d`, `RTL32e`

## Test Type
Unit test with mocked WebSocket

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTL32b, RTL32b1 — updateMessage sends MESSAGE ProtocolMessage with action MESSAGE_UPDATE

| Spec | Requirement |
|------|-------------|
| RTL32b | Send a `MESSAGE` `ProtocolMessage` containing a single `Message` |
| RTL32b1 | `action` set to `MESSAGE_UPDATE` for `updateMessage()` |

Tests that `updateMessage()` sends a MESSAGE ProtocolMessage with the message action set to MESSAGE_UPDATE.

### Setup
```pseudo
channel_name = "test-RTL32-update-${random_id()}"
captured_messages = []

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    captured_messages.append(msg)
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH
      ))
    ELSE IF msg.action == MESSAGE:
      mock_ws.active_connection.send_to_client(ACK(
        msgSerial: msg.msgSerial,
        count: 1,
        res: { "serials": ["version-serial-1"] }
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

result = AWAIT channel.updateMessage(
  Message(serial: "msg-serial-1", name: "updated", data: "new-data"),
)
```

### Assertions
```pseudo
# Find the MESSAGE ProtocolMessage (not the ATTACH)
message_pm = null
FOR pm IN captured_messages:
  IF pm.action == MESSAGE:
    message_pm = pm
ASSERT message_pm IS NOT null

ASSERT message_pm.channel == channel_name
ASSERT message_pm.messages.length == 1

msg = message_pm.messages[0]
ASSERT msg.action == MessageAction.MESSAGE_UPDATE  # numeric: 1
ASSERT msg.serial == "msg-serial-1"
ASSERT msg.name == "updated"
ASSERT msg.data == "new-data"
```

---

## RTL32b, RTL32b1 — deleteMessage sends MESSAGE ProtocolMessage with action MESSAGE_DELETE

| Spec | Requirement |
|------|-------------|
| RTL32b | Send a `MESSAGE` `ProtocolMessage` containing a single `Message` |
| RTL32b1 | `action` set to `MESSAGE_DELETE` for `deleteMessage()` |

Tests that `deleteMessage()` sends MESSAGE_DELETE.

### Setup
```pseudo
channel_name = "test-RTL32-delete-${random_id()}"
captured_messages = []

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    captured_messages.append(msg)
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH
      ))
    ELSE IF msg.action == MESSAGE:
      mock_ws.active_connection.send_to_client(ACK(
        msgSerial: msg.msgSerial,
        count: 1,
        res: { "serials": ["version-serial-1"] }
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

result = AWAIT channel.deleteMessage(
  Message(serial: "msg-serial-1"),
)
```

### Assertions
```pseudo
message_pm = null
FOR pm IN captured_messages:
  IF pm.action == MESSAGE:
    message_pm = pm
ASSERT message_pm IS NOT null

msg = message_pm.messages[0]
ASSERT msg.action == MessageAction.MESSAGE_DELETE  # numeric: 2
ASSERT msg.serial == "msg-serial-1"
```

---

## RTL32b, RTL32b1 — appendMessage sends MESSAGE ProtocolMessage with action MESSAGE_APPEND

| Spec | Requirement |
|------|-------------|
| RTL32b | Send a `MESSAGE` `ProtocolMessage` containing a single `Message` |
| RTL32b1 | `action` set to `MESSAGE_APPEND` for `appendMessage()` |

Tests that `appendMessage()` sends MESSAGE_APPEND.

### Setup
```pseudo
channel_name = "test-RTL32-append-${random_id()}"
captured_messages = []

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    captured_messages.append(msg)
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH
      ))
    ELSE IF msg.action == MESSAGE:
      mock_ws.active_connection.send_to_client(ACK(
        msgSerial: msg.msgSerial,
        count: 1,
        res: { "serials": ["version-serial-1"] }
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

result = AWAIT channel.appendMessage(
  Message(serial: "msg-serial-1", data: "appended-data"),
  operation: MessageOperation(description: "appended content")
)
```

### Assertions
```pseudo
message_pm = null
FOR pm IN captured_messages:
  IF pm.action == MESSAGE:
    message_pm = pm
ASSERT message_pm IS NOT null

msg = message_pm.messages[0]
ASSERT msg.action == MessageAction.MESSAGE_APPEND  # numeric: 5
ASSERT msg.serial == "msg-serial-1"
ASSERT msg.data == "appended-data"
```

---

## RTL32b2 — version field set from MessageOperation

**Spec requirement:** RTL32b2 — `version` set to the `MessageOperation` object if provided.

Tests that the `version` field on the wire message is set to the MessageOperation when provided, and absent when not provided.

### Setup
```pseudo
channel_name = "test-RTL32b2-${random_id()}"
captured_messages = []

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    captured_messages.append(msg)
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH
      ))
    ELSE IF msg.action == MESSAGE:
      mock_ws.active_connection.send_to_client(ACK(
        msgSerial: msg.msgSerial,
        count: 1,
        res: { "serials": ["version-serial-1"] }
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

# With operation
AWAIT channel.updateMessage(
  Message(serial: "msg-serial-1", data: "v2"),
  operation: MessageOperation(
    description: "edited content",
    metadata: { "reason": "typo" }
  )
)

# Without operation
AWAIT channel.updateMessage(
  Message(serial: "msg-serial-2", data: "v2")
)
```

### Assertions
```pseudo
message_pms = []
FOR pm IN captured_messages:
  IF pm.action == MESSAGE:
    message_pms.append(pm)
ASSERT message_pms.length == 2

# With operation: version field present
msg_with_op = message_pms[0].messages[0]
ASSERT msg_with_op.version IS NOT null
ASSERT msg_with_op.version.description == "edited content"
ASSERT msg_with_op.version.metadata["reason"] == "typo"

# Without operation: version field absent
msg_without_op = message_pms[1].messages[0]
ASSERT msg_without_op.version IS null
```

---

## RTL32c — does not mutate user-supplied Message

**Spec requirement:** RTL32c — The SDK must not mutate the user-supplied `Message` object.

Tests that the original Message object is unchanged after calling updateMessage.

### Setup
```pseudo
channel_name = "test-RTL32c-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH
      ))
    ELSE IF msg.action == MESSAGE:
      mock_ws.active_connection.send_to_client(ACK(
        msgSerial: msg.msgSerial,
        count: 1,
        res: { "serials": ["version-serial-1"] }
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

original_message = Message(serial: "msg-serial-1", name: "original", data: "original-data")
AWAIT channel.updateMessage(original_message)
```

### Assertions
```pseudo
# Original message unchanged
ASSERT original_message.name == "original"
ASSERT original_message.data == "original-data"
ASSERT original_message.serial == "msg-serial-1"
ASSERT original_message.action IS null
```

---

## RTL32d — returns UpdateDeleteResult from ACK

**Spec requirement:** RTL32d — On success, returns an `UpdateDeleteResult` object containing the version serial of the published update, obtained from the first element of the `serials` array of the `res` field of the `ACK`.

Tests that the result is parsed from the ACK ProtocolMessage.

### Setup
```pseudo
channel_name = "test-RTL32d-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH
      ))
    ELSE IF msg.action == MESSAGE:
      mock_ws.active_connection.send_to_client(ACK(
        msgSerial: msg.msgSerial,
        count: 1,
        res: { "serials": ["01770000000000-000@abcdef:000"] }
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

result = AWAIT channel.updateMessage(
  Message(serial: "msg-serial-1", data: "updated")
)
```

### Assertions
```pseudo
ASSERT result IS UpdateDeleteResult
ASSERT result.versionSerial == "01770000000000-000@abcdef:000"
```

---

## RTL32d — NACK returns error

**Spec requirement:** RTL32d — Indicates an error if the operation was not successful.

Tests that a NACK results in an error.

### Setup
```pseudo
channel_name = "test-RTL32d-nack-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH
      ))
    ELSE IF msg.action == MESSAGE:
      mock_ws.active_connection.send_to_client(NACK(
        msgSerial: msg.msgSerial,
        count: 1,
        error: ErrorInfo(code: 40160, message: "Not permitted")
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

AWAIT channel.updateMessage(
  Message(serial: "msg-serial-1", data: "updated")
) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40160
```

---

## RTL32e — params sent in ProtocolMessage.params

**Spec requirement:** RTL32e — Any params provided in the third argument must be sent in the `TR4q` `ProtocolMessage.params` field.

Tests that optional params are forwarded in the ProtocolMessage.

### Setup
```pseudo
channel_name = "test-RTL32e-${random_id()}"
captured_messages = []

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    captured_messages.append(msg)
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH
      ))
    ELSE IF msg.action == MESSAGE:
      mock_ws.active_connection.send_to_client(ACK(
        msgSerial: msg.msgSerial,
        count: 1,
        res: { "serials": ["version-serial-1"] }
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

AWAIT channel.updateMessage(
  Message(serial: "msg-serial-1", data: "v2"),
  params: { "key1": "value1", "key2": "value2" }
)
```

### Assertions
```pseudo
message_pm = null
FOR pm IN captured_messages:
  IF pm.action == MESSAGE:
    message_pm = pm
ASSERT message_pm IS NOT null

ASSERT message_pm.params["key1"] == "value1"
ASSERT message_pm.params["key2"] == "value2"
```

---

## RTL32a — serial validation

**Spec requirement:** RTL32a — Takes a first argument of a `Message` object (which must contain a populated `serial` field).

Tests that calling updateMessage/deleteMessage/appendMessage with a missing serial throws an error. Follows the same validation as RSL15a.

### Setup
```pseudo
channel_name = "test-RTL32a-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps and Assertions
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

# Empty serial
AWAIT channel.updateMessage(
  Message(serial: "", data: "v2")
) FAILS WITH error
ASSERT error.code == 40003

# Null serial (if applicable in language)
AWAIT channel.deleteMessage(
  Message(data: "v2")
) FAILS WITH error
ASSERT error.code == 40003
```
