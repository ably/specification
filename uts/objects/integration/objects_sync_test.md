# Objects Sync Integration Tests

Spec points: `RTO4`, `RTO5`, `RTO17`

## Test Type
Integration test against Ably sandbox

## Protocol Variants
json, msgpack

Each test in this file runs once per protocol variant. The `PROTOCOL` variable
is set to `"json"` or `"msgpack"` for the current run. Client options should set
`useBinaryProtocol: PROTOCOL == "msgpack"`.

## Purpose

Verify the sync sequence against the real server: attach with HAS_OBJECTS,
receive OBJECT_SYNC, reach SYNCED state. Also tests re-attach behaviour where
the client detaches and re-attaches to verify the pool is re-synced.

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox.realtime.ably-nonprod.net`.

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

### Notes
- Each test uses a unique channel name

---

## RTO4, RTO5 - Attach triggers sync, get() resolves after SYNCED

**Test ID**: `objects/integration/RTO4-RTO5/attach-sync-get-0`

**Spec requirement:** On ATTACHED with HAS_OBJECTS flag, client transitions to SYNCING,
processes OBJECT_SYNC messages, then transitions to SYNCED. get() waits for SYNCED.

### Setup
```pseudo
channel_name = "objects-sync-" + random_id()

client = Realtime(options: { key: api_key, useBinaryProtocol: PROTOCOL == "msgpack" })
client.connect()
AWAIT_STATE client.connection.state == CONNECTED

channel = client.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
```

### Test Steps
```pseudo
root = AWAIT channel.object.get()
```

### Assertions
```pseudo
ASSERT root IS PathObject
ASSERT root.path() == ""
```

### Teardown
```pseudo
client.close()
```

---

## RTO5, RTO17 - Two clients sync same channel with pre-existing data

**Test ID**: `objects/integration/RTO5-RTO17/two-clients-sync-0`

**Spec requirement:** Both clients complete sync and see the same object pool state.

### Setup
```pseudo
channel_name = "objects-two-sync-" + random_id()

client_a = Realtime(options: { key: api_key, useBinaryProtocol: PROTOCOL == "msgpack" })
client_b = Realtime(options: { key: api_key, useBinaryProtocol: PROTOCOL == "msgpack" })

client_a.connect()
AWAIT_STATE client_a.connection.state == CONNECTED

client_b.connect()
AWAIT_STATE client_b.connection.state == CONNECTED

channel_a = client_a.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
channel_b = client_b.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
```

### Test Steps
```pseudo
// Client A creates data
root_a = AWAIT channel_a.object.get()
AWAIT root_a.set("key1", "value1")

// Client B attaches and syncs — should see the data
root_b = AWAIT channel_b.object.get()
poll_until(root_b.get("key1").value() == "value1", timeout: 10s)
```

### Assertions
```pseudo
ASSERT root_b.get("key1").value() == "value1"
```

### Teardown
```pseudo
client_a.close()
client_b.close()
```

---

## RTO17 - Re-attach re-syncs object pool

**Test ID**: `objects/integration/RTO17/reattach-resyncs-0`

**Spec requirement:** On re-attach, the sync state machine restarts and the pool
is re-populated from the server.

### Setup
```pseudo
channel_name = "objects-reattach-" + random_id()

client = Realtime(options: { key: api_key, useBinaryProtocol: PROTOCOL == "msgpack" })
client.connect()
AWAIT_STATE client.connection.state == CONNECTED

channel = client.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()
```

### Test Steps
```pseudo
// Set some data
AWAIT root.set("before_detach", "hello")
ASSERT root.get("before_detach").value() == "hello"

// Detach and re-attach
AWAIT channel.detach()
AWAIT channel.attach()

// Re-sync should restore data
root = AWAIT channel.object.get()
poll_until(root.get("before_detach").value() == "hello", timeout: 10s)
```

### Assertions
```pseudo
ASSERT root.get("before_detach").value() == "hello"
```

### Teardown
```pseudo
client.close()
```

---

## RTO4 - Attach without OBJECT_SUBSCRIBE still resolves get() with empty pool

**Test ID**: `objects/integration/RTO4/attach-subscribe-only-0`

**Spec requirement:** Channel attached with only OBJECT_SUBSCRIBE mode. Server
sends HAS_OBJECTS, sync completes, root is an empty LiveMap.

### Setup
```pseudo
channel_name = "objects-subscribe-only-" + random_id()

client = Realtime(options: { key: api_key, useBinaryProtocol: PROTOCOL == "msgpack" })
client.connect()
AWAIT_STATE client.connection.state == CONNECTED

channel = client.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE"] })
```

### Test Steps
```pseudo
root = AWAIT channel.object.get()
```

### Assertions
```pseudo
ASSERT root IS PathObject
ASSERT root.size() == 0
```

### Teardown
```pseudo
client.close()
```
