# PushChannel Integration Tests

Spec points: `RSH7a`, `RSH7b`, `RSH7c`, `RSH7d`

## Test Type
Integration test against Ably sandbox

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox-rest.ably.io`.

### App Provisioning

Uses `ably-common/test-resources/test-app-setup.json` which provides:
- `keys[0]` — full access (default capability `{"*":["*"]}`)

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  full_access_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {full_access_key}
```

### Notes
- All clients use `useBinaryProtocol: false` (SDK does not implement msgpack)
- All clients use `endpoint: "sandbox"`
- These tests require the platform to support push notifications and the local device to be configurable for push registration. If the sandbox or platform does not support push device registration, these tests should be skipped.
- A device must be registered (via `push.admin.deviceRegistrations.save`) before device-based channel subscriptions can be created
- The `PushChannel` methods operate on behalf of the local device — the `LocalDevice` must be configured to simulate a registered push target device

---

## RSH7a, RSH7c — subscribeDevice and unsubscribeDevice round-trip

| Spec | Requirement |
|------|-------------|
| RSH7a | subscribeDevice() subscribes the local device to push on a channel |
| RSH7a2 | Performs a POST to /push/channelSubscriptions with device id and channel name |
| RSH7c | unsubscribeDevice() unsubscribes the local device from push on a channel |
| RSH7c2 | Performs a DELETE to /push/channelSubscriptions with device id and channel name |

Tests the full device subscription lifecycle: register a device, subscribe it to a channel via `PushChannel.subscribeDevice()`, verify the subscription exists, then unsubscribe via `PushChannel.unsubscribeDevice()` and verify it is removed.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

device_id = "test-device-pushchan-" + random_id()
channel_name = "pushenabled:test-rsh7a-" + random_id()
device_token = "test-apns-token-" + random_id()

# Register a device via admin API (required before device subscriptions work)
AWAIT client.push.admin.deviceRegistrations.save(DeviceDetails(
  id: device_id,
  platform: "ios",
  formFactor: "phone",
  push: DevicePushDetails(
    recipient: { "transportType": "apns", "deviceToken": device_token }
  )
))

# Configure the local device to match the registered device
# The deviceIdentityToken is obtained from the registration response
# For integration testing, we use the admin API to register and then
# configure the LocalDevice with values that allow push device auth
client.device = LocalDevice(
  id: device_id,
  deviceIdentityToken: "test-device-identity-token",
  clientId: null
)

channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Subscribe the device to push on this channel
AWAIT channel.push.subscribeDevice()

# Verify subscription exists via admin API
result = AWAIT client.push.admin.channelSubscriptions.list({
  "channel": channel_name,
  "deviceId": device_id
})
ASSERT result.items.length >= 1

found = false
FOR sub IN result.items:
  IF sub.deviceId == device_id AND sub.channel == channel_name:
    found = true
ASSERT found == true

# Unsubscribe the device
AWAIT channel.push.unsubscribeDevice()

# Verify subscription is removed
result_after = AWAIT client.push.admin.channelSubscriptions.list({
  "channel": channel_name,
  "deviceId": device_id
})
ASSERT result_after.items.length == 0
```

### Cleanup
```pseudo
AWAIT client.push.admin.deviceRegistrations.remove(device_id)
```

---

## RSH7b, RSH7d — subscribeClient and unsubscribeClient round-trip

| Spec | Requirement |
|------|-------------|
| RSH7b | subscribeClient() subscribes the local device's clientId to push on a channel |
| RSH7b2 | Performs a POST to /push/channelSubscriptions with device clientId and channel name |
| RSH7d | unsubscribeClient() unsubscribes the local device's clientId from push on a channel |
| RSH7d2 | Performs a DELETE to /push/channelSubscriptions with device clientId and channel name |

Tests the full client subscription lifecycle: configure a local device with a `clientId`, subscribe via `PushChannel.subscribeClient()`, verify the subscription exists, then unsubscribe via `PushChannel.unsubscribeClient()` and verify it is removed.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client_id = "test-client-pushchan-" + random_id()
channel_name = "pushenabled:test-rsh7b-" + random_id()

# Configure the local device with a clientId
# subscribeClient does not require device registration — it subscribes
# by clientId, not by deviceId
client.device = LocalDevice(
  id: "test-device-" + random_id(),
  deviceIdentityToken: "test-device-identity-token",
  clientId: client_id
)

channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Subscribe the client to push on this channel
AWAIT channel.push.subscribeClient()

# Verify subscription exists via admin API
result = AWAIT client.push.admin.channelSubscriptions.list({
  "channel": channel_name,
  "clientId": client_id
})
ASSERT result.items.length >= 1

found = false
FOR sub IN result.items:
  IF sub.clientId == client_id AND sub.channel == channel_name:
    found = true
ASSERT found == true

# Unsubscribe the client
AWAIT channel.push.unsubscribeClient()

# Verify subscription is removed
result_after = AWAIT client.push.admin.channelSubscriptions.list({
  "channel": channel_name,
  "clientId": client_id
})
ASSERT result_after.items.length == 0
```
