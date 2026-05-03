# REST Fault Proxy Integration Tests

Spec points: `RSC10`, `RSC15m`, `REC2c2`, `RTL6`

## Test Type

Proxy integration test against Ably Sandbox endpoint

## Proxy Infrastructure

See `uts/test/realtime/integration/helpers/proxy.md` for the full proxy infrastructure specification.

## Corresponding Unit Tests

- `uts/test/rest/unit/auth/token_renewal.md` -- RSC10 (unit test verifies token renewal logic with mocked HTTP)
- `uts/test/rest/unit/fallback.md` -- RSC15m/REC2c2 (unit test verifies fallback/error handling with mocked HTTP)
- `uts/test/realtime/unit/channels/channel_publish.md` -- RTL6 (unit test verifies publish request formation)

## Sandbox Setup

Tests run against the Ably Sandbox via a programmable proxy.

### App Provisioning

```pseudo
BEFORE ALL TESTS:
  # Provision test app
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  # Clean up test app
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

### Common Cleanup

```pseudo
AFTER EACH TEST:
  IF client IS NOT null:
    # For Realtime clients, close the connection
    IF client HAS connection AND client.connection.state IN [connected, connecting, disconnected]:
      client.connection.close()
      AWAIT_STATE client.connection.state == ConnectionState.closed
        WITH timeout: 10 seconds
  IF session IS NOT null:
    session.close()
```

### Token Auth Helper

```pseudo
function request_token_from_sandbox(api_key, token_params):
  # Split API key into key name and secret
  key_name = api_key.split(":")[0]
  key_secret = api_key.split(":")[1]

  # Request a token from the sandbox REST API
  response = POST https://sandbox-rest.ably.io/keys/{key_name}/requestToken
    WITH Authorization: Basic base64(api_key)
    WITH body: token_params OR {}

  RETURN parse_json(response.body)  # TokenDetails
```

---

## Test 18: RSC10 -- Token renewal on HTTP 401 (40142)

| Spec | Requirement |
|------|-------------|
| RSC10 | When a REST request receives a 401 with a token error (40140-40149), the SDK should renew the token and retry the request |

Tests that when an authenticated REST request receives an HTTP 401 with error code 40142 (token expired), the SDK transparently renews the token via `authCallback` and retries the request. The proxy returns 401 on the first HTTP request to a channel endpoint, then passes through subsequent requests.

### Setup

```pseudo
# Track authCallback invocations
auth_callback_count = 0

# Create proxy session that returns 401 on the first channel request
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "http_request", "pathContains": "/channels/" },
    "action": {
      "type": "http_respond",
      "status": 401,
      "body": { "error": { "code": 40142, "statusCode": 401, "message": "Token expired" } }
    },
    "times": 1,
    "comment": "RSC10: Return 401 on first channel request, then passthrough"
  }]
)

# Use token auth with authCallback so the SDK can renew
client = Rest(options: ClientOptions(
  authCallback: (params) => {
    auth_callback_count++
    # Request a token from the sandbox using the API key
    token_details = request_token_from_sandbox(api_key, params)
    RETURN token_details
  },
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false
))

channel_name = "test-RSC10-token-renewal-" + random_string()
channel = client.channels.get(channel_name)
```

### Test Steps

```pseudo
# Publish a message -- first request gets 401, SDK renews token, retries
result = AWAIT channel.publish("test-event", "hello")

# The publish should succeed (SDK transparently renewed and retried)
```

### Assertions

```pseudo
# Publish completed successfully (no error thrown)
ASSERT result IS successful

# authCallback was called at least twice (initial token + renewal after 401)
ASSERT auth_callback_count >= 2

# Proxy event log shows two HTTP requests to the channel endpoint
log = session.get_log()
http_requests = log.filter(e => e.type == "http_request" AND e.path CONTAINS "/channels/")
ASSERT http_requests.length >= 2

# First request was intercepted (got 401), second request passed through (got 2xx)
http_responses = log.filter(e => e.type == "http_response")
ASSERT http_responses[0].status == 401
ASSERT http_responses[1].status IN [200, 201]
```

---

## Test 19: RSC15m / REC2c2 -- HTTP 503 error with fallback hosts disabled

| Spec | Requirement |
|------|-------------|
| RSC15m | When the set of fallback domains is empty, failing HTTP requests that would have qualified for a retry against a fallback host will instead result in an error immediately |
| REC2c2 | Fallback hosts are automatically disabled when `endpoint` is set to an explicit hostname |

Tests that when a REST request receives an HTTP 503 (Service Unavailable) and the client is configured with `endpoint: "localhost"` (which disables fallback hosts per REC2c2), the SDK returns the error to the caller without attempting fallback hosts.

### Setup

```pseudo
# Create proxy session that returns 503 on the first channel request
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: [{
    "match": { "type": "http_request", "pathContains": "/channels/" },
    "action": {
      "type": "http_respond",
      "status": 503,
      "body": { "error": { "code": 50300, "statusCode": 503, "message": "Service temporarily unavailable" } }
    },
    "times": 1,
    "comment": "RSC15m: Return 503 on first channel request"
  }]
)

# Use key auth (Basic auth not possible over non-TLS, so use token auth)
client = Rest(options: ClientOptions(
  authCallback: (params) => {
    token_details = request_token_from_sandbox(api_key, params)
    RETURN token_details
  },
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false
))

