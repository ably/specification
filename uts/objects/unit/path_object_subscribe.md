# PathObject Subscribe Tests

Spec points: `RTPO19`–`RTPO21`, `RTO24`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Shared Helpers

See `helpers/standard_test_pool.md` for `setup_synced_channel` and builder functions.

---

## RTPO19 - subscribe() returns Subscription and receives events

**Test ID**: `objects/unit/RTPO19/subscribe-receives-events-0`

| Spec | Requirement |
|------|-------------|
| RTPO19c | Returns Subscription object |
| RTPO19d1 | Event.object is a PathObject pointing to change path |
| RTPO19d2 | Event.message is the ObjectMessage |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
sub = root.get("score").subscribe((event) => events.append(event))
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
ASSERT events[0].object IS PathObject
ASSERT events[0].object.path() == "score"
ASSERT events[0].message IS NOT null
```

---

## RTPO19b1b - subscribe() with depth 1 only receives self events

**Test ID**: `objects/unit/RTPO19b1b/subscribe-depth-1-self-only-0`

**Spec requirement:** depth=1 means only changes at the exact subscribed path trigger the listener.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.subscribe((event) => events.append(event), { depth: 1 })
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "name", { string: "Bob" }, "99", "remote")
]))
poll_until(events.length >= 1, timeout: 5s)

mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "100", "remote")
]))
```

### Assertions
```pseudo
ASSERT events.length == 1
```

---

## RTPO19b1c - subscribe() with depth 2 receives self and children

**Test ID**: `objects/unit/RTPO19b1c/subscribe-depth-2-children-0`

**Spec requirement:** depth=n means changes up to n-1 levels of children trigger the listener.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.subscribe((event) => events.append(event), { depth: 2 })
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "name", { string: "Bob" }, "99", "remote")
]))
poll_until(events.length >= 1, timeout: 5s)

mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "100", "remote")
]))
poll_until(events.length >= 2, timeout: 5s)

mock_ws.send_to_client(build_object_message("test", [
  build_map_set("map:profile@1000", "email", { string: "bob@example.com" }, "101", "remote")
]))
```

### Assertions
```pseudo
ASSERT events.length == 2
```

---

## RTPO19b1a - subscribe() with no depth receives all descendants

**Test ID**: `objects/unit/RTPO19b1a/subscribe-unlimited-depth-0`

**Spec requirement:** If depth is undefined, subscription receives events at any depth.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.subscribe((event) => events.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "name", { string: "Bob" }, "99", "remote")
]))
poll_until(events.length >= 1, timeout: 5s)

mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "100", "remote")
]))
poll_until(events.length >= 2, timeout: 5s)

mock_ws.send_to_client(build_object_message("test", [
  build_map_set("map:prefs@1000", "theme", { string: "light" }, "101", "remote")
]))
poll_until(events.length >= 3, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events.length >= 3
```

---

## RTPO19b1d - subscribe() with non-positive depth throws 40003

**Test ID**: `objects/unit/RTPO19b1d/subscribe-non-positive-depth-throws-0`

**Spec requirement:** If depth is provided and is not a positive integer, throw 40003.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
root.subscribe((event) => {}, { depth: 0 }) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40003
```

---

## RTPO19b1d - subscribe() with negative depth throws 40003

**Test ID**: `objects/unit/RTPO19b1d/subscribe-negative-depth-throws-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
root.subscribe((event) => {}, { depth: -1 }) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40003
```

---

## RTPO19e - subscribe() follows path not identity

**Test ID**: `objects/unit/RTPO19e/subscribe-follows-path-0`

**Spec requirement:** If the object at the path changes identity, the subscription continues to deliver events for the new object.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.get("score").subscribe((event) => events.append(event))
```

### Test Steps
```pseudo
// Replace the counter at "score" with a new counter
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "score", { objectId: "counter:new@2000" }, "99", "remote")
]))

// Increment the NEW counter at "score"
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:new@2000", 10, "100", "remote")
]))
poll_until(events.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
// Should receive event for the new counter, since subscription follows path
found_new = false
FOR event IN events:
  IF event.object.path() == "score":
    found_new = true
ASSERT found_new == true
```

---

## RTPO19f - child events bubble up to parent subscription

**Test ID**: `objects/unit/RTPO19f/child-events-bubble-0`

**Spec requirement:** Events at child paths bubble up subject to depth filtering.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.get("profile").subscribe((event) => events.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("map:profile@1000", "email", { string: "bob@example.com" }, "99", "remote")
]))
poll_until(events.length >= 1, timeout: 5s)

mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:nested@1000", 3, "100", "remote")
]))
poll_until(events.length >= 2, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events.length >= 2
```

---

## RTO24b3 - depth filtering formula

**Test ID**: `objects/unit/RTO24b3/depth-filtering-formula-0`

**Spec requirement:** Event dispatched if `eventPath.length - subscriptionPath.length + 1 <= depth`.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
// Subscribe at "profile" with depth 2:
// self (profile) → segmentDiff=0, 0+1=1 ≤ 2 ✓
// child (profile.email) → segmentDiff=1, 1+1=2 ≤ 2 ✓
// grandchild (profile.prefs.theme) → segmentDiff=2, 2+1=3 > 2 ✗
root.get("profile").subscribe((event) => events.append(event), { depth: 2 })
```

### Test Steps
```pseudo
// Self event (profile map update)
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("map:profile@1000", "email", { string: "bob@example.com" }, "99", "remote")
]))
poll_until(events.length >= 1, timeout: 5s)

// Child event (nested counter)
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:nested@1000", 3, "100", "remote")
]))
poll_until(events.length >= 2, timeout: 5s)

// Grandchild event (prefs.theme) — should NOT be received
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("map:prefs@1000", "theme", { string: "light" }, "101", "remote")
]))
```

### Assertions
```pseudo
ASSERT events.length == 2
```

---

## RTO24b5 - listener exception does not affect other listeners

**Test ID**: `objects/unit/RTO24b5/listener-exception-caught-0`

**Spec requirement:** If a listener throws, the error is caught and logged without affecting other subscriptions.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.subscribe((event) => { THROW Error("boom") })
root.subscribe((event) => events.append(event))
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
ASSERT events.length == 1
```

---

## RTPO20 - unsubscribe() deregisters listener

**Test ID**: `objects/unit/RTPO20/unsubscribe-deregisters-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
sub = root.get("score").subscribe((event) => events.append(event))
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

## RTPO19g - subscribe() has no side effects

**Test ID**: `objects/unit/RTPO19g/subscribe-no-side-effects-0`

**Spec requirement:** Must not have side effects on RealtimeObject, channel, or their status.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
state_before = channel.state
```

### Test Steps
```pseudo
root.get("score").subscribe((event) => {})
```

### Assertions
```pseudo
ASSERT channel.state == state_before
```

---

## RTPO19 - MAP_CLEAR triggers subscription events on child paths

**Test ID**: `objects/unit/RTPO19/map-clear-triggers-child-events-0`

**Spec requirement:** When MAP_CLEAR is applied, subscriptions on affected child paths receive events.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.subscribe((event) => events.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_map_clear("root", "99", "remote")
]))
poll_until(events.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events.length >= 1
```

---

## RTPO19 - subscribe() on primitive path receives change events

**Test ID**: `objects/unit/RTPO19/subscribe-primitive-path-0`

**Spec requirement:** A subscription on a path pointing to a primitive (e.g., root.get("name")) fires when the map entry at that key changes.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.get("name").subscribe((event) => events.append(event))
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
ASSERT events.length == 1
ASSERT events[0].object.path() == "name"
```

---

## RTPO19d - subscribe() event provides correct PathObject

**Test ID**: `objects/unit/RTPO19d/event-path-object-correct-0`

**Spec requirement:** RTPO19d1: event.object is a PathObject pointing to the change location.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.subscribe((event) => events.append(event))
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
ASSERT events[0].object IS PathObject
ASSERT events[0].object.path() == "score"
ASSERT events[0].object.value() == 107
```

---

## RTPO21 - subscribeIterator() yields events

**Test ID**: `objects/unit/RTPO21/subscribe-iterator-yields-0`

| Spec | Requirement |
|------|-------------|
| RTPO21b | Returns async iterable of PathObjectSubscriptionEvent |
| RTPO21d | Each iteration yields next event |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
iter = root.get("score").subscribeIterator()
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "99", "remote")
]))

event = AWAIT iter.next()
```

### Assertions
```pseudo
ASSERT event.object IS PathObject
ASSERT event.object.path() == "score"
```

---

## RTPO21 - subscribeIterator() with depth option

**Test ID**: `objects/unit/RTPO21/subscribe-iterator-depth-0`

**Spec requirement:** subscribeIterator accepts same options as subscribe, including depth.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
iter = root.subscribeIterator({ depth: 1 })
```

### Test Steps
```pseudo
// Self event (depth 1 allows)
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "name", { string: "Bob" }, "99", "remote")
]))
event = AWAIT iter.next()

// Child event (depth 1 rejects — counter at depth 2)
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "100", "remote")
]))
```

### Assertions
```pseudo
ASSERT event.object.path() == ""
```

---

## RTPO21 - subscribeIterator() break cleanup

**Test ID**: `objects/unit/RTPO21/subscribe-iterator-break-cleanup-0`

**Spec requirement:** Breaking out of the iterator loop cleans up the underlying subscription.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
received = []
```

### Test Steps
```pseudo
iter = root.get("score").subscribeIterator()

mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 1, "99", "remote")
]))

event = AWAIT iter.next()
received.append(event)

// Break the iterator (cleanup)
iter.return()

// Further events should not be received
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 1, "100", "remote")
]))
```

### Assertions
```pseudo
ASSERT received.length == 1
```

---

## RTPO21 - subscribeIterator() multiple concurrent iterators

**Test ID**: `objects/unit/RTPO21/subscribe-iterator-concurrent-0`

**Spec requirement:** Multiple iterators can coexist independently.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
iter1 = root.get("score").subscribeIterator()
iter2 = root.get("score").subscribeIterator()
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 5, "99", "remote")
]))

event1 = AWAIT iter1.next()
event2 = AWAIT iter2.next()
```

### Assertions
```pseudo
ASSERT event1.object.path() == "score"
ASSERT event2.object.path() == "score"
```
