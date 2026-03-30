# Stats API Tests

Spec points: `RSC6`

## Test Type
Unit test with mocked HTTP client

## Mock Configuration

These tests use the mock HTTP infrastructure defined in `rest_client.md`. The mock supports:
- Handler-based configuration with `onConnectionAttempt` and `onRequest`
- Capturing requests via `captured_requests` arrays
- Configurable responses with status codes, bodies, and headers

See `rest_client.md` for detailed mock interface documentation.

## Purpose

Tests the `stats()` method which retrieves application statistics from Ably. The stats endpoint requires authentication and returns paginated results.

---

## RSC6a - stats() returns paginated results

**Spec requirement:** The `stats()` method retrieves application statistics from the `/stats` endpoint and returns a PaginatedResult of Stats objects.

Tests that `stats()` returns a PaginatedResult of Stats objects.

### Setup
```pseudo
captured_requests = []
stats_data = [
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
]

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, stats_data)
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
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
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.method == "GET"
ASSERT request.path == "/stats"
```

---

## RSC6a - stats() requires authentication

**Spec requirement:** The `/stats` endpoint requires authentication. Requests must include valid credentials.

Tests that stats() requires authentication.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
AWAIT client.stats()
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
request = captured_requests[0]

# Request should have Authorization header
ASSERT "Authorization" IN request.headers
```

---

## RSC6b1 - stats() with start parameter

**Spec requirement:** The `start` parameter filters stats to return entries from the specified start time onwards.

Tests that the `start` parameter filters stats by start time.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
start_time = DateTime(2024, 1, 1, 0, 0, 0)
AWAIT client.stats(start: start_time)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.query_params["start"] == str(start_time.millisecondsSinceEpoch)
```

---

## RSC6b1 - stats() with end parameter

**Spec requirement:** The `end` parameter filters stats to return entries up to the specified end time.

Tests that the `end` parameter filters stats by end time.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
end_time = DateTime(2024, 1, 31, 23, 59, 59)
AWAIT client.stats(end: end_time)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.query_params["end"] == str(end_time.millisecondsSinceEpoch)
```

---

## RSC6b2 - stats() with limit parameter

**Spec requirement:** The `limit` parameter restricts the number of stats entries returned in a single page.

Tests that the `limit` parameter restricts the number of results.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
AWAIT client.stats(limit: 10)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.query_params["limit"] == "10"
```

---

## RSC6b3 - stats() with direction parameter

**Spec requirement:** The `direction` parameter controls the ordering of results (forwards or backwards in time).

Tests that the `direction` parameter controls result ordering.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
# Test forwards direction
AWAIT client.stats(direction: "forwards")
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.query_params["direction"] == "forwards"
```

---

## RSC6b4 - stats() with unit parameter

**Spec requirement:** The `unit` parameter specifies the time granularity for stats aggregation (minute, hour, day, or month).

Tests that the `unit` parameter specifies the stats granularity.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
# Valid units: minute, hour, day, month
AWAIT client.stats(unit: "day")
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.query_params["unit"] == "day"
```

---

## RSC6a - stats() pagination navigation

**Spec requirement:** Stats results must support pagination using Link headers and provide hasNext() functionality.

Tests that stats results support pagination navigation.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, 
      [{"intervalId": "2024-01-01:00:00", "unit": "hour"}],
      headers: {"link": '</stats?start=...&limit=1>; rel="next"'}
    )
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
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

**Spec requirement:** The stats() method must handle empty result sets correctly.

Tests that stats() handles empty results correctly.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
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

**Spec requirement:** Errors from the stats endpoint must be properly propagated to the caller.

Tests that errors from the stats endpoint are properly propagated.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(401, {
      "error": {
        "message": "Unauthorized",
        "code": 40100,
        "statusCode": 401
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
AWAIT client.stats() FAILS WITH error
ASSERT error.statusCode == 401
ASSERT error.code == 40100
```
