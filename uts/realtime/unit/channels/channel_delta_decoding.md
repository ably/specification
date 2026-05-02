# Channel Delta Decoding Tests

Spec points: `RTL18`, `RTL18a`, `RTL18b`, `RTL18c`, `RTL19`, `RTL19a`, `RTL19b`, `RTL19c`, `RTL20`, `RTL21`, `PC3`, `PC3a`

## Test Type
Unit test with mocked WebSocket

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Mock VCDiff Infrastructure

See `uts/test/realtime/unit/helpers/mock_vcdiff.md` for the full Mock VCDiff Infrastructure specification.

> **Transport encoding note:** On JSON transport (the default for unit tests),
> binary vcdiff delta payloads cannot be transmitted as raw bytes — they must be
> base64-encoded. Mock message constructions in these tests use raw data with
> `encoding: "vcdiff"` for clarity. Implementations using JSON transport should
> adapt mock messages to use `base64_encode(delta)` as the data, with `/base64`
> appended to the encoding field (e.g., `"vcdiff/base64"` or `"utf-8/vcdiff/base64"`).
> The SDK's decoding pipeline processes encoding steps right-to-left: base64-decode
> first, then apply vcdiff, then decode utf-8 if present.

---

## RTL21 - Messages in array decoded in ascending index order

**Spec requirement:** The messages in the `messages` array of a `ProtocolMessage` should each be decoded in ascending order of their index in the array.

Tests that when a ProtocolMessage contains multiple messages where later messages
are deltas referencing earlier messages, they are decoded correctly because
processing happens in array order.

### Setup
```pseudo
channel_name = "test-RTL21-order-${random_id()}"
encoder = MockVCDiffEncoder()
decoder = MockVCDiffDecoder()

received_messages = []

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

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  plugins: { vcdiff: decoder }
))
channel = client.channels.get(channel_name)
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Send a ProtocolMessage with 3 messages:
# - msg-1: non-delta (establishes base)
# - msg-2: delta referencing msg-1
# - msg-3: delta referencing msg-2
# This only works if messages are decoded in order [0], [1], [2]

base_data = "first message"
second_data = "second message"
third_data = "third message"

delta_1_to_2 = encoder.encode(base_data, second_data)
delta_2_to_3 = encoder.encode(second_data, third_data)

mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "serial:0",
  messages: [
    {
      id: "serial:0",
      data: base_data,
      encoding: null
    },
    {
      id: "serial:1",
      data: delta_1_to_2,
      encoding: "vcdiff",
      extras: { delta: { from: "serial:0", format: "vcdiff" } }
    },
    {
      id: "serial:2",
      data: delta_2_to_3,
      encoding: "vcdiff",
      extras: { delta: { from: "serial:1", format: "vcdiff" } }
    }
  ]
))

AWAIT length(received_messages) == 3
```

### Assertions
```pseudo
ASSERT received_messages[0].data == "first message"
ASSERT received_messages[1].data == "second message"
ASSERT received_messages[2].data == "third message"
CLOSE_CLIENT(client)
```

---

## RTL19b - Non-delta message stores base payload

**Spec requirement:** In the case of a non-delta message, the resulting `data` value is stored as the base payload.

Tests that after receiving a non-delta message, its data is stored as the base
payload so that a subsequent delta message can reference it.

### Setup
```pseudo
channel_name = "test-RTL19b-base-${random_id()}"
encoder = MockVCDiffEncoder()
decoder = MockVCDiffDecoder()

received_messages = []

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

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  plugins: { vcdiff: decoder }
))
channel = client.channels.get(channel_name)
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Send non-delta message to establish base
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-1:0",
  messages: [
    {
      id: "msg-1:0",
      data: "base payload",
      encoding: null
    }
  ]
))

AWAIT length(received_messages) == 1

# Send delta referencing the base
delta = encoder.encode("base payload", "updated payload")

mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-2:0",
  messages: [
    {
      id: "msg-2:0",
      data: delta,
      encoding: "vcdiff",
      extras: { delta: { from: "msg-1:0", format: "vcdiff" } }
    }
  ]
))

AWAIT length(received_messages) == 2
```

