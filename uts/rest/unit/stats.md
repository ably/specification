# Stats API Tests

Spec points: `RSC6`, `RSC6a`, `RSC6b1`, `RSC6b2`, `RSC6b3`, `RSC6b4`, `TS12`, `TS12a`, `TS12c`, `TS12p`, `TS12r`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

## Purpose

Tests the `stats()` method which retrieves application statistics from Ably. The stats endpoint requires authentication and returns paginated results.

---

## RSC6a - stats() returns PaginatedResult with Stats objects

**Test ID**: `rest/unit/RSC6a/returns-paginated-stats-0`

**Spec requirement:** Returns a `PaginatedResult` page containing `Stats` objects in the `PaginatedResult#items` attribute returned from the stats request.

Tests that `stats()` makes a GET request to `/stats` and returns a PaginatedResult containing Stats objects.

### Setup
```pseudo
captured_requests = []
# TS12: the flattened Stats shape — intervalId, unit, and a flat `entries`
# map keyed by dotted metric path (plus optional schema/appId/inProgress).
# The deep per-type structure (all/inbound/outbound/… → messages/presence →
# count/data) was deprecated and removed as of specification version 2.2.
stats_data = [
  {
    "intervalId": "2024-01-01:00:00",
    "unit": "hour",
    "schema": "https://schemas.ably.com/json/app-stats-0.0.1.json",
    "appId": "abcd1234",
    "entries": {
      "messages.all.all.count": 100,
      "messages.all.all.data": 5000
    }
  },
  {
    "intervalId": "2024-01-01:01:00",
    "unit": "hour",
    "entries": {
      "messages.all.all.count": 150,
      "messages.all.all.data": 7500
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

# Stats objects should have the correct fields (TS12)
ASSERT result.items[0].intervalId == "2024-01-01:00:00"    # TS12a
ASSERT result.items[0].unit == "hour"                       # TS12c
# TS12r: statistics are exposed as a flat `entries` map
ASSERT result.items[0].entries["messages.all.all.count"] == 100
ASSERT result.items[0].entries["messages.all.all.data"] == 5000
# TS12p: intervalTime is parsed from intervalId
ASSERT result.items[0].intervalTime == Time(2024, 1, 1, 0, 0, 0, UTC)
ASSERT result.items[1].intervalId == "2024-01-01:01:00"
ASSERT result.items[1].entries["messages.all.all.count"] == 150

# Verify correct endpoint and method
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.method == "GET"
ASSERT request.path == "/stats"
```

---

## RSC6a - stats() sends authenticated request with standard headers

**Test ID**: `rest/unit/RSC6a/authenticated-with-headers-1`

**Spec requirement:** The `/stats` endpoint requires authentication. Requests must include valid credentials and standard Ably headers.

Tests that stats() sends an authenticated request with standard Ably headers.

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

# Request must be authenticated
ASSERT "Authorization" IN request.headers

# Standard Ably headers must be present
ASSERT "X-Ably-Version" IN request.headers
ASSERT "Ably-Agent" IN request.headers
```

---

## RSC6b1 - stats() with start parameter

**Test ID**: `rest/unit/RSC6b1/start-param-millis-0`

**Spec requirement:** `start` is an optional timestamp field represented as milliseconds since epoch. If provided, must be equal to or less than `end` if provided or to the current time otherwise.

Tests that the `start` parameter is sent as milliseconds since epoch.

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
start_time = DateTime(2024, 1, 1, 0, 0, 0, UTC)
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

**Test ID**: `rest/unit/RSC6b1/end-param-millis-1`

**Spec requirement:** `end` is an optional timestamp field represented as milliseconds since epoch.

Tests that the `end` parameter is sent as milliseconds since epoch.

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
end_time = DateTime(2024, 1, 31, 23, 59, 59, UTC)
AWAIT client.stats(end: end_time)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.query_params["end"] == str(end_time.millisecondsSinceEpoch)
```

---

## RSC6b1 - stats() with start and end parameters

**Test ID**: `rest/unit/RSC6b1/start-and-end-params-2`

**Spec requirement:** `start` and `end` are optional timestamp fields. `start`, if provided, must be equal to or less than `end` if provided.

Tests that both `start` and `end` are sent as query parameters when provided together.

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
start_time = DateTime(2024, 1, 1, 0, 0, 0, UTC)
end_time = DateTime(2024, 1, 31, 23, 59, 59, UTC)
AWAIT client.stats(start: start_time, end: end_time)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.query_params["start"] == str(start_time.millisecondsSinceEpoch)
ASSERT request.query_params["end"] == str(end_time.millisecondsSinceEpoch)
```

---

## RSC6b2 - stats() with direction parameter

**Test ID**: `rest/unit/RSC6b2/direction-param-forwards-0`

**Spec requirement:** `direction` backwards or forwards; if omitted the direction defaults to the REST API default (backwards).

Tests that the `direction` parameter is sent as a query parameter.

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
AWAIT client.stats(direction: "forwards")
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.query_params["direction"] == "forwards"
```

---

## RSC6b2 - stats() direction defaults to backwards

**Test ID**: `rest/unit/RSC6b2/direction-defaults-backwards-1`

**Spec requirement:** If omitted the direction defaults to the REST API default (backwards).

Tests that when direction is not specified, it is either omitted from the query (letting the server apply the default) or sent as "backwards".

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

# Direction should either be absent (server default) or "backwards"
ASSERT "direction" NOT IN request.query_params
    OR request.query_params["direction"] == "backwards"
