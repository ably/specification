# PathObject Subscribe Tests

Spec points: `RTPO19`, `RTO24`, `RTO25`

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
| RTPO19d | Returns Subscription object |
| RTPO19e1 | Event.object is a PathObject pointing to change path |
| RTPO19e2 | Event.message is the PublicAPI::ObjectMessage |

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
ASSERT events[0].message.serial == "99"
ASSERT events[0].message.siteCode == "remote"
ASSERT events[0].message.operation IS NOT null
ASSERT events[0].message.operation.action == "COUNTER_INC"
ASSERT events[0].message.channel == "test"
```

---

## RTPO19b - subscribe() checks RTO25 access API preconditions on DETACHED channel

**Test ID**: `objects/unit/RTPO19b/subscribe-precondition-detached-0`

| Spec | Requirement |
|------|-------------|
| RTPO19b | Checks the access API preconditions per RTO25 |
| RTO25b | If channel is DETACHED or FAILED, throw ErrorInfo with statusCode 400 and code 90001 |

Tests that subscribe() on a DETACHED channel throws 90001.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionDetails: {
      connectionId: "conn-1",
      connectionKey: "conn-key-1",
      siteCode: "test-site",
      objectsGCGracePeriod: 86400000
    })
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED, channel: msg.channel, channelSerial: "sync1:", flags: HAS_OBJECTS
      ))
      mock_ws.send_to_client(build_object_sync_message(msg.channel, "sync1:", STANDARD_POOL_OBJECTS))
    ELSE IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED, channel: msg.channel
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: { key: "fake:key", autoConnect: true })
channel = client.channels.get("test", {
  modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"]
})
root = AWAIT channel.object.get()

AWAIT channel.detach()
AWAIT_STATE channel.state == DETACHED
```

### Test Steps
```pseudo
root.subscribe((event) => {}) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 90001
ASSERT error.statusCode == 400
```

---

## RTPO19c1a - subscribe() with non-positive depth throws 40003

**Test ID**: `objects/unit/RTPO19c1a/subscribe-non-positive-depth-throws-0`

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

## RTPO19c1a - subscribe() with negative depth throws 40003

**Test ID**: `objects/unit/RTPO19c1a/subscribe-negative-depth-throws-0`

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

## RTPO19c1 - subscribe() with depth 1 only receives self events

**Test ID**: `objects/unit/RTPO19c1/subscribe-depth-1-self-only-0`

**Spec requirement:** depth=1 means only changes at the exact subscribed path trigger the listener (RTO24c2b).

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.subscribe((event) => events.append(event), { depth: 1 })
// Quiescence control: an unlimited-depth root listener that DOES cover the out-of-scope child path,
// so it fires on the send below and gives us a delivery to await (Negative-assertion quiescence,
// helpers/standard_test_pool.md).
control = []
root.subscribe((event) => control.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "name", { string: "Bob" }, remote_serial(0), "remote")
]))
poll_until(events.length >= 1, timeout: 5s)

control_before = control.length
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "100", "remote")
]))
// Negative-assertion quiescence: the unlimited-depth control covers ["score"], so await its delivery
// for this dispatch, THEN assert the depth-1 listener did NOT fire on the out-of-scope child update.
poll_until(control.length > control_before, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events.length == 1
```

---

## RTPO19c1 - subscribe() with depth 2 receives self and children

**Test ID**: `objects/unit/RTPO19c1/subscribe-depth-2-children-0`

**Spec requirement:** depth=2 means changes at the subscribed path and one level of children trigger the listener (RTO24c2c).

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.subscribe((event) => events.append(event), { depth: 2 })
// Quiescence control: an unlimited-depth root listener that covers the out-of-scope grandchild path,
// so it fires on the send below (Negative-assertion quiescence, helpers/standard_test_pool.md).
control = []
root.subscribe((event) => control.append(event))
```

### Test Steps
```pseudo
// Self event (root map update) — candidate [] is covered at depth 2.
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "name", { string: "Bob" }, remote_serial(0), "remote")
]))
poll_until(events.length >= 1, timeout: 5s)

// Child event (root["score"] counter) — candidate ["score"], relativeDepth 1-0+1 = 2 <= 2, covered.
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "100", "remote")
]))
poll_until(events.length >= 2, timeout: 5s)

// Grandchild event (root["profile"]["nested_counter"] counter) — candidate ["profile","nested_counter"],
// relativeDepth 2-0+1 = 3 > 2, NOT covered. A COUNTER_INC yields ONLY this single candidate (no key
// candidate), unlike a MAP_SET on a child map which would also emit the covered parent-map path (RTO24b2a1).
control_before = control.length
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:nested@1000", 1, "101", "remote")
]))
// Negative-assertion quiescence: the unlimited-depth control covers ["profile","nested_counter"], so await
// its delivery for this dispatch, THEN assert the depth-2 listener did NOT fire on the grandchild update.
poll_until(control.length > control_before, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events.length == 2
```

---

## RTPO19c1 - subscribe() with no depth receives all descendants

**Test ID**: `objects/unit/RTPO19c1/subscribe-unlimited-depth-0`

**Spec requirement:** If depth is undefined, subscription receives events at any depth (RTO24c2a).

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.subscribe((event) => events.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "name", { string: "Bob" }, remote_serial(0), "remote")
]))
poll_until(events.length >= 1, timeout: 5s)

mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "100", "remote")
]))
poll_until(events.length >= 2, timeout: 5s)

mock_ws.send_to_client(build_object_message("test", [
  build_map_set("map:prefs@1000", "theme", { string: "light" }, remote_serial(1), "remote")
]))
poll_until(events.length >= 3, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events.length >= 3
```

---

## RTPO19d - subscribe() returns Subscription with unsubscribe()

**Test ID**: `objects/unit/RTPO19d/subscribe-returns-subscription-0`

**Spec requirement:** RTPO19d: subscribe returns a Subscription (SUB1) object. Calling unsubscribe() deregisters the listener.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
sub = root.get("score").subscribe((event) => events.append(event))
// Quiescence control: a separate, still-subscribed listener on the same (live) object that WILL fire
// on the send below, giving a delivery to await (Negative-assertion quiescence, helpers/standard_test_pool.md).
control = []
root.get("score").subscribe((event) => control.append(event))
```

### Test Steps
```pseudo
ASSERT sub IS Subscription
sub.unsubscribe()

mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "99", "remote")
]))
// Negative-assertion quiescence: the separate control listener (still subscribed) fires on this
// dispatch; await it, THEN assert the unsubscribed listener did not fire.
poll_until(control.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events.length == 0
```

---

## RTPO19e1 - subscribe() event provides correct PathObject

**Test ID**: `objects/unit/RTPO19e1/event-path-object-correct-0`

**Spec requirement:** RTPO19e1: event.object is a PathObject pointing to the change location.

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

## RTPO19e2 - subscribe() event delivers PublicAPI::ObjectMessage for operations

**Test ID**: `objects/unit/RTPO19e2/event-message-delivery-0`

| Spec | Requirement |
|------|-------------|
| RTPO19e2 | event.message is a PublicAPI::ObjectMessage derived from the LiveObjectUpdate.objectMessage per PAOM3 |
| RTO24b2b2 | message populated when objectMessage has an operation field |

Tests that the event delivered to a subscription listener includes a `message` field containing a `PublicAPI::ObjectMessage` with the correct fields copied from the source ObjectMessage.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.get("score").subscribe((event) => events.append(event))
```

### Test Steps
```pseudo
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 42, "serial-1", "site-a")
]))
poll_until(events.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events[0].message IS NOT null
ASSERT events[0].message.channel == "test"
ASSERT events[0].message.serial == "serial-1"
ASSERT events[0].message.siteCode == "site-a"
ASSERT events[0].message.operation IS NOT null
ASSERT events[0].message.operation.action == "COUNTER_INC"
ASSERT events[0].message.operation.objectId == "counter:score@1000"
ASSERT events[0].message.operation.counterInc.number == 42
```

---

## RTPO19e2 - subscribe() event omits message when objectMessage has no operation

**Test ID**: `objects/unit/RTPO19e2/event-message-omitted-no-operation-0`

**Spec requirement:** RTPO19e2: if the objectMessage's operation field is not populated, message is omitted.

Tests that events triggered by non-operation updates (e.g. sync-only changes) do not include a message field.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.subscribe((event) => events.append(event))
```

### Test Steps
```pseudo
// Send an OBJECT_SYNC that changes counter:score@1000's state (100 -> 200) via replaceData
// (RTLC6) — a sync-triggered update, so its objectMessage has no `operation` field.
// The sync intentionally omits `root`: per RTO5c2a the root object must never be removed from
// the pool (RTO3b), so root is retained and still references "score" — counter:score therefore
// stays reachable and its sync-triggered update dispatches to the root subscription (message
// omitted). (This also exercises RTO5c2a: a compliant SDK must not GC root just because a
// completed sync omitted it.)
mock_ws.send_to_client(ProtocolMessage(
  action: OBJECT_SYNC,
  channel: "test",
  channelSerial: "sync2:",
  state: [
    build_object_state("counter:score@1000", {"aaa": "t:1"}, {
      counter: { count: 0 },
      createOp: { counterCreate: { count: 200 } }
    })
  ]
))
poll_until(events.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
// Events from sync-triggered updates should have no message
FOR event IN events:
  ASSERT event.message IS null OR event.message IS undefined
```

---

## RTPO19f - subscribe() follows path not identity

**Test ID**: `objects/unit/RTPO19f/subscribe-follows-path-0`

**Spec requirement:** RTPO19f: subscription is registered by path, so if the object at the path changes identity, the subscription continues to deliver events for the new object.

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
  build_map_set("root", "score", { objectId: "counter:new@2000" }, remote_serial(0), "remote")
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
  build_map_set("root", "name", { string: "Bob" }, remote_serial(0), "remote")
]))
poll_until(events.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events.length == 1
ASSERT events[0].object.path() == "name"
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

## RTPO19 - child events bubble up to parent subscription

**Test ID**: `objects/unit/RTPO19/child-events-bubble-0`

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
  build_map_set("map:profile@1000", "email", { string: "bob@example.com" }, remote_serial(0), "remote")
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

## RTO24c1 - depth filtering formula

**Test ID**: `objects/unit/RTO24c1/depth-filtering-formula-0`

| Spec | Requirement |
|------|-------------|
| RTO24c1 | subPath is a prefix of eventPath AND (depth null OR eventPath.length - subPath.length + 1 <= depth) |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
// Seed a grandchild OBJECT under profile.prefs (path ["profile","prefs","deep"]) so the grandchild
// stimulus below can be a COUNTER_INC yielding ONLY that single depth-3 candidate. Sent BEFORE
// subscribing, so it does not fire the listener under test. (RTO6 zero-value-creates counter:deep@3000.)
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("map:prefs@1000", "deep", { objectId: "counter:deep@3000" }, "50", "remote")
]))
events = []
// Subscribe at "profile" with depth 2:
// self (profile)          -> eventPath=["profile"],                  1 - 1 + 1 = 1 <= 2  yes
// child (profile.nested)  -> eventPath=["profile","nested_counter"], 2 - 1 + 1 = 2 <= 2  yes
// grandchild (prefs.deep) -> eventPath=["profile","prefs","deep"],   3 - 1 + 1 = 3 > 2   no
root.get("profile").subscribe((event) => events.append(event), { depth: 2 })
// Quiescence control: an unlimited-depth root listener that covers the out-of-scope grandchild path,
// so it fires on the grandchild send below (Negative-assertion quiescence, helpers/standard_test_pool.md).
control = []
root.subscribe((event) => control.append(event))
```

### Test Steps
```pseudo
// Self event (profile map update) — first covered candidate is ["profile"].
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("map:profile@1000", "email", { string: "bob@example.com" }, remote_serial(0), "remote")
]))
poll_until(events.length >= 1, timeout: 5s)

