# Pagination Integration Tests

Spec points: `TG1`, `TG2`, `TG3`, `TG4`, `TG5`

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

## TG1, TG2 - PaginatedResult items and navigation

Tests that `PaginatedResult` contains items and provides navigation methods.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
unique_channel = client.channels.get("pagination-basic-" + random_string())

# Publish enough messages to require pagination
FOR i IN 1..15:
  AWAIT unique_channel.publish(name: "event-" + str(i), data: str(i))

WAIT 2 seconds
```

### Test Steps
```pseudo
# Request with small limit to force pagination
page1 = AWAIT unique_channel.history(limit: 5)
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
unique_channel = client.channels.get("pagination-next-" + random_string())

# Publish messages
FOR i IN 1..12:
  AWAIT unique_channel.publish(name: "event-" + str(i), data: str(i))

WAIT 2 seconds
```

### Test Steps
```pseudo
page1 = AWAIT unique_channel.history(limit: 5)
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
unique_channel = client.channels.get("pagination-first-" + random_string())

FOR i IN 1..10:
  AWAIT unique_channel.publish(name: "event-" + str(i), data: str(i))

WAIT 2 seconds
```

### Test Steps
```pseudo
page1 = AWAIT unique_channel.history(limit: 3)
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
unique_channel = client.channels.get("pagination-iterate-" + random_string())

# Publish known set of messages
message_count = 25
FOR i IN 1..message_count:
  AWAIT unique_channel.publish(name: "event-" + str(i), data: str(i))

WAIT 2 seconds
```

### Test Steps
```pseudo
all_messages = []
page = AWAIT unique_channel.history(limit: 7)

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

## TG - next() on last page returns null or throws

Tests behavior when calling `next()` on the last page.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
unique_channel = client.channels.get("pagination-last-" + random_string())

# Publish small number of messages
AWAIT unique_channel.publish(name: "event1", data: "1")
AWAIT unique_channel.publish(name: "event2", data: "2")

WAIT 1 second
```

### Test Steps
```pseudo
page = AWAIT unique_channel.history(limit: 10)

ASSERT page.isLast() == true
ASSERT page.hasNext() == false
```

### Assertions
```pseudo
# Behavior on next() when on last page is implementation-defined
# Either returns null or throws - verify consistent behavior
result = AWAIT page.next()
ASSERT result IS null OR result.items.length == 0
```

---

## TG - Pagination with direction forwards

Tests that pagination works correctly with forwards direction.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
unique_channel = client.channels.get("pagination-forwards-" + random_string())

FOR i IN 1..10:
  AWAIT unique_channel.publish(name: "event-" + str(i), data: str(i))

WAIT 2 seconds
```

### Test Steps
```pseudo
page1 = AWAIT unique_channel.history(limit: 4, direction: "forwards")
page2 = AWAIT page1.next()
```

### Assertions
```pseudo
# Forwards: oldest first
ASSERT page1.items[0].name == "event-1"
ASSERT page1.items[3].name == "event-4"

# Second page continues from where first left off
ASSERT page2.items[0].name == "event-5"
```

---

## TG - hasPrevious and previous (if supported)

Tests `hasPrevious()` and `previous()` navigation (if supported by the library).

### Note
Previous page navigation may not be supported in all SDKs. This test should be skipped if the library doesn't implement previous navigation.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
unique_channel = client.channels.get("pagination-previous-" + random_string())

FOR i IN 1..10:
  AWAIT unique_channel.publish(name: "event-" + str(i), data: str(i))

WAIT 2 seconds
```

### Test Steps
```pseudo
page1 = AWAIT unique_channel.history(limit: 3)
page2 = AWAIT page1.next()

IF page2.hasPrevious IS defined AND page2.hasPrevious() == true:
  prev_page = AWAIT page2.previous()

  # prev_page should match page1
  ASSERT prev_page.items.length == page1.items.length
  FOR i IN 0..prev_page.items.length:
    ASSERT prev_page.items[i].id == page1.items[i].id
```
