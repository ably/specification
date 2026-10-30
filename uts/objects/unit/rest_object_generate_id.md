# RestObject generateObjectId Tests

Spec points: `RSO4`, `RSO4a1`, `RSO4b`, `RSO4c`, `RSO4d`, `RSO4e`, `RSO4e1`, `RSO4e1a`, `RSO4e1b`, `RSO4e1c`, `RSO4e2`, `RSO4f`, `RSO4g`, `RSO4h`, `RSO4j`, `RSO4k`, `RSO5d`, `RSO5h`, `RSO12`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

## Purpose

Tests local object ID generation for REST callers: the `initialValue` encoding, nonce generation,
use of server time, and the derivation of `objectId` per RTO14. The mocked HTTP client answers the
server time request (RTO16, via `RestClient#time`) and any `publish` request; no other requests are
expected.

## Common Setup

`objects_plugin` denotes the SDK's `Objects` plugin ([PC5](../../../specifications/features.md#PC5)),
supplied under the `Objects` `PluginType` key.

`mapCreate.semantics` is written as the symbolic enum value `"LWW"` in inputs (see *Enum values* in the
UTS README), and is asserted inside `initialValue` as its `ObjectsMapSemantics` integer encoding (`0`,
per OMP2).

```pseudo
SERVER_TIME = 1700000000000

setup_rest_object(channel_name, use_binary_protocol: false):
  captured_requests = []

  mock_http = MockHttpClient(
    onConnectionAttempt: (conn) => conn.respond_with_success(),
    onRequest: (req) => {
      captured_requests.append(req)
      IF req.url.path == "/time":
        req.respond_with(200, [SERVER_TIME])
      ELSE:
        req.respond_with(201, { "messageId": "msg-id-1", "channel": channel_name, "objectIds": [] })
    }
  )
  install_mock(mock_http)

  client = Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    useBinaryProtocol: use_binary_protocol,
    plugins: { Objects: objects_plugin }
  ))
  channel = client.channels.get(channel_name)

  RETURN { client, channel, captured_requests }
```

---

## RSO4d - Map create body yields a map objectId

**Test ID**: `objects/unit/RSO4d/map-type-objectid-0`

**Spec requirement:** RSO4d — The RTO14 `type` is `map` when `createBody.mapCreate` is provided.

### Setup
```pseudo
{ channel } = setup_rest_object("test-RSO4d-map-" + random_id())
```

### Test Steps
```pseudo
result = AWAIT channel.object.generateObjectId(RestObjectGenerateIdBody(
  mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {})
))
```

### Assertions
```pseudo
ASSERT result.objectId STARTS WITH "map:"
```

---

## RSO4d - Counter create body yields a counter objectId

**Test ID**: `objects/unit/RSO4d/counter-type-objectid-1`

**Spec requirement:** RSO4d — The RTO14 `type` is `counter` when `createBody.counterCreate` is provided.

### Setup
```pseudo
{ channel } = setup_rest_object("test-RSO4d-counter-" + random_id())
```

### Test Steps
```pseudo
result = AWAIT channel.object.generateObjectId(RestObjectGenerateIdBody(
  counterCreate: RestObjectCounterCreate(count: 5)
))
```

### Assertions
```pseudo
ASSERT result.objectId STARTS WITH "counter:"
```

---

## RSO4g, RSO4h - objectId derived per RTO14 from initialValue, nonce and server time

**Test ID**: `objects/unit/RSO4h/objectid-derivation-0`

| Spec | Requirement |
|------|-------------|
| RSO4g | Retrieves the current server time as described in RTO16 |
| RSO4h | Constructs the `objectId` per RTO14 from the `type`, `initialValue`, `nonce` and server time |
| RTO14 | `[type]:[base64url(SHA-256(utf8("[initialValue]:[nonce]")))]@[timestamp]` |

Tests that the returned `objectId` is consistent with the returned `initialValue` and `nonce`, and
that its timestamp is the server time. The client is newly created, so it has no persisted server
time offset (RTO16a) and must obtain server time from `/time`.