### Assertions
```pseudo
ASSERT received_messages[0].data == "base payload"
ASSERT received_messages[1].data == "updated payload"
CLOSE_CLIENT(client)
```

---

## RTL19b - JSON-encoded non-delta message stores wire-form base payload

**Spec requirement:** In the case of a non-delta message, the resulting `data` value
is stored as the base payload.

Tests that when a non-delta message has `encoding: "json"`, the base payload stored
for subsequent delta decoding is the raw JSON **string** (the wire form after base64
decoding, if any, but **before** json/utf-8 decoding), not the parsed object. This
matches the ably-js behaviour where `lastPayload` is only updated by `base64`
(outermost) and `vcdiff` steps, never by `json` or `utf-8`.

This is critical because the vcdiff delta is computed by the server against the
wire-form payload. Storing the fully-decoded object (e.g., a Map) instead of the
JSON string would cause vcdiff decoding to fail with "no base payload available"
since the stored value would not be a String or Uint8List.

### Setup
```pseudo
channel_name = "test-RTL19b-json-base-${random_id()}"
encoder = MockVCDiffEncoder()
decoder = MockVCDiffDecoder()

received_messages = []

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

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  plugins: { vcdiff: decoder }
))
channel = client.channels.get(channel_name)
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Send a non-delta message with JSON encoding.
# The wire data is a JSON string; after decoding, the subscriber sees a Map.
# The base payload stored for delta decoding should be the JSON string,
# not the parsed Map.
json_string = '{"foo":"bar","count":1}'

mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-1:0",
  messages: [
    {
      id: "msg-1:0",
      data: json_string,
      encoding: "json"
    }
  ]
))

AWAIT length(received_messages) == 1

# Send a delta referencing the JSON string base.
# The delta is computed against the JSON string, not the parsed object.
new_json_string = '{"foo":"baz","count":2}'
delta = encoder.encode(json_string, new_json_string)

mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-2:0",
  messages: [
    {
      id: "msg-2:0",
      data: delta,
      encoding: "utf-8/vcdiff",
      extras: { delta: { from: "msg-1:0", format: "vcdiff" } }
    }
  ]
))

AWAIT length(received_messages) == 2
```

### Assertions
```pseudo
# First message: subscriber receives the parsed JSON object
ASSERT received_messages[0].data == { "foo": "bar", "count": 1 }

# Second message: delta decoded against JSON string base, then utf-8 decoded
# to produce the new JSON string, which is delivered as-is (no json encoding
# step in the delta message's encoding)
ASSERT received_messages[1].data == new_json_string
CLOSE_CLIENT(client)
```

---

## RTL19a - Base64 encoding step decoded before storing base payload

**Spec requirement:** When processing any message (whether a delta or a full message), if the message `encoding` string ends in `base64`, the message `data` should be base64-decoded (and the `encoding` string modified accordingly per RSL6).

Tests that a base64-encoded non-delta message is decoded before its data is
stored as the base payload, so that subsequent delta application uses the decoded
(binary) form.

### Setup
```pseudo
channel_name = "test-RTL19a-base64-${random_id()}"
encoder = MockVCDiffEncoder()
decoder = MockVCDiffDecoder()

received_messages = []

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

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  plugins: { vcdiff: decoder }
))
channel = client.channels.get(channel_name)
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# The base payload is binary data [0x48, 0x65, 0x6C, 0x6C, 0x6F] ("Hello")
# Sent as base64-encoded string
base_binary = [0x48, 0x65, 0x6C, 0x6C, 0x6F]
base_as_base64 = "SGVsbG8="

mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-1:0",
  messages: [
    {
      id: "msg-1:0",
      data: base_as_base64,
      encoding: "base64"
    }
  ]
))

AWAIT length(received_messages) == 1

# Now send a delta that references the binary base payload
new_binary = [0x57, 0x6F, 0x72, 0x6C, 0x64]  # "World"
delta = encoder.encode(base_binary, new_binary)

mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-2:0",
  messages: [
    {
      id: "msg-2:0",
      data: base64_encode(delta),
      encoding: "vcdiff/base64",
      extras: { delta: { from: "msg-1:0", format: "vcdiff" } }
    }
  ]
))

AWAIT length(received_messages) == 2
```

