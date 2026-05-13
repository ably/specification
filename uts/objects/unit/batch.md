# Batch API Tests

Spec points: `RTPO22`, `RTINS19`, `RTBC1`–`RTBC16`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Shared Helpers

See `helpers/standard_test_pool.md` for `setup_synced_channel` and builder functions.

---

## RTPO22 - PathObject#batch resolves path and executes fn

**Test ID**: `objects/unit/RTPO22/batch-resolves-and-executes-0`

| Spec | Requirement |
|------|-------------|
| RTPO22c | Resolves path to LiveObject |
| RTPO22d | Creates RootBatchContext wrapping Instance |
| RTPO22e | Executes fn with BatchContext |
| RTPO22f | Flushes after fn returns |

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
AWAIT root.batch((ctx) => {
  ctx.set("name", "Bob")
  ctx.set("age", 31)
})
```

### Assertions
```pseudo
ASSERT captured_messages.length == 1
ASSERT captured_messages[0].state.length == 2
ASSERT captured_messages[0].state[0].operation.action == "MAP_SET"
ASSERT captured_messages[0].state[0].operation.mapSet.key == "name"
ASSERT captured_messages[0].state[1].operation.action == "MAP_SET"
ASSERT captured_messages[0].state[1].operation.mapSet.key == "age"
```

---

## RTPO22c - PathObject#batch on unresolvable path throws 92007

**Test ID**: `objects/unit/RTPO22c/batch-unresolvable-throws-0`

**Spec requirement:** If path does not resolve to LiveObject, throw 92007.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.get("nonexistent").get("deep").batch((ctx) => {}) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92007
```

---

## RTINS19 - Instance#batch resolves and executes fn

**Test ID**: `objects/unit/RTINS19/batch-instance-executes-0`

| Spec | Requirement |
|------|-------------|
| RTINS19d | Creates RootBatchContext wrapping Instance |
| RTINS19e | Executes fn with BatchContext |
| RTINS19f | Flushes after fn returns |

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
instance = root.instance()
AWAIT instance.batch((ctx) => {
  ctx.set("name", "Charlie")
  ctx.remove("age")
})
```

### Assertions
```pseudo
ASSERT captured_messages.length == 1
ASSERT captured_messages[0].state.length == 2
ASSERT captured_messages[0].state[0].operation.action == "MAP_SET"
ASSERT captured_messages[0].state[1].operation.action == "MAP_REMOVE"
```

---

## RTINS19c - Instance#batch on non-LiveObject throws 92007

**Test ID**: `objects/unit/RTINS19c/batch-non-live-object-throws-0`

**Spec requirement:** If wrapped value is not a LiveObject, throw 92007.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
name_inst = root.instance().get("name")
AWAIT name_inst.batch((ctx) => {}) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92007
```

---

## RTBC3 - BatchContext#id returns objectId

**Test ID**: `objects/unit/RTBC3/id-returns-objectid-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
received_id = null
AWAIT root.batch((ctx) => {
  received_id = ctx.id()
})
```

### Assertions
```pseudo
ASSERT received_id == "root"
```

---

## RTBC5 - BatchContext#value delegates to Instance#value

**Test ID**: `objects/unit/RTBC5/value-delegates-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
received_value = null
AWAIT root.get("score").batch((ctx) => {
  received_value = ctx.value()
})
```

### Assertions
```pseudo
ASSERT received_value == 100
```

---

## RTBC4 - BatchContext#get wraps result via wrapInstance

**Test ID**: `objects/unit/RTBC4/get-wraps-instance-0`

