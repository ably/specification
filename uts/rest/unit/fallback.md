# Host Fallback and Endpoint Configuration Tests

Spec points: `RSC15`, `RSC15a`, `RSC15f`, `RSC15j`, `RSC15l`, `RSC15m`, `REC1`, `REC1a`, `REC1b`, `REC1b1`, `REC1b2`, `REC1b3`, `REC1b4`, `REC1c`, `REC1c1`, `REC1c2`, `REC1d`, `REC1d1`, `REC1d2`, `REC2`, `REC2a`, `REC2a1`, `REC2a2`, `REC2b`, `REC2c`, `REC2c1`, `REC2c2`, `REC2c3`, `REC2c4`, `REC2c5`, `REC2c6`, `REC3`, `REC3a`, `REC3b`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `rest_client.md` for the full Mock HTTP Infrastructure specification. These tests use the same `MockHttpClient` interface with `PendingConnection` and `PendingRequest`.

Fallback tests require the mock to support:
- Connection-level failures (DNS, connection refused, timeout)
- Per-host or per-request response configuration
- Tracking multiple sequential requests to different hosts

---

## RSC15m - Fallback only when fallback domains non-empty

**Test ID**: `rest/unit/RSC15m/no-fallback-empty-hosts-0`

**Spec requirement:** Fallback retry is only attempted when fallback hosts are configured (non-empty list).

Tests that fallback behavior is skipped when no fallback hosts are configured.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(500, { "error": { "code": 50000 } })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  fallbackHosts: []  # Explicitly empty
))
```

### Test Steps
```pseudo
AWAIT client.time() FAILS WITH error
# Should fail without retry
ASSERT mock_http.captured_requests.length == 1
ASSERT error.statusCode == 500
```

---

## RSC15a - Fallback hosts tried in random order

**Test ID**: `rest/unit/RSC15a/fallback-random-order-0`

**Spec requirement:** When the primary host fails, fallback hosts must be tried in random order to distribute load.

Tests that fallback hosts are tried when primary fails, in random order.

### Setup
```pseudo
mock_http = MockHttpClient()
# All requests fail to test full fallback sequence
mock_http.queue_responses(
  count: 6,  # primary + 5 fallbacks
  status: 500,
  body: { "error": { "code": 50000 } }
)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.time() FAILS WITH error
# Expected to fail after all retries
```

### Assertions
```pseudo
requests = mock_http.captured_requests

# First request to primary
ASSERT requests[0].url.host == "main.realtime.ably.net"

# Subsequent requests to fallback hosts
fallback_hosts_used = [r.url.host FOR r IN requests[1:]]

expected_fallbacks = [
  "main.a.fallback.ably-realtime.com",
  "main.b.fallback.ably-realtime.com",
  "main.c.fallback.ably-realtime.com",
  "main.d.fallback.ably-realtime.com",
  "main.e.fallback.ably-realtime.com"
]

# All used hosts should be valid fallbacks
ASSERT ALL host IN fallback_hosts_used: host IN expected_fallbacks

# To test randomness: run test multiple times and verify order varies
# (Implementation note: may need statistical test or seed control)
```

---

## RSC15l - Qualifying errors trigger fallback

**Test ID**: `rest/unit/RSC15l/qualifying-errors-trigger-fallback-0`

| Spec | Requirement |
|------|-------------|
| RSC15l1 | Host unreachable errors trigger fallback |
| RSC15l2 | Request timeout errors trigger fallback |
| RSC15l3 | HTTP 5xx status codes (500-504) trigger fallback |

Tests that specific error conditions trigger fallback retry.

### Test Cases

| ID | Spec | Condition | Should Retry |
|----|------|-----------|--------------|
| 1 | RSC15l1 | Host unreachable | Yes |
| 2 | RSC15l2 | Request timeout | Yes |
| 3 | RSC15l3 | HTTP 500 | Yes |
| 4 | RSC15l3 | HTTP 501 | Yes |
| 5 | RSC15l3 | HTTP 502 | Yes |
| 6 | RSC15l3 | HTTP 503 | Yes |
| 7 | RSC15l3 | HTTP 504 | Yes |
| 8 | | HTTP 400 | No |
| 9 | | HTTP 401 | No |
| 10 | | HTTP 404 | No |

### Setup (HTTP status codes)
```pseudo
FOR EACH test_case IN [500, 501, 502, 503, 504]:
  mock_http = MockHttpClient()
  mock_http.queue_response(test_case, { "error": { "code": test_case * 100 } })
  mock_http.queue_response(200, { "time": 1234567890000 })

  client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

  AWAIT client.time()

  ASSERT mock_http.captured_requests.length == 2
  ASSERT mock_http.captured_requests[1].url.host != mock_http.captured_requests[0].url.host