### Assertions
```pseudo
# First message decoded from base64 to binary
ASSERT received_messages[0].data == base_binary

# Second message delta-decoded using the binary base, then delivered as binary
ASSERT received_messages[1].data == new_binary
CLOSE_CLIENT(client)
```

---

## RTL19c - Delta application result stored as new base payload

**Spec requirement:** In the case of a delta message with a `vcdiff` encoding step, the `vcdiff` decoder must be used to decode the base payload of the delta message, applying that delta to the stored base payload. The direct result of that vcdiff delta application, before performing any further decoding steps, is stored as the updated base payload.

Tests that after decoding a delta message, the decoded result becomes the new
base payload for subsequent deltas (chained deltas).

### Setup
```pseudo
channel_name = "test-RTL19c-chain-${random_id()}"
encoder = MockVCDiffEncoder()
decoder = MockVCDiffDecoder()

received_messages = []

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

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  plugins: { vcdiff: decoder }
))
channel = client.channels.get(channel_name)
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Message 1: non-delta, establishes base
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-1:0",
  messages: [
    {
      id: "msg-1:0",
      data: "value-A",
      encoding: null
    }
  ]
))

AWAIT length(received_messages) == 1

# Message 2: delta from msg-1 to value-B
delta_A_to_B = encoder.encode("value-A", "value-B")

mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-2:0",
  messages: [
    {
      id: "msg-2:0",
      data: delta_A_to_B,
      encoding: "vcdiff",
      extras: { delta: { from: "msg-1:0", format: "vcdiff" } }
    }
  ]
))

AWAIT length(received_messages) == 2

# Message 3: delta from msg-2 to value-C
# This verifies the base was updated to value-B after decoding msg-2
delta_B_to_C = encoder.encode("value-B", "value-C")

mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-3:0",
  messages: [
    {
      id: "msg-3:0",
      data: delta_B_to_C,
      encoding: "vcdiff",
      extras: { delta: { from: "msg-2:0", format: "vcdiff" } }
    }
  ]
))

AWAIT length(received_messages) == 3
```

### Assertions
```pseudo
ASSERT received_messages[0].data == "value-A"
ASSERT received_messages[1].data == "value-B"
ASSERT received_messages[2].data == "value-C"
CLOSE_CLIENT(client)
```

---

## RTL20 - Delta with mismatched base message ID triggers recovery

**Spec requirement:** The `id` of the last received message on each channel must be stored along with the base payload. When processing a delta message, the stored last message `id` must be compared against the delta reference `id` in `Message.extras.delta.from`. If the delta reference `id` does not equal the stored `id`, the message decoding must fail and the recovery procedure from RTL18 must be executed.

Tests that when a delta message references a message ID that doesn't match the
stored last message ID, the client initiates decode failure recovery.

### Setup
```pseudo
channel_name = "test-RTL20-mismatch-${random_id()}"
encoder = MockVCDiffEncoder()
decoder = MockVCDiffDecoder()

state_changes = []
attach_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_messages.append(msg)
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
  plugins: { vcdiff: decoder }
))
channel = client.channels.get(channel_name)
channel.on((change) => state_changes.append(change))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Establish base with msg-1
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-1:0",
  channelSerial: "serial-1",
  messages: [
    {
      id: "msg-1:0",
      data: "base payload",
      encoding: null
    }
  ]
))

# Wait for message to be processed
AWAIT Future.delayed(Duration.zero)

# Clear state tracking from initial attach
state_changes = []
initial_attach_count = length(attach_messages)

# Send delta that references wrong message ID (msg-999 instead of msg-1)
delta = encoder.encode("base payload", "new payload")

mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-2:0",
  messages: [
    {
      id: "msg-2:0",
      data: delta,
      encoding: "vcdiff",
      extras: { delta: { from: "msg-999:0", format: "vcdiff" } }
    }
  ]
))

# RTL18c: channel transitions to ATTACHING and sends ATTACH
AWAIT_STATE channel.state == ChannelState.attaching
```

