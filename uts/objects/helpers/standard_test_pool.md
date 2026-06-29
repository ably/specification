# Standard Test Pool and Helpers

Shared fixtures, protocol message builders, and synced-channel setup pattern for all LiveObjects test files.

## Standard Test Tree

The standard test pool defines a fixed LiveObjects tree used across test files. All object IDs use short synthetic values for clarity (real servers validate the hash format, but unit tests construct objects directly).

```
root (LiveMap, objectId: "root", semantics: LWW)
  +-- "name" -> string "Alice"
  +-- "age" -> number 30
  +-- "active" -> boolean true
  +-- "score" -> objectId "counter:score@1000"
  +-- "profile" -> objectId "map:profile@1000"
  +-- "data" -> json {"tags": ["a", "b"]}
  +-- "avatar" -> bytes base64("AQID") (raw bytes: [1, 2, 3])

counter:score@1000 (LiveCounter, data: 100)

map:profile@1000 (LiveMap, semantics: LWW)
  +-- "email" -> string "alice@example.com"
  +-- "nested_counter" -> objectId "counter:nested@1000"
  +-- "prefs" -> objectId "map:prefs@1000"

counter:nested@1000 (LiveCounter, data: 5)

map:prefs@1000 (LiveMap, semantics: LWW)
  +-- "theme" -> string "dark"
```

All map entries have timeserial `"t:0"` and `tombstone: false` unless otherwise noted.
All objects have `siteTimeserials: { "aaa": "t:0" }` and `createOperationIsMerged: true` unless otherwise noted.

### Expected parentReferences after sync

After `setup_synced_channel` completes (including the RTO5c10 rebuild), each object's `parentReferences` should be:

| Object | parentReferences |
|--------|-----------------|
| `root` | `{}` (empty -- root is not referenced by any parent) |
| `counter:score@1000` | `{ "root": {"score"} }` |
| `map:profile@1000` | `{ "root": {"profile"} }` |
| `counter:nested@1000` | `{ "map:profile@1000": {"nested_counter"} }` |
| `map:prefs@1000` | `{ "map:profile@1000": {"prefs"} }` |

Only entries whose value is a `LiveObject` (i.e. `data.objectId` is present) contribute to parentReferences. Primitive-valued entries ("name", "age", "active", "data", "avatar", "email", "theme") do not.

---

## STANDARD_POOL_OBJECTS

An array of `ObjectMessage` instances wrapping `ObjectState` for building OBJECT_SYNC messages. Each object is represented as `build_object_state(...)` using the builders below.

```pseudo
STANDARD_POOL_OBJECTS = [
  build_object_state("root", {"aaa": "t:0"}, {
    map: {
      semantics: "LWW",
      entries: {
        "name":    { data: { string: "Alice" },                     timeserial: "t:0" },
        "age":     { data: { number: 30 },                          timeserial: "t:0" },
        "active":  { data: { boolean: true },                       timeserial: "t:0" },
        "score":   { data: { objectId: "counter:score@1000" },      timeserial: "t:0" },
        "profile": { data: { objectId: "map:profile@1000" },        timeserial: "t:0" },
        "data":    { data: { json: {"tags": ["a", "b"]} },          timeserial: "t:0" },
        "avatar":  { data: { bytes: "AQID" },                       timeserial: "t:0" }
      }
    },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  }),
  build_object_state("counter:score@1000", {"aaa": "t:0"}, {
    counter: { count: 100 },
    createOp: { counterCreate: { count: 100 } }
  }),
  build_object_state("map:profile@1000", {"aaa": "t:0"}, {
    map: {
      semantics: "LWW",
      entries: {
        "email":          { data: { string: "alice@example.com" },            timeserial: "t:0" },
        "nested_counter": { data: { objectId: "counter:nested@1000" },        timeserial: "t:0" },
        "prefs":          { data: { objectId: "map:prefs@1000" },             timeserial: "t:0" }
      }
    },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  }),
  build_object_state("counter:nested@1000", {"aaa": "t:0"}, {
    counter: { count: 5 },
    createOp: { counterCreate: { count: 5 } }
  }),
  build_object_state("map:prefs@1000", {"aaa": "t:0"}, {
    map: {
      semantics: "LWW",
      entries: {
        "theme": { data: { string: "dark" }, timeserial: "t:0" }
      }
    },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  })
]
```

---

## Builder Functions

### Protocol Message Builders

