# Mock VCDiff Infrastructure

This document specifies the mock VCDiff encoder and decoder for unit tests. Tests that need to encode or decode vcdiff deltas should reference this document.

## Purpose

The mock VCDiff infrastructure provides a deterministic, predictable encoding and decoding algorithm for testing delta compression functionality without a real vcdiff library. The algorithm is designed so that:

1. **Encoded deltas are inspectable** — the delta payload contains both the base and the new value in a human-readable format
2. **Decoding validates the base** — the decoder verifies that the base argument matches what was used during encoding, catching base payload storage bugs
3. **Round-trip is exact** — `decode(base, encode(base, value)) == value`

## Algorithm

### Encoding

The encoder takes a base payload and a new value, and produces a delta.

**String inputs:**
```pseudo
encode(base: String, value: String) -> String:
  return encode_uri_component(base) + "/" + encode_uri_component(value)
```

**Binary inputs:**
```pseudo
encode(base: byte[], value: byte[]) -> byte[]:
  return utf8_encode(base64url_encode(base) + "/" + base64url_encode(value))
```

### Decoding

The decoder takes a base payload and a delta, validates the base, and returns the original value.

**String inputs:**
```pseudo
decode(base: String, delta: String) -> String:
  parts = delta.split("/")
  IF length(parts) != 2:
    THROW "Invalid delta format"
  encoded_base = parts[0]
  encoded_value = parts[1]
  decoded_base = decode_uri_component(encoded_base)
  IF decoded_base != base:
    THROW "Base mismatch: expected base does not match delta"
  return decode_uri_component(encoded_value)
```

**Binary inputs:**
```pseudo
decode(base: byte[], delta: byte[]) -> byte[]:
  delta_string = utf8_decode(delta)
  parts = delta_string.split("/")
  IF length(parts) != 2:
    THROW "Invalid delta format"
  encoded_base = parts[0]
  encoded_value = parts[1]
  decoded_base = base64url_decode(encoded_base)
  IF decoded_base != base:
    THROW "Base mismatch: expected base does not match delta"
  return base64url_decode(encoded_value)
```

### Examples

**String round-trip:**
```pseudo
base = "hello world"
value = "goodbye world"

delta = encode(base, value)
# delta == "hello%20world/goodbye%20world"

result = decode(base, delta)
# result == "goodbye world"
```

**String with special characters:**
```pseudo
base = "msg/1"
value = "msg/2"

delta = encode(base, value)
# delta == "msg%2F1/msg%2F2"

result = decode(base, delta)
# result == "msg/2"
```

**Binary round-trip:**
```pseudo
base = [0x48, 0x65, 0x6C, 0x6C, 0x6F]   # "Hello" in UTF-8
value = [0x57, 0x6F, 0x72, 0x6C, 0x64]   # "World" in UTF-8

delta = encode(base, value)
# delta == utf8_encode("SGVsbG8/V29ybGQ")
#        == [0x53, 0x47, 0x56, 0x73, 0x62, 0x47, 0x38, 0x2F,
#            0x56, 0x32, 0x39, 0x79, 0x62, 0x47, 0x51]

result = decode(base, delta)
# result == [0x57, 0x6F, 0x72, 0x6C, 0x64]  # "World"
```

**Base mismatch (decode fails):**
```pseudo
base = "hello"
value = "world"
delta = encode(base, value)  # "hello/world"

wrong_base = "wrong"
decode(wrong_base, delta)  # THROWS "Base mismatch"
```

## Mock Interface

### MockVCDiffEncoder

```pseudo
interface MockVCDiffEncoder:
  encode(base: String, value: String) -> String
  encode(base: byte[], value: byte[]) -> byte[]
```

### MockVCDiffDecoder

The decoder implements the `VCDiffDecoder` interface specified in VD2a.

```pseudo
interface MockVCDiffDecoder:
  decode(delta: byte[], base: byte[]) -> byte[]
```

Note: The `VCDiffDecoder` interface (VD2) only specifies a binary API
(`decode(delta, base) -> byte[]`). The string overloads on the encoder and
decoder are a convenience for test setup — they allow tests to construct delta
payloads from string values without manually converting to binary. The SDK's
vcdiff plugin integration point uses the binary-only `VCDiffDecoder` interface.

### FailingMockVCDiffDecoder

For testing RTL18 decode failure recovery, a decoder that always throws:

```pseudo
interface FailingMockVCDiffDecoder:
  decode(delta: byte[], base: byte[]) -> byte[]:
    THROW "Simulated vcdiff decode failure"
```

## Usage in Tests

### Creating delta payloads for mock server messages

When the mock WebSocket server needs to send a delta-encoded MESSAGE, use the
encoder to construct the delta payload from known base and value strings:

```pseudo
encoder = MockVCDiffEncoder()

# First message (non-delta, establishes base payload)
base_data = "first message"

# Second message (delta, references first)
new_data = "second message"
delta_payload = encoder.encode(base_data, new_data)

# Server sends the delta message
mock_ws.send_to_client(ProtocolMessage(
  action: MESSAGE,
  channel: channel_name,
  messages: [
    {
      id: "msg-2",
      data: delta_payload,
      encoding: "vcdiff",
      extras: { delta: { from: "msg-1", format: "vcdiff" } }
    }
  ]
))
```

### Registering the decoder as a plugin

```pseudo
decoder = MockVCDiffDecoder()

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  plugins: { vcdiff: decoder }
))
```

### Testing decode failure recovery (RTL18)

```pseudo
failing_decoder = FailingMockVCDiffDecoder()

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  plugins: { vcdiff: failing_decoder }
))
```

## Notes on Base64URL

Base64URL encoding uses the URL-safe alphabet (`A-Z`, `a-z`, `0-9`, `-`, `_`)
with no padding (`=`). This is distinct from standard Base64 which uses `+` and
`/`. The URL-safe alphabet is used here because `/` is the separator character
in the delta format.
