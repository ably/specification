# RealtimePresence Channel State Tests

Spec points: `RTL9`, `RTL9a`, `RTL11`, `RTL11a`, `RTP1`, `RTP5`, `RTP5a`, `RTP5b`, `RTP5f`, `RTP13`

## Test Type
Unit test — mock WebSocket required.

## Purpose

Tests the interaction between channel state transitions and presence. Covers the
HAS_PRESENCE flag triggering a sync, channel state side effects on presence maps,
the syncComplete attribute, the RealtimeChannel#presence attribute (RTL9), and
channel state effects on queued presence actions (RTL11).

---

## RTP1 - HAS_PRESENCE flag triggers sync

**Spec requirement:** When a channel ATTACHED ProtocolMessage is received with the
HAS_PRESENCE flag set, the server will perform a SYNC operation. If the flag is 0
or absent, the presence map should be considered in sync immediately with no members.

### Setup
```pseudo
channel_name = "test-RTP1-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: HAS_PRESENCE
      ))
      # Server follows up with SYNC
      mock_ws.send_to_client(ProtocolMessage(
        action: SYNC,
        channel: channel_name,
        channelSerial: "seq1:",
        presence: [
          PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100)
        ]
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Wait for sync to complete
members = AWAIT channel.presence.get()
```

### Assertions
```pseudo
ASSERT members.length == 1
ASSERT members[0].clientId == "alice"
ASSERT channel.presence.syncComplete == true
```

---

## RTP1 - No HAS_PRESENCE flag means empty presence

**Spec requirement:** If the flag is 0 or absent, the presence map should be considered
in sync immediately with no members present on the channel.

### Setup
```pseudo
channel_name = "test-RTP1-empty-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # No HAS_PRESENCE flag
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

members = AWAIT channel.presence.get()
```

### Assertions
```pseudo
ASSERT members.length == 0
ASSERT channel.presence.syncComplete == true  # Immediately in sync
```

---

## RTP1, RTP19a - No HAS_PRESENCE clears existing members

**Spec requirement (RTP19a):** If the PresenceMap has existing members when an ATTACHED
message is received without a HAS_PRESENCE flag, emit a LEAVE event for each existing
member and remove all members from the PresenceMap.

### Setup
```pseudo
channel_name = "test-RTP19a-${random_id()}"

connection_count = 0
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_count++
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "conn-${connection_count}"
    ))
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      IF connection_count == 1:
        # First attach: has presence
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: channel_name,
          flags: HAS_PRESENCE
        ))
        mock_ws.send_to_client(ProtocolMessage(
          action: SYNC,
          channel: channel_name,
          channelSerial: "seq1:",
          presence: [
            PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100),
            PresenceMessage(action: PRESENT, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100)
          ]
        ))
      ELSE:
        # Second attach: no HAS_PRESENCE
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: channel_name
        ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Verify members exist after first sync
members = AWAIT channel.presence.get()
ASSERT members.length == 2

# Track LEAVE events
leave_events = []
channel.presence.subscribe(action: LEAVE, (event) => {
  leave_events.append(event)
})

# Simulate disconnect and reconnect
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Reconnect — this time ATTACHED without HAS_PRESENCE
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT_STATE channel.state == ChannelState.attached

members_after = AWAIT channel.presence.get()
```

### Assertions
```pseudo
# All members removed
ASSERT members_after.length == 0

# LEAVE events emitted for each member
ASSERT leave_events.length == 2
ASSERT leave_events.any(e => e.clientId == "alice")
ASSERT leave_events.any(e => e.clientId == "bob")

# LEAVE events have id=null per RTP19a
ASSERT leave_events.every(e => e.id IS null)
```

---

## RTP5a - DETACHED clears both presence maps

**Spec requirement:** If the channel enters the DETACHED state, all queued presence
messages fail immediately, and both the PresenceMap and internal PresenceMap (RTP17)
are cleared. LEAVE events should NOT be emitted when clearing.

### Setup
```pseudo
channel_name = "test-RTP5a-detached-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: HAS_PRESENCE
      ))
      mock_ws.send_to_client(ProtocolMessage(
        action: SYNC,
        channel: channel_name,
        channelSerial: "seq1:",
        presence: [
          PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100)
        ]
      ))
    ELSE IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(action: DETACHED, channel: channel_name))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Verify member exists
members = AWAIT channel.presence.get()
ASSERT members.length == 1

# Track events — LEAVE should NOT be emitted on clear
leave_events = []
channel.presence.subscribe(action: LEAVE, (event) => {
  leave_events.append(event)
})

# Detach the channel
AWAIT channel.detach()
ASSERT channel.state == ChannelState.detached
```

