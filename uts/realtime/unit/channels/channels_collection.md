# RealtimeChannels Collection Tests

Spec points: `RTS1`, `RTS2`, `RTS3a`, `RTS4c`, `RTS4d`, `RTS4e`

## Test Type
Unit test - no network calls required

These tests verify the channels collection management functionality. Most need no mock infrastructure, as they focus on the in-memory collection behavior. The `RTS4d` and `RTS4e` tests that attach a channel use the mock WebSocket described in `uts/realtime/unit/helpers/mock_websocket.md`.

---

## RTS1 - Channels collection accessible via RealtimeClient

**Test ID**: `realtime/unit/RTS1/channels-collection-accessible-0`

**Spec requirement:** `Channels` is a collection of `RealtimeChannel` objects accessible through `RealtimeClient#channels`.

Tests that the Realtime client exposes a channels collection.

### Setup
```pseudo
client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
channels = client.channels
```

### Assertions
```pseudo
ASSERT channels IS RealtimeChannels
ASSERT channels IS NOT null
CLOSE_CLIENT(client)
```

---

## RTS2 - Check if channel exists

**Test ID**: `realtime/unit/RTS2/channel-exists-check-0`

**Spec requirement:** Methods should exist to check if a channel exists or iterate through the existing channels.

Tests the `exists()` method returns correct boolean for existing and non-existing channels.

### Setup
```pseudo
channel_name = "test-RTS2-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Before creating any channel
exists_before = client.channels.exists(channel_name)

# Create the channel
channel = client.channels.get(channel_name)

# After creating the channel
exists_after = client.channels.exists(channel_name)

# Check for non-existent channel
other_channel_name = "test-RTS2-other-${random_id()}"
exists_other = client.channels.exists(other_channel_name)
```

### Assertions
```pseudo
ASSERT exists_before == false
ASSERT exists_after == true
ASSERT exists_other == false
CLOSE_CLIENT(client)
```

---

## RTS2 - Iterate through existing channels

**Test ID**: `realtime/unit/RTS2/iterate-channels-1`

**Spec requirement:** Methods should exist to check if a channel exists or iterate through the existing channels.

Tests that channel names can be iterated.

### Setup
```pseudo
channel_name_a = "test-RTS2-a-${random_id()}"
channel_name_b = "test-RTS2-b-${random_id()}"
channel_name_c = "test-RTS2-c-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Create several channels
client.channels.get(channel_name_a)
client.channels.get(channel_name_b)
client.channels.get(channel_name_c)

# Get all channel names
names = client.channels.names
```

### Assertions
```pseudo
ASSERT channel_name_a IN names
ASSERT channel_name_b IN names
ASSERT channel_name_c IN names
ASSERT length(names) == 3
CLOSE_CLIENT(client)
```

---

## RTS3a - Get creates new channel if none exists

**Test ID**: `realtime/unit/RTS3a/get-creates-new-channel-0`

**Spec requirement:** Creates a new `RealtimeChannel` object for the specified channel if none exists, or returns the existing channel.

Tests that `get()` creates a new channel when called with a new name.

### Setup
```pseudo
channel_name = "test-RTS3a-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Get a channel that doesn't exist yet
channel = client.channels.get(channel_name)
```

### Assertions
```pseudo
ASSERT channel IS RealtimeChannel
ASSERT channel.name == channel_name
ASSERT client.channels.exists(channel_name) == true
CLOSE_CLIENT(client)
```

---

## RTS3a - Get returns existing channel

**Test ID**: `realtime/unit/RTS3a/get-returns-existing-channel-1`

**Spec requirement:** Creates a new `RealtimeChannel` object for the specified channel if none exists, or returns the existing channel.

Tests that `get()` returns the same channel instance when called multiple times.

### Setup
```pseudo
channel_name = "test-RTS3a-existing-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Get a channel
channel1 = client.channels.get(channel_name)

# Get the same channel again
channel2 = client.channels.get(channel_name)
```

### Assertions
```pseudo
ASSERT channel1 IS SAME AS channel2  # Same object reference
ASSERT channel1.name == channel_name
ASSERT channel2.name == channel_name
CLOSE_CLIENT(client)
```

---

## RTS3a - Operator subscript creates or returns channel

**Test ID**: `realtime/unit/RTS3a/subscript-operator-channel-2`

**Spec requirement:** Creates a new `RealtimeChannel` object for the specified channel if none exists, or returns the existing channel.

Tests that the subscript operator `[]` behaves the same as `get()`.

