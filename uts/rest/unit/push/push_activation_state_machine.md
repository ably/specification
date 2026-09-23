# Push Activation State Machine Tests

Spec points: `RSH2a`, `RSH2b`, `RSH3a1c`, `RSH3a1d`, `RSH3a2a`, `RSH3a2a1`, `RSH3a2a2`, `RSH3a2a3`, `RSH3a2a4`, `RSH3a2b`, `RSH3a2c`, `RSH3a2d`, `RSH3a2e`, `RSH3a3a`, `RSH3b1a`, `RSH3b2a`, `RSH3b2b`, `RSH3b3a`, `RSH3b3b`, `RSH3b3c`, `RSH3b3d`, `RSH3b4a`, `RSH3b4b`, `RSH3c1a`, `RSH3c2a`, `RSH3c2b`, `RSH3c2c`, `RSH3c3a`, `RSH3c3b`, `RSH3d1a`, `RSH3d1b`, `RSH3d2a`, `RSH3d2b`, `RSH3d2c`, `RSH3d2c1`, `RSH3d2d`, `RSH3e1a`, `RSH3e1b`, `RSH3e2a`, `RSH3e2b`, `RSH3e3b`, `RSH3e3c`, `RSH3f1a`, `RSH3f2a`, `RSH3g1a`, `RSH3g2a`, `RSH3g2b`, `RSH3g2c`, `RSH3g3a`, `RSH3g3b`, `RSH6a`, `RSH8h`

## Test Type
Unit test with mocked HTTP client and mocked push platform

## Mock HTTP Infrastructure

See `uts/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

## Mock Push Platform Infrastructure

See `uts/rest/unit/helpers/mock_push_platform.md` for the portable push platform primitives (`PushKeyValueStorage`, `requestToken`, `PushPlatformConfig`), the standard `ably.push.*` storage keys, and the `MockPushStorage` mock.

## Notes

The Activation State Machine (`RSH3`) has seven states:

`NotActivated` (initial), `WaitingForPushDeviceDetails`, `WaitingForDeviceRegistration`, `WaitingForNewPushDeviceDetails`, `WaitingForRegistrationSync`, `AfterRegistrationSyncFailed`, `WaitingForDeregistration`

and ten events:

`CalledActivate`, `CalledDeactivate`, `GotPushDeviceDetails`, `GettingPushDeviceDetailsFailed`, `GotDeviceRegistration`, `GettingDeviceRegistrationFailed`, `RegistrationSynced`, `SyncRegistrationFailed`, `Deregistered`, `DeregistrationFailed`.

These tests are **black-box**: they never construct events or inspect machine state directly. Events are produced by driving the public API (`push.activate()`, `push.deactivate()` — `RSH2a`/`RSH2b`), by the mocked `requestToken` (producing `GotPushDeviceDetails` / `GettingPushDeviceDetailsFailed` per `RSH8h`), and by responding to the mocked HTTP requests the machine issues. State is observed through behaviour (which requests are made, which operations resolve or fail) and, after operations settle, through the persisted `ably.push.activationState`.

To pin the machine in an intermediate state, tests hold a `PendingRequest` (capture it in the `onRequest` handler without responding) or a pending `requestToken` (a `Deferred`), and release it later. A `Deferred<T>` is a harness construct: a future the test completes manually with `deferred.complete(value)` or `deferred.fail(error)`; `deferred.future` is the awaitable side.

Device authentication assertions follow `RSH6a` (`X-Ably-DeviceToken` header). An SDK using a different device-auth mechanism (e.g. an `Authorization` bearer header carrying the `deviceIdentityToken`) must record a deviation and adapt the assertion.

Tests must not assert *when* `id`/`deviceSecret` are generated (see "Notes for Spec Authors" in `mock_push_platform.md`): some SDKs generate them eagerly on device load, others lazily per `RSH3a2b`.

## Shared Test Setup

All tests use the following helpers, plus the `BEFORE EACH TEST` / `AFTER EACH TEST` isolation from `mock_push_platform.md`.

```pseudo
# HTTP mock routing registration endpoints; captures every request.
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

