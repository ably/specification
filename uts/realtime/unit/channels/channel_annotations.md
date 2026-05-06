# RealtimeChannel Annotations Tests

Spec points: `RTL26`, `RTAN1`, `RTAN1a`, `RTAN1b`, `RTAN1c`, `RTAN1d`, `RTAN2`, `RTAN2a`, `RTAN3`, `RTAN3a`, `RTAN4`, `RTAN4a`, `RTAN4b`, `RTAN4c`, `RTAN4d`, `RTAN4e`, `RTAN4e1`, `RTAN5`, `RTAN5a`

## Test Type
Unit test with mocked WebSocket

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTL26 — channel.annotations returns RealtimeAnnotations

**Test ID**: `realtime/unit/RTL26/annotations-attribute-type-0`

**Spec requirement:** RTL26 — `RealtimeChannel#annotations` attribute contains the `RealtimeAnnotations` object for this channel.

Tests that the channel exposes an `annotations` attribute of type `RealtimeAnnotations`.

### Setup
```pseudo
mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get("test-RTL26")
```

### Assertions
```pseudo
ASSERT channel.annotations IS RealtimeAnnotations
CLOSE_CLIENT(client)
```

---

## RTAN1a, RTAN1c — publish sends ANNOTATION ProtocolMessage with ANNOTATION_CREATE

**Test ID**: `realtime/unit/RTAN1a/publish-sends-annotation-0`

| Spec | Requirement |
|------|-------------|
| RTAN1a | Accepts same arguments and performs same validation, field setting, and data encoding as RSAN1 |
| RTAN1c | Must put annotation into array in `annotations` field of a `ProtocolMessage` with action `ANNOTATION`, channel set to channel name |

Tests that `annotations.publish()` sends a correctly formatted ANNOTATION ProtocolMessage.

### Setup
```pseudo
channel_name = "test-RTAN1-publish-${random_id()}"
captured_messages = []

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    captured_messages.append(msg)
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH | ANNOTATION_PUBLISH
      ))
    ELSE IF msg.action == ANNOTATION:
      mock_ws.active_connection.send_to_client(ACK(
        msgSerial: msg.msgSerial,
        count: 1
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

AWAIT channel.annotations.publish("msg-serial-1", Annotation(
  type: "com.example.reaction",
  name: "like"
))
```

### Assertions
```pseudo
annotation_pm = null
FOR pm IN captured_messages:
  IF pm.action == ANNOTATION:
    annotation_pm = pm
ASSERT annotation_pm IS NOT null

ASSERT annotation_pm.channel == channel_name
ASSERT annotation_pm.annotations.length == 1

ann = annotation_pm.annotations[0]
ASSERT ann.action == AnnotationAction.ANNOTATION_CREATE  # numeric: 0
ASSERT ann.messageSerial == "msg-serial-1"
ASSERT ann.type == "com.example.reaction"
ASSERT ann.name == "like"
CLOSE_CLIENT(client)
```

---

## RTAN1a — publish validates type is required

**Test ID**: `realtime/unit/RTAN1a/validates-type-required-1`

**Spec requirement:** RTAN1a — Performs the same validation as RSAN1. Per RSAN1a3, the `type` field is required.

Tests that publishing an annotation without a `type` field throws an error.

### Setup
```pseudo
channel_name = "test-RTAN1a-validate-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH | ANNOTATION_PUBLISH
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps and Assertions
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

AWAIT channel.annotations.publish("msg-serial-1", Annotation(
  name: "like"
)) FAILS WITH error
ASSERT error IS NOT null  # Error code is implementation-defined; RSAN1a3 does not mandate a specific code
CLOSE_CLIENT(client)
```

---

## RTAN1a — publish encodes data per RSL4

**Test ID**: `realtime/unit/RTAN1a/encodes-data-json-2`

**Spec requirement:** RTAN1a — Performs the same data encoding as RSAN1. Per RSAN1c3, data must be encoded per RSL4.

Tests that JSON data in an annotation is encoded following message encoding rules.

