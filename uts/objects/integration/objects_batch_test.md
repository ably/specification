# Objects Batch Integration Tests

Spec points: `RTPO22`, `RTBC12`–`RTBC15`

## Test Type
Integration test against Ably sandbox

## Purpose

Batch operations end-to-end — multiple mutations in a single publish, atomic
propagation to subscribers. Verifies that batch() groups multiple operations
into a single ProtocolMessage and the server processes and delivers them
correctly to other clients.

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

## RTPO22 - Batch set of multiple keys arrives to second client

**Test ID**: `objects/integration/RTPO22/batch-set-propagates-0`

**Spec requirement:** batch() groups multiple mutations into a single publish.
All operations are delivered together to subscribers.

### Setup
```pseudo
channel_name = "objects-batch-" + random_id()

client_a = Realtime(options: { key: api_key })
client_b = Realtime(options: { key: api_key })

client_a.connect()
AWAIT_STATE client_a.connection.state == CONNECTED

client_b.connect()
AWAIT_STATE client_b.connection.state == CONNECTED

channel_a = client_a.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
channel_b = client_b.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })

root_a = AWAIT channel_a.object.get()
root_b = AWAIT channel_b.object.get()
```

### Test Steps
```pseudo
AWAIT root_a.batch((ctx) => {
  ctx.set("x", 1)
  ctx.set("y", 2)
  ctx.set("z", 3)
})

poll_until(root_b.get("x").value() == 1, timeout: 10s)
```

### Assertions
```pseudo
ASSERT root_b.get("x").value() == 1
ASSERT root_b.get("y").value() == 2
ASSERT root_b.get("z").value() == 3
```

### Teardown
```pseudo
client_a.close()
client_b.close()
```

---

## RTPO22 - Batch with mixed operations (set + remove + increment)

**Test ID**: `objects/integration/RTPO22/batch-mixed-ops-0`

**Spec requirement:** Batch can contain different operation types published atomically.

### Setup
```pseudo
channel_name = "objects-batch-mixed-" + random_id()

client_a = Realtime(options: { key: api_key })
client_b = Realtime(options: { key: api_key })

client_a.connect()
AWAIT_STATE client_a.connection.state == CONNECTED

client_b.connect()
AWAIT_STATE client_b.connection.state == CONNECTED

channel_a = client_a.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
channel_b = client_b.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })

root_a = AWAIT channel_a.object.get()
root_b = AWAIT channel_b.object.get()
```

### Test Steps
```pseudo
// Set up initial state
AWAIT root_a.set("to_remove", "temp")
AWAIT root_a.set("counter", LiveCounter.create(10))
poll_until(root_b.get("to_remove").value() == "temp", timeout: 10s)
poll_until(root_b.get("counter").value() == 10, timeout: 10s)

// Batch with mixed operations
AWAIT root_a.batch((ctx) => {
  ctx.set("name", "Alice")
  ctx.remove("to_remove")
  child = ctx.get("counter")
  child.increment(5)
})

poll_until(root_b.get("name").value() == "Alice", timeout: 10s)
```

### Assertions
```pseudo
ASSERT root_b.get("name").value() == "Alice"
ASSERT root_b.get("to_remove").value() == null
ASSERT root_b.get("counter").value() == 15
```

### Teardown
```pseudo
client_a.close()
client_b.close()
```

---

## RTPO22 - Batch with LiveCounterValueType creates counter atomically

**Test ID**: `objects/integration/RTPO22/batch-create-counter-0`

**Spec requirement:** Batch containing LiveCounterValueType generates COUNTER_CREATE +
MAP_SET in a single publish. The server processes both atomically.

### Setup
```pseudo
channel_name = "objects-batch-counter-" + random_id()

client_a = Realtime(options: { key: api_key })
client_b = Realtime(options: { key: api_key })

client_a.connect()
AWAIT_STATE client_a.connection.state == CONNECTED

client_b.connect()
AWAIT_STATE client_b.connection.state == CONNECTED

channel_a = client_a.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
channel_b = client_b.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })

root_a = AWAIT channel_a.object.get()
root_b = AWAIT channel_b.object.get()
```

### Test Steps
```pseudo
AWAIT root_a.batch((ctx) => {
  ctx.set("batch_counter", LiveCounter.create(99))
  ctx.set("label", "created in batch")
})

poll_until(root_b.get("batch_counter").value() == 99, timeout: 10s)
```

### Assertions
```pseudo
ASSERT root_b.get("batch_counter").value() == 99
ASSERT root_b.get("label").value() == "created in batch"
ASSERT root_b.get("batch_counter").instance() IS NOT null
```

### Teardown
```pseudo
client_a.close()
client_b.close()
```
