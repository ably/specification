# RestObject Integration Tests

Spec points: `RSL16`, `RSO2`, `RSO2g`, `RSO3`, `RSO3c`, `RSO4`, `RSO5`, `RSO5a1`, `RSO5c3`, `RSO5d`, `RSO5e`, `RSO5f`, `RSO5g2`, `RSO5h`, `RSO5i`, `RSO5j`, `RSO6`, `RSO7`, `RSO9`, `RSO10`, `RSO13`, `RSO14`, `RSO15`

## Test Type
Integration test against Ably sandbox

## Protocol Variants
json, msgpack

Each test in this file runs once per protocol variant. The `PROTOCOL` variable
is set to `"json"` or `"msgpack"` for the current run. Client options should set
`useBinaryProtocol: PROTOCOL == "msgpack"`.

## Purpose

End-to-end verification that `RestObject#publish`, `RestObject#get` and
`RestObject#generateObjectId` interoperate with the real service: the wire encodings the SDK
produces are accepted, the responses the service returns are decoded into the documented types, and
locally generated object IDs are accepted by the server.

Server-defined behaviour (compact formatting of bytes and JSON leaves, path syntax, error codes for
unresolvable targets) is deliberately not asserted beyond what the SDK specification requires.

## Corresponding Unit Tests
- `objects/unit/rest_object_get.md` — RSL16, RSO2, RSO9
- `objects/unit/rest_object_publish.md` — RSO3, RSO5, RSO7, RSO10
- `objects/unit/rest_object_generate_id.md` — RSO4, RSO11

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

### Common Client Setup

`objects_plugin` denotes the SDK's `Objects` plugin, supplied under the `Objects` `PluginType` key.

```pseudo
create_rest_channel(test_name):
  client = Rest(options: ClientOptions(
    key: api_key,
    endpoint: "nonprod:sandbox",
    useBinaryProtocol: PROTOCOL == "msgpack",
    plugins: { Objects: objects_plugin }
  ))
  channel = client.channels.get("objects-rest-" + test_name + "-" + random_id())
  RETURN { client, channel }
```

### Notes
- Each test uses a unique channel name, so every test starts from an empty channel object.
- Reads that follow a write use `poll_until_success`: a value written by `publish` may not be
  visible to an immediately following `get`, and a read of a path that does not exist yet fails with
  a not-found error until it does.
- `keys[0]` has the default `{"*":["*"]}` capability, which permits object reads and writes.

---

## RSO3, RSO2 - mapSet primitives on the channel object, read back in compact and full modes

**Test ID**: `objects/integration/RSO3/mapset-primitives-roundtrip-0`

| Spec | Requirement |
|------|-------------|
| RSO3 | `publish` sends operations to the server |
| RSO5e | `mapSet` sets a key on an existing map |
| RSO10 | Publish result carries `messageId`, `channel` and `objectIds` |
| RSO2f | Compact result is the server's response, verbatim |
| RSO2g1, RSO14 | Full map result is a `RestLiveMap` |
| RSO9c | Full leaf entries decoded per OD5 |

Tests that every `PublishObjectData` leaf type round-trips through the server. Compact assertions are
limited to string, number and boolean leaves, whose compact representation the SDK does not transform.

### Setup
```pseudo
{ channel } = create_rest_channel("RSO3-primitives")
```

### Test Steps
```pseudo
publish_result = AWAIT channel.object.publish([
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "str", value: PublishObjectData(string: "hello"))),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "num", value: PublishObjectData(number: 42.5))),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "bool", value: PublishObjectData(boolean: true))),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "bin", value: PublishObjectData(bytes: bytes([0x01, 0x02, 0x03])))),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "jobj", value: PublishObjectData(json: { "a": [1, 2] }))),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "jarr", value: PublishObjectData(json: ["x", 1])))
])

compact = poll_until_success(
  condition: FUNCTION() =>
    c = AWAIT channel.object.get()
    IF c["jarr"] IS NOT null:
      RETURN c
    RETURN null
)

full = AWAIT channel.object.get(RestObjectGetParams(compact: false))
```