```

### Setup (Non-retryable errors)
```pseudo
FOR EACH test_case IN [400, 401, 404]:
  mock_http = MockHttpClient()
  mock_http.queue_response(test_case, { "error": { "code": test_case * 100 } })

  client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

  AWAIT client.time() FAILS WITH error
  # Expected to fail

  # Should NOT have retried
  ASSERT mock_http.captured_requests.length == 1
```

### Setup (Timeout)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_timeout()  # Simulates timeout
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpRequestTimeout: 1000
))

AWAIT client.time()

ASSERT mock_http.captured_requests.length == 2
```

---

## RSC15l4 - CloudFront errors trigger fallback

**Test ID**: `rest/unit/RSC15l4/cloudfront-error-triggers-fallback-0`

**Spec requirement:** Responses with a CloudFront Server header and status >= 400 must trigger fallback retry.

Tests that responses with CloudFront server header and status >= 400 trigger fallback.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(403,
  body: { "error": "Forbidden" },
  headers: { "Server": "CloudFront" }
)
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 2
ASSERT mock_http.captured_requests[0].url.host == "main.realtime.ably.net"
ASSERT mock_http.captured_requests[1].url.host != "main.realtime.ably.net"
```

---

## RSC15l - Comprehensive fallback scenarios with different error types

These tests verify that fallback behavior works correctly for different network and HTTP error conditions.

### RSC15l - Connection refused triggers fallback

**Test ID**: `rest/unit/RSC15l/connection-refused-fallback-0`

```pseudo
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => {
    request_count++
    IF request_count == 1:
      # First attempt (primary host) - connection refused
      conn.respond_with_refused()
    ELSE:
      # Fallback succeeds
      conn.respond_with_success()
  },
  onRequest: (req) => {
    req.respond_with(200, {"time": 1234567890000})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

result = AWAIT client.time()

# Should have succeeded on fallback
ASSERT result IS valid
ASSERT request_count == 2
```

### RSC15l - DNS error triggers fallback

**Test ID**: `rest/unit/RSC15l/dns-error-fallback-1`

```pseudo
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => {
    request_count++
    IF request_count == 1:
      # First attempt - DNS failure
      conn.respond_with_dns_error()
    ELSE:
      # Fallback succeeds
      conn.respond_with_success()
  },
  onRequest: (req) => {
    req.respond_with(200, {"time": 1234567890000})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

result = AWAIT client.time()

ASSERT result IS valid
ASSERT request_count == 2
```

### RSC15l - Connection timeout triggers fallback

**Test ID**: `rest/unit/RSC15l/connection-timeout-fallback-2`

```pseudo
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => {
    request_count++
    IF request_count == 1:
      # First attempt - connection timeout
      conn.respond_with_timeout()
    ELSE:
      # Fallback succeeds
      conn.respond_with_success()
  },
  onRequest: (req) => {
    req.respond_with(200, {"time": 1234567890000})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpRequestTimeout: 1000
))

result = AWAIT client.time()

ASSERT result IS valid
ASSERT request_count == 2
```

### RSC15l - Request timeout triggers fallback

**Test ID**: `rest/unit/RSC15l/request-timeout-fallback-3`

```pseudo
request_count = 0
captured_hosts = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => {
    captured_hosts.append(conn.host)
    conn.respond_with_success()
  },
  onRequest: (req) => {
    request_count++
    IF request_count == 1:
      # First request times out
      req.respond_with_timeout()
    ELSE:
      # Fallback succeeds
      req.respond_with(200, {"time": 1234567890000})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpRequestTimeout: 1000
))

result = AWAIT client.time()

