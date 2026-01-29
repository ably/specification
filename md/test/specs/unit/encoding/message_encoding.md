# Message Encoding Tests

Spec points: `RSL4`, `RSL4a`, `RSL4b`, `RSL4c`, `RSL4d`, `RSL6`, `RSL6a`, `RSL6b`

## Test Type
Unit test with mocked HTTP client

## Mock Configuration

### HTTP Client Mock
Captures outgoing requests to verify encoding, returns configurable responses.

## Fixtures
Tests should use the encoding fixtures from `ably-common` where available for cross-SDK consistency.

---

## RSL4a - String data encoding

Tests that string data is transmitted without transformation.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false  # Use JSON for easier inspection
))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: "plain string data")
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
body = parse_json(request.body)[0]

ASSERT body["data"] == "plain string data"
ASSERT "encoding" NOT IN body OR body["encoding"] IS null
```

---

## RSL4b - JSON object encoding

Tests that JSON objects are serialized with `json` encoding.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: { "key": "value", "nested": { "a": 1 } })
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
body = parse_json(request.body)[0]

# Data should be JSON-serialized string
ASSERT body["data"] IS String
ASSERT parse_json(body["data"]) == { "key": "value", "nested": { "a": 1 } }
ASSERT body["encoding"] == "json"
```

---

## RSL4c - Binary data encoding

Tests that binary data is base64-encoded for JSON protocol.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false  # JSON protocol requires base64 for binary
))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
binary_data = bytes([0x00, 0x01, 0x02, 0xFF, 0xFE])
AWAIT channel.publish(name: "event", data: binary_data)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
body = parse_json(request.body)[0]

ASSERT body["encoding"] == "base64"
ASSERT base64_decode(body["data"]) == bytes([0x00, 0x01, 0x02, 0xFF, 0xFE])
```

---

## RSL4c - Binary data with MessagePack

Tests that binary data is transmitted directly with MessagePack protocol.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: true  # MessagePack
))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
binary_data = bytes([0x00, 0x01, 0x02, 0xFF, 0xFE])
AWAIT channel.publish(name: "event", data: binary_data)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
body = msgpack_decode(request.body)[0]

# Binary data should be transmitted directly, no base64
ASSERT body["data"] == bytes([0x00, 0x01, 0x02, 0xFF, 0xFE])
ASSERT "encoding" NOT IN body OR body["encoding"] IS null
```

---

## RSL4d - Array data encoding

Tests that arrays are JSON-encoded.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: [1, 2, "three", { "four": 4 }])
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
body = parse_json(request.body)[0]

ASSERT body["encoding"] == "json"
ASSERT parse_json(body["data"]) == [1, 2, "three", { "four": 4 }]
```

---

## RSL6a - Decoding base64 data

Tests that `base64` encoded data is decoded correctly.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, [
  {
    "id": "msg1",
    "name": "event",
    "data": "AAECAwQ=",  # base64 of [0, 1, 2, 3, 4]
    "encoding": "base64",
    "timestamp": 1234567890000
  }
])

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
history = AWAIT channel.history()
message = history.items[0]
```

### Assertions
```pseudo
ASSERT message.data == bytes([0x00, 0x01, 0x02, 0x03, 0x04])
ASSERT message.encoding IS null  # Encoding consumed after decode
```

---

## RSL6a - Decoding JSON data

Tests that `json` encoded data is decoded correctly.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, [
  {
    "id": "msg1",
    "name": "event",
    "data": "{\"key\":\"value\",\"number\":42}",
    "encoding": "json",
    "timestamp": 1234567890000
  }
])

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
history = AWAIT channel.history()
message = history.items[0]
```

### Assertions
```pseudo
ASSERT message.data == { "key": "value", "number": 42 }
ASSERT message.encoding IS null
```

---

## RSL6a - Decoding chained encodings

Tests that chained encodings (e.g., `json/base64`) are decoded in reverse order.

### Setup
```pseudo
mock_http = MockHttpClient()
# Data: {"key":"value"} -> JSON string -> base64 encoded
json_string = "{\"key\":\"value\"}"
base64_of_json = base64_encode(json_string)

mock_http.queue_response(200, [
  {
    "id": "msg1",
    "name": "event",
    "data": base64_of_json,
    "encoding": "json/base64",  # Decode base64 first, then JSON
    "timestamp": 1234567890000
  }
])

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
history = AWAIT channel.history()
message = history.items[0]
```

### Assertions
```pseudo
ASSERT message.data == { "key": "value" }
ASSERT message.encoding IS null
```

---

## RSL6b - Unrecognized encoding preserved

Tests that unrecognized encodings are preserved and data is left as-is.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, [
  {
    "id": "msg1",
    "name": "event",
    "data": "encrypted-data-here",
    "encoding": "custom-encryption/base64",
    "timestamp": 1234567890000
  }
])

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
history = AWAIT channel.history()
message = history.items[0]
```

### Assertions
```pseudo
# base64 should be decoded, but custom-encryption is unrecognized
ASSERT message.encoding == "custom-encryption"
# Data should be base64-decoded but not further processed
ASSERT message.data IS bytes  # Result of base64 decode
```

---

## RSL4 - Encoding fixtures from ably-common

Tests encoding/decoding using standardized fixtures.

### Setup
```pseudo
# Load fixtures from ably-common/test-resources/...
encoding_fixtures = load_fixtures("encoding.json")
```

### Test Steps
```pseudo
FOR EACH fixture IN encoding_fixtures:
  mock_http = MockHttpClient()
  mock_http.queue_response(201, { "serials": ["s1"] })

  client = Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    useBinaryProtocol: fixture.use_binary_protocol
  ))
  channel = client.channels.get("test")

  # Publish with input data
  AWAIT channel.publish(name: "event", data: fixture.input_data)

  # Verify encoded format
  request = mock_http.captured_requests[0]

  IF fixture.use_binary_protocol:
    body = msgpack_decode(request.body)[0]
  ELSE:
    body = parse_json(request.body)[0]

  ASSERT body["data"] == fixture.expected_wire_data
  ASSERT body["encoding"] == fixture.expected_encoding
```