### Setup
```pseudo
channel_name = "test-RTS3a-subscript-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Use subscript to get channel
channel1 = client.channels[channel_name]

# Use get() to get same channel
channel2 = client.channels.get(channel_name)

# Use subscript again
channel3 = client.channels[channel_name]
```

### Assertions
```pseudo
ASSERT channel1 IS SAME AS channel2
ASSERT channel2 IS SAME AS channel3
ASSERT channel1.name == channel_name
CLOSE_CLIENT(client)
```

---

## RTS4c - Release on non-existent channel is no-op

**Test ID**: `realtime/unit/RTS4c/release-nonexistent-noop-0`

**Spec requirement:** If there is no channel with that name in the collection, `release()` must return without error.

Tests that releasing a channel that doesn't exist completes without error.

### Setup
```pseudo
channel_name = "test-RTS4c-nonexistent-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
```

### Test Steps
```pseudo
# Release a channel that was never created
client.channels.release(channel_name)
```

### Assertions
```pseudo
# Should complete without throwing
ASSERT client.channels.exists(channel_name) == false
CLOSE_CLIENT(client)
```

---

## RTS4d - Release removes an initialized channel

**Test ID**: `realtime/unit/RTS4d/release-removes-channel-0`

**Spec requirement:** If the channel's state is `INITIALIZED`, `DETACHED` or `FAILED`, the SDK must remove the channel from the collection before `release()` returns, so that it can be garbage collected.

Tests that `release()` synchronously removes an `INITIALIZED` channel from the collection.

### Setup
```pseudo
channel_name = "test-RTS4d-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
```

### Test Steps
```pseudo
channel = client.channels.get(channel_name)
ASSERT channel.state == ChannelState.initialized
ASSERT client.channels.exists(channel_name) == true

client.channels.release(channel_name)
```

### Assertions
```pseudo
ASSERT client.channels.exists(channel_name) == false
CLOSE_CLIENT(client)
```

---

## RTS4d - Release removes a channel once detached

**Test ID**: `realtime/unit/RTS4d/release-after-detach-1`

**Spec requirement:** If the channel's state is `INITIALIZED`, `DETACHED` or `FAILED`, the SDK must remove the channel from the collection before `release()` returns, so that it can be garbage collected.

Tests that a channel which has been attached and then detached can be released.

### Setup
```pseudo
channel_name = "test-RTS4d-detached-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel
      ))
    ELSE IF msg.action == DETACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: DETACHED,
        channel: msg.channel
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
AWAIT channel.detach()
ASSERT channel.state == ChannelState.detached

client.channels.release(channel_name)
```

### Assertions
```pseudo
ASSERT client.channels.exists(channel_name) == false
CLOSE_CLIENT(client)
```

---

## RTS4e - Release of an attached channel fails

**Test ID**: `realtime/unit/RTS4e/release-attached-fails-0`

**Spec requirement:** If the channel's state is anything else, `release()` must raise an `ErrorInfo` with `code` 90011 and `statusCode` 400, and take no other action.

Tests that releasing an `ATTACHED` channel fails, and leaves the channel attached and in the collection.

### Setup
```pseudo
channel_name = "test-RTS4e-attached-${random_id()}"

captured_detach_messages = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == DETACH:
      captured_detach_messages.append(msg)
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(
        action: ATTACHED,
        channel: msg.channel
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
ASSERT channel.state == ChannelState.attached

client.channels.release(channel_name) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 90011
ASSERT error.statusCode == 400
ASSERT channel.state == ChannelState.attached
ASSERT client.channels.exists(channel_name) == true
ASSERT client.channels.get(channel_name) IS SAME AS channel
ASSERT length(captured_detach_messages) == 0
CLOSE_CLIENT(client)
```

---

## RTS3a - Get after release creates new channel

**Test ID**: `realtime/unit/RTS3a/get-after-release-new-3`

**Spec requirement:** Creates a new `RealtimeChannel` object for the specified channel if none exists.

Tests that getting a channel after release creates a fresh instance.

### Setup
```pseudo
channel_name = "test-RTS3a-release-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Create a channel
channel1 = client.channels.get(channel_name)

# Release it
client.channels.release(channel_name)

# Get the same channel name again
channel2 = client.channels.get(channel_name)
```

### Assertions
```pseudo
ASSERT channel1 IS NOT SAME AS channel2  # Different object instances
ASSERT channel2.name == channel_name
ASSERT client.channels.exists(channel_name) == true
CLOSE_CLIENT(client)
```
