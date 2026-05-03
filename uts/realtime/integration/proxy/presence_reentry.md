# Presence Re-entry Proxy Integration Tests

Spec points: `RTP17i`, `RTP17g`

## Test Type

Proxy integration test against Ably Sandbox endpoint

## Proxy Infrastructure

See `uts/test/realtime/integration/helpers/proxy.md` for the full proxy infrastructure specification.

## Corresponding Unit Tests

- `uts/test/realtime/unit/presence/realtime_presence_reentry.md` -- RTP17i (automatic re-entry on ATTACHED non-RESUMED), RTP17g (re-entry publishes ENTER with stored clientId and data)

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
  IF session IS NOT null:
    session.close()
    session = null
```

---

## Test 27: RTP17i/RTP17g -- Automatic presence re-enter on non-resumed reattach

| Spec | Requirement |
|------|-------------|
| RTP17i | The RealtimePresence object should perform automatic re-entry whenever the channel receives an ATTACHED ProtocolMessage, except in the case where the channel is already attached and the ProtocolMessage has the RESUMED bit flag set |
| RTP17g | Automatic re-entry consists of, for each member of the internal PresenceMap, publishing a PresenceMessage with an ENTER action using the clientId, data, and id attributes from that member |

Tests that when an already-attached channel receives an injected ATTACHED ProtocolMessage with `resumed=false` (flags=0, RESUMED bit not set), the SDK automatically re-enters all locally-entered presence members. Verified via proxy log: count PRESENCE frames (action=14, client_to_server) before injection, then poll until the count increases.

The server won't broadcast the re-enter to other subscribers (since from the server's perspective the member never left), so a second observer client is not used. The proxy log provides direct evidence of the SDK's wire behaviour.

### Setup

```pseudo
channel_name = unique_channel_name("test-rtp17i")

# Extract key name and key secret from the provisioned API key
key_parts = api_key.split(":")
key_name = key_parts[0]
key_secret = key_parts[1]

# Create proxy session with clean passthrough (no fault rules)
session = create_proxy_session(rules: [])

# client: the presence member, connects through the proxy so we can inject ATTACHED
# Needs a clientId for presence — use authCallback with JWT that includes clientId
client = Realtime(options: ClientOptions(
  authCallback: (params, cb) => {
    cb(null, generateJWT(keyName: key_name, keySecret: key_secret, clientId: "client-a"))
  },
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))

channel = client.channels.get(channel_name)
```

### Test Steps

```pseudo
# Phase 1 — Establish real presence state

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15 seconds

AWAIT channel.attach()
AWAIT channel.presence.enter(data: "hello")

# Phase 2 — Count PRESENCE frames in the log before injection

log_before = session.get_log()
presence_frames_before = log_before.filter(e =>
  e.type == "ws_frame" AND
  e.direction == "client_to_server" AND
  e.message.action == 14
).length

# Phase 3 — Inject ATTACHED with resumed=false (flags=0)
# This triggers RTP17i re-entry without needing an actual disconnect

session.trigger_action({
  type: "inject_to_client",
  message: {
    action: 11,
    channel: channel_name,
    flags: 0,
    error: { code: 91001, statusCode: 500, message: "Continuity lost" }
  }
})

# Phase 4 — Poll until a new PRESENCE frame appears in the log

POLL_UNTIL(timeout: 10 seconds, interval: 200ms):
  log = session.get_log()
  presence_frames = log.filter(e =>
    e.type == "ws_frame" AND
    e.direction == "client_to_server" AND
    e.message.action == 14
  )
  RETURN presence_frames.length > presence_frames_before
```

### Assertions

```pseudo
# Get final proxy log
log_after = session.get_log()
all_presence_frames = log_after.filter(e =>
  e.type == "ws_frame" AND
  e.direction == "client_to_server" AND
  e.message.action == 14
)

# At least one new PRESENCE frame was sent after the injection
ASSERT all_presence_frames.length > presence_frames_before

