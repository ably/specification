# Delta Decoding Integration Tests

Spec points: `PC3`, `PC3a`, `RTL18`, `RTL18b`, `RTL18c`, `RTL19b`, `RTL20`

## Test Type
Integration test against Ably sandbox

## Purpose

End-to-end verification of vcdiff delta decoding using real connections against the
Ably sandbox. The server generates vcdiff-encoded deltas when a channel is attached
with `params: { delta: 'vcdiff' }`. These tests verify that the SDK correctly
decodes those deltas using a real vcdiff decoder plugin.

These tests complement the unit tests (which use a mock vcdiff encoder/decoder) by
exercising the full pipeline: publish → server generates delta → SDK decodes with
real vcdiff decoder → subscriber receives original data.

## Dependencies

These tests require a real VCDiff decoder that implements the `VCDiffDecoder`
interface (`VD2a`). The decoder must accept `(delta: byte[], base: byte[]) -> byte[]`.

Concrete implementations should adapt whichever vcdiff library is available for their
platform. For example, the Dart SDK uses the `vcdiff` package which exposes
`decode(Uint8List source, Uint8List delta) -> Uint8List` — note the swapped argument
order compared to `VD2a`.

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox-rest.ably.io`.

**Note:** `useBinaryProtocol: false` is required if the SDK does not implement msgpack.

### App Provisioning

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

### Test Data

All tests that publish multiple messages use the same dataset:

```pseudo
test_data = [
  { foo: "bar", count: 1, status: "active" },
  { foo: "bar", count: 2, status: "active" },
  { foo: "bar", count: 2, status: "inactive" },
  { foo: "bar", count: 3, status: "inactive" },
  { foo: "bar", count: 3, status: "active" }
]
```

The data is intentionally similar between messages so that the server generates
small vcdiff deltas rather than sending full messages.

---

## PC3 - Delta plugin decodes messages end-to-end

**Spec requirement:** A plugin provided with the PluginType key `vcdiff` should be
capable of decoding vcdiff-encoded messages.

Tests that with a real vcdiff decoder plugin and a channel configured for delta
mode, all published messages are received with correct data, and that the decoder
was invoked for the delta messages (all except the first).

### Setup
```pseudo
channel_name = "delta-PC3-" + random_id()

# Use a wrapping decoder that counts invocations
decode_count = 0
counting_decoder = VCDiffDecoder(
  onDecode: (delta, base) => {
    decode_count++
  }
)

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false,
  plugins: { vcdiff: counting_decoder }
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

channel = client.channels.get(channel_name, options: ChannelOptions(
  params: { "delta": "vcdiff" }
))

AWAIT channel.attach()

received_messages = []

# Fail the test if the channel reattaches (decode failure)
channel.on(ChannelEvent.attaching, (change) => {
  FAIL("Channel reattaching due to decode failure: " + change.reason)
})

channel.subscribe((msg) => received_messages.append(msg))

# Publish all messages sequentially
FOR i IN 0..length(test_data) - 1:
  AWAIT channel.publish(str(i), test_data[i])

# Wait for all messages to be received
WAIT UNTIL length(received_messages) == length(test_data)
  WITH timeout: 15 seconds
```

### Assertions
```pseudo
FOR i IN 0..length(test_data) - 1:
  ASSERT received_messages[i].name == str(i)
  ASSERT received_messages[i].data == test_data[i]

# First message is sent as full payload, rest as deltas
ASSERT decode_count == length(test_data) - 1
```

### Cleanup
```pseudo
client.close()
```

---

## RTL19b - Dissimilar payloads received without delta encoding

**Spec requirement:** In the case of a non-delta message, the resulting `data` value
is stored as the base payload.

Tests that when a channel is configured for delta mode but successive messages have
completely dissimilar payloads (random binary data), the server is expected to send
full messages rather than deltas. The SDK must handle this correctly — each non-delta
message updates the stored base payload and is delivered to subscribers.

If the server nonetheless chooses to generate a delta, the test does not fail; it
verifies correct behaviour regardless of whether deltas are used. The assertion on
decode count is skipped if deltas were generated.

### Setup
```pseudo
channel_name = "delta-dissimilar-" + random_id()
message_count = 5

decode_count = 0
counting_decoder = VCDiffDecoder(
  onDecode: (delta, base) => {
    decode_count++
  }
)

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false,
  plugins: { vcdiff: counting_decoder }
))

# Generate random binary payloads — 1KB each, completely dissimilar
payloads = []
FOR i IN 0..message_count - 1:
  payloads.append(random_bytes(1024))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

channel = client.channels.get(channel_name, options: ChannelOptions(
  params: { "delta": "vcdiff" }
))

