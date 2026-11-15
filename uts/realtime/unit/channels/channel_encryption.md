# RealtimeChannel Encryption Tests

Spec points: `RSL5`, `RSL5a`, `RSL5b`, `RSL5c`, `RTL6a`, `RTL7d`, `RSL6a`, `RSL6b`, `TB2b`, `TB2b1`, `TB2b2`

## Test Type
Unit test with mocked WebSocket (and, for history, a mocked HTTP client)

## Mock WebSocket Infrastructure

See `uts/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification, and
`uts/rest/unit/helpers/mock_http.md` for the HTTP mock.

## Fixtures

RSL5c requires these tests to use the ably-common fixtures
[`test-resources/crypto-data-128.json`](https://github.com/ably/ably-common/blob/main/test-resources/crypto-data-128.json) and
[`test-resources/crypto-data-256.json`](https://github.com/ably/ably-common/blob/main/test-resources/crypto-data-256.json).
`load_fixtures(name)` reads one, with these fields:

| Field | Meaning |
|-------|---------|
| `algorithm`, `mode`, `keylength` | `aes`, `cbc`, and 128 or 256 |
| `key` | the key, base64 |
| `iv` | the initialization vector every item was encrypted with, base64 |
| `items[]` | the messages |
| `items[].encoded` | a message as the publisher passes it: `name`, `data`, and an `encoding` of `base64` (binary data) or `json` (a JSON object or array), or none (a string) |
| `items[].encrypted` | the same message on the wire over the JSON protocol: `name`, base64 ciphertext `data`, and `encoding` (e.g. `utf-8/cipher+aes-128-cbc/base64`) |
| `items[].msgpack` | the same message on the wire over MessagePack, base64 of its msgpack encoding: binary ciphertext `data` and `encoding` without the final `/base64` (e.g. `utf-8/cipher+aes-128-cbc`) |

Test harness helpers:

- **`fixture_data(fixture_message)`** — the `data` a publisher passes for an `items[].encoded` message: the string
  itself with no `encoding`, `base64_decode(data)` for `base64`, and `parse_json(data)` for `json`.
- **`fixture_cipher_params(fixture)`** — `Crypto.getDefaultParams(CipherParamOptions(key: fixture.key, algorithm:
  fixture.algorithm, mode: fixture.mode))`, with `set_fixed_iv(params, base64_decode(fixture.iv))` applied.
- **`set_fixed_iv(cipher_params, iv)`** — the test hook that makes an encryption deterministic. The features spec
  has the IV come from a secure random source for every message, and TZ2 lets `CipherParams` carry "anything necessary
  to implement the supported algorithms", so how a test fixes the IV is SDK-specific (e.g. an internal `iv` attribute).
  Encrypting the fixture items with the fixture's IV must reproduce the fixture's ciphertext exactly.

Every test runs over both fixtures, `crypto-data-128.json` and `crypto-data-256.json`, which covers RSL5b
(AES-128 and AES-256 CBC).

---

## RSL5c, RTL6a - Published messages are encrypted to the fixture data (JSON)

**Test ID**: `realtime/unit/RSL5c/publish-encrypts-fixtures-json-0`

| Spec | Requirement |
|------|-------------|
| RSL5a | With a `cipher` channel option, message payloads are encrypted when sent to Ably |
| RSL5b | AES 256 and 128 CBC encryption must be supported |
| RSL5c | Tests must exist that encrypt and decrypt the ably-common fixture data for AES 128 and AES 256 |
| RTL6a | Messages are encoded in the same way as the `RestChannel#publish` method |

Tests that publishing each fixture item on a channel with the fixture's cipher sends the fixture's `encrypted` data
and encoding over the JSON protocol.

### Setup
```pseudo
fixture_files = ["crypto-data-128.json", "crypto-data-256.json"]
```

### Test Steps and Assertions
```pseudo
FOR EACH fixture_file IN fixture_files:
  fixture = load_fixtures(fixture_file)
  channel_name = "test-RSL5c-json-${random_id()}"
  captured_messages = []

  mock_ws = MockWebSocket(
    onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
    onMessageFromClient: (msg) => {
      IF msg.action == ATTACH:
        mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
      ELSE IF msg.action == MESSAGE:
        captured_messages.append(msg.messages[0])
        mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
    }
  )
  install_mock(mock_ws)

  client = Realtime(options: ClientOptions(
    key: "appId.keyId:keySecret",
    autoConnect: false,
    useBinaryProtocol: false
  ))
  channel = client.channels.get(channel_name, RealtimeChannelOptions(
    cipher: fixture_cipher_params(fixture),
    attachOnSubscribe: false
  ))

  client.connect()
  AWAIT_STATE client.connection.state == ConnectionState.connected
  AWAIT channel.attach()

  FOR EACH item IN fixture.items:
    AWAIT channel.publish(name: item.encoded.name, data: fixture_data(item.encoded))

  ASSERT length(captured_messages) == length(fixture.items)
  FOR i IN 0..length(fixture.items) - 1:
    item = fixture.items[i]
    ASSERT captured_messages[i].name == item.encrypted.name
    ASSERT captured_messages[i].data == item.encrypted.data
    ASSERT captured_messages[i].encoding == item.encrypted.encoding

  CLOSE_CLIENT(client)
```

