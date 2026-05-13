# Objects GC Integration Tests

Spec points: `RTO10`, `RTLM19`

## Test Type
Integration test against Ably sandbox

## Purpose

Behavioral verification of garbage collection for tombstoned objects and tombstoned
map entries. Uses `ADVANCE_TIME` (fake timers) to control timing and verifies GC
through observable API consequences rather than internal pool state inspection.

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox-rest.ably.io`.

### App Provisioning

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

### Notes
- These tests use fake timers to control GC timing
- Each test uses a unique channel name

---

## RTO10 - Tombstoned object is GC'd and recreatable

**Test ID**: `objects/integration/RTO10/tombstoned-object-gc-recreate-0`

**Spec requirement:** After an object is tombstoned and the GC grace period elapses,
the object is removed from the pool. A new object can then be created at the same
map key.

### Setup
```pseudo
enable_fake_timers()
channel_name = "objects-gc-object-" + random_id()

client = Realtime(options: { key: api_key })
client.connect()
AWAIT_STATE client.connection.state == CONNECTED

channel = client.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()
```

### Test Steps
```pseudo
// Create a counter
AWAIT root.set("counter", LiveCounter.create(42))
ASSERT root.get("counter").value() == 42
counter_id = root.get("counter").instance().id()

// Remove it (tombstones the entry and the object)
AWAIT root.remove("counter")
ASSERT root.get("counter").value() == null

// Advance past GC grace period
ADVANCE_TIME(86400000 + 300000)

// Create a new counter at the same key
AWAIT root.set("counter", LiveCounter.create(99))
```

### Assertions
```pseudo
ASSERT root.get("counter").value() == 99
new_counter_id = root.get("counter").instance().id()
ASSERT new_counter_id != counter_id
```

### Teardown
```pseudo
client.close()
```

---

## RTLM19 - Tombstoned map entry is GC'd, re-settable with old serial

**Test ID**: `objects/integration/RTLM19/tombstoned-entry-gc-reset-0`

**Spec requirement:** After a map entry is tombstoned and GC'd, the entry is fully
removed. A subsequent MAP_SET with any serial succeeds because there is no existing
entry to compare against.

### Setup
```pseudo
enable_fake_timers()
channel_name = "objects-gc-entry-" + random_id()

client = Realtime(options: { key: api_key })
client.connect()
AWAIT_STATE client.connection.state == CONNECTED

channel = client.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()
```

### Test Steps
```pseudo
// Set then remove a key
AWAIT root.set("ephemeral", "temporary")
ASSERT root.get("ephemeral").value() == "temporary"

AWAIT root.remove("ephemeral")
ASSERT root.get("ephemeral").value() == null

// Advance past GC grace period for entries
ADVANCE_TIME(86400000 + 300000)

// Set the same key again
AWAIT root.set("ephemeral", "revived")
```

### Assertions
```pseudo
ASSERT root.get("ephemeral").value() == "revived"
```

### Teardown
```pseudo
client.close()
```
