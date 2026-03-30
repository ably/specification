# Connection Opening Failures — Proxy Integration Tests

Spec points: `RTN14a`, `RTN14b`, `RTN14c`, `RTN14d`, `RTN14g`

## Test Type

Proxy integration test against Ably Sandbox endpoint

## Proxy Infrastructure

See `uts/test/realtime/integration/helpers/proxy.md` for the full proxy infrastructure specification.

## Related Unit Tests

See `uts/test/realtime/unit/connection/connection_open_failures_test.md` for the corresponding unit tests that verify the same spec points with mocked WebSocket.

## Sandbox Setup

Tests run against the Ably Sandbox via a programmable proxy.

### App Provisioning

```pseudo
BEFORE ALL TESTS:
  # Provision test app
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  # Clean up test app
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

### Common Cleanup

```pseudo
AFTER EACH TEST:
  IF client IS NOT null AND client.connection.state IN [connected, connecting, disconnected]:
    client.connection.close()
    AWAIT_STATE client.connection.state == ConnectionState.closed
      WITH timeout: 10 seconds
  IF session IS NOT null:
    session.close()
```

---

## RTN14a — Fatal error during connection open causes FAILED

| Spec | Requirement |
|------|-------------|
| RTN14a | If the connection attempt encounters a fatal error (non-token error), the connection transitions to FAILED |

Tests that when the server responds with a fatal ERROR (non-token error code) during connection open, the SDK transitions to FAILED and sets errorReason. This verifies the same behaviour as the unit test but against the real Ably sandbox with fault injection.

### Setup

```pseudo
# Create proxy session that replaces the first CONNECTED with a fatal ERROR
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "ws_frame_to_client", "action": "CONNECTED" },
    "action": {
      "type": "replace",
      "message": {
        "action": 9,
        "error": { "code": 40005, "statusCode": 400, "message": "Invalid key" }
      }
    },
    "times": 1,
    "comment": "RTN14a: Replace CONNECTED with fatal ERROR"
  }]
)

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))
```

### Test Steps

```pseudo
# Record state changes for sequence verification
state_changes = []
client.connection.on((change) => {
  state_changes.append(change.current)
})

# Start connection
client.connect()

# Wait for FAILED state
AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 15 seconds
```

### Assertions

```pseudo
# Connection transitioned to FAILED
ASSERT client.connection.state == ConnectionState.failed

# Error reason is set from the injected ERROR message
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 40005
ASSERT client.connection.errorReason.statusCode == 400

# State sequence includes CONNECTING -> FAILED
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.connecting,
  ConnectionState.failed
]

# Connection ID/key not set (never received real CONNECTED)
ASSERT client.connection.id IS null
ASSERT client.connection.key IS null
```

---

## RTN14b — Token error during connection, SDK renews and reconnects

| Spec | Requirement |
|------|-------------|
| RTN14b | If a token error (40140-40149) occurs during connection and the token is renewable, attempt to obtain a new token and retry |

Tests that when the server responds with a token error during the first connection attempt, the SDK renews the token via authCallback and successfully connects on the second attempt. The proxy intercepts only the first CONNECTED, replacing it with a 40142 error; the second attempt passes through.

### Setup

```pseudo
# Track authCallback invocations
auth_callback_count = 0

# Create proxy session that injects token error on first CONNECTED only
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "ws_frame_to_client", "action": "CONNECTED" },
    "action": {
      "type": "replace",
      "message": {
        "action": 9,
        "error": { "code": 40142, "statusCode": 401, "message": "Token expired" }
      }
    },
    "times": 1,
    "comment": "RTN14b: Token error on first connect, renewal should succeed"
  }]
)

# Use token auth with authCallback so the SDK can renew
client = Realtime(options: ClientOptions(
  authCallback: (params) => {
    auth_callback_count++
    # Request a token from the sandbox using the API key
    token_details = request_token_from_sandbox(api_key, params)
    RETURN token_details
  },
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))
```

### Test Steps

```pseudo
# Record state changes for sequence verification
state_changes = []
client.connection.on((change) => {
  state_changes.append(change.current)
})

# Start connection
client.connect()

# SDK should see token error, renew token, reconnect, and reach CONNECTED
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 30 seconds
```

### Assertions

```pseudo
# Successfully connected after token renewal
ASSERT client.connection.state == ConnectionState.connected

# Connection properties are set (from the real CONNECTED on second attempt)
ASSERT client.connection.id IS NOT null
ASSERT client.connection.key IS NOT null

# authCallback was called at least twice (initial token + renewal)
ASSERT auth_callback_count >= 2

# State sequence shows the SDK went through CONNECTING, then back to CONNECTING after error,
# and finally reached CONNECTED
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.connecting,
  ConnectionState.connected
]

# Proxy event log shows two WebSocket connections
log = session.get_log()
ws_connects = log.filter(e => e.type == "ws_connect")
ASSERT ws_connects.length >= 2

# No residual error reason on successful connection
ASSERT client.connection.errorReason IS null
```

---

## RTN14d — Retry after connection refused

| Spec | Requirement |
|------|-------------|
| RTN14d | After a recoverable connection failure, the client transitions to DISCONNECTED and automatically retries after disconnectedRetryTimeout |

Tests that when the first WebSocket connection is refused at the transport level, the SDK transitions to DISCONNECTED, waits for the retry timeout, and successfully connects on the second attempt. The proxy refuses the first connection and passes through the second.

### Setup

```pseudo
# Create proxy session that refuses the first WebSocket connection
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "ws_connect", "count": 1 },
    "action": { "type": "refuse_connection" },
    "times": 1,
    "comment": "RTN14d: Refuse first WebSocket connection"
  }]
)

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false,
  disconnectedRetryTimeout: 2000
))
```

### Test Steps

```pseudo
# Record state changes for sequence verification
state_changes = []
client.connection.on((change) => {
  state_changes.append(change.current)
})

