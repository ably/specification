# RealtimeChannel State and Events Tests

Spec points: `RTL2`, `RTL2a`, `RTL2b`, `RTL2d`, `RTL2g`, `RTL2i`, `TH1`, `TH2`, `TH3`, `TH5`, `TH6`

## Test Type
Unit test with mocked WebSocket

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTL2b - Channel state attribute

**Spec requirement:** `RealtimeChannel#state` attribute is the current state of the channel, of type `ChannelState`.

Tests that channel has a state attribute of type ChannelState.

### Setup
```pseudo
channel_name = "test-RTL2b-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Assertions
```pseudo
ASSERT channel.state IS ChannelState
ASSERT channel.state == ChannelState.initialized
CLOSE_CLIENT(client)
```

---

## RTL2b - Channel initial state is initialized

**Spec requirement:** Channel state attribute reflects the current state.

Tests that a newly created channel starts in the initialized state.

### Setup
```pseudo
channel_name = "test-RTL2b-init-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
```

### Test Steps
```pseudo
channel = client.channels.get(channel_name)
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.initialized
CLOSE_CLIENT(client)
```

---

## RTL2a - State change events emitted for every state change

**Spec requirement:** It emits a `ChannelState` `ChannelEvent` for every channel state change.

Tests that state changes emit corresponding events.

### Setup
```pseudo
channel_name = "test-RTL2a-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE)
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)

state_changes = []
channel.on().listen((change) => state_changes.append(change))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Trigger attach - should emit attaching then attached
mock_ws.onMessageFromClient = (msg) => {
  IF msg.action == ATTACH:
    mock_ws.send_to_client(ProtocolMessage(
      action: ATTACHED,
      channel: channel_name
    ))
}

AWAIT channel.attach()
```

### Assertions
```pseudo
# Should have emitted attaching and attached state changes
ASSERT length(state_changes) >= 2
ASSERT state_changes[0].current == ChannelState.attaching
ASSERT state_changes[0].previous == ChannelState.initialized
ASSERT state_changes[1].current == ChannelState.attached
ASSERT state_changes[1].previous == ChannelState.attaching
CLOSE_CLIENT(client)
```

---

## RTL2d, TH1, TH2, TH5 - ChannelStateChange object structure

| Spec | Requirement |
|------|-------------|
| RTL2d | A ChannelStateChange object is emitted as the first argument for every ChannelEvent |
| TH1 | Whenever the channel state changes, a ChannelStateChange object is emitted |
| TH2 | Contains current state and previous state attributes |
| TH5 | Contains the event that generated the state change |

Tests the structure of ChannelStateChange objects.

### Setup
```pseudo
channel_name = "test-RTL2d-${random_id()}"

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

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)

captured_change = null
channel.on().listen((change) => {
  IF change.current == ChannelState.attaching:
    captured_change = change
})
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT captured_change IS NOT null
ASSERT captured_change IS ChannelStateChange
ASSERT captured_change.current == ChannelState.attaching
ASSERT captured_change.previous == ChannelState.initialized
ASSERT captured_change.event == ChannelEvent.attaching
CLOSE_CLIENT(client)
```

---

## RTL2d, TH3 - ChannelStateChange includes error reason when applicable

**Spec requirement:** Any state change triggered by a ProtocolMessage that contains an error member should populate the reason with that error.

Tests that error information is included in state change when present.

### Setup
```pseudo
channel_name = "test-RTL2d-error-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Server rejects attachment with error
      mock_ws.send_to_client(ProtocolMessage(
        action: ERROR,
        channel: channel_name,
        error: ErrorInfo(
          code: 40160,
          statusCode: 401,
          message: "Channel denied"
        )
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)

captured_change = null
channel.on(ChannelEvent.failed).listen((change) => {
  captured_change = change
})
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

AWAIT channel.attach() FAILS WITH error
```

### Assertions
```pseudo
ASSERT captured_change IS NOT null
ASSERT captured_change.current == ChannelState.failed
ASSERT captured_change.reason IS NOT null
ASSERT captured_change.reason.code == 40160
ASSERT captured_change.reason.message == "Channel denied"
CLOSE_CLIENT(client)
```

---

## RTL2 - Filtered event subscription

**Spec requirement:** RealtimeChannel implements EventEmitter and emits ChannelEvent events.

Tests that subscribing to a specific event only receives that event.

### Setup
```pseudo
channel_name = "test-RTL2-filtered-${random_id()}"

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

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)

attached_events = []
channel.on(ChannelEvent.attached).listen((change) => attached_events.append(change))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()
```

### Assertions
```pseudo
# Should only receive attached event, not attaching
ASSERT length(attached_events) == 1
ASSERT attached_events[0].current == ChannelState.attached
ASSERT attached_events[0].event == ChannelEvent.attached
CLOSE_CLIENT(client)
```

---

## RTL2g - UPDATE event for condition changes without state change

**Spec requirement:** It emits an UPDATE ChannelEvent for changes to channel
conditions for which the ChannelState does not change, unless explicitly
prevented by a more specific condition (see RTL12).

Tests that UPDATE events are emitted when channel conditions change without
state change. Per RTL12, the additional ATTACHED must NOT have the RESUMED flag
set (resumed=true suppresses the UPDATE event).

### Setup
```pseudo
channel_name = "test-RTL2g-${random_id()}"

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

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)

