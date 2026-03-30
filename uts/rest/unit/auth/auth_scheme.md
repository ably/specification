# Auth Scheme Selection Tests

Spec points: `RSA1`, `RSA2`, `RSA3`, `RSA4`, `RSA4b`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/test/rest/unit/rest_client.md` for the full Mock HTTP Infrastructure specification. These tests use the same `MockHttpClient` interface with `PendingConnection` and `PendingRequest`.

## Purpose

These tests verify that the library correctly selects between Basic authentication (API key) and Token authentication based on ClientOptions configuration.

### Key Rules

- **Basic auth**: Uses `Authorization: Basic {base64(key)}` header
- **Token auth**: Uses `Authorization: Bearer {token}` header
- **RSA4b**: If `clientId` is provided with an API key, the library MUST use token auth (not basic auth)

---

## RSA4 - Basic auth with API key only

**Spec requirement:** When only an API key is provided (no clientId), Basic auth is used.

Tests that when only an API key is provided (no clientId), Basic auth is used.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(key: "appId.keyId:keySecret")
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
request = captured_requests[0]

# Basic auth header uses base64-encoded key
expected_auth = "Basic " + base64("appId.keyId:keySecret")
ASSERT request.headers["Authorization"] == expected_auth
```

---

## RSA4b - Token auth when clientId provided with key

**Spec requirement:** When `clientId` is provided along with an API key, the library MUST use token auth (not basic auth).

Tests that when `clientId` is provided along with an API key, the library uses token auth (obtains a token using the key).

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.path matches "/keys/.*/requestToken":
      # Token request (library exchanges key for token)
      req.respond_with(200, {
        "token": "obtained-token",
        "expires": now() + 3600000,
        "clientId": "my-client-id"
      })
    ELSE:
      # Actual API request
      req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(
    key: "appId.keyId:keySecret",
    clientId: "my-client-id"
  )
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# Two requests: token request + API call
ASSERT captured_requests.length == 2

# First request is token request (can use Basic auth internally)
token_request = captured_requests[0]
ASSERT token_request.path matches "/keys/.*/requestToken"

# Second request uses Bearer token
api_request = captured_requests[1]
ASSERT api_request.headers["Authorization"] == "Bearer obtained-token"
ASSERT api_request.headers["Authorization"] NOT STARTS WITH "Basic"
```

---

## RSA3 - Token auth with explicit token

**Spec requirement:** When an explicit token is provided, it is used for Bearer auth.

Tests that when an explicit token is provided, it is used for Bearer auth.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(token: "explicit-token-string")
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer explicit-token-string"
```

---

## RSA3 - Token auth with TokenDetails

**Spec requirement:** When TokenDetails is provided, the token string is extracted and used for Bearer auth.

Tests that when TokenDetails is provided, the token string is extracted and used.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(
    tokenDetails: TokenDetails(
      token: "token-from-details",
      expires: now() + 3600000
    )
  )
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer token-from-details"
```

---

## RSA4 - useTokenAuth forces token auth

**Spec requirement:** `useTokenAuth: true` forces token auth even with just an API key.

Tests that `useTokenAuth: true` forces token auth even with just an API key.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.path matches "/keys/.*/requestToken":
      # Token request
      req.respond_with(200, {
        "token": "obtained-token",
        "expires": now() + 3600000
      })
    ELSE:
      # API request
      req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(
    key: "appId.keyId:keySecret",
    useTokenAuth: true
  )
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# Should obtain token rather than use Basic auth
api_request = captured_requests[1]
ASSERT api_request.headers["Authorization"] == "Bearer obtained-token"
```

---

## RSA4 - authCallback triggers token auth

**Spec requirement:** Presence of authCallback triggers token auth.

Tests that presence of authCallback triggers token auth.

### Setup
```pseudo
captured_requests = []

auth_callback = FUNCTION(params):
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
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer callback-token"
```

---

## RSA4 - authUrl triggers token auth

**Spec requirement:** Presence of authUrl triggers token auth.

