# Connection Resume and Recovery Proxy Integration Tests (RTN15, RTN16)

Spec points: `RTN15a`, `RTN15b`, `RTN15c6`, `RTN15c7`, `RTN15g`, `RTN15g2`, `RTN15h1`, `RTN15h3`, `RTN15j`, `RTN16d`, `RTN16l`, `RTN19a`, `RTN19a2`

## Test Type

Proxy integration test against Ably Sandbox endpoint.

Uses the programmable proxy (`uts/test/proxy/`) to inject transport-level faults while the SDK communicates with the real Ably backend. See `uts/test/realtime/integration/helpers/proxy.md` for proxy infrastructure details.

Corresponding unit tests: `uts/test/realtime/unit/connection/connection_failures_test.md`, `uts/test/realtime/unit/connection/connection_recovery_test.md`

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
  port_base = allocate_port_range(count: 11)
  # Tests use port_base + 0 through port_base + 10
```

---

## Test 6: RTN15a - Unexpected disconnect triggers resume

| Spec | Requirement |
|------|-------------|
| RTN15a | If transport is disconnected unexpectedly, attempt resume |

Tests that an unexpected transport disconnect causes the SDK to reconnect and attempt a resume, verified via the proxy event log.

**Unit test counterpart:** `connection_failures_test.md` > RTN15a

### Setup

**Proxy rules:** Close the WebSocket connection after a 1-second delay. This simulates an unexpected disconnect after the SDK has connected.

```pseudo
session = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 0,
  rules: [
    {
      match: { type: "delay_after_ws_connect", delayMs: 1000 },
      action: { type: "close" },
      times: 1,
      comment: "RTN15a: Close WebSocket after 1s to trigger unexpected disconnect"
    }
  ]
)
```

**SDK config:**

```pseudo
client = Realtime(options: ClientOptions(
  authCallback: (params) => {
    RETURN generate_jwt(keyName: key_name, keySecret: key_secret)
  },
  endpoint: "localhost",
  port: port_base + 0,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))
```

### Test Steps

```pseudo
# Register state listener BEFORE connecting so we capture all state transitions
state_changes = []
client.connection.on((change) => {
  state_changes.append(change.current)
})

# Connect through proxy
client.connect()

# Wait for first connected (rule fires after 1s, then proxy closes connection)
# SDK should reconnect and resume
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH condition: state_changes.filter(s => s == ConnectionState.connected).length >= 2
  WITH timeout: 30s
```

### Assertions

```pseudo
# State changes should include: connecting, connected, disconnected, connecting, connected
disconnectedIdx = state_changes.indexOf(ConnectionState.disconnected)
ASSERT disconnectedIdx >= 0

# After the disconnected, there should be another connecting and connected
postDisconnectConnectingIdx = state_changes.indexOf(ConnectionState.connecting, disconnectedIdx)
ASSERT postDisconnectConnectingIdx > disconnectedIdx

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

**Proxy rules:** Close the WebSocket connection after a 1-second delay.

```pseudo
session = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 1,
  rules: [
    {
      match: { type: "delay_after_ws_connect", delayMs: 1000 },
      action: { type: "close" },
      times: 1,
      comment: "RTN15b/c6: Close WebSocket after 1s to trigger resume"
    }
  ]
)
```

**SDK config:**