update_events = []
channel.on(ChannelEvent.update).listen((change) => update_events.append(change))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Server sends another ATTACHED message without RESUMED flag
# (e.g., loss of message continuity after transport resume)
# Per RTL12, this should trigger UPDATE because resumed=false
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: channel_name
  # No RESUMED flag — indicates loss of continuity
))

# Wait for the event to be processed
AWAIT Future.delayed(Duration.zero)
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached  # State unchanged
ASSERT length(update_events) == 1
ASSERT update_events[0].event == ChannelEvent.update
ASSERT update_events[0].current == ChannelState.attached
ASSERT update_events[0].previous == ChannelState.attached
ASSERT update_events[0].resumed == false
CLOSE_CLIENT(client)
```

---

## RTL2g - No duplicate state events

**Spec requirement:** The library must never emit a ChannelState ChannelEvent for a state equal to the previous state.

Tests that state events are not emitted when state doesn't actually change.

### Setup
```pseudo
channel_name = "test-RTL2g-nodup-${random_id()}"

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

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)

all_events = []
channel.on().listen((change) => all_events.append(change))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

initial_count = length(all_events)

# Server sends another ATTACHED message (no RESUMED flag)
# Per RTL12, this triggers UPDATE (not a duplicate state event)
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: channel_name
))

AWAIT Future.delayed(Duration.zero)
```

### Assertions
```pseudo
# Should have received UPDATE event, not another ATTACHED state event
# Count all events where current == attached AND event == attached (state event)
attached_state_events = filter(all_events, (e) => 
  e.current == ChannelState.attached AND e.event == ChannelEvent.attached
)
ASSERT length(attached_state_events) == 1  # Only the original attach
CLOSE_CLIENT(client)
```

---

## RTL2i, TH6 - hasBacklog flag in ChannelStateChange

| Spec | Requirement |
|------|-------------|
| RTL2i | ChannelStateChange may expose hasBacklog property |
| TH6 | hasBacklog indicates whether channel should expect backlog from resume/rewind |

Tests that hasBacklog is set when ATTACHED message contains HAS_BACKLOG flag.

### Setup
```pseudo
channel_name = "test-RTL2i-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: HAS_BACKLOG
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)

captured_change = null
channel.on(ChannelEvent.attached).listen((change) => {
  captured_change = change
})
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT captured_change IS NOT null
ASSERT captured_change.hasBacklog == true
CLOSE_CLIENT(client)
```

---

## RTL2i - hasBacklog false when flag not present

**Spec requirement:** hasBacklog should only be true when ATTACHED message contains HAS_BACKLOG flag.

Tests that hasBacklog is false when the flag is not present.

### Setup
```pseudo
channel_name = "test-RTL2i-false-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
        # No HAS_BACKLOG flag
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)

captured_change = null
channel.on(ChannelEvent.attached).listen((change) => {
  captured_change = change
})
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT captured_change IS NOT null
ASSERT captured_change.hasBacklog == false OR captured_change.hasBacklog IS null
CLOSE_CLIENT(client)
```

---

## RTL2d - resumed flag in ChannelStateChange

**Spec requirement:** ChannelStateChange has a resumed property indicating whether the ATTACHED message had the RESUMED flag set.

Tests that resumed flag is correctly propagated.

### Setup
```pseudo
channel_name = "test-RTL2d-resumed-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: RESUMED
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)

captured_change = null
channel.on(ChannelEvent.attached).listen((change) => {
  captured_change = change
})
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT captured_change IS NOT null
ASSERT captured_change.resumed == true
CLOSE_CLIENT(client)
```

---

## Channel errorReason attribute

**Spec requirement:** Channel should expose error information when in failed state.

Tests that errorReason is populated when channel enters failed state.

### Setup
```pseudo
channel_name = "test-errorReason-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ERROR,
        channel: channel_name,
        error: ErrorInfo(
          code: 40160,
          statusCode: 401,
          message: "Not authorized"
        )
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

AWAIT channel.attach() FAILS WITH error
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.failed
ASSERT channel.errorReason IS NOT null
ASSERT channel.errorReason.code == 40160
ASSERT channel.errorReason.message == "Not authorized"
CLOSE_CLIENT(client)
```

---

## Channel errorReason cleared on successful attach

**Spec requirement:** Error reason should be cleared when channel successfully attaches.

Tests that errorReason is cleared after successful attach following a failure.

### Setup
```pseudo
channel_name = "test-errorReason-clear-${random_id()}"
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

# Second attach succeeds
AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT channel.errorReason IS null
CLOSE_CLIENT(client)
```
