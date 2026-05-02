# Realtime Client Tests

Spec points: `RTC1`, `RTC1a`, `RTC1b`, `RTC1c`, `RTC1f`, `RTC2`, `RTC3`, `RTC4`, `RTC12`, `RTC13`, `RTC15`, `RTC16`, `RTC17`

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

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTC12 - Constructor String Argument Detection

**Spec requirement:** The Realtime constructor must accept a string argument and detect whether it's an API key (contains `:`) or token (no `:`), matching REST client behavior.

The Realtime client has the same constructors as the REST client.

**See:** `uts/test/realtime/unit/client/client_options.md` - RSC1, RSC1a, RSC1c

The same test cases apply:
- API key string (`"appId.keyId:keySecret"`) -> Basic auth
- Token string (no `:` delimiter) -> Token auth
- Empty string -> Error

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
CLOSE_CLIENT(client)
```

---

## RTC3 - Channels Attribute

**Spec requirement:** The Realtime client must expose a `channels` property that provides access to the Channels collection.

Tests that `RealtimeClient#channels` provides access to the Channels collection.

### Setup
```pseudo
channel_name = "test-RTC3-${random_id()}"

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
channel = client.channels.get(channel_name)
ASSERT channel IS RealtimeChannel
ASSERT channel.name == channel_name
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
```

---

## RTC13 - Push Attribute

**Spec requirement:** RTC13 — `RealtimeClient#push` attribute provides access to the `Push` object.

Tests that `RealtimeClient#push` provides access to the Push object.

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
ASSERT client.push IS NOT null
ASSERT client.push IS Push
ASSERT client.push.admin IS PushAdmin
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
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
CLOSE_CLIENT(client)
```

---

## Test Infrastructure Notes

See `uts/test/realtime/unit/helpers/mock_websocket.md` for mock installation, test isolation, and timer mocking guidance.

### Channel Naming

Tests that use channels should use uniquely-named channels to avoid:
- Collisions between concurrent tests
- Server-side side-effects from previous test runs
- State leakage between test cases

Use generated unique identifiers (UUIDs, timestamps, or test-framework-provided unique names) for channel names rather than fixed strings like "test-channel".
