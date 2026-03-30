# Channel Fault Proxy Integration Tests

Spec points: `RTL4f`, `RTL4h`, `RTL5f`, `RTL13a`, `RTL14`

## Test Type

Proxy integration test against Ably Sandbox endpoint

## Proxy Infrastructure

See `uts/test/realtime/integration/helpers/proxy.md` for the full proxy infrastructure specification.

## Corresponding Unit Tests

- `uts/test/realtime/unit/channels/channel_attach.md` -- RTL4f (attach timeout), RTL4h (server error on attach)
- `uts/test/realtime/unit/channels/channel_detach.md` -- RTL5f (detach timeout)
- `uts/test/realtime/unit/channels/channel_server_initiated_detach.md` -- RTL13a (unsolicited DETACHED triggers reattach)
- `uts/test/realtime/unit/channels/channel_error.md` -- RTL14 (channel ERROR transitions to FAILED)

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

## Test 13: RTL4f -- Attach timeout (server doesn't respond)

| Spec | Requirement |
|------|-------------|
| RTL4f | If an ATTACHED ProtocolMessage is not received within realtimeRequestTimeout, the attach request should be treated as though it has failed and the channel should transition to the SUSPENDED state |

Tests that when the proxy suppresses the client's ATTACH message so the server never sees it, the SDK's attach timer fires and the channel transitions to SUSPENDED. This verifies the same behaviour as the unit test but with a real Ably connection and real clock timing.

### Setup

```pseudo
channel_name = "test-RTL4f-${random_id()}"

# Create proxy session that suppresses ATTACH messages for our channel
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "ws_frame_to_server", "action": "ATTACH", "channel": channel_name },
    "action": { "type": "suppress" },
    "comment": "RTL4f: Suppress ATTACH so server never responds"
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

channel = client.channels.get(channel_name)
```

### Test Steps

```pseudo
# Record channel state changes for sequence verification
channel_state_changes = []
channel.on((change) => {
  channel_state_changes.append(change.current)
})

# Connect through proxy -- connection itself is not faulted
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15 seconds

# Start attach -- proxy will suppress the ATTACH, so server never responds
attach_future = channel.attach()

# Channel should enter ATTACHING immediately
AWAIT_STATE channel.state == ChannelState.attaching
  WITH timeout: 5 seconds

# Wait for the channel to transition to SUSPENDED after realtimeRequestTimeout
AWAIT_STATE channel.state == ChannelState.suspended
  WITH timeout: 15 seconds

# The attach() call should have failed with a timeout error
AWAIT attach_future FAILS WITH error
```

### Assertions

```pseudo
# Channel transitioned to SUSPENDED
ASSERT channel.state == ChannelState.suspended

# Error indicates timeout
ASSERT error IS NOT null

# State sequence: ATTACHING -> SUSPENDED
ASSERT channel_state_changes CONTAINS_IN_ORDER [
  ChannelState.attaching,
  ChannelState.suspended
]

# Connection remains CONNECTED (attach timeout is channel-scoped)
ASSERT client.connection.state == ConnectionState.connected

# Proxy log confirms the ATTACH was suppressed (never forwarded to server)
log = session.get_log()
attach_frames_to_server = log.filter(e =>
  e.type == "ws_frame" AND
  e.direction == "client_to_server" AND
  e.message.action == 10 AND
  e.message.channel == channel_name
)
ASSERT attach_frames_to_server.length == 0
```

---

## Test 14: RTL4h / RTL14 -- Server responds with ERROR to ATTACH

| Spec | Requirement |
|------|-------------|
| RTL4h | If an ERROR ProtocolMessage is received for the channel during ATTACHING, the channel transitions to FAILED |
| RTL14 | If an ERROR ProtocolMessage is received for this channel, the channel should immediately transition to the FAILED state |

Tests that when the proxy replaces the server's ATTACHED response with a channel-scoped ERROR, the SDK transitions the channel to FAILED with the injected error. The connection should remain CONNECTED.

### Setup

```pseudo
channel_name = "test-RTL4h-${random_id()}"

# Create proxy session that replaces ATTACHED with channel ERROR
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "ws_frame_to_client", "action": "ATTACHED", "channel": channel_name },
    "action": {
      "type": "replace",
      "message": {
        "action": 9,
        "channel": channel_name,
        "error": { "code": 40160, "statusCode": 403, "message": "Not permitted" }
      }
    },
    "times": 1,
    "comment": "RTL4h: Replace ATTACHED with channel ERROR"
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

channel = client.channels.get(channel_name)
```

### Test Steps

