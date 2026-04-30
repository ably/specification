# RealtimePresence Enter/Update/Leave Tests

Spec points: `RTP4`, `RTP8`, `RTP8a`–`RTP8j`, `RTP9`, `RTP9a`–`RTP9e`, `RTP10`, `RTP10a`–`RTP10e`, `RTP14`, `RTP14a`–`RTP14d`, `RTP15`, `RTP15a`–`RTP15f`, `RTP16`, `RTP16a`–`RTP16c`

## Test Type
Unit test — mock WebSocket required.

## Purpose

Tests the `RealtimePresence#enter`, `update`, `leave`, `enterClient`, `updateClient`,
and `leaveClient` functions. These methods send PRESENCE ProtocolMessages to the server
and handle ACK/NACK responses. Tests cover protocol message format, implicit channel
attach, connection state conditions, and error cases.

**Note on wildcard clientId:** Several tests use `clientId: "*"` (wildcard) which is
the Ably convention for clients permitted to act on behalf of any clientId via
`enterClient`/`updateClient`/`leaveClient`. Some SDKs may reject `"*"` at the
`ClientOptions` construction level. In such cases, adapt these tests to use a
concrete clientId (e.g., `"admin"`) and skip the client-side `enterClient` clientId
mismatch check (RTP15f), or configure the mock to accept any clientId.

---

## RTP8a, RTP8c - enter sends PRESENCE with ENTER action

**Spec requirement:** Enters the current client into this channel. A PRESENCE
ProtocolMessage with a PresenceMessage with action ENTER is sent. The clientId
attribute of the PresenceMessage must not be present (implicitly uses the connection's
clientId).

### Setup
```pseudo
channel_name = "test-RTP8a-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionId: "conn-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(
        action: ACK,
        msgSerial: msg.msgSerial,
        count: 1
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
```

### Assertions
```pseudo
ASSERT captured_presence.length == 1
ASSERT captured_presence[0].action == PRESENCE
ASSERT captured_presence[0].channel == channel_name
ASSERT captured_presence[0].presence.length == 1
ASSERT captured_presence[0].presence[0].action == ENTER
# RTP8c: clientId must NOT be present in the PresenceMessage
ASSERT captured_presence[0].presence[0].clientId IS null

CLOSE_CLIENT(client)
```

---

## RTP8e - enter with data

**Spec requirement:** Optional data can be included when entering. Data will be encoded
and decoded as with normal messages.

### Setup
```pseudo
channel_name = "test-RTP8e-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionId: "conn-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
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

AWAIT channel.presence.enter(data: "hello world")
```

### Assertions
```pseudo
ASSERT captured_presence.length == 1
ASSERT captured_presence[0].presence[0].action == ENTER
ASSERT captured_presence[0].presence[0].data == "hello world"

CLOSE_CLIENT(client)
```

---

## RTP8d - enter implicitly attaches channel

**Spec requirement:** Implicitly attaches the RealtimeChannel if the channel is in the
INITIALIZED state.

### Setup
```pseudo
channel_name = "test-RTP8d-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionId: "conn-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
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

ASSERT channel.state == ChannelState.initialized

# enter() on INITIALIZED channel triggers implicit attach
AWAIT channel.presence.enter()
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached

CLOSE_CLIENT(client)
```

---

## RTP8g - enter on DETACHED or FAILED channel errors

**Spec requirement:** If the channel is DETACHED or FAILED, the enter request results
in an error immediately.

### Setup
```pseudo
channel_name = "test-RTP8g-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Respond with error to put channel in FAILED state
      mock_ws.send_to_client(ProtocolMessage(
        action: ERROR,
        channel: channel_name,
        error: ErrorInfo(code: 90001, message: "Channel failed")
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

# Put channel into FAILED state
AWAIT channel.attach() FAILS WITH attach_error
ASSERT channel.state == ChannelState.failed

# enter() on FAILED channel should error immediately
AWAIT channel.presence.enter() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null

CLOSE_CLIENT(client)
```

---

## RTP8j - enter with wildcard or null clientId errors

