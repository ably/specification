# Time API Tests

Spec points: `RSC16`

## Test Type
Unit test with mocked HTTP client

## Mock Configuration

These tests use the mock HTTP infrastructure defined in `rest_client.md`. The mock supports:
- Handler-based configuration with `onConnectionAttempt` and `onRequest`
- Capturing requests via `captured_requests` arrays
- Configurable responses with status codes, bodies, and headers

See `rest_client.md` for detailed mock interface documentation.

## Purpose

Tests the `time()` method which retrieves the current server time from Ably.

**Note:** The `time()` endpoint does NOT require authentication. Do not use it for testing authentication - use the channel status endpoint instead.

---

## RSC16 - time() returns server time

**Spec requirement:** The `time()` method retrieves the server time from the `/time` endpoint and returns it as a DateTime or timestamp.

Tests that `time()` returns the server time as a DateTime/timestamp.

### Setup
```pseudo
captured_requests = []
server_time_ms = 1704067200000  # 2024-01-01 00:00:00 UTC

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [server_time_ms])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
result = AWAIT client.time()
```

### Assertions
```pseudo
# Result should be a DateTime matching the server timestamp
ASSERT result IS DateTime
ASSERT result.millisecondsSinceEpoch == server_time_ms

# Verify correct endpoint was called
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.method == "GET"
ASSERT request.path == "/time"
```

---

## RSC16 - time() request format

**Spec requirement:** The time request must be a GET request to `/time` with standard Ably headers.

Tests that the time request is correctly formatted.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [1704067200000])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
request = captured_requests[0]

# Should be GET request to /time
ASSERT request.method == "GET"
ASSERT request.path == "/time"

# Should have standard Ably headers
ASSERT "X-Ably-Version" IN request.headers
ASSERT "Ably-Agent" IN request.headers
```

---

## RSC16 - time() does not require authentication

**Spec requirement:** The `/time` endpoint does not require authentication and should succeed without credentials.

Tests that time() works without authentication credentials.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [1704067200000])
  }
)
install_mock(mock_http)

# Client with no authentication
client = Rest(options: ClientOptions())  # No key or token
```

### Test Steps
```pseudo
result = AWAIT client.time()
```

### Assertions
```pseudo
# Should succeed without authentication
ASSERT result IS DateTime

# Request should not have Authorization header
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT "Authorization" NOT IN request.headers
```

---

## RSC16 - time() error handling

**Spec requirement:** Errors from the `/time` endpoint should be properly propagated to the caller.

Tests that errors from the time endpoint are properly propagated.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(500, {
      "error": {
        "message": "Internal server error",
        "code": 50000,
        "statusCode": 500
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
TRY:
  AWAIT client.time()
  FAIL("Expected exception")
CATCH AblyException as e:
  ASSERT e.statusCode == 500
  ASSERT e.code == 50000
```
