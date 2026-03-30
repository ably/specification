# Auth Callback Tests

Spec points: `RSA8c`, `RSA8d`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/test/rest/unit/rest_client.md` for the full Mock HTTP Infrastructure specification. These tests use the same `MockHttpClient` interface with `PendingConnection` and `PendingRequest`.

## Purpose

These tests verify that the library correctly invokes `authCallback` and `authUrl` to obtain tokens for authentication. The authCallback/authUrl can return:
- A `TokenDetails` object (containing token, expires, etc.)
- A `TokenRequest` object (which the library exchanges for a token)
- A JWT string (raw token string)

---

## RSA8d - authCallback invoked for authentication

**Spec requirement:** When `authCallback` is configured, it is invoked to obtain a token for authentication.

Tests that when `authCallback` is configured, it is invoked to obtain a token.

### Setup
```pseudo
callback_invoked = false
callback_params = null
captured_requests = []

auth_callback = FUNCTION(params):
  callback_invoked = true
  callback_params = params
  RETURN TokenDetails(
    token: "callback-token",
    expires: now() + 3600000
  )

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(authCallback: auth_callback)
)
```

### Test Steps
```pseudo
# Make a request that requires authentication
result = AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# authCallback was invoked
ASSERT callback_invoked == true

# Request used the token from authCallback
ASSERT captured_requests.length == 1
ASSERT captured_requests[0].headers["Authorization"] == "Bearer callback-token"
```

---

## RSA8d - authCallback returning JWT string

**Spec requirement:** authCallback can return a raw JWT string (not wrapped in TokenDetails).

Tests that authCallback can return a raw JWT string (not wrapped in TokenDetails).

### Setup
```pseudo
captured_requests = []

auth_callback = FUNCTION(params):
  # Return raw JWT string instead of TokenDetails
  RETURN "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-jwt-payload"

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(authCallback: auth_callback)
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# Request used the JWT from authCallback
ASSERT captured_requests[0].headers["Authorization"] == "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test-jwt-payload"
```

---

## RSA8d - authCallback returning TokenRequest

**Spec requirement:** When authCallback returns a TokenRequest, the library must exchange it for a token via the requestToken endpoint.

Tests that when authCallback returns a TokenRequest, the library exchanges it for a token.

### Setup
```pseudo
captured_requests = []

auth_callback = FUNCTION(params):
  # Return a TokenRequest (to be exchanged for token)
  RETURN TokenRequest(
    keyName: "app.key",
    ttl: 3600000,
    timestamp: now(),
    nonce: "unique-nonce",
    mac: "computed-mac"
  )

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.path matches "/keys/.*/requestToken":
      # First request exchanges TokenRequest for TokenDetails
      req.respond_with(200, {
        "token": "exchanged-token",
        "expires": now() + 3600000
      })
    ELSE:
      # Second request is the actual API call
      req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(authCallback: auth_callback)
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# Two HTTP requests: token exchange + API call
ASSERT captured_requests.length == 2

# First request was POST to /keys/{keyName}/requestToken
first_request = captured_requests[0]
ASSERT first_request.method == "POST"
ASSERT first_request.path matches "/keys/.*/requestToken"

# Second request used the exchanged token
second_request = captured_requests[1]
ASSERT second_request.headers["Authorization"] == "Bearer exchanged-token"
```

---

## RSA8d - authCallback receives TokenParams

**Spec requirement:** authCallback receives TokenParams when provided to authorize().

Tests that authCallback receives TokenParams when provided to authorize().

### Setup
```pseudo
received_params = null

auth_callback = FUNCTION(params):
  received_params = params
  RETURN TokenDetails(
    token: "test-token",
    expires: now() + 3600000
  )

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(authCallback: auth_callback)
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

**Spec requirement:** When `authUrl` is configured, the library must fetch a token from it before making API requests.

Tests that when `authUrl` is configured, the library fetches a token from it.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.url.host == "auth.example.com":
      # authUrl returns TokenDetails
      req.respond_with(200, {
        "token": "authurl-token",
        "expires": now() + 3600000
      })
    ELSE:
      # Actual API request
      req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(
    authUrl: "https://auth.example.com/token"
  )
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# First request was to authUrl
auth_request = captured_requests[0]
ASSERT auth_request.url.host == "auth.example.com"
ASSERT auth_request.url.path == "/token"
ASSERT auth_request.method == "GET"

