# Request Endpoint Tests

Spec points: `RSC25`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/test/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

---

## RSC25 - Requests sent to primary domain first

**Spec requirement:** Requests are sent to the `primary domain` as determined by `REC1`. New HTTP requests (except where `RSC15f` applies and a cached fallback host is in effect) are first attempted against the `primary domain`.

### RSC25 - Default primary domain used for requests

Tests that REST requests are sent to the default primary domain when no endpoint configuration is provided.

#### Setup
```pseudo
mock_http = MockHttpClient(
  onRequest: (req) => {
    req.respond_with(200, {"time": 1234567890000})
  }
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

#### Test Steps
```pseudo
AWAIT client.time()
```

#### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 1
ASSERT mock_http.captured_requests[0].url.host == DEFAULT_REST_HOST
```

---

### RSC25 - Custom endpoint used for requests

Tests that REST requests are sent to a custom production routing policy domain.

#### Setup
```pseudo
mock_http = MockHttpClient(
  onRequest: (req) => {
    req.respond_with(200, {"time": 1234567890000})
  }
)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "sandbox"
))
```

#### Test Steps
```pseudo
AWAIT client.time()
```

#### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 1
ASSERT mock_http.captured_requests[0].url.host == "sandbox.realtime.ably.net"
```

---

### RSC25 - Multiple requests all go to primary domain

Tests that successive requests continue to use the primary domain (no unexpected host switching).

#### Setup
```pseudo
mock_http = MockHttpClient(
  onRequest: (req) => {
    req.respond_with(200, {"time": 1234567890000})
  }
)

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
ASSERT mock_http.captured_requests.length == 3
FOR EACH request IN mock_http.captured_requests:
  ASSERT request.url.host == DEFAULT_REST_HOST
```

---

### RSC25 - Primary domain tried first before fallback

Tests that when the primary host fails and a fallback succeeds, the primary was attempted first.

#### Setup
```pseudo
request_count = 0

mock_http = MockHttpClient(
  onRequest: (req) => {
    request_count++
    IF request_count == 1:
      req.respond_with(500, {"error": {"code": 50000}})
    ELSE:
      req.respond_with(200, {"time": 1234567890000})
  }
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

#### Test Steps
```pseudo
AWAIT client.time()
```

#### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 2
# First request was to primary domain
ASSERT mock_http.captured_requests[0].url.host == DEFAULT_REST_HOST
# Second request was to a fallback domain (not primary)
ASSERT mock_http.captured_requests[1].url.host != DEFAULT_REST_HOST
```

---

### RSC25 - Request path preserved when sent to primary domain

Tests that the request path and query parameters are correctly constructed when sent to the primary domain.

#### Setup
```pseudo
mock_http = MockHttpClient(
  onRequest: (req) => {
    req.respond_with(200, [])
  }
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

#### Test Steps
```pseudo
AWAIT client.channels.get("test-channel").history()
```

#### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 1
request = mock_http.captured_requests[0]
ASSERT request.url.host == DEFAULT_REST_HOST
ASSERT request.url.path == "/channels/test-channel/messages"
ASSERT request.method == "GET"
```
