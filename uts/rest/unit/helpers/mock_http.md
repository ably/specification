# Mock HTTP Infrastructure

This document specifies the mock HTTP infrastructure for REST unit tests. All REST unit tests that need to intercept HTTP requests should reference this document.

## Purpose

The mock infrastructure enables unit testing of REST client behavior without making real network calls. It supports:

1. **Intercepting HTTP requests** - Capture the URL, headers, method, and body of outgoing requests
2. **Controlling request outcomes** - Simulate various connection results including successful responses, connection refused, DNS errors, timeouts, and other network-level failures
3. **Injecting responses** - Configure responses (status, headers, body) to be returned
4. **Capturing requests** - Record all request details for test assertions

## Installation Mechanism

The mechanism for injecting the mock is implementation-specific and not part of the public API. Possible approaches include:

- Dependency injection of HTTP client interface
- Platform-specific mocking (e.g., URLProtocol in Swift, HttpClientHandler in .NET)
- Test doubles or mocking frameworks
- Package-level variable substitution

## Mock Interface

```pseudo
interface MockHttpClient:
  # Awaitable event triggers for test code
  await_connection_attempt(timeout?: Duration): Future<PendingConnection>
  await_request(timeout?: Duration): Future<PendingRequest>
  
  # Test management
  reset()  # Clear all state

interface PendingConnection:
  host: String
  port: Int
  tls: Boolean
  timestamp: Time
  
  # Methods for test code to respond to the connection attempt
  respond_with_success()  # Connection succeeds, allows HTTP requests
  respond_with_refused()  # Connection refused at network level
  respond_with_timeout()  # Connection times out (unresponsive)
  respond_with_dns_error()  # DNS resolution fails

interface PendingRequest:
  url: URL
  method: String  # GET, POST, etc.
  headers: Map<String, String>
  body: Bytes
  timestamp: Time
  
  # Methods for test code to respond to the HTTP request
  respond_with(status: Int, body: Any, headers?: Map<String, String>)
  respond_with_delay(delay: Duration, status: Int, body: Any, headers?: Map<String, String>)
  respond_with_timeout()  # Request timeout (after connection established)
```

## Handler-Based Configuration

For simple test scenarios, implementations may support handler-based configuration:

```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
  },
  onRequest: (req) => {
    IF req.url.path == "/time":
      req.respond_with(200, {"time": 1234567890000})
    ELSE:
      req.respond_with(404, {"error": {"code": 40400}})
  }
)
```

Handlers are called automatically when connection attempts or requests occur. The await-based API should always be available for tests that need to coordinate responses with test state.

### When to Use Each Pattern

**Handler pattern** (recommended for most tests):
- Response is predetermined based on URL, method, or request count
- Simple scenarios with known request/response pairs
- No need to coordinate with external test state

**Await pattern** (for advanced scenarios):
- Need to inspect request details before deciding how to respond
- Test logic depends on external state not known at setup time
- Complex coordination between request timing and test assertions

## Example: Handler Pattern

```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {"time": 1234567890000})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

result = AWAIT client.time()

ASSERT captured_requests.length == 1
ASSERT captured_requests[0].url.path == "/time"
```

## Example: Handler with State (Different Responses by Count)

```pseudo
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    request_count++
    IF request_count == 1:
      req.respond_with(500, {"error": {"code": 50000}})
    ELSE:
      req.respond_with(200, {"time": 1234567890000})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# First request fails, triggers retry, second succeeds
result = AWAIT client.time()

ASSERT request_count == 2
```

## Example: Await Pattern

```pseudo
mock_http = MockHttpClient()
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# Start request in background
request_future = client.time()

# Wait for and handle connection
connection = AWAIT mock_http.await_connection_attempt()
connection.respond_with_success()

# Wait for and handle HTTP request
request = AWAIT mock_http.await_request()
ASSERT request.headers["X-Ably-Version"] IS NOT null
request.respond_with(200, {"time": 1234567890000})

# Complete the operation
result = AWAIT request_future
```

## Connection-Level Failures

The mock distinguishes between connection-level and request-level failures:

**Connection-level failures** (handled by `PendingConnection`):
- `respond_with_refused()` - TCP connection refused
- `respond_with_timeout()` - Connection attempt times out
- `respond_with_dns_error()` - DNS resolution fails

**Request-level failures** (handled by `PendingRequest`):
- `respond_with(4xx/5xx, ...)` - HTTP error response
- `respond_with_timeout()` - Request times out after connection established

```pseudo
# Connection refused example
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_refused()
)

# vs HTTP 500 error example
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(500, {"error": {...}})
)
```

## Test Isolation

Each test should:

1. Create a fresh mock HTTP client
2. Install/inject the mock
3. Create the REST client
4. Perform test steps and assertions
5. Clean up the mock

```pseudo
BEFORE EACH TEST:
  mock_http = MockHttpClient()
  install_mock(mock_http)

AFTER EACH TEST:
  uninstall_mock()
```

## Timer Mocking for Timeouts

Tests that verify timeout behavior should use timer mocking where practical to avoid slow tests.

**Approaches (in order of preference):**

1. **Mock/fake timers** - Use framework-provided timer mocking
   ```pseudo
   enable_fake_timers()
   request_future = client.time()
   ADVANCE_TIME(1000)  # Instantly trigger timeout
   ```

2. **Dependency injection** - Library accepts clock interface in tests

3. **Short timeouts** - Use very short timeout values
   ```pseudo
   client = Rest(options: ClientOptions(httpRequestTimeout: 50))
   ```

4. **Actual delays** - Last resort if mocking unavailable