// Child event (nested counter at ["profile","nested_counter"], relativeDepth 2) — covered.
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:nested@1000", 3, "100", "remote")
]))
poll_until(events.length >= 2, timeout: 5s)

// Grandchild event (counter:deep at ["profile","prefs","deep"], relativeDepth 3) — should NOT be received.
// A COUNTER_INC yields ONLY this single depth-3 candidate (no shallower covered candidate, unlike a
// MAP_SET on map:prefs which would also emit the covered ["profile","prefs"] path per RTO24b2a1).
control_before = control.length
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:deep@3000", 1, "101", "remote")
]))
// Negative-assertion quiescence: the unlimited-depth control covers ["profile","prefs","deep"], so
// await its delivery for this dispatch, THEN assert the depth-2 listener did NOT fire on the grandchild.
poll_until(control.length > control_before, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events.length == 2
```

---

## RTO24c1 - prefix mismatch does not trigger subscription

**Test ID**: `objects/unit/RTO24c1/prefix-mismatch-0`

| Spec | Requirement |
|------|-------------|
| RTO24c1 | subPath must be a prefix of eventPath |
| RTO24c2d | ["admins"] and ["userPosts"] not covered by subscription at ["users"] |

Tests that a subscription at one path does not receive events for a sibling path that is not a prefix match.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
profile_events = []
root.get("profile").subscribe((event) => profile_events.append(event))
// Control listener at root: fires on both out-of-scope sends below, providing a
// delivery to await on the same dispatch (Negative-assertion quiescence,
// helpers/standard_test_pool.md) before asserting profile_events is unchanged.
control_events = []
root.subscribe((event) => control_events.append(event))
```

### Test Steps
```pseudo
// Change at "score" — "profile" is not a prefix of "score"
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 7, "99", "remote")
]))

// Change at "name" — "profile" is not a prefix of "name"
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "name", { string: "Bob" }, remote_serial(0), "remote")
]))
// QUIESCENCE: await the control listener (fires for both sends) so that any
// profile_events callback would also have run before we assert it is unchanged.
poll_until(control_events.length >= 2, timeout: 5s)
```

### Assertions
```pseudo
ASSERT profile_events.length == 0
```

---

## RTO24b2a - candidate path construction includes map update keys

**Test ID**: `objects/unit/RTO24b2a/candidate-paths-map-keys-0`

| Spec | Requirement |
|------|-------------|
| RTO24b2a1 | First candidate is pathToThis itself |
| RTO24b2a2 | For LiveMapUpdate, append pathToThis extended by each update key |

Tests that when a MAP_SET updates a key on a map, subscriptions on the child path (pathToThis + key) are notified, not just subscriptions on the map itself.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
score_events = []
root_events = []
// Subscribe at the child path "score" (pathToThis=[""] + key "score" = ["score"])
root.get("score").subscribe((event) => score_events.append(event))
// Subscribe at root path (pathToThis=[""])
root.subscribe((event) => root_events.append(event))
```

### Test Steps
```pseudo
// MAP_SET on root with key "score" — generates candidates:
//   1. pathToThis = [] (root itself)
//   2. [] + "score" = ["score"] (from the map update key)
// Both subscriptions should fire
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "score", { objectId: "counter:new@2000" }, remote_serial(0), "remote")
]))
poll_until(score_events.length >= 1, timeout: 5s)
poll_until(root_events.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT score_events.length == 1
ASSERT score_events[0].object.path() == "score"
ASSERT root_events.length == 1
```

---

## RTO24b2c - listener exception does not affect other listeners

**Test ID**: `objects/unit/RTO24b2c/listener-exception-caught-0`

**Spec requirement:** If a listener throws, the error is caught and logged without affecting other subscriptions or other pathToThis iterations.

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
  build_map_set("root", "name", { string: "Bob" }, remote_serial(0), "remote")
]))
poll_until(events.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events.length == 1
```

---

## RTO24b1 - dispatch via getFullPaths for multi-path objects

**Test ID**: `objects/unit/RTO24b1/multi-path-dispatch-0`

| Spec | Requirement |
|------|-------------|
| RTO24b1 | Let pathsToThis be the set of paths returned by getFullPaths on the LiveObject |
| RTO24b2 | For each pathToThis, construct candidates and dispatch |

Tests that when a LiveObject is reachable via multiple paths, subscriptions on all those paths receive events. We create this by adding a second reference to the same counter.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events_score = []
events_alias = []

// "score" already points to counter:score@1000.
// Add a second reference "alias" -> counter:score@1000 so it has two paths.
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "alias", { objectId: "counter:score@1000" }, "98", "remote")
]))

