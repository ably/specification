# RealtimeChannel Subscribe and Unsubscribe Tests

Spec points: `RTL7`, `RTL7a`, `RTL7b`, `RTL7g`, `RTL7h`, `RTL7f`, `RTL8`, `RTL8a`, `RTL8b`, `RTL8c`, `RTL17`

## Test Type
Unit test with mocked WebSocket

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTL7a - Subscribe with no name receives all messages

**Spec requirement:** Subscribe with a single listener argument subscribes a listener to all messages.

Tests that subscribing without a name filter delivers all incoming messages regardless of name.

### Setup
```pseudo
channel_name = "test-RTL7a-${random_id()}"

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
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

received_messages = []
channel.subscribe((message) => {
  received_messages.append(message)
})

# Server sends messages with different names
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "event1", data: "data1")
  ]
))

mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "event2", data: "data2")
  ]
))

mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: null, data: "data3")
  ]
))
```

### Assertions
```pseudo
ASSERT length(received_messages) == 3
ASSERT received_messages[0].name == "event1"
ASSERT received_messages[0].data == "data1"
ASSERT received_messages[1].name == "event2"
ASSERT received_messages[1].data == "data2"
ASSERT received_messages[2].name IS null
ASSERT received_messages[2].data == "data3"
```

---

## RTL7a - Subscribe receives multiple messages from a single ProtocolMessage

**Spec requirement:** Subscribe with a single listener argument subscribes a listener to all messages.

Tests that when a ProtocolMessage contains multiple messages in its `messages` array, each is delivered individually to the subscriber.

### Setup
```pseudo
channel_name = "test-RTL7a-multi-${random_id()}"

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
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

received_messages = []
channel.subscribe((message) => {
  received_messages.append(message)
})

# Server sends a single ProtocolMessage with multiple messages
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "batch1", data: "first"),
    Message(name: "batch2", data: "second"),
    Message(name: "batch3", data: "third")
  ]
))
```

### Assertions
```pseudo
ASSERT length(received_messages) == 3
ASSERT received_messages[0].name == "batch1"
ASSERT received_messages[1].name == "batch2"
ASSERT received_messages[2].name == "batch3"
```

---

## RTL7b - Subscribe with name only receives matching messages

**Spec requirement:** Subscribe with a name argument and a listener argument subscribes a listener to only messages whose `name` member matches the string name.

Tests that subscribing with a name filter delivers only messages with the matching name.

### Setup
```pseudo
channel_name = "test-RTL7b-${random_id()}"

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
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

received_messages = []
channel.subscribe("target", (message) => {
  received_messages.append(message)
})

# Server sends messages with different names
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "other", data: "should-not-receive")
  ]
))

mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "target", data: "should-receive")
  ]
))

mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: null, data: "no-name-should-not-receive")
  ]
))
```

### Assertions
```pseudo
ASSERT length(received_messages) == 1
ASSERT received_messages[0].name == "target"
ASSERT received_messages[0].data == "should-receive"
```

---

## RTL7b - Multiple name-specific subscriptions are independent

**Spec requirement:** Subscribe with a name argument and a listener argument subscribes a listener to only messages whose `name` member matches the string name.

Tests that multiple name-specific subscriptions each receive only their matching messages.

### Setup
```pseudo
channel_name = "test-RTL7b-multi-${random_id()}"

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
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

alpha_messages = []
beta_messages = []

channel.subscribe("alpha", (message) => {
  alpha_messages.append(message)
})

channel.subscribe("beta", (message) => {
  beta_messages.append(message)
})

mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "alpha", data: "a1"),
    Message(name: "beta", data: "b1"),
    Message(name: "alpha", data: "a2"),
    Message(name: "gamma", data: "g1")
  ]
))
```

### Assertions
```pseudo
ASSERT length(alpha_messages) == 2
ASSERT alpha_messages[0].data == "a1"
ASSERT alpha_messages[1].data == "a2"

ASSERT length(beta_messages) == 1
ASSERT beta_messages[0].data == "b1"
```

---

## RTL7g - Subscribe triggers implicit attach when attachOnSubscribe is true

**Spec requirement:** If the `attachOnSubscribe` channel option is `true`, implicitly attaches the `RealtimeChannel` if the channel is in the `INITIALIZED`, `DETACHING`, or `DETACHED` states. The listener will always be registered regardless of the implicit attach result.

Tests that subscribing on a channel with `attachOnSubscribe: true` (the default) triggers an implicit attach from INITIALIZED state.

### Setup
```pseudo
channel_name = "test-RTL7g-${random_id()}"
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
# Default attachOnSubscribe is true
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

ASSERT channel.state == ChannelState.initialized

received_messages = []
channel.subscribe((message) => {
  received_messages.append(message)
})

# Wait for implicit attach to complete
AWAIT_STATE channel.state == ChannelState.attached
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT attach_message_count == 1

# Verify the listener was registered by sending a message
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "test", data: "hello")
  ]
))
ASSERT length(received_messages) == 1
```

---

