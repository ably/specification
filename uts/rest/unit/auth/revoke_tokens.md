# Revoke Tokens Tests

Spec points: `RSA17`, `RSA17b`, `RSA17c`, `RSA17d`, `RSA17e`, `RSA17f`, `RSA17g`, `BAR2`, `TRS2`, `TRF2`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification. These tests use the same `MockHttpClient` interface with `PendingConnection` and `PendingRequest`.

## Server Response Format

With `X-Ably-Version >= 3` (sent by all current SDKs), the server returns a
`BatchResult` envelope for all batch responses:

```json
{
  "successCount": 1,
  "failureCount": 1,
  "results": [
    { "target": "clientId:alice", "issuedBefore": 1700000000000, "appliesAt": 1700000001000 },
    { "target": "invalidType:abc", "error": { "code": 40000, "statusCode": 400, "message": "..." } }
  ]
}
```

- **All success** returns HTTP 201 with this format.
- **Mixed success/failure** returns HTTP 201 with this format (not HTTP 400).
- **Server-level errors** (HTTP 500, 401, etc.) return an error object: `{"error": {...}}`.

The SDK passes through this response directly — no client-side normalisation
is needed because the server provides `successCount`, `failureCount`, and `results`.

**Legacy format (no version header):** Without `X-Ably-Version`, the server
returns a plain array for all-success and `{error, batchResponse}` for mixed
results (HTTP 400). This format is not used by current SDKs.

---

## RSA17g - revokeTokens sends POST to /keys/{keyName}/revokeTokens

**Spec requirement:** `Auth#revokeTokens` takes a `TokenRevocationTargetSpecifier` or
an array of `TokenRevocationTargetSpecifier`s and sends them in a POST request to
`/keys/{API_KEY_NAME}/revokeTokens`, where `API_KEY_NAME` is the API key name
obtained by reading `AuthOptions#key` up until the first `:` character.

### RSA17g_1 - Sends POST request to correct path

**Test ID**: `rest/unit/RSA17g/sends-post-correct-path-0`

**Spec requirement:** revokeTokens sends a POST request to `/keys/{keyName}/revokeTokens`.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      { "target": "clientId:alice", "issuedBefore": 1700000000000, "appliesAt": 1700000001000 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: "alice")
])
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
ASSERT captured_requests[0].method == "POST"
ASSERT captured_requests[0].url.path == "/keys/appId.keyName/revokeTokens"
```

---

## RSA17b - Target specifiers mapped to type:value strings

**Spec requirement:** The `TokenRevocationTargetSpecifier`s should be mapped to
strings by joining the `type` and `value` with a `:` character and sent in the
`targets` field of the request body.

### RSA17b_1 - Single specifier sent as targets array

**Test ID**: `rest/unit/RSA17b/single-specifier-targets-0`

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      { "target": "clientId:alice", "issuedBefore": 1700000000000, "appliesAt": 1700000001000 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: "alice")
])
```

### Assertions
```pseudo
request_body = JSON_PARSE(captured_requests[0].body)
ASSERT request_body["targets"] == ["clientId:alice"]
```

### RSA17b_2 - Multiple specifiers with different types

**Test ID**: `rest/unit/RSA17b/multiple-specifier-types-1`

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      { "target": "clientId:alice", "issuedBefore": 1700000000000, "appliesAt": 1700000001000 },
      { "target": "revocationKey:group-1", "issuedBefore": 1700000000000, "appliesAt": 1700000001000 },
      { "target": "channel:secret", "issuedBefore": 1700000000000, "appliesAt": 1700000001000 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: "alice"),
  TokenRevocationTargetSpecifier(type: "revocationKey", value: "group-1"),
  TokenRevocationTargetSpecifier(type: "channel", value: "secret")
])
```

### Assertions
```pseudo
request_body = JSON_PARSE(captured_requests[0].body)
ASSERT request_body["targets"] == ["clientId:alice", "revocationKey:group-1", "channel:secret"]
```

---

## RSA17c - Returns BatchResult

| Spec | Requirement |
|------|-------------|
| RSA17c | Returns a `BatchResult<TokenRevocationSuccessResult \| TokenRevocationFailureResult>` |
| BAR2a | `successCount` - the number of successful operations |
| BAR2b | `failureCount` - the number of unsuccessful operations |
| BAR2c | `results` - an array of results |

### RSA17c_1 - All success result

**Test ID**: `rest/unit/RSA17c/all-success-result-0`

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, [
      { "target": "clientId:alice", "issuedBefore": 1700000000000, "appliesAt": 1700000001000 },
      { "target": "clientId:bob", "issuedBefore": 1700000000000, "appliesAt": 1700000002000 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: "alice"),
  TokenRevocationTargetSpecifier(type: "clientId", value: "bob")
])
```

