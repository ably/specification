# Stats API Tests

Spec points: `RSC6`

## Test Type
Unit test with mocked HTTP

## Purpose

Tests the `stats()` method which retrieves application statistics from Ably. The stats endpoint requires authentication and returns paginated results.

---

## RSC6a - stats() returns paginated results

Tests that `stats()` returns a PaginatedResult of Stats objects.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "app.key:secret"),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response(200, [
  {
    "intervalId": "2024-01-01:00:00",
    "unit": "hour",
    "all": {
      "messages": {"count": 100, "data": 5000},
      "all": {"count": 100, "data": 5000}
    }
  },
  {
    "intervalId": "2024-01-01:01:00",
    "unit": "hour",
    "all": {
      "messages": {"count": 150, "data": 7500},
      "all": {"count": 150, "data": 7500}
    }
  }
])

result = AWAIT client.stats()
```

### Assertions
```pseudo
# Result should be a PaginatedResult
ASSERT result IS PaginatedResult
ASSERT result.items.length == 2

# First stats object
ASSERT result.items[0].intervalId == "2024-01-01:00:00"
ASSERT result.items[0].unit == "hour"

# Verify correct endpoint was called
request = mock_http.captured_requests[0]
ASSERT request.method == "GET"
ASSERT request.path == "/stats"
```

---

## RSC6a - stats() requires authentication

Tests that stats() requires authentication.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "app.key:secret"),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response(200, [])
AWAIT client.stats()
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]

# Request should have Authorization header
ASSERT "Authorization" IN request.headers
```

---

## RSC6b1 - stats() with start parameter

Tests that the `start` parameter filters stats by start time.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "app.key:secret"),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response(200, [])

start_time = DateTime(2024, 1, 1, 0, 0, 0)
AWAIT client.stats(start: start_time)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT request.query_params["start"] == str(start_time.millisecondsSinceEpoch)
```

---

## RSC6b1 - stats() with end parameter

Tests that the `end` parameter filters stats by end time.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "app.key:secret"),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response(200, [])

end_time = DateTime(2024, 1, 31, 23, 59, 59)
AWAIT client.stats(end: end_time)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT request.query_params["end"] == str(end_time.millisecondsSinceEpoch)
```

---

## RSC6b2 - stats() with limit parameter

Tests that the `limit` parameter restricts the number of results.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "app.key:secret"),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response(200, [])
AWAIT client.stats(limit: 10)
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT request.query_params["limit"] == "10"
```

---

## RSC6b3 - stats() with direction parameter

Tests that the `direction` parameter controls result ordering.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "app.key:secret"),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response(200, [])

# Test forwards direction
AWAIT client.stats(direction: "forwards")
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT request.query_params["direction"] == "forwards"
```

---

## RSC6b4 - stats() with unit parameter

Tests that the `unit` parameter specifies the stats granularity.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "app.key:secret"),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response(200, [])

# Valid units: minute, hour, day, month
AWAIT client.stats(unit: "day")
```

### Assertions
```pseudo
request = mock_http.captured_requests[0]
ASSERT request.query_params["unit"] == "day"
```

---

## RSC6a - stats() pagination navigation

Tests that stats results support pagination navigation.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "app.key:secret"),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
# First page with Link header for next page
mock_http.queue_response(200, [
  {"intervalId": "2024-01-01:00:00", "unit": "hour"}
], headers: {
  "link": '</stats?start=...&limit=1>; rel="next"'
})

page1 = AWAIT client.stats(limit: 1)
```

### Assertions
```pseudo
ASSERT page1.items.length == 1
ASSERT page1.hasNext() == true

# Can navigate to next page
# (actual navigation tested in pagination tests)
```

---

## RSC6a - stats() empty results

Tests that stats() handles empty results correctly.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "app.key:secret"),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response(200, [])
result = AWAIT client.stats()
```

### Assertions
```pseudo
ASSERT result.items IS List
ASSERT result.items.length == 0
ASSERT result.hasNext() == false
ASSERT result.isLast() == true
```

---

## RSC6a - stats() error handling

Tests that errors from the stats endpoint are properly propagated.

### Setup
```pseudo
mock_http = MockHttpClient()

client = Rest(
  options: ClientOptions(key: "app.key:secret"),
  httpClient: mock_http
)
```

### Test Steps
```pseudo
mock_http.queue_response(401, {
  "error": {
    "message": "Unauthorized",
    "code": 40100,
    "statusCode": 401
  }
})

TRY:
  AWAIT client.stats()
  FAIL("Expected exception")
CATCH AblyException as e:
  ASSERT e.statusCode == 401
  ASSERT e.code == 40100
```
