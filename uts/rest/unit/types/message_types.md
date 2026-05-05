# Message Types Tests

Spec points: `TM1`, `TM2`, `TM3`, `TM4`, `TM2a`, `TM2b`, `TM2c`, `TM2d`, `TM2e`, `TM2f`, `TM2g`, `TM2h`, `TM2i`

## Test Type
Unit test - pure type/model validation

## Mock Configuration
No mocks required - these verify type structure, constructors, and encoding.

---

## TM2a-TM2i - Message attributes

**Spec requirement:** Message type must provide all required attributes according to TM2a-TM2i specifications.

| Spec | Attribute | Description |
|------|-----------|-------------|
| TM2a | id | Unique message identifier |
| TM2b | name | Event name |
| TM2c | data | Message payload (string, object, or binary) |
| TM2d | clientId | Client ID of the publisher |
| TM2e | connectionId | Connection ID of the publisher |
| TM2f | timestamp | Message timestamp in milliseconds |
| TM2g | encoding | Encoding information for the data |
| TM2h | extras | Additional message metadata |
| TM2i | serial | Server-assigned serial number |

Tests that `Message` has all required attributes.

### Test Steps
```pseudo
# TM2a - id attribute
message = Message(id: "unique-id")
ASSERT message.id == "unique-id"

# TM2b - name attribute
message = Message(name: "event-name")
ASSERT message.name == "event-name"

# TM2c - data attribute
message = Message(data: "string-data")
ASSERT message.data == "string-data"

message = Message(data: { "key": "value" })
ASSERT message.data == { "key": "value" }

message = Message(data: bytes([0x01, 0x02]))
ASSERT message.data == bytes([0x01, 0x02])

# TM2d - clientId attribute
message = Message(clientId: "message-client")
ASSERT message.clientId == "message-client"

# TM2e - connectionId attribute
message = Message(connectionId: "conn-id")
ASSERT message.connectionId == "conn-id"

# TM2f - timestamp attribute
message = Message(timestamp: 1234567890000)
ASSERT message.timestamp == 1234567890000

# TM2g - encoding attribute
message = Message(encoding: "json/base64")
ASSERT message.encoding == "json/base64"

# TM2h - extras attribute
message = Message(extras: {
  "push": { "notification": { "title": "Hello" } }
})
ASSERT message.extras["push"]["notification"]["title"] == "Hello"

# TM2i - serial attribute (server-assigned)
# Serial is typically read-only from server responses
```

---

## TM3 - fromEncoded / fromEncodedArray

**Spec requirement (TM3):** `fromEncoded` and `fromEncodedArray` are alternative constructors that take an already-deserialized Message-like object (or array of such), and optionally a `channelOptions`, and return a `Message` (or array of `Messages`) that is decoded and decrypted as specified in RSL6. The idiomatic method name varies by SDK (e.g., `fromEncoded` in JS, `fromJson`/`fromMap` in Dart).

Tests that `fromEncoded` correctly deserializes wire-format messages.

### Test Steps
```pseudo
json_data = {
  "id": "msg-123",
  "name": "test-event",
  "data": "hello world",
  "clientId": "sender-client",
  "connectionId": "conn-456",
  "timestamp": 1234567890000,
  "encoding": null,
  "extras": { "headers": { "x-custom": "value" } }
}

message = Message.fromEncoded(json_data)

ASSERT message.id == "msg-123"
ASSERT message.name == "test-event"
ASSERT message.data == "hello world"
ASSERT message.clientId == "sender-client"
ASSERT message.connectionId == "conn-456"
ASSERT message.timestamp == 1234567890000
ASSERT message.extras["headers"]["x-custom"] == "value"
```

---

## TM3 - fromEncoded decodes encoding field

**Spec requirement (TM3):** `fromEncoded` decodes data based on the `encoding` field, with any residual transforms left in the `encoding` property per RSL6b.

Tests that `fromEncoded` correctly handles encoded data during deserialization.

### Test Cases

| ID | Encoding | Wire Data | Expected Data |
|----|----------|-----------|---------------|
| 1 | `null` | `"plain text"` | `"plain text"` |
| 2 | `"json"` | `"{\"key\":\"value\"}"` | `{ "key": "value" }` |
| 3 | `"base64"` | `"SGVsbG8="` | `bytes("Hello")` |
| 4 | `"json/base64"` | `"eyJrIjoidiJ9"` | `{ "k": "v" }` |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  json_data = {
    "id": "msg",
    "name": "event",
    "data": test_case.wire_data,
    "encoding": test_case.encoding
  }

  message = Message.fromEncoded(json_data)

  ASSERT message.data == test_case.expected_data
  ASSERT message.encoding IS null  # Encoding consumed
```

---

## TM4 - Message constructors

**Spec requirement (TM4):** `Message` has constructors `constructor(name: String?, data: Data?)` and `constructor(name: String?, data: Data?, clientId: String?)`.

Tests that `Message` can be constructed with the specified signatures.

### Test Steps
```pseudo
# constructor(name, data)
message = Message(name: "event-name", data: "payload")
ASSERT message.name == "event-name"
ASSERT message.data == "payload"
ASSERT message.clientId IS null OR message.clientId IS undefined

# constructor(name, data, clientId)
message = Message(name: "event-name", data: "payload", clientId: "client-1")
ASSERT message.name == "event-name"
ASSERT message.data == "payload"
ASSERT message.clientId == "client-1"

# Both name and data are nullable
message = Message(name: null, data: null)
ASSERT message.name IS null OR message.name IS undefined
ASSERT message.data IS null OR message.data IS undefined
```

---

## TM - Null/missing attributes

**Spec requirement:** Message type must handle null or missing optional attributes correctly.

Tests that null or missing attributes are handled correctly.

### Test Steps
```pseudo
# Minimal message
message = Message()

# All optional attributes should be null/undefined
ASSERT message.id IS null OR message.id IS undefined
ASSERT message.name IS null OR message.name IS undefined
ASSERT message.data IS null OR message.data IS undefined
ASSERT message.clientId IS null OR message.clientId IS undefined
ASSERT message.timestamp IS null OR message.timestamp IS undefined
```

---

## TM - Message with extras

**Spec requirement:** Message extras field must support arbitrary metadata including push notification configuration (TM2h).

Tests that Message extras (push notifications, etc.) are handled correctly.

### Test Steps
```pseudo
# Push notification extras
message = Message(
  name: "push-event",
  data: "payload",
  extras: {
    "push": {
      "notification": {
        "title": "New Message",
        "body": "You have a new notification"
      },
      "data": {
        "customKey": "customValue"
      }
    }
  }
)

ASSERT message.extras["push"]["notification"]["title"] == "New Message"
ASSERT message.extras["push"]["data"]["customKey"] == "customValue"
```
