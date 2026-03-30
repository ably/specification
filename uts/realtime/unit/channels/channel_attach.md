# RealtimeChannel Attach Tests

Spec points: `RTL4`, `RTL4a`, `RTL4b`, `RTL4c`, `RTL4c1`, `RTL4f`, `RTL4g`, `RTL4h`, `RTL4i`, `RTL4j`, `RTL4k`, `RTL4l`, `RTL4m`

## Test Type
Unit test with mocked WebSocket

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTL4a - Attach when already attached is no-op

**Spec requirement:** If already ATTACHED nothing is done.

Tests that calling attach on an already-attached channel returns immediately.

### Setup
```pseudo
channel_name = "test-RTL4a-${random_id()}"
attach_message_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_message_count++
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# First attach
AWAIT channel.attach()
ASSERT channel.state == ChannelState.attached
ASSERT attach_message_count == 1

# Second attach - should be no-op
AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT attach_message_count == 1  # No additional ATTACH message sent
```

---

## RTL4h - Attach while attaching waits for completion

**Spec requirement:** If the channel is in a pending state ATTACHING, do the attach operation after the completion of the pending request.

Tests that calling attach while already attaching waits for the first attach to complete.

### Setup
```pseudo
channel_name = "test-RTL4h-${random_id()}"
attach_message_count = 0
attach_responses_sent = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_message_count++
      # Delay response to allow second attach call
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Start first attach (don't await)
attach_future_1 = channel.attach()

# Wait for channel to enter attaching state
AWAIT_STATE channel.state == ChannelState.attaching

# Start second attach while first is pending
attach_future_2 = channel.attach()

# Now send the ATTACHED response
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: channel_name
))

# Both should complete
AWAIT attach_future_1
AWAIT attach_future_2
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT attach_message_count == 1  # Only one ATTACH message sent
```

---

## RTL4h - Attach while detaching waits then attaches

**Spec requirement:** If the channel is in a pending state DETACHING, do the attach operation after the completion of the pending request.

Tests that calling attach while detaching waits for detach to complete, then attaches.

### Setup
```pseudo
channel_name = "test-RTL4h-detaching-${random_id()}"
messages_from_client = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    messages_from_client.append(msg)
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == DETACH:
      # Delay DETACHED response
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Attach first
AWAIT channel.attach()
ASSERT channel.state == ChannelState.attached

# Start detach (don't await)
detach_future = channel.detach()
AWAIT_STATE channel.state == ChannelState.detaching

# Start attach while detaching
attach_future = channel.attach()

# Send DETACHED response
mock_ws.send_to_client(ProtocolMessage(
  action: DETACHED,
  channel: channel_name
))

# Wait for detach to complete
AWAIT detach_future

# Now ATTACH should be sent and we wait for it
AWAIT attach_future
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
# Should have: ATTACH, DETACH, ATTACH
attach_messages = filter(messages_from_client, (m) => m.action == ATTACH)
ASSERT length(attach_messages) == 2
```

---

## RTL4g - Attach from failed state clears errorReason

**Spec requirement:** If the channel is in the FAILED state, the attach request sets its errorReason to null, and proceeds with a channel attach.

Tests that attaching from failed state clears the error and attempts attach.

### Setup
```pseudo
channel_name = "test-RTL4g-${random_id()}"
attach_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      IF attach_count == 1:
        # First attach fails
        mock_ws.send_to_client(ProtocolMessage(
          action: ERROR,
          channel: channel_name,
          error: ErrorInfo(code: 40160, message: "Denied")
        ))
      ELSE:
        # Second attach succeeds
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: channel_name
        ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# First attach fails
AWAIT channel.attach() FAILS WITH error
ASSERT channel.state == ChannelState.failed
ASSERT channel.errorReason IS NOT null

# Second attach from failed state
AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT channel.errorReason IS null
```

---

## RTL4b - Attach fails when connection is closed

**Spec requirement:** If the connection state is CLOSED, CLOSING, SUSPENDED or FAILED, the attach request results in an error.

Tests that attach fails when connection is in closed state.

### Setup
```pseudo
channel_name = "test-RTL4b-closed-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE)
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Close the connection
AWAIT client.close()
ASSERT client.connection.state == ConnectionState.closed

# Try to attach
AWAIT channel.attach() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code IS NOT null
ASSERT channel.state != ChannelState.attached
```