### Assertions
```pseudo
ASSERT publish_result.messageId IS String
ASSERT publish_result.messageId.length > 0
ASSERT publish_result.channel == channel.name
ASSERT publish_result.objectIds IS List

ASSERT compact["str"] == "hello"
ASSERT compact["num"] == 42.5
ASSERT compact["bool"] == true

ASSERT full IS RestLiveMap
ASSERT full.objectId == "root"
ASSERT full.map.semantics == "LWW"
ASSERT full.map.entries["str"].data.string == "hello"
ASSERT full.map.entries["num"].data.number == 42.5
ASSERT full.map.entries["bool"].data.boolean == true
ASSERT full.map.entries["bin"].data.bytes IS Binary
ASSERT full.map.entries["bin"].data.bytes == bytes([0x01, 0x02, 0x03])
ASSERT full.map.entries["jobj"].data.json == { "a": [1, 2] }
ASSERT full.map.entries["jarr"].data.json == ["x", 1]
```

---

## RSO3, RSO2 - Edge-case leaf values round-trip without being dropped or altered

**Test ID**: `objects/integration/RSO3/mapset-edge-values-roundtrip-1`

| Spec | Requirement |
|------|-------------|
| RSO3d2 | `mapSet.value` is encoded per OD4 and accepted by the server |
| RSO2f | Compact result is the server's response, verbatim |
| RSO9c2 | Full leaf entries decoded per OD5; `bytes` holds a native `Binary` |

Tests leaf values that an implementation can mistake for "absent" (empty string, empty bytes, `0`,
`false`) or lose precision on (the largest and smallest integers exactly representable as an IEEE 754
double, `±(2^53 - 1)`). Each must be stored and read back exactly. Compact assertions are limited to
string, number and boolean leaves, whose compact representation the SDK does not transform.

### Setup
```pseudo
{ channel } = create_rest_channel("RSO3-edge-values")

MAX_EXACT_INT = 9007199254740991    # 2^53 - 1
```

### Test Steps
```pseudo
AWAIT channel.object.publish([
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "emptyStr", value: PublishObjectData(string: ""))),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "emptyBin", value: PublishObjectData(bytes: bytes([])))),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "zero", value: PublishObjectData(number: 0))),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "maxInt", value: PublishObjectData(number: MAX_EXACT_INT))),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "minInt", value: PublishObjectData(number: -MAX_EXACT_INT))),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "no", value: PublishObjectData(boolean: false)))
])

compact = poll_until_success(
  condition: FUNCTION() =>
    c = AWAIT channel.object.get()
    IF "no" IN c:
      RETURN c
    RETURN null
)

full = AWAIT channel.object.get(RestObjectGetParams(compact: false))
```

### Assertions
```pseudo
ASSERT compact["emptyStr"] == ""
ASSERT compact["zero"] == 0
ASSERT compact["maxInt"] == MAX_EXACT_INT
ASSERT compact["minInt"] == -MAX_EXACT_INT
ASSERT compact["no"] == false

ASSERT full.map.entries["emptyStr"].data.string == ""
ASSERT full.map.entries["emptyBin"].data.bytes IS Binary
ASSERT full.map.entries["emptyBin"].data.bytes == bytes([])
ASSERT full.map.entries["zero"].data.number == 0
ASSERT full.map.entries["maxInt"].data.number == MAX_EXACT_INT
ASSERT full.map.entries["minInt"].data.number == -MAX_EXACT_INT
ASSERT full.map.entries["no"].data.boolean == false
```

---

## RSO2g3 - Full-mode get of a leaf value via path

**Test ID**: `objects/integration/RSO2g3/full-leaf-via-path-0`

**Spec requirement:** RSO2g3 — When the full-mode target is a leaf, it is returned as an `ObjectData` decoded per OD5, with `objectId` unset (RSO9c1).

### Setup
```pseudo
{ channel } = create_rest_channel("RSO2g3-leaf")

AWAIT channel.object.publish([
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "bin", value: PublishObjectData(bytes: bytes([0xFF, 0x00])))),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "prefs", value: PublishObjectData(json: { "theme": "dark" })))
])
```

### Test Steps
```pseudo
bin_leaf = poll_until_success(
  condition: FUNCTION() => AWAIT channel.object.get(RestObjectGetParams(path: "bin", compact: false))
)
json_leaf = poll_until_success(
  condition: FUNCTION() => AWAIT channel.object.get(RestObjectGetParams(path: "prefs", compact: false))
)
```