AWAIT channel.attach()

received_messages = []

# Fail the test if the channel reattaches (decode failure)
channel.on(ChannelEvent.attaching, (change) => {
  FAIL("Channel reattaching due to decode failure: " + change.reason)
})

channel.subscribe((msg) => received_messages.append(msg))

FOR i IN 0..message_count - 1:
  AWAIT channel.publish(str(i), payloads[i])

WAIT UNTIL length(received_messages) == message_count
  WITH timeout: 15 seconds
```

### Assertions
```pseudo
# All messages received with correct data
FOR i IN 0..message_count - 1:
  ASSERT received_messages[i].name == str(i)
  ASSERT received_messages[i].data == payloads[i]

# The server is expected to send full messages (no deltas) for dissimilar
# random binary payloads. If so, the decoder should not have been called.
# However, the server may still choose to generate deltas, so we only log
# the decode count rather than asserting it is zero.
LOG "Decoder was called " + str(decode_count) + " times for " + str(message_count) + " dissimilar messages"
```

### Cleanup
```pseudo
client.close()
```

---

## PC3 - No deltas without delta channel param

**Spec requirement:** The vcdiff plugin is only used when the channel is configured to
request delta compression from the server.

Tests that when a channel is attached without `params: { delta: 'vcdiff' }`, the
server sends full messages and the vcdiff decoder is never called.

### Setup
```pseudo
channel_name = "delta-no-param-" + random_id()

decode_count = 0
counting_decoder = VCDiffDecoder(
  onDecode: (delta, base) => {
    decode_count++
  }
)

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false,
  plugins: { vcdiff: counting_decoder }
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Attach WITHOUT delta params
channel = client.channels.get(channel_name)

AWAIT channel.attach()

received_messages = []
channel.subscribe((msg) => received_messages.append(msg))

FOR i IN 0..length(test_data) - 1:
  AWAIT channel.publish(str(i), test_data[i])

WAIT UNTIL length(received_messages) == length(test_data)
  WITH timeout: 15 seconds
```

### Assertions
```pseudo
FOR i IN 0..length(test_data) - 1:
  ASSERT received_messages[i].name == str(i)
  ASSERT received_messages[i].data == test_data[i]

# No deltas — decoder was never called
ASSERT decode_count == 0
```

### Cleanup
```pseudo
client.close()
```

---

## RTL18, RTL18b, RTL18c, RTL20 - Recovery after last message ID mismatch

| Spec | Requirement |
|------|-------------|
| RTL18 | Decode failure triggers automatic recovery |
| RTL18b | The failed message is discarded |
| RTL18c | ATTACH sent with channelSerial, channel transitions to ATTACHING with error 40018 |
| RTL20 | Delta reference ID must match stored last message ID |

Tests that when the stored last message ID is cleared (simulating a gap), the next
delta message fails the RTL20 base reference check, triggering the RTL18 recovery
procedure. After recovery the channel reattaches and remaining messages are delivered.

**Note:** This test manipulates internal SDK state (the stored last message ID) to
simulate a message gap. The mechanism for doing this is implementation-specific.

### Setup
```pseudo
channel_name = "delta-recovery-mismatch-" + random_id()

decode_count = 0
counting_decoder = VCDiffDecoder(
  onDecode: (delta, base) => {
    decode_count++
  }
)

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false,
  plugins: { vcdiff: counting_decoder }
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

channel = client.channels.get(channel_name, options: ChannelOptions(
  params: { "delta": "vcdiff" }
))

AWAIT channel.attach()

received_messages = []
attaching_reasons = []

channel.on(ChannelEvent.attaching, (change) => {
  attaching_reasons.append(change.reason)
})

channel.subscribe((msg) => received_messages.append(msg))

# Publish first batch of messages and wait for them to arrive.
# Publishing in two batches ensures the server has sent and the client has
# processed the first batch before we clear the stored ID. If all messages
# were published at once, they could all arrive in a single ProtocolMessage
# before clearLastPayloadMessageId takes effect.
FOR i IN 0..2:
  AWAIT channel.publish(str(i), test_data[i])

WAIT UNTIL length(received_messages) >= 3
  WITH timeout: 15 seconds

# Simulate a message gap by clearing the stored last message ID.
# The next delta will fail the RTL20 check.
# (Implementation-specific: access internal _lastPayload.messageId or equivalent)
CLEAR channel._lastPayload.messageId

# Publish remaining messages — the server should send these as deltas,
# which will fail the RTL20 check and trigger recovery
FOR i IN 3..length(test_data) - 1:
  AWAIT channel.publish(str(i), test_data[i])

