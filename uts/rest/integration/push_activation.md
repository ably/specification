# Push Activation Integration Tests

Spec points: `RSH1a`, `RSH2a`, `RSH2b`, `RSH2f`, `RSH3a2a3`, `RSH3a2c`, `RSH3b3c`, `RSH6a`, `RSH8a`, `RSH8c`

## Test Type
Integration test against Ably sandbox

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox.realtime.ably-nonprod.net`.

### App Provisioning

Uses `ably-common/test-resources/test-app-setup.json` which provides:
- `keys[0]` — full access (default capability `{"*":["*"]}`)
- `keys[1]` — includes `pushenabled:*` with `push-subscribe` capability (and `pushenabled:admin:*` with `push-admin`)

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox.realtime.ably-nonprod.net/apps
    WITH body from ably-common/test-resources/test-app-setup.json
    WITH timeout 30s

  app_config = parse_json(response.body)
  full_access_key = app_config.keys[0].key_str
  push_subscribe_key = app_config.keys[1].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  # Best-effort: catch and ignore timeout errors, sandbox apps auto-expire
  DELETE https://sandbox.realtime.ably-nonprod.net/apps/{app_id}
    WITH Authorization: Basic {full_access_key}
    WITH timeout 30s
```

## Notes

### Design: the `ablyChannel` test recipient

The portable `requestToken` primitive (see `uts/rest/unit/helpers/mock_push_platform.md`) can only produce `fcm`/`apns`/`web` tokens, none of which is usable against the sandbox without real platform credentials — the sandbox cannot deliver to a fabricated FCM/APNs token, so an activation driven by `requestToken` could never be verified end to end.

Instead, these tests use the sandbox's special test-only `ablyChannel` recipient (referenced by `RSH1a`; established by ably-js's `test/support/push_channel_transport.js`). The sandbox accepts device registrations whose `push.recipient` is:

```pseudo
{
  "transportType": "ablyChannel",
  "channel": <channel name>,
  "ablyKey": <api key>,
  "ablyUrl": <rest url>       # e.g. "https://sandbox.realtime.ably-nonprod.net"
}
```

and delivers push publishes to that recipient as messages named `__ably_push__` on the named channel, with the push payload JSON-encoded as a string in the message `data`.

Tests pre-seed `ably.push.pushRecipient` in `MockPushStorage` with such a recipient. Per `RSH3a2c`, on `CalledActivate` the machine finds the local device already has push details, sends `GotPushDeviceDetails` directly, and never calls `requestToken` — so the platform config's `requestToken` raises `FAIL("requestToken must not be called")`. The registration `POST /push/deviceRegistrations`, the identity-token grant, the `PATCH` sync, deregistration, and push delivery are all exercised against the real server.

### RSH8a tolerance caveat

`RSH8a` requires the `LocalDevice` attributes to be populated from persisted state "to the extent that they exist". Seeding only `ably.push.pushRecipient` — with no persisted `id`/`deviceSecret`/`deviceIdentityToken` — is therefore a legitimate partial state that implementations must tolerate: `id` and `deviceSecret` are generated per `RSH3a2b` (or eagerly per the `RSH8k2` note), and activation proceeds. If an SDK's corrupt-state discard (`RSH8a1`) is over-eager and throws away the seeded recipient because `id`/`deviceSecret` are absent, that is a bug these tests are intended to surface — `RSH8a1` applies only when loading `id` or `deviceSecret` *fails*, not when they were never persisted.

### RSH6a raw-token question — RESOLVED

`rest/integration/RSH8c/identity-token-usable-0` doubles as the server-acceptance check for the `RSH6a` `X-Ably-DeviceToken` header: `push_subscribe_key` has only `push-subscribe` capability on `pushenabled:*` channels, so the `subscribeDevice()` POST is authorized by valid device authentication, not by the key. Empirically verified (2026-08-07, both ably-dart and ably-js derived runs): the sandbox accepts the **raw** token value — the normative form per `RSH6a` — and also tolerates a base64-encoded value; garbage values are rejected (400, code 40005), proving the header is genuinely validated. SDKs that base64-encode (ably-java, ably-cocoa) therefore work but are non-conformant; `RSH6a` now says this explicitly.

