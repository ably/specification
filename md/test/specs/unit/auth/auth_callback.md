# Auth Callback Tests

Spec points: `RSA8c`, `RSA8c1a`, `RSA8c1b`, `RSA8c1c`, `RSA8c2`, `RSA8c3`, `RSA8d`

## Test Type
Unit test with mocked HTTP client and/or mocked authCallback

## Mock Configuration

### HTTP Client Mock
Captures requests and returns configurable responses.

### authCallback Mock
A function that can be configured to:
- Return various token types (TokenDetails, TokenRequest, token string)
- Throw errors
- Track invocation count and parameters

---

## RSA8d - authCallback invocation

Tests that `authCallback` is invoked with `TokenParams` and returns token.

### Setup
```pseudo
callback_invocations = []

mock_auth_callback = (token_params) => {
  callback_invocations.append(token_params)
  RETURN TokenDetails(
    token: "mock-token-string",
    expires: now() + 3600000,  # 1 hour from now
    clientId: "callback-client"
  )
}

mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  authCallback: mock_auth_callback,
  clientId: "test-client"
))
```

### Test Steps
```pseudo
# Trigger auth by making a request
channel = client.channels.get("test")
AWAIT channel.publish(name: "event", data: "data")
```

### Assertions
```pseudo
# Callback was invoked
ASSERT callback_invocations.length >= 1

# TokenParams were passed
token_params = callback_invocations[0]
ASSERT token_params IS TokenParams

# Token was used in request
request = mock_http.captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer mock-token-string"
```

---

## RSA8d - authCallback returns different token types

Tests that authCallback can return TokenDetails, TokenRequest, or token string.

### Test Cases

| ID | Return Type | Return Value | Expected Behavior |
|----|-------------|--------------|-------------------|
| 1 | `TokenDetails` | `TokenDetails(token: "tok1", ...)` | Token used directly |
| 2 | `String` (token) | `"raw-token-string"` | String used as token |
| 3 | `TokenRequest` | `TokenRequest(keyName: "...", ...)` | Exchanged for token via Ably |

### Setup (Case 1 - TokenDetails)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  authCallback: (params) => TokenDetails(
    token: "callback-token",
    expires: now() + 3600000
  )
))
```

### Test Steps (Case 1)
```pseudo
AWAIT client.channels.get("test").publish(name: "e", data: "d")

request = mock_http.captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer callback-token"
```

### Setup (Case 2 - String)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  authCallback: (params) => "raw-string-token"
))
```

### Test Steps (Case 2)
```pseudo
AWAIT client.channels.get("test").publish(name: "e", data: "d")

request = mock_http.captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer raw-string-token"
```

### Setup (Case 3 - TokenRequest)
```pseudo
mock_http = MockHttpClient()
# First request: exchange TokenRequest for TokenDetails
mock_http.queue_response(200, {
  "token": "exchanged-token",
  "expires": now() + 3600000,
  "keyName": "appId.keyId"
})
# Second request: actual publish
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  authCallback: (params) => TokenRequest(
    keyName: "appId.keyId",
    ttl: 3600000,
    timestamp: now(),
    nonce: "unique-nonce",
    mac: "valid-mac-signature"
  )
))
```

### Test Steps (Case 3)
```pseudo
AWAIT client.channels.get("test").publish(name: "e", data: "d")

# First request should be token exchange
ASSERT mock_http.captured_requests[0].url.path == "/keys/appId.keyId/requestToken"

# Second request should use exchanged token
ASSERT mock_http.captured_requests[1].headers["Authorization"] == "Bearer exchanged-token"
```

---

## RSA8c - authUrl queries URL for token

Tests that `authUrl` is queried to obtain a token.

### Setup
```pseudo
mock_http = MockHttpClient()

# Response from authUrl
mock_http.queue_response_for_host("auth.example.com", 200,
  body: { "token": "authurl-token", "expires": now() + 3600000 },
  headers: { "Content-Type": "application/json" }
)

# Response from Ably for publish
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  authUrl: "https://auth.example.com/get-token"
))
```

### Test Steps
```pseudo
AWAIT client.channels.get("test").publish(name: "e", data: "d")
```

### Assertions
```pseudo
# First request goes to authUrl
auth_request = mock_http.captured_requests[0]
ASSERT auth_request.url.host == "auth.example.com"
ASSERT auth_request.url.path == "/get-token"

# Subsequent request uses obtained token
publish_request = mock_http.captured_requests[1]
ASSERT publish_request.headers["Authorization"] == "Bearer authurl-token"
```

---

## RSA8c1a - authUrl with GET method

Tests that TokenParams and authParams are sent as query string for GET requests.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response_for_host("auth.example.com", 200,
  body: "plain-token-string",
  headers: { "Content-Type": "text/plain" }
)
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  authUrl: "https://auth.example.com/token",
  authMethod: "GET",
  authParams: { "custom": "param1" },
  authHeaders: { "X-Custom-Header": "value1" }
))
```

### Test Steps
```pseudo
AWAIT client.channels.get("test").publish(name: "e", data: "d")
```

### Assertions
```pseudo
auth_request = mock_http.captured_requests[0]