### Assertions
```pseudo
ASSERT bin_leaf.bytes IS Binary
ASSERT bin_leaf.bytes == bytes([0xFF, 0x00])

ASSERT json_leaf.json == { "theme": "dark" }
```

---

## RSO5g2, RSO5i, RSO15 - counterCreate at a path, counterInc via path and objectId

**Test ID**: `objects/integration/RSO5i/counter-create-increment-0`

| Spec | Requirement |
|------|-------------|
| RSO5g2 | `counterCreate` with `path` creates a counter at that location |
| RSO5i | `counterInc` changes a counter by a signed amount; targeted by `objectId` or `path` |
| RSO10c | `objectIds` identifies the affected objects |
| RSO15 | Full-mode counter is a `RestLiveCounter` |

### Setup
```pseudo
{ channel } = create_rest_channel("RSO5i-counter")
```

### Test Steps
```pseudo
create_result = AWAIT channel.object.publish(RestObjectOperation(
  path: "visits",
  counterCreate: RestObjectCounterCreate(count: 10)
))

counter_id = create_result.objectIds.find(id => id STARTS WITH "counter:")

AWAIT channel.object.publish(RestObjectOperation(
  path: "visits",
  counterInc: RestObjectCounterInc(number: 5)
))
AWAIT channel.object.publish(RestObjectOperation(
  objectId: counter_id,
  counterInc: RestObjectCounterInc(number: -3)
))

poll_until_success(
  condition: FUNCTION() => (AWAIT channel.object.get(RestObjectGetParams(path: "visits"))) == 12
)

full = AWAIT channel.object.get(RestObjectGetParams(objectId: counter_id, compact: false))
```

### Assertions
```pseudo
ASSERT counter_id IS NOT null

ASSERT full IS RestLiveCounter
ASSERT full.objectId == counter_id
ASSERT full.counter.data.number == 12
```

---

## RSO5g2, RSO5j - Standalone counterCreate returns a server-generated objectId

**Test ID**: `objects/integration/RSO5g2/standalone-counter-create-1`

| Spec | Requirement |
|------|-------------|
| RSO5g2 | `counterCreate` with neither `objectId` nor `path` creates a standalone object whose identifier is returned |
| RSO5j | For plain `counterCreate`, the server generates the `objectId` and returns it in `objectIds` |
| RSO15 | Full-mode counter is a `RestLiveCounter` |

### Setup
```pseudo
{ channel } = create_rest_channel("RSO5g2-standalone")
```

### Test Steps
```pseudo
result = AWAIT channel.object.publish(RestObjectOperation(
  counterCreate: RestObjectCounterCreate(count: 42)
))

counter_id = result.objectIds[0]

full = poll_until_success(
  condition: FUNCTION() => AWAIT channel.object.get(RestObjectGetParams(objectId: counter_id, compact: false))
)
```

### Assertions
```pseudo
ASSERT result.objectIds.length == 1
ASSERT counter_id STARTS WITH "counter:"

ASSERT full IS RestLiveCounter
ASSERT full.objectId == counter_id
ASSERT full.counter.data.number == 42
```

---

## RSO5c3, RSO5j - Standalone mapCreate returns a server-generated objectId

**Test ID**: `objects/integration/RSO5j/standalone-map-create-0`

| Spec | Requirement |
|------|-------------|
| RSO5c3 | `mapCreate` with neither `objectId` nor `path` creates a standalone object whose identifier is returned |
| RSO5j | For plain `mapCreate`, the server generates the `objectId` and returns it in `objectIds` |
| RSO3d2, RSO13 | Entry data of every `PublishObjectData` leaf type is encoded per OD4 and accepted by the server |

### Setup
```pseudo
{ channel } = create_rest_channel("RSO5j-standalone")
```

### Test Steps
```pseudo
result = AWAIT channel.object.publish(RestObjectOperation(
  mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {
    "name": RestObjectMapEntry(data: PublishObjectData(string: "Alice")),
    "age": RestObjectMapEntry(data: PublishObjectData(number: 30)),
    "active": RestObjectMapEntry(data: PublishObjectData(boolean: true)),
    "avatar": RestObjectMapEntry(data: PublishObjectData(bytes: bytes([0x0A, 0x0B]))),
    "prefs": RestObjectMapEntry(data: PublishObjectData(json: { "theme": "dark" })),
    "tags": RestObjectMapEntry(data: PublishObjectData(json: ["a", "b"]))
  })
))

map_id = result.objectIds[0]

full = poll_until_success(
  condition: FUNCTION() => AWAIT channel.object.get(RestObjectGetParams(objectId: map_id, compact: false))
)
```

