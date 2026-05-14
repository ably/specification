# Instance Tests

Spec points: `RTINS1`–`RTINS19`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Shared Helpers

See `helpers/standard_test_pool.md` for `setup_synced_channel` and builder functions.

---

## RTINS3 - id property returns objectId

**Test ID**: `objects/unit/RTINS3/id-returns-objectid-0`

| Spec | Requirement |
|------|-------------|
| RTINS3a | LiveObject -> returns objectId |
| RTINS3b | Primitive -> returns null |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
counter_inst = root.get("score").instance()
ASSERT counter_inst.id() == "counter:score@1000"

map_inst = root.get("profile").instance()
ASSERT map_inst.id() == "map:profile@1000"
```

---

## RTINS4 - value() returns counter number or primitive

**Test ID**: `objects/unit/RTINS4/value-counter-0`

| Spec | Requirement |
|------|-------------|
| RTINS4a | LiveCounter -> numeric value |
| RTINS4c | LiveMap -> null |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
counter_inst = root.get("score").instance()
ASSERT counter_inst.value() == 100

map_inst = root.instance()
ASSERT map_inst.value() == null
```

---

## RTINS5 - get() returns Instance wrapping entry value

**Test ID**: `objects/unit/RTINS5/get-wraps-entry-0`

| Spec | Requirement |
|------|-------------|
| RTINS5b | LiveMap -> look up key, wrap result in Instance |
| RTINS5c | Non-LiveMap -> null |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
root_inst = root.instance()
```

### Assertions
```pseudo
name_inst = root_inst.get("name")
ASSERT name_inst IS Instance
ASSERT name_inst.value() == "Alice"

score_inst = root_inst.get("score")
ASSERT score_inst.id() == "counter:score@1000"

null_inst = root_inst.get("nonexistent")
ASSERT null_inst == null
```

---

## RTINS6 - entries() yields [key, Instance] pairs

**Test ID**: `objects/unit/RTINS6/entries-yields-instances-0`

| Spec | Requirement |
|------|-------------|
| RTINS6a | LiveMap -> [key, Instance] pairs |
| RTINS6b | Non-LiveMap -> empty iterator |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
root_inst = root.instance()
```

### Test Steps
```pseudo
entries = {}
FOR [key, inst] IN root_inst.entries():
  entries[key] = inst
```

### Assertions
```pseudo
ASSERT entries.length == 7
ASSERT entries["name"] IS Instance
ASSERT entries["name"].value() == "Alice"
```

---

## RTINS9 - size() returns non-tombstoned count

**Test ID**: `objects/unit/RTINS9/size-0`

| Spec | Requirement |
|------|-------------|
| RTINS9a | LiveMap -> non-tombstoned entry count |
| RTINS9b | Non-LiveMap -> null |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
root_inst = root.instance()
ASSERT root_inst.size() == 7

counter_inst = root.get("score").instance()
ASSERT counter_inst.size() == null
```

---

## RTINS10 - compact() recursively compacts

**Test ID**: `objects/unit/RTINS10/compact-0`

**Spec requirement:** Behaves identically to PathObject#compact on the wrapped value.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
root_inst = root.instance()
```

### Test Steps
```pseudo
result = root_inst.compact()
```

### Assertions
```pseudo
ASSERT result["name"] == "Alice"
ASSERT result["score"] == 100
ASSERT result["profile"]["email"] == "alice@example.com"
```

---

## RTINS12 - set() delegates to LiveMap#set

**Test ID**: `objects/unit/RTINS12/set-delegates-0`

| Spec | Requirement |
|------|-------------|
| RTINS12b | LiveMap -> delegate to LiveMap#set |
| RTINS12c | Non-LiveMap -> throw 92007 |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
root_inst = root.instance()
```

### Test Steps
```pseudo
AWAIT root_inst.set("name", "Bob")
```

### Assertions
```pseudo
ASSERT root.get("name").value() == "Bob"
```

---

## RTINS12c - set() on non-LiveMap throws 92007

**Test ID**: `objects/unit/RTINS12c/set-non-map-throws-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
counter_inst = root.get("score").instance()
```

### Test Steps
```pseudo
AWAIT counter_inst.set("key", "value") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92007
```

---

## RTINS13 - remove() delegates to LiveMap#remove

**Test ID**: `objects/unit/RTINS13/remove-delegates-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
root_inst = root.instance()
```

### Test Steps
```pseudo
AWAIT root_inst.remove("name")
```

### Assertions
```pseudo
ASSERT root.get("name").value() == null
```

---

## RTINS14 - increment() delegates to LiveCounter#increment

**Test ID**: `objects/unit/RTINS14/increment-delegates-0`

| Spec | Requirement |
|------|-------------|
| RTINS14b | LiveCounter -> delegate to increment |
| RTINS14c | Non-LiveCounter -> throw 92007 |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
counter_inst = root.get("score").instance()
```