ASSERT result IS valid
ASSERT request_count == 2
# Should have tried different hosts
ASSERT captured_hosts[0] != captured_hosts[1]
```

### RSC15l - HTTP 5xx errors trigger fallback

**Test ID**: `rest/unit/RSC15l/http-5xx-triggers-fallback-4`

```pseudo
FOR EACH status_code IN [500, 501, 502, 503, 504]:
  request_count = 0
  
  mock_http = MockHttpClient(
    onConnectionAttempt: (conn) => conn.respond_with_success(),
    onRequest: (req) => {
      request_count++
      IF request_count == 1:
        req.respond_with(status_code, {"error": {"code": status_code * 100}})
      ELSE:
        req.respond_with(200, {"time": 1234567890000})
    }
  )
  install_mock(mock_http)
  
  client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
  
  result = AWAIT client.time()
  
  ASSERT result IS valid
  ASSERT request_count == 2
```

### RSC15l - HTTP 4xx errors do NOT trigger fallback

**Test ID**: `rest/unit/RSC15l/http-4xx-no-fallback-5`

```pseudo
FOR EACH status_code IN [400, 401, 404]:
  request_count = 0
  
  mock_http = MockHttpClient(
    onConnectionAttempt: (conn) => conn.respond_with_success(),
    onRequest: (req) => {
      request_count++
      req.respond_with(status_code, {"error": {"code": status_code * 100}})
    }
  )
  install_mock(mock_http)
  
  client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
  
  AWAIT client.time() FAILS WITH error
  ASSERT error.statusCode == status_code
  
  # Should NOT have retried
  ASSERT request_count == 1
```

---

## RSC15j - Host header matches request host

**Test ID**: `rest/unit/RSC15j/host-header-matches-request-0`

**Spec requirement:** The HTTP Host header must match the actual host being requested, including for fallback hosts.

Tests that the Host header is set correctly for fallback requests.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(500, { "error": { "code": 50000 } })
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
request_1 = mock_http.captured_requests[0]
request_2 = mock_http.captured_requests[1]

# Host header should match the actual host being requested
ASSERT request_1.headers["Host"] == request_1.url.host
ASSERT request_2.headers["Host"] == request_2.url.host
ASSERT request_1.headers["Host"] != request_2.headers["Host"]
```

---

## RSC15f - Successful fallback host cached

**Test ID**: `rest/unit/RSC15f/successful-fallback-cached-0`

**Spec requirement:** When a fallback host succeeds, it should be cached and used for subsequent requests (for a limited time).

Tests that after successful fallback, that host is used for subsequent requests.

### Setup
```pseudo
mock_http = MockHttpClient()
# First request to primary fails
mock_http.queue_response_for_host("main.realtime.ably.net", 500, { "error": {} })
# First fallback succeeds
mock_http.queue_response_for_host("main.a.fallback.ably-realtime.com", 200, { "time": 1000 })
# Second request should go directly to cached fallback
mock_http.queue_response_for_host("main.a.fallback.ably-realtime.com", 200, { "time": 2000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  fallbackRetryTimeout: 60000  # 60 seconds
))
```

### Test Steps
```pseudo
# First request - triggers fallback
result1 = AWAIT client.time()

# Second request - should use cached fallback
result2 = AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 3

# Request 1: primary (failed)
ASSERT mock_http.captured_requests[0].url.host == "main.realtime.ably.net"

# Request 2: fallback (succeeded)
ASSERT mock_http.captured_requests[1].url.host == "main.a.fallback.ably-realtime.com"

# Request 3: cached fallback (no retry to primary)
ASSERT mock_http.captured_requests[2].url.host == "main.a.fallback.ably-realtime.com"
```

---

## RSC15f - Cached fallback expires after timeout

**Test ID**: `rest/unit/RSC15f/cached-fallback-expires-1`

**Spec requirement:** Cached fallback hosts must expire after `fallbackRetryTimeout` duration, after which the primary host is tried again.

Tests that cached fallback host is cleared after `fallbackRetryTimeout`.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response_for_host("main.realtime.ably.net", 500, { "error": {} })
mock_http.queue_response_for_host("main.a.fallback.ably-realtime.com", 200, { "time": 1000 })
# After timeout, primary should be tried again
mock_http.queue_response_for_host("main.realtime.ably.net", 200, { "time": 2000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  fallbackRetryTimeout: 100  # 100ms for testing
))
```

### Test Steps
```pseudo
# First request triggers fallback
AWAIT client.time()

# Wait for timeout to expire
WAIT 150 milliseconds

# Next request should try primary again
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 3