### Assertions
```pseudo
ASSERT result.objectIds.length == 1
ASSERT map_id STARTS WITH "map:"

ASSERT full IS RestLiveMap
ASSERT full.objectId == map_id
ASSERT full.map.entries["name"].data.string == "Alice"
ASSERT full.map.entries["age"].data.number == 30
ASSERT full.map.entries["active"].data.boolean == true
ASSERT full.map.entries["avatar"].data.bytes IS Binary
ASSERT full.map.entries["avatar"].data.bytes == bytes([0x0A, 0x0B])
ASSERT full.map.entries["prefs"].data.json == { "theme": "dark" }
ASSERT full.map.entries["tags"].data.json == ["a", "b"]
```

---

## RSO5c3, RSO2g1 - mapCreate at a path is reachable from the channel object

**Test ID**: `objects/integration/RSO5c3/map-create-at-path-0`

| Spec | Requirement |
|------|-------------|
| RSO5c3 | `mapCreate` with `path` creates the map at that location |
| RSO2g1 | Nested maps in a full-mode response are decoded recursively as `RestLiveMap` |
| RSO2d | `path` and `objectId` targeting of `get` |

### Setup
```pseudo
{ channel } = create_rest_channel("RSO5c3-path")
```

### Test Steps
```pseudo
AWAIT channel.object.publish(RestObjectOperation(
  path: "profile",
  mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {
    "nickname": RestObjectMapEntry(data: PublishObjectData(string: "ally"))
  })
))

root_full = poll_until_success(
  condition: FUNCTION() =>
    r = AWAIT channel.object.get(RestObjectGetParams(compact: false))
    IF "profile" IN r.map.entries:
      RETURN r
    RETURN null
)

profile = root_full.map.entries["profile"].data
nickname_via_path = AWAIT channel.object.get(RestObjectGetParams(path: "profile.nickname"))
nickname_via_id = AWAIT channel.object.get(RestObjectGetParams(objectId: profile.objectId, path: "nickname"))
```

### Assertions
```pseudo
ASSERT profile IS RestLiveMap
ASSERT profile.objectId STARTS WITH "map:"
ASSERT profile.map.entries["nickname"].data.string == "ally"

ASSERT nickname_via_path == "ally"
ASSERT nickname_via_id == "ally"
```

---

## RSO5e, RSO6 - mapSet targeted by a nested path

**Test ID**: `objects/integration/RSO5e/mapset-nested-path-0`

| Spec | Requirement |
|------|-------------|
| RSO5e | `mapSet` sets a key on an existing map, targeted by `path` |
| RSO6 | Caller-supplied `path` strings, including dot-separated nested paths, are passed to the server without modification |

Tests `mapSet` targeted by a single-segment path and by a dot-separated nested path (without
wildcards), observing that each key lands on the intended map.

### Setup
```pseudo
{ channel } = create_rest_channel("RSO5e-nested-path")

AWAIT channel.object.publish(RestObjectOperation(path: "outer",
  mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {})))
poll_until_success(
  condition: FUNCTION() => (AWAIT channel.object.get(RestObjectGetParams(path: "outer"))) IS NOT null
)

AWAIT channel.object.publish(RestObjectOperation(path: "outer.inner",
  mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {})))
poll_until_success(
  condition: FUNCTION() => (AWAIT channel.object.get(RestObjectGetParams(path: "outer.inner"))) IS NOT null
)
```

### Test Steps
```pseudo
AWAIT channel.object.publish([
  RestObjectOperation(path: "outer",
    mapSet: RestObjectMapSet(key: "shallow", value: PublishObjectData(number: 1))),
  RestObjectOperation(path: "outer.inner",
    mapSet: RestObjectMapSet(key: "deep", value: PublishObjectData(string: "value")))
])

compact = poll_until_success(
  condition: FUNCTION() =>
    c = AWAIT channel.object.get()
    IF c["outer"]["shallow"] == 1 AND c["outer"]["inner"]["deep"] == "value":
      RETURN c
    RETURN null
)
```

