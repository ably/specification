# Revoke Tokens Integration Tests

Spec points: `RSA17`, `RSA17b`, `RSA17c`, `RSA17d`, `RSA17e`, `RSA17f`, `RSA17g`, `TRS2`, `TRF2`

## Test Type
Integration test against Ably sandbox

## Purpose

End-to-end verification of `Auth#revokeTokens` against the Ably sandbox.
These tests verify that token revocation actually prevents subsequent use
of the revoked token, in addition to confirming the response format.

## Verification Strategy

Revocation is verified using **Realtime connections** rather than REST requests.
After revoking a token, the server pushes a disconnect to any connected Realtime
client using that token. This is more reliable than polling with REST requests,
because token revocation may take a small delay to become active on the REST
path. The Realtime disconnect is immediate and carries the `40141` error code.

The test sets up `disconnected` listeners **before** performing the revocation,
to avoid missing the state change.

## Server Response Format

The Ably server returns token revocation results as a **plain JSON array** of
per-target results:

```json
[{"target": "clientId:xxx", "appliesAt": 1234567890, "issuedBefore": 1234567890}]
```

On failure for a specific target, the element contains an `error` field instead:

```json
[{"target": "invalidType:abc", "error": {"code": 40000, "statusCode": 400, "message": "..."}}]
```

There is no `BatchResult` envelope — the `successCount` and `failureCount` fields
(RSA17c) must be computed **client-side** by counting elements with and without an
`error` field. This is consistent with how batch presence responses work (see
`batch_presence.md`).

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox-rest.ably.io`.

### App Provisioning

Uses `ably-common/test-resources/test-app-setup.json` which provides:
- `keys[0]` — full access (default capability `{"*":["*"]}`)
- `keys[4]` — `revocableTokens: true` (required for the revokeTokens endpoint)

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  full_access_key = app_config.keys[0].key_str
  revocable_key = app_config.keys[4].key_str  # revocableTokens: true
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {full_access_key}
```

---

## RSA17g, RSA17b, RSA17c, TRS2 - Token revocation prevents subsequent use

**Spec requirement:** `Auth#revokeTokens` sends a POST to
`/keys/{keyName}/revokeTokens` with `targets` as `type:value` strings, and
returns a result containing per-target success information. After revocation,
the token must be rejected by the server.

| Spec | Requirement |
|------|-------------|
| RSA17g | POST to `/keys/{keyName}/revokeTokens` |
| RSA17b | Targets mapped to `type:value` strings |
| RSA17c | Returns per-target results; SDK computes `successCount`, `failureCount` client-side |
| TRS2a | Success result contains `target` string |
| TRS2b | Success result contains `appliesAt` timestamp |
| TRS2c | Success result contains `issuedBefore` timestamp |

### Setup
```pseudo
client_id = "revoke-client-" + random_id()

# Create a key-auth REST client (using the revocable key) for revoking and token issuance
key_client = Rest(options: ClientOptions(
  key: revocable_key,
  endpoint: "sandbox"
))

# Request a native token for the clientId
token_details = AWAIT key_client.auth.requestToken(clientId: client_id)

# Create a Realtime client using the token, and wait for it to connect
realtime_client = Realtime(options: ClientOptions(
  token: token_details,
  endpoint: "sandbox"
))
AWAIT realtime_client.connection.once("connected")
```

### Test Steps
```pseudo
# Step 1: Set up a disconnected listener BEFORE revoking (to not miss the event)
disconnected_promise = realtime_client.connection.once("disconnected")

# Step 2: Revoke the token by clientId
revoke_result = AWAIT key_client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: client_id)
])

# Step 3: Verify the revokeTokens response structure (RSA17c, TRS2)
ASSERT revoke_result.successCount == 1
ASSERT revoke_result.failureCount == 0
ASSERT revoke_result.results.length == 1

success = revoke_result.results[0]
ASSERT success IS TokenRevocationSuccessResult
ASSERT success.target == "clientId:" + client_id
ASSERT success.issuedBefore IS number
ASSERT success.appliesAt IS number

# Step 4: Verify the Realtime client is disconnected with 40141 (token revoked)
state_change = AWAIT disconnected_promise
ASSERT state_change.reason.code == 40141
```

---

## RSA17d - Token auth client rejected

**Spec requirement:** If called from a client using token authentication,
should raise an error with code `40162` and status code `401`. This is a
client-side check — no HTTP request is made to the server.

