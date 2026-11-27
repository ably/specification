# Message Patch Type Tests

Spec points: `TM5`, `TM2v`, `MPA1`, `MPA2`, `MPA2a`, `MPA2b`, `MPA2b1`, `MPA2b2`, `MPA2b3`, `MPD2`, `MPD2a`–`MPD2d`, `MPD4`, `MPD4a`, `MPH2`, `MPH2a`–`MPH2c`, `MPU2`, `MPU2a`, `MPU2b`, `MPP2`, `MPP2a`

## Test Type
Unit test (no mocking needed — pure type construction, encoding and decoding)

## Related Tests

The encoding of operation values when sending (MPD3) is covered by `uts/rest/unit/channel/patch_message.md` and `uts/realtime/unit/channels/channel_patch_message.md`. Applying a patch (TM9) is covered by `uts/rest/unit/types/message_apply_patch.md`.

---

## TM5 — MessageAction includes MESSAGE_PATCH

**Test ID**: `rest/unit/TM5/message-patch-action-value-0`

**Spec requirement:** TM5 — `Message` `Action` enum has the following values in order from zero: `MESSAGE_CREATE`, `MESSAGE_UPDATE`, `MESSAGE_DELETE`, `META`, `MESSAGE_SUMMARY`, `MESSAGE_APPEND`, `MESSAGE_PATCH`.

Tests that `MESSAGE_PATCH` has the numeric wire value 6.

### Assertions
```pseudo
ASSERT MessageAction.MESSAGE_PATCH.toInt() == 6
ASSERT MessageAction.fromInt(6) == MessageAction.MESSAGE_PATCH

msg = Message.fromJson({ "serial": "s1", "action": 6 })
ASSERT msg.action == MessageAction.MESSAGE_PATCH
```

---

## TM2v, MPA2, MPD2, MPH2, MPU2, MPP2 — received patches are parsed into typed operations

**Test ID**: `rest/unit/TM2v/patches-parsed-from-wire-0`

| Spec | Requirement |
|------|-------------|
| TM2v | `patches` `MessagePatches` — the changes a `MESSAGE_PATCH` makes |
| MPA2a | `data` array of `MessagePatchDataOperation` |
| MPA2b1 | `extras.headers` array of `MessagePatchHeaderOperation` |
| MPA2b2 | `extras.userClaim` `MessagePatchUserClaimOperation` |
| MPA2b3 | `extras.privileged` `MessagePatchPrivilegedOperation` |
| MPD2a–MPD2d | `op`, `path`, `data`, `encoding` |
| MPH2a–MPH2c | `op`, `key`, `value` |
| MPU2a, MPU2b | `op`, `value` |
| MPP2a | `op` |

Tests that every attribute of a received `patches` field is exposed, including operations that only Ably sends.

### Test Steps
```pseudo
msg = AWAIT Message.fromEncoded({
  "action": 6,
  "serial": "msg-serial-1",
  "version": { "serial": "version-serial-2", "timestamp": 1700000002000 },
  "patches": {
    "data": [
      { "op": "append", "path": "/content/0/text", "data": " more" },
      { "op": "set", "data": "replaced" },
      { "op": "remove", "path": "/old" }
    ],
    "extras": {
      "headers": [
        { "op": "set", "key": "status", "value": "complete" },
        { "op": "set", "key": "count", "value": 3 },
        { "op": "set", "key": "final", "value": true },
        { "op": "remove", "key": "draft" }
      ],
      "userClaim": { "op": "set", "value": "moderator" },
      "privileged": { "op": "remove" }
    }
  }
})
```

### Assertions
```pseudo
ASSERT msg.patches IS MessagePatches

data_ops = msg.patches.data
ASSERT data_ops.length == 3
ASSERT data_ops[0] IS MessagePatchDataOperation
ASSERT data_ops[0].op == "append"
ASSERT data_ops[0].path == "/content/0/text"
ASSERT data_ops[0].data == " more"
ASSERT data_ops[1].op == "set"
ASSERT data_ops[1].path IS null OR data_ops[1].path == ""
ASSERT data_ops[1].data == "replaced"
ASSERT data_ops[2].op == "remove"
ASSERT data_ops[2].path == "/old"
ASSERT data_ops[2].data IS null

headers = msg.patches.extras.headers
ASSERT headers.length == 4
ASSERT headers[0] IS MessagePatchHeaderOperation
ASSERT headers[0].op == "set"
ASSERT headers[0].key == "status"
ASSERT headers[0].value == "complete"
ASSERT headers[1].value == 3
ASSERT headers[2].value == true
ASSERT headers[3].op == "remove"
ASSERT headers[3].key == "draft"
ASSERT headers[3].value IS null

ASSERT msg.patches.extras.userClaim IS MessagePatchUserClaimOperation
ASSERT msg.patches.extras.userClaim.op == "set"
ASSERT msg.patches.extras.userClaim.value == "moderator"

ASSERT msg.patches.extras.privileged IS MessagePatchPrivilegedOperation
ASSERT msg.patches.extras.privileged.op == "remove"
```

