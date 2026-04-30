# Additional ATTACHED Message Handling Tests

Spec points: `RTL12`

## Test Type
Unit test with mocked WebSocket

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTL12 - Additional ATTACHED with resumed=false emits UPDATE with error

**Spec requirement:** An attached channel may receive an additional `ATTACHED`
`ProtocolMessage` from Ably at any point. If and only if the `resumed` flag is
false, this should result in the channel emitting an `UPDATE` event with a
`ChannelStateChange` object. The `ChannelStateChange` object should have both
`previous` and `current` attributes set to `attached`, the `reason` attribute
set to the `error` member of the `ATTACHED` `ProtocolMessage` (if any), and the
`resumed` attribute set per the `RESUMED` bitflag of the `ATTACHED`
`ProtocolMessage`.

Tests that an additional ATTACHED message without the RESUMED flag emits an
UPDATE event with the correct attributes including the error reason.

### Setup
```pseudo
channel_name = "test-RTL12-update-${random_id()}"

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
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

update_events = []
channel.on(ChannelEvent.update).listen((change) => update_events.append(change))

# Server sends additional ATTACHED without RESUMED flag, with an error
# (e.g., loss of message continuity after transport resume)
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: channel_name,
  error: ErrorInfo(code: 50000, statusCode: 500, message: "generic serverside failure")
))

AWAIT Future.delayed(Duration.zero)
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT length(update_events) == 1
ASSERT update_events[0].event == ChannelEvent.update
ASSERT update_events[0].current == ChannelState.attached
ASSERT update_events[0].previous == ChannelState.attached
ASSERT update_events[0].resumed == false
ASSERT update_events[0].reason.code == 50000
CLOSE_CLIENT(client)
```

---

## RTL12 - Additional ATTACHED with resumed=true does NOT emit UPDATE

**Spec requirement:** The UPDATE event should only be emitted if and only if the
`resumed` flag is false. When `resumed` is true, the additional ATTACHED message
indicates a successful resume with no loss of continuity, and no event should be
emitted to the public channel emitter.

Tests that an additional ATTACHED message with the RESUMED flag does not emit an
UPDATE event.

### Setup
```pseudo
channel_name = "test-RTL12-no-update-${random_id()}"

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
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

update_events = []
channel.on(ChannelEvent.update).listen((change) => update_events.append(change))

# Server sends additional ATTACHED WITH RESUMED flag
# This indicates successful resume with no loss of continuity
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: channel_name,
  flags: RESUMED
))

AWAIT Future.delayed(Duration.zero)
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT length(update_events) == 0
CLOSE_CLIENT(client)
```

---

## RTL12 - Additional ATTACHED without error has null reason

**Spec requirement:** The `reason` attribute is set to the `error` member of the
`ATTACHED` `ProtocolMessage` (if any).

Tests that when an additional ATTACHED message has no error field, the UPDATE
event's reason is null.

### Setup
```pseudo
channel_name = "test-RTL12-no-error-${random_id()}"

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
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

update_events = []
channel.on(ChannelEvent.update).listen((change) => update_events.append(change))

# Server sends additional ATTACHED without RESUMED flag and without error
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: channel_name
))

AWAIT Future.delayed(Duration.zero)
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT length(update_events) == 1
ASSERT update_events[0].resumed == false
ASSERT update_events[0].reason IS null
CLOSE_CLIENT(client)
```