**Spec requirement:** If the connection is CONNECTED and the clientId is '*' (wildcard)
or null (anonymous), the enter request results in an error immediately.

### Setup
```pseudo
channel_name = "test-RTP8j-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
  }
)
install_mock(mock_ws)

# No clientId — anonymous client
client = Realtime(options: ClientOptions(key: "fake.key:secret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# enter() without clientId should error
AWAIT channel.presence.enter() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null

CLOSE_CLIENT(client)
```

---

## RTP8j - enter with wildcard clientId errors

### Setup

Note: Some SDKs may reject wildcard clientId `"*"` at the `ClientOptions`
construction level rather than at `enter()` time. In that case, this test
validates that the error occurs at `ClientOptions` creation instead.
```pseudo
channel_name = "test-RTP8j-wild-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
  }
)
install_mock(mock_ws)

# Wildcard clientId
client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "*", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

AWAIT channel.presence.enter() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null

CLOSE_CLIENT(client)
```

---

## RTP8h - NACK for missing presence permission

**Spec requirement:** If the Ably service determines that the client does not have
required presence permission, a NACK is sent resulting in an error.

### Setup
```pseudo
channel_name = "test-RTP8h-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      mock_ws.send_to_client(ProtocolMessage(
        action: NACK,
        msgSerial: msg.msgSerial,
        count: 1,
        error: ErrorInfo(code: 40160, statusCode: 401, message: "Presence permission denied")
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

AWAIT channel.presence.enter() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
ASSERT error.code == 40160

CLOSE_CLIENT(client)
```

---

## RTP9a, RTP9d - update sends PRESENCE with UPDATE action

**Spec requirement:** Updates the data for the present member. A PRESENCE ProtocolMessage
with action UPDATE is sent. The clientId must not be present.

### Setup
```pseudo
channel_name = "test-RTP9a-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionId: "conn-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
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

AWAIT channel.presence.update(data: "new-status")
```

### Assertions
```pseudo
ASSERT captured_presence.length == 1
ASSERT captured_presence[0].presence[0].action == UPDATE
ASSERT captured_presence[0].presence[0].data == "new-status"
ASSERT captured_presence[0].presence[0].clientId IS null  # RTP9d

CLOSE_CLIENT(client)
```

---

## RTP10a, RTP10c - leave sends PRESENCE with LEAVE action

**Spec requirement:** Leaves this client from the channel. A PRESENCE ProtocolMessage
with action LEAVE is sent. The clientId must not be present.

### Setup
```pseudo
channel_name = "test-RTP10a-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionId: "conn-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
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

AWAIT channel.presence.leave()
```

### Assertions
```pseudo
ASSERT captured_presence.length == 1
ASSERT captured_presence[0].presence[0].action == LEAVE
ASSERT captured_presence[0].presence[0].clientId IS null  # RTP10c

CLOSE_CLIENT(client)
```

---

## RTP10a - leave with data updates the member data

**Spec requirement:** The data will be updated with the values provided when leaving.

### Setup
```pseudo
channel_name = "test-RTP10a-data-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
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

AWAIT channel.presence.leave(data: "goodbye")
```

### Assertions
```pseudo
ASSERT captured_presence[0].presence[0].action == LEAVE
ASSERT captured_presence[0].presence[0].data == "goodbye"

CLOSE_CLIENT(client)
```

---

## RTP14a - enterClient enters on behalf of another clientId

**Spec requirement:** Enters into presence on a channel on behalf of another clientId.
This allows a single client with suitable permissions to register presence on behalf
of any number of clients using a single connection.

### Setup
```pseudo
channel_name = "test-RTP14a-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "*", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

AWAIT channel.presence.enterClient("user-alice", data: "alice-data")
AWAIT channel.presence.enterClient("user-bob", data: "bob-data")
```

### Assertions
```pseudo
ASSERT captured_presence.length == 2

# First enter: user-alice
ASSERT captured_presence[0].presence[0].action == ENTER
ASSERT captured_presence[0].presence[0].clientId == "user-alice"
ASSERT captured_presence[0].presence[0].data == "alice-data"

# Second enter: user-bob
ASSERT captured_presence[1].presence[0].action == ENTER
ASSERT captured_presence[1].presence[0].clientId == "user-bob"
ASSERT captured_presence[1].presence[0].data == "bob-data"

CLOSE_CLIENT(client)
```

