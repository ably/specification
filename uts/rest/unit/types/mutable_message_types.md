# Mutable Message Type Tests

Spec points: `TM2j`, `TM2r`, `TM2s`, `TM2s1`, `TM2s2`, `TM2s3`, `TM2s4`, `TM2s5`, `TM2u`, `TM5`, `TM8`, `TM8a`, `MOP2a`, `MOP2b`, `MOP2c`, `UDR1`, `UDR2`, `UDR2a`, `TAN1`, `TAN2`, `TAN2a`–`TAN2l`

## Test Type
Unit test (no mocking needed — pure type construction and serialization)

---

## TM5 — MessageAction enum values

**Spec requirement:** TM5 — `Message` `Action` enum has the following values in order from zero: `MESSAGE_CREATE`, `MESSAGE_UPDATE`, `MESSAGE_DELETE`, `META`, `MESSAGE_SUMMARY`, `MESSAGE_APPEND`.

Tests that the `MessageAction` enum has the correct numeric values for wire serialization.

### Assertions
```pseudo
ASSERT MessageAction.MESSAGE_CREATE.toInt() == 0
ASSERT MessageAction.MESSAGE_UPDATE.toInt() == 1
ASSERT MessageAction.MESSAGE_DELETE.toInt() == 2
ASSERT MessageAction.META.toInt() == 3
ASSERT MessageAction.MESSAGE_SUMMARY.toInt() == 4
ASSERT MessageAction.MESSAGE_APPEND.toInt() == 5

# Round-trip from int
ASSERT MessageAction.fromInt(0) == MessageAction.MESSAGE_CREATE
ASSERT MessageAction.fromInt(5) == MessageAction.MESSAGE_APPEND
```

---

## TM2j, TM2r — Message has action and serial fields

| Spec | Requirement |
|------|-------------|
| TM2j | `action` enum |
| TM2r | `serial` string — an opaque string that uniquely identifies the message |

Tests that `Message` supports `action` and `serial` fields, and that `toJson()` serializes `action` as a numeric value.

### Test Steps
```pseudo
msg = Message(
  name: "test",
  data: "hello",
  serial: "serial-1",
  action: MessageAction.MESSAGE_UPDATE
)
```

### Assertions
```pseudo
ASSERT msg.serial == "serial-1"
ASSERT msg.action == MessageAction.MESSAGE_UPDATE

json_data = msg.toJson()
ASSERT json_data["serial"] == "serial-1"
ASSERT json_data["action"] == 1  # Numeric wire value for MESSAGE_UPDATE
ASSERT json_data["name"] == "test"
ASSERT json_data["data"] == "hello"
```

---

## TM2s — Message.version populated from wire

| Spec | Requirement |
|------|-------------|
| TM2s | `version` is an object containing information about the latest version of a message |
| TM2s1 | `serial` — an opaque string that identifies the specific version |
| TM2s2 | `timestamp` — time in milliseconds since epoch |
| TM2s3 | `clientId` — string |
| TM2s4 | `description` — string |
| TM2s5 | `metadata` — Dict<String, string> |

Tests that `Message.fromJson()` correctly parses the `version` object with all fields.

### Test Steps
```pseudo
msg = Message.fromJson({
  "serial": "msg-serial-1",
  "name": "test",
  "data": "hello",
  "version": {
    "serial": "version-serial-1",
    "timestamp": 1700000001000,
    "clientId": "editor-1",
    "description": "fixed typo",
    "metadata": { "reason": "typo", "tool": "editor" }
  }
})
```

### Assertions
```pseudo
ASSERT msg.version IS NOT null
ASSERT msg.version IS MessageVersion
ASSERT msg.version.serial == "version-serial-1"
ASSERT msg.version.timestamp == 1700000001000
ASSERT msg.version.clientId == "editor-1"
ASSERT msg.version.description == "fixed typo"
ASSERT msg.version.metadata["reason"] == "typo"
ASSERT msg.version.metadata["tool"] == "editor"
```

---

## TM2s1, TM2s2 — Message.version defaults when not on wire

| Spec | Requirement |
|------|-------------|
| TM2s | If a message does not contain a `version` object the SDK must initialize one and set a subset of fields |
| TM2s1 | If `version.serial` is not received, must be set to the `TM2r` `serial`, if set |
| TM2s2 | If `version.timestamp` is not received, must be set to the `TM2f` `timestamp`, if set |

Tests that when `version` is absent from the wire, the SDK initializes it with defaults from `serial` and `timestamp`.

### Test Steps
```pseudo
msg = Message.fromJson({
  "serial": "msg-serial-1",
  "timestamp": 1700000000000,
  "name": "test",
  "data": "hello"
})
```

### Assertions
```pseudo
# version must be initialized even though not on wire
ASSERT msg.version IS NOT null
ASSERT msg.version IS MessageVersion

# TM2s1: version.serial defaults to message serial
ASSERT msg.version.serial == "msg-serial-1"

# TM2s2: version.timestamp defaults to message timestamp
ASSERT msg.version.timestamp == 1700000000000

# Other fields should be null
ASSERT msg.version.clientId IS null
ASSERT msg.version.description IS null
ASSERT msg.version.metadata IS null
```