```pseudo
client = Realtime(options: ClientOptions(
  authCallback: (params) => {
    RETURN generate_jwt(keyName: key_name, keySecret: key_secret)
  },
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

# Proxy closes connection after 1s; wait for disconnected then reconnected
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 10s

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

**Proxy rules:** Two rules work together:
1. Close the WebSocket connection after 1 second (fires once) to trigger a resume attempt.
2. Replace the 2nd CONNECTED message (the resume response) with a crafted one that has a different connectionId and an error, simulating a failed resume.

```pseudo
session = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 2,
  rules: [
    {
      match: { type: "delay_after_ws_connect", delayMs: 1000 },
      action: { type: "close" },
      times: 1,
      comment: "RTN15c7: Close WebSocket after 1s to trigger resume attempt"
    },
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
  authCallback: (params) => {
    RETURN generate_jwt(keyName: key_name, keySecret: key_secret)
  },
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

# Proxy closes connection after 1s; wait for disconnected then reconnected
# SDK reconnects, but proxy replaces the CONNECTED response with a new connectionId
# SDK should still reach CONNECTED, but with the new identity
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 10s

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
# Provision a token via REST using the API key (promise-based)
rest = Ably.Rest(options: ClientOptions(key: api_key, endpoint: "sandbox"))
token_details = AWAIT rest.auth.requestToken()
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
# NOTE: ably-js reports error code 40171 ("Token not renewable") rather than the injected
# 40142, because the SDK detects it has no means to renew (no key, no authCallback, no
# authUrl) and substitutes a more specific error code before transitioning to FAILED.
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 40171
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
  authCallback: (params) => {
    RETURN generate_jwt(keyName: key_name, keySecret: key_secret)
  },
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

## Test 21: RTN15j - Fatal ERROR on established connection

| Spec | Requirement |
|------|-------------|
| RTN15j | If an ERROR ProtocolMessage with an empty channel attribute is received, this indicates a fatal error in the connection. The client should transition to the FAILED state triggering all attached channels to transition to the FAILED state as well. The Connection#errorReason should be set with the error received from Ably. |

Tests that a connection-level ERROR ProtocolMessage (no channel field) causes the connection to transition to FAILED, propagates the error to all attached channels, and that the SDK does not attempt to reconnect.

**Unit test counterpart:** `connection_failures_test.md` > RTN15j

### Setup

**Proxy rules:** None initially (passthrough). The ERROR is injected imperatively after connection and channel attachment complete.

```pseudo
session = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 5,
  rules: []
)
```

**SDK config:**

```pseudo
client = Realtime(options: ClientOptions(
  authCallback: (params) => {
    RETURN generate_jwt(keyName: key_name, keySecret: key_secret)
  },
  endpoint: "localhost",
  port: port_base + 5,
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

# Attach two channels in parallel
channel_a = client.channels.get(uniqueChannelName("fatal-error-a"))
channel_b = client.channels.get(uniqueChannelName("fatal-error-b"))
AWAIT Promise.all([channel_a.attach(), channel_b.attach()])
  WITH timeout: 15s

# Record state changes
connection_state_changes = []
client.connection.on((change) => {
  connection_state_changes.append(change.current)
})
channel_a_state_changes = []
channel_a.on((change) => {
  channel_a_state_changes.append(change.current)
})
channel_b_state_changes = []
channel_b.on((change) => {
  channel_b_state_changes.append(change.current)
})

# Inject a connection-level ERROR via proxy imperative action
session.trigger_action({
  type: "inject_to_client",
  message: {
    "action": 9,
    "error": {
      "code": 50000,
      "statusCode": 500,
      "message": "Internal server error"
    }
  }
})

# SDK should transition to FAILED
AWAIT_STATE client.connection.state == ConnectionState.failed
  WITH timeout: 15s
```

### Assertions

```pseudo
# RTN15j: Connection is in FAILED state
ASSERT client.connection.state == ConnectionState.failed

# Connection errorReason has the injected error
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 50000
ASSERT client.connection.errorReason.statusCode == 500

# Both channels transitioned to FAILED
ASSERT channel_a.state == ChannelState.failed
ASSERT channel_b.state == ChannelState.failed

# Channel errors match the connection error
ASSERT channel_a.errorReason IS NOT null
ASSERT channel_a.errorReason.code == 50000
ASSERT channel_b.errorReason IS NOT null
ASSERT channel_b.errorReason.code == 50000

# State change sequences
ASSERT connection_state_changes CONTAINS ConnectionState.failed
ASSERT channel_a_state_changes CONTAINS ChannelState.failed
ASSERT channel_b_state_changes CONTAINS ChannelState.failed

# No reconnection attempted — only the original ws_connect in the proxy log
log = session.get_log()
ws_connects = log.filter(e => e.type == "ws_connect")
ASSERT ws_connects.length == 1
```

### Cleanup

```pseudo
# No need to close — already in FAILED state
session.close()
```

---

## Test 22: RTN15g/g2 - connectionStateTtl expiry clears resume state

| Spec | Requirement |
|------|-------------|
| RTN15g | If disconnected for longer than connectionStateTtl, do not attempt resume; connect as a fresh connection |
| RTN15g2 | The staleness measure is whether the time since last activity exceeds connectionStateTtl + maxIdleInterval |

Tests that when the client has been disconnected for longer than connectionStateTtl + maxIdleInterval, the SDK does not attempt to resume. Instead it makes a fresh connection, resulting in a new connectionId.

**Unit test counterpart:** `connection_failures_test.md` > RTN15g

### Setup

**Proxy rules:** Three rules work together:
1. Replace the first CONNECTED message to inject short `connectionStateTtl` (2000ms) and `maxIdleInterval` (15000ms) into connectionDetails, and set a known `connectionId` so we can verify the final id differs.
2. Close the WebSocket connection after 1 second (fires once). At this point the client enters DISCONNECTED with `connectionStateTtl=2000ms`.
3. Refuse the second ws_connect (fires once). This keeps the client in DISCONNECTED while the TTL clock runs out, so when the TTL expires the client transitions to SUSPENDED. The third ws_connect (when the `suspendedRetryTimeout` fires) should be a fresh connection.

```pseudo
session = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 6,
  rules: [
    {
      "match": { "type": "ws_frame_to_client", "action": "CONNECTED", "count": 1 },
      "action": {
        "type": "replace",
        "message": {
          "action": 4,
          "connectionId": "proxy-ttl-test-id",
          "connectionKey": "__PASSTHROUGH__",
          "connectionDetails": {
            "connectionKey": "__PASSTHROUGH__",
            "clientId": null,
            "maxMessageSize": 65536,
            "maxInboundRate": 250,
            "maxOutboundRate": 100,
            "maxFrameSize": 524288,
            "serverId": "test-server",
            "connectionStateTtl": 2000,
            "maxIdleInterval": 15000
          }
        }
      },
      "times": 1,
      "comment": "RTN15g: Replace 1st CONNECTED to set short connectionStateTtl (2s) and known connectionId"
    },
    {
      "match": { "type": "delay_after_ws_connect", "delayMs": 1000 },
      "action": { "type": "close" },
      "times": 1,
      "comment": "RTN15g: Close connection after 1s — client enters DISCONNECTED with 2s TTL"
    },
    {
      "match": { "type": "ws_connect", "count": 2 },
      "action": { "type": "refuse" },
      "times": 1,
      "comment": "RTN15g: Refuse 2nd ws_connect — keeps client disconnected until TTL expires and SUSPENDED fires"
    }
  ]
)
```

**SDK config:** Use a short `suspendedRetryTimeout` so the test doesn't wait long after SUSPENDED.

```pseudo
client = Realtime(options: ClientOptions(
  authCallback: (params) => {
    RETURN generate_jwt(keyName: key_name, keySecret: key_secret)
  },
  endpoint: "localhost",
  port: port_base + 6,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false,
  suspendedRetryTimeout: 1000
))
```

### Test Steps

```pseudo
# Connect through proxy — first CONNECTED is replaced with short TTL and known connectionId
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15s

# Verify proxy-injected connectionId
ASSERT client.connection.id == "proxy-ttl-test-id"

# T=1s: proxy closes connection -> DISCONNECTED
# T=1-3s: retry attempt is refused -> stays DISCONNECTED
# T=3s: connectionStateTtl(2s) expires -> SUSPENDED
# T=4s: suspendedRetryTimeout(1s) fires -> fresh ws_connect (no resume)
# -> CONNECTED with new connectionId from real server

AWAIT_STATE client.connection.state == ConnectionState.suspended
  WITH timeout: 15s

# After suspended, SDK makes a fresh connection
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15s
```

### Assertions

```pseudo
# RTN15g: Connection ID changed (fresh connection, not resumed)
ASSERT client.connection.id != "proxy-ttl-test-id"

# Verify the proxy log shows at least 3 ws_connects
log = session.get_log()
ws_connects = log.filter(e => e.type == "ws_connect")
ASSERT ws_connects.length >= 3

# First ws_connect: initial — no resume
ASSERT ws_connects[0].queryParams["resume"] IS null

# Last ws_connect: fresh connection after TTL expiry — no resume
last_ws_connect = ws_connects[ws_connects.length - 1]
ASSERT last_ws_connect.queryParams["resume"] IS null
```

### Cleanup

```pseudo
client.connection.close()
AWAIT_STATE client.connection.state == ConnectionState.closed
  WITH timeout: 10s
session.close()
```

---

## Test 23: RTN19a/a2 - Unacked messages resent on new transport after resume

| Spec | Requirement |
|------|-------------|
| RTN19a | Any ProtocolMessage awaiting ACK/NACK on the old transport must be resent on the new transport |
| RTN19a2 | On successful resume (RTN15c6), the resent messages retain the same msgSerial |

Tests that a message awaiting ACK on the old transport is resent after reconnection and resume, and that the publish eventually completes successfully.

**Unit test counterpart:** `connection_failures_test.md` > RTN19a

### Setup

**Proxy rules:** Suppress the first ACK (action 1) from the server. This causes the SDK to have an unacknowledged message when the disconnect occurs.

```pseudo
session = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 7,
  rules: [
    {
      "match": { "type": "ws_frame_to_client", "action": "ACK" },
      "action": {
        "type": "suppress"
      },
      "times": 1,
      "comment": "RTN19a: Suppress the first ACK so the SDK has a pending unacked message"
    }
  ]
)
```

**SDK config:**

```pseudo
client = Realtime(options: ClientOptions(
  authCallback: (params) => {
    RETURN generate_jwt(keyName: key_name, keySecret: key_secret)
  },
  endpoint: "localhost",
  port: port_base + 7,
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

# Attach a channel
channel = client.channels.get("test-resend-unacked")
channel.attach()
AWAIT_STATE channel.state == ChannelState.attached
  WITH timeout: 15s

# Start a publish — do NOT await it yet.
# The message is sent to the server, but the ACK is suppressed by the proxy rule.
publish_future = channel.publish("event", "test-data")

# Poll the proxy log until we can confirm both:
#   (a) the MESSAGE frame has been sent client->server (action==15)
#   (b) the ACK frame has been suppressed server->client (action==1 with ruleMatched)
# This avoids a fixed sleep and ensures the disconnect fires at the right moment.
poll_until(
  condition: () => {
    log = session.get_log()
    message_sent = log has ws_frame client_to_server action==15
    ack_suppressed = log has ws_frame server_to_client action==1 with ruleMatched
    return message_sent AND ack_suppressed
  },
  timeout: 10s
)

# Close the connection — the SDK has an unacked message pending
session.trigger_action({ type: "close" })

# SDK reconnects and resumes (the ACK suppression rule already fired once,
# so the reconnected session passes ACKs through normally)
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15s

# Now await the publish — it should complete successfully after the message
# is resent on the new transport and ACKed
AWAIT publish_future
  WITH timeout: 15s
```

### Assertions

```pseudo
# The publish completed successfully (no exception thrown)
ASSERT publish_future.completed == true
ASSERT publish_future.error IS null

# Verify resume occurred
log = session.get_log()
ws_connects = log.filter(e => e.type == "ws_connect")
ASSERT ws_connects.length >= 2
ASSERT ws_connects[1].queryParams["resume"] IS NOT null

# RTN19a: The MESSAGE frame was sent on both transports (original + resend)
message_frames = log.filter(e =>
  e.type == "ws_frame_to_server" AND
  e.message.action == "MESSAGE"
)
ASSERT message_frames.length >= 2

# RTN19a2: On successful resume, the resent message has the same msgSerial
ASSERT message_frames[0].message.msgSerial == message_frames[1].message.msgSerial

# Successful resume: connectionId preserved
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

## Test 24: RTN16d - Successful recovery preserves connectionId and updates connectionKey

| Spec | Requirement |
|------|-------------|
| RTN16d | After a connection has been successfully recovered, Connection#id should be identical to the id of the connection that was recovered, and Connection#key should have been updated to the ConnectionDetails#connectionKey provided in the CONNECTED ProtocolMessage |
| RTN16k | The first connection with a `recover` option should add a `recover` querystring param set from the connectionKey component of the recoveryKey |

Tests that when a client is instantiated with a `recover` option containing a valid recovery key obtained from a previous connection, the SDK sends the `recover` query parameter, and after successful recovery the connectionId is preserved and the connectionKey is updated.

**Unit test counterpart:** `connection_recovery_test.md` > RTN16k, RTN16g

### Setup

**Step 1: Establish an initial connection and obtain a recovery key.**

Use a direct proxy session (passthrough, no rules) to connect to the sandbox, attach a channel, and capture the recovery key.

```pseudo
session_1 = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 8,
  rules: []
)

