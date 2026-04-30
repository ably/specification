# Auth.tokenDetails Tests

Spec points: `RSA16`, `RSA16a`, `RSA16b`, `RSA16c`, `RSA16d`

## Test Type
Unit test with mocked HTTP client and/or mocked authCallback

## Overview

`Auth#tokenDetails` is a property that holds the `TokenDetails` representing the token currently in use by the library. These tests verify:
- It holds the current token when using token auth
- It handles tokens provided as strings (without full TokenDetails)
- It is updated on authorize() and library-initiated renewals
- It is null when using basic auth or when no valid token exists

## Mock HTTP Infrastructure

See `uts/test/rest/unit/rest_client.md` for the full Mock HTTP Infrastructure specification.

---

## RSA16a - tokenDetails holds current token

**Spec requirement:** `Auth#tokenDetails` holds a `TokenDetails` representing the token currently in use by the library, if any.

### Test: tokenDetails reflects token from authCallback

#### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, {"channelId": "test", "status": {"isActive": true}})
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  authCallback: (params) => TokenDetails(
    token: "callback-token-abc",
    expires: now() + 3600000,
    issued: now(),
    clientId: "my-client"
  )
))
```

#### Test Steps
```pseudo
# Force token acquisition by making a request
AWAIT client.channels.get("test").status()
```

#### Assertions
```pseudo
ASSERT client.auth.tokenDetails IS NOT null
ASSERT client.auth.tokenDetails.token == "callback-token-abc"
ASSERT client.auth.tokenDetails.clientId == "my-client"
ASSERT client.auth.tokenDetails.expires IS NOT null
ASSERT client.auth.tokenDetails.issued IS NOT null
```

---

### Test: tokenDetails reflects token from requestToken

#### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    IF req.path matches "/keys/.*/requestToken":
      req.respond_with(200, {
        "token": "requested-token-xyz",
        "expires": now() + 3600000,
        "issued": now(),
        "keyName": "appId.keyId",
        "clientId": "token-client"
      })
    ELSE:
      req.respond_with(200, {"channelId": "test", "status": {"isActive": true}})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

#### Test Steps
```pseudo
# Explicitly authorize to get a token
AWAIT client.auth.authorize()
```

#### Assertions
```pseudo
ASSERT client.auth.tokenDetails IS NOT null
ASSERT client.auth.tokenDetails.token == "requested-token-xyz"
ASSERT client.auth.tokenDetails.clientId == "token-client"
```

---

## RSA16b - tokenDetails with token string only

**Spec requirement:** If the library is provided with a token without the corresponding `TokenDetails`, then `tokenDetails` holds a `TokenDetails` instance in which only the `token` attribute is populated with that token string.

### Test: tokenDetails created from token string in ClientOptions

#### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, {"channelId": "test", "status": {"isActive": true}})
)
install_mock(mock_http)

# Provide only a token string, not full TokenDetails
client = Rest(options: ClientOptions(token: "standalone-token-string"))
```

#### Test Steps
```pseudo
# Access tokenDetails immediately after construction
token_details = client.auth.tokenDetails
```

#### Assertions
```pseudo
ASSERT token_details IS NOT null
ASSERT token_details.token == "standalone-token-string"
# Other fields should be null since we only had the token string
ASSERT token_details.expires IS null
ASSERT token_details.issued IS null
ASSERT token_details.clientId IS null
ASSERT token_details.capability IS null
```

---

### Test: tokenDetails created from token string in authCallback

#### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, {"channelId": "test", "status": {"isActive": true}})
)
install_mock(mock_http)

# authCallback returns just a token string, not TokenDetails
client = Rest(options: ClientOptions(
  authCallback: (params) => "just-a-token-string"
))
```

#### Test Steps
```pseudo
# Force token acquisition
AWAIT client.channels.get("test").status()
```

#### Assertions
```pseudo
ASSERT client.auth.tokenDetails IS NOT null
ASSERT client.auth.tokenDetails.token == "just-a-token-string"
# Other fields should be null
ASSERT client.auth.tokenDetails.expires IS null
ASSERT client.auth.tokenDetails.issued IS null
```

---

## RSA16c - tokenDetails updated on token changes

**Spec requirement:** `tokenDetails` is set with the current token (if applicable) on instantiation and each time it is replaced, whether the result of an explicit `Auth#authorize` operation, or a library-initiated renewal resulting from expiry or a token error response.

