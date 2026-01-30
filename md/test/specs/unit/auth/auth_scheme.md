# Auth Scheme Selection Tests

Spec points: `RSA1`, `RSA2`, `RSA3`, `RSA4`, `RSA4b`

## Test Type
Unit test with mocked HTTP

## Purpose

These tests verify that the library correctly selects between Basic authentication (API key) and Token authentication based on ClientOptions configuration.

### Key Rules

- **Basic auth**: Uses `Authorization: Basic {base64(key)}` header
- **Token auth**: Uses `Authorization: Bearer {token}` header
- **RSA4b**: If `clientId` is provided with an API key, the library MUST use token auth (not basic auth)

---

## RSA4 - Basic auth with API key only

Tests that when only an API key is provided (no clientId), Basic auth is used.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "appId.keyId:keySecret"),
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
request = mock_http.captured_requests[0]

# Basic auth header uses base64-encoded key
expected_auth = "Basic " + base64("appId.keyId:keySecret")
ASSERT request.headers["Authorization"] == expected_auth
```

---

## RSA4b - Token auth when clientId provided with key

Tests that when `clientId` is provided along with an API key, the library uses token auth (obtains a token using the key).

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(
    key: "appId.keyId:keySecret",
    clientId: "my-client-id"
  ),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
# Token request (library exchanges key for token)
mock_http.queue_response(200, {
  "token": "obtained-token",
  "expires": now() + 3600000,
  "clientId": "my-client-id"
})
# Actual API request
mock_http.queue_response(200, {"channelId": "test"})

AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# Two requests: token request + API call
ASSERT mock_http.captured_requests.length == 2

# First request is token request (can use Basic auth internally)
token_request = mock_http.captured_requests[0]
ASSERT token_request.path matches "/keys/.*/requestToken"

# Second request uses Bearer token
api_request = mock_http.captured_requests[1]
ASSERT api_request.headers["Authorization"] == "Bearer obtained-token"
ASSERT api_request.headers["Authorization"] NOT STARTS WITH "Basic"
```

---

## RSA3 - Token auth with explicit token

Tests that when an explicit token is provided, it is used for Bearer auth.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(token: "explicit-token-string"),
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
request = mock_http.captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer explicit-token-string"
```

---

## RSA3 - Token auth with TokenDetails

Tests that when TokenDetails is provided, the token string is extracted and used.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(
    tokenDetails: TokenDetails(
      token: "token-from-details",
      expires: now() + 3600000
    )
  ),
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
request = mock_http.captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer token-from-details"
```

---

## RSA4 - useTokenAuth forces token auth

Tests that `useTokenAuth: true` forces token auth even with just an API key.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(
    key: "appId.keyId:keySecret",
    useTokenAuth: true
  ),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
# Token request
mock_http.queue_response(200, {
  "token": "obtained-token",
  "expires": now() + 3600000
})
# API request
mock_http.queue_response(200, {"channelId": "test"})

AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
# Should obtain token rather than use Basic auth
api_request = mock_http.captured_requests[1]
ASSERT api_request.headers["Authorization"] == "Bearer obtained-token"
```

---

## RSA4 - authCallback triggers token auth

Tests that presence of authCallback triggers token auth.

### Setup
```pseudo
mock_http = MockHttpClient()

auth_callback = FUNCTION(params):
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
mock_http.queue_response(200, {"channelId": "test"})
AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer callback-token"
```

---

## RSA4 - authUrl triggers token auth

Tests that presence of authUrl triggers token auth.

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
# authUrl response
mock_http.queue_response_for_host("auth.example.com", 200, {
  "token": "authurl-token",
  "expires": now() + 3600000
})
# API request
mock_http.queue_response(200, {"channelId": "test"})

AWAIT client.request("GET", "/channels/test")
```

### Assertions
```pseudo
api_request = mock_http.captured_requests[1]
ASSERT api_request.headers["Authorization"] == "Bearer authurl-token"
```

---

## RSA4 - Error when no auth method available

Tests that an error is raised when no authentication method is configured.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(),  # No key, token, or auth callback
  httpClient: mock_http
)
```

### Test Steps
```pseudo
TRY:
  AWAIT client.request("GET", "/channels/test")
  FAIL("Expected exception")
CATCH AblyException as e:
  ASSERT e.code == 40106  # No authentication method
```

### Assertions
```pseudo
# No HTTP request should have been made
ASSERT mock_http.captured_requests.length == 0
```

---

## RSA4 - Error when token expired and no renewal method

Tests that an appropriate error is raised when a static token has expired and there's no way to renew it.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(
    tokenDetails: TokenDetails(
      token: "expired-token",
      expires: now() - 1000  # Already expired
    )
    # No key, authCallback, or authUrl for renewal
  ),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
TRY:
  AWAIT client.request("GET", "/channels/test")
  FAIL("Expected exception")
CATCH AblyException as e:
  ASSERT e.code == 40171  # Token expired with no means of renewal
```

### Assertions
```pseudo
# No HTTP request should have been made
ASSERT mock_http.captured_requests.length == 0
```

---

## RSA1 - Auth method priority

Tests the priority order when multiple auth options are provided.

### Setup
```pseudo
mock_http = MockHttpClient()

auth_callback = FUNCTION(params):
  RETURN TokenDetails(
    token: "callback-token",
    expires: now() + 3600000
  )

# Both key and authCallback provided
client = Rest(
  options: ClientOptions(
    key: "appId.keyId:keySecret",
    authCallback: auth_callback
  ),
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
# authCallback takes precedence, so Bearer auth is used
request = mock_http.captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer callback-token"
```

---

## RSA2 - Basic auth header format

Tests the exact format of Basic auth header.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "app123.key456:secretXYZ"),
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
request = mock_http.captured_requests[0]

# Verify exact Base64 encoding
# "app123.key456:secretXYZ" base64 encoded
expected = "Basic " + base64("app123.key456:secretXYZ")
ASSERT request.headers["Authorization"] == expected

# The Base64 should NOT have URL-safe encoding (+ and / are valid)
ASSERT request.headers["Authorization"] CONTAINS "Basic "
```

---

## RSC18 - Basic auth requires TLS

Tests that Basic auth is rejected over non-TLS connections.

### Setup
```pseudo
mock_http = MockHttpClient()
```

### Test Steps
```pseudo
TRY:
  client = Rest(
    options: ClientOptions(
      key: "appId.keyId:keySecret",
      tls: false  # Non-TLS connection
    ),
    httpClient: mock_http
  )
  AWAIT client.request("GET", "/channels/test")
  FAIL("Expected exception")
CATCH AblyException as e:
  ASSERT e.code == 40103  # Cannot use Basic auth over non-TLS
```

### Assertions
```pseudo
# No HTTP request should have been made
ASSERT mock_http.captured_requests.length == 0
```

---

## RSC18 - Token auth allowed over non-TLS

Tests that token auth is allowed over non-TLS connections.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(
    token: "explicit-token",
    tls: false  # Non-TLS allowed for token auth
  ),
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
request = mock_http.captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer explicit-token"

# Request should use http:// (non-TLS)
ASSERT request.url.scheme == "http"
```