### Assertions
```pseudo
# RTL18c: A new ATTACH message was sent for recovery
ASSERT length(attach_messages) > initial_attach_count

# RTL18c: The ATTACH message includes channelSerial from previous message
recovery_attach = attach_messages[length(attach_messages) - 1]
ASSERT recovery_attach.channelSerial == "serial-1"

# RTL18c: Channel state went to ATTACHING with error code 40018
ASSERT state_changes CONTAINS_IN_ORDER [
  ChannelState.attaching
]
attaching_change = FIND state_changes WHERE current == ChannelState.attaching
ASSERT attaching_change.reason.code == 40018
CLOSE_CLIENT(client)
```

---

## RTL20 - Last message ID updated after successful decode

**Spec requirement:** The `id` of the last received message on each channel must be stored along with the base payload.

Tests that the stored last message ID is updated to the ID of the last message
in a ProtocolMessage after successful decoding, and is used correctly for the
next delta's base reference check.

### Setup
```pseudo
channel_name = "test-RTL20-id-update-${random_id()}"
encoder = MockVCDiffEncoder()
decoder = MockVCDiffDecoder()

received_messages = []

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

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  plugins: { vcdiff: decoder }
))
channel = client.channels.get(channel_name)
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Send ProtocolMessage with 2 messages in the array
# The last message ID should be stored as "serial:1" (the last in the array)
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "serial:0",
  messages: [
    {
      id: "serial:0",
      data: "first",
      encoding: null
    },
    {
      id: "serial:1",
      data: "second",
      encoding: null
    }
  ]
))

AWAIT length(received_messages) == 2

# Now send a delta that references "serial:1" (the last message ID)
# This should succeed because the stored ID matches
delta = encoder.encode("second", "third")

mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-2:0",
  messages: [
    {
      id: "msg-2:0",
      data: delta,
      encoding: "vcdiff",
      extras: { delta: { from: "serial:1", format: "vcdiff" } }
    }
  ]
))

AWAIT length(received_messages) == 3
```

### Assertions
```pseudo
# The delta was decoded successfully, confirming the stored ID was "serial:1"
ASSERT received_messages[0].data == "first"
ASSERT received_messages[1].data == "second"
ASSERT received_messages[2].data == "third"
CLOSE_CLIENT(client)
```

---

## PC3, PC3a - VCDiff plugin decodes delta messages

| Spec | Requirement |
|------|-------------|
| PC3 | A plugin provided with PluginType key `vcdiff` should be capable of decoding vcdiff-encoded messages |
| PC3a | The base argument of VCDiffDecoder.decode should receive the stored base payload; if the base is a string it should be UTF-8 encoded to binary before being passed |

Tests that the vcdiff plugin is used to decode delta-encoded messages and that
string base payloads are UTF-8 encoded to binary before being passed to the
decoder.

### Setup
```pseudo
channel_name = "test-PC3-decode-${random_id()}"
encoder = MockVCDiffEncoder()

# Use a wrapping decoder that records the arguments it receives
decode_calls = []

recording_decoder = MockVCDiffDecoder(
  onDecode: (delta, base) => {
    decode_calls.append({ delta: delta, base: base })
  }
)

received_messages = []

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

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  plugins: { vcdiff: recording_decoder }
))
channel = client.channels.get(channel_name)
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Send a string non-delta message (establishes string base payload)
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-1:0",
  messages: [
    {
      id: "msg-1:0",
      data: "hello world",
      encoding: null
    }
  ]
))

AWAIT length(received_messages) == 1

# Send a delta message referencing the string base
delta = encoder.encode("hello world", "goodbye world")

mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-2:0",
  messages: [
    {
      id: "msg-2:0",
      data: delta,
      encoding: "vcdiff",
      extras: { delta: { from: "msg-1:0", format: "vcdiff" } }
    }
  ]
))

AWAIT length(received_messages) == 2
```

### Assertions
```pseudo
# PC3: The decoder was called to decode the delta
ASSERT length(decode_calls) == 1

# PC3a: The base argument was UTF-8 encoded to binary
# "hello world" as UTF-8 bytes
ASSERT decode_calls[0].base == utf8_encode("hello world")

# PC3a: The delta argument is the raw delta payload
ASSERT decode_calls[0].delta == delta

# The decoded message was delivered to the subscriber
ASSERT received_messages[1].data == "goodbye world"
CLOSE_CLIENT(client)
```

