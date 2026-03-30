# REST Channel History Tests

Spec points: `RSL2`, `RSL2a`, `RSL2b`, `RSL2b1`, `RSL2b2`, `RSL2b3`

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

## RSL2a - History returns PaginatedResult

**Spec requirement:** The `history()` method must return a `PaginatedResult` object containing an array of `Message` objects.

Tests that `history()` returns a `PaginatedResult` containing messages.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      { "id": "msg1", "name": "event1", "data": "data1", "timestamp": 1000 },
      { "id": "msg2", "name": "event2", "data": "data2", "timestamp": 2000 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
result = AWAIT channel.history()
```

### Assertions
```pseudo
ASSERT result IS PaginatedResult
ASSERT result.items IS List
ASSERT result.items.length == 2

ASSERT result.items[0] IS Message
ASSERT result.items[0].id == "msg1"
ASSERT result.items[0].name == "event1"
ASSERT result.items[0].data == "data1"
```

---

## RSL2b - History query parameters

**Spec requirement:** History method parameters (start, end, direction, limit) must be encoded as query string parameters in the HTTP request.

Tests that history parameters are correctly sent as query string.

### Setup
```pseudo
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
channel = client.channels.get("test-channel")
```

### Test Cases

| ID | Parameter | Value | Expected Query |
|----|-----------|-------|----------------|
| 1 | start | `1234567890000` | `start=1234567890000` |
| 2 | end | `1234567899999` | `end=1234567899999` |
| 3 | direction | `"backwards"` | `direction=backwards` |
| 4 | direction | `"forwards"` | `direction=forwards` |
| 5 | limit | `50` | `limit=50` |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  captured_requests = []

  params = {}
  params[test_case.parameter] = test_case.value

  AWAIT channel.history(params)

  request = captured_requests[0]
  ASSERT request.url.query_params[test_case.parameter] == str(test_case.value)
```

---

## RSL2b1 - Default direction is backwards

**Spec requirement:** When the direction parameter is not specified, the default direction for history queries must be backwards (newest messages first).

Tests that the default direction for history is backwards (newest first).

### Setup
```pseudo
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
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
AWAIT channel.history()  # No direction specified
```

### Assertions
```pseudo
request = captured_requests[0]

# Either direction param is absent (server default) or explicitly "backwards"
IF "direction" IN request.url.query_params:
  ASSERT request.url.query_params["direction"] == "backwards"
# If absent, server defaults to backwards per spec
```

---

## RSL2b2 - Limit parameter

**Spec requirement:** The limit parameter must control the maximum number of messages returned in a single history query.

Tests that limit parameter restricts the number of returned items.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      { "id": "msg1", "name": "e", "data": "d", "timestamp": 1000 },
      { "id": "msg2", "name": "e", "data": "d", "timestamp": 2000 },
      { "id": "msg3", "name": "e", "data": "d", "timestamp": 3000 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
AWAIT channel.history(limit: 10)

request = captured_requests[0]
ASSERT request.url.query_params["limit"] == "10"
```

---

## RSL2b3 - Default limit is 100

**Spec requirement:** When the limit parameter is not specified, the default limit must be 100 messages.

Tests that the default limit is 100 when not specified.

### Setup
```pseudo
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
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
AWAIT channel.history()  # No limit specified
```

### Assertions
```pseudo
request = captured_requests[0]

# Either limit param is absent (server default) or explicitly "100"
IF "limit" IN request.url.query_params:
  ASSERT request.url.query_params["limit"] == "100"
# If absent, server defaults to 100 per spec
```

---

## RSL2 - History request URL format

**Spec requirement:** History requests must use the URL path `/channels/<channel_name>/messages` with proper URL encoding of the channel name.

Tests that history requests use the correct URL path.

### Setup
```pseudo
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    request_count = request_count + 1
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Cases

| ID | Channel Name | Expected Path |
|----|--------------|---------------|
| 1 | `"simple"` | `/channels/simple/messages` |
| 2 | `"with:colon"` | `/channels/with%3Acolon/messages` |
| 3 | `"with/slash"` | `/channels/with%2Fslash/messages` |
| 4 | `"with space"` | `/channels/with%20space/messages` |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  captured_requests = []
  request_count = 0

  channel = client.channels.get(test_case.channel_name)
  AWAIT channel.history()

  ASSERT request_count == 1
  request = captured_requests[0]
  ASSERT request.method == "GET"
  ASSERT request.url.path == test_case.expected_path
```

---

## RSL2 - History with time range

**Spec requirement:** History queries must support start and end time parameters to retrieve messages within a specific time window.

Tests combining start and end parameters for time-bounded queries.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      { "id": "msg1", "name": "e", "data": "d", "timestamp": 1500 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
AWAIT channel.history(
  start: 1000,
  end: 2000
)
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.url.query_params["start"] == "1000"
ASSERT request.url.query_params["end"] == "2000"
```
