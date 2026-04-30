# PresenceMessage Types Tests

Spec points: `TP1`, `TP2`, `TP3`, `TP3a`, `TP3b`, `TP3c`, `TP3d`, `TP3e`, `TP3f`, `TP3g`, `TP3h`, `TP3i`, `TP4`, `TP5`

## Test Type
Unit test — pure type/model validation, no mocks required.

---

## TP2 - PresenceAction enum values

**Spec requirement:** PresenceMessage Action enum has the following values in order
from zero: ABSENT, PRESENT, ENTER, LEAVE, UPDATE.

### Test Steps
```pseudo
ASSERT PresenceAction.absent.index == 0
ASSERT PresenceAction.present.index == 1
ASSERT PresenceAction.enter.index == 2
ASSERT PresenceAction.leave.index == 3
ASSERT PresenceAction.update.index == 4
```

---

## TP3a-TP3i - PresenceMessage attributes

**Spec requirement:** PresenceMessage type must provide all required attributes.

| Spec | Attribute | Description |
|------|-----------|-------------|
| TP3a | id | Unique presence message identifier |
| TP3b | action | PresenceAction enum |
| TP3c | clientId | Client ID of the member |
| TP3d | connectionId | Connection ID of the member |
| TP3e | data | Payload (string, object, or binary) |
| TP3f | encoding | Encoding information for data |
| TP3g | timestamp | Timestamp in milliseconds since epoch |
| TP3h | memberKey | String combining connectionId and clientId |
| TP3i | extras | JSON-encodable key-value pairs |

### Test Steps
```pseudo
# TP3a - id attribute
msg = PresenceMessage(id: "presence-123")
ASSERT msg.id == "presence-123"

# TP3b - action attribute
msg = PresenceMessage(action: ENTER)
ASSERT msg.action == ENTER

# TP3c - clientId attribute
msg = PresenceMessage(clientId: "user-1")
ASSERT msg.clientId == "user-1"

# TP3d - connectionId attribute
msg = PresenceMessage(connectionId: "conn-1")
ASSERT msg.connectionId == "conn-1"

# TP3e - data attribute (string)
msg = PresenceMessage(data: "hello")
ASSERT msg.data == "hello"

# TP3e - data attribute (object)
msg = PresenceMessage(data: { "status": "online" })
ASSERT msg.data == { "status": "online" }

# TP3f - encoding attribute
msg = PresenceMessage(encoding: "json")
ASSERT msg.encoding == "json"

# TP3g - timestamp attribute
msg = PresenceMessage(timestamp: 1234567890000)
ASSERT msg.timestamp == 1234567890000

# TP3i - extras attribute
msg = PresenceMessage(extras: { "headers": { "x-custom": "value" } })
ASSERT msg.extras["headers"]["x-custom"] == "value"
```

---

## TP3h - memberKey combines connectionId and clientId

**Spec requirement:** memberKey is a string function that combines the connectionId
and clientId to ensure multiple connected clients with the same clientId are uniquely
identifiable.

### Test Steps
```pseudo
msg = PresenceMessage(connectionId: "conn-1", clientId: "user-1")
ASSERT msg.memberKey == "conn-1:user-1"

msg2 = PresenceMessage(connectionId: "conn-2", clientId: "user-1")
ASSERT msg2.memberKey == "conn-2:user-1"

# Same clientId, different connectionId — different memberKey
ASSERT msg.memberKey != msg2.memberKey
```

---

## TP3d - connectionId defaults from ProtocolMessage

**Spec requirement:** If connectionId is not present in a received presence message,
it should be set to the connectionId of the encapsulating ProtocolMessage.

### Test Steps
```pseudo
protocol_msg = ProtocolMessage(
  action: PRESENCE,
  connectionId: "proto-conn-1",
  presence: [
    { "action": "enter", "clientId": "user-1" }
  ]
)

# After processing, the PresenceMessage should inherit connectionId
presence_msg = protocol_msg.presence[0]
ASSERT presence_msg.connectionId == "proto-conn-1"
```

---

## TP3a - id defaults from ProtocolMessage

**Spec requirement:** For Realtime messages without an id, the id should be set to
protocolMsgId:index where index is the 0-based position in the presence array.

### Test Steps
```pseudo
protocol_msg = ProtocolMessage(
  action: PRESENCE,
  id: "proto-msg-42",
  presence: [
    { "action": "enter", "clientId": "alice" },
    { "action": "enter", "clientId": "bob" }
  ]
)

# After processing, presence messages should have derived ids
ASSERT protocol_msg.presence[0].id == "proto-msg-42:0"
ASSERT protocol_msg.presence[1].id == "proto-msg-42:1"
```

---

## TP3g - timestamp defaults from ProtocolMessage

**Spec requirement:** If timestamp is not present in a received presence message,
it should be set to the timestamp of the encapsulating ProtocolMessage.

### Test Steps
```pseudo
protocol_msg = ProtocolMessage(
  action: PRESENCE,
  timestamp: 9999999,
  presence: [
    { "action": "enter", "clientId": "user-1" }
  ]
)

presence_msg = protocol_msg.presence[0]
ASSERT presence_msg.timestamp == 9999999
```