### Setup
```pseudo
{ channel, captured_requests } = setup_rest_object("test-RSO4h-" + random_id())
```

### Test Steps
```pseudo
result = AWAIT channel.object.generateObjectId(RestObjectGenerateIdBody(
  counterCreate: RestObjectCounterCreate(count: 42)
))
```

### Assertions
```pseudo
time_requests = captured_requests.filter(r => r.url.path == "/time")
ASSERT time_requests.length == 1
ASSERT time_requests[0].method == "GET"

expected_hash = base64url_encode(sha256(utf8_encode(result.initialValue + ":" + result.nonce)))
ASSERT result.objectId == "counter:" + expected_hash + "@" + str(SERVER_TIME)
```

---

## RSO4e2 - Counter initialValue is the JSON representation of the counter create body

**Test ID**: `objects/unit/RSO4e2/counter-initial-value-0`

**Spec requirement:** RSO4e2 — If `createBody.counterCreate` was provided, the `initialValue` is a JSON-string representation of the body, equivalent to RTO12f13.

### Setup
```pseudo
{ channel } = setup_rest_object("test-RSO4e2-" + random_id())
```

### Test Steps
```pseudo
result = AWAIT channel.object.generateObjectId(RestObjectGenerateIdBody(
  counterCreate: RestObjectCounterCreate(count: 42)
))
```

### Assertions
```pseudo
ASSERT parse_json(result.initialValue) == { "count": 42 }
```

---

## RSO4e1 - Map initialValue encodes semantics and entry data with JSON protocol rules

**Test ID**: `objects/unit/RSO4e1/map-initial-value-0`

| Spec | Requirement |
|------|-------------|
| RSO4e1a | `mapCreate.semantics` encoded per OMP2 |
| RSO4e1b | Each entry's `data` encoded per OD4d |
| RSO4e1c | The `initialValue` is a JSON-string representation of the resulting body, equivalent to RTO11f15 |

### Setup
```pseudo
{ channel } = setup_rest_object("test-RSO4e1-" + random_id())
```

### Test Steps
```pseudo
result = AWAIT channel.object.generateObjectId(RestObjectGenerateIdBody(
  mapCreate: RestObjectMapCreate(
    semantics: "LWW",
    entries: {
      "name":   RestObjectMapEntry(data: PublishObjectData(string: "Alice")),
      "age":    RestObjectMapEntry(data: PublishObjectData(number: 30)),
      "active": RestObjectMapEntry(data: PublishObjectData(boolean: true)),
      "avatar": RestObjectMapEntry(data: PublishObjectData(bytes: bytes([0x01, 0x02, 0x03]))),
      "prefs":  RestObjectMapEntry(data: PublishObjectData(json: { "theme": "dark" })),
      "visits": RestObjectMapEntry(data: PublishObjectData(objectId: "counter:h@1"))
    }
  )
))
```

### Assertions
```pseudo
initial_value = parse_json(result.initialValue)
ASSERT initial_value["semantics"] == 0

entries = initial_value["entries"]
ASSERT entries.keys() == {"name", "age", "active", "avatar", "prefs", "visits"}
ASSERT entries["name"] == { "data": { "string": "Alice" } }
ASSERT entries["age"] == { "data": { "number": 30 } }
ASSERT entries["active"] == { "data": { "boolean": true } }
ASSERT entries["avatar"] == { "data": { "bytes": "AQID" } }
ASSERT entries["prefs"]["data"]["encoding"] == "json"
ASSERT parse_json(entries["prefs"]["data"]["string"]) == { "theme": "dark" }
ASSERT entries["visits"] == { "data": { "objectId": "counter:h@1" } }
```

---

## RSO4e - initialValue uses JSON encoding regardless of the client protocol

**Test ID**: `objects/unit/RSO4e/json-regardless-of-protocol-0`

