# Message Types Tests

Spec points: `TM1`, `TM2`, `TM3`, `TM4`, `TM5`, `TM2a`, `TM2b`, `TM2c`, `TM2d`, `TM2e`, `TM2f`, `TM2g`, `TM2h`, `TM2i`

## Test Type
Unit test - pure type/model validation

## Mock Configuration
No mocks required - these verify type structure and serialization.

---

## TM2a-TM2i - Message attributes

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

## TM3 - Message from JSON (wire format)

Tests that `Message` can be deserialized from JSON wire format.

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

message = Message.fromJson(json_data)

ASSERT message.id == "msg-123"
ASSERT message.name == "test-event"
ASSERT message.data == "hello world"
ASSERT message.clientId == "sender-client"
ASSERT message.connectionId == "conn-456"
ASSERT message.timestamp == 1234567890000
ASSERT message.extras["headers"]["x-custom"] == "value"
```

---

## TM3 - Message with encoded data from JSON

Tests that `Message` correctly handles encoded data during deserialization.

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

  message = Message.fromJson(json_data)

  ASSERT message.data == test_case.expected_data
  ASSERT message.encoding IS null  # Encoding consumed
```

---

## TM4 - Message to JSON (wire format)

Tests that `Message` serializes correctly for transmission.

### Test Steps
```pseudo
message = Message(
  id: "custom-id",
  name: "outgoing-event",
  data: "outgoing-data",
  clientId: "sending-client"
)

json_data = message.toJson()

ASSERT json_data["id"] == "custom-id"
ASSERT json_data["name"] == "outgoing-event"
ASSERT json_data["data"] == "outgoing-data"
ASSERT json_data["clientId"] == "sending-client"
```

---

## TM4 - Message with object data to JSON

Tests that object data is JSON-encoded for transmission.

### Test Steps
```pseudo
message = Message(
  name: "json-event",
  data: { "nested": { "array": [1, 2, 3] } }
)

json_data = message.toJson()

# Object should be JSON-encoded with encoding field set
ASSERT json_data["encoding"] == "json"
ASSERT parse_json(json_data["data"]) == { "nested": { "array": [1, 2, 3] } }
```

---

## TM4 - Message with binary data to JSON

Tests that binary data is base64-encoded for JSON transmission.

### Test Steps
```pseudo
message = Message(
  name: "binary-event",
  data: bytes([0x00, 0x01, 0xFF])
)

json_data = message.toJson()

ASSERT json_data["encoding"] == "base64"
ASSERT base64_decode(json_data["data"]) == bytes([0x00, 0x01, 0xFF])
```

---

## TM5 - Message equality

Tests that messages can be compared for equality.

### Test Steps
```pseudo
message1 = Message(id: "same-id", name: "event", data: "data")
message2 = Message(id: "same-id", name: "event", data: "data")
message3 = Message(id: "different-id", name: "event", data: "data")

ASSERT message1 == message2  # Same content
ASSERT message1 != message3  # Different id
```

---

## TM - Message with extras

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

json_data = message.toJson()

ASSERT json_data["extras"]["push"]["notification"]["title"] == "New Message"
ASSERT json_data["extras"]["push"]["data"]["customKey"] == "customValue"
```

---

## TM - Null/missing attributes

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

# Serialization should omit null fields
json_data = message.toJson()
ASSERT "id" NOT IN json_data OR json_data["id"] IS null
ASSERT "name" NOT IN json_data OR json_data["name"] IS null
ASSERT "data" NOT IN json_data OR json_data["data"] IS null
```
