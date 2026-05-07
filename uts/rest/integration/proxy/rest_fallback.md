# REST Fallback Proxy Integration Tests

Spec points: `RSC15l`, `RSC15l2`, `RSC15l4`, `RSL1k4`

## Test Type

Proxy integration test against Ably Sandbox endpoint

## Proxy Infrastructure

See `uts/realtime/integration/helpers/proxy.md` for the full proxy infrastructure specification.

## Corresponding Unit Tests

- `uts/rest/unit/fallback.md` -- RSC15l/RSC15l4 (unit test verifies fallback logic with mocked HTTP)
- `uts/rest/unit/publish.md` -- RSL1k (unit test verifies idempotent publish logic with mocked HTTP)

## Purpose

These tests verify fallback host retry behaviour and HTTP error handling that
cannot be fully tested with mocked HTTP because the `shouldFallback`
classification and error surfacing vary by platform. By exercising the SDK's
real HTTP client through the proxy (or directly against an unreachable
endpoint), we confirm the actual retry and error-parsing behaviour end-to-end.

## Sandbox Setup

Tests run against the Ably Sandbox via a programmable proxy.

### App Provisioning

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox.realtime.ably-nonprod.net/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox.realtime.ably-nonprod.net/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

### Common Cleanup

```pseudo
AFTER EACH TEST:
  IF session IS NOT null:
    session.close()
```

### Token Auth Helper

```pseudo
function token_auth_callback(api_key):
  RETURN (params, cb) => {
    # Create a temporary Rest client pointed directly at the sandbox (bypassing the proxy)
    # and use it to obtain a TokenDetails object
    inner_rest = Rest(options: ClientOptions(
      key: api_key,
      endpoint: SANDBOX_ENDPOINT
    ))
    inner_rest.auth.requestToken().then(
      (token) => cb(null, token),
      (err) => cb(err, null)
    )
  }
```

Note: The sandbox endpoint is used directly (not through the proxy) so that token requests are never intercepted by proxy fault-injection rules.

### Fallback Host Configuration

These tests need fallback hosts enabled. `endpoint: "localhost"` would normally
disable automatic fallback host selection (REC2c2), but explicitly providing
`fallbackHosts: ["localhost"]` overrides this. Both the primary and fallback
requests route through the same proxy, with `times: 1` rules ensuring only the
first request is faulted.

---

## RSC15l2 - Request timeout triggers fallback via proxy

**Test ID**: `rest/proxy/RSC15l2/timeout-triggers-fallback-0`

| Spec | Requirement |
|------|-------------|
| RSC15l | Errors that necessitate use of an alternative host |
| RSC15l2 | Request timeout triggers fallback |

Tests that when an HTTP request times out after the connection is established,
the SDK retries on a fallback host. The proxy delays the first HTTP response
beyond the SDK's `httpRequestTimeout`, causing a timeout. The retry goes to
a fallback host (also routed through the proxy) and succeeds.

### Setup

```pseudo
session = create_proxy_session(
  endpoint: "nonprod:sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "http_request", "pathContains": "/time" },
    "action": {
      "type": "http_delay",
      "delayMs": 20000
    },
    "times": 1,
    "comment": "RSC15l2: Delay first /time request beyond httpRequestTimeout"
  }]
)

client = Rest(options: ClientOptions(
  authCallback: token_auth_callback(api_key),
  endpoint: "localhost",
  fallbackHosts: ["localhost"],
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  httpRequestTimeout: 3000
))
```

### Test Steps

```pseudo
result = AWAIT client.time()
```

### Assertions

```pseudo
# The request should succeed (retried on fallback after timeout)
ASSERT result IS number

# Proxy event log shows at least two HTTP requests to /time
log = session.get_log()
http_requests = log.filter(e => e.type == "http_request" AND e.path CONTAINS "/time")
ASSERT http_requests.length >= 2
```

---

## RSC15l4 - CloudFront Server header triggers fallback via proxy

**Test ID**: `rest/proxy/RSC15l4/cloudfront-header-fallback-0`

| Spec | Requirement |
|------|-------------|
| RSC15l4 | A response with a `Server: CloudFront` header and HTTP status >= 400 should trigger fallback |

Tests that when the proxy returns an HTTP 403 with a `Server: CloudFront`
header, the SDK treats it as a retryable server error and retries on a
fallback host.

### Setup

```pseudo
session = create_proxy_session(
  endpoint: "nonprod:sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "http_request", "pathContains": "/time" },
    "action": {
      "type": "http_respond",
      "status": 403,
      "body": { "error": { "message": "Forbidden", "code": 40300, "statusCode": 403 } },
      "headers": { "Server": "CloudFront" }
    },
    "times": 1,
    "comment": "RSC15l4: CloudFront 403 on first /time request"
  }]
)

client = Rest(options: ClientOptions(
  authCallback: token_auth_callback(api_key),
  endpoint: "localhost",
  fallbackHosts: ["localhost"],
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
result = AWAIT client.time()
```

