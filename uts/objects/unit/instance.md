# Instance Tests

Spec points: `RTINS1`–`RTINS16`

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
| RTINS4a | Checks access API preconditions per RTO25 |
| RTINS4b | InternalLiveCounter -> delegates to InternalLiveCounter#value |
| RTINS4c | Primitive -> returns value directly |
| RTINS4d | InternalLiveMap -> null |

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
| RTINS5b | Checks access API preconditions per RTO25 |
| RTINS5c | InternalLiveMap -> look up key, wrap result in Instance |
| RTINS5d | Non-InternalLiveMap -> null |

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

## RTINS6 - entries() returns array of [key, Instance] pairs

**Test ID**: `objects/unit/RTINS6/entries-yields-instances-0`

| Spec | Requirement |
|------|-------------|
| RTINS6a | Checks access API preconditions per RTO25 |
| RTINS6b | InternalLiveMap -> array of [key, Instance] pairs |
| RTINS6c | Non-InternalLiveMap -> empty array |

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
| RTINS9a | Checks access API preconditions per RTO25 |
| RTINS9b | InternalLiveMap -> non-tombstoned entry count |
| RTINS9c | Non-InternalLiveMap -> null |

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

| Spec | Requirement |
|------|-------------|
| RTINS10a | Checks access API preconditions per RTO25 |
| RTINS10b | Behaves identically to PathObject#compact on the wrapped value |

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

## RTINS12 - set() delegates to InternalLiveMap#set

**Test ID**: `objects/unit/RTINS12/set-delegates-0`

| Spec | Requirement |
|------|-------------|
| RTINS12b | Checks write API preconditions per RTO26 |
| RTINS12c | InternalLiveMap -> delegate to InternalLiveMap#set |
| RTINS12d | Non-InternalLiveMap -> throw 92007 |

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

## RTINS12d - set() on non-InternalLiveMap throws 92007

**Test ID**: `objects/unit/RTINS12d/set-non-map-throws-0`

**Spec requirement:** If the wrapped value is not an InternalLiveMap, throw ErrorInfo with code 92007.

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

## RTINS13 - remove() delegates to InternalLiveMap#remove

**Test ID**: `objects/unit/RTINS13/remove-delegates-0`

| Spec | Requirement |
|------|-------------|
| RTINS13b | Checks write API preconditions per RTO26 |
| RTINS13c | InternalLiveMap -> delegate to InternalLiveMap#remove |
| RTINS13d | Non-InternalLiveMap -> throw 92007 |

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

## RTINS14 - increment() delegates to InternalLiveCounter#increment

**Test ID**: `objects/unit/RTINS14/increment-delegates-0`

| Spec | Requirement |
|------|-------------|
| RTINS14b | Checks write API preconditions per RTO26 |
| RTINS14c | InternalLiveCounter -> delegate to increment |
| RTINS14d | Non-InternalLiveCounter -> throw 92007 |

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

## RTINS14d - increment() on non-InternalLiveCounter throws 92007

**Test ID**: `objects/unit/RTINS14d/increment-non-counter-throws-0`

**Spec requirement:** If the wrapped value is not an InternalLiveCounter, throw ErrorInfo with code 92007.

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

## RTINS15 - decrement() delegates to InternalLiveCounter#decrement

**Test ID**: `objects/unit/RTINS15/decrement-delegates-0`

| Spec | Requirement |
|------|-------------|
| RTINS15b | Checks write API preconditions per RTO26 |
| RTINS15c | InternalLiveCounter -> delegate to decrement |
| RTINS15d | Non-InternalLiveCounter -> throw 92007 |

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

## RTINS14a - increment() defaults to 1

**Test ID**: `objects/unit/RTINS14a/increment-default-0`

**Spec requirement:** amount defaults to 1 (RTINS14a1).

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

**Spec requirement:** amount defaults to 1 (RTINS15a1).

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

## RTINS16 - subscribe() receives InstanceSubscriptionEvent

**Test ID**: `objects/unit/RTINS16/subscribe-receives-events-0`

