# Realtime Channel Publish Integration Tests

Spec points: `RTL6`, `RTL6f`, `RSL4`, `RSL6`, `RSL6a2`

## Test Type
Integration test against Ably sandbox

## Purpose

End-to-end verification that messages published on one realtime connection are
received by a subscriber on a different connection with data integrity preserved.
Covers string, JSON object, and binary payloads to exercise the full encoding
pipeline (RSL4/RSL6), and verifies message metadata (RTL6f).

## Sandbox Setup

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox.realtime.ably-nonprod.net/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox.realtime.ably-nonprod.net/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

---

## RTL6, RSL4d2 - String data round-trip

| Spec | Requirement |
|------|-------------|
| RTL6 | RealtimeChannel#publish sends messages to Ably |
| RSL4d2 | A string message payload is represented as a JSON string |

**Spec requirement:** A string published on one connection is received with
identical data on a subscriber connection.

### Setup
```pseudo
channel_name = "publish-string-" + random_id()

publisher = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))

subscriber = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))

publisher.connect()
subscriber.connect()
AWAIT_STATE publisher.connection.state == CONNECTED
AWAIT_STATE subscriber.connection.state == CONNECTED

pub_channel = publisher.channels.get(channel_name)
sub_channel = subscriber.channels.get(channel_name)
```

### Test Steps
```pseudo
# Subscribe first, then publish
received = []
AWAIT sub_channel.subscribe((msg) => received.append(msg))
AWAIT pub_channel.attach()

AWAIT pub_channel.publish(name: "string-event", data: "hello world")

poll_until(
  condition: FUNCTION() => received.length >= 1,
  interval: 200ms,
  timeout: 10s
)
```

### Assertions
```pseudo
ASSERT received.length == 1
ASSERT received[0].name == "string-event"
ASSERT received[0].data == "hello world"
ASSERT received[0].data IS String

CLOSE_CLIENT(publisher)
CLOSE_CLIENT(subscriber)
```

---

## RTL6, RSL4d3 - JSON object data round-trip

| Spec | Requirement |
|------|-------------|
| RTL6 | RealtimeChannel#publish sends messages to Ably |
| RSL4d3 | A JSON message payload is stringified as a JSON Object or Array |

**Spec requirement:** A JSON object published on one connection is received as
an equivalent object on a subscriber connection.

### Setup
```pseudo
channel_name = "publish-json-" + random_id()

publisher = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))

subscriber = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))

publisher.connect()
subscriber.connect()
AWAIT_STATE publisher.connection.state == CONNECTED
AWAIT_STATE subscriber.connection.state == CONNECTED

pub_channel = publisher.channels.get(channel_name)
sub_channel = subscriber.channels.get(channel_name)
```

### Test Steps
```pseudo
json_data = {"key": "value", "nested": {"count": 42}, "list": [1, 2, 3]}

received = []
AWAIT sub_channel.subscribe((msg) => received.append(msg))
AWAIT pub_channel.attach()

AWAIT pub_channel.publish(name: "json-event", data: json_data)

poll_until(
  condition: FUNCTION() => received.length >= 1,
  interval: 200ms,
  timeout: 10s
)
```

### Assertions
```pseudo
ASSERT received.length == 1
ASSERT received[0].name == "json-event"
ASSERT received[0].data["key"] == "value"
ASSERT received[0].data["nested"]["count"] == 42
ASSERT received[0].data["list"] == [1, 2, 3]

CLOSE_CLIENT(publisher)
CLOSE_CLIENT(subscriber)
```

---

## RTL6, RSL4d1 - Binary data round-trip

| Spec | Requirement |
|------|-------------|
| RTL6 | RealtimeChannel#publish sends messages to Ably |
| RSL4d1 | A binary message payload is encoded as Base64 |
| RSL6a | Received messages are decoded automatically based on encoding field |