# After timeout, primary is tried again
ASSERT mock_http.captured_requests[2].url.host == "main.realtime.ably.net"
```

---

## RSC15f - Expired preferred fallback host not resurrected by late in-flight success

**Test ID**: `rest/unit/RSC15f/expired-not-resurrected-2`

**Spec requirement:** After `fallbackRetryTimeout` has elapsed the preference must be un-stored and future requests must restart the fallback sequence from the primary host. A late-arriving successful response against the previously-preferred fallback must not re-establish it as the preference.

Tests that a request that completes successfully against a fallback *after* `fallbackRetryTimeout` has expired does not re-pin that fallback as the preferred host.

### Setup
```pseudo
mock_http = MockHttpClient()

# Request handler: primary fails on first attempt, all others succeed.
# Second request (to cached fallback) is NOT responded to immediately —
# we hold the PendingRequest and respond later, after the timeout expires.
held_request = null
request_index = 0

mock_http.onRequest = (req) =>
  request_index += 1
  if request_index == 1
    # First request to primary — fail to trigger fallback
    req.respond_with(500, { "error": { "message": "fail", "code": 50000, "statusCode": 500 } })
  else if request_index == 2
    # First fallback — succeed, caches this host
    req.respond_with(200, [1000])
  else if request_index == 3
    # Second request goes to cached fallback — hold it (don't respond yet)
    held_request = req
  else
    # All subsequent requests — succeed
    req.respond_with(200, [1000])

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  fallbackRetryTimeout: 100  # 100ms for testing
))
```

### Test Steps
```pseudo
# Request 1+2: primary fails → fallback succeeds → fallback cached
AWAIT client.time()

# Request 3: goes to cached fallback, but we hold the response
request_future = client.time()   # starts but does not complete

# Advance time past fallbackRetryTimeout so the cache expires
WAIT 150 milliseconds

# Request 4: cache expired → should try primary again
AWAIT client.time()

# Now let the held request (3) complete successfully
held_request.respond_with(200, [1000])
AWAIT request_future

# Request 5: the late success from request 3 must NOT have re-pinned
# the fallback — this request should go to primary again
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 5

# Requests 1+2: primary fail → fallback success
ASSERT mock_http.captured_requests[0].url.host == "main.realtime.ably.net"
ASSERT mock_http.captured_requests[1].url.host != "main.realtime.ably.net"

fallback_host = mock_http.captured_requests[1].url.host

# Request 3: went to cached fallback (held, not yet responded)
ASSERT mock_http.captured_requests[2].url.host == fallback_host

# Request 4: after timeout expiry, primary is tried again
ASSERT mock_http.captured_requests[3].url.host == "main.realtime.ably.net"

# Request 5: late success from request 3 did NOT re-pin fallback
ASSERT mock_http.captured_requests[4].url.host == "main.realtime.ably.net"
```

---

# REC1 - Primary Domain Configuration

## REC1a - Default primary domain

**Test ID**: `rest/unit/REC1a/default-primary-domain-0`

**Spec requirement:** When no endpoint configuration is provided, the default primary domain is `rest.ably.io` for REST and `realtime.ably.io` for Realtime.

Tests that the default primary domain is used when no endpoint options are specified.

> **Note:** The spec defines the legacy default as `rest.ably.io` for REST and `realtime.ably.io` for Realtime. SDKs adopting the new `endpoint` routing policy (REC1b) should use `main.realtime.ably.net` as the new default. SDKs still using the legacy `restHost`/`realtimeHost` pattern should assert against `rest.ably.io` / `realtime.ably.io` respectively.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests[0].url.host == "main.realtime.ably.net"
```

---

## REC1b2 - Endpoint option as explicit hostname (with period)

**Test ID**: `rest/unit/REC1b2/explicit-hostname-with-period-0`

Tests that when `endpoint` contains a period (`.`), it's treated as an explicit hostname.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "custom.ably.example.com"
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests[0].url.host == "custom.ably.example.com"
```

---

## REC1b2 - Endpoint option as localhost

**Test ID**: `rest/unit/REC1b2/endpoint-localhost-1`

Tests that `endpoint: "localhost"` is treated as an explicit hostname.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "localhost"
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests[0].url.host == "localhost"
```

---

## REC1b2 - Endpoint option as IPv6 address

**Test ID**: `rest/unit/REC1b2/endpoint-ipv6-address-2`