---

## RSL5c, RTL6a - Published messages are encrypted to the fixture data (MessagePack)

**Test ID**: `realtime/unit/RSL5c/publish-encrypts-fixtures-msgpack-1`

| Spec | Requirement |
|------|-------------|
| RSL5a | With a `cipher` channel option, message payloads are encrypted when sent to Ably |
| RSL5c | Tests must exist that encrypt and decrypt the ably-common fixture data for AES 128 and AES 256 |
| RSL4c | Over MessagePack, binary data is sent as is |

Tests that over MessagePack the ciphertext is sent as binary, with no final `base64` step in the encoding, matching
each item's `msgpack` form.

### Setup
```pseudo
fixture_files = ["crypto-data-128.json", "crypto-data-256.json"]
```

### Test Steps and Assertions
```pseudo
FOR EACH fixture_file IN fixture_files:
  fixture = load_fixtures(fixture_file)
  channel_name = "test-RSL5c-msgpack-${random_id()}"
  captured_messages = []

  mock_ws = MockWebSocket(
    onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
    onMessageFromClient: (msg) => {
      IF msg.action == ATTACH:
        mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
      ELSE IF msg.action == MESSAGE:
        mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
    },
    onBinaryDataFrame: (bytes) => {
      decoded = MSGPACK_DECODE(bytes)
      IF decoded["action"] == MESSAGE_ACTION_INT:
        captured_messages.append(decoded["messages"][0])
    }
  )
  install_mock(mock_ws)

  client = Realtime(options: ClientOptions(
    key: "appId.keyId:keySecret",
    autoConnect: false,
    useBinaryProtocol: true
  ))
  channel = client.channels.get(channel_name, RealtimeChannelOptions(
    cipher: fixture_cipher_params(fixture),
    attachOnSubscribe: false
  ))

  client.connect()
  AWAIT_STATE client.connection.state == ConnectionState.connected
  AWAIT channel.attach()

  FOR EACH item IN fixture.items:
    AWAIT channel.publish(name: item.encoded.name, data: fixture_data(item.encoded))

  ASSERT length(captured_messages) == length(fixture.items)
  FOR i IN 0..length(fixture.items) - 1:
    expected = MSGPACK_DECODE(base64_decode(fixture.items[i].msgpack))
    ASSERT captured_messages[i]["name"] == expected["name"]
    ASSERT captured_messages[i]["data"] IS Binary
    ASSERT captured_messages[i]["data"] == expected["data"]
    ASSERT captured_messages[i]["encoding"] == expected["encoding"]

  CLOSE_CLIENT(client)
```

---

## RSL5c, RTL7d - Received messages are decrypted from the fixture data (JSON)

**Test ID**: `realtime/unit/RTL7d/subscribe-decrypts-fixtures-json-0`

| Spec | Requirement |
|------|-------------|
| RSL5a | With a `cipher` channel option, message payloads are decrypted when received on the channel |
| RSL5c | Tests must exist that encrypt and decrypt the ably-common fixture data for AES 128 and AES 256 |
| RTL7d | Messages delivered are automatically decoded based on the `encoding` attribute; tests should exist to publish and subscribe to encoded messages using the RSL5c fixture data |

Tests that each fixture item's `encrypted` message, received over the JSON protocol, is delivered to a subscriber
with the publisher's original `data` and no remaining `encoding`.

### Setup
```pseudo
fixture_files = ["crypto-data-128.json", "crypto-data-256.json"]
```

