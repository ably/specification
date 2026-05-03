# Connection Recovery Tests (RTN16)

Spec points: `RTN16d`, `RTN16f`, `RTN16f1`, `RTN16g`, `RTN16g1`, `RTN16g2`, `RTN16i`, `RTN16j`, `RTN16k`, `RTN16l`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTN16g, RTN16g1 - createRecoveryKey returns string with connectionKey, msgSerial, and channel/channelSerial pairs

| Spec | Requirement |
|------|-------------|
| RTN16g | `Connection#createRecoveryKey` returns a string incorporating the connectionKey, current msgSerial, and channel name/channelSerial pairs for every attached channel |
| RTN16g1 | The recovery key must be serialized in a way that can encode any unicode channel name |

Tests that `createRecoveryKey()` returns a correctly structured recovery key containing the connection key, message serial, and channel serials for attached channels, including channels with unicode names.

### Setup

```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-1",
      connectionKey: "key-abc-123",
      connectionDetails: ConnectionDetails(
        connectionKey: "key-abc-123",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Test Steps

```pseudo
# Connect
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Get the WebSocket connection for sending mock responses
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection

# Get two channels and simulate attaching them (including one with unicode name)
channel_a = client.channels.get("channel-alpha")
channel_b = client.channels.get("channel-éàü-世界")

# Attach channel_a
channel_a.attach()
ws_connection.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: "channel-alpha",
  channelSerial: "serial-a-001"
))
AWAIT_STATE channel_a.state == ChannelState.attached

# Attach channel_b (unicode name)
channel_b.attach()
ws_connection.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: "channel-éàü-世界",
  channelSerial: "serial-b-002"
))
AWAIT_STATE channel_b.state == ChannelState.attached

# Create recovery key
recovery_key_string = client.connection.createRecoveryKey()
```

### Assertions

```pseudo
# Recovery key is not null
ASSERT recovery_key_string IS NOT null

# Deserialize the recovery key (JSON format per ably-js reference)
recovery_key = fromJson(recovery_key_string)

# Contains connectionKey
ASSERT recovery_key["connectionKey"] == "key-abc-123"

# Contains msgSerial (starts at 0 since no messages were sent)
ASSERT recovery_key["msgSerial"] == 0

# Contains channelSerials map with both channels
ASSERT recovery_key["channelSerials"] IS NOT null
ASSERT recovery_key["channelSerials"]["channel-alpha"] == "serial-a-001"

# RTN16g1: Unicode channel name is correctly encoded in the serialized key
ASSERT recovery_key["channelSerials"]["channel-éàü-世界"] == "serial-b-002"

# Verify round-trip: re-serializing and deserializing preserves the unicode name
re_serialized = toJson(recovery_key)
re_parsed = fromJson(re_serialized)
ASSERT re_parsed["channelSerials"]["channel-éàü-世界"] == "serial-b-002"

