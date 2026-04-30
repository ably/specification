# Client ID Tests

Spec points: `RSA7`, `RSA7a`, `RSA7b`, `RSA7c`, `RSA12`, `RSA12a`, `RSA12b`, `RSA15`, `RSA15a`, `RSA15b`, `RSA15c`

## Test Type
Unit test with mocked HTTP client and/or authCallback

## Mock HTTP Infrastructure

See `uts/test/rest/unit/rest_client.md` for the full Mock HTTP Infrastructure specification. These tests use the same `MockHttpClient` interface with `PendingConnection` and `PendingRequest`.

---

## RSA7a - clientId from ClientOptions

**Spec requirement:** `clientId` from `ClientOptions` is accessible via `auth.clientId`.

Tests that `clientId` from `ClientOptions` is accessible via `auth.clientId`.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  clientId: "my-client-id"
))
```

### Assertions
```pseudo
ASSERT client.auth.clientId == "my-client-id"
```

---

## RSA7b - clientId from TokenDetails

**Spec requirement:** `clientId` is derived from `TokenDetails` when token auth is used.

Tests that `clientId` is derived from `TokenDetails` when token auth is used.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, { "channelId": "test", "status": { "isActive": true } })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  tokenDetails: TokenDetails(
    token: "token-with-clientId",
    expires: now() + 3600000,
    clientId: "token-client-id"
  )
))
```

### Assertions
```pseudo
ASSERT client.auth.clientId == "token-client-id"
```

---

## RSA7b - clientId from authCallback TokenDetails

**Spec requirement:** `clientId` is extracted from `TokenDetails` returned by `authCallback`.

Tests that `clientId` is extracted from `TokenDetails` returned by `authCallback`.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, { "channelId": "test", "status": { "isActive": true } })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  authCallback: (params) => TokenDetails(
    token: "callback-token",
    expires: now() + 3600000,
    clientId: "callback-client-id"
  )
))
```

### Test Steps
```pseudo
# Trigger auth by making a request
AWAIT client.channels.get("test").status()
```

### Assertions
```pseudo
ASSERT client.auth.clientId == "callback-client-id"
```

---

## RSA7c - clientId null when unidentified

**Spec requirement:** `auth.clientId` is null when no client identity is established.

Tests that `auth.clientId` is null when no client identity is established.

### Setup
```pseudo
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
# No clientId specified
```

### Assertions
```pseudo
ASSERT client.auth.clientId IS null
```

---

## RSA7c - clientId null with unidentified token

**Spec requirement:** `auth.clientId` is null when token has no `clientId`.

Tests that `auth.clientId` is null when token has no `clientId`.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, { "channelId": "test", "status": { "isActive": true } })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  tokenDetails: TokenDetails(
    token: "token-without-clientId",
    expires: now() + 3600000
    # No clientId in token
  )
))
```

### Assertions
```pseudo
ASSERT client.auth.clientId IS null
```

---

## RSA12a - clientId passed to authCallback in TokenParams

**Spec requirement:** `clientId` is passed to `authCallback` via `TokenParams`.

Tests that `clientId` is passed to `authCallback` via `TokenParams`.

### Setup
```pseudo
received_params = []

mock_auth_callback = (params) => {
  received_params.append(params)
  RETURN TokenDetails(token: "tok", expires: now() + 3600000)
}

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, { "channelId": "test", "status": { "isActive": true } })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  authCallback: mock_auth_callback,
  clientId: "library-client-id"
))
```

### Test Steps
```pseudo
# Trigger auth
AWAIT client.channels.get("test").status()
```

### Assertions
```pseudo
ASSERT received_params.length >= 1
ASSERT received_params[0].clientId == "library-client-id"
```

---

## RSA12b - clientId sent to authUrl

**Spec requirement:** `clientId` is sent as a parameter when using `authUrl`.

Tests that `clientId` is sent as a parameter when using `authUrl`.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.url.host == "auth.example.com":
      req.respond_with(200, 
        body: { "token": "url-token", "expires": now() + 3600000 },
        headers: { "Content-Type": "application/json" }
      )
    ELSE:
      req.respond_with(200, { "channelId": "test", "status": { "isActive": true } })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  authUrl: "https://auth.example.com/token",
  clientId: "url-client-id"
))
```

### Test Steps
```pseudo
AWAIT client.channels.get("test").status()
```

### Assertions
```pseudo
auth_request = captured_requests[0]
ASSERT auth_request.url.host == "auth.example.com"

# clientId should be in query params (GET) or body (POST)
IF auth_request.method == "GET":
  ASSERT auth_request.url.query_params["clientId"] == "url-client-id"
ELSE:
  body_params = parse_form_urlencoded(auth_request.body)
  ASSERT body_params["clientId"] == "url-client-id"
```

---

## RSA7 - clientId updated after authorize()

**Spec requirement:** `auth.clientId` is updated when `authorize()` returns a new token with different `clientId`.

Tests that `auth.clientId` is updated when `authorize()` returns a new token with different `clientId`.

### Setup
```pseudo
token_count = 0