---

## RTL4b - Attach fails when connection is failed

**Spec requirement:** If the connection state is FAILED, the attach request results in an error.

Tests that attach fails when connection is in failed state.

### Setup
```pseudo
channel_name = "test-RTL4b-failed-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED_MESSAGE)
    # Server sends fatal error
    mock_ws.send_to_client_and_close(ProtocolMessage(
      action: ERROR,
      error: ErrorInfo(code: 80000, message: "Fatal error")
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.failed

# Try to attach
AWAIT channel.attach() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
ASSERT channel.state != ChannelState.attached
```

---

## RTL4b - Attach fails when connection is suspended

**Spec requirement:** If the connection state is SUSPENDED, the attach request results in an error.

Tests that attach fails when connection is in suspended state.

### Setup
```pseudo
channel_name = "test-RTL4b-suspended-${random_id()}"

# Configure client with short suspend timeout for testing
client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  suspendedRetryTimeout: 100  # Short timeout for testing
))
channel = client.channels.get(channel_name)

# Mock that refuses all connections to trigger suspended state
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_refused()
)
install_mock(mock_ws)
```

### Test Steps
```pseudo
client.connect()

# Wait for connection to enter suspended state after retries exhausted
AWAIT_STATE client.connection.state == ConnectionState.suspended

# Try to attach
AWAIT channel.attach() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
ASSERT channel.state != ChannelState.attached
```

---

## RTL4i - Attach queued when connection is connecting

**Spec requirement:** If the connection state is INITIALIZED, CONNECTING or DISCONNECTED, the channel should be put into the ATTACHING state.

Tests that attach transitions channel to attaching when connection is connecting.

### Setup
```pseudo
channel_name = "test-RTL4i-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    # Delay connection response
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Start connecting but don't complete
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connecting

# Start attach while connection is still connecting
attach_future = channel.attach()

# Channel should immediately enter attaching
AWAIT_STATE channel.state == ChannelState.attaching
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attaching
# Attach message not yet sent (connection not ready)
```

---

## RTL4i - Attach completes when connection becomes connected

**Spec requirement:** Attach message will be sent once the connection becomes CONNECTED.

Tests that queued attach completes when connection is established.

### Setup
```pseudo
channel_name = "test-RTL4i-connected-${random_id()}"
attach_message_received = false

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    # Delay connection response
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_message_received = true
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Start connecting
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connecting

# Start attach while connecting
attach_future = channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching
ASSERT attach_message_received == false

# Complete connection
pending_conn = AWAIT mock_ws.await_connection_attempt()
pending_conn.respond_with_success(CONNECTED_MESSAGE)

# Wait for attach to complete
AWAIT attach_future
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT attach_message_received == true
```

---

## RTL4c - Attach sends ATTACH message and transitions to attaching

**Spec requirement:** An ATTACH ProtocolMessage is sent to the server, the state transitions to ATTACHING.

Tests the normal attach flow.

### Setup
```pseudo
channel_name = "test-RTL4c-${random_id()}"
captured_attach_message = null

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      captured_attach_message = msg
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

state_during_attach = null
channel.on(ChannelEvent.attaching).listen((change) => {
  state_during_attach = channel.state
})

AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT state_during_attach == ChannelState.attaching
ASSERT channel.state == ChannelState.attached
ASSERT captured_attach_message IS NOT null
ASSERT captured_attach_message.action == ATTACH
ASSERT captured_attach_message.channel == channel_name
```

---

## RTL4c1 - ATTACH message includes channelSerial when available

**Spec requirement:** The ATTACH ProtocolMessage channelSerial field must be set to the RTL15b channelSerial.

Tests that channelSerial is included in ATTACH message when available.

### Setup
```pseudo
channel_name = "test-RTL4c1-${random_id()}"
captured_attach_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      captured_attach_messages.append(msg)
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        channelSerial: "serial-from-server-1"
      ))
    ELSE IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# First attach - no channelSerial yet
AWAIT channel.attach()

# Detach
AWAIT channel.detach()

# Second attach - should include channelSerial from previous ATTACHED
AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT length(captured_attach_messages) == 2
# First attach has no channelSerial (or null)
ASSERT captured_attach_messages[0].channelSerial IS null OR captured_attach_messages[0].channelSerial IS NOT SET
# Second attach includes channelSerial from previous attachment
ASSERT captured_attach_messages[1].channelSerial == "serial-from-server-1"
```

