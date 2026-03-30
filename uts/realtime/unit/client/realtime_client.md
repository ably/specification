# Realtime Client Tests

Spec points: `RTC1`, `RTC1a`, `RTC1b`, `RTC1c`, `RTC1f`, `RTC2`, `RTC3`, `RTC4`, `RTC12`, `RTC15`, `RTC16`, `RTC17`

## Test Type
Unit test with mocked WebSocket connection

## Pseudocode Conventions

### Type Assertions

Type assertions in pseudocode (e.g., `ASSERT client.connection IS Connection`) verify that an object has the expected type or interface. Implementation varies by language:

- **Strongly typed languages** (Dart, Swift, Kotlin, TypeScript): Use native type checks or casting verification
- **Weakly typed languages** (JavaScript, Python, Ruby): Verify the object has the expected methods/properties instead of checking type directly

**Example:**
```pseudo
# Pseudocode
ASSERT client.connection IS Connection

# JavaScript implementation
assert(typeof client.connection.connect === 'function');
assert(typeof client.connection.close === 'function');
assert(typeof client.connection.state === 'string');

# Dart implementation
expect(client.connection, isA<Connection>());
```

For weakly typed languages, verify the object behaves as the expected interface rather than checking its type name.

### State Transitions

State transitions may be synchronous or asynchronous depending on the implementation. Use `AWAIT_STATE` to indicate waiting for a state to reach an expected value:

```pseudo
# Pseudocode
AWAIT_STATE client.connection.state == ConnectionState.connecting
```

This means: if the state is already `connecting`, proceed immediately; otherwise, wait for a state change event until it reaches `connecting`. Implementations should use appropriate timeout values to prevent tests hanging indefinitely.

## Mock WebSocket Infrastructure

These tests require the ability to intercept and mock WebSocket connections without making real network calls. The mock infrastructure must support:

1. **Intercepting connection attempts** - Capture the URL and query parameters used when connecting
2. **Injecting server messages** - Deliver protocol messages to the client as if from the server
3. **Capturing client messages** - Record protocol messages sent by the client
4. **Controlling connection outcomes** - Simulate various connection results including successful connections, connection refused, DNS errors, timeouts, connection delays, and other network-level failures
5. **Simulating connection events** - Trigger disconnect and error conditions on established connections

The mechanism for injecting the mock is implementation-specific and not part of the public API. Possible approaches include:
- Package-level variable substitution (e.g., `var dialWebsocket = ...`)
- Build tag conditional compilation
- Internal test exports (`export_test.go` pattern in Go)
- Dependency injection via internal constructors

### Mock Interface

The mock should implement or simulate this behavior:

```pseudo
interface MockWebSocket:
  # Event sequence tracking - unified timeline of all events
  events: List<MockEvent>  # Ordered sequence of all connection and message events

  # Message injection (server -> client)
  send_to_client(message: ProtocolMessage)

  # Awaitable event triggers for test code
  await_next_message_from_client(timeout?: Duration): Future<ProtocolMessage>
  await_connection_attempt(timeout?: Duration): Future<PendingConnection>
  await_close_request(timeout?: Duration): Future<void>

  # Connection control (for established connections)
  simulate_disconnect(error?: ErrorInfo)

enum MockEventType:
  CONNECTION_ATTEMPT
  CONNECTION_SUCCESS
  CONNECTION_FAILURE
  MESSAGE_FROM_CLIENT
  MESSAGE_TO_CLIENT
  DISCONNECT
  CLOSE_REQUEST

struct MockEvent:
  type: MockEventType
  timestamp: Time
  data: Any  # Event-specific data (PendingConnection, ProtocolMessage, ErrorInfo, etc.)

interface PendingConnection:
  url: URL
  protocol: String  # "application/json" or "application/x-msgpack"
  timestamp: Time

  # Methods for test code to respond to the connection attempt
  respond_with_success(connected_message: ProtocolMessage)
  respond_with_refused()  # Connection refused at network level
  respond_with_timeout()  # Connection times out (unresponsive)
  respond_with_error(error_message: ProtocolMessage, then_close: bool = true)  # WebSocket connects but server sends ERROR
```

### Protocol Message Templates

```pseudo
CONNECTED_MESSAGE = ProtocolMessage(
  action: CONNECTED,
  connectionId: "test-connection-id",
  connectionDetails: ConnectionDetails(
    connectionKey: "test-connection-key",
    clientId: null,
    connectionStateTtl: 120000,
    maxIdleInterval: 15000
  )
)

CLOSED_MESSAGE = ProtocolMessage(
  action: CLOSED
)

DISCONNECTED_MESSAGE = ProtocolMessage(
  action: DISCONNECTED,
  error: ErrorInfo(code: 80003, message: "Connection disconnected")
)

ERROR_MESSAGE(code, message) = ProtocolMessage(
  action: ERROR,
  error: ErrorInfo(code: code, statusCode: code / 100, message: message)
)
```