---

## RTP15a - updateClient and leaveClient

**Spec requirement:** Performs update or leave for a given clientId. Functionally
equivalent to the corresponding enter, update, and leave methods.

### Setup
```pseudo
channel_name = "test-RTP15a-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "*", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

AWAIT channel.presence.enterClient("user-1", data: "entered")
AWAIT channel.presence.updateClient("user-1", data: "updated")
AWAIT channel.presence.leaveClient("user-1", data: "leaving")
```

### Assertions
```pseudo
ASSERT captured_presence.length == 3

ASSERT captured_presence[0].presence[0].action == ENTER
ASSERT captured_presence[0].presence[0].clientId == "user-1"
ASSERT captured_presence[0].presence[0].data == "entered"

ASSERT captured_presence[1].presence[0].action == UPDATE
ASSERT captured_presence[1].presence[0].clientId == "user-1"
ASSERT captured_presence[1].presence[0].data == "updated"

ASSERT captured_presence[2].presence[0].action == LEAVE
ASSERT captured_presence[2].presence[0].clientId == "user-1"
ASSERT captured_presence[2].presence[0].data == "leaving"

CLOSE_CLIENT(client)
```

---

## RTP15e - enterClient implicitly attaches channel

**Spec requirement:** Implicitly attaches the RealtimeChannel if the channel is in the
INITIALIZED state. If the channel is in or enters the DETACHED or FAILED state, error.

### Setup
```pseudo
channel_name = "test-RTP15e-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
  }
)
install_mock(mock_ws)

client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "*", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

ASSERT channel.state == ChannelState.initialized

AWAIT channel.presence.enterClient("user-1")
```

### Assertions
```pseudo
ASSERT channel.state == ChannelState.attached

CLOSE_CLIENT(client)
```

---

## RTP15f - enterClient with mismatched clientId errors

**Spec requirement:** If the client is identified and has a valid clientId, and the
clientId argument does not match the client's clientId, then it should indicate an error.

### Setup
```pseudo
channel_name = "test-RTP15f-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
  }
)
install_mock(mock_ws)

# Client has a specific (non-wildcard) clientId
client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "my-client", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# enterClient with a different clientId than the connection's clientId
AWAIT channel.presence.enterClient("other-client") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
# Connection and channel remain available
ASSERT client.connection.state == ConnectionState.connected
ASSERT channel.state == ChannelState.attached

CLOSE_CLIENT(client)
```

---

## RTP16a - Presence message sent when channel is ATTACHED

**Spec requirement:** If the channel is ATTACHED then presence messages are sent
immediately to the connection.

### Setup
```pseudo
channel_name = "test-RTP16a-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
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
```

### Assertions
```pseudo
# Message was sent immediately
ASSERT captured_presence.length == 1

CLOSE_CLIENT(client)
```

---

## RTP16b - Presence message queued when channel is ATTACHING

**Spec requirement:** If the channel is ATTACHING or INITIALIZED and queueMessages is
true, presence messages are queued at channel level, sent once channel becomes ATTACHED.

### Setup
```pseudo
channel_name = "test-RTP16b-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      # Delay the ATTACHED response
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
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

# Start attach but don't complete it
channel.attach()
AWAIT_STATE channel.state == ChannelState.attaching

# Queue presence while ATTACHING
enter_future = channel.presence.enter()

# No messages sent yet
ASSERT captured_presence.length == 0

# Now complete the attach
mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))

AWAIT enter_future
```

### Assertions
```pseudo
# Queued presence message was sent after attach completed
ASSERT captured_presence.length == 1
ASSERT captured_presence[0].presence[0].action == ENTER

CLOSE_CLIENT(client)
```

---

## RTP16c - Presence message errors in other channel states

**Spec requirement:** In any other case (channel not ATTACHED, ATTACHING, or INITIALIZED
with queueMessages) the operation should result in an error.