### Setup
```pseudo
channel_name = "test-RTAN1a-encode-${random_id()}"
captured_messages = []

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    captured_messages.append(msg)
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH | ANNOTATION_PUBLISH
      ))
    ELSE IF msg.action == ANNOTATION:
      mock_ws.active_connection.send_to_client(ACK(
        msgSerial: msg.msgSerial,
        count: 1
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

AWAIT channel.annotations.publish("msg-serial-1", Annotation(
  type: "com.example.data",
  data: { "key": "value", "nested": { "a": 1 } }
))
```

### Assertions
```pseudo
annotation_pm = null
FOR pm IN captured_messages:
  IF pm.action == ANNOTATION:
    annotation_pm = pm
ASSERT annotation_pm IS NOT null

ann = annotation_pm.annotations[0]
ASSERT ann.data IS String
ASSERT ann.encoding == "json"
ASSERT parse_json(ann.data) == { "key": "value", "nested": { "a": 1 } }
CLOSE_CLIENT(client)
```

---

## RTAN1b — publish has same connection and channel state conditions as message publishing

**Test ID**: `realtime/unit/RTAN1b/publish-channel-state-0`

**Spec requirement:** RTAN1b — Has the same connection and channel state conditions as message publishing, see RTL6c.

Tests that annotation publish fails in FAILED and SUSPENDED channel states, matching the behaviour tested in `uts/test/realtime/unit/channels/channel_publish.md` (RTL6c4). The same connection and channel state preconditions apply.

### Setup
```pseudo
channel_name = "test-RTAN1b-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Send ERROR to put channel in FAILED state
      mock_ws.active_connection.send_to_client(ProtocolMessage(
        action: ERROR,
        channel: channel_name,
        error: ErrorInfo(code: 40160, message: "Not permitted")
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps and Assertions
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED

# Attempt attach — will fail, putting channel in FAILED
TRY:
  AWAIT channel.attach()
CATCH:
  # Expected — channel is now FAILED

ASSERT channel.state == FAILED

AWAIT channel.annotations.publish("msg-serial-1", Annotation(
  type: "com.example.reaction",
  name: "like"
)) FAILS WITH error
ASSERT error IS NOT null
CLOSE_CLIENT(client)
```

---

## RTAN1d — publish indicates success/failure via ACK/NACK

**Test ID**: `realtime/unit/RTAN1d/publish-ack-nack-0`

**Spec requirement:** RTAN1d — Must indicate success or failure of the publish (once ACKed or NACKed) in the same way as `RealtimeChannel#publish`.

Tests that the publish resolves on ACK and rejects on NACK.

### Setup (ACK case)
```pseudo
channel_name = "test-RTAN1d-ack-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH | ANNOTATION_PUBLISH
      ))
    ELSE IF msg.action == ANNOTATION:
      mock_ws.active_connection.send_to_client(ACK(
        msgSerial: msg.msgSerial,
        count: 1
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps (ACK)
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

# Should resolve without error
AWAIT channel.annotations.publish("msg-serial-1", Annotation(
  type: "com.example.reaction",
  name: "like"
))
# If we get here, publish succeeded (no assertion needed beyond no throw)
CLOSE_CLIENT(client)
```

### Setup (NACK case)
```pseudo
channel_name = "test-RTAN1d-nack-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH | ANNOTATION_PUBLISH
      ))
    ELSE IF msg.action == ANNOTATION:
      mock_ws.active_connection.send_to_client(NACK(
        msgSerial: msg.msgSerial,
        count: 1,
        error: ErrorInfo(code: 40160, message: "Not permitted")
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps and Assertions (NACK)
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

AWAIT channel.annotations.publish("msg-serial-1", Annotation(
  type: "com.example.reaction",
  name: "like"
)) FAILS WITH error
ASSERT error.code == 40160
CLOSE_CLIENT(client)
```

---

## RTAN2a — delete sends ANNOTATION ProtocolMessage with ANNOTATION_DELETE

**Test ID**: `realtime/unit/RTAN2a/delete-sends-annotation-0`

**Spec requirement:** RTAN2a — Must be identical to RTAN1 `publish()` except that the `Annotation.action` is set to `ANNOTATION_DELETE`, not `ANNOTATION_CREATE`.

Tests that `annotations.delete()` sends ANNOTATION_DELETE.

