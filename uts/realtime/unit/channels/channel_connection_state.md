# RealtimeChannel Connection State Side Effects Tests

Spec points: `RTL3`, `RTL3a`, `RTL3b`, `RTL3c`, `RTL3d`, `RTL3e`, `RTL4c1`

## Test Type
Unit test with mocked WebSocket

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTL3e - DISCONNECTED has no effect on ATTACHED channel

**Spec requirement:** If the connection state enters the DISCONNECTED state, it will have no effect on the channel states.

Tests that a channel in the ATTACHED state is unaffected when the connection transitions to DISCONNECTED.

### Setup
```pseudo
channel_name = "test-RTL3e-attached-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel
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
ASSERT channel.state == ChannelState.attached

# Record channel state changes from this point
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Simulate transport failure - connection goes to DISCONNECTED
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.disconnected
```

### Assertions
```pseudo
# Channel state must remain ATTACHED
ASSERT channel.state == ChannelState.attached

# No channel state change events should have been emitted
ASSERT length(channel_state_changes) == 0
CLOSE_CLIENT(client)
```

---

## RTL3e - DISCONNECTED has no effect on ATTACHING channel

**Spec requirement:** If the connection state enters the DISCONNECTED state, it will have no effect on the channel states.

Tests that a channel in the ATTACHING state is unaffected when the connection transitions to DISCONNECTED.

### Setup
```pseudo
channel_name = "test-RTL3e-attaching-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Do NOT respond - leave channel in ATTACHING state
      pass
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

# Start attach but don't await - server won't respond
attach_future = channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching

# Record channel state changes from this point
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Simulate transport failure - connection goes to DISCONNECTED
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.disconnected
```

### Assertions
```pseudo
# Channel state must remain ATTACHING
ASSERT channel.state == ChannelState.attaching

# No channel state change events should have been emitted
ASSERT length(channel_state_changes) == 0
CLOSE_CLIENT(client)
```

---

## RTL3a - FAILED connection transitions ATTACHED channel to FAILED

**Spec requirement:** If the connection state enters the FAILED state, then an ATTACHING or ATTACHED channel state will transition to FAILED and set the `RealtimeChannel#errorReason`.

Tests that attached channels transition to FAILED when the connection enters FAILED state.

### Setup
```pseudo
channel_name = "test-RTL3a-attached-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel
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
ASSERT channel.state == ChannelState.attached

# Record channel state changes
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Server sends a fatal connection-level ERROR
mock_ws.active_connection.send_to_client_and_close(ProtocolMessage(
  action: ERROR,
  error: ErrorInfo(
    code: 40198,
    statusCode: 403,
    message: "Account disabled"
  )
))
AWAIT_STATE client.connection.state == ConnectionState.failed
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.failed
ASSERT channel.errorReason IS NOT null
ASSERT channel.errorReason.code == 40198

# Channel state change event was emitted
ASSERT length(channel_state_changes) >= 1
failed_change = channel_state_changes.find(c => c.current == ChannelState.failed)
ASSERT failed_change IS NOT null
ASSERT failed_change.previous == ChannelState.attached
ASSERT failed_change.reason IS NOT null
ASSERT failed_change.reason.code == 40198
CLOSE_CLIENT(client)
```

---

## RTL3a - FAILED connection transitions ATTACHING channel to FAILED

**Spec requirement:** If the connection state enters the FAILED state, then an ATTACHING or ATTACHED channel state will transition to FAILED and set the `RealtimeChannel#errorReason`.

Tests that a channel in the ATTACHING state transitions to FAILED when the connection enters FAILED.

### Setup
```pseudo
channel_name = "test-RTL3a-attaching-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Do NOT respond - leave channel in ATTACHING state
      pass
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

# Start attach but don't await - server won't respond
attach_future = channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching

# Record channel state changes
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Server sends a fatal connection-level ERROR
mock_ws.active_connection.send_to_client_and_close(ProtocolMessage(
  action: ERROR,
  error: ErrorInfo(
    code: 40198,
    statusCode: 403,
    message: "Account disabled"
  )
))
AWAIT_STATE client.connection.state == ConnectionState.failed

# The pending attach should fail
AWAIT attach_future FAILS WITH error
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.failed
ASSERT channel.errorReason IS NOT null

failed_change = channel_state_changes.find(c => c.current == ChannelState.failed)
ASSERT failed_change IS NOT null
ASSERT failed_change.previous == ChannelState.attaching
CLOSE_CLIENT(client)
```

---

## RTL3a - Channels in other states are unaffected by FAILED connection

**Spec requirement:** If the connection state enters the FAILED state, then an ATTACHING or ATTACHED channel state will transition to FAILED.

Tests that channels in INITIALIZED, DETACHED, SUSPENDED, or FAILED states are not affected when the connection enters FAILED.