```pseudo
# Record channel state changes for sequence verification
channel_state_changes = []
channel.on((change) => {
  channel_state_changes.append(change.current)
})

# Connect through proxy
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15 seconds

# Attach -- proxy replaces ATTACHED with ERROR
AWAIT channel.attach() FAILS WITH error

# Channel should be in FAILED state
AWAIT_STATE channel.state == ChannelState.failed
  WITH timeout: 10 seconds
```

### Assertions

```pseudo
# Channel transitioned to FAILED
ASSERT channel.state == ChannelState.failed

# Error reason matches the injected error
ASSERT channel.errorReason IS NOT null
ASSERT channel.errorReason.code == 40160
ASSERT channel.errorReason.statusCode == 403

# The error returned from attach() matches
ASSERT error IS NOT null
ASSERT error.code == 40160

# State sequence: ATTACHING -> FAILED
ASSERT channel_state_changes CONTAINS_IN_ORDER [
  ChannelState.attaching,
  ChannelState.failed
]

# Connection remains CONNECTED (channel error does not affect connection)
ASSERT client.connection.state == ConnectionState.connected
```

---

## Test 15: RTL5f -- Detach timeout (server doesn't respond)

| Spec | Requirement |
|------|-------------|
| RTL5f | If a DETACHED ProtocolMessage is not received within realtimeRequestTimeout, the detach request should be treated as though it has failed and the channel will return to its previous state |

Tests that when the channel is attached normally and then the proxy suppresses the DETACH message, the SDK's detach timer fires and the channel reverts to ATTACHED. This requires a two-phase proxy configuration: first allow normal attach, then add a rule to suppress DETACH.

### Setup

```pseudo
channel_name = "test-RTL5f-${random_id()}"

# Phase 1: Create proxy session with NO fault rules (clean passthrough)
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: []
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

channel = client.channels.get(channel_name)
```

### Test Steps

```pseudo
# Record channel state changes for sequence verification
channel_state_changes = []
channel.on((change) => {
  channel_state_changes.append(change.current)
})

# Phase 1: Connect and attach normally through proxy
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15 seconds

AWAIT channel.attach()
ASSERT channel.state == ChannelState.attached

# Clear state change history from the attach phase
channel_state_changes.clear()

# Phase 2: Add rule to suppress DETACH messages
session.add_rules([{
  "match": { "type": "ws_frame_to_server", "action": "DETACH", "channel": channel_name },
  "action": { "type": "suppress" },
  "comment": "RTL5f: Suppress DETACH so server never responds"
}], position: "prepend")

# Phase 3: Try to detach -- proxy suppresses DETACH, so server never sends DETACHED
detach_future = channel.detach()

# Channel should enter DETACHING
AWAIT_STATE channel.state == ChannelState.detaching
  WITH timeout: 5 seconds

# Wait for the channel to revert to ATTACHED after realtimeRequestTimeout
AWAIT_STATE channel.state == ChannelState.attached
  WITH timeout: 15 seconds

# The detach() call should have failed with a timeout error
AWAIT detach_future FAILS WITH error
```

### Assertions

```pseudo
# Channel reverted to ATTACHED (previous state)
ASSERT channel.state == ChannelState.attached

# Error indicates timeout
ASSERT error IS NOT null

# State sequence: DETACHING -> ATTACHED (revert)
ASSERT channel_state_changes CONTAINS_IN_ORDER [
  ChannelState.detaching,
  ChannelState.attached
]

# Connection remains CONNECTED
ASSERT client.connection.state == ConnectionState.connected
```

---

## Test 16: RTL13a -- Server sends unsolicited DETACHED, channel re-attaches

| Spec | Requirement |
|------|-------------|
| RTL13a | If the channel is ATTACHED and receives a server-initiated DETACHED, an immediate reattach attempt should be made by sending ATTACH, transitioning to ATTACHING with the error from the DETACHED message |

Tests that when the proxy injects an unsolicited DETACHED message for an attached channel, the SDK automatically re-attaches. The proxy passes all normal traffic through, and the re-attach ATTACH/ATTACHED exchange completes against the real server.

### Setup

```pseudo
channel_name = "test-RTL13a-${random_id()}"

# Create proxy session with clean passthrough (no fault rules initially)
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: []
)

client = Realtime(options: ClientOptions(
  key: api_key,
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
# Connect and attach normally through proxy
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15 seconds

AWAIT channel.attach()
ASSERT channel.state == ChannelState.attached

# Record channel state changes from this point
channel_state_changes = []
channel.on((change) => {
  channel_state_changes.append(change.current)
})

# Inject an unsolicited DETACHED message with error via imperative action
session.trigger_action({
  type: "inject_to_client",
  message: {
    "action": 13,
    "channel": channel_name,
    "error": { "code": 90198, "statusCode": 500, "message": "Channel detached by server" }
  }
})

# Channel should transition ATTACHING (reattach) -> ATTACHED (reattach succeeds)
AWAIT_STATE channel.state == ChannelState.attached
  WITH timeout: 15 seconds
```

