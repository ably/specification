# RestObject Attribute and Get Tests

Spec points: `RSL16`, `RSL16b`, `RSO1`, `RSO1a`, `RSO2`, `RSO2a1`, `RSO2b`, `RSO2c`, `RSO2d`, `RSO2e`, `RSO2f`, `RSO2g`, `RSO2g1`, `RSO2g2`, `RSO2g3`, `RSO2g4`, `RSO2h`, `RSO6`, `RSO8`, `RSO9`, `RSO9a`, `RSO9b`, `RSO9c`, `RSO9c1`, `RSO9c2`, `RSO9d`, `RSO14`, `RSO15`, `RSO16`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

## Purpose

Tests the REST entry point to LiveObjects: the `RestChannel#object` attribute, and
`RestObject#get` request formation and response decoding in both compact and full
modes. Server behaviour (path resolution, compact formatting) is out of scope; these
tests verify only what the SDK sends and how it decodes what it receives.

## Common Setup

`objects_plugin` denotes the SDK's `Objects` plugin ([PC5](../../../specifications/features.md#PC5)),
supplied under the `Objects` `PluginType` key. How the plugin value is obtained is SDK-specific.

Unless a test states otherwise, clients use the JSON protocol (`useBinaryProtocol: false`) so
request and response bodies can be inspected as JSON.

```pseudo
setup_rest_object(channel_name, response_body, use_binary_protocol: false):
  captured_requests = []

  mock_http = MockHttpClient(
    onConnectionAttempt: (conn) => conn.respond_with_success(),
    onRequest: (req) => {
      captured_requests.append(req)
      IF use_binary_protocol:
        req.respond_with(200, msgpack_encode(response_body),
          headers: { "Content-Type": "application/x-msgpack" })
      ELSE:
        req.respond_with(200, response_body,
          headers: { "Content-Type": "application/json" })
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

## RSO1a - One RestObject instance per RestChannel

**Test ID**: `objects/unit/RSO1a/one-instance-per-channel-0`

**Spec requirement:** RSO1a — There is one `RestObject` instance per `RestChannel`, accessed via the `RestChannel#object` attribute.

Tests that repeated access returns the same instance, and that different channels have different instances.

### Setup
```pseudo
{ client, channel } = setup_rest_object("test-RSO1a-a-" + random_id(), {})
other_channel = client.channels.get("test-RSO1a-b-" + random_id())
```

### Assertions
```pseudo
ASSERT channel.object IS SAME AS channel.object
ASSERT channel.object IS NOT SAME AS other_channel.object
```

---

## RSL16b - Accessing channel.object without the Objects plugin

**Test ID**: `objects/unit/RSL16b/missing-plugin-error-0`

**Spec requirement:** RSL16b — It is a programmer error to access `RestChannel#object` without first providing the `Objects` plugin in the client options. If this is handled by throwing, the error must be an `ErrorInfo` with `statusCode` 400 and `code` 40019.

Tests that accessing `channel.object` on a client without the `Objects` plugin fails with 40019.

