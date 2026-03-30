# REST Client Tests

Spec points: `RSC7`, `RSC7b`, `RSC7c`, `RSC7d`, `RSC7e`, `RSC8`, `RSC8a`, `RSC8b`, `RSC8c`, `RSC8d`, `RSC8e`, `RSC13`, `RSC18`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/test/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

---

## RSC7e - X-Ably-Version header

**Spec requirement:** All REST requests must include the `X-Ably-Version` header with the spec version.

Tests that all REST requests include the `X-Ably-Version` header.

### Setup
```pseudo
captured_request = null

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_request = req
    req.respond_with(200, {"time": 1234567890000})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT captured_request IS NOT null
ASSERT "X-Ably-Version" IN captured_request.headers
ASSERT captured_request.headers["X-Ably-Version"] matches pattern "[0-9.]+"
```

---

## RSC7d, RSC7d1, RSC7d2 - Ably-Agent header

| Spec | Requirement |
|------|-------------|
| RSC7d | All requests must include Ably-Agent header |
| RSC7d1 | Header format: space-separated key/value pairs |
| RSC7d2 | Must include library name and version |

Tests that all REST requests include the `Ably-Agent` header with correct format.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT "Ably-Agent" IN request.headers

agent = request.headers["Ably-Agent"]
# Format: key[/value] entries joined by spaces
# Must include at least library name/version
ASSERT agent matches pattern "ably-[a-z]+/[0-9]+\\.[0-9]+\\.[0-9]+"
# May include additional entries like platform info
```

---

## RSC7c - Request ID when addRequestIds enabled

**Spec requirement:** When `addRequestIds` is true, all requests must include a `request_id` query parameter with a unique URL-safe identifier.

Tests that `request_id` query parameter is included when `addRequestIds` is true.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  addRequestIds: true
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT "request_id" IN request.url.query_params

request_id = request.url.query_params["request_id"]
# Should be url-safe base64 encoded, at least 12 characters (9 bytes base64)
ASSERT request_id.length >= 12
ASSERT request_id matches pattern "[A-Za-z0-9_-]+"
```

---

## RSC7c - Request ID preserved on fallback retry

**Spec requirement:** The same `request_id` must be preserved when retrying a failed request to fallback hosts.

Tests that the same `request_id` is used when retrying to a fallback host.

### Setup
```pseudo
mock_http = MockHttpClient()
# First request fails with 500
mock_http.queue_response(500, { "error": { "code": 50000 } })
# Retry succeeds
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  addRequestIds: true
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 2

request_id_1 = mock_http.captured_requests[0].url.query_params["request_id"]
request_id_2 = mock_http.captured_requests[1].url.query_params["request_id"]

ASSERT request_id_1 == request_id_2  # Same ID for retry
```

---

## RSC8a, RSC8b - Protocol selection

| Spec | Requirement |
|------|-------------|
| RSC8a | MessagePack protocol is used by default |
| RSC8b | JSON protocol used when `useBinaryProtocol` is false |

Tests that the correct protocol (MessagePack or JSON) is used based on configuration.

### Setup
```pseudo
mock_http = MockHttpClient()
```

### Test Cases

| ID | useBinaryProtocol | Expected Content-Type |
|----|-------------------|----------------------|
| 1 | `true` (default) | `application/x-msgpack` |
| 2 | `false` | `application/json` |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  mock_http.reset()
  mock_http.queue_response(201, { "serials": ["s1"] })

  client = Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    useBinaryProtocol: test_case.useBinaryProtocol
  ))

  AWAIT client.channels.get("test").publish(name: "e", data: "d")

  request = mock_http.captured_requests[0]
  ASSERT request.headers["Content-Type"] == test_case.expected_content_type
  ASSERT request.headers["Accept"] == test_case.expected_content_type
```

---

## RSC8c - Accept and Content-Type headers

**Spec requirement:** Accept and Content-Type headers must match the configured protocol (application/json or application/x-msgpack).

Tests that Accept and Content-Type headers reflect the configured protocol.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false  # JSON for easier inspection
))
```

### Test Steps
```pseudo
AWAIT client.channels.get("test").publish(name: "e", data: "d")
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT request.headers["Accept"] == "application/json"
ASSERT request.headers["Content-Type"] == "application/json"
```

---

## RSC8d - Handle mismatched response Content-Type

**Spec requirement:** The client must be able to decode responses in either JSON or MessagePack format, regardless of which format was requested.