### Setup
```pseudo
channel_name = "test-RTAN2-delete-${random_id()}"
captured_messages = []

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    captured_messages.append(msg)
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH | ANNOTATION_PUBLISH
      ))
    ELSE IF msg.action == ANNOTATION:
      mock_ws.active_connection.send_to_client(ACK(
        msgSerial: msg.msgSerial,
        count: 1
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

AWAIT channel.annotations.delete("msg-serial-1", Annotation(
  type: "com.example.reaction",
  name: "like"
))
```

### Assertions
```pseudo
annotation_pm = null
FOR pm IN captured_messages:
  IF pm.action == ANNOTATION:
    annotation_pm = pm
ASSERT annotation_pm IS NOT null

ann = annotation_pm.annotations[0]
ASSERT ann.action == AnnotationAction.ANNOTATION_DELETE  # numeric: 1
ASSERT ann.messageSerial == "msg-serial-1"
ASSERT ann.type == "com.example.reaction"
ASSERT ann.name == "like"
CLOSE_CLIENT(client)
```

---

## RTAN3a — get is identical to RestAnnotations#get

**Spec requirement:** RTAN3a — Is identical to `RestAnnotations#get`.

`RealtimeAnnotations#get` uses the same underlying REST endpoint as `RestAnnotations#get`. The tests in `uts/test/rest/unit/channel/annotations.md` (covering RSAN3) should be used to verify that all the same behaviour, parameters, and return types apply when called on a `RealtimeChannel` instance.

---

## RTAN4a, RTAN4b — subscribe delivers annotations from ANNOTATION ProtocolMessage

**Test ID**: `realtime/unit/RTAN4a/subscribe-delivers-annotations-0`

| Spec | Requirement |
|------|-------------|
| RTAN4a | Should support the same set of type signatures as `RealtimeChannel#subscribe` (RTL7), except `name` is called `type` |
| RTAN4b | When the library receives a `ProtocolMessage` with action `ANNOTATION`, every member of the `annotations` array should be delivered to registered listeners |

Tests that subscribing to annotations delivers decoded Annotation objects when an ANNOTATION ProtocolMessage is received.

### Setup
```pseudo
channel_name = "test-RTAN4-subscribe-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH | ANNOTATION_PUBLISH | ANNOTATION_SUBSCRIBE
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name, RealtimeChannelOptions(
  attachOnSubscribe: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

received_annotations = []
channel.annotations.subscribe((annotation) => {
  received_annotations.append(annotation)
})

# Server sends ANNOTATION ProtocolMessage with two annotations
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ANNOTATION,
  channel: channel_name,
  annotations: [
    {
      "id": "ann-1",
      "action": 0,
      "type": "com.example.reaction",
      "name": "like",
      "clientId": "user-1",
      "serial": "ann-serial-1",
      "messageSerial": "msg-serial-1",
      "timestamp": 1700000000000
    },
    {
      "id": "ann-2",
      "action": 0,
      "type": "com.example.reaction",
      "name": "heart",
      "clientId": "user-2",
      "serial": "ann-serial-2",
      "messageSerial": "msg-serial-1",
      "timestamp": 1700000001000
    }
  ]
))
```

### Assertions
```pseudo
ASSERT received_annotations.length == 2

ann1 = received_annotations[0]
ASSERT ann1 IS Annotation
ASSERT ann1.id == "ann-1"
ASSERT ann1.action == AnnotationAction.ANNOTATION_CREATE
ASSERT ann1.type == "com.example.reaction"
ASSERT ann1.name == "like"
ASSERT ann1.clientId == "user-1"
ASSERT ann1.serial == "ann-serial-1"
ASSERT ann1.messageSerial == "msg-serial-1"
ASSERT ann1.timestamp == 1700000000000

ann2 = received_annotations[1]
ASSERT ann2.name == "heart"
ASSERT ann2.clientId == "user-2"
CLOSE_CLIENT(client)
```

---

## RTAN4c — subscribe with type filter delivers only matching annotations

**Test ID**: `realtime/unit/RTAN4c/subscribe-type-filter-0`

**Spec requirement:** RTAN4c — If the user subscribes with a `type` (or array of types), the SDK must deliver only annotations whose `type` field exactly equals the requested type.

Tests that type-filtered subscription only delivers matching annotations.

