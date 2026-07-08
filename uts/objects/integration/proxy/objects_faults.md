# Objects Proxy Integration Tests

Spec points: `RTO5a2`, `RTO7`, `RTO8`, `RTO17`, `RTO20e`, `RTO20e1`

## Test Type

Proxy integration test against Ably Sandbox endpoint

## Proxy Infrastructure

See `uts/docs/proxy.md` for the full proxy infrastructure specification.

## Corresponding Unit Tests

- `objects/unit/objects_pool.md` — RTO5a2 (new sync discards old), RTO7/RTO8 (buffering during SYNCING)
- `objects/unit/realtime_object.md` — RTO17 (sync state events), RTO20e (publishAndApply waits
  for SYNCED), RTO20e1 (in-flight operation fails with 92008 when the channel leaves the
  attached state during the sync wait)

## Sandbox Setup

Tests run against the Ably Sandbox via a programmable proxy.

### App Provisioning

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox.realtime.ably-nonprod.net/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox.realtime.ably-nonprod.net/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

### Common Cleanup

```pseudo
AFTER EACH TEST:
  FOR EACH client created by the test (client / client_a / client_b):
    IF client.connection.state IN [connected, connecting, disconnected]:
      client.connection.close()
      AWAIT_STATE client.connection.state == ConnectionState.closed
        WITH timeout: 10 seconds
  IF session IS NOT null:
    session.close()
```

### Protocol Message Action Numbers (Objects-relevant)

| Name | Number |
|------|--------|
| ACK | 1 |
| ERROR | 9 |
| ATTACHED | 11 |
| DETACHED | 13 |
| OBJECT | 19 |
| OBJECT_SYNC | 20 |

> Rule `match.action` values are **strings**; objects actions must use numeric strings
> (e.g. `"20"`) — see the *Match Conditions* section in `uts/docs/proxy.md`.

---

## RTO5a2, RTO17 - Sync interrupted by disconnect, re-syncs on reconnect

**Test ID**: `objects/proxy/RTO5a2-RTO17/sync-interrupted-reconnect-0`

| Spec | Requirement |
|------|-------------|
| RTO5a2 | New sync sequence discards old SyncObjectsPool |
| RTO17 | Sync state transitions: SYNCING → SYNCED, re-triggered on re-attach |

Tests that when the connection drops mid-OBJECT_SYNC, the client discards
partial sync state and re-syncs cleanly on reconnect. The proxy disconnects
after the first OBJECT_SYNC frame so the sync is never completed, then on
reconnect the client re-attaches and syncs fully.

### Setup

```pseudo
channel_name = "objects-sync-interrupt-" + random_id()

// Disconnect after first OBJECT_SYNC frame
session = create_proxy_session(
  endpoint: "nonprod:sandbox",

  rules: [{
    "match": { "type": "ws_frame_to_client", "action": "20" },
    "action": { "type": "disconnect" },
    "times": 1,
    "comment": "RTO5a2: Disconnect after first OBJECT_SYNC to interrupt sync"
  }]
)

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))

channel = client.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
```

### Test Steps

```pseudo
client.connect()
AWAIT_STATE client.connection.state == CONNECTED
  WITH timeout: 15 seconds

// First attach triggers sync; proxy disconnects mid-sync
channel.attach()
AWAIT_STATE client.connection.state == DISCONNECTED
  WITH timeout: 15 seconds

// Client auto-reconnects; re-attach triggers fresh sync
AWAIT_STATE client.connection.state == CONNECTED
  WITH timeout: 30 seconds

// get() waits for SYNCED — will only resolve if re-sync completes
root = AWAIT channel.object.get()
  WITH timeout: 30 seconds
```

### Assertions

```pseudo
ASSERT root IS PathObject
ASSERT root.path() == ""
```

---

## RTO7, RTO8 - Mutations during re-sync are buffered and applied

**Test ID**: `objects/proxy/RTO7-RTO8/mutations-buffered-during-resync-0`

| Spec | Requirement |
|------|-------------|
| RTO7 | Buffer OBJECT messages during SYNCING |
| RTO8 | Apply buffered messages after sync completes |

Client A publishes mutations while client B is re-syncing after reconnect.
The mutations should be buffered and applied after the sync completes.

### Setup

