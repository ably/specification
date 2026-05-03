# RealtimeChannel Subscribe and Unsubscribe Tests

Spec points: `RTL7`, `RTL7a`, `RTL7b`, `RTL7g`, `RTL7h`, `RTL7f`, `RTL8`, `RTL8a`, `RTL8b`, `RTL8c`, `RTL17`, `RTL22`, `RTL22a`, `RTL22b`, `RTL22c`, `RTL22d`, `MFI1`, `MFI2`, `MFI2a`, `MFI2b`, `MFI2c`, `MFI2d`, `MFI2e`

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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
```

---

## RTL7f - Messages not echoed when echoMessages is false

**Spec requirement:** A test should exist ensuring published messages are not echoed back to the subscriber when `echoMessages` is set to false in the `RealtimeClient` library constructor.

> **Implementation note:** Echo suppression may be implemented either by client-side
> filtering (comparing incoming message connectionId against the local connectionId,
> as shown below) or by server-side delegation (passing `echo=false` in the connection
> parameters). SDKs using server-side delegation should adapt this test to verify the
> echo parameter is set on the connection URL, rather than testing client-side filtering.

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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
```

---

## RTL22a - Subscribe with MessageFilter matching name

| Spec | Requirement |
|------|-------------|
| RTL22 | Methods must be provided for attaching and removing a listener which only executes when the message matches a set of criteria. |
| RTL22a | The method must allow for filters matching one or more of: extras.ref.timeserial, extras.ref.type or name. See MFI1 for an object implementation. |
| RTL22d | The method should use the MessageFilter object if possible and idiomatic for the language. |
| MFI1 | Supplies filter options to subscribe as defined in RTL22. |
| MFI2d | name - A string for checking if a message's name matches the supplied value. |

Tests that subscribing with a MessageFilter specifying `name` delivers only messages whose name matches the filter.

### Setup
```pseudo
channel_name = "test-RTL22a-name-${random_id()}"

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

filtered_messages = []
filter = MessageFilter(name: "target-event")
channel.subscribe(filter, (message) => {
  filtered_messages.append(message)
})

# Server sends messages with different names
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "target-event", data: "match-1")
  ]
))

mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "other-event", data: "no-match")
  ]
))

mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "target-event", data: "match-2")
  ]
))

mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: null, data: "no-name")
  ]
))
```

### Assertions
```pseudo
ASSERT length(filtered_messages) == 2
ASSERT filtered_messages[0].name == "target-event"
ASSERT filtered_messages[0].data == "match-1"
ASSERT filtered_messages[1].name == "target-event"
ASSERT filtered_messages[1].data == "match-2"
CLOSE_CLIENT(client)
```

---

## RTL22a - Subscribe with MessageFilter matching extras.ref.timeserial

| Spec | Requirement |
|------|-------------|
| RTL22a | The method must allow for filters matching one or more of: extras.ref.timeserial, extras.ref.type or name. |
| MFI2b | refTimeserial - A string for checking if a message's extras.ref.timeserial matches the supplied value. |

Tests that subscribing with a MessageFilter specifying `refTimeserial` delivers only messages whose `extras.ref.timeserial` matches the filter value.

### Setup
```pseudo
channel_name = "test-RTL22a-ref-timeserial-${random_id()}"

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

filtered_messages = []
filter = MessageFilter(refTimeserial: "abc123@1700000000000-0")
channel.subscribe(filter, (message) => {
  filtered_messages.append(message)
})

# Message with matching extras.ref.timeserial
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "reply", data: "match", extras: {
      "ref": {"timeserial": "abc123@1700000000000-0", "type": "com.ably.reply"}
    })
  ]
))

# Message with different extras.ref.timeserial
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "reply", data: "no-match", extras: {
      "ref": {"timeserial": "xyz789@1700000000000-0", "type": "com.ably.reply"}
    })
  ]
))

# Message with no extras.ref at all
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "plain", data: "no-ref")
  ]
))

# Another message with matching extras.ref.timeserial
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "reaction", data: "match-2", extras: {
      "ref": {"timeserial": "abc123@1700000000000-0", "type": "com.ably.reaction"}
    })
  ]
))
```

### Assertions
```pseudo
ASSERT length(filtered_messages) == 2
ASSERT filtered_messages[0].data == "match"
ASSERT filtered_messages[1].data == "match-2"
CLOSE_CLIENT(client)
```

---

## RTL22b - Subscribe with MessageFilter isRef false delivers only messages without extras.ref

| Spec | Requirement |
|------|-------------|
| RTL22b | The method must allow for matching only messages which do not have extras.ref. |
| MFI2a | isRef - A boolean for checking if a message contains an extras.ref field. |

Tests that subscribing with a MessageFilter specifying `isRef: false` delivers only messages that do NOT have an `extras.ref` field.