## RSH2a, RSH3a2, RSH3b3, RSH3c2 — activate performs the full registration flow

**Test ID**: `rest/unit/RSH2a/activate-full-flow-0`

| Spec | Requirement |
|------|-------------|
| RSH2a | `Push#activate` sends a `CalledActivate` event to the state machine |
| RSH3a2b | `id` and `deviceSecret` are generated locally |
| RSH3a2d | The device requests push details from the underlying platform |
| RSH3a2e | Transitions to `WaitingForPushDeviceDetails` |
| RSH3b3b | On `GotPushDeviceDetails`, POSTs the `LocalDevice` with push details and `deviceSecret` to `/push/deviceRegistrations` |
| RSH3b3d | Transitions to `WaitingForDeviceRegistration` |
| RSH3c2a | On `GotDeviceRegistration`, updates the local `DeviceDetails` |
| RSH3c2b | Makes `Push#activate` return with no error |
| RSH3c2c | Transitions to `WaitingForNewPushDeviceDetails` |

Tests the complete happy-path activation of a previously unactivated device: token acquisition, direct-HTTP registration, and the resulting persisted state.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = push_client(mock_storage)
```

### Test Steps
```pseudo
AWAIT client.push.activate()
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.url.path == "/push/deviceRegistrations"

body = parse_json(request.body)
# RSH3b3b — the LocalDevice with push details and deviceSecret
ASSERT body["id"] IS NOT null
ASSERT body["deviceSecret"] IS NOT null
ASSERT body["platform"] == "android"
ASSERT body["formFactor"] == "phone"
ASSERT body["push"]["recipient"] == {
  "transportType": "fcm",
  "registrationToken": "fcm-token-1"
}

# RSH3c2a + RSH8c — the registration response was applied and persisted
persisted = mock_storage.dump()
ASSERT persisted["ably.push.deviceId"] == body["id"]
ASSERT persisted["ably.push.deviceSecret"] IS NOT null
ASSERT parse_json(persisted["ably.push.deviceIdentityToken"]) == "ident-token-1"
ASSERT parse_json(persisted["ably.push.pushRecipient"]) == {
  "transportType": "fcm",
  "registrationToken": "fcm-token-1"
}
```

---

## RSH3a2b — generated device identifiers are unique and the secret has sufficient entropy

**Test ID**: `rest/unit/RSH3a2b/device-id-secret-generation-0`

**Spec requirement:** RSH3a2b — `id` must be a unique identifier; `deviceSecret` must be a base64-encoded digest of at least 32 bytes derived from secure random data.

Tests the properties of the generated identifiers, without asserting *when* they are generated (see Notes).

### Setup
```pseudo
captured_requests = mock_registration_server()
storage_a = MockPushStorage()
storage_b = MockPushStorage()
```

### Test Steps
```pseudo
AWAIT push_client(storage_a).push.activate()
AWAIT push_client(storage_b).push.activate()
poll_until_success(() => storage_a.dump()["ably.push.deviceId"] != null)
poll_until_success(() => storage_b.dump()["ably.push.deviceId"] != null)
```

### Assertions
```pseudo
a = storage_a.dump()
b = storage_b.dump()

# Unique per device
ASSERT a["ably.push.deviceId"] != b["ably.push.deviceId"]
ASSERT a["ably.push.deviceSecret"] != b["ably.push.deviceSecret"]

# The secret is base64 and decodes to at least 32 bytes
decoded = base64_decode(a["ably.push.deviceSecret"])
ASSERT decoded.length >= 32
```

---

## RSH3b3a, RSH8c — activate with a custom registerCallback routes registration through the callback

**Test ID**: `rest/unit/RSH3b3a/activate-register-callback-0`

| Spec | Requirement |
|------|-------------|
| RSH3b3a | If a custom `registerCallback` was provided to `Push#activate`, pass it the local `DeviceDetails` updated with the push details |
| RSH3b3c | When the registration is done, a `GotDeviceRegistration` or `GettingDeviceRegistrationFailed` event should be fired |
| RSH8c | Following successful registration, the now known `deviceIdentityToken` is set and persisted |