---

## RTC12 - Constructor String Argument Detection

**Spec requirement:** The Realtime constructor must accept a string argument and detect whether it's an API key (contains `:`) or token (no `:`), matching REST client behavior.

The Realtime client has the same constructors as the REST client.

**See:** `uts/test/realtime/unit/client/client_options.md` - RSC1, RSC1a, RSC1c

The same test cases apply:
- API key string (`"appId.keyId:keySecret"`) → Basic auth
- Token string (no `:` delimiter) → Token auth
- Empty string → Error

---

## RTC12 - Invalid Arguments Error

**Spec requirement:** Error code 40106 must be raised when no valid credentials are provided, matching REST client behavior.

The Realtime client has the same error handling as the REST client for invalid credentials.

**See:** `uts/test/realtime/unit/client/client_options.md` - RSC1b

Error code 40106 should be raised when no valid credentials are provided.

---

## RTC2 - Connection Attribute

**Spec requirement:** The Realtime client must expose a `connection` property that provides access to the Connection object.

Tests that `RealtimeClient#connection` provides access to the underlying Connection object.

### Setup
```pseudo
mock_ws = create_mock_websocket()
install_mock(mock_ws)

# Create client with autoConnect: false to avoid immediate connection
client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Assertions
```pseudo
ASSERT client.connection IS NOT null
ASSERT client.connection IS Connection
ASSERT client.connection.state == ConnectionState.initialized
```

---

## RTC3 - Channels Attribute

**Spec requirement:** The Realtime client must expose a `channels` property that provides access to the Channels collection.

Tests that `RealtimeClient#channels` provides access to the Channels collection.

### Setup
```pseudo
mock_ws = create_mock_websocket()
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Assertions
```pseudo
ASSERT client.channels IS NOT null
ASSERT client.channels IS Channels

# Should be able to get/create channels
channel = client.channels.get("test-channel")
ASSERT channel IS RealtimeChannel
ASSERT channel.name == "test-channel"
```

---

## RTC4 - Auth Attribute

**Spec requirement:** The Realtime client must expose an `auth` property that provides access to the Auth object.

Tests that `RealtimeClient#auth` provides access to the Auth object.

### Setup
```pseudo
mock_ws = create_mock_websocket()
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Assertions
```pseudo
ASSERT client.auth IS NOT null
ASSERT client.auth IS Auth
```

---

## RTC17 - ClientId Attribute

**Spec requirement:** The Realtime client must expose a `clientId` property that returns the clientId from the auth object.

Tests that `RealtimeClient#clientId` returns the clientId from the auth object.

### RTC17a - Returns auth clientId

```pseudo
mock_ws = create_mock_websocket()
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  clientId: "explicit-client-id",
  autoConnect: false
))

ASSERT client.clientId == "explicit-client-id"
ASSERT client.clientId == client.auth.clientId
```

---

## RTC1a - echoMessages Option

**Spec requirement:** The `echoMessages` option (default true) controls whether messages published by this client are echoed back on subscriptions. Sent as `echo` query parameter.

Tests the `echoMessages` option which controls whether messages from this connection are echoed back.

### RTC1a_1 - echoMessages defaults to true

```pseudo
mock_ws = create_mock_websocket()
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret"
))

# Wait for connection attempt
pending = AWAIT mock_ws.await_connection_attempt()

# Check the connection URL query parameters
ASSERT pending.url.query_params["echo"] == "true"
```

### RTC1a_2 - echoMessages set to false

```pseudo
mock_ws = create_mock_websocket()
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  echoMessages: false
))

# Wait for connection attempt
pending = AWAIT mock_ws.await_connection_attempt()

# Check the connection URL query parameters
ASSERT pending.url.query_params["echo"] == "false"
```

---

## RTC1b - autoConnect Option

**Spec requirement:** The `autoConnect` option (default true) controls whether the client automatically connects on instantiation or waits for explicit `connect()` call.

Tests the `autoConnect` option which controls automatic connection on instantiation.

### RTC1b_1 - autoConnect defaults to true

```pseudo
mock_ws = create_mock_websocket()
mock_ws.on_connect(respond_with: CONNECTED_MESSAGE)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret"
))

# Should immediately attempt connection (state may be connecting or already connected)
AWAIT_STATE client.connection.state == ConnectionState.connecting OR
            client.connection.state == ConnectionState.connected

# Wait for connection
AWAIT client.connection.once(ConnectionEvent.connected)

ASSERT mock_ws.connect_attempts.length >= 1
```

