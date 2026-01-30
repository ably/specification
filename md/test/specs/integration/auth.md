# Auth Integration Tests

Spec points: `RSA4`, `RSA8`

## Test Type
Integration test against Ably sandbox

## Token Formats

All tests in this file should be run with **both**:
1. **JWTs** (primary) - Generate using a third-party JWT library
2. **Ably native tokens** - Obtained using `requestToken()`

JWT should be the primary token format. See README for details.

## Test Environment

### Prerequisites
- Ably sandbox app provisioned via `POST https://sandbox.realtime.ably-nonprod.net/apps`
- API key from provisioned app
- Channel names must be unique per test (see README for naming convention)

### Setup Pattern
```pseudo
BEFORE ALL TESTS:
  app_config = provision_sandbox_app()
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox.realtime.ably-nonprod.net/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

---

## RSA4 - Basic auth with API key

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

Tests that invalid API keys are rejected by the server.

### Setup
```pseudo
channel_name = "test-RSA4-invalid-" + random_id()
client = Rest(options: ClientOptions(
  key: "invalid.key:secret",
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
TRY:
  AWAIT client.request("GET", "/channels/" + channel_name)
  FAIL("Expected authentication error")
CATCH AblyException as e:
  ASSERT e.statusCode == 401
  ASSERT e.code >= 40100 AND e.code < 40200
```

---

## Notes

### Tests moved to unit tests

The following functionality is better tested via unit tests with a mocked HTTP client:

- **`createTokenRequest()`** (RSA9) - This is a local signing operation that doesn't require server interaction
- **`authorize()` token renewal** (RSA14) - Unit tests can explicitly confirm that a new token is used on subsequent requests
- **Token expiry and renewal cycle** (RSA4b4) - See `unit/auth/token_renewal.md`
