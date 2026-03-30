# Realtime Mutable Messages & Annotations Integration Tests

Spec points: `RTL28`, `RTL31`, `RTL32`, `RTAN1`, `RTAN2`, `RTAN4`

## Test Type
Integration test against Ably sandbox

## Purpose

End-to-end verification of mutable messages and annotations over realtime
(WebSocket) connections against the Ably sandbox. These tests complement the REST
integration tests (`rest/integration/mutable_messages.md`) by verifying:

- Update/delete/append via MESSAGE ProtocolMessage (RTL32) rather than HTTP PATCH (RSL15)
- Real-time delivery of mutation events to subscribers
- Annotation publish/delete via ANNOTATION ProtocolMessage (RTAN1/RTAN2) rather than HTTP POST (RSAN1/RSAN2)
- Real-time delivery of annotations to subscribers (RTAN4)
- getMessage and getMessageVersions work from a RealtimeChannel instance (RTL28/RTL31)

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox-rest.ably.io`.

**Note:** `useBinaryProtocol: false` is required if the SDK does not implement msgpack.

### App Provisioning

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

### Notes
- All clients use `useBinaryProtocol: false` (SDK does not implement msgpack)
- All clients use `endpoint: "sandbox"`
- All channel names use the `mutable:` namespace prefix — the test app setup configures
  the `mutable` namespace with `mutableMessages: true`

---

## RTL32 — Update a message via realtime and observe on subscriber

**Spec requirement:** RTL32b1 — `updateMessage()` sends a MESSAGE ProtocolMessage
with `MESSAGE_UPDATE` action. RTL32d — returns `UpdateDeleteResult` from ACK.

Tests that a message published via realtime can be updated via a realtime channel,
and the update event is delivered in real-time to a subscriber on a separate connection.

### Setup
```pseudo
channel_name = "mutable:rt-update-" + random_id()

client_a = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client_b = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client_a.connect()
client_b.connect()

AWAIT_STATE client_a.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
AWAIT_STATE client_b.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds

channel_a = client_a.channels.get(channel_name)
channel_b = client_b.channels.get(channel_name)

AWAIT channel_b.attach()

# Collect all messages on client B
received_messages = []
channel_b.subscribe((msg) => {
  received_messages.append(msg)
})

AWAIT channel_a.attach()
```

### Test Steps
```pseudo
# Publish original message via realtime
AWAIT channel_a.publish(name: "original", data: "v1")

# Wait for client B to receive the original
poll_until(
  condition: FUNCTION() => received_messages.length >= 1,
  interval: 200ms,
  timeout: 10s
)

# Get the serial from the received message
serial = received_messages[0].serial

# Update via realtime
update_result = AWAIT channel_a.updateMessage(
  Message(serial: serial, name: "updated", data: "v2"),
  operation: MessageOperation(description: "edited")
)

# Wait for client B to receive the update event
poll_until(
  condition: FUNCTION() => received_messages.length >= 2,
  interval: 200ms,
  timeout: 10s
)
```

### Assertions
```pseudo
# Update returned a result
ASSERT update_result IS UpdateDeleteResult
ASSERT update_result.versionSerial IS String
ASSERT update_result.versionSerial.length > 0

# Client B received the original
ASSERT received_messages[0].action == MessageAction.MESSAGE_CREATE
ASSERT received_messages[0].name == "original"
ASSERT received_messages[0].data == "v1"
ASSERT received_messages[0].serial IS String
ASSERT received_messages[0].serial.length > 0

# Client B received the update in real-time
update_msg = received_messages[1]
ASSERT update_msg.action == MessageAction.MESSAGE_UPDATE
ASSERT update_msg.name == "updated"
ASSERT update_msg.data == "v2"
ASSERT update_msg.serial == serial
```

### Cleanup
```pseudo
AWAIT client_a.close()
AWAIT client_b.close()
```

---

## RTL32 — Delete a message via realtime and observe on subscriber

**Spec requirement:** RTL32b1 — `deleteMessage()` sends a MESSAGE ProtocolMessage
with `MESSAGE_DELETE` action.

Tests that a published message can be deleted via a realtime channel and the delete
event is delivered in real-time to a subscriber.

### Setup
```pseudo
channel_name = "mutable:rt-delete-" + random_id()

client_a = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client_b = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client_a.connect()
client_b.connect()

AWAIT_STATE client_a.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
AWAIT_STATE client_b.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds

channel_a = client_a.channels.get(channel_name)
channel_b = client_b.channels.get(channel_name)

AWAIT channel_b.attach()

received_messages = []
channel_b.subscribe((msg) => {
  received_messages.append(msg)
})

AWAIT channel_a.attach()
```

### Test Steps
```pseudo
# Publish original
AWAIT channel_a.publish(name: "to-delete", data: "ephemeral")

