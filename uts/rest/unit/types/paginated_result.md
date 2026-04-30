# PaginatedResult Types Tests

Spec points: `TG1`, `TG2`, `TG3`, `TG4`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

These tests use the mock HTTP infrastructure described in `/Users/paddy/data/worknew/dev/dart-experiments/uts/test/rest/unit/rest_client.md`.

The mock supports:
- Intercepting HTTP requests and capturing details (URL, headers, method, body)
- Queueing responses with configurable status, headers, and body
- Handler-based configuration with `onConnectionAttempt` and `onRequest`
- Recording requests in `captured_requests` arrays
- Request counting with `request_count` variables

---

## TG1 - PaginatedResult items attribute

**Spec requirement:** `PaginatedResult` must contain an `items` array with the result data.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      { "id": "item1", "name": "e1", "data": "d1" },
      { "id": "item2", "name": "e2", "data": "d2" }
    ])
  }
)
install_mock(mock_http)

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

**Spec requirement:** `PaginatedResult` must provide `hasNext()` and `isLast()` methods to indicate pagination state.

### Test Case 1: Has more pages

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200,
      body: [{ "id": "item1" }],
      headers: {
        "Link": "</channels/test/messages?cursor=next123>; rel=\"next\""
      }
    )
  }
)
install_mock(mock_http)

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

---

### Test Case 2: No more pages

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200,
      body: [{ "id": "item1" }],
      headers: {}  # No Link header for next
    )
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test")
```

### Test Steps
```pseudo
result = AWAIT channel.history()
```

### Assertions
```pseudo
ASSERT result.hasNext() == false
ASSERT result.isLast() == true
```

---

## TG3 - next() method

**Spec requirement:** The `next()` method must fetch the next page using the URL from the Link header.

### Setup
```pseudo
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    request_count++
    
    IF request_count == 1:
      # First page
      req.respond_with(200,
        body: [{ "id": "page1-item1" }, { "id": "page1-item2" }],
        headers: {
          "Link": "</channels/test/messages?cursor=abc123>; rel=\"next\""
        }
      )
    ELSE:
      # Second page
      req.respond_with(200,
        body: [{ "id": "page2-item1" }],
        headers: {}  # Last page
      )
  }
)
install_mock(mock_http)

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
next_request = captured_requests[1]
ASSERT "cursor" IN next_request.url.query_params
ASSERT next_request.url.query_params["cursor"] == "abc123"
```

---

## TG4 - first() method

**Spec requirement:** The `first()` method must return to the first page using the URL from the Link header's `rel="first"` link.

### Setup
```pseudo
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    request_count++
    
    IF request_count == 1:
      # Initial request
      req.respond_with(200,
        body: [{ "id": "item1" }],
        headers: {
          "Link": "</channels/test/messages?cursor=next>; rel=\"next\", </channels/test/messages>; rel=\"first\""
        }
      )
    ELSE IF request_count == 2:
      # Next page
      req.respond_with(200,
        body: [{ "id": "item2" }],
        headers: {
          "Link": "</channels/test/messages>; rel=\"first\""
        }
      )
    ELSE:
      # First page again
      req.respond_with(200,
        body: [{ "id": "item1" }],
        headers: {
          "Link": "</channels/test/messages?cursor=next>; rel=\"next\""
        }
      )
  }
)
install_mock(mock_http)

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

**Spec requirement:** Empty results must be handled correctly with an empty `items` array.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200,
      body: [],
      headers: {}
    )
  }
)
install_mock(mock_http)

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

**Spec requirement:** Various Link header formats must be correctly parsed to determine pagination state and next page URLs.

### Test Cases

| ID | Link Header | Expected hasNext | Expected cursor |
|----|-------------|------------------|-----------------|
| 1 | `</path?cursor=abc>; rel="next"` | true | `"abc"` |
| 2 | `</path?cursor=abc>; rel="next", </path>; rel="first"` | true | `"abc"` |
| 3 | `</path>; rel="first"` | false | (none) |
| 4 | (empty) | false | (none) |

### Setup and Execution
```pseudo
FOR EACH test_case IN test_cases:
  captured_requests = []
  
  mock_http = MockHttpClient(
    onConnectionAttempt: (conn) => conn.respond_with_success(),
    onRequest: (req) => {
      captured_requests.push(req)
      
      IF test_case.link_header IS NOT empty:
        req.respond_with(200,
          body: [{ "id": "item" }],
          headers: { "Link": test_case.link_header }
        )
      ELSE:
        req.respond_with(200,
          body: [{ "id": "item" }],
          headers: {}
        )
    }
  )
  install_mock(mock_http)

  client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
  result = AWAIT client.channels.get("test").history()

  ASSERT result.hasNext() == test_case.expected_hasNext
```

---

## TG - PaginatedResult type parameter

**Spec requirement:** `PaginatedResult<T>` must correctly type its items to the expected type `T`.

