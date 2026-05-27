# RealtimeObject Tests

Spec points: `RTO2`, `RTO10`, `RTO15`, `RTO17`–`RTO20`, `RTO22`–`RTO26`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Shared Helpers

See `helpers/standard_test_pool.md` for `setup_synced_channel`, `setup_synced_channel_no_ack`, and builder functions.

---

## RTO23 - get() returns PathObject wrapping root

**Test ID**: `objects/unit/RTO23/get-returns-path-object-0`

| Spec | Requirement |
|------|-------------|
| RTO23d | Returns PathObject with path set to empty list and root set to root LiveMap |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root IS PathObject
ASSERT root.path == []
```

---

## RTO23a - get() requires OBJECT_SUBSCRIBE mode

**Test ID**: `objects/unit/RTO23a/get-requires-subscribe-mode-0`

**Spec requirement:** Requires OBJECT_SUBSCRIBE channel mode per RTO2.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionDetails: {
      connectionId: "conn-1", connectionKey: "key-1", siteCode: "test-site"
    })
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED, channel: msg.channel, channelSerial: "sync1:", flags: HAS_OBJECTS
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_PUBLISH"] })
```

### Test Steps
```pseudo
AWAIT channel.object.get() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40024
```

---

## RTO23b - get() throws on DETACHED channel

**Test ID**: `objects/unit/RTO23b/get-throws-detached-0`

| Spec | Requirement |
|------|-------------|
| RTO23b | If channel is DETACHED or FAILED, throw ErrorInfo with statusCode 400 and code 90001 |

Tests that get() on a DETACHED channel throws 90001 per the RTO25 access API preconditions.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionDetails: {
      connectionId: "conn-1", connectionKey: "key-1", siteCode: "test-site"
    })
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED, channel: msg.channel, channelSerial: "sync1:",
        flags: HAS_OBJECTS
      ))
      mock_ws.send_to_client(build_object_sync_message(msg.channel, "sync1:", STANDARD_POOL_OBJECTS))
    ELSE IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED, channel: msg.channel
      ))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE"] })
```

### Test Steps
```pseudo
// Attach and sync first, then detach
AWAIT channel.object.get()
AWAIT channel.detach()
AWAIT_STATE channel.state == DETACHED

AWAIT channel.object.get() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 90001
ASSERT error.statusCode == 400
```

---

## RTO23c - get() waits for SYNCED state

**Test ID**: `objects/unit/RTO23c/get-waits-for-synced-0`

**Spec requirement:** If sync state is not SYNCED, waits for SYNCED transition.

### Setup
```pseudo
attach_sent = false
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionDetails: {
      connectionId: "conn-1", connectionKey: "key-1", siteCode: "test-site",
      objectsGCGracePeriod: 86400000
    })
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_sent = true
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED, channel: msg.channel, channelSerial: "sync1:cursor",
        flags: HAS_OBJECTS
      ))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
```

### Test Steps
```pseudo
get_future = channel.object.get()

poll_until(attach_sent, timeout: 5s)

mock_ws.send_to_client(build_object_sync_message(
  "test", "sync1:", STANDARD_POOL_OBJECTS
))

root = AWAIT get_future
```

### Assertions
```pseudo
ASSERT root IS PathObject
ASSERT root.path == []
```

---

## RTO15 - publish sends OBJECT ProtocolMessage

**Test ID**: `objects/unit/RTO15/publish-sends-object-pm-0`

| Spec | Requirement |
|------|-------------|
| RTO15e1 | action set to OBJECT |
| RTO15e2 | channel set to channel name |
| RTO15e3 | state set to encoded ObjectMessages |
| RTO15h | Returns PublishResult from ACK |

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
        action: ATTACHED, channel: msg.channel, channelSerial: "sync1:",
        flags: HAS_OBJECTS
      ))
      mock_ws.send_to_client(build_object_sync_message("test", "sync1:", STANDARD_POOL_OBJECTS))
    ELSE IF msg.action == OBJECT:
      captured_messages.append(msg)
      mock_ws.send_to_client(build_ack_message(msg.msgSerial, ["serial-0"]))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
AWAIT channel.object.get()
```

### Test Steps
```pseudo
result = AWAIT channel.object.publish([
  build_counter_inc("counter:score@1000", 5, null, null)
])
```