**Spec requirement:** RSO4e — The `initialValue` is always carried as a JSON string regardless of the negotiated transport format, so encoding must use the JSON protocol rules from OD4d.

Tests that a client using the binary protocol produces the same `initialValue` as a JSON-protocol
client, with `bytes` Base64-encoded.

### Setup
```pseudo
create_body = RestObjectGenerateIdBody(
  mapCreate: RestObjectMapCreate(
    semantics: "LWW",
    entries: {
      "avatar": RestObjectMapEntry(data: PublishObjectData(bytes: bytes([0x01, 0x02, 0x03])))
    }
  )
)

{ channel: json_channel } = setup_rest_object("test-RSO4e-json-" + random_id())
{ channel: binary_channel } = setup_rest_object("test-RSO4e-binary-" + random_id(),
  use_binary_protocol: true)
```

### Test Steps
```pseudo
json_result = AWAIT json_channel.object.generateObjectId(create_body)
binary_result = AWAIT binary_channel.object.generateObjectId(create_body)
```

### Assertions
```pseudo
ASSERT binary_result.initialValue IS String
ASSERT binary_result.initialValue == json_result.initialValue
ASSERT parse_json(binary_result.initialValue)["entries"]["avatar"]["data"]["bytes"] == "AQID"
```

---

## RSO4e1a - Unrecognized mapCreate semantics rejected

**Test ID**: `objects/unit/RSO4e1a/unrecognized-semantics-error-0`

**Spec requirement:** RSO4e1a — If the `mapCreate.semantics` value is unrecognized, the library should throw an `ErrorInfo` with `statusCode` 400 and `code` 40003.

Not applicable to SDKs whose `ObjectsMapSemantics` type makes an unrecognized value unrepresentable.

### Setup
```pseudo
{ channel } = setup_rest_object("test-RSO4e1a-" + random_id())
```

### Test Steps and Assertions
```pseudo
AWAIT channel.object.generateObjectId(RestObjectGenerateIdBody(
  mapCreate: RestObjectMapCreate(semantics: "not-a-semantics", entries: {})
)) FAILS WITH error

ASSERT error.code == 40003
ASSERT error.statusCode == 400
```

---

## RSO4c - Missing create body rejected

**Test ID**: `objects/unit/RSO4c/missing-create-body-error-0`

**Spec requirement:** RSO4c — If neither `createBody.mapCreate` nor `createBody.counterCreate` is provided, the library should throw an `ErrorInfo` with `statusCode` 400 and `code` 40003.

Not applicable to SDKs whose `RestObjectGenerateIdBody` representation makes an empty body
unrepresentable.

### Setup
```pseudo
{ channel, captured_requests } = setup_rest_object("test-RSO4c-" + random_id())
```

### Test Steps and Assertions
```pseudo
AWAIT channel.object.generateObjectId(RestObjectGenerateIdBody()) FAILS WITH error

ASSERT error.code == 40003
ASSERT error.statusCode == 400
ASSERT captured_requests.length == 0
```

---

## RSO4f - Nonce is a string of at least 16 characters

**Test ID**: `objects/unit/RSO4f/nonce-generated-0`

**Spec requirement:** RSO4f — Generates a unique string `nonce`, as described in RTO11f6 (16+ characters).

### Setup
```pseudo
{ channel } = setup_rest_object("test-RSO4f-" + random_id())
```

### Test Steps
```pseudo
result = AWAIT channel.object.generateObjectId(RestObjectGenerateIdBody(
  counterCreate: RestObjectCounterCreate(count: 0)
))
```

### Assertions
```pseudo
ASSERT result.nonce.length >= 16
```

---

## RSO4j - Repeated calls produce different objectId and nonce

**Test ID**: `objects/unit/RSO4j/unique-per-call-0`

**Spec requirement:** RSO4j — Two invocations with the same `createBody` produce different `objectId` and `nonce` values.