poll_until(
  condition: FUNCTION() => received_messages.length >= 1,
  interval: 200ms,
  timeout: 10s
)

serial = received_messages[0].serial

# Delete via realtime
delete_result = AWAIT channel_a.deleteMessage(Message(serial: serial))

# Wait for delete event
poll_until(
  condition: FUNCTION() => received_messages.length >= 2,
  interval: 200ms,
  timeout: 10s
)
```

### Assertions
```pseudo
ASSERT delete_result IS UpdateDeleteResult
ASSERT delete_result.versionSerial IS String
ASSERT delete_result.versionSerial.length > 0

# Client B received the delete event
delete_msg = received_messages[1]
ASSERT delete_msg.action == MessageAction.MESSAGE_DELETE
ASSERT delete_msg.serial == serial
```

### Cleanup
```pseudo
AWAIT client_a.close()
AWAIT client_b.close()
```

---

## RTL32 — Append to a message via realtime and observe on subscriber

**Spec requirement:** RTL32b1 — `appendMessage()` sends a MESSAGE ProtocolMessage
with `MESSAGE_APPEND` action.

### Setup
```pseudo
channel_name = "mutable:rt-append-" + random_id()

client_a = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client_b = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client_a.connect()
client_b.connect()

AWAIT_STATE client_a.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
AWAIT_STATE client_b.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds

channel_a = client_a.channels.get(channel_name)
channel_b = client_b.channels.get(channel_name)

AWAIT channel_b.attach()

received_messages = []
channel_b.subscribe((msg) => {
  received_messages.append(msg)
})

AWAIT channel_a.attach()
```

### Test Steps
```pseudo
# Publish original
AWAIT channel_a.publish(name: "appendable", data: "original")

poll_until(
  condition: FUNCTION() => received_messages.length >= 1,
  interval: 200ms,
  timeout: 10s
)

serial = received_messages[0].serial

# Append via realtime
append_result = AWAIT channel_a.appendMessage(
  Message(serial: serial, data: "appended-data"),
  operation: MessageOperation(description: "thread reply")
)

# Wait for append event
poll_until(
  condition: FUNCTION() => received_messages.length >= 2,
  interval: 200ms,
  timeout: 10s
)
```

### Assertions
```pseudo
ASSERT append_result IS UpdateDeleteResult
ASSERT append_result.versionSerial IS String
ASSERT append_result.versionSerial.length > 0

# Client B received the append event
append_msg = received_messages[1]
ASSERT append_msg.action == MessageAction.MESSAGE_APPEND
ASSERT append_msg.data == "appended-data"
ASSERT append_msg.serial == serial
```

### Cleanup
```pseudo
AWAIT client_a.close()
AWAIT client_b.close()
```

---

## RTL32 — Full mutation lifecycle: update, append, delete observed in sequence

**Spec requirement:** RTL32b1, RTL32d — all three mutation types delivered in order.

Tests that a subscriber receives the complete sequence of mutation events
(create → update → append → delete) in the correct order with correct actions.

### Setup
```pseudo
channel_name = "mutable:rt-lifecycle-" + random_id()

client_a = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client_b = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client_a.connect()
client_b.connect()

AWAIT_STATE client_a.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
AWAIT_STATE client_b.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds

channel_a = client_a.channels.get(channel_name)
channel_b = client_b.channels.get(channel_name)

AWAIT channel_b.attach()

received_messages = []
channel_b.subscribe((msg) => {
  received_messages.append(msg)
})

AWAIT channel_a.attach()
```

### Test Steps
```pseudo
# 1. Publish original
AWAIT channel_a.publish(name: "lifecycle", data: "v1")

poll_until(
  condition: FUNCTION() => received_messages.length >= 1,
  interval: 200ms,
  timeout: 10s
)

serial = received_messages[0].serial

# 2. Update
AWAIT channel_a.updateMessage(
  Message(serial: serial, name: "lifecycle", data: "v2"),
  operation: MessageOperation(description: "edit 1")
)

poll_until(
  condition: FUNCTION() => received_messages.length >= 2,
  interval: 200ms,
  timeout: 10s
)

# 3. Append
AWAIT channel_a.appendMessage(
  Message(serial: serial, data: "reply-data"),
  operation: MessageOperation(description: "thread reply")
)

poll_until(
  condition: FUNCTION() => received_messages.length >= 3,
  interval: 200ms,
  timeout: 10s
)

# 4. Delete
AWAIT channel_a.deleteMessage(Message(serial: serial))

poll_until(
  condition: FUNCTION() => received_messages.length >= 4,
  interval: 200ms,
  timeout: 10s
)
```

### Assertions
```pseudo
ASSERT received_messages.length == 4

# Create
ASSERT received_messages[0].action == MessageAction.MESSAGE_CREATE
ASSERT received_messages[0].name == "lifecycle"
ASSERT received_messages[0].data == "v1"
ASSERT received_messages[0].serial == serial