client_1 = Realtime(options: ClientOptions(
  authCallback: (params) => {
    RETURN generate_jwt(keyName: key_name, keySecret: key_secret)
  },
  endpoint: "localhost",
  port: port_base + 8,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))
```

**Step 2: Create a second client using the recovery key.**

A second proxy session is used so we can inspect the `recover` query parameter in the log.

```pseudo
session_2 = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 9,
  rules: []
)
```

### Test Steps

```pseudo
# --- Phase 1: Obtain recovery key from first client ---

client_1.connect()
AWAIT_STATE client_1.connection.state == ConnectionState.connected
  WITH timeout: 15s

original_connection_id = client_1.connection.id
original_connection_key = client_1.connection.key
ASSERT original_connection_id IS NOT null

# Attach a channel so it appears in the recovery key
channel_1 = client_1.channels.get(uniqueChannelName("recovery-test"))
channel_1.attach()
AWAIT_STATE channel_1.state == ChannelState.attached
  WITH timeout: 15s

# Get the recovery key
recovery_key = client_1.connection.createRecoveryKey()
ASSERT recovery_key IS NOT null

# Close the first client's transport WITHOUT closing the Ably connection gracefully.
# We want the server to keep the connection state alive for recovery.
# Use session_1.trigger_action to forcibly close the WebSocket.
session_1.trigger_action({ type: "close" })

