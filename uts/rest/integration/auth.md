# Auth Integration Tests

Spec points: `RSA4`, `RSA8`

## Test Type
Integration test against Ably sandbox

## Token Formats

All tests in this file should be run with **both**:
1. **JWTs** (primary) - Generate using a third-party JWT library
2. **Ably native tokens** - Obtained using `requestToken()`

JWT should be the primary token format. See README for details.

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox-rest.ably.io`.

### App Provisioning

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

---

## RSA4 - Basic auth with API key

**Spec requirement:** RSA4 - Client can authenticate using an API key via HTTP Basic Auth.

Tests that API key authentication works against real server.

### Setup
```pseudo
channel_name = "test-RSA4-" + random_id()
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
# Use channel status endpoint (requires authentication)
result = AWAIT client.request("GET", "/channels/" + channel_name)
```

### Assertions
```pseudo
# Just verify the request succeeded - don't check response body
ASSERT result.statusCode >= 200 AND result.statusCode < 300
```

---

## RSA8 - Token auth with JWT

**Spec requirement:** RSA8 - Client can authenticate using a JWT token.

Tests authentication using a JWT token.

### Setup
```pseudo
# Generate a valid JWT using a third-party library
jwt = generate_jwt(
  key_name: extract_key_name(api_key),
  key_secret: extract_key_secret(api_key),
  ttl: 3600000
)

