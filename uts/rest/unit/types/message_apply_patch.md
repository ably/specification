# Message.applyPatch Tests

Spec points: `TM9`, `TM9a`, `TM9b`, `TM9c`, `TM9d`, `TM9d1`–`TM9d4`, `TM9e`, `TM9f`, `TM9f1`–`TM9f5`, `TM9g`, `TM9g1`–`TM9g4`

## Test Type
Unit test (no mocking needed — `Message.applyPatch` is a pure function)

## Conventions

The message and the patch are built with `Message.fromEncoded` (TM3), as the SDK would decode them on receipt, so each operation's value is in the form MPD4 gives it. Two helpers keep the tests short:

```pseudo
FUNCTION decode(values):
  RETURN AWAIT Message.fromEncoded({ "serial": "s1", "timestamp": 1, ...values })

FUNCTION decode_patch(patches, values = {}):
  RETURN decode({
    "action": 6,  # MESSAGE_PATCH
    "version": { "serial": "v2", "timestamp": 2 },
    "patches": patches,
    ...values
  })
```

A message whose `data` is decoded JSON is built with `"encoding": "json"`; a message whose `data` is JSON text is built with the text and no encoding, so it decodes to a string.

Every failure of `applyPatch` is an `ErrorInfo` with `code` 40000 and `statusCode` 400 (TM9a, TM9b, TM9e).

---

## TM9d, TM9f3, TM9g1 — applies operations to decoded JSON data

**Test ID**: `rest/unit/TM9f3/apply-to-decoded-data-0`

| Spec | Requirement |
|------|-------------|
| TM9d1 | The result's `action` is `MESSAGE_UPDATE` |
| TM9d4 | The result's `version` is the patch's `version` |
| TM9f3e | `set` with the last reference token `-` adds an element after the last one |
| TM9f3d | `set` of an object member adds the member if absent |
| TM9f3f | `append` concatenates a string value |
| TM9f3h | A value with `encoding` `json` is the JSON value its text represents |
| TM9g1 | Header operations `set` and `remove` change `extras.headers` |

Tests that `applyPatch` applies data and header operations to a message whose `data` is a decoded JSON object.

### Test Steps
```pseudo
message = decode({
  "name": "reply",
  "data": "{\"content\":[{\"type\":\"text\",\"text\":\"Hel\"}],\"meta\":{\"kept\":true}}",
  "encoding": "json",
  "extras": { "headers": { "status": "streaming", "model": "m1" } }
})
patch = decode_patch({
  "data": [
    { "op": "append", "path": "/content/0/text", "data": "lo" },
    { "op": "set", "path": "/content/-", "data": "{\"type\":\"tool\"}", "encoding": "json" },
    { "op": "set", "path": "/done", "data": "true", "encoding": "json" }
  ],
  "extras": {
    "headers": [
      { "op": "set", "key": "status", "value": "complete" },
      { "op": "remove", "key": "model" }
    ]
  }
})

patched = Message.applyPatch(message, patch)
```

### Assertions
```pseudo
ASSERT patched.action == MessageAction.MESSAGE_UPDATE
ASSERT patched.serial == "s1"
ASSERT patched.name == "reply"
ASSERT patched.version.serial == "v2"
ASSERT patched.data == {
  "content": [{ "type": "text", "text": "Hello" }, { "type": "tool" }],
  "meta": { "kept": true },
  "done": true
}
ASSERT patched.encoding IS null OR patched.encoding == ""
ASSERT patched.extras == { "headers": { "status": "complete" } }
ASSERT patched.patches IS null
ASSERT patched IS Message
```

---

## TM9d — keeps the message's fields other than data, extras and version

**Test ID**: `rest/unit/TM9d/keeps-message-fields-0`

| Spec | Requirement |
|------|-------------|
| TM9d | The result has the message's attribute values, except those in TM9d1–TM9d4 |
| TM9d | The patch's own `clientId`, `connectionId` and `timestamp` do not affect the result |

Tests that the result takes only `action`, `data`, `encoding`, `extras` and `version` from applying the patch.

### Test Steps
```pseudo
message = decode({ "clientId": "author", "connectionId": "c1", "data": "Hel" })
patch = decode_patch(
  { "data": [{ "op": "append", "data": "lo" }] },
  { "clientId": "patcher", "connectionId": "c2", "timestamp": 2 }
)

patched = Message.applyPatch(message, patch)
```