Tests that a custom registrar replaces the direct HTTP registration entirely, and that the identity token it returns is persisted.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = push_client(mock_storage)

registered_devices = []
FUNCTION register_callback(device):
  registered_devices.append(device)
  RETURN {"deviceIdentityToken": {"token": "custom-ident-1"}}
```

### Test Steps
```pseudo
AWAIT client.push.activate(registerCallback: register_callback)
poll_until_success(() => mock_storage.dump()["ably.push.deviceIdentityToken"] != null)
```

### Assertions
```pseudo
# Registration went through the callback, not HTTP
ASSERT captured_requests.length == 0
ASSERT registered_devices.length == 1
ASSERT registered_devices[0].push.recipient == {
  "transportType": "fcm",
  "registrationToken": "fcm-token-1"
}

# RSH8c — the callback's identity token was persisted
ASSERT parse_json(mock_storage.dump()["ably.push.deviceIdentityToken"]) == "custom-ident-1"
```

---

## RSH3c3 — failed registration fails activate and returns to NotActivated

**Test ID**: `rest/unit/RSH3c3a/registration-failure-0`

| Spec | Requirement |
|------|-------------|
| RSH3c3a | On `GettingDeviceRegistrationFailed`, makes `Push#activate` return with the error |
| RSH3c3b | Transitions to `NotActivated` |

Tests that a server rejection of the registration POST propagates to `activate()`, that the machine returns to `NotActivated`, and that a subsequent `activate()` retries the registration.

### Setup
```pseudo
fail_registration = true
captured_requests = mock_registration_server(overrides: (req) => {
  IF req.method == "POST" AND req.url.path == "/push/deviceRegistrations" AND fail_registration:
    req.respond_with(400, {"error": {"message": "registration rejected", "code": 40198, "statusCode": 400}})
    RETURN true
  RETURN false
})
mock_storage = MockPushStorage()
client = push_client(mock_storage)
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.activate() FAILS WITH error
ASSERT error.code == 40198
ASSERT captured_requests.length == 1
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")

# RSH3c3b — from NotActivated, activation can be retried successfully
fail_registration = false
AWAIT client.push.activate()
ASSERT captured_requests.length == 2
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

---

## RSH3b4, RSH8h — failed token acquisition fails activate and returns to NotActivated

**Test ID**: `rest/unit/RSH3b4a/token-failure-0`

| Spec | Requirement |
|------|-------------|
| RSH8h | If an attempt to obtain the push transport details fails, a `GettingPushDeviceDetailsFailed` event containing the error is sent to the state machine |
| RSH3b4a | Makes `Push#activate` return with the error |
| RSH3b4b | Transitions to `NotActivated` |

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = push_client(mock_storage, requestToken: () => RAISE Error("permission denied"))
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.activate() FAILS WITH error
ASSERT error.message CONTAINS "permission denied"

# No registration was attempted
ASSERT captured_requests.length == 0
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")
```

---

## RSH3a2a, RSH3a2a3, RSH3e2 — activate on an already-registered device syncs the registration via PATCH

**Test ID**: `rest/unit/RSH3a2a3/activate-existing-registration-sync-0`

| Spec | Requirement |
|------|-------------|
| RSH3a2a | If the local device has `deviceIdentityToken`, performs a validation of the local `DeviceDetails` |
| RSH3a2a3 | Performs the RSH3d3b registration sync: an HTTP PATCH to `/push/deviceRegistrations/:deviceId` carrying the complete `push.recipient` |
| RSH3a2a4 | Transitions to `WaitingForRegistrationSync` |
| RSH3e2b | On `RegistrationSynced` (entered via `CalledActivate`), makes `Push#activate` return with no error |
| RSH3e2a | Transitions to `WaitingForNewPushDeviceDetails` |

