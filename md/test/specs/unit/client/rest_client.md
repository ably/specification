# REST Client Tests

Spec points: `RSC7`, `RSC7b`, `RSC7c`, `RSC7d`, `RSC7e`, `RSC8`, `RSC8a`, `RSC8b`, `RSC8c`, `RSC8d`, `RSC8e`, `RSC13`, `RSC18`

## Test Type
Unit test with mocked HTTP client

## Mock Configuration

### HTTP Client Mock
Captures outgoing requests and returns configurable responses.

---

## RSC7e - X-Ably-Version header

Tests that all REST requests include the `X-Ably-Version` header.

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
ASSERT "X-Ably-Version" IN request.headers
ASSERT request.headers["X-Ably-Version"] matches pattern "[0-9.]+"
```

---

## RSC7d, RSC7d1, RSC7d2 - Ably-Agent header

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

Tests that configured timeouts are applied to HTTP requests.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_delayed_response(
  delay: 5000,  # 5 second delay
  status: 200,
  body: { "time": 1234567890000 }
)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpRequestTimeout: 1000  # 1 second timeout
))
```

### Test Steps
```pseudo
TRY:
  AWAIT client.time()
  FAIL("Expected timeout exception")
CATCH AblyException as e:
  ASSERT e.code == 50003 OR e.message CONTAINS "timeout"
```

---

## RSC18 - TLS configuration

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
