# Connection Resume Proxy Integration Tests (RTN15)

Spec points: `RTN15a`, `RTN15b`, `RTN15c6`, `RTN15c7`, `RTN15h1`, `RTN15h3`

## Test Type

Proxy integration test against Ably Sandbox endpoint.

Uses the programmable proxy (`uts/test/proxy/`) to inject transport-level faults while the SDK communicates with the real Ably backend. See `uts/test/realtime/integration/helpers/proxy.md` for proxy infrastructure details.

Corresponding unit tests: `uts/test/realtime/unit/connection/connection_failures_test.md`

## Sandbox Setup

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

## Port Allocation

Each test allocates a unique proxy port to avoid conflicts:

```pseudo
BEFORE ALL TESTS:
  port_base = allocate_port_range(count: 5)
  # Tests use port_base + 0 through port_base + 4
```

---

## Test 6: RTN15a - Unexpected disconnect triggers resume

| Spec | Requirement |
|------|-------------|
| RTN15a | If transport is disconnected unexpectedly, attempt resume |

Tests that an unexpected transport disconnect causes the SDK to reconnect and attempt a resume, verified via the proxy event log.

**Unit test counterpart:** `connection_failures_test.md` > RTN15a

### Setup

**Proxy rules:** None (passthrough). The disconnect is triggered imperatively after the SDK connects.

```pseudo
session = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 0,
  rules: []
)
```

**SDK config:**

```pseudo
client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: port_base + 0,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))
```

### Test Steps

```pseudo
# Connect through proxy
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15s

# Record state changes from this point
state_changes = []
client.connection.on((change) => {
  state_changes.append(change.current)
})

# Trigger unexpected disconnect via proxy imperative action
session.trigger_action({ type: "disconnect" })

# SDK should reconnect and resume
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15s
```

### Assertions

```pseudo
# State changes should include disconnected -> connecting -> connected
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.disconnected,
  ConnectionState.connecting,
  ConnectionState.connected
]

# Verify resume was attempted via proxy log
log = session.get_log()
ws_connects = log.filter(e => e.type == "ws_connect")
ASSERT ws_connects.length >= 2

# Second WebSocket connection should include resume query parameter
ASSERT ws_connects[1].queryParams["resume"] IS NOT null
```

### Cleanup

```pseudo
client.connection.close()
AWAIT_STATE client.connection.state == ConnectionState.closed
  WITH timeout: 10s
session.close()
```

---

## Test 7: RTN15b, RTN15c6 - Resume preserves connectionId

| Spec | Requirement |
|------|-------------|
| RTN15b | Resume is attempted with connectionKey in `resume` query parameter |
| RTN15c6 | Successful resume indicated by same connectionId in CONNECTED response |

Tests that after an unexpected disconnect and successful resume, the connection ID remains the same and the resume query parameter contains the connection key.

**Unit test counterpart:** `connection_failures_test.md` > RTN15b, RTN15c6

### Setup

**Proxy rules:** None (passthrough). Disconnect is triggered imperatively.

```pseudo
session = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 1,
  rules: []
)
```

**SDK config:**

```pseudo
client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: port_base + 1,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))
```

### Test Steps

```pseudo
# Connect through proxy
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15s

# Record connection identity before disconnect
original_connection_id = client.connection.id
original_connection_key = client.connection.key
ASSERT original_connection_id IS NOT null
ASSERT original_connection_key IS NOT null

# Trigger unexpected disconnect
session.trigger_action({ type: "disconnect" })

# Wait for SDK to resume
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15s
```

### Assertions

```pseudo
# RTN15c6: Connection ID is preserved (successful resume)
ASSERT client.connection.id == original_connection_id

# RTN15b: Second ws_connect URL includes resume={connectionKey}
log = session.get_log()
ws_connects = log.filter(e => e.type == "ws_connect")
ASSERT ws_connects.length >= 2
ASSERT ws_connects[1].queryParams["resume"] == original_connection_key

# No error reason on successful resume
ASSERT client.connection.errorReason IS null
```

### Cleanup

```pseudo
client.connection.close()
AWAIT_STATE client.connection.state == ConnectionState.closed
  WITH timeout: 10s
session.close()
```

---

## Test 8: RTN15c7 - Failed resume gets new connectionId

| Spec | Requirement |
|------|-------------|
| RTN15c7 | If resume fails, server sends CONNECTED with new connectionId and error |

