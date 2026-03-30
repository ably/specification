# RealtimePresence Automatic Re-entry Tests

Spec points: `RTP17a`, `RTP17e`, `RTP17g`, `RTP17g1`, `RTP17i`

## Test Type
Unit test — mock WebSocket required.

## Purpose

Tests automatic re-entry of presence members when a channel reattaches. The
RealtimePresence object maintains an internal PresenceMap (RTP17) of locally-entered
members. When the channel receives an ATTACHED ProtocolMessage (except when already
attached with RESUMED flag), it re-publishes an ENTER for each member in the internal map.

**Important:** The internal PresenceMap (LocalPresenceMap) is populated from server
PRESENCE echoes — messages with the current connection's connectionId — NOT directly
from the client's `enter()` or `enterClient()` calls. The server always echoes presence
events back to the originating client. Mock WebSocket setups must simulate this echo
for the LocalPresenceMap to contain any members for re-entry.

---

## RTP17i - Automatic re-entry on ATTACHED (non-RESUMED)

**Spec requirement:** The RealtimePresence object should perform automatic re-entry
whenever the channel receives an ATTACHED ProtocolMessage, except in the case where
the channel is already attached and the ProtocolMessage has the RESUMED bit flag set.

### Setup
```pseudo
channel_name = "test-RTP17i-${random_id()}"

connection_count = 0
captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_count++
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "conn-${connection_count}"
    ))
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
      # Server echoes the presence event back to the client.
      # This populates the LocalPresenceMap (RTP17) which is keyed by
      # server echoes, not by the client's own enter() calls.
      FOR idx, p IN enumerate(msg.presence):
        mock_ws.send_to_client(ProtocolMessage(
          action: PRESENCE,
          channel: channel_name,
          connectionId: "conn-${connection_count}",
          presence: [
            PresenceMessage(
              action: p.action,
              clientId: p.clientId OR "my-client",
              connectionId: "conn-${connection_count}",
              id: "conn-${connection_count}:${msg.msgSerial}:${idx}",
              timestamp: NOW(),
              data: p.data
            )
          ]
        ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "my-client", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Enter presence
AWAIT channel.presence.enter(data: "hello")

ASSERT captured_presence.length == 1

# Simulate disconnect and reconnect (new connectionId)
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.disconnected

# Clear captured to track only re-entry messages
captured_presence = []

# Reconnect — triggers reattach with new ATTACHED (non-RESUMED)
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT_STATE channel.state == ChannelState.attached
```

### Assertions
```pseudo
# RTP17i: Automatic re-entry sends ENTER for the member
ASSERT captured_presence.length >= 1

reenter = captured_presence.find(m => m.presence[0].action == ENTER)
ASSERT reenter IS NOT null
```

---

## RTP17g - Re-entry publishes ENTER with stored clientId and data

**Spec requirement:** For each member of the RTP17 internal PresenceMap, publish a
PresenceMessage with an ENTER action using the clientId, data, and id attributes
from that member.

### Setup
```pseudo
channel_name = "test-RTP17g-${random_id()}"

connection_count = 0
captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_count++
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "conn-${connection_count}"
    ))
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
      # Server echoes the presence event back to populate LocalPresenceMap
      FOR idx, p IN enumerate(msg.presence):
        mock_ws.send_to_client(ProtocolMessage(
          action: PRESENCE,
          channel: channel_name,
          connectionId: "conn-${connection_count}",
          presence: [
            PresenceMessage(
              action: p.action,
              clientId: p.clientId,
              connectionId: "conn-${connection_count}",
              id: "conn-${connection_count}:${msg.msgSerial}:${idx}",
              timestamp: NOW(),
              data: p.data
            )
          ]
        ))
  }
)
install_mock(mock_ws)

# Use a non-wildcard clientId that has enterClient permission.
# Note: Some SDKs reject wildcard clientId "*" at the ClientOptions level.
# Use a concrete clientId and rely on server-side permission for enterClient.
client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "admin", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Enter multiple members via enterClient
AWAIT channel.presence.enterClient("alice", data: "alice-data")
AWAIT channel.presence.enterClient("bob", data: "bob-data")

ASSERT captured_presence.length == 2

# Simulate disconnect and reconnect
captured_presence = []
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.disconnected

AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT_STATE channel.state == ChannelState.attached
```

