# Idempotent Publishing Tests

Spec points: `RSL1k`, `RSL1k1`, `RSL1k2`, `RSL1k3`, `RSL1k4`, `RSL1k5`

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

## RSL1k1 - idempotentRestPublishing default

**Spec requirement:** The `idempotentRestPublishing` client option must default to `true` for library versions >= 1.2.

Tests the default value of `idempotentRestPublishing` option.

### Test Cases

| ID | Library Version | Expected Default |
|----|-----------------|------------------|
| 1 | >= 1.2 | `true` |

### Test Steps
```pseudo
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# Verify default value
ASSERT client.options.idempotentRestPublishing == true
```

---

## RSL1k2 - Message ID format when idempotent publishing enabled

**Spec requirement:** When `idempotentRestPublishing` is enabled, library-generated message IDs must follow the format `<base64>:<serial>` where base64 is a URL-safe base64-encoded random value and serial is a zero-based sequential integer.

Tests that library-generated message IDs follow the `<base64>:<serial>` format.

### Setup
```pseudo
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
  idempotentRestPublishing: true
))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: "data")
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)[0]

ASSERT "id" IN body
message_id = body["id"]

# Format: <base64>:<serial>
parts = message_id.split(":")
ASSERT parts.length == 2

# First part is base64-encoded (url-safe)
ASSERT parts[0] matches pattern "[A-Za-z0-9_-]+"
ASSERT parts[0].length >= 12  # At least 9 bytes base64 encoded

# Second part is a serial number (starting from 0)
ASSERT parts[1] == "0"
```

---

## RSL1k2 - Serial increments for batch publish

**Spec requirement:** When publishing multiple messages in a batch, all messages must share the same base ID with incrementing serial numbers starting from 0.

Tests that serial numbers increment for each message in a batch.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, { "serials": ["s1", "s2", "s3"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  idempotentRestPublishing: true
))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
messages = [
  Message(name: "event1", data: "data1"),
  Message(name: "event2", data: "data2"),
  Message(name: "event3", data: "data3")
]
AWAIT channel.publish(messages: messages)
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)

# All messages should share the same base but different serials
base_ids = []
serials = []

FOR i, msg IN enumerate(body):
  parts = msg["id"].split(":")
  base_ids.append(parts[0])
  serials.append(int(parts[1]))

# Same base for all messages in batch
ASSERT ALL base == base_ids[0] FOR base IN base_ids

# Sequential serials starting from 0
ASSERT serials == [0, 1, 2]
```

---

## RSL1k3 - Separate publishes get unique base IDs

**Spec requirement:** Each separate publish call must generate a new unique base ID, even for messages published to the same channel.

Tests that separate publish calls generate unique base IDs.

### Setup
```pseudo
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
  idempotentRestPublishing: true
))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event1", data: "data1")
AWAIT channel.publish(name: "event2", data: "data2")
```

### Assertions
```pseudo
body1 = parse_json(captured_requests[0].body)[0]
body2 = parse_json(captured_requests[1].body)[0]

base1 = body1["id"].split(":")[0]
base2 = body2["id"].split(":")[0]

# Different publish calls should have different base IDs
ASSERT base1 != base2
```

---

## RSL1k3 - No ID generated when idempotent publishing disabled

**Spec requirement:** When `idempotentRestPublishing` is false, the library must not automatically generate message IDs.

Tests that message IDs are not automatically generated when disabled.

### Setup
```pseudo
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
  idempotentRestPublishing: false
))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: "data")
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)[0]

# No automatic ID should be added
ASSERT "id" NOT IN body
```

---

## RSL1k - Client-supplied ID preserved

**Spec requirement:** Client-supplied message IDs must be preserved and transmitted exactly as provided, even when `idempotentRestPublishing` is enabled.

Tests that client-supplied message IDs are not overwritten.

### Setup
```pseudo
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
  idempotentRestPublishing: true  # Even with this enabled
))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
AWAIT channel.publish(
  message: Message(id: "my-custom-id", name: "event", data: "data")
)
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)[0]

# Client-supplied ID should be preserved exactly
ASSERT body["id"] == "my-custom-id"
```

---

## RSL1k2 - Same ID used on retry

**Spec requirement:** When a publish request is retried after a failure, the same message ID(s) must be used to ensure idempotent behavior.

Tests that the same message ID is used when retrying after failure.

### Setup
```pseudo
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    request_count = request_count + 1
    
    # First request fails with retryable error
    IF request_count == 1:
      req.respond_with(500, { "error": { "code": 50000 } })
    ELSE:
      # Retry succeeds
      req.respond_with(201, { "serials": ["s1"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  idempotentRestPublishing: true
))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
AWAIT channel.publish(name: "event", data: "data")
```

### Assertions
```pseudo
ASSERT request_count == 2

body1 = parse_json(captured_requests[0].body)[0]
body2 = parse_json(captured_requests[1].body)[0]

# Same ID should be used for retry
ASSERT body1["id"] == body2["id"]
```

---

## RSL1k - Mixed client and library IDs in batch

**Spec requirement:** In a batch publish, messages with client-supplied IDs must be preserved, while messages without IDs receive library-generated IDs using the standard format.

Tests batch publishing with some messages having client IDs and some not.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, { "serials": ["s1", "s2", "s3"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  idempotentRestPublishing: true
))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
messages = [
  Message(id: "client-id-1", name: "event1", data: "data1"),
  Message(name: "event2", data: "data2"),  # No ID - should be generated
  Message(id: "client-id-2", name: "event3", data: "data3")
]
AWAIT channel.publish(messages: messages)
```

### Assertions
```pseudo
request = captured_requests[0]
body = parse_json(request.body)

# Client IDs preserved
ASSERT body[0]["id"] == "client-id-1"
ASSERT body[2]["id"] == "client-id-2"

# Library-generated ID for middle message
ASSERT body[1]["id"] matches pattern "[A-Za-z0-9_-]+:[0-9]+"
```
