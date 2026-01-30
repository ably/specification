# Auth Callback Tests

Spec points: `RSA8c`, `RSA8d`

## Test Type
Unit test with mocked HTTP

## Purpose

These tests verify that the library correctly invokes `authCallback` and `authUrl` to obtain tokens for authentication. The authCallback/authUrl can return:
- A `TokenDetails` object (containing token, expires, etc.)
- A `TokenRequest` object (which the library exchanges for a token)
- A JWT string (raw token string)

---

## RSA8d - authCallback invoked for authentication

Tests that when `authCallback` is configured, it is invoked to obtain a token.

### Setup
```pseudo
mock_http = MockHttpClient()
callback_invoked = false
callback_params = null

auth_callback = FUNCTION(params):
  callback_invoked = true
  callback_params = params
  RETURN TokenDetails(
    token: "callback-token",
    expires: now() + 3600000
  )

client = Rest(
  options: ClientOptions(authCallback: auth_callback),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
# Queue success response for authenticated request
mock_http.queue_response(200, {"channelId": "test"})

# Make a request that requires authentication
result = AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# authCallback was invoked
ASSERT callback_invoked == true

# Request used the token from authCallback
ASSERT mock_http.captured_requests.length == 1
ASSERT mock_http.captured_requests[0].headers["Authorization"] == "Bearer callback-token"
```

---

## RSA8d - authCallback returning JWT string

Tests that authCallback can return a raw JWT string (not wrapped in TokenDetails).

### Setup
```pseudo
mock_http = MockHttpClient()

auth_callback = FUNCTION(params):
  # Return raw JWT string instead of TokenDetails
  RETURN "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-jwt-payload"

client = Rest(
  options: ClientOptions(authCallback: auth_callback),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response(200, {"channelId": "test"})
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# Request used the JWT from authCallback
ASSERT mock_http.captured_requests[0].headers["Authorization"] == "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-jwt-payload"
```

---

## RSA8d - authCallback returning TokenRequest

Tests that when authCallback returns a TokenRequest, the library exchanges it for a token.

### Setup
```pseudo
mock_http = MockHttpClient()

auth_callback = FUNCTION(params):
  # Return a TokenRequest (to be exchanged for token)
  RETURN TokenRequest(
    keyName: "app.key",
    ttl: 3600000,
    timestamp: now(),
    nonce: "unique-nonce",
    mac: "computed-mac"
  )

client = Rest(
  options: ClientOptions(authCallback: auth_callback),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
# First request exchanges TokenRequest for TokenDetails
mock_http.queue_response(200, {
  "token": "exchanged-token",
  "expires": now() + 3600000
})
# Second request is the actual API call
mock_http.queue_response(200, {"channelId": "test"})

AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# Two HTTP requests: token exchange + API call
ASSERT mock_http.captured_requests.length == 2

# First request was POST to /keys/{keyName}/requestToken
first_request = mock_http.captured_requests[0]
ASSERT first_request.method == "POST"
ASSERT first_request.path matches "/keys/.*/requestToken"

# Second request used the exchanged token
second_request = mock_http.captured_requests[1]
ASSERT second_request.headers["Authorization"] == "Bearer exchanged-token"
```

---

## RSA8d - authCallback receives TokenParams

Tests that authCallback receives TokenParams when provided to authorize().

### Setup
```pseudo
mock_http = MockHttpClient()
received_params = null

auth_callback = FUNCTION(params):
  received_params = params
  RETURN TokenDetails(
    token: "test-token",
    expires: now() + 3600000
  )

client = Rest(
  options: ClientOptions(authCallback: auth_callback),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
AWAIT client.auth.authorize(
  tokenParams: TokenParams(
    clientId: "requested-client-id",
    ttl: 7200000,
    capability: {"channel1": ["publish"]}
  )
)
```

### Assertions
```pseudo
# authCallback received the TokenParams
ASSERT received_params.clientId == "requested-client-id"
ASSERT received_params.ttl == 7200000
ASSERT received_params.capability == {"channel1": ["publish"]}
```

---

## RSA8c - authUrl invoked for authentication

Tests that when `authUrl` is configured, the library fetches a token from it.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(
    authUrl: "https://auth.example.com/token"
  ),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
