# Push Admin Integration Tests

Spec points: `RSH1`, `RSH1a`, `RSH1b1`, `RSH1b2`, `RSH1b3`, `RSH1b4`, `RSH1b5`, `RSH1c1`, `RSH1c2`, `RSH1c3`, `RSH1c4`, `RSH1c5`

## Test Type
Integration test against Ably sandbox

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox-rest.ably.io`.

### App Provisioning

Uses `ably-common/test-resources/test-app-setup.json` which provides:
- `keys[0]` — full access (default capability `{"*":["*"]}`)
- `keys[1]` — includes `pushenabled:admin:*` with `push-admin` capability

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  full_access_key = app_config.keys[0].key_str
  push_admin_key = app_config.keys[1].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {full_access_key}
```

### Notes
- All clients use `useBinaryProtocol: false` (SDK does not implement msgpack)
- All clients use `endpoint: "sandbox"`
- Push admin operations require the `push-admin` capability — use `push_admin_key` or `full_access_key`
- Device registrations created during tests must be cleaned up to avoid polluting the sandbox

---

## RSH1a — publish sends push notification to clientId

**Spec requirement:** RSH1a — `publish(recipient, data)` performs an HTTP request to `/push/publish`.

Tests that a push notification can be published to a `clientId` recipient. The sandbox accepts the request even though no real device receives it.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
```

### Test Steps and Assertions
```pseudo
# Publish with clientId recipient — should not throw
AWAIT client.push.admin.publish(
  recipient: { "clientId": "test-client-push" },
  data: {
    "notification": {
      "title": "Integration Test",
      "body": "Hello from push admin"
    }
  }
)
```

---

## RSH1a — publish rejects invalid recipient

**Spec requirement:** RSH1a — Tests should exist with invalid recipient details.

Tests that the sandbox returns an error for an empty recipient.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.admin.publish(
  recipient: {},
  data: { "notification": { "title": "Test" } }
) FAILS WITH error
ASSERT error.code IS NOT null
```

---

## RSH1b3, RSH1b1 — save and get device registration

| Spec | Requirement |
|------|-------------|
| RSH1b3 | `#save(device)` issues a PUT to register a device |
| RSH1b1 | `#get(deviceId)` retrieves a registered device |

Tests the full device registration lifecycle: save, then retrieve.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
device_id = "test-device-" + random_id()
```

### Test Steps
```pseudo
# Save a device registration
saved = AWAIT client.push.admin.deviceRegistrations.save(DeviceDetails(
  id: device_id,
  platform: "ios",
  formFactor: "phone",
  push: DevicePushDetails(
    recipient: { "transportType": "apns", "deviceToken": "test-token-" + random_id() }
  )
))
```

### Assertions
```pseudo
ASSERT saved IS DeviceDetails
ASSERT saved.id == device_id
ASSERT saved.platform == "ios"
ASSERT saved.formFactor == "phone"
ASSERT saved.push.recipient["transportType"] == "apns"

# Retrieve the same device
retrieved = AWAIT client.push.admin.deviceRegistrations.get(device_id)
ASSERT retrieved IS DeviceDetails
ASSERT retrieved.id == device_id
ASSERT retrieved.platform == "ios"
```

### Cleanup
```pseudo
AWAIT client.push.admin.deviceRegistrations.remove(device_id)
```

---

## RSH1b3 — save updates existing device registration

**Spec requirement:** RSH1b3 — A test should exist for a successful subsequent save with an update.

Tests that saving a device with the same ID updates the existing registration.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
device_id = "test-device-update-" + random_id()
```

### Test Steps
```pseudo
# Initial save
AWAIT client.push.admin.deviceRegistrations.save(DeviceDetails(
  id: device_id,
  platform: "ios",
  formFactor: "phone",
  push: DevicePushDetails(
    recipient: { "transportType": "apns", "deviceToken": "token-v1" }
  )
))

# Update with new token
updated = AWAIT client.push.admin.deviceRegistrations.save(DeviceDetails(
  id: device_id,
  platform: "ios",
  formFactor: "phone",
  push: DevicePushDetails(
    recipient: { "transportType": "apns", "deviceToken": "token-v2" }
  )
))
```

### Assertions
```pseudo
ASSERT updated.id == device_id
ASSERT updated.push.recipient["deviceToken"] == "token-v2"

# Verify via get
retrieved = AWAIT client.push.admin.deviceRegistrations.get(device_id)
ASSERT retrieved.push.recipient["deviceToken"] == "token-v2"
```

### Cleanup
```pseudo
AWAIT client.push.admin.deviceRegistrations.remove(device_id)
```

---

## RSH1b1 — get returns error for unknown device

**Spec requirement:** RSH1b1 — Results in a not found error if the device cannot be found.

Tests that retrieving a nonexistent device returns a not-found error.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.admin.deviceRegistrations.get("nonexistent-device-" + random_id()) FAILS WITH error
ASSERT error.statusCode == 404
```

---

## RSH1b2 — list device registrations with filters

**Spec requirement:** RSH1b2 — `#list(params)` returns a paginated result with `DeviceDetails` filtered by params.