# Second request used the token from authUrl
api_request = captured_requests[1]
ASSERT api_request.headers["Authorization"] == "Bearer authurl-token"
```

---

## RSA8c - authUrl with POST method

**Spec requirement:** authMethod can be set to POST for authUrl requests.

Tests that authMethod can be set to POST for authUrl.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.url.host == "auth.example.com":
      req.respond_with(200, {
        "token": "authurl-token",
        "expires": now() + 3600000
      })
    ELSE:
      req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(
    authUrl: "https://auth.example.com/token",
    authMethod: "POST"
  )
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# authUrl request used POST method
auth_request = captured_requests[0]
ASSERT auth_request.method == "POST"
```

---

## RSA8c - authUrl with custom headers

**Spec requirement:** authHeaders are sent with authUrl requests.

Tests that authHeaders are sent with authUrl requests.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.url.host == "auth.example.com":
      req.respond_with(200, {
        "token": "authurl-token",
        "expires": now() + 3600000
      })
    ELSE:
      req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(
    authUrl: "https://auth.example.com/token",
    authHeaders: {
      "X-Custom-Header": "custom-value",
      "X-API-Key": "my-api-key"
    }
  )
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
auth_request = captured_requests[0]
ASSERT auth_request.headers["X-Custom-Header"] == "custom-value"
ASSERT auth_request.headers["X-API-Key"] == "my-api-key"
```

---

## RSA8c - authUrl with query params

**Spec requirement:** authParams are sent as query parameters with authUrl GET requests.

Tests that authParams are sent as query parameters with authUrl GET requests.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.url.host == "auth.example.com":
      req.respond_with(200, {
        "token": "authurl-token",
        "expires": now() + 3600000
      })
    ELSE:
      req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(
    authUrl: "https://auth.example.com/token",
    authParams: {
      "client_id": "my-client",
      "scope": "publish:*"
    }
  )
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
auth_request = captured_requests[0]
ASSERT auth_request.url.query_params["client_id"] == "my-client"
ASSERT auth_request.url.query_params["scope"] == "publish:*"
```

---

## RSA8c - authUrl returning JWT string

**Spec requirement:** authUrl can return a raw JWT string (not JSON).

Tests that authUrl can return a raw JWT string.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.url.host == "auth.example.com":
      # authUrl returns plain text JWT (not JSON)
      req.respond_with(200, 
        body: "eyJhbGciOiJIUzI1NiJ9.jwt-body.signature",
        headers: {"Content-Type": "text/plain"}
      )
    ELSE:
      req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(
    authUrl: "https://auth.example.com/jwt"
  )
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
api_request = captured_requests[1]
ASSERT api_request.headers["Authorization"] == "Bearer eyJhbGciOiJIUzI1NiJ9.jwt-body.signature"
```

---

## RSA8d - authCallback error propagated

**Spec requirement:** Errors from authCallback are properly propagated to the caller.

Tests that errors from authCallback are properly propagated.

### Setup
```pseudo
captured_requests = []

auth_callback = FUNCTION(params):
  THROW Error("Authentication server unavailable")

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(authCallback: auth_callback)
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
ASSERT captured_requests.length == 0
```

---

## RSA8c - authUrl error propagated

**Spec requirement:** HTTP errors from authUrl are properly propagated to the caller.

Tests that HTTP errors from authUrl are properly propagated.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.url.host == "auth.example.com":
      # authUrl returns error
      req.respond_with(500, {
        "error": "Internal server error"
      })
    ELSE:
      req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(
    authUrl: "https://auth.example.com/token"
  )
)
```

### Test Steps
```pseudo
TRY:
  AWAIT client.request("GET", "/channels/test")
  FAIL("Expected exception")
CATCH AblyException as e:
  ASSERT e.statusCode == 500 OR e.message CONTAINS "auth"
```

### Assertions
```pseudo
# Only authUrl request was made, not the API request
ASSERT captured_requests.length == 1
ASSERT captured_requests[0].url.host == "auth.example.com"
```