### Assertions
```pseudo
ASSERT patched.clientId == "author"
ASSERT patched.connectionId == "c1"
ASSERT patched.timestamp == 1
ASSERT patched.version.serial == "v2"
ASSERT patched.data == "Hello"
```

---

## TM9c — does not mutate the message

**Test ID**: `rest/unit/TM9c/message-not-mutated-0`

**Spec requirement:** TM9c — The SDK must not mutate the message, nor any value it holds, such as a JSON-encodable object or array in its `data` or its `extras`.

Tests that the message, its decoded data and its extras are unchanged after `applyPatch`.

### Test Steps
```pseudo
message = decode({
  "action": 0,  # MESSAGE_CREATE
  "data": "{\"a\":{\"text\":\"x\"},\"b\":{\"unchanged\":true},\"list\":[1]}",
  "encoding": "json",
  "extras": { "headers": { "h": "v" } }
})
before = message.toJson()
patch = decode_patch({
  "data": [
    { "op": "append", "path": "/a/text", "data": "y" },
    { "op": "set", "path": "/list/-", "data": "2", "encoding": "json" }
  ],
  "extras": { "headers": [{ "op": "set", "key": "h", "value": "w" }] }
})

patched = Message.applyPatch(message, patch)
```

### Assertions
```pseudo
ASSERT message.toJson() == before
ASSERT message.action == MessageAction.MESSAGE_CREATE
ASSERT message.data == { "a": { "text": "x" }, "b": { "unchanged": true }, "list": [1] }
ASSERT message.extras == { "headers": { "h": "v" } }

ASSERT patched.data == { "a": { "text": "xy" }, "b": { "unchanged": true }, "list": [1, 2] }
ASSERT patched.extras == { "headers": { "h": "w" } }
```

---

## TM9f5 — splices operations into JSON text, keeping its formatting

**Test ID**: `rest/unit/TM9f5/splice-into-json-text-0`

| Spec | Requirement |
|------|-------------|
| TM9f5 | For `data` holding JSON text, only the described text changes; whitespace and number text are unchanged |
| TM9f5a | The value text is the operation's `data` verbatim if its `encoding` is `json`, else the JSON string of its value |
| TM9f5c | A new member is inserted after the last member's value as `,"name":value`, without whitespace |
| TM9f5d | A new element is inserted after the last element as `,value`, without whitespace |
| TM9f5e | `append` inserts the escaped string before the closing quotation mark |

Tests that operations on a string holding JSON text produce exactly the expected text.

### Test Steps
```pseudo
text = "{ \"content\" : [ {\"text\":\"Hel\"} ], \"n\": 1.0 }"
message = decode({ "data": text })
patch = decode_patch({
  "data": [
    { "op": "append", "path": "/content/0/text", "data": "lo \"world\"" },
    { "op": "set", "path": "/obj", "data": "{ \"spaced\" : 1 }", "encoding": "json" },
    { "op": "set", "path": "/content/-", "data": "end" }
  ]
})

patched = Message.applyPatch(message, patch)
```

### Assertions
```pseudo
ASSERT patched.data IS String
ASSERT patched.data == "{ \"content\" : [ {\"text\":\"Hello \\\"world\\\"\"},\"end\" ], \"n\": 1.0,\"obj\":{ \"spaced\" : 1 } }"
ASSERT patched.encoding IS null OR patched.encoding == ""
```

---

## TM9f5 — binary JSON text is patched as its UTF-8 text is

**Test ID**: `rest/unit/TM9f5/splice-into-binary-json-1`

**Spec requirement:** TM9f5 — If `data` is binary holding JSON text, the result is binary holding the changed JSON text.

Tests that a message whose `data` is binary UTF-8 JSON gives binary data with the same text a string message gives.

### Test Steps
```pseudo
text = "{ \"content\" : [ {\"text\":\"Hel\"} ] }"
message = decode({ "data": base64_encode(utf8_encode(text)), "encoding": "base64" })
patch = decode_patch({
  "data": [{ "op": "append", "path": "/content/0/text", "data": "lo" }]
})

patched = Message.applyPatch(message, patch)
```

### Assertions
```pseudo
ASSERT patched.data IS Binary
ASSERT utf8_decode(patched.data) == "{ \"content\" : [ {\"text\":\"Hello\"} ] }"
```

