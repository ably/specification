# REST Channel PatchMessage Tests

Spec points: `RSL15`, `RSL15a`, `RSL15b`, `RSL15b1`, `RSL15c`, `RSL15e`, `RSL15g`, `MPD3`, `MPD3a`, `MPD3b`, `MPD3c`, `MPD3d`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

These tests use the mock HTTP infrastructure defined in `uts/rest/unit/helpers/mock_http.md`.

## Related Tests

`patchMessage()` shares the behaviour of `updateMessage()`, `deleteMessage()` and `appendMessage()` that `uts/rest/unit/channel/update_delete_message.md` covers (RSL15b7, RSL15c, RSL15e, RSL15f, serial URL-encoding). The tests below cover what is specific to `patchMessage()`: its action, and the encoding of the `patches` field.

---

## RSL15b, RSL15b1 — patchMessage sends PATCH with action MESSAGE_PATCH

**Test ID**: `rest/unit/RSL15b1/patch-sends-patch-action-0`

| Spec | Requirement |
|------|-------------|
| RSL15b | The SDK must send a PATCH to `/channels/{channelName}/messages/{serial}` with whatever fields were in the user-supplied `Message` |
| RSL15b1 | `action` set to `MESSAGE_PATCH` for `patchMessage()` |
| RSL15e | On success, returns an `UpdateDeleteResult` |

Tests that `patchMessage()` sends a PATCH request with the `MESSAGE_PATCH` action and the `patches` field, and returns the version serial.

### Setup
```pseudo
channel_name = "test-RSL15-patch-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, { "versionSerial": "vs1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
result = AWAIT channel.patchMessage(
  Message(
    serial: "msg-serial-1",
    patches: MessagePatches(
      data: [
        MessagePatchDataOperation(op: "append", path: "/content/0/text", data: " more text")
      ],
      extras: {
        "headers": [
          MessagePatchHeaderOperation(op: "set", key: "status", value: "complete"),
          MessagePatchHeaderOperation(op: "remove", key: "draft")
        ]
      }
    )
  )
)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "PATCH"
ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name) + "/messages/msg-serial-1"

body = parse_json(request.body)
ASSERT body["action"] == 6  # MESSAGE_PATCH numeric value
ASSERT body["serial"] == "msg-serial-1"
ASSERT body["patches"]["data"] == [
  { "op": "append", "path": "/content/0/text", "data": " more text" }
]
ASSERT body["patches"]["extras"]["headers"] == [
  { "op": "set", "key": "status", "value": "complete" },
  { "op": "remove", "key": "draft" }
]

ASSERT result IS UpdateDeleteResult
ASSERT result.versionSerial == "vs1"
```

---

## RSL15g, MPD3 — patch operation values encoded with the JSON protocol

**Test ID**: `rest/unit/RSL15g/patch-values-encoded-json-0`

| Spec | Requirement |
|------|-------------|
| RSL15g | The `data` of each operation in `patches` must be encoded per MPD3 |
| MPD3a | A string is sent unchanged |
| MPD3b | A binary value is encoded per RSL4d1 when using JSON: Base64, with `encoding` `base64` |
| MPD3c | Any other value, including a number, boolean or `null`, is stringified as JSON with `encoding` `json` |
| MPD3d | An operation without `data` is sent without `data` or `encoding` |

Tests that each operation's value is encoded for the JSON protocol, including JSON values that are not objects or arrays.

### Setup
```pseudo
channel_name = "test-RSL15g-json-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, { "versionSerial": "vs1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.patchMessage(
  Message(
    serial: "s1",
    patches: MessagePatches(data: [
      MessagePatchDataOperation(op: "append", path: "/text", data: "lo"),
      MessagePatchDataOperation(op: "set", path: "/bin", data: bytes([0x01, 0x02])),
      MessagePatchDataOperation(op: "set", path: "/obj", data: { "b": 1 }),
      MessagePatchDataOperation(op: "set", path: "/list/-", data: [1, 2]),
      MessagePatchDataOperation(op: "set", path: "/count", data: 42),
      MessagePatchDataOperation(op: "set", path: "/done", data: true),
      MessagePatchDataOperation(op: "set", path: "/cleared", data: null),
      MessagePatchDataOperation(op: "remove", path: "/old")
    ])
  )
)
```