### Assertions
```pseudo
# Both members re-entered with ENTER action and original data
reentry_messages = captured_presence.filter(m => m.action == PRESENCE)
presence_items = []
FOR msg IN reentry_messages:
  FOR p IN msg.presence:
    presence_items.append(p)

ASSERT presence_items.length >= 2

alice_reentry = presence_items.find(p => p.clientId == "alice")
bob_reentry = presence_items.find(p => p.clientId == "bob")

ASSERT alice_reentry IS NOT null
ASSERT alice_reentry.action == ENTER
ASSERT alice_reentry.data == "alice-data"

ASSERT bob_reentry IS NOT null
ASSERT bob_reentry.action == ENTER
ASSERT bob_reentry.data == "bob-data"
```

---

## RTP17g1 - Re-entry omits id when connectionId changed

**Spec requirement:** If the current connection id is different from the connectionId
attribute of the stored member, the published PresenceMessage must not have its id set.

### Setup
```pseudo
channel_name = "test-RTP17g1-${random_id()}"

connection_count = 0
captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_count++
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "conn-${connection_count}"
    ))
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
      # Server echoes the presence event back to populate LocalPresenceMap
      FOR idx, p IN enumerate(msg.presence):
        mock_ws.send_to_client(ProtocolMessage(
          action: PRESENCE,
          channel: channel_name,
          connectionId: "conn-${connection_count}",
          presence: [
            PresenceMessage(
              action: p.action,
              clientId: p.clientId OR "my-client",
              connectionId: "conn-${connection_count}",
              id: "conn-${connection_count}:${msg.msgSerial}:${idx}",
              timestamp: NOW(),
              data: p.data
            )
          ]
        ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "my-client", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

AWAIT channel.presence.enter(data: "hello")

# First connection is conn-1
ASSERT connection_count == 1

# Disconnect and reconnect — new connectionId (conn-2)
captured_presence = []
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.disconnected

AWAIT_STATE client.connection.state == ConnectionState.connected
ASSERT connection_count == 2

AWAIT_STATE channel.state == ChannelState.attached
```

### Assertions
```pseudo
# Re-entry message should NOT have id set because connectionId changed
reentry = captured_presence.find(m => m.action == PRESENCE)
ASSERT reentry IS NOT null

reentry_presence = reentry.presence[0]
ASSERT reentry_presence.action == ENTER
ASSERT reentry_presence.id IS null  # RTP17g1: id not set when connectionId changed
ASSERT reentry_presence.data == "hello"
```

---

## RTP17i - No re-entry when ATTACHED with RESUMED flag

**Spec requirement:** Automatic re-entry is NOT performed when the channel is already
attached and the ProtocolMessage has the RESUMED bit flag set.

### Setup
```pseudo
channel_name = "test-RTP17i-resumed-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionId: "conn-1", connectionKey: "key-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
      # Server echoes the presence event back to populate LocalPresenceMap
      FOR idx, p IN enumerate(msg.presence):
        mock_ws.send_to_client(ProtocolMessage(
          action: PRESENCE,
          channel: channel_name,
          connectionId: "conn-1",
          presence: [
            PresenceMessage(
              action: p.action,
              clientId: p.clientId OR "my-client",
              connectionId: "conn-1",
              id: "conn-1:${msg.msgSerial}:${idx}",
              timestamp: NOW(),
              data: p.data
            )
          ]
        ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "my-client", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

AWAIT channel.presence.enter(data: "hello")

# Clear captured
captured_presence = []

# Server sends ATTACHED with RESUMED flag while already attached
# (e.g., after a brief transport-level reconnect that preserved the connection)
mock_ws.send_to_client(ProtocolMessage(
  action: ATTACHED,
  channel: channel_name,
  flags: RESUMED
))
```

