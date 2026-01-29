# PaginatedResult Types Tests

Spec points: `TG1`, `TG2`, `TG3`, `TG4`

## Test Type
Unit test with mocked HTTP client

## Mock Configuration

### HTTP Client Mock
Returns responses with Link headers for pagination.

---

## TG1 - PaginatedResult items attribute

Tests that `PaginatedResult` contains an `items` array.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, [
  { "id": "item1", "name": "e1", "data": "d1" },
  { "id": "item2", "name": "e2", "data": "d2" }
])

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test")
```

### Test Steps
```pseudo
result = AWAIT channel.history()
```

### Assertions
```pseudo
ASSERT result.items IS List
ASSERT result.items.length == 2
ASSERT result.items[0].id == "item1"
ASSERT result.items[1].id == "item2"
```

---

## TG2 - hasNext() and isLast() methods

Tests that `PaginatedResult` provides correct navigation state.

### Setup (Has more pages)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200,
  body: [{ "id": "item1" }],
  headers: {
    "Link": "</channels/test/messages?cursor=next123>; rel=\"next\""
  }
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test")
```

### Test Steps
```pseudo
result = AWAIT channel.history()
```

### Assertions
```pseudo
ASSERT result.hasNext() == true
ASSERT result.isLast() == false
```

### Setup (No more pages)
```pseudo
mock_http.reset()
mock_http.queue_response(200,
  body: [{ "id": "item1" }],
  headers: {}  # No Link header for next
)
```

### Assertions (No more pages)
```pseudo
result = AWAIT channel.history()
ASSERT result.hasNext() == false
ASSERT result.isLast() == true
```

---

## TG3 - next() method

Tests that `next()` fetches the next page of results.

### Setup
```pseudo
mock_http = MockHttpClient()
# First page
mock_http.queue_response(200,
  body: [{ "id": "page1-item1" }, { "id": "page1-item2" }],
  headers: {
    "Link": "</channels/test/messages?cursor=abc123>; rel=\"next\""
  }
)
# Second page
mock_http.queue_response(200,
  body: [{ "id": "page2-item1" }],
  headers: {}  # Last page
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test")
```

### Test Steps
```pseudo
page1 = AWAIT channel.history()
page2 = AWAIT page1.next()
```

### Assertions
```pseudo
# First page
ASSERT page1.items.length == 2
ASSERT page1.items[0].id == "page1-item1"
ASSERT page1.hasNext() == true

# Second page
ASSERT page2.items.length == 1
ASSERT page2.items[0].id == "page2-item1"
ASSERT page2.hasNext() == false

# Verify next request used cursor from Link header
next_request = mock_http.captured_requests[1]
ASSERT "cursor" IN next_request.url.query_params
ASSERT next_request.url.query_params["cursor"] == "abc123"
```

---

## TG4 - first() method

Tests that `first()` returns to the first page.

### Setup
```pseudo
mock_http = MockHttpClient()
# Initial request
mock_http.queue_response(200,
  body: [{ "id": "item1" }],
  headers: {
    "Link": "</channels/test/messages?cursor=next>; rel=\"next\", </channels/test/messages>; rel=\"first\""
  }
)
# Next page
mock_http.queue_response(200,
  body: [{ "id": "item2" }],
  headers: {
    "Link": "</channels/test/messages>; rel=\"first\""
  }
)
# First page again
mock_http.queue_response(200,
  body: [{ "id": "item1" }],
  headers: {
    "Link": "</channels/test/messages?cursor=next>; rel=\"next\""
  }
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test")
```

### Test Steps
```pseudo
page1 = AWAIT channel.history()
page2 = AWAIT page1.next()
first_page = AWAIT page2.first()
```

### Assertions
```pseudo
ASSERT first_page.items[0].id == "item1"
```

---

## TG - Empty result

Tests that empty results are handled correctly.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200,
  body: [],
  headers: {}
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test")
```

### Test Steps
```pseudo
result = AWAIT channel.history()
```

### Assertions
```pseudo
ASSERT result.items IS List
ASSERT result.items.length == 0
ASSERT result.hasNext() == false
ASSERT result.isLast() == true
```

---

## TG - Link header parsing

Tests correct parsing of various Link header formats.

### Test Cases

| ID | Link Header | Expected hasNext | Expected cursor |
|----|-------------|------------------|-----------------|
| 1 | `</path?cursor=abc>; rel="next"` | true | `"abc"` |
| 2 | `</path?cursor=abc>; rel="next", </path>; rel="first"` | true | `"abc"` |
| 3 | `</path>; rel="first"` | false | (none) |
| 4 | (empty) | false | (none) |

### Setup
```pseudo
mock_http = MockHttpClient()

FOR EACH test_case IN test_cases:
  mock_http.reset()
  mock_http.queue_response(200,
    body: [{ "id": "item" }],
    headers: { "Link": test_case.link_header } IF test_case.link_header ELSE {}
  )

  client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
  result = AWAIT client.channels.get("test").history()

  ASSERT result.hasNext() == test_case.expected_hasNext
```

---

## TG - PaginatedResult type parameter

Tests that `PaginatedResult<T>` correctly types its items.

### Note
This is primarily a compile-time/type-system verification for strongly-typed languages.

### Test Steps
```pseudo
# History returns PaginatedResult<Message>
history_result = AWAIT channel.history()
ASSERT history_result.items[0] IS Message

# If the language supports generics, verify:
# PaginatedResult<Message> cannot be assigned to PaginatedResult<String>
```

---

## TG - next() on last page

Tests behavior when calling `next()` on the last page.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200,
  body: [{ "id": "item" }],
  headers: {}  # No next link
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test")
```

### Test Steps
```pseudo
result = AWAIT channel.history()
ASSERT result.isLast() == true

next_result = AWAIT result.next()
```

### Assertions
```pseudo
# Implementation may either:
# 1. Return null
# 2. Return empty PaginatedResult
# 3. Throw an exception

ASSERT next_result IS null OR next_result.items.length == 0
```
