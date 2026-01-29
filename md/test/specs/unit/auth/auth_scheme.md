# Auth Scheme Selection Tests

Spec points: `RSA1`, `RSA2`, `RSA3`, `RSA4`, `RSA4a`, `RSA4b`, `RSA4c`

## Test Type
Unit test - pure validation logic, minimal mocking required

## Mock Configuration

### HTTP Client Mock (where needed)
For tests that trigger actual requests to verify auth header format.

---

## RSA1 - API key format validation

Tests that API keys must match the expected format.

### Test Cases

| ID | Input | Expected |
|----|-------|----------|
| 1 | `"appId.keyId:keySecret"` | Valid |
| 2 | `"appId.keyId"` | Invalid (no secret) |
| 3 | `"invalid-format"` | Invalid |
| 4 | `""` | Invalid |
| 5 | `"a.b:c"` | Valid (minimal format) |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  IF test_case.expected == "Valid":
    # Should not throw
    client = Rest(options: ClientOptions(key: test_case.input))
    ASSERT client IS valid
  ELSE:
    ASSERT ClientOptions(key: test_case.input) THROWS ConfigurationException
```

---

## RSA2 - Basic auth when using API key

Tests that Basic authentication is used when API key is provided.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
auth_header = request.headers["Authorization"]

ASSERT auth_header STARTS WITH "Basic "

# Decode and verify
credentials = base64_decode(auth_header.substring(6))
ASSERT credentials == "appId.keyId:keySecret"
```

---

## RSA3 - Token auth when token provided

Tests that Bearer token authentication is used when token is provided.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(token: "my-token-string"))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
auth_header = request.headers["Authorization"]

ASSERT auth_header == "Bearer my-token-string"
```

---

## RSA3 - Token auth when TokenDetails provided

Tests that Bearer authentication extracts token from TokenDetails.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  tokenDetails: TokenDetails(
    token: "token-from-details",
    expires: now() + 3600000
  )
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer token-from-details"
```

---

## RSA4 - Auth method selection priority

Tests the order of preference for authentication methods.

### Test Cases (RSA4a, RSA4b, RSA4c)

| ID | Spec | Options Provided | Expected Auth Method |
|----|------|------------------|---------------------|
| 1 | RSA4a | `authCallback` only | Token (from callback) |
| 2 | RSA4a | `authUrl` only | Token (from URL) |
| 3 | RSA4b | `key` + `clientId` | Token (implicit) |
| 4 | RSA4c | `key` only | Basic |
| 5 | | `key` + `authCallback` | Token (callback takes precedence) |
| 6 | | `token` + `key` | Token (explicit token used) |

### Setup (Case 1 - authCallback)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  authCallback: (params) => TokenDetails(
    token: "callback-token",
    expires: now() + 3600000
  )
))
```

### Test Steps (Case 1)
```pseudo
AWAIT client.time()

request = mock_http.captured_requests[0]
ASSERT request.headers["Authorization"] == "Bearer callback-token"
```

### Setup (Case 3 - key + clientId triggers token auth)
```pseudo
mock_http = MockHttpClient()
# Token request
mock_http.queue_response(200, {
  "token": "auto-token",
  "expires": now() + 3600000,
  "keyName": "appId.keyId"
})
# Actual request
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  clientId: "my-client"
))
```

### Test Steps (Case 3)
```pseudo
AWAIT client.time()

# First request should be token creation
ASSERT mock_http.captured_requests[0].url.path CONTAINS "requestToken"

# Second request should use Bearer token
ASSERT mock_http.captured_requests[1].headers["Authorization"] STARTS WITH "Bearer "
```

### Setup (Case 4 - key only uses Basic)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps (Case 4)
```pseudo
AWAIT client.time()

request = mock_http.captured_requests[0]
ASSERT request.headers["Authorization"] STARTS WITH "Basic "
```

### Setup (Case 5 - authCallback takes precedence over key)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  authCallback: (params) => "callback-wins"
))
```

### Test Steps (Case 5)
```pseudo
AWAIT client.time()

request = mock_http.captured_requests[0]
# authCallback should be used, not Basic auth
ASSERT request.headers["Authorization"] == "Bearer callback-wins"
```

---

## RSA4 - No auth credentials error

Tests that an error is raised when no authentication method is configured.

### Test Steps
```pseudo
TRY:
  client = Rest(options: ClientOptions())  # No auth configured
  FAIL("Expected exception")
CATCH ConfigurationException as e:
  ASSERT e.message CONTAINS "auth" OR e.message CONTAINS "key" OR e.message CONTAINS "token"
```
