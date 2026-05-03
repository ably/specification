# Auth Re-authorization Proxy Integration Tests

Spec points: `RTN22`, `RTC8a`

## Test Type

Proxy integration test against Ably Sandbox endpoint.

Uses the programmable proxy (`uts/test/proxy/`) to inject transport-level faults while the SDK communicates with the real Ably backend. See `uts/test/realtime/integration/helpers/proxy.md` for proxy infrastructure details.

Corresponding unit tests:
- `uts/test/realtime/unit/connection/server_initiated_reauth_test.md` (RTN22, RTN22a)
- `uts/test/realtime/unit/auth/realtime_authorize.md` (RTC8a, RTC8a1)
- `uts/test/realtime/unit/auth/connection_auth_test.md` (RSA4c3 covers RTN22 reauth failure while CONNECTED)

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
  port_base = allocate_port_range(count: 1)
  # Tests use port_base + 0
```

---

## Test 26: RTN22/RTC8a -- Server-initiated re-authentication

| Spec | Requirement |
|------|-------------|
| RTN22 | Ably can request that a connected client re-authenticates by sending an AUTH ProtocolMessage. The client must then immediately start a new authentication process. |
| RTC8a | If the connection is CONNECTED and Ably requests re-authentication, the client must obtain a new token, then send an AUTH ProtocolMessage to Ably with an auth attribute containing an AuthDetails object with the token string. |

Tests that when the proxy injects a server-initiated AUTH ProtocolMessage (action 17) into an established connection, the SDK re-authenticates via the authCallback and sends an AUTH message back to the server, all while remaining CONNECTED.

**Unit test counterpart:** `server_initiated_reauth_test.md` > RTN22

### Setup

**Proxy rules:** None (passthrough). The AUTH injection is triggered imperatively after the SDK connects.

```pseudo
session = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 0,
  rules: []
)
```

**SDK config:** Use authCallback so re-authentication can be observed. The callback generates a JWT token from the sandbox key parts.

```pseudo
auth_callback_count = 0
key_name, key_secret = get_key_parts(api_key)

auth_callback = FUNCTION(params, callback):
  auth_callback_count = auth_callback_count + 1
  # Generate a JWT token signed with the sandbox key
  jwt = generate_jwt(key_name: key_name, key_secret: key_secret)
  callback(null, jwt)

client = Realtime(options: ClientOptions(
  authCallback: auth_callback,
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

# Record identity and auth state before injection
original_connection_id = client.connection.id
original_auth_callback_count = auth_callback_count
ASSERT original_connection_id IS NOT null
ASSERT original_auth_callback_count >= 1

# Record state changes from this point
state_changes = []
client.connection.on((change) => {
  state_changes.append(change.current)
})

# Inject a server-initiated AUTH ProtocolMessage (action 17)
# This simulates Ably requesting re-authentication
AWAIT session.triggerAction({
  type: "inject_to_client",
  message: { action: 17 }
})

# Wait for the SDK to process the AUTH and send its response
# The authCallback should be invoked, and the SDK should send AUTH back.
# Allow time for the token request round-trip to the sandbox.
AWAIT pollUntil(
  CONDITION: auth_callback_count > original_auth_callback_count,
  timeout: 15s
)
```

### Assertions

```pseudo
# authCallback was called again (re-authentication triggered)
ASSERT auth_callback_count == original_auth_callback_count + 1

# Connection remains CONNECTED (re-auth does not disrupt the connection)
ASSERT client.connection.state == ConnectionState.connected

# Connection ID is unchanged (no reconnection occurred)
ASSERT client.connection.id == original_connection_id

# No state transitions away from CONNECTED occurred
non_connected_changes = state_changes.filter(
  s => s != "connected"
)
ASSERT non_connected_changes.length == 0

# Proxy log shows the SDK sent an AUTH frame (action 17) from client to server
log = AWAIT session.getLog()
client_auth_frames = log.filter(
  e => e.type == "ws_frame"
    AND e.direction == "client_to_server"
    AND (e.message.action == 17 OR e.message.action == "AUTH")
    AND e.message.auth IS NOT null
)
ASSERT client_auth_frames.length >= 1
```

### Cleanup

```pseudo
client.connection.close()
AWAIT_STATE client.connection.state == ConnectionState.closed
  WITH timeout: 10s
session.close()
```

### Note

After the SDK sends the AUTH response, the server may respond with a CONNECTED message (connection update per RTN24). However, since the injected AUTH was not a genuine server request (it was injected by the proxy), the real Ably server may not respond as expected. The key assertions are that the SDK's auth machinery was triggered (authCallback invoked, AUTH frame sent) and that the connection was not disrupted.

---

## Integration Test Notes

### Timeout Handling

All `AWAIT_STATE` calls use generous timeouts since real network traffic through the proxy is involved:
- Initial CONNECTED: 15 seconds (auth + transport setup through proxy)
- Auth callback re-invocation: 15 seconds (allows for token request round-trip to sandbox)
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
