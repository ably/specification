# RealtimePresence Get Tests

Spec points: `RTP11`, `RTP11a`, `RTP11b`, `RTP11c`, `RTP11c1`, `RTP11c2`, `RTP11c3`, `RTP11d`

## Test Type
Unit test — mock WebSocket required.

## Purpose

Tests the `RealtimePresence#get` function which returns the list of current members
on the channel from the local PresenceMap. By default it waits for the SYNC to complete
before returning. It supports filtering by clientId and connectionId, and has specific
error behaviour for SUSPENDED channels.

---

## RTP11a - get returns current members (single-message sync)

**Spec requirement:** Returns the list of current members on the channel. By default,
will wait for the SYNC to be completed.

This test uses a single-message sync: the ATTACHED has HAS_PRESENCE, but the SYNC
message is not sent immediately. The get() call must wait until the sync arrives
and completes.

### Setup
```pseudo
channel_name = "test-RTP11a-single-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionId: "conn-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Send ATTACHED with HAS_PRESENCE but do NOT send SYNC yet
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: HAS_PRESENCE
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

# Start get() — sync has not arrived yet, so this must wait
get_future = channel.presence.get()

# Verify the get has not resolved yet (sync still pending)
ASSERT get_future IS NOT complete

# Now send a single-message SYNC (channelSerial with empty cursor = complete)
mock_ws.send_to_client(ProtocolMessage(
  action: SYNC,
  channel: channel_name,
  channelSerial: "seq1:",
  presence: [
    PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100, data: "a"),
    PresenceMessage(action: PRESENT, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100, data: "b")
  ]
))

members = AWAIT get_future
```

### Assertions
```pseudo
ASSERT members.length == 2
client_ids = members.map(m => m.clientId).sort()
ASSERT client_ids == ["alice", "bob"]
```

---

## RTP11a, RTP11c1 - get waits for multi-message sync

**Spec requirement:** When waitForSync is true (default), the method will wait until
SYNC is complete before returning a list of members. A multi-message sync has a
non-empty cursor in the first message and an empty cursor in the final message.

### Setup
```pseudo
channel_name = "test-RTP11c1-multi-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionId: "conn-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Send ATTACHED with HAS_PRESENCE but do NOT send SYNC yet
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: HAS_PRESENCE
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

# Start get() — sync has not arrived yet
get_future = channel.presence.get()

# Verify the get has not resolved yet
ASSERT get_future IS NOT complete

# Send first SYNC message (non-empty cursor = more to come)
mock_ws.send_to_client(ProtocolMessage(
  action: SYNC,
  channel: channel_name,
  channelSerial: "seq1:cursor1",
  presence: [
    PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100)
  ]
))

# get() should still be waiting — sync not complete
ASSERT get_future IS NOT complete

# Send final SYNC message (empty cursor = sync complete)
mock_ws.send_to_client(ProtocolMessage(
  action: SYNC,
  channel: channel_name,
  channelSerial: "seq1:",
  presence: [
    PresenceMessage(action: PRESENT, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100)
  ]
))

members = AWAIT get_future
```

### Assertions
```pseudo
# Both alice (from first SYNC message) and bob (from second) are present
ASSERT members.length == 2
client_ids = members.map(m => m.clientId).sort()
ASSERT client_ids == ["alice", "bob"]
```

---

## RTP11c1 - get with waitForSync=false returns immediately

**Spec requirement:** When waitForSync is false, the known set of presence members is
returned immediately, which may be incomplete if the SYNC is not finished.

### Setup
```pseudo
channel_name = "test-RTP11c1-nowait-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionId: "conn-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: HAS_PRESENCE
      ))
      # Start SYNC but don't complete it (cursor is non-empty)
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

# Sync is in progress but we don't wait
members = AWAIT channel.presence.get(waitForSync: false)
```

### Assertions
```pseudo
# Returns what's available so far (may be incomplete)
ASSERT members.length == 1
ASSERT members[0].clientId == "alice"
```

---

## RTP11c2 - get filtered by clientId

**Spec requirement:** clientId param filters members by the provided clientId.

### Setup
```pseudo
channel_name = "test-RTP11c2-${random_id()}"

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
          PresenceMessage(action: PRESENT, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100),
          PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c3", id: "c3:0:0", timestamp: 100)
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

members = AWAIT channel.presence.get(clientId: "alice")
```

### Assertions
```pseudo
# Only alice entries returned (from two different connections)
ASSERT members.length == 2
ASSERT members.every(m => m.clientId == "alice")
```

---

## RTP11c3 - get filtered by connectionId

**Spec requirement:** connectionId param filters members by the provided connectionId.

### Setup
```pseudo
channel_name = "test-RTP11c3-${random_id()}"

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
          PresenceMessage(action: PRESENT, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100),
          PresenceMessage(action: PRESENT, clientId: "carol", connectionId: "c1", id: "c1:0:1", timestamp: 100)
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

members = AWAIT channel.presence.get(connectionId: "c1")
```

### Assertions
```pseudo
# Only members from connection c1 (alice and carol)
ASSERT members.length == 2
ASSERT members.every(m => m.connectionId == "c1")
```

---

## RTP11b - get implicitly attaches channel

**Spec requirement:** Implicitly attaches the RealtimeChannel if the channel is in the
INITIALIZED state. If the channel enters DETACHED or FAILED before the operation
succeeds, error.

### Setup
```pseudo
channel_name = "test-RTP11b-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
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

ASSERT channel.state == ChannelState.initialized

members = AWAIT channel.presence.get(waitForSync: false)
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT members IS NOT null
```

---

## RTP11d - get on SUSPENDED channel errors by default

**Spec requirement:** If the RealtimeChannel is SUSPENDED, get will by default (or if
waitForSync is true) result in an error with code 91005. If waitForSync is false,
it returns the members currently stored in the PresenceMap.

### Setup
```pseudo
channel_name = "test-RTP11d-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: HAS_PRESENCE
      ))
      # Deliver a member via SYNC
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

# Simulate channel becoming SUSPENDED (e.g., connection drops)
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE channel.state == ChannelState.suspended

# Default get (waitForSync=true) should error
AWAIT channel.presence.get() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
ASSERT error.code == 91005
```

---

## RTP11d - get on SUSPENDED channel with waitForSync=false returns members

**Spec requirement:** If waitForSync is false on a SUSPENDED channel, return the
members currently in the PresenceMap.

### Setup
```pseudo
channel_name = "test-RTP11d-nowait-${random_id()}"

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

# Simulate channel becoming SUSPENDED
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE channel.state == ChannelState.suspended

# waitForSync=false returns what's in the PresenceMap
members = AWAIT channel.presence.get(waitForSync: false)
```

### Assertions
```pseudo
ASSERT members.length == 1
ASSERT members[0].clientId == "alice"
```