This test applies only to SDKs that handle the programmer error by throwing. SDKs that make it
impossible to express (for example, by only exposing `object` on a channel type that exists when the
plugin is installed) should note the test as not applicable.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, {})
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-RSL16b-" + random_id())
```

### Test Steps and Assertions
```pseudo
channel.object FAILS WITH error
ASSERT error.code == 40019
ASSERT error.statusCode == 400
```

---

## RSO2c - get with no params sends GET to channel object endpoint

**Test ID**: `objects/unit/RSO2c/get-default-endpoint-0`

| Spec | Requirement |
|------|-------------|
| RSO2c | Sends a `GET` request to `/channels/{channelName}/object`; `/{objectId}` is appended only if `params.objectId` is provided |
| RSO2d | `params.path` and `params.compact` are sent as query parameters only if provided |

Tests that `get()` without params targets the channel object endpoint and sends no `path` or `compact` query parameters.

### Setup
```pseudo
channel_name = "test-RSO2c-default-" + random_id()
{ channel, captured_requests } = setup_rest_object(channel_name, {})
```

### Test Steps
```pseudo
AWAIT channel.object.get()
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.method == "GET"
ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name) + "/object"
ASSERT "path" NOT IN request.url.query_params
ASSERT "compact" NOT IN request.url.query_params
```

---

## RSO2c - get with objectId appends percent-encoded path segment

**Test ID**: `objects/unit/RSO2c/get-objectid-path-segment-0`

**Spec requirement:** RSO2c — When `params.objectId` is provided, `/{objectId}` is appended to `/channels/{channelName}/object`. The `objectId` path segment must be percent-encoded per RFC 3986 §2.1.

Tests that the `objectId` is appended as a single percent-encoded path segment, including when it
contains characters that are not valid in a path segment.

### Setup
```pseudo
channel_name = "test-RSO2c-objectid-" + random_id()
```

### Test Cases

| ID | objectId |
|----|----------|
| 1 | `"root"` |
| 2 | `"map:QWsI5HQnz7AbhLgn9U2xlA2wq0Ax7HHYbJtJDF9mVqg@1700000000000"` |
| 3 | `"counter:a/b c?d#e@1700000000000"` |

### Test Steps and Assertions
```pseudo
FOR EACH test_case IN test_cases:
  { channel, captured_requests } = setup_rest_object(channel_name, {})

  AWAIT channel.object.get(RestObjectGetParams(objectId: test_case.objectId))

  ASSERT captured_requests.length == 1
  request = captured_requests[0]
  ASSERT request.method == "GET"
  ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name)
    + "/object/" + encode_uri_component(test_case.objectId)
```

---

## RSO2d - path and compact sent as query parameters

**Test ID**: `objects/unit/RSO2d/path-compact-query-params-0`

**Spec requirement:** RSO2d — The `params.path` and `params.compact` fields, if provided, must be sent as URL query string parameters.

Tests that `path` and `compact` are sent as query parameters, alone and combined with `objectId`.

### Setup
```pseudo
channel_name = "test-RSO2d-" + random_id()
```

### Test Cases

| ID | params | Expected path suffix | Expected query params |
|----|--------|----------------------|-----------------------|
| 1 | `{ path: "a.b.c" }` | `"/object"` | `{ "path": "a.b.c" }` |
| 2 | `{ compact: false }` | `"/object"` | `{ "compact": "false" }` |
| 3 | `{ compact: true }` | `"/object"` | `{ "compact": "true" }` |
| 4 | `{ objectId: "map:abc@1", path: "x.y", compact: false }` | `"/object/" + encode_uri_component("map:abc@1")` | `{ "path": "x.y", "compact": "false" }` |

### Test Steps and Assertions
```pseudo
FOR EACH test_case IN test_cases:
  { channel, captured_requests } = setup_rest_object(channel_name, {})

  AWAIT channel.object.get(RestObjectGetParams(test_case.params))

  request = captured_requests[0]
  ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name)
    + test_case.expected_path_suffix
  ASSERT request.url.query_params == test_case.expected_query_params
```

---

## RSO6 - get passes path to the server verbatim

**Test ID**: `objects/unit/RSO6/get-path-verbatim-0`

| Spec | Requirement |
|------|-------------|
| RSO6 | Caller-supplied `path` strings must be passed to the server without modification or normalization |
| RSO2h | The library must not perform client-side validation of `params.path` content |

Tests that path strings the SDK might be tempted to parse, normalize or reject are sent unchanged.

### Setup
```pseudo
channel_name = "test-RSO6-get-" + random_id()
```

### Test Cases

| ID | path |
|----|------|
| 1 | `"items.*.count"` |
| 2 | `"a\\.b.c"` |
| 3 | `".a..b."` |
| 4 | `""` |
| 5 | `"with space/and?query&chars=1#frag"` |
| 6 | `"ünïcödé.键"` |

### Test Steps and Assertions
```pseudo
FOR EACH test_case IN test_cases:
  { channel, captured_requests } = setup_rest_object(channel_name, {})

  AWAIT channel.object.get(RestObjectGetParams(path: test_case.path))

  ASSERT captured_requests.length == 1
  # query_params holds URL-decoded values: the decoded value must equal the input exactly
  ASSERT captured_requests[0].url.query_params["path"] == test_case.path
