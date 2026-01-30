# Host Fallback and Endpoint Configuration Tests

Spec points: `RSC15`, `RSC15a`, `RSC15f`, `RSC15j`, `RSC15l`, `RSC15m`, `REC1`, `REC1a`, `REC1b`, `REC1b1`, `REC1b2`, `REC1b3`, `REC1b4`, `REC1c`, `REC1c1`, `REC1c2`, `REC1d`, `REC1d1`, `REC1d2`, `REC2`, `REC2a`, `REC2a1`, `REC2a2`, `REC2b`, `REC2c`, `REC2c1`, `REC2c2`, `REC2c3`, `REC2c4`, `REC2c5`, `REC2c6`, `REC3`, `REC3a`, `REC3b`

## Test Type
Unit test with mocked HTTP client

## Mock Configuration

### HTTP Client Mock
Captures outgoing requests and returns configurable responses.
Must support:
- Per-host response configuration
- Simulating various failure conditions (timeout, DNS failure, HTTP errors)

---

## RSC15m - Fallback only when fallback domains non-empty

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
TRY:
  AWAIT client.time()
  FAIL("Expected exception")
CATCH AblyException as e:
  # Should fail without retry
  ASSERT mock_http.captured_requests.length == 1
  ASSERT e.statusCode == 500
```

---

## RSC15a - Fallback hosts tried in random order

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
TRY:
  AWAIT client.time()
  FAIL("Expected exception after all retries")
CATCH AblyException:
  PASS  # Expected
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

  TRY:
    AWAIT client.time()
  CATCH AblyException:
    PASS

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

## RSC15j - Host header matches request host

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

# REC1 - Primary Domain Configuration

## REC1a - Default primary domain

Tests that the default primary domain is `main.realtime.ably.net` when no endpoint options are specified.

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

Tests that `endpoint: "[id]"` (without period or nonprod prefix) resolves to `[id].realtime.ably.net`.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "sandbox"
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

## REC1b1 - Endpoint conflicts with deprecated environment option

Tests that specifying both `endpoint` and `environment` is invalid.

### Setup
```pseudo
# No mock needed - should fail during client construction
```

### Test Steps
```pseudo
TRY:
  client = Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    endpoint: "sandbox",
    environment: "production"  # Deprecated, conflicts with endpoint
  ))
  FAIL("Expected exception for conflicting options")
CATCH AblyException as e:
  ASSERT e.code == 40000 OR e.message CONTAINS "invalid" OR e.message CONTAINS "conflict"
```

---

## REC1b1 - Endpoint conflicts with deprecated restHost option

Tests that specifying both `endpoint` and `restHost` is invalid.

### Setup
```pseudo
# No mock needed - should fail during client construction
```

### Test Steps
```pseudo
TRY:
  client = Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    endpoint: "sandbox",
    restHost: "custom.host.com"  # Deprecated, conflicts with endpoint
  ))
  FAIL("Expected exception for conflicting options")
CATCH AblyException as e:
  ASSERT e.code == 40000 OR e.message CONTAINS "invalid" OR e.message CONTAINS "conflict"
```

---

## REC1b1 - Endpoint conflicts with deprecated realtimeHost option

Tests that specifying both `endpoint` and `realtimeHost` is invalid.

### Setup
```pseudo
# No mock needed - should fail during client construction
```

### Test Steps
```pseudo
TRY:
  client = Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    endpoint: "sandbox",
    realtimeHost: "custom.realtime.com"  # Deprecated, conflicts with endpoint
  ))
  FAIL("Expected exception for conflicting options")
CATCH AblyException as e:
  ASSERT e.code == 40000 OR e.message CONTAINS "invalid" OR e.message CONTAINS "conflict"
```

---

## REC1b1 - Endpoint conflicts with deprecated fallbackHostsUseDefault option

Tests that specifying both `endpoint` and `fallbackHostsUseDefault` is invalid.

### Setup
```pseudo
# No mock needed - should fail during client construction
```

### Test Steps
```pseudo
TRY:
  client = Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    endpoint: "sandbox",
    fallbackHostsUseDefault: true  # Deprecated, conflicts with endpoint
  ))
  FAIL("Expected exception for conflicting options")
CATCH AblyException as e:
  ASSERT e.code == 40000 OR e.message CONTAINS "invalid" OR e.message CONTAINS "conflict"
```

---

## REC1c2 - Deprecated environment option determines primary domain

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

Tests that specifying both `environment` and `restHost` is invalid.

### Setup
```pseudo
# No mock needed - should fail during client construction
```

### Test Steps
```pseudo
TRY:
  client = Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    environment: "sandbox",
    restHost: "custom.host.com"
  ))
  FAIL("Expected exception for conflicting options")
CATCH AblyException as e:
  ASSERT e.code == 40000 OR e.message CONTAINS "invalid" OR e.message CONTAINS "conflict"
```

---

## REC1c1 - Environment conflicts with realtimeHost

Tests that specifying both `environment` and `realtimeHost` is invalid.

### Setup
```pseudo
# No mock needed - should fail during client construction
```

### Test Steps
```pseudo
TRY:
  client = Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    environment: "sandbox",
    realtimeHost: "custom.realtime.com"
  ))
  FAIL("Expected exception for conflicting options")
CATCH AblyException as e:
  ASSERT e.code == 40000 OR e.message CONTAINS "invalid" OR e.message CONTAINS "conflict"
```

---

## REC1d1 - Deprecated restHost option determines primary domain

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

Tests that default configuration provides the standard fallback domains.

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

Tests that specifying both `fallbackHosts` and `fallbackHostsUseDefault` is invalid.

### Setup
```pseudo
# No mock needed - should fail during client construction
```

### Test Steps
```pseudo
TRY:
  client = Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    fallbackHosts: ["fb1.example.com"],
    fallbackHostsUseDefault: true
  ))
  FAIL("Expected exception for conflicting options")
CATCH AblyException as e:
  ASSERT e.code == 40000 OR e.message CONTAINS "invalid" OR e.message CONTAINS "conflict"
```

---

## REC2b - Deprecated fallbackHostsUseDefault option

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
TRY:
  AWAIT client.time()
  FAIL("Expected exception")
CATCH AblyException:
  PASS
```

### Assertions
```pseudo
# No fallback attempted - only one request
ASSERT mock_http.captured_requests.length == 1
ASSERT mock_http.captured_requests[0].url.host == "custom.ably.example.com"
```

---

## REC2c3 - Nonprod routing policy fallback domains

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

Tests that production routing policy via `endpoint` has corresponding fallback domains.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(500, { "error": { "code": 50000 } })
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "sandbox"
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

## REC2c5 - Production routing policy fallback domains (via deprecated environment)

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
TRY:
  AWAIT client.time()
  FAIL("Expected exception")
CATCH AblyException:
  PASS
```

### Assertions
```pseudo
# No fallback attempted
ASSERT mock_http.captured_requests.length == 1
ASSERT mock_http.captured_requests[0].url.host == "custom.rest.example.com"
```

---

## REC2c6 - Custom realtimeHost has no fallbacks

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
TRY:
  AWAIT client.time()
  FAIL("Expected exception")
CATCH AblyException:
  PASS
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
```

---

## REC3b - Custom connectivity check URL

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
```

---

## REC3 - Connectivity check response validation

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
```