### Setup
```pseudo
channel_name = "test-RTAN4c-filter-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH | ANNOTATION_PUBLISH | ANNOTATION_SUBSCRIBE
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name, RealtimeChannelOptions(
  attachOnSubscribe: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

reaction_annotations = []
channel.annotations.subscribe(
  type: "com.example.reaction",
  listener: (annotation) => {
    reaction_annotations.append(annotation)
  }
)

# Server sends mixed annotation types
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ANNOTATION,
  channel: channel_name,
  annotations: [
    {
      "action": 0,
      "type": "com.example.reaction",
      "name": "like",
      "messageSerial": "msg-serial-1",
      "serial": "ann-serial-1",
      "timestamp": 1700000000000
    },
    {
      "action": 0,
      "type": "com.example.comment",
      "name": "text",
      "messageSerial": "msg-serial-1",
      "serial": "ann-serial-2",
      "timestamp": 1700000001000
    },
    {
      "action": 0,
      "type": "com.example.reaction",
      "name": "heart",
      "messageSerial": "msg-serial-1",
      "serial": "ann-serial-3",
      "timestamp": 1700000002000
    }
  ]
))
```

### Assertions
```pseudo
# Only reaction annotations delivered
ASSERT reaction_annotations.length == 2
ASSERT reaction_annotations[0].name == "like"
ASSERT reaction_annotations[1].name == "heart"
CLOSE_CLIENT(client)
```

---

## RTAN4d — subscribe implicitly attaches channel

**Test ID**: `realtime/unit/RTAN4d/subscribe-implicit-attach-0`

**Spec requirement:** RTAN4d — Has the same connection and channel state preconditions and return value as `RealtimeChannel#subscribe`, including implicitly attaching unless the user requests otherwise per RTL7g/RTL7h.

Tests that subscribing to annotations triggers an implicit attach from INITIALIZED state when `attachOnSubscribe` is true (the default).

### Setup
```pseudo
channel_name = "test-RTAN4d-attach-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH | ANNOTATION_PUBLISH | ANNOTATION_SUBSCRIBE
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
# Default attachOnSubscribe is true
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED

ASSERT channel.state == INITIALIZED

channel.annotations.subscribe((annotation) => {})

# Wait for implicit attach to complete
AWAIT_STATE channel.state == ATTACHED
```

### Assertions
```pseudo
ASSERT channel.state == ATTACHED
CLOSE_CLIENT(client)
```

---

## RTAN4e — subscribe warns when ANNOTATION_SUBSCRIBE mode not granted

**Test ID**: `realtime/unit/RTAN4e/subscribe-warns-no-mode-0`

**Spec requirement:** RTAN4e — Once the channel is in the attached state, the channel modes are checked for the presence of the `ANNOTATION_SUBSCRIBE` mode. If missing, the library should log a warning.

Tests that a warning is logged when the channel is attached without ANNOTATION_SUBSCRIBE mode.

### Setup
```pseudo
channel_name = "test-RTAN4e-warn-${random_id()}"
log_messages = []

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Respond with ATTACHED but WITHOUT ANNOTATION_SUBSCRIBE flag
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH
      ))
  }
)

client = Realtime(
  options: ClientOptions(
    key: "appId.keyId:keySecret",
    autoConnect: false,
    logHandler: (level, message) => {
      IF level == WARN:
        log_messages.append(message)
    }
  ),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name, RealtimeChannelOptions(
  attachOnSubscribe: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

channel.annotations.subscribe((annotation) => {})
```

### Assertions
```pseudo
# A warning should have been logged about ANNOTATION_SUBSCRIBE mode
ASSERT log_messages.length >= 1
found_warning = false
FOR msg IN log_messages:
  IF msg CONTAINS "ANNOTATION_SUBSCRIBE":
    found_warning = true
ASSERT found_warning == true
CLOSE_CLIENT(client)
```

---

## RTAN4e1 — subscribe does not warn when not attached and attachOnSubscribe is false

**Test ID**: `realtime/unit/RTAN4e1/no-warn-unattached-0`

**Spec requirement:** RTAN4e1 — This check does not apply if `attachOnSubscribe` has been set to `false` and the channel is not attached.

Tests that no ANNOTATION_SUBSCRIBE warning is emitted when the channel is not attached and attachOnSubscribe is false.

