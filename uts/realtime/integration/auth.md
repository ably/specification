# Realtime Auth Integration Tests

Spec points: `RTC8`, `RSA8`, `RSA7`

## Test Type
Integration test against Ably sandbox

## Token Formats

Tests use JWTs generated using a third-party JWT library, signed with the app key secret using HMAC-SHA256.

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox-rest.ably.io`.

### App Provisioning

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

---

## RTC8a - In-band reauthorization on CONNECTED client

**Spec requirement:** RTC8a - When `auth.authorize()` is called on a CONNECTED realtime client, it sends an AUTH protocol message with the new token rather than disconnecting/reconnecting.

Tests that calling authorize() on a connected client succeeds and the connection remains connected (UPDATE event, not disconnect/reconnect).

### Setup
```pseudo
auth_callback = FUNCTION(params):
  RETURN generate_jwt(
    key_name: extract_key_name(api_key),
    key_secret: extract_key_secret(api_key),
    ttl: 3600000
  )

client = Realtime(options: ClientOptions(
  authCallback: auth_callback,
  endpoint: "sandbox",
  autoConnect: false
))
```

### Test Steps
```pseudo
# Connect and wait for CONNECTED
client.connect()
AWAIT_STATE client.connection.state == CONNECTED

# Record connection ID before reauth
connection_id_before = client.connection.id

# Collect state changes during reauth
state_changes = []
subscription = client.connection.on(LISTEN state_changes.append)

# Call authorize — should send AUTH and get UPDATE, not disconnect
token = AWAIT client.auth.authorize()

# Check state after reauth
connection_id_after = client.connection.id
```

### Assertions
```pseudo
# authorize() returned a valid token
ASSERT token IS NOT NULL
ASSERT token.token IS String

# Connection remained connected — same connection ID
ASSERT connection_id_after == connection_id_before

# No state transitions occurred (UPDATE has current == previous == connected,
# so filtering for actual transitions should yield nothing)
state_transitions = state_changes.filter(c => c.current != c.previous)
ASSERT state_transitions IS EMPTY

AWAIT client.close()
```

---

## RTC8c - authorize() from INITIALIZED initiates connection

**Spec requirement:** RTC8c - When `auth.authorize()` is called on a client in INITIALIZED state, it should initiate the connection.

Tests that calling authorize() on an unconnected client triggers a connection.

### Setup
```pseudo
auth_callback = FUNCTION(params):
  RETURN generate_jwt(
    key_name: extract_key_name(api_key),
    key_secret: extract_key_secret(api_key),
    ttl: 3600000
  )

client = Realtime(options: ClientOptions(
  authCallback: auth_callback,
  endpoint: "sandbox",
  autoConnect: false
))
```

### Test Steps
```pseudo
# Client starts in INITIALIZED, no connection
ASSERT client.connection.state == INITIALIZED

# authorize() should trigger connection
token = AWAIT client.auth.authorize()

# Wait for connection to be established
AWAIT_STATE client.connection.state == CONNECTED
```

### Assertions
```pseudo
ASSERT token IS NOT NULL
ASSERT client.connection.state == CONNECTED
ASSERT client.connection.id IS NOT NULL

AWAIT client.close()
```

---

## RSA8 - Token auth on realtime connection

**Spec requirement:** RSA8 - Realtime client can connect using token authentication via an authCallback that returns JWTs.

Tests that a realtime client can connect using JWT-based token auth.

### Setup
```pseudo
auth_callback = FUNCTION(params):
  RETURN generate_jwt(
    key_name: extract_key_name(api_key),
    key_secret: extract_key_secret(api_key),
    ttl: 3600000
  )

client = Realtime(options: ClientOptions(
  authCallback: auth_callback,
  endpoint: "sandbox",
  autoConnect: false
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == CONNECTED
```

### Assertions
```pseudo
ASSERT client.connection.state == CONNECTED
ASSERT client.connection.id IS NOT NULL
ASSERT client.connection.errorReason IS NULL

AWAIT client.close()
```

---

## RSA7 - clientId validation on realtime connection

**Spec requirement:** RSA7 - The server validates clientId consistency between token claims and connection parameters.

Tests that:
1. A JWT with a clientId allows connection with matching clientId
2. A JWT with a clientId rejects connection with mismatched clientId

### Test 1: Matching clientId succeeds

#### Setup
```pseudo
test_client_id = "test-client-" + random_id()

auth_callback = FUNCTION(params):
  RETURN generate_jwt(
    key_name: extract_key_name(api_key),
    key_secret: extract_key_secret(api_key),
    client_id: test_client_id,
    ttl: 3600000
  )

client = Realtime(options: ClientOptions(
  authCallback: auth_callback,
  clientId: test_client_id,
  endpoint: "sandbox",
  autoConnect: false
))
```

#### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == CONNECTED
```

#### Assertions
```pseudo
ASSERT client.connection.state == CONNECTED
ASSERT client.auth.clientId == test_client_id

AWAIT client.close()
```

### Test 2: Mismatched clientId fails

#### Setup
```pseudo
auth_callback = FUNCTION(params):
  RETURN generate_jwt(
    key_name: extract_key_name(api_key),
    key_secret: extract_key_secret(api_key),
    client_id: "token-client-id",
    ttl: 3600000
  )
```

#### Test Steps
```pseudo
# ClientOptions constructor should reject mismatched clientId
# The clientId in options ("wrong-client-id") doesn't match the token's clientId
# This is validated client-side per RSA7
EXPECT THROW creating Realtime(options: ClientOptions(
  authCallback: auth_callback,
  clientId: "wrong-client-id",
  endpoint: "sandbox",
  autoConnect: false
))
```

#### Assertions
```pseudo
# Note: The mismatch is detected client-side when the token is obtained.
# The exact behavior depends on implementation: it may throw during
# authorize() or during token validation. The key assertion is that
# the connection enters FAILED state with error code 40102.
```