### Known server issue: registration-update PATCH on `ablyChannel`-recipient devices (fixed, pending deploy)

A server bug made `PATCH /push/deviceRegistrations/:deviceId` fail with 400 (code 40000, `unknown transport type 'ablyChannel'`) for any device whose **stored** recipient was `ablyChannel`, regardless of the PATCH body and of key vs device auth (while `PUT`/`POST` accepted the recipient, and the identical PATCH against an `fcm`-recipient device succeeded). Root cause: the transport gate's `allowAblyChannel` flag was never carried onto loaded registrations, so the update path re-validated the stored recipient with the flag unset. Fixed by [ably/realtime#8591](https://github.com/ably/realtime/pull/8591). The two tests that exercise the registration sync against an `ablyChannel`-recipient device (`reactivation-validates-0`, `update-token-synced-0` — and `rest/proxy/RSH3e3d/sync-failure-recovery-0` in the proxy spec) are specified against the fixed behaviour; until the fix is deployed to the sandbox, derived tests should be skipped with a reason referencing that PR, then unskipped.

### Other notes

- All clients use `useBinaryProtocol: false` and `endpoint: "nonprod:sandbox"`. These are control-plane tests: JSON only, no Protocol Variants.
- Integration tests still use `MockPushStorage` and `install_push_platform` (see `uts/rest/unit/helpers/mock_push_platform.md`) — only the HTTP transport is real. Storage seeding, `dump()`, and the standard `ably.push.*` keys work exactly as in the unit specs.
- Only one push platform is installed at a time (a fresh `install_push_platform` replaces the previous one). Within a test, all push-activation clients are built over the *same* storage, so re-installing via `push_client(storage, ...)` is safe. The `admin_client()` performs only key-authenticated admin operations and does not drive the activation machine.
- Recipient channel names and device registrations are unique per run; device registrations created during tests must be cleaned up.
- Suite timeout: 120 seconds. All `WITH timeout`, `poll_until` and `poll_until_success` values below are wall-clock time.
- `rest/integration/RSH2f/update-token-synced-0` is a **validation-risk test**: see its own notes.

## Shared Test Setup

```pseudo
# Storage pre-seeded with an ablyChannel recipient (see Notes). No id/secret/
# identity token — this is a first-ever activation with known push details.
FUNCTION seeded_storage(recipient_channel: String):
  storage = MockPushStorage()
  storage.seed({
    "ably.push.pushRecipient": json_encode({
      "transportType": "ablyChannel",
      "channel": recipient_channel,
      "ablyKey": full_access_key,
      "ablyUrl": "https://sandbox.realtime.ably-nonprod.net"
    })
  })
  RETURN storage

# Per RSH3a2c the seeded recipient means requestToken is never consulted.
FUNCTION push_client(storage, key?: String, platform?: String):
  install_push_platform(MockPushPlatform(
    platform: platform ?? "android",
    formFactor: "phone",
    storage: storage,
    requestToken: () => FAIL("requestToken must not be called: recipient is pre-seeded (RSH3a2c)")
  ))
  RETURN Rest(options: ClientOptions(
    key: key ?? full_access_key,
    endpoint: "nonprod:sandbox",
    useBinaryProtocol: false
  ))

# Separate client for server-side verification via the push admin API.
FUNCTION admin_client():
  RETURN Rest(options: ClientOptions(
    key: full_access_key,
    endpoint: "nonprod:sandbox",
    useBinaryProtocol: false
  ))
```

---

## RSH2a — activate registers the device with the real server

**Test ID**: `rest/integration/RSH2a/activate-registers-device-0`

| Spec | Requirement |
|------|-------------|
| RSH2a | `Push#activate` drives the state machine through a full registration |
| RSH3a2c | With push details already persisted, activation proceeds without calling `requestToken` |
| RSH3b3b | The `LocalDevice` is registered via `POST /push/deviceRegistrations` and the server accepts it |
| RSH8c | The granted `deviceIdentityToken` is set on the local device |

Tests the full happy-path activation round-trip against the real server: the seeded `ablyChannel` recipient is registered, the server grants a `deviceIdentityToken`, and the registration is visible through the admin API.

