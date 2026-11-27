# RealtimeChannel PatchMessage Tests

Spec points: `RTL32`, `RTL32b`, `RTL32b1`, `RTL32d`, `RTL32f`, `MPD3`, `MPD4`, `MPD4a`, `TM2v`, `TM9`

## Test Type
Unit test with mocked WebSocket

## Mock WebSocket Infrastructure

See `uts/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Related Tests

`patchMessage()` shares the behaviour of the other operations that `uts/realtime/unit/channels/channel_update_delete_message.md` covers (RTL32b2, RTL32c, RTL32e). The value encoding rules of MPD3 are covered in detail by `uts/rest/unit/channel/patch_message.md`; the tests below check that the realtime path applies them. The rules of `Message.applyPatch` are covered by `uts/rest/unit/types/message_apply_patch.md`.

---

## RTL32b, RTL32b1, RTL32d — patchMessage sends MESSAGE ProtocolMessage with action MESSAGE_PATCH

**Test ID**: `realtime/unit/RTL32b1/patch-message-action-0`

| Spec | Requirement |
|------|-------------|
| RTL32b | Send a `MESSAGE` `ProtocolMessage` containing a single `Message` populated with the fields of the user-supplied `Message` |
| RTL32b1 | `action` set to `MESSAGE_PATCH` for `patchMessage()` |
| RTL32d | Returns an `UpdateDeleteResult` containing the version serial from the `ACK` |

Tests that `patchMessage()` sends a MESSAGE ProtocolMessage with the `MESSAGE_PATCH` action and the `patches` field, and returns the version serial from the ACK. The channel is not attached first: like a publish, a patch does not require the channel to be attached, and the mock does not respond to `ATTACH`.

### Setup
```pseudo
channel_name = "test-RTL32-patch-${random_id()}"
captured_messages = []

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    captured_messages.append(msg)
    IF msg.action == MESSAGE:
      mock_ws.active_connection.send_to_client(ACK(
        msgSerial: msg.msgSerial,
        count: 1,
        res: { "serials": ["version-serial-1"] }
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false, useBinaryProtocol: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED

result = AWAIT channel.patchMessage(
  Message(
    serial: "msg-serial-1",
    patches: MessagePatches(
      data: [MessagePatchDataOperation(op: "append", path: "/text", data: "lo")],
      extras: { "headers": [MessagePatchHeaderOperation(op: "set", key: "status", value: "complete")] }
    )
  )
)
```

### Assertions
```pseudo
message_pm = null
FOR pm IN captured_messages:
  IF pm.action == MESSAGE:
    message_pm = pm
ASSERT message_pm IS NOT null

ASSERT message_pm.channel == channel_name
ASSERT message_pm.messages.length == 1

msg = message_pm.messages[0].toJson()
ASSERT msg["action"] == 6  # MESSAGE_PATCH numeric value
ASSERT msg["serial"] == "msg-serial-1"
ASSERT msg["patches"]["data"] == [{ "op": "append", "path": "/text", "data": "lo" }]
ASSERT msg["patches"]["extras"]["headers"] == [{ "op": "set", "key": "status", "value": "complete" }]

ASSERT result IS UpdateDeleteResult
ASSERT result.versionSerial == "version-serial-1"

# The patch was sent without attaching the channel
ASSERT NOT ANY pm IN captured_messages WHERE pm.action == ATTACH
ASSERT channel.state == ChannelState.INITIALIZED
CLOSE_CLIENT(client)
```

---

## RTL32f — patch operation values encoded per MPD3

**Test ID**: `realtime/unit/RTL32f/patch-values-encoded-0`

| Spec | Requirement |
|------|-------------|
| RTL32f | The `data` of each operation in `patches` must be encoded per MPD3 |
| MPD3b | A binary value is encoded as Base64, with `encoding` `base64`, when using JSON |
| MPD3c | Any other value, including a number or boolean, is stringified as JSON with `encoding` `json` |

Tests that the realtime path encodes each operation's value as the REST path does.

### Setup
```pseudo
channel_name = "test-RTL32f-${random_id()}"
captured_messages = []

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    captured_messages.append(msg)
    IF msg.action == MESSAGE:
      mock_ws.active_connection.send_to_client(ACK(
        msgSerial: msg.msgSerial,
        count: 1,
        res: { "serials": ["version-serial-1"] }
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false, useBinaryProtocol: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED

AWAIT channel.patchMessage(
  Message(
    serial: "s1",
    patches: MessagePatches(data: [
      MessagePatchDataOperation(op: "set", path: "/obj", data: { "b": 1 }),
      MessagePatchDataOperation(op: "set", path: "/bin", data: bytes([0x01, 0x02])),
      MessagePatchDataOperation(op: "set", path: "/done", data: true)
    ])
  )
)
```

### Assertions
```pseudo
message_pm = null
FOR pm IN captured_messages:
  IF pm.action == MESSAGE:
    message_pm = pm

ops = message_pm.messages[0].toJson()["patches"]["data"]
ASSERT parse_json(ops[0]["data"]) == { "b": 1 }
ASSERT ops[0]["encoding"] == "json"
ASSERT ops[1]["data"] == "AQI="
ASSERT ops[1]["encoding"] == "base64"
ASSERT ops[2]["data"] == "true"
ASSERT ops[2]["encoding"] == "json"
CLOSE_CLIENT(client)
```

---

## MPD4, TM2v — received MESSAGE_PATCH is decoded and delivered to subscribers

**Test ID**: `realtime/unit/MPD4/patch-received-decoded-0`

| Spec | Requirement |
|------|-------------|
| TM5 | `MESSAGE_PATCH` is action 6 |
| TM2v | `patches` holds the changes a `MESSAGE_PATCH` makes |
| MPD4 | The `data` of each operation is decoded by inverting its `encoding` per RSL6a |
| MPD4a | A leading `json` transform is not inverted: the `data` stays as JSON text with `encoding` `json` |

Tests that a `MESSAGE_PATCH` received over realtime is delivered to subscribers with its operations decoded, keeping JSON values as text.

### Setup
```pseudo
channel_name = "test-MPD4-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(channel: channel_name))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false, useBinaryProtocol: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
received = []
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.subscribe((msg) => received.append(msg))

mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "conn:0",
  timestamp: 1700000002000,
  messages: [{
    "action": 6,
    "serial": "msg-serial-1",
    "version": { "serial": "version-serial-2", "timestamp": 1700000002000 },
    "patches": {
      "data": [
        { "op": "set", "path": "/a", "data": "{\"b\":1}", "encoding": "json" },
        { "op": "set", "path": "/c", "data": "AQI=", "encoding": "base64" },
        { "op": "append", "path": "/d", "data": "text" }
      ],
      "extras": { "headers": [{ "op": "set", "key": "status", "value": "complete" }] }
    }
  }]
))
poll_until(received.length == 1)
```

### Assertions
```pseudo
msg = received[0]
ASSERT msg.action == MessageAction.MESSAGE_PATCH
ASSERT msg.serial == "msg-serial-1"
ASSERT msg.version.serial == "version-serial-2"

ops = msg.patches.data
ASSERT ops.length == 3

# MPD4a — JSON value stays as JSON text
ASSERT ops[0].op == "set"
ASSERT ops[0].path == "/a"
ASSERT ops[0].data == "{\"b\":1}"
ASSERT ops[0].encoding == "json"

# MPD4 — Base64 is decoded to binary, leaving no encoding
ASSERT ops[1].data == bytes([0x01, 0x02])
ASSERT ops[1].encoding IS null OR ops[1].encoding == ""

ASSERT ops[2].data == "text"
ASSERT ops[2].encoding IS null OR ops[2].encoding == ""

ASSERT msg.patches.extras.headers[0].op == "set"
ASSERT msg.patches.extras.headers[0].key == "status"
ASSERT msg.patches.extras.headers[0].value == "complete"
CLOSE_CLIENT(client)
```

---

## TM9 — subscriber keeps its message up to date with Message.applyPatch

**Test ID**: `realtime/unit/TM9/subscriber-applies-patch-0`

| Spec | Requirement |
|------|-------------|
| TM9 | `Message.applyPatch` returns a new `Message` that represents the message with the patch applied |
| TM9d1 | The result's `action` is `MESSAGE_UPDATE` |
| TM9d4 | The result's `version` is the patch's `version` |

Tests the end-to-end use: a subscriber receives a `MESSAGE_CREATE` with JSON data, then two `MESSAGE_PATCH` messages, and applies each to its message, keeping the result in `patched_message`.

### Setup
```pseudo
channel_name = "test-TM9-subscriber-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(channel: channel_name))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false, useBinaryProtocol: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)

patched_message = null
patches_applied = 0
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.subscribe((msg) => {
  IF msg.action == MessageAction.MESSAGE_CREATE:
    patched_message = msg
  ELSE IF msg.action == MessageAction.MESSAGE_PATCH:
    patched_message = Message.applyPatch(patched_message, msg)
    patches_applied++
})

FUNCTION send_message(msg_serial, wire_message):
  mock_ws.active_connection.send_to_client(ProtocolMessage(
    action: MESSAGE,
    channel: channel_name,
    id: "conn:" + msg_serial,
    timestamp: 1700000000000,
    messages: [wire_message]
  ))

send_message("0", {
  "action": 0,
  "serial": "msg-serial-1",
  "clientId": "author",
  "name": "reply",
  "data": "{\"text\":\"Hel\",\"toolCalls\":[]}",
  "encoding": "json"
})
send_message("1", {
  "action": 6,
  "serial": "msg-serial-1",
  "clientId": "patcher",
  "version": { "serial": "version-serial-2", "timestamp": 1700000001000 },
  "patches": { "data": [{ "op": "append", "path": "/text", "data": "lo" }] }
})
send_message("2", {
  "action": 6,
  "serial": "msg-serial-1",
  "version": { "serial": "version-serial-3", "timestamp": 1700000002000 },
  "patches": {
    "data": [{ "op": "set", "path": "/toolCalls/-", "data": "{\"name\":\"search\"}", "encoding": "json" }],
    "extras": { "headers": [{ "op": "set", "key": "status", "value": "complete" }] }
  }
})
poll_until(patches_applied == 2)
```

### Assertions
```pseudo
ASSERT patched_message.action == MessageAction.MESSAGE_UPDATE
ASSERT patched_message.serial == "msg-serial-1"
ASSERT patched_message.version.serial == "version-serial-3"
ASSERT patched_message.data == { "text": "Hello", "toolCalls": [{ "name": "search" }] }
ASSERT patched_message.extras["headers"] == { "status": "complete" }

# Kept from the MESSAGE_CREATE, not taken from the patches
ASSERT patched_message.clientId == "author"
ASSERT patched_message.name == "reply"
CLOSE_CLIENT(client)
```
