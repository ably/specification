# Forwards Compatibility Tests (RTF1, RSF1)

Spec points: `RTF1`, `RSF1`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Overview

The Ably client library must apply the robustness principle to deserialization:

- **RTF1**: ProtocolMessages and related types must tolerate unrecognised attributes (ignored) and unknown enum values (handled gracefully).
- **RSF1**: Messages and related types must tolerate unrecognised attributes (ignored) and unknown enum values (ignored).

These tests verify that the library does not throw errors or crash when encountering unknown fields or enum values from the server, enabling forwards compatibility when the server adds new features.

---

## RTF1 - ProtocolMessage with unrecognised attributes is deserialized without error

**Spec requirement:** Deserialization of ProtocolMessages and related types must be tolerant to unrecognised attributes, which must be ignored.

Tests that the client correctly processes a ProtocolMessage containing extra unknown fields that are not part of the current spec, without throwing errors.

### Setup

```pseudo
channel_name = "test-RTF1-extra-attrs-${random_id()}"
received_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

channel = client.channels.get(channel_name)
channel.subscribe((msg) => {
  received_messages.append(msg)
})
channel.attach()

# Respond to ATTACH request
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: channel_name,
  flags: 0
))
AWAIT_STATE channel.state == ChannelState.attached

# Send a MESSAGE ProtocolMessage with extra unknown attributes.
# The raw JSON includes fields that don't exist in the current spec.
# The client must ignore these and process the message normally.
mock_ws.active_connection.send_to_client_raw({
  "action": 15,  # MESSAGE
  "channel": channel_name,
  "messages": [
    {
      "name": "test-event",
      "data": "hello",
      "serial": "msg-serial-1"
    }
  ],
  "unknownField1": "some-future-value",
  "unknownField2": 42,
  "unknownNestedObject": {
    "nestedKey": "nestedValue"
  },
  "unknownArray": [1, 2, 3]
})

# Wait for the message to be delivered to the subscriber
poll_until(
  () => received_messages.length >= 1,
  interval: 100ms,
  timeout: 5s
)
```

### Assertions

```pseudo
# Message was delivered successfully despite unknown fields
ASSERT received_messages.length == 1
ASSERT received_messages[0].name == "test-event"
ASSERT received_messages[0].data == "hello"

# Connection remains healthy
ASSERT client.connection.state == ConnectionState.connected
ASSERT channel.state == ChannelState.attached
CLOSE_CLIENT(client)
```

> **Implementation note:** The `send_to_client_raw` method sends a raw JSON object
> directly to the client's WebSocket, bypassing the ProtocolMessage constructor. This
> is necessary because the standard `send_to_client(ProtocolMessage(...))` would strip
> unknown fields during construction. If `send_to_client_raw` is not available in the
> mock infrastructure, implementations can serialize a ProtocolMessage and inject
> additional fields into the JSON before sending, or modify the mock to support
> arbitrary extra fields.

---

## RTF1 - ProtocolMessage with unknown action enum value is handled gracefully

**Spec requirement:** Deserialization of ProtocolMessages and associated enums must be tolerant to unknown enum values, which must be handled in some sensible, language-idiomatic way.

Tests that the client does not crash or disconnect when receiving a ProtocolMessage with an action value that is not defined in the current spec.

### Setup

```pseudo
channel_name = "test-RTF1-unknown-action-${random_id()}"
state_changes = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  useBinaryProtocol: false
))

# Record connection state changes to detect unexpected disconnections
client.connection.on((change) => {
  state_changes.append(change.current)
})
```

### Test Steps

```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Send a ProtocolMessage with an unknown action value.
# Action 254 is not defined in the current spec.
mock_ws.active_connection.send_to_client_raw({
  "action": 254,
  "channel": channel_name,
  "unknownPayload": "future-feature-data"
})

# Send a normal HEARTBEAT to verify the connection is still processing messages
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: HEARTBEAT
))

# Give the client time to process both messages
poll_until(
  () => true,
  interval: 100ms,
  timeout: 1s
)
```

### Assertions

```pseudo
# Connection should still be CONNECTED - the unknown action was silently ignored
ASSERT client.connection.state == ConnectionState.connected

# No unexpected state transitions occurred (only the initial connecting -> connected)
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.connecting,
  ConnectionState.connected
]
# Verify no disconnected or failed states appeared
ASSERT ConnectionState.disconnected NOT IN state_changes
ASSERT ConnectionState.failed NOT IN state_changes

CLOSE_CLIENT(client)
```

---

## RSF1 - Message with unrecognised attributes is deserialized without error

**Spec requirement:** Deserialization of Messages and related types, and associated enums, must be tolerant to unrecognised attributes or enum values. Such unrecognised values must be ignored.

Tests that a Message containing extra unknown fields is delivered to subscribers without error, and the known fields are correctly parsed.

### Setup

```pseudo
channel_name = "test-RSF1-extra-attrs-${random_id()}"
received_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

channel = client.channels.get(channel_name)
channel.subscribe((msg) => {
  received_messages.append(msg)
})
channel.attach()

# Respond to ATTACH request
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: channel_name,
  flags: 0
))
AWAIT_STATE channel.state == ChannelState.attached

# Send a MESSAGE ProtocolMessage where the individual messages within
# the messages array contain unknown fields. The ProtocolMessage itself
# is well-formed, but the Message objects have extra attributes.
mock_ws.active_connection.send_to_client_raw({
  "action": 15,  # MESSAGE
  "channel": channel_name,
  "messages": [
    {
      "name": "event-1",
      "data": "payload-1",
      "serial": "serial-1",
      "futureField": "future-value",
      "futureNumber": 99,
      "futureObject": {"nested": true}
    },
    {
      "name": "event-2",
      "data": "payload-2",
      "serial": "serial-2",
      "anotherUnknownField": [1, 2, 3]
    }
  ]
})

# Wait for both messages to be delivered
poll_until(
  () => received_messages.length >= 2,
  interval: 100ms,
  timeout: 5s
)
```

### Assertions

```pseudo
# Both messages were delivered successfully despite unknown fields
ASSERT received_messages.length == 2

# Known fields were correctly parsed
ASSERT received_messages[0].name == "event-1"
ASSERT received_messages[0].data == "payload-1"

ASSERT received_messages[1].name == "event-2"
ASSERT received_messages[1].data == "payload-2"

# Connection and channel remain healthy
ASSERT client.connection.state == ConnectionState.connected
ASSERT channel.state == ChannelState.attached
CLOSE_CLIENT(client)
```

---

## Implementation Notes

### send_to_client_raw

These tests require the ability to send raw JSON to the client's WebSocket connection, including fields that are not part of the ProtocolMessage or Message type definitions. The `send_to_client_raw` method on the mock connection accepts a raw JSON object (map/dictionary) and serializes it directly to the WebSocket, bypassing any type-safe constructors that would strip unknown fields.

If the mock infrastructure does not support `send_to_client_raw`, alternatives include:
1. Constructing a JSON string manually and writing it to the mock WebSocket transport
2. Modifying the mock `send_to_client` to accept extra fields as an additional parameter
3. Using the language's serialization to add fields post-construction (e.g., adding to a Map after `toJson()`)

### Enum Handling

The RTF1 test for unknown action values verifies that the client does not crash. The exact handling of unknown enum values is language-idiomatic:
- **Dart/Swift/Kotlin**: May deserialize to a sentinel/unknown enum variant or null
- **JavaScript/Python**: May store the raw numeric value
- **All languages**: Must not throw an exception or disconnect
