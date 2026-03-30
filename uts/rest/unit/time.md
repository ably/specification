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

**Spec requirement:** The `/time` endpoint does not require authentication and should not send an Authorization header, even when credentials are available.

Tests that time() does not send authentication credentials, even when the client has them.

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

# Client has credentials, but time() should not use them
client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
result = AWAIT client.time()
```

### Assertions
```pseudo
# Should succeed
ASSERT result IS DateTime

# Request should not have Authorization header even though client has credentials
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT "Authorization" NOT IN request.headers
```

---

## RSC16 - time() works without TLS

**Spec requirement:** The `/time` endpoint does not require authentication, so it should be callable over HTTP (non-TLS) without sending credentials. The RSC18 restriction (no basic auth over non-TLS) does not apply because time() doesn't send authentication.

Tests that time() succeeds over HTTP (non-TLS) without sending credentials.

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

# Client with API key but using token auth to avoid RSC18 restriction
# on authenticated operations. time() should still work over HTTP.
client = Rest(options: ClientOptions(
  key: "app.key:secret",
  tls: false,
  useTokenAuth: true
))
```

### Test Steps
```pseudo
result = AWAIT client.time()
```

### Assertions
```pseudo
# Should succeed without sending authentication over HTTP
ASSERT result IS DateTime

# Request should use HTTP (not HTTPS)
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.url.scheme == "http"

# Request should not have Authorization header
ASSERT "Authorization" NOT IN request.headers
```

### Note
This test verifies that the RSC18 check (which rejects basic auth over non-TLS connections) is only applied to operations that require authentication. The `time()` endpoint is unauthenticated, so it should work regardless of TLS settings. The client constructor still requires credentials, but time() doesn't use them.

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
