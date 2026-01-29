# REST Channel Publish Tests

Spec points: `RSL1`, `RSL1a`, `RSL1b`, `RSL1c`, `RSL1d`, `RSL1e`, `RSL1h`, `RSL1i`, `RSL1j`, `RSL1l`, `RSL1m`

## Test Type
Unit test with mocked HTTP client

## Mock Configuration

### HTTP Client Mock
All tests use a mocked HTTP client that:
- Captures outgoing requests for inspection
- Returns configurable responses
- Is injected via the language-appropriate mechanism

### Standard Success Response
```json
{
  "statusCode": 201,
  "headers": { "Content-Type": "application/json" },
  "body": { "serials": ["abc123"] }
}
```

### Standard Error Response
```json
{
  "statusCode": 400,
  "headers": { "Content-Type": "application/json" },
  "body": {
    "error": {
      "code": 40000,
      "statusCode": 400,
      "message": "Bad request"
    }
  }
}
```

---

## RSL1a, RSL1b - Publish with name and data

Tests that `publish(name, data)` sends a single message.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["serial1"] })

client = Rest(
  options: ClientOptions(key: "appId.keyId:keySecret")
)
# mock_http is injected via language-appropriate mechanism
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "greeting", data: "hello")
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]

# RSL1b - single message published
ASSERT request.method == "POST"
ASSERT request.url.path == "/channels/test-channel/messages"

body = parse_json(request.body)
ASSERT body IS List
ASSERT body.length == 1
ASSERT body[0]["name"] == "greeting"
ASSERT body[0]["data"] == "hello"
```

---

## RSL1a, RSL1c - Publish with Message array

Tests that `publish(messages: [...])` sends all messages in a single request.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1", "s2", "s3"] })

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-channel")
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
ASSERT mock_http.captured_requests.length == 1

request = mock_http.captured_requests[0]
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

Tests that null values are omitted from the transmitted message.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-channel")
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
  mock_http.reset()
  mock_http.queue_response(201, { "serials": ["s1"] })

  AWAIT channel.publish(name: test_case.name, data: test_case.data)

  body = parse_json(mock_http.captured_requests[0].body)
  ASSERT body == [test_case.expected_body]
  ASSERT "name" NOT IN body[0] IF test_case.name IS null
  ASSERT "data" NOT IN body[0] IF test_case.data IS null
```

---

## RSL1h - publish(name, data) signature

Tests that the two-argument form takes no additional arguments and works correctly.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-channel")
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
ASSERT mock_http.captured_requests.length == 1
body = parse_json(mock_http.captured_requests[0].body)
ASSERT body[0]["name"] == "event"
ASSERT body[0]["data"] == "payload"
```

---

## RSL1i - Message size limit

Tests that messages exceeding `maxMessageSize` are rejected with error 40009.

### Setup
```pseudo
mock_http = MockHttpClient()
# Note: mock should NOT receive any request for this test

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  maxMessageSize: 1024  # 1KB limit for testing
))
channel = client.channels.get("test-channel")
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
  mock_http.reset()
  mock_http.queue_response(201, { "serials": ["s1"] })

  large_data = "x" * test_case.size

  IF test_case.expected == "Success":
    AWAIT channel.publish(name: "event", data: large_data)
    ASSERT mock_http.captured_requests.length == 1
  ELSE:
    ASSERT channel.publish(name: "event", data: large_data) THROWS AblyException WITH:
      code == 40009
    ASSERT mock_http.captured_requests.length == 0  # Request never sent
```

---

## RSL1j - All Message attributes transmitted

Tests that all valid Message attributes are included in the encoded message.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-channel")
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
body = parse_json(mock_http.captured_requests[0].body)[0]

ASSERT body["name"] == "test-event"
ASSERT body["data"] == "test-data"
ASSERT body["id"] == "custom-message-id"
ASSERT body["extras"]["push"]["notification"]["title"] == "Test"
# clientId handling is tested separately in RSL1m tests
```

---

## RSL1l - Publish params as querystring

Tests that additional params are sent as querystring parameters.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-channel")
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
request = mock_http.captured_requests[0]

ASSERT request.url.query_params["customParam"] == "customValue"
ASSERT request.url.query_params["anotherParam"] == "123"
```

---

## RSL1m - ClientId not set from library clientId

Tests that the library does not automatically set `Message.clientId` from the client's configured `clientId`.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  clientId: "library-client-id"
))
channel = client.channels.get("test-channel")
```

### Test Cases (RSL1m1-RSL1m3)

| ID | Spec | Message clientId | Library clientId | Expected in request |
|----|------|------------------|------------------|---------------------|
| RSL1m1 | Message with no clientId, library has clientId | `null` | `"lib-client"` | clientId absent |
| RSL1m2 | Message clientId matches library clientId | `"lib-client"` | `"lib-client"` | `"lib-client"` |
| RSL1m3 | Unidentified client, message has clientId | `"msg-client"` | `null` | `"msg-client"` |

### Test Steps
```pseudo
# RSL1m1 - Message with no clientId
mock_http.reset()
mock_http.queue_response(201, { "serials": ["s1"] })

client_with_id = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  clientId: "lib-client"
))
AWAIT client_with_id.channels.get("ch").publish(name: "e", data: "d")

body = parse_json(mock_http.captured_requests[0].body)[0]
ASSERT "clientId" NOT IN body  # Library should not inject its clientId


# RSL1m2 - Message clientId matches library
mock_http.reset()
mock_http.queue_response(201, { "serials": ["s1"] })

AWAIT client_with_id.channels.get("ch").publish(
  message: Message(name: "e", data: "d", clientId: "lib-client")
)

body = parse_json(mock_http.captured_requests[0].body)[0]
ASSERT body["clientId"] == "lib-client"  # Explicit clientId preserved


# RSL1m3 - Unidentified client with message clientId
mock_http.reset()
mock_http.queue_response(201, { "serials": ["s1"] })

client_no_id = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
AWAIT client_no_id.channels.get("ch").publish(
  message: Message(name: "e", data: "d", clientId: "msg-client")
)

body = parse_json(mock_http.captured_requests[0].body)[0]
ASSERT body["clientId"] == "msg-client"
```

### Note
RSL1m4 (clientId mismatch rejection) requires an integration test as the server performs the validation.
