# Time API Tests

Spec points: `RSC16`

## Test Type
Unit test with mocked HTTP

## Purpose

Tests the `time()` method which retrieves the current server time from Ably.

**Note:** The `time()` endpoint does NOT require authentication. Do not use it for testing authentication - use the channel status endpoint instead.

---

## RSC16 - time() returns server time

Tests that `time()` returns the server time as a DateTime/timestamp.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "app.key:secret"),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
# Server returns array with single timestamp (milliseconds since epoch)
server_time_ms = 1704067200000  # 2024-01-01 00:00:00 UTC
mock_http.queue_response(200, [server_time_ms])

result = AWAIT client.time()
```

### Assertions
```pseudo
# Result should be a DateTime matching the server timestamp
ASSERT result IS DateTime
ASSERT result.millisecondsSinceEpoch == server_time_ms

# Verify correct endpoint was called
request = mock_http.captured_requests[0]
ASSERT request.method == "GET"
ASSERT request.path == "/time"
```

---

## RSC16 - time() request format

Tests that the time request is correctly formatted.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "app.key:secret"),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response(200, [1704067200000])
AWAIT client.time()
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]

# Should be GET request to /time
ASSERT request.method == "GET"
ASSERT request.path == "/time"

# Should have standard Ably headers
ASSERT "X-Ably-Version" IN request.headers
ASSERT "Ably-Agent" IN request.headers
```

---

## RSC16 - time() does not require authentication

Tests that time() works without authentication credentials.

### Setup
```pseudo
mock_http = MockHttpClient()

# Client with no authentication
client = Rest(
  options: ClientOptions(),  # No key or token
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response(200, [1704067200000])
result = AWAIT client.time()
```

### Assertions
```pseudo
# Should succeed without authentication
ASSERT result IS DateTime

# Request should not have Authorization header
request = mock_http.captured_requests[0]
ASSERT "Authorization" NOT IN request.headers
```

---

## RSC16 - time() error handling

Tests that errors from the time endpoint are properly propagated.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "app.key:secret"),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response(500, {
  "error": {
    "message": "Internal server error",
    "code": 50000,
    "statusCode": 500
  }
})

TRY:
  AWAIT client.time()
  FAIL("Expected exception")
CATCH AblyException as e:
  ASSERT e.statusCode == 500
  ASSERT e.code == 50000
```