### Setup
```pseudo
recipient_channel = "push-recipient-RSH2a-" + random_id()
storage = seeded_storage(recipient_channel)
client = push_client(storage)
```

### Test Steps
```pseudo
AWAIT client.push.activate() WITH timeout 15s
```

### Assertions
```pseudo
device = client.device()
ASSERT device.id IS NOT null
ASSERT device.deviceIdentityToken IS NOT null

# Persistence settles fire-and-forget after activate resolves
poll_until_success(
  condition: () => storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails",
  interval: 100ms,
  timeout: 10s
)

# Server-side verification via a separate admin client
admin = admin_client()
registration = AWAIT admin.push.admin.deviceRegistrations.get(device.id) WITH timeout 10s
ASSERT registration.id == device.id
ASSERT registration.platform == "android"
ASSERT registration.formFactor == "phone"
ASSERT registration.push.recipient["transportType"] == "ablyChannel"
ASSERT registration.push.recipient["channel"] == recipient_channel
```

### Cleanup
```pseudo
AWAIT admin.push.admin.deviceRegistrations.remove(device.id)
```

---

## RSH8c, RSH6a — persisted deviceIdentityToken is usable by a fresh client

**Test ID**: `rest/integration/RSH8c/identity-token-usable-0`

| Spec | Requirement |
|------|-------------|
| RSH8c | The `deviceIdentityToken` granted at registration is persisted and recovered |
| RSH8a | A fresh client hydrates the `LocalDevice` from persisted state |
| RSH6a | Device-authenticated requests carry `X-Ably-DeviceToken`, and the server accepts it |

Tests that the registration's identity token round-trips through storage: a fresh client over the same storage performs a device-authenticated operation (`channel.push.subscribeDevice()`) without calling `activate()` and without re-registering. The fresh client uses `push_subscribe_key`, whose `push-subscribe` capability authorizes subscribing **only the authenticated device** — so the operation succeeds only if the server accepts the SDK's `X-Ably-DeviceToken` header. **Derived tests must report whether the server accepts the RAW token value** (see Notes: RSH6a raw-token open question).

### Setup
```pseudo
recipient_channel = "push-recipient-RSH8c-" + random_id()
storage = seeded_storage(recipient_channel)

# First app run: register the device
client1 = push_client(storage)
AWAIT client1.push.activate() WITH timeout 15s
device_id = client1.device().id
```

### Test Steps
```pseudo
# Second app run: fresh client over the same storage, restricted key.
# No activate() call — the LocalDevice must hydrate from storage (RSH8a).
client2 = push_client(storage, key: push_subscribe_key)
channel_name = "pushenabled:test-RSH8c-" + random_id()
channel = client2.channels.get(channel_name)

AWAIT channel.push.subscribeDevice() WITH timeout 15s
```

### Assertions
```pseudo
ASSERT client2.device().id == device_id
ASSERT client2.device().deviceIdentityToken IS NOT null

# Server-side verification: the subscription exists
admin = admin_client()
result = AWAIT admin.push.admin.channelSubscriptions.list({
  "channel": channel_name,
  "deviceId": device_id
}) WITH timeout 10s
ASSERT result.items.length == 1
ASSERT result.items[0].deviceId == device_id
ASSERT result.items[0].channel == channel_name
```

### Cleanup
```pseudo
AWAIT admin.push.admin.channelSubscriptions.remove(PushChannelSubscription(
  channel: channel_name,
  deviceId: device_id
))
AWAIT admin.push.admin.deviceRegistrations.remove(device_id)
```

---

## RSH2b — deactivate deregisters the device from the real server

**Test ID**: `rest/integration/RSH2b/deactivate-deregisters-0`

| Spec | Requirement |
|------|-------------|
| RSH2b | `Push#deactivate` drives the state machine through deregistration |
| RSH3g3a | The device is deregistered via `DELETE /push/deviceRegistrations` and the server accepts it |

Tests that after `deactivate()` resolves, the registration no longer exists server-side. A missing device is reported by the admin `get` as an error with `statusCode` 404 (as in `rest/integration/push_admin.md`).