---

## TM2u, TM8a — Message.annotations defaults to empty

| Spec | Requirement |
|------|-------------|
| TM2u | `annotations` is an object of type `MessageAnnotations`. If not set on the wire, the SDK must set it to an empty `MessageAnnotations` object |
| TM8a | `summary` `Dict<string, JsonObject>` — a missing `summary` field indicates an empty summary |

Tests that `annotations` is initialized to an empty `MessageAnnotations` when not present on the wire.

### Test Steps
```pseudo
msg = Message.fromJson({
  "serial": "msg-serial-1",
  "name": "test"
})
```

### Assertions
```pseudo
ASSERT msg.annotations IS NOT null
ASSERT msg.annotations IS MessageAnnotations
ASSERT msg.annotations.summary IS NOT null
ASSERT msg.annotations.summary IS empty  # No keys
```

---

## MOP2a–c — MessageOperation fields

| Spec | Requirement |
|------|-------------|
| MOP2a | `clientId?: String` |
| MOP2b | `description?: String` |
| MOP2c | `metadata?: Dict<String, String>` |

Tests that `MessageOperation` can be constructed with all optional fields and that `toJson()` serializes correctly.

### Test Steps
```pseudo
op = MessageOperation(
  clientId: "user-1",
  description: "edit description",
  metadata: { "reason": "typo", "tool": "editor" }
)
```

### Assertions
```pseudo
ASSERT op.clientId == "user-1"
ASSERT op.description == "edit description"
ASSERT op.metadata["reason"] == "typo"
ASSERT op.metadata["tool"] == "editor"

# Serialization
json_data = op.toJson()
ASSERT json_data["clientId"] == "user-1"
ASSERT json_data["description"] == "edit description"
ASSERT json_data["metadata"]["reason"] == "typo"

# All-null construction
empty_op = MessageOperation()
ASSERT empty_op.clientId IS null
ASSERT empty_op.description IS null
ASSERT empty_op.metadata IS null

empty_json = empty_op.toJson()
ASSERT "clientId" NOT IN empty_json
ASSERT "description" NOT IN empty_json
ASSERT "metadata" NOT IN empty_json
```

---

## UDR2a — UpdateDeleteResult fields

| Spec | Requirement |
|------|-------------|
| UDR1 | Contains the result of an update or delete message operation |
| UDR2a | `versionSerial` `String?` — the new version serial string |

Tests that `UpdateDeleteResult` can be constructed from a response map.

### Assertions
```pseudo
# Non-null versionSerial
result1 = UpdateDeleteResult.fromJson({ "versionSerial": "version-serial-abc" })
ASSERT result1 IS UpdateDeleteResult
ASSERT result1.versionSerial == "version-serial-abc"

# Null versionSerial (message superseded)
result2 = UpdateDeleteResult.fromJson({ "versionSerial": null })
ASSERT result2.versionSerial IS null

# Missing versionSerial key treated as null
result3 = UpdateDeleteResult.fromJson({})
ASSERT result3.versionSerial IS null
```

---

## TAN2 — Annotation type attributes and action encoding

| Spec | Requirement |
|------|-------------|
| TAN1 | An `Annotation` represents an individual annotation event |
| TAN2a | `id` string |
| TAN2b | `action` enum: `ANNOTATION_CREATE` (0), `ANNOTATION_DELETE` (1) |
| TAN2b1 | In wire protocol action is numeric; SDK exposes as enum |
| TAN2c–TAN2l | Various string, number, and object fields |

Tests that `Annotation.fromJson()` decodes all fields and that `AnnotationAction` enum has correct numeric values.

### Test Steps
```pseudo
ann = Annotation.fromJson({
  "id": "ann-id-1",
  "action": 0,
  "clientId": "user-1",
  "name": "like",
  "count": 5,
  "data": "thumbs-up",
  "encoding": null,
  "timestamp": 1700000000000,
  "serial": "ann-serial-1",
  "messageSerial": "msg-serial-1",
  "type": "com.example.reaction",
  "extras": { "custom": "metadata" }
})
```

### Assertions
```pseudo
ASSERT ann IS Annotation
ASSERT ann.id == "ann-id-1"
ASSERT ann.action == AnnotationAction.ANNOTATION_CREATE
ASSERT ann.clientId == "user-1"
ASSERT ann.name == "like"
ASSERT ann.count == 5
ASSERT ann.data == "thumbs-up"
ASSERT ann.timestamp == 1700000000000
ASSERT ann.serial == "ann-serial-1"
ASSERT ann.messageSerial == "msg-serial-1"
ASSERT ann.type == "com.example.reaction"
ASSERT ann.extras["custom"] == "metadata"

# AnnotationAction numeric values
ASSERT AnnotationAction.ANNOTATION_CREATE.toInt() == 0
ASSERT AnnotationAction.ANNOTATION_DELETE.toInt() == 1
ASSERT AnnotationAction.fromInt(0) == AnnotationAction.ANNOTATION_CREATE
ASSERT AnnotationAction.fromInt(1) == AnnotationAction.ANNOTATION_DELETE
```