Tests listing device registrations filtered by `deviceId`.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
device_id = "test-device-list-" + random_id()

# Register a device first
AWAIT client.push.admin.deviceRegistrations.save(DeviceDetails(
  id: device_id,
  platform: "android",
  formFactor: "tablet",
  push: DevicePushDetails(
    recipient: { "transportType": "gcm", "registrationToken": "test-token" }
  )
))
```

### Test Steps
```pseudo
result = AWAIT client.push.admin.deviceRegistrations.list({"deviceId": device_id})
```

### Assertions
```pseudo
ASSERT result IS PaginatedResult
ASSERT result.items.length == 1
ASSERT result.items[0].id == device_id
ASSERT result.items[0].platform == "android"
```

### Cleanup
```pseudo
AWAIT client.push.admin.deviceRegistrations.remove(device_id)
```

---

## RSH1b2 — list supports pagination with limit

**Spec requirement:** RSH1b2 — A test should exist controlling the pagination with the `limit` attribute.

Tests that the `limit` parameter restricts the number of results.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
client_id = "test-client-list-" + random_id()
device_ids = []

# Register multiple devices with the same clientId
FOR i IN [1, 2, 3]:
  device_id = "test-device-limit-" + i + "-" + random_id()
  device_ids.append(device_id)
  AWAIT client.push.admin.deviceRegistrations.save(DeviceDetails(
    id: device_id,
    clientId: client_id,
    platform: "ios",
    formFactor: "phone",
    push: DevicePushDetails(
      recipient: { "transportType": "apns", "deviceToken": "token-" + i }
    )
  ))
```

### Test Steps
```pseudo
result = AWAIT client.push.admin.deviceRegistrations.list({
  "clientId": client_id,
  "limit": "2"
})
```

### Assertions
```pseudo
ASSERT result.items.length <= 2
ASSERT result.hasNext == true
```

### Cleanup
```pseudo
FOR device_id IN device_ids:
  AWAIT client.push.admin.deviceRegistrations.remove(device_id)
```

---

## RSH1b4 — remove deletes device registration

**Spec requirement:** RSH1b4 — `#remove(deviceId)` deletes the registered device.

Tests that a registered device can be removed and is no longer retrievable.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
device_id = "test-device-remove-" + random_id()

# Register a device
AWAIT client.push.admin.deviceRegistrations.save(DeviceDetails(
  id: device_id,
  platform: "ios",
  formFactor: "phone",
  push: DevicePushDetails(
    recipient: { "transportType": "apns", "deviceToken": "test-token" }
  )
))
```

### Test Steps
```pseudo
# Remove the device
AWAIT client.push.admin.deviceRegistrations.remove(device_id)

# Verify it's gone
AWAIT client.push.admin.deviceRegistrations.get(device_id) FAILS WITH error
ASSERT error.statusCode == 404
```

---

## RSH1b4 — remove succeeds for nonexistent device

**Spec requirement:** RSH1b4 — Deleting a device that does not exist still succeeds.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
```

### Test Steps and Assertions
```pseudo
# Should not throw
AWAIT client.push.admin.deviceRegistrations.remove("nonexistent-device-" + random_id())
```

---

## RSH1b5 — removeWhere deletes devices by clientId

**Spec requirement:** RSH1b5 — `#removeWhere(params)` deletes registered devices matching params.

Tests that devices can be bulk-removed by `clientId`.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
client_id = "test-client-removeWhere-" + random_id()
device_ids = []

# Register two devices with the same clientId
FOR i IN [1, 2]:
  device_id = "test-device-rw-" + i + "-" + random_id()
  device_ids.append(device_id)
  AWAIT client.push.admin.deviceRegistrations.save(DeviceDetails(
    id: device_id,
    clientId: client_id,
    platform: "ios",
    formFactor: "phone",
    push: DevicePushDetails(
      recipient: { "transportType": "apns", "deviceToken": "token-" + i }
    )
  ))
```

### Test Steps
```pseudo
# Remove all devices for this clientId
AWAIT client.push.admin.deviceRegistrations.removeWhere({"clientId": client_id})

# Verify both are gone
result = AWAIT client.push.admin.deviceRegistrations.list({"clientId": client_id})
ASSERT result.items.length == 0
```

---

## RSH1c3, RSH1c1 — save and list channel subscriptions

| Spec | Requirement |
|------|-------------|
| RSH1c3 | `#save(subscription)` creates a channel subscription |
| RSH1c1 | `#list(params)` returns paginated subscriptions |

Tests the channel subscription lifecycle: save then list.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
device_id = "test-device-sub-" + random_id()
channel_name = "pushenabled:test-sub-" + random_id()