### Setup
```pseudo
recipient_channel = "push-recipient-RSH2b-" + random_id()
storage = seeded_storage(recipient_channel)
client = push_client(storage)

AWAIT client.push.activate() WITH timeout 15s
device_id = client.device().id

# Confirm the registration exists before deactivating
admin = admin_client()
AWAIT admin.push.admin.deviceRegistrations.get(device_id) WITH timeout 10s
```

### Test Steps
```pseudo
AWAIT client.push.deactivate() WITH timeout 15s
```

### Assertions
```pseudo
AWAIT admin.push.admin.deviceRegistrations.get(device_id) FAILS WITH error
ASSERT error.statusCode == 404
```

---

## RSH3a2a3 — reactivation over registered state syncs against the real server

**Test ID**: `rest/integration/RSH3a2a3/reactivation-validates-0`

| Spec | Requirement |
|------|-------------|
| RSH3a2a3 | `activate()` over already-registered state performs the RSH3d3b registration sync (HTTP PATCH, or the permitted PUT legacy equivalent), which must be accepted by the server |
| RSH3a2a | The machine recovered into `WaitingForNewPushDeviceDetails` validates the existing registration rather than re-registering |

Tests that a second app run's `activate()` — which validates the persisted registration against the real server — resolves, and that the registration survives intact. Integration tests capture no requests: the assertions are purely behavioural (the operation resolves; the server-side registration is unchanged).

### Setup
```pseudo
recipient_channel = "push-recipient-RSH3a2a3-" + random_id()
storage = seeded_storage(recipient_channel)

# First app run: register the device
client1 = push_client(storage)
AWAIT client1.push.activate() WITH timeout 15s
device_id = client1.device().id
```

### Test Steps
```pseudo
# Second app run: fresh client over the same storage
client2 = push_client(storage)
AWAIT client2.push.activate() WITH timeout 15s
```

### Assertions
```pseudo
# The sync (PATCH /push/deviceRegistrations/:deviceId) was accepted:
# activate resolved and the same device is still registered server-side
ASSERT client2.device().id == device_id
ASSERT client2.device().deviceIdentityToken IS NOT null

admin = admin_client()
registration = AWAIT admin.push.admin.deviceRegistrations.get(device_id) WITH timeout 10s
ASSERT registration.id == device_id
ASSERT registration.push.recipient["transportType"] == "ablyChannel"
ASSERT registration.push.recipient["channel"] == recipient_channel
```

### Cleanup
```pseudo
AWAIT admin.push.admin.deviceRegistrations.remove(device_id)
```

---

## RSH1a — direct publish to the activated device is received end to end

**Test ID**: `rest/integration/RSH1a/direct-publish-received-0`

| Spec | Requirement |
|------|-------------|
| RSH1a | `push.admin.publish(recipient, data)` delivers a push notification to a registered device recipient |

The full end-to-end path: an activated device (with an `ablyChannel` recipient), an admin publish addressed to `{"deviceId": ...}`, and delivery verified by receiving the `__ably_push__` message on the recipient channel. The sandbox delivers the push payload JSON-encoded as a string in the message `data`.

### Setup
```pseudo
recipient_channel = "push-recipient-RSH1a-" + random_id()
storage = seeded_storage(recipient_channel)
client = push_client(storage)

AWAIT client.push.activate() WITH timeout 15s
device_id = client.device().id

# A realtime client subscribed to the recipient channel receives the push
realtime = Realtime(options: ClientOptions(
  key: full_access_key,
  endpoint: "nonprod:sandbox",
  useBinaryProtocol: false
))
rt_channel = realtime.channels.get(recipient_channel)
received = []
AWAIT rt_channel.subscribe("__ably_push__", (msg) => received.append(msg)) WITH timeout 10s
```

### Test Steps
```pseudo
push_payload = {
  "notification": { "title": "Integration Test", "body": "Push activation e2e" },
  "data": { "foo": "bar" }
}

admin = admin_client()
AWAIT admin.push.admin.publish(
  recipient: { "deviceId": device_id },
  data: push_payload
) WITH timeout 10s
```