### Setup
```pseudo
# Generate a JWT using the revocable key
jwt = generate_jwt(
  key_name: extract_key_name(revocable_key),
  key_secret: extract_key_secret(revocable_key),
  ttl: 3600000
)

# Create a client using token auth (JWT)
token_rest = Rest(options: ClientOptions(
  token: jwt,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
```

### Test Steps
```pseudo
AWAIT token_rest.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: "anyone")
]) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40162
ASSERT error.statusCode == 401
```

---

## RSA17e, RSA17f - issuedBefore and allowReauthMargin

| Spec | Requirement |
|------|-------------|
| RSA17e | Optional `issuedBefore` timestamp in milliseconds |
| RSA17f | Optional `allowReauthMargin` boolean delays revocation by ~30 seconds |

**Spec requirement:** When `issuedBefore` is provided, only tokens issued before
that timestamp are revoked. When `allowReauthMargin` is true, the revocation is
delayed by approximately 30 seconds to allow token renewal.

### Setup
```pseudo
client_id = "revoke-margin-client-" + random_id()

key_client = Rest(options: ClientOptions(
  key: revocable_key,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
# Step 1: Revoke with issuedBefore and allowReauthMargin
server_time = AWAIT key_client.time()

# Use an issuedBefore in the past to avoid affecting any active tokens
issued_before = server_time - (20 * 60 * 1000)

revoke_result = AWAIT key_client.auth.revokeTokens(
  [TokenRevocationTargetSpecifier(type: "clientId", value: client_id)],
  options: { issuedBefore: issued_before, allowReauthMargin: true }
)

ASSERT revoke_result.successCount == 1
ASSERT revoke_result.results.length == 1

# RSA17e: issuedBefore should reflect what we sent
ASSERT revoke_result.results[0].issuedBefore == issued_before

# RSA17f: allowReauthMargin delays appliesAt by ~30 seconds
ASSERT revoke_result.results[0].appliesAt > server_time + (30 * 1000)
```

---

## RSA17c, TRF2 - Mixed success and failure (invalid specifier type)

**Spec requirement:** The response can contain both successful and failed
per-target results. An invalid target type produces a failure result with
an `ErrorInfo`.

| Spec | Requirement |
|------|-------------|
| RSA17c | `BatchResult` with `successCount` and `failureCount` |
| TRF2a | Failure result contains `target` string |
| TRF2b | Failure result contains `error` ErrorInfo |

This test includes an invalid specifier type alongside a valid one, to
verify the server returns per-target error information. The valid revocation
is also verified by confirming the Realtime client is disconnected.

### Setup
```pseudo
client_id = "revoke-mixed-client-" + random_id()

# Create a key-auth REST client for revoking and token issuance
key_client = Rest(options: ClientOptions(
  key: revocable_key,
  endpoint: "sandbox"
))

# Request a native token for the clientId
token_details = AWAIT key_client.auth.requestToken(clientId: client_id)

# Create a Realtime client using the token, and wait for it to connect
realtime_client = Realtime(options: ClientOptions(
  token: token_details,
  endpoint: "sandbox"
))
AWAIT realtime_client.connection.once("connected")
```

### Test Steps
```pseudo
# Step 1: Set up a disconnected listener BEFORE revoking
disconnected_promise = realtime_client.connection.once("disconnected")

# Step 2: Revoke with one valid and one invalid specifier
revoke_result = AWAIT key_client.auth.revokeTokens([
  TokenRevocationTargetSpecifier(type: "clientId", value: client_id),
  TokenRevocationTargetSpecifier(type: "invalidType", value: "abc")
])

# Step 3: Verify the response contains both success and failure
ASSERT revoke_result.successCount == 1
ASSERT revoke_result.failureCount == 1
ASSERT revoke_result.results.length == 2

# Valid specifier succeeds
success = revoke_result.results[0]
ASSERT success IS TokenRevocationSuccessResult
ASSERT success.target == "clientId:" + client_id
ASSERT success.issuedBefore IS number
ASSERT success.appliesAt IS number

# Invalid specifier fails
failure = revoke_result.results[1]
ASSERT failure IS TokenRevocationFailureResult
ASSERT failure.target == "invalidType:abc"
ASSERT failure.error IS ErrorInfo
ASSERT failure.error.statusCode == 400

# Step 4: Verify the Realtime client is disconnected with 40141 (token revoked)
state_change = AWAIT disconnected_promise
ASSERT state_change.reason.code == 40141
```