```

---

## RSO2f, RSO8 - Compact response returned verbatim

**Test ID**: `objects/unit/RSO2f/compact-returned-verbatim-0`

| Spec | Requirement |
|------|-------------|
| RSO2f | When `params.compact` is `true` or omitted, the decoded response body must be returned verbatim, with no further structural transformation or decoding |
| RSO8 | `RestObjectGetCompactResult` shape and value formats are server-defined and not transformed by the library |

Tests that a compact response is returned exactly as decoded from the wire — in particular that
string values that look like Base64 or JSON are not decoded, and that object-reference shapes are
not resolved.

### Setup
```pseudo
compact_body = {
  "name": "Alice",
  "age": 30,
  "active": true,
  "visits": 7,
  "avatar": "AQID",
  "prefs": "{\"theme\":\"dark\"}",
  "tags": "[\"a\",\"b\"]",
  "nested": { "inner": { "deep": 1 } },
  "empty": {},
  "cycle": { "objectId": "map:cycleHash@1700000000000" }
}

{ channel } = setup_rest_object("test-RSO2f-" + random_id(), compact_body)
```

### Test Steps
```pseudo
result_default = AWAIT channel.object.get()
result_explicit = AWAIT channel.object.get(RestObjectGetParams(compact: true))
```

### Assertions
```pseudo
ASSERT result_default == compact_body
ASSERT result_explicit == compact_body

# String values are not Base64- or JSON-decoded
ASSERT result_default["avatar"] == "AQID"
ASSERT result_default["avatar"] IS String
ASSERT result_default["prefs"] == "{\"theme\":\"dark\"}"
ASSERT result_default["prefs"] IS String
```

---

## RSO2f - Compact scalar response returned verbatim

**Test ID**: `objects/unit/RSO2f/compact-scalar-verbatim-1`

**Spec requirement:** RSO2f — When `params.compact` is `true` or omitted, the decoded response body must be returned to the caller verbatim.

Tests that a compact response that is not a map (for example a counter value, or a leaf value
reached via `path`) is returned as-is.

### Test Cases

| ID | Response body |
|----|---------------|
| 1 | `42` |
| 2 | `-1.5` |
| 3 | `"hello"` |
| 4 | `false` |

### Test Steps and Assertions
```pseudo
FOR EACH test_case IN test_cases:
  { channel } = setup_rest_object("test-RSO2f-scalar-" + random_id(), test_case.response_body)

  result = AWAIT channel.object.get(RestObjectGetParams(path: "some.key"))

  ASSERT result == test_case.response_body
```

---

## RSO2e, RSO2f - Compact msgpack response decoded per RSC8 and returned verbatim

**Test ID**: `objects/unit/RSO2e/compact-msgpack-decoded-0`

| Spec | Requirement |
|------|-------------|
| RSO2e | The response body must be decoded per RSC8 |
| RSO2f | The decoded compact body is returned verbatim |

Tests that with the binary protocol the request advertises MessagePack, the MessagePack response
is decoded, and binary values in a compact response are returned as binary without further transformation.

### Setup
```pseudo
compact_body = {
  "name": "Alice",
  "count": 5,
  "avatar": bytes([0x01, 0x02, 0x03])
}

{ channel, captured_requests } = setup_rest_object(
  "test-RSO2e-msgpack-" + random_id(), compact_body, use_binary_protocol: true)