root.get("score").subscribe((event) => events_score.append(event))
root.get("alias").subscribe((event) => events_alias.append(event))
```

### Test Steps
```pseudo
// Increment counter:score@1000 — getFullPaths returns ["score"] and ["alias"]
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 5, "99", "remote")
]))
poll_until(events_score.length >= 1, timeout: 5s)
poll_until(events_alias.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
ASSERT events_score.length == 1
ASSERT events_score[0].object.path() == "score"
ASSERT events_alias.length == 1
ASSERT events_alias[0].object.path() == "alias"
```

---

## RTO24b2b - subscription fires exactly once per dispatch

**Test ID**: `objects/unit/RTO24b2b/fires-once-per-dispatch-0`

| Spec | Requirement |
|------|-------------|
| RTO24b2b | Find the first eventPath in candidatePaths that the subscription covers; call the listener exactly once |

Tests that when a MAP_SET generates multiple candidate paths that a subscription covers, the listener is called exactly once with the first (most preferred) candidate.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
// Subscribe at root (unlimited depth) — covers both [] and ["score"]
root.subscribe((event) => events.append(event))
```

### Test Steps
```pseudo
// MAP_SET on root with key "score" — candidates are [] and ["score"]
// Root subscription covers both, but should fire exactly once with
// the first candidate (pathToThis = [])
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "score", { objectId: "counter:new@2000" }, remote_serial(0), "remote")
]))
poll_until(events.length >= 1, timeout: 5s)

// QUIESCENCE: a second, single-candidate dispatch acts as the control delivery
// (Negative-assertion quiescence, helpers/standard_test_pool.md). Awaiting it
// guarantees any spurious second callback from the first (multi-candidate)
// dispatch would already have run, so events.length == 2 confirms the first
// dispatch fired exactly once.
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:new@2000", 1, "100", "remote")
]))
poll_until(events.length >= 2, timeout: 5s)
```

### Assertions
```pseudo
// Exactly one event per dispatch, even though multiple candidates match:
// one from the multi-candidate MAP_SET + one from the control increment.
ASSERT events.length == 2
```
