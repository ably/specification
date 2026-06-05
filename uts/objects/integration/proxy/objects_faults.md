# Objects Proxy Integration Tests

Spec points: `RTO5a2`, `RTO7`, `RTO8`, `RTO17`, `RTO20e`

## Test Type

Proxy integration test against Ably Sandbox endpoint

## Proxy Infrastructure

See `realtime/integration/helpers/proxy.md` for the full proxy infrastructure specification.

## Corresponding Unit Tests

- `objects/unit/objects_pool.md` — RTO5a2 (new sync discards old), RTO7/RTO8 (buffering during SYNCING)
- `objects/unit/realtime_object.md` — RTO17 (sync state events), RTO20e (publishAndApply waits for SYNCED/fails on FAILED)

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
  IF client IS NOT null AND client.connection.state IN [connected, connecting, disconnected]:
    client.connection.close()
    AWAIT_STATE client.connection.state == ConnectionState.closed
      WITH timeout: 10 seconds
  IF session IS NOT null:
    session.close()
```

### Protocol Message Action Numbers (Objects-relevant)

| Name | Number |
|------|--------|
| ATTACHED | 11 |
| DETACHED | 13 |
| OBJECT | 19 |
| OBJECT_SYNC | 20 |

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
    "match": { "type": "ws_frame_to_client", "action": 20 },
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
client_a = Realtime(options: { key: api_key })
client_a.connect()
AWAIT_STATE client_a.connection.state == CONNECTED
  WITH timeout: 15 seconds

channel_a = client_a.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root_a = AWAIT channel_a.object.get()

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
| RTO20e | publishAndApply waits for SYNCED; fails with 92008 if channel enters DETACHED/SUSPENDED/FAILED |

Client sets up a channel with objects, then the proxy injects a channel ERROR
to transition to FAILED. A PathObject mutation (which uses publishAndApply
internally) should fail with error 92008.

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

// Inject channel ERROR to transition to FAILED
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

// Attempt a mutation — should fail since channel is FAILED
AWAIT root.set("key", "value") FAILS WITH error
```

### Assertions

```pseudo
ASSERT error.code == 92008
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
client_a = Realtime(options: { key: api_key })
client_a.connect()
AWAIT_STATE client_a.connection.state == CONNECTED
  WITH timeout: 15 seconds

channel_a = client_a.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root_a = AWAIT channel_a.object.get()

// Set up initial data
AWAIT root_a.set("existing", "before")

// Client B: through proxy with delayed OBJECT_SYNC
session = create_proxy_session(
  endpoint: "nonprod:sandbox",

  rules: [{
    "match": { "type": "ws_frame_to_client", "action": 20 },
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