### RTC1b_2 - autoConnect set to false

```pseudo
mock_ws = create_mock_websocket()
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

# Should NOT attempt connection
ASSERT client.connection.state == ConnectionState.initialized
ASSERT mock_ws.connect_attempts.length == 0

# Should remain in initialized state until explicit connect
WAIT 100ms
ASSERT client.connection.state == ConnectionState.initialized
ASSERT mock_ws.connect_attempts.length == 0
```

### RTC1b_3 - Explicit connect after autoConnect false

```pseudo
mock_ws = create_mock_websocket()
mock_ws.on_connect(respond_with: CONNECTED_MESSAGE)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

ASSERT client.connection.state == ConnectionState.initialized

# Explicit connect
client.connection.connect()

AWAIT_STATE client.connection.state == ConnectionState.connecting

# Wait for connection
AWAIT client.connection.once(ConnectionEvent.connected)

ASSERT mock_ws.events.filter(type: CONNECTION_ATTEMPT).length == 1
AWAIT_STATE client.connection.state == ConnectionState.connected
```

---

## RTC1c - recover Option

**Spec requirement:** The `recover` option accepts a recovery key to resume a previous connection's state. The connection key is sent as the `recover` query parameter and is used only for the initial connection attempt.

Tests the `recover` option for connection state recovery.

### RTC1c_1 - recover string sent in connection request

```pseudo
mock_ws = create_mock_websocket()
install_mock(mock_ws)

recovery_key = encode_recovery_key({
  connectionKey: "previous-connection-key",
  msgSerial: 5,
  channelSerials: { "channel1": "serial1" }
})

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  recover: recovery_key
))

# Wait for connection attempt
pending = AWAIT mock_ws.await_connection_attempt()

# Check the connection URL query parameters
ASSERT pending.url.query_params["recover"] == "previous-connection-key"
```

### RTC1c_2 - recover option cleared after connection attempt (RTN16k)

```pseudo
mock_ws = create_mock_websocket()
mock_ws.on_connect(respond_with: CONNECTED_MESSAGE)
install_mock(mock_ws)

recovery_key = encode_recovery_key({
  connectionKey: "previous-connection-key",
  msgSerial: 5,
  channelSerials: {}
})

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  recover: recovery_key
))

# Wait for connection
AWAIT client.connection.once(ConnectionEvent.connected)

# Simulate disconnect and reconnect
mock_ws.simulate_disconnect()
AWAIT client.connection.once(ConnectionEvent.disconnected)

mock_ws.on_connect(respond_with: CONNECTED_MESSAGE)
AWAIT client.connection.once(ConnectionEvent.connected)

# Second connection should NOT include recover parameter
# (RTN16k - recover is used only for initial connection)
second_connect_url = mock_ws.connect_attempts[1].url
ASSERT "recover" NOT IN second_connect_url.query_params
```

### RTC1c_3 - Invalid recovery key handled gracefully

```pseudo
mock_ws = create_mock_websocket()
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  recover: "invalid-not-a-valid-recovery-key"
))

# Wait for connection attempt (recovery key decoding failure is logged, not fatal)
pending = AWAIT mock_ws.await_connection_attempt()

# Connection should proceed without recover parameter
ASSERT "recover" NOT IN pending.url.query_params
```

---

## RTC1f - transportParams Option

| Spec | Requirement |
|------|-------------|
| RTC1f | Custom query parameters can be added via `transportParams` |
| RTC1f1 | User-specified transportParams override library defaults |

Tests the `transportParams` option for additional WebSocket query parameters.

### RTC1f_1 - transportParams included in connection URL

```pseudo
mock_ws = create_mock_websocket()
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  transportParams: {
    "customParam": "customValue",
    "anotherParam": "123"
  }
))

# Wait for connection attempt
pending = AWAIT mock_ws.await_connection_attempt()

# Check the connection URL query parameters
ASSERT pending.url.query_params["customParam"] == "customValue"
ASSERT pending.url.query_params["anotherParam"] == "123"
```

### RTC1f_2 - transportParams with different value types (Stringifiable)

```pseudo
mock_ws = create_mock_websocket()
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  transportParams: {
    "stringParam": "hello",
    "numberParam": 42,
    "boolTrueParam": true,
    "boolFalseParam": false
  }
))

# Wait for connection attempt
pending = AWAIT mock_ws.await_connection_attempt()

# Check stringification of values (RTC1f)
ASSERT pending.url.query_params["stringParam"] == "hello"
ASSERT pending.url.query_params["numberParam"] == "42"
ASSERT pending.url.query_params["boolTrueParam"] == "true"
ASSERT pending.url.query_params["boolFalseParam"] == "false"
```