ASSERT auth_request.method == "GET"
ASSERT auth_request.url.query_params["custom"] == "param1"
# TokenParams should also be in query string (e.g., timestamp if present)
ASSERT auth_request.headers["X-Custom-Header"] == "value1"
ASSERT auth_request.body IS empty
```

---

## RSA8c1b - authUrl with POST method

Tests that TokenParams and authParams are form-encoded in body for POST requests.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response_for_host("auth.example.com", 200,
  body: { "token": "post-token" },
  headers: { "Content-Type": "application/json" }
)
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  authUrl: "https://auth.example.com/token",
  authMethod: "POST",
  authParams: { "custom": "param1" },
  authHeaders: { "X-Custom-Header": "value1" }
))
```

### Test Steps
```pseudo
AWAIT client.channels.get("test").publish(name: "e", data: "d")
```

### Assertions
```pseudo
auth_request = mock_http.captured_requests[0]

ASSERT auth_request.method == "POST"
ASSERT auth_request.headers["Content-Type"] == "application/x-www-form-urlencoded"
ASSERT auth_request.headers["X-Custom-Header"] == "value1"

body_params = parse_form_urlencoded(auth_request.body)
ASSERT body_params["custom"] == "param1"
```

---

## RSA8c1c - authUrl preserves existing query params

Tests that existing query params in authUrl are preserved and merged.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response_for_host("auth.example.com", 200,
  body: { "token": "merged-token" },
  headers: { "Content-Type": "application/json" }
)
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  authUrl: "https://auth.example.com/token?existing=value&another=123",
  authMethod: "GET",
  authParams: { "added": "new" }
))
```

### Test Steps
```pseudo
AWAIT client.channels.get("test").publish(name: "e", data: "d")
```

### Assertions
```pseudo
auth_request = mock_http.captured_requests[0]

# All params should be present
ASSERT auth_request.url.query_params["existing"] == "value"
ASSERT auth_request.url.query_params["another"] == "123"
ASSERT auth_request.url.query_params["added"] == "new"
```

---

## RSA8c2 - TokenParams take precedence over authParams

Tests that when names conflict, TokenParams values are used.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response_for_host("auth.example.com", 200,
  body: { "token": "precedence-token" },
  headers: { "Content-Type": "application/json" }
)
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  authUrl: "https://auth.example.com/token",
  authMethod: "GET",
  authParams: { "clientId": "from-authParams", "custom": "authParams-value" },
  clientId: "from-tokenParams"  # This becomes part of TokenParams
))
```

### Test Steps
```pseudo
AWAIT client.channels.get("test").publish(name: "e", data: "d")
```

### Assertions
```pseudo
auth_request = mock_http.captured_requests[0]

# TokenParams.clientId should override authParams.clientId
ASSERT auth_request.url.query_params["clientId"] == "from-tokenParams"
# Non-conflicting authParams preserved
ASSERT auth_request.url.query_params["custom"] == "authParams-value"
```

---

## RSA8c3 - AuthOptions replaces ClientOptions defaults

Tests that authParams/authHeaders in AuthOptions replace (not merge) ClientOptions defaults.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response_for_host("auth.example.com", 200,
  body: { "token": "replaced-token" },
  headers: { "Content-Type": "application/json" }
)
mock_http.queue_response(201, { "serials": ["s1"] })

client = Rest(options: ClientOptions(
  authUrl: "https://auth.example.com/token",
  authParams: { "default1": "value1", "default2": "value2" },
  authHeaders: { "X-Default": "default-header" }
))
```

### Test Steps
```pseudo
# Call authorize with new authParams that should REPLACE defaults
AWAIT client.auth.authorize(
  authOptions: AuthOptions(
    authParams: { "override": "new-value" }  # Replaces, doesn't merge
    # No authHeaders specified - should clear the defaults
  )
)

# Trigger a request to see what auth params are used
mock_http.queue_response_for_host("auth.example.com", 200,
  body: { "token": "new-token" },
  headers: { "Content-Type": "application/json" }
)
mock_http.queue_response(201, { "serials": ["s1"] })

AWAIT client.channels.get("test").publish(name: "e", data: "d")
```

### Assertions
```pseudo
auth_request = mock_http.captured_requests_for_host("auth.example.com").last

# Only the override param should be present (defaults replaced)
ASSERT auth_request.url.query_params["override"] == "new-value"
ASSERT "default1" NOT IN auth_request.url.query_params
ASSERT "default2" NOT IN auth_request.url.query_params

# Headers should be cleared (replaced with empty)
ASSERT "X-Default" NOT IN auth_request.headers
```