---

## TM9f5f, TM9f5g, TM9f5h — removes members and elements from JSON text

**Test ID**: `rest/unit/TM9f5f/remove-from-json-text-0`

| Spec | Requirement |
|------|-------------|
| TM9f5f | A member or element followed by another is deleted up to the start of the next |
| TM9f5g | The last of several is deleted from the end of the previous value |
| TM9f5h | The only one is deleted from its start to the end of its value |

Tests the three cases of removing from JSON text, on JSON kept outside an Ably message, passed as the message's `data`.

### Test Steps
```pseudo
patch = decode_patch({
  "data": [
    { "op": "remove", "path": "/a/1" },
    { "op": "remove", "path": "/b" },
    { "op": "remove", "path": "/c" },
    { "op": "remove", "path": "/d/only" }
  ]
})
message = Message(serial: "s1", data: "{\"a\":[1,2,3],\"b\":2,\"c\":3,\"d\":{\"only\":true}}")

patched = Message.applyPatch(message, patch)
```

### Assertions
```pseudo
# /a/1: element 2 is followed by 3, so deleted up to it (TM9f5f)
# /b and then /c: each is followed by another member, so deleted up to it (TM9f5f)
# /d/only: the only member of "d", so its text is deleted (TM9f5h)
ASSERT patched.data == "{\"a\":[1,3],\"d\":{}}"
```

### Test Steps (last of several)
```pseudo
message2 = Message(serial: "s1", data: "{\"a\":1, \"b\":2}")
patch2 = decode_patch({ "data": [{ "op": "remove", "path": "/b" }] })

patched2 = Message.applyPatch(message2, patch2)
```

### Assertions (last of several)
```pseudo
# TM9f5g: deleted from the end of 1, the previous value
ASSERT patched2.data == "{\"a\":1}"
```

---

## TM9f5i — escaped member names are matched after unescaping

**Test ID**: `rest/unit/TM9f5i/escaped-member-name-0`

**Spec requirement:** TM9f5i — The SDK must compare the name of a member in the JSON text with a reference token after unescaping the JSON string of the name.

Tests that a member whose name is escaped in the JSON text is found by its unescaped name, and that RFC 6901 escapes in the path are unescaped.

### Test Steps
```pseudo
message = decode({ "data": "{\"a\\u0062\":\"x\",\"c/d\":\"y\"}" })
patch = decode_patch({
  "data": [
    { "op": "append", "path": "/ab", "data": "1" },
    { "op": "append", "path": "/c~1d", "data": "2" }
  ]
})

patched = Message.applyPatch(message, patch)
```

### Assertions
```pseudo
ASSERT patched.data == "{\"a\\u0062\":\"x1\",\"c/d\":\"y2\"}"
```

---

## TM9f5c, TM9f5e — spliced text is escaped as a JSON string

**Test ID**: `rest/unit/TM9f5e/json-string-escaping-0`

| Spec | Requirement |
|------|-------------|
| TM9f5c | A new member's name is inserted as a JSON string (RFC 8259 section 7) |
| TM9f5e | `append` inserts the JSON string of its `data`, without the enclosing quotation marks |

Tests that text spliced into JSON text, for both `append` and a new member's name, is escaped so that the result is valid JSON holding the original characters. RFC 8259 allows more than one escaping of a character, so the test parses the result rather than comparing the text.

### Test Steps
```pseudo
message = decode({ "data": "{\"t\":\"\"}" })
patch = decode_patch({
  "data": [
    { "op": "append", "path": "/t", "data": "q\"b\\n\nt\tc\u0001é<>&" },
    { "op": "set", "path": "/new\nkey", "data": "v" }
  ]
})

patched = Message.applyPatch(message, patch)
```

### Assertions
```pseudo
ASSERT patched.data IS String
ASSERT json_parse(patched.data) == { "t": "q\"b\\n\nt\tc\u0001é<>&", "new\nkey": "v" }
ASSERT patched.data STARTS WITH "{\"t\":\"q"
ASSERT patched.data ENDS WITH "\"}"
```

---

## TM9f2 — applies operations to the whole of data

**Test ID**: `rest/unit/TM9f2/apply-to-whole-data-0`