| Spec | Requirement |
|------|-------------|
| RTINS16b | Checks access API preconditions per RTO25 |
| RTINS16d | Subscribes via LiveObject#subscribe (RTLO4b) |
| RTINS16e1 | Event.object is an Instance wrapping the LiveObject |
| RTINS16f | Returns Subscription |
| RTINS16g | Identity-based subscription |

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

## RTINS16c - subscribe() on primitive throws 92007

**Test ID**: `objects/unit/RTINS16c/subscribe-primitive-throws-0`

**Spec requirement:** If wrapped value is not a LiveObject (i.e. it is a primitive), throw ErrorInfo with code 92007.

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

## RTINS16e2 - InstanceSubscriptionEvent contains PublicAPI::ObjectMessage

**Test ID**: `objects/unit/RTINS16e2/subscription-event-message-0`

| Spec | Requirement |
|------|-------------|
| RTINS16e1 | Event.object is an Instance wrapping the LiveObject |
| RTINS16e2 | Event.message is a PublicAPI::ObjectMessage derived from the triggering ObjectMessage |

Tests that the InstanceSubscriptionEvent includes both the `object` (Instance) and `message` (PublicAPI::ObjectMessage) fields when a data update arrives.

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
  build_map_set("root", "name", { string: "Bob" }, remote_serial(0), "remote")
]))
poll_until(events.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events[0].object IS Instance
ASSERT events[0].object.id() == "root"
ASSERT events[0].message IS NOT null
ASSERT events[0].message.channel == "test"
ASSERT events[0].message.operation.action == "MAP_SET"
ASSERT events[0].message.operation.objectId == "root"
ASSERT events[0].message.operation.mapSet.key == "name"
```

---

## RTINS16f - subscribe() returns Subscription for deregistration

**Test ID**: `objects/unit/RTINS16f/subscribe-returns-subscription-0`

**Spec requirement:** Returns a Subscription object (RTINS16f). Deregistration is via Subscription#unsubscribe.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
counter_inst = root.get("score").instance()
events = []
sub = counter_inst.subscribe((event) => events.append(event))
sub.unsubscribe()

# Quiescence control: a second, still-subscribed listener on the same
# counter instance that WILL fire on the same dispatch as the send below.
# See helpers/standard_test_pool.md "Negative-assertion quiescence".
control_events = []
counter_inst.subscribe((event) => control_events.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "99", "remote")
]))
```

### Assertions
```pseudo
# Negative-assertion quiescence (helpers/standard_test_pool.md): await the
# control listener so that once it has been delivered, the unsubscribed
# listener would also have fired had it remained subscribed; THEN assert
# the unsubscribed listener's count is unchanged.
poll_until(control_events.length >= 1, timeout: 5s)
ASSERT events.length == 0
```

---

## RTINS16g - Instance subscription follows identity not path

**Test ID**: `objects/unit/RTINS16g/subscription-follows-identity-0`

**Spec requirement:** The subscription is identity-based: it follows the specific LiveObject instance, regardless of where it sits in the graph.

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
  build_map_set("root", "score", { objectId: "counter:new@2000" }, remote_serial(0), "remote")
]))

mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 10, "100", "remote")
]))
poll_until(events.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events.length >= 1
# RTINS16e1: the delivered event carries the Instance wrapping the
# LiveObject that fired. Assert against the DELIVERED EVENT's object id
# (not the pre-existing counter_inst handle, whose id is already
# "counter:score@1000" at subscribe time and so would pass even if the
# listener fired for the wrong object after the score key was repointed).
ASSERT events[0].object IS Instance
ASSERT events[0].object.id() == "counter:score@1000"
```

---

## RTINS16h - subscribe() has no side effects

**Test ID**: `objects/unit/RTINS16h/subscribe-no-side-effects-0`

**Spec requirement:** The subscribe operation must not have any side effects on RealtimeObject, the underlying channel, or their status.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
counter_inst = root.get("score").instance()
channel_state_before = channel.state
```

### Test Steps
```pseudo
sub = counter_inst.subscribe((event) => {})
```

### Assertions
```pseudo
ASSERT channel.state == channel_state_before
```