### Assertions
```pseudo
ASSERT captured_messages.length == 1
ASSERT captured_messages[0].action == OBJECT
ASSERT captured_messages[0].channel == "test"
ASSERT captured_messages[0].state.length == 1
ASSERT result.serials == ["serial-0"]
```

---

## RTO20 - publishAndApply applies locally on ACK

**Test ID**: `objects/unit/RTO20/publish-and-apply-local-0`

| Spec | Requirement |
|------|-------------|
| RTO20b | Calls publish and awaits PublishResult |
| RTO20d2a | Synthetic message serial from PublishResult |
| RTO20d2b | Synthetic message siteCode from ConnectionDetails |
| RTO20f | Apply synthetic messages with source LOCAL |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.increment(10)
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 110
```

---

## RTO20c - publishAndApply logs error when siteCode missing

**Test ID**: `objects/unit/RTO20c/missing-site-code-0`

| Spec | Requirement |
|------|-------------|
| RTO20c1 | Requires siteCode from ConnectionDetails |

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionDetails: {
      connectionId: "conn-1", connectionKey: "key-1",
      objectsGCGracePeriod: 86400000
    })
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED, channel: msg.channel, channelSerial: "sync1:",
        flags: HAS_OBJECTS
      ))
      mock_ws.send_to_client(build_object_sync_message("test", "sync1:", STANDARD_POOL_OBJECTS))
    ELSE IF msg.action == OBJECT:
      mock_ws.send_to_client(build_ack_message(msg.msgSerial, ["serial-0"]))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()
```

### Test Steps
```pseudo
AWAIT root.increment(10)
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 100
```

---

## RTO20d1 - null serial in PublishResult is skipped

**Test ID**: `objects/unit/RTO20d1/null-serial-skipped-0`

**Spec requirement:** If serial from PublishResult is null, skip that ObjectMessage.

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
      mock_ws.send_to_client(build_object_sync_message("test", "sync1:", STANDARD_POOL_OBJECTS))
    ELSE IF msg.action == OBJECT:
      mock_ws.send_to_client(build_ack_message(msg.msgSerial, [null]))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()
```

### Test Steps
```pseudo
AWAIT root.increment(10)
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 100
```

---

## RTO20e - publishAndApply waits for SYNCED during SYNCING

**Test ID**: `objects/unit/RTO20e/waits-for-synced-0`

**Spec requirement:** If sync state is not SYNCED, wait for SYNCED transition.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync2:cursor",
  flags: HAS_OBJECTS
))

inc_future = root.increment(10)

mock_ws.send_to_client(build_object_sync_message("test", "sync2:", STANDARD_POOL_OBJECTS))

AWAIT inc_future
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 110
```

---

## RTO20e1 - publishAndApply fails when channel enters FAILED during sync wait

**Test ID**: `objects/unit/RTO20e1/fails-on-channel-failed-0`

**Spec requirement:** If channel enters DETACHED/SUSPENDED/FAILED while waiting, fail with 92008.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync2:cursor",
  flags: HAS_OBJECTS
))

inc_future = root.increment(10)

mock_ws.send_to_client(ProtocolMessage(
  action: DETACHED, channel: "test",
  error: { code: 90000, statusCode: 400, message: "Channel detached" }
))

AWAIT inc_future FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92008
```

---

## RTO17, RTO18 - Sync state events

**Test ID**: `objects/unit/RTO17/sync-state-events-0`

| Spec | Requirement |
|------|-------------|
| RTO17b | Emit event matching new sync state |
| RTO18b1 | SYNCING event |
| RTO18b2 | SYNCED event |
| RTO18e | Listeners called with no arguments |

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
        action: ATTACHED, channel: msg.channel, channelSerial: "sync1:cursor",
        flags: HAS_OBJECTS
      ))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })

events = []
channel.object.on(SYNCING, () => events.append("SYNCING"))
channel.object.on(SYNCED, () => events.append("SYNCED"))
```

### Test Steps
```pseudo
get_future = channel.object.get()

poll_until(events.length >= 1, timeout: 5s)

mock_ws.send_to_client(build_object_sync_message("test", "sync1:", STANDARD_POOL_OBJECTS))

AWAIT get_future
```

### Assertions
```pseudo
ASSERT events CONTAINS_IN_ORDER ["SYNCING", "SYNCED"]
```

---

## RTO18d - Duplicate listener registered twice fires twice