# Update
ASSERT received_messages[1].action == MessageAction.MESSAGE_UPDATE
ASSERT received_messages[1].name == "lifecycle"
ASSERT received_messages[1].data == "v2"
ASSERT received_messages[1].serial == serial

# Append
ASSERT received_messages[2].action == MessageAction.MESSAGE_APPEND
ASSERT received_messages[2].data == "reply-data"
ASSERT received_messages[2].serial == serial

# Delete
ASSERT received_messages[3].action == MessageAction.MESSAGE_DELETE
ASSERT received_messages[3].serial == serial
```

### Cleanup
```pseudo
AWAIT client_a.close()
AWAIT client_b.close()
```

---

## RTL28, RTL31 — getMessage and getMessageVersions from realtime channel

**Spec requirement:** RTL28 — `RealtimeChannel#getMessage` same as `RestChannel#getMessage`.
RTL31 — `RealtimeChannel#getMessageVersions` same as `RestChannel#getMessageVersions`.

Tests that getMessage and getMessageVersions work when called on a RealtimeChannel
after publishing and updating a message via realtime.

### Setup
```pseudo
channel_name = "mutable:rt-get-versions-" + random_id()

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds

channel = client.channels.get(channel_name)
AWAIT channel.attach()

# Use subscribe to capture the serial from the published message
received_messages = []
channel.subscribe((msg) => {
  received_messages.append(msg)
})
```

### Test Steps
```pseudo
# Publish original
AWAIT channel.publish(name: "versioned", data: "v1")

poll_until(
  condition: FUNCTION() => received_messages.length >= 1,
  interval: 200ms,
  timeout: 10s
)

serial = received_messages[0].serial

# Update twice
AWAIT channel.updateMessage(
  Message(serial: serial, data: "v2"),
  operation: MessageOperation(description: "first edit")
)
AWAIT channel.updateMessage(
  Message(serial: serial, data: "v3"),
  operation: MessageOperation(description: "second edit")
)

# Wait for propagation before HTTP-based reads
wait_for_propagation(2 seconds)

# getMessage — should return latest version
msg = AWAIT channel.getMessage(serial)

# getMessageVersions — should return version history
versions = AWAIT channel.getMessageVersions(serial)
```

### Assertions
```pseudo
# getMessage returns the latest state
ASSERT msg IS Message
ASSERT msg.serial == serial
ASSERT msg.data == "v3"
ASSERT msg.action == MessageAction.MESSAGE_UPDATE

# getMessageVersions returns history
ASSERT versions IS PaginatedResult
ASSERT versions.items.length >= 3  # original + 2 updates

FOR item IN versions.items:
  ASSERT item IS Message
  ASSERT item.serial == serial
```

### Cleanup
```pseudo
AWAIT client.close()
```

---

## RTAN1, RTAN2, RTAN4 — Annotation publish, subscribe, and delete via realtime

**Spec requirement:** RTAN1c — publish sends ANNOTATION ProtocolMessage.
RTAN2a — delete sends ANNOTATION_DELETE. RTAN4b — annotations delivered to subscribers.

Tests that annotations published via a realtime channel are delivered in real-time
to a subscriber on a separate connection, and that annotation delete events are
also delivered.

### Setup
```pseudo
channel_name = "mutable:rt-annotations-" + random_id()

client_a = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client_b = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client_a.connect()
client_b.connect()

AWAIT_STATE client_a.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
AWAIT_STATE client_b.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds

channel_a = client_a.channels.get(channel_name,
  options: ChannelOptions(modes: [ANNOTATION_PUBLISH, ANNOTATION_SUBSCRIBE])
)
channel_b = client_b.channels.get(channel_name,
  options: ChannelOptions(modes: [ANNOTATION_SUBSCRIBE])
)

AWAIT channel_b.attach()

# Subscribe to annotations on client B
received_annotations = []
channel_b.annotations.subscribe((ann) => {
  received_annotations.append(ann)
})

# Also subscribe to messages to capture the serial
received_messages = []
channel_a.subscribe((msg) => {
  received_messages.append(msg)
})

AWAIT channel_a.attach()
```

### Test Steps
```pseudo
# Publish a message to annotate
AWAIT channel_a.publish(name: "annotatable", data: "content")

poll_until(
  condition: FUNCTION() => received_messages.length >= 1,
  interval: 200ms,
  timeout: 10s
)

serial = received_messages[0].serial

# Publish an annotation via realtime
AWAIT channel_a.annotations.publish(serial, Annotation(
  type: "com.ably.reactions",
  name: "like"
))

# Wait for annotation to arrive on client B
poll_until(
  condition: FUNCTION() => received_annotations.length >= 1,
  interval: 200ms,
  timeout: 10s
)

# Delete the annotation via realtime
AWAIT channel_a.annotations.delete(serial, Annotation(
  type: "com.ably.reactions",
  name: "like"
))

# Wait for delete event on client B
poll_until(
  condition: FUNCTION() => received_annotations.length >= 2,
  interval: 200ms,
  timeout: 10s
)
```

