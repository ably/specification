# Objects GC Integration Tests

Spec points: `RTO10`, `RTLM19`, `RTLM5d2h`, `RTLM7`

## Test Type
Integration test against Ably sandbox

## Protocol Variants
json, msgpack

Each test in this file runs once per protocol variant. The `PROTOCOL` variable
is set to `"json"` or `"msgpack"` for the current run. Client options should set
`useBinaryProtocol: PROTOCOL == "msgpack"`.

## Purpose

Behavioral verification of tombstone semantics end-to-end against the real
server: removing a map entry tombstones it (RTLM7), tombstoned entries read
back as undefined/null (RTLM5d2h), and the same key is recreatable — the
server assigns a fresh objectId to the replacement object, which is safe
because tombstoned state is retained for the GC grace period (RTO10).

## Scope

The timer-based GC sweep itself (RTO10a–RTO10c, RTLM19a) is verified at the
**unit tier** (`objects/unit/realtime_object.md`, RTO10 tests), where the
clock and the sweep interval are controllable. It is intentionally **not**
exercised here: integration tests run on wall-clock time against a real
server (see *Integration timeouts are wall-clock* in
`docs/writing-derived-tests.md`), and the sweep cadence (RTO10a, ~5 minutes)
combined with the server-provided grace period (RTO10b, default 24 hours per
RTO10b3) is not observable within test timeouts. Do not use `ADVANCE_TIME`
in this file.

> Note: assertions of the form `value() == null` denote the spec's
> undefined/null absent value (RTLM5d2h); a deriving SDK asserts its
> language's mapping (e.g. `undefined` in JavaScript).

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

## RTO10 - Tombstoned object is recreatable with new objectId

**Test ID**: `objects/integration/RTO10/tombstoned-object-gc-recreate-0`

**Spec requirement:** After an object is tombstoned (removed from its parent
map), a new object can be created at the same map key. The new object gets a
different server-assigned objectId, confirming the old object is gone while
its tombstone is retained for the grace period (RTO10).

### Setup
```pseudo
channel_name = "objects-gc-object-" + random_id()

client = Realtime(options: { key: api_key, endpoint: "nonprod:sandbox", autoConnect: false, useBinaryProtocol: PROTOCOL == "msgpack" })
client.connect()
AWAIT_STATE client.connection.state == CONNECTED
  WITH timeout: 15 seconds

channel = client.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()
  WITH timeout: 15 seconds
```

### Test Steps
```pseudo
// Create a counter
AWAIT root.set("counter", LiveCounter.create(42))
poll_until(root.get("counter").value() == 42)

counter_id = root.get("counter").instance().id

// Remove it (tombstones the entry and the object, RTLM7)
AWAIT root.remove("counter")

// RTLM5d2h: tombstoned entries read back as undefined/null
poll_until(root.get("counter").value() == null)

// Create a new counter at the same key
AWAIT root.set("counter", LiveCounter.create(99))
poll_until(root.get("counter").value() == 99)
```

### Assertions
```pseudo
ASSERT root.get("counter").value() == 99
ASSERT root.get("counter").instance().id != counter_id
```

### Teardown
```pseudo
client.close()
```

---

## RTLM19 - Tombstoned map entry is re-settable

**Test ID**: `objects/integration/RTLM19/tombstoned-entry-gc-reset-0`

**Spec requirement:** After a map entry is tombstoned (removed, RTLM7), the
entry can be re-set. The subsequent MAP_SET succeeds because the server
assigns a newer serial than the removal's, while the tombstoned entry is
retained for the grace period pending GC (RTLM19).

### Setup
```pseudo
channel_name = "objects-gc-entry-" + random_id()

client = Realtime(options: { key: api_key, endpoint: "nonprod:sandbox", autoConnect: false, useBinaryProtocol: PROTOCOL == "msgpack" })
client.connect()
AWAIT_STATE client.connection.state == CONNECTED
  WITH timeout: 15 seconds

channel = client.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()
  WITH timeout: 15 seconds
```

### Test Steps
```pseudo
// Set then remove a key
AWAIT root.set("ephemeral", "temporary")
poll_until(root.get("ephemeral").value() == "temporary")

AWAIT root.remove("ephemeral")

// RTLM5d2h: tombstoned entries read back as undefined/null
poll_until(root.get("ephemeral").value() == null)

// Set the same key again
AWAIT root.set("ephemeral", "revived")
poll_until(root.get("ephemeral").value() == "revived")
```

### Assertions
```pseudo
ASSERT root.get("ephemeral").value() == "revived"
```

### Teardown
```pseudo
client.close()
```