## RTL7g - Subscribe triggers implicit attach from DETACHED state

**Spec requirement:** If the `attachOnSubscribe` channel option is `true`, implicitly attaches the `RealtimeChannel` if the channel is in the `INITIALIZED`, `DETACHING`, or `DETACHED` states.

Tests that subscribing on a DETACHED channel triggers an implicit attach.

### Setup
```pseudo
channel_name = "test-RTL7g-detached-${random_id()}"
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

AWAIT channel.attach()
AWAIT channel.detach()
ASSERT channel.state == ChannelState.detached
ASSERT attach_message_count == 1

# Subscribe should trigger implicit attach from DETACHED
channel.subscribe((message) => {})

AWAIT_STATE channel.state == ChannelState.attached
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT attach_message_count == 2
```

---

## RTL7g - Listener registered even if implicit attach fails

**Spec requirement:** The listener will always be registered regardless of the implicit attach result.

Tests that the subscription listener is registered even when the implicit attach fails.

### Setup
```pseudo
channel_name = "test-RTL7g-fail-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Fail the attach with a channel error
      mock_ws.send_to_client(ProtocolMessage(
        action: ERROR,
        channel: channel_name,
        error: ErrorInfo(code: 40160, statusCode: 401, message: "Not permitted")
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

received_messages = []
channel.subscribe((message) => {
  received_messages.append(message)
})

# Wait for the channel to enter FAILED from the rejected attach
AWAIT_STATE channel.state == ChannelState.failed

# Verify the listener was registered despite the failed attach.
# Re-attach the channel so messages can flow.
# First, reset mock to succeed on attach:
mock_ws.onMessageFromClient = (msg) => {
  IF msg.action == ATTACH:
    mock_ws.send_to_client(ProtocolMessage(
      action: ATTACHED,
      channel: channel_name
    ))
}
AWAIT channel.attach()

mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "test", data: "after-reattach")
  ]
))
```

### Assertions
```pseudo
ASSERT length(received_messages) == 1
ASSERT received_messages[0].data == "after-reattach"
```

---

## RTL7h - Subscribe does not attach when attachOnSubscribe is false

**Spec requirement:** If the `attachOnSubscribe` channel option is `false`, then subscribe should not trigger an implicit attach.

Tests that subscribing with `attachOnSubscribe: false` does not trigger an attach.

### Setup
```pseudo
channel_name = "test-RTL7h-${random_id()}"
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
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

ASSERT channel.state == ChannelState.initialized

channel.subscribe((message) => {})
```

### Assertions
```pseudo
# Channel should remain INITIALIZED — no attach triggered
ASSERT channel.state == ChannelState.initialized
ASSERT attach_message_count == 0
```

---

## RTL7g - Subscribe does not attach when already attached

**Spec requirement:** Implicitly attaches the `RealtimeChannel` if the channel is in the `INITIALIZED`, `DETACHING`, or `DETACHED` states.

Tests that subscribing on an already-attached channel does not trigger another attach.

### Setup
```pseudo
channel_name = "test-RTL7g-already-${random_id()}"
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

AWAIT channel.attach()
ASSERT attach_message_count == 1

# Subscribe on already-attached channel — no additional attach
channel.subscribe((message) => {})
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT attach_message_count == 1
```

---

## RTL7g - Subscribe does not attach when already attaching

**Spec requirement:** Implicitly attaches the `RealtimeChannel` if the channel is in the `INITIALIZED`, `DETACHING`, or `DETACHED` states.

Tests that subscribing on a channel that is already ATTACHING does not trigger a second attach.

### Setup
```pseudo
channel_name = "test-RTL7g-attaching-${random_id()}"
attach_message_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_message_count++
      # Don't respond yet — leave channel in ATTACHING
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

# Start attach but don't complete it
attach_future = channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching
ASSERT attach_message_count == 1

# Subscribe while attaching — should not trigger another attach
channel.subscribe((message) => {})
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attaching
ASSERT attach_message_count == 1  # No additional ATTACH message sent
```

---

## RTL17 - Messages not delivered when channel is not ATTACHED

**Spec requirement:** No messages should be passed to subscribers if the channel is in any state other than `ATTACHED`.

Tests that incoming MESSAGE protocol messages are not delivered to subscribers when the channel is not in the ATTACHED state (e.g. ATTACHING, SUSPENDED).

### Setup
```pseudo
channel_name = "test-RTL17-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Don't respond — leave channel in ATTACHING
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

received_messages = []
channel.subscribe((message) => {
  received_messages.append(message)
})

# Start attach but don't complete it — channel stays ATTACHING
attach_future = channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching

# Server sends a message while channel is still ATTACHING
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "premature", data: "should-not-deliver")
  ]
))
```

### Assertions
```pseudo
# Message should not have been delivered
ASSERT length(received_messages) == 0
```

---

## RTL7f - Messages not echoed when echoMessages is false

**Spec requirement:** A test should exist ensuring published messages are not echoed back to the subscriber when `echoMessages` is set to false in the `RealtimeClient` library constructor.