channel_name = "test-RSC15m-503-error-" + random_string()
channel = client.channels.get(channel_name)
```

### Test Steps

```pseudo
# Try to publish a message -- should fail with 503 error
AWAIT channel.publish("test-event", "hello") FAILS WITH error
```

### Assertions

```pseudo
# The error propagates to the caller with the correct error code
ASSERT error.code == 50300
ASSERT error.statusCode == 503

# Proxy event log shows only one HTTP request to the channel endpoint
# (no fallback attempts since endpoint="localhost" disables fallback hosts)
log = session.get_log()
http_requests = log.filter(e => e.type == "http_request" AND e.path CONTAINS "/channels/")
ASSERT http_requests.length == 1
```

---

## Test 20: RTL6 -- End-to-end publish and history through proxy

| Spec | Requirement |
|------|-------------|
| RTL6 | Messages published via a Realtime connection should be deliverable and retrievable |

Tests that the proxy transparently forwards both WebSocket and HTTP traffic without interfering with normal operation. A Realtime client publishes a message through the proxy, and a REST client retrieves it via channel history, also through the proxy. This is a "golden path" test that validates the proxy infrastructure itself.

### Setup

```pseudo
# Create proxy session with no rules (pure passthrough)
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: []
)

# Create Realtime client through proxy for publishing
realtime_client = Realtime(options: ClientOptions(
  authCallback: (params) => {
    token_details = request_token_from_sandbox(api_key, params)
    RETURN token_details
  },
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,
  autoConnect: false
))

# Create REST client through proxy for history retrieval
rest_client = Rest(options: ClientOptions(
  authCallback: (params) => {
    token_details = request_token_from_sandbox(api_key, params)
    RETURN token_details
  },
  endpoint: "localhost",
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false
))

channel_name = "test-RTL6-publish-history-" + random_string()
realtime_channel = realtime_client.channels.get(channel_name)
rest_channel = rest_client.channels.get(channel_name)
```

### Test Steps

```pseudo
# Connect Realtime client through proxy
realtime_client.connect()
AWAIT_STATE realtime_client.connection.state == ConnectionState.connected
  WITH timeout: 15 seconds

# Attach to the channel
AWAIT realtime_channel.attach()
AWAIT_STATE realtime_channel.state == ChannelState.attached
  WITH timeout: 10 seconds

# Publish a message via Realtime
AWAIT realtime_channel.publish("test-msg", "hello world")

# Brief pause to allow the message to be persisted on the server
# (history is eventually consistent)
poll_until(
  condition: () => {
    history = AWAIT rest_channel.history()
    RETURN history.items.length > 0
  },
  interval: 500ms,
  timeout: 10 seconds
)

# Retrieve channel history via REST
history = AWAIT rest_channel.history()
```

### Assertions

```pseudo
# History contains the published message
ASSERT history.items.length >= 1

# Find the published message in history
published_msg = history.items.find(m => m.name == "test-msg")
ASSERT published_msg IS NOT null
ASSERT published_msg.data == "hello world"

# Proxy event log shows both WebSocket and HTTP traffic
log = session.get_log()

# At least one WebSocket connection was made (Realtime client)
ws_connects = log.filter(e => e.type == "ws_connect")
ASSERT ws_connects.length >= 1

# At least one HTTP request was made (REST history call + token requests)
http_requests = log.filter(e => e.type == "http_request")
ASSERT http_requests.length >= 1
```

### Cleanup

```pseudo
# Close the Realtime client
realtime_client.connection.close()
AWAIT_STATE realtime_client.connection.state == ConnectionState.closed
  WITH timeout: 10 seconds
```

---

## Integration Test Notes

### Timeout Handling

All `AWAIT_STATE` calls use generous timeouts because real network traffic is involved:
- Connection to CONNECTED via proxy: 15 seconds (allows for auth + transport setup)
- Channel attach: 10 seconds
- History polling: 10 seconds (allows for eventual consistency)
- Cleanup close: 10 seconds

### Authentication Through Proxy

All tests use `authCallback` with token auth rather than API key auth. This is required because:
1. `tls: false` is needed for proxy tests (proxy serves plain HTTP/WS with TLS only upstream)
2. RSC18 prohibits Basic auth over non-TLS connections
3. `authCallback` makes tokens renewable, which is needed for RSC10 (token renewal test)

The `authCallback` requests tokens directly from the sandbox REST API (bypassing the proxy) using the API key. Only the SDK's own HTTP/WebSocket traffic goes through the proxy.

### Fallback Host Behaviour

With `endpoint: "localhost"`, fallback hosts are automatically disabled (REC2c2). This means:
- RSC15m/REC2c2: The SDK will NOT attempt fallback hosts after a 5xx error when fallback hosts are disabled
- The error propagates directly to the caller
- The proxy log will show only a single HTTP request (no fallback attempts)

### Why Proxy Tests for REST Faults

These tests verify behaviour that unit tests cover with mocked HTTP, but provide higher confidence because:
1. **Real HTTP connections** -- the SDK's actual HTTP client is exercised through the proxy
2. **Real token renewal** -- RSC10 exercises the full authCallback flow against the sandbox
3. **Real error responses** -- the proxy returns correctly-formatted HTTP error responses
4. **End-to-end verification** -- RTL6 confirms publish and history work through the proxy infrastructure