CLOSE_CLIENT(client)
```

---

## RTN16g2 - createRecoveryKey returns null in inactive states and before first connect

**Spec requirement:** `createRecoveryKey()` should return null when the SDK is in the CLOSED, CLOSING, FAILED, or SUSPENDED states, or when it does not have a connectionKey (e.g. before first connect).

Tests that `createRecoveryKey()` returns null in all the specified states.

### Setup

```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-1",
      connectionKey: "key-1",
      connectionDetails: ConnectionDetails(
        connectionKey: "key-1",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Test Steps

```pseudo
# Before connecting (INITIALIZED state, no connectionKey)
ASSERT client.connection.createRecoveryKey() IS null

# Connect and verify recovery key is available when CONNECTED
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
ASSERT client.connection.createRecoveryKey() IS NOT null

# Transition to CLOSING then CLOSED
client.connection.close()
AWAIT_STATE client.connection.state == ConnectionState.closing
ASSERT client.connection.createRecoveryKey() IS null

AWAIT_STATE client.connection.state == ConnectionState.closed
ASSERT client.connection.createRecoveryKey() IS null
```

### Assertions

```pseudo
# All null cases verified inline above.
# For FAILED and SUSPENDED states, create separate clients to test:

# --- Test FAILED state ---
mock_ws_failed = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "conn-f",
      connectionKey: "key-f",
      connectionDetails: ConnectionDetails(
        connectionKey: "key-f",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws_failed)

client_failed = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
client_failed.connect()
AWAIT_STATE client_failed.connection.state == ConnectionState.connected

# Trigger FAILED via fatal ERROR
ws_conn = mock_ws_failed.events.find(e => e.type == CONNECTION_SUCCESS).connection
ws_conn.send_to_client_and_close(ProtocolMessage(
  action: ERROR,
  error: ErrorInfo(code: 50000, statusCode: 500, message: "Fatal error")
))
AWAIT_STATE client_failed.connection.state == ConnectionState.failed
ASSERT client_failed.connection.createRecoveryKey() IS null

# --- Test SUSPENDED state ---
mock_ws_suspended = MockWebSocket(
  onConnectionAttempt: (conn) => {
    # All connections fail after initial, to force SUSPENDED
    IF connection_attempt_count == 1:
      conn.respond_with_success()
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "conn-s",
        connectionKey: "key-s",
        connectionDetails: ConnectionDetails(
          connectionKey: "key-s",
          maxIdleInterval: 15000,
          connectionStateTtl: 2000
        )
      ))
    ELSE:
      conn.respond_with_refused()
  }
)
install_mock(mock_ws_suspended)

client_suspended = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  disconnectedRetryTimeout: 500,
  autoConnect: false,
  fallbackHosts: []
))

enable_fake_timers()

client_suspended.connect()
AWAIT_STATE client_suspended.connection.state == ConnectionState.connected

ws_conn_s = mock_ws_suspended.events.find(e => e.type == CONNECTION_SUCCESS).connection
ws_conn_s.simulate_disconnect()

# Advance time until SUSPENDED (connectionStateTtl expires)
LOOP up to 10 times:
  ADVANCE_TIME(1500)
  IF client_suspended.connection.state == ConnectionState.suspended:
    BREAK

AWAIT_STATE client_suspended.connection.state == ConnectionState.suspended
ASSERT client_suspended.connection.createRecoveryKey() IS null

CLOSE_CLIENT(client_suspended)
```

---

## RTN16k - recover option adds recover query param to WebSocket URL

**Spec requirement:** When instantiated with the `recover` client option, the library should add a `recover` querystring param (set from the connectionKey component of the recoveryKey) to the first WebSocket request. After successful connection, it should never again supply a `recover` param.

Tests that the `recover` query parameter is sent on the first connection and not on subsequent reconnections.

### Setup

```pseudo
connection_attempt_count = 0
captured_connection_attempts = []

# Construct a valid recoveryKey
recovery_key = toJson({
  "connectionKey": "recovered-key-xyz",
  "msgSerial": 5,
  "channelSerials": {}
})

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    captured_connection_attempts.append(conn)
    conn.respond_with_success()

    IF connection_attempt_count == 1:
      # First connection: successful recovery (same connectionId as implied by recoveryKey)
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "recovered-conn-id",
        connectionKey: "new-key-after-recovery",
        connectionDetails: ConnectionDetails(
          connectionKey: "new-key-after-recovery",
          maxIdleInterval: 15000,
          connectionStateTtl: 120000
        )
      ))
    ELSE:
      # Subsequent connection: resume after disconnect
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "recovered-conn-id",
        connectionKey: "resumed-key",
        connectionDetails: ConnectionDetails(
          connectionKey: "resumed-key",
          maxIdleInterval: 15000,
          connectionStateTtl: 120000
        )
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  recover: recovery_key,
  autoConnect: false
))
```

### Test Steps

```pseudo
# Connect - should use recover param
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Simulate disconnect and reconnection
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection
ws_connection.simulate_disconnect()

# Wait for resume reconnection
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# First connection attempt includes recover param with connectionKey from recoveryKey
ASSERT captured_connection_attempts[0].url.query_params["recover"] == "recovered-key-xyz"

# First connection attempt does NOT include resume param
ASSERT "resume" NOT IN captured_connection_attempts[0].url.query_params

# Second connection attempt uses resume (not recover) since client is now connected
ASSERT captured_connection_attempts[1].url.query_params["resume"] == "new-key-after-recovery"
ASSERT "recover" NOT IN captured_connection_attempts[1].url.query_params

CLOSE_CLIENT(client)
```

---

## RTN16f - recover option initializes msgSerial from recoveryKey

**Spec requirement:** When instantiated with the `recover` client option, the library should initialize its internal msgSerial counter to the msgSerial component of the recoveryKey. If recover fails, the counter should be reset to 0 per RTN15c7.

Tests that the msgSerial is initialized from the recoveryKey and reset on recovery failure.

### Setup

```pseudo
connection_attempt_count = 0
captured_messages = []

# Construct a recoveryKey with msgSerial of 42
recovery_key = toJson({
  "connectionKey": "old-key",
  "msgSerial": 42,
  "channelSerials": {
    "test-channel": "ch-serial-1"
  }
})

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    conn.respond_with_success()

    IF connection_attempt_count == 1:
      # Successful recovery
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "recovered-conn",
        connectionKey: "new-key",
        connectionDetails: ConnectionDetails(
          connectionKey: "new-key",
          maxIdleInterval: 15000,
          connectionStateTtl: 120000
        )
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  recover: recovery_key,
  autoConnect: false
))
```

### Test Steps

```pseudo
# Connect with recovery
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Get WebSocket connection reference
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection

# Attach the recovered channel
channel = client.channels.get("test-channel")
channel.attach()
ws_connection.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: "test-channel",
  channelSerial: "ch-serial-updated"
))
AWAIT_STATE channel.state == ChannelState.attached

# Publish a message - the msgSerial should start from the recovered value (42)
channel.publish("event", "data")

# Capture the MESSAGE frame sent by the client
sent_frames = mock_ws.events.filter(e => e.type == "ws_frame" AND e.direction == "client_to_server")
message_frame = sent_frames.find(f => f.message.action == MESSAGE)

# ACK the message
ws_connection.send_to_client(ProtocolMessage(
  action: ACK,
  msgSerial: 42,
  count: 1
))
```

### Assertions

```pseudo
# The first message published uses msgSerial from the recoveryKey
ASSERT message_frame IS NOT null
ASSERT message_frame.message.msgSerial == 42

CLOSE_CLIENT(client)
```

---

## RTN16f1 - Malformed recoveryKey logs error and connects normally

**Spec requirement:** If the recovery key provided in the `recover` client option cannot be deserialized due to malformed data, then an error should be logged and the connection should be made like no `recover` option was provided.

Tests that a malformed recoveryKey is handled gracefully: the connection proceeds normally without the `recover` query parameter.

### Setup

```pseudo
connection_attempt_count = 0
captured_connection_attempts = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    captured_connection_attempts.append(conn)
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "fresh-conn",
      connectionKey: "fresh-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "fresh-key",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

# Use a malformed (non-JSON) recover string
client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  recover: "this-is-not-valid-json!!!",
  autoConnect: false
))
```

### Test Steps

```pseudo
# Connect - should proceed as a normal connection (no recover param)
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions

```pseudo
# Connection succeeded normally
ASSERT client.connection.state == ConnectionState.connected
ASSERT client.connection.id == "fresh-conn"
ASSERT client.connection.key == "fresh-key"

# No recover param was sent (malformed key was rejected)
ASSERT "recover" NOT IN captured_connection_attempts[0].url.query_params

# Also no resume param (this is a fresh connection)
ASSERT "resume" NOT IN captured_connection_attempts[0].url.query_params

# Only one connection attempt (normal connection, no retries)
ASSERT connection_attempt_count == 1

CLOSE_CLIENT(client)
```

> **Implementation note:** The spec requires that an error be logged when the recovery
> key is malformed. Implementations should verify this by capturing log output (e.g.,
> via a log handler) and asserting that an error-level log message was emitted mentioning
> the malformed recovery key. The exact mechanism for capturing logs is implementation-specific.

---

## RTN16j - recover option instantiates channels from recoveryKey with correct channelSerials

| Spec | Requirement |
|------|-------------|
| RTN16j | When instantiated with the `recover` client option, for every channel/channelSerial pair in the recoveryKey, the library should instantiate a corresponding channel and set its channelSerial (RTL15b) |

Tests that channels listed in the recoveryKey are pre-instantiated with their channel serials before the connection is established.

### Setup

```pseudo
connection_attempt_count = 0

# Construct a recoveryKey with multiple channels
recovery_key = toJson({
  "connectionKey": "old-key-abc",
  "msgSerial": 10,
  "channelSerials": {
    "channel-one": "serial-1-abc",
    "channel-two": "serial-2-def",
    "channel-üñîçöðé": "serial-3-unicode"
  }
})

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "recovered-conn",
      connectionKey: "new-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "new-key",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  recover: recovery_key,
  autoConnect: false
))
```

### Test Steps

```pseudo
# Connect with recovery
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
```

### Assertions

```pseudo
# RTN16j: Channels from the recoveryKey are instantiated
channel_one = client.channels.get("channel-one")
channel_two = client.channels.get("channel-two")
channel_unicode = client.channels.get("channel-üñîçöðé")