```

### Test Steps
```pseudo
result = AWAIT channel.object.get()
```

### Assertions
```pseudo
ASSERT captured_requests[0].headers["Accept"] == "application/x-msgpack"

ASSERT result["name"] == "Alice"
ASSERT result["count"] == 5
ASSERT result["avatar"] IS Binary
ASSERT result["avatar"] == bytes([0x01, 0x02, 0x03])
```

---

## RSO2g1, RSO2g2, RSO2g3, RSO9a, RSO14, RSO16 - Full map response decoded recursively

**Test ID**: `objects/unit/RSO2g1/full-map-recursive-decode-0`

| Spec | Requirement |
|------|-------------|
| RSO2g1 | A node with a `map` field is returned as a `RestLiveMap`; each `map.entries[key].data` is decoded recursively per RSO2g |
| RSO2g2 | A node with a `counter` field is returned as a `RestLiveCounter` |
| RSO2g3 | Any other node is an `ObjectData` leaf decoded per OD5 |
| RSO14 | `RestLiveMap` has `objectId`, `map.semantics`, `map.entries` |
| RSO15 | `RestLiveCounter` has `objectId`, `counter.data.number` |
| RSO16 | `RestLiveMapEntry.data` is a recursively decoded `RestObjectGetFullResult` |

Tests that a full-mode map response is decoded into nested `RestLiveMap`, `RestLiveCounter` and
decoded `ObjectData` leaves (JSON protocol).

`map.semantics` is sent on the wire as the `ObjectsMapSemantics` integer (`0` = `LWW`, per OMP2) and
asserted as the symbolic enum value (see *Enum values* in the UTS README).

### Setup
```pseudo
full_body = {
  "objectId": "root",
  "map": {
    "semantics": 0,
    "entries": {
      "str":   { "data": { "string": "hello" } },
      "num":   { "data": { "number": 42 } },
      "bool":  { "data": { "boolean": true } },
      "bin":   { "data": { "bytes": base64_encode(bytes([0x01, 0x02, 0x03])) } },
      "jobj":  { "data": { "string": "{\"a\":1}", "encoding": "json" } },
      "jarr":  { "data": { "string": "[1,2,3]", "encoding": "json" } },
      "visits": {
        "data": {
          "objectId": "counter:visitsHash@1700000000000",
          "counter": { "data": { "number": 7 } }
        }
      },
      "profile": {
        "data": {
          "objectId": "map:profileHash@1700000000000",
          "map": {
            "semantics": 0,
            "entries": {
              "nickname": { "data": { "string": "ally" } }
            }
          }
        }
      }
    }
  }
}

{ channel } = setup_rest_object("test-RSO2g1-" + random_id(), full_body)
```

### Test Steps
```pseudo
result = AWAIT channel.object.get(RestObjectGetParams(compact: false))
```

### Assertions
```pseudo
ASSERT result IS RestLiveMap
ASSERT result.objectId == "root"
ASSERT result.map.semantics == "LWW"
ASSERT result.map.entries.keys() == {"str", "num", "bool", "bin", "jobj", "jarr", "visits", "profile"}

# Leaves (RSO2g3, RSO9c)
ASSERT result.map.entries["str"].data.string == "hello"
ASSERT result.map.entries["num"].data.number == 42
ASSERT result.map.entries["bool"].data.boolean == true
ASSERT result.map.entries["bin"].data.bytes IS Binary
ASSERT result.map.entries["bin"].data.bytes == bytes([0x01, 0x02, 0x03])
ASSERT result.map.entries["jobj"].data.json == { "a": 1 }
ASSERT result.map.entries["jarr"].data.json == [1, 2, 3]
ASSERT result.map.entries["jobj"].data.encoding == null

# Nested counter (RSO2g2, RSO15)
visits = result.map.entries["visits"].data
ASSERT visits IS RestLiveCounter
ASSERT visits.objectId == "counter:visitsHash@1700000000000"
ASSERT visits.counter.data.number == 7