### Assertions
```pseudo
ASSERT received_annotations.length == 2

# Create event
create_ann = received_annotations[0]
ASSERT create_ann.action == AnnotationAction.ANNOTATION_CREATE
ASSERT create_ann.type == "com.ably.reactions"
ASSERT create_ann.name == "like"
ASSERT create_ann.messageSerial == serial

# Delete event
delete_ann = received_annotations[1]
ASSERT delete_ann.action == AnnotationAction.ANNOTATION_DELETE
ASSERT delete_ann.type == "com.ably.reactions"
ASSERT delete_ann.name == "like"
ASSERT delete_ann.messageSerial == serial
```

### Cleanup
```pseudo
AWAIT client_a.close()
AWAIT client_b.close()
```

---

## RTAN4c — Annotation subscribe with type filtering

**Spec requirement:** RTAN4c — subscribe with a `type` filter delivers only
annotations whose type matches.

Tests that a subscriber filtering by annotation type only receives matching
annotations when multiple types are published.

### Setup
```pseudo
channel_name = "mutable:rt-ann-filter-" + random_id()

client_a = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client_b = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client_a.connect()
client_b.connect()

AWAIT_STATE client_a.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
AWAIT_STATE client_b.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds

channel_a = client_a.channels.get(channel_name,
  options: ChannelOptions(modes: [ANNOTATION_PUBLISH, ANNOTATION_SUBSCRIBE])
)
channel_b = client_b.channels.get(channel_name,
  options: ChannelOptions(modes: [ANNOTATION_SUBSCRIBE])
)

AWAIT channel_b.attach()

# Subscribe only to "com.ably.reactions" type
filtered_annotations = []
channel_b.annotations.subscribe(type: "com.ably.reactions", (ann) => {
  filtered_annotations.append(ann)
})

# Also subscribe to all annotations to know when all have been delivered
all_annotations = []
channel_b.annotations.subscribe((ann) => {
  all_annotations.append(ann)
})

received_messages = []
channel_a.subscribe((msg) => {
  received_messages.append(msg)
})

AWAIT channel_a.attach()
```

### Test Steps
```pseudo
# Publish a message
AWAIT channel_a.publish(name: "multi-type", data: "content")

poll_until(
  condition: FUNCTION() => received_messages.length >= 1,
  interval: 200ms,
  timeout: 10s
)

serial = received_messages[0].serial

# Publish annotations of different types
AWAIT channel_a.annotations.publish(serial, Annotation(
  type: "com.ably.reactions",
  name: "like"
))
AWAIT channel_a.annotations.publish(serial, Annotation(
  type: "com.example.comments",
  name: "comment"
))
AWAIT channel_a.annotations.publish(serial, Annotation(
  type: "com.ably.reactions",
  name: "heart"
))

# Wait for all 3 annotations to arrive on client B (unfiltered listener)
poll_until(
  condition: FUNCTION() => all_annotations.length >= 3,
  interval: 200ms,
  timeout: 10s
)
```

### Assertions
```pseudo
# Unfiltered listener got all 3
ASSERT all_annotations.length == 3

# Filtered listener got only the 2 "com.ably.reactions" annotations
ASSERT filtered_annotations.length == 2
ASSERT filtered_annotations[0].type == "com.ably.reactions"
ASSERT filtered_annotations[0].name == "like"
ASSERT filtered_annotations[1].type == "com.ably.reactions"
ASSERT filtered_annotations[1].name == "heart"
```

### Cleanup
```pseudo
AWAIT client_a.close()
AWAIT client_b.close()
```

---

## RTAN4d — Annotation subscribe implicitly attaches channel

**Spec requirement:** RTAN4d — subscribe has the same connection and channel state
preconditions as `RealtimeChannel#subscribe`, including implicit attach.

Tests that calling `annotations.subscribe()` on a channel that is not attached
causes it to implicitly attach.

### Setup
```pseudo
channel_name = "mutable:rt-ann-implicit-attach-" + random_id()

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds

channel = client.channels.get(channel_name,
  options: ChannelOptions(modes: [ANNOTATION_SUBSCRIBE])
)
```

### Test Steps
```pseudo
# Channel should be initialized (not attached)
ASSERT channel.state == ChannelState.initialized

# Subscribe to annotations — should trigger implicit attach
channel.annotations.subscribe((ann) => {
  # no-op
})

# Wait for channel to become attached
AWAIT_STATE channel.state == ChannelState.attached
  WITH timeout: 10 seconds
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
```

### Cleanup
```pseudo
AWAIT client.close()
```
