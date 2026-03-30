# ChannelOptions and Derived Channels Tests

Spec points: `TB2`, `TB3`, `TB4`, `RTS3b`, `RTS3c`, `RTS3c1`, `RTS5`, `RTL16`

## Test Type
Unit test - no network calls required for most tests

These tests verify channel options and derived channel functionality.

---

## TB2 - ChannelOptions attributes

| Spec | Requirement |
|------|-------------|
| TB2b | `cipher` - CipherParams for encryption |
| TB2c | `params` - Dict of channel parameters |
| TB2d | `modes` - Array of ChannelMode |
| TB4 | `attachOnSubscribe` - boolean, defaults to true |

Tests that ChannelOptions has all required attributes with correct defaults.

### Setup
```pseudo
options = RealtimeChannelOptions()
```

### Assertions
```pseudo
ASSERT options.cipherParams IS null
ASSERT options.params IS null
ASSERT options.modes IS null
ASSERT options.attachOnSubscribe == true
```

---

## TB2c - ChannelOptions with params

**Spec requirement:** `params` is a Dict<string,string> of key/value pairs for channel parameters.

Tests that channel options can be created with params.

### Setup
```pseudo
options = RealtimeChannelOptions(
  params: {"rewind": "1", "delta": "vcdiff"}
)
```

### Assertions
```pseudo
ASSERT options.params["rewind"] == "1"
ASSERT options.params["delta"] == "vcdiff"
```

---

## TB2d - ChannelOptions with modes

**Spec requirement:** `modes` is an array of ChannelMode.

Tests that channel options can be created with modes.

### Setup
```pseudo
options = RealtimeChannelOptions(
  modes: [ChannelMode.publish, ChannelMode.subscribe]
)
```

### Assertions
```pseudo
ASSERT options.modes CONTAINS ChannelMode.publish
ASSERT options.modes CONTAINS ChannelMode.subscribe
ASSERT length(options.modes) == 2
```

---

## TB3 - withCipherKey constructor

**Spec requirement:** Optional constructor that takes a key only.

Tests the withCipherKey factory constructor.

### Setup
```pseudo
# 256-bit key as base64
key = "MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDE="
options = RealtimeChannelOptions.withCipherKey(key)
```

### Assertions
```pseudo
ASSERT options.cipherParams IS NOT null
ASSERT options.cipherParams.algorithm == "aes"
ASSERT options.cipherParams.keyLength == 256
```

---

## TB4 - attachOnSubscribe default

**Spec requirement:** `attachOnSubscribe` defaults to true.

Tests the default value of attachOnSubscribe.

### Setup
```pseudo
options1 = RealtimeChannelOptions()
options2 = RealtimeChannelOptions(attachOnSubscribe: false)
```

### Assertions
```pseudo
ASSERT options1.attachOnSubscribe == true
ASSERT options2.attachOnSubscribe == false
```

---

## RTS3b - Options set on new channel

**Spec requirement:** If options are provided, the options are set on the RealtimeChannel when creating a new RealtimeChannel.

Tests that get() with options sets them on new channels.

### Setup
```pseudo
channel_name = "test-RTS3b-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))

channelOptions = RealtimeChannelOptions(
  params: {"rewind": "1"},
  modes: [ChannelMode.subscribe]
)
```

### Test Steps
```pseudo
channel = client.channels.get(channel_name, channelOptions)
```

### Assertions
```pseudo
ASSERT channel.options.params["rewind"] == "1"
ASSERT channel.options.modes CONTAINS ChannelMode.subscribe
```

---

## RTS3c - Options updated on existing channel (soft-deprecated)

**Spec requirement:** Accessing an existing channel with options will update the options.

Tests that get() with options updates existing channel (when no reattachment needed).

### Setup
```pseudo
channel_name = "test-RTS3c-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))

# Create channel with initial options
initialOptions = RealtimeChannelOptions(attachOnSubscribe: false)
channel = client.channels.get(channel_name, initialOptions)
```

### Test Steps
```pseudo
# Update with new options that don't require reattachment
newOptions = RealtimeChannelOptions(
  cipherParams: CipherParams.fromKey(someKey),
  attachOnSubscribe: true
)
sameChannel = client.channels.get(channel_name, newOptions)
```

### Assertions
```pseudo
ASSERT sameChannel IS SAME AS channel
ASSERT channel.options.cipherParams IS NOT null
ASSERT channel.options.attachOnSubscribe == true
```

---

## RTS3c1 - Error if options would trigger reattachment

**Spec requirement:** If a new set of ChannelOptions is supplied that would trigger a reattachment, it must raise an error.

Tests that get() throws error when params/modes change on attached channel.

### Setup
```pseudo
channel_name = "test-RTS3c1-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))

# Create and attach channel
channel = client.channels.get(channel_name)
AWAIT channel.attach()
ASSERT channel.state == ChannelState.attached
```

### Test Steps
```pseudo
# Try to update with options that require reattachment
newOptions = RealtimeChannelOptions(
  params: {"rewind": "1"}  # params triggers reattachment
)

client.channels.get(channel_name, newOptions) FAILS WITH error
ASSERT error.code == 40000

# Channel options should not have changed
ASSERT channel.options.params IS null
```

---

## RTS3c1 - Error if modes change on attaching channel

**Spec requirement:** Must raise error if options would trigger reattachment on attaching channel.

Tests error when modes change on attaching channel.

### Setup
```pseudo
channel_name = "test-RTS3c1-attaching-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))

channel = client.channels.get(channel_name)
# Put channel in attaching state (implementation detail)
```

