# RestObject Publish Tests

Spec points: `RSO3`, `RSO3a1`, `RSO3b`, `RSO3c`, `RSO3d`, `RSO3d1`, `RSO3d2`, `RSO3d3`, `RSO3d4`, `RSO3e`, `RSO3f`, `RSO3g`, `RSO3h`, `RSO5`, `RSO5a`, `RSO5b`, `RSO5b1`, `RSO5c`, `RSO5d`, `RSO5e`, `RSO5f`, `RSO5g`, `RSO5h`, `RSO5i`, `RSO6`, `RSO7`, `RSO10`, `RSO13`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

## Purpose

Tests `RestObject#publish` request formation: endpoint, batching, the wire shape of each
`RestObjectOperation` variant, `ObjectData` encoding of leaf values, the absence of client-side
validation that is delegated to the server, and decoding of the `RestObjectPublishResult`.

## Common Setup

`objects_plugin` denotes the SDK's `Objects` plugin ([PC5](../../../specifications/features.md#PC5)),
supplied under the `Objects` `PluginType` key.

Unless a test states otherwise, clients use the JSON protocol (`useBinaryProtocol: false`) so the
request body can be inspected with `parse_json`.

`mapCreate.semantics` is written as the symbolic enum value `"LWW"` in operations the test constructs
(see *Enum values* in the UTS README), and is asserted on the wire as its `ObjectsMapSemantics`
integer encoding (`0`, per OMP2).

```pseudo
DEFAULT_PUBLISH_RESPONSE = {
  "messageId": "msg-id-1",
  "channel": "ignored-by-tests",
  "objectIds": []
}

setup_rest_object(channel_name, use_binary_protocol: false, client_options: {}):
  captured_requests = []

  mock_http = MockHttpClient(
    onConnectionAttempt: (conn) => conn.respond_with_success(),
    onRequest: (req) => {
      captured_requests.append(req)
      IF use_binary_protocol:
        req.respond_with(201, msgpack_encode(DEFAULT_PUBLISH_RESPONSE),
          headers: { "Content-Type": "application/x-msgpack" })
      ELSE:
        req.respond_with(201, DEFAULT_PUBLISH_RESPONSE,
          headers: { "Content-Type": "application/json" })
    }
  )
  install_mock(mock_http)

  client = Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    useBinaryProtocol: use_binary_protocol,
    plugins: { Objects: objects_plugin },
    ...client_options
  ))
  channel = client.channels.get(channel_name)

  RETURN { client, channel, captured_requests }
```

---

## RSO3e - Single operation sent as POST with a one-element JSON array body

**Test ID**: `objects/unit/RSO3e/single-op-post-0`

| Spec | Requirement |
|------|-------------|
| RSO3a1 | `op` is a single `RestObjectOperation` or an array of them |
| RSO3e | Sends a `POST` to `/channels/{channelName}/object` with the encoded operations as an array body, encoded per RSC8 |

Tests that a single (non-array) operation is sent as a POST whose body is an array containing that one operation.

### Setup
```pseudo
channel_name = "test-RSO3e-single-" + random_id()
{ channel, captured_requests } = setup_rest_object(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.object.publish(RestObjectOperation(
  objectId: "root",
  mapSet: RestObjectMapSet(key: "greeting", value: PublishObjectData(string: "hello"))
))
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name) + "/object"
ASSERT request.headers["Content-Type"] == "application/json"

body = parse_json(request.body)
ASSERT body IS List
ASSERT body.length == 1
ASSERT body[0]["objectId"] == "root"
ASSERT body[0]["mapSet"] == { "key": "greeting", "value": { "string": "hello" } }
```

---

## RSO3e - Request body encoded as MessagePack with the binary protocol

**Test ID**: `objects/unit/RSO3e/msgpack-body-1`

**Spec requirement:** RSO3e — The request body is encoded per RSC8: MessagePack when the binary protocol is in use.

### Setup
```pseudo
channel_name = "test-RSO3e-msgpack-" + random_id()
{ channel, captured_requests } = setup_rest_object(channel_name, use_binary_protocol: true)
```