| Spec | Requirement |
|------|-------------|
| TM9f2a | `set` without a path replaces `data`; a `json` object or array is decoded and the `encoding` is empty |
| TM9f2b | `append` to absent `data` sets it to the operation's `data`, and the `encoding` is empty |
| TM9f2c | `append` of a string to a string, or binary to binary, concatenates them, and the `encoding` is empty |

Tests the operations without a `path`.

### Test Steps and Assertions
```pseudo
append = decode_patch({ "data": [{ "op": "append", "data": " world" }] })

# TM9f2c — string
ASSERT Message.applyPatch(decode({ "data": "hello" }), append).data == "hello world"

# TM9f2b — absent data
appended = Message.applyPatch(decode({}), append)
ASSERT appended.data == " world"
ASSERT appended.encoding IS null OR appended.encoding == ""

# TM9f2c — binary
append_binary = decode_patch({ "data": [{ "op": "append", "data": "Aw==", "encoding": "base64" }] })
binary = decode({ "data": "AQI=", "encoding": "base64" })
ASSERT Message.applyPatch(binary, append_binary).data == bytes([0x01, 0x02, 0x03])

# TM9f2a — set to a JSON value
set = decode_patch({ "data": [{ "op": "set", "data": "{\"a\":1}", "encoding": "json" }] })
patched = Message.applyPatch(decode({ "data": "hello" }), set)
ASSERT patched.data == { "a": 1 }
ASSERT patched.encoding IS null OR patched.encoding == ""

# TM9f2a — set to a string
set_string = decode_patch({ "data": [{ "op": "set", "data": "replaced" }] })
ASSERT Message.applyPatch(decode({ "data": "{\"a\":1}", "encoding": "json" }), set_string).data == "replaced"
```

---

## TM9f2a, TM9f2d — rejects whole-data operations that cannot be applied

**Test ID**: `rest/unit/TM9f2d/append-whole-non-string-0`

| Spec | Requirement |
|------|-------------|
| TM9f2a | `set` without a path of a `json` value that is not an object or array cannot be applied |
| TM9f2b | `append` to absent `data` requires the operation's `encoding` to be empty |
| TM9f2d | Any other `append` without a path, and any `remove` without a path, cannot be applied |

Tests that appending without a path to decoded JSON data, appending a JSON value without a path, setting the whole of `data` to a JSON scalar, and removing without a path, fail.

### Test Steps and Assertions
```pseudo
message = decode({ "data": "{\"a\":1}", "encoding": "json" })

append = decode_patch({ "data": [{ "op": "append", "data": "x" }] })
Message.applyPatch(message, append) FAILS WITH error
ASSERT error.code == 40000
ASSERT error.statusCode == 400

remove = decode_patch({ "data": [{ "op": "remove" }] })
Message.applyPatch(message, remove) FAILS WITH error
ASSERT error.code == 40000
ASSERT error.statusCode == 400

# TM9f2b, TM9f2c — the operation's encoding must be empty
append_json = decode_patch({ "data": [{ "op": "append", "data": "\"x\"", "encoding": "json" }] })
FOR target IN [decode({}), decode({ "data": "text" })]:
  Message.applyPatch(target, append_json) FAILS WITH error
  ASSERT error.code == 40000
  ASSERT error.statusCode == 400

# TM9f2a — a JSON scalar cannot replace the whole of data
FOR value IN ["null", "1", "true", "\"s\""]:
  set_scalar = decode_patch({ "data": [{ "op": "set", "data": value, "encoding": "json" }] })
  Message.applyPatch(decode({ "data": "hello" }), set_scalar) FAILS WITH error
  ASSERT error.code == 40000
  ASSERT error.statusCode == 400
```

---

## TM9e — rejects the whole patch if any operation is rejected

**Test ID**: `rest/unit/TM9e/atomic-rejection-0`

**Spec requirement:** TM9e — If any operation cannot be applied, `applyPatch` must fail with an `ErrorInfo` with `code` 40000 and `statusCode` 400, and must not return a result. The `message` should identify the operation by its index.

Tests that a failure in the second operation fails the whole patch, and leaves the message unchanged.

### Test Steps
```pseudo
message = decode({ "data": "{\"a\":\"x\"}", "encoding": "json", "extras": { "headers": { "h": "v" } } })
patch = decode_patch({
  "data": [
    { "op": "append", "path": "/a", "data": "y" },
    { "op": "append", "path": "/missing", "data": "y" }
  ],
  "extras": { "headers": [{ "op": "set", "key": "h", "value": "w" }] }
})
```

