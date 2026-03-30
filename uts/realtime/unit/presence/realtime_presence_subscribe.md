# RealtimePresence Subscribe/Unsubscribe Tests

Spec points: `RTP6`, `RTP6a`, `RTP6b`, `RTP6d`, `RTP6e`, `RTP7`, `RTP7a`, `RTP7b`, `RTP7c`

## Test Type
Unit test — mock WebSocket required.

## Purpose

Tests the `RealtimePresence#subscribe` and `RealtimePresence#unsubscribe` functions.
Subscribe registers listeners for incoming presence events (ENTER, LEAVE, UPDATE, PRESENT).
Unsubscribe removes previously registered listeners. Subscribe may implicitly attach the
channel depending on the `attachOnSubscribe` channel option.

---

## RTP6a - Subscribe to all presence events

**Spec requirement:** Subscribe with a single listener argument subscribes a listener to
all presence messages.

### Setup
```pseudo
channel_name = "test-RTP6a-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
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

received_events = []
channel.presence.subscribe((event) => {
  received_events.append(event)
})

AWAIT_STATE channel.state == ChannelState.attached

# Server delivers ENTER, UPDATE, and LEAVE events
mock_ws.send_to_client(ProtocolMessage(
  action: PRESENCE,
  channel: channel_name,
  presence: [
    PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 1000)
  ]
))

mock_ws.send_to_client(ProtocolMessage(
  action: PRESENCE,
  channel: channel_name,
  presence: [
    PresenceMessage(action: UPDATE, clientId: "alice", connectionId: "c1", id: "c1:1:0", timestamp: 2000, data: "updated")
  ]
))

mock_ws.send_to_client(ProtocolMessage(
  action: PRESENCE,
  channel: channel_name,
  presence: [
    PresenceMessage(action: LEAVE, clientId: "alice", connectionId: "c1", id: "c1:2:0", timestamp: 3000)
  ]
))
```

### Assertions
```pseudo
ASSERT received_events.length == 3
ASSERT received_events[0].action == ENTER
ASSERT received_events[0].clientId == "alice"
ASSERT received_events[1].action == UPDATE
ASSERT received_events[1].data == "updated"
ASSERT received_events[2].action == LEAVE
```

---

## RTP6b - Subscribe filtered by action

**Spec requirement:** Subscribe with an action argument and a listener subscribes the
listener to receive only presence messages with that action.

### Setup
```pseudo
channel_name = "test-RTP6b-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
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

enter_events = []
leave_events = []

channel.presence.subscribe(action: ENTER, (event) => {
  enter_events.append(event)
})

channel.presence.subscribe(action: LEAVE, (event) => {
  leave_events.append(event)
})

# Server delivers all three action types
mock_ws.send_to_client(ProtocolMessage(
  action: PRESENCE,
  channel: channel_name,
  presence: [
    PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 1000),
    PresenceMessage(action: UPDATE, clientId: "alice", connectionId: "c1", id: "c1:1:0", timestamp: 2000),
    PresenceMessage(action: LEAVE, clientId: "alice", connectionId: "c1", id: "c1:2:0", timestamp: 3000)
  ]
))
```

### Assertions
```pseudo
# ENTER listener only gets ENTER events
ASSERT enter_events.length == 1
ASSERT enter_events[0].action == ENTER

# LEAVE listener only gets LEAVE events
ASSERT leave_events.length == 1
ASSERT leave_events[0].action == LEAVE

# Neither listener receives UPDATE
```

---

## RTP6b - Subscribe filtered by multiple actions

**Spec requirement:** The action argument may also be an array of actions.

### Setup
```pseudo
channel_name = "test-RTP6b-multi-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
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

enter_leave_events = []
channel.presence.subscribe(actions: [ENTER, LEAVE], (event) => {
  enter_leave_events.append(event)
})

mock_ws.send_to_client(ProtocolMessage(
  action: PRESENCE,
  channel: channel_name,
  presence: [
    PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 1000),
    PresenceMessage(action: UPDATE, clientId: "alice", connectionId: "c1", id: "c1:1:0", timestamp: 2000),
    PresenceMessage(action: LEAVE, clientId: "alice", connectionId: "c1", id: "c1:2:0", timestamp: 3000)
  ]
))
```

### Assertions
```pseudo
# Only ENTER and LEAVE events received — UPDATE filtered out
ASSERT enter_leave_events.length == 2
ASSERT enter_leave_events[0].action == ENTER
ASSERT enter_leave_events[1].action == LEAVE
```

---

## RTP6d - Subscribe implicitly attaches channel

**Spec requirement:** If the `attachOnSubscribe` channel option is true (default),
implicitly attach the RealtimeChannel if the channel is in the INITIALIZED, DETACHING,
or DETACHED states.

### Setup
```pseudo
channel_name = "test-RTP6d-${random_id()}"

attach_count = 0
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
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

# Subscribe without explicitly attaching — should trigger implicit attach
channel.presence.subscribe((event) => {})

AWAIT_STATE channel.state == ChannelState.attached
```

### Assertions
```pseudo
ASSERT attach_count == 1
ASSERT channel.state == ChannelState.attached
```

---

## RTP6e - Subscribe with attachOnSubscribe=false does not attach