Tests that `endpoint` containing `::` is treated as an explicit hostname (IPv6).

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "::1"
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
# IPv6 addresses may be bracketed in URLs
ASSERT mock_http.captured_requests[0].url.host == "::1" OR
       mock_http.captured_requests[0].url.host == "[::1]"
```

---

## REC1b3 - Endpoint option as nonprod routing policy

**Test ID**: `rest/unit/REC1b3/nonprod-routing-policy-0`

Tests that `endpoint: "nonprod:[id]"` resolves to `[id].realtime.ably-nonprod.net`.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "nonprod:staging"
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests[0].url.host == "staging.realtime.ably-nonprod.net"
```

---

## REC1b4 - Endpoint option as production routing policy

**Test ID**: `rest/unit/REC1b4/production-routing-policy-0`

Tests that `endpoint: "[id]"` (without period or nonprod prefix) resolves to `[id].realtime.ably.net`.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "test"
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests[0].url.host == "test.realtime.ably.net"
```

---

## REC1b1 - Endpoint conflicts with deprecated environment option

**Test ID**: `rest/unit/REC1b1/endpoint-conflicts-environment-0`

Tests that specifying both `endpoint` and `environment` is invalid.

### Setup
```pseudo
# No mock needed - should fail during client construction
```

### Test Steps
```pseudo
Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "test",
  environment: "production"  # Deprecated, conflicts with endpoint
)) FAILS WITH error
ASSERT error.code == 40000 OR error.message CONTAINS "invalid" OR error.message CONTAINS "conflict"
```

---

## REC1b1 - Endpoint conflicts with deprecated restHost option

**Test ID**: `rest/unit/REC1b1/endpoint-conflicts-resthost-1`

Tests that specifying both `endpoint` and `restHost` is invalid.

### Setup
```pseudo
# No mock needed - should fail during client construction
```

### Test Steps
```pseudo
Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "test",
  restHost: "custom.host.com"  # Deprecated, conflicts with endpoint
)) FAILS WITH error
ASSERT error.code == 40000 OR error.message CONTAINS "invalid" OR error.message CONTAINS "conflict"
```

---

## REC1b1 - Endpoint conflicts with deprecated realtimeHost option

**Test ID**: `rest/unit/REC1b1/endpoint-conflicts-realtimehost-2`

Tests that specifying both `endpoint` and `realtimeHost` is invalid.

### Setup
```pseudo
# No mock needed - should fail during client construction
```

### Test Steps
```pseudo
Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "test",
  realtimeHost: "custom.realtime.com"  # Deprecated, conflicts with endpoint
)) FAILS WITH error
ASSERT error.code == 40000 OR error.message CONTAINS "invalid" OR error.message CONTAINS "conflict"
```

---

## REC1b1 - Endpoint conflicts with deprecated fallbackHostsUseDefault option

**Test ID**: `rest/unit/REC1b1/endpoint-conflicts-fallback-default-3`

Tests that specifying both `endpoint` and `fallbackHostsUseDefault` is invalid.

### Setup
```pseudo
# No mock needed - should fail during client construction
```

### Test Steps
```pseudo
Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "test",
  fallbackHostsUseDefault: true  # Deprecated, conflicts with endpoint
)) FAILS WITH error
ASSERT error.code == 40000 OR error.message CONTAINS "invalid" OR error.message CONTAINS "conflict"
```

---

## REC1c2 - Deprecated environment option determines primary domain

**Test ID**: `rest/unit/REC1c2/environment-sets-primary-domain-0`

Tests that the deprecated `environment` option sets primary domain to `[id].realtime.ably.net`.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  environment: "sandbox"  # Deprecated but still supported
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests[0].url.host == "sandbox.realtime.ably.net"
```

---

## REC1c1 - Environment conflicts with restHost

**Test ID**: `rest/unit/REC1c1/environment-conflicts-resthost-0`

Tests that specifying both `environment` and `restHost` is invalid.

### Setup
```pseudo
# No mock needed - should fail during client construction
```

### Test Steps
```pseudo
Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  environment: "sandbox",
  restHost: "custom.host.com"
)) FAILS WITH error
ASSERT error.code == 40000 OR error.message CONTAINS "invalid" OR error.message CONTAINS "conflict"
```

---

## REC1c1 - Environment conflicts with realtimeHost

**Test ID**: `rest/unit/REC1c1/environment-conflicts-realtimehost-1`

Tests that specifying both `environment` and `realtimeHost` is invalid.