# authUrl returns TokenDetails
mock_http.queue_response_for_host("auth.example.com", 200, {
  "token": "authurl-token",
  "expires": now() + 3600000
})
# Actual API request
mock_http.queue_response(200, {"channelId": "test"})

AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# First request was to authUrl
auth_request = mock_http.captured_requests[0]
ASSERT auth_request.url.host == "auth.example.com"
ASSERT auth_request.url.path == "/token"
ASSERT auth_request.method == "GET"

# Second request used the token from authUrl
api_request = mock_http.captured_requests[1]
ASSERT api_request.headers["Authorization"] == "Bearer authurl-token"
```

---

## RSA8c - authUrl with POST method

Tests that authMethod can be set to POST for authUrl.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(
    authUrl: "https://auth.example.com/token",
    authMethod: "POST"
  ),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response_for_host("auth.example.com", 200, {
  "token": "authurl-token",
  "expires": now() + 3600000
})
mock_http.queue_response(200, {"channelId": "test"})

AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# authUrl request used POST method
auth_request = mock_http.captured_requests[0]
ASSERT auth_request.method == "POST"
```

---

## RSA8c - authUrl with custom headers

Tests that authHeaders are sent with authUrl requests.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(
    authUrl: "https://auth.example.com/token",
    authHeaders: {
      "X-Custom-Header": "custom-value",
      "X-API-Key": "my-api-key"
    }
  ),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response_for_host("auth.example.com", 200, {
  "token": "authurl-token",
  "expires": now() + 3600000
})
mock_http.queue_response(200, {"channelId": "test"})

AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
auth_request = mock_http.captured_requests[0]
ASSERT auth_request.headers["X-Custom-Header"] == "custom-value"
ASSERT auth_request.headers["X-API-Key"] == "my-api-key"
```

---

## RSA8c - authUrl with query params

Tests that authParams are sent as query parameters with authUrl GET requests.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(
    authUrl: "https://auth.example.com/token",
    authParams: {
      "client_id": "my-client",
      "scope": "publish:*"
    }
  ),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response_for_host("auth.example.com", 200, {
  "token": "authurl-token",
  "expires": now() + 3600000
})
mock_http.queue_response(200, {"channelId": "test"})

AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
auth_request = mock_http.captured_requests[0]
ASSERT auth_request.url.query_params["client_id"] == "my-client"
ASSERT auth_request.url.query_params["scope"] == "publish:*"
```

---

## RSA8c - authUrl returning JWT string

Tests that authUrl can return a raw JWT string.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(
    authUrl: "https://auth.example.com/jwt"
  ),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
# authUrl returns plain text JWT (not JSON)
mock_http.queue_response_for_host("auth.example.com", 200,
  "eyJhbGciOiJIUzI1NiJ9.jwt-body.signature",
  content_type: "text/plain"
)
mock_http.queue_response(200, {"channelId": "test"})

AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
api_request = mock_http.captured_requests[1]
ASSERT api_request.headers["Authorization"] == "Bearer eyJhbGciOiJIUzI1NiJ9.jwt-body.signature"
```

---

## RSA8d - authCallback error propagated

Tests that errors from authCallback are properly propagated.

### Setup
```pseudo
mock_http = MockHttpClient()

auth_callback = FUNCTION(params):
  THROW Error("Authentication server unavailable")

client = Rest(
  options: ClientOptions(authCallback: auth_callback),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
TRY:
  AWAIT client.request("GET", "/channels/test")
  FAIL("Expected exception")
CATCH AblyException as e:
  # Error should indicate auth failure
  ASSERT e.message CONTAINS "Authentication server unavailable"
```

### Assertions
```pseudo
# No HTTP requests should have been made
ASSERT mock_http.captured_requests.length == 0
```

---

## RSA8c - authUrl error propagated

Tests that HTTP errors from authUrl are properly propagated.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(
    authUrl: "https://auth.example.com/token"
  ),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
# authUrl returns error
mock_http.queue_response_for_host("auth.example.com", 500, {
  "error": "Internal server error"
})

TRY:
  AWAIT client.request("GET", "/channels/test")
  FAIL("Expected exception")
CATCH AblyException as e:
  ASSERT e.statusCode == 500 OR e.message CONTAINS "auth"
```

### Assertions
```pseudo
# Only authUrl request was made, not the API request
ASSERT mock_http.captured_requests.length == 1
ASSERT mock_http.captured_requests[0].url.host == "auth.example.com"
```