### Assertions

```pseudo
# The request should succeed (retried on fallback after CloudFront error)
ASSERT result IS number

# Proxy event log shows at least two HTTP requests to /time
log = session.get_log()
http_requests = log.filter(e => e.type == "http_request" AND e.path CONTAINS "/time")
ASSERT http_requests.length >= 2

# First response was the injected 403 with CloudFront header
http_responses = log.filter(e => e.type == "http_response")
ASSERT http_responses[0].status == 403
```

---

## Unreachable endpoint surfaces correct error (no proxy)

**Test ID**: `rest/proxy/RSC15l/unreachable-endpoint-error-0`

Tests that when the SDK's HTTP client cannot connect to the target host at all
(ECONNREFUSED), the error is surfaced as a usable ErrorInfo-like object with
status/code information. This test does NOT use the proxy -- it points the SDK
at a port where nothing is listening.

### Setup

```pseudo
# No proxy session needed for this test.

# Pick a port that is not listening (e.g. 19999).
non_listening_port = 19999

# Use token auth via authCallback so the SDK can authenticate without
# contacting the dead endpoint. The inner Rest client talks directly to the
# sandbox to obtain a token.
client = Rest(options: ClientOptions(
  authCallback: token_auth_callback(api_key),
  endpoint: "localhost",
  port: non_listening_port,
  tls: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
AWAIT client.time() FAILS WITH error
```

### Assertions

```pseudo
# The error is an ErrorInfo-like object with a statusCode or code
# (the exact code/statusCode depends on the SDK's HTTP layer, but it must
# be present and non-null so callers can programmatically handle it)
ASSERT error IS NOT null
ASSERT error.statusCode IS NOT null OR error.code IS NOT null
```

---

## Connection drop mid-response retried on fallback (http_drop)

**Test ID**: `rest/proxy/RSC15l/connection-drop-fallback-1`

| Spec | Requirement |
|------|-------------|
| RSC15l | Errors that necessitate use of an alternative host |

Tests that when the proxy drops the TCP connection mid-request (simulating
ECONNRESET), the SDK classifies this as a retryable error and retries on a
fallback host. The proxy drops the first `/time` request, then passes through
on the retry.

### Setup

```pseudo
session = create_proxy_session(
  endpoint: "nonprod:sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "http_request", "pathContains": "/time" },
    "action": {
      "type": "http_drop"
    },
    "times": 1,
    "comment": "Drop TCP connection on first /time request (ECONNRESET)"
  }]
)

client = Rest(options: ClientOptions(
  authCallback: token_auth_callback(api_key),
  endpoint: "localhost",
  fallbackHosts: ["localhost"],
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
result = AWAIT client.time()
```

### Assertions

```pseudo
# The request should succeed (retried on fallback after connection drop)
ASSERT result IS number

# Proxy event log shows at least two HTTP requests to /time
log = session.get_log()
http_requests = log.filter(e => e.type == "http_request" AND e.path CONTAINS "/time")
ASSERT http_requests.length >= 2
```

---

## HTTP 5xx with JSON error body -- error parsed correctly (http_respond 503)

**Test ID**: `rest/proxy/RSC15l/http-5xx-json-error-parsed-0`

Tests that when the proxy returns an HTTP 503 with a well-formed JSON error
body (containing an `error` object with `code`, `statusCode`, and `message`),
the SDK parses the ErrorInfo fields from the response body. No fallback hosts
are configured, so the error propagates directly to the caller.

### Setup

```pseudo
session = create_proxy_session(
  endpoint: "nonprod:sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "http_request", "pathContains": "/time" },
    "action": {
      "type": "http_respond",
      "status": 503,
      "body": { "error": { "code": 50300, "statusCode": 503, "message": "Service temporarily unavailable" } }
    },
    "times": 1,
    "comment": "Return 503 with JSON error body on first /time request"
  }]
)

# No fallbackHosts -- endpoint="localhost" disables fallback (REC2c2)
client = Rest(options: ClientOptions(
  authCallback: token_auth_callback(api_key),
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
AWAIT client.time() FAILS WITH error
```

### Assertions

```pseudo
# The SDK parsed the error fields from the JSON response body
ASSERT error.code == 50300
ASSERT error.statusCode == 503
ASSERT error.message CONTAINS "Service temporarily unavailable"
```

---

## HTTP 5xx without JSON error body -- error synthesized (http_respond 503)

**Test ID**: `rest/proxy/RSC15l/http-5xx-no-json-synthesized-1`

