# LiveObject Subscribe Tests

Spec points: `RTLO4b`, `RTLO4b3`, `RTLO4b4c1`, `RTLO4b4c3a`, `RTLO4b4c3c`, `RTLO4b4d`, `RTLO4b4e`, `RTLO4b6`, `RTLO4b7`

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
| RTLO4b4c3a | Registered listeners called with LiveObjectUpdate |
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

## RTLO4b7 - subscribe returns Subscription with unsubscribe method

**Test ID**: `objects/unit/RTLO4b7/subscribe-returns-subscription-0`

| Spec | Requirement |
|------|-------------|
| RTLO4b7 | Returns a Subscription object |

Tests that `subscribe` returns a `Subscription` object that has an `unsubscribe` method.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
instance = root.get("score").instance()
```

### Test Steps
```pseudo
sub = instance.subscribe((event) => {})
```

### Assertions
```pseudo
ASSERT sub IS Subscription
ASSERT sub.unsubscribe IS Function
```

---

## RTLO4b7 - Subscription#unsubscribe stops delivery

**Test ID**: `objects/unit/RTLO4b7/subscription-unsubscribe-stops-delivery-0`

| Spec | Requirement |
|------|-------------|
| RTLO4b7 | Returns a Subscription object |
| RTLO4b4c3a | Registered listeners called with LiveObjectUpdate |

Tests that calling `unsubscribe()` on the returned `Subscription` deregisters the listener so that subsequent updates do not trigger it.

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

## RTLO4b7 - Subscription#unsubscribe is idempotent

**Test ID**: `objects/unit/RTLO4b7/subscription-unsubscribe-idempotent-0`

**Spec requirement:** Calling `Subscription#unsubscribe()` multiple times must not throw or produce errors.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
instance = root.get("score").instance()
sub = instance.subscribe((event) => {})
```

### Test Steps
```pseudo
sub.unsubscribe()
sub.unsubscribe()
```

### Assertions
```pseudo
// No error thrown — both calls complete without error
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

## RTLO4b4c3c - tombstone update deregisters all LiveObject#subscribe listeners

**Test ID**: `objects/unit/RTLO4b4c3c/tombstone-deregisters-listeners-0`

| Spec | Requirement |
|------|-------------|
| RTLO4b4c3c | If LiveObjectUpdate.tombstone is true, deregister all LiveObject#subscribe listeners |
| RTLO4b4c3a | Listeners are called with the tombstone update itself before deregistration |

Tests that when a tombstone update is emitted, all registered listeners are called with the tombstone update, but subsequent updates do not fire any listener because they have been deregistered.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
updates_a = []
updates_b = []
instance = root.get("score").instance()
instance.subscribe((event) => updates_a.append(event))
instance.subscribe((event) => updates_b.append(event))
```

### Test Steps
```pseudo
# Send an OBJECT_DELETE which causes a tombstone LiveObjectUpdate
mock_ws.send_to_client(build_object_message("test", [
  build_object_delete("counter:score@1000", "50", "remote")
]))
poll_until(updates_a.length >= 1, timeout: 5s)

# Both listeners should have received the tombstone update
ASSERT updates_a.length == 1
ASSERT updates_a[0].tombstone == true
ASSERT updates_b.length == 1
ASSERT updates_b[0].tombstone == true

# Send another update — listeners should have been deregistered by tombstone
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 3, "51", "remote")
]))
```

### Assertions
```pseudo
ASSERT updates_a.length == 1
ASSERT updates_b.length == 1
```

---

## RTLO4b4d - LiveObjectUpdate.objectMessage is populated from source ObjectMessage

**Test ID**: `objects/unit/RTLO4b4d/update-has-object-message-0`

| Spec | Requirement |
|------|-------------|
| RTLO4b4d | LiveObjectUpdate.objectMessage is the source ObjectMessage that caused the update |

Tests that when an update is triggered by an incoming ObjectMessage, the `LiveObjectUpdate.objectMessage` field is populated with that source ObjectMessage.

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
  build_counter_inc("counter:score@1000", 7, "99", "remote")
]))
poll_until(updates.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT updates.length == 1
ASSERT updates[0].objectMessage IS NOT null
ASSERT updates[0].objectMessage.serial == "99"
ASSERT updates[0].objectMessage.siteCode == "remote"
ASSERT updates[0].objectMessage.operation.action == "COUNTER_INC"
ASSERT updates[0].objectMessage.operation.objectId == "counter:score@1000"
```

---

## RTLO4b4e - LiveObjectUpdate.tombstone is true for tombstone updates

**Test ID**: `objects/unit/RTLO4b4e/tombstone-flag-true-0`

| Spec | Requirement |
|------|-------------|
| RTLO4b4e | LiveObjectUpdate.tombstone indicates the update was emitted as a result of tombstoning |

Tests that when a `LiveObject` is tombstoned (e.g. via OBJECT_DELETE), the emitted `LiveObjectUpdate` has `tombstone == true`.

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
  build_object_delete("counter:score@1000", "50", "remote")
]))
poll_until(updates.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT updates.length == 1
ASSERT updates[0].tombstone == true
```

---

## RTLO4b4e - LiveObjectUpdate.tombstone is false for normal updates

**Test ID**: `objects/unit/RTLO4b4e/tombstone-flag-false-0`

**Spec requirement:** LiveObjectUpdate.tombstone defaults to false if not explicitly set.

Tests that for a normal (non-tombstone) update, `LiveObjectUpdate.tombstone` is `false`.

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
  build_counter_inc("counter:score@1000", 7, "99", "remote")
]))
poll_until(updates.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT updates.length == 1
ASSERT updates[0].tombstone == false
```