### Note
This is primarily a compile-time/type-system verification for strongly-typed languages.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      { "id": "msg1", "name": "event", "data": "test" }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test")
```

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

**Spec requirement:** Calling `next()` on the last page must handle gracefully (return null, empty result, or throw).

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200,
      body: [{ "id": "item" }],
      headers: {}  # No next link
    )
  }
)
install_mock(mock_http)

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

---

## TG - Pagination preserves authentication

**Spec requirement:** Pagination requests must include the same authentication credentials as the initial request.

### Setup
```pseudo
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    request_count++
    
    IF request_count == 1:
      req.respond_with(200,
        body: [{ "id": "item1" }],
        headers: {
          "Link": "</channels/test/messages?cursor=next>; rel=\"next\""
        }
      )
    ELSE:
      req.respond_with(200, body: [{ "id": "item2" }])
  }
)
install_mock(mock_http)

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
# Both requests should have Authorization header
ASSERT "Authorization" IN captured_requests[0].headers
ASSERT "Authorization" IN captured_requests[1].headers
ASSERT captured_requests[0].headers["Authorization"] == captured_requests[1].headers["Authorization"]
```

---

## TG - Pagination with relative URLs

**Spec requirement:** Link headers with relative URLs must be resolved relative to the base REST host.

### Setup
```pseudo
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    request_count++
    
    IF request_count == 1:
      req.respond_with(200,
        body: [{ "id": "item1" }],
        headers: {
          "Link": "</channels/test/messages?page=2>; rel=\"next\""
        }
      )
    ELSE:
      req.respond_with(200, body: [{ "id": "item2" }])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  restHost: "rest.ably.io"
))
channel = client.channels.get("test")
```

### Test Steps
```pseudo
page1 = AWAIT channel.history()
page2 = AWAIT page1.next()
```

### Assertions
```pseudo
# Second request should use full URL
ASSERT captured_requests[1].url.host == "rest.ably.io"
ASSERT captured_requests[1].url.path == "/channels/test/messages"
ASSERT "page" IN captured_requests[1].url.query_params
```

---

## TG - Multiple Link relations

**Spec requirement:** Link headers may contain multiple relations (next, first, last) which must all be parsed correctly.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200,
      body: [{ "id": "item1" }],
      headers: {
        "Link": "</channels/test/messages?page=2>; rel=\"next\", </channels/test/messages?page=1>; rel=\"first\", </channels/test/messages?page=5>; rel=\"last\""
      }
    )
  }
)
install_mock(mock_http)

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
# Implementation should be able to navigate to next, first, or last pages
```

---

## TG - Pagination with presence results

**Spec requirement:** Pagination must work identically for presence results as it does for message results.

### Setup
```pseudo
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    request_count++
    
    IF request_count == 1:
      req.respond_with(200,
        body: [{ "action": 1, "clientId": "client1" }],
        headers: {
          "Link": "</channels/test/presence?page=2>; rel=\"next\""
        }
      )
    ELSE:
      req.respond_with(200, body: [{ "action": 1, "clientId": "client2" }])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test")
```

### Test Steps
```pseudo
page1 = AWAIT channel.presence.get()
page2 = AWAIT page1.next()
```

### Assertions
```pseudo
ASSERT page1 IS PaginatedResult<PresenceMessage>
ASSERT page1.items[0].clientId == "client1"
ASSERT page2.items[0].clientId == "client2"
```

---

## TG - Pagination includes request headers

**Spec requirement:** Pagination requests must include all standard Ably headers (X-Ably-Version, Ably-Agent, etc.).

### Setup
```pseudo
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    request_count++
    
    IF request_count == 1:
      req.respond_with(200,
        body: [{ "id": "item1" }],
        headers: {
          "Link": "</channels/test/messages?cursor=next>; rel=\"next\""
        }
      )
    ELSE:
      req.respond_with(200, body: [{ "id": "item2" }])
  }
)
install_mock(mock_http)

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
# Check headers on pagination request
next_request = captured_requests[1]
ASSERT "X-Ably-Version" IN next_request.headers
ASSERT "Ably-Agent" IN next_request.headers
ASSERT next_request.headers["Ably-Agent"] contains "ably-"
```

---

## TG - Error handling on next()

**Spec requirement:** Errors during pagination (e.g., 404, 500) must be raised as `AblyException`.

### Setup
```pseudo
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    request_count++
    
    IF request_count == 1:
      req.respond_with(200,
        body: [{ "id": "item1" }],
        headers: {
          "Link": "</channels/test/messages?cursor=invalid>; rel=\"next\""
        }
      )
    ELSE:
      req.respond_with(404, {
        "error": {
          "code": 40400,
          "statusCode": 404,
          "message": "Not found"
        }
      })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get("test")
```

### Test Steps
```pseudo
page1 = AWAIT channel.history()

AWAIT page1.next() FAILS WITH error
ASSERT error.statusCode == 404
ASSERT error.code == 40400
```