### Assertions
```pseudo
# RTP5a: No LEAVE events emitted when clearing on DETACHED
ASSERT leave_events.length == 0

# Presence map is cleared
members_after = channel.presence.get(waitForSync: false)
ASSERT members_after.length == 0
```

---

## RTP5a - FAILED clears both presence maps

**Spec requirement:** Same as DETACHED — FAILED state clears both maps, no LEAVE emitted.

### Setup
```pseudo
channel_name = "test-RTP5a-failed-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: HAS_PRESENCE
      ))
      mock_ws.send_to_client(ProtocolMessage(
        action: SYNC,
        channel: channel_name,
        channelSerial: "seq1:",
        presence: [
          PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100)
        ]
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

members = AWAIT channel.presence.get()
ASSERT members.length == 1

leave_events = []
channel.presence.subscribe(action: LEAVE, (event) => {
  leave_events.append(event)
})

# Server sends channel ERROR to put channel in FAILED state
mock_ws.send_to_client(ProtocolMessage(
  action: ERROR,
  channel: channel_name,
  error: ErrorInfo(code: 90001, message: "Channel failed")
))

AWAIT_STATE channel.state == ChannelState.failed
```

### Assertions
```pseudo
# RTP5a: No LEAVE events emitted
ASSERT leave_events.length == 0
```

---

## RTP5b - ATTACHED sends queued presence messages

**Spec requirement:** If a channel enters the ATTACHED state then all queued presence
messages will be sent immediately.

### Setup
```pseudo
channel_name = "test-RTP5b-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Delay attach response
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "my-client", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Start attach — channel goes to ATTACHING
channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching

# Queue presence while channel is ATTACHING
enter_future = channel.presence.enter(data: "queued")

# No presence sent yet
ASSERT captured_presence.length == 0

# Complete the attach
mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))

AWAIT enter_future
```

### Assertions
```pseudo
# Queued presence was sent after attach completed
ASSERT captured_presence.length == 1
ASSERT captured_presence[0].presence[0].action == ENTER
ASSERT captured_presence[0].presence[0].data == "queued"
```

---

## RTP5f - SUSPENDED maintains presence map

**Spec requirement:** If the channel enters SUSPENDED, all queued presence messages fail
immediately, but the PresenceMap is maintained. This ensures that when the channel later
becomes ATTACHED, it will only emit presence events for changes that occurred while
disconnected.

### Setup
```pseudo
channel_name = "test-RTP5f-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: HAS_PRESENCE
      ))
      mock_ws.send_to_client(ProtocolMessage(
        action: SYNC,
        channel: channel_name,
        channelSerial: "seq1:",
        presence: [
          PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100),
          PresenceMessage(action: PRESENT, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100)
        ]
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

members = AWAIT channel.presence.get()
ASSERT members.length == 2

# Channel becomes SUSPENDED (e.g., connection transitions to SUSPENDED)
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE channel.state == ChannelState.suspended

# PresenceMap is maintained during SUSPENDED
members_during_suspended = channel.presence.get(waitForSync: false)
```

### Assertions
```pseudo
# Members still exist in the map
ASSERT members_during_suspended.length == 2
```

---

## RTP13 - syncComplete attribute

**Spec requirement:** RealtimePresence#syncComplete is true if the initial SYNC
operation has completed for the members present on the channel.

### Setup
```pseudo
channel_name = "test-RTP13-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: HAS_PRESENCE
      ))
      # Start multi-message SYNC (cursor is non-empty)
      mock_ws.send_to_client(ProtocolMessage(
        action: SYNC,
        channel: channel_name,
        channelSerial: "seq1:cursor1",
        presence: [
          PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100)
        ]
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Sync is in progress — not yet complete
ASSERT channel.presence.syncComplete == false

# Complete the sync (empty cursor)
mock_ws.send_to_client(ProtocolMessage(
  action: SYNC,
  channel: channel_name,
  channelSerial: "seq1:",
  presence: [
    PresenceMessage(action: PRESENT, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100)
  ]
))
```

### Assertions
```pseudo
ASSERT channel.presence.syncComplete == true
```

---

## RTL9, RTL9a - RealtimeChannel#presence attribute

**Spec requirement (RTL9):** `RealtimeChannel#presence` attribute.
**Spec requirement (RTL9a):** Returns the `RealtimePresence` object for this channel.