**Test ID**: `objects/unit/RTO18d/duplicate-listener-0`

**Spec requirement:** If same listener registered twice, it is invoked twice per event.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
call_count = 0
listener = () => { call_count++ }
channel.object.on(SYNCED, listener)
channel.object.on(SYNCED, listener)
```

### Test Steps
```pseudo
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync2:cursor", flags: HAS_OBJECTS
))
mock_ws.send_to_client(build_object_sync_message("test", "sync2:", STANDARD_POOL_OBJECTS))

poll_until(call_count >= 2, timeout: 5s)
```

### Assertions
```pseudo
ASSERT call_count == 2
```

---

## RTO19 - off() deregisters listener

**Test ID**: `objects/unit/RTO19/off-deregisters-0`

**Spec requirement:** Deregisters event listener previously registered via on().

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
call_count = 0
listener = () => { call_count++ }
sub = channel.object.on(SYNCED, listener)
sub.off()
```

### Test Steps
```pseudo
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync2:cursor", flags: HAS_OBJECTS
))
mock_ws.send_to_client(build_object_sync_message("test", "sync2:", STANDARD_POOL_OBJECTS))
```

### Assertions
```pseudo
ASSERT call_count == 0
```

---

## RTO2 - Channel mode enforcement

**Test ID**: `objects/unit/RTO2/mode-enforcement-0`

| Spec | Requirement |
|------|-------------|
| RTO2a | ATTACHED state checks granted modes |
| RTO2b | Non-ATTACHED checks requested modes |
| RTO2a2 | Missing mode throws 40024 |

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
        flags: HAS_OBJECTS,
        modes: ["OBJECT_SUBSCRIBE"]
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
AWAIT root.set("name", "Bob") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40024
```

---

## RTO25a - Access API precondition requires OBJECT_SUBSCRIBE mode

**Test ID**: `objects/unit/RTO25a/access-requires-subscribe-mode-0`

| Spec | Requirement |
|------|-------------|
| RTO25a | Require OBJECT_SUBSCRIBE channel mode per RTO2 |

Tests that a read operation (e.g. PathObject value()) without OBJECT_SUBSCRIBE mode throws error 40024.

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
        flags: HAS_OBJECTS,
        modes: ["OBJECT_PUBLISH"]
      ))
      mock_ws.send_to_client(build_object_sync_message(msg.channel, "sync1:", STANDARD_POOL_OBJECTS))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_PUBLISH"] })
```

### Test Steps
```pseudo
AWAIT channel.object.get() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40024
ASSERT error.statusCode == 400
```

---

## RTO25b - Access API precondition throws on DETACHED channel

**Test ID**: `objects/unit/RTO25b/access-throws-detached-0`

| Spec | Requirement |
|------|-------------|
| RTO25b | If channel is DETACHED or FAILED, throw ErrorInfo with statusCode 400 and code 90001 |

Tests that calling get() on a DETACHED channel throws 90001.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionDetails: {
      connectionId: "conn-1", connectionKey: "key-1", siteCode: "test-site"
    })
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED, channel: msg.channel, channelSerial: "sync1:",
        flags: HAS_OBJECTS
      ))
      mock_ws.send_to_client(build_object_sync_message(msg.channel, "sync1:", STANDARD_POOL_OBJECTS))
    ELSE IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED, channel: msg.channel
      ))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE"] })
```

### Test Steps
```pseudo
// Attach, sync, then detach to get channel into DETACHED state
AWAIT channel.object.get()
AWAIT channel.detach()
AWAIT_STATE channel.state == DETACHED

AWAIT channel.object.get() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 90001
ASSERT error.statusCode == 400
```

---

## RTO25b - Access API precondition throws on FAILED channel

**Test ID**: `objects/unit/RTO25b/access-throws-failed-0`

| Spec | Requirement |
|------|-------------|
| RTO25b | If channel is DETACHED or FAILED, throw ErrorInfo with statusCode 400 and code 90001 |

Tests that calling get() on a FAILED channel throws 90001.

### Setup
```pseudo
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionDetails: {
      connectionId: "conn-1", connectionKey: "key-1", siteCode: "test-site"
    })
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ERROR, channel: msg.channel,
        error: { code: 90000, statusCode: 400, message: "Channel error" }
      ))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE"] })
```

### Test Steps
```pseudo
// Trigger attach which will fail, putting channel into FAILED state
channel.attach()
AWAIT_STATE channel.state == FAILED