### Test: tokenDetails set on instantiation with tokenDetails option

#### Setup
```pseudo
initial_token = TokenDetails(
  token: "initial-token",
  expires: now() + 3600000,
  issued: now(),
  clientId: "initial-client"
)

client = Rest(options: ClientOptions(tokenDetails: initial_token))
```

#### Test Steps
```pseudo
# Access tokenDetails immediately after construction
token_details = client.auth.tokenDetails
```

#### Assertions
```pseudo
ASSERT token_details IS NOT null
ASSERT token_details.token == "initial-token"
ASSERT token_details.clientId == "initial-client"
```

---

### Test: tokenDetails updated after explicit authorize()

#### Setup
```pseudo
token_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, {"channelId": "test", "status": {"isActive": true}})
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  authCallback: (params) => {
    token_count = token_count + 1
    RETURN TokenDetails(
      token: "token-v" + str(token_count),
      expires: now() + 3600000,
      clientId: "client-v" + str(token_count)
    )
  }
))
```

#### Test Steps
```pseudo
# First authorize
AWAIT client.auth.authorize()
first_token = client.auth.tokenDetails

# Second authorize
AWAIT client.auth.authorize()
second_token = client.auth.tokenDetails
```

#### Assertions
```pseudo
ASSERT first_token.token == "token-v1"
ASSERT first_token.clientId == "client-v1"

ASSERT second_token.token == "token-v2"
ASSERT second_token.clientId == "client-v2"

# Verify it's actually updated, not the same object
ASSERT first_token.token != second_token.token
```

---

### Test: tokenDetails updated after library-initiated renewal on expiry

#### Setup
```pseudo
test_clock = TestClock()
token_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, {"channelId": "test", "status": {"isActive": true}})
)
install_mock(mock_http)

WITH_CLOCK(test_clock):
  client = Rest(options: ClientOptions(
    authCallback: (params) => {
      token_count = token_count + 1
      RETURN TokenDetails(
        token: "token-v" + str(token_count),
        expires: test_clock.now() + 1000,  # Expires in 1 second
        clientId: "client-v" + str(token_count)
      )
    }
  ))
```

#### Test Steps
```pseudo
WITH_CLOCK(test_clock):
  # First request - gets initial token
  AWAIT client.channels.get("test").status()
  first_token = client.auth.tokenDetails
  
  # Advance time past token expiry
  test_clock.advance(2000 milliseconds)
  
  # Second request - should trigger renewal
  AWAIT client.channels.get("test").status()
  second_token = client.auth.tokenDetails
```

#### Assertions
```pseudo
ASSERT first_token.token == "token-v1"
ASSERT second_token.token == "token-v2"
```

---

### Test: tokenDetails updated after library-initiated renewal on 40142 error

#### Setup
```pseudo
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    request_count = request_count + 1
    IF request_count == 1:
      # First request fails with token expired error
      req.respond_with(401, {
        "error": {
          "code": 40142,
          "statusCode": 401,
          "message": "Token expired"
        }
      })
    ELSE:
      # Subsequent requests succeed
      req.respond_with(200, {"channelId": "test", "status": {"isActive": true}})
  }
)
install_mock(mock_http)

token_count = 0

client = Rest(options: ClientOptions(
  authCallback: (params) => {
    token_count = token_count + 1
    RETURN TokenDetails(
      token: "token-v" + str(token_count),
      expires: now() + 3600000,
      clientId: "client-v" + str(token_count)
    )
  }
))
```

#### Test Steps
```pseudo
# First get a token
AWAIT client.auth.authorize()
first_token = client.auth.tokenDetails

# Make a request that will fail with 40142, triggering renewal
AWAIT client.channels.get("test").status()
second_token = client.auth.tokenDetails
```

#### Assertions
```pseudo
ASSERT first_token.token == "token-v1"
ASSERT second_token.token == "token-v2"
```

---

## RSA16d - tokenDetails is null when appropriate

**Spec requirement:** `tokenDetails` is `null` if there is no current token, including after a previous token has been determined to be invalid or expired, or if the library is using basic auth.

### Test: tokenDetails is null when using basic auth

#### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, {"channelId": "test", "status": {"isActive": true}})
)
install_mock(mock_http)