### Test Steps
```pseudo
AWAIT channel.object.publish(RestObjectOperation(
  path: "visits",
  counterInc: RestObjectCounterInc(number: 1)
))
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.headers["Content-Type"] == "application/x-msgpack"

body = msgpack_decode(request.body)
ASSERT body IS List
ASSERT body.length == 1
ASSERT body[0]["path"] == "visits"
ASSERT body[0]["counterInc"] == { "number": 1 }
```

---

## RSO3c - Array of operations sent in a single request, in order

**Test ID**: `objects/unit/RSO3c/batch-single-request-0`

**Spec requirement:** RSO3c — When `op` is an array, all operations must be sent in a single server request.

### Setup
```pseudo
channel_name = "test-RSO3c-" + random_id()
{ channel, captured_requests } = setup_rest_object(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.object.publish([
  RestObjectOperation(path: "a", mapSet: RestObjectMapSet(key: "x", value: PublishObjectData(number: 1))),
  RestObjectOperation(objectId: "root", mapRemove: RestObjectMapRemove(key: "old")),
  RestObjectOperation(path: "score", counterInc: RestObjectCounterInc(number: -2))
])
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

body = parse_json(captured_requests[0].body)
ASSERT body.length == 3
ASSERT body[0]["mapSet"]["key"] == "x"
ASSERT body[1]["mapRemove"] == { "key": "old" }
ASSERT body[2]["counterInc"] == { "number": -2 }
```

---

## RSO3h - No client-side limit on batch size

**Test ID**: `objects/unit/RSO3h/no-batch-size-limit-0`

**Spec requirement:** RSO3h — The library must not enforce a client-side limit on the number of operations in a batch.

### Setup
```pseudo
channel_name = "test-RSO3h-" + random_id()
{ channel, captured_requests } = setup_rest_object(channel_name)

ops = []
FOR i IN 0..999:
  ops.append(RestObjectOperation(
    objectId: "root",
    mapSet: RestObjectMapSet(key: "k" + str(i), value: PublishObjectData(number: i))
  ))
```

### Test Steps
```pseudo
AWAIT channel.object.publish(ops)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
body = parse_json(captured_requests[0].body)
ASSERT body.length == 1000
ASSERT body[999]["mapSet"]["key"] == "k999"
```

---

## RSO3b, RSO10 - Publish result decoded from the response

**Test ID**: `objects/unit/RSO10/publish-result-0`

| Spec | Requirement |
|------|-------------|
| RSO3b | The return type is a `RestObjectPublishResult` |
| RSO10 | `RestObjectPublishResult` has `messageId`, `channel` and `objectIds` |

### Setup
```pseudo
channel_name = "test-RSO10-" + random_id()

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(201, {
    "messageId": "abc123:0",
    "channel": channel_name,
    "objectIds": ["map:newHash@1700000000000", "root"]
  })
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false,
  plugins: { Objects: objects_plugin }
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
result = AWAIT channel.object.publish(RestObjectOperation(
  path: "profile",
  mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {})
))
```

### Assertions
```pseudo
ASSERT result.messageId == "abc123:0"
ASSERT result.channel == channel_name
ASSERT result.objectIds == ["map:newHash@1700000000000", "root"]
```

---

## RSO3d4, RSO5c-RSO5i - Wire shape of each operation type, without an action field

**Test ID**: `objects/unit/RSO3d4/op-wire-shape-no-action-0`

| Spec | Requirement |
|------|-------------|
| RSO3d4 | The wire payload must not include an explicit `action` field; the action is inferred from the operation-specific field |
| RSO5c | `mapCreate` body: `semantics`, `entries` |
| RSO5d | `mapCreateWithObjectId` body: `initialValue`, `nonce` (with `objectId` set) |
| RSO5e | `mapSet` body: `key`, `value` |
| RSO5f | `mapRemove` body: `key` |
| RSO5g | `counterCreate` body: `count` |
| RSO5h | `counterCreateWithObjectId` body: `initialValue`, `nonce` (with `objectId` set) |
| RSO5i | `counterInc` body: `number` |

Tests that each `RestObjectOperation` variant is encoded under its operation-specific field name with
the expected body, and that no `action` field is present.