AWAIT channel.object.get() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 90001
ASSERT error.statusCode == 400
```

---

## RTO26a - Write API precondition requires OBJECT_PUBLISH mode

**Test ID**: `objects/unit/RTO26a/write-requires-publish-mode-0`

| Spec | Requirement |
|------|-------------|
| RTO26a | Require OBJECT_PUBLISH channel mode per RTO2 |

Tests that a write operation without OBJECT_PUBLISH mode throws error 40024.

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
        flags: HAS_OBJECTS,
        modes: ["OBJECT_SUBSCRIBE"]
      ))
      mock_ws.send_to_client(build_object_sync_message(msg.channel, "sync1:", STANDARD_POOL_OBJECTS))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE"] })
root = AWAIT channel.object.get()
```

### Test Steps
```pseudo
AWAIT root.set("name", "Bob") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40024
ASSERT error.statusCode == 400
```

---

## RTO26b - Write API precondition throws on DETACHED channel

**Test ID**: `objects/unit/RTO26b/write-throws-detached-0`

| Spec | Requirement |
|------|-------------|
| RTO26b | If channel is DETACHED, FAILED, or SUSPENDED, throw ErrorInfo with statusCode 400 and code 90001 |

Tests that a write operation on a DETACHED channel throws 90001.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
// Detach the channel after sync
mock_ws.send_to_client(ProtocolMessage(
  action: DETACHED, channel: "test",
  error: { code: 90000, statusCode: 400, message: "Channel detached" }
))
AWAIT_STATE channel.state == DETACHED

AWAIT root.set("name", "Bob") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 90001
ASSERT error.statusCode == 400
```

---

## RTO26b - Write API precondition throws on FAILED channel

**Test ID**: `objects/unit/RTO26b/write-throws-failed-0`

| Spec | Requirement |
|------|-------------|
| RTO26b | If channel is DETACHED, FAILED, or SUSPENDED, throw ErrorInfo with statusCode 400 and code 90001 |

Tests that a write operation on a FAILED channel throws 90001.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
// Force channel to FAILED state
mock_ws.send_to_client(ProtocolMessage(
  action: ERROR, channel: "test",
  error: { code: 90000, statusCode: 400, message: "Channel error" }
))
AWAIT_STATE channel.state == FAILED

AWAIT root.set("name", "Bob") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 90001
ASSERT error.statusCode == 400
```

---

## RTO26c - Write API precondition throws when echoMessages is false

**Test ID**: `objects/unit/RTO26c/write-throws-echo-disabled-0`

| Spec | Requirement |
|------|-------------|
| RTO26c | If echoMessages is false, throw ErrorInfo with statusCode 400 and code 40000 |

Tests that a write operation with echoMessages disabled throws 40000.

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
AWAIT root.set("name", "Bob") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40000
ASSERT error.statusCode == 400
```

---

## RTO24a - RealtimeObject maintains a single PathObjectSubscriptionRegister

**Test ID**: `objects/unit/RTO24a/single-register-instance-0`

**Spec requirement:** The RealtimeObject instance maintains a single PathObjectSubscriptionRegister that manages all path-based subscriptions for the channel.

Tests that subscriptions registered via different PathObjects on the same channel share a single register, so updates are dispatched to all matching subscriptions regardless of which PathObject was used to subscribe.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")

events_root = []
events_score = []

// Subscribe via root PathObject at path []
root.subscribe((event) => events_root.append(event))

// Subscribe via a deeper PathObject at path ["score"]
score_path = root.get("score")
score_path.subscribe((event) => events_score.append(event))
```

### Test Steps
```pseudo
// Trigger an update on the score counter
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 5, "s:1", "aaa")
]))

poll_until(events_score.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
// Both subscriptions are managed by the same register and both fire
ASSERT events_root.length >= 1
ASSERT events_score.length >= 1
```

---

## RTO24c1 - Subscription coverage: prefix match with depth constraint

**Test ID**: `objects/unit/RTO24c1/coverage-prefix-depth-0`

| Spec | Requirement |
|------|-------------|
| RTO24c1 | Subscription covers eventPath if subPath is prefix and depth constraint satisfied |

Tests that a subscription with a depth constraint only receives events within the specified depth.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")

shallow_events = []
deep_events = []

// Subscribe at root with depth 1 — covers root and immediate children only
root.subscribe({ depth: 1 }, (event) => shallow_events.append(event))

