# MessagePack Interoperability Tests

Spec points: `RSL6a3`

## Test Type
Unit test — no server or mock needed. Operates on static fixture data.

## Fixtures
Tests use `ably-common/test-resources/msgpack_test_fixtures.json`.

Each fixture has:
- `name`: human-readable description
- `data`: the expected decoded data value
- `numRepeat`: if > 0, the expected data is `data` repeated `numRepeat` times
- `type`: one of `"string"`, `"binary"`, `"jsonArray"`, `"jsonObject"`
- `encoding`: the encoding field on the wire message (empty string means none)
- `msgpack`: base64-encoded msgpack bytes of an entire ProtocolMessage

The ProtocolMessage contains a single Message in its `messages` array. The `data`
field in the fixture describes the expected decoded content of that message.

---

## RSL6a3 - Decode binary-encoded protocol messages using interop fixtures

**Spec requirement:** A set of tests should exist to ensure that the client library
can successfully encode and decode binary encoded protocol messages.

### Setup
```pseudo
fixtures = load_json("ably-common/test-resources/msgpack_test_fixtures.json")
```

### Test: each fixture decodes correctly
```pseudo
FOR EACH fixture IN fixtures:
  # 1. Decode the msgpack ProtocolMessage
  msgpack_bytes = base64_decode(fixture["msgpack"])
  protocol_message = msgpack_deserialize(msgpack_bytes)

  # 2. Extract the first (only) message
  wire_message = protocol_message["messages"][0]

  # 3. Build the expected data
  IF fixture["type"] == "string":
    IF fixture["numRepeat"] > 0:
      expected = fixture["data"] * fixture["numRepeat"]  # repeat string
    ELSE:
      expected = fixture["data"]
    END
  ELSE IF fixture["type"] == "binary":
    raw_string = fixture["data"] * fixture["numRepeat"]
    expected = encode_utf8(raw_string)  # Uint8List / byte array
  ELSE IF fixture["type"] == "jsonArray" OR fixture["type"] == "jsonObject":
    expected = fixture["data"]  # native array or map
  END

  # 4. Decode the wire message using the standard decoding pipeline
  message = Message.fromMap(wire_message)

  # 5. Verify
  ASSERT message.data == expected
  ASSERT message.encoding IS null  # all encoding consumed
END
```

### Assertions per fixture type

**String fixtures** (`type == "string"`):
- `message.data` is a String equal to `fixture["data"]` repeated `fixture["numRepeat"]` times

**Binary fixtures** (`type == "binary"`):
- The wire message has `encoding: "base64"` and base64-encoded `data`
- After decoding, `message.data` is a byte array (Uint8List)
- The byte content equals the UTF-8 encoding of `fixture["data"]` repeated `fixture["numRepeat"]` times

**JSON fixtures** (`type == "jsonArray"` or `type == "jsonObject"`):
- The wire message has `encoding: "json"` and JSON-encoded `data`
- After decoding, `message.data` is a native List or Map matching `fixture["data"]`

---

## RSL6a3 - Re-encode decoded messages back to msgpack (round-trip)

### Test: each fixture round-trips through encode/decode
```pseudo
FOR EACH fixture IN fixtures:
  # 1. Decode the original
  msgpack_bytes = base64_decode(fixture["msgpack"])
  protocol_message = msgpack_deserialize(msgpack_bytes)
  wire_message = protocol_message["messages"][0]

  # 2. Decode to a Message
  message = Message.fromMap(wire_message)

  # 3. Re-encode the message for msgpack wire format
  re_encoded = message.toMap(useBinaryProtocol: true)

  # 4. Wrap in a ProtocolMessage and serialize
  re_pm = { "messages": [re_encoded], "msgSerial": 0 }
  re_bytes = msgpack_serialize(re_pm)

  # 5. Deserialize and decode again
  re_pm2 = msgpack_deserialize(re_bytes)
  re_message = Message.fromMap(re_pm2["messages"][0])

  # 6. Verify round-trip
  ASSERT re_message.data == message.data
  ASSERT re_message.encoding IS null
END
```
