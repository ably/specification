# REST Client request() Tests

Spec points: `RSC19`, `RSC19b`, `RSC19c`, `RSC19d`, `RSC19e`, `RSC19f`, `RSC19f1`, `HP1`, `HP3`, `HP4`, `HP5`, `HP6`, `HP7`, `HP8`

## Test Type
Unit test with mocked HTTP client

## Overview

The `request()` method provides a generic way to make HTTP requests to Ably endpoints with all built-in library functionality (authentication, paging, fallback hosts, protocol encoding).

## Mock Configuration

### HTTP Client Mock
Captures outgoing requests and returns configurable responses.

---

## RSC19f - Method signature supports required HTTP methods

Tests that the request() method supports GET, POST, PUT, PATCH, and DELETE methods.

### Setup
```pseudo
mock_http = MockHttpClient()
```

### Test Cases

| ID | Method | Path | Expected |
|----|--------|------|----------|
| 1 | GET | /test | Success |
| 2 | POST | /test | Success |
| 3 | PUT | /test | Success |
| 4 | PATCH | /test | Success |
| 5 | DELETE | /test | Success |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  mock_http.reset()
  mock_http.queue_response(200, [])

  client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

  response = AWAIT client.request(test_case.method, test_case.path, version: 3)

  request = mock_http.captured_requests[0]
  ASSERT request.method == test_case.method
  ASSERT request.url.path == test_case.path
```

---

## RSC19f - Query parameters passed correctly

Tests that the params argument adds URL query parameters.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, [])

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
response = AWAIT client.request("GET", "/channels/test/messages",
  version: 3,
  params: { "limit": "10", "direction": "backwards" }
)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT request.url.query_params["limit"] == "10"
ASSERT request.url.query_params["direction"] == "backwards"
```

---

## RSC19f - Custom headers passed correctly

Tests that the headers argument adds custom HTTP headers.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, [])

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
response = AWAIT client.request("GET", "/test",
  version: 3,
  headers: { "X-Custom-Header": "custom-value", "X-Another": "another-value" }
)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT request.headers["X-Custom-Header"] == "custom-value"
ASSERT request.headers["X-Another"] == "another-value"
```

---

## RSC19f - Request body sent correctly

Tests that the body argument is included in the request.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "id": "123" })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false  # JSON for easier inspection
))
```

### Test Steps
```pseudo
response = AWAIT client.request("POST", "/channels/test/messages",
  version: 3,
  body: { "name": "event", "data": "payload" }
)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
body = json_decode(request.body)
ASSERT body["name"] == "event"
ASSERT body["data"] == "payload"
```

---

## RSC19f1 - X-Ably-Version header uses explicit version parameter

Tests that the version parameter sets the X-Ably-Version header.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, [])

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Cases

| ID | Version | Expected Header |
|----|---------|-----------------|
| 1 | 2 | "2" |
| 2 | 3 | "3" |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  mock_http.reset()
  mock_http.queue_response(200, [])

  response = AWAIT client.request("GET", "/test", version: test_case.version)

  request = mock_http.captured_requests[0]
  ASSERT request.headers["X-Ably-Version"] == test_case.expected_header
```

---

## RSC19b - Uses configured authentication

Tests that request() uses the REST client's configured authentication mechanism.

### Test Case 1: Basic authentication (API key)

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, [])

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
response = AWAIT client.request("GET", "/test", version: 3)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT "Authorization" IN request.headers
ASSERT request.headers["Authorization"] STARTS_WITH "Basic "

# Verify the base64 encoded credentials
credentials = base64_decode(request.headers["Authorization"].substring(6))
ASSERT credentials == "appId.keyId:keySecret"
```

### Test Case 2: Token authentication

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, [])

client = Rest(options: ClientOptions(token: "my-token-string"))
```

### Test Steps
```pseudo
response = AWAIT client.request("GET", "/test", version: 3)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT "Authorization" IN request.headers
ASSERT request.headers["Authorization"] STARTS_WITH "Bearer "
```

---

## RSC19c - Protocol headers set correctly (JSON)

Tests that Accept and Content-Type headers reflect the configured protocol.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, [])

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false  # JSON
))
```

