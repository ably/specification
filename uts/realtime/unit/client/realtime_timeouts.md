# Realtime Client Configured Timeouts

Spec points: `RTC7`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## Purpose

The realtime client must use the configured timeouts specified in `ClientOptions`,
falling back to client library defaults. This file tests that custom timeout values
are correctly applied to realtime operations.

Default timeout values (from spec):
- `realtimeRequestTimeout`: 10,000 ms (TO3l11) — used for CONNECT, ATTACH, DETACH, HEARTBEAT
- `disconnectedRetryTimeout`: 15,000 ms (TO3l1) — delay before reconnecting from DISCONNECTED
- `suspendedRetryTimeout`: 30,000 ms (TO3l2) — delay before reconnecting from SUSPENDED

---

## RTC7 - realtimeRequestTimeout applied to channel attach

**Spec requirement:** The client library must use the configured timeouts specified
in the ClientOptions.

Tests that a custom `realtimeRequestTimeout` is applied to channel attach operations.
When the server does not respond to ATTACH within the timeout, the operation should fail.

### Setup
```pseudo
channel_name = "test-RTC7-attach-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Do NOT respond — simulate timeout
      PASS
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  realtimeRequestTimeout: 500
))

channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Start attach — will not get a response
attach_future = channel.attach()

# Advance past the custom timeout
ADVANCE_TIME(600)

# Attach should fail
AWAIT attach_future FAILS WITH error
```

### Assertions
```pseudo
# The timeout used the custom value (500ms), not the default (10000ms)
ASSERT error IS NOT null
# Channel should be in SUSPENDED state (RTL4f: attach timeout → SUSPENDED)
ASSERT channel.state == ChannelState.suspended
CLOSE_CLIENT(client)
```

---

## RTC7 - realtimeRequestTimeout applied to channel detach

**Spec requirement:** The client library must use the configured timeouts specified
in the ClientOptions.

Tests that a custom `realtimeRequestTimeout` is applied to channel detach operations.

### Setup
```pseudo
channel_name = "test-RTC7-detach-${random_id()}"
ignore_detach = false

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success()
    conn.send_to_client(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: 0
      ))
    IF msg.action == DETACH AND ignore_detach:
      # Do NOT respond — simulate timeout
      PASS
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  realtimeRequestTimeout: 500
))

channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Now ignore DETACH messages
ignore_detach = true

# Start detach — will not get a response
detach_future = channel.detach()

# Advance past the custom timeout
ADVANCE_TIME(600)

# Detach should fail
AWAIT detach_future FAILS WITH error
```

### Assertions
```pseudo
# The timeout used the custom value (500ms), not the default (10000ms)
ASSERT error IS NOT null
# Channel should still be in ATTACHED state (RTL5f: detach timeout → back to ATTACHED)
ASSERT channel.state == ChannelState.attached
CLOSE_CLIENT(client)
```

---

## RTC7 - disconnectedRetryTimeout controls reconnection delay

**Spec requirement:** The client library must use the configured timeouts specified
in the ClientOptions.

Tests that a custom `disconnectedRetryTimeout` controls the delay before reconnection
after the connection is lost.

Note: Per RTN15a, when a previously-CONNECTED client disconnects, the first
reconnection attempt is immediate (no delay). This immediate retry must be
accounted for. We make all retries after the initial connection fail, and
disable fallback hosts so SocketException errors don't trigger fallback host
iteration. A mock HTTP client is used to avoid real network requests from
the connectivity checker (RTN17j).

### Setup
```pseudo
connection_attempt_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    IF connection_attempt_count == 1:
      # Initial connection succeeds
      conn.respond_with_success()
      conn.send_to_client(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-id",
        connectionKey: "connection-key",
        connectionDetails: ConnectionDetails(
          connectionKey: "connection-key",
          maxIdleInterval: 0,
          connectionStateTtl: 120000
        )
      ))
    ELSE:
      # All subsequent attempts fail
      conn.respond_with_refused()
  }
)
install_mock(mock_ws)

mock_http = MockHttpClient(
  onRequest: (req) => req.respond_with(200, "yes")
)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  disconnectedRetryTimeout: 2000,
  fallbackHosts: []
), httpClient: mock_http)
```

### Test Steps
```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
ASSERT connection_attempt_count == 1

# Force disconnection — triggers RTN15a immediate retry (which fails),
# then schedules timer-based retry using disconnectedRetryTimeout
mock_ws.active_connection.close()

# Wait for the immediate retry to fail and state to return to DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Record attempts after the immediate retry cycle
count_after_immediate = connection_attempt_count

# Advance time by less than the custom timeout — no new retry yet
ADVANCE_TIME(1500)
ASSERT connection_attempt_count == count_after_immediate

# Advance past the custom timeout (2000ms + jitter margin)
ADVANCE_TIME(1500)
```

### Assertions
```pseudo
# A new reconnection attempt was made after the custom delay
ASSERT connection_attempt_count > count_after_immediate
CLOSE_CLIENT(client)
```

---

## RTC7 - default timeouts applied when not configured

**Spec requirement:** The client library must use the configured timeouts specified
in the ClientOptions, falling back to the client library defaults.

Tests that default timeout values are used when no custom values are specified.

### Setup
```pseudo
client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Assertions
```pseudo
# Default values per spec (TO3l*)
ASSERT client.options.realtimeRequestTimeout == 10000
ASSERT client.options.disconnectedRetryTimeout == 15000
ASSERT client.options.suspendedRetryTimeout == 30000
ASSERT client.options.httpOpenTimeout == 4000
ASSERT client.options.httpRequestTimeout == 10000
CLOSE_CLIENT(client)
```
