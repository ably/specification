# RealtimeChannel History Integration Test

Spec points: `RTL10d`

## Test Type
Integration test against Ably Sandbox endpoint

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox-rest.ably.io`.

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

---

## RTL10d - History contains messages published by another client

| Spec | Requirement |
|------|-------------|
| RTL10d | A test should exist that publishes messages from one client, and upon confirmation of message delivery, a history request should be made on another client to ensure all messages are available |

Tests that messages published by one Realtime client are available in the history retrieved by a separate client.

### Setup

```pseudo
channel_name = "history-RTL10d-" + random_id()

publisher = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

subscriber = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

publisher.connect()
subscriber.connect()

AWAIT_STATE publisher.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
AWAIT_STATE subscriber.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds

pub_channel = publisher.channels.get(channel_name)
sub_channel = subscriber.channels.get(channel_name)

AWAIT pub_channel.attach()
AWAIT sub_channel.attach()
```

### Test Steps

```pseudo
# Publish messages from publisher client and await confirmation
AWAIT pub_channel.publish(name: "event1", data: "data1")
AWAIT pub_channel.publish(name: "event2", data: "data2")
AWAIT pub_channel.publish(name: "event3", data: "data3")

# Retrieve history from subscriber client
# Poll until all messages appear
history = poll_until(
  condition: FUNCTION() =>
    result = AWAIT sub_channel.history()
    RETURN result.items.length == 3,
  interval: 500ms,
  timeout: 10s
)
```

### Assertions

```pseudo
ASSERT history.items.length == 3

# Default order is backwards (newest first)
ASSERT history.items[0].name == "event3"
ASSERT history.items[0].data == "data3"

ASSERT history.items[1].name == "event2"
ASSERT history.items[1].data == "data2"

ASSERT history.items[2].name == "event1"
ASSERT history.items[2].data == "data1"
```

### Cleanup

```pseudo
AFTER TEST:
  publisher.close()
  subscriber.close()
```