### Setup
```pseudo
initialized_channel_name = "test-RTL3a-init-${random_id()}"
detached_channel_name = "test-RTL3a-detached-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel
      ))
    ELSE IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: msg.channel
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
initialized_channel = client.channels.get(initialized_channel_name)
detached_channel = client.channels.get(detached_channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Leave initialized_channel in INITIALIZED state (never attach)
ASSERT initialized_channel.state == ChannelState.initialized

# Attach then detach to get to DETACHED state
AWAIT detached_channel.attach()
AWAIT detached_channel.detach()
ASSERT detached_channel.state == ChannelState.detached

# Record state changes on both channels
init_changes = []
detached_changes = []
initialized_channel.on().listen((change) => init_changes.append(change))
detached_channel.on().listen((change) => detached_changes.append(change))

# Server sends a fatal connection-level ERROR
mock_ws.active_connection.send_to_client_and_close(ProtocolMessage(
  action: ERROR,
  error: ErrorInfo(
    code: 40198,
    statusCode: 403,
    message: "Account disabled"
  )
))
AWAIT_STATE client.connection.state == ConnectionState.failed
```

### Assertions
```pseudo
# Channels not in ATTACHING/ATTACHED should be unaffected
ASSERT initialized_channel.state == ChannelState.initialized
ASSERT detached_channel.state == ChannelState.detached
ASSERT length(init_changes) == 0
ASSERT length(detached_changes) == 0
CLOSE_CLIENT(client)
```

---

## RTL3b - CLOSED connection transitions ATTACHED channel to DETACHED

**Spec requirement:** If the connection state enters the CLOSED state, then an ATTACHING or ATTACHED channel state will transition to DETACHED.

Tests that an attached channel transitions to DETACHED when the connection is explicitly closed.

### Setup
```pseudo
channel_name = "test-RTL3b-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel
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
ASSERT channel.state == ChannelState.attached

# Record channel state changes
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Close the connection
client.close()
AWAIT_STATE client.connection.state == ConnectionState.closed
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.detached

detached_change = channel_state_changes.find(c => c.current == ChannelState.detached)
ASSERT detached_change IS NOT null
ASSERT detached_change.previous == ChannelState.attached
CLOSE_CLIENT(client)
```

---

## RTL3b - CLOSED connection transitions ATTACHING channel to DETACHED

**Spec requirement:** If the connection state enters the CLOSED state, then an ATTACHING or ATTACHED channel state will transition to DETACHED.

Tests that a channel in the ATTACHING state transitions to DETACHED when the connection is closed.

### Setup
```pseudo
channel_name = "test-RTL3b-attaching-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Do NOT respond - leave channel in ATTACHING state
      pass
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

# Start attach but don't await - server won't respond
attach_future = channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching

# Record channel state changes
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Close the connection
client.close()
AWAIT_STATE client.connection.state == ConnectionState.closed

# The pending attach should fail
AWAIT attach_future FAILS WITH error
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.detached

detached_change = channel_state_changes.find(c => c.current == ChannelState.detached)
ASSERT detached_change IS NOT null
ASSERT detached_change.previous == ChannelState.attaching
CLOSE_CLIENT(client)
```

---

## RTL3c - SUSPENDED connection transitions ATTACHED channel to SUSPENDED

**Spec requirement:** If the connection state enters the SUSPENDED state, then an ATTACHING or ATTACHED channel state will transition to SUSPENDED.

Tests that an attached channel transitions to SUSPENDED when the connection enters SUSPENDED state.

### Setup
```pseudo
channel_name = "test-RTL3c-${random_id()}"

enable_fake_timers()

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(ProtocolMessage(
    action: CONNECTED,
    connectionId: "connection-id",
    connectionKey: "connection-key",
    connectionDetails: ConnectionDetails(
      connectionKey: "connection-key",
      maxIdleInterval: 15000,
      connectionStateTtl: 120000
    )
  )),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  fallbackHosts: [],
  disconnectedRetryTimeout: 1000
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()
ASSERT channel.state == ChannelState.attached

# Record channel state changes
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Simulate disconnect - all reconnection attempts will fail
mock_ws.onConnectionAttempt = (conn) => conn.respond_with_refused()
mock_ws.active_connection.simulate_disconnect()

# Connection must exhaust disconnectedRetryTimeout retries within connectionStateTtl
# to transition from DISCONNECTED to SUSPENDED. The total time advance must exceed
# connectionStateTtl (from connectionDetails, per RTN21).
LOOP up to 30 times:
  ADVANCE_TIME(5000)
  IF client.connection.state == ConnectionState.suspended:
    BREAK

AWAIT_STATE client.connection.state == ConnectionState.suspended
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.suspended

suspended_change = channel_state_changes.find(c => c.current == ChannelState.suspended)
ASSERT suspended_change IS NOT null
ASSERT suspended_change.previous == ChannelState.attached
CLOSE_CLIENT(client)
```

