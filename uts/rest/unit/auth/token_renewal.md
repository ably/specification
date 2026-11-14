# Token Renewal Tests

Spec points: `RSA4a2`, `RSA4b`, `RSA4b1`, `RSC10`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/rest/unit/rest_client.md` for the full Mock HTTP Infrastructure specification. These tests use the same `MockHttpClient` interface with `PendingConnection` and `PendingRequest`.

## Purpose

These tests verify that the library correctly handles token expiry and triggers renewal when:
1. A token is known to be expired before a request
2. A request is rejected by the server due to token expiry

---

## RSA4b - Token renewal on expiry rejection

**Test ID**: `rest/unit/RSA4b/renewal-on-40142-0`

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

## RSA4b - Token renewal on 40140 error

**Test ID**: `rest/unit/RSA4b/renewal-on-40140-1`

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

## RSA4b - Token renewal on token error after expiry

**Test ID**: `rest/unit/RSA4b/renewal-on-token-error-0`

**Spec requirement:** Per RSA4b, when the client has a means to renew the token and the server responds with a token error (401 HTTP status code and an Ably error value `40140 <= code < 40150`), the client makes a single attempt to reissue the token and resend the request using the new token.

Note: This test does not rely on RSA4b1 pre-emptive local expiry detection, which is optional and gated on a persisted server-time offset. The initial (expired) token is sent, the server rejects it with a token error, and renewal is triggered per RSA4b.

Tests that when the initial token is rejected by the server with a token error, the library obtains a new token and retries the request with it.

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
    IF req.headers["Authorization"] == "Bearer expired-token":
      # Server rejects the expired token with a token error
      req.respond_with(401, {
        "error": {
          "code": 40142,
          "statusCode": 401,
          "message": "Token expired"
        }
      })
    ELSE:
      # Retry with the renewed token succeeds
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
# Force initial (expired) token acquisition
AWAIT client.auth.authorize()

# The expired token is rejected by the server, triggering renewal (RSA4b)
AWAIT client.channels.get("test").history()
```

### Assertions
```pseudo
# Callback was called twice (initial + renewal after 401)
ASSERT callback_count == 2

# Exactly one history request succeeds, using the renewed token
requests_to_history = captured_requests.filter(
  r => r.path == "/channels/test/messages"
)
ASSERT requests_to_history.any(
  r => r.headers["Authorization"] == "Bearer fresh-token"
)
```

---

## RSA4b1 - Pre-emptive token renewal with server-time offset

**Test ID**: `rest/unit/RSA4b1/preemptive-renewal-with-offset-0`

**Spec requirement:** Per RSA4b1, a client library MAY save a round-trip for expired tokens by detecting expiry locally, but only when all of the following apply: the current token is a `TokenDetails` object with an `expires` attribute; the library has previously queried the time from the Ably service and persisted the local clock offset (RSA10k); and the `expires` time has passed based on the Ably service time. This test establishes those preconditions by setting `queryTime: true` (so the client obtains and persists a server-time offset via RSA10k) and verifies that, when the optional detection is implemented, the client renews pre-emptively without first issuing a failing request.

Note: RSA4b1 is optional. A conformant SDK that declines the optional pre-emptive detection will instead send the expired token and renew on the server's token error (covered by `rest/unit/RSA4b/renewal-on-token-error-0`). SDKs that do not implement RSA4b1 should skip this test.

Tests that, when the server-time offset has been persisted (RSA10k) and the current token has expired according to server time, the library renews the token pre-emptively rather than sending the expired token.

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
    IF req.path == "/time":
      # /time returns an ARRAY of a single server-time value in ms.
      # Return the current time so the persisted offset is ~0 and the
      # already-expired token is detected as expired against server time.
      req.respond_with(200, [now()])
    ELSE IF req.headers["Authorization"] == "Bearer expired-token":
      # The expired token must never reach the API under RSA4b1;
      # if it does, respond with a token error to make the failure obvious.
      req.respond_with(401, {
        "error": {
          "code": 40142,
          "statusCode": 401,
          "message": "Token expired"
        }
      })
    ELSE:
      # Request with the renewed token succeeds
      req.respond_with(200, [])
  }
)
install_mock(mock_http)

# queryTime: true causes the client to obtain and persist the server-time
# offset (RSA10k), which is the precondition for RSA4b1 local detection.
client = Rest(
  options: ClientOptions(
    authCallback: auth_callback,
    queryTime: true
  )
)
```

### Test Steps
```pseudo
# Force initial (expired) token acquisition and persisting of the offset
AWAIT client.auth.authorize()

# With the offset persisted and the token expired per server time, the
# client should detect expiry locally and renew before issuing the request
AWAIT client.channels.get("test").history()
```

### Assertions
```pseudo
# Callback was called twice (initial + pre-emptive renewal)
ASSERT callback_count == 2

# Exactly one history request, and it used the renewed token
requests_to_history = captured_requests.filter(
  r => r.path == "/channels/test/messages"
)
ASSERT requests_to_history.length == 1
ASSERT requests_to_history[0].headers["Authorization"] == "Bearer fresh-token"

# The expired token was never sent to the API (renewal was pre-emptive)
expired_api_requests = captured_requests.filter(
  r => r.path == "/channels/test/messages"
       AND r.headers["Authorization"] == "Bearer expired-token"
)
ASSERT expired_api_requests.length == 0
```

---

## RSA4a2 - No renewal without authCallback

**Test ID**: `rest/unit/RSA4a2/no-renewal-without-callback-0`

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
AWAIT client.channels.get("test").history() FAILS WITH error
ASSERT error.code == 40171
```