| Spec | Requirement |
|------|-------------|
| RTBC4c | Delegates to Instance#get |
| RTBC4d | Wraps result via RootBatchContext#wrapInstance |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
child_id = null
AWAIT root.batch((ctx) => {
  child = ctx.get("score")
  child_id = child.id()
})
```

### Assertions
```pseudo
ASSERT child_id == "counter:score@1000"
```

---

## RTBC4 - BatchContext#get returns null for nonexistent key

**Test ID**: `objects/unit/RTBC4/get-null-nonexistent-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
result = "not_null"
AWAIT root.batch((ctx) => {
  result = ctx.get("nonexistent")
})
```

### Assertions
```pseudo
ASSERT result == null
```

---

## RTBC6 - BatchContext#entries yields [key, BatchContext] pairs

**Test ID**: `objects/unit/RTBC6/entries-yields-pairs-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
keys = []
AWAIT root.batch((ctx) => {
  FOR [key, child] IN ctx.entries():
    keys.append(key)
})
```

### Assertions
```pseudo
ASSERT keys.length == 6
ASSERT "name" IN keys
ASSERT "score" IN keys
```

---

## RTBC9 - BatchContext#size delegates to Instance#size

**Test ID**: `objects/unit/RTBC9/size-delegates-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
received_size = null
AWAIT root.batch((ctx) => {
  received_size = ctx.size()
})
```

### Assertions
```pseudo
ASSERT received_size == 6
```

---

## RTBC10 - BatchContext#compact delegates to Instance#compact

**Test ID**: `objects/unit/RTBC10/compact-delegates-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
result = null
AWAIT root.batch((ctx) => {
  result = ctx.compact()
})
```

### Assertions
```pseudo
ASSERT result["name"] == "Alice"
ASSERT result["score"] == 100
```

---

## RTBC12 - BatchContext#set queues MAP_SET message

**Test ID**: `objects/unit/RTBC12/set-queues-map-set-0`

| Spec | Requirement |
|------|-------------|
| RTBC12d | Queues message constructor for MAP_SET |

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
AWAIT root.batch((ctx) => {
  ctx.set("name", "Bob")
})
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

## RTBC12c - BatchContext#set on non-LiveMap throws 92007

**Test ID**: `objects/unit/RTBC12c/set-non-map-throws-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.get("score").batch((ctx) => {
  ctx.set("key", "value")
}) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92007
```

---

## RTBC13 - BatchContext#remove queues MAP_REMOVE message

**Test ID**: `objects/unit/RTBC13/remove-queues-map-remove-0`

### Setup
```pseudo
captured_messages = []
// (same mock setup as RTPO22, capturing OBJECT messages)
```

### Test Steps
```pseudo
AWAIT root.batch((ctx) => {
  ctx.remove("name")
})
```

### Assertions
```pseudo
ASSERT captured_messages.length == 1
obj_msg = captured_messages[0].state[0]
ASSERT obj_msg.operation.action == "MAP_REMOVE"
ASSERT obj_msg.operation.objectId == "root"
ASSERT obj_msg.operation.mapRemove.key == "name"
```

---

## RTBC14 - BatchContext#increment queues COUNTER_INC message

**Test ID**: `objects/unit/RTBC14/increment-queues-counter-inc-0`

### Setup
```pseudo
captured_messages = []
// (same mock setup as RTPO22, capturing OBJECT messages)
```

### Test Steps
```pseudo
AWAIT root.get("score").batch((ctx) => {
  ctx.increment(25)
})
```

### Assertions
```pseudo
ASSERT captured_messages.length == 1
obj_msg = captured_messages[0].state[0]
ASSERT obj_msg.operation.action == "COUNTER_INC"
ASSERT obj_msg.operation.objectId == "counter:score@1000"
ASSERT obj_msg.operation.counterInc.number == 25
```

---

## RTBC14c - BatchContext#increment on non-LiveCounter throws 92007

**Test ID**: `objects/unit/RTBC14c/increment-non-counter-throws-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.batch((ctx) => {
  ctx.increment(5)
}) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92007
```

---

## RTBC15 - BatchContext#decrement delegates to increment with negated amount

**Test ID**: `objects/unit/RTBC15/decrement-negates-0`

### Setup
```pseudo
captured_messages = []
// (same mock setup as RTPO22, capturing OBJECT messages)
```

### Test Steps
```pseudo
AWAIT root.get("score").batch((ctx) => {
  ctx.decrement(10)
})
```

### Assertions
```pseudo
ASSERT captured_messages.length == 1
obj_msg = captured_messages[0].state[0]
ASSERT obj_msg.operation.action == "COUNTER_INC"
ASSERT obj_msg.operation.counterInc.number == -10
```

---

## RTBC16c - wrapInstance memoizes by objectId

**Test ID**: `objects/unit/RTBC16c/wrap-instance-memoized-0`

**Spec requirement:** If a wrapper for that objectId already exists, the existing wrapper is returned.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
same_ref = false
AWAIT root.batch((ctx) => {
  child1 = ctx.get("score")
  child2 = ctx.get("score")
  same_ref = (child1 IS child2)
})
```