---

## RTL3c - SUSPENDED connection transitions ATTACHING channel to SUSPENDED

**Spec requirement:** If the connection state enters the SUSPENDED state, then an ATTACHING or ATTACHED channel state will transition to SUSPENDED.

Tests that a channel in the ATTACHING state transitions to SUSPENDED when the connection enters SUSPENDED state.

### Setup
```pseudo
channel_name = "test-RTL3c-attaching-${random_id()}"

enable_fake_timers()

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(ProtocolMessage(
    action: CONNECTED,
    connectionId: "connection-id",
    connectionKey: "connection-key",
    connectionDetails: ConnectionDetails(
      connectionKey: "connection-key",
      maxIdleInterval: 15000,
      connectionStateTtl: 120000
    )
  )),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Do NOT respond - leave channel in ATTACHING state
      pass
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  fallbackHosts: [],
  disconnectedRetryTimeout: 1000
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Start attach but don't await - server won't respond
attach_future = channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching

# Record channel state changes
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Simulate disconnect - all reconnection attempts will fail
mock_ws.onConnectionAttempt = (conn) => conn.respond_with_refused()
mock_ws.active_connection.simulate_disconnect()

# Connection must exhaust disconnectedRetryTimeout retries within connectionStateTtl
# to transition from DISCONNECTED to SUSPENDED. The total time advance must exceed
# connectionStateTtl (from connectionDetails, per RTN21).
LOOP up to 30 times:
  ADVANCE_TIME(5000)
  IF client.connection.state == ConnectionState.suspended:
    BREAK

AWAIT_STATE client.connection.state == ConnectionState.suspended
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.suspended

suspended_change = channel_state_changes.find(c => c.current == ChannelState.suspended)
ASSERT suspended_change IS NOT null
ASSERT suspended_change.previous == ChannelState.attaching
CLOSE_CLIENT(client)
```

---

## RTL3d, RTL4c1 - CONNECTED connection re-attaches ATTACHED channels with channelSerial

| Spec | Requirement |
|------|-------------|
| RTL3d | If the connection state enters the CONNECTED state, any channels in the ATTACHING, ATTACHED, or SUSPENDED states should be transitioned to ATTACHING and initiate an RTL4c attach sequence |
| RTL4c1 | The ATTACH ProtocolMessage channelSerial field must be set to the RTL15b channelSerial |

Tests that when a connection is re-established, previously attached channels are re-attached automatically, and that the re-attach ATTACH message includes the channel's stored channelSerial.

### Setup
```pseudo
channel_name = "test-RTL3d-attached-${random_id()}"
attach_messages = []

late mock_ws
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_messages.append(msg)
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel,
        channelSerial: "serial-001"
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  disconnectedRetryTimeout: 100
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()
ASSERT channel.state == ChannelState.attached
ASSERT length(attach_messages) == 1

# Record channel state changes
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Simulate disconnect
mock_ws.active_connection.simulate_disconnect()

# Wait for reconnection and re-attach
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT_STATE channel.state == ChannelState.attached
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached

# A second ATTACH message was sent for the re-attach
ASSERT length(attach_messages) == 2

# RTL4c1: The re-attach ATTACH message must include the channelSerial
# from the previous ATTACHED response
ASSERT attach_messages[1].channelSerial == "serial-001"

# Channel transitioned through ATTACHING during re-attach
ASSERT channel_state_changes CONTAINS_IN_ORDER [
  ChannelState.attaching,
  ChannelState.attached
]
CLOSE_CLIENT(client)
```

---

## RTL3d - CONNECTED connection re-attaches SUSPENDED channels

**Spec requirement:** If the connection state enters the CONNECTED state, any channels in the ATTACHING, ATTACHED, or SUSPENDED states should be transitioned to ATTACHING and initiate an RTL4c attach sequence.

Tests that suspended channels are re-attached when the connection is re-established.