Tests that when the proxy returns an HTTP 503 with a JSON body that does NOT
contain an `error` field (e.g. `{}`), the SDK still produces a usable error
from the HTTP status code alone. This is the closest the proxy can get to a
non-parseable body while still returning valid JSON.

### Setup

```pseudo
session = create_proxy_session(
  endpoint: "nonprod:sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "http_request", "pathContains": "/time" },
    "action": {
      "type": "http_respond",
      "status": 503,
      "body": {}
    },
    "times": 1,
    "comment": "Return 503 with empty JSON body (no error field) on first /time request"
  }]
)

# No fallbackHosts -- endpoint="localhost" disables fallback (REC2c2)
client = Rest(options: ClientOptions(
  authCallback: token_auth_callback(api_key),
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
AWAIT client.time() FAILS WITH error
```

### Assertions

```pseudo
# The SDK synthesized an error from the HTTP status code
ASSERT error.statusCode == 503
```

---

## HTTP 4xx with JSON error body -- not retried, error parsed (http_respond 403)

**Test ID**: `rest/proxy/RSC15l/http-4xx-not-retried-0`

Tests that when the proxy returns an HTTP 403 (a 4xx client error) with a
well-formed JSON error body, the SDK does NOT retry on fallback hosts -- even
when fallback hosts are configured -- and instead propagates the parsed error
directly to the caller. Only 5xx and certain special cases (RSC15l4 CloudFront)
should trigger fallback; 4xx errors indicate a client-side problem.

### Setup

```pseudo
session = create_proxy_session(
  endpoint: "nonprod:sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "http_request", "pathContains": "/time" },
    "action": {
      "type": "http_respond",
      "status": 403,
      "body": { "error": { "code": 40300, "statusCode": 403, "message": "Forbidden" } }
    },
    "times": 1,
    "comment": "Return 403 with JSON error body on first /time request"
  }]
)

# Fallback hosts ARE configured -- but 403 should NOT trigger fallback
client = Rest(options: ClientOptions(
  authCallback: token_auth_callback(api_key),
  endpoint: "localhost",
  fallbackHosts: ["localhost"],
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
AWAIT client.time() FAILS WITH error
```

### Assertions

```pseudo
# The SDK parsed the error fields from the JSON response body
ASSERT error.code == 40300
ASSERT error.statusCode == 403

# Proxy event log shows exactly 1 HTTP request to /time (no fallback retry)
log = session.get_log()
http_requests = log.filter(e => e.type == "http_request" AND e.path CONTAINS "/time")
ASSERT http_requests.length == 1
```

---

## RSL1k4 - Idempotent publish retry deduplication

**Test ID**: `rest/proxy/RSL1k4/idempotent-retry-dedup-0`

| Spec | Requirement |
|------|-------------|
| RSL1k4 | An explicit test for idempotency of publishes with library-generated ids shall exist that simulates an error response to a successful publish, expects an automatic retry by the library, and verifies that the batch is published only once |

### Proxy Action

This test uses the `http_replace_response` proxy action, which forwards the
request to the upstream server (so the publish actually succeeds), discards
the real response, and returns a fake 5xx error response to the client. This
causes the SDK to believe the publish failed and retry it, while the server
already persisted the message. The server then deduplicates the retry based
on the library-generated message `id`.

#### Setup

```pseudo
session = create_proxy_session(
  endpoint: "nonprod:sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "http_request", "method": "POST", "pathContains": "/channels/" },
    "action": {
      "type": "http_replace_response",
      "status": 503,
      "body": { "error": { "code": 50300, "statusCode": 503, "message": "Service temporarily unavailable" } }
    },
    "times": 1,
    "comment": "RSL1k4: Forward first publish to server, then return fake 503 to client"
  }]
)

client = Rest(options: ClientOptions(
  authCallback: token_auth_callback(api_key),
  endpoint: "localhost",
  fallbackHosts: ["localhost"],
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  idempotentRestPublishing: true
))

channel_name = "test-RSL1k4-idempotent-" + random_string()
channel = client.channels.get(channel_name)
```

#### Test Steps

```pseudo
# Publish a message -- first attempt succeeds server-side but client sees 503,
# SDK retries, server deduplicates the retry
AWAIT channel.publish("test", "data")
```

#### Assertions

```pseudo
# The publish completed successfully (SDK retried after the fake 503)
# No error thrown

# Verify via history that only one copy of the message exists
# (server deduplicated the retry based on the library-generated message id)
history = AWAIT channel.history()
matching = history.items.filter(m => m.name == "test" AND m.data == "data")
ASSERT matching.length == 1

# Proxy event log shows at least two POST requests to /channels/
log = session.get_log()
http_requests = log.filter(e => e.type == "http_request" AND e.method == "POST" AND e.path CONTAINS "/channels/")
ASSERT http_requests.length >= 2
```
