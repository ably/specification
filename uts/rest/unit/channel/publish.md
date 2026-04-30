# REST Channel Publish Tests

Spec points: `RSL1`, `RSL1a`, `RSL1b`, `RSL1c`, `RSL1d`, `RSL1e`, `RSL1h`, `RSL1i`, `RSL1j`, `RSL1l`, `RSL1m`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

These tests use the mock HTTP infrastructure defined in `/Users/paddy/data/worknew/dev/dart-experiments/uts/test/rest/unit/rest_client.md`.

The mock must support:
- Handler-based configuration with `onConnectionAttempt` and `onRequest` callbacks
- Request capture via `captured_requests` arrays
- Request counting via `request_count` variables
- Response configuration with status, headers, and body

See rest_client.md for the complete `MockHttpClient` interface specification.

---

## RSL1a, RSL1b - Publish with name and data

| Spec | Requirement |
|------|-------------|
| RSL1a | Channel publish method must support publishing a single message with name and data |
| RSL1b | Single message publish must send the message in an array via POST to `/channels/<channel_name>/messages` |

Tests that `publish(name, data)` sends a single message.

### Setup
```pseudo
channel_name = "test-RSL1a-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, { "serials": ["serial1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "greeting", data: "hello")
```

### Assertions
```pseudo
request = captured_requests[0]

# RSL1b - single message published
ASSERT request.method == "POST"
ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name) + "/messages"

body = parse_json(request.body)
ASSERT body IS List
# NOTE: Some SDKs send a single message as a plain JSON object rather than
# wrapping it in an array. The Ably API accepts both formats. SDKs MAY send
# a single message as either an object or a single-element array.
ASSERT body.length == 1
ASSERT body[0]["name"] == "greeting"
ASSERT body[0]["data"] == "hello"
```

---

## RSL1a, RSL1c - Publish with Message array

| Spec | Requirement |
|------|-------------|
| RSL1a | Channel publish method must support publishing an array of Message objects |
| RSL1c | Publishing multiple messages must send all messages in a single HTTP request |

Tests that `publish(messages: [...])` sends all messages in a single request.

### Setup
```pseudo
channel_name = "test-RSL1c-${random_id()}"
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    request_count = request_count + 1
    req.respond_with(201, { "serials": ["s1", "s2", "s3"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
messages = [
  Message(name: "event1", data: "data1"),
  Message(name: "event2", data: { "key": "value" }),
  Message(name: "event3", data: bytes([0x01, 0x02, 0x03]))
]
AWAIT channel.publish(messages: messages)
```

### Assertions
```pseudo
# RSL1c - single request for array
ASSERT request_count == 1

request = captured_requests[0]
body = parse_json(request.body)

ASSERT body.length == 3
ASSERT body[0]["name"] == "event1"
ASSERT body[0]["data"] == "data1"
ASSERT body[1]["name"] == "event2"
ASSERT body[1]["data"] == { "key": "value" }
# Note: binary data encoding tested separately in encoding tests
```

---

## RSL1e - Null name and data

**Spec requirement:** Null values for name and data must be omitted from the transmitted message JSON, not sent as JSON null.

Tests that null values are omitted from the transmitted message.

### Setup
```pseudo
channel_name = "test-RSL1e-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Cases

| ID | name | data | Expected body |
|----|------|------|---------------|
| 1 | `null` | `"hello"` | `[{"data": "hello"}]` |
| 2 | `"event"` | `null` | `[{"name": "event"}]` |
| 3 | `null` | `null` | `[{}]` |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  captured_requests = []

  AWAIT channel.publish(name: test_case.name, data: test_case.data)

  body = parse_json(captured_requests[0].body)
  ASSERT body == [test_case.expected_body]
  ASSERT "name" NOT IN body[0] IF test_case.name IS null
  ASSERT "data" NOT IN body[0] IF test_case.data IS null
```

---

## RSL1h - publish(name, data) signature

**Spec requirement:** The publish method must support a two-argument signature `publish(name, data)` for publishing a single message.

Tests that the two-argument form takes no additional arguments and works correctly.

### Setup
```pseudo
channel_name = "test-RSL1h-${random_id()}"
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    request_count = request_count + 1
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# This is a compile-time/type-system test in strongly-typed languages
# The API should accept exactly (name, data) with no extras
AWAIT channel.publish(name: "event", data: "payload")
# If language allows, verify that extra positional args are rejected at compile time
```

### Assertions
```pseudo
ASSERT request_count == 1
body = parse_json(captured_requests[0].body)
ASSERT body[0]["name"] == "event"
ASSERT body[0]["data"] == "payload"
```

---

## RSL1i - Message size limit

**Spec requirement:** Messages exceeding the `maxMessageSize` client option must be rejected before transmission with error code 40009.

Tests that messages exceeding `maxMessageSize` are rejected with error 40009.

