# Realtime Token Request Integration Tests

Spec points: `RSA9`, `RSA9a`, `RSA9g`

## Test Type
Integration test against Ably sandbox

## Purpose

End-to-end verification that `Auth#createTokenRequest` produces a signed
`TokenRequest` that the Ably service accepts. This validates that the HMAC
signature computation (RSA9g) is compatible with the server.

## Sandbox Setup

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox.realtime.ably-nonprod.net/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox.realtime.ably-nonprod.net/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

---

## RSA9a, RSA9g - createTokenRequest produces server-accepted token

| Spec | Requirement |
|------|-------------|
| RSA9a | Returns a signed TokenRequest that can be used to obtain a token |
| RSA9g | A valid HMAC is created using the key secret |

**Spec requirement:** A TokenRequest created by `createTokenRequest` contains
a valid HMAC signature. When this TokenRequest is passed to another client's
`authCallback`, that client must be able to connect successfully, proving the
server accepted the TokenRequest.

### Setup
```pseudo
# Client A creates TokenRequests using the API key
creator = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

# Client B connects using TokenRequests from client A
client = Realtime(options: ClientOptions(
  authCallback: FUNCTION(params):
    token_request = AWAIT creator.auth.createTokenRequest()
    RETURN token_request,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == CONNECTED
  WITH timeout: 15s
```

### Assertions
```pseudo
ASSERT client.connection.state == CONNECTED
ASSERT client.connection.id IS NOT NULL
ASSERT client.connection.errorReason IS NULL

CLOSE_CLIENT(client)
```

---

## RSA9 - createTokenRequest with clientId

| Spec | Requirement |
|------|-------------|
| RSA9 | createTokenRequest accepts TokenParams including clientId |

**Spec requirement:** A TokenRequest created with a specific clientId produces
a token that authenticates the client with that identity.

### Setup
```pseudo
test_client_id = "token-request-client-" + random_id()

creator = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

client = Realtime(options: ClientOptions(
  authCallback: FUNCTION(params):
    token_request = AWAIT creator.auth.createTokenRequest(
      TokenParams(clientId: test_client_id)
    )
    RETURN token_request,
  clientId: test_client_id,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == CONNECTED
  WITH timeout: 15s
```

### Assertions
```pseudo
ASSERT client.connection.state == CONNECTED
ASSERT client.auth.clientId == test_client_id

CLOSE_CLIENT(client)
```