### Test Steps and Assertions
```pseudo
FOR EACH fixture_file IN fixture_files:
  fixture = load_fixtures(fixture_file)
  channel_name = "test-RTL7d-json-${random_id()}"
  received_messages = []

  mock_ws = MockWebSocket(
    onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
    onMessageFromClient: (msg) => {
      IF msg.action == ATTACH:
        mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    }
  )
  install_mock(mock_ws)

  client = Realtime(options: ClientOptions(
    key: "appId.keyId:keySecret",
    autoConnect: false,
    useBinaryProtocol: false
  ))
  channel = client.channels.get(channel_name, RealtimeChannelOptions(
    cipher: fixture_cipher_params(fixture),
    attachOnSubscribe: false
  ))
  channel.subscribe((message) => received_messages.append(message))

  client.connect()
  AWAIT_STATE client.connection.state == ConnectionState.connected
  AWAIT channel.attach()

  FOR EACH item IN fixture.items:
    mock_ws.send_to_client(ProtocolMessage(
      action: MESSAGE,
      channel: channel_name,
      messages: [Message.fromJson(item.encrypted)]
    ))

  poll_until(() => length(received_messages) == length(fixture.items), timeout: 5 seconds)

  FOR i IN 0..length(fixture.items) - 1:
    item = fixture.items[i]
    ASSERT received_messages[i].name == item.encoded.name
    ASSERT received_messages[i].data == fixture_data(item.encoded)
    ASSERT received_messages[i].encoding == null

  CLOSE_CLIENT(client)
```

---

## RSL5c, RTL7d - Received messages are decrypted from the fixture data (MessagePack)

**Test ID**: `realtime/unit/RTL7d/subscribe-decrypts-fixtures-msgpack-1`

| Spec | Requirement |
|------|-------------|
| RSL5a | With a `cipher` channel option, message payloads are decrypted when received on the channel |
| RSL5c | Tests must exist that encrypt and decrypt the ably-common fixture data for AES 128 and AES 256 |
| RTL7d | Messages delivered are automatically decoded based on the `encoding` attribute |

Tests that each fixture item's `msgpack` message, with binary ciphertext, received over MessagePack is delivered with
the publisher's original `data`.

### Setup
```pseudo
fixture_files = ["crypto-data-128.json", "crypto-data-256.json"]
```

### Test Steps and Assertions
```pseudo
FOR EACH fixture_file IN fixture_files:
  fixture = load_fixtures(fixture_file)
  channel_name = "test-RTL7d-msgpack-${random_id()}"
  received_messages = []

  mock_ws = MockWebSocket(
    onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
    onMessageFromClient: (msg) => {
      IF msg.action == ATTACH:
        mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    }
  )
  install_mock(mock_ws)

  client = Realtime(options: ClientOptions(
    key: "appId.keyId:keySecret",
    autoConnect: false,
    useBinaryProtocol: true
  ))
  channel = client.channels.get(channel_name, RealtimeChannelOptions(
    cipher: fixture_cipher_params(fixture),
    attachOnSubscribe: false
  ))
  channel.subscribe((message) => received_messages.append(message))

  client.connect()
  AWAIT_STATE client.connection.state == ConnectionState.connected
  AWAIT channel.attach()

  FOR EACH item IN fixture.items:
    # The wire message as MessagePack carries it: binary ciphertext, encoding without the final base64
    wire_message = MSGPACK_DECODE(base64_decode(item.msgpack))
    mock_ws.send_to_client(ProtocolMessage(
      action: MESSAGE,
      channel: channel_name,
      messages: [Message.fromJson(wire_message)]
    ))

  poll_until(() => length(received_messages) == length(fixture.items), timeout: 5 seconds)

  FOR i IN 0..length(fixture.items) - 1:
    item = fixture.items[i]
    ASSERT received_messages[i].name == item.encoded.name
    ASSERT received_messages[i].data == fixture_data(item.encoded)
    ASSERT received_messages[i].encoding == null

  CLOSE_CLIENT(client)
```

---

## RSL6a - History messages are decrypted from the fixture data

**Test ID**: `realtime/unit/RSL6a/history-decrypts-fixtures-0`

| Spec | Requirement |
|------|-------------|
| RSL6a | All messages received will be decoded automatically based on the `encoding` field, applying the decryption rules of RSL5 |
| RSL5a | With a `cipher` channel option, message payloads are decrypted when received on the channel |
| RTL10 | `RealtimeChannel#history` returns messages from the REST history endpoint |

Tests that a history page of fixture `encrypted` messages is returned decrypted.

### Setup
```pseudo
fixture_files = ["crypto-data-128.json", "crypto-data-256.json"]
```

### Test Steps and Assertions
```pseudo
FOR EACH fixture_file IN fixture_files:
  fixture = load_fixtures(fixture_file)
  channel_name = "test-RSL6a-history-${random_id()}"

  mock_http = MockHttpClient(
    onConnectionAttempt: (conn) => conn.respond_with_success(),
    onRequest: (req) => {
      req.respond_with(200, fixture.items.map(item => item.encrypted), headers: {"Content-Type": "application/json"})
    }
  )
  install_mock(mock_http)

  client = Realtime(options: ClientOptions(
    key: "appId.keyId:keySecret",
    autoConnect: false,
    useBinaryProtocol: false
  ))
  channel = client.channels.get(channel_name, RealtimeChannelOptions(cipher: fixture_cipher_params(fixture)))

  result = AWAIT channel.history()

  ASSERT length(result.items) == length(fixture.items)
  FOR i IN 0..length(fixture.items) - 1:
    item = fixture.items[i]
    ASSERT result.items[i].name == item.encoded.name
    ASSERT result.items[i].data == fixture_data(item.encoded)
    ASSERT result.items[i].encoding == null

  CLOSE_CLIENT(client)
```

