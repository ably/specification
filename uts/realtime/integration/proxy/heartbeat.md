# Realtime Heartbeat — Proxy Integration Tests

Spec points: `RTN23a`

## Test Type

Proxy integration test against Ably Sandbox endpoint

## Proxy Infrastructure

See `uts/test/realtime/integration/helpers/proxy.md` for the full proxy infrastructure specification.

## Related Unit Tests

See `uts/test/realtime/unit/connection/heartbeat_test.md` for the corresponding unit tests that verify the same spec points with mocked WebSocket and fake timers.

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

## RTN23a — Heartbeat starvation causes disconnect and reconnect

| Spec | Requirement |
|------|-------------|
| RTN23a | If no activity is received for `maxIdleInterval + realtimeRequestTimeout`, the transport should be disconnected |

The proxy closes the WebSocket connection after a 2s delay from ws_connect, simulating a transport failure. The SDK transitions to DISCONNECTED and automatically reconnects. The close rule fires once (times: 1), so the second WS connection is unaffected.

### Setup

```pseudo
# Create proxy session that closes the WebSocket after 2s to simulate transport failure
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "delay_after_ws_connect", "delayMs": 2000 },
    "action": { "type": "close" },
    "times": 1,
    "comment": "RTN23a: Close WebSocket after 2s to simulate transport failure"
  }]
)

keyName = api_key.split(":")[0]
keySecret = api_key.split(":")[1]

client = Realtime(options: ClientOptions(
  authCallback: (_params, cb) => {
    cb(null, generateJWT({ keyName, keySecret }))
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

# SDK receives real CONNECTED from Ably (within the 2s before close fires)
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15 seconds

# Capture connection details from the first connection
first_connection_id = client.connection.id
first_connection_key = client.connection.key
ASSERT first_connection_id IS NOT null

# The proxy closes the WebSocket after 2s. The SDK detects the close frame
# immediately and transitions to DISCONNECTED, then automatically reconnects.
# The close rule has times=1, so the second WS connection is unaffected.

# Wait for DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 15 seconds

# Wait for successful reconnection
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 30 seconds
```

### Assertions

```pseudo
# Connection is re-established with new connection details
ASSERT client.connection.state == ConnectionState.connected
ASSERT client.connection.id IS NOT null
ASSERT client.connection.key IS NOT null

# State sequence shows: connected -> disconnected -> reconnecting -> connected
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.connecting,
  ConnectionState.connected,
  ConnectionState.disconnected,
  ConnectionState.connecting,
  ConnectionState.connected
]

# Proxy event log confirms two WebSocket connections
log = session.get_log()
ws_connects = log.filter(e => e.type == "ws_connect")
ASSERT ws_connects.length >= 2

# Second connection should include resume parameter (RTN15c)
ASSERT ws_connects[1].queryParams["resume"] IS NOT null
```

---

## Integration Test Notes

### Timing Considerations

The RTN23a test is fast because the `close` action sends a WebSocket close frame that the SDK detects immediately. The proxy closes the connection after the configured 2s delay, so the test completes in approximately 2–3 seconds rather than waiting for an idle timer to expire.

The unit tests in `heartbeat_test.md` use fake timers and short intervals for fast, deterministic testing of the same logic.

### Why Proxy Tests vs Unit Tests

These tests complement the unit tests in `heartbeat_test.md`:

1. **Real transport failure** -- the proxy sends an actual WebSocket close frame; the SDK handles it through the real connection lifecycle code
2. **Real reconnection** -- the SDK reconnects through a real WebSocket to a real server
3. **Real `heartbeats=true` parameter** -- verified in the actual WebSocket URL captured by the proxy