# Wait for all messages to be received — recovery will reattach and
# the server will resend from the channelSerial
WAIT UNTIL (unique message names in received_messages) covers all 0..length(test_data)-1
  WITH timeout: 30 seconds
```

### Assertions
```pseudo
# All messages were eventually received with correct data (may have duplicates
# from the server resending after recovery)
FOR i IN 0..length(test_data) - 1:
  msg = FIND received_messages WHERE name == str(i)
  ASSERT msg IS NOT null
  ASSERT msg.data == test_data[i]

# RTL18c: Recovery was triggered with error code 40018
ASSERT length(attaching_reasons) >= 1
ASSERT attaching_reasons[0].code == 40018
```

### Cleanup
```pseudo
client.close()
```

---

## RTL18, RTL18c - Recovery after decode failure

| Spec | Requirement |
|------|-------------|
| RTL18 | Decode failure triggers automatic recovery |
| RTL18c | ATTACH sent with channelSerial, channel transitions to ATTACHING with error 40018 |

Tests that when the vcdiff decoder throws an error, the channel transitions to
ATTACHING with error 40018 and recovers by reattaching. After recovery, remaining
messages are delivered (the server resends from the channelSerial as non-deltas
since the decode context is lost).

### Setup
```pseudo
channel_name = "delta-recovery-decode-" + random_id()

# Decoder that always fails
failing_decoder = FailingVCDiffDecoder()

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false,
  plugins: { vcdiff: failing_decoder }
))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

channel = client.channels.get(channel_name, options: ChannelOptions(
  params: { "delta": "vcdiff" }
))

AWAIT channel.attach()

received_messages = []
attaching_reasons = []

channel.on(ChannelEvent.attaching, (change) => {
  attaching_reasons.append(change.reason)
})

channel.subscribe((msg) => received_messages.append(msg))

FOR i IN 0..length(test_data) - 1:
  AWAIT channel.publish(str(i), test_data[i])

# Wait for all messages — first arrives as non-delta, second triggers decode
# failure and recovery, then remaining messages arrive after reattach
WAIT UNTIL length(received_messages) >= length(test_data)
  WITH timeout: 30 seconds
```

### Assertions
```pseudo
# All messages eventually received with correct data
FOR i IN 0..length(test_data) - 1:
  msg = FIND received_messages WHERE name == str(i)
  ASSERT msg IS NOT null
  ASSERT msg.data == test_data[i]

# RTL18c: At least one recovery was triggered
ASSERT length(attaching_reasons) >= 1
ASSERT attaching_reasons[0].code == 40018
```

### Cleanup
```pseudo
client.close()
```

---

## PC3 - No plugin causes FAILED state

**Spec requirement:** Without a vcdiff decoder plugin, vcdiff-encoded messages cannot
be decoded and the channel should transition to FAILED.

Tests that when a channel is configured for delta mode but no vcdiff plugin is
registered, receiving a delta-encoded message causes the channel to transition to
FAILED with error code 40019.

**Note:** This test uses a separate publisher client because the subscribing client's
channel transitions to FAILED when it receives a delta it cannot decode. If the same
client were used for both publishing and subscribing, subsequent `publish()` calls
would fail with a "channel is FAILED" error, and pending publish ACKs could also
fail. Using a separate publisher avoids these complications.

### Setup
```pseudo
channel_name = "delta-no-plugin-" + random_id()

# Subscriber — no vcdiff plugin, but requests delta channel param
subscriber = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

# Publisher — separate connection, publishes without delta param
publisher = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
```

### Test Steps
```pseudo
subscriber.connect()
publisher.connect()
AWAIT_STATE subscriber.connection.state == ConnectionState.connected
AWAIT_STATE publisher.connection.state == ConnectionState.connected

sub_channel = subscriber.channels.get(channel_name, options: ChannelOptions(
  params: { "delta": "vcdiff" }
))

AWAIT sub_channel.attach()

# Publisher uses a plain channel (no delta param)
pub_channel = publisher.channels.get(channel_name)
AWAIT pub_channel.attach()

# Publish enough messages to trigger delta encoding on subscriber
FOR i IN 0..length(test_data) - 1:
  AWAIT pub_channel.publish(str(i), test_data[i])

# Subscriber channel should transition to FAILED when it receives a delta
# it cannot decode (no vcdiff plugin registered)
WAIT UNTIL sub_channel.state == ChannelState.failed
  WITH timeout: 15 seconds
```

### Assertions
```pseudo
ASSERT sub_channel.state == ChannelState.failed
ASSERT sub_channel.errorReason.code == 40019
```

### Cleanup
```pseudo
subscriber.close()
publisher.close()
```
