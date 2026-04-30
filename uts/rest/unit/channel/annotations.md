# REST Channel Annotations Tests

Spec points: `RSL10`, `RSAN1`, `RSAN1a`, `RSAN1a2`, `RSAN1a3`, `RSAN1c`, `RSAN1c1`, `RSAN1c2`, `RSAN1c3`, `RSAN1c4`, `RSAN1c5`, `RSAN1c6`, `RSAN2`, `RSAN2a`, `RSAN3`, `RSAN3a`, `RSAN3b`, `RSAN3c`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

These tests use the mock HTTP infrastructure defined in `uts/test/rest/unit/helpers/mock_http.md`.

---

## RSL10 — channel.annotations returns RestAnnotations

**Spec requirement:** RSL10 — `RestChannel#annotations` attribute contains the `RestAnnotations` object for this channel.

Tests that the channel exposes an `annotations` attribute of type `RestAnnotations`.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, {})
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-RSL10")
```

### Assertions
```pseudo
ASSERT channel.annotations IS RestAnnotations
```

---

## RSAN1c6, RSAN1c1, RSAN1c2 — publish sends POST with ANNOTATION_CREATE to correct endpoint

| Spec | Requirement |
|------|-------------|
| RSAN1c6 | Body sent as POST to `/channels/{channelName}/messages/{messageSerial}/annotations` |
| RSAN1c1 | `Annotation.action` must be set to `ANNOTATION_CREATE` |
| RSAN1c2 | `Annotation.messageSerial` must be set to the identifier from the first argument |

Tests that `annotations.publish()` sends a correctly formatted POST request.

### Setup
```pseudo
channel_name = "test-RSAN1-publish-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.annotations.publish("msg-serial-1", Annotation(
  type: "com.example.reaction",
  name: "like"
))
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name) + "/messages/msg-serial-1/annotations"

body = parse_json(request.body)
ASSERT body IS List
ASSERT body.length == 1

annotation = body[0]
ASSERT annotation["action"] == 0  # ANNOTATION_CREATE numeric value
ASSERT annotation["messageSerial"] == "msg-serial-1"
ASSERT annotation["type"] == "com.example.reaction"
ASSERT annotation["name"] == "like"
```

---

## RSAN1a3 — publish validates type is required

**Spec requirement:** RSAN1a3 — The SDK must validate that the user supplied a `type`. All other fields are optional.

Tests that publishing an annotation without a `type` field throws an error.

### Setup
```pseudo
channel_name = "test-RSAN1a3-${random_id()}"

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(201, {})
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps and Assertions
```pseudo
# Annotation without type
AWAIT channel.annotations.publish("msg-serial-1", Annotation(
  name: "like"
)) FAILS WITH error
ASSERT error.code == 40003
```

---

## RSAN1c3 — annotation data encoded per RSL4

**Spec requirement:** RSAN1c3 — If the user has supplied an `Annotation.data`, that must be encoded (and the `encoding` set) just as it would be for a `Message`, per `RSL4`.

Tests that JSON data in an annotation is encoded following message encoding rules.

### Setup
```pseudo
channel_name = "test-RSAN1c3-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.annotations.publish("msg-serial-1", Annotation(
  type: "com.example.data",
  data: { "key": "value", "nested": { "a": 1 } }
))
```

### Assertions
```pseudo
body = parse_json(captured_requests[0].body)
annotation = body[0]

# JSON data should be encoded as a string with encoding field
ASSERT annotation["data"] IS String
ASSERT annotation["encoding"] == "json"
ASSERT parse_json(annotation["data"]) == { "key": "value", "nested": { "a": 1 } }
```

---

## RSAN1c4 — idempotent ID generated when enabled

**Spec requirement:** RSAN1c4 — If `idempotentRestPublishing` is enabled and the annotation has an empty `id`, the SDK should generate a base64-encoded random string, append `:0`, and set it as the `Annotation.id`.

Tests that an idempotent ID is auto-generated when the option is enabled.

### Setup
```pseudo
channel_name = "test-RSAN1c4-enabled-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  idempotentRestPublishing: true
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.annotations.publish("msg-serial-1", Annotation(
  type: "com.example.reaction"
))
```

### Assertions
```pseudo
body = parse_json(captured_requests[0].body)
annotation = body[0]

ASSERT "id" IN annotation
annotation_id = annotation["id"]

# Format: <base64>:0
parts = annotation_id.split(":")
ASSERT parts.length == 2
ASSERT parts[0] matches pattern "[A-Za-z0-9_-]+"
ASSERT parts[0].length >= 12  # At least 9 bytes base64 encoded
ASSERT parts[1] == "0"
```