Tests that a fresh client over storage holding a registered device does not re-register (no POST); it validates the existing registration by syncing it to the device-specific path. (Per RSH3a2a3, an SDK may equivalently perform the sync as a legacy PUT with the full local `DeviceDetails` as body — such SDKs adapt the method/body assertions accordingly, without recording a deviation.)

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
AWAIT activate_into(mock_storage)
device_id = mock_storage.dump()["ably.push.deviceId"]
```

### Test Steps
```pseudo
# A fresh client over the same storage simulates an app restart
client = push_client(mock_storage)
AWAIT client.push.activate()
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

### Assertions
```pseudo
# One POST from the seeding activation, then exactly one sync PATCH — no second POST
ASSERT captured_requests.length == 2
request = captured_requests[1]
ASSERT request.method == "PATCH"
ASSERT request.url.path == "/push/deviceRegistrations/" + encode_uri_component(device_id)

# RSH3d3b — changed fields only, with the complete recipient
body = parse_json(request.body)
ASSERT body["push"]["recipient"] == {
  "transportType": "fcm",
  "registrationToken": "fcm-token-1"
}
```

---

## RSH3a2a2 — activate on an already-registered device with a custom registerCallback

**Test ID**: `rest/unit/RSH3a2a2/activate-existing-registration-register-callback-0`

**Spec requirement:** RSH3a2a2 — If a custom `registerCallback` was provided to `Push#activate`, pass it the local `DeviceDetails` (instead of the RSH3a2a3 PATCH sync).

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
AWAIT activate_into(mock_storage)
device_id = mock_storage.dump()["ably.push.deviceId"]

registered_devices = []
FUNCTION register_callback(device):
  registered_devices.append(device)
  RETURN {"deviceIdentityToken": {"token": "ident-token-1"}}
```

### Test Steps and Assertions
```pseudo
client = push_client(mock_storage)
AWAIT client.push.activate(registerCallback: register_callback)

# The validation went through the callback: no requests beyond the seeding POST
ASSERT captured_requests.length == 1
ASSERT registered_devices.length == 1
ASSERT registered_devices[0].id == device_id
```

---

## RSH3a2a1 — activate fails with 61002 when the client identity conflicts with the registered device

**Test ID**: `rest/unit/RSH3a2a1/activate-clientid-mismatch-0`

**Spec requirement:** RSH3a2a1 — If the `LocalDevice` has a non-empty `clientId`, and the present identified client has a different (non-null) `clientId`, a `SyncRegistrationFailed` event should be fired containing an error with code 61002.

Tests that a device registered by an identified client cannot be re-activated by a client identified differently: `activate()` fails with 61002, no validation request is made, and the machine ends in `AfterRegistrationSyncFailed` (`RSH3e3b`).

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
AWAIT activate_into(mock_storage, clientId: "alice")
```

### Test Steps and Assertions
```pseudo
client = push_client(mock_storage, clientId: "bob")
AWAIT client.push.activate() FAILS WITH error
ASSERT error.code == 61002

# No validation request was made — only the seeding POST
ASSERT captured_requests.length == 1
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "AfterRegistrationSyncFailed")
```

---

## RSH3d1 — activate when already registered in the same session resolves without any request

**Test ID**: `rest/unit/RSH3d1a/activate-when-registered-resolves-0`

| Spec | Requirement |
|------|-------------|
| RSH3d1a | In `WaitingForNewPushDeviceDetails`, on `CalledActivate`, makes `Push#activate` return with no error |
| RSH3d1b | Transitions to `WaitingForNewPushDeviceDetails` (self) |

Contrast with `RSH3a2a3`: the *same* client instance whose machine is already in `WaitingForNewPushDeviceDetails` resolves a second `activate()` immediately; only a *fresh* machine starting from persisted state re-syncs via PATCH.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.activate()

# No additional request beyond the original registration POST
ASSERT captured_requests.length == 1
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

---

## RSH3b1a — repeated activate while waiting for push device details is idempotent

**Test ID**: `rest/unit/RSH3b1a/activate-while-waiting-push-details-0`