# Client with only API key - uses basic auth
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

#### Test Steps
```pseudo
# Make a request using basic auth (no token)
AWAIT client.channels.get("test").status()
```

#### Assertions
```pseudo
# Should be null because we're using basic auth, not token auth
ASSERT client.auth.tokenDetails IS null
```

---

### Test: tokenDetails is null before any token is obtained

#### Setup
```pseudo
# Client configured for token auth but no request made yet
client = Rest(options: ClientOptions(
  authCallback: (params) => TokenDetails(
    token: "my-token",
    expires: now() + 3600000
  )
))
```

#### Test Steps
```pseudo
# Don't make any requests - just check tokenDetails
token_details = client.auth.tokenDetails
```

#### Assertions
```pseudo
# Should be null because no token has been obtained yet
ASSERT token_details IS null
```

---

### Test: tokenDetails is null after token invalidation

**Note:** This test verifies behavior when a token error occurs and cannot be renewed (e.g., authCallback fails).

#### Setup
```pseudo
callback_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    # Always fail with token error
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

client = Rest(options: ClientOptions(
  authCallback: (params) => {
    callback_count = callback_count + 1
    IF callback_count == 1:
      RETURN TokenDetails(token: "first-token", expires: now() + 3600000)
    ELSE:
      # Second callback fails - cannot renew
      THROW AblyException("Cannot obtain new token")
  }
))
```

#### Test Steps
```pseudo
# First authorize succeeds
AWAIT client.auth.authorize()
ASSERT client.auth.tokenDetails IS NOT null
ASSERT client.auth.tokenDetails.token == "first-token"

# Make a request that fails with 40142
# Renewal will be attempted but will fail
AWAIT client.channels.get("test").status() FAILS WITH error
# Expected to fail - error is expected
```

#### Assertions
```pseudo
# After failed renewal, tokenDetails should be null
# (the old token is invalid and we couldn't get a new one)
ASSERT client.auth.tokenDetails IS null
```

---

### Test: tokenDetails is null after switching from token to basic auth

**Note:** This tests the case where a client is reconfigured to use basic auth after having used token auth.

#### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, {"channelId": "test", "status": {"isActive": true}})
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  authCallback: (params) => TokenDetails(
    token: "my-token",
    expires: now() + 3600000
  )
))
```

#### Test Steps
```pseudo
# First use token auth
AWAIT client.auth.authorize()
ASSERT client.auth.tokenDetails IS NOT null

# Now authorize with basic auth (providing key in authOptions)
AWAIT client.auth.authorize(
  authOptions: AuthOptions(
    key: "appId.keyId:keySecret",
    useTokenAuth: false
  )
)
```

#### Assertions
```pseudo
# After switching to basic auth, tokenDetails should be null
ASSERT client.auth.tokenDetails IS null
```

---

## Edge Cases

### Test: tokenDetails preserved across multiple successful requests

#### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, {"channelId": "test", "status": {"isActive": true}})
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  authCallback: (params) => TokenDetails(
    token: "stable-token",
    expires: now() + 3600000,
    clientId: "stable-client"
  )
))
```

#### Test Steps
```pseudo
# Make multiple requests
AWAIT client.channels.get("test").status()
first_check = client.auth.tokenDetails

AWAIT client.channels.get("test").status()
second_check = client.auth.tokenDetails

AWAIT client.channels.get("test").status()
third_check = client.auth.tokenDetails
```

#### Assertions
```pseudo
# Token should remain the same across requests (not re-fetched)
ASSERT first_check.token == "stable-token"
ASSERT second_check.token == "stable-token"
ASSERT third_check.token == "stable-token"
```

---

### Test: tokenDetails reflects capability from token

#### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, {"channelId": "test", "status": {"isActive": true}})
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  authCallback: (params) => TokenDetails(
    token: "capable-token",
    expires: now() + 3600000,
    capability: '{"channel1":["publish","subscribe"],"channel2":["subscribe"]}'
  )
))
```

#### Test Steps
```pseudo
AWAIT client.channels.get("test").status()
```

#### Assertions
```pseudo
ASSERT client.auth.tokenDetails IS NOT null
ASSERT client.auth.tokenDetails.capability == '{"channel1":["publish","subscribe"],"channel2":["subscribe"]}'
```