### Setup
```pseudo
channel_name = "test-RTL22b-isref-false-${random_id()}"

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

filtered_messages = []
filter = MessageFilter(isRef: false)
channel.subscribe(filter, (message) => {
  filtered_messages.append(message)
})

# Message WITHOUT extras.ref (no extras at all)
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "plain", data: "no-extras")
  ]
))

# Message WITH extras.ref — should NOT be delivered
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "reply", data: "has-ref", extras: {
      "ref": {"timeserial": "abc123@1700000000000-0", "type": "com.ably.reply"}
    })
  ]
))

# Message with extras but no ref field — should be delivered
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "annotated", data: "extras-no-ref", extras: {
      "headers": {"custom-key": "custom-value"}
    })
  ]
))

# Another message WITH extras.ref — should NOT be delivered
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "reaction", data: "also-has-ref", extras: {
      "ref": {"timeserial": "xyz789@1700000000000-0", "type": "com.ably.reaction"}
    })
  ]
))
```

### Assertions
```pseudo
# Only messages without extras.ref should be delivered
ASSERT length(filtered_messages) == 2
ASSERT filtered_messages[0].name == "plain"
ASSERT filtered_messages[0].data == "no-extras"
ASSERT filtered_messages[1].name == "annotated"
ASSERT filtered_messages[1].data == "extras-no-ref"
CLOSE_CLIENT(client)
```

---

## RTL22c - Subscribe with MessageFilter matching multiple criteria (name + refType)

| Spec | Requirement |
|------|-------------|
| RTL22c | The listener must only execute if all provided criteria are met. |
| MFI2c | refType - A string for checking if a message's extras.ref.type matches the supplied value. |
| MFI2d | name - A string for checking if a message's name matches the supplied value. |

Tests that when a MessageFilter specifies multiple criteria (name AND refType), only messages matching ALL criteria are delivered.

### Setup
```pseudo
channel_name = "test-RTL22c-multi-${random_id()}"

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

filtered_messages = []
filter = MessageFilter(name: "comment", refType: "com.ably.reply")
channel.subscribe(filter, (message) => {
  filtered_messages.append(message)
})

# Message matching BOTH name AND refType — should be delivered
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "comment", data: "both-match", extras: {
      "ref": {"timeserial": "abc@1700000000000-0", "type": "com.ably.reply"}
    })
  ]
))

# Message matching name but NOT refType — should NOT be delivered
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "comment", data: "name-only", extras: {
      "ref": {"timeserial": "def@1700000000000-0", "type": "com.ably.reaction"}
    })
  ]
))

# Message matching refType but NOT name — should NOT be delivered
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "update", data: "type-only", extras: {
      "ref": {"timeserial": "ghi@1700000000000-0", "type": "com.ably.reply"}
    })
  ]
))

# Message matching NEITHER — should NOT be delivered
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "update", data: "neither")
  ]
))

# Another message matching BOTH — should be delivered
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "comment", data: "both-match-2", extras: {
      "ref": {"timeserial": "jkl@1700000000000-0", "type": "com.ably.reply"}
    })
  ]
))
```

### Assertions
```pseudo
# Only messages matching ALL criteria (name == "comment" AND refType == "com.ably.reply")
ASSERT length(filtered_messages) == 2
ASSERT filtered_messages[0].data == "both-match"
ASSERT filtered_messages[1].data == "both-match-2"
CLOSE_CLIENT(client)
```

---

## RTL22a, MFI2e - Subscribe with MessageFilter matching clientId

| Spec | Requirement |
|------|-------------|
| RTL22a | The method must allow for filters matching one or more of: extras.ref.timeserial, extras.ref.type or name. |
| MFI2e | clientId - A string for checking if a message's clientId matches the supplied value. |

Tests that subscribing with a MessageFilter specifying `clientId` delivers only messages whose clientId matches the filter value.

### Setup
```pseudo
channel_name = "test-RTL22a-clientid-${random_id()}"

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

filtered_messages = []
filter = MessageFilter(clientId: "user-42")
channel.subscribe(filter, (message) => {
  filtered_messages.append(message)
})

# Message with matching clientId
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "chat", data: "hello", clientId: "user-42")
  ]
))

# Message with different clientId — should NOT be delivered
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "chat", data: "hi", clientId: "user-99")
  ]
))

# Message with no clientId — should NOT be delivered
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "system", data: "broadcast")
  ]
))

# Another message with matching clientId
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    Message(name: "chat", data: "world", clientId: "user-42")
  ]
))
```

### Assertions
```pseudo
ASSERT length(filtered_messages) == 2
ASSERT filtered_messages[0].data == "hello"
ASSERT filtered_messages[0].clientId == "user-42"
ASSERT filtered_messages[1].data == "world"
ASSERT filtered_messages[1].clientId == "user-42"
CLOSE_CLIENT(client)
```