**Spec requirement:** RSH3b1a — In `WaitingForPushDeviceDetails`, on `CalledActivate`, transitions to `WaitingForPushDeviceDetails` (self).

Tests that calling `activate()` again while token acquisition is in flight does not request a second token or issue a second registration; both calls resolve when registration completes (`RSH3c2b`).

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()

token_deferred = Deferred<PushDeviceToken>()
token_requests = 0
client = push_client(mock_storage, requestToken: () => {
  token_requests += 1
  RETURN token_deferred.future
})
```

### Test Steps
```pseudo
first = client.push.activate()   # pends on requestToken
second = client.push.activate()  # RSH3b1a — self-transition

token_deferred.complete(PushDeviceToken(transportType: "fcm", token: "fcm-token-1"))

AWAIT first
AWAIT second
```

### Assertions
```pseudo
ASSERT token_requests == 1
ASSERT captured_requests.length == 1
ASSERT captured_requests[0].method == "POST"
```

---

## RSH3b2 — deactivate while waiting for push device details returns to NotActivated

**Test ID**: `rest/unit/RSH3b2a/deactivate-while-waiting-push-details-0`

| Spec | Requirement |
|------|-------------|
| RSH3b2a | Makes `Push#deactivate` return with no error |
| RSH3b2b | Transitions to `NotActivated` |
| RSH3a3a | In `NotActivated`, `GotPushDeviceDetails` is consumed with a self-transition |

Tests that deactivating while token acquisition is in flight succeeds immediately without any HTTP request, and that the token arriving afterwards (`GotPushDeviceDetails` in `NotActivated`) does **not** trigger a registration.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()

token_deferred = Deferred<PushDeviceToken>()
client = push_client(mock_storage, requestToken: () => token_deferred.future)
```

### Test Steps
```pseudo
activation = client.push.activate()  # pends on requestToken

AWAIT client.push.deactivate()       # RSH3b2a — resolves with no error
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")

# The token arrives late: RSH3a3a — consumed in NotActivated, no registration
token_deferred.complete(PushDeviceToken(transportType: "fcm", token: "fcm-token-1"))
```

### Assertions
```pseudo
# No deregistration DELETE (nothing was registered), and no late POST
poll_until(() => false, interval: 50ms, timeout: 500ms)  # allow any erroneous request to surface
ASSERT captured_requests.length == 0
ASSERT mock_storage.dump()["ably.push.activationState"] == "NotActivated"
```

---

## RSH3c1a — repeated activate while device registration is in flight is idempotent

**Test ID**: `rest/unit/RSH3c1a/activate-while-registering-0`

**Spec requirement:** RSH3c1a — In `WaitingForDeviceRegistration`, on `CalledActivate`, transitions to `WaitingForDeviceRegistration` (self).

### Setup
```pseudo
held_post = null
captured_requests = mock_registration_server(overrides: (req) => {
  IF req.method == "POST" AND req.url.path == "/push/deviceRegistrations" AND held_post == null:
    held_post = req  # hold the registration open
    RETURN true
  RETURN false
})
mock_storage = MockPushStorage()
client = push_client(mock_storage)
```

### Test Steps
```pseudo
first = client.push.activate()
poll_until_success(() => held_post != null)

second = client.push.activate()  # RSH3c1a — self-transition, no second POST

held_post.respond_with(201, merge(parse_json(held_post.body), {"deviceIdentityToken": {"token": "ident-token-1"}}))

AWAIT first
AWAIT second
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

---

## RSH3d2, RSH3g2 — deactivate deregisters the device and clears local state

**Test ID**: `rest/unit/RSH2b/deactivate-full-flow-0`

