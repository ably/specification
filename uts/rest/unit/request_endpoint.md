# Request Endpoint Tests

Spec points: `RSC25`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

---

## RSC25 - Requests sent to primary domain first

**Spec requirement:** Requests are sent to the `primary domain` as determined by `REC1`. New HTTP requests (except where `RSC15f` applies and a cached fallback host is in effect) are first attempted against the `primary domain`.

### RSC25 - Default primary domain used for requests

**Test ID**: `rest/unit/RSC25/default-primary-domain-0`

Tests that REST requests are sent to the default primary domain when no endpoint configuration is provided.

#### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [1234567890000])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

#### Test Steps
```pseudo
AWAIT client.time()
```

#### Assertions
```pseudo
ASSERT captured_requests.length == 1
ASSERT captured_requests[0].url.host == DEFAULT_REST_HOST
```

---

### RSC25 - Custom endpoint used for requests

**Test ID**: `rest/unit/RSC25/custom-endpoint-domain-1`

Tests that REST requests are sent to a custom production routing policy domain.

#### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [1234567890000])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "test"
))
```

#### Test Steps
```pseudo
AWAIT client.time()
```

#### Assertions
```pseudo
ASSERT captured_requests.length == 1
ASSERT captured_requests[0].url.host == "test.realtime.ably.net"
```

---

### RSC25 - Multiple requests all go to primary domain

**Test ID**: `rest/unit/RSC25/multiple-requests-primary-domain-2`

Tests that successive requests continue to use the primary domain (no unexpected host switching).

#### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [1234567890000])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

#### Test Steps
```pseudo
AWAIT client.time()
AWAIT client.time()
AWAIT client.time()
```

#### Assertions
```pseudo
ASSERT captured_requests.length == 3
FOR EACH request IN captured_requests:
  ASSERT request.url.host == DEFAULT_REST_HOST
```

---

### RSC25 - Primary domain tried first before fallback

**Test ID**: `rest/unit/RSC25/primary-tried-before-fallback-3`

Tests that when the primary host fails and a fallback succeeds, the primary was attempted first.

#### Setup
```pseudo
request_count = 0
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    request_count++
    IF request_count == 1:
      req.respond_with(500, {"error": {"message": "Internal error", "code": 50000, "statusCode": 500}})
    ELSE:
      req.respond_with(200, [1234567890000])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

#### Test Steps
```pseudo
AWAIT client.time()
```

#### Assertions
```pseudo
ASSERT captured_requests.length == 2
# First request was to primary domain
ASSERT captured_requests[0].url.host == DEFAULT_REST_HOST
# Second request was to a fallback domain (not primary)
ASSERT captured_requests[1].url.host != DEFAULT_REST_HOST
```

---

### RSC25 - Request path preserved when sent to primary domain

**Test ID**: `rest/unit/RSC25/request-path-preserved-4`

Tests that the request path and query parameters are correctly constructed when sent to the primary domain.

#### Setup
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
```

#### Test Steps
```pseudo
AWAIT client.channels.get("test-channel").history()
```

#### Assertions
```pseudo
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.url.host == DEFAULT_REST_HOST
ASSERT request.url.path == "/channels/test-channel/messages"
ASSERT request.method == "GET"
```
