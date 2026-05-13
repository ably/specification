# LiveMap API Tests

Spec points: `RTLM5`, `RTLM10`–`RTLM13`, `RTLM20`–`RTLM21`, `RTLM24`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Shared Helpers

See `helpers/standard_test_pool.md` for `setup_synced_channel` and builder functions.

---

## RTLM5 - get() returns resolved value from LiveMap

**Test ID**: `objects/unit/RTLM5/get-string-value-0`

**Spec requirement:** Returns value at key, resolved per RTLM5d2.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.get("name").value() == "Alice"
ASSERT root.get("age").value() == 30
ASSERT root.get("active").value() == true
```

---

## RTLM5 - get() returns null for non-existent key

**Test ID**: `objects/unit/RTLM5/get-nonexistent-key-0`

**Spec requirement:** If no entry exists at key, return null.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.get("nonexistent").value() == null
```

---

## RTLM5 - get() resolves objectId to LiveObject

**Test ID**: `objects/unit/RTLM5/get-objectid-reference-0`

**Spec requirement:** If data.objectId exists, resolve from pool. Return LiveCounter/LiveMap.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 100
ASSERT root.get("profile").get("email").value() == "alice@example.com"
```

---

## RTLM10 - size() returns non-tombstoned entry count

**Test ID**: `objects/unit/RTLM10/size-non-tombstoned-0`

**Spec requirement:** Returns number of non-tombstoned entries.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.size() == 7
```

---

## RTLM11 - entries() yields key-value pairs

**Test ID**: `objects/unit/RTLM11/entries-yields-pairs-0`

**Spec requirement:** Returns non-tombstoned key-value pairs.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
entries = []
FOR [key, pathObj] IN root.entries():
  entries.append(key)
```

### Assertions
```pseudo
ASSERT "name" IN entries
ASSERT "age" IN entries
ASSERT "active" IN entries
ASSERT "score" IN entries
ASSERT "profile" IN entries
ASSERT "data" IN entries
ASSERT "avatar" IN entries
ASSERT entries.length == 7
```

---

## RTLM12 - keys() yields only keys

**Test ID**: `objects/unit/RTLM12/keys-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
keys = list(root.keys())
```

### Assertions
```pseudo
ASSERT keys.length == 7
ASSERT "name" IN keys
```

---

## RTLM20 - set() sends MAP_SET message with v6 format

**Test ID**: `objects/unit/RTLM20/set-sends-map-set-0`

| Spec | Requirement |
|------|-------------|
| RTLM20e2 | action set to MAP_SET |
| RTLM20e3 | objectId set to LiveMap's objectId |
| RTLM20e6 | mapSet.key set |
| RTLM20e7c | mapSet.value.string for string value |

### Setup
```pseudo
captured_messages = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionDetails: {
      connectionId: "conn-1", connectionKey: "key-1", siteCode: "test-site",
      objectsGCGracePeriod: 86400000
    })
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED, channel: msg.channel, channelSerial: "sync1:", flags: HAS_OBJECTS
      ))
      mock_ws.send_to_client(build_object_sync_message(msg.channel, "sync1:", STANDARD_POOL_OBJECTS))
    ELSE IF msg.action == OBJECT:
      captured_messages.append(msg)
      serials = msg.state.map((_, i) => "ack-" + msg.msgSerial + ":" + i)
      mock_ws.send_to_client(build_ack_message(msg.msgSerial, serials))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()
