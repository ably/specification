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
control = []
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

# Per the Negative-assertion quiescence pattern (helpers/standard_test_pool.md): subscribe a
# control listener that WILL fire on the same dispatch as the message under test, then AWAIT it
# before asserting `updates` is unchanged.
sub_control = instance.subscribe((event) => control.append(event))
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 10, "02", "remote")
]))
poll_until(control.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
# Control delivered, so the unsubscribed listener would also have run had it still been registered.
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
control = []
instance = root.get("score").instance()
instance.subscribe((event) => updates.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 5, "01", "remote")
]))
poll_until(updates.length >= 1, timeout: 5s)

# Serial "02" passes the newness check (RTLO4a6); an increment with no `number` is the noop (RTLC9h)
# Use a raw ObjectMessage with no `number` field so it exercises the real RTLC9h/RTLO4b4c1 noop branch
# (a `number: 0` would EXIST per RTLC9g and produce a non-noop update with amount 0).
mock_ws.send_to_client(build_object_message("test", [
  ObjectMessage(
    serial: "02",
    siteCode: "remote",
    operation: { action: "COUNTER_INC", objectId: "counter:score@1000", counterInc: {} }
  )
]))
# Negative-assertion quiescence (helpers/standard_test_pool.md): drive a follow-up "03" increment
# and await it via a SEPARATE control listener (its own `control` array). Because "03" is dispatched
# after the noop "02" on the same channel, once the control fires the noop has certainly been
# processed. The control is kept separate so it does not inflate `updates`.
control_sub = instance.subscribe((event) => control.append(event))
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 3, "03", "remote")
]))
poll_until(control.length >= 1, timeout: 5s)
control_sub.unsubscribe()
```

### Assertions
```pseudo
# The noop "02" produced no LiveObjectUpdate, so the original listener fired only for "01" and "03"
# → updates.length == 2. (The separate control listener only provides the quiescence barrier; had
# the noop wrongly fired, updates.length would be 3.)
ASSERT updates.length == 2
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

## RTLO4b - subscribe on InternalLiveMap receives LiveMapUpdate

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
  build_map_set("root", "name", { string: "Bob" }, remote_serial(0), "remote")
]))
poll_until(updates.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT updates.length == 1
```

---

## RTLO4b4c3c - tombstone update deregisters all Instance#subscribe listeners

**Test ID**: `objects/unit/RTLO4b4c3c/tombstone-deregisters-listeners-0`

| Spec | Requirement |
|------|-------------|
| RTLO4b4c3c | If LiveObjectUpdate.tombstone is true, deregister all listeners |
| RTLO4b4c3a | Listeners are called with the tombstone update itself before deregistration |

Tests that when a tombstone update is emitted, all registered listeners are called with the update, but subsequent updates do not fire any listener because they have been deregistered. Tested through Instance#subscribe (RTINS16); the tombstone is identified by `message.operation.action == "OBJECT_DELETE"`.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
updates_a = []
updates_b = []
control = []
instance = root.get("score").instance()
instance.subscribe((event) => updates_a.append(event))
instance.subscribe((event) => updates_b.append(event))
```

### Test Steps
```pseudo
# Send an OBJECT_DELETE which causes a tombstone
mock_ws.send_to_client(build_object_message("test", [
  build_object_delete("counter:score@1000", "50", "remote")
]))
# Per the Negative-assertion quiescence pattern (helpers/standard_test_pool.md): for the
# multi-listener case, AWAIT ALL involved listeners on this dispatch before asserting either count.
poll_until(updates_a.length >= 1, timeout: 5s)
poll_until(updates_b.length >= 1, timeout: 5s)

# Both listeners should have received the tombstone update
ASSERT updates_a.length == 1
ASSERT updates_a[0].message.operation.action == "OBJECT_DELETE"
ASSERT updates_b.length == 1
ASSERT updates_b[0].message.operation.action == "OBJECT_DELETE"

# Send another update to the tombstoned object — the deregistered listeners must not fire.
# QUIESCENCE: a tombstoned object ignores further operations (RTLC7e), so neither the deregistered
# listeners nor a fresh listener on counter:score@1000 would ever fire — it cannot serve as a
# control. Use a SEPARATE LIVE object: subscribe a control listener to map:profile@1000 and drive an
# observable update on it AFTER the message under test. Messages are processed in order, so once the
# control fires, "51" has also been processed (helpers/standard_test_pool.md "Negative-assertion quiescence").
control_inst = root.get("profile").instance()
control_inst.subscribe((event) => control.append(event))
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 3, "51", "remote")
]))
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("map:profile@1000", "quiescence_probe", { string: "x" }, "52", "remote")
]))
poll_until(control.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
# Control delivered, so any still-registered original listener would also have run.
ASSERT updates_a.length == 1
ASSERT updates_b.length == 1
```

---

## RTLO4b4d - InstanceSubscriptionEvent.message is populated from source ObjectMessage

**Test ID**: `objects/unit/RTLO4b4d/update-has-object-message-0`

| Spec | Requirement |
|------|-------------|
| RTLO4b4d | The update carries the source ObjectMessage |
| RTINS16e | InstanceSubscriptionEvent.message is a PublicAPI::ObjectMessage |

Tests that when an update is triggered by an incoming ObjectMessage, the `InstanceSubscriptionEvent.message` field is populated with the public ObjectMessage. Tested through Instance#subscribe (RTINS16).

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
ASSERT updates[0].message IS NOT null
ASSERT updates[0].message.serial == "99"
ASSERT updates[0].message.siteCode == "remote"
ASSERT updates[0].message.operation.action == "COUNTER_INC"
ASSERT updates[0].message.operation.objectId == "counter:score@1000"
```

---

## RTLO4b4e - tombstone update identified by OBJECT_DELETE action

**Test ID**: `objects/unit/RTLO4b4e/tombstone-flag-true-0`

| Spec | Requirement |
|------|-------------|
| RTLO4b4e | Tombstone update emitted when LiveObject is tombstoned |

Tests that when a `LiveObject` is tombstoned (e.g. via OBJECT_DELETE), the emitted event carries an OBJECT_DELETE operation. Tested through Instance#subscribe (RTINS16).

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
ASSERT updates[0].message.operation.action == "OBJECT_DELETE"
```

---

## RTLO4b4e - normal update carries non-tombstone action

**Test ID**: `objects/unit/RTLO4b4e/tombstone-flag-false-0`

**Spec requirement:** Normal (non-tombstone) updates carry a regular operation action.

Tests that for a normal update, the event carries a COUNTER_INC action (not OBJECT_DELETE). Tested through Instance#subscribe (RTINS16).

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
ASSERT updates[0].message.operation.action == "COUNTER_INC"
```