# Nested map, decoded recursively (RSO2g1, RSO16)
profile = result.map.entries["profile"].data
ASSERT profile IS RestLiveMap
ASSERT profile.objectId == "map:profileHash@1700000000000"
ASSERT profile.map.semantics == "LWW"
ASSERT profile.map.entries["nickname"].data.string == "ally"
```

---

## RSO2g2, RSO9b, RSO15 - Full counter response

**Test ID**: `objects/unit/RSO2g2/full-counter-0`

| Spec | Requirement |
|------|-------------|
| RSO2g2 | A response with a `counter` field is returned as a `RestLiveCounter` without further decoding |
| RSO15 | `RestLiveCounter` has `objectId` and `counter.data.number` |

### Setup
```pseudo
full_body = {
  "objectId": "counter:abcHash@1700000000000",
  "counter": { "data": { "number": -3.5 } }
}

{ channel } = setup_rest_object("test-RSO2g2-" + random_id(), full_body)
```

### Test Steps
```pseudo
result = AWAIT channel.object.get(RestObjectGetParams(
  objectId: "counter:abcHash@1700000000000",
  compact: false
))
```

### Assertions
```pseudo
ASSERT result IS RestLiveCounter
ASSERT result.objectId == "counter:abcHash@1700000000000"
ASSERT result.counter.data.number == -3.5
```

---

## RSO2g3, RSO9c - Full leaf response decoded per OD5 (JSON protocol)

**Test ID**: `objects/unit/RSO2g3/full-leaf-decode-json-0`

| Spec | Requirement |
|------|-------------|
| RSO2g3 | A response with neither `map` nor `counter` is an `ObjectData` leaf decoded per OD5 |
| RSO9c1 | The returned `ObjectData` has `objectId` and `encoding` unset |
| RSO9c2 | `bytes` holds a native `Binary`; JSON-encoded payloads appear parsed |

Tests decoding of each leaf type when the full-mode target is a leaf value.

### Test Cases

| ID | Response body | Expected field | Expected value |
|----|---------------|----------------|----------------|
| 1 | `{ "string": "hello" }` | `string` | `"hello"` |
| 2 | `{ "number": 3.25 }` | `number` | `3.25` |
| 3 | `{ "boolean": false }` | `boolean` | `false` |
| 4 | `{ "bytes": "AQID" }` | `bytes` | `bytes([0x01, 0x02, 0x03])` |
| 5 | `{ "string": "{\"k\":\"v\"}", "encoding": "json" }` | `json` | `{ "k": "v" }` |
| 6 | `{ "string": "[1,\"a\",null]", "encoding": "json" }` | `json` | `[1, "a", null]` |

### Test Steps and Assertions
```pseudo
FOR EACH test_case IN test_cases:
  { channel } = setup_rest_object("test-RSO2g3-" + random_id(), test_case.response_body)

  result = AWAIT channel.object.get(RestObjectGetParams(path: "leaf", compact: false))

  ASSERT result IS ObjectData
  ASSERT result[test_case.expected_field] == test_case.expected_value
  ASSERT result.objectId == null
  ASSERT result.encoding == null
  IF test_case.expected_field == "bytes":
    ASSERT result.bytes IS Binary
```

---

## RSO2g3, RSO9c2 - Full leaf response decoded per OD5 (MessagePack protocol)

**Test ID**: `objects/unit/RSO2g3/full-leaf-decode-msgpack-1`

**Spec requirement:** RSO2g3 — Leaves are decoded per OD5: with MessagePack, `bytes` arrives as binary and is returned as-is, and `string` with `encoding: "json"` is parsed as JSON (OD5a2).

### Test Cases

| ID | Response body | Expected field | Expected value |
|----|---------------|----------------|----------------|
| 1 | `{ "bytes": bytes([0xFF, 0x00]) }` | `bytes` | `bytes([0xFF, 0x00])` |
| 2 | `{ "string": "{\"k\":[1,2]}", "encoding": "json" }` | `json` | `{ "k": [1, 2] }` |
| 3 | `{ "string": "plain" }` | `string` | `"plain"` |

### Test Steps and Assertions
```pseudo
FOR EACH test_case IN test_cases:
  { channel } = setup_rest_object("test-RSO2g3-msgpack-" + random_id(),
    test_case.response_body, use_binary_protocol: true)

  result = AWAIT channel.object.get(RestObjectGetParams(path: "leaf", compact: false))

  ASSERT result[test_case.expected_field] == test_case.expected_value
  ASSERT result.encoding == null