### Assertions
```pseudo
# Only one request was made (no retry)
ASSERT request_count == 1
```

---

## RSA4b - Renewal with authUrl

**Test ID**: `rest/unit/RSA4b/renewal-via-authurl-2`

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

## RSA4b - Renewal limit

**Test ID**: `rest/unit/RSA4b/renewal-limit-no-loop-3`

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
AWAIT client.channels.get("test").history() FAILS WITH error
# Should eventually give up
ASSERT error.code == 40142
```

### Assertions
```pseudo
# The library MUST retry at most once per original request (one renewal
# attempt). After the renewed token is also rejected, the error is
# propagated to the caller.
ASSERT callback_count == 2  # Initial token + one renewal
ASSERT request_count == 2   # Original request + one retry
```

---

## RSC10 - REST request retried after token renewal

**Test ID**: `rest/unit/RSC10/request-retried-after-renewal-0`

**Spec requirement:** If a REST request responds with a token error (401 HTTP status code and an Ably error value 40140 <= code < 40150), then the Auth class is responsible for reissuing a token and the request should be reattempted.

This test verifies the end-to-end flow at the HTTP client level: the original REST API call is transparently retried after the token is renewed, and the caller receives the successful result without knowing a renewal occurred.

Note: The RSA4b tests above verify the auth renewal mechanism in isolation. This RSC10 test verifies the HTTP client's retry behaviour wrapping that mechanism.

### Setup
```pseudo
callback_count = 0
captured_requests = []

auth_callback = FUNCTION(params):
  callback_count = callback_count + 1
  RETURN TokenDetails(
    token: "token-" + str(callback_count),
    expires: now() + 3600000
  )

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.headers["Authorization"] == "Bearer token-1":
      # First token is rejected
      req.respond_with(401, {
        "error": {
          "code": 40142,
          "statusCode": 401,
          "message": "Token expired"
        }
      })
    ELSE:
      # Renewed token succeeds — return channel status
      req.respond_with(200, {
        "channelId": "test",
        "status": {"isActive": true, "occupancy": {"metrics": {"connections": 0}}}
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
# Call channel.status() — the caller should not see the 401/renewal
result = AWAIT client.channels.get("test").status()
```

### Assertions
```pseudo
# The call succeeded transparently
ASSERT result IS ChannelDetails

# Two HTTP requests were made to /channels/test (original + retry)
channel_requests = captured_requests.filter(r => r.path == "/channels/test")
ASSERT channel_requests.length == 2

# Auth callback was called twice (initial token + renewal)
ASSERT callback_count == 2

# First request used first token, second used renewed token
ASSERT channel_requests[0].headers["Authorization"] == "Bearer token-1"
ASSERT channel_requests[1].headers["Authorization"] == "Bearer token-2"
```

---

## RSC10b - Non-token 401 errors MUST NOT trigger token renewal

**Test ID**: `rest/unit/RSC10b/non-token-401-no-renewal-0`

**Spec requirement:** Only errors with codes in the range 40140–40149 trigger token renewal. Other 401 errors (e.g. 40100 Unauthorized) MUST be propagated immediately without any renewal or retry attempt.

### Setup
```pseudo
callback_count = 0
request_count = 0

auth_callback = FUNCTION(params):
  callback_count = callback_count + 1
  RETURN TokenDetails(
    token: "token-" + str(callback_count),
    expires: now() + 3600000
  )

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    request_count = request_count + 1
    # Return a 401 with a non-token error code
    req.respond_with(401, {
      "error": {
        "code": 40100,
        "statusCode": 401,
        "message": "Unauthorized"
      }
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
AWAIT client.channels.get("test").status() FAILS WITH error
ASSERT error.code == 40100
```

### Assertions
```pseudo
# Only one HTTP request — no retry
ASSERT request_count == 1

# Auth callback was called once (initial token only, no renewal)
ASSERT callback_count == 1
```

---

## RSA4b - Token renewal with MessagePack error response

**Test ID**: `rest/unit/RSA4b/renewal-msgpack-response-4`

**Spec requirement:** Token renewal must work correctly when the server returns the 401 token-error response in MessagePack format (which is the default when `useBinaryProtocol: true`). The SDK must decode the msgpack error body to extract the token-error code (40140–40149) and trigger renewal.

### Setup
```pseudo
callback_count = 0
request_count = 0

auth_callback = FUNCTION(params):
  callback_count = callback_count + 1
  RETURN TokenDetails(
    token: "token-" + str(callback_count),
    expires: now() + 3600000
  )

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    request_count = request_count + 1
    IF request_count == 1:
      # First request fails with token expired — returned as msgpack
      req.respond_with(401,
        body: msgpack_encode({
          "error": {
            "code": 40142,
            "statusCode": 401,
            "message": "Token expired"
          }
        }),
        headers: { "Content-Type": "application/x-msgpack" }
      )
    ELSE:
      # Retry succeeds — also returned as msgpack
      req.respond_with(200,
        body: msgpack_encode([1234567890000]),
        headers: { "Content-Type": "application/x-msgpack" }
      )
  }
)
install_mock(mock_http)

client = Rest(
  options: ClientOptions(
    authCallback: auth_callback,
    useBinaryProtocol: true  # Default — msgpack
  )
)
```

### Test Steps
```pseudo
result = AWAIT client.time()
```

### Assertions
```pseudo
# Auth callback was called twice (initial + renewal)
ASSERT callback_count == 2

# Two HTTP requests were made (original + retry)
ASSERT request_count == 2

# Result is successful
ASSERT result == 1234567890000
```