### Test Steps
```pseudo
response = AWAIT client.request("POST", "/test",
  version: 3,
  body: { "data": "test" }
)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT request.headers["Accept"] == "application/json"
ASSERT request.headers["Content-Type"] == "application/json"
```

---

## RSC19c - Protocol headers set correctly (MsgPack)

Tests that Accept and Content-Type headers reflect MsgPack protocol when configured.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, msgpack_encode([]))

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: true  # MsgPack
))
```

### Test Steps
```pseudo
response = AWAIT client.request("POST", "/test",
  version: 3,
  body: { "data": "test" }
)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT request.headers["Accept"] == "application/x-msgpack"
ASSERT request.headers["Content-Type"] == "application/x-msgpack"
```

---

## RSC19c - Request body encoded according to protocol

Tests that the request body is encoded using the configured protocol.

### Test Case 1: JSON encoding

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, [])

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: false
))
```

### Test Steps
```pseudo
response = AWAIT client.request("POST", "/test",
  version: 3,
  body: { "name": "event", "data": { "nested": "value" } }
)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
# Body should be valid JSON
body = json_decode(request.body)
ASSERT body["name"] == "event"
ASSERT body["data"]["nested"] == "value"
```

### Test Case 2: MsgPack encoding

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, msgpack_encode([]))

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  useBinaryProtocol: true
))
```

### Test Steps
```pseudo
response = AWAIT client.request("POST", "/test",
  version: 3,
  body: { "name": "event", "data": "value" }
)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
# Body should be valid MsgPack
body = msgpack_decode(request.body)
ASSERT body["name"] == "event"
ASSERT body["data"] == "value"
```

---

## RSC19c - Response body decoded according to Content-Type

Tests that the response body is automatically decoded based on Content-Type header.

### Test Case 1: JSON response

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200,
  body: json_encode([{ "id": "1", "name": "item1" }, { "id": "2", "name": "item2" }]),
  headers: { "Content-Type": "application/json" }
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
response = AWAIT client.request("GET", "/test", version: 3)
items = response.items()
```

### Assertions
```pseudo
ASSERT items.length == 2
ASSERT items[0]["id"] == "1"
ASSERT items[1]["name"] == "item2"
```

### Test Case 2: MsgPack response

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200,
  body: msgpack_encode([{ "id": "1" }]),
  headers: { "Content-Type": "application/x-msgpack" }
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
response = AWAIT client.request("GET", "/test", version: 3)
items = response.items()
```

### Assertions
```pseudo
ASSERT items.length == 1
ASSERT items[0]["id"] == "1"
```

---

## RSC19d, HP4 - HttpPaginatedResponse provides status code

Tests that the response object provides access to the HTTP status code.

### Setup
```pseudo
mock_http = MockHttpClient()
```

### Test Cases

| ID | Status Code |
|----|-------------|
| 1 | 200 |
| 2 | 201 |
| 3 | 400 |
| 4 | 404 |
| 5 | 500 |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  mock_http.reset()

  IF test_case.status_code >= 400:
    mock_http.queue_response(test_case.status_code,
      { "error": { "code": test_case.status_code * 100, "message": "Error" } })
  ELSE:
    mock_http.queue_response(test_case.status_code, [])

  client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
  response = AWAIT client.request("GET", "/test", version: 3)

  ASSERT response.statusCode == test_case.status_code
```

---

## RSC19d, HP5 - HttpPaginatedResponse provides success indicator

Tests that the success property correctly reflects 2xx status codes.

### Setup
```pseudo
mock_http = MockHttpClient()
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Cases

| ID | Status Code | Expected Success |
|----|-------------|------------------|
| 1 | 200 | true |
| 2 | 201 | true |
| 3 | 204 | true |
| 4 | 299 | true |
| 5 | 300 | false |
| 6 | 400 | false |
| 7 | 500 | false |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  mock_http.reset()

  IF test_case.status_code >= 400:
    mock_http.queue_response(test_case.status_code,
      { "error": { "code": test_case.status_code * 100, "message": "Error" } })
  ELSE:
    mock_http.queue_response(test_case.status_code, [])

  response = AWAIT client.request("GET", "/test", version: 3)

  ASSERT response.success == test_case.expected_success
```