### Setup
```pseudo
channel_name = "test-RSO3d4-" + random_id()
```

### Test Cases

| ID | Operation | Expected wire object |
|----|-----------|----------------------|
| 1 | `RestObjectOperation(path: "m", mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {}))` | `{ "path": "m", "mapCreate": { "semantics": 0, "entries": {} } }` |
| 2 | `RestObjectOperation(objectId: "map:h@1", mapCreateWithObjectId: RestObjectCreateWithObjectId(initialValue: "{\"semantics\":0,\"entries\":{}}", nonce: "nonce-0123456789ab"))` | `{ "objectId": "map:h@1", "mapCreateWithObjectId": { "initialValue": "{\"semantics\":0,\"entries\":{}}", "nonce": "nonce-0123456789ab" } }` |
| 3 | `RestObjectOperation(objectId: "root", mapSet: RestObjectMapSet(key: "k", value: PublishObjectData(boolean: true)))` | `{ "objectId": "root", "mapSet": { "key": "k", "value": { "boolean": true } } }` |
| 4 | `RestObjectOperation(path: "a.b", mapRemove: RestObjectMapRemove(key: "k"))` | `{ "path": "a.b", "mapRemove": { "key": "k" } }` |
| 5 | `RestObjectOperation(counterCreate: RestObjectCounterCreate(count: 10))` | `{ "counterCreate": { "count": 10 } }` |
| 6 | `RestObjectOperation(objectId: "counter:h@1", counterCreateWithObjectId: RestObjectCreateWithObjectId(initialValue: "{\"count\":10}", nonce: "nonce-0123456789ab"))` | `{ "objectId": "counter:h@1", "counterCreateWithObjectId": { "initialValue": "{\"count\":10}", "nonce": "nonce-0123456789ab" } }` |
| 7 | `RestObjectOperation(objectId: "counter:h@1", counterInc: RestObjectCounterInc(number: -5))` | `{ "objectId": "counter:h@1", "counterInc": { "number": -5 } }` |

### Test Steps and Assertions
```pseudo
FOR EACH test_case IN test_cases:
  { channel, captured_requests } = setup_rest_object(channel_name)

  AWAIT channel.object.publish(test_case.operation)

  wire_op = parse_json(captured_requests[0].body)[0]
  ASSERT wire_op == test_case.expected_wire_object
  ASSERT "action" NOT IN wire_op
```

---

## RSO3d3 - id, objectId and path preserved verbatim

**Test ID**: `objects/unit/RSO3d3/targeting-fields-verbatim-0`

**Spec requirement:** RSO3d3 — The `id`, `objectId`, and `path` fields of the operation, if provided by the caller, must be preserved verbatim in the wire payload.

### Setup
```pseudo
channel_name = "test-RSO3d3-" + random_id()
{ channel, captured_requests } = setup_rest_object(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.object.publish([
  RestObjectOperation(
    id: "my-op-id:0",
    objectId: "map:Ab-_9@1700000000000",
    mapRemove: RestObjectMapRemove(key: "k")
  ),
  RestObjectOperation(
    id: "  spaced id ",
    path: "a\\.b.*.c",
    counterInc: RestObjectCounterInc(number: 1)
  )
])
```

### Assertions
```pseudo
body = parse_json(captured_requests[0].body)

ASSERT body[0]["id"] == "my-op-id:0"
ASSERT body[0]["objectId"] == "map:Ab-_9@1700000000000"
ASSERT "path" NOT IN body[0]

ASSERT body[1]["id"] == "  spaced id "
ASSERT body[1]["path"] == "a\\.b.*.c"
ASSERT "objectId" NOT IN body[1]
```

---

## RSO6 - publish passes path to the server verbatim

**Test ID**: `objects/unit/RSO6/publish-path-verbatim-0`

**Spec requirement:** RSO6 — The library must pass caller-supplied `path` strings in `RestObjectOperation` to the server without modification or normalization.

### Setup
```pseudo
channel_name = "test-RSO6-publish-" + random_id()
```

### Test Cases

| ID | path |
|----|------|
| 1 | `"items.*"` |
| 2 | `"a\\.b.c"` |
| 3 | `".a..b."` |
| 4 | `""` |
| 5 | `"ünïcödé.键"` |

