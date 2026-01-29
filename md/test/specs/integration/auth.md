# Auth Integration Tests

Spec points: `RSA4`, `RSA8`, `RSA9`, `RSA10`, `RSA14`, `RSA15`

## Test Type
Integration test against Ably sandbox

## Test Environment

### Prerequisites
- Ably sandbox app provisioned via `POST https://sandbox.realtime.ably-nonprod.net/apps`
- API key from provisioned app

### Setup Pattern
```pseudo
BEFORE ALL TESTS:
  app_config = provision_sandbox_app()
  api_key = app_config.keys[0].key_str

AFTER ALL TESTS:
  # Sandbox apps auto-delete after 60 minutes
```

---

## RSA4 - Basic auth with API key

Tests that API key authentication works against real server.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
result = AWAIT client.time()
```

### Assertions
```pseudo
ASSERT result IS valid timestamp
ASSERT result > 0
```

---

## RSA8 - Token auth with obtained token

Tests obtaining a token and using it for authentication.

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
# Obtain a token
token_details = AWAIT key_client.auth.requestToken()

# Create new client using only the token
token_client = Rest(options: ClientOptions(
  token: token_details.token,
  endpoint: "sandbox"
))

# Verify token works
result = AWAIT token_client.time()
```

### Assertions
```pseudo
ASSERT token_details.token IS String
ASSERT token_details.token.length > 0
ASSERT token_details.expires > now()
ASSERT result IS valid timestamp
```

---

## RSA9 - createTokenRequest creates signed request

Tests that `createTokenRequest` produces a valid, signed token request.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
token_request = AWAIT client.auth.createTokenRequest(
  tokenParams: TokenParams(
    clientId: "test-client",
    ttl: 3600000
  )
)
```

### Assertions
```pseudo
ASSERT token_request.keyName IS String
ASSERT token_request.keyName CONTAINS "."  # appId.keyId format
ASSERT token_request.timestamp IS Number
ASSERT token_request.nonce IS String
ASSERT token_request.mac IS String  # Signature
ASSERT token_request.ttl == 3600000
ASSERT token_request.clientId == "test-client"
```

---

## RSA9 - TokenRequest can be exchanged for token

Tests that a `TokenRequest` created by one client can be exchanged for a token.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
# Create token request
token_request = AWAIT client.auth.createTokenRequest()

# Exchange it for a token (simulating another client)
token_details = AWAIT client.auth.requestToken(
  tokenRequest: token_request
)
```

### Assertions
```pseudo
ASSERT token_details.token IS String
ASSERT token_details.expires > now()
```

---

## RSA10 - authorize() obtains and uses token

Tests that `authorize()` obtains a token and uses it for subsequent requests.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
# Initially using Basic auth
time1 = AWAIT client.time()

# Switch to token auth
token_details = AWAIT client.auth.authorize()

# Subsequent requests use token
time2 = AWAIT client.time()
```

### Assertions
```pseudo
ASSERT token_details IS TokenDetails
ASSERT token_details.token IS String
ASSERT client.auth.tokenDetails.token == token_details.token
```

---

## RSA14 - Token expiry and renewal

Tests that expired tokens are automatically renewed when using authCallback.

### Setup
```pseudo
# Use a very short TTL to trigger renewal
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  defaultTokenParams: TokenParams(ttl: 5000)  # 5 second TTL
))
```

### Test Steps
```pseudo
# First request obtains token
time1 = AWAIT client.time()
first_token = client.auth.tokenDetails.token

# Wait for token to expire
WAIT 6 seconds

# Next request should automatically get new token
time2 = AWAIT client.time()
second_token = client.auth.tokenDetails.token
```

### Assertions
```pseudo
ASSERT first_token IS String
ASSERT second_token IS String
ASSERT first_token != second_token  # Token was renewed
```

---

## RSA15 - Invalid credentials rejected

Tests that invalid API keys are rejected by the server.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: "invalid.key:secret",
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
TRY:
  AWAIT client.time()
  FAIL("Expected authentication error")
CATCH AblyException as e:
  ASSERT e.statusCode == 401
  ASSERT e.code >= 40100 AND e.code < 40200
```

---

## RSA15 - Expired token rejected

Tests that expired tokens are rejected and trigger re-auth.

### Setup
```pseudo
# Manually create an expired token
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

# Get a very short-lived token
token_details = AWAIT client.auth.requestToken(
  tokenParams: TokenParams(ttl: 1000)  # 1 second
)

# Wait for it to expire
WAIT 2 seconds

# Create client with expired token and no way to refresh
expired_client = Rest(options: ClientOptions(
  token: token_details.token,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
TRY:
  AWAIT expired_client.time()
  FAIL("Expected token expired error")
CATCH AblyException as e:
  ASSERT e.code == 40142 OR e.code == 40140  # Token expired codes
```

---

## RSA - clientId in token

Tests that tokens correctly carry clientId.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
token_details = AWAIT client.auth.requestToken(
  tokenParams: TokenParams(clientId: "my-client-id")
)

# Verify clientId in token
token_client = Rest(options: ClientOptions(
  token: token_details.token,
  endpoint: "sandbox"
))

# Publish to verify clientId is associated
channel = token_client.channels.get("clientid-test-" + random_string())
AWAIT channel.publish(name: "event", data: "data")

WAIT 1 second

history = AWAIT channel.history()
```

### Assertions
```pseudo
ASSERT token_details.clientId == "my-client-id"
ASSERT history.items[0].clientId == "my-client-id"
```
