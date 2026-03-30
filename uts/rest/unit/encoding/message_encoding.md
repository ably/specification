# Message Encoding Tests

Spec points: `RSL4`, `RSL4a`, `RSL4b`, `RSL4c`, `RSL4d`, `RSL6`, `RSL6a`, `RSL6b`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

These tests use the mock HTTP infrastructure described in `/Users/paddy/data/worknew/dev/dart-experiments/uts/test/rest/unit/rest_client.md`.

The mock supports:
- Intercepting HTTP requests and capturing details (URL, headers, method, body)
- Queueing responses with configurable status, headers, and body
- Handler-based configuration with `onConnectionAttempt` and `onRequest`
- Recording requests in `captured_requests` arrays
- Request counting with `request_count` variables

## Fixtures
Tests should use the encoding fixtures from `ably-common` where available for cross-SDK consistency.

---

## RSL4a - String data encoding

**Spec requirement:** String data must be transmitted without transformation and without an encoding field.

### Setup
```pseudo
channel_name = "test-RSL4a-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false  # Use JSON for easier inspection
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: "plain string data")
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)[0]

ASSERT body["data"] == "plain string data"
ASSERT "encoding" NOT IN body OR body["encoding"] IS null
```

---

## RSL4b - JSON object encoding

**Spec requirement:** JSON objects must be serialized to a JSON string with `encoding: "json"`.

### Setup
```pseudo
channel_name = "test-RSL4b-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: { "key": "value", "nested": { "a": 1 } })
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)[0]

# Data should be JSON-serialized string
ASSERT body["data"] IS String
ASSERT parse_json(body["data"]) == { "key": "value", "nested": { "a": 1 } }
ASSERT body["encoding"] == "json"
```

---

## RSL4c - Binary data encoding with JSON protocol

**Spec requirement:** Binary data must be base64-encoded when using JSON protocol.

### Setup
```pseudo
channel_name = "test-RSL4c-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false  # JSON protocol requires base64 for binary
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
binary_data = bytes([0x00, 0x01, 0x02, 0xFF, 0xFE])
AWAIT channel.publish(name: "event", data: binary_data)
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)[0]

ASSERT body["encoding"] == "base64"
ASSERT base64_decode(body["data"]) == bytes([0x00, 0x01, 0x02, 0xFF, 0xFE])
```

---

## RSL4c - Binary data with MessagePack protocol

**Spec requirement:** Binary data must be transmitted directly (without base64 encoding) when using MessagePack protocol.

### Setup
```pseudo
channel_name = "test-RSL4c-msgpack-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: true  # MessagePack
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
binary_data = bytes([0x00, 0x01, 0x02, 0xFF, 0xFE])
AWAIT channel.publish(name: "event", data: binary_data)
```

### Assertions
```pseudo
request = captured_requests[0]
body = msgpack_decode(request.body)[0]

# Binary data should be transmitted directly, no base64
ASSERT body["data"] == bytes([0x00, 0x01, 0x02, 0xFF, 0xFE])
ASSERT "encoding" NOT IN body OR body["encoding"] IS null
```

---

## RSL4d - Array data encoding

**Spec requirement:** Arrays must be JSON-encoded with `encoding: "json"`.

### Setup
```pseudo
channel_name = "test-RSL4d-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: [1, 2, "three", { "four": 4 }])
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)[0]

ASSERT body["encoding"] == "json"
ASSERT parse_json(body["data"]) == [1, 2, "three", { "four": 4 }]
```

---

## RSL6a - Decoding base64 data

**Spec requirement:** Data with `encoding: "base64"` must be decoded to binary, and the encoding field consumed.

### Setup
```pseudo
channel_name = "test-RSL6a-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      {
        "id": "msg1",
        "name": "event",
        "data": "AAECAwQ=",  # base64 of [0, 1, 2, 3, 4]
        "encoding": "base64",
        "timestamp": 1234567890000
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

**Spec requirement:** Data with `encoding: "json"` must be decoded from JSON string to native object, and the encoding field consumed.

### Setup
```pseudo
channel_name = "test-RSL6a-json-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      {
        "id": "msg1",
        "name": "event",
        "data": "{\"key\":\"value\",\"number\":42}",
        "encoding": "json",
        "timestamp": 1234567890000
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

**Spec requirement:** Chained encodings (e.g., `json/base64`) must be decoded in reverse order (last applied encoding is removed first). When processing chained encodings, decoders MUST handle intermediate data types — for example, after decoding `base64`, the data will be binary bytes; a subsequent `json` decoder MUST convert those bytes to a UTF-8 string before JSON parsing.

### Setup
```pseudo
channel_name = "test-RSL6a-chained-${random_id()}"
captured_requests = []

# Data: {"key":"value"} -> JSON string -> base64 encoded
json_string = "{\"key\":\"value\"}"
base64_of_json = base64_encode(json_string)

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      {
        "id": "msg1",
        "name": "event",
        "data": base64_of_json,
        "encoding": "json/base64",  # Decode base64 first, then JSON
        "timestamp": 1234567890000
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

**Spec requirement:** Unrecognized encoding values must be preserved in the encoding field, with only recognized encodings being decoded.

### Setup
```pseudo
channel_name = "test-RSL6b-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      {
        "id": "msg1",
        "name": "event",
        "data": "encrypted-data-here",
        "encoding": "custom-encryption/base64",
        "timestamp": 1234567890000
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

**Spec requirement:** Implementations must correctly encode data according to standardized test fixtures from `ably-common`.