### Assertions
```pseudo
ops = parse_json(captured_requests[0].body)["patches"]["data"]
ASSERT ops.length == 8

# MPD3a — string unchanged
ASSERT ops[0] == { "op": "append", "path": "/text", "data": "lo" }

# MPD3b — binary as Base64
ASSERT ops[1]["data"] == "AQI="
ASSERT ops[1]["encoding"] == "base64"

# MPD3c — every other JSON value as JSON text
ASSERT ops[2]["data"] IS String
ASSERT parse_json(ops[2]["data"]) == { "b": 1 }
ASSERT ops[2]["encoding"] == "json"
ASSERT parse_json(ops[3]["data"]) == [1, 2]
ASSERT ops[3]["encoding"] == "json"
ASSERT ops[4]["data"] == "42"
ASSERT ops[4]["encoding"] == "json"
ASSERT ops[5]["data"] == "true"
ASSERT ops[5]["encoding"] == "json"
ASSERT ops[6]["data"] == "null"
ASSERT ops[6]["encoding"] == "json"

# MPD3d — no data, no encoding
ASSERT ops[7] == { "op": "remove", "path": "/old" }
```

---

## RSL15g, MPD3 — patch operation values encoded with the MessagePack protocol

**Test ID**: `rest/unit/RSL15g/patch-values-encoded-msgpack-1`

| Spec | Requirement |
|------|-------------|
| RSL15g | The `data` of each operation in `patches` must be encoded per MPD3 |
| MPD3a | A string is sent unchanged, as a string |
| MPD3b | A binary value is encoded per RSL4c1 when using MessagePack: as MessagePack binary |
| MPD3c | Any other value is stringified as JSON, sent as a MessagePack string, with `encoding` `json` |

Tests that each operation's value is encoded for the MessagePack protocol.

### Setup
```pseudo
channel_name = "test-RSL15g-msgpack-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, { "versionSerial": "vs1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: true  # MessagePack
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.patchMessage(
  Message(
    serial: "s1",
    patches: MessagePatches(data: [
      MessagePatchDataOperation(op: "append", path: "/text", data: "lo"),
      MessagePatchDataOperation(op: "set", path: "/bin", data: bytes([0x01, 0x02])),
      MessagePatchDataOperation(op: "set", path: "/count", data: 42)
    ])
  )
)
```

### Assertions
```pseudo
body = msgpack_decode(captured_requests[0].body)
ASSERT body["action"] == 6
ops = body["patches"]["data"]

ASSERT ops[0]["data"] == "lo"
ASSERT "encoding" NOT IN ops[0] OR ops[0]["encoding"] IS null

# Binary transmitted directly, no Base64
ASSERT ops[1]["data"] == bytes([0x01, 0x02])
ASSERT "encoding" NOT IN ops[1] OR ops[1]["encoding"] IS null

# JSON value as a MessagePack string
ASSERT ops[2]["data"] IS String
ASSERT ops[2]["data"] == "42"
ASSERT ops[2]["encoding"] == "json"
```

---

## RSL15c — patchMessage does not mutate the user-supplied Message or its patches

**Test ID**: `rest/unit/RSL15c/patch-no-mutate-message-0`

| Spec | Requirement |
|------|-------------|
| RSL15c | The SDK must not mutate the user-supplied `Message` object |
| MPD3 | The SDK must not mutate the user-supplied operation |

Tests that encoding the operation values for the request leaves the user's `Message`, and each operation's `data` and `encoding`, unchanged.

### Setup
```pseudo
channel_name = "test-RSL15c-patch-${random_id()}"

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, { "versionSerial": "vs1" })
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
object_op = MessagePatchDataOperation(op: "set", path: "/obj", data: { "b": 1 })
binary_op = MessagePatchDataOperation(op: "set", path: "/bin", data: bytes([0x01, 0x02]))
message = Message(
  serial: "s1",
  patches: MessagePatches(data: [object_op, binary_op])
)

AWAIT channel.patchMessage(message)
```

### Assertions
```pseudo
ASSERT message.action IS null OR message.action == MessageAction.MESSAGE_CREATE
ASSERT message.patches.data.length == 2
ASSERT message.patches.data[0].data == { "b": 1 }
ASSERT message.patches.data[0].encoding IS null
ASSERT message.patches.data[1].data == bytes([0x01, 0x02])
ASSERT message.patches.data[1].encoding IS null
```

---

## RSL15a — patchMessage requires a serial

**Test ID**: `rest/unit/RSL15a/patch-serial-required-0`

**Spec requirement:** RSL15a — The first argument is a `Message` object, which must contain a populated `serial` field.

Tests that `patchMessage()` fails, without sending a request, when the message has no serial. The error code matches the one `update_delete_message.md` asserts for the sibling operations.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, { "versionSerial": "vs1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-RSL15a-patch-${random_id()}")
```

### Test Steps and Assertions
```pseudo
AWAIT channel.patchMessage(Message(
  patches: MessagePatches(data: [MessagePatchDataOperation(op: "append", path: "/text", data: "x")])
)) FAILS WITH error
ASSERT error.code == 40003

ASSERT captured_requests.length == 0
```