# Start connection
client.connect()

# SDK should fail on first attempt, go DISCONNECTED, retry, then reach CONNECTED
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 30 seconds
```

### Assertions

```pseudo
# Successfully connected after retry
ASSERT client.connection.state == ConnectionState.connected

# Connection properties are set
ASSERT client.connection.id IS NOT null
ASSERT client.connection.key IS NOT null

# State sequence shows CONNECTING -> DISCONNECTED -> CONNECTING -> CONNECTED
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.connecting,
  ConnectionState.disconnected,
  ConnectionState.connecting,
  ConnectionState.connected
]

# Proxy event log shows two WebSocket connection attempts
log = session.get_log()
ws_connects = log.filter(e => e.type == "ws_connect")
ASSERT ws_connects.length >= 2
```

---

## RTN14g — Connection-level ERROR during open causes FAILED

| Spec | Requirement |
|------|-------------|
| RTN14g | If an ERROR ProtocolMessage with empty channel attribute is received, transition to FAILED state and set errorReason |

Tests that when the server responds with a connection-level ERROR (no channel field) with a server error code during connection open, the SDK transitions to FAILED. This is functionally similar to RTN14a but uses a 5xx error code (server error) rather than a 4xx client error, confirming that both ranges (outside 40140-40149) result in FAILED.

### Setup

```pseudo
# Create proxy session that replaces the first CONNECTED with a server ERROR
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "ws_frame_to_client", "action": "CONNECTED" },
    "action": {
      "type": "replace",
      "message": {
        "action": 9,
        "error": { "code": 50000, "statusCode": 500, "message": "Internal server error" }
      }
    },
    "times": 1,
    "comment": "RTN14g: Connection-level ERROR (server error) during open"
  }]
)

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))
```

### Test Steps

```pseudo
# Record state changes for sequence verification
state_changes = []
client.connection.on((change) => {
  state_changes.append(change.current)
})

# Start connection
client.connect()

# Wait for FAILED state
AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 15 seconds
```

### Assertions

```pseudo
# Connection transitioned to FAILED
ASSERT client.connection.state == ConnectionState.failed

# Error reason is set from the injected ERROR message
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 50000
ASSERT client.connection.errorReason.statusCode == 500
ASSERT client.connection.errorReason.message == "Internal server error"

# State sequence includes CONNECTING -> FAILED
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.connecting,
  ConnectionState.failed
]

# Connection ID/key not set
ASSERT client.connection.id IS null
ASSERT client.connection.key IS null
```

---

## RTN14c — Connection timeout (no CONNECTED received)

| Spec | Requirement |
|------|-------------|
| RTN14c | A connection attempt fails if not connected within realtimeRequestTimeout |

Tests that when the server accepts the WebSocket but never sends a CONNECTED message, the SDK times out and transitions to DISCONNECTED. The proxy suppresses the CONNECTED message from the server, forcing the SDK to rely on its timeout logic.

### Setup

```pseudo
# Create proxy session that suppresses all CONNECTED messages
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "ws_frame_to_client", "action": "CONNECTED" },
    "action": { "type": "suppress" },
    "comment": "RTN14c: Suppress CONNECTED to force timeout"
  }]
)

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false,
  realtimeRequestTimeout: 3000
))
```

### Test Steps

```pseudo
# Record state changes for sequence verification
state_changes = []
client.connection.on((change) => {
  state_changes.append(change.current)
})

# Start connection
client.connect()

# SDK should time out waiting for CONNECTED and transition to DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 15 seconds
```

### Assertions

```pseudo
# Connection timed out and transitioned to DISCONNECTED
ASSERT client.connection.state == ConnectionState.disconnected

# Error reason indicates timeout
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.message CONTAINS "timeout"
  OR client.connection.errorReason.code IN [50003, 80003]

# State sequence includes CONNECTING -> DISCONNECTED
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.connecting,
  ConnectionState.disconnected
]

# Connection ID/key not set (CONNECTED was never received)
ASSERT client.connection.id IS null
ASSERT client.connection.key IS null
```

---

## Integration Test Notes

### Timeout Handling

All `AWAIT_STATE` calls use generous timeouts because real network traffic is involved:
- Connection to CONNECTED via proxy: 30 seconds (allows for auth + transport + retry)
- Connection to FAILED/DISCONNECTED: 15 seconds (allows for proxy rule processing)
- Cleanup close: 10 seconds

### Token Auth Helper

The RTN14b test requires a helper to request tokens from the sandbox:

```pseudo
function request_token_from_sandbox(api_key, token_params):
  # Split API key into key name and secret
  key_name = api_key.split(":")[0]
  key_secret = api_key.split(":")[1]

  # Request a token from the sandbox REST API
  response = POST https://sandbox-rest.ably.io/keys/{key_name}/requestToken
    WITH Authorization: Basic base64(api_key)
    WITH body: token_params OR {}

  RETURN parse_json(response.body)  # TokenDetails
```

### Why Proxy Tests vs Unit Tests

These tests verify the same spec points as the unit tests in `connection_open_failures_test.md`, but provide higher confidence because:

1. **Real WebSocket connections** -- the SDK's actual transport layer is exercised
2. **Real Ably protocol** -- the proxy modifies real server responses, not synthetic mocks
3. **Real timing** -- timeout behaviour is tested with actual clocks, not fake timers
4. **Real token renewal** -- RTN14b exercises the full authCallback-to-reconnect flow against the sandbox