### Setup
```pseudo
channel_name = "test-RSL1i-${random_id()}"
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    request_count = request_count + 1
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  maxMessageSize: 1024  # 1KB limit for testing
))
channel = client.channels.get(channel_name)
```

### Test Cases

| ID | Message size | Expected |
|----|--------------|----------|
| 1 | 1000 bytes | Success (under limit) |
| 2 | 1024 bytes | Success (at limit) |
| 3 | 1025 bytes | Error 40009 |
| 4 | 10000 bytes | Error 40009 |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  captured_requests = []
  request_count = 0

  large_data = "x" * test_case.size

  IF test_case.expected == "Success":
    AWAIT channel.publish(name: "event", data: large_data)
    ASSERT request_count == 1
  ELSE:
    ASSERT channel.publish(name: "event", data: large_data) THROWS AblyException WITH:
      code == 40009
    ASSERT request_count == 0  # Request never sent
```

---

## RSL1j - All Message attributes transmitted

**Spec requirement:** All valid Message attributes (name, data, id, clientId, extras) must be included in the transmitted message payload.

Tests that all valid Message attributes are included in the encoded message.

### Setup
```pseudo
channel_name = "test-RSL1j-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
message = Message(
  name: "test-event",
  data: "test-data",
  clientId: "explicit-client-id",  # RSL1m tests cover whether this should be sent
  id: "custom-message-id",
  extras: { "push": { "notification": { "title": "Test" } } }
)

AWAIT channel.publish(message: message)
```

### Assertions
```pseudo
body = parse_json(captured_requests[0].body)[0]

ASSERT body["name"] == "test-event"
ASSERT body["data"] == "test-data"
ASSERT body["id"] == "custom-message-id"
ASSERT body["extras"]["push"]["notification"]["title"] == "Test"
# clientId handling is tested separately in RSL1m tests
```

---

## RSL1l - Publish params as querystring

**Spec requirement:** Additional params passed to the publish method must be sent as query string parameters in the HTTP request.

Tests that additional params are sent as querystring parameters.

### Setup
```pseudo
channel_name = "test-RSL1l-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
params = {
  "customParam": "customValue",
  "anotherParam": "123"
}

AWAIT channel.publish(
  message: Message(name: "event", data: "data"),
  params: params
)
```

### Assertions
```pseudo
request = captured_requests[0]

ASSERT request.url.query_params["customParam"] == "customValue"
ASSERT request.url.query_params["anotherParam"] == "123"
```

---

## RSL1m - ClientId not set from library clientId

| Spec | Requirement |
|------|-------------|
| RSL1m1 | Library must not automatically inject its clientId into messages that don't have one |
| RSL1m2 | Explicit message clientId must be preserved even if it matches library clientId |
| RSL1m3 | Unidentified clients (no library clientId) can publish messages with explicit clientId |

Tests that the library does not automatically set `Message.clientId` from the client's configured `clientId`.

### Setup
```pseudo
channel_name = "test-RSL1m-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  clientId: "library-client-id"
))
channel = client.channels.get(channel_name)
```

### Test Cases (RSL1m1-RSL1m3)

| ID | Spec | Message clientId | Library clientId | Expected in request |
|----|------|------------------|------------------|---------------------|
| RSL1m1 | Message with no clientId, library has clientId | `null` | `"lib-client"` | clientId absent |
| RSL1m2 | Message clientId matches library clientId | `"lib-client"` | `"lib-client"` | `"lib-client"` |
| RSL1m3 | Unidentified client, message has clientId | `"msg-client"` | `null` | `"msg-client"` |

### Test Steps
```pseudo
channel_name_m1 = "test-RSL1m1-${random_id()}"
channel_name_m2 = "test-RSL1m2-${random_id()}"
channel_name_m3 = "test-RSL1m3-${random_id()}"

# RSL1m1 - Message with no clientId
captured_requests = []

client_with_id = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  clientId: "lib-client"
))
AWAIT client_with_id.channels.get(channel_name_m1).publish(name: "e", data: "d")

body = parse_json(captured_requests[0].body)[0]
ASSERT "clientId" NOT IN body  # Library should not inject its clientId


# RSL1m2 - Message clientId matches library
captured_requests = []

AWAIT client_with_id.channels.get(channel_name_m2).publish(
  message: Message(name: "e", data: "d", clientId: "lib-client")
)

body = parse_json(captured_requests[0].body)[0]
ASSERT body["clientId"] == "lib-client"  # Explicit clientId preserved


# RSL1m3 - Unidentified client with message clientId
captured_requests = []

client_no_id = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
AWAIT client_no_id.channels.get(channel_name_m3).publish(
  message: Message(name: "e", data: "d", clientId: "msg-client")
)

body = parse_json(captured_requests[0].body)[0]
ASSERT body["clientId"] == "msg-client"
```

### Note
RSL1m4 (clientId mismatch rejection) requires an integration test as the server performs the validation.
