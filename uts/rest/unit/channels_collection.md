# REST Channels Collection Tests

Spec points: `RSN1`, `RSN2`, `RSN3a`, `RSN3b`, `RSN3c`, `RSN4a`, `RSN4b`

## Test Type
Unit test - no network calls required

These tests verify the REST channels collection management functionality. No mock infrastructure is needed as these tests focus on the in-memory collection behavior.

---

## RSN1 - Channels collection accessible via RestClient

**Spec requirement:** `Channels` is a collection of `RestChannel` objects accessible through `RestClient#channels`.

Tests that the Rest client exposes a channels collection.

### Setup
```pseudo
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Assertions
```pseudo
ASSERT client.channels IS RestChannels
ASSERT client.channels IS NOT null
```

---

## RSN2 - Check if channel exists

**Spec requirement:** Methods should exist to check if a channel exists or iterate through the existing channels.

Tests the `exists()` method returns correct boolean for existing and non-existing channels.

### Setup
```pseudo
channel_name = "test-RSN2-${random_id()}"

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
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
other_channel_name = "test-RSN2-other-${random_id()}"
exists_other = client.channels.exists(other_channel_name)
```

### Assertions
```pseudo
ASSERT exists_before == false
ASSERT exists_after == true
ASSERT exists_other == false
```

---

## RSN2 - Iterate through existing channels

**Spec requirement:** Methods should exist to check if a channel exists or iterate through the existing channels.

Tests that channels can be iterated.

### Setup
```pseudo
channel_name_a = "test-RSN2-a-${random_id()}"
channel_name_b = "test-RSN2-b-${random_id()}"
channel_name_c = "test-RSN2-c-${random_id()}"

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Create several channels
client.channels.get(channel_name_a)
client.channels.get(channel_name_b)
client.channels.get(channel_name_c)

# Iterate channels
channel_names = [ch.name FOR ch IN client.channels]
```

### Assertions
```pseudo
ASSERT channel_name_a IN channel_names
ASSERT channel_name_b IN channel_names
ASSERT channel_name_c IN channel_names
ASSERT length(channel_names) == 3
```

---

## RSN3a - Get creates new channel if none exists

**Spec requirement:** Creates a new `RestChannel` object for the specified channel if none exists, or returns the existing channel. `ChannelOptions` can be provided in an optional second argument.

### Setup
```pseudo
channel_name = "test-RSN3a-${random_id()}"

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
channel = client.channels.get(channel_name)
```

### Assertions
```pseudo
ASSERT channel IS RestChannel
ASSERT channel.name == channel_name
ASSERT client.channels.exists(channel_name) == true
```

---

## RSN3a - Get returns existing channel

**Spec requirement:** Creates a new `RestChannel` object for the specified channel if none exists, or returns the existing channel.

### Setup
```pseudo
channel_name = "test-RSN3a-existing-${random_id()}"

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
channel1 = client.channels.get(channel_name)
channel2 = client.channels.get(channel_name)
```

### Assertions
```pseudo
ASSERT channel1 IS SAME AS channel2  # Same object reference
ASSERT channel1.name == channel_name
```

---

## RSN3a - Operator subscript creates or returns channel

**Spec requirement:** Creates a new `RestChannel` object for the specified channel if none exists, or returns the existing channel.

### Setup
```pseudo
channel_name = "test-RSN3a-subscript-${random_id()}"

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
channel1 = client.channels[channel_name]
channel2 = client.channels.get(channel_name)
channel3 = client.channels[channel_name]
```

### Assertions
```pseudo
ASSERT channel1 IS SAME AS channel2
ASSERT channel2 IS SAME AS channel3
ASSERT channel1.name == channel_name
```

---

## RSN4a - Release removes channel

**Spec requirement:** Takes one argument, the channel name, and releases the corresponding channel entity (that is, deletes it to allow it to be garbage collected).

### Setup
```pseudo
channel_name = "test-RSN4a-${random_id()}"

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
client.channels.get(channel_name)
ASSERT client.channels.exists(channel_name) == true

client.channels.release(channel_name)
```

### Assertions
```pseudo
ASSERT client.channels.exists(channel_name) == false
```

---

## RSN4b - Release on non-existent channel is no-op

**Spec requirement:** Calling `release()` with a channel name that does not correspond to an extant channel entity must return without error.

### Setup
```pseudo
channel_name = "test-RSN4b-${random_id()}"

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Release a channel that was never created — should not throw
client.channels.release(channel_name)
```

### Assertions
```pseudo
ASSERT client.channels.exists(channel_name) == false
```

---

## RSN3a - Get after release creates new channel

**Spec requirement:** Creates a new `RestChannel` object for the specified channel if none exists.

Tests that getting a channel after release creates a fresh instance.

### Setup
```pseudo
channel_name = "test-RSN3a-release-${random_id()}"

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
channel1 = client.channels.get(channel_name)

client.channels.release(channel_name)

channel2 = client.channels.get(channel_name)
```

### Assertions
```pseudo
ASSERT channel1 IS NOT SAME AS channel2  # Different object instances
ASSERT channel2.name == channel_name
ASSERT client.channels.exists(channel_name) == true
```