---

## MPD4, MPD4a — operation values are decoded, keeping JSON values as text

**Test ID**: `rest/unit/MPD4/patch-values-decoded-0`

| Spec | Requirement |
|------|-------------|
| MPD4 | The `data` of each operation is decoded by inverting the transforms in its `encoding` per RSL6a |
| MPD4a | If the first transform is `json`, it is not inverted: `data` stays as JSON text with `encoding` `json` |

Tests that each operation's value is decoded as a message's `data` is, except that a JSON value stays as JSON text.

### Test Steps
```pseudo
msg = AWAIT Message.fromEncoded({
  "action": 6,
  "serial": "s1",
  "patches": {
    "data": [
      { "op": "set", "path": "/a", "data": "{\"b\":1}", "encoding": "json" },
      { "op": "set", "path": "/n", "data": "42", "encoding": "json" },
      { "op": "set", "path": "/c", "data": "AQI=", "encoding": "base64" },
      { "op": "set", "path": "/u", "data": "aGk=", "encoding": "utf-8/base64" },
      { "op": "set", "path": "/j", "data": "eyJ4IjoxfQ==", "encoding": "json/utf-8/base64" },
      { "op": "append", "path": "/d", "data": "text" }
    ]
  }
})
```

### Assertions
```pseudo
ops = msg.patches.data

# MPD4a — JSON values stay as JSON text, whatever their type
ASSERT ops[0].data == "{\"b\":1}"
ASSERT ops[0].encoding == "json"
ASSERT ops[1].data == "42"
ASSERT ops[1].encoding == "json"

# MPD4 — other transforms are inverted, as for a message's data
ASSERT ops[2].data == bytes([0x01, 0x02])
ASSERT ops[2].encoding IS null OR ops[2].encoding == ""
ASSERT ops[3].data == "hi"
ASSERT ops[3].encoding IS null OR ops[3].encoding == ""

# MPD4a — the transforms after a leading json are inverted, leaving the JSON text
ASSERT ops[4].data == "{\"x\":1}"
ASSERT ops[4].encoding == "json"

ASSERT ops[5].data == "text"
ASSERT ops[5].encoding IS null OR ops[5].encoding == ""
```

---

## MPA2, MPD2, MPH2 — patches round-trip through toJson

**Test ID**: `rest/unit/MPA2/patches-serialized-to-wire-0`

| Spec | Requirement |
|------|-------------|
| MPA2 | The attributes of `MessagePatches` |
| MPD2 | The attributes of `MessagePatchDataOperation` |
| MPH2 | The attributes of `MessagePatchHeaderOperation` |

Tests that a `Message` constructed with `patches` serializes them with the wire field names. String values need no encoding (MPD3a), so they appear unchanged.

### Test Steps
```pseudo
msg = Message(
  serial: "s1",
  action: MessageAction.MESSAGE_PATCH,
  patches: MessagePatches(
    data: [
      MessagePatchDataOperation(op: "append", path: "/text", data: "lo"),
      MessagePatchDataOperation(op: "remove", path: "/old")
    ],
    extras: {
      "headers": [MessagePatchHeaderOperation(op: "set", key: "status", value: "complete")]
    }
  )
)
json_data = msg.toJson()
```

### Assertions
```pseudo
ASSERT json_data["action"] == 6
ASSERT json_data["serial"] == "s1"
ASSERT json_data["patches"]["data"] == [
  { "op": "append", "path": "/text", "data": "lo" },
  { "op": "remove", "path": "/old" }
]
ASSERT json_data["patches"]["extras"]["headers"] == [
  { "op": "set", "key": "status", "value": "complete" }
]
```
