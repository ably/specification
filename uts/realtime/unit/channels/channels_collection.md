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
```

---

## RTS2 - Check if channel exists

**Spec requirement:** Methods should exist to check if a channel exists or iterate through the existing channels.

Tests the `exists()` method returns correct boolean for existing and non-existing channels.

### Setup
```pseudo
client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Before creating any channel
exists_before = client.channels.exists("test-channel")

# Create the channel
channel = client.channels.get("test-channel")

# After creating the channel
exists_after = client.channels.exists("test-channel")

# Check for non-existent channel
exists_other = client.channels.exists("other-channel")
```

### Assertions
```pseudo
ASSERT exists_before == false
ASSERT exists_after == true
ASSERT exists_other == false
```

---

## RTS2 - Iterate through existing channels

**Spec requirement:** Methods should exist to check if a channel exists or iterate through the existing channels.

Tests that channel names can be iterated.

### Setup
```pseudo
client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Create several channels
client.channels.get("channel-a")
client.channels.get("channel-b")
client.channels.get("channel-c")

# Get all channel names
names = client.channels.names
```

### Assertions
```pseudo
ASSERT "channel-a" IN names
ASSERT "channel-b" IN names
ASSERT "channel-c" IN names
ASSERT length(names) == 3
```

---

## RTS3a - Get creates new channel if none exists

**Spec requirement:** Creates a new `RealtimeChannel` object for the specified channel if none exists, or returns the existing channel.

Tests that `get()` creates a new channel when called with a new name.

### Setup
```pseudo
client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Get a channel that doesn't exist yet
channel = client.channels.get("new-channel")
```

### Assertions
```pseudo
ASSERT channel IS RealtimeChannel
ASSERT channel.name == "new-channel"
ASSERT client.channels.exists("new-channel") == true
```

---

## RTS3a - Get returns existing channel

**Spec requirement:** Creates a new `RealtimeChannel` object for the specified channel if none exists, or returns the existing channel.

Tests that `get()` returns the same channel instance when called multiple times.

### Setup
```pseudo
client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Get a channel
channel1 = client.channels.get("test-channel")

# Get the same channel again
channel2 = client.channels.get("test-channel")
```

### Assertions
```pseudo
ASSERT channel1 IS SAME AS channel2  # Same object reference
ASSERT channel1.name == "test-channel"
ASSERT channel2.name == "test-channel"
```

---

## RTS3a - Operator subscript creates or returns channel

**Spec requirement:** Creates a new `RealtimeChannel` object for the specified channel if none exists, or returns the existing channel.

Tests that the subscript operator `[]` behaves the same as `get()`.

### Setup
```pseudo
client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Use subscript to get channel
channel1 = client.channels["test-channel"]

# Use get() to get same channel
channel2 = client.channels.get("test-channel")

# Use subscript again
channel3 = client.channels["test-channel"]
```

### Assertions
```pseudo
ASSERT channel1 IS SAME AS channel2
ASSERT channel2 IS SAME AS channel3
ASSERT channel1.name == "test-channel"
```

---

## RTS4a - Release detaches and removes channel

**Spec requirement:** Detaches the channel and then releases the channel resource i.e. it's deleted and can then be garbage collected.

Tests that `release()` removes the channel from the collection.

### Setup
```pseudo
client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Create a channel
channel = client.channels.get("test-channel")
ASSERT client.channels.exists("test-channel") == true

# Release the channel
AWAIT client.channels.release("test-channel")
```

### Assertions
```pseudo
ASSERT client.channels.exists("test-channel") == false
```

---

## RTS4a - Release on non-existent channel is no-op

**Spec requirement:** Detaches the channel and then releases the channel resource.

Tests that releasing a channel that doesn't exist completes without error.

### Setup
```pseudo
client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Release a channel that was never created
AWAIT client.channels.release("nonexistent-channel")
```

### Assertions
```pseudo
# Should complete without throwing
ASSERT client.channels.exists("nonexistent-channel") == false
```

---

## RTS4a - Release calls detach on attached channel

**Spec requirement:** Detaches the channel and then releases the channel resource.

Tests that releasing an attached channel detaches it first.

### Setup
```pseudo
client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
```

### Test Steps
```pseudo
# Create and attach a channel
channel = client.channels.get("test-channel")
AWAIT channel.attach()
ASSERT channel.state == ChannelState.attached

# Capture the state before release
state_before_release = channel.state

# Release the channel
AWAIT client.channels.release("test-channel")
```

### Assertions
```pseudo
ASSERT state_before_release == ChannelState.attached
ASSERT client.channels.exists("test-channel") == false
# Channel should have been detached before removal
```

---

## RTS3a - Get after release creates new channel

**Spec requirement:** Creates a new `RealtimeChannel` object for the specified channel if none exists.

Tests that getting a channel after release creates a fresh instance.

### Setup
```pseudo
client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Create a channel
channel1 = client.channels.get("test-channel")

# Release it
AWAIT client.channels.release("test-channel")

# Get the same channel name again
channel2 = client.channels.get("test-channel")
```

### Assertions
```pseudo
ASSERT channel1 IS NOT SAME AS channel2  # Different object instances
ASSERT channel2.name == "test-channel"
ASSERT client.channels.exists("test-channel") == true
```