```pseudo
build_object_sync_message(channel, channelSerial, objectMessages[]):
  RETURN ProtocolMessage(
    action: OBJECT_SYNC,
    channel: channel,
    channelSerial: channelSerial,
    state: objectMessages
  )

build_object_message(channel, objectMessages[]):
  RETURN ProtocolMessage(
    action: OBJECT,
    channel: channel,
    state: objectMessages
  )

build_ack_message(msgSerial, serials[]):
  RETURN ProtocolMessage(
    action: ACK,
    msgSerial: msgSerial,
    res: [{ serials: serials }]
  )
```

### ObjectMessage Builders (Operations)

```pseudo
build_counter_inc(objectId, number, serial, siteCode):
  RETURN ObjectMessage(
    serial: serial,
    siteCode: siteCode,
    operation: {
      action: "COUNTER_INC",
      objectId: objectId,
      counterInc: { number: number }
    }
  )

build_map_set(objectId, key, value, serial, siteCode):
  RETURN ObjectMessage(
    serial: serial,
    siteCode: siteCode,
    operation: {
      action: "MAP_SET",
      objectId: objectId,
      mapSet: { key: key, value: value }
    }
  )

build_map_remove(objectId, key, serial, siteCode, serialTimestamp?):
  RETURN ObjectMessage(
    serial: serial,
    siteCode: siteCode,
    serialTimestamp: serialTimestamp,
    operation: {
      action: "MAP_REMOVE",
      objectId: objectId,
      mapRemove: { key: key }
    }
  )

build_map_clear(objectId, serial, siteCode):
  RETURN ObjectMessage(
    serial: serial,
    siteCode: siteCode,
    operation: {
      action: "MAP_CLEAR",
      objectId: objectId
    }
  )

build_object_delete(objectId, serial, siteCode, serialTimestamp?):
  RETURN ObjectMessage(
    serial: serial,
    siteCode: siteCode,
    serialTimestamp: serialTimestamp,
    operation: {
      action: "OBJECT_DELETE",
      objectId: objectId
    }
  )

build_counter_create(objectId, counterCreate, serial, siteCode):
  RETURN ObjectMessage(
    serial: serial,
    siteCode: siteCode,
    operation: {
      action: "COUNTER_CREATE",
      objectId: objectId,
      counterCreate: counterCreate
    }
  )

build_map_create(objectId, mapCreate, serial, siteCode):
  RETURN ObjectMessage(
    serial: serial,
    siteCode: siteCode,
    operation: {
      action: "MAP_CREATE",
      objectId: objectId,
      mapCreate: mapCreate
    }
  )
```

### ObjectMessage Builder (State — for OBJECT_SYNC)

```pseudo
build_object_state(objectId, siteTimeserials, opts):
  state = {
    objectId: objectId,
    siteTimeserials: siteTimeserials
  }
  IF opts.map IS NOT null:
    state.map = opts.map
  IF opts.counter IS NOT null:
    state.counter = opts.counter
  IF opts.tombstone IS NOT null:
    state.tombstone = opts.tombstone
  IF opts.createOp IS NOT null:
    state.createOp = opts.createOp
  RETURN ObjectMessage(object: state)
```

### ObjectMessage Builder (State wrapper)

Wraps an existing `ObjectState` in an `ObjectMessage` with the `object` field populated. Used when `replaceData` (RTLC6, RTLM6) needs an `ObjectMessage` rather than a bare `ObjectState`.

```pseudo
build_object_message_with_state(objectState):
  RETURN ObjectMessage(object: objectState)
```

### PublicAPI::ObjectMessage Builder

Constructs a `PublicAPI::ObjectMessage` from an internal `ObjectMessage` and a channel name, per PAOM3. Used by subscription tests that verify the user-facing message delivered to listeners.

```pseudo
build_public_object_message(objectMessage, channelName):
  pub = PublicAPI::ObjectMessage()
  pub.channel = channelName
  pub.id = objectMessage.id
  pub.clientId = objectMessage.clientId
  pub.connectionId = objectMessage.connectionId
  pub.timestamp = objectMessage.timestamp
  pub.serial = objectMessage.serial
  pub.serialTimestamp = objectMessage.serialTimestamp
  pub.siteCode = objectMessage.siteCode
  pub.extras = objectMessage.extras
  pub.operation = PublicAPI::ObjectOperation from objectMessage.operation per PAOOP3
  RETURN pub
```

---

## Standard Synced-Channel Setup

Used by all mock WebSocket test files. Creates a connected client with a synced channel containing the standard test pool.

