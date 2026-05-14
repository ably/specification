# LiveCounter API Tests

Spec points: `RTLC5`, `RTLC11`–`RTLC13`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Shared Helpers

See `helpers/standard_test_pool.md` for `setup_synced_channel` and builder functions.

---

## RTLC5 - value() returns current counter data

**Test ID**: `objects/unit/RTLC5/value-returns-data-0`

| Spec | Requirement |
|------|-------------|
| RTLC5c | Returns current data value |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
counter = root.get("score")
ASSERT counter.value() == 100
```

---

## RTLC5a - value() requires OBJECT_SUBSCRIBE mode

**Test ID**: `objects/unit/RTLC5a/value-requires-subscribe-0`

**Spec requirement:** Requires OBJECT_SUBSCRIBE channel mode per RTO2.

This is implicitly tested by `setup_synced_channel` which always includes OBJECT_SUBSCRIBE. A negative test would use a channel without OBJECT_SUBSCRIBE and verify the error.

---

## RTLC12 - increment sends v6 COUNTER_INC message

**Test ID**: `objects/unit/RTLC12/increment-sends-counter-inc-0`

| Spec | Requirement |
|------|-------------|
| RTLC12e2 | action set to COUNTER_INC |
| RTLC12e3 | objectId set to counter's objectId |
| RTLC12e5 | counterInc.number set to amount |
| RTLC12g | Publishes via publishAndApply |

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
AWAIT root.increment(25)
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

## RTLC12 - increment applies locally after ACK

**Test ID**: `objects/unit/RTLC12/increment-applies-locally-0`

**Spec requirement:** Via publishAndApply, value reflects change after await.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.increment(50)
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 150
```

---

## RTLC12b - increment requires OBJECT_PUBLISH mode

**Test ID**: `objects/unit/RTLC12b/increment-requires-publish-0`

**Spec requirement:** Requires OBJECT_PUBLISH channel mode.

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
AWAIT root.increment(10) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40024
```

---

## RTLC12d - increment with echoMessages false throws

**Test ID**: `objects/unit/RTLC12d/echo-messages-false-0`

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
        action: ATTACHED, channel: msg.channel, channelSerial: "sync1:",
        flags: HAS_OBJECTS
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
AWAIT root.increment(10) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40000
```

---

## RTLC12e1 - increment with non-number throws

**Test ID**: `objects/unit/RTLC12e1/increment-non-number-0`

**Spec requirement:** If amount is null, not Number, not finite, or omitted, throw 40003.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.increment("not_a_number") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40003
```

---

## RTLC13 - decrement delegates to increment with negated amount

**Test ID**: `objects/unit/RTLC13/decrement-negates-0`

| Spec | Requirement |
|------|-------------|
| RTLC13b | Alias for increment with negative amount |

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
AWAIT root.decrement(15)
```

### Assertions
```pseudo
ASSERT captured_messages[0].state[0].operation.counterInc.number == -15
ASSERT root.get("score").value() == 85
```

---

## RTLC11 - LiveCounterUpdate emitted on increment

**Test ID**: `objects/unit/RTLC11/counter-update-on-inc-0`

| Spec | Requirement |
|------|-------------|
| RTLC11b1 | update.amount is the increment value |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")

updates = []
instance = root.get("score").instance()
instance.subscribe((event) => updates.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "99", "remote-site")
]))

poll_until(updates.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT updates[0].message.operation.counterInc.number == 7
```

---

## RTLC12e1 - Table-driven invalid increment amounts

**Test ID**: `objects/unit/RTLC12e1/increment-invalid-amounts-table-0`

**Spec requirement:** If amount is null, not Number, not finite, or NaN, throw 40003.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")

invalid_amounts = [
  { value: null,        label: "null" },
  { value: NaN,         label: "NaN" },
  { value: Infinity,    label: "Infinity" },
  { value: -Infinity,   label: "-Infinity" },
  { value: "10",        label: "string" },
  { value: true,        label: "boolean" },
  { value: [1, 2],      label: "array" },
  { value: { n: 1 },    label: "object" }
]
```

### Test Steps
```pseudo
FOR scenario IN invalid_amounts:
  AWAIT root.increment(scenario.value) FAILS WITH error
  ASSERT error.code == 40003
```