### Setup
```pseudo
channel_name = "test-RTAN4e1-${random_id()}"
log_messages = []

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  }
)

client = Realtime(
  options: ClientOptions(
    key: "appId.keyId:keySecret",
    autoConnect: false,
    logHandler: (level, message) => {
      IF level == WARN:
        log_messages.append(message)
    }
  ),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name, RealtimeChannelOptions(
  attachOnSubscribe: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED

# Channel is INITIALIZED, not attached
ASSERT channel.state == INITIALIZED

channel.annotations.subscribe((annotation) => {})
```

### Assertions
```pseudo
# No warning about ANNOTATION_SUBSCRIBE should be logged
found_warning = false
FOR msg IN log_messages:
  IF msg CONTAINS "ANNOTATION_SUBSCRIBE":
    found_warning = true
ASSERT found_warning == false
CLOSE_CLIENT(client)
```

---

## RTAN5a — unsubscribe removes listeners

**Test ID**: `realtime/unit/RTAN5a/unsubscribe-removes-listeners-0`

**Spec requirement:** RTAN5a — Should support the same set of type signatures as `RealtimeChannel#unsubscribe` (RTL8), except that the `name` argument is called `type`.

Tests that unsubscribing removes annotation listeners.

### Setup
```pseudo
channel_name = "test-RTAN5-unsub-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH | ANNOTATION_PUBLISH | ANNOTATION_SUBSCRIBE
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name, RealtimeChannelOptions(
  attachOnSubscribe: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

received_annotations = []
listener = (annotation) => {
  received_annotations.append(annotation)
}
channel.annotations.subscribe(listener)

# Send first annotation — should be received
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ANNOTATION,
  channel: channel_name,
  annotations: [
    {
      "action": 0,
      "type": "com.example.reaction",
      "name": "like",
      "messageSerial": "msg-serial-1",
      "serial": "ann-serial-1",
      "timestamp": 1700000000000
    }
  ]
))

ASSERT received_annotations.length == 1

# Unsubscribe
channel.annotations.unsubscribe(listener)

# Send second annotation — should NOT be received
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ANNOTATION,
  channel: channel_name,
  annotations: [
    {
      "action": 0,
      "type": "com.example.reaction",
      "name": "heart",
      "messageSerial": "msg-serial-1",
      "serial": "ann-serial-2",
      "timestamp": 1700000001000
    }
  ]
))
```

### Assertions
```pseudo
# Only the first annotation was received
ASSERT received_annotations.length == 1
ASSERT received_annotations[0].name == "like"
CLOSE_CLIENT(client)
```

---

## RTAN5a — unsubscribe with type removes only type-filtered listener

**Test ID**: `realtime/unit/RTAN5a/unsubscribe-type-filter-1`

Tests that unsubscribing with a type filter only removes that specific type's listener.

### Setup
```pseudo
channel_name = "test-RTAN5a-typed-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        flags: PUBLISH | ANNOTATION_PUBLISH | ANNOTATION_SUBSCRIBE
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)
channel = client.channels.get(channel_name, RealtimeChannelOptions(
  attachOnSubscribe: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()

reaction_received = []
comment_received = []

reaction_listener = (ann) => { reaction_received.append(ann) }
comment_listener = (ann) => { comment_received.append(ann) }

channel.annotations.subscribe(type: "com.example.reaction", listener: reaction_listener)
channel.annotations.subscribe(type: "com.example.comment", listener: comment_listener)

# Unsubscribe only reactions
channel.annotations.unsubscribe(type: "com.example.reaction", listener: reaction_listener)

# Send both types
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ANNOTATION,
  channel: channel_name,
  annotations: [
    {
      "action": 0,
      "type": "com.example.reaction",
      "name": "like",
      "messageSerial": "msg-serial-1",
      "serial": "ann-serial-1",
      "timestamp": 1700000000000
    },
    {
      "action": 0,
      "type": "com.example.comment",
      "name": "text",
      "messageSerial": "msg-serial-1",
      "serial": "ann-serial-2",
      "timestamp": 1700000001000
    }
  ]
))
```

### Assertions
```pseudo
# Reactions unsubscribed, comments still active
ASSERT reaction_received.length == 0
ASSERT comment_received.length == 1
ASSERT comment_received[0].type == "com.example.comment"
CLOSE_CLIENT(client)
```