### Assertions
```pseudo
ASSERT compact["outer"] == { "shallow": 1, "inner": { "deep": "value" } }
```

---

## RSO5e, RSO7 - mapSet with an objectId reference to an existing object

**Test ID**: `objects/integration/RSO5e/mapset-object-reference-1`

| Spec | Requirement |
|------|-------------|
| RSO5e | `mapSet` sets a key on an existing map |
| RSO7 | `PublishObjectData.objectId` references an existing object |
| RSO10 | Publish result carries `messageId`, `channel` and `objectIds` |
| RSO2g | Full-mode response carries the referenced object's `objectId` under each referencing key |

Tests that a `mapSet` whose value is an `objectId` reference to an object created by an earlier,
separate publish makes a second key reference the same object.

When an object is reachable under several keys, the server may inline its contents under only one of
them and return the others as a bare object reference; which key gets the inlined contents is
server-defined. The assertions therefore check only the `objectId` under each key, and read the
counter's value by `objectId`.

### Setup
```pseudo
{ channel } = create_rest_channel("RSO5e-object-ref")

create_result = AWAIT channel.object.publish(RestObjectOperation(
  path: "first",
  counterCreate: RestObjectCounterCreate(count: 5)
))
counter_id = create_result.objectIds.find(id => id STARTS WITH "counter:")

poll_until_success(
  condition: FUNCTION() => (AWAIT channel.object.get(RestObjectGetParams(path: "first"))) == 5
)
```

### Test Steps
```pseudo
set_result = AWAIT channel.object.publish(RestObjectOperation(
  objectId: "root",
  mapSet: RestObjectMapSet(key: "second", value: PublishObjectData(objectId: counter_id))
))

full = poll_until_success(
  condition: FUNCTION() =>
    r = AWAIT channel.object.get(RestObjectGetParams(compact: false))
    IF "second" IN r.map.entries:
      RETURN r
    RETURN null
)

counter = AWAIT channel.object.get(RestObjectGetParams(objectId: counter_id, compact: false))
```

### Assertions
```pseudo
ASSERT counter_id IS NOT null

ASSERT set_result.messageId IS String
ASSERT set_result.messageId.length > 0
ASSERT set_result.channel == channel.name
ASSERT set_result.objectIds IS List

ASSERT full.map.entries["first"].data.objectId == counter_id
ASSERT full.map.entries["second"].data.objectId == counter_id

ASSERT counter IS RestLiveCounter
ASSERT counter.counter.data.number == 5
```

---

## RSO5f - mapRemove via path and via objectId

**Test ID**: `objects/integration/RSO5f/map-remove-0`

**Spec requirement:** RSO5f — `mapRemove` removes a key from an existing map, targeted by `objectId` or `path`.

### Setup
```pseudo
{ channel } = create_rest_channel("RSO5f-remove")

AWAIT channel.object.publish([
  RestObjectOperation(path: "settings",
    mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {
      "a": RestObjectMapEntry(data: PublishObjectData(number: 1)),
      "b": RestObjectMapEntry(data: PublishObjectData(number: 2))
    })),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "keep", value: PublishObjectData(string: "x"))),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "drop", value: PublishObjectData(string: "y")))
])
```

### Test Steps
```pseudo
AWAIT channel.object.publish([
  RestObjectOperation(path: "settings", mapRemove: RestObjectMapRemove(key: "a")),
  RestObjectOperation(objectId: "root", mapRemove: RestObjectMapRemove(key: "drop"))
])

compact = poll_until_success(
  condition: FUNCTION() =>
    c = AWAIT channel.object.get()
    IF "drop" NOT IN c AND c["settings"] IS NOT null AND "a" NOT IN c["settings"]:
      RETURN c
    RETURN null
)
```

### Assertions
```pseudo
ASSERT compact["keep"] == "x"
ASSERT "drop" NOT IN compact
ASSERT compact["settings"] == { "b": 2 }
```

---

## RSO6 - Wildcard path passed through to the server

**Test ID**: `objects/integration/RSO6/wildcard-path-passthrough-0`

