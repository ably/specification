# REST Channel History Integration Tests

Spec points: `RSL2a`, `RSL2b`, `RSL2b1`, `RSL2b2`, `RSL2b3`

## Test Type
Integration test against Ably sandbox

## Test Environment

### Prerequisites
- Ably sandbox app provisioned via `POST https://sandbox.realtime.ably-nonprod.net/apps`
- API key from provisioned app

### Setup Pattern
```pseudo
BEFORE ALL TESTS:
  app_config = provision_sandbox_app()
  api_key = app_config.keys[0].key_str

AFTER ALL TESTS:
  # Sandbox apps auto-delete after 60 minutes
```

---

## RSL2a - History returns published messages

Tests that published messages appear in channel history.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
unique_channel = client.channels.get("history-test-" + random_string())
```

### Test Steps
```pseudo
# Publish some messages
AWAIT unique_channel.publish(name: "event1", data: "data1")
AWAIT unique_channel.publish(name: "event2", data: "data2")
AWAIT unique_channel.publish(name: "event3", data: { "key": "value" })

# Wait for persistence
WAIT 1 second

# Retrieve history
history = AWAIT unique_channel.history()
```

### Assertions
```pseudo
ASSERT history.items.length == 3

# Default order is backwards (newest first)
ASSERT history.items[0].name == "event3"
ASSERT history.items[0].data == { "key": "value" }

ASSERT history.items[1].name == "event2"
ASSERT history.items[1].data == "data2"

ASSERT history.items[2].name == "event1"
ASSERT history.items[2].data == "data1"

# All messages should have timestamps
ASSERT ALL msg IN history.items: msg.timestamp IS NOT null
```

---

## RSL2b1 - History direction forwards

Tests that `direction: forwards` returns messages oldest-first.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
unique_channel = client.channels.get("history-direction-" + random_string())
```

### Test Steps
```pseudo
# Publish with small delays to ensure ordering
AWAIT unique_channel.publish(name: "first", data: "1")
WAIT 100 milliseconds
AWAIT unique_channel.publish(name: "second", data: "2")
WAIT 100 milliseconds
AWAIT unique_channel.publish(name: "third", data: "3")

WAIT 1 second

history = AWAIT unique_channel.history(direction: "forwards")
```

### Assertions
```pseudo
ASSERT history.items.length == 3
ASSERT history.items[0].name == "first"
ASSERT history.items[1].name == "second"
ASSERT history.items[2].name == "third"
```

---

## RSL2b2 - History limit parameter

Tests that `limit` parameter restricts number of returned messages.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
unique_channel = client.channels.get("history-limit-" + random_string())
```

### Test Steps
```pseudo
# Publish multiple messages
FOR i IN 1..10:
  AWAIT unique_channel.publish(name: "event-" + str(i), data: str(i))

WAIT 1 second

history = AWAIT unique_channel.history(limit: 5)
```

### Assertions
```pseudo
ASSERT history.items.length == 5

# Should get the 5 most recent (backwards direction by default)
ASSERT history.items[0].name == "event-10"
ASSERT history.items[4].name == "event-6"
```

---

## RSL2b - History time range

Tests that `start` and `end` parameters filter by time.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
unique_channel = client.channels.get("history-time-" + random_string())
```

### Test Steps
```pseudo
# Publish first batch
AWAIT unique_channel.publish(name: "before", data: "before-range")

start_time = now()
WAIT 500 milliseconds

# Publish middle batch
AWAIT unique_channel.publish(name: "during-1", data: "in-range-1")
AWAIT unique_channel.publish(name: "during-2", data: "in-range-2")

WAIT 500 milliseconds
end_time = now()

# Publish last batch
AWAIT unique_channel.publish(name: "after", data: "after-range")

WAIT 1 second

history = AWAIT unique_channel.history(
  start: start_time,
  end: end_time
)
```

### Assertions
```pseudo
ASSERT history.items.length == 2
names = [msg.name FOR msg IN history.items]
ASSERT "during-1" IN names
ASSERT "during-2" IN names
ASSERT "before" NOT IN names
ASSERT "after" NOT IN names
```

---

## RSL2 - History with binary data

Tests that binary data is correctly stored and retrieved.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
unique_channel = client.channels.get("history-binary-" + random_string())
```

### Test Steps
```pseudo
binary_data = bytes([0x00, 0x01, 0x02, 0xFF, 0xFE, 0xFD])

AWAIT unique_channel.publish(name: "binary-event", data: binary_data)

WAIT 1 second

history = AWAIT unique_channel.history()
```

### Assertions
```pseudo
ASSERT history.items.length == 1
ASSERT history.items[0].data == bytes([0x00, 0x01, 0x02, 0xFF, 0xFE, 0xFD])
```

---

## RSL2 - History with JSON object data

Tests that JSON objects are correctly stored and retrieved.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
unique_channel = client.channels.get("history-json-" + random_string())
```

### Test Steps
```pseudo
json_data = {
  "string": "value",
  "number": 42,
  "boolean": true,
  "null": null,
  "array": [1, 2, 3],
  "nested": { "a": "b" }
}

AWAIT unique_channel.publish(name: "json-event", data: json_data)

WAIT 1 second

history = AWAIT unique_channel.history()
```

### Assertions
```pseudo
ASSERT history.items.length == 1
ASSERT history.items[0].data == json_data
```

---

## RSL2 - Empty history

Tests that history returns empty result for channel with no messages.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
unique_channel = client.channels.get("history-empty-" + random_string())
```

### Test Steps
```pseudo
history = AWAIT unique_channel.history()
```

### Assertions
```pseudo
ASSERT history.items IS List
ASSERT history.items.length == 0
ASSERT history.hasNext() == false
```