---

## RSL6b - An encrypted message is delivered still encrypted without a cipher

**Test ID**: `realtime/unit/RSL6b/no-cipher-delivers-encrypted-0`

**Spec requirement:** If, for example, incompatible encryption details are provided or invalid Base64 is detected in the message payload, an error message will be sent to the logger, but the message will still be delivered with last successful decoding and the `encoding` field. For example, if a message had a decoding of "utf-8/cipher+aes-128-cbc/base64", and the payload was successfully Base64 decoded but the payload could not be decrypted because the `CipherParam` details were not configured, the message would be delivered with the binary payload and an `encoding` of "utf-8/cipher+aes-128-cbc".

Tests that a channel with no `cipher` delivers an encrypted message with its base64 decoded and the rest of its
encoding kept, and logs an error.

### Setup
```pseudo
fixture = load_fixtures("crypto-data-256.json")
item = fixture.items[0]  # a string: encoding "utf-8/cipher+aes-256-cbc/base64"
channel_name = "test-RSL6b-${random_id()}"
received_messages = []
captured_log_messages = []

log_handler = FUNCTION(level, message):
  captured_log_messages.append({level: level, message: message})

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  useBinaryProtocol: false,
  logHandler: log_handler,
  logLevel: LOG_ERROR
))
channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))  # no cipher
channel.subscribe((message) => received_messages.append(message))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [Message.fromJson(item.encrypted)]
))

poll_until(() => length(received_messages) == 1, timeout: 5 seconds)
```

### Assertions
```pseudo
ASSERT received_messages[0].name == item.encrypted.name
ASSERT received_messages[0].data IS Binary
ASSERT received_messages[0].data == base64_decode(item.encrypted.data)
ASSERT received_messages[0].encoding == "utf-8/cipher+aes-256-cbc"

ASSERT captured_log_messages.any(m => m.level == LOG_ERROR) == true
CLOSE_CLIENT(client)
```

---

## TB2b2 - A CipherParamOptions cipher option is resolved with getDefaultParams

**Test ID**: `realtime/unit/TB2b2/cipher-param-options-0`

| Spec | Requirement |
|------|-------------|
| TB2b | `cipher` is either a `CipherParams` instance or a `CipherParamOptions` instance |
| TB2b2 | For a `CipherParamOptions` instance, the client library should call `getDefaultParams`, passing it the options hash, to obtain a `CipherParams` instance |

Tests that a channel whose `cipher` option is a `CipherParamOptions` holding only a base64 key encrypts what it
publishes with AES at that key's length, and decrypts it again when the server delivers it back.

The IV here is random (no test hook can reach the `CipherParams` the SDK derives), so the ciphertext is checked
by its shape and by the round trip rather than against the fixture.

### Setup
```pseudo
fixture = load_fixtures("crypto-data-256.json")
channel_name = "test-TB2b2-${random_id()}"
published_messages = []
received_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == MESSAGE:
      published_messages.append(msg.messages[0])
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
      # Deliver the published message back to the channel, as Ably would
      mock_ws.send_to_client(ProtocolMessage(action: MESSAGE, channel: channel_name, messages: msg.messages))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  useBinaryProtocol: false
))
channel = client.channels.get(channel_name, RealtimeChannelOptions(
  cipher: CipherParamOptions(key: fixture.key),  # base64 string; algorithm, mode and keyLength from the defaults
  attachOnSubscribe: false
))
channel.subscribe((message) => received_messages.append(message))
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

AWAIT channel.publish(name: "example", data: "The quick brown fox jumped over the lazy dog")
poll_until(() => length(received_messages) == 1, timeout: 5 seconds)
```

### Assertions
```pseudo
# Encrypted on the wire with AES-256-CBC: a 16-byte IV followed by whole 16-byte blocks
ASSERT published_messages[0].encoding == "utf-8/cipher+aes-256-cbc/base64"
ciphertext = base64_decode(published_messages[0].data)
ASSERT length(ciphertext) > 16
ASSERT length(ciphertext) % 16 == 0

# Decrypted again on delivery
ASSERT received_messages[0].data == "The quick brown fox jumped over the lazy dog"
ASSERT received_messages[0].encoding == null
CLOSE_CLIENT(client)
```
