# Objects Lifecycle Integration Tests

Spec points: `RTO23`, `RTPO15`, `RTPO17`

## Test Type
Integration test against Ably sandbox

## Protocol Variants
json, msgpack

Each test in this file runs once per protocol variant. The `PROTOCOL` variable
is set to `"json"` or `"msgpack"` for the current run. Client options should set
`useBinaryProtocol: PROTOCOL == "msgpack"`.

## Purpose

End-to-end lifecycle: connect, sync, create objects via PathObject, mutate, and
verify propagation to a second client. Complements unit tests by verifying real
server sync, mutation delivery, and object creation.

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
- Each test uses a unique channel name to avoid interference

---

## RTO23, RTPO15 - Set primitive via PathObject, second client reads it

**Test ID**: `objects/integration/RTO23-RTPO15/set-primitive-propagates-0`

**Spec requirement:** PathObject#set delegates to InternalLiveMap#set. The mutation
propagates via the server and a second client sees the updated value.

### Setup
```pseudo
channel_name = "objects-lifecycle-" + random_id()

client_a = Realtime(options: { key: api_key, endpoint: "nonprod:sandbox", autoConnect: false, useBinaryProtocol: PROTOCOL == "msgpack" })
client_b = Realtime(options: { key: api_key, endpoint: "nonprod:sandbox", autoConnect: false, useBinaryProtocol: PROTOCOL == "msgpack" })

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
// Client A sets a value
AWAIT root_a.set("greeting", "hello")

// Client B subscribes and waits for the update
events_b = []
root_b.subscribe((event) => events_b.append(event))
poll_until(root_b.get("greeting").value() == "hello")
```

### Assertions
```pseudo
ASSERT root_b.get("greeting").value() == "hello"
```

### Teardown
```pseudo
client_a.close()
client_b.close()
```

---

## RTPO15 - Set with LiveCounter, second client reads counter

**Test ID**: `objects/integration/RTPO15/set-counter-value-type-0`

**Spec requirement:** PathObject#set with LiveCounter creates a new counter
on the server. Second client syncs and reads the counter value.

### Setup
```pseudo
channel_name = "objects-counter-create-" + random_id()

client_a = Realtime(options: { key: api_key, endpoint: "nonprod:sandbox", autoConnect: false, useBinaryProtocol: PROTOCOL == "msgpack" })
client_b = Realtime(options: { key: api_key, endpoint: "nonprod:sandbox", autoConnect: false, useBinaryProtocol: PROTOCOL == "msgpack" })

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
AWAIT root_a.set("my_counter", LiveCounter.create(42))
poll_until(root_b.get("my_counter").value() == 42)
```

### Assertions
```pseudo
ASSERT root_b.get("my_counter").value() == 42
ASSERT root_b.get("my_counter").instance() IS NOT null
```

### Teardown
```pseudo
client_a.close()
client_b.close()
```

---

## RTPO17 - Increment counter, second client sees updated value

**Test ID**: `objects/integration/RTPO17/increment-propagates-0`

**Spec requirement:** PathObject#increment delegates to InternalLiveCounter#increment.
The server applies the increment and propagates the updated value.

### Setup
```pseudo
channel_name = "objects-increment-" + random_id()

client_a = Realtime(options: { key: api_key, endpoint: "nonprod:sandbox", autoConnect: false, useBinaryProtocol: PROTOCOL == "msgpack" })
client_b = Realtime(options: { key: api_key, endpoint: "nonprod:sandbox", autoConnect: false, useBinaryProtocol: PROTOCOL == "msgpack" })

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
// Create a counter first
AWAIT root_a.set("hits", LiveCounter.create(0))
poll_until(root_b.get("hits").value() == 0)

// Increment it
AWAIT root_a.get("hits").increment(10)
poll_until(root_b.get("hits").value() == 10)
```

### Assertions
```pseudo
ASSERT root_a.get("hits").value() == 10
ASSERT root_b.get("hits").value() == 10
```

### Teardown
```pseudo
client_a.close()
client_b.close()
```

---

## RTPO15 - Set with LiveMap, second client reads nested map

**Test ID**: `objects/integration/RTPO15/set-map-value-type-0`

**Spec requirement:** PathObject#set with LiveMap creates a nested map.
Second client can navigate into the nested map.

### Setup
```pseudo
channel_name = "objects-map-create-" + random_id()

client_a = Realtime(options: { key: api_key, endpoint: "nonprod:sandbox", autoConnect: false, useBinaryProtocol: PROTOCOL == "msgpack" })
client_b = Realtime(options: { key: api_key, endpoint: "nonprod:sandbox", autoConnect: false, useBinaryProtocol: PROTOCOL == "msgpack" })

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
AWAIT root_a.set("settings", LiveMap.create({
  "theme": "dark",
  "fontSize": 14
}))
poll_until(root_b.get("settings").get("theme").value() == "dark")
```

### Assertions
```pseudo
ASSERT root_b.get("settings").get("theme").value() == "dark"
ASSERT root_b.get("settings").get("fontSize").value() == 14
```

### Teardown
```pseudo
client_a.close()
client_b.close()
```

---

## RTO23 - get() waits for sync and returns PathObject

**Test ID**: `objects/integration/RTO23/get-returns-path-object-0`

**Spec requirement:** channel.object.get() returns a PathObject pointing to the root
after the sync sequence completes.

### Setup
```pseudo
channel_name = "objects-get-root-" + random_id()

client = Realtime(options: { key: api_key, endpoint: "nonprod:sandbox", autoConnect: false, useBinaryProtocol: PROTOCOL == "msgpack" })
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
ASSERT root.size() == 0
```

### Teardown
```pseudo
client.close()
```

---

## RTPO15 - Client syncs pre-existing data provisioned via REST

**Test ID**: `objects/integration/RTPO15/rest-provisioned-data-sync-0`

**Spec requirement:** Data created via the REST API is visible to a realtime client
that connects afterward.

### Setup
```pseudo
channel_name = "objects-rest-provision-" + random_id()

// Provision data via REST before any realtime client connects
provision_objects_via_rest(api_key, channel_name, [
  {
    mapSet: { key: "provisioned", value: { string: "from_rest" } },
    objectId: "root"
  }
])
```

### Test Steps
```pseudo
client = Realtime(options: { key: api_key, endpoint: "nonprod:sandbox", autoConnect: false, useBinaryProtocol: PROTOCOL == "msgpack" })
client.connect()
AWAIT_STATE client.connection.state == CONNECTED

channel = client.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT channel.object.get()
```

### Assertions
```pseudo
ASSERT root.get("provisioned").value() == "from_rest"
```

### Teardown
```pseudo
client.close()
```