### RTC1f1 - transportParams override library defaults

```pseudo
mock_ws = create_mock_websocket()
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  transportParams: {
    "v": "3",  # Override protocol version
    "heartbeats": "false"  # Override heartbeats
  }
))

# Wait for connection attempt
pending = AWAIT mock_ws.await_connection_attempt()

# User-specified values should override defaults
ASSERT pending.url.query_params["v"] == "3"
ASSERT pending.url.query_params["heartbeats"] == "false"
```

---

## RTC15 - connect() Method

**Spec requirement:** The Realtime client must provide a `connect()` method that calls `Connection#connect()`.

Tests the `RealtimeClient#connect` method.

### RTC15a - connect() calls Connection#connect

```pseudo
mock_ws = create_mock_websocket()
mock_ws.on_connect(respond_with: CONNECTED_MESSAGE)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

ASSERT client.connection.state == ConnectionState.initialized

# Call connect on client (should proxy to connection)
client.connect()

AWAIT_STATE client.connection.state == ConnectionState.connecting

AWAIT client.connection.once(ConnectionEvent.connected)
AWAIT_STATE client.connection.state == ConnectionState.connected
```

---

## RTC16 - close() Method

**Spec requirement:** The Realtime client must provide a `close()` method that calls `Connection#close()`.

Tests the `RealtimeClient#close` method.

### RTC16a - close() calls Connection#close

```pseudo
mock_ws = create_mock_websocket()
mock_ws.on_connect(respond_with: CONNECTED_MESSAGE)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret"
))

# Wait for connection
AWAIT client.connection.once(ConnectionEvent.connected)
AWAIT_STATE client.connection.state == ConnectionState.connected

# Configure mock to respond to CLOSE with CLOSED
mock_ws.on_message(action: CLOSE, respond_with: CLOSED_MESSAGE)

# Call close on client (should proxy to connection)
client.close()

AWAIT_STATE client.connection.state == ConnectionState.closing OR
            client.connection.state == ConnectionState.closed

AWAIT client.connection.once(ConnectionEvent.closed)
AWAIT_STATE client.connection.state == ConnectionState.closed
```

---

## Shared Options (Reference to REST Client Tests)

The following options are shared with the REST client and should behave identically:

| Option | REST Spec | Test File |
|--------|-----------|-----------|
| `key` | RSC1, RSC1a | `uts/test/realtime/unit/client/client_options.md` |
| `token` / `tokenDetails` | RSC1c | `uts/test/realtime/unit/client/client_options.md` |
| `authCallback` / `authUrl` | RSA8 | `unit/auth/auth_callback.md` |
| `clientId` | RSA7, RSC17 | `unit/auth/client_id.md` |
| `tls` | RSC18 | `uts/test/rest/unit/rest_client.md` |
| `environment` / `endpoint` | RSC15e, REC1 | `unit/client/fallback.md` |
| `restHost` / `realtimeHost` | RSC12, TO3k2, TO3k3 | `unit/client/fallback.md` |
| `fallbackHosts` | RSC15 | `unit/client/fallback.md` |
| `useBinaryProtocol` | RSC8, TO3f | `uts/test/rest/unit/rest_client.md` |
| `logLevel` / `logHandler` | TO3b, TO3c | (not yet specified) |

### Realtime-Specific Verification for Shared Options

For shared options that affect the WebSocket connection, verify the behavior in the Realtime context:

#### TLS Setting (RSC18) in Realtime

```pseudo
mock_ws = create_mock_websocket()
mock_ws.on_connect(respond_with: CONNECTED_MESSAGE)
install_mock(mock_ws)

FOR EACH tls_setting IN [true, false]:
  mock_ws.reset()

  # Note: Basic auth requires TLS, so use token auth for tls: false
  IF tls_setting:
    client = Realtime(options: ClientOptions(
      key: "appId.keyId:keySecret",
      tls: true
    ))
  ELSE:
    client = Realtime(options: ClientOptions(
      token: "test-token",
      tls: false
    ))

  AWAIT client.connection.once(ConnectionEvent.connected)

  connect_url = mock_ws.last_connect_url
  IF tls_setting:
    ASSERT connect_url.scheme == "wss"
  ELSE:
    ASSERT connect_url.scheme == "ws"

  client.close()
```

#### useBinaryProtocol in Realtime

