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
| RTO23d | Returns PathObject with path set to empty list and root set to root InternalLiveMap |

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
      connectionId: "conn-1", connectionKey: "key-1", siteCode: "test-site",
      objectsGCGracePeriod: 86400000
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

## RTO23e - get() re-attaches a DETACHED channel (ensure-active-channel)

**Test ID**: `objects/unit/RTO23e/get-reattaches-detached-0`

| Spec | Requirement |
|------|-------------|
| RTO23e | Performs the ensure-active-channel procedure (RTL33) on the underlying RealtimeChannel; if it fails, get() rejects with that ErrorInfo |
| RTL33b | A DETACHED channel is implicitly (re-)attached and get() waits for it to complete |

Tests that get() on a DETACHED channel no longer throws 90001 — per RTO23e it runs ensure-active-channel
(RTL33), which for a DETACHED channel performs an implicit attach (RTL33b); once the channel re-attaches and
re-syncs, get() resolves with the root PathObject. (Contrast RTO25b, where the *access* APIs — value/keys/
subscribe — still throw 90001 on DETACHED/FAILED; see the RTO25b sections below.)

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

// get() on a DETACHED channel triggers ensure-active-channel (RTL33b) -> implicit re-attach -> resolves
root = AWAIT channel.object.get()
```

### Assertions
```pseudo
ASSERT root IS PathObject
ASSERT root.path == []
ASSERT channel.state == ATTACHED
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
root = AWAIT channel.object.get()
```

### Test Steps
```pseudo
# Drive the internal publish (RTO15) through a public mutation — RTO15 is an internal
# function; its PublishResult is consumed internally by RTO20 (apply-on-ACK), which the
# neighbouring RTO20 tests cover. Only the observable wire behaviour is asserted here.
AWAIT root.get("score").increment(5)
```

### Assertions
```pseudo
ASSERT captured_messages.length == 1
ASSERT captured_messages[0].action == OBJECT
ASSERT captured_messages[0].channel == "test"
ASSERT captured_messages[0].state.length == 1
# RTO15e3 - the state entry is the encoded ObjectMessage for the driven mutation
ASSERT captured_messages[0].state[0].operation.action == COUNTER_INC
ASSERT captured_messages[0].state[0].operation.objectId == "counter:score@1000"
ASSERT captured_messages[0].state[0].operation.counterInc.number == 5
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
AWAIT root.get("score").increment(10)
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
AWAIT root.get("score").increment(10)
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
AWAIT root.get("score").increment(10)
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

inc_future = root.get("score").increment(10)

# Per RTO20e the write must WAIT for the sync to reach SYNCED: while still
# SYNCING the increment must not have applied yet.
ASSERT inc_future IS NOT complete
ASSERT root.get("score").value() == 100

mock_ws.send_to_client(build_object_sync_message("test", "sync2:", STANDARD_POOL_OBJECTS))

AWAIT inc_future
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 110
```

---

## RTO20e1 - publishAndApply fails when channel enters DETACHED during sync wait

**Test ID**: `objects/unit/RTO20e1/fails-on-channel-detached-0`

**Spec requirement:** If channel enters DETACHED/SUSPENDED/FAILED while waiting, fail with 92008.

The channel is detached **client-side** while the operation waits for SYNCED — an unsolicited
server DETACHED would trigger an immediate re-attach (RTL13a) in a compliant SDK, so the channel
would never observably stay DETACHED. A solicited `channel.detach()` does not trigger RTL13a; the
shared mock answers the outbound DETACH with DETACHED.

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

inc_future = root.get("score").increment(10)

# The publish and its ACK complete against the mock; publishAndApply parks in the
# RTO20e wait for SYNCED
ASSERT inc_future IS NOT complete

# A client-side detach then moves the channel to DETACHED
AWAIT channel.detach()

AWAIT inc_future FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 92008
```

---

## RTO20e1 - publishAndApply fails when channel enters FAILED during sync wait

**Test ID**: `objects/unit/RTO20e1/fails-on-channel-failed-0`

**Spec requirement:** If channel enters DETACHED/SUSPENDED/FAILED while waiting, fail with 92008.

An injected channel ERROR puts the channel into FAILED while the operation waits for SYNCED —
the same sequence as the ERROR-based proxy-tier test
(`objects/proxy/RTO20e/publish-fails-on-channel-failed-0`). Together with the DETACHED test above
this covers the reachable channel states of the RTO20e1 clause; SUSPENDED is a connection-level
state and is out of scope for a channel-level unit mock.

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