### Test Steps and Assertions
```pseudo
FOR EACH test_case IN test_cases:
  { channel, captured_requests } = setup_rest_object(channel_name)

  AWAIT channel.object.publish(RestObjectOperation(
    path: test_case.path,
    mapSet: RestObjectMapSet(key: "k", value: PublishObjectData(string: "v"))
  ))

  ASSERT captured_requests.length == 1
  ASSERT parse_json(captured_requests[0].body)[0]["path"] == test_case.path
```

---

## RSO3d1 - mapCreate semantics encoded per OMP2

**Test ID**: `objects/unit/RSO3d1/mapcreate-semantics-encoded-0`

**Spec requirement:** RSO3d1 — If the operation includes a `mapCreate.semantics` field, the library must encode the semantics value per OMP2 (`LWW` = `0`).

### Setup
```pseudo
channel_name = "test-RSO3d1-" + random_id()
{ channel, captured_requests } = setup_rest_object(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.object.publish(RestObjectOperation(
  mapCreate: RestObjectMapCreate(semantics: "LWW", entries: {})
))
```

### Assertions
```pseudo
ASSERT parse_json(captured_requests[0].body)[0]["mapCreate"]["semantics"] == 0
```

---

## RSO3d1 - Unrecognized mapCreate semantics rejected

**Test ID**: `objects/unit/RSO3d1/unrecognized-semantics-error-1`

**Spec requirement:** RSO3d1 — If the `mapCreate.semantics` value is unrecognized, the library should throw an `ErrorInfo` with `statusCode` 400 and `code` 40003.

Not applicable to SDKs whose `ObjectsMapSemantics` type makes an unrecognized value unrepresentable
(see *Language-inapplicable inputs* in the UTS README).

### Setup
```pseudo
channel_name = "test-RSO3d1-invalid-" + random_id()
{ channel, captured_requests } = setup_rest_object(channel_name)
```

### Test Steps and Assertions
```pseudo
AWAIT channel.object.publish(RestObjectOperation(
  mapCreate: RestObjectMapCreate(semantics: "not-a-semantics", entries: {})
)) FAILS WITH error

ASSERT error.code == 40003
ASSERT error.statusCode == 400
ASSERT captured_requests.length == 0
```

---

## RSO3d2, RSO7 - mapSet value encoded per OD4 (JSON protocol)

**Test ID**: `objects/unit/RSO3d2/mapset-value-encoded-json-0`

| Spec | Requirement |
|------|-------------|
| RSO3d2 | `ObjectData` values reachable from the operation, including `mapSet.value`, must be encoded per OD4 |
| RSO7 | `PublishObjectData` has exactly one of `string`, `number`, `boolean`, `bytes`, `json`, `objectId` |
| OD4d | JSON protocol: `bytes` Base64-encoded; JSON object/array stringified into `string` with `encoding: "json"` |

### Setup
```pseudo
channel_name = "test-RSO3d2-json-" + random_id()
```

### Test Cases

| ID | value | Expected wire `value` |
|----|-------|-----------------------|
| 1 | `PublishObjectData(string: "hello")` | `{ "string": "hello" }` |
| 2 | `PublishObjectData(number: 1.5)` | `{ "number": 1.5 }` |
| 3 | `PublishObjectData(boolean: false)` | `{ "boolean": false }` |
| 4 | `PublishObjectData(bytes: bytes([0x01, 0x02, 0x03]))` | `{ "bytes": "AQID" }` |
| 5 | `PublishObjectData(json: { "a": [1, 2] })` | `{ "string": "{\"a\":[1,2]}", "encoding": "json" }` |
| 6 | `PublishObjectData(json: [1, "x"])` | `{ "string": "[1,\"x\"]", "encoding": "json" }` |
| 7 | `PublishObjectData(objectId: "counter:h@1")` | `{ "objectId": "counter:h@1" }` |

For JSON-encoded payloads (cases 5–6), compare `parse_json(value["string"])` against the input rather
than the exact string, since key order and whitespace of the stringified JSON are not specified.