Tests that responses with different Content-Type than requested are still processed if supported.

### Setup
```pseudo
mock_http = MockHttpClient()
# Client requests JSON but server returns msgpack
mock_http.queue_response(200,
  body: msgpack_encode({ "time": 1234567890000 }),
  headers: { "Content-Type": "application/x-msgpack" }
)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false  # Client prefers JSON
))
```

### Test Steps
```pseudo
result = AWAIT client.time()
```

### Assertions
```pseudo
# Should successfully parse msgpack response despite requesting JSON
ASSERT result IS DateTime OR result == 1234567890000
```

---

## RSC8e - Unsupported Content-Type handling

**Spec requirement:** When the server returns an unsupported Content-Type, the client must raise an error with code 40013 for 2xx responses, or propagate the HTTP status code for error responses.

Tests error handling when server returns unsupported Content-Type.

### Test Cases

| ID | Status Code | Content-Type | Expected Error Code |
|----|-------------|--------------|---------------------|
| 1 | 500 | `text/html` | 500 (status propagated) |
| 2 | 200 | `text/html` | 40013 |

### Setup (Case 1 - Error status)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(500,
  body: "<html>Server Error</html>",
  headers: { "Content-Type": "text/html" }
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps (Case 1)
```pseudo
TRY:
  AWAIT client.time()
  FAIL("Expected exception")
CATCH AblyException as e:
  ASSERT e.statusCode == 500
  ASSERT e.message CONTAINS "unsupported" OR e.message CONTAINS "content"
```

### Setup (Case 2 - Success status but bad content)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200,
  body: "<html>OK</html>",
  headers: { "Content-Type": "text/html" }
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps (Case 2)
```pseudo
TRY:
  AWAIT client.time()
  FAIL("Expected exception")
CATCH AblyException as e:
  ASSERT e.statusCode == 400
  ASSERT e.code == 40013
```

---

## RSC13 - Request timeouts

**Spec requirement:** HTTP requests must respect the `httpRequestTimeout` option and fail with code 50003 when the timeout is exceeded.

Tests that configured timeouts are applied to HTTP requests.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success()
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpRequestTimeout: 1000  # 1 second timeout
))
```

### Test Steps
```pseudo
time_future = client.time()

# Wait for request and respond with delay
request = AWAIT mock_http.await_request()
request.respond_with_delay(5000, 200, {"time": 1234567890000})

TRY:
  AWAIT time_future
  FAIL("Expected timeout exception")
CATCH AblyException as e:
  ASSERT e.code == 50003 OR e.message CONTAINS "timeout"
```

### Note
This test should use timer mocking where available (see Test Infrastructure Notes) to avoid 1+ second test delays.

---

## RSC18 - TLS configuration

**Spec requirement:** The `tls` option controls whether HTTPS (true, default) or HTTP (false) is used for REST requests.

Tests that TLS setting controls protocol used.

### Test Cases

| ID | tls | Expected Scheme |
|----|-----|-----------------|
| 1 | `true` (default) | `https` |
| 2 | `false` | `http` |

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })
```

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  mock_http.reset()
  mock_http.queue_response(200, { "time": 1234567890000 })

  client = Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    tls: test_case.tls
  ))

  AWAIT client.time()

  request = mock_http.captured_requests[0]
  ASSERT request.url.scheme == test_case.expected_scheme
```

---

## RSC18 - Basic auth over HTTP rejected

**Spec requirement:** Basic authentication (API key) must be rejected when `tls` is false. Token authentication is permitted over HTTP. Error code 40103.

Tests that Basic authentication is rejected when TLS is disabled.

### Setup
```pseudo
# No mock needed - should fail before making request
```

### Test Steps
```pseudo
TRY:
  client = Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    tls: false
  ))
  # Attempt any operation that requires auth
  AWAIT client.time()
  FAIL("Expected exception")
CATCH AblyException as e:
  ASSERT e.code == 40103 OR e.message CONTAINS "insecure" OR e.message CONTAINS "TLS"
```

### Note
Token auth over HTTP should be allowed. Only Basic auth (API key) should be rejected.

### Additional Test - Token auth over HTTP allowed
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  token: "some-token-string",
  tls: false
))

result = AWAIT client.time()
# Should succeed - token auth over HTTP is permitted
ASSERT result IS valid
```

---

## Test Infrastructure Notes

See `uts/test/rest/unit/helpers/mock_http.md` for mock installation, test isolation, and timer mocking guidance.
