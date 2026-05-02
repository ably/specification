# Realtime Channel Subscribe Integration Tests

Spec points: `RTL7`, `RTL7a`, `RTL7b`, `RTL7d`

## Test Type
Integration test against Ably sandbox

## Purpose

End-to-end verification that realtime message subscription delivers messages
correctly between connections. Complements the publish tests by verifying
subscribe-specific behavior: filtered subscriptions by message name, and
bidirectional message flow.

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

## RTL7a - Subscribe with no name filter receives all messages

| Spec | Requirement |
|------|-------------|
| RTL7a | Subscribe with a single listener argument subscribes to all messages |

**Spec requirement:** A subscriber with no name filter receives messages
regardless of their name.

### Setup
```pseudo
channel_name = "subscribe-all-" + random_id()

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
received = []
AWAIT sub_channel.subscribe((msg) => received.append(msg))
AWAIT pub_channel.attach()

AWAIT pub_channel.publish(name: "event-a", data: "data-a")
AWAIT pub_channel.publish(name: "event-b", data: "data-b")
AWAIT pub_channel.publish(name: "event-c", data: "data-c")

poll_until(
  condition: FUNCTION() => received.length >= 3,
  interval: 200ms,
  timeout: 10s
)
```

### Assertions
```pseudo
ASSERT received.length == 3

names = received.map(m => m.name)
ASSERT "event-a" IN names
ASSERT "event-b" IN names
ASSERT "event-c" IN names

CLOSE_CLIENT(publisher)
CLOSE_CLIENT(subscriber)
```

---

## RTL7b - Subscribe with name filter receives only matching messages

| Spec | Requirement |
|------|-------------|
| RTL7b | Subscribe with a name argument subscribes only to messages with that name |

**Spec requirement:** A subscriber with a name filter receives only messages
whose name matches the filter.

### Setup
```pseudo
channel_name = "subscribe-filtered-" + random_id()

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
# Subscribe only for "target" events
target_received = []
AWAIT sub_channel.subscribe(name: "target", (msg) => target_received.append(msg))

# Also subscribe to all events to know when publishing is complete
all_received = []
sub_channel.subscribe((msg) => all_received.append(msg))

AWAIT pub_channel.attach()

AWAIT pub_channel.publish(name: "other", data: "ignored")
AWAIT pub_channel.publish(name: "target", data: "wanted-1")
AWAIT pub_channel.publish(name: "other", data: "ignored")
AWAIT pub_channel.publish(name: "target", data: "wanted-2")

poll_until(
  condition: FUNCTION() => all_received.length >= 4,
  interval: 200ms,
  timeout: 10s
)
```

### Assertions
```pseudo
# All 4 messages arrived
ASSERT all_received.length == 4

# Filtered subscription received only "target" messages
ASSERT target_received.length == 2
ASSERT target_received[0].name == "target"
ASSERT target_received[0].data == "wanted-1"
ASSERT target_received[1].name == "target"
ASSERT target_received[1].data == "wanted-2"

CLOSE_CLIENT(publisher)
CLOSE_CLIENT(subscriber)
```

---

## RTL7 - Bidirectional message flow

| Spec | Requirement |
|------|-------------|
| RTL7 | RealtimeChannel#subscribe receives messages from any publisher on the channel |

**Spec requirement:** Two clients on the same channel can both publish and
subscribe. Messages from each client are received by the other.

### Setup
```pseudo
channel_name = "subscribe-bidir-" + random_id()

client_a = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false,
  clientId: "client-a"
))

client_b = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false,
  clientId: "client-b"
))

client_a.connect()
client_b.connect()
AWAIT_STATE client_a.connection.state == CONNECTED
AWAIT_STATE client_b.connection.state == CONNECTED

channel_a = client_a.channels.get(channel_name)
channel_b = client_b.channels.get(channel_name)
```

### Test Steps
```pseudo
received_by_a = []
received_by_b = []

AWAIT channel_a.subscribe((msg) => received_by_a.append(msg))
AWAIT channel_b.subscribe((msg) => received_by_b.append(msg))

# A publishes, B should receive
AWAIT channel_a.publish(name: "from-a", data: "hello from a")

# B publishes, A should receive
AWAIT channel_b.publish(name: "from-b", data: "hello from b")

poll_until(
  condition: FUNCTION() => received_by_a.length >= 2 AND received_by_b.length >= 2,
  interval: 200ms,
  timeout: 10s
)
```

### Assertions
```pseudo
# Both clients receive messages from both publishers (including their own echoes)
a_names = received_by_a.map(m => m.name)
b_names = received_by_b.map(m => m.name)

ASSERT "from-a" IN a_names
ASSERT "from-b" IN a_names
ASSERT "from-a" IN b_names
ASSERT "from-b" IN b_names

CLOSE_CLIENT(client_a)
CLOSE_CLIENT(client_b)
```
