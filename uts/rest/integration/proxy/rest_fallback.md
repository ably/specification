# REST Fallback Proxy Integration Tests

Spec points: `RSC15l`, `RSC15l2`, `RSC15l4`

## Test Type

Proxy integration test against Ably Sandbox endpoint

## Proxy Infrastructure

See `uts/realtime/integration/helpers/proxy.md` for the full proxy infrastructure specification.

## Corresponding Unit Tests

- `uts/rest/unit/fallback.md` -- RSC15l/RSC15l4 (unit test verifies fallback logic with mocked HTTP)

## Purpose

These tests verify fallback host retry behaviour that cannot be fully tested
with mocked HTTP because the `shouldFallback` classification varies by
platform. By exercising the SDK's real HTTP client through the proxy, we
confirm the actual retry behaviour end-to-end.

## Sandbox Setup

Tests run against the Ably Sandbox via a programmable proxy.

### App Provisioning

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

### Common Cleanup

```pseudo
AFTER EACH TEST:
  IF session IS NOT null:
    session.close()
```

### Fallback Host Configuration

These tests need fallback hosts enabled. `endpoint: "localhost"` would normally
disable automatic fallback host selection (REC2c2), but explicitly providing
`fallbackHosts: ["localhost"]` overrides this. Both the primary and fallback
requests route through the same proxy, with `times: 1` rules ensuring only the
first request is faulted.

---

## RSC15l2 - Request timeout triggers fallback via proxy

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
  endpoint: "sandbox",
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

| Spec | Requirement |
|------|-------------|
| RSC15l4 | A response with a `Server: CloudFront` header and HTTP status >= 400 should trigger fallback |

Tests that when the proxy returns an HTTP 403 with a `Server: CloudFront`
header, the SDK treats it as a retryable server error and retries on a
fallback host.

### Setup

```pseudo
session = create_proxy_session(
  endpoint: "sandbox",
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