**Spec requirement:** If the `attachOnSubscribe` channel option is false, do not
implicitly attach.

### Setup
```pseudo
channel_name = "test-RTP6e-${random_id()}"

attach_count = 0
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", autoConnect: false))
channel = client.channels.get(channel_name, options: ChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

ASSERT channel.state == ChannelState.initialized

channel.presence.subscribe((event) => {})
```

### Assertions
```pseudo
# Channel stays in INITIALIZED — no implicit attach
ASSERT channel.state == ChannelState.initialized
ASSERT attach_count == 0
```

---

## RTP7c - Unsubscribe all listeners

**Spec requirement:** Unsubscribe with no arguments unsubscribes all listeners.

### Setup
```pseudo
channel_name = "test-RTP7c-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
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

events_a = []
events_b = []

channel.presence.subscribe((event) => { events_a.append(event) })
channel.presence.subscribe((event) => { events_b.append(event) })

# Deliver first event — both listeners receive it
mock_ws.send_to_client(ProtocolMessage(
  action: PRESENCE,
  channel: channel_name,
  presence: [
    PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 1000)
  ]
))

ASSERT events_a.length == 1
ASSERT events_b.length == 1

# Unsubscribe all
channel.presence.unsubscribe()

# Deliver second event — no listeners receive it
mock_ws.send_to_client(ProtocolMessage(
  action: PRESENCE,
  channel: channel_name,
  presence: [
    PresenceMessage(action: ENTER, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 2000)
  ]
))
```

### Assertions
```pseudo
ASSERT events_a.length == 1  # No new events after unsubscribe
ASSERT events_b.length == 1
```

---

## RTP7a - Unsubscribe specific listener

**Spec requirement:** Unsubscribe with a single listener argument unsubscribes that
specific listener.

### Setup
```pseudo
channel_name = "test-RTP7a-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
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

events_a = []
events_b = []

listener_a = (event) => { events_a.append(event) }
listener_b = (event) => { events_b.append(event) }

channel.presence.subscribe(listener_a)
channel.presence.subscribe(listener_b)

# Unsubscribe only listener_a
channel.presence.unsubscribe(listener_a)

mock_ws.send_to_client(ProtocolMessage(
  action: PRESENCE,
  channel: channel_name,
  presence: [
    PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 1000)
  ]
))
```

### Assertions
```pseudo
ASSERT events_a.length == 0  # Unsubscribed — no events
ASSERT events_b.length == 1  # Still subscribed — receives event
```

---

## RTP7b - Unsubscribe listener for specific action

**Spec requirement:** Unsubscribe with an action argument and a listener unsubscribes
the listener for that action only.

### Setup
```pseudo
channel_name = "test-RTP7b-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
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

received = []
listener = (event) => { received.append(event) }

# Subscribe to both ENTER and LEAVE
channel.presence.subscribe(action: ENTER, listener)
channel.presence.subscribe(action: LEAVE, listener)

# Unsubscribe only for ENTER
channel.presence.unsubscribe(action: ENTER, listener)

mock_ws.send_to_client(ProtocolMessage(
  action: PRESENCE,
  channel: channel_name,
  presence: [
    PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 1000),
    PresenceMessage(action: LEAVE, clientId: "alice", connectionId: "c1", id: "c1:1:0", timestamp: 2000)
  ]
))
```

### Assertions
```pseudo
# Only LEAVE received — ENTER subscription was removed
ASSERT received.length == 1
ASSERT received[0].action == LEAVE
```

---

## RTP6 - Presence events update the PresenceMap

**Spec requirement:** Incoming presence messages are applied to the PresenceMap (RTP2)
before being emitted to subscribers.

### Setup
```pseudo
channel_name = "test-RTP6-map-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
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

channel.presence.subscribe((event) => {})

# Server delivers ENTER
mock_ws.send_to_client(ProtocolMessage(
  action: PRESENCE,
  channel: channel_name,
  presence: [
    PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 1000, data: "hello")
  ]
))

members = channel.presence.get(waitForSync: false)
```

### Assertions
```pseudo
ASSERT members.length == 1
ASSERT members[0].clientId == "alice"
ASSERT members[0].data == "hello"
ASSERT members[0].action == PRESENT  # Stored as PRESENT per RTP2d2
```

---

## RTP6 - Multiple presence messages in single ProtocolMessage

**Spec requirement:** A PRESENCE ProtocolMessage may contain multiple PresenceMessages.

### Setup
```pseudo
channel_name = "test-RTP6-batch-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
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

received = []
channel.presence.subscribe((event) => { received.append(event) })

# Server delivers multiple presence events in one ProtocolMessage
mock_ws.send_to_client(ProtocolMessage(
  action: PRESENCE,
  channel: channel_name,
  presence: [
    PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 1000),
    PresenceMessage(action: ENTER, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 1000),
    PresenceMessage(action: ENTER, clientId: "carol", connectionId: "c3", id: "c3:0:0", timestamp: 1000)
  ]
))
```

### Assertions
```pseudo
ASSERT received.length == 3
ASSERT received[0].clientId == "alice"
ASSERT received[1].clientId == "bob"
ASSERT received[2].clientId == "carol"
```