inc_future = root.get("score").increment(10)

# The publish and its ACK complete against the mock; publishAndApply parks in the
# RTO20e wait for SYNCED
ASSERT inc_future IS NOT complete

# Then the channel ERROR moves the channel to FAILED
mock_ws.send_to_client(ProtocolMessage(
  action: ERROR, channel: "test",
  error: { code: 90000, statusCode: 400, message: "Channel failed" }
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

## RTO23e - get() on a FAILED channel rejects with 90001 (ensure-active-channel)

**Test ID**: `objects/unit/RTO23e/get-rejects-failed-0`

| Spec | Requirement |
|------|-------------|
| RTO23e | Performs ensure-active-channel (RTL33) on the underlying RealtimeChannel; if it fails, get() rejects with that ErrorInfo |
| RTL33c | A FAILED channel causes ensure-active-channel to throw ErrorInfo with statusCode 400 and code 90001 |

Tests that get() on a FAILED channel rejects with 90001 — per RTO23e, ensure-active-channel (RTL33) is run, and
for a FAILED channel RTL33c throws 90001. (The 90001 assertion is unchanged from the old RTO25b framing; only the
governing clause moved from RTO25b to RTO23e/RTL33c, since get() is gated by RTO23e, not the access-API RTO25.)

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

## RTO25a - Access API precondition requires OBJECT_SUBSCRIBE mode

**Test ID**: `objects/unit/RTO25a/access-requires-subscribe-mode-0`

| Spec | Requirement |
|------|-------------|
| RTO25a | Require OBJECT_SUBSCRIBE channel mode per RTO2 |

Tests that the access path requires OBJECT_SUBSCRIBE — without it, obtaining/using the objects API throws 40024.

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

Tests that an access method (`keys()`) on a DETACHED channel throws 90001. The `root` PathObject is obtained
while the channel is ATTACHED (with OBJECT_SUBSCRIBE granted); the channel is then detached **client-side**,
and the subsequent read trips the RTO25b state precondition. (Contrast `get()`, which re-attaches per RTO23e.)

A client-side `channel.detach()` is used rather than injecting a server DETACHED, because an unsolicited
DETACHED triggers an immediate re-attach (RTL13a) in a compliant SDK — the channel never observably stays
DETACHED. The shared mock answers the outbound DETACH with DETACHED.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
// Detach the channel client-side after sync
AWAIT channel.detach()
AWAIT_STATE channel.state == DETACHED

root.keys() FAILS WITH error
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

Tests that an access method (`keys()`) on a FAILED channel throws 90001. `root` is obtained while ATTACHED, the
channel is then forced to FAILED, and the subsequent read trips the RTO25b state precondition.

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

root.keys() FAILS WITH error
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

Tests that a write operation on a DETACHED channel throws 90001. The channel is detached
**client-side** — an unsolicited server DETACHED triggers an immediate re-attach (RTL13a) in a
compliant SDK, so the channel never observably stays DETACHED. The shared mock answers the
outbound DETACH with DETACHED.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
// Detach the channel client-side after sync
AWAIT channel.detach()
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
// Trigger an update on the score counter. siteCode "remote" is absent from the pool's
// siteTimeserials ({"aaa":"t:0"}), so the op passes the newness check (RTLO4a) regardless of serial ordering.
// The "t:N" serials also sort after the pool entry timeserials ("t:0") for the entry-level LWW check (RTLM9).
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 5, "t:1", "remote")
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

// Subscribe at root with depth 1 — per RTO24c2b this covers ONLY root's own path ([]),
// NOT its children (a child like ["score"] is relativeDepth 1-0+1 = 2 > 1).
root.subscribe((event) => shallow_events.append(event), { depth: 1 })

// Subscribe at root with no depth limit — covers everything
root.subscribe((event) => deep_events.append(event))
```

### Test Steps
```pseudo
// Update root itself (a MAP_SET on root — candidate path [] is covered by depth 1).
// siteCode "remote" is absent from the pool's siteTimeserials ({"aaa":"t:0"}), so the op passes the
// newness check (RTLO4a / _canApplyOperation); the "t:N" serials also sort after the pool entry
// timeserials ("t:0") for the entry-level LWW check (RTLM9).
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "name", { string: "Bob" }, remote_serial(0), "remote")
]))
poll_until(deep_events.length >= 1, timeout: 5s)

// Update a child of root (path ["score"], relativeDepth 2) — NOT covered by depth 1, covered by deep.
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 5, "t:2", "remote")
]))
poll_until(deep_events.length >= 2, timeout: 5s)

