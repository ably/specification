# Logging Tests

Spec points: `RSC2`, `RSC3`, `RSC4`, `TO3b`, `TO3c`

## Test Type
Unit test with mocked HTTP client

## Mock Configuration

These tests use the mock HTTP infrastructure defined in `rest_client.md`. The mock supports:
- Handler-based configuration with `onConnectionAttempt` and `onRequest`
- Capturing requests via `captured_requests` arrays
- Configurable responses with status codes, bodies, and headers

See `rest_client.md` for detailed mock interface documentation.

## Purpose

Tests the logging support for the Ably client. The logging API uses a structured
format where each log event has a fixed message string and a context map of
key-value pairs, rather than interpolated strings.

The `LogHandler` signature is:
```
LogHandler(level: LogLevel, message: String, context: Map<String, dynamic>)
```

---

## RSC2 - Default log level is warn

**Spec requirement:** The default log level is `warn`. Only `error` and `warn` level
events should be emitted when the default level is used.

### Setup
```pseudo
captured_logs = []

mock_http = MockHttpClient(
  onRequest: (req) => req.respond_with(200, [1704067200000])
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "app.key:secret",
  logHandler: (level, message, context) => captured_logs.push({level, message, context})
))
```

### Test Steps
```pseudo
AWAIT client.time()

# Default level is warn, so info/debug/verbose messages should be filtered
ASSERT ALL log IN captured_logs: log.level IN [error, warn]
```

---

## TO3b - Log level can be changed

**Spec requirement:** The log level can be changed via `ClientOptions.logLevel`.
Setting the level to `verbose` should capture all log events.

### Setup
```pseudo
captured_logs = []

mock_http = MockHttpClient(
  onRequest: (req) => req.respond_with(200, [1704067200000])
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "app.key:secret",
  logLevel: verbose,
  logHandler: (level, message, context) => captured_logs.push({level, message, context})
))
```

### Test Steps
```pseudo
AWAIT client.time()

# With verbose, should have info+debug+verbose messages
info_logs = captured_logs.filter(l => l.level == info)
ASSERT info_logs.length > 0

# Must have an info log for the time() method entry (not checked directly,
# but client creation emits "Client created" at info level)
ASSERT ANY log IN captured_logs: log.level == info

# Must have a debug log for the HTTP request
debug_logs = captured_logs.filter(l => l.level == debug)
ASSERT ANY log IN debug_logs: log.message CONTAINS "HTTP request"
```

---

## TO3c - Custom log handler receives structured events

**Spec requirement:** A custom log handler provided via `ClientOptions.logHandler`
receives structured log events with level, message, and context.

### Setup
```pseudo
captured_logs = []

mock_http = MockHttpClient(
  onRequest: (req) => req.respond_with(200, [1704067200000])
)
install_mock(mock_http)

handler = (level, message, context) => captured_logs.push({level, message, context})

client = Rest(options: ClientOptions(
  key: "app.key:secret",
  logLevel: info,
  logHandler: handler
))
```

### Test Steps
```pseudo
AWAIT client.time()

# Custom handler was called
ASSERT captured_logs.length > 0

# Structured context is provided
ASSERT ANY log IN captured_logs: log.context IS NOT EMPTY
```

---

## TO3c2 - Structured context contains expected keys

**Spec requirement:** The structured context map contains relevant key-value pairs
for the log event. HTTP request logs include method, host, and path.

### Setup
```pseudo
captured_logs = []

mock_http = MockHttpClient(
  onRequest: (req) => req.respond_with(200, [1704067200000])
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "app.key:secret",
  logLevel: debug,
  logHandler: (level, message, context) => captured_logs.push({level, message, context})
))
```

### Test Steps
```pseudo
AWAIT client.time()

# Find the HTTP request log
http_logs = captured_logs.filter(l => l.message CONTAINS "HTTP request" AND l.level == debug)
ASSERT http_logs.length >= 1
ASSERT "method" IN http_logs[0].context
ASSERT "host" IN http_logs[0].context
ASSERT "path" IN http_logs[0].context
```

---

## RSC2b - LogLevel.none produces no log events

**Spec requirement:** Setting log level to `none` should suppress all log output.

### Setup
```pseudo
captured_logs = []

mock_http = MockHttpClient(
  onRequest: (req) => req.respond_with(200, [1704067200000])
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "app.key:secret",
  logLevel: none,
  logHandler: (level, message, context) => captured_logs.push({level, message, context})
))
```

### Test Steps
```pseudo
AWAIT client.time()

# No logs should be captured
ASSERT captured_logs.length == 0
```