### Test Steps and Assertions
```pseudo
FOR EACH test_case IN test_cases:
  { channel, captured_requests } = setup_rest_object(channel_name)

  AWAIT channel.object.publish(RestObjectOperation(
    objectId: "root",
    mapSet: RestObjectMapSet(key: "k", value: test_case.value)
  ))

  wire_value = parse_json(captured_requests[0].body)[0]["mapSet"]["value"]
  IF test_case.value.json IS NOT null:
    ASSERT wire_value["encoding"] == "json"
    ASSERT wire_value["string"] IS String
    ASSERT parse_json(wire_value["string"]) == test_case.value.json
    ASSERT wire_value.keys() == {"string", "encoding"}
  ELSE:
    ASSERT wire_value == test_case.expected_wire_value
```

---

## RSO3d2 - mapSet value encoded per OD4 (MessagePack protocol)

**Test ID**: `objects/unit/RSO3d2/mapset-value-encoded-msgpack-1`

**Spec requirement:** RSO3d2 — `ObjectData` values are encoded per OD4. With MessagePack (OD4c), `bytes` is sent as MessagePack binary and JSON payloads are stringified into `string` with `encoding: "json"`.

### Setup
```pseudo
channel_name = "test-RSO3d2-msgpack-" + random_id()
{ channel, captured_requests } = setup_rest_object(channel_name, use_binary_protocol: true)
```

### Test Steps
```pseudo
AWAIT channel.object.publish([
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "bin", value: PublishObjectData(bytes: bytes([0x01, 0x02, 0x03])))),
  RestObjectOperation(objectId: "root",
    mapSet: RestObjectMapSet(key: "obj", value: PublishObjectData(json: { "a": 1 })))
])
```

### Assertions
```pseudo
body = msgpack_decode(captured_requests[0].body)

ASSERT body[0]["mapSet"]["value"]["bytes"] IS Binary
ASSERT body[0]["mapSet"]["value"]["bytes"] == bytes([0x01, 0x02, 0x03])

ASSERT body[1]["mapSet"]["value"]["encoding"] == "json"
ASSERT parse_json(body[1]["mapSet"]["value"]["string"]) == { "a": 1 }
```

---

## RSO3d2, RSO13 - mapCreate entries encoded per OD4

**Test ID**: `objects/unit/RSO3d2/mapcreate-entries-encoded-2`

| Spec | Requirement |
|------|-------------|
| RSO3d2 | The `data` field of each entry in `mapCreate.entries` must be encoded per OD4 |
| RSO13 | `RestObjectMapEntry` has a `data` `PublishObjectData` |

### Setup
```pseudo
channel_name = "test-RSO3d2-entries-" + random_id()
{ channel, captured_requests } = setup_rest_object(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.object.publish(RestObjectOperation(
  path: "profile",
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
entries = parse_json(captured_requests[0].body)[0]["mapCreate"]["entries"]

ASSERT entries["name"] == { "data": { "string": "Alice" } }
ASSERT entries["age"] == { "data": { "number": 30 } }
ASSERT entries["active"] == { "data": { "boolean": true } }
ASSERT entries["avatar"] == { "data": { "bytes": "AQID" } }
ASSERT entries["prefs"]["data"]["encoding"] == "json"
ASSERT parse_json(entries["prefs"]["data"]["string"]) == { "theme": "dark" }
ASSERT entries["visits"] == { "data": { "objectId": "counter:h@1" } }
```

---

## RSO3f - No auto-generated operation id, even with idempotentRestPublishing

**Test ID**: `objects/unit/RSO3f/no-auto-generated-id-0`

**Spec requirement:** RSO3f — The library must not auto-generate `RestObjectOperation.id` values. The `idempotentRestPublishing` option does not apply to `RestObject#publish`.

Tests that, with `idempotentRestPublishing: true`, operations without an `id` are sent without one, and
operations with an `id` keep it unchanged.

### Setup
```pseudo
channel_name = "test-RSO3f-" + random_id()
{ channel, captured_requests } = setup_rest_object(channel_name,
  client_options: { idempotentRestPublishing: true })
```