---

## RSC19d, HP6 - HttpPaginatedResponse provides error code from header

Tests that the errorCode property extracts the value from X-Ably-Errorcode header.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(401,
  body: { "error": { "code": 40101, "message": "Unauthorized" } },
  headers: { "X-Ably-Errorcode": "40101" }
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
response = AWAIT client.request("GET", "/test", version: 3)
```

### Assertions
```pseudo
ASSERT response.errorCode == 40101
```

---

## RSC19d, HP7 - HttpPaginatedResponse provides error message from header

Tests that the errorMessage property extracts the value from X-Ably-Errormessage header.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(401,
  body: { "error": { "code": 40101, "message": "Unauthorized" } },
  headers: {
    "X-Ably-Errorcode": "40101",
    "X-Ably-Errormessage": "Token expired"
  }
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
response = AWAIT client.request("GET", "/test", version: 3)
```

### Assertions
```pseudo
ASSERT response.errorMessage == "Token expired"
```

---

## RSC19d, HP8 - HttpPaginatedResponse provides all response headers

Tests that all response headers are accessible.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200,
  body: [],
  headers: {
    "Content-Type": "application/json",
    "X-Request-Id": "req-123",
    "X-Custom-Header": "custom-value"
  }
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
response = AWAIT client.request("GET", "/test", version: 3)
```

### Assertions
```pseudo
headers = response.headers
ASSERT headers["Content-Type"] == "application/json"
ASSERT headers["X-Request-Id"] == "req-123"
ASSERT headers["X-Custom-Header"] == "custom-value"
```

---

## RSC19d, HP3 - HttpPaginatedResponse provides response items

Tests that the items() method returns the decoded response body.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, [
  { "id": "msg1", "name": "event1", "data": "data1" },
  { "id": "msg2", "name": "event2", "data": "data2" }
])

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
response = AWAIT client.request("GET", "/channels/test/messages", version: 3)
items = response.items()
```

### Assertions
```pseudo
ASSERT items.length == 2
ASSERT items[0]["id"] == "msg1"
ASSERT items[1]["id"] == "msg2"
```

---

## RSC19d, HP1 - HttpPaginatedResponse pagination support

Tests that multi-page responses can be navigated using next().

### Setup
```pseudo
mock_http = MockHttpClient()

# First page
mock_http.queue_response(200,
  body: [{ "id": "1" }, { "id": "2" }],
  headers: {
    "Link": '</channels/test/messages?page=2>; rel="next"'
  }
)

# Second page
mock_http.queue_response(200,
  body: [{ "id": "3" }],
  headers: {}  # No "next" link - last page
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
response = AWAIT client.request("GET", "/channels/test/messages", version: 3)
```

### Assertions
```pseudo
# First page
items1 = response.items()
ASSERT items1.length == 2
ASSERT response.hasNext() == true

# Navigate to second page
response = AWAIT response.next()
items2 = response.items()
ASSERT items2.length == 1
ASSERT items2[0]["id"] == "3"
ASSERT response.hasNext() == false
```

---

## RSC19d - Non-array response handling

Tests that non-array responses are handled correctly (wrapped as single item).

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
response = AWAIT client.request("GET", "/time", version: 3)
items = response.items()
```

### Assertions
```pseudo
# Non-array response should be accessible
ASSERT items.length == 1 OR items["time"] == 1234567890000
# Implementation may vary - either wrap in array or return object directly
```

---

## RSC19e - Network error handling

Tests that network errors are properly propagated after fallback attempts.

### Setup
```pseudo
mock_http = MockHttpClient()
# Simulate network failure
mock_http.queue_network_error("connection refused")

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  fallbackHosts: []  # Disable fallback for this test
))
```

### Test Steps
```pseudo
TRY:
  response = AWAIT client.request("GET", "/test", version: 3)
  FAIL("Expected exception")