# Wait for the client to detect the disconnect
AWAIT_STATE client_1.connection.state == ConnectionState.disconnected
  WITH timeout: 10s

# Close client_1 without allowing it to reconnect
client_1.connection.close()
AWAIT_STATE client_1.connection.state == ConnectionState.closed
  WITH timeout: 10s
session_1.close()

# --- Phase 2: Recover using the recovery key ---

client_2 = Realtime(options: ClientOptions(
  authCallback: (params) => {
    RETURN generate_jwt(keyName: key_name, keySecret: key_secret)
  },
  endpoint: "localhost",
  port: port_base + 9,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false,
  recover: recovery_key
))

client_2.connect()
AWAIT_STATE client_2.connection.state == ConnectionState.connected
  WITH timeout: 15s
```

### Assertions

```pseudo
# RTN16d: Connection ID is preserved (same as original connection)
ASSERT client_2.connection.id == original_connection_id

# RTN16d: Connection key is updated (new key from server)
ASSERT client_2.connection.key IS NOT null
ASSERT client_2.connection.key != original_connection_key

# RTN16k: Verify the recover query parameter was sent via proxy log
log = session_2.get_log()
ws_connects = log.filter(e => e.type == "ws_connect")
ASSERT ws_connects.length >= 1
ASSERT ws_connects[0].queryParams["recover"] == original_connection_key