### Assertions
```pseudo
poll_until(
  condition: FUNCTION() => RETURN received[0] IF received.length >= 1 ELSE null,
  interval: 100ms,
  timeout: 15s
)

msg = received[0]
ASSERT msg.name == "__ably_push__"
received_payload = parse_json(msg.data)
ASSERT received_payload["notification"]["title"] == "Integration Test"
ASSERT received_payload["notification"]["body"] == "Push activation e2e"
ASSERT received_payload["data"] == { "foo": "bar" }
```

### Cleanup
```pseudo
realtime.close()
AWAIT admin.push.admin.deviceRegistrations.remove(device_id)
```

---

## RSH3b3c — registration rejected by the server fails activation

**Test ID**: `rest/integration/RSH3b3c/registration-failure-invalid-platform-0`

| Spec | Requirement |
|------|-------------|
| RSH3b3c | A failed registration fires `GettingDeviceRegistrationFailed`, failing `activate()` with the server's error |
| RSH3b4a | The activated callback is called with the error and the machine returns to `NotActivated` |

Tests that a registration the real server rejects — here an invalid `platform` on the platform config — surfaces the server's error through `activate()`, and the machine settles back in `NotActivated`. (Mirrors ably-js `failed_registration`, which observes `code` 40000 / `statusCode` 400 from the sandbox; this spec asserts only a 4xx-range error to avoid over-constraining server behaviour.)

### Setup
```pseudo
recipient_channel = "push-recipient-RSH3b3c-" + random_id()
storage = seeded_storage(recipient_channel)
client = push_client(storage, platform: "not_a_real_platform")
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.activate() FAILS WITH error WITH timeout 15s
ASSERT error IS NOT null
ASSERT error.statusCode >= 400 AND error.statusCode < 500

# The machine settles back in NotActivated
poll_until_success(
  condition: () => storage.dump()["ably.push.activationState"] == "NotActivated",
  interval: 100ms,
  timeout: 10s
)

ASSERT client.device().deviceIdentityToken == null
```

---

## RSH2f — updateToken's fire-and-forget sync is accepted by the real server

**Test ID**: `rest/integration/RSH2f/update-token-synced-0`

| Spec | Requirement |
|------|-------------|
| RSH2f | `Push#updateToken(token)` delivers new push transport details to the library |
| RSH3d3b | The resulting registration sync (HTTP PATCH carrying the new `push.recipient`) is accepted by the server |

Tests that on an activated device, `updateToken` resolves and the fire-and-forget PATCH sync lands server-side: the admin API eventually shows the new `fcm` recipient. Note `RSH2f` is part of the pending token-variants spec extension (drafted in `specifications/features.md`, not yet merged upstream).

**Isolation notes:**
- This test intentionally **replaces** the device's `ablyChannel` recipient with an `fcm` one (the sandbox accepts fabricated FCM `registrationToken`s at both registration and update time, empirically confirmed 2026-08-07), after which the device can no longer receive `ablyChannel` deliveries. It therefore uses its own storage and device (every test here does), and if a derived suite ever shares a device between tests, this test must run last.
- Subject to the known server issue above until [ably/realtime#8591](https://github.com/ably/realtime/pull/8591) is deployed.

### Setup
```pseudo
recipient_channel = "push-recipient-RSH2f-" + random_id()
storage = seeded_storage(recipient_channel)
client = push_client(storage)

AWAIT client.push.activate() WITH timeout 15s
device_id = client.device().id
new_token = "fake-fcm-token-" + random_id()
```

### Test Steps
```pseudo
AWAIT client.push.updateToken(PushDeviceToken(
  transportType: "fcm",
  token: new_token
)) WITH timeout 15s
```

### Assertions
```pseudo
# The sync is fire-and-forget: poll the admin API until the PATCH lands
admin = admin_client()
registration = poll_until(
  condition: FUNCTION() =>
    reg = AWAIT admin.push.admin.deviceRegistrations.get(device_id)
    RETURN reg IF reg.push.recipient["transportType"] == "fcm" ELSE null,
  interval: 500ms,
  timeout: 20s
)

ASSERT registration.id == device_id
ASSERT registration.push.recipient["transportType"] == "fcm"
ASSERT registration.push.recipient["registrationToken"] == new_token
```

### Cleanup
```pseudo
AWAIT admin.push.admin.deviceRegistrations.remove(device_id)
```