| Spec | Requirement |
|------|-------------|
| RSH2b | `Push#deactivate` sends a `CalledDeactivate` event to the state machine |
| RSH3d2b | Makes an asynchronous DELETE to `/push/deviceRegistrations` using the device's ID, with push device authentication without other token or key authentication |
| RSH3d2d | Transitions to `WaitingForDeregistration` |
| RSH3g2a | On `Deregistered`, clears all local `DeviceDetails` |
| RSH3g2b | Makes `Push#deactivate` return with no error |
| RSH3g2c | Transitions to `NotActivated` |

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
device_id = mock_storage.dump()["ably.push.deviceId"]
```

### Test Steps
```pseudo
AWAIT client.push.deactivate()
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")
```

### Assertions
```pseudo
ASSERT captured_requests.length == 2
request = captured_requests[1]
ASSERT request.method == "DELETE"
ASSERT request.url.path == "/push/deviceRegistrations"
ASSERT request.url.query["deviceId"] == device_id

# RSH3d2b + RSH6a — push device authentication
ASSERT request.headers["X-Ably-DeviceToken"] == "ident-token-1"

# RSH3g2a — the registered identity is cleared from storage, not just memory
persisted = mock_storage.dump()
ASSERT "ably.push.deviceIdentityToken" NOT IN persisted
ASSERT "ably.push.pushRecipient" NOT IN persisted
```

---

## RSH3d2a — deactivate with a custom deregisterCallback routes deregistration through the callback

**Test ID**: `rest/unit/RSH3d2a/deactivate-deregister-callback-0`

**Spec requirement:** RSH3d2a — If a custom `deregisterCallback` was provided to `Push#deactivate`, pass it the local `DeviceDetails`'s id.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
device_id = mock_storage.dump()["ably.push.deviceId"]

deregistered_ids = []
FUNCTION deregister_callback(deviceId):
  deregistered_ids.append(deviceId)
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.deactivate(deregisterCallback: deregister_callback)

# Deregistration went through the callback: no DELETE
ASSERT captured_requests.length == 1  # just the seeding POST
ASSERT deregistered_ids == [device_id]
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")
```

---

## RSH3a1c — deactivate from NotActivated with a registered device still deregisters

**Test ID**: `rest/unit/RSH3a1c/deactivate-not-activated-with-token-0`

**Spec requirement:** RSH3a1c — In `NotActivated`, on `CalledDeactivate`, if the local device has `deviceIdentityToken`, does the same as RSH3d2.

Tests via hand-seeded storage: a device that is registered (has an identity token) but whose persisted machine state is `NotActivated` — e.g. state left behind by an earlier partial failure.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
mock_storage.seed({
  "ably.push.deviceId": "seeded-device-1",
  "ably.push.deviceSecret": "seeded-secret",
  "ably.push.deviceIdentityToken": "\"seeded-ident-token\"",
  "ably.push.activationState": "NotActivated"
})
client = push_client(mock_storage)
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.deactivate()

ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.method == "DELETE"
ASSERT request.url.query["deviceId"] == "seeded-device-1"
ASSERT request.headers["X-Ably-DeviceToken"] == "seeded-ident-token"
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")
```

---

## RSH3a1d — deactivate from NotActivated with no registration resolves without any request

**Test ID**: `rest/unit/RSH3a1d/deactivate-not-activated-0`

**Spec requirement:** RSH3a1d — Otherwise (no `deviceIdentityToken`), does the same as RSH3g2 (resolve deactivate, remain `NotActivated`).

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = push_client(mock_storage)
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.deactivate()

ASSERT captured_requests.length == 0
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")
```

---

## RSH3d2c1 — deregistration treats 401 as success

**Test ID**: `rest/unit/RSH3d2c1/deregister-401-succeeds-0`

**Spec requirement:** RSH3d2c1 — `Deregistered` should be fired if the DELETE returns a 2xx status, 401 (unauthorized), or error code 40005 (invalid credentials). Otherwise `DeregistrationFailed`.

A 401 means the server no longer recognises the device's credentials — the registration is already gone, so deactivation has succeeded.

### Setup
```pseudo
captured_requests = mock_registration_server(overrides: (req) => {
  IF req.method == "DELETE":
    req.respond_with(401, {"error": {"message": "unauthorized", "code": 40100, "statusCode": 401}})
    RETURN true
  RETURN false
})
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.deactivate()  # resolves despite the 401

poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")
persisted = mock_storage.dump()
ASSERT "ably.push.deviceIdentityToken" NOT IN persisted
```

---

## RSH3d2c1 — deregistration treats error code 40005 as success

**Test ID**: `rest/unit/RSH3d2c1/deregister-40005-succeeds-1`

**Spec requirement:** RSH3d2c1 — as above; 40005 (invalid credentials) is classified as `Deregistered`.

### Setup
```pseudo
captured_requests = mock_registration_server(overrides: (req) => {
  IF req.method == "DELETE":
    req.respond_with(400, {"error": {"message": "invalid credentials", "code": 40005, "statusCode": 400}})
    RETURN true
  RETURN false
})
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.deactivate()  # resolves despite the 40005

poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")
```

---

## RSH3d2c1, RSH3g3 — deregistration failure fails deactivate and rolls back to the previous state

**Test ID**: `rest/unit/RSH3g3b/deregister-failure-rollback-0`

| Spec | Requirement |
|------|-------------|
| RSH3d2c1 | Status codes other than 2xx/401/40005 fire `DeregistrationFailed` (a non-retriable 4xx is injected so that SDKs implementing RSC15 fallback-host retries issue exactly one DELETE attempt) |
| RSH3g3a | Makes `Push#deactivate` return with the error |
| RSH3g3b | Transitions to the previous state (`WaitingForNewPushDeviceDetails` here) |

Tests the rollback by observing that after the failure the device is still registered: a retry of `deactivate()` issues the DELETE again, and succeeds.

### Setup
```pseudo
fail_delete = true
captured_requests = mock_registration_server(overrides: (req) => {
  IF req.method == "DELETE" AND fail_delete:
    req.respond_with(400, {"error": {"message": "deregistration rejected", "code": 40198, "statusCode": 400}})
    RETURN true
  RETURN false
})
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.deactivate() FAILS WITH error
ASSERT error.code == 40198

# RSH3g3b — still registered: the identity token survives the failed deregistration
ASSERT mock_storage.dump()["ably.push.deviceIdentityToken"] IS NOT null

# Retry succeeds from the rolled-back state
fail_delete = false
AWAIT client.push.deactivate()
ASSERT captured_requests.length == 3  # POST + failed DELETE + successful DELETE
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")
```

---

## RSH3g1a — repeated deactivate while deregistration is in flight is idempotent

**Test ID**: `rest/unit/RSH3g1a/deactivate-while-deregistering-0`

**Spec requirement:** RSH3g1a — In `WaitingForDeregistration`, on `CalledDeactivate`, transitions to `WaitingForDeregistration` (self).

### Setup
```pseudo
held_delete = null
captured_requests = mock_registration_server(overrides: (req) => {
  IF req.method == "DELETE" AND held_delete == null:
    held_delete = req  # hold the deregistration open
    RETURN true
  RETURN false
})
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
```

### Test Steps
```pseudo
first = client.push.deactivate()
poll_until_success(() => held_delete != null)

second = client.push.deactivate()  # RSH3g1a — self-transition, no second DELETE

held_delete.respond_with(204, "")

AWAIT first
AWAIT second
```

### Assertions
```pseudo
# Exactly one DELETE was issued
delete_requests = captured_requests WHERE method == "DELETE"
ASSERT delete_requests.length == 1
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")
```

---

## RSH3e3, RSH3f1 — a failed registration sync fails activate; re-activating retries the sync

**Test ID**: `rest/unit/RSH3e3c/sync-failure-then-reactivate-0`

| Spec | Requirement |
|------|-------------|
| RSH3e3c | On `SyncRegistrationFailed` (entered via `CalledActivate`), makes `Push#activate` return with the error |
| RSH3e3b | Transitions to `AfterRegistrationSyncFailed` |
| RSH3f1a | In `AfterRegistrationSyncFailed`, `CalledActivate` does the same as RSH3a2a (the RSH3a2a3 PATCH sync) |