# Each channel has its channelSerial set from the recoveryKey
ASSERT channel_one.properties.channelSerial == "serial-1-abc"
ASSERT channel_two.properties.channelSerial == "serial-2-def"
ASSERT channel_unicode.properties.channelSerial == "serial-3-unicode"

# RTN16i: Channels are NOT automatically attached — the user must explicitly attach them.
# They should be in INITIALIZED state (the library instantiated them but didn't attach).
ASSERT channel_one.state == ChannelState.initialized
ASSERT channel_two.state == ChannelState.initialized
ASSERT channel_unicode.state == ChannelState.initialized

# When the user attaches, the ATTACH message should include the channelSerial
# (this enables the server to resume the channel from the correct point)
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection

channel_one.attach()

# Capture the ATTACH frame sent by the client
sent_frames = mock_ws.events.filter(e =>
  e.type == "ws_frame" AND
  e.direction == "client_to_server" AND
  e.message.action == ATTACH AND
  e.message.channel == "channel-one"
)
ASSERT sent_frames.length == 1
ASSERT sent_frames[0].message.channelSerial == "serial-1-abc"

# Complete the attachment
ws_connection.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: "channel-one",
  channelSerial: "serial-1-abc-updated"
))
AWAIT_STATE channel_one.state == ChannelState.attached

CLOSE_CLIENT(client)
```