mock_auth_callback = (params) => {
  token_count = token_count + 1
  RETURN TokenDetails(
    token: "token-" + str(token_count),
    expires: now() + 3600000,
    clientId: "client-" + str(token_count)
  )
}

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, { "channelId": "test", "status": { "isActive": true } })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(authCallback: mock_auth_callback))
```

### Test Steps
```pseudo
# First auth
AWAIT client.channels.get("test").status()

ASSERT client.auth.clientId == "client-1"

# Second auth with explicit authorize
AWAIT client.auth.authorize()

ASSERT client.auth.clientId == "client-2"
```

---

## RSA12 - Wildcard clientId

**Spec requirement:** Wildcard `*` clientId allows the token to be used with any client identity.

Tests handling of wildcard `*` clientId.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, { "channelId": "test", "status": { "isActive": true } })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  tokenDetails: TokenDetails(
    token: "wildcard-token",
    expires: now() + 3600000,
    clientId: "*"  # Wildcard
  )
))
```

### Assertions
```pseudo
# Wildcard clientId should be preserved
ASSERT client.auth.clientId == "*"
```

### Note
The wildcard `*` clientId allows the token to be used with any client identity. This is a special case where `clientId` on individual operations can vary.

---

## RSA7 - clientId consistency between ClientOptions and token

**Spec requirement:** `clientId` in `ClientOptions` must be consistent with token's `clientId` (mismatch is an error).

Tests that `clientId` in `ClientOptions` is consistent with token's `clientId`.

### Test Cases

| ID | ClientOptions clientId | Token clientId | Expected |
|----|----------------------|----------------|----------|
| 1 | `"client-a"` | `"client-a"` | Success |
| 2 | `"client-a"` | `"client-b"` | Error |
| 3 | `"client-a"` | `null` | Success (client keeps explicit) |
| 4 | `"client-a"` | `"*"` | Success (wildcard allows any) |
| 5 | `null` | `"client-b"` | Success (inherit from token) |

### Setup (Case 2 - Mismatch should error)
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, { "channelId": "test", "status": { "isActive": true } })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  clientId: "client-a",
  tokenDetails: TokenDetails(
    token: "mismatched-token",
    expires: now() + 3600000,
    clientId: "client-b"  # Different from ClientOptions
  )
))
```

### Test Steps (Case 2)
```pseudo
AWAIT client.channels.get("test").status() FAILS WITH error  # Or any operation requiring auth
ASSERT error.message CONTAINS "clientId" OR error.message CONTAINS "mismatch"
```

### Note
The exact timing of mismatch detection (constructor vs first use) may vary by implementation. The key requirement is that the mismatch is detected and reported as an error.

---

## RSA15a - Token clientId must match ClientOptions clientId

**Spec requirement:** Any `clientId` provided in `ClientOptions` must match any non-wildcard `clientId` value in `TokenDetails`.

This is tested by the RSA7 consistency test above (cases 1 and 2). When Token Auth is used and both `ClientOptions.clientId` and `TokenDetails.clientId` are set to non-wildcard values, they must match.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, { "channelId": "test", "status": { "isActive": true } })
  }
)
install_mock(mock_http)

# Matching case — should succeed
client_match = Rest(options: ClientOptions(
  clientId: "my-client",
  tokenDetails: TokenDetails(
    token: "matching-token",
    expires: now() + 3600000,
    clientId: "my-client"
  )
))

# Mismatching case — should error
ASSERT Rest(options: ClientOptions(
  clientId: "my-client",
  tokenDetails: TokenDetails(
    token: "mismatched-token",
    expires: now() + 3600000,
    clientId: "other-client"
  )
)) THROWS error
```

### Assertions
```pseudo
ASSERT client_match.auth.clientId == "my-client"
ASSERT error.code == 40102
```

---

## RSA15b - Wildcard token clientId permits any ClientOptions clientId

**Spec requirement:** If the `clientId` from `TokenDetails` is a wildcard string `'*'`, then the client is permitted to be either unidentified or identified by providing a `clientId`.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, { "channelId": "test", "status": { "isActive": true } })
  }
)
install_mock(mock_http)

# Wildcard token with explicit clientId — should succeed
client = Rest(options: ClientOptions(
  clientId: "any-client",
  tokenDetails: TokenDetails(
    token: "wildcard-token",
    expires: now() + 3600000,
    clientId: "*"
  )
))
```

### Assertions
```pseudo
# No error thrown — wildcard allows any clientId
ASSERT client.auth.clientId == "any-client"
```

---

## RSA15c - Incompatible clientId results in error (REST) or FAILED (Realtime)

**Spec requirement:** Following an auth request which uses a `TokenDetails` that contains an incompatible `clientId`, the library should in the case of REST result in an appropriate error response, and in the case of Realtime transition the connection state to `FAILED`.

### REST case

See RSA15a mismatch case above — the REST client raises an error with code 40102.

### Realtime case

See `realtime/integration/auth.md` RSA7 test — the Realtime client transitions to FAILED state when a token with a mismatched clientId is used.