### Setup
```pseudo
# Load fixtures from ably-common/test-resources/...
encoding_fixtures = load_fixtures("encoding.json")
```

### Test Steps
```pseudo
FOR EACH fixture IN encoding_fixtures:
  channel_name = "test-RSL4-fixture-${random_id()}"
  captured_requests = []
  
  mock_http = MockHttpClient(
    onConnectionAttempt: (conn) => conn.respond_with_success(),
    onRequest: (req) => {
      captured_requests.push(req)
      req.respond_with(201, { "serials": ["s1"] })
    }
  )
  install_mock(mock_http)

  client = Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    useBinaryProtocol: fixture.use_binary_protocol
  ))
  channel = client.channels.get(channel_name)

  # Publish with input data
  AWAIT channel.publish(name: "event", data: fixture.input_data)

  # Verify encoded format
  request = captured_requests[0]

  IF fixture.use_binary_protocol:
    body = msgpack_decode(request.body)[0]
  ELSE:
    body = parse_json(request.body)[0]

  ASSERT body["data"] == fixture.expected_wire_data
  ASSERT body["encoding"] == fixture.expected_encoding
```

---

## Additional Encoding Tests

### RSL4 - Null data encoding

**Spec requirement:** Null values must be transmitted without transformation.

### Setup
```pseudo
channel_name = "test-RSL4-null-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: null)
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)[0]

ASSERT body["data"] IS null
ASSERT "encoding" NOT IN body OR body["encoding"] IS null
```

---

### RSL4 - Number data encoding

**Spec requirement:** Numeric values must be transmitted directly without encoding.

### Setup
```pseudo
channel_name = "test-RSL4-number-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: 42)
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)[0]

ASSERT body["data"] == 42
ASSERT "encoding" NOT IN body OR body["encoding"] IS null
```

---

### RSL4 - Boolean data encoding

**Spec requirement:** Boolean values must be transmitted directly without encoding.

### Setup
```pseudo
channel_name = "test-RSL4-bool-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: true)
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)[0]

ASSERT body["data"] == true
ASSERT "encoding" NOT IN body OR body["encoding"] IS null
```

---

### RSL6 - Decoding UTF-8 encoded data

**Spec requirement:** Data with `encoding: "utf-8/base64"` must decode base64 first, then interpret as UTF-8 string.

### Setup
```pseudo
channel_name = "test-RSL6-utf8-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      {
        "id": "msg1",
        "name": "event",
        "data": "SGVsbG8gV29ybGQ=",  # base64 of UTF-8 "Hello World"
        "encoding": "utf-8/base64",
        "timestamp": 1234567890000
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
history = AWAIT channel.history()
message = history.items[0]
```

### Assertions
```pseudo
ASSERT message.data == "Hello World"
ASSERT message.data IS String
ASSERT message.encoding IS null
```

---

### RSL6 - Complex chained encoding

**Spec requirement:** Multiple encoding layers must be decoded in correct order.

### Setup
```pseudo
channel_name = "test-RSL6-complex-${random_id()}"
captured_requests = []

# Create data: object -> JSON -> UTF-8 bytes -> base64
original_object = { "status": "active", "count": 5 }
json_string = to_json(original_object)
utf8_bytes = encode_utf8(json_string)
base64_data = base64_encode(utf8_bytes)

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      {
        "id": "msg1",
        "name": "event",
        "data": base64_data,
        "encoding": "json/utf-8/base64",
        "timestamp": 1234567890000
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
history = AWAIT channel.history()
message = history.items[0]
```

### Assertions
```pseudo
# Should decode: base64 -> utf-8 -> json
ASSERT message.data == { "status": "active", "count": 5 }
ASSERT message.encoding IS null
```

---

## Protocol Selection Tests

### RSL4 - JSON protocol uses correct Content-Type

**Spec requirement:** When `useBinaryProtocol: false`, requests must use `Content-Type: application/json`.

### Setup
```pseudo
channel_name = "test-RSL4-json-ct-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: "test")
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.headers["Content-Type"] == "application/json"
ASSERT request.headers["Accept"] == "application/json"
```

---

### RSL4 - MessagePack protocol uses correct Content-Type

**Spec requirement:** When `useBinaryProtocol: true`, requests must use `Content-Type: application/x-msgpack`.

### Setup
```pseudo
channel_name = "test-RSL4-msgpack-ct-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: true
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: "test")
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.headers["Content-Type"] == "application/x-msgpack"
ASSERT request.headers["Accept"] == "application/x-msgpack"
```

---

## Empty Data Tests

### RSL4 - Empty string encoding

**Spec requirement:** Empty strings must be transmitted as empty strings without encoding.

### Setup
```pseudo
channel_name = "test-RSL4-empty-str-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: "")
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)[0]

ASSERT body["data"] == ""
ASSERT "encoding" NOT IN body OR body["encoding"] IS null
```

---

### RSL4 - Empty array encoding

**Spec requirement:** Empty arrays must be JSON-encoded.

### Setup
```pseudo
channel_name = "test-RSL4-empty-arr-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: [])
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)[0]

ASSERT body["encoding"] == "json"
ASSERT parse_json(body["data"]) == []
```

---

### RSL4 - Empty object encoding

**Spec requirement:** Empty objects must be JSON-encoded.

### Setup
```pseudo
channel_name = "test-RSL4-empty-obj-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: {})
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)[0]

ASSERT body["encoding"] == "json"
ASSERT parse_json(body["data"]) == {}
```