```

---

## RSC6b3 - stats() with limit parameter

**Test ID**: `rest/unit/RSC6b3/limit-param-value-0`

**Spec requirement:** `limit` supports up to 1,000 items; if omitted the limit defaults to the REST API default (100).

Tests that the `limit` parameter is sent as a query parameter.

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

## RSC6b3 - stats() limit defaults to 100

**Test ID**: `rest/unit/RSC6b3/limit-defaults-to-100-1`

**Spec requirement:** If omitted the limit defaults to the REST API default (100).

Tests that when limit is not specified, it is either omitted from the query (letting the server apply the default) or sent as "100".

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

# Limit should either be absent (server default) or "100"
ASSERT "limit" NOT IN request.query_params
    OR request.query_params["limit"] == "100"
```

---

## RSC6b4 - stats() with unit parameter

**Test ID**: `rest/unit/RSC6b4/unit-param-values-0`

**Spec requirement:** `unit` is the period for which the stats will be aggregated by, values supported are `minute`, `hour`, `day` or `month`; if omitted the unit defaults to the REST API default (`minute`).

Tests that each valid unit value is sent as a query parameter.

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

### Test Cases

| ID | Unit |
|----|------|
| 1 | minute |
| 2 | hour |
| 3 | day |
| 4 | month |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  captured_requests = []

  AWAIT client.stats(unit: test_case.unit)

  ASSERT captured_requests.length == 1
  request = captured_requests[0]
  ASSERT request.query_params["unit"] == test_case.unit
```

---

## RSC6b4 - stats() unit defaults to minute

**Test ID**: `rest/unit/RSC6b4/unit-defaults-to-minute-1`

**Spec requirement:** If omitted the unit defaults to the REST API default (`minute`).

Tests that when unit is not specified, it is either omitted from the query (letting the server apply the default) or sent as "minute".

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

# Unit should either be absent (server default) or "minute"
ASSERT "unit" NOT IN request.query_params
    OR request.query_params["unit"] == "minute"
```

---

## RSC6b - stats() with all parameters combined

**Test ID**: `rest/unit/RSC6b/all-params-combined-0`

| Spec | Requirement |
|------|-------------|
| RSC6b1 | `start` and `end` timestamp parameters |
| RSC6b2 | `direction` parameter |
| RSC6b3 | `limit` parameter |
| RSC6b4 | `unit` parameter |

Tests that all parameters can be used together in a single request.

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
start_time = DateTime(2024, 1, 1, 0, 0, 0, UTC)
end_time = DateTime(2024, 1, 31, 23, 59, 59, UTC)
AWAIT client.stats(
  start: start_time,
  end: end_time,
  direction: "forwards",
  limit: 50,
  unit: "hour"
)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.query_params["start"] == str(start_time.millisecondsSinceEpoch)
ASSERT request.query_params["end"] == str(end_time.millisecondsSinceEpoch)
ASSERT request.query_params["direction"] == "forwards"
ASSERT request.query_params["limit"] == "50"
ASSERT request.query_params["unit"] == "hour"
```

---

## RSC6a - stats() with no parameters sends no query params

**Test ID**: `rest/unit/RSC6a/no-params-clean-request-2`

**Spec requirement:** All parameters are optional. When no parameters are provided, the request should omit query parameters (letting the server apply defaults).

Tests that calling stats() with no arguments sends a clean GET to `/stats`.

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
ASSERT request.method == "GET"
ASSERT request.path == "/stats"

# No query parameters should be sent (server applies defaults)
ASSERT request.query_params IS empty
```

---

## RSC6a - stats() pagination with Link headers

**Test ID**: `rest/unit/RSC6a/pagination-link-headers-3`

**Spec requirement:** Returns a `PaginatedResult` page. PaginatedResult supports navigation via Link headers (TG4, TG6).

Tests that stats results support pagination navigation using Link headers.

### Setup
```pseudo
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    request_count++
    IF request_count == 1:
      req.respond_with(200,
        [{"intervalId": "2024-01-01:01:00", "unit": "hour"}],
        headers: {"Link": '</stats?start=1704070800000&limit=1>; rel="next"'}
      )
    ELSE:
      req.respond_with(200,
        [{"intervalId": "2024-01-01:00:00", "unit": "hour"}]
      )
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "app.key:secret"))
```

### Test Steps
```pseudo
page1 = AWAIT client.stats(limit: 1)
page2 = AWAIT page1.next()
```

### Assertions
```pseudo
# First page
ASSERT page1.items.length == 1
ASSERT page1.items[0].intervalId == "2024-01-01:01:00"
ASSERT page1.hasNext() == true
ASSERT page1.isLast() == false

# Second page
ASSERT page2.items.length == 1
ASSERT page2.items[0].intervalId == "2024-01-01:00:00"
ASSERT page2.hasNext() == false
ASSERT page2.isLast() == true
```

---

## RSC6a - stats() empty results

**Test ID**: `rest/unit/RSC6a/empty-results-handled-4`

**Spec requirement:** Returns a `PaginatedResult` page containing `Stats` objects. Must handle empty result sets correctly.

Tests that stats() handles empty results correctly.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
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
ASSERT result IS PaginatedResult
ASSERT result.items.length == 0
ASSERT result.hasNext() == false
ASSERT result.isLast() == true
```

---

## RSC6a - stats() error handling

**Test ID**: `rest/unit/RSC6a/error-propagated-5`

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