// Subscribe at root with no depth limit — covers everything
root.subscribe((event) => deep_events.append(event))
```

### Test Steps
```pseudo
// Update a direct child of root (path ["score"]) — depth 1 from root
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 5, "s:1", "aaa")
]))
poll_until(deep_events.length >= 1, timeout: 5s)

// Update a nested object (path ["profile", "nested_counter"]) — depth 2 from root
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:nested@1000", 1, "s:2", "aaa")
]))
poll_until(deep_events.length >= 2, timeout: 5s)
```

### Assertions
```pseudo
// Shallow subscription (depth 1) only sees the direct child update
ASSERT shallow_events.length == 1

// Deep subscription (no depth limit) sees both updates
ASSERT deep_events.length >= 2
```

---

## RTO10 - GC removes tombstoned objects past grace period

**Test ID**: `objects/unit/RTO10/gc-tombstoned-objects-0`

| Spec | Requirement |
|------|-------------|
| RTO10a | Check at regular intervals |
| RTO10c1b | Remove if difference >= grace period |
| RTO10b1 | Grace period from ConnectionDetails |

### Setup
```pseudo
enable_fake_timers()
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")

mock_ws.send_to_client(build_object_message("test", [
  build_object_delete("counter:score@1000", "99", "site1", 1000)
]))
```

### Test Steps
```pseudo
ADVANCE_TIME(86400000 + 300000)
```

### Assertions
```pseudo
ASSERT root.get("score").value() == null
```

---

## RTO20 - Echo deduplication via appliedOnAckSerials

**Test ID**: `objects/unit/RTO20/echo-dedup-0`

**Spec requirement:** When echo arrives with same serial as applied-on-ACK, it is deduplicated.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.increment(10)
score_after_apply = root.get("score").value()

mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 10, "ack-0:0", "test-site")
]))
score_after_echo = root.get("score").value()
```

### Assertions
```pseudo
ASSERT score_after_apply == 110
ASSERT score_after_echo == 110
```

---

## RTO20f - Apply-on-ACK does not update siteTimeserials

**Test ID**: `objects/unit/RTO20f/ack-no-site-timeserials-update-0`

| Spec | Requirement |
|------|-------------|
| RTO20f | Apply with source LOCAL |
| RTLC7c2 | LOCAL source does not update siteTimeserials |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
site_serials_before = root.get("score").instance()._liveObject.siteTimeserials
```

### Test Steps
```pseudo
AWAIT root.increment(10)
site_serials_after = root.get("score").instance()._liveObject.siteTimeserials
```

### Assertions
```pseudo
ASSERT site_serials_after == site_serials_before
```

---

## RTO20 - ACK after echo does not double-apply

**Test ID**: `objects/unit/RTO20/ack-after-echo-no-double-apply-0`

**Spec requirement:** If the echo arrives before the ACK is processed, the ACK-based apply finds the serial already applied and deduplicates via RTO9a3.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel_no_ack("test")
```

### Test Steps
```pseudo
inc_future = root.increment(10)

// Send the echo BEFORE the ACK
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 10, "ack-0:0", "test-site")
]))

// Now send the ACK
mock_ws.send_to_client(build_ack_message(0, ["ack-0:0"]))

AWAIT inc_future
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 110
```

---

## RTO5c9, RTO20 - appliedOnAckSerials cleared on re-sync

**Test ID**: `objects/unit/RTO5c9-RTO20/ack-serials-cleared-on-resync-0`

**Spec requirement:** appliedOnAckSerials is cleared when sync completes. After re-sync, an echo with a previously-applied serial is applied normally (not deduplicated).

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.increment(10)
ASSERT root.get("score").value() == 110

// Trigger re-sync
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync2:cursor", flags: HAS_OBJECTS
))
mock_ws.send_to_client(build_object_sync_message("test", "sync2:", STANDARD_POOL_OBJECTS))

// After re-sync, the score is back to 100 (from pool state)
ASSERT root.get("score").value() == 100
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 100
```

---

## RTO20 - Subscription fires on apply-on-ACK

**Test ID**: `objects/unit/RTO20/subscription-fires-on-ack-apply-0`

**Spec requirement:** When publishAndApply applies locally via ACK, subscription listeners are notified.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
events = []
root.get("score").subscribe((event) => events.append(event))
```