### Setup
```pseudo
{ channel } = setup_rest_object("test-RSO4j-" + random_id())
create_body = RestObjectGenerateIdBody(counterCreate: RestObjectCounterCreate(count: 1))
```

### Test Steps
```pseudo
first = AWAIT channel.object.generateObjectId(create_body)
second = AWAIT channel.object.generateObjectId(create_body)
```

### Assertions
```pseudo
ASSERT first.nonce != second.nonce
ASSERT first.objectId != second.objectId
```

---

## RSO4k - initialValue is deterministic for a given create body

**Test ID**: `objects/unit/RSO4k/initial-value-deterministic-0`

**Spec requirement:** RSO4k — The `initialValue` is deterministic for a given `createBody`: identical input produces identical output.

### Setup
```pseudo
{ channel } = setup_rest_object("test-RSO4k-" + random_id())
create_body = RestObjectGenerateIdBody(
  mapCreate: RestObjectMapCreate(
    semantics: "LWW",
    entries: {
      "a": RestObjectMapEntry(data: PublishObjectData(string: "x")),
      "b": RestObjectMapEntry(data: PublishObjectData(json: { "k": [1, 2] }))
    }
  )
)
```

### Test Steps
```pseudo
first = AWAIT channel.object.generateObjectId(create_body)
second = AWAIT channel.object.generateObjectId(create_body)
```

### Assertions
```pseudo
ASSERT first.initialValue == second.initialValue
```

---

## RSO4b, RSO5d, RSO5h - Generated values publish verbatim in *WithObjectId operations

**Test ID**: `objects/unit/RSO4b/generated-id-publish-roundtrip-0`

| Spec | Requirement |
|------|-------------|
| RSO4b | The returned values are intended to be supplied to a subsequent `mapCreateWithObjectId` or `counterCreateWithObjectId` operation |
| RSO5d | `mapCreateWithObjectId` carries `initialValue` and `nonce`, with `objectId` set to the generated ID |
| RSO5h | `counterCreateWithObjectId` has the same body and constraints as RSO5d |

Tests that values from `generateObjectId` are sent unchanged when used in a batch with an operation
that references the new object by ID.

### Setup
```pseudo
channel_name = "test-RSO4b-" + random_id()
{ channel, captured_requests } = setup_rest_object(channel_name)
```

### Test Steps
```pseudo
counter = AWAIT channel.object.generateObjectId(RestObjectGenerateIdBody(
  counterCreate: RestObjectCounterCreate(count: 3)
))
map = AWAIT channel.object.generateObjectId(RestObjectGenerateIdBody(
  mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {
    "visits": RestObjectMapEntry(data: PublishObjectData(objectId: counter.objectId))
  })
))

AWAIT channel.object.publish([
  RestObjectOperation(
    objectId: counter.objectId,
    counterCreateWithObjectId: RestObjectCreateWithObjectId(
      initialValue: counter.initialValue, nonce: counter.nonce)
  ),
  RestObjectOperation(
    objectId: map.objectId,
    mapCreateWithObjectId: RestObjectCreateWithObjectId(
      initialValue: map.initialValue, nonce: map.nonce)
  ),
  RestObjectOperation(
    objectId: "root",
    mapSet: RestObjectMapSet(key: "stats", value: PublishObjectData(objectId: map.objectId))
  )
])
```

### Assertions
```pseudo
publish_requests = captured_requests.filter(r => r.method == "POST")
ASSERT publish_requests.length == 1
ASSERT publish_requests[0].url.path == "/channels/" + encode_uri_component(channel_name) + "/object"

body = parse_json(publish_requests[0].body)
ASSERT body[0] == {
  "objectId": counter.objectId,
  "counterCreateWithObjectId": { "initialValue": counter.initialValue, "nonce": counter.nonce }
}
ASSERT body[1] == {
  "objectId": map.objectId,
  "mapCreateWithObjectId": { "initialValue": map.initialValue, "nonce": map.nonce }
}
ASSERT body[2]["mapSet"]["value"] == { "objectId": map.objectId }
```