Tests that when a resume fails (simulated by the proxy replacing the server's second CONNECTED response with one containing a different connectionId and error), the SDK accepts the new connection identity and exposes the error.

**Unit test counterpart:** `connection_failures_test.md` > RTN15c7

### Setup

**Proxy rules:** Replace the 2nd CONNECTED message (the resume response) with a crafted one that has a different connectionId and an error, simulating a failed resume.

```pseudo
session = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 2,
  rules: [
    {
      "match": { "type": "ws_frame_to_client", "action": "CONNECTED", "count": 2 },
      "action": {
        "type": "replace",
        "message": {
          "action": 4,
          "connectionId": "proxy-injected-new-id",
          "connectionKey": "proxy-injected-new-key",
          "connectionDetails": {
            "connectionKey": "proxy-injected-new-key",
            "clientId": null,
            "maxMessageSize": 65536,
            "maxInboundRate": 250,
            "maxOutboundRate": 100,
            "maxFrameSize": 524288,
            "serverId": "test-server",
            "connectionStateTtl": 120000,
            "maxIdleInterval": 15000
          },
          "error": {
            "code": 80008,
            "statusCode": 400,
            "message": "Unable to recover connection"
          }
        }
      },
      "times": 1,
      "comment": "RTN15c7: Replace 2nd CONNECTED with failed resume (different connectionId + error 80008)"
    }
  ]
)
```

**SDK config:**

```pseudo
client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: port_base + 2,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))
```

### Test Steps

```pseudo
# Connect through proxy — first CONNECTED passes through normally
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15s

# Record original identity
original_connection_id = client.connection.id
ASSERT original_connection_id IS NOT null
ASSERT original_connection_id != "proxy-injected-new-id"

# Trigger disconnect — SDK will attempt resume
session.trigger_action({ type: "disconnect" })

# SDK reconnects, but proxy replaces the CONNECTED response with a new connectionId
# SDK should still reach CONNECTED, but with the new identity
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15s
```

### Assertions

```pseudo
# RTN15c7: Connection ID changed (resume failed, got new connection)
ASSERT client.connection.id == "proxy-injected-new-id"
ASSERT client.connection.id != original_connection_id

# Connection key updated to the new one
ASSERT client.connection.key == "proxy-injected-new-key"

# Error reason is set indicating why resume failed
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 80008

# Connection is still CONNECTED (not FAILED — the server gave a new connection)
ASSERT client.connection.state == ConnectionState.connected

# Verify resume was attempted in the proxy log
log = session.get_log()
ws_connects = log.filter(e => e.type == "ws_connect")
ASSERT ws_connects.length >= 2
ASSERT ws_connects[1].queryParams["resume"] IS NOT null
```

### Cleanup

```pseudo
client.connection.close()
AWAIT_STATE client.connection.state == ConnectionState.closed
  WITH timeout: 10s
session.close()
```

---

## Test 9: RTN15h1 - DISCONNECTED with token error, non-renewable token -> FAILED

| Spec | Requirement |
|------|-------------|
| RTN15h1 | If DISCONNECTED contains a token error and the token is not renewable, transition to FAILED |

Tests that when the proxy injects a DISCONNECTED message with a token error (code 40142), and the SDK was configured with a non-renewable token (token string only, no key or authCallback), the SDK transitions to FAILED because it has no means to renew the token.

**Unit test counterpart:** `connection_failures_test.md` > RTN15h1

### Setup

**Proxy rules:** After the initial WebSocket connection is established, wait 1 second then inject a DISCONNECTED message with token error and close the connection.

```pseudo
session = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 3,
  rules: [
    {
      "match": { "type": "delay_after_ws_connect", "delayMs": 1000 },
      "action": {
        "type": "inject_to_client_and_close",
        "message": {
          "action": 6,
          "error": {
            "code": 40142,
            "statusCode": 401,
            "message": "Token expired"
          }
        }
      },
      "times": 1,
      "comment": "RTN15h1: Inject DISCONNECTED with token error (40142) after 1s"
    }
  ]
)
```

**Token provisioning:** Obtain a real token from the sandbox so the initial connection succeeds, then use it without any renewal capability.

```pseudo
# Provision a token via REST using the API key
rest = Rest(options: ClientOptions(key: api_key, endpoint: "sandbox"))
token_details = rest.auth.requestToken()
token_string = token_details.token
```

**SDK config:** Use the token string directly — no key, no authCallback. This makes the token non-renewable.

```pseudo
client = Realtime(options: ClientOptions(
  token: token_string,
  endpoint: "localhost",
  port: port_base + 3,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))
```

### Test Steps

```pseudo
# Connect through proxy — initial connection succeeds with the real token
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15s

# Record state changes
state_changes = []
client.connection.on((change) => {
  state_changes.append(change.current)
})

# After 1s the proxy injects DISCONNECTED with 40142 and closes the socket.
# The SDK has a non-renewable token, so it cannot renew -> FAILED.
AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 15s
```

### Assertions

```pseudo
# RTN15h1: Ended in FAILED state
ASSERT client.connection.state == ConnectionState.failed

# Error reason reflects the token error
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 40142
ASSERT client.connection.errorReason.statusCode == 401

# State changes should show the transition to FAILED
# (may pass through DISCONNECTED briefly before FAILED)
ASSERT state_changes CONTAINS ConnectionState.failed
```

### Cleanup

```pseudo
# No need to close — already in FAILED state
session.close()
```

---

## Test 10: RTN15h3 - DISCONNECTED with non-token error triggers reconnect

| Spec | Requirement |
|------|-------------|
| RTN15h3 | If DISCONNECTED contains a non-token error, initiate immediate reconnect with resume |

Tests that when the proxy injects a DISCONNECTED message with a non-token error (code 80003), the SDK reconnects and resumes rather than transitioning to FAILED.

**Unit test counterpart:** `connection_failures_test.md` > RTN15h3

### Setup

**Proxy rules:** After the initial WebSocket connection, wait 1 second then inject a DISCONNECTED message with a non-token error and close the connection. Only fire once — the reconnection attempt passes through cleanly.

```pseudo
session = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 4,
  rules: [
    {
      "match": { "type": "delay_after_ws_connect", "delayMs": 1000 },
      "action": {
        "type": "inject_to_client_and_close",
        "message": {
          "action": 6,
          "error": {
            "code": 80003,
            "statusCode": 500,
            "message": "Service temporarily unavailable"
          }
        }
      },
      "times": 1,
      "comment": "RTN15h3: Inject DISCONNECTED with non-token error (80003) after 1s, once only"
    }
  ]
)
```

**SDK config:**

```pseudo
client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: port_base + 4,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))
```

### Test Steps

```pseudo
# Connect through proxy
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15s

# Record state changes
state_changes = []
client.connection.on((change) => {
  state_changes.append(change.current)
})

# After 1s the proxy injects DISCONNECTED with non-token error and closes.
# The rule fires once, so the reconnection attempt passes through to the real server.

# Wait for DISCONNECTED (from the injected message)
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 10s

# SDK should automatically reconnect
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15s
```

### Assertions

```pseudo
# RTN15h3: SDK reconnected successfully (not FAILED)
ASSERT client.connection.state == ConnectionState.connected

# State changes should show: disconnected -> connecting -> connected
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.disconnected,
  ConnectionState.connecting,
  ConnectionState.connected
]

# Verify resume was attempted
log = session.get_log()
ws_connects = log.filter(e => e.type == "ws_connect")
ASSERT ws_connects.length >= 2
ASSERT ws_connects[1].queryParams["resume"] IS NOT null

# No error reason after successful reconnection
ASSERT client.connection.errorReason IS null
```

### Cleanup

```pseudo
client.connection.close()
AWAIT_STATE client.connection.state == ConnectionState.closed
  WITH timeout: 10s
session.close()
```

---

## Integration Test Notes

### Timeout Handling

All `AWAIT_STATE` calls use generous timeouts since real network traffic through the proxy is involved:
- Initial CONNECTED: 15 seconds (auth + transport setup through proxy)
- Reconnection CONNECTED: 15 seconds (allows for SDK retry logic + network round-trip)
- DISCONNECTED (injected): 10 seconds (1s proxy delay + processing)
- FAILED: 15 seconds (SDK may attempt intermediate steps)
- CLOSED (cleanup): 10 seconds

### Error Handling

If any test fails to reach an expected state:
- Log the connection `errorReason`
- Log all recorded `state_changes`
- Retrieve and log the proxy session event log via `session.get_log()`
- Fail with diagnostic information

### Cleanup

Always clean up both the SDK client and the proxy session:

```pseudo
AFTER EACH TEST:
  IF client IS NOT null AND client.connection.state IN [connected, connecting, disconnected]:
    client.connection.close()
    AWAIT_STATE client.connection.state == ConnectionState.closed
      WITH timeout: 10s
  IF session IS NOT null:
    session.close()
```