### Setup
```pseudo
# No mock needed - should fail during client construction
```

### Test Steps
```pseudo
Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  environment: "sandbox",
  realtimeHost: "custom.realtime.com"
)) FAILS WITH error
ASSERT error.code == 40000 OR error.message CONTAINS "invalid" OR error.message CONTAINS "conflict"
```

---

## REC1d1 - Deprecated restHost option determines primary domain

**Test ID**: `rest/unit/REC1d1/resthost-sets-primary-domain-0`

Tests that the deprecated `restHost` option sets the primary domain.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  restHost: "custom.rest.example.com"
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests[0].url.host == "custom.rest.example.com"
```

---

## REC1d2 - Deprecated realtimeHost option determines primary domain (when restHost not set)

**Test ID**: `rest/unit/REC1d2/realtimehost-sets-primary-domain-0`

Tests that `realtimeHost` sets primary domain when `restHost` is not specified.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeHost: "custom.realtime.example.com"
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests[0].url.host == "custom.realtime.example.com"
```

---

## REC1d - restHost takes precedence over realtimeHost

**Test ID**: `rest/unit/REC1d/resthost-precedence-over-realtimehost-0`

Tests that when both `restHost` and `realtimeHost` are specified, `restHost` is used for REST requests.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  restHost: "rest.example.com",
  realtimeHost: "realtime.example.com"
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
# REST client uses restHost, not realtimeHost
ASSERT mock_http.captured_requests[0].url.host == "rest.example.com"
```

---

# REC2 - Fallback Domains Configuration

## REC2c1 - Default fallback domains

**Test ID**: `rest/unit/REC2c1/default-fallback-domains-0`

**Spec requirement:** When using default configuration, fallback domains follow the pattern `[a-e].ably-realtime.com`.

Tests that default configuration provides the standard fallback domains.

> **Note:** The spec defines the legacy fallback pattern as `[a-e].ably-realtime.com`. SDKs adopting the new `endpoint` routing policy (REC1b) should use `main.[a-e].fallback.ably-realtime.com`. SDKs still using the legacy pattern should assert against `[a-e].ably-realtime.com`.

### Setup
```pseudo
mock_http = MockHttpClient()
# Primary fails
mock_http.queue_response(500, { "error": { "code": 50000 } })
# Fallback succeeds
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 2
ASSERT mock_http.captured_requests[0].url.host == "main.realtime.ably.net"

expected_fallbacks = [
  "main.a.fallback.ably-realtime.com",
  "main.b.fallback.ably-realtime.com",
  "main.c.fallback.ably-realtime.com",
  "main.d.fallback.ably-realtime.com",
  "main.e.fallback.ably-realtime.com"
]
ASSERT mock_http.captured_requests[1].url.host IN expected_fallbacks
```

---

## REC2a2 - Custom fallbackHosts option

**Test ID**: `rest/unit/REC2a2/custom-fallback-hosts-0`

Tests that the `fallbackHosts` option overrides default fallbacks.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(500, { "error": { "code": 50000 } })
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  fallbackHosts: ["fb1.example.com", "fb2.example.com", "fb3.example.com"]
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 2
ASSERT mock_http.captured_requests[0].url.host == "main.realtime.ably.net"
ASSERT mock_http.captured_requests[1].url.host IN ["fb1.example.com", "fb2.example.com", "fb3.example.com"]
```

---

## REC2a1 - fallbackHosts conflicts with fallbackHostsUseDefault

**Test ID**: `rest/unit/REC2a1/fallback-hosts-conflicts-use-default-0`

Tests that specifying both `fallbackHosts` and `fallbackHostsUseDefault` is invalid.

### Setup
```pseudo
# No mock needed - should fail during client construction
```

### Test Steps
```pseudo
Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  fallbackHosts: ["fb1.example.com"],
  fallbackHostsUseDefault: true
)) FAILS WITH error
ASSERT error.code == 40000 OR error.message CONTAINS "invalid" OR error.message CONTAINS "conflict"
```

---

## REC2b - Deprecated fallbackHostsUseDefault option

**Test ID**: `rest/unit/REC2b/fallback-hosts-use-default-0`

Tests that `fallbackHostsUseDefault: true` uses the default fallback domains.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(500, { "error": { "code": 50000 } })
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  restHost: "custom.host.com",  # Would normally disable fallbacks
  fallbackHostsUseDefault: true  # Force default fallbacks
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 2
ASSERT mock_http.captured_requests[0].url.host == "custom.host.com"

