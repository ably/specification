# LiveObject Subscribe Tests

Spec points: `RTLO4b`, `RTLO4c`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Shared Helpers

See `helpers/standard_test_pool.md` for `setup_synced_channel` and builder functions.

---

## RTLO4b - subscribe registers listener for data updates

**Test ID**: `objects/unit/RTLO4b/subscribe-receives-updates-0`

| Spec | Requirement |
|------|-------------|
| RTLO4b3 | User provides listener for data updates |
| RTLO4b4c2 | Listener called with LiveObjectUpdate |
| RTLO4b7 | Returns Subscription object |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
updates = []
instance = root.get("score").instance()
sub = instance.subscribe((event) => updates.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "99", "remote")
]))
poll_until(updates.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT sub IS Subscription
ASSERT updates.length == 1
```

---

## RTLO4b4c1 - noop update does not trigger listener

**Test ID**: `objects/unit/RTLO4b4c1/noop-no-trigger-0`

**Spec requirement:** If LiveObjectUpdate is a noop, do nothing.

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
  build_counter_inc("counter:score@1000", 5, "01", "remote")
]))
poll_until(updates.length >= 1, timeout: 5s)

mock_ws.send_to_client(build_object_message("test", [
  ObjectMessage(
    serial: "01", siteCode: "remote",
    operation: { action: "COUNTER_INC", objectId: "counter:score@1000", counterInc: {} }
  )
]))
```

### Assertions
```pseudo
ASSERT updates.length == 1
```

---

## RTLO4c - unsubscribe deregisters listener

**Test ID**: `objects/unit/RTLO4c/unsubscribe-deregisters-0`

| Spec | Requirement |
|------|-------------|
| RTLO4c3 | Once deregistered, subsequent updates do not call listener |
| RTLO4c4 | No side effects on channel or RealtimeObject |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
updates = []
instance = root.get("score").instance()
sub = instance.subscribe((event) => updates.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 5, "01", "remote")
]))
poll_until(updates.length >= 1, timeout: 5s)

sub.unsubscribe()

mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 10, "02", "remote")
]))
```

### Assertions
```pseudo
ASSERT updates.length == 1
```

---

## RTLO4b1 - subscribe requires OBJECT_SUBSCRIBE mode

**Test ID**: `objects/unit/RTLO4b1/subscribe-requires-mode-0`

**Spec requirement:** Requires OBJECT_SUBSCRIBE channel mode per RTO2.

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
        flags: HAS_OBJECTS, modes: ["OBJECT_PUBLISH"]
      ))
      mock_ws.send_to_client(build_object_sync_message(msg.channel, "sync1:", STANDARD_POOL_OBJECTS))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()
instance = root.get("score").instance()
```

### Test Steps
```pseudo
instance.subscribe((event) => {}) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40024
```

---

## RTLO4b6 - subscribe has no side effects

**Test ID**: `objects/unit/RTLO4b6/subscribe-no-side-effects-0`

**Spec requirement:** Must not have side effects on RealtimeObject, channel, or their status.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
state_before = channel.state
instance = root.get("score").instance()
```

### Test Steps
```pseudo
instance.subscribe((event) => {})
```

### Assertions
```pseudo
ASSERT channel.state == state_before
```

---

## RTLO4b - subscribe on LiveMap receives LiveMapUpdate

**Test ID**: `objects/unit/RTLO4b/subscribe-map-update-0`

**Spec requirement:** LiveMapUpdate.update contains key -> "updated"/"removed".

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
updates = []
instance = root.instance()
instance.subscribe((event) => updates.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "name", { string: "Bob" }, "99", "remote")
]))
poll_until(updates.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT updates.length == 1
```

---

## RTLO4c1 - unsubscribe requires no channel mode

**Test ID**: `objects/unit/RTLO4c1/unsubscribe-no-mode-required-0`

**Spec requirement:** Does not require any specific channel modes.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
instance = root.get("score").instance()
sub = instance.subscribe((event) => {})
```

### Test Steps
```pseudo
sub.unsubscribe()
```

### Assertions
```pseudo
// No error thrown
```