# Register a device first (required for deviceId subscriptions)
AWAIT client.push.admin.deviceRegistrations.save(DeviceDetails(
  id: device_id,
  platform: "ios",
  formFactor: "phone",
  push: DevicePushDetails(
    recipient: { "transportType": "apns", "deviceToken": "test-token" }
  )
))
```

### Test Steps
```pseudo
# Save a channel subscription
saved = AWAIT client.push.admin.channelSubscriptions.save(PushChannelSubscription(
  channel: channel_name,
  deviceId: device_id
))
```

### Assertions
```pseudo
ASSERT saved IS PushChannelSubscription
ASSERT saved.channel == channel_name
ASSERT saved.deviceId == device_id

# List subscriptions for this channel
result = AWAIT client.push.admin.channelSubscriptions.list({"channel": channel_name})
ASSERT result IS PaginatedResult
ASSERT result.items.length >= 1

found = false
FOR sub IN result.items:
  IF sub.deviceId == device_id:
    found = true
    ASSERT sub.channel == channel_name
ASSERT found == true
```

### Cleanup
```pseudo
AWAIT client.push.admin.channelSubscriptions.remove(PushChannelSubscription(
  channel: channel_name,
  deviceId: device_id
))
AWAIT client.push.admin.deviceRegistrations.remove(device_id)
```

---

## RSH1c3 — save channel subscription with clientId

**Spec requirement:** RSH1c3 — A test should exist for saving a `clientId`-based subscription.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
client_id = "test-client-sub-" + random_id()
channel_name = "pushenabled:test-clientsub-" + random_id()
```

### Test Steps
```pseudo
saved = AWAIT client.push.admin.channelSubscriptions.save(PushChannelSubscription(
  channel: channel_name,
  clientId: client_id
))
```

### Assertions
```pseudo
ASSERT saved.channel == channel_name
ASSERT saved.clientId == client_id
```

### Cleanup
```pseudo
AWAIT client.push.admin.channelSubscriptions.remove(PushChannelSubscription(
  channel: channel_name,
  clientId: client_id
))
```

---

## RSH1c2 — listChannels returns channel names with subscriptions

**Spec requirement:** RSH1c2 — `#listChannels(params)` returns a paginated result with `String` objects.

Tests that channels with active subscriptions appear in listChannels.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
client_id = "test-client-lc-" + random_id()
channel_name = "pushenabled:test-listchannels-" + random_id()

# Create a subscription to ensure the channel appears
AWAIT client.push.admin.channelSubscriptions.save(PushChannelSubscription(
  channel: channel_name,
  clientId: client_id
))
```

### Test Steps
```pseudo
result = AWAIT client.push.admin.channelSubscriptions.listChannels({})
```

### Assertions
```pseudo
ASSERT result IS PaginatedResult
# The channel we subscribed to should appear in the list
ASSERT channel_name IN result.items
```

### Cleanup
```pseudo
AWAIT client.push.admin.channelSubscriptions.remove(PushChannelSubscription(
  channel: channel_name,
  clientId: client_id
))
```

---

## RSH1c4 — remove deletes channel subscription

**Spec requirement:** RSH1c4 — `#remove(subscription)` deletes a channel subscription using subscription attributes as params.

Tests that a subscription can be removed and no longer appears in list results.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
client_id = "test-client-rm-" + random_id()
channel_name = "pushenabled:test-remove-" + random_id()

# Create a subscription
AWAIT client.push.admin.channelSubscriptions.save(PushChannelSubscription(
  channel: channel_name,
  clientId: client_id
))
```

### Test Steps
```pseudo
# Remove the subscription
AWAIT client.push.admin.channelSubscriptions.remove(PushChannelSubscription(
  channel: channel_name,
  clientId: client_id
))

# Verify it's gone
result = AWAIT client.push.admin.channelSubscriptions.list({
  "channel": channel_name,
  "clientId": client_id
})
ASSERT result.items.length == 0
```

---

## RSH1c4 — remove succeeds for nonexistent subscription

**Spec requirement:** RSH1c4 — Deleting a subscription that does not exist still succeeds.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
```

### Test Steps and Assertions
```pseudo
# Should not throw
AWAIT client.push.admin.channelSubscriptions.remove(PushChannelSubscription(
  channel: "pushenabled:nonexistent-" + random_id(),
  clientId: "nonexistent-client"
))
```

---

## RSH1c5 — removeWhere deletes subscriptions by clientId

**Spec requirement:** RSH1c5 — `#removeWhere(params)` deletes matching channel subscriptions.

Tests that subscriptions can be bulk-removed by `clientId`.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
client_id = "test-client-rwsub-" + random_id()
channel_names = []

# Create subscriptions on two channels for the same clientId
FOR i IN [1, 2]:
  ch = "pushenabled:test-rwsub-" + i + "-" + random_id()
  channel_names.append(ch)
  AWAIT client.push.admin.channelSubscriptions.save(PushChannelSubscription(
    channel: ch,
    clientId: client_id
  ))
```

### Test Steps
```pseudo
# Remove all subscriptions for this clientId
AWAIT client.push.admin.channelSubscriptions.removeWhere({"clientId": client_id})

# Verify they're all gone
result = AWAIT client.push.admin.channelSubscriptions.list({"clientId": client_id})
ASSERT result.items.length == 0
```