### Setup
```pseudo
channel_name = "test-RTP16c-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: channel_name,
        error: ErrorInfo(code: 90001, message: "Detached")
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

# Put channel in DETACHED state
AWAIT channel.attach() FAILS WITH attach_error
ASSERT channel.state == ChannelState.detached

AWAIT channel.presence.enter() FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null

CLOSE_CLIENT(client)
```

---

## RTP15c - enterClient has no side effects on normal enter

**Spec requirement:** Using enterClient, updateClient, and leaveClient methods should
have no side effects on a client that has entered normally using enter.

### Setup
```pseudo
channel_name = "test-RTP15c-${random_id()}"

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionId: "conn-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
  }
)
install_mock(mock_ws)

# Wildcard clientId to allow both enter() and enterClient() on the same connection.
# See note in Purpose section about SDK-level wildcard validation.
client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "*", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Normal enter for the wildcard client
AWAIT channel.presence.enter(data: "main-client")

# enterClient for a different user
AWAIT channel.presence.enterClient("other-user", data: "other-data")

# leaveClient for the other user
AWAIT channel.presence.leaveClient("other-user")
```

### Assertions
```pseudo
# Three presence messages sent: enter, enterClient, leaveClient
ASSERT captured_presence.length == 3

# The main client's enter is unaffected by the enterClient/leaveClient calls
ASSERT captured_presence[0].presence[0].action == ENTER
ASSERT captured_presence[0].presence[0].data == "main-client"
ASSERT captured_presence[0].presence[0].clientId IS null  # Uses connection clientId

ASSERT captured_presence[1].presence[0].action == ENTER
ASSERT captured_presence[1].presence[0].clientId == "other-user"

ASSERT captured_presence[2].presence[0].action == LEAVE
ASSERT captured_presence[2].presence[0].clientId == "other-user"

CLOSE_CLIENT(client)
```

---

## RTP4 - 50 members via enterClient (same connection)

**Spec requirement:** Ensure a test exists that enters 250 members using
RealtimePresence#enterClient on a single connection, and checks for PRESENT events
to be emitted for each member, and once sync is complete, all members should be
present in a RealtimePresence#get request.

Note: The spec says 250 but we use 50 as a practical test size that validates the
same behavior (bulk enterClient, SYNC delivery, get correctness) without excessive
test runtime.

This test variant uses a single connection that both enters members and subscribes
to presence. The server echoes ENTER events back on the same connection.

### Setup
```pseudo
channel_name = "test-RTP4-same-${random_id()}"
member_count = 50

captured_presence = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionId: "conn-1")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: HAS_PRESENCE
      ))
    ELSE IF msg.action == PRESENCE:
      captured_presence.append(msg)
      mock_ws.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))

      # Server echoes back the ENTER as a PRESENCE event
      FOR idx, p IN enumerate(msg.presence):
        mock_ws.send_to_client(ProtocolMessage(
          action: PRESENCE,
          channel: channel_name,
          presence: [
            PresenceMessage(
              action: ENTER,
              clientId: p.clientId,
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

client = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "*", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

# Track ENTER events received by subscriber
received_enters = []
channel.presence.subscribe(action: ENTER, (event) => {
  received_enters.append(event)
})

# Enter 50 members
FOR i IN 0..member_count-1:
  AWAIT channel.presence.enterClient("user-${i}", data: "data-${i}")

# Send a complete SYNC with all 50 members as PRESENT
sync_members = []
FOR i IN 0..member_count-1:
  sync_members.append(PresenceMessage(
    action: PRESENT,
    clientId: "user-${i}",
    connectionId: "conn-1",
    id: "conn-1:${i}:0",
    timestamp: NOW(),
    data: "data-${i}"
  ))

mock_ws.send_to_client(ProtocolMessage(
  action: SYNC,
  channel: channel_name,
  channelSerial: "seq1:",
  presence: sync_members
))

# Get all members after sync
members = AWAIT channel.presence.get()
```