**Spec requirement:** RSO6 — Caller-supplied `path` strings are passed to the server without modification; path semantics are server-defined.

Tests end-to-end that a path using the server's `*` wildcard segment is passed through unmodified,
by observing its server-side effect on every child of a map.

### Setup
```pseudo
{ channel } = create_rest_channel("RSO6-wildcard")

AWAIT channel.object.publish(RestObjectOperation(path: "items",
  mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {})))
poll_until_success(
  condition: FUNCTION() => (AWAIT channel.object.get(RestObjectGetParams(path: "items"))) IS NOT null
)

AWAIT channel.object.publish([
  RestObjectOperation(path: "items.one",
    mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {})),
  RestObjectOperation(path: "items.two",
    mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {}))
])
poll_until_success(
  condition: FUNCTION() =>
    i = AWAIT channel.object.get(RestObjectGetParams(path: "items"))
    RETURN "one" IN i AND "two" IN i
)
```

### Test Steps
```pseudo
AWAIT channel.object.publish(RestObjectOperation(
  path: "items.*",
  mapSet: RestObjectMapSet(key: "flag", value: PublishObjectData(boolean: true))
))

items = poll_until_success(
  condition: FUNCTION() =>
    i = AWAIT channel.object.get(RestObjectGetParams(path: "items"))
    IF i["one"]["flag"] == true AND i["two"]["flag"] == true:
      RETURN i
    RETURN null
)
```

### Assertions
```pseudo
ASSERT items["one"]["flag"] == true
ASSERT items["two"]["flag"] == true
```

---

## RSO6, RSO5f, RSO5i - Wildcard path with mapRemove and counterInc

**Test ID**: `objects/integration/RSO6/wildcard-remove-increment-1`

| Spec | Requirement |
|------|-------------|
| RSO6 | Caller-supplied `path` strings are passed to the server without modification |
| RSO5f | `mapRemove` targeted by `path` |
| RSO5i | `counterInc` targeted by `path` |

Tests that a wildcard path works with operations other than `mapSet`: a `mapRemove` that removes the
same key from every child map, and a `counterInc` that increments every child counter.

### Setup
```pseudo
{ channel } = create_rest_channel("RSO6-wildcard-ops")

AWAIT channel.object.publish([
  RestObjectOperation(path: "maps",
    mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {})),
  RestObjectOperation(path: "counters",
    mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {}))
])
poll_until_success(
  condition: FUNCTION() =>
    c = AWAIT channel.object.get()
    RETURN "maps" IN c AND "counters" IN c
)

AWAIT channel.object.publish([
  RestObjectOperation(path: "maps.one",
    mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {
      "foo": RestObjectMapEntry(data: PublishObjectData(string: "a")),
      "keep": RestObjectMapEntry(data: PublishObjectData(number: 1))
    })),
  RestObjectOperation(path: "maps.two",
    mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {
      "foo": RestObjectMapEntry(data: PublishObjectData(string: "b")),
      "keep": RestObjectMapEntry(data: PublishObjectData(number: 2))
    })),
  RestObjectOperation(path: "counters.c1", counterCreate: RestObjectCounterCreate(count: 10)),
  RestObjectOperation(path: "counters.c2", counterCreate: RestObjectCounterCreate(count: 20))
])
poll_until_success(
  condition: FUNCTION() =>
    c = AWAIT channel.object.get()
    RETURN "one" IN c["maps"] AND "two" IN c["maps"] AND "c1" IN c["counters"] AND "c2" IN c["counters"]
)
```

### Test Steps
```pseudo
AWAIT channel.object.publish([
  RestObjectOperation(path: "maps.*", mapRemove: RestObjectMapRemove(key: "foo")),
  RestObjectOperation(path: "counters.*", counterInc: RestObjectCounterInc(number: 5))
])

compact = poll_until_success(
  condition: FUNCTION() =>
    c = AWAIT channel.object.get()
    IF "foo" NOT IN c["maps"]["one"] AND "foo" NOT IN c["maps"]["two"]
        AND c["counters"]["c1"] == 15 AND c["counters"]["c2"] == 25:
      RETURN c
    RETURN null
)
```

### Assertions
```pseudo
ASSERT compact["maps"]["one"] == { "keep": 1 }
ASSERT compact["maps"]["two"] == { "keep": 2 }
ASSERT compact["counters"]["c1"] == 15
ASSERT compact["counters"]["c2"] == 25
```