```

---

## RSO2g4, RSO9d - Unrecognized object shape passed through

**Test ID**: `objects/unit/RSO2g4/unrecognized-object-passthrough-0`

| Spec | Requirement |
|------|-------------|
| RSO2g4 | Unrecognized object shapes must be passed through unmodified, per RSF1 |
| RSO9d | For unrecognized object types, the result contains at minimum `objectId`, with additional fields passed through unmodified |

Tests that a full-mode response for an object type the SDK does not know about does not fail
decoding, and that the `objectId` and the unrecognized fields reach the caller — both at the top level
and as a map entry.

In SDKs whose result types cannot carry arbitrary extra fields, the assertions on `futureType` are not
applicable; the `objectId` assertions still apply.

### Setup
```pseudo
full_body = {
  "objectId": "root",
  "map": {
    "semantics": 0,
    "entries": {
      "known": { "data": { "string": "ok" } },
      "future": {
        "data": {
          "objectId": "future:xyzHash@1700000000000",
          "futureType": { "someField": 1 }
        }
      }
    }
  }
}
top_level_body = {
  "objectId": "future:topHash@1700000000000",
  "futureType": { "someField": 2 }
}
```

### Test Steps
```pseudo
{ channel } = setup_rest_object("test-RSO2g4-entry-" + random_id(), full_body)
map_result = AWAIT channel.object.get(RestObjectGetParams(compact: false))

{ channel: channel2 } = setup_rest_object("test-RSO2g4-top-" + random_id(), top_level_body)
top_result = AWAIT channel2.object.get(RestObjectGetParams(compact: false))
```

### Assertions
```pseudo
ASSERT map_result IS RestLiveMap
ASSERT map_result.map.entries["known"].data.string == "ok"

future_entry = map_result.map.entries["future"].data
ASSERT future_entry.objectId == "future:xyzHash@1700000000000"
ASSERT future_entry.futureType == { "someField": 1 }

ASSERT top_result.objectId == "future:topHash@1700000000000"
ASSERT top_result.futureType == { "someField": 2 }
```

---

## RSO2h - get performs no client-side validation and surfaces server errors

**Test ID**: `objects/unit/RSO2h/no-validation-server-error-0`

**Spec requirement:** RSO2h — The library must not perform client-side validation of `params.objectId` or `params.path` content; any server-returned error must be surfaced to the caller as a rejected `ErrorInfo`.

Tests that unusual `objectId`/`path` values are sent to the server, and the server's error response is
surfaced as the rejection.

### Setup
```pseudo
channel_name = "test-RSO2h-" + random_id()
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(404, {
      "error": { "code": 40400, "statusCode": 404, "message": "Object not found" }
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

### Test Steps and Assertions
```pseudo
AWAIT channel.object.get(RestObjectGetParams(
  objectId: "not-a-valid-object-id",
  path: "..*..",
  compact: false
)) FAILS WITH error

ASSERT captured_requests.length == 1
ASSERT captured_requests[0].url.path == "/channels/" + encode_uri_component(channel_name)
  + "/object/" + encode_uri_component("not-a-valid-object-id")
ASSERT captured_requests[0].url.query_params["path"] == "..*.."

ASSERT error.code == 40400
ASSERT error.statusCode == 404
```