### Setup
```pseudo
channel_name = "test-RTL3d-suspended-${random_id()}"
attach_message_count = 0

enable_fake_timers()

late mock_ws
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(ProtocolMessage(
    action: CONNECTED,
    connectionId: "connection-id",
    connectionKey: "connection-key",
    connectionDetails: ConnectionDetails(
      connectionKey: "connection-key",
      maxIdleInterval: 15000,
      connectionStateTtl: 120000
    )
  )),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_message_count++
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  fallbackHosts: [],
  disconnectedRetryTimeout: 1000,
  suspendedRetryTimeout: 2000
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach()
ASSERT channel.state == ChannelState.attached
ASSERT attach_message_count == 1

# Simulate disconnect - all reconnection attempts will fail
mock_ws.onConnectionAttempt = (conn) => conn.respond_with_refused()
mock_ws.active_connection.simulate_disconnect()

# Connection must exhaust disconnectedRetryTimeout retries within connectionStateTtl
# to transition from DISCONNECTED to SUSPENDED. The total time advance must exceed
# connectionStateTtl (from connectionDetails, per RTN21).
LOOP up to 30 times:
  ADVANCE_TIME(5000)
  IF client.connection.state == ConnectionState.suspended:
    BREAK

AWAIT_STATE client.connection.state == ConnectionState.suspended
ASSERT channel.state == ChannelState.suspended

# Record channel state changes from this point
channel_state_changes = []
channel.on().listen((change) => channel_state_changes.append(change))

# Allow reconnection to succeed
mock_ws.onConnectionAttempt = (conn) => conn.respond_with_success(CONNECTED_MESSAGE)

# Advance time past suspendedRetryTimeout to trigger retry
LOOP up to 10 times:
  ADVANCE_TIME(2500)
  IF client.connection.state == ConnectionState.connected:
    BREAK

AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT_STATE channel.state == ChannelState.attached
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached

# An ATTACH message was sent for the re-attach
ASSERT attach_message_count >= 2

# Channel transitioned from SUSPENDED through ATTACHING to ATTACHED
ASSERT channel_state_changes CONTAINS_IN_ORDER [
  ChannelState.attaching,
  ChannelState.attached
]
CLOSE_CLIENT(client)
```

---

## RTL3d - Channels in INITIALIZED or DETACHED are not re-attached on CONNECTED

**Spec requirement:** If the connection state enters the CONNECTED state, any channels in the ATTACHING, ATTACHED, or SUSPENDED states should be transitioned to ATTACHING.

Tests that channels in INITIALIZED or DETACHED states are not affected when the connection becomes CONNECTED.

### Setup
```pseudo
initialized_channel_name = "test-RTL3d-init-${random_id()}"
detached_channel_name = "test-RTL3d-detached-${random_id()}"
attach_messages = []

late mock_ws
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_messages.append(msg)
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel
      ))
    ELSE IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: msg.channel
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  disconnectedRetryTimeout: 100
))
initialized_channel = client.channels.get(initialized_channel_name)
detached_channel = client.channels.get(detached_channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Leave initialized_channel in INITIALIZED state
ASSERT initialized_channel.state == ChannelState.initialized

# Attach then detach to get to DETACHED state
AWAIT detached_channel.attach()
AWAIT detached_channel.detach()
ASSERT detached_channel.state == ChannelState.detached

attach_count_before = length(attach_messages)

# Record state changes
init_changes = []
detached_changes = []
initialized_channel.on().listen((change) => init_changes.append(change))
detached_channel.on().listen((change) => detached_changes.append(change))

# Simulate disconnect and reconnect
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions
```pseudo
# Neither channel should have been re-attached
ASSERT initialized_channel.state == ChannelState.initialized
ASSERT detached_channel.state == ChannelState.detached
ASSERT length(init_changes) == 0
ASSERT length(detached_changes) == 0

# No new ATTACH messages for these channels
attach_count_after = length(attach_messages)
new_attach_channels = [m.channel FOR m IN attach_messages[attach_count_before:]]
ASSERT initialized_channel_name NOT IN new_attach_channels
ASSERT detached_channel_name NOT IN new_attach_channels
CLOSE_CLIENT(client)
```

---

## RTL3d - Multiple channels re-attached on CONNECTED

**Spec requirement:** If the connection state enters the CONNECTED state, any channels in the ATTACHING, ATTACHED, or SUSPENDED states should be transitioned to ATTACHING and initiate an RTL4c attach sequence.

Tests that multiple channels in eligible states are all re-attached when the connection is restored.

### Setup
```pseudo
channel1_name = "test-RTL3d-multi1-${random_id()}"
channel2_name = "test-RTL3d-multi2-${random_id()}"
attach_messages = []

late mock_ws
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_messages.append(msg)
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  disconnectedRetryTimeout: 100
))
channel1 = client.channels.get(channel1_name)
channel2 = client.channels.get(channel2_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel1.attach()
AWAIT channel2.attach()
ASSERT channel1.state == ChannelState.attached
ASSERT channel2.state == ChannelState.attached

attach_count_before = length(attach_messages)

# Simulate disconnect and reconnect
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT_STATE channel1.state == ChannelState.attached
AWAIT_STATE channel2.state == ChannelState.attached
```

### Assertions
```pseudo
ASSERT channel1.state == ChannelState.attached
ASSERT channel2.state == ChannelState.attached

# Both channels should have received new ATTACH messages
new_attach_channels = [m.channel FOR m IN attach_messages[attach_count_before:]]
ASSERT channel1_name IN new_attach_channels
ASSERT channel2_name IN new_attach_channels
CLOSE_CLIENT(client)
```
