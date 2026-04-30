# RealtimeChannels Collection Tests

Spec points: `RTS1`, `RTS2`, `RTS3a`, `RTS4a`

## Test Type
Unit test - no network calls required

These tests verify the channels collection management functionality. No mock infrastructure is needed as these tests focus on the in-memory collection behavior.

---

## RTS1 - Channels collection accessible via RealtimeClient

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

## RTS4a - Release detaches and removes channel

**Spec requirement:** Detaches the channel and then releases the channel resource i.e. it's deleted and can then be garbage collected.

Tests that `release()` removes the channel from the collection.

### Setup
```pseudo
channel_name = "test-RTS4a-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Create a channel
channel = client.channels.get(channel_name)
ASSERT client.channels.exists(channel_name) == true

# Release the channel
AWAIT client.channels.release(channel_name)
```

### Assertions
```pseudo
ASSERT client.channels.exists(channel_name) == false
CLOSE_CLIENT(client)
```

---

## RTS4a - Release on non-existent channel is no-op

**Spec requirement:** Detaches the channel and then releases the channel resource.

Tests that releasing a channel that doesn't exist completes without error.

### Setup
```pseudo
channel_name = "test-RTS4a-nonexistent-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Release a channel that was never created
AWAIT client.channels.release(channel_name)
```

### Assertions
```pseudo
# Should complete without throwing
ASSERT client.channels.exists(channel_name) == false
CLOSE_CLIENT(client)
```

---

## RTS4a - Release calls detach on attached channel

**Spec requirement:** Detaches the channel and then releases the channel resource.

Tests that releasing an attached channel detaches it first.

### Setup
```pseudo
channel_name = "test-RTS4a-attached-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
```

### Test Steps
```pseudo
# Create and attach a channel
channel = client.channels.get(channel_name)
AWAIT channel.attach()
ASSERT channel.state == ChannelState.attached

# Capture the state before release
state_before_release = channel.state

# Release the channel
AWAIT client.channels.release(channel_name)
```

### Assertions
```pseudo
ASSERT state_before_release == ChannelState.attached
ASSERT client.channels.exists(channel_name) == false
# Channel should have been detached before removal
CLOSE_CLIENT(client)
```

---

## RTS3a - Get after release creates new channel

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
AWAIT client.channels.release(channel_name)

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