### Assertions
```pseudo
ASSERT result.successCount == 2
ASSERT result.failureCount == 0
ASSERT result.results.length == 2
```

### RSA17c_2 - Mixed success and failure result

**Test ID**: `rest/unit/RSA17c/mixed-success-failure-1`

**Spec requirement:** When the server returns a mix of successes and failures,
the response is HTTP 200 with a `BatchResult` envelope.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, {
      "successCount": 1,
      "failureCount": 1,
      "results": [
        { "target": "clientId:alice", "issuedBefore": 1700000000000, "appliesAt": 1700000001000 },
        { "target": "invalidType:abc", "error": { "code": 40000, "statusCode": 400, "message": "Invalid target type" } }
      ]
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: "alice"),
  TokenRevocationTargetSpecifier(type: "invalidType", value: "abc")
])
```

### Assertions
```pseudo
ASSERT result.successCount == 1
ASSERT result.failureCount == 1
ASSERT result.results.length == 2
```

### RSA17c_3 - All failure result

**Test ID**: `rest/unit/RSA17c/all-failure-result-2`

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, {
      "successCount": 0,
      "failureCount": 2,
      "results": [
        { "target": "invalidType:foo", "error": { "code": 40000, "statusCode": 400, "message": "Invalid target type" } },
        { "target": "invalidType:bar", "error": { "code": 40000, "statusCode": 400, "message": "Invalid target type" } }
      ]
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "invalidType", value: "foo"),
  TokenRevocationTargetSpecifier(type: "invalidType", value: "bar")
])
```

### Assertions
```pseudo
ASSERT result.successCount == 0
ASSERT result.failureCount == 2
ASSERT result.results.length == 2
```

---

## TRS2 - TokenRevocationSuccessResult attributes

| Spec | Requirement |
|------|-------------|
| TRS2a | `target` string - the target specifier |
| TRS2b | `appliesAt` Time - timestamp at which the revocation takes effect |
| TRS2c | `issuedBefore` Time - timestamp for which previously issued tokens are revoked |

### TRS2_1 - Success result contains target, appliesAt, and issuedBefore

**Test ID**: `rest/unit/TRS2/success-result-attributes-0`

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, [
      { "target": "clientId:alice", "issuedBefore": 1700000000000, "appliesAt": 1700000001000 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: "alice")
])
```

### Assertions
```pseudo
success = result.results[0]
ASSERT success IS TokenRevocationSuccessResult
ASSERT success.target == "clientId:alice"
ASSERT success.issuedBefore == 1700000000000
ASSERT success.appliesAt == 1700000001000
```

---

## TRF2 - TokenRevocationFailureResult attributes

| Spec | Requirement |
|------|-------------|
| TRF2a | `target` string - the target specifier |
| TRF2b | `error` ErrorInfo - reason the revocation failed |

### TRF2_1 - Failure result contains target and error

**Test ID**: `rest/unit/TRF2/failure-result-attributes-0`

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, {
      "successCount": 0,
      "failureCount": 1,
      "results": [
        { "target": "invalidType:abc", "error": { "code": 40000, "statusCode": 400, "message": "Invalid target type" } }
      ]
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "invalidType", value: "abc")
])
```

### Assertions
```pseudo
failure = result.results[0]
ASSERT failure IS TokenRevocationFailureResult
ASSERT failure.target == "invalidType:abc"
ASSERT failure.error IS ErrorInfo
ASSERT failure.error.code == 40000
ASSERT failure.error.statusCode == 400
ASSERT failure.error.message CONTAINS "Invalid target type"
```

---

## RSA17d - Token auth clients cannot revoke tokens

**Spec requirement:** If called from a client using token authentication, should
raise an `ErrorInfo` with a `40162` error code and `401` status code. This is a
client-side check — no HTTP request is made.

### RSA17d_1 - Token auth client fails with 40162

**Test ID**: `rest/unit/RSA17d/token-auth-revoke-rejected-0`

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(token: "a.token.string"))
```

### Test Steps
```pseudo
AWAIT client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: "alice")
]) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40162
ASSERT error.statusCode == 401