### Assertions
```pseudo
Message.applyPatch(message, patch) FAILS WITH error
ASSERT error.code == 40000
ASSERT error.statusCode == 400

ASSERT message.data == { "a": "x" }
ASSERT message.extras == { "headers": { "h": "v" } }
```

---

## TM9f1, TM9f3 — rejects operations that cannot be applied

**Test ID**: `rest/unit/TM9f3/invalid-operations-rejected-0`

| Spec | Requirement |
|------|-------------|
| TM9f1 | An `op` other than `set`, `append` or `remove` cannot be applied |
| TM9f3 | A path operation requires `data` to be a JSON object or array |
| TM9f3a | A `path` must be a JSON Pointer |
| TM9f3b | Every reference token but the last must reference an existing value |
| TM9f3c | The parent must be an object or array |
| TM9f3e | `set` of an array element requires `-` or an existing index |
| TM9f3f | `append` requires an existing string, and cannot use `-` |
| TM9f3g | `remove` requires an existing value, and cannot use `-` |

Tests each case that cannot be applied, against both decoded JSON data and JSON text, since the SDK applies operations to each form separately (TM9f4, TM9f5).

### Test Steps and Assertions
```pseudo
cases = [
  # [data, operation]
  [{ "a": 1 },  { "op": "append", "path": "/a", "data": "x" }],    # TM9f3f: not a string
  [{ "a": [] }, { "op": "append", "path": "/a/-", "data": "x" }],  # TM9f3f: "-"
  [{ "a": "x" }, { "op": "append", "path": "/a", "data": "\"y\"", "encoding": "json" }],  # TM9f3f: encoding not empty
  [{ "a": [] }, { "op": "remove", "path": "/a/-" }],               # TM9f3g: "-"
  [{ "a": [] }, { "op": "set", "path": "/a/0", "data": "x" }],     # TM9f3e: no element 0
  [{ "a": [1] }, { "op": "set", "path": "/a/01", "data": "x" }],   # TM9f3e: leading zero is not an index
  [{ "a": 1 },  { "op": "set", "path": "/a/b", "data": "x" }],     # TM9f3c: parent is a number
  [{ "a": 1 },  { "op": "set", "path": "/x/y", "data": "x" }],     # TM9f3b: /x does not exist
  [{ "a": 1 },  { "op": "set", "path": "a", "data": "x" }],        # TM9f3a: no leading "/"
  [{ "a": 1 },  { "op": "set", "path": "/~2", "data": "x" }],      # TM9f3a: invalid "~" escape
  [{ "a": 1 },  { "op": "remove", "path": "/b" }],                 # TM9f3g: /b does not exist
  [{ "a": 1 },  { "op": "move", "path": "/a" }]                    # TM9f1: unknown op
]

FOR [data, op] IN cases:
  FOR message IN [
    decode({ "data": json_stringify(data), "encoding": "json" }),  # decoded JSON
    decode({ "data": json_stringify(data) })                       # JSON text
  ]:
    patch = decode_patch({ "data": [op] })
    Message.applyPatch(message, patch) FAILS WITH error
    ASSERT error.code == 40000
    ASSERT error.statusCode == 400

# TM9f3 — a path operation on data that is not a JSON object or array
not_container = decode({ "data": "plain text" })
patch = decode_patch({ "data": [{ "op": "set", "path": "/a", "data": "x" }] })
Message.applyPatch(not_container, patch) FAILS WITH error
ASSERT error.code == 40000
```

---

## TM9g1 — rejects removing a header that does not exist

**Test ID**: `rest/unit/TM9g1/remove-missing-header-0`

**Spec requirement:** TM9g1 — `remove` cannot be applied if `extras.headers` does not have the header.

### Test Steps and Assertions
```pseudo
message = decode({ "data": "x" })
patch = decode_patch({ "extras": { "headers": [{ "op": "remove", "key": "h" }] } })

Message.applyPatch(message, patch) FAILS WITH error
ASSERT error.code == 40000
ASSERT error.statusCode == 400
```

---

## TM9g1 — set header adds extras and headers when absent

**Test ID**: `rest/unit/TM9g1/set-header-adds-extras-1`