---

## RTL4f - Attach times out and transitions to suspended

**Spec requirement:** If an ATTACHED ProtocolMessage is not received within realtimeRequestTimeout, the attach request should be treated as though it has failed and the channel should transition to the SUSPENDED state.

Tests attach timeout behavior.

### Setup
```pseudo
channel_name = "test-RTL4f-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Don't respond - simulate timeout
  }
)
install_mock(mock_ws)

# Use short timeout for testing
client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  realtimeRequestTimeout: 100  # 100ms timeout for testing
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

attach_future = channel.attach()

# Advance time past timeout
ADVANCE_TIME(150)

AWAIT attach_future FAILS WITH error
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.suspended
ASSERT error IS NOT null
```

---

## RTL4k - ATTACH includes params from ChannelOptions

**Spec requirement:** If the user has specified a non-empty params object in the ChannelOptions, it must be included in a params field of the ATTACH ProtocolMessage.

Tests that channel params are included in ATTACH message.

### Setup
```pseudo
channel_name = "test-RTL4k-${random_id()}"
captured_attach_message = null

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      captured_attach_message = msg
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))

channel_options = RealtimeChannelOptions(
  params: {"rewind": "1", "delta": "vcdiff"}
)
channel = client.channels.get(channel_name, channel_options)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT captured_attach_message IS NOT null
ASSERT captured_attach_message.params IS NOT null
ASSERT captured_attach_message.params["rewind"] == "1"
ASSERT captured_attach_message.params["delta"] == "vcdiff"
```

---

## RTL4l - ATTACH includes modes as flags

**Spec requirement:** If the user has specified a modes array in the ChannelOptions, it must be encoded as a bitfield and set as the flags field of the ATTACH ProtocolMessage.

Tests that channel modes are encoded in ATTACH flags.

### Setup
```pseudo
channel_name = "test-RTL4l-${random_id()}"
captured_attach_message = null

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      captured_attach_message = msg
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))

channel_options = RealtimeChannelOptions(
  modes: [ChannelMode.publish, ChannelMode.subscribe]
)
channel = client.channels.get(channel_name, channel_options)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT captured_attach_message IS NOT null
ASSERT captured_attach_message.flags IS NOT null
# Flags should include PUBLISH (131072, TR3r bit 17) and SUBSCRIBE (262144, TR3s bit 18) bits
ASSERT (captured_attach_message.flags AND 131072) != 0   # PUBLISH bit set
ASSERT (captured_attach_message.flags AND 262144) != 0  # SUBSCRIBE bit set
```

---

## RTL4m - Channel modes populated from ATTACHED response

**Spec requirement:** On receipt of an ATTACHED, the client library should decode the flags into an array of ChannelModes and expose it as a read-only modes field.

Tests that modes are decoded from ATTACHED flags.

### Setup
```pseudo
channel_name = "test-RTL4m-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: 393216  # PUBLISH (131072, TR3r) + SUBSCRIBE (262144, TR3s)
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT channel.modes IS NOT null
ASSERT ChannelMode.publish IN channel.modes
ASSERT ChannelMode.subscribe IN channel.modes
```

---

## RTL4j - ATTACH_RESUME flag set for reattach

**Spec requirement:** If the attach is not a clean attach, the library should set the ATTACH_RESUME flag in the ATTACH message.

Tests that ATTACH_RESUME flag is set on reattachment.

### Setup
```pseudo
channel_name = "test-RTL4j-${random_id()}"
captured_attach_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      captured_attach_messages.append(msg)
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
    ELSE IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# First attach - clean attach
AWAIT channel.attach()

# Detach
AWAIT channel.detach()

# Reattach - should have ATTACH_RESUME flag
AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT length(captured_attach_messages) == 2
# First attach should NOT have ATTACH_RESUME flag
ASSERT (captured_attach_messages[0].flags AND 32) == 0  # ATTACH_RESUME = 32
# Second attach SHOULD have ATTACH_RESUME flag
ASSERT (captured_attach_messages[1].flags AND 32) != 0  # ATTACH_RESUME = 32
```