```

### Test Steps
```pseudo
AWAIT root.set("name", "Bob")
```

### Assertions
```pseudo
ASSERT captured_messages.length == 1
obj_msg = captured_messages[0].state[0]
ASSERT obj_msg.operation.action == "MAP_SET"
ASSERT obj_msg.operation.objectId == "root"
ASSERT obj_msg.operation.mapSet.key == "name"
ASSERT obj_msg.operation.mapSet.value.string == "Bob"
```

---

## RTLM20 - set() with different value types

**Test ID**: `objects/unit/RTLM20/set-value-types-0`

| Spec | Requirement |
|------|-------------|
| RTLM20e7b | JsonArray/JsonObject -> mapSet.value.json |
| RTLM20e7d | Number -> mapSet.value.number |
| RTLM20e7e | Boolean -> mapSet.value.boolean |

### Setup
```pseudo
captured_messages = []
// (same mock setup as above, capturing OBJECT messages)
```

### Test Steps
```pseudo
AWAIT root.set("num_key", 42)
AWAIT root.set("bool_key", false)
AWAIT root.set("json_key", {"nested": true})
```

### Assertions
```pseudo
ASSERT captured_messages[0].state[0].operation.mapSet.value.number == 42
ASSERT captured_messages[1].state[0].operation.mapSet.value.boolean == false
ASSERT captured_messages[2].state[0].operation.mapSet.value.json == {"nested": true}
```

---

## RTLM20e7g - set() with LiveCounterValueType consumes and sends create + set

**Test ID**: `objects/unit/RTLM20e7g/set-counter-value-type-0`

| Spec | Requirement |
|------|-------------|
| RTLM20e7g1 | Consume value type to generate COUNTER_CREATE |
| RTLM20e7g2 | Set mapSet.value.objectId to the created objectId |
| RTLM20h1 | Array: CREATE messages then MAP_SET |

### Setup
```pseudo
captured_messages = []
// (same mock setup as above)
```

### Test Steps
```pseudo
AWAIT root.set("new_counter", LiveCounter.create(50))
```

### Assertions
```pseudo
ASSERT captured_messages.length == 1
state = captured_messages[0].state
ASSERT state.length == 2
ASSERT state[0].operation.action == "COUNTER_CREATE"
ASSERT state[0].operation.objectId STARTS WITH "counter:"
ASSERT state[1].operation.action == "MAP_SET"
ASSERT state[1].operation.mapSet.value.objectId == state[0].operation.objectId
```

---

## RTLM21 - remove() sends MAP_REMOVE message

**Test ID**: `objects/unit/RTLM21/remove-sends-map-remove-0`

| Spec | Requirement |
|------|-------------|
| RTLM21e2 | action set to MAP_REMOVE |
| RTLM21e5 | mapRemove.key set |

### Setup
```pseudo
captured_messages = []
// (same mock setup as above)
```

### Test Steps
```pseudo
AWAIT root.remove("name")
```

### Assertions
```pseudo
obj_msg = captured_messages[0].state[0]
ASSERT obj_msg.operation.action == "MAP_REMOVE"
ASSERT obj_msg.operation.objectId == "root"
ASSERT obj_msg.operation.mapRemove.key == "name"
```

---

## RTLM20d - set() with echoMessages false throws

**Test ID**: `objects/unit/RTLM20d/echo-messages-false-0`

**Spec requirement:** If echoMessages is false, throw 40000.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionDetails: {
      connectionId: "conn-1", connectionKey: "key-1", siteCode: "test-site",
      objectsGCGracePeriod: 86400000
    })
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED, channel: msg.channel, channelSerial: "sync1:", flags: HAS_OBJECTS
      ))
      mock_ws.send_to_client(build_object_sync_message(msg.channel, "sync1:", STANDARD_POOL_OBJECTS))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key", echoMessages: false })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()
```

### Test Steps
```pseudo
AWAIT root.set("name", "Bob") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40000
```

---

## RTLM21d - remove() with echoMessages false throws

**Test ID**: `objects/unit/RTLM21d/echo-messages-false-0`

**Spec requirement:** Same as RTLM20d for remove.

### Setup
```pseudo
// Same echoMessages: false setup as above
```

### Test Steps
```pseudo
AWAIT root.remove("name") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40000
```

---

## RTLM20 - set() applies locally after ACK

**Test ID**: `objects/unit/RTLM20/set-applies-locally-0`

**Spec requirement:** Via publishAndApply, local state reflects change after await.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.set("name", "Bob")
```

### Assertions
```pseudo
ASSERT root.get("name").value() == "Bob"
```

---

## RTLM24 - clear() sends MAP_CLEAR message

**Test ID**: `objects/unit/RTLM24/clear-sends-map-clear-0`

**Spec requirement:** Constructs MAP_CLEAR ObjectMessage.

### Setup
```pseudo
captured_messages = []
// (same mock setup capturing OBJECT messages)
```

### Test Steps
```pseudo
instance = root.instance()
AWAIT instance.clear()
```

### Assertions
```pseudo
obj_msg = captured_messages[0].state[0]
ASSERT obj_msg.operation.action == "MAP_CLEAR"
ASSERT obj_msg.operation.objectId == "root"
```

---

## RTLM20 - Table-driven invalid set value types

**Test ID**: `objects/unit/RTLM20/set-invalid-values-table-0`

**Spec requirement:** set() rejects values of unsupported types with error 40013.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")

invalid_values = [
  { value: some_function,  label: "function" },
  { value: undefined,      label: "undefined" },
  { value: some_symbol,    label: "symbol" }
]
```

### Test Steps
```pseudo
FOR scenario IN invalid_values:
  AWAIT root.set("key", scenario.value) FAILS WITH error
  ASSERT error.code == 40013
```

---

## RTLM20 - set() with bytes value type

**Test ID**: `objects/unit/RTLM20/set-bytes-value-0`

| Spec | Requirement |
|------|-------------|
| RTLM20e7f | Binary -> mapSet.value.bytes (base64 encoded) |

### Setup
```pseudo
captured_messages = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionDetails: {
      connectionId: "conn-1", connectionKey: "key-1", siteCode: "test-site",
      objectsGCGracePeriod: 86400000
    })
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED, channel: msg.channel, channelSerial: "sync1:", flags: HAS_OBJECTS
      ))
      mock_ws.send_to_client(build_object_sync_message(msg.channel, "sync1:", STANDARD_POOL_OBJECTS))
    ELSE IF msg.action == OBJECT:
      captured_messages.append(msg)
      serials = msg.state.map((_, i) => "ack-" + msg.msgSerial + ":" + i)
      mock_ws.send_to_client(build_ack_message(msg.msgSerial, serials))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()
```

### Test Steps
```pseudo
AWAIT root.set("binary_data", bytes([1, 2, 3]))
```

### Assertions
```pseudo
ASSERT captured_messages[0].state[0].operation.mapSet.value.bytes == "AQID"
```
