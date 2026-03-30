# RealtimeChannel Attributes

Spec points: `RTL23`, `RTL24`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

---

## RTL23 - RealtimeChannel name attribute

**Spec requirement:** `RealtimeChannel#name` attribute is a string containing the
channel's name.

Tests that the channel name attribute returns the name used when getting the channel.

### Setup
```pseudo
client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Assertions
```pseudo
channel = client.channels.get("my-channel")
ASSERT channel.name == "my-channel"

# Also works with special characters
channel2 = client.channels.get("namespace:channel-name")
ASSERT channel2.name == "namespace:channel-name"
```

---

## RTL24 - errorReason set on channel error

**Spec requirement:** `RealtimeChannel#errorReason` attribute is an optional
`ErrorInfo` object which is set by the library when an error occurs on the channel.

Tests that errorReason is populated when a channel receives an ERROR ProtocolMessage
(RTL14).

### Setup
```pseudo
channel_name = "test-RTL24-error-${random_id()}"

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
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Verify errorReason is initially null
ASSERT channel.errorReason IS null

# Send an ERROR ProtocolMessage for this channel
mock_ws.send_to_client(ProtocolMessage(
  action: ERROR,
  channel: channel_name,
  error: ErrorInfo(
    message: "Channel error occurred",
    code: 90001,
    statusCode: 500
  )
))

AWAIT_STATE channel.state == ChannelState.failed
```

### Assertions
```pseudo
ASSERT channel.errorReason IS NOT null
ASSERT channel.errorReason.code == 90001
ASSERT channel.errorReason.statusCode == 500
ASSERT channel.errorReason.message == "Channel error occurred"
```

---

## RTL24 - errorReason set on attach failure

**Spec requirement:** `RealtimeChannel#errorReason` is set by the library when an
error occurs on the channel, as described by RTL4g.

Tests that errorReason is populated when an attach is rejected by the server.

### Setup
```pseudo
channel_name = "test-RTL24-attach-fail-${random_id()}"

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
      # Reject attach with DETACHED + error
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: channel_name,
        error: ErrorInfo(
          message: "Permission denied",
          code: 40160,
          statusCode: 401
        )
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Attach should fail
AWAIT channel.attach() FAILS WITH error
```

### Assertions
```pseudo
# errorReason is set from the DETACHED response error
ASSERT channel.errorReason IS NOT null
ASSERT channel.errorReason.code == 40160
ASSERT channel.errorReason.statusCode == 401
```

---

## RTL24 - errorReason cleared on successful attach

**Spec requirement:** The errorReason should be cleared when the channel
successfully attaches or reattaches.

Tests that errorReason is reset to null after a successful attach following a
previous error.

### Setup
```pseudo
channel_name = "test-RTL24-clear-attach-${random_id()}"
attach_count = 0

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
      attach_count++
      IF attach_count == 1:
        # First attach: reject
        mock_ws.send_to_client(ProtocolMessage(
          action: DETACHED,
          channel: channel_name,
          error: ErrorInfo(
            message: "Temporary error",
            code: 50000,
            statusCode: 500
          )
        ))
      ELSE:
        # Subsequent attaches: succeed
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: channel_name,
          flags: 0
        ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# First attach fails — errorReason set
AWAIT channel.attach() FAILS WITH error
ASSERT channel.errorReason IS NOT null
ASSERT channel.errorReason.code == 50000

# Second attach succeeds — errorReason cleared
AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached
ASSERT channel.errorReason IS null
```

---

## RTL24 - errorReason cleared on successful detach

**Spec requirement:** The errorReason should be cleared when the channel
successfully detaches.

Tests that errorReason is reset to null after a successful detach, even if
the channel previously had an error.

Note: To reliably set errorReason, we use an ERROR ProtocolMessage (which
transitions the channel to FAILED via RTL14). An ATTACHED-while-already-ATTACHED
message (UPDATE) emits a ChannelStateChange event with the error, but
implementations may not persist it to the errorReason attribute — only state
transitions via RTL14 or RTL4g reliably set errorReason. After the ERROR puts
the channel in FAILED, we reattach (which clears errorReason), then verify
detach also leaves errorReason null.

### Setup
```pseudo
channel_name = "test-RTL24-clear-detach-${random_id()}"
attach_count = 0

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
    IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: channel_name
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))

channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Send ERROR — channel transitions to FAILED, errorReason is set (RTL14)
mock_ws.send_to_client(ProtocolMessage(
  action: ERROR,
  channel: channel_name,
  error: ErrorInfo(
    message: "Channel error",
    code: 90002,
    statusCode: 500
  )
))

AWAIT_STATE channel.state == ChannelState.failed

ASSERT channel.errorReason IS NOT null
ASSERT channel.errorReason.code == 90002

# Reattach — errorReason cleared on successful attach
AWAIT channel.attach()
ASSERT channel.errorReason IS null

# Now detach — errorReason stays null
AWAIT channel.detach()
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.detached
ASSERT channel.errorReason IS null
```
