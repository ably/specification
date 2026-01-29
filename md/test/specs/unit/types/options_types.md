# Options Types Tests

Spec points: `TO1`, `TO2`, `TO3`, `AO1`, `AO2`

## Test Type
Unit test - pure type/model validation

## Mock Configuration
No mocks required - these verify type structure and defaults.

---

## TO3 - ClientOptions attributes

Tests that `ClientOptions` has all REST-relevant attributes with correct defaults.

### Test Cases - Required Attributes

| ID | Attribute | Type | Default |
|----|-----------|------|---------|
| 1 | `key` | String | (none) |
| 2 | `token` | String | (none) |
| 3 | `tokenDetails` | TokenDetails | (none) |
| 4 | `authCallback` | Function | (none) |
| 5 | `authUrl` | String | (none) |
| 6 | `authMethod` | String | `"GET"` |
| 7 | `authHeaders` | Map | (empty) |
| 8 | `authParams` | Map | (empty) |
| 9 | `clientId` | String | (none) |
| 10 | `endpoint` | String | (none - uses production) |
| 11 | `restHost` | String | `"rest.ably.io"` |
| 12 | `fallbackHosts` | List | (default fallback hosts) |
| 13 | `tls` | Boolean | `true` |
| 14 | `httpRequestTimeout` | Integer | `10000` (10 seconds) |
| 15 | `httpMaxRetryCount` | Integer | `3` |
| 16 | `httpMaxRetryDuration` | Integer | `15000` (15 seconds) |
| 17 | `fallbackRetryTimeout` | Integer | `600000` (10 minutes) |
| 18 | `useBinaryProtocol` | Boolean | `true` |
| 19 | `idempotentRestPublishing` | Boolean | `true` |
| 20 | `addRequestIds` | Boolean | `false` |
| 21 | `queryTime` | Boolean | `false` |
| 22 | `maxMessageSize` | Integer | `65536` (64KB) |
| 23 | `defaultTokenParams` | TokenParams | (none) |

### Test Steps - Defaults
```pseudo
options = ClientOptions()

ASSERT options.authMethod == "GET"
ASSERT options.tls == true
ASSERT options.httpRequestTimeout == 10000
ASSERT options.httpMaxRetryCount == 3
ASSERT options.useBinaryProtocol == true
ASSERT options.idempotentRestPublishing == true
ASSERT options.addRequestIds == false
ASSERT options.queryTime == false
ASSERT options.maxMessageSize == 65536
```

### Test Steps - Setting Values
```pseudo
options = ClientOptions(
  key: "appId.keyId:keySecret",
  clientId: "my-client",
  endpoint: "sandbox",
  tls: false,
  httpRequestTimeout: 30000,
  useBinaryProtocol: false,
  idempotentRestPublishing: false,
  addRequestIds: true
)

ASSERT options.key == "appId.keyId:keySecret"
ASSERT options.clientId == "my-client"
ASSERT options.endpoint == "sandbox"
ASSERT options.tls == false
ASSERT options.httpRequestTimeout == 30000
ASSERT options.useBinaryProtocol == false
ASSERT options.idempotentRestPublishing == false
ASSERT options.addRequestIds == true
```

---

## TO3 - ClientOptions with custom hosts

Tests custom host configuration.

### Test Steps
```pseudo
options = ClientOptions(
  key: "appId.keyId:keySecret",
  restHost: "custom.ably.example.com",
  fallbackHosts: ["fallback1.example.com", "fallback2.example.com"]
)

ASSERT options.restHost == "custom.ably.example.com"
ASSERT options.fallbackHosts == ["fallback1.example.com", "fallback2.example.com"]
```

---

## TO3 - ClientOptions with auth URL

Tests auth URL configuration.

### Test Steps
```pseudo
options = ClientOptions(
  authUrl: "https://auth.example.com/token",
  authMethod: "POST",
  authHeaders: { "X-API-Key": "secret" },
  authParams: { "scope": "full" }
)

ASSERT options.authUrl == "https://auth.example.com/token"
ASSERT options.authMethod == "POST"
ASSERT options.authHeaders["X-API-Key"] == "secret"
ASSERT options.authParams["scope"] == "full"
```