### Assertions

```pseudo
# Channel re-attached successfully
ASSERT channel.state == ChannelState.attached

# State sequence: ATTACHING (with error from DETACHED) -> ATTACHED
ASSERT channel_state_changes CONTAINS_IN_ORDER [
  ChannelState.attaching,
  ChannelState.attached
]

# Connection remains CONNECTED throughout
ASSERT client.connection.state == ConnectionState.connected

# Proxy log shows the re-attach ATTACH message from the client
log = session.get_log()
attach_frames = log.filter(e =>
  e.type == "ws_frame" AND
  e.direction == "client_to_server" AND
  e.message.action == 10 AND
  e.message.channel == channel_name
)
# At least 2 ATTACH frames: initial attach + reattach after injected DETACHED
ASSERT attach_frames.length >= 2
```

---

## Test 17: RTL14 -- Server sends channel ERROR, channel goes FAILED

| Spec | Requirement |
|------|-------------|
| RTL14 | If an ERROR ProtocolMessage is received for this channel, the channel should immediately transition to the FAILED state, and the RealtimeChannel.errorReason should be set |

Tests that when the proxy injects a channel-scoped ERROR message for an attached channel, the SDK transitions the channel to FAILED. The connection should remain CONNECTED because the error is channel-scoped, not connection-scoped.

### Setup

```pseudo
channel_name = "test-RTL14-${random_id()}"

# Create proxy session with clean passthrough
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: []
)

client = Realtime(options: ClientOptions(
  key: api_key,
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
# Connect and attach normally through proxy
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15 seconds

AWAIT channel.attach()
ASSERT channel.state == ChannelState.attached

# Record channel state changes from this point
channel_state_changes = []
channel.on((change) => {
  channel_state_changes.append(change.current)
})

# Inject a channel-scoped ERROR message via imperative action
session.trigger_action({
  type: "inject_to_client",
  message: {
    "action": 9,
    "channel": channel_name,
    "error": { "code": 40160, "statusCode": 403, "message": "Not permitted" }
  }
})

# Channel should transition to FAILED
AWAIT_STATE channel.state == ChannelState.failed
  WITH timeout: 10 seconds
```

### Assertions

```pseudo
# Channel transitioned to FAILED
ASSERT channel.state == ChannelState.failed

# errorReason is set from the injected ERROR
ASSERT channel.errorReason IS NOT null
ASSERT channel.errorReason.code == 40160
ASSERT channel.errorReason.statusCode == 403
ASSERT channel.errorReason.message CONTAINS "Not permitted"

# State change event shows ATTACHED -> FAILED
ASSERT channel_state_changes CONTAINS_IN_ORDER [
  ChannelState.failed
]
ASSERT length(channel_state_changes) == 1

# Connection remains CONNECTED (channel-scoped ERROR does not close connection)
ASSERT client.connection.state == ConnectionState.connected
```

---

## Integration Test Notes

### Why Proxy Tests vs Unit Tests

These tests verify the same spec points as the unit tests, but provide higher confidence because:

1. **Real WebSocket connections** -- the SDK's actual transport layer is exercised
2. **Real Ably protocol** -- the proxy modifies real server responses, not synthetic mocks
3. **Real timing** -- timeout behaviour (RTL4f, RTL5f) is tested with actual clocks, not fake timers
4. **Real server interaction** -- the reattach in RTL13a completes against the live sandbox, verifying the full round-trip

### Timeout Handling

All `AWAIT_STATE` calls use generous timeouts because real network traffic is involved:
- Connection to CONNECTED via proxy: 15 seconds
- Channel state transitions with real server: 15 seconds
- Timeout-based transitions (RTL4f, RTL5f): realtimeRequestTimeout + 12 seconds headroom
- Cleanup close: 10 seconds

### Channel Names

Each test uses a unique channel name with a random component (`${random_id()}`) to avoid interference between tests running in the same sandbox app.

### Two-Phase Proxy Configuration

Test 15 (RTL5f) uses a two-phase approach:
1. Start with clean passthrough rules to allow normal connection and attach
2. Dynamically add fault rules via `session.add_rules()` before the detach attempt

This avoids needing separate proxy sessions for the attach and detach phases.