---

## RSAN1c4 — idempotent ID not generated when disabled

**Spec requirement:** RSAN1c4 — The SDK should only generate idempotent IDs when `idempotentRestPublishing` is enabled.

Tests that no ID is auto-generated when idempotent publishing is disabled.

### Setup
```pseudo
channel_name = "test-RSAN1c4-disabled-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  idempotentRestPublishing: false
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.annotations.publish("msg-serial-1", Annotation(
  type: "com.example.reaction"
))
```

### Assertions
```pseudo
body = parse_json(captured_requests[0].body)
annotation = body[0]

ASSERT "id" NOT IN annotation
```

---

## RSAN2a — delete sends POST with ANNOTATION_DELETE

**Spec requirement:** RSAN2a — Must be identical to RSAN1 `publish()` except that the `Annotation.action` is set to `ANNOTATION_DELETE`, not `ANNOTATION_CREATE`.

Tests that `annotations.delete()` sends a POST with the delete action.

### Setup
```pseudo
channel_name = "test-RSAN2-delete-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.annotations.delete("msg-serial-1", Annotation(
  type: "com.example.reaction",
  name: "like"
))
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name) + "/messages/msg-serial-1/annotations"

body = parse_json(request.body)
ASSERT body IS List
ASSERT body.length == 1

annotation = body[0]
ASSERT annotation["action"] == 1  # ANNOTATION_DELETE numeric value
ASSERT annotation["messageSerial"] == "msg-serial-1"
ASSERT annotation["type"] == "com.example.reaction"
ASSERT annotation["name"] == "like"
```

---

## RSAN3b — get sends GET to correct endpoint

| Spec | Requirement |
|------|-------------|
| RSAN3b | Sends a GET request to `/channels/{channelName}/messages/{messageSerial}/annotations` |

Tests that `annotations.get()` sends a GET request to the correct URL.

### Setup
```pseudo
channel_name = "test-RSAN3-get-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      {
        "id": "ann-1",
        "action": 0,
        "type": "com.example.reaction",
        "name": "like",
        "clientId": "user-1",
        "serial": "ann-serial-1",
        "messageSerial": "msg-serial-1",
        "timestamp": 1700000000000
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
result = AWAIT channel.annotations.get("msg-serial-1")
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.method == "GET"
ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name) + "/messages/msg-serial-1/annotations"
```

---

## RSAN3c — get returns PaginatedResult of Annotations

**Spec requirement:** RSAN3c — Returns a `PaginatedResult<Annotation>` page containing the first page of decoded `Annotation` objects.

Tests that the response is parsed into a paginated result of annotations with all fields.

### Setup
```pseudo
channel_name = "test-RSAN3c-${random_id()}"

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, [
      {
        "id": "ann-1",
        "action": 0,
        "type": "com.example.reaction",
        "name": "like",
        "clientId": "user-1",
        "count": 1,
        "data": "thumbs-up",
        "serial": "ann-serial-1",
        "messageSerial": "msg-serial-1",
        "timestamp": 1700000000000,
        "extras": { "custom": "metadata" }
      },
      {
        "id": "ann-2",
        "action": 0,
        "type": "com.example.reaction",
        "name": "heart",
        "clientId": "user-2",
        "serial": "ann-serial-2",
        "messageSerial": "msg-serial-1",
        "timestamp": 1700000001000
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
result = AWAIT channel.annotations.get("msg-serial-1")
```

### Assertions
```pseudo
ASSERT result IS PaginatedResult
ASSERT result.items.length == 2

ann1 = result.items[0]
ASSERT ann1 IS Annotation
ASSERT ann1.id == "ann-1"
ASSERT ann1.action == AnnotationAction.ANNOTATION_CREATE
ASSERT ann1.type == "com.example.reaction"
ASSERT ann1.name == "like"
ASSERT ann1.clientId == "user-1"
ASSERT ann1.count == 1
ASSERT ann1.data == "thumbs-up"
ASSERT ann1.serial == "ann-serial-1"
ASSERT ann1.messageSerial == "msg-serial-1"
ASSERT ann1.timestamp == 1700000000000
ASSERT ann1.extras["custom"] == "metadata"

ann2 = result.items[1]
ASSERT ann2.name == "heart"
ASSERT ann2.clientId == "user-2"
```

---

## RSAN3b — get passes params as querystring

**Spec requirement:** RSAN3b — Any `params` are sent in the querystring.

Tests that optional params are sent as query parameters.

### Setup
```pseudo
channel_name = "test-RSAN3b-params-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.annotations.get("msg-serial-1", params: { "limit": "50" })
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.url.query_params["limit"] == "50"
```
