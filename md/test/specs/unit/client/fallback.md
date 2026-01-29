# Host Fallback Tests

Spec points: `RSC15`, `RSC15a`, `RSC15f`, `RSC15j`, `RSC15l`, `RSC15m`, `REC1`, `REC2`

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

## REC1, REC2 - Custom endpoint and fallback configuration

Tests various endpoint configuration options.

### Test Cases

| ID | Options | Expected Primary | Expected Fallbacks |
|----|---------|-----------------|-------------------|
| 1 | default | `main.realtime.ably.net` | `main.[a-e].fallback.ably-realtime.com` |
| 2 | `endpoint: "sandbox"` | `sandbox.realtime.ably.net` | `sandbox.[a-e].fallback.ably-realtime.com` |
| 3 | `restHost: "custom.host.com"` | `custom.host.com` | (empty) |
| 4 | `fallbackHosts: ["fb1.com", "fb2.com"]` | `main.realtime.ably.net` | `["fb1.com", "fb2.com"]` |

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(200, { "time": 1234567890000 })
```

### Test Steps (Case 1 - Default)
```pseudo
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
AWAIT client.time()

ASSERT mock_http.captured_requests[0].url.host == "main.realtime.ably.net"
```

### Test Steps (Case 2 - Environment)
```pseudo
mock_http.reset()
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  endpoint: "sandbox"
))
AWAIT client.time()

ASSERT mock_http.captured_requests[0].url.host == "sandbox.realtime.ably.net"
```

### Test Steps (Case 3 - Custom host, no fallback)
```pseudo
mock_http.reset()
mock_http.queue_response(500, { "error": {} })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  restHost: "custom.host.com"
))

TRY:
  AWAIT client.time()
CATCH:
  PASS

# No fallback attempted with custom host
ASSERT mock_http.captured_requests.length == 1
ASSERT mock_http.captured_requests[0].url.host == "custom.host.com"
```

### Test Steps (Case 4 - Custom fallbacks)
```pseudo
mock_http.reset()
mock_http.queue_response(500, { "error": {} })
mock_http.queue_response(200, { "time": 1234567890000 })

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  fallbackHosts: ["fb1.example.com", "fb2.example.com"]
))

AWAIT client.time()

ASSERT mock_http.captured_requests[0].url.host == "main.realtime.ably.net"
ASSERT mock_http.captured_requests[1].url.host IN ["fb1.example.com", "fb2.example.com"]
```