**Spec requirement:** A binary payload published on one connection is received as
an equivalent binary payload on a subscriber connection, with the encoding layer
handling Base64 encoding/decoding transparently.

### Setup
```pseudo
channel_name = "publish-binary-" + random_id()

publisher = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))

subscriber = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))

publisher.connect()
subscriber.connect()
AWAIT_STATE publisher.connection.state == CONNECTED
AWAIT_STATE subscriber.connection.state == CONNECTED

pub_channel = publisher.channels.get(channel_name)
sub_channel = subscriber.channels.get(channel_name)
```

### Test Steps
```pseudo
# Create a binary payload with known content
binary_data = byte_array([0, 1, 2, 255, 128, 64])

received = []
AWAIT sub_channel.subscribe((msg) => received.append(msg))
AWAIT pub_channel.attach()

AWAIT pub_channel.publish(name: "binary-event", data: binary_data)

poll_until(
  condition: FUNCTION() => received.length >= 1,
  interval: 200ms,
  timeout: 10s
)
```

### Assertions
```pseudo
ASSERT received.length == 1
ASSERT received[0].name == "binary-event"
ASSERT received[0].data IS Binary
ASSERT received[0].data == binary_data

CLOSE_CLIENT(publisher)
CLOSE_CLIENT(subscriber)
```

---

## RTL6f - connectionId matches publisher

| Spec | Requirement |
|------|-------------|
| RTL6f | Message#connectionId should match the current Connection#id for all published messages |

**Spec requirement:** The connectionId of received messages matches the
publisher's Connection#id.

### Setup
```pseudo
channel_name = "publish-connid-" + random_id()

publisher = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))

subscriber = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))

publisher.connect()
subscriber.connect()
AWAIT_STATE publisher.connection.state == CONNECTED
AWAIT_STATE subscriber.connection.state == CONNECTED

pub_channel = publisher.channels.get(channel_name)
sub_channel = subscriber.channels.get(channel_name)
```

### Test Steps
```pseudo
publisher_connection_id = publisher.connection.id

received = []
AWAIT sub_channel.subscribe((msg) => received.append(msg))
AWAIT pub_channel.attach()

AWAIT pub_channel.publish(name: "connid-test", data: "data")

poll_until(
  condition: FUNCTION() => received.length >= 1,
  interval: 200ms,
  timeout: 10s
)
```

### Assertions
```pseudo
ASSERT received[0].connectionId == publisher_connection_id
ASSERT received[0].connectionId != subscriber.connection.id

CLOSE_CLIENT(publisher)
CLOSE_CLIENT(subscriber)
```

---

## RSL6a2 - Message extras round-trip

| Spec | Requirement |
|------|-------------|
| RSL6a2 | Tests must exist to ensure interoperability for the extras field |

**Spec requirement:** A message published with an `extras` object is received
with an equivalent JSON-encodable object.

### Setup
```pseudo
channel_name = "pushenabled:publish-extras-" + random_id()

publisher = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))

subscriber = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))

publisher.connect()
subscriber.connect()
AWAIT_STATE publisher.connection.state == CONNECTED
AWAIT_STATE subscriber.connection.state == CONNECTED

pub_channel = publisher.channels.get(channel_name)
sub_channel = subscriber.channels.get(channel_name)
```

### Test Steps
```pseudo
extras = {"push": {"notification": {"title": "Testing"}}}

received = []
AWAIT sub_channel.subscribe((msg) => received.append(msg))
AWAIT pub_channel.attach()

AWAIT pub_channel.publish(Message(name: "extras-test", data: "payload", extras: extras))

poll_until(
  condition: FUNCTION() => received.length >= 1,
  interval: 200ms,
  timeout: 10s
)
```

### Assertions
```pseudo
ASSERT received[0].extras IS NOT NULL
ASSERT received[0].extras["push"]["notification"]["title"] == "Testing"

CLOSE_CLIENT(publisher)
CLOSE_CLIENT(subscriber)
```
