# Push Device Authentication Tests

Spec points: `RSH6`, `RSH6a`, `RSH6b`, `RSH1b3`, `RSH1b5`, `RSH1c3`, `RSH1c4`, `RSH3d2b`

## Test Type
Unit test with mocked HTTP client and mocked push platform

## Mock HTTP Infrastructure

See `uts/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

## Mock Push Platform Infrastructure

See `uts/rest/unit/helpers/mock_push_platform.md` for the portable push platform primitives (`PushKeyValueStorage`, `requestToken`, `PushPlatformConfig`), the standard `ably.push.*` storage keys, and the `MockPushStorage` mock.

## Notes

These tests cover **push device authentication** (`RSH6`) — how an activated (or partially activated) push target device authenticates itself for requests that operate on its own registration — and the clauses of the push admin API (`RSH1b`/`RSH1c`) that require it:

- `RSH6a` — *"If a device has completed activation and has a `deviceIdentityToken` then push device authentication is performed for a request by adding an `X-Ably-DeviceToken` request header whose value is the `deviceIdentityToken`."* The spec adds: this header *"has always been `X-Ably-DeviceToken`, but has previously been mistakenly documented as `X-Ably-DeviceIdentityToken` … It was never renamed."*
- `RSH6b` — *"If a device has not completed [activation] but has a `deviceSecret` then push device authentication is performed for a request by adding an `X-Ably-DeviceSecret` request header whose value is the `deviceSecret`."*

The `RSH1b3`/`RSH1b5`/`RSH1c3`/`RSH1c4` admin operations must include push device authentication **only** when the `deviceId` they reference is that of the present, activated client. For any other `deviceId` (or a `clientId`-based subscription) the request carries no device-auth header — admin operations are otherwise authorised solely by the client's normal token/key auth.

**Deviation caveats:**

- As in `push_activation_state_machine.md`: an SDK using a different device-auth mechanism (e.g. an `Authorization` bearer header carrying the base64-encoded `deviceIdentityToken`, as ably-js's activation plugin does) must record a deviation and adapt the header assertions.
- ably-js's common push admin implementation (`src/common/lib/client/push.ts`) currently does **not** implement the own-device auth clauses of `RSH1b3`/`RSH1b5`/`RSH1c3`/`RSH1c4` at all — its admin requests never carry device auth. These tests are written to the feature spec; ably-js derived tests may record a deviation for the `RSH6a` admin tests below.
- ably-js does not implement `RSH6b` (`X-Ably-DeviceSecret`) — its device-auth path requires a `deviceIdentityToken` and fails without one. Derived tests for the `RSH6b` test below may record a deviation.
- The `RSH6b` test drives activation through a custom `registerCallback` whose result confers no `deviceIdentityToken`. Some SDKs may not accept a registration result without an identity token; if the scenario is unreachable that way, the derived test may instead construct it by seeding storage with `ably.push.deviceId`, `ably.push.deviceSecret`, and `ably.push.activationState` = `"WaitingForNewPushDeviceDetails"` — and **no** `ably.push.deviceIdentityToken` — then deactivating.
- `PushChannelSubscription.forDevice`/`forClientId` are the IDL's factories (`PCS5`); an SDK without them may construct the subscription by an equivalent means.

## Shared Test Setup

All tests use the following helpers (adapted from `push_activation_state_machine.md`, with routes added for the admin `channelSubscriptions` endpoints), plus the `BEFORE EACH TEST` / `AFTER EACH TEST` isolation from `mock_push_platform.md`.

```pseudo
# HTTP mock routing registration and admin endpoints; captures every request.
# Individual tests override specific routes via the `overrides` handler,
# which is consulted first and may hold requests without responding.
FUNCTION mock_registration_server(overrides?: (req) => Boolean):
  captured_requests = []
  mock_http = MockHttpClient(
    onConnectionAttempt: (conn) => conn.respond_with_success(),
    onRequest: (req) => {
      captured_requests.append(req)
      IF overrides != null AND overrides(req):
        RETURN  # the override handled (or held) the request
      IF req.method == "POST" AND req.url.path == "/push/deviceRegistrations":
        body = parse_json(req.body)
        req.respond_with(201, merge(body, {"deviceIdentityToken": {"token": "ident-token-1"}}))
      ELSE IF req.method == "PUT" AND req.url.path STARTS WITH "/push/deviceRegistrations/":
        req.respond_with(200, parse_json(req.body))
      ELSE IF req.method == "PATCH" AND req.url.path STARTS WITH "/push/deviceRegistrations/":
        req.respond_with(200, parse_json(req.body))
      ELSE IF req.method == "DELETE" AND req.url.path == "/push/deviceRegistrations":
        req.respond_with(204, "")
      ELSE IF req.method == "POST" AND req.url.path == "/push/channelSubscriptions":
        req.respond_with(200, parse_json(req.body))
      ELSE IF req.method == "DELETE" AND req.url.path == "/push/channelSubscriptions":
        req.respond_with(204, "")
      ELSE:
        req.respond_with(500, {"error": {"message": "unexpected request", "code": 50000}})
    }
  )
  install_mock(mock_http)
  RETURN captured_requests