### Assertions
```pseudo
# All 50 members entered
ASSERT captured_presence.length == member_count

# All 50 ENTER events received by subscriber
ASSERT received_enters.length == member_count

# All 50 members present after sync
ASSERT members.length == member_count

# Verify each member exists with correct data
FOR i IN 0..member_count-1:
  member = members.find(m => m.clientId == "user-${i}")
  ASSERT member IS NOT null
  ASSERT member.data == "data-${i}"

CLOSE_CLIENT(client)
```

---

## RTP4 - 50 members via enterClient (different connections)

**Spec requirement:** Same as above, but the original intent: one connection enters
members, a different connection observes the ENTER events and verifies all members
via get(). This is the more realistic scenario where one client populates presence
and another client discovers the members.

### Setup
```pseudo
channel_name = "test-RTP4-diff-${random_id()}"
member_count = 50

# --- Connection A: the entering client ---
captured_presence_a = []
mock_ws_a = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionId: "conn-A")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws_a.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: HAS_PRESENCE
      ))
    ELSE IF msg.action == PRESENCE:
      captured_presence_a.append(msg)
      mock_ws_a.send_to_client(ProtocolMessage(action: ACK, msgSerial: msg.msgSerial, count: 1))
  }
)

# --- Connection B: the observing client ---
mock_ws_b = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(
    ProtocolMessage(action: CONNECTED, connectionId: "conn-B")
  ),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws_b.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: channel_name,
        flags: HAS_PRESENCE
      ))
  }
)

install_mock(mock_ws_a, client: "A")
install_mock(mock_ws_b, client: "B")

client_a = Realtime(options: ClientOptions(key: "fake.key:secret", clientId: "*", autoConnect: false))
client_b = Realtime(options: ClientOptions(key: "fake.key:secret", autoConnect: false))
channel_a = client_a.channels.get(channel_name)
channel_b = client_b.channels.get(channel_name)
```

### Test Steps
```pseudo
# Connect and attach both clients
client_a.connect()
AWAIT_STATE client_a.connection.state == ConnectionState.connected
AWAIT channel_a.attach()

client_b.connect()
AWAIT_STATE client_b.connection.state == ConnectionState.connected
AWAIT channel_b.attach()

# Subscribe on client B to observe remote presence events
received_enters_b = []
channel_b.presence.subscribe(action: ENTER, (event) => {
  received_enters_b.append(event)
})

# Client A enters 50 members
FOR i IN 0..member_count-1:
  AWAIT channel_a.presence.enterClient("user-${i}", data: "data-${i}")

# Server delivers those ENTER events to client B as PRESENCE messages
# (In real Ably, the server broadcasts to all connections on the channel)
FOR i IN 0..member_count-1:
  mock_ws_b.send_to_client(ProtocolMessage(
    action: PRESENCE,
    channel: channel_name,
    presence: [
      PresenceMessage(
        action: ENTER,
        clientId: "user-${i}",
        connectionId: "conn-A",
        id: "conn-A:${i}:0",
        timestamp: NOW(),
        data: "data-${i}"
      )
    ]
  ))

# Server sends a SYNC to client B with all 50 members
sync_members = []
FOR i IN 0..member_count-1:
  sync_members.append(PresenceMessage(
    action: PRESENT,
    clientId: "user-${i}",
    connectionId: "conn-A",
    id: "conn-A:${i}:0",
    timestamp: NOW(),
    data: "data-${i}"
  ))

mock_ws_b.send_to_client(ProtocolMessage(
  action: SYNC,
  channel: channel_name,
  channelSerial: "seq1:",
  presence: sync_members
))

# Client B gets all members
members = AWAIT channel_b.presence.get()
```

### Assertions
```pseudo
# Client A sent all 50 presence messages
ASSERT captured_presence_a.length == member_count

# Client B received all 50 ENTER events
ASSERT received_enters_b.length == member_count

# All 50 members present via get() on client B
ASSERT members.length == member_count

# Verify each member has correct data and connectionId from conn-A
FOR i IN 0..member_count-1:
  member = members.find(m => m.clientId == "user-${i}")
  ASSERT member IS NOT null
  ASSERT member.data == "data-${i}"
  ASSERT member.connectionId == "conn-A"

CLOSE_CLIENT(client_a)
CLOSE_CLIENT(client_b)
```
