# Client Options Tests

Spec points: `RSC1`, `RSC1a`, `RSC1b`, `RSC1c`

## Test Type
Unit test - no network, no mocks required (pure validation logic)

## RSC1, RSC1a, RSC1c - Constructor String Argument Detection

Tests that the client correctly identifies whether a string argument is an API key or a token.

### Setup
None required.

### Test Cases

| ID | Input | Expected Detection | Rationale |
|----|-------|-------------------|-----------|
| 1 | `"appId.keyId:keySecret"` | API key | Contains `:` delimiter |
| 2 | `"xVLyHw.A-pwh:5WEB4HEAT3pOqWp9"` | API key | Real key format with special chars |
| 3 | `"xVLyHw.A-pwh:5WEB4HEAT3pOqWp9-the_rest"` | API key | Key with extended secret |
| 4 | `"abcdef1234567890"` | Token | No `:` delimiter (opaque token) |
| 5 | `"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"` | Token | JWT format (no `:` before first `.`) |
| 6 | `""` | Error | Empty string is invalid |

### Test Steps

```pseudo
FOR EACH test_case IN test_cases:
  IF test_case.expected == "API key":
    client = Rest(key: test_case.input)
    ASSERT client.options.key == test_case.input
    ASSERT client.auth uses Basic Auth scheme
  ELSE IF test_case.expected == "Token":
    client = Rest(token: test_case.input)
    ASSERT client.options.tokenDetails.token == test_case.input
    ASSERT client.auth uses Token Auth scheme
  ELSE IF test_case.expected == "Error":
    ASSERT Rest(test_case.input) THROWS AblyException
```

### Assertions
- API key strings result in `ClientOptions.key` being set
- Token strings result in `ClientOptions.tokenDetails.token` being set
- Auth scheme is correctly inferred (Basic for key, Token for token)

---

## RSC1b - Invalid Arguments Error

Tests that constructing a client without valid credentials raises error 40106.

### Setup
None required.

### Test Cases

| ID | Options | Expected |
|----|---------|----------|
| 1 | `ClientOptions()` (no key, no token, no authCallback, no authUrl) | Error 40106 |
| 2 | `ClientOptions(useTokenAuth: true)` (no means to obtain token) | Error 40106 |
| 3 | `ClientOptions(clientId: "test")` (clientId alone is not auth) | Error 40106 |

### Test Steps

```pseudo
FOR EACH test_case IN test_cases:
  ASSERT Rest(options: test_case.options) THROWS AblyException WITH:
    code == 40106
    message CONTAINS "key" OR "token" OR "auth"
```

### Assertions
- Constructor throws `AblyException`
- Error code is `40106`
- Error message is informative about missing credentials

---

## RSC1 - ClientOptions Constructor

Tests that full `ClientOptions` object is accepted and values are preserved.

### Setup
None required.

### Test Cases

```pseudo
options = ClientOptions(
  key: "appId.keyId:keySecret",
  clientId: "testClient",
  endpoint: "sandbox",
  tls: true,
  httpRequestTimeout: 5000,
  idempotentRestPublishing: true,
  logLevel: LogLevel.verbose
)
```

### Test Steps

```pseudo
client = Rest(options: options)

ASSERT client.options.key == "appId.keyId:keySecret"
ASSERT client.options.clientId == "testClient"
ASSERT client.options.endpoint == "sandbox"
ASSERT client.options.tls == true
ASSERT client.options.httpRequestTimeout == 5000
ASSERT client.options.idempotentRestPublishing == true
ASSERT client.options.logLevel == LogLevel.verbose
```

### Assertions
- All provided options are preserved in `client.options`
- Default values are applied for unspecified options
