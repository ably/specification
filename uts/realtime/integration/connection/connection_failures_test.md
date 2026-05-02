# Realtime Connection Failures Integration Tests

Spec points: `RTN14a`, `RTN14g`

## Test Type
Integration test against Ably sandbox

## Purpose

End-to-end verification that the server rejects invalid credentials with the
correct error codes and the SDK transitions to the expected state. Complements
the unit tests which verify client-side state machine behavior with mocked
transports.

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

## RTN14a - Invalid API key causes FAILED

| Spec | Requirement |
|------|-------------|
| RTN14a | If an API key is invalid, the connection transitions to FAILED |

**Spec requirement:** When connecting with an invalid API key, the server sends
an ERROR ProtocolMessage and the connection transitions to the FAILED state with
the error set on Connection#errorReason.

### Setup
```pseudo
client = Realtime(options: ClientOptions(
  key: "invalid.key:secret",
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == FAILED
  WITH timeout: 15s
```

### Assertions
```pseudo
ASSERT client.connection.state == FAILED
ASSERT client.connection.errorReason IS NOT NULL
ASSERT client.connection.errorReason.code == 40005 OR client.connection.errorReason.code == 40101
ASSERT client.connection.errorReason.statusCode == 401 OR client.connection.errorReason.statusCode == 404

CLOSE_CLIENT(client)
```

---

## RTN14g - Revoked key causes FAILED

| Spec | Requirement |
|------|-------------|
| RTN14g | An ERROR ProtocolMessage with an empty channel for reasons other than token error causes FAILED |

**Spec requirement:** When connecting with a key that has been revoked or belongs
to a deleted app, the server sends a non-token ERROR and the connection transitions
to FAILED.

Note: This test uses a syntactically valid but non-existent app ID. The server
rejects the connection with a 404 or 401 error, which is not a token error
(not in the 40140-40149 range), so RTN14g applies.

### Setup
```pseudo
# Use a key with a valid format but non-existent app
client = Realtime(options: ClientOptions(
  key: "nonexistent.keyname:keysecret",
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == FAILED
  WITH timeout: 15s
```

### Assertions
```pseudo
ASSERT client.connection.state == FAILED
ASSERT client.connection.errorReason IS NOT NULL
# Server returns 40005 (invalid key) or similar non-token error
ASSERT client.connection.errorReason.code < 40140 OR client.connection.errorReason.code >= 40150

CLOSE_CLIENT(client)
```