# Should use default fallbacks despite custom restHost
expected_fallbacks = [
  "main.a.fallback.ably-realtime.com",
  "main.b.fallback.ably-realtime.com",
  "main.c.fallback.ably-realtime.com",
  "main.d.fallback.ably-realtime.com",
  "main.e.fallback.ably-realtime.com"
]
ASSERT mock_http.captured_requests[1].url.host IN expected_fallbacks
```

---

## REC2c2 - Explicit hostname endpoint has no fallbacks

**Test ID**: `rest/unit/REC2c2/explicit-hostname-no-fallbacks-0`

Tests that when `endpoint` is an explicit hostname, fallback domains are empty.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(500, { "error": { "code": 50000 } })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "custom.ably.example.com"  # Contains period = explicit hostname
))
```

### Test Steps
```pseudo
AWAIT client.time() FAILS WITH error
# Expected to fail with no fallback
```

### Assertions
```pseudo
# No fallback attempted - only one request
ASSERT mock_http.captured_requests.length == 1
ASSERT mock_http.captured_requests[0].url.host == "custom.ably.example.com"
```

---

## REC2c3 - Nonprod routing policy fallback domains

**Test ID**: `rest/unit/REC2c3/nonprod-fallback-domains-0`

Tests that nonprod routing policy has corresponding nonprod fallback domains.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(500, { "error": { "code": 50000 } })
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "nonprod:staging"
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 2
ASSERT mock_http.captured_requests[0].url.host == "staging.realtime.ably-nonprod.net"

expected_fallbacks = [
  "staging.a.fallback.ably-realtime-nonprod.com",
  "staging.b.fallback.ably-realtime-nonprod.com",
  "staging.c.fallback.ably-realtime-nonprod.com",
  "staging.d.fallback.ably-realtime-nonprod.com",
  "staging.e.fallback.ably-realtime-nonprod.com"
]
ASSERT mock_http.captured_requests[1].url.host IN expected_fallbacks
```

---

## REC2c4 - Production routing policy fallback domains (via endpoint)

**Test ID**: `rest/unit/REC2c4/production-endpoint-fallback-domains-0`

Tests that production routing policy via `endpoint` has corresponding fallback domains.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(500, { "error": { "code": 50000 } })
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "test"
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 2
ASSERT mock_http.captured_requests[0].url.host == "test.realtime.ably.net"

expected_fallbacks = [
  "test.a.fallback.ably-realtime.com",
  "test.b.fallback.ably-realtime.com",
  "test.c.fallback.ably-realtime.com",
  "test.d.fallback.ably-realtime.com",
  "test.e.fallback.ably-realtime.com"
]
ASSERT mock_http.captured_requests[1].url.host IN expected_fallbacks
```

---

## REC2c5 - Production routing policy fallback domains (via deprecated environment)

**Test ID**: `rest/unit/REC2c5/production-environment-fallback-domains-0`

Tests that production routing policy via deprecated `environment` has corresponding fallback domains.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(500, { "error": { "code": 50000 } })
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  environment: "sandbox"  # Deprecated
))
```

### Test Steps
```pseudo
AWAIT client.time()
```

### Assertions
```pseudo
ASSERT mock_http.captured_requests.length == 2
ASSERT mock_http.captured_requests[0].url.host == "sandbox.realtime.ably.net"

expected_fallbacks = [
  "sandbox.a.fallback.ably-realtime.com",
  "sandbox.b.fallback.ably-realtime.com",
  "sandbox.c.fallback.ably-realtime.com",
  "sandbox.d.fallback.ably-realtime.com",
  "sandbox.e.fallback.ably-realtime.com"
]
ASSERT mock_http.captured_requests[1].url.host IN expected_fallbacks
```

---

## REC2c6 - Custom restHost has no fallbacks

**Test ID**: `rest/unit/REC2c6/custom-resthost-no-fallbacks-0`

Tests that deprecated `restHost` option results in no fallback domains.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(500, { "error": { "code": 50000 } })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  restHost: "custom.rest.example.com"
))
```

### Test Steps
```pseudo
AWAIT client.time() FAILS WITH error
# Expected to fail with no fallback
```

