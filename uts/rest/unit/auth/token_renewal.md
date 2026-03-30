# Token Renewal Tests

Spec points: `RSA4b4`, `RSA14`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/test/rest/unit/rest_client.md` for the full Mock HTTP Infrastructure specification. These tests use the same `MockHttpClient` interface with `PendingConnection` and `PendingRequest`.

## Purpose

These tests verify that the library correctly handles token expiry and triggers renewal when:
1. A token is known to be expired before a request
2. A request is rejected by the server due to token expiry

---

## RSA4b4 - Token renewal on expiry rejection

**Spec requirement:** When a request is rejected with error code 40142 (token expired), the library must obtain a new token via the auth callback and retry the request automatically.

Tests that when a request is rejected with a token expiry error, the library obtains a new token and retries.

### Setup
```pseudo
callback_count = 0
tokens = ["first-token", "second-token"]
captured_requests = []
request_count = 0

auth_callback = FUNCTION(params):
  token = tokens[callback_count]
  callback_count = callback_count + 1
  RETURN TokenDetails(
    token: token,
    expires: now() + 3600000
  )

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    request_count++
    IF request_count == 1:
      # First request fails with token expired
      req.respond_with(401, {
        "error": {
          "code": 40142,
          "statusCode": 401,
          "message": "Token expired"
        }
      })
    ELSE:
      # Second request (after renewal) succeeds
      req.respond_with(200, [{"channel": "test"}])
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(authCallback: auth_callback)
)
```

### Test Steps
```pseudo
result = AWAIT client.channels.get("test").history()
```

### Assertions
```pseudo
# authCallback was called twice (initial + renewal)
ASSERT callback_count == 2

# Two HTTP requests were made
ASSERT request_count == 2

# First request used first token
ASSERT captured_requests[0].headers["Authorization"] == "Bearer first-token"

# Second request used renewed token
ASSERT captured_requests[1].headers["Authorization"] == "Bearer second-token"

# Final result is successful
ASSERT result.items IS List
```

---

## RSA4b4 - Token renewal on 40140 error

**Spec requirement:** Token renewal must also be triggered for error code 40140 (token error), not just 40142 (token expired).

Tests renewal is triggered for error code 40140 (token error).

### Setup
```pseudo
callback_count = 0
request_count = 0

auth_callback = FUNCTION(params):
  callback_count = callback_count + 1
  RETURN TokenDetails(
    token: "token-" + callback_count,
    expires: now() + 3600000
  )

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    request_count++
    IF request_count == 1:
      # First attempt fails with 40140
      req.respond_with(401, {
        "error": {
          "code": 40140,
          "statusCode": 401,
          "message": "Token error"
        }
      })
    ELSE:
      # Retry succeeds
      req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(authCallback: auth_callback)
)
```

### Test Steps
```pseudo
AWAIT client.channels.get("test").history()
```

### Assertions
```pseudo
ASSERT callback_count == 2
ASSERT request_count == 2
```

---

## RSA14 - Pre-emptive token renewal

**Spec requirement:** If a token is known to be expired before making a request, renewal must happen pre-emptively without first making a failing request.

Tests that if a token is known to be expired before making a request, renewal happens without first making a failing request.

### Setup
```pseudo
callback_count = 0
captured_requests = []

auth_callback = FUNCTION(params):
  callback_count = callback_count + 1
  IF callback_count == 1:
    # First token is already expired
    RETURN TokenDetails(
      token: "expired-token",
      expires: now() - 1000  # Already expired
    )
  ELSE:
    RETURN TokenDetails(
      token: "fresh-token",
      expires: now() + 3600000
    )

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    # Only success response (no 401 expected)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(authCallback: auth_callback)
)
```

### Test Steps
```pseudo
# Force initial token acquisition
AWAIT client.auth.authorize()

# This should detect expired token and renew before request
AWAIT client.channels.get("test").history()
```

### Assertions
```pseudo
# Callback was called twice (initial + pre-emptive renewal)
ASSERT callback_count == 2

# Only ONE HTTP request to the API (history)
# No failed request with expired token
requests_to_channels = captured_requests.filter(
  r => r.path.contains("/channels/")
)
ASSERT requests_to_channels.length == 1
ASSERT requests_to_channels[0].headers["Authorization"] == "Bearer fresh-token"
```

---

## RSA4b4 - No renewal without authCallback

**Spec requirement:** Token renewal is not attempted if no renewal mechanism (authCallback/authUrl/key) is available.

Tests that token renewal is not attempted if no renewal mechanism is available.

### Setup
```pseudo
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    request_count++
    req.respond_with(401, {
      "error": {
        "code": 40142,
        "statusCode": 401,
        "message": "Token expired"
      }
    })
  }
)
install_mock(mock_http)

# Client with explicit token but no authCallback
client = Rest(
  options: ClientOptions(token: "static-token")
)
```

### Test Steps
```pseudo
TRY:
  AWAIT client.channels.get("test").history()
  FAIL("Expected token expired error")
CATCH AblyException as e:
  ASSERT e.code == 40142
```

### Assertions
```pseudo
# Only one request was made (no retry)
ASSERT request_count == 1
```

---

## RSA4b4 - Renewal with authUrl

**Spec requirement:** Token renewal must work via authUrl when a request is rejected with error code 40142.

Tests that token renewal works via authUrl.

### Setup
```pseudo
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    request_count++
    
    IF req.url.host == "example.com":
      # authUrl requests - return tokens
      IF request_count == 1:
        req.respond_with(200, {
          "token": "first-token",
          "expires": now() + 3600000
        })
      ELSE:
        # Second token request (renewal)
        req.respond_with(200, {
          "token": "second-token",
          "expires": now() + 3600000
        })
    ELSE:
      # API requests
      IF request_count == 2:
        # First API request fails
        req.respond_with(401, {
          "error": {"code": 40142, "message": "Token expired"}
        })
      ELSE:
        # Retry succeeds
        req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(
    authUrl: "https://example.com/auth"
  )
)
```

### Test Steps
```pseudo
AWAIT client.channels.get("test").history()
```

### Assertions
```pseudo
# Two requests to authUrl
auth_requests = captured_requests.filter(
  r => r.url.host == "example.com"
)
ASSERT auth_requests.length == 2

# Two requests to Ably API
api_requests = captured_requests.filter(
  r => r.url.host != "example.com"
)
ASSERT api_requests.length == 2

# Second API request used renewed token
ASSERT api_requests[1].headers["Authorization"] == "Bearer second-token"
```

---

## RSA4b4 - Renewal limit

**Spec requirement:** Token renewal must not loop infinitely if server keeps rejecting tokens.

Tests that token renewal doesn't loop infinitely if server keeps rejecting.

### Setup
```pseudo
callback_count = 0
request_count = 0

auth_callback = FUNCTION(params):
  callback_count = callback_count + 1
  RETURN TokenDetails(
    token: "token-" + callback_count,
    expires: now() + 3600000
  )

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    request_count++
    # Always return token expired
    req.respond_with(401, {
      "error": {"code": 40142, "message": "Token expired"}
    })
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
  AWAIT client.channels.get("test").history()
  FAIL("Expected error after max retries")
CATCH AblyException as e:
  # Should eventually give up
  ASSERT e.code == 40142
```

### Assertions
```pseudo
# Should not retry indefinitely (implementation-specific limit)
ASSERT callback_count <= 3  # Reasonable retry limit
ASSERT request_count <= 3  # Should stop making requests
```