# No resume param (this is recovery, not resume)
ASSERT ws_connects[0].queryParams["resume"] IS null

# No error on successful recovery
ASSERT client_2.connection.errorReason IS null
```

### Cleanup

```pseudo
client_2.connection.close()
AWAIT_STATE client_2.connection.state == ConnectionState.closed
  WITH timeout: 10s
session_2.close()
```

---

## Test 25: RTN16l - Recovery failure treated as fresh connection (per RTN15c7)

| Spec | Requirement |
|------|-------------|
| RTN16l | Recovery failures should be handled identically to resume failures, per RTN15c7, RTN15c5, and RTN15c4 |
| RTN15c7 | If recovery/resume fails, server sends CONNECTED with a new connectionId and an error; client resets msgSerial to 0 |

Tests that when a recovery attempt fails (the server responds with a new connectionId and an error because it cannot recover the connection), the SDK handles it as a fresh connection: it gets a new connectionId, sets the error on the connection, and the client remains in CONNECTED state.

**Unit test counterpart:** `connection_recovery_test.md` > RTN16f

### Setup

**Proxy rules:** Replace the first CONNECTED response with one that has a different connectionId and an error, simulating the server rejecting the recovery attempt.

```pseudo
session = create_proxy_session(
  endpoint: "sandbox",
  port: port_base + 10,
  rules: [
    {
      "match": { "type": "ws_frame_to_client", "action": "CONNECTED", "count": 1 },
      "action": {
        "type": "replace",
        "message": {
          "action": 4,
          "connectionId": "recovery-failed-new-id",
          "connectionKey": "recovery-failed-new-key",
          "connectionDetails": {
            "connectionKey": "recovery-failed-new-key",
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
      "comment": "RTN16l: Replace CONNECTED with recovery failure (new connectionId + error 80008)"
    }
  ]
)
```

**SDK config:** Use a fabricated recovery key. The connectionKey doesn't need to be valid since the proxy will replace the server response anyway.

```pseudo
fabricated_recovery_key = toJson({
  "connectionKey": "stale-old-key",
  "msgSerial": 99,
  "channelSerials": {
    "old-channel": "old-serial"
  }
})

client = Realtime(options: ClientOptions(
  authCallback: (params) => {
    RETURN generate_jwt(keyName: key_name, keySecret: key_secret)
  },
  endpoint: "localhost",
  port: port_base + 10,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false,
  recover: fabricated_recovery_key
))
```

### Test Steps

```pseudo
# Connect with the fabricated recovery key
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15s
```

### Assertions

```pseudo
# RTN16l + RTN15c7: Connection got a new ID (recovery failed)
ASSERT client.connection.id == "recovery-failed-new-id"
ASSERT client.connection.key == "recovery-failed-new-key"

# RTN15c7: Error is set on the connection indicating recovery failure
ASSERT client.connection.errorReason IS NOT null
ASSERT client.connection.errorReason.code == 80008

# Connection is still CONNECTED (not FAILED — the server gave a new connection)
ASSERT client.connection.state == ConnectionState.connected

# Verify the recover param was sent via proxy log
log = session.get_log()
ws_connects = log.filter(e => e.type == "ws_connect")
ASSERT ws_connects.length >= 1
ASSERT ws_connects[0].queryParams["recover"] == "stale-old-key"
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

### Temporal Triggers vs Imperative Actions

Where possible, tests use temporal proxy rules (e.g. `delay_after_ws_connect` + `close`) rather than imperative `session.trigger_action({ type: "disconnect" })` calls. Temporal triggers are deterministic — the proxy fires them at a known point in the connection lifecycle — whereas imperative actions can race with SDK internal state transitions, leading to flaky tests.

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