# The last (most recent) re-enter frame should contain the presence data
reenter_frame = all_presence_frames[all_presence_frames.length - 1]
ASSERT reenter_frame.message.presence IS NOT null
ASSERT reenter_frame.message.presence.length >= 1

# RTP17g: re-enter uses stored clientId, data, and ENTER action
reenter_msg = reenter_frame.message.presence[0]
ASSERT reenter_msg.clientId == "client-a"
ASSERT reenter_msg.data == "hello"
ASSERT reenter_msg.action == 2  # ENTER

# Channel should still be attached and connection still connected
ASSERT channel.state == ChannelState.attached
ASSERT client.connection.state == ConnectionState.connected
```

---

## Test 28: RTP17i -- Presence re-enter after real disconnect

| Spec | Requirement |
|------|-------------|
| RTP17i | The RealtimePresence object should perform automatic re-entry whenever the channel receives an ATTACHED ProtocolMessage, except in the case where the channel is already attached and the ProtocolMessage has the RESUMED bit flag set |

Tests the same RTP17i re-entry logic, but triggered via a real WebSocket disconnect and reconnect rather than injection. The proxy closes the WebSocket connection 3 seconds after it is established (giving time to attach and enter presence). On reconnect, the proxy replaces the 2nd ATTACHED message on the channel with a non-resumed one (flags=0), triggering re-entry. We verify via proxy log that a PRESENCE ENTER frame is sent after the 2nd `ws_connect` event.

### Setup

```pseudo
channel_name = unique_channel_name("test-rtp17i-real")

# Extract key name and key secret from the provisioned API key
key_parts = api_key.split(":")
key_name = key_parts[0]
key_secret = key_parts[1]

# Create proxy session with two fault rules:
# 1. Close the WebSocket 3s after connect (giving time to attach + enter presence)
# 2. Replace the 2nd ATTACHED on the channel with a non-resumed one
session = create_proxy_session(
  rules: [
    {
      match: { type: "delay_after_ws_connect", delayMs: 3000 },
      action: { type: "close" },
      times: 1,
      comment: "RTP17i: Close WebSocket after 3s to trigger reconnect"
    },
    {
      match: { type: "ws_frame_to_client", action: "ATTACHED", channel: channel_name, count: 2 },
      action: {
        type: "replace",
        message: {
          action: 11,
          channel: channel_name,
          flags: 0,
          error: { code: 91001, statusCode: 500, message: "Continuity lost" }
        }
      },
      times: 1,
      comment: "RTP17i: Replace 2nd ATTACHED with non-resumed to trigger re-entry"
    }
  ]
)

# client_a: the presence member, connects through the proxy
client_a = Realtime(options: ClientOptions(
  authCallback: (params, cb) => {
    cb(null, generateJWT(keyName: key_name, keySecret: key_secret, clientId: "client-a"))
  },
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))

channel_a = client_a.channels.get(channel_name)
```

### Test Steps

```pseudo
# Phase 1 — Establish presence before the proxy closes the connection

client_a.connect()
AWAIT_STATE client_a.connection.state == ConnectionState.connected
  WITH timeout: 15 seconds

AWAIT channel_a.attach()
AWAIT channel_a.presence.enter(data: "hello")

# Phase 2 — Wait for the temporal trigger to fire (at T+3s) and for reconnect

# The proxy's delay_after_ws_connect rule closes the WebSocket at T+3s
AWAIT_STATE client_a.connection.state == ConnectionState.disconnected
  WITH timeout: 10 seconds
AWAIT_STATE client_a.connection.state == ConnectionState.connected
  WITH timeout: 15 seconds

# Wait for the channel to reattach (the 2nd ATTACHED will be replaced with non-resumed)
AWAIT_STATE channel_a.state == ChannelState.attached
  WITH timeout: 15 seconds

# Phase 3 — Poll until a PRESENCE frame appears in the log after the 2nd ws_connect