---

## PC3 - No vcdiff plugin causes FAILED state

**Spec requirement:** A plugin provided with the PluginType key `vcdiff` should be capable of decoding vcdiff-encoded messages. Without it, vcdiff-encoded messages cannot be decoded.

Tests that when a vcdiff-encoded message is received but no vcdiff plugin is
registered, the channel transitions to FAILED with error code 40019.

### Setup
```pseudo
channel_name = "test-PC3-no-plugin-${random_id()}"

state_changes = []

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

# No vcdiff plugin registered
client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
channel = client.channels.get(channel_name)
channel.on((change) => state_changes.append(change))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

state_changes = []

# Send a delta-encoded message without a vcdiff plugin registered
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-1:0",
  messages: [
    {
      id: "msg-1:0",
      data: "some-delta-data",
      encoding: "vcdiff",
      extras: { delta: { from: "msg-0:0", format: "vcdiff" } }
    }
  ]
))

# Channel should transition to FAILED
AWAIT_STATE channel.state == ChannelState.failed
```

### Assertions
```pseudo
# Channel is FAILED with error code 40019 (no vcdiff plugin)
ASSERT channel.state == ChannelState.failed
ASSERT channel.errorReason.code == 40019
CLOSE_CLIENT(client)
```

---

## RTL18 - Decode failure triggers recovery (RTL18a, RTL18b, RTL18c)

| Spec | Requirement |
|------|-------------|
| RTL18a | Log error with code 40018 |
| RTL18b | Discard the message |
| RTL18c | Send ATTACH with channelSerial set to previous message's channelSerial, transition to ATTACHING, wait for ATTACHED confirmation. ChannelStateChange.reason should have code 40018. |

Tests that when vcdiff decoding fails, the client discards the message,
transitions to ATTACHING, and sends an ATTACH with the correct channelSerial for
recovery.

### Setup
```pseudo
channel_name = "test-RTL18-recovery-${random_id()}"

state_changes = []
attach_messages = []
received_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_messages.append(msg)
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

# Use a decoder that always fails
failing_decoder = FailingMockVCDiffDecoder()

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  plugins: { vcdiff: failing_decoder }
))
channel = client.channels.get(channel_name)
channel.on((change) => state_changes.append(change))
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Establish base with a non-delta message first
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-1:0",
  channelSerial: "serial-100",
  messages: [
    {
      id: "msg-1:0",
      data: "base payload",
      encoding: null
    }
  ]
))

AWAIT length(received_messages) == 1

# Clear state tracking from initial attach
state_changes = []
initial_attach_count = length(attach_messages)

# Send a delta message — the failing decoder will throw during decode
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-2:0",
  channelSerial: "serial-200",
  messages: [
    {
      id: "msg-2:0",
      data: "fake-delta-payload",
      encoding: "vcdiff",
      extras: { delta: { from: "msg-1:0", format: "vcdiff" } }
    }
  ]
))

# RTL18c: channel transitions to ATTACHING for recovery
AWAIT_STATE channel.state == ChannelState.attaching
```

### Assertions
```pseudo
# RTL18b: The failed delta message was NOT delivered to subscribers
ASSERT length(received_messages) == 1
ASSERT received_messages[0].data == "base payload"

# RTL18c: A new ATTACH was sent for recovery
ASSERT length(attach_messages) > initial_attach_count
recovery_attach = attach_messages[length(attach_messages) - 1]

# RTL18c: The ATTACH includes channelSerial from the previous successful message
ASSERT recovery_attach.channelSerial == "serial-100"

# RTL18c: Channel state went to ATTACHING with error code 40018
ASSERT state_changes CONTAINS_IN_ORDER [
  ChannelState.attaching
]
attaching_change = FIND state_changes WHERE current == ChannelState.attaching
ASSERT attaching_change.reason.code == 40018
CLOSE_CLIENT(client)
```

---

## RTL18c - Recovery completes when server sends ATTACHED

**Spec requirement:** Send an ATTACH ProtocolMessage and wait for a confirmation ATTACHED, as per RTL4c and RTL4f.

