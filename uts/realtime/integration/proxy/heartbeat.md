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

Tests that when the proxy suppresses all server-to-client frames after the initial CONNECTED handshake, the SDK's heartbeat idle timer fires and the client transitions through DISCONNECTED before reconnecting successfully. This exercises the real idle timer logic (no fake timers) against a live Ably connection.

The server's CONNECTED message includes `connectionDetails.maxIdleInterval` (typically 15000ms). The SDK computes the heartbeat timeout as `maxIdleInterval + realtimeRequestTimeout`. With a shortened `realtimeRequestTimeout` of 5000ms, the total timeout is approximately 20s. The test uses a generous overall timeout of 45s.

### Setup

```pseudo
# Create proxy session that suppresses all server frames after initial CONNECTED settles
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "delay_after_ws_connect", "delayMs": 2000 },
    "action": { "type": "suppress_onwards" },
    "times": 1,
    "comment": "RTN23a: Suppress all server frames after 2s to starve heartbeats"
  }]
)

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false,
  realtimeRequestTimeout: 5000
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

# SDK receives real CONNECTED from Ably (within the 2s before suppression starts)
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15 seconds

# Capture connection details from the first connection
first_connection_id = client.connection.id
first_connection_key = client.connection.key
ASSERT first_connection_id IS NOT null

# Now all server frames are suppressed. The SDK's idle timer will fire after
# maxIdleInterval + realtimeRequestTimeout (~15s + 5s = ~20s).
# The SDK transitions to DISCONNECTED and reconnects.
# The suppress_onwards rule has times=1, so the second WS connection is unaffected.

# Wait for the SDK to disconnect and reconnect successfully
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 45 seconds
  WITH condition: client.connection.id != first_connection_id
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

The heartbeat starvation test (RTN23a) is inherently slow because the idle timer depends on `maxIdleInterval` from the server's CONNECTED message. The Ably sandbox typically sends `maxIdleInterval: 15000` (15 seconds). Combined with `realtimeRequestTimeout`, the total idle timeout is approximately 20 seconds. This is unavoidable in an integration test that exercises real timers against a real backend.

The unit tests in `heartbeat_test.md` use fake timers and short intervals for fast, deterministic testing of the same logic.

### `suppress_onwards` Semantics

The `suppress_onwards` action suppresses all subsequent server-to-client frames on the current WebSocket connection. It is a temporal rule triggered by `delay_after_ws_connect`, which means:

1. It fires once after the specified delay from the first WebSocket connect
2. With `times: 1`, it only applies to the first WS connection in the session
3. When the SDK reconnects with a new WebSocket connection, frames flow normally

This is the key mechanism that allows the test to verify heartbeat starvation on the first connection while permitting successful reconnection.

### Why Proxy Tests vs Unit Tests

These tests complement the unit tests in `heartbeat_test.md`:

1. **Real idle timer** -- the SDK's actual timer fires after real elapsed time, not fake timers
2. **Real `maxIdleInterval`** -- the value comes from the Ably sandbox's CONNECTED message, not a mock
3. **Real reconnection** -- the SDK reconnects through a real WebSocket to a real server
4. **Real `heartbeats=true` parameter** -- verified in the actual WebSocket URL captured by the proxy