### Test Steps
```pseudo
AWAIT channel.object.publish([
  RestObjectOperation(path: "a", counterInc: RestObjectCounterInc(number: 1)),
  RestObjectOperation(id: "caller-id", path: "b", counterInc: RestObjectCounterInc(number: 1))
])
```

### Assertions
```pseudo
body = parse_json(captured_requests[0].body)
ASSERT "id" NOT IN body[0]
ASSERT body[1]["id"] == "caller-id"
```

---

## RSO5b1 - Operation with no body field rejected before any request

**Test ID**: `objects/unit/RSO5b1/no-body-field-error-0`

**Spec requirement:** RSO5b1 — If a `RestObjectOperation` has zero of the operation-specific body fields set, the library should throw an `ErrorInfo` with `statusCode` 400 and `code` 40003 before sending any HTTP request.

Not applicable to SDKs whose `RestObjectOperation` representation makes an operation with no body
unrepresentable.

### Setup
```pseudo
channel_name = "test-RSO5b1-none-" + random_id()
{ channel, captured_requests } = setup_rest_object(channel_name)
```

### Test Steps and Assertions
```pseudo
AWAIT channel.object.publish(RestObjectOperation(objectId: "root")) FAILS WITH error

ASSERT error.code == 40003
ASSERT error.statusCode == 400
ASSERT captured_requests.length == 0
```

---

## RSO5b1 - Operation with multiple body fields rejected; no partial batch sent

**Test ID**: `objects/unit/RSO5b1/multiple-body-fields-error-1`

**Spec requirement:** RSO5b1 — If a `RestObjectOperation` has more than one of the operation-specific body fields set, the library should throw an `ErrorInfo` with `statusCode` 400 and `code` 40003 before sending any HTTP request.

Tests that one invalid operation in a batch causes the whole publish to fail without any request being
sent. Not applicable to SDKs whose `RestObjectOperation` representation makes an operation with more
than one body unrepresentable.

### Setup
```pseudo
channel_name = "test-RSO5b1-multi-" + random_id()
{ channel, captured_requests } = setup_rest_object(channel_name)
```

### Test Steps and Assertions
```pseudo
AWAIT channel.object.publish([
  RestObjectOperation(path: "ok", counterInc: RestObjectCounterInc(number: 1)),
  RestObjectOperation(
    objectId: "root",
    mapSet: RestObjectMapSet(key: "k", value: PublishObjectData(string: "v")),
    mapRemove: RestObjectMapRemove(key: "k")
  )
]) FAILS WITH error

ASSERT error.code == 40003
ASSERT error.statusCode == 400
ASSERT captured_requests.length == 0
```

---

## RSO3g - No client-side validation of targeting; server error surfaced

**Test ID**: `objects/unit/RSO3g/no-targeting-validation-0`

**Spec requirement:** RSO3g — The library must not perform client-side validation of operation targeting (combinations of `objectId` and `path`); any server-returned error must be surfaced to the caller as a rejected `ErrorInfo`.

Tests that operations with targeting combinations the operation's constraints disallow (RSO5c3, RSO5e3)
are still sent to the server, and the server's error response is surfaced.

### Setup
```pseudo
channel_name = "test-RSO3g-" + random_id()
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(400, {
      "error": { "code": 40000, "statusCode": 400, "message": "Invalid operation targeting" }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false,
  plugins: { Objects: objects_plugin }
))
channel = client.channels.get(channel_name)
```

### Test Cases

| ID | Operation |
|----|-----------|
| 1 | `RestObjectOperation(objectId: "root", path: "a", mapSet: RestObjectMapSet(key: "k", value: PublishObjectData(string: "v")))` |
| 2 | `RestObjectOperation(mapRemove: RestObjectMapRemove(key: "k"))` |
| 3 | `RestObjectOperation(objectId: "counter:h@1", counterCreate: RestObjectCounterCreate(count: 1))` |

### Test Steps and Assertions
```pseudo
FOR EACH test_case IN test_cases:
  captured_requests.clear()

  AWAIT channel.object.publish(test_case.operation) FAILS WITH error

  ASSERT captured_requests.length == 1
  ASSERT error.code == 40000
  ASSERT error.statusCode == 400
```