channel_name = "test-RSA8-jwt-" + random_id()
client = Rest(options: ClientOptions(
  token: jwt,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
result = AWAIT client.request("GET", "/channels/" + channel_name)
```

### Assertions
```pseudo
ASSERT result.statusCode >= 200 AND result.statusCode < 300
```

---

## RSA8 - Token auth with native token

**Spec requirement:** RSA8 - Client can authenticate using an Ably native token obtained via `requestToken()`.

Tests obtaining a native token and using it for authentication.

### Setup
```pseudo
# First client with API key to obtain token
key_client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
# Obtain a native token
token_details = AWAIT key_client.auth.requestToken()

# Create new client using only the token
channel_name = "test-RSA8-native-" + random_id()
token_client = Rest(options: ClientOptions(
  token: token_details.token,
  endpoint: "sandbox"
))

# Verify token works
result = AWAIT token_client.request("GET", "/channels/" + channel_name)
```

### Assertions
```pseudo
ASSERT token_details.token IS String
ASSERT token_details.token.length > 0
ASSERT token_details.expires > now()
ASSERT result.statusCode >= 200 AND result.statusCode < 300
```

---

## RSA8 - authCallback with TokenRequest

**Spec requirement:** RSA8 - Client can use `authCallback` to obtain authentication via `TokenRequest`.

Tests using an `authCallback` that returns a `TokenRequest`, which is then exchanged for a token.

### Setup
```pseudo
# Client that generates token requests
token_request_client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

# authCallback that creates and returns a TokenRequest
auth_callback = FUNCTION(params):
  RETURN AWAIT token_request_client.auth.createTokenRequest(params)

channel_name = "test-RSA8-callback-" + random_id()
client = Rest(options: ClientOptions(
  authCallback: auth_callback,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
result = AWAIT client.request("GET", "/channels/" + channel_name)
```

### Assertions
```pseudo
ASSERT result.statusCode >= 200 AND result.statusCode < 300
```

---

## RSA8 - authCallback with JWT

**Spec requirement:** RSA8 - Client can use `authCallback` to obtain JWT tokens dynamically.

Tests using an `authCallback` that returns a JWT.

### Setup
```pseudo
auth_callback = FUNCTION(params):
  RETURN generate_jwt(
    key_name: extract_key_name(api_key),
    key_secret: extract_key_secret(api_key),
    client_id: params.clientId,
    ttl: params.ttl OR 3600000
  )

channel_name = "test-RSA8-jwt-callback-" + random_id()
client = Rest(options: ClientOptions(
  authCallback: auth_callback,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
result = AWAIT client.request("GET", "/channels/" + channel_name)
```

### Assertions
```pseudo
ASSERT result.statusCode >= 200 AND result.statusCode < 300
```

---

## RSA4 - Invalid credentials rejected

**Spec requirement:** RSA4 - Server rejects requests with invalid API key credentials.

Tests that invalid API keys are rejected by the server.

### Setup
```pseudo
channel_name = "test-RSA4-invalid-" + random_id()

# Use the real app_id with a fabricated key name. The server returns HTTP 401
# with Ably error code 40400 (key not found).
invalid_key = app_id + ".invalidKey:invalidSecret"

client = Rest(options: ClientOptions(
  key: invalid_key,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
result = AWAIT client.request("GET", "/channels/" + channel_name)
ASSERT result.statusCode == 401
ASSERT result.errorCode == 40400
```

---

## RSC10 - Token renewal with expired JWT

**Spec requirement:** RSC10 - When a REST request fails with a token error (40140-40149), the client should automatically renew the token and retry the request.

Tests that an expired JWT triggers automatic token renewal via authCallback.

### Setup
```pseudo
# Track how many times the callback is invoked
callback_count = 0

auth_callback = FUNCTION(params):
  callback_count = callback_count + 1
  IF callback_count == 1:
    # First call: return an already-expired JWT (expired 5 seconds ago)
    RETURN generate_jwt(
      key_name: extract_key_name(api_key),
      key_secret: extract_key_secret(api_key),
      expires_at: now() - 5_seconds
    )
  ELSE:
    # Subsequent calls: return a valid JWT
    RETURN generate_jwt(
      key_name: extract_key_name(api_key),
      key_secret: extract_key_secret(api_key),
      ttl: 3600000
    )

channel_name = "test-RSC10-renewal-" + random_id()
client = Rest(options: ClientOptions(
  authCallback: auth_callback,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
# Make a REST request — first token is expired, should trigger renewal
result = AWAIT client.request("GET", "/channels/" + channel_name)
```

### Assertions
```pseudo
# The request succeeded (token was renewed and retried)
ASSERT result.statusCode >= 200 AND result.statusCode < 300

# The authCallback was called twice: once for expired token, once for renewal
ASSERT callback_count == 2
```

---

## RSA8 - Capability restriction

**Spec requirement:** RSA8 - Tokens with restricted capabilities should only allow the permitted operations.

Tests that a JWT with restricted capability is enforced by the server.

### Setup
```pseudo
# Create a JWT with capability restricted to a specific channel
allowed_channel = "test-RSA8-cap-allowed-" + random_id()
denied_channel = "test-RSA8-cap-denied-" + random_id()

jwt = generate_jwt(
  key_name: extract_key_name(api_key),
  key_secret: extract_key_secret(api_key),
  capability: '{"' + allowed_channel + '":["publish","subscribe"]}',
  ttl: 3600000
)

client = Rest(options: ClientOptions(
  token: jwt,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
# Publish to allowed channel should succeed — the JWT grants "publish" capability.
# Note: Do NOT use client.request("GET", "/channels/...") here — that is a channel
# status request which requires "channel-metadata" capability, not "publish".
AWAIT client.channels.get(allowed_channel).publish(name: "test", data: "hello")

# Publish to denied channel should fail with 40160 (capability refused)
AWAIT client.channels.get(denied_channel).publish(name: "test", data: "hello") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40160
ASSERT error.statusCode == 401
```

---

## Notes

### Tests moved to unit tests

The following functionality is better tested via unit tests with a mocked HTTP client:

- **`createTokenRequest()`** (RSA9) - This is a local signing operation that doesn't require server interaction
- **`authorize()` token renewal** (RSA14) - Unit tests can explicitly confirm that a new token is used on subsequent requests
- **Token expiry and renewal cycle** (RSA4b4) - See `unit/auth/token_renewal.md`