Tests that presence of authUrl triggers token auth.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.url.host == "auth.example.com":
      # authUrl response
      req.respond_with(200, {
        "token": "authurl-token",
        "expires": now() + 3600000
      })
    ELSE:
      # API request
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
api_request = captured_requests[1]
ASSERT api_request.headers["Authorization"] == "Bearer authurl-token"
```

---

## RSA4 - Error when no auth method available

**Spec requirement:** An error is raised when no authentication method is configured (code 40106).

Tests that an error is raised when no authentication method is configured.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions()  # No key, token, or auth callback
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test") FAILS WITH error
ASSERT error.code == 40106  # No authentication method
```

### Assertions
```pseudo
# No HTTP request should have been made
ASSERT captured_requests.length == 0
```

---

## RSA4 - Error when token expired and no renewal method

**Spec requirement:** An error is raised when a static token has expired and there's no way to renew it (code 40171).

Tests that an appropriate error is raised when a static token has expired and there's no way to renew it.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(
    tokenDetails: TokenDetails(
      token: "expired-token",
      expires: now() - 1000  # Already expired
    )
    # No key, authCallback, or authUrl for renewal
  )
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test") FAILS WITH error
ASSERT error.code == 40171  # Token expired with no means of renewal
```

### Assertions
```pseudo
# No HTTP request should have been made
ASSERT captured_requests.length == 0
```

---

## RSA1 - Auth method priority

**Spec requirement:** When multiple auth options are provided, token-based auth takes precedence over basic auth.

Tests the priority order when multiple auth options are provided.

### Setup
```pseudo
captured_requests = []

auth_callback = FUNCTION(params):
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

# Both key and authCallback provided
client = Rest(
  options: ClientOptions(
    key: "appId.keyId:keySecret",
    authCallback: auth_callback
  )
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# authCallback takes precedence, so Bearer auth is used
request = captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer callback-token"
```

---

## RSA2 - Basic auth header format

**Spec requirement:** Basic auth uses the format `Authorization: Basic {base64(key)}`.

Tests the exact format of Basic auth header.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(key: "app123.key456:secretXYZ")
)
```

### Test Steps
```pseudo
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
request = captured_requests[0]

# Verify exact Base64 encoding
# "app123.key456:secretXYZ" base64 encoded
expected = "Basic " + base64("app123.key456:secretXYZ")
ASSERT request.headers["Authorization"] == expected

# The Base64 should NOT have URL-safe encoding (+ and / are valid)
ASSERT request.headers["Authorization"] CONTAINS "Basic "
```

---

## RSC18 - Basic auth requires TLS

**Spec requirement:** Basic auth is rejected over non-TLS connections (code 40103).

Tests that Basic auth is rejected over non-TLS connections. The error is thrown at client construction time when the configuration would result in Basic auth over non-TLS.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {"channelId": "test", "status": {"isActive": true}})
  }
)
install_mock(mock_http)
```

### Test Steps
```pseudo
# Error is thrown at construction time - the client cannot be created
# with Basic auth (API key only) over non-TLS
Rest(
  options: ClientOptions(
    key: "appId.keyId:keySecret",
    tls: false  # Non-TLS connection with Basic auth
  )
) FAILS WITH error
ASSERT error.code == 40103  # Cannot use Basic auth over non-TLS
```

### Assertions
```pseudo
# No HTTP request should have been made - error thrown at construction
ASSERT captured_requests.length == 0
```

### Note
The RSC18 check only applies when the client configuration would result in Basic authentication (API key sent directly). It does NOT apply to:
- Token auth (Bearer tokens are allowed over non-TLS)
- Unauthenticated endpoints like `time()` which don't send credentials

---

## RSC18 - Token auth allowed over non-TLS

**Spec requirement:** Token auth is allowed over non-TLS connections.

Tests that token auth is allowed over non-TLS connections.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {"channelId": "test", "status": {"isActive": true}})
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(
    token: "explicit-token",
    tls: false  # Non-TLS allowed for token auth
  )
)
```

### Test Steps
```pseudo
AWAIT client.channels.get("test").status()
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer explicit-token"

# Request should use http:// (non-TLS)
ASSERT request.url.scheme == "http"
```