### Assertions
```pseudo
ASSERT same_ref == true
```

---

## RTBC16d - flush publishes via RTO15 (publish, not publishAndApply)

**Test ID**: `objects/unit/RTBC16d/flush-uses-publish-0`

**Spec requirement:** Flushes queued messages as a single array via RealtimeObject#publish.

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
AWAIT root.batch((ctx) => {
  ctx.set("name", "Bob")
  ctx.set("age", 31)
  child = ctx.get("score")
  child.increment(50)
})
```

### Assertions
```pseudo
// All operations published as a single OBJECT message
ASSERT captured_messages.length == 1
ASSERT captured_messages[0].state.length == 3
ASSERT captured_messages[0].state[0].operation.action == "MAP_SET"
ASSERT captured_messages[0].state[1].operation.action == "MAP_SET"
ASSERT captured_messages[0].state[2].operation.action == "COUNTER_INC"
```

---

## RTBC16d - flush with no queued messages does not publish

**Test ID**: `objects/unit/RTBC16d/flush-empty-no-publish-0`

**Spec requirement:** If there are no queued messages, no publish is performed.

### Setup
```pseudo
captured_messages = []
// (same mock setup as RTPO22, capturing OBJECT messages)
```

### Test Steps
```pseudo
AWAIT root.batch((ctx) => {
  // Read-only: no writes queued
  ctx.value()
  ctx.size()
})
```

### Assertions
```pseudo
ASSERT captured_messages.length == 0
```

---

## RTBC16e - closed batch throws 40000 on any method call

**Test ID**: `objects/unit/RTBC16e/closed-batch-throws-0`

**Spec requirement:** After the batch is closed, any method call must throw 40000.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
saved_ctx = null
```

### Test Steps
```pseudo
AWAIT root.batch((ctx) => {
  saved_ctx = ctx
})

saved_ctx.set("name", "Bob") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40000
```

---

## RTBC16e - closed batch read methods also throw 40000

**Test ID**: `objects/unit/RTBC16e/closed-batch-read-throws-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
saved_ctx = null
```

### Test Steps
```pseudo
AWAIT root.batch((ctx) => {
  saved_ctx = ctx
})

saved_ctx.id() FAILS WITH error_id
saved_ctx.value() FAILS WITH error_value
saved_ctx.size() FAILS WITH error_size
```

### Assertions
```pseudo
ASSERT error_id.code == 40000
ASSERT error_value.code == 40000
ASSERT error_size.code == 40000
```

---

## RTPO22g - RootBatchContext closed after flush regardless of success

**Test ID**: `objects/unit/RTPO22g/closed-after-flush-0`

**Spec requirement:** The RootBatchContext is closed after flush completes, regardless of success or failure.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
saved_ctx = null
```

### Test Steps
```pseudo
AWAIT root.batch((ctx) => {
  saved_ctx = ctx
  ctx.set("name", "Bob")
})

saved_ctx.set("age", 99) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40000
```

---

## RTPO22b - PathObject#batch requires OBJECT_PUBLISH mode

**Test ID**: `objects/unit/RTPO22b/batch-requires-publish-mode-0`

**Spec requirement:** Requires OBJECT_PUBLISH channel mode per RTO2.

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
        action: ATTACHED, channel: msg.channel, channelSerial: "sync1:",
        flags: HAS_OBJECTS, modes: ["OBJECT_SUBSCRIBE"]
      ))
      mock_ws.send_to_client(build_object_sync_message(msg.channel, "sync1:", STANDARD_POOL_OBJECTS))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()
```

### Test Steps
```pseudo
AWAIT root.batch((ctx) => {
  ctx.set("name", "Bob")
}) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40024
```
