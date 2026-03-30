# Token Request Parameter Defaults

Spec points: `RSA5`, `RSA6`, `RSA9`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/test/rest/unit/rest_client.md` for the full Mock HTTP Infrastructure specification. These tests use the same `MockHttpClient` interface with `PendingConnection` and `PendingRequest`.

## Purpose

Tests the handling of `ttl` and `capability` parameters in `createTokenRequest()`.
The spec requires that when these values are not provided by the user, they must be
**null** in the token request rather than defaulted client-side. This allows Ably to
apply its own server-side defaults (60 minute TTL, key capabilities).

**Portability note:** The `ttl` and `capability` fields on `TokenRequest` must be
nullable types (e.g. `int?` / `String?` in Dart, `Integer` / `String` in Java,
`*int` / `*string` in Go). This allows implementations to distinguish "not specified"
(null) from an explicit value, and to omit null fields during serialization.

---

## RSA5 - TTL is null when not specified

**Spec requirement:** TTL for new tokens is specified in milliseconds. If the user-provided `tokenParams` does not specify a TTL, the TTL field should be null in the `tokenRequest`, and Ably will supply a token with a TTL of 60 minutes.

Tests that `createTokenRequest()` without explicit TTL produces a token request
with a null `ttl`, rather than a client-side default like 3600000.

### Setup
```pseudo
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
token_request = AWAIT client.auth.createTokenRequest()
```

### Assertions
```pseudo
# TTL should be null (not zero, not a default like 3600000)
ASSERT token_request.ttl IS null
```

---

## RSA5b - Explicit TTL is preserved

**Spec requirement:** When `tokenParams` specifies a TTL, it must be included in the token request.

### Setup
```pseudo
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
token_request = AWAIT client.auth.createTokenRequest(
  tokenParams: TokenParams(ttl: 7200000)  # 2 hours
)
```

### Assertions
```pseudo
ASSERT token_request.ttl == 7200000
```

---

## RSA5c - TTL from defaultTokenParams is used

**Spec requirement:** TTL from `ClientOptions.defaultTokenParams` should be used when no explicit TTL is provided to `createTokenRequest()`.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  defaultTokenParams: TokenParams(ttl: 1800000)  # 30 minutes
))
```

### Test Steps
```pseudo
token_request = AWAIT client.auth.createTokenRequest()
```

### Assertions
```pseudo
ASSERT token_request.ttl == 1800000
```

---

## RSA5d - Explicit TTL overrides defaultTokenParams

**Spec requirement:** An explicit TTL in `tokenParams` takes precedence over `defaultTokenParams`.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  defaultTokenParams: TokenParams(ttl: 1800000)  # 30 minutes
))
```

### Test Steps
```pseudo
token_request = AWAIT client.auth.createTokenRequest(
  tokenParams: TokenParams(ttl: 600000)  # 10 minutes
)
```

### Assertions
```pseudo
ASSERT token_request.ttl == 600000
```

---

## RSA6 - Capability is null when not specified

**Spec requirement:** The `capability` for new tokens is JSON stringified. If the user-provided `tokenParams` does not specify capabilities, the `capability` field should be null in the `tokenRequest`, and Ably will supply a token with the capabilities of the underlying key.

Tests that `createTokenRequest()` without explicit capability produces a token
request with a null `capability`, rather than a client-side default like `{"*":["*"]}`.

### Setup
```pseudo
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
token_request = AWAIT client.auth.createTokenRequest()
```

### Assertions
```pseudo
# Capability should be null (not a default like '{"*":["*"]}')
ASSERT token_request.capability IS null
```

---

## RSA6b - Explicit capability is preserved

**Spec requirement:** When `tokenParams` specifies a capability, it must be included in the token request as a JSON string.

### Setup
```pseudo
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
token_request = AWAIT client.auth.createTokenRequest(
  tokenParams: TokenParams(capability: '{"channel-a":["publish","subscribe"]}')
)
```

### Assertions
```pseudo
ASSERT token_request.capability == '{"channel-a":["publish","subscribe"]}'
```

---

## RSA6c - Capability from defaultTokenParams is used

**Spec requirement:** Capability from `ClientOptions.defaultTokenParams` should be used when no explicit capability is provided to `createTokenRequest()`.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  defaultTokenParams: TokenParams(capability: '{"*":["subscribe"]}')
))
```

### Test Steps
```pseudo
token_request = AWAIT client.auth.createTokenRequest()
```

### Assertions
```pseudo
ASSERT token_request.capability == '{"*":["subscribe"]}'
```

---

## RSA6d - Explicit capability overrides defaultTokenParams

**Spec requirement:** An explicit capability in `tokenParams` takes precedence over `defaultTokenParams`.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  defaultTokenParams: TokenParams(capability: '{"*":["subscribe"]}')
))
```

### Test Steps
```pseudo
token_request = AWAIT client.auth.createTokenRequest(
  tokenParams: TokenParams(capability: '{"channel-x":["publish"]}')
)
```

### Assertions
```pseudo
ASSERT token_request.capability == '{"channel-x":["publish"]}'
```