**Spec requirement:** TM9g1 — `set` sets the member of `extras.headers` named by its `key`, adding `extras` and `extras.headers` if they are absent.

### Test Steps and Assertions
```pseudo
message = decode({ "data": "x" })
patch = decode_patch({ "extras": { "headers": [{ "op": "set", "key": "status", "value": "done" }] } })

ASSERT Message.applyPatch(message, patch).extras == { "headers": { "status": "done" } }
```

---

## TM9d, TM9g2, TM9g4 — sets or removes the user claim, ignoring the patch's own extras

**Test ID**: `rest/unit/TM9g2/user-claim-operations-0`

| Spec | Requirement |
|------|-------------|
| TM9g2 | `userClaim` `set` sets `extras.userClaim`; `remove` deletes it, if present |
| TM9g4 | If deleting `extras.userClaim` leaves `extras` empty, the result has no `extras` |
| TM9d | The patch's own `extras` do not affect the result |

### Test Steps and Assertions
```pseudo
message = decode({ "data": "x", "extras": { "headers": { "h": "v" }, "userClaim": "moderator" } })

set = decode_patch(
  { "data": [{ "op": "append", "data": "y" }], "extras": { "userClaim": { "op": "set", "value": "guest" } } },
  { "extras": { "push": { "notification": { "title": "t" } }, "userClaim": "guest" } }
)
patched = Message.applyPatch(message, set)
ASSERT patched.extras == { "headers": { "h": "v" }, "userClaim": "guest" }
ASSERT patched.version.serial == "v2"

remove = decode_patch({
  "data": [{ "op": "append", "data": "y" }],
  "extras": { "userClaim": { "op": "remove" } }
})
ASSERT Message.applyPatch(message, remove).extras == { "headers": { "h": "v" } }

# Removing a missing claim succeeds, and leaves no extras (TM9g4)
unclaimed = decode({ "data": "x" })
ASSERT Message.applyPatch(unclaimed, remove).extras IS null
```

---

## TM9g3 — removes privileged extras

**Test ID**: `rest/unit/TM9g3/privileged-remove-0`

**Spec requirement:** TM9g3 — `privileged` `remove` deletes `extras.privileged`, if present.

### Test Steps and Assertions
```pseudo
message = decode({ "data": "x", "extras": { "headers": { "h": "v" }, "privileged": { "skipRule": "*" } } })
patch = decode_patch({
  "extras": {
    "headers": [{ "op": "set", "key": "h", "value": "w" }],
    "privileged": { "op": "remove" }
  }
})

ASSERT Message.applyPatch(message, patch).extras == { "headers": { "h": "w" } }
```

---

## TM9a, TM9b — rejects a patch for another message, or a message that is not a patch

**Test ID**: `rest/unit/TM9a/reject-non-patch-or-serial-0`

| Spec | Requirement |
|------|-------------|
| TM9a | If the patch's `action` is not `MESSAGE_PATCH`, fail with 40000 |
| TM9b | If the patch's `serial` is not the message's `serial`, fail with 40000 |

### Test Steps and Assertions
```pseudo
message = decode({ "data": "x" })

# TM9b
other = decode_patch({ "data": [{ "op": "append", "data": "y" }] }, { "serial": "s2" })
Message.applyPatch(message, other) FAILS WITH error
ASSERT error.code == 40000
ASSERT error.statusCode == 400

# TM9a
Message.applyPatch(message, message) FAILS WITH error
ASSERT error.code == 40000
ASSERT error.statusCode == 400
```

---

## TM9f4 — sets a member named like a language-reserved key as an ordinary member

**Test ID**: `rest/unit/TM9f4/reserved-member-name-0`

**Spec requirement:** TM9f4 — The SDK must add or set a member named by a reference token as an ordinary member of the object.

Tests that a member named `__proto__` (special in JavaScript) is set as an ordinary member. Other languages run the same test; it guards against any name the language's object model treats specially.

### Test Steps
```pseudo
message = decode({ "data": "{}", "encoding": "json" })
patch = decode_patch({
  "data": [{ "op": "set", "path": "/__proto__", "data": "{\"polluted\":true}", "encoding": "json" }]
})

patched = Message.applyPatch(message, patch)
```

### Assertions
```pseudo
ASSERT keys(patched.data) == ["__proto__"]
ASSERT patched.data["__proto__"] == { "polluted": true }
```