```pseudo
channel_name = "objects-buffer-resync-" + random_id()

// Client A: direct connection (no proxy), publishes mutations
client_a = Realtime(options: { key: api_key, endpoint: "nonprod:sandbox", autoConnect: false })
client_a.connect()
AWAIT_STATE client_a.connection.state == CONNECTED
  WITH timeout: 15 seconds

channel_a = client_a.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root_a = AWAIT channel_a.object.get()
  WITH timeout: 15 seconds

// Set initial data
AWAIT root_a.set("key1", "initial")

// Client B: through proxy, will be disconnected
session = create_proxy_session(
  endpoint: "nonprod:sandbox",

  rules: []
)

client_b = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))

channel_b = client_b.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
```

### Test Steps

```pseudo
// Client B connects and syncs
client_b.connect()
AWAIT_STATE client_b.connection.state == CONNECTED
  WITH timeout: 15 seconds

root_b = AWAIT channel_b.object.get()
  WITH timeout: 15 seconds
poll_until(root_b.get("key1").value() == "initial", timeout: 10s)

// Disconnect client B
session.trigger_action({ type: "disconnect" })
AWAIT_STATE client_b.connection.state == DISCONNECTED
  WITH timeout: 15 seconds

// While B is disconnected, A publishes a mutation
AWAIT root_a.set("key1", "updated_during_disconnect")

// Client B reconnects and re-syncs; the mutation should be visible
AWAIT_STATE client_b.connection.state == CONNECTED
  WITH timeout: 30 seconds

root_b = AWAIT channel_b.object.get()
  WITH timeout: 15 seconds
poll_until(root_b.get("key1").value() == "updated_during_disconnect", timeout: 15s)
```

### Assertions

```pseudo
ASSERT root_b.get("key1").value() == "updated_during_disconnect"
```

### Teardown

```pseudo
client_a.close()
client_b.close()
session.close()
```

---

## RTO17 - Server-initiated detach triggers re-sync on re-attach

**Test ID**: `objects/proxy/RTO17/server-detach-resync-0`

| Spec | Requirement |
|------|-------------|
| RTO17 | On re-attach, sync state machine restarts from INITIALIZED |

The proxy injects a DETACHED message for the channel, simulating a server-initiated
detach. After the client automatically re-attaches, it must re-sync the object pool.

### Setup

```pseudo
channel_name = "objects-detach-resync-" + random_id()

session = create_proxy_session(
  endpoint: "nonprod:sandbox",

  rules: []
)

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))

channel = client.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
```

### Test Steps

```pseudo
client.connect()
AWAIT_STATE client.connection.state == CONNECTED
  WITH timeout: 15 seconds

root = AWAIT channel.object.get()
  WITH timeout: 15 seconds

// Set some data
AWAIT root.set("before_detach", "hello")
ASSERT root.get("before_detach").value() == "hello"

// Inject server-initiated DETACHED
session.trigger_action({
  type: "inject_to_client",
  message: {
    action: 13,
    channel: channel_name
  }
})

// Client should auto-re-attach (RTL13a)
AWAIT_STATE channel.state == ChannelState.attached
  WITH timeout: 30 seconds

// Re-sync should restore data
root = AWAIT channel.object.get()
  WITH timeout: 15 seconds
poll_until(root.get("before_detach").value() == "hello", timeout: 15s)
```

### Assertions

```pseudo
ASSERT root.get("before_detach").value() == "hello"
```

---

## RTO20e - publishAndApply fails when channel enters FAILED during SYNCING

**Test ID**: `objects/proxy/RTO20e/publish-fails-on-channel-failed-0`

| Spec | Requirement |
|------|-------------|
| RTO20e | publishAndApply waits for the sync state to transition to SYNCED before applying locally |
| RTO20e1 | If the channel enters DETACHED/SUSPENDED/FAILED while waiting, the operation fails with 92008, statusCode 400, cause = channel errorReason |

The client syncs a channel, is forced back into SYNCING, and issues a mutation
*while* SYNCING — the publish and its ACK complete against the real server, then
publishAndApply parks in the RTO20e wait for SYNCED. The proxy then injects a
channel ERROR so the channel enters FAILED whilst the operation is waiting; the
pending mutation must fail with error 92008 (RTO20e1).

> Note: the mutation must be in flight *before* the channel fails. A mutation issued on a
> channel already in DETACHED/FAILED/SUSPENDED fails the RTO26b write precondition with 90001
> and never reaches publishAndApply — that is different behaviour, not this test. The unit-tier
> test `objects/unit/RTO20e1/fails-on-channel-failed-0` uses the same sequence.

### Setup

```pseudo
channel_name = "objects-publish-failed-" + random_id()

session = create_proxy_session(
  endpoint: "nonprod:sandbox",

  rules: []
)

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))

channel = client.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
```

### Test Steps