### Assertions
```pseudo
# No re-entry — RESUMED flag means the server still has our presence state
ASSERT captured_presence.length == 0
```

---

## RTP17e - Failed re-entry emits UPDATE with error

**Spec requirement:** If an automatic presence ENTER fails (e.g., NACK), emit an UPDATE
event on the channel with resumed=true and reason set to ErrorInfo with code 91004,
message indicating the failure and clientId, and cause set to the NACK error.

### Setup
```pseudo
channel_name = "test-RTP17e-${random_id()}"

connection_count = 0
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_count++
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "conn-${connection_count}"
    ))
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      IF connection_count == 1:
        # First connection: ACK the enter and echo back the presence event
        mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
        FOR idx, p IN enumerate(msg.presence):
          mock_ws.send_to_client(ProtocolMessage(
            action: PRESENCE,
            channel: channel_name,
            connectionId: "conn-1",
            presence: [
              PresenceMessage(
                action: p.action,
                clientId: p.clientId OR "my-client",
                connectionId: "conn-1",
                id: "conn-1:${msg.msgSerial}:${idx}",
                timestamp: NOW(),
                data: p.data
              )
            ]
          ))
      ELSE:
        # Second connection: NACK the re-entry
        mock_ws.send_to_client(ProtocolMessage(
          action: NACK,
          msgSerial: msg.msgSerial,
          count: 1,
          error: ErrorInfo(code: 40160, statusCode: 401, message: "Presence denied")
        ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "my-client", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

AWAIT channel.presence.enter(data: "hello")

# Listen for channel UPDATE events with the re-entry failure error code.
# Note: The ATTACHED state change itself may also emit an UPDATE event
# (e.g., when transitioning from ATTACHED to ATTACHED with resumed=false).
# Filter for the specific 91004 error code to distinguish re-entry failure.
channel_events = []
channel.on(ChannelEvent.update, (change) => {
  IF change.reason IS NOT null AND change.reason.code == 91004:
    channel_events.append(change)
})

# Disconnect and reconnect — re-entry will be NACKed
mock_ws.active_connection.simulate_disconnect()
AWAIT_STATE client.connection.state == ConnectionState.disconnected

AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT_STATE channel.state == ChannelState.attached

# Wait for the re-entry NACK to be processed
AWAIT UNTIL channel_events.length >= 1
```

### Assertions
```pseudo
ASSERT channel_events.length >= 1

update_event = channel_events[0]
ASSERT update_event.resumed == true
ASSERT update_event.reason IS NOT null
ASSERT update_event.reason.code == 91004
ASSERT update_event.reason.message CONTAINS "my-client"
ASSERT update_event.reason.cause IS NOT null
ASSERT update_event.reason.cause.code == 40160
```

---

## RTP17a - Server publishes member regardless of subscribe capability

**Spec requirement:** All members belonging to the current connection are published as a
PresenceMessage on the channel by the server irrespective of whether the client has
permission to subscribe. The member should be present in both the internal and public
presence set via get.

### Setup
```pseudo
channel_name = "test-RTP17a-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionId: "conn-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Channel with presence capability but no subscribe capability
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: PRESENCE
      ))
    ELSE IF msg.action == PRESENCE:
      # ACK the enter
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
      # Server delivers the presence event back to the client
      mock_ws.send_to_client(ProtocolMessage(
        action: PRESENCE,
        channel: channel_name,
        presence: [
          PresenceMessage(
            action: ENTER,
            clientId: "my-client",
            connectionId: "conn-1",
            id: "conn-1:0:0",
            timestamp: 1000
          )
        ]
      ))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "my-client", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

AWAIT channel.presence.enter()

# Check public presence map
members = channel.presence.get(waitForSync: false)
```

### Assertions
```pseudo
ASSERT members.length == 1
ASSERT members[0].clientId == "my-client"
```