### Test Steps
```pseudo
newOptions = RealtimeChannelOptions(
  modes: [ChannelMode.subscribe]  # modes triggers reattachment
)

client.channels.get(channel_name, newOptions) FAILS WITH error
ASSERT error.code == 40000
```

---

## RTL16 - setOptions updates channel options

**Spec requirement:** setOptions takes a ChannelOptions object and sets or updates the stored channel options.

Tests that setOptions updates the channel options.

### Setup
```pseudo
channel_name = "test-RTL16-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
newOptions = RealtimeChannelOptions(
  params: {"delta": "vcdiff"},
  attachOnSubscribe: false
)
AWAIT channel.setOptions(newOptions)
```

### Assertions
```pseudo
ASSERT channel.options.params["delta"] == "vcdiff"
ASSERT channel.options.attachOnSubscribe == false
```

---

## RTL16a - setOptions triggers reattachment when needed

**Spec requirement:** If params or modes are provided and channel is attached, setOptions triggers reattachment.

Tests that setOptions with params/modes on attached channel triggers reattachment.

### Setup
```pseudo
channel_name = "test-RTL16a-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))
channel = client.channels.get(channel_name)
AWAIT channel.attach()
ASSERT channel.state == ChannelState.attached
```

### Test Steps
```pseudo
stateChanges = []
subscription = channel.on().listen((change) => stateChanges.append(change))

newOptions = RealtimeChannelOptions(
  params: {"rewind": "1"}
)
AWAIT channel.setOptions(newOptions)
```

### Assertions
```pseudo
# Should have gone through attaching state
ASSERT stateChanges CONTAINS change WHERE change.current == ChannelState.attaching
ASSERT channel.state == ChannelState.attached
ASSERT channel.options.params["rewind"] == "1"
```

---

## RTS5a - getDerived creates derived channel

**Spec requirement:** Takes RealtimeChannel name and DeriveOptions to create a derived channel.

Tests that getDerived creates a channel with the correct derived name.

### Setup
```pseudo
base_channel_name = "test-RTS5a-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))

deriveOptions = DeriveOptions(filter: "name == 'foo'")
```

### Test Steps
```pseudo
channel = client.channels.getDerived(base_channel_name, deriveOptions)
```

### Assertions
```pseudo
# Channel name should be encoded with filter
ASSERT channel.name STARTS WITH "[filter="
ASSERT channel.name ENDS WITH "]" + base_channel_name
```

---

## RTS5a1 - Derived channel filter is base64 encoded

**Spec requirement:** The filter should be synthesized as [filter=<base64 encoded JMESPath string>]channelName.

Tests that the filter expression is base64 encoded in the channel name.

### Setup
```pseudo
base_channel_name = "test-RTS5a1-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))

filter = "name == 'test'"
deriveOptions = DeriveOptions(filter: filter)
```

### Test Steps
```pseudo
channel = client.channels.getDerived(base_channel_name, deriveOptions)
expectedEncoded = base64_encode(filter)  # "bmFtZSA9PSAndGVzdCc="
```

### Assertions
```pseudo
ASSERT channel.name == "[filter=" + expectedEncoded + "]" + base_channel_name
```

---

## RTS5a2 - Derived channel with params

**Spec requirement:** If channel options are provided with params, they are included in the derived channel name.

Tests that channel params are included in the derived channel name.

### Setup
```pseudo
base_channel_name = "test-RTS5a2-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))

deriveOptions = DeriveOptions(filter: "type == 'message'")
channelOptions = RealtimeChannelOptions(
  params: {"rewind": "1", "delta": "vcdiff"}
)
```

### Test Steps
```pseudo
channel = client.channels.getDerived(base_channel_name, deriveOptions, channelOptions)
```

### Assertions
```pseudo
# Parse the channel name to extract the qualifier and base name
# Expected format: [filter=<base64>?param1=val1&param2=val2]baseName
ASSERT channel.name ENDS WITH "]" + base_channel_name

# Extract the qualifier (everything between [ and ])
qualifier = extract_between(channel.name, "[", "]")

# Verify filter is present
ASSERT qualifier STARTS WITH "filter="

# Extract and parse params from qualifier (after the ?)
IF qualifier CONTAINS "?":
  paramsString = qualifier.split("?")[1]
  parsedParams = parse_query_string(paramsString)
  ASSERT parsedParams["rewind"] == "1"
  ASSERT parsedParams["delta"] == "vcdiff"
  ASSERT length(parsedParams) == 2
ELSE:
  FAIL("Expected params in qualifier")
```

---

## RTS5 - getDerived with options sets them on channel

**Spec requirement:** ChannelOptions can be provided as an optional third argument.

Tests that getDerived passes options to the created channel.

### Setup
```pseudo
base_channel_name = "test-RTS5-${random_id()}"

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false))

deriveOptions = DeriveOptions(filter: "true")
channelOptions = RealtimeChannelOptions(
  modes: [ChannelMode.subscribe],
  attachOnSubscribe: false
)
```

### Test Steps
```pseudo
channel = client.channels.getDerived(base_channel_name, deriveOptions, channelOptions)
```

### Assertions
```pseudo
ASSERT channel.options.modes CONTAINS ChannelMode.subscribe
ASSERT channel.options.attachOnSubscribe == false
```

---

## DO2a - DeriveOptions filter attribute

**Spec requirement:** DeriveOptions has a filter attribute containing a JMESPath string expression.

Tests the DeriveOptions class.

### Setup
```pseudo
deriveOptions = DeriveOptions(filter: "name == 'event' && data.count > 10")
```

### Assertions
```pseudo
ASSERT deriveOptions.filter == "name == 'event' && data.count > 10"
```
