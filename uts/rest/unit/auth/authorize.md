# Auth.authorize() Tests

Spec points: `RSA10`, `RSA10a`, `RSA10b`, `RSA10e`, `RSA10g`, `RSA10h`, `RSA10i`, `RSA10j`, `RSA10k`, `RSA10l`

## Test Type
Unit test with mocked HTTP client and/or mocked authCallback

## Mock HTTP Infrastructure

See `uts/test/rest/unit/rest_client.md` for the full Mock HTTP Infrastructure specification. These tests use the same `MockHttpClient` interface with `PendingConnection` and `PendingRequest`.

---

## RSA10a - authorize() with default tokenParams

**Spec requirement:** `authorize()` obtains a token using configured defaults.

Tests that `authorize()` obtains a token using configured defaults.

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
        "expires": now() + 3600000,
        "keyName": "appId.keyId"
      })
    ELSE:
      # Subsequent request to verify token is used
      req.respond_with(200, { "time": 1234567890000 })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
token_details = AWAIT client.auth.authorize()
```

### Assertions
```pseudo
ASSERT token_details IS TokenDetails
ASSERT token_details.token == "obtained-token"

# Verify token is now used for requests
AWAIT client.time()
ASSERT captured_requests.last.headers["Authorization"] == "Bearer obtained-token"
```

---

## RSA10b - authorize() with explicit tokenParams

**Spec requirement:** Provided `tokenParams` override defaults in authorize().

Tests that provided `tokenParams` override defaults.

### Setup
```pseudo
callback_params = []

mock_auth_callback = (params) => {
  callback_params.append(params)
  RETURN TokenDetails(token: "callback-token", expires: now() + 3600000)
}

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  authCallback: mock_auth_callback,
  clientId: "default-client"  # Default TokenParams
))
```

### Test Steps
```pseudo
AWAIT client.auth.authorize(
  tokenParams: TokenParams(
    clientId: "override-client",
    ttl: 7200000
  )
)
```

### Assertions
```pseudo
params = callback_params[0]
ASSERT params.clientId == "override-client"  # Overridden
ASSERT params.ttl == 7200000
```

---

## RSA10e - authorize() saves tokenParams for reuse

**Spec requirement:** `tokenParams` provided to `authorize()` are saved and reused on subsequent token requests.

Tests that `tokenParams` provided to `authorize()` are saved and reused.

### Setup
```pseudo
callback_invocations = []

mock_auth_callback = (params) => {
  callback_invocations.append(params)
  RETURN TokenDetails(
    token: "token-" + str(callback_invocations.length),
    expires: now() + 1000  # Very short expiry for testing
  )
}

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, { "time": 1234567890000 })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(authCallback: mock_auth_callback))
```

### Test Steps
```pseudo
# First authorize with custom params
AWAIT client.auth.authorize(
  tokenParams: TokenParams(clientId: "saved-client", ttl: 3600000)
)

# Wait for token to expire
WAIT 1500 milliseconds

# Force re-auth via request - should reuse saved params
AWAIT client.time()
```

### Assertions
```pseudo
# Second callback should have received the saved params
ASSERT callback_invocations[1].clientId == "saved-client"
ASSERT callback_invocations[1].ttl == 3600000
```

---

## RSA10g - authorize() updates Auth.tokenDetails

**Spec requirement:** After `authorize()`, `auth.tokenDetails` reflects the new token.

Tests that after `authorize()`, `auth.tokenDetails` reflects the new token.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, {
      "token": "new-token",
      "expires": now() + 3600000,
      "keyName": "appId.keyId",
      "clientId": "token-client"
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
ASSERT client.auth.tokenDetails IS null  # Before authorize

result = AWAIT client.auth.authorize()
```

### Assertions
```pseudo
ASSERT client.auth.tokenDetails IS NOT null
ASSERT client.auth.tokenDetails.token == "new-token"
ASSERT client.auth.tokenDetails.clientId == "token-client"
ASSERT client.auth.tokenDetails == result  # Same object
```

---

## RSA10h - authorize() with authOptions replaces defaults

**Spec requirement:** `authOptions` in `authorize()` replaces stored auth options.

Tests that `authOptions` in `authorize()` replaces stored auth options.

### Setup
```pseudo
original_callback_called = false
new_callback_called = false

original_callback = (params) => {
  original_callback_called = true
  RETURN TokenDetails(token: "original", expires: now() + 3600000)
}

new_callback = (params) => {
  new_callback_called = true
  RETURN TokenDetails(token: "new", expires: now() + 3600000)
}

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(authCallback: original_callback))
```

### Test Steps
```pseudo
AWAIT client.auth.authorize(
  authOptions: AuthOptions(authCallback: new_callback)
)
```

### Assertions
```pseudo
ASSERT original_callback_called == false
ASSERT new_callback_called == true
```

---

## RSA10i - authorize() preserves key from constructor

**Spec requirement:** The API key from `ClientOptions` is preserved even when `authOptions` are provided.

Tests that the API key from `ClientOptions` is preserved even when `authOptions` are provided.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.path matches "/keys/.*/requestToken":
      # Initial token request using key
      req.respond_with(200, {
        "token": "token-via-key",
        "expires": now() + 3600000,
        "keyName": "appId.keyId"
      })
    ELSE:
      req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Call authorize with new authUrl but no key
AWAIT client.auth.authorize(
  authOptions: AuthOptions(
    authUrl: "https://new-auth.example.com/token"
  )
)

# The key should still be available for signing
# Implementation can still use key for requestToken
```

### Assertions
```pseudo
# Key from constructor should be preserved (not cleared)
# Exact assertion depends on whether auth.key is exposed
# Verify by checking that key-based operations still work
```

---

## RSA10j - authorize() when already authorized

**Spec requirement:** Calling `authorize()` when a valid token exists obtains a new token.

Tests that calling `authorize()` when a valid token exists obtains a new token.

### Setup
```pseudo
token_count = 0

mock_auth_callback = (params) => {
  token_count = token_count + 1
  RETURN TokenDetails(
    token: "token-" + str(token_count),
    expires: now() + 3600000
  )
}

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, {"channelId": "test"})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(authCallback: mock_auth_callback))
```

### Test Steps
```pseudo
result1 = AWAIT client.auth.authorize()
result2 = AWAIT client.auth.authorize()
```

### Assertions
```pseudo
ASSERT result1.token == "token-1"
ASSERT result2.token == "token-2"
ASSERT client.auth.tokenDetails.token == "token-2"
```

---

## RSA10k - authorize() with queryTime option

**Spec requirement:** `queryTime: true` causes time to be queried from server before requesting token.

Tests that `queryTime: true` causes time to be queried from server.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.url.path == "/time":
      # Time query
      req.respond_with(200, { "time": 1234567890000 })
    ELSE:
      # Token request
      req.respond_with(200, {
        "token": "time-synced-token",
        "expires": 1234567890000 + 3600000
      })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.auth.authorize(
  authOptions: AuthOptions(queryTime: true)
)
```

### Assertions
```pseudo
# Should have made two requests: time query + token request
time_request = captured_requests.find(r => r.url.path == "/time")
ASSERT time_request IS NOT null
```

---

## RSA10l - authorize() error handling

**Spec requirement:** Errors during authorization are properly propagated to the caller.

Tests that errors during authorization are properly propagated.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
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

client = Rest(options: ClientOptions(key: "invalid.key:secret"))
```

### Test Steps
```pseudo
TRY:
  AWAIT client.auth.authorize()
  FAIL("Expected exception")
CATCH AblyException as e:
  ASSERT e.code == 40100
  ASSERT e.statusCode == 401
```
