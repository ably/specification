# REST Mutable Messages Integration Tests

Spec points: `RSL1n`, `RSL11`, `RSL14`, `RSL15`, `RSAN1`, `RSAN2`, `RSAN3`

## Test Type
Integration test against Ably sandbox

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox-rest.ably.io`.

### App Provisioning

Uses `ably-common/test-resources/test-app-setup.json` which provides:
- `keys[0]` — full access (default capability `{"*":["*"]}`)

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  full_access_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {full_access_key}
```

### Notes
- All clients use `useBinaryProtocol: false` (SDK does not implement msgpack)
- All clients use `endpoint: "sandbox"`
- All channel names use the `mutable:` namespace prefix — the test app setup configures the `mutable` namespace with `mutableMessages: true`, which is required for getMessage, updateMessage, deleteMessage, appendMessage, and annotations

---

## RSL1n — publish returns serials from sandbox

**Spec requirement:** RSL1n — On success, returns a `PublishResult` containing message serials.

Tests that publish returns real serials from the Ably sandbox.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
channel_name = "mutable:test-RSL1n-serials-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps and Assertions
```pseudo
# Single message
result1 = AWAIT channel.publish(name: "event1", data: "data1")
ASSERT result1 IS PublishResult
ASSERT result1.serials IS List
ASSERT result1.serials.length == 1
ASSERT result1.serials[0] IS String
ASSERT result1.serials[0].length > 0

# Multiple messages
result2 = AWAIT channel.publish(messages: [
  Message(name: "event2", data: "data2"),
  Message(name: "event3", data: "data3"),
  Message(name: "event4", data: "data4")
])
ASSERT result2.serials.length == 3
ASSERT ALL serial IN result2.serials: serial IS String AND serial.length > 0

# Serials should be unique
ASSERT result2.serials[0] != result2.serials[1]
ASSERT result2.serials[1] != result2.serials[2]
```

---

## RSL11 — getMessage retrieves published message

**Spec requirement:** RSL11 — `getMessage()` retrieves a message by serial.

Tests that a published message can be retrieved by its serial.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
channel_name = "mutable:test-RSL11-getMessage-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Publish a message and get its serial
publish_result = AWAIT channel.publish(name: "test-event", data: "hello world")
serial = publish_result.serials[0]

# Retrieve the message by serial
msg = AWAIT channel.getMessage(serial)
```

### Assertions
```pseudo
ASSERT msg IS Message
ASSERT msg.name == "test-event"
ASSERT msg.data == "hello world"
ASSERT msg.serial == serial
ASSERT msg.action == MessageAction.MESSAGE_CREATE
ASSERT msg.timestamp IS NOT null
```

---

## RSL15 — updateMessage updates a published message

**Spec requirement:** RSL15 — `updateMessage()` sends a PATCH that updates a message.

Tests that a published message can be updated and the update is visible via `getMessage()`.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
channel_name = "mutable:test-RSL15-update-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Publish original message
publish_result = AWAIT channel.publish(name: "original", data: "original-data")
serial = publish_result.serials[0]

# Update the message
update_result = AWAIT channel.updateMessage(
  Message(serial: serial, name: "updated", data: "updated-data"),
  operation: MessageOperation(description: "edited content")
)
```

### Assertions
```pseudo
# Update returns a version serial
ASSERT update_result IS UpdateDeleteResult
ASSERT update_result.versionSerial IS String
ASSERT update_result.versionSerial.length > 0

# Verify via getMessage
updated_msg = AWAIT channel.getMessage(serial)
ASSERT updated_msg.name == "updated"
ASSERT updated_msg.data == "updated-data"
ASSERT updated_msg.action == MessageAction.MESSAGE_UPDATE
ASSERT updated_msg.version.description == "edited content"
```

---

## RSL15 — deleteMessage deletes a published message

**Spec requirement:** RSL15 — `deleteMessage()` sends a PATCH that marks a message as deleted.

Tests that a published message can be deleted.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
channel_name = "mutable:test-RSL15-delete-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Publish original message
publish_result = AWAIT channel.publish(name: "to-delete", data: "delete-me")
serial = publish_result.serials[0]

# Delete the message
delete_result = AWAIT channel.deleteMessage(
  Message(serial: serial)
)
```

### Assertions
```pseudo
ASSERT delete_result IS UpdateDeleteResult
ASSERT delete_result.versionSerial IS String
ASSERT delete_result.versionSerial.length > 0