POLL_UNTIL(timeout: 10 seconds, interval: 200ms):
  log = session.get_log()
  ws_connects = log.filter(e => e.type == "ws_connect")
  IF ws_connects.length < 2: RETURN false
  second_connect_time = ws_connects[1].timestamp
  presence_after_reconnect = log.filter(e =>
    e.type == "ws_frame" AND
    e.direction == "client_to_server" AND
    e.message.action == 14 AND
    e.timestamp > second_connect_time
  )
  RETURN presence_after_reconnect.length > 0
```

### Assertions

```pseudo
# Get final proxy log
log = session.get_log()
ws_connects = log.filter(e => e.type == "ws_connect")
second_connect_time = ws_connects[1].timestamp

reenter_frames = log.filter(e =>
  e.type == "ws_frame" AND
  e.direction == "client_to_server" AND
  e.message.action == 14 AND
  e.timestamp > second_connect_time
)

ASSERT reenter_frames.length >= 1

# Check the first re-enter frame
reenter_frame = reenter_frames[0]
ASSERT reenter_frame.message.presence IS NOT null
ASSERT reenter_frame.message.presence.length >= 1

# RTP17g: re-enter uses stored clientId, data, and ENTER action
reenter_msg = reenter_frame.message.presence[0]
ASSERT reenter_msg.clientId == "client-a"
ASSERT reenter_msg.data == "hello"
ASSERT reenter_msg.action == 2  # ENTER

# Channel is still attached and connection is still connected
ASSERT channel_a.state == ChannelState.attached
ASSERT client_a.connection.state == ConnectionState.connected
```

---

## Integration Test Notes

### Single-Client Design (Test 27)

Test 27 uses only one client (the presence member) rather than a second observer. Since from the server's perspective the member never left (we only injected ATTACHED on the client side without a real disconnect), the server does not broadcast a presence event to any observers. Verifying the re-entry via the proxy log is more reliable: the proxy log directly records every PRESENCE wire frame (action=14) sent from the SDK.

### Real Disconnect Design (Test 28)

Test 28 uses a temporal proxy rule (`delay_after_ws_connect` + `close`) to close the WebSocket 3 seconds after it opens. This gives enough time for the initial attach and presence enter to complete before the disconnect. On reconnect, a second proxy rule intercepts the 2nd ATTACHED on the channel (count: 2) and replaces it with a non-resumed message, triggering RTP17i re-entry.

### clientId and Authentication

Both tests use `authCallback` with `generateJWT` that includes the `clientId: "client-a"` claim. This avoids passing `clientId` directly on `ClientOptions` (which can trigger unexpected token auth flows) and provides direct control over the identity used for presence.

### Presence Action on Re-entry

Per RTP17g, the SDK sends a PRESENCE message with action ENTER (wire value 2). The proxy log captures this wire-level message. The assertion checks `presence[0].action == 2` directly on the frame in the proxy log.

### Proxy Log Frame Structure

Each `ws_frame` log entry has the shape:

```pseudo
{
  type: "ws_frame",
  direction: "client_to_server" | "server_to_client",
  timestamp: <unix ms>,
  message: {
    action: <int>,        # 14 == PRESENCE
    channel: <string>,
    presence: [           # present for PRESENCE messages
      {
        clientId: <string>,
        data: <any>,
        action: <int>     # 2 == ENTER
      }
    ]
  }
}
```

### Timeout Handling

All `AWAIT_STATE` and `POLL_UNTIL` calls use generous timeouts because real network traffic is involved:
- Connection to CONNECTED: 15 seconds
- Channel attach: implicit in the `AWAIT channel.attach()` call
- Disconnect detection: 10 seconds
- Presence re-entry poll: 10 seconds
- Cleanup close: implicit in `session.close()`

### Channel Names

Each test uses a unique channel name with a random component to avoid interference between tests running in the same sandbox app.