### Test Steps
```pseudo
AWAIT root.increment(10)
```

### Assertions
```pseudo
ASSERT events.length >= 1
ASSERT root.get("score").value() == 110
```

---

## RTO23 - get() implicitly attaches channel

**Test ID**: `objects/unit/RTO23/get-implicit-attach-0`

**Spec requirement:** get() triggers attach if channel is not yet attached.

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
    ELSE IF msg.action == OBJECT:
      serials = msg.state.map((_, i) => "ack-" + msg.msgSerial + ":" + i)
      mock_ws.send_to_client(build_ack_message(msg.msgSerial, serials))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
```

### Test Steps
```pseudo
ASSERT channel.state == INITIALIZED
root = AWAIT channel.object.get()
```

### Assertions
```pseudo
ASSERT root IS PathObject
ASSERT root.path == []
ASSERT channel.state == ATTACHED
```

---

## RTO23d - get() resolves immediately when already SYNCED

**Test ID**: `objects/unit/RTO23d/get-resolves-immediately-synced-0`

**Spec requirement:** If sync state is already SYNCED, get() resolves immediately.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
root2 = AWAIT channel.object.get()
```

### Assertions
```pseudo
ASSERT root2 IS PathObject
ASSERT root2.path == []
```

---

## RTO10b1 - GC grace period from ConnectionDetails

**Test ID**: `objects/unit/RTO10b1/gc-grace-period-source-0`

**Spec requirement:** GC grace period comes from ConnectionDetails.objectsGCGracePeriod.

### Setup
```pseudo
enable_fake_timers()
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionDetails: {
      connectionId: "conn-1", connectionKey: "key-1", siteCode: "test-site",
      objectsGCGracePeriod: 5000
    })
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED, channel: msg.channel, channelSerial: "sync1:",
        flags: HAS_OBJECTS
      ))
      mock_ws.send_to_client(build_object_sync_message(msg.channel, "sync1:", STANDARD_POOL_OBJECTS))
    ELSE IF msg.action == OBJECT:
      serials = msg.state.map((_, i) => "ack-" + msg.msgSerial + ":" + i)
      mock_ws.send_to_client(build_ack_message(msg.msgSerial, serials))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()

mock_ws.send_to_client(build_object_message("test", [
  build_object_delete("counter:score@1000", "99", "site1", 1000)
]))
```

### Test Steps
```pseudo
// Short grace period (5000ms) — advance past it
ADVANCE_TIME(5000 + 1000)
```

### Assertions
```pseudo
ASSERT root.get("score").value() == null
```

---

## RTO17, RTO18 - Sync event sequences for all state transitions

**Test ID**: `objects/unit/RTO17-RTO18/sync-event-sequences-0`

**Spec requirement:** Verify all sync state transition sequences.

### Setup
```pseudo
scenarios = [
  {
    name: "initial attach",
    trigger: () => {
      channel.attach()
    },
    expected_events: ["SYNCING", "SYNCED"]
  },
  {
    name: "re-attach after detach",
    trigger: () => {
      mock_ws.send_to_client(ProtocolMessage(action: DETACHED, channel: "test"))
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED, channel: "test", channelSerial: "sync2:cursor", flags: HAS_OBJECTS
      ))
      mock_ws.send_to_client(build_object_sync_message("test", "sync2:", STANDARD_POOL_OBJECTS))
    },
    expected_events: ["SYNCING", "SYNCED"]
  },
  {
    name: "re-sync on new ATTACHED",
    trigger: () => {
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED, channel: "test", channelSerial: "sync3:cursor", flags: HAS_OBJECTS
      ))
      mock_ws.send_to_client(build_object_sync_message("test", "sync3:", STANDARD_POOL_OBJECTS))
    },
    expected_events: ["SYNCING", "SYNCED"]
  },
  {
    name: "ATTACHED without HAS_OBJECTS",
    trigger: () => {
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED, channel: "test", channelSerial: "sync4:", flags: 0
      ))
    },
    expected_events: ["SYNCED"]
  }
]

FOR scenario IN scenarios:
  { client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
  events = []
  channel.object.on(SYNCING, () => events.append("SYNCING"))
  channel.object.on(SYNCED, () => events.append("SYNCED"))

  scenario.trigger()
  poll_until(events.length >= scenario.expected_events.length, timeout: 5s)

  ASSERT events == scenario.expected_events
```