### Assertions
```pseudo
# No fallback attempted
ASSERT mock_http.captured_requests.length == 1
ASSERT mock_http.captured_requests[0].url.host == "custom.rest.example.com"
```

---

## REC2c6 - Custom realtimeHost has no fallbacks

**Test ID**: `rest/unit/REC2c6/custom-realtimehost-no-fallbacks-1`

Tests that deprecated `realtimeHost` option results in no fallback domains.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(500, { "error": { "code": 50000 } })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeHost: "custom.realtime.example.com"
))
```

### Test Steps
```pseudo
AWAIT client.time() FAILS WITH error
# Expected to fail with no fallback
```

### Assertions
```pseudo
# No fallback attempted
ASSERT mock_http.captured_requests.length == 1
ASSERT mock_http.captured_requests[0].url.host == "custom.realtime.example.com"
```

---

# REC3 - Connectivity Check URL

## REC3a - Default connectivity check URL

**Test ID**: `rest/unit/REC3a/default-connectivity-check-url-0`

Tests that the default connectivity check URL is `https://internet-up.ably-realtime.com/is-the-internet-up.txt`.

### Note
This test is primarily relevant for Realtime clients that perform connectivity checks. The connectivity check URL is used to verify internet connectivity before attempting to connect.

### Setup
```pseudo
mock_http = MockHttpClient()
# Queue response for connectivity check
mock_http.queue_response_for_url(
  "https://internet-up.ably-realtime.com/is-the-internet-up.txt",
  200,
  "yes"
)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Trigger connectivity check (implementation-specific)
# Some libraries expose this, others do it internally
result = AWAIT client.connection.checkConnectivity()
# OR: observe that connectivity check request was made during connection
```

### Assertions
```pseudo
connectivity_requests = mock_http.captured_requests.filter(
  r => r.url.path CONTAINS "is-the-internet-up"
)
ASSERT connectivity_requests.length >= 1
ASSERT connectivity_requests[0].url.toString() == "https://internet-up.ably-realtime.com/is-the-internet-up.txt"

CLOSE_CLIENT(client)
```

---

## REC3b - Custom connectivity check URL

**Test ID**: `rest/unit/REC3b/custom-connectivity-check-url-0`

Tests that the `connectivityCheckUrl` option overrides the default.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response_for_url(
  "https://custom.example.com/connectivity",
  200,
  "ok"
)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  connectivityCheckUrl: "https://custom.example.com/connectivity"
))
```

### Test Steps
```pseudo
result = AWAIT client.connection.checkConnectivity()
```

### Assertions
```pseudo
connectivity_requests = mock_http.captured_requests.filter(
  r => r.url.host == "custom.example.com"
)
ASSERT connectivity_requests.length >= 1
ASSERT connectivity_requests[0].url.toString() == "https://custom.example.com/connectivity"

# Should NOT request the default URL
default_requests = mock_http.captured_requests.filter(
  r => r.url.host == "internet-up.ably-realtime.com"
)
ASSERT default_requests.length == 0

CLOSE_CLIENT(client)
```

---

## REC3 - Connectivity check response validation

**Test ID**: `rest/unit/REC3/connectivity-check-validation-0`

Tests that the connectivity check expects a specific response.

### Test Cases

| ID | Response | Expected Result |
|----|----------|-----------------|
| 1 | HTTP 200 with body "yes" | Connected |
| 2 | HTTP 200 with body "no" | Not connected |
| 3 | HTTP 200 with empty body | Not connected |
| 4 | HTTP 404 | Not connected |
| 5 | Network error | Not connected |

### Setup (Case 1 - Success)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response_for_url(
  "https://internet-up.ably-realtime.com/is-the-internet-up.txt",
  200,
  "yes"
)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
result = AWAIT client.connection.checkConnectivity()

ASSERT result == true

CLOSE_CLIENT(client)
```

### Setup (Case 2 - Wrong body)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response_for_url(
  "https://internet-up.ably-realtime.com/is-the-internet-up.txt",
  200,
  "no"
)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
result = AWAIT client.connection.checkConnectivity()

ASSERT result == false

CLOSE_CLIENT(client)
```

### Setup (Case 4 - HTTP error)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response_for_url(
  "https://internet-up.ably-realtime.com/is-the-internet-up.txt",
  404,
  "Not Found"
)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
result = AWAIT client.connection.checkConnectivity()

ASSERT result == false

CLOSE_CLIENT(client)
```