---

## TP3 - PresenceMessage from JSON (wire format)

**Spec requirement:** PresenceMessage must support deserialization from JSON wire format.

### Test Steps
```pseudo
json_data = {
  "id": "pm-123",
  "action": "enter",
  "clientId": "user-1",
  "connectionId": "conn-1",
  "data": "hello",
  "encoding": null,
  "timestamp": 1234567890000,
  "extras": { "headers": { "x-key": "x-value" } }
}

msg = PresenceMessage.fromJson(json_data)

ASSERT msg.id == "pm-123"
ASSERT msg.action == ENTER
ASSERT msg.clientId == "user-1"
ASSERT msg.connectionId == "conn-1"
ASSERT msg.data == "hello"
ASSERT msg.timestamp == 1234567890000
ASSERT msg.extras["headers"]["x-key"] == "x-value"
```

---

## TP3 - PresenceMessage with encoded data from JSON

**Spec requirement:** Deserialization must decode data based on the encoding field.

### Test Cases

| ID | Encoding | Wire Data | Expected Data |
|----|----------|-----------|---------------|
| 1 | `null` | `"plain text"` | `"plain text"` |
| 2 | `"json"` | `"{\"status\":\"online\"}"` | `{ "status": "online" }` |
| 3 | `"base64"` | `"SGVsbG8="` | `bytes("Hello")` |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  json_data = {
    "action": "enter",
    "clientId": "user-1",
    "data": test_case.wire_data,
    "encoding": test_case.encoding
  }

  msg = PresenceMessage.fromJson(json_data)

  ASSERT msg.data == test_case.expected_data
  ASSERT msg.encoding IS null  # Encoding consumed
```

---

## TP3 - PresenceMessage to JSON (wire format)

**Spec requirement:** PresenceMessage must support serialization to JSON wire format.

### Test Steps
```pseudo
msg = PresenceMessage(
  action: ENTER,
  clientId: "user-1",
  data: "hello",
  extras: { "headers": { "x-key": "x-value" } }
)

json_data = msg.toJson()

ASSERT json_data["action"] == "enter"
ASSERT json_data["clientId"] == "user-1"
ASSERT json_data["data"] == "hello"
ASSERT json_data["extras"]["headers"]["x-key"] == "x-value"
```

---

## TP3 - Null/missing attributes omitted from serialization

**Spec requirement:** Null or missing optional attributes should be omitted from
serialized output.

### Test Steps
```pseudo
msg = PresenceMessage(action: ENTER, clientId: "user-1")

json_data = msg.toJson()

ASSERT json_data["action"] == "enter"
ASSERT json_data["clientId"] == "user-1"
ASSERT "data" NOT IN json_data OR json_data["data"] IS null
ASSERT "encoding" NOT IN json_data OR json_data["encoding"] IS null
ASSERT "extras" NOT IN json_data OR json_data["extras"] IS null
ASSERT "id" NOT IN json_data OR json_data["id"] IS null
```

---

## TP4 - fromEncoded and fromEncodedArray

**Spec requirement:** fromEncoded and fromEncodedArray are alternative constructors
that take an already-deserialized PresenceMessage-like object (or array) and return
decoded and decrypted PresenceMessage(s). Behavior is the same as TM3.

### Test Steps
```pseudo
# fromEncoded — single message
raw = {
  "action": "enter",
  "clientId": "user-1",
  "data": "{\"status\":\"online\"}",
  "encoding": "json"
}

msg = PresenceMessage.fromEncoded(raw)

ASSERT msg.action == ENTER
ASSERT msg.clientId == "user-1"
ASSERT msg.data == { "status": "online" }
ASSERT msg.encoding IS null

# fromEncodedArray — array of messages
raw_array = [
  { "action": "enter", "clientId": "alice", "data": "hello" },
  { "action": "enter", "clientId": "bob", "data": "world" }
]

messages = PresenceMessage.fromEncodedArray(raw_array)

ASSERT messages.length == 2
ASSERT messages[0].clientId == "alice"
ASSERT messages[0].data == "hello"
ASSERT messages[1].clientId == "bob"
ASSERT messages[1].data == "world"
```

---

## TP5 - PresenceMessage size calculation

**Spec requirement:** The size of the PresenceMessage is calculated in the same way
as for Message (see TM6). This is used for TO3l8 (maxMessageSize) enforcement.

### Test Steps
```pseudo
# Size includes clientId + data + extras (same formula as TM6)
msg = PresenceMessage(
  action: ENTER,
  clientId: "user-1",
  data: "hello"
)

size = msg.size

# Size should account for clientId (6 bytes) + data (5 bytes) = 11
ASSERT size == 11

# Size with object data (JSON-encoded size)
msg2 = PresenceMessage(
  action: ENTER,
  clientId: "u",
  data: { "key": "value" }
)

# clientId (1) + JSON-encoded data length
ASSERT msg2.size > 1
```