### Setup
```pseudo
fail_patch = true
captured_requests = mock_registration_server(overrides: (req) => {
  IF req.method == "PATCH" AND fail_patch:
    req.respond_with(400, {"error": {"message": "sync rejected", "code": 40199, "statusCode": 400}})
    RETURN true
  RETURN false
})
mock_storage = MockPushStorage()
AWAIT activate_into(mock_storage)
device_id = mock_storage.dump()["ably.push.deviceId"]
```

### Test Steps and Assertions
```pseudo
# Fresh client over registered storage: activate syncs via PATCH, which fails
client = push_client(mock_storage)
AWAIT client.push.activate() FAILS WITH error
ASSERT error.code == 40199
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "AfterRegistrationSyncFailed")

# RSH3f1a — activate again; the machine re-runs the RSH3a2a validation
fail_patch = false
AWAIT client.push.activate()

patch_requests = captured_requests WHERE method == "PATCH"
ASSERT patch_requests.length == 2
ASSERT patch_requests[1].url.path == "/push/deviceRegistrations/" + encode_uri_component(device_id)
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

---

## RSH3f2a — deactivate from AfterRegistrationSyncFailed deregisters normally

**Test ID**: `rest/unit/RSH3f2a/deactivate-after-sync-failure-0`

**Spec requirement:** RSH3f2a — In `AfterRegistrationSyncFailed`, on `CalledDeactivate`, does the same as RSH3d2.

### Setup
```pseudo
captured_requests = mock_registration_server(overrides: (req) => {
  IF req.method == "PATCH":
    req.respond_with(400, {"error": {"message": "sync rejected", "code": 40199, "statusCode": 400}})
    RETURN true
  RETURN false
})
mock_storage = MockPushStorage()
AWAIT activate_into(mock_storage)
device_id = mock_storage.dump()["ably.push.deviceId"]

client = push_client(mock_storage)
AWAIT client.push.activate() FAILS WITH error  # drive into AfterRegistrationSyncFailed
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "AfterRegistrationSyncFailed")
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.deactivate()

delete_requests = captured_requests WHERE method == "DELETE"
ASSERT delete_requests.length == 1
ASSERT delete_requests[0].url.query["deviceId"] == device_id
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")
```

---

## RSH3g3b — deregistration failure from AfterRegistrationSyncFailed rolls back to AfterRegistrationSyncFailed

**Test ID**: `rest/unit/RSH3g3b/deregister-failure-rollback-after-sync-failed-1`

**Spec requirement:** RSH3g3b — Transitions to the previous state, which is either `WaitingForNewPushDeviceDetails` or `AfterRegistrationSyncFailed`.

Tests the second rollback target: after a failed deactivation from `AfterRegistrationSyncFailed`, the machine is back in `AfterRegistrationSyncFailed` — observable because a subsequent `activate()` re-runs the RSH3a2a validation (per `RSH3f1a`) rather than resolving immediately.

### Setup
```pseudo
fail_patch = true
fail_delete = true
captured_requests = mock_registration_server(overrides: (req) => {
  IF req.method == "PATCH" AND fail_patch:
    req.respond_with(400, {"error": {"message": "sync rejected", "code": 40199, "statusCode": 400}})
    RETURN true
  IF req.method == "DELETE" AND fail_delete:
    req.respond_with(400, {"error": {"message": "deregistration rejected", "code": 40198, "statusCode": 400}})
    RETURN true
  RETURN false
})
mock_storage = MockPushStorage()
AWAIT activate_into(mock_storage)

client = push_client(mock_storage)
AWAIT client.push.activate() FAILS WITH error  # -> AfterRegistrationSyncFailed
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "AfterRegistrationSyncFailed")
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.deactivate() FAILS WITH error
ASSERT error.code == 40198

# Back in AfterRegistrationSyncFailed: activate re-syncs via PATCH (RSH3f1a)
fail_patch = false
AWAIT client.push.activate()
patch_requests = captured_requests WHERE method == "PATCH"
ASSERT patch_requests.length == 2
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```
