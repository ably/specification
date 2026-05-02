# Realtime Token Renewal Integration Tests

Spec points: `RSA4b`, `RTN14b`

## Test Type
Integration test against Ably sandbox

## Purpose

End-to-end verification that the realtime client handles token expiry correctly:
when the server rejects a connection or in-flight request due to an expired token,
the client automatically renews via the authCallback and recovers.

## Token Formats

Tests use JWTs generated using a third-party JWT library, signed with the app key
secret using HMAC-SHA256.

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

## RSA4b, RTN14b - Token renewal on expiry

| Spec | Requirement |
|------|-------------|
| RSA4b | Client with renewable token automatically reissues on token error |
| RTN14b | Token error on connection triggers renewal and reconnection |

**Spec requirement:** When a realtime client's token expires, the server sends
a DISCONNECTED message with a token error code (40140-40149). The client must
automatically invoke the authCallback to obtain a new token and reconnect.

### Setup
```pseudo
key_name = extract_key_name(api_key)
key_secret = extract_key_secret(api_key)
callback_count = 0

auth_callback = FUNCTION(params):
  callback_count++
  IF callback_count == 1:
    # First token: very short TTL (5 seconds)
    RETURN generate_jwt(
      key_name: key_name,
      key_secret: key_secret,
      ttl: 5000
    )
  ELSE:
    # Subsequent tokens: long TTL
    RETURN generate_jwt(
      key_name: key_name,
      key_secret: key_secret,
      ttl: 3600000
    )

client = Realtime(options: ClientOptions(
  authCallback: auth_callback,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == CONNECTED

# Record the initial connection ID
initial_connection_id = client.connection.id
ASSERT callback_count == 1

# Wait for token to expire and the client to recover.
# The server will send a DISCONNECTED with a token error once the token
# expires. The client should automatically renew and reconnect.
poll_until(
  condition: FUNCTION() => callback_count >= 2,
  interval: 1000ms,
  timeout: 30s
)

# Wait for reconnection
AWAIT_STATE client.connection.state == CONNECTED
  WITH timeout: 15s
```

### Assertions
```pseudo
# authCallback was invoked at least twice (initial + renewal)
ASSERT callback_count >= 2

# Client is connected
ASSERT client.connection.state == CONNECTED

CLOSE_CLIENT(client)
```