### Test Steps
```pseudo
AWAIT counter_inst.increment(25)
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 125
```

---

## RTINS14c - increment() on non-LiveCounter throws 92007

**Test ID**: `objects/unit/RTINS14c/increment-non-counter-throws-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
map_inst = root.instance()
```

### Test Steps
```pseudo
AWAIT map_inst.increment(5) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92007
```

---

## RTINS15 - decrement() delegates to LiveCounter#decrement

**Test ID**: `objects/unit/RTINS15/decrement-delegates-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
counter_inst = root.get("score").instance()
```

### Test Steps
```pseudo
AWAIT counter_inst.decrement(10)
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 90
```

---

## RTINS16 - subscribe() receives InstanceSubscriptionEvent

**Test ID**: `objects/unit/RTINS16/subscribe-receives-events-0`

| Spec | Requirement |
|------|-------------|
| RTINS16c | Subscribes via LiveObject#subscribe |
| RTINS16d1 | Event.object is the Instance |
| RTINS16e | Returns Subscription |
| RTINS16f | Identity-based subscription |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
counter_inst = root.get("score").instance()
events = []
sub = counter_inst.subscribe((event) => events.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "99", "remote")
]))
poll_until(events.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT sub IS Subscription
ASSERT events.length == 1
ASSERT events[0].object IS Instance
ASSERT events[0].object.id() == "counter:score@1000"
```

---

## RTINS16b - subscribe() on primitive throws 92007

**Test ID**: `objects/unit/RTINS16b/subscribe-primitive-throws-0`

**Spec requirement:** If wrapped value is not LiveObject, throw 92007.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
name_inst = root.instance().get("name")
name_inst.subscribe((event) => {}) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92007
```

---

## RTINS16f - Instance subscription follows identity not path

**Test ID**: `objects/unit/RTINS16f/subscription-follows-identity-0`

**Spec requirement:** Instance follows the specific LiveObject, regardless of tree position.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
counter_inst = root.get("score").instance()
events = []
counter_inst.subscribe((event) => events.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "score", { objectId: "counter:new@2000" }, "99", "remote")
]))

mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 10, "100", "remote")
]))
poll_until(events.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events.length >= 1
ASSERT counter_inst.id() == "counter:score@1000"
```

---

## RTINS17 - unsubscribe() deregisters listener

**Test ID**: `objects/unit/RTINS17/unsubscribe-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
counter_inst = root.get("score").instance()
events = []
sub = counter_inst.subscribe((event) => events.append(event))
sub.unsubscribe()
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "99", "remote")
]))
```

### Assertions
```pseudo
ASSERT events.length == 0
```

---

## RTINS14a - increment() defaults to 1

**Test ID**: `objects/unit/RTINS14a/increment-default-0`

**Spec requirement:** amount defaults to 1.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
counter_inst = root.get("score").instance()
```

### Test Steps
```pseudo
AWAIT counter_inst.increment()
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 101
```

---

## RTINS15a - decrement() defaults to 1

**Test ID**: `objects/unit/RTINS15a/decrement-default-0`

**Spec requirement:** amount defaults to 1.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
counter_inst = root.get("score").instance()
```

### Test Steps
```pseudo
AWAIT counter_inst.decrement()
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 99
```

---

## RTINS16 - Subscription event contains message metadata

**Test ID**: `objects/unit/RTINS16/subscription-event-metadata-0`

| Spec | Requirement |
|------|-------------|
| RTINS16d1 | Event.object is the Instance |
| RTINS16d2 | Event.message is the ObjectMessage that triggered the update |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
root_inst = root.instance()
events = []
root_inst.subscribe((event) => events.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "name", { string: "Bob" }, "99", "remote")
]))
poll_until(events.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events[0].object IS Instance
ASSERT events[0].object.id() == "root"
ASSERT events[0].message IS NOT null
ASSERT events[0].message.operation.action == "MAP_SET"
ASSERT events[0].message.operation.mapSet.key == "name"
```