# Verify via getMessage — action should be MESSAGE_DELETE
deleted_msg = AWAIT channel.getMessage(serial)
ASSERT deleted_msg.action == MessageAction.MESSAGE_DELETE
```

---

## RSL14 — getMessageVersions returns version history

**Spec requirement:** RSL14 — `getMessageVersions()` retrieves all versions of a message.

Tests that version history contains the original and all updates.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
channel_name = "mutable:test-RSL14-versions-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Publish original
publish_result = AWAIT channel.publish(name: "versioned", data: "v1")
serial = publish_result.serials[0]

# Update twice
AWAIT channel.updateMessage(
  Message(serial: serial, data: "v2"),
  operation: MessageOperation(description: "first edit")
)
AWAIT channel.updateMessage(
  Message(serial: serial, data: "v3"),
  operation: MessageOperation(description: "second edit")
)

# Get version history
versions = AWAIT channel.getMessageVersions(serial)
```

### Assertions
```pseudo
ASSERT versions IS PaginatedResult
ASSERT versions.items.length >= 3  # Original + 2 updates

# All items should be Messages with the same serial
FOR item IN versions.items:
  ASSERT item IS Message
  ASSERT item.serial == serial
```

---

## RSL15 — appendMessage appends to a published message

**Spec requirement:** RSL15 — `appendMessage()` sends a PATCH with `MESSAGE_APPEND` action.

Tests that a message can be appended to.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
channel_name = "mutable:test-RSL15-append-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Publish original
publish_result = AWAIT channel.publish(name: "appendable", data: "original")
serial = publish_result.serials[0]

# Append to the message
append_result = AWAIT channel.appendMessage(
  Message(serial: serial, data: "appended-data"),
  operation: MessageOperation(description: "appended content")
)
```

### Assertions
```pseudo
ASSERT append_result IS UpdateDeleteResult
ASSERT append_result.versionSerial IS String
ASSERT append_result.versionSerial.length > 0
```

---

## RSAN1, RSAN2 — publish and delete annotations on a message

| Spec | Requirement |
|------|-------------|
| RSAN1 | `RestAnnotations#publish` creates an annotation on a message |
| RSAN2 | `RestAnnotations#delete` deletes an annotation from a message |
| RSAN3 | `RestAnnotations#get` retrieves annotations for a message |

Tests the full annotation lifecycle: create, verify, delete.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
channel_name = "mutable:test-RSAN-lifecycle-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Publish a message to annotate
publish_result = AWAIT channel.publish(name: "annotatable", data: "content")
serial = publish_result.serials[0]

# Create an annotation
AWAIT channel.annotations.publish(serial, Annotation(
  type: "com.ably.reactions",
  name: "like"
))

# Verify annotation exists
annotations = AWAIT channel.annotations.get(serial)
ASSERT annotations.items.length >= 1

found = false
FOR ann IN annotations.items:
  IF ann.type == "com.ably.reactions" AND ann.name == "like":
    found = true
    ASSERT ann.action == AnnotationAction.ANNOTATION_CREATE
    ASSERT ann.messageSerial == serial
ASSERT found == true

# Delete the annotation
AWAIT channel.annotations.delete(serial, Annotation(
  type: "com.ably.reactions",
  name: "like"
))
```

---

## RSAN3 — get annotations returns PaginatedResult

**Spec requirement:** RSAN3c — Returns a `PaginatedResult<Annotation>` containing decoded annotations.

Tests that multiple annotations can be retrieved as a paginated result.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
channel_name = "mutable:test-RSAN3-paginated-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Publish a message
publish_result = AWAIT channel.publish(name: "multi-annotated", data: "content")
serial = publish_result.serials[0]

# Publish multiple annotations
AWAIT channel.annotations.publish(serial, Annotation(
  type: "com.ably.reactions",
  name: "like"
))
AWAIT channel.annotations.publish(serial, Annotation(
  type: "com.ably.reactions",
  name: "heart"
))

# Retrieve annotations
result = AWAIT channel.annotations.get(serial)
```

### Assertions
```pseudo
ASSERT result IS PaginatedResult
ASSERT result.items.length >= 2

FOR ann IN result.items:
  ASSERT ann IS Annotation
  ASSERT ann.messageSerial == serial
  ASSERT ann.type == "com.ably.reactions"
  ASSERT ann.timestamp IS NOT null
```