After the OBJECT_SYNC sequence completes, the SDK rebuilds parentReferences per RTO5c10: reset all LiveObject parentReferences to empty (RTLO3f2), then iterate all LiveMap entries calling addParentReference (RTLO4g) for each entry whose value is a LiveObject. See "Expected parentReferences after sync" above for the resulting state.

```pseudo
setup_synced_channel(channel_name):
  mock_ws = MockWebSocket(
    onConnectionAttempt: (conn) => conn.respond_with_success(
      ProtocolMessage(action: CONNECTED, connectionDetails: {
        connectionId: "conn-1",
        connectionKey: "conn-key-1",
        siteCode: "test-site",
        objectsGCGracePeriod: 86400000
      })
    ),
    onMessageFromClient: (msg) => {
      IF msg.action == ATTACH:
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: msg.channel,
          channelSerial: "sync1:",
          flags: HAS_OBJECTS
        ))
        mock_ws.send_to_client(build_object_sync_message(
          msg.channel, "sync1:", STANDARD_POOL_OBJECTS
        ))
      ELSE IF msg.action == OBJECT:
        serials = []
        FOR i IN 0..msg.state.length - 1:
          serials.append("ack-" + msg.msgSerial + ":" + i)
        mock_ws.send_to_client(build_ack_message(msg.msgSerial, serials))
    }
  )
  install_mock(mock_ws)

  client = Realtime(options: {
    key: "fake:key",
    autoConnect: true
  })
  channel = client.channels.get(channel_name, {
    modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"]
  })
  root = AWAIT channel.object.get()

  RETURN { client, channel, root, mock_ws }
```

### Variant: Setup Without Auto-ACK

For tests that need to control ACK timing, use this variant that omits the OBJECT message handler:

```pseudo
setup_synced_channel_no_ack(channel_name):
  mock_ws = MockWebSocket(
    onConnectionAttempt: (conn) => conn.respond_with_success(
      ProtocolMessage(action: CONNECTED, connectionDetails: {
        connectionId: "conn-1",
        connectionKey: "conn-key-1",
        siteCode: "test-site",
        objectsGCGracePeriod: 86400000
      })
    ),
    onMessageFromClient: (msg) => {
      IF msg.action == ATTACH:
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: msg.channel,
          channelSerial: "sync1:",
          flags: HAS_OBJECTS
        ))
        mock_ws.send_to_client(build_object_sync_message(
          msg.channel, "sync1:", STANDARD_POOL_OBJECTS
        ))
    }
  )
  install_mock(mock_ws)

  client = Realtime(options: {
    key: "fake:key",
    autoConnect: true
  })
  channel = client.channels.get(channel_name, {
    modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"]
  })
  root = AWAIT channel.object.get()

  RETURN { client, channel, root, mock_ws }
```

---

## REST Fixture Provisioning

For integration tests that need pre-existing object state before the test client connects, use the REST API to establish fixtures.

The objects REST API uses the **V2 format** (per the LiveObjects OpenAPI specification). A request publishes a single operation, or a batch of operations as a JSON array — there is **no** `{ "messages": [...] }` envelope. Each operation names its type via a payload key (`mapSet`, `mapRemove`, `mapCreate`, `counterInc`, `counterCreate`) and targets an object by `objectId` **or** `path`. Note the endpoint path is singular (`/object`).

```pseudo
provision_objects_via_rest(api_key, channel_name, operations):
  # operations: a single operation object, or an array of operation objects (batch)
  POST https://sandbox.realtime.ably-nonprod.net/channels/{encode_uri_component(channel_name)}/object
    WITH Authorization: Basic {base64(api_key)}
    WITH Content-Type: application/json
    WITH body: operations
```

Operation shapes (target by `objectId` or `path`; an optional `id` on any operation is an idempotency key):

```pseudo
{ mapSet:        { key: "<key>", value: <value> },                          objectId|path: "<target>" }
{ mapRemove:     { key: "<key>" },                                          objectId|path: "<target>" }
{ mapCreate:     { semantics: 0, entries: { "<key>": { data: <value> } } } [, objectId|path: "<target>"] }  # semantics 0 = LWW
{ counterCreate: { count: <number> }                                       [, objectId|path: "<target>"] }
{ counterInc:    { number: <number> },                                      objectId|path: "<target>" }      # negative number = decrement
```

where `<value>` is a primitive value object: `{ string: "..." }`, `{ number: ... }`, `{ boolean: ... }`, `{ bytes: "<base64>" }`, or a reference `{ objectId: "..." }` (`string`/`bytes` may also carry an optional `encoding`).