```pseudo
client.connect()
AWAIT_STATE client.connection.state == CONNECTED
  WITH timeout: 15 seconds

root = AWAIT channel.object.get()
  WITH timeout: 15 seconds

// Force the objects back into SYNCING: inject an ATTACHED (action 11) carrying the
// HAS_OBJECTS flag (bit 7, i.e. flags: 128). RTO4c starts a new sync sequence on every
// ATTACHED protocol message; the server never sent this ATTACHED, so no OBJECT_SYNC
// follows and the objects remain SYNCING. The channel itself stays ATTACHED.
session.trigger_action({
  type: "inject_to_client",
  message: { action: 11, channel: channel_name, flags: 128 }
})

// Mutate WHILE SYNCING: the channel is ATTACHED so the write preconditions (RTO26)
// pass and the publish + ACK complete against the real server; publishAndApply then
// waits for a SYNCED that will never arrive (RTO20e). Do not await yet.
pending = root.set("key", "value")

// Ensure the operation is in the RTO20e sync-wait, not still publishing: wait until
// the proxy log shows the server's ACK (action 1) for the OBJECT publish, then allow
// a brief real-time yield for the client to move the ACKed operation into the wait.
// (There is no observable client state between "ACK processed" and "parked in the
// sync-wait" to poll on, so a small fixed yield is required — the deriving SDK may
// substitute an equivalent scheduler yield.)
poll_until(session.get_log() CONTAINS event WHERE type == "ws_frame"
  AND direction == "server_to_client" AND message.action == 1, timeout: 10s)
WAIT 500ms  // real (wall-clock) time

// The channel enters FAILED whilst the operation waits for SYNCED (RTO20e1)
session.trigger_action({
  type: "inject_to_client",
  message: {
    action: 9,
    channel: channel_name,
    error: { statusCode: 400, code: 90000, message: "injected error" }
  }
})

AWAIT_STATE channel.state == ChannelState.failed
  WITH timeout: 15 seconds

AWAIT pending FAILS WITH error
  WITH timeout: 15 seconds
```

### Assertions

```pseudo
ASSERT error.code == 92008
ASSERT error.statusCode == 400
// RTO20e1: cause is set to RealtimeChannel.errorReason — the injected channel ERROR
ASSERT error.cause IS NOT null
ASSERT error.cause.code == 90000
```

---

## RTO5, RTO7 - Publish during sync, echo arrives after sync completes

**Test ID**: `objects/proxy/RTO5-RTO7/publish-during-sync-echo-after-0`

| Spec | Requirement |
|------|-------------|
| RTO5c6 | Apply buffered OBJECT messages after sync completes |
| RTO7 | Buffer OBJECT messages during SYNCING |

The proxy delays the OBJECT_SYNC completion so the client stays in SYNCING.
Client A publishes a mutation that arrives as an OBJECT message to client B
while B is still syncing. The mutation must be buffered and applied after
sync completes.

### Setup

```pseudo
channel_name = "objects-publish-during-sync-" + random_id()

// Client A: direct, no proxy
client_a = Realtime(options: { key: api_key, endpoint: "nonprod:sandbox", autoConnect: false })
client_a.connect()
AWAIT_STATE client_a.connection.state == CONNECTED
  WITH timeout: 15 seconds

channel_a = client_a.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root_a = AWAIT channel_a.object.get()
  WITH timeout: 15 seconds

// Set up initial data
AWAIT root_a.set("existing", "before")

// Client B: through proxy with delayed OBJECT_SYNC
session = create_proxy_session(
  endpoint: "nonprod:sandbox",

  rules: [{
    "match": { "type": "ws_frame_to_client", "action": "20" },
    "action": { "type": "delay", "delayMs": 3000 },
    "times": 1,
    "comment": "Delay first OBJECT_SYNC to keep B in SYNCING state"
  }]
)

client_b = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))

channel_b = client_b.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
```

### Test Steps

```pseudo
// Start client B — will be stuck in SYNCING due to delayed OBJECT_SYNC
client_b.connect()
AWAIT_STATE client_b.connection.state == CONNECTED
  WITH timeout: 15 seconds
channel_b.attach()

// While B is syncing, A publishes a mutation
AWAIT root_a.set("existing", "after")

// B's get() will resolve once delayed sync completes
root_b = AWAIT channel_b.object.get()
  WITH timeout: 30 seconds

// The mutation from A should be visible (either in sync data or buffered OBJECT)
poll_until(root_b.get("existing").value() == "after", timeout: 15s)
```

### Assertions

```pseudo
ASSERT root_b.get("existing").value() == "after"
```

### Teardown

```pseudo
client_a.close()
client_b.close()
session.close()
```