CATCH AblyException as e:
  ASSERT e.code == 80000 OR e.message CONTAINS "network" OR e.message CONTAINS "connection"
```

---

## RSC19e - Timeout error handling

Tests that request timeouts are properly handled.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_delayed_response(
  delay: 5000,  # 5 second delay
  status: 200,
  body: []
)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpRequestTimeout: 1000,  # 1 second timeout
  fallbackHosts: []  # Disable fallback
))
```

### Test Steps
```pseudo
TRY:
  response = AWAIT client.request("GET", "/test", version: 3)
  FAIL("Expected timeout exception")
CATCH AblyException as e:
  ASSERT e.code == 50003 OR e.message CONTAINS "timeout"
```

---

## RSC19e - HTTP error status does not trigger fallback

Tests that HTTP error responses (4xx, 5xx with valid Ably error body) are returned directly without fallback retry.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(400,
  body: { "error": { "code": 40000, "message": "Bad request" } },
  headers: { "X-Ably-Errorcode": "40000" }
)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  fallbackHosts: ["a.ably-realtime.com", "b.ably-realtime.com"]
))
```

### Test Steps
```pseudo
response = AWAIT client.request("GET", "/test", version: 3)
```

### Assertions
```pseudo
# Should return the error response, not retry to fallback
ASSERT response.statusCode == 400
ASSERT response.success == false
ASSERT response.errorCode == 40000

# Only one request should have been made (no fallback)
ASSERT mock_http.captured_requests.length == 1
```

---

## RSC19e, RSC15 - Fallback hosts tried on server errors

Tests that fallback hosts are attempted when primary host returns server error without valid Ably error.

### Setup
```pseudo
mock_http = MockHttpClient()

# Primary host fails with non-Ably 500 error
mock_http.queue_response(500,
  body: "Internal Server Error",
  headers: { "Content-Type": "text/plain" }
)

# Fallback succeeds
mock_http.queue_response(200, [{ "id": "1" }])

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  fallbackHosts: ["fallback.ably-realtime.com"]
))
```

### Test Steps
```pseudo
response = AWAIT client.request("GET", "/test", version: 3)
```

### Assertions
```pseudo
ASSERT response.statusCode == 200
ASSERT response.success == true

# Two requests: primary failed, fallback succeeded
ASSERT mock_http.captured_requests.length == 2
ASSERT mock_http.captured_requests[1].url.host == "fallback.ably-realtime.com"
```

---

## RSC19b - Cannot override authentication

Tests that the request() method does not allow overriding the configured authentication via custom headers.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, [])

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Attempt to override auth with custom header
response = AWAIT client.request("GET", "/test",
  version: 3,
  headers: { "Authorization": "Bearer malicious-token" }
)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]

# The configured Basic auth should be used, not the custom header
ASSERT request.headers["Authorization"] STARTS_WITH "Basic "
# Should NOT contain the attempted override
ASSERT request.headers["Authorization"] != "Bearer malicious-token"
```

### Note
This behavior may vary by implementation. Some libraries may allow header override while others enforce configured auth. The spec states authentication is "unconditional" per RSC19b.

---

## RSC19f - Path with leading slash

Tests that paths are handled correctly whether or not they include a leading slash.

### Setup
```pseudo
mock_http = MockHttpClient()
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Cases

| ID | Path | Expected Path in Request |
|----|------|--------------------------|
| 1 | "/channels/test" | "/channels/test" |
| 2 | "channels/test" | "/channels/test" |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  mock_http.reset()
  mock_http.queue_response(200, [])

  response = AWAIT client.request("GET", test_case.path, version: 3)

  request = mock_http.captured_requests[0]
  ASSERT request.url.path == test_case.expected_path
```

---

## RSC19d - Empty response handling

Tests that empty responses (204 No Content) are handled correctly.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(204,
  body: null,  # No body
  headers: {}
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
response = AWAIT client.request("DELETE", "/channels/test/messages/123", version: 3)
```

### Assertions
```pseudo
ASSERT response.statusCode == 204
ASSERT response.success == true
items = response.items()
ASSERT items IS null OR items.length == 0
```