---

## RSO4, RSO5d, RSO5h - Locally generated object IDs accepted in a single batch

**Test ID**: `objects/integration/RSO4/generated-ids-batch-0`

| Spec | Requirement |
|------|-------------|
| RSO4 | `generateObjectId` computes `objectId`, `nonce`, `initialValue` locally |
| RSO5d | `mapCreateWithObjectId` creates a map with the client-generated ID |
| RSO5h | `counterCreateWithObjectId` creates a counter with the client-generated ID |
| RSO3c | All operations in an array are sent in a single request |

Tests that IDs generated by the SDK are accepted by the server — which validates the `objectId`
against `initialValue` and `nonce` — and that a batch can reference the new objects before the server
has assigned anything.

### Setup
```pseudo
{ channel } = create_rest_channel("RSO4-generated")
```

### Test Steps
```pseudo
counter = AWAIT channel.object.generateObjectId(RestObjectGenerateIdBody(
  counterCreate: RestObjectCounterCreate(count: 7)
))
map = AWAIT channel.object.generateObjectId(RestObjectGenerateIdBody(
  mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {
    "visits": RestObjectMapEntry(data: PublishObjectData(objectId: counter.objectId)),
    "label": RestObjectMapEntry(data: PublishObjectData(string: "stats")),
    "raw": RestObjectMapEntry(data: PublishObjectData(bytes: bytes([0x01])))
  })
))

result = AWAIT channel.object.publish([
  RestObjectOperation(objectId: counter.objectId,
    counterCreateWithObjectId: RestObjectCreateWithObjectId(
      initialValue: counter.initialValue, nonce: counter.nonce)),
  RestObjectOperation(objectId: map.objectId,
    mapCreateWithObjectId: RestObjectCreateWithObjectId(
      initialValue: map.initialValue, nonce: map.nonce)),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "stats", value: PublishObjectData(objectId: map.objectId)))
])

stats = poll_until_success(
  condition: FUNCTION() => AWAIT channel.object.get(RestObjectGetParams(path: "stats", compact: false))
)
```

### Assertions
```pseudo
ASSERT counter.objectId STARTS WITH "counter:"
ASSERT map.objectId STARTS WITH "map:"
ASSERT result.objectIds CONTAINS counter.objectId
ASSERT result.objectIds CONTAINS map.objectId

ASSERT stats IS RestLiveMap
ASSERT stats.objectId == map.objectId
ASSERT stats.map.entries["label"].data.string == "stats"
ASSERT stats.map.entries["raw"].data.bytes == bytes([0x01])

visits = stats.map.entries["visits"].data
ASSERT visits IS RestLiveCounter
ASSERT visits.objectId == counter.objectId
ASSERT visits.counter.data.number == 7
```

---

## RSO5a1 - Operation id makes a publish idempotent

**Test ID**: `objects/integration/RSO5a1/idempotent-operation-id-0`

**Spec requirement:** RSO5a1 — `id` is a per-operation message ID for idempotent publishing; the SDK sends a caller-supplied `id` unchanged (RSO3d3), so the server can de-duplicate.

### Setup
```pseudo
{ channel } = create_rest_channel("RSO5a1-idempotent")

AWAIT channel.object.publish(RestObjectOperation(
  path: "count",
  counterCreate: RestObjectCounterCreate(count: 0)
))
poll_until_success(
  condition: FUNCTION() => (AWAIT channel.object.get(RestObjectGetParams(path: "count"))) == 0
)

op_id = "idem-" + random_id()
```

### Test Steps
```pseudo
AWAIT channel.object.publish(RestObjectOperation(
  id: op_id, path: "count", counterInc: RestObjectCounterInc(number: 1)))
AWAIT channel.object.publish(RestObjectOperation(
  id: op_id, path: "count", counterInc: RestObjectCounterInc(number: 1)))

# Marker write published after both increments; once it is visible, both increments have been processed
AWAIT channel.object.publish(RestObjectOperation(
  objectId: "root", mapSet: RestObjectMapSet(key: "marker", value: PublishObjectData(boolean: true))))
compact = poll_until_success(
  condition: FUNCTION() =>
    c = AWAIT channel.object.get()
    IF c["marker"] == true:
      RETURN c
    RETURN null
)
```