```pseudo
mock_ws = create_mock_websocket()
install_mock(mock_ws)

FOR EACH use_binary IN [true, false]:
  mock_ws.reset()

  client = Realtime(options: ClientOptions(
    key: "appId.keyId:keySecret",
    useBinaryProtocol: use_binary
  ))

  pending = AWAIT mock_ws.await_connection_attempt()

  IF use_binary:
    ASSERT pending.url.query_params["format"] == "msgpack"
  ELSE:
    ASSERT pending.url.query_params["format"] == "json"

  client.close()
```

---

## Connection URL Query Parameters

Tests that the connection URL includes all required query parameters.

### Standard Query Parameters

```pseudo
mock_ws = create_mock_websocket()
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret"
))

pending = AWAIT mock_ws.await_connection_attempt()

# Required parameters
ASSERT "v" IN pending.url.query_params  # Protocol version
ASSERT "format" IN pending.url.query_params  # msgpack or json
ASSERT "heartbeats" IN pending.url.query_params  # RTN23b
ASSERT "echo" IN pending.url.query_params

# Auth parameters (one of these depending on auth method)
ASSERT ("key" IN pending.url.query_params) OR
       ("accessToken" IN pending.url.query_params)
```

---

## Test Infrastructure Notes

### Mock Installation

The `install_mock()` function represents whatever SDK-specific mechanism is used to substitute the real WebSocket implementation with the mock. This could be:

- **Go**: Package-level variable override in test file, or build-tag conditional compilation
- **JavaScript**: Module mocking via Jest or similar
- **Dart**: Dependency injection via internal constructors or zone-based overrides
- **Swift/Kotlin**: Protocol/interface substitution

The mock should be installed **before** creating the Realtime client and should be cleaned up after each test.

### Async Handling

Tests use async primitives to handle asynchronous behavior:
- `AWAIT client.connection.once(event)` - Wait for specific connection events
- `AWAIT_STATE condition` - Wait for a state condition to become true (see Pseudocode Conventions section)
- `AWAIT mock_ws.await_connection_attempt()` - Wait for the client to attempt a connection

Implementations should:
- Use appropriate async/await patterns for the language
- Set reasonable timeouts to prevent tests hanging indefinitely
- Clean up event listeners after the wait completes

### Timer Mocking

Tests may need to verify behavior that depends on timeouts (e.g., connection timeouts, heartbeat intervals, retry delays). To avoid slow tests, implementations **should** use timer mocking/fake timers where practical.

**Timer mocking support varies by language:**

- **Well-supported**: JavaScript (Jest/Sinon fake timers), Python (freezegun), Ruby (timecop)
- **Dependency injection preferred**: Go, Swift, Kotlin/Java (often use clock interfaces rather than global mocking)
- **Mixed**: Dart (fake_async available but less common), C# (TimeProvider in .NET 8+)

**Pseudocode convention:**

```pseudo
# ADVANCE_TIME - Advance fake timers (or actually wait if mocking unavailable)
ADVANCE_TIME(15000)  # Advance 15 seconds

# Implementations should:
# 1. Use fake/mock timers if available in the language/framework
# 2. Fall back to actual delays if timer mocking is impractical
# 3. Document which approach is used
```

**Implementation guidance:**

- **Preferred**: Mock/fake the timer/clock mechanism used by the library
  - Provides instant test execution
  - Allows precise control over timing
  - Example: `jest.advanceTimersByTime(15000)` in JavaScript

- **Alternative**: Use dependency injection of clock/timer abstractions
  - Library accepts a clock interface in tests
  - Tests provide a controllable implementation
  - Common in strongly-typed languages

- **Fallback**: Use actual time delays
  - Only if timer mocking is impractical for the language/framework
  - Keep delays as short as possible while maintaining test reliability
  - May need to adjust timeouts to prevent flakiness

Tests in this specification use `ADVANCE_TIME(milliseconds)` to indicate time progression. Implementations should choose the approach that best fits their language and testing ecosystem.

### Test Isolation

Each test should:
1. Create a fresh mock WebSocket
2. Install the mock
3. Create the Realtime client
4. Perform assertions
5. Close the client
6. Restore/cleanup the mock

```pseudo
BEFORE EACH TEST:
  mock_ws = create_mock_websocket()
  install_mock(mock_ws)

AFTER EACH TEST:
  IF client IS NOT null:
    client.close()
  uninstall_mock()
```

### Channel Naming

Tests that use channels should use uniquely-named channels to avoid:
- Collisions between concurrent tests
- Server-side side-effects from previous test runs
- State leakage between test cases

Use generated unique identifiers (UUIDs, timestamps, or test-framework-provided unique names) for channel names rather than fixed strings like "test-channel".