FUNCTION build_push_platform(storage, token?: PushDeviceToken, requestToken?: Function):
  RETURN MockPushPlatform(
    platform: "android",
    formFactor: "phone",
    storage: storage,
    requestToken: requestToken ?? (() => token ?? PushDeviceToken(transportType: "fcm", token: "fcm-token-1"))
  )

FUNCTION push_client(storage, clientId?: String, token?, requestToken?):
  install_push_platform(build_push_platform(storage, token, requestToken))
  RETURN Rest(options: ClientOptions(
    key: "appId.keyId:keySecret",
    clientId: clientId
  ))

# Runs a full activation so that `storage` holds a registered device
# (deviceId, deviceSecret, deviceIdentityToken, pushRecipient) and the
# persisted activation state is WaitingForNewPushDeviceDetails.
FUNCTION activate_into(storage, clientId?: String):
  client = push_client(storage, clientId)
  AWAIT client.push.activate()
  poll_until_success(() => storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
  RETURN client
```

---

## RSH6a, RSH1b3 — deviceRegistrations.save for the present activated device includes device auth

**Test ID**: `rest/unit/RSH6a/admin-device-registrations-save-own-device-0`

| Spec | Requirement |
|------|-------------|
| RSH6a | Device auth is performed *"by adding an `X-Ably-DeviceToken` request header whose value is the `deviceIdentityToken`"* |
| RSH1b3 | `#save(device)` issues a `PUT` request to `/push/deviceRegistrations/:deviceId` using the `DeviceDetails` object argument. *"If the client has been activated as a push target device, and the specified `deviceId` is that of the present client, then this request must include push device authentication"* |

Tests that after full activation, an admin `save()` whose `DeviceDetails.id` is the local device's id carries the `X-Ably-DeviceToken` header with the registered `deviceIdentityToken`.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
device_id = mock_storage.dump()["ably.push.deviceId"]
```

### Test Steps
```pseudo
device = DeviceDetails(
  id: device_id,
  platform: "android",
  formFactor: "phone",
  push: DevicePushDetails(
    recipient: {"transportType": "fcm", "registrationToken": "fcm-token-1"}
  )
)

AWAIT client.push.admin.deviceRegistrations.save(device)
```

### Assertions
```pseudo
# The seeding activation POST, then the admin save PUT
ASSERT captured_requests.length == 2

request = captured_requests[1]
ASSERT request.method == "PUT"
ASSERT request.url.path == "/push/deviceRegistrations/" + encode_uri_component(device_id)

# RSH1b3 + RSH6a — the deviceId is that of the present activated client,
# so the request must include push device authentication
ASSERT request.headers["X-Ably-DeviceToken"] == "ident-token-1"
```

---

## RSH6a, RSH1b3 — deviceRegistrations.save for a different device carries no device auth

**Test ID**: `rest/unit/RSH6a/admin-save-other-device-no-device-auth-1`

**Spec requirement:** RSH1b3 — device auth is required only *"if the client has been activated as a push target device, and the specified `deviceId` is that of the present client"*. For any other `deviceId`, the request must **not** include push device authentication.

Tests that the same activated client saving a `DeviceDetails` for a *different* `deviceId` sends no device-auth header.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
```

### Test Steps
```pseudo
device = DeviceDetails(
  id: "other-device-1",
  platform: "ios",
  formFactor: "tablet",
  push: DevicePushDetails(
    recipient: {"transportType": "apns", "deviceToken": "apns-token-1"}
  )
)

AWAIT client.push.admin.deviceRegistrations.save(device)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 2

request = captured_requests[1]
ASSERT request.method == "PUT"
ASSERT request.url.path == "/push/deviceRegistrations/" + encode_uri_component("other-device-1")

# The deviceId is not that of the present client — no device auth
ASSERT "X-Ably-DeviceToken" NOT IN request.headers
ASSERT "X-Ably-DeviceSecret" NOT IN request.headers
```

---

## RSH6a, RSH1c3, RSH1c4 — channelSubscriptions save/remove for the present device include device auth

**Test ID**: `rest/unit/RSH6a/admin-channel-subscriptions-save-own-device-2`

| Spec | Requirement |
|------|-------------|
| RSH1c3 | `#save(pushChannelSubscription)` issues a `POST` request to `/push/channelSubscriptions`. *"If the client has been activated as a push target device, and the specified `PushChannelSubscription` contains a `deviceId` matching that of the present client, then this request must include push device authentication"* |
| RSH1c4 | `#remove(push_channel_subscription)` issues a `DELETE` request to `/push/channelSubscriptions` using the attributes as params. *"If the client has been activated as a push target device, and the specified `PushChannelSubscription` contains a `deviceId` matching that of the present client, then this request must include push device authentication"* |
| RSH6a | Device auth is the `X-Ably-DeviceToken` header carrying the `deviceIdentityToken` |

Tests that an activated client saving, and then removing, a channel subscription for its own `deviceId` includes the `X-Ably-DeviceToken` header on both requests.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
device_id = mock_storage.dump()["ably.push.deviceId"]
```

### Test Steps
```pseudo
subscription = PushChannelSubscription.forDevice("push-test-channel", device_id)

AWAIT client.push.admin.channelSubscriptions.save(subscription)    # RSH1c3
AWAIT client.push.admin.channelSubscriptions.remove(subscription)  # RSH1c4
```

### Assertions
```pseudo
# Seeding POST, then the subscription POST, then the subscription DELETE
ASSERT captured_requests.length == 3

# RSH1c3 — the save POST includes device auth
save_request = captured_requests[1]
ASSERT save_request.method == "POST"
ASSERT save_request.url.path == "/push/channelSubscriptions"
body = parse_json(save_request.body)
ASSERT body["channel"] == "push-test-channel"
ASSERT body["deviceId"] == device_id
ASSERT save_request.headers["X-Ably-DeviceToken"] == "ident-token-1"

# RSH1c4 — the remove DELETE includes device auth
remove_request = captured_requests[2]
ASSERT remove_request.method == "DELETE"
ASSERT remove_request.url.path == "/push/channelSubscriptions"
ASSERT remove_request.url.queryParams["channel"] == "push-test-channel"
ASSERT remove_request.url.queryParams["deviceId"] == device_id
ASSERT remove_request.headers["X-Ably-DeviceToken"] == "ident-token-1"
```

---

## RSH6a, RSH1b5 — deviceRegistrations.removeWhere for the present device includes device auth

**Test ID**: `rest/unit/RSH6a/admin-remove-where-own-device-3`

| Spec | Requirement |
|------|-------------|
| RSH1b5 | `#removeWhere(params)` issues a `DELETE` request to `/push/deviceRegistrations` and deletes the registered devices matching the provided `params`. *"If the client has been activated as a push target device, and the specified `deviceId` is that of the present client, then this request must include push device authentication"* |
| RSH6a | Device auth is the `X-Ably-DeviceToken` header carrying the `deviceIdentityToken` |

Tests that an activated client issuing `removeWhere(deviceId: <own id>)` includes the `X-Ably-DeviceToken` header on the DELETE.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
device_id = mock_storage.dump()["ably.push.deviceId"]
```

### Test Steps
```pseudo
AWAIT client.push.admin.deviceRegistrations.removeWhere({"deviceId": device_id})
```

### Assertions
```pseudo
ASSERT captured_requests.length == 2

request = captured_requests[1]
ASSERT request.method == "DELETE"
ASSERT request.url.path == "/push/deviceRegistrations"
ASSERT request.url.queryParams["deviceId"] == device_id

# RSH1b5 + RSH6a — the deviceId param is that of the present activated client
ASSERT request.headers["X-Ably-DeviceToken"] == "ident-token-1"
```

---

## RSH6b — a device with a deviceSecret but no deviceIdentityToken authenticates with X-Ably-DeviceSecret

**Test ID**: `rest/unit/RSH6b/device-secret-auth-before-identity-token-0`

| Spec | Requirement |
|------|-------------|
| RSH6b | *"If a device has not completed [activation] but has a `deviceSecret` then push device authentication is performed for a request by adding an `X-Ably-DeviceSecret` request header whose value is the `deviceSecret`"* |
| RSH3d2b | The deregistration DELETE is made *"using the device's ID, with push device authentication"* |

Tests the `deviceSecret` form of device auth: the device is activated through a custom `registerCallback` whose result confers **no** `deviceIdentityToken` (registration "succeeds" but the device never completes the identity-token half of activation). The subsequent `deactivate()` DELETE must then carry `X-Ably-DeviceSecret` — matching the persisted `ably.push.deviceSecret` — and **not** `X-Ably-DeviceToken`.

See the Notes for the storage-seeding fallback if a derived SDK cannot reach this state via `registerCallback`, and the ably-js deviation caveat (ably-js does not implement `RSH6b`).

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = push_client(mock_storage)

FUNCTION register_callback(device):
  RETURN {}  # registration succeeds but confers no deviceIdentityToken
```

### Test Steps
```pseudo
AWAIT client.push.activate(registerCallback: register_callback)
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")

device_id = mock_storage.dump()["ably.push.deviceId"]
device_secret = mock_storage.dump()["ably.push.deviceSecret"]

AWAIT client.push.deactivate()
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")
```

### Assertions
```pseudo
# Registration went through the callback, so the only HTTP request is the DELETE
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "DELETE"
ASSERT request.url.path == "/push/deviceRegistrations"
ASSERT request.url.queryParams["deviceId"] == device_id

# RSH6b — deviceSecret auth, since the device has no deviceIdentityToken
ASSERT request.headers["X-Ably-DeviceSecret"] == device_secret
ASSERT "X-Ably-DeviceToken" NOT IN request.headers
```