Tests that when `echoMessages` is false, messages originating from this connection (identified by matching `connectionId`) are not delivered to subscribers.

### Setup
```pseudo
channel_name = "test-RTL7f-${random_id()}"
connection_id = "conn-self-123"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(ProtocolMessage(
    action: CONNECTED,
    connectionId: connection_id,
    connectionKey: "key-456"
  )),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  echoMessages: false
))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

received_messages = []
channel.subscribe((message) => {
  received_messages.append(message)
})

# Server echoes back a message with this connection's connectionId
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  connectionId: connection_id,
  messages: [
    Message(name: "echo", data: "from-self")
  ]
))

# Server sends a message from a different connection
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  connectionId: "conn-other-789",
  messages: [
    Message(name: "remote", data: "from-other")
  ]
))
```

### Assertions
```pseudo
# Only the message from the other connection should be delivered
ASSERT length(received_messages) == 1
ASSERT received_messages[0].name == "remote"
ASSERT received_messages[0].data == "from-other"
```

---

## RTL8a - Unsubscribe specific listener from all messages

**Spec requirement:** Unsubscribe with a single listener argument unsubscribes the provided listener to all messages if subscribed.

Tests that unsubscribing a specific listener stops it from receiving messages, while other listeners continue.

### Setup
```pseudo
channel_name = "test-RTL8a-${random_id()}"

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
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

messages_a = []
messages_b = []

listener_a = (message) => { messages_a.append(message) }
listener_b = (message) => { messages_b.append(message) }

channel.subscribe(listener_a)
channel.subscribe(listener_b)

# Both listeners receive first message
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "msg1", data: "first")
  ]
))

ASSERT length(messages_a) == 1
ASSERT length(messages_b) == 1

# Unsubscribe listener_a
channel.unsubscribe(listener_a)

# Only listener_b should receive second message
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "msg2", data: "second")
  ]
))
```

### Assertions
```pseudo
ASSERT length(messages_a) == 1  # Did not receive second message
ASSERT length(messages_b) == 2  # Received both messages
ASSERT messages_b[1].name == "msg2"
```

---

## RTL8b - Unsubscribe listener from specific name

**Spec requirement:** Unsubscribe with a name argument and a listener argument unsubscribes the provided listener if previously subscribed with a name-specific subscription.

Tests that unsubscribing with a name removes only that name-specific subscription for the listener.

### Setup
```pseudo
channel_name = "test-RTL8b-${random_id()}"

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
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

received_messages = []
listener = (message) => { received_messages.append(message) }

# Subscribe to two different names with the same listener
channel.subscribe("alpha", listener)
channel.subscribe("beta", listener)

# Both subscriptions active
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "alpha", data: "a1"),
    Message(name: "beta", data: "b1")
  ]
))
ASSERT length(received_messages) == 2

# Unsubscribe only from "alpha"
channel.unsubscribe("alpha", listener)

mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "alpha", data: "a2"),
    Message(name: "beta", data: "b2")
  ]
))
```

### Assertions
```pseudo
# "alpha" unsubscribed but "beta" still active
ASSERT length(received_messages) == 3
ASSERT received_messages[2].name == "beta"
ASSERT received_messages[2].data == "b2"
```

---

## RTL8c - Unsubscribe with no arguments removes all listeners

**Spec requirement:** Unsubscribe with no arguments unsubscribes all listeners.

Tests that calling unsubscribe with no arguments removes all subscriptions from the channel.

### Setup
```pseudo
channel_name = "test-RTL8c-${random_id()}"

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
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

messages_all = []
messages_named = []

channel.subscribe((message) => { messages_all.append(message) })
channel.subscribe("specific", (message) => { messages_named.append(message) })

# Both listeners receive
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "specific", data: "first")
  ]
))
ASSERT length(messages_all) == 1
ASSERT length(messages_named) == 1

# Unsubscribe all
channel.unsubscribe()

# No listeners should receive
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "specific", data: "second"),
    Message(name: "other", data: "third")
  ]
))
```

### Assertions
```pseudo
ASSERT length(messages_all) == 1   # No new messages
ASSERT length(messages_named) == 1  # No new messages
```

---

## RTL8a - Unsubscribe listener not currently subscribed is no-op

**Spec requirement:** Unsubscribe with a single listener argument unsubscribes the provided listener to all messages if subscribed.

Tests that unsubscribing a listener that was never subscribed does not cause an error or affect existing subscriptions.

### Setup
```pseudo
channel_name = "test-RTL8a-noop-${random_id()}"

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
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

received_messages = []
active_listener = (message) => { received_messages.append(message) }
unused_listener = (message) => {}

channel.subscribe(active_listener)

# Unsubscribe a listener that was never subscribed — should be no-op
channel.unsubscribe(unused_listener)

mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "test", data: "still-works")
  ]
))
```

### Assertions
```pseudo
# Existing subscription should be unaffected
ASSERT length(received_messages) == 1
ASSERT received_messages[0].data == "still-works"
```