### Assertions
```pseudo
ASSERT compact["count"] == 1
```

---

## RSL16, RSO2g - State written by a realtime client is readable via REST

**Test ID**: `objects/integration/RSL16/realtime-write-rest-read-0`

| Spec | Requirement |
|------|-------------|
| RSL16 | `RestChannel#object` reads the same channel object that realtime clients write |
| RSO2f | Compact result is the server's response, verbatim |
| RSO2g1, RSO2g2, RSO2g3 | Full-mode response decoded into `RestLiveMap`, `RestLiveCounter` and `ObjectData` leaves |

Tests interoperability between the realtime and REST object APIs: objects created over a realtime
connection (via `PathObject#set` with `LiveMap`/`LiveCounter` value types) are decoded correctly by
`RestObject#get`. All other tests in this file write via REST.

### Setup
```pseudo
channel_name = "objects-rest-RSL16-interop-" + random_id()

realtime = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "nonprod:sandbox",
  autoConnect: false,
  useBinaryProtocol: PROTOCOL == "msgpack",
  plugins: { Objects: objects_plugin }
))
realtime.connect()
AWAIT_STATE realtime.connection.state == CONNECTED

realtime_channel = realtime.channels.get(channel_name, { modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"] })
root = AWAIT realtime_channel.object.get()

rest = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "nonprod:sandbox",
  useBinaryProtocol: PROTOCOL == "msgpack",
  plugins: { Objects: objects_plugin }
))
channel = rest.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT root.set("str", "hello")
AWAIT root.set("bin", bytes([0x01, 0x02, 0x03]))
AWAIT root.set("prefs", { "theme": "dark" })
AWAIT root.set("visits", LiveCounter.create(7))
AWAIT root.set("profile", LiveMap.create({ "nickname": "ally" }))

full = poll_until_success(
  condition: FUNCTION() =>
    r = AWAIT channel.object.get(RestObjectGetParams(compact: false))
    IF "profile" IN r.map.entries:
      RETURN r
    RETURN null
)
compact = AWAIT channel.object.get()
```

### Assertions
```pseudo
ASSERT compact["str"] == "hello"
ASSERT compact["visits"] == 7
ASSERT compact["profile"]["nickname"] == "ally"

ASSERT full IS RestLiveMap
ASSERT full.objectId == "root"
ASSERT full.map.entries["str"].data.string == "hello"
ASSERT full.map.entries["bin"].data.bytes IS Binary
ASSERT full.map.entries["bin"].data.bytes == bytes([0x01, 0x02, 0x03])
ASSERT full.map.entries["prefs"].data.json == { "theme": "dark" }

visits = full.map.entries["visits"].data
ASSERT visits IS RestLiveCounter
ASSERT visits.objectId STARTS WITH "counter:"
ASSERT visits.counter.data.number == 7

profile = full.map.entries["profile"].data
ASSERT profile IS RestLiveMap
ASSERT profile.objectId STARTS WITH "map:"
ASSERT profile.map.entries["nickname"].data.string == "ally"
```

### Teardown
```pseudo
realtime.close()
```

---

## RSO2h - Server error for an unresolvable target surfaced as ErrorInfo

**Test ID**: `objects/integration/RSO2h/unresolvable-target-error-0`

**Spec requirement:** RSO2h — The library does not validate `objectId` or `path`; server-returned errors are surfaced to the caller as a rejected `ErrorInfo`.

The specific error codes are server-defined, so this test asserts only that the rejection is a
client-error `ErrorInfo`.

### Setup
```pseudo
{ channel } = create_rest_channel("RSO2h-errors")
```

### Test Steps and Assertions
```pseudo
AWAIT channel.object.get(RestObjectGetParams(
  objectId: "map:doesNotExistAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA@1700000000000"
)) FAILS WITH error
ASSERT error IS ErrorInfo
ASSERT error.statusCode >= 400 AND error.statusCode < 500

AWAIT channel.object.get(RestObjectGetParams(path: "no.such.path")) FAILS WITH path_error
ASSERT path_error IS ErrorInfo
ASSERT path_error.statusCode >= 400 AND path_error.statusCode < 500
```
