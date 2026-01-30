# Token Renewal Tests

Spec points: `RSA4b4`, `RSA14`

## Test Type
Unit test with mocked HTTP

## Purpose

These tests verify that the library correctly handles token expiry and triggers renewal when:
1. A token is known to be expired before a request
2. A request is rejected by the server due to token expiry

---

## RSA4b4 - Token renewal on expiry rejection

Tests that when a request is rejected with a token expiry error, the library obtains a new token and retries.

### Setup
```pseudo
mock_http = MockHttpClient()
callback_count = 0
tokens = ["first-token", "second-token"]

auth_callback = FUNCTION(params):
  token = tokens[callback_count]
  callback_count = callback_count + 1
  RETURN TokenDetails(
    token: token,
    expires: now() + 3600000
  )

client = Rest(
  options: ClientOptions(authCallback: auth_callback),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
# First request gets token, then fails with 40142 (token expired)
mock_http.queue_response(401, {
  "error": {
    "code": 40142,
    "statusCode": 401,
    "message": "Token expired"
  }
})
# After renewal, second attempt succeeds
mock_http.queue_response(200, [{"channel": "test"}])

result = AWAIT client.channels.get("test").history()
```

### Assertions
```pseudo
# authCallback was called twice (initial + renewal)
ASSERT callback_count == 2

# Two HTTP requests were made
ASSERT mock_http.request_count == 2

# First request used first token
first_request = mock_http.captured_requests[0]
ASSERT first_request.headers["Authorization"] == "Bearer first-token"

# Second request used renewed token
second_request = mock_http.captured_requests[1]
ASSERT second_request.headers["Authorization"] == "Bearer second-token"

# Final result is successful
ASSERT result.items IS List
```

---

## RSA4b4 - Token renewal on 40140 error

Tests renewal is triggered for error code 40140 (token error).

### Setup
```pseudo
mock_http = MockHttpClient()
callback_count = 0

auth_callback = FUNCTION(params):
  callback_count = callback_count + 1
  RETURN TokenDetails(
    token: "token-" + callback_count,
    expires: now() + 3600000
  )

client = Rest(
  options: ClientOptions(authCallback: auth_callback),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
# First attempt fails with 40140
mock_http.queue_response(401, {
  "error": {
    "code": 40140,
    "statusCode": 401,
    "message": "Token error"
  }
})
# Retry succeeds
mock_http.queue_response(200, [])

AWAIT client.channels.get("test").history()
```

### Assertions
```pseudo
ASSERT callback_count == 2
ASSERT mock_http.request_count == 2
```

---

## RSA14 - Pre-emptive token renewal

Tests that if a token is known to be expired before making a request, renewal happens without first making a failing request.

### Setup
```pseudo
mock_http = MockHttpClient()
callback_count = 0

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

client = Rest(
  options: ClientOptions(authCallback: auth_callback),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
# Force initial token acquisition
AWAIT client.auth.authorize()

# Queue only success response (no 401 expected)
mock_http.queue_response(200, [])

# This should detect expired token and renew before request
AWAIT client.channels.get("test").history()
```

### Assertions
```pseudo
# Callback was called twice (initial + pre-emptive renewal)
ASSERT callback_count == 2

# Only ONE HTTP request to the API (history)
# No failed request with expired token
requests_to_channels = mock_http.captured_requests.filter(
  r => r.path.contains("/channels/")
)
ASSERT requests_to_channels.length == 1
ASSERT requests_to_channels[0].headers["Authorization"] == "Bearer fresh-token"
```

---

## RSA4b4 - No renewal without authCallback

Tests that token renewal is not attempted if no renewal mechanism is available.

### Setup
```pseudo
mock_http = MockHttpClient()

# Client with explicit token but no authCallback
client = Rest(
  options: ClientOptions(token: "static-token"),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response(401, {
  "error": {
    "code": 40142,
    "statusCode": 401,
    "message": "Token expired"
  }
})

TRY:
  AWAIT client.channels.get("test").history()
  FAIL("Expected token expired error")
CATCH AblyException as e:
  ASSERT e.code == 40142
```

### Assertions
```pseudo
# Only one request was made (no retry)
ASSERT mock_http.request_count == 1
```

---

## RSA4b4 - Renewal with authUrl

Tests that token renewal works via authUrl.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(
    authUrl: "https://example.com/auth"
  ),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
# First token request
mock_http.queue_response_for_host("example.com", 200, {
  "token": "first-token",
  "expires": now() + 3600000
})
# First API request fails
mock_http.queue_response(401, {
  "error": {"code": 40142, "message": "Token expired"}
})
# Second token request (renewal)
mock_http.queue_response_for_host("example.com", 200, {
  "token": "second-token",
  "expires": now() + 3600000
})
# Retry succeeds
mock_http.queue_response(200, [])

AWAIT client.channels.get("test").history()
```

### Assertions
```pseudo
# Two requests to authUrl
auth_requests = mock_http.captured_requests.filter(
  r => r.url.host == "example.com"
)
ASSERT auth_requests.length == 2

# Two requests to Ably API
api_requests = mock_http.captured_requests.filter(
  r => r.url.host != "example.com"
)
ASSERT api_requests.length == 2

# Second API request used renewed token
ASSERT api_requests[1].headers["Authorization"] == "Bearer second-token"
```

---

## RSA4b4 - Renewal limit

Tests that token renewal doesn't loop infinitely if server keeps rejecting.

### Setup
```pseudo
mock_http = MockHttpClient()
callback_count = 0

auth_callback = FUNCTION(params):
  callback_count = callback_count + 1
  RETURN TokenDetails(
    token: "token-" + callback_count,
    expires: now() + 3600000
  )

client = Rest(
  options: ClientOptions(authCallback: auth_callback),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
# Always return token expired
FOR i IN 1..10:
  mock_http.queue_response(401, {
    "error": {"code": 40142, "message": "Token expired"}
  })

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
```
