# REST Channel History Integration Tests

Spec points: `RSL2a`, `RSL2b`, `RSL2b1`, `RSL2b2`, `RSL2b3`

## Test Type
Integration test against Ably sandbox

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

## RSL2a - History returns published messages

**Spec requirement:** RSL2a - `history` returns a `PaginatedResult` containing messages for the channel.

Tests that published messages appear in channel history.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
channel_name = "history-test-RSL2a-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Publish some messages
AWAIT channel.publish(name: "event1", data: "data1")
AWAIT channel.publish(name: "event2", data: "data2")
AWAIT channel.publish(name: "event3", data: { "key": "value" })

# Poll until messages appear in history
history = poll_until(
  condition: FUNCTION() =>
    result = AWAIT channel.history()
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

**Spec requirement:** RSL2b1 - `direction` param controls message ordering (forwards = oldest first).

Tests that `direction: forwards` returns messages oldest-first.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
channel_name = "history-direction-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Publish messages - ordering is determined by server timestamp
AWAIT channel.publish(name: "first", data: "1")
AWAIT channel.publish(name: "second", data: "2")
AWAIT channel.publish(name: "third", data: "3")

# Poll until all messages appear
poll_until(
  condition: FUNCTION() =>
    result = AWAIT channel.history()
    RETURN result.items.length == 3,
  interval: 500ms,
  timeout: 10s
)

history = AWAIT channel.history(direction: "forwards")
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

**Spec requirement:** RSL2b2 - `limit` param restricts the number of messages returned.

Tests that `limit` parameter restricts number of returned messages.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
channel_name = "history-limit-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Publish multiple messages
FOR i IN 1..10:
  AWAIT channel.publish(name: "event-" + str(i), data: str(i))

# Poll until all messages are persisted
poll_until(
  condition: FUNCTION() =>
    result = AWAIT channel.history()
    RETURN result.items.length == 10,
  interval: 500ms,
  timeout: 10s
)

history = AWAIT channel.history(limit: 5)
```

### Assertions
```pseudo
ASSERT history.items.length == 5

# Should get the 5 most recent (backwards direction by default)
ASSERT history.items[0].name == "event-10"
ASSERT history.items[4].name == "event-6"
```

---

## RSL2b3 - History time range parameters

**Spec requirement:** RSL2b3 - `start` and `end` params filter messages by timestamp range.

Tests that `start` and `end` parameters filter messages by time.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
channel_name = "history-timerange-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Publish early messages
AWAIT channel.publish(name: "early1", data: "e1")
AWAIT channel.publish(name: "early2", data: "e2")

# Small delay to help ensure server assigns distinct timestamps between batches
WAIT 2ms

# Publish late messages
AWAIT channel.publish(name: "late1", data: "l1")
AWAIT channel.publish(name: "late2", data: "l2")

# Poll until all messages appear and retrieve with server timestamps
all_messages = poll_until(
  condition: FUNCTION() =>
    result = AWAIT channel.history()
    RETURN result.items IF result.items.length == 4 ELSE null,
  interval: 500ms,
  timeout: 10s
)

# Use server-assigned timestamps to define the time boundary.
# Client-side now() must not be used here — client and server clocks may
# differ, and publishes may complete within the same client-clock millisecond.
early_timestamps = all_messages.filter(m => m.name STARTS WITH "early").map(m => m.timestamp)
late_timestamps  = all_messages.filter(m => m.name STARTS WITH "late").map(m => m.timestamp)

max_early_ts = max(early_timestamps)
min_late_ts  = min(late_timestamps)
time_boundary = floor((max_early_ts + min_late_ts) / 2)

# Query only early messages (up to the boundary)
early_history = AWAIT channel.history(
  start: max_early_ts - 1000,
  end: time_boundary
)

# Query only late messages (from the boundary onwards)
late_history = AWAIT channel.history(
  start: time_boundary + 1,
  end: min_late_ts + 1000
)
```

### Assertions
```pseudo
ASSERT early_history.items.length >= 1
ASSERT late_history.items.length >= 1

# Early messages should contain "early" names
ASSERT ANY msg IN early_history.items: msg.name STARTS WITH "early"

# Late messages should contain "late" names
ASSERT ANY msg IN late_history.items: msg.name STARTS WITH "late"
```

---

## RSL2 - History on channel with no messages

**Spec requirement:** RSL2a - `history` returns empty `PaginatedResult` when channel has no messages.

Tests that history on an empty channel returns empty result.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
# Use a fresh channel with no messages
channel_name = "history-empty-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
history = AWAIT channel.history()
```

### Assertions
```pseudo
ASSERT history.items IS List
ASSERT history.items.length == 0
ASSERT history.hasNext() == false
ASSERT history.isLast() == true
```