### Setup
```pseudo
channel_name = "test-RTL9a-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {}
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
presence = channel.presence
```

### Assertions
```pseudo
ASSERT presence IS RealtimePresence
ASSERT presence IS NOT null
```

### RTL9a - Same presence object returned for same channel

```pseudo
ASSERT channel.presence === channel.presence  # identity check — same instance
```

---

## RTL11 - Queued presence actions fail on DETACHED

**Spec requirement (RTL11):** If a channel enters the DETACHED, SUSPENDED or FAILED
state, then all presence actions that are still queued for send on that channel per
RTP16b should be deleted from the queue, and any callback passed to the corresponding
presence method invocation should be called with an ErrorInfo indicating the failure.

### Setup
```pseudo
channel_name = "test-RTL11-detached-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Do NOT respond — leave channel in ATTACHING so presence queues
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "my-client", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Start attach — channel goes to ATTACHING
channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching

# Queue presence while channel is ATTACHING (per RTP16b)
enter_future = channel.presence.enter(data: "queued-enter")

# Verify nothing sent yet
ASSERT captured_presence.length == 0

# Server sends DETACHED — channel transitions to DETACHED
mock_ws.send_to_client(ProtocolMessage(
  action: DETACHED,
  channel: channel_name,
  error: ErrorInfo(code: 90001, message: "Channel detached")
))

AWAIT_STATE channel.state == ChannelState.detached
```

### Assertions
```pseudo
# Queued presence was NOT sent
ASSERT captured_presence.length == 0

# The enter future completed with an error
AWAIT enter_future FAILS WITH error
ASSERT error IS ErrorInfo
ASSERT error.code IS NOT null
```

---

## RTL11 - Queued presence actions fail on SUSPENDED

### Setup
```pseudo
channel_name = "test-RTL11-suspended-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Do NOT respond — leave channel in ATTACHING
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "my-client", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching

# Queue multiple presence actions
enter_future = channel.presence.enter(data: "queued-enter")
update_future = channel.presence.update(data: "queued-update")

ASSERT captured_presence.length == 0

# Connection goes SUSPENDED, causing channel to go SUSPENDED
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE channel.state == ChannelState.suspended
```

### Assertions
```pseudo
# No presence messages were sent
ASSERT captured_presence.length == 0

# Both queued futures completed with errors
AWAIT enter_future FAILS WITH enter_error
ASSERT enter_error IS ErrorInfo

AWAIT update_future FAILS WITH update_error
ASSERT update_error IS ErrorInfo
```

---

## RTL11 - Queued presence actions fail on FAILED

### Setup
```pseudo
channel_name = "test-RTL11-failed-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Do NOT respond — leave channel in ATTACHING
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "my-client", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching

# Queue presence
enter_future = channel.presence.enter(data: "queued-enter")

ASSERT captured_presence.length == 0

# Server sends ERROR for this channel — channel goes FAILED
mock_ws.send_to_client(ProtocolMessage(
  action: ERROR,
  channel: channel_name,
  error: ErrorInfo(code: 90001, message: "Channel failed")
))

AWAIT_STATE channel.state == ChannelState.failed
```

### Assertions
```pseudo
# No presence messages were sent
ASSERT captured_presence.length == 0

# Queued future completed with an error
AWAIT enter_future FAILS WITH error
ASSERT error IS ErrorInfo
```

---

## RTL11a - ACK/NACK unaffected by channel state changes

**Spec requirement (RTL11a):** For clarity, any messages awaiting an ACK or NACK are
unaffected by channel state changes i.e. a channel that becomes detached following an
explicit request to detach may still receive an ACK or NACK for messages published on
that channel later.

### Setup
```pseudo
channel_name = "test-RTL11a-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      # Do NOT send ACK yet — hold it
    ELSE IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(action: DETACHED, channel: channel_name))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "my-client", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Send presence — it goes to the server, but no ACK yet
enter_future = channel.presence.enter(data: "awaiting-ack")
ASSERT captured_presence.length == 1

# Detach the channel
channel.detach()
AWAIT_STATE channel.state == ChannelState.detached

# Now the server sends the ACK for the presence message that was already sent
mock_ws.send_to_client(ProtocolMessage(
  action: ACK,
  msgSerial: captured_presence[0].msgSerial,
  count: 1
))
```

### Assertions
```pseudo
# The enter future resolves successfully — ACK was processed despite channel being DETACHED
AWAIT enter_future  # should complete without error
```