---

## TO3 - ClientOptions with defaultTokenParams

Tests default token parameters configuration.

### Test Steps
```pseudo
options = ClientOptions(
  key: "appId.keyId:keySecret",
  defaultTokenParams: TokenParams(
    ttl: 7200000,
    clientId: "default-client",
    capability: "{\"*\":[\"subscribe\"]}"
  )
)

ASSERT options.defaultTokenParams.ttl == 7200000
ASSERT options.defaultTokenParams.clientId == "default-client"
ASSERT options.defaultTokenParams.capability == "{\"*\":[\"subscribe\"]}"
```

---

## AO2 - AuthOptions attributes

Tests that `AuthOptions` has all required attributes.

### Test Cases

| ID | Attribute | Type |
|----|-----------|------|
| 1 | `key` | String |
| 2 | `token` | String |
| 3 | `tokenDetails` | TokenDetails |
| 4 | `authCallback` | Function |
| 5 | `authUrl` | String |
| 6 | `authMethod` | String |
| 7 | `authHeaders` | Map |
| 8 | `authParams` | Map |
| 9 | `queryTime` | Boolean |

### Test Steps
```pseudo
auth_options = AuthOptions(
  authUrl: "https://auth.example.com/token",
  authMethod: "POST",
  authHeaders: { "Authorization": "Bearer api-key" },
  authParams: { "user": "test" },
  queryTime: true
)

ASSERT auth_options.authUrl == "https://auth.example.com/token"
ASSERT auth_options.authMethod == "POST"
ASSERT auth_options.authHeaders["Authorization"] == "Bearer api-key"
ASSERT auth_options.authParams["user"] == "test"
ASSERT auth_options.queryTime == true
```

---

## AO - AuthOptions with authCallback

Tests that `AuthOptions` can hold an authCallback function.

### Test Steps
```pseudo
callback_called = false

test_callback = (params) => {
  callback_called = true
  RETURN TokenDetails(token: "callback-token", expires: now() + 3600000)
}

auth_options = AuthOptions(authCallback: test_callback)

# Verify callback is stored and callable
result = auth_options.authCallback(TokenParams())
ASSERT callback_called == true
ASSERT result.token == "callback-token"
```

---

## TO - Endpoint affects host selection

Tests that endpoint option affects default hosts.

### Test Cases

| ID | Endpoint | Expected Rest Host |
|----|----------|--------------------|
| 1 | (none/production) | `rest.ably.io` |
| 2 | `"sandbox"` | `sandbox-rest.ably.io` |
| 3 | `"custom-env"` | `custom-env-rest.ably.io` |

### Note
The actual host resolution may be tested at the HTTP client level. This test verifies the option is stored correctly.

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  IF test_case.endpoint IS none:
    options = ClientOptions(key: "appId.keyId:keySecret")
  ELSE:
    options = ClientOptions(
      key: "appId.keyId:keySecret",
      endpoint: test_case.endpoint
    )

  ASSERT options.endpoint == test_case.endpoint
```

---

## TO - Conflicting options validation

Tests that conflicting options are detected.

### Test Cases

| ID | Options | Expected |
|----|---------|----------|
| 1 | `key` + `authCallback` | Valid (authCallback takes precedence) |
| 2 | `restHost` + `endpoint` | Invalid (conflict) |
| 3 | (no auth options) | Invalid |

### Test Steps (Case 2 - Conflicting hosts)
```pseudo
TRY:
  options = ClientOptions(
    key: "appId.keyId:keySecret",
    restHost: "custom.host.com",
    endpoint: "sandbox"
  )
  FAIL("Expected configuration error")
CATCH ConfigurationException as e:
  ASSERT e.message CONTAINS "restHost" OR e.message CONTAINS "endpoint"
```

### Test Steps (Case 3 - No auth)
```pseudo
TRY:
  client = Rest(options: ClientOptions())
  FAIL("Expected configuration error")
CATCH ConfigurationException as e:
  ASSERT e.message CONTAINS "auth" OR e.message CONTAINS "key" OR e.message CONTAINS "token"
```