Tests that after decode failure recovery, the channel returns to ATTACHED state
when the server confirms with an ATTACHED ProtocolMessage, and that new messages
can be received afterwards.

### Setup
```pseudo
channel_name = "test-RTL18c-complete-${random_id()}"
encoder = MockVCDiffEncoder()

state_changes = []
received_messages = []
attach_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

# Use a decoder that fails on first call, then succeeds
decode_attempt = 0
conditional_decoder = MockVCDiffDecoder(
  onDecode: (delta, base) => {
    decode_attempt++
    IF decode_attempt == 1:
      THROW "Simulated decode failure"
  }
)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  plugins: { vcdiff: conditional_decoder }
))
channel = client.channels.get(channel_name)
channel.on((change) => state_changes.append(change))
channel.subscribe((msg) => received_messages.append(msg))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Establish base
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-1:0",
  channelSerial: "serial-1",
  messages: [
    {
      id: "msg-1:0",
      data: "original base",
      encoding: null
    }
  ]
))

AWAIT length(received_messages) == 1

# Send delta that will fail on first decode attempt
# This triggers recovery → ATTACHING → ATTACHED
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-2:0",
  channelSerial: "serial-2",
  messages: [
    {
      id: "msg-2:0",
      data: "bad-delta",
      encoding: "vcdiff",
      extras: { delta: { from: "msg-1:0", format: "vcdiff" } }
    }
  ]
))

# Recovery: ATTACHING → server auto-responds with ATTACHED
AWAIT_STATE channel.state == ChannelState.attached

state_changes = []

# After recovery, server resends from channelSerial with a fresh non-delta
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-3:0",
  channelSerial: "serial-3",
  messages: [
    {
      id: "msg-3:0",
      data: "fresh after recovery",
      encoding: null
    }
  ]
))

AWAIT length(received_messages) == 2
```

### Assertions
```pseudo
# Channel recovered and is now attached
ASSERT channel.state == ChannelState.attached

# Messages received: the original base and the fresh message after recovery
# (the failed delta msg-2 was discarded per RTL18b)
ASSERT received_messages[0].data == "original base"
ASSERT received_messages[1].data == "fresh after recovery"
CLOSE_CLIENT(client)
```

---

## RTL18 - Only one recovery in progress at a time

**Spec requirement:** The client must automatically execute the recovery procedure. (Implied: concurrent decode failures should not trigger multiple simultaneous recovery attempts.)

Tests that if multiple delta decode failures occur in quick succession, only one
recovery ATTACH is sent (the recovery flag prevents duplicate recovery attempts).

### Setup
```pseudo
channel_name = "test-RTL18-single-recovery-${random_id()}"

attach_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      attach_messages.append(msg)
      # Do NOT auto-respond with ATTACHED — leave recovery in progress
      IF length(attach_messages) == 1:
        # Only respond to the initial attach
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: channel_name
        ))
  }
)
install_mock(mock_ws)

failing_decoder = FailingMockVCDiffDecoder()

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  plugins: { vcdiff: failing_decoder }
))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

initial_attach_count = length(attach_messages)

# Establish base
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-1:0",
  channelSerial: "serial-1",
  messages: [
    {
      id: "msg-1:0",
      data: "base",
      encoding: null
    }
  ]
))

AWAIT Future.delayed(Duration.zero)

# Send first delta that will fail — triggers recovery
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-2:0",
  messages: [
    {
      id: "msg-2:0",
      data: "bad-delta-1",
      encoding: "vcdiff",
      extras: { delta: { from: "msg-1:0", format: "vcdiff" } }
    }
  ]
))

AWAIT_STATE channel.state == ChannelState.attaching

# Send second delta that also fails — recovery already in progress
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  id: "msg-3:0",
  messages: [
    {
      id: "msg-3:0",
      data: "bad-delta-2",
      encoding: "vcdiff",
      extras: { delta: { from: "msg-2:0", format: "vcdiff" } }
    }
  ]
))

AWAIT Future.delayed(Duration.zero)
```

### Assertions
```pseudo
# Only one recovery ATTACH was sent (not two)
recovery_attaches = length(attach_messages) - initial_attach_count
ASSERT recovery_attaches == 1
CLOSE_CLIENT(client)
```