# No HTTP request should have been made
ASSERT captured_requests.length == 0
```

### RSA17d_2 - Token auth via useTokenAuth flag fails with 40162

**Test ID**: `rest/unit/RSA17d/use-token-auth-revoke-rejected-1`

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret", useTokenAuth: true))
```

### Test Steps
```pseudo
AWAIT client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: "alice")
]) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40162
ASSERT error.statusCode == 401
ASSERT captured_requests.length == 0
```

---

## RSA17e - Optional issuedBefore parameter

**Spec requirement:** Accepts an optional `issuedBefore` timestamp, represented as
milliseconds since the epoch, which is included in the request body.

### RSA17e_1 - issuedBefore included in request body

**Test ID**: `rest/unit/RSA17e/issued-before-included-0`

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      { "target": "clientId:alice", "issuedBefore": 1699999000000, "appliesAt": 1700000001000 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.auth.revokeTokens(
  [TokenRevocationTargetSpecifier(type: "clientId", value: "alice")],
  options: { issuedBefore: 1699999000000 }
)
```

### Assertions
```pseudo
request_body = JSON_PARSE(captured_requests[0].body)
ASSERT request_body["issuedBefore"] == 1699999000000
```

### RSA17e_2 - issuedBefore omitted when not provided

**Test ID**: `rest/unit/RSA17e/issued-before-omitted-1`

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      { "target": "clientId:alice", "issuedBefore": 1700000000000, "appliesAt": 1700000001000 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: "alice")
])
```

### Assertions
```pseudo
request_body = JSON_PARSE(captured_requests[0].body)
ASSERT "issuedBefore" NOT IN request_body
```

---

## RSA17f - Optional allowReauthMargin parameter

**Spec requirement:** If an `allowReauthMargin` boolean is supplied, it should be
included in the `allowReauthMargin` field of the request body.

### RSA17f_1 - allowReauthMargin included when true

**Test ID**: `rest/unit/RSA17f/reauth-margin-included-0`

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      { "target": "clientId:alice", "issuedBefore": 1700000000000, "appliesAt": 1700000030000 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.auth.revokeTokens(
  [TokenRevocationTargetSpecifier(type: "clientId", value: "alice")],
  options: { allowReauthMargin: true }
)
```

### Assertions
```pseudo
request_body = JSON_PARSE(captured_requests[0].body)
ASSERT request_body["allowReauthMargin"] == true
```

### RSA17f_2 - allowReauthMargin omitted when not provided

**Test ID**: `rest/unit/RSA17f/reauth-margin-omitted-1`

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      { "target": "clientId:alice", "issuedBefore": 1700000000000, "appliesAt": 1700000001000 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: "alice")
])
```

### Assertions
```pseudo
request_body = JSON_PARSE(captured_requests[0].body)
ASSERT "allowReauthMargin" NOT IN request_body
```

### RSA17f_3 - Both issuedBefore and allowReauthMargin together

**Test ID**: `rest/unit/RSA17f/both-options-together-2`

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      { "target": "clientId:alice", "issuedBefore": 1699999000000, "appliesAt": 1700000030000 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.auth.revokeTokens(
  [TokenRevocationTargetSpecifier(type: "clientId", value: "alice")],
  options: { issuedBefore: 1699999000000, allowReauthMargin: true }
)
```

### Assertions
```pseudo
request_body = JSON_PARSE(captured_requests[0].body)
ASSERT request_body["targets"] == ["clientId:alice"]
ASSERT request_body["issuedBefore"] == 1699999000000
ASSERT request_body["allowReauthMargin"] == true
```

---

## Error handling

### RSA17_Error_1 - Server error is propagated as an error

**Test ID**: `rest/unit/RSA17/server-error-propagated-0`

**Spec requirement:** A server-level error (e.g. 500) for the entire request
is propagated as an error, not a per-target failure.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(500, {
      "error": { "code": 50000, "statusCode": 500, "message": "Internal error" }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: "alice")
]) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 50000
ASSERT error.statusCode == 500
```

---

## Request authentication

### RSA17_Auth_1 - Request uses Basic authentication

**Test ID**: `rest/unit/RSA17/request-uses-basic-auth-0`

**Spec requirement:** revokeTokens requires key-based auth (RSA17d rejects token
auth). The POST request uses the client's configured Basic authentication.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      { "target": "clientId:alice", "issuedBefore": 1700000000000, "appliesAt": 1700000001000 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyName:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: "alice")
])
```

### Assertions
```pseudo
ASSERT captured_requests[0].headers["Authorization"] STARTS WITH "Basic "
```