// Negative-assertion quiescence: the shallow listener fired exactly once on the FIRST dispatch
// (the root self-update at []) and must NOT fire on the second (child ["score"]) dispatch. The deep
// listener is the control that fires on both; poll the shallow listener too so its count isn't racing.
poll_until(shallow_events.length >= 1, timeout: 5s)
```

### Assertions
```pseudo
// Shallow subscription (depth 1) only sees the root self-update, not the child update
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

// Tombstone stamped "now": only the ADVANCE_TIME below makes it GC-eligible
mock_ws.send_to_client(build_object_message("test", [
  build_object_delete("counter:score@1000", "99", "site1", now())
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

## RTO10c1b1 - GC never removes the root object

**Test ID**: `objects/unit/RTO10c1b1/gc-root-never-removed-0`

| Spec | Requirement |
|------|-------------|
| RTLO4e10 | OBJECT_DELETE targeting root is rejected with a warning |
| RTO10c1b1 | The root object is never removed from the pool by GC |
| RTO3b | ObjectsPool must always contain the root object |

The realtime system never publishes an `OBJECT_DELETE` targeting `root`; receiving
one indicates a faulty message. It must not tombstone the root object (RTLO4e10),
and even after the GC grace period elapses the root object must remain in the pool
and stay functional (RTO10c1b1, safeguarding RTO3b).

Note: this test verifies the composed behaviour. The RTO10c1b1 branch in isolation
(a tombstoned root surviving the GC sweep) is deliberately not exercised: RTLO4e10
makes that state unreachable in a conforming implementation, so the GC-side
exclusion is defense-in-depth verified by its spec tag rather than by fabricating
an impossible state.

### Setup
```pseudo
enable_fake_timers()
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")

// Rogue OBJECT_DELETE targeting the root object: rejected per RTLO4e10
mock_ws.send_to_client(build_object_message("test", [
  build_object_delete("root", remote_serial(0), "remote", now())
]))
```

### Test Steps
```pseudo
ASSERT root.get("name").value() == "Alice"  // root not tombstoned, data untouched

ADVANCE_TIME(86400000 + 300000)

// root must still be live: a subsequent operation still applies to the same
// root object the client holds
mock_ws.send_to_client(build_object_message("test", [
  build_map_set("root", "name", { string: "Bob" }, remote_serial(1), "remote")
]))
```

### Assertions
```pseudo
ASSERT root.get("name").value() == "Bob"
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
AWAIT root.get("score").increment(10)
score_after_apply = root.get("score").value()

mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 10, ack_serial(0, 0), "test-site")
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
| RTLC7c | siteTimeserials written only for CHANNEL source (verified via the source=LOCAL complement) |

Verified through observable behaviour: after a local increment (applied via ACK
with source LOCAL), an inbound COUNTER_INC from the same siteCode as the ACK — but
carrying a DIFFERENT serial that sorts at-or-below the ACK serial — should still
apply. If LOCAL had incorrectly written the ACK serial to siteTimeserials, the
per-site newness check would reject this inbound message as stale.

The mock's ACK serial for the first publish is `ack_serial(0, 0)` (= "t:1:0") with
siteCode `SITE_CODE` (= "test-site", from ConnectionDetails). The inbound message
reuses that siteCode but carries serial `"t:0:9"`. This serial is deliberately NOT
`ack_serial(0, 0)`: reusing the ACK serial would make RTO9a3 (apply-on-ACK echo
dedup) discard the message before any newness check runs, so the test could never
observe the siteTimeserials behaviour it is verifying. `"t:0:9"` is not in
`appliedOnAckSerials` (so it is not deduped) yet sorts BELOW `"t:1:0"`, so it will
be rejected by the newness check iff LOCAL wrongly recorded
`siteTimeserials[SITE_CODE] = "t:1:0"`.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
AWAIT root.get("score").increment(10)
ASSERT root.get("score").value() == 110

# Send inbound COUNTER_INC from siteCode SITE_CODE with serial "t:0:9": a serial that
# is NOT the apply-on-ACK serial (so RTO9a3 echo dedup does not discard it) yet sorts
# below "t:1:0". If LOCAL incorrectly set siteTimeserials[SITE_CODE] = "t:1:0", this
# fails the newness check and value stays 110; if LOCAL correctly left siteTimeserials
# untouched, SITE_CODE has no entry and the op applies, reaching 120.
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 10, below_ack_serial(9), SITE_CODE)
]))
poll_until(root.get("score").value() == 120, timeout: 5s)
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 120
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
inc_future = root.get("score").increment(10)

// Wait for the publish to reach the transport before injecting the echo/ACK. On SDKs where
// the publish is dispatched asynchronously, an ACK that arrives while no message is pending
// on the connection is discarded, and inc_future would never complete.
poll_until(mock_ws.events.filter(e => e.type == MESSAGE_FROM_CLIENT AND e.data.action == OBJECT).length >= 1, timeout: 5s)

// Send the echo BEFORE the ACK
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 10, ack_serial(0, 0), "test-site")
]))

// Now send the ACK
mock_ws.send_to_client(build_ack_message(0, [ack_serial(0, 0)]))

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
AWAIT root.get("score").increment(10)
ASSERT root.get("score").value() == 110

// Trigger re-sync — appliedOnAckSerials should be cleared per RTO5c9
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync2:cursor", flags: HAS_OBJECTS
))
mock_ws.send_to_client(build_object_sync_message("test", "sync2:", STANDARD_POOL_OBJECTS))
ASSERT root.get("score").value() == 100

// Replay the same serial (ack_serial(0, 0)) that was used for apply-on-ACK.
// If appliedOnAckSerials was cleared, this applies normally.
// If NOT cleared, dedup (RTO9a3) would reject it and score stays 100.
mock_ws.send_to_client(build_object_message("test", [
  build_counter_inc("counter:score@1000", 10, ack_serial(0, 0), SITE_CODE)
]))
poll_until(root.get("score").value() == 110, timeout: 5s)
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 110
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
AWAIT root.get("score").increment(10)
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
      serials = msg.state.map((_, i) => ack_serial(msg.msgSerial, i))
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
      serials = msg.state.map((_, i) => ack_serial(msg.msgSerial, i))
      mock_ws.send_to_client(build_ack_message(msg.msgSerial, serials))
  }
)
install_mock(mock_ws)
client = Realtime(options: { key: "fake:key" })
channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()

// Tombstone stamped "now": after ADVANCE_TIME(6000) it is eligible under the
// 5000ms server-provided grace but NOT under the 24h default, so this test fails
// if the implementation ignores ConnectionDetails.objectsGCGracePeriod
mock_ws.send_to_client(build_object_message("test", [
  build_object_delete("counter:score@1000", "99", "site1", now())
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
    // Fixture requirement: a genuine FIRST attach can only be observed on a
    // fresh, NON-synced channel with the SYNCING/SYNCED listeners registered
    // BEFORE attach(). setup_synced_channel() returns an already-ATTACHED+SYNCED
    // channel, so attach() would be a no-op and the first transitions would have
    // already fired before any listener could be attached. This scenario therefore
    // provides its own setup that builds an unattached channel and wires the
    // listeners up front; the shared loop honours scenario.setup when present.
    setup: () => {
      mock_ws = MockWebSocket(
        onConnectionAttempt: (conn) => conn.respond_with_success(
          ProtocolMessage(action: CONNECTED, connectionDetails: {
            connectionId: "conn-1", connectionKey: "conn-key-1",
            siteCode: SITE_CODE, objectsGCGracePeriod: 86400000
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
      client = Realtime(options: { key: "fake:key", autoConnect: true })
      channel = client.channels.get("test", { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
      // NOTE: channel is NOT yet attached/synced here — listeners must be wired
      // by the loop before scenario.trigger() calls attach().
      RETURN { client, channel, mock_ws }
    },
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
    // RTO4c transitions the (currently SYNCED) sync state to SYNCING for ANY ATTACHED → emits SYNCING;
    // RTO4b (no HAS_OBJECTS) then completes the sync immediately via RTO4b4 → emits SYNCED.
    expected_events: ["SYNCING", "SYNCED"]
  }
]

FOR scenario IN scenarios:
  // Scenarios that need a fresh (non-synced) fixture provide their own setup so
  // listeners can be registered BEFORE the first attach; the rest reuse the
  // standard already-synced channel and register listeners after setup.
  IF scenario.setup IS PRESENT:
    { client, channel, mock_ws } = scenario.setup()
  ELSE:
    { client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
  events = []
  channel.object.on(SYNCING, () => events.append("SYNCING"))
  channel.object.on(SYNCED, () => events.append("SYNCED"))

  scenario.trigger()
  poll_until(events.length >= scenario.expected_events.length, timeout: 5s)

  ASSERT events == scenario.expected_events
```
