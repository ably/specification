# Pagination Integration Tests

Spec points: `TG1`, `TG2`, `TG3`, `TG4`, `TG5`

## Test Type
Integration test against Ably sandbox

## Test Environment

### Prerequisites
- Ably sandbox app provisioned via `POST https://sandbox.realtime.ably-nonprod.net/apps`
- API key from provisioned app
- Channel names must be unique per test (see README for naming convention)

### Setup Pattern
```pseudo
BEFORE ALL TESTS:
  app_config = provision_sandbox_app()
  app_id = app_config.app_id
  api_key = app_config.keys[0].key_str

AFTER ALL TESTS:
  DELETE https://sandbox.realtime.ably-nonprod.net/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

---

## TG1, TG2 - PaginatedResult items and navigation

Tests that `PaginatedResult` contains items and provides navigation methods.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
channel_name = "pagination-basic-" + random_id()
channel = client.channels.get(channel_name)

# Publish enough messages to require pagination
FOR i IN 1..15:
  AWAIT channel.publish(name: "event-" + str(i), data: str(i))

# Poll until all messages are persisted
poll_until(
  condition: FUNCTION() =>
    result = AWAIT channel.history()
    RETURN result.items.length == 15,
  interval: 500ms,
  timeout: 15s
)
```

### Test Steps
```pseudo
# Request with small limit to force pagination
page1 = AWAIT channel.history(limit: 5)
```

### Assertions
```pseudo
# TG1 - items contains array of results
ASSERT page1.items IS List
ASSERT page1.items.length == 5

# TG2 - hasNext/isLast indicate more pages
ASSERT page1.hasNext() == true
ASSERT page1.isLast() == false
```

---

## TG3 - next() retrieves subsequent page

Tests that `next()` retrieves the next page of results.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
channel_name = "pagination-next-" + random_id()
channel = client.channels.get(channel_name)

# Publish messages
FOR i IN 1..12:
  AWAIT channel.publish(name: "event-" + str(i), data: str(i))

# Poll until all messages are persisted
poll_until(
  condition: FUNCTION() =>
    result = AWAIT channel.history()
    RETURN result.items.length == 12,
  interval: 500ms,
  timeout: 15s
)
```

### Test Steps
```pseudo
page1 = AWAIT channel.history(limit: 5)
page2 = AWAIT page1.next()
page3 = AWAIT page2.next()
```

### Assertions
```pseudo
ASSERT page1.items.length == 5
ASSERT page2.items.length == 5
ASSERT page3.items.length == 2  # Remaining messages

# Verify no duplicate messages across pages
all_ids = []
FOR page IN [page1, page2, page3]:
  FOR item IN page.items:
    ASSERT item.id NOT IN all_ids
    all_ids.append(item.id)

ASSERT all_ids.length == 12
```

---

## TG4 - first() retrieves first page

Tests that `first()` returns to the first page of results.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
channel_name = "pagination-first-" + random_id()
channel = client.channels.get(channel_name)

FOR i IN 1..10:
  AWAIT channel.publish(name: "event-" + str(i), data: str(i))

# Poll until all messages are persisted
poll_until(
  condition: FUNCTION() =>
    result = AWAIT channel.history()
    RETURN result.items.length == 10,
  interval: 500ms,
  timeout: 15s
)
```

### Test Steps
```pseudo
page1 = AWAIT channel.history(limit: 3)
page2 = AWAIT page1.next()
first_page = AWAIT page2.first()
```

### Assertions
```pseudo
# first_page should have same items as page1
ASSERT first_page.items.length == page1.items.length

FOR i IN 0..first_page.items.length:
  ASSERT first_page.items[i].id == page1.items[i].id
```

---

## TG5 - Iterate through all pages

Tests iteration through entire result set using pagination.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
channel_name = "pagination-iterate-" + random_id()
channel = client.channels.get(channel_name)

# Publish known set of messages
message_count = 25
FOR i IN 1..message_count:
  AWAIT channel.publish(name: "event-" + str(i), data: str(i))

# Poll until all messages are persisted
poll_until(
  condition: FUNCTION() =>
    result = AWAIT channel.history()
    RETURN result.items.length == message_count,
  interval: 500ms,
  timeout: 30s
)
```

### Test Steps
```pseudo
all_messages = []
page = AWAIT channel.history(limit: 7)

WHILE true:
  all_messages.extend(page.items)

  IF NOT page.hasNext():
    BREAK

  page = AWAIT page.next()
```

### Assertions
```pseudo
ASSERT all_messages.length == message_count

# Verify all messages retrieved
event_names = [msg.name FOR msg IN all_messages]
FOR i IN 1..message_count:
  ASSERT "event-" + str(i) IN event_names
```

---

## TG - next() on last page returns null

Tests behavior when calling `next()` on the last page.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
channel_name = "pagination-lastnext-" + random_id()
channel = client.channels.get(channel_name)

# Publish just a few messages
FOR i IN 1..3:
  AWAIT channel.publish(name: "event-" + str(i), data: str(i))

# Poll until messages are persisted
poll_until(
  condition: FUNCTION() =>
    result = AWAIT channel.history()
    RETURN result.items.length == 3,
  interval: 500ms,
  timeout: 10s
)
```

### Test Steps
```pseudo
page = AWAIT channel.history(limit: 10)  # Larger than message count
```

### Assertions
```pseudo
ASSERT page.items.length == 3
ASSERT page.hasNext() == false
ASSERT page.isLast() == true

# Calling next() should return null (or empty result)
next_page = AWAIT page.next()
ASSERT next_page IS null OR next_page.items.length == 0
```
