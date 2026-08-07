# Push updateToken Tests

Spec points: `RSH2f`, `RSH2f1`, `RSH2f2`, `RSH2f3`, `RSH3a2a3`, `RSH3a3a`, `RSH3d3`, `RSH3d3a`, `RSH3d3b`, `RSH3d3c`, `RSH3d3d`, `RSH3e1a`, `RSH3e1b`, `RSH3e2a`, `RSH3e2c`, `RSH3e3b`, `RSH3e3d`, `RSH3f1a`, `RSH3g2a`, `RSH3h`, `RSH4`, `RSH6a`, `RSH8g`, `RSH8l2`, `PCP3a`, `PDT4`

## Test Type
Unit test with mocked HTTP client and mocked push platform

## Mock HTTP Infrastructure

See `uts/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

## Mock Push Platform Infrastructure

See `uts/rest/unit/helpers/mock_push_platform.md` for the portable push platform primitives (`PushKeyValueStorage`, `requestToken`, `PushPlatformConfig`, `PushDeviceToken`), the standard `ably.push.*` storage keys, and the `MockPushStorage` mock.

## Notes

`push.updateToken(token: PushDeviceToken)` is specified by `RSH2f` (with `PushDeviceToken` per `PDT1`–`PDT4`): the portable API (established by ably-js PR #2267) through which the application delivers a rotated or additional platform token, thereby producing the `RSH8g` `GotPushDeviceDetails` event. Note `RSH2f`/`RSH8l`/`PCP3a`/`PDT*` are part of the pending token-variants spec extension (drafted in `specifications/features.md`, not yet merged upstream); the remaining anchors are long-established points.

`updateToken` resolves once the new recipient has been persisted (to `ably.push.pushRecipient`) and the `GotPushDeviceDetails` event has been handed to the state machine. The registration sync the event triggers (`RSH3d3b`/`RSH3d3c`) is **fire-and-forget**: its outcome is reported through the `updatedCallback` provided to `Push#activate` (`RSH3e2c`/`RSH3e3d`), never through the `updateToken` return value. Tests therefore poll for the sync's observable effects (the HTTP request, the persisted state) rather than awaiting a promise.

The client-side guards are specified by `RSH2f1` (validation) and `RSH2f2` (activation required): `updateToken` fails with `code` 40000 — before any event reaches the machine and without any HTTP request — when the device is not activated (no `deviceIdentityToken`), when the token is null or malformed, when the token string is empty, or when `transportType` is `"web"` (web recipients are constructed by the SDK's own web-platform flow and are not app-suppliable — see the token-to-recipient table in `mock_push_platform.md`).

These tests are **black-box**, following `push_activation_state_machine.md`: they never construct events or inspect machine state directly. Events are produced by driving the public API (`push.activate()`, `push.deactivate()`, `push.updateToken()`) and by responding to the mocked HTTP requests the machine issues. State is observed through behaviour (which requests are made, which operations resolve or fail) and, after operations settle, through the persisted `ably.push.activationState`. To pin the machine in an intermediate state, tests hold a `PendingRequest` (capture it in the `onRequest` handler without responding) and release it later; `Deferred<T>` is as defined in `push_activation_state_machine.md`.

Device authentication assertions follow `RSH6a` (`X-Ably-DeviceToken` header). An SDK using a different device-auth mechanism (e.g. an `Authorization` bearer header carrying the `deviceIdentityToken` — as ably-js does) must record a deviation and adapt the assertion.

**Known ably-js deviations** (record in derived tests):

- `RSH3e3d` says a sync failure not attributable to a `CalledActivate` calls the `updatedCallback` provided to `Push#activate` with the error; `RSH3e2c` says a successful sync calls it with no error. ably-js currently routes failures to the deprecated `updateFailedCallback` (`RSH3e3a`) and has no success-notification path at all, so derived ably-js tests must adapt the callback assertions in `update-token-sync-failure-callback-4` (deliver the error via `updateFailedCallback`; omit the no-error `RSH3e2c` assertion).
- (Resolved — no longer a deviation:) `RSH3a2a3` now defines the re-activation/retry sync as the same `RSH3d3b` PATCH carrying the complete recipient (with a full-body PUT permitted as a legacy equivalent, as ably-java and ably-cocoa do). ably-js's PATCH-based `updateRegistration()` in `AfterRegistrationSyncFailed` is therefore conformant, and the retry-request assertions in `update-token-sync-failure-callback-4` assert the PATCH directly.

## Shared Test Setup

All tests use the following helpers, plus the `BEFORE EACH TEST` / `AFTER EACH TEST` isolation from `mock_push_platform.md`. They are the helpers of `push_activation_state_machine.md`, with `build_push_platform`/`push_client` extended to take an optional `platform`.

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

FUNCTION build_push_platform(storage, token?: PushDeviceToken, requestToken?: Function, platform?: String):
  RETURN MockPushPlatform(
    platform: platform ?? "android",
    formFactor: "phone",
    storage: storage,
    requestToken: requestToken ?? (() => token ?? PushDeviceToken(transportType: "fcm", token: "fcm-token-1"))
  )

FUNCTION push_client(storage, clientId?: String, token?, requestToken?, platform?):
  install_push_platform(build_push_platform(storage, token, requestToken, platform))
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

## RSH8g, RSH3d3 — a rotated fcm token is synced via PATCH with changed fields only

**Test ID**: `rest/unit/RSH3d3b/update-token-patch-0`

| Spec | Requirement |
|------|-------------|
| RSH8g | A change of the push transport details sends a `GotPushDeviceDetails` event to the state machine |
| RSH3d3 | In `WaitingForNewPushDeviceDetails`, `GotPushDeviceDetails` occurs when the push details change after first being set (e.g. FCM registration token refresh) |
| RSH3d3b | Makes an asynchronous PATCH to `/push/deviceRegistrations/:deviceId` with only the changed fields as body; requires push device authentication |
| RSH3d3c | When the sync is done, a `RegistrationSynced` or `SyncRegistrationFailed` event is fired |
| RSH3e2a | On `RegistrationSynced`, transitions to `WaitingForNewPushDeviceDetails` |
| RSH6a | Push device authentication adds an `X-Ably-DeviceToken` header whose value is the `deviceIdentityToken` |

Tests that delivering a rotated FCM token to an activated device produces the RSH3d3b sync: a PATCH addressed to the device, carrying only the new recipient, authenticated as the device, and that the new recipient is persisted and the machine settles back in `WaitingForNewPushDeviceDetails`.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
device_id = mock_storage.dump()["ably.push.deviceId"]
```

### Test Steps
```pseudo
AWAIT client.push.updateToken(PushDeviceToken(transportType: "fcm", token: "fcm-token-2"))

# The sync is fire-and-forget: poll for the PATCH it issues
poll_until(() => captured_requests.length == 2)
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

### Assertions
```pseudo
request = captured_requests[1]
ASSERT request.method == "PATCH"
ASSERT request.url.path == "/push/deviceRegistrations/" + encode_uri_component(device_id)

# RSH3d3b — only the changed fields travel in the body; the device id is in the URL
ASSERT parse_json(request.body) == {
  "push": {"recipient": {"transportType": "fcm", "registrationToken": "fcm-token-2"}}
}

# RSH3d3b + RSH6a — push device authentication
ASSERT request.headers["X-Ably-DeviceToken"] == "ident-token-1"

# The rotated recipient was persisted
ASSERT parse_json(mock_storage.dump()["ably.push.pushRecipient"]) == {
  "transportType": "fcm",
  "registrationToken": "fcm-token-2"
}
```

---

## RSH8g — an apns token maps to an apns recipient

**Test ID**: `rest/unit/RSH8g/update-token-apns-recipient-1`

| Spec | Requirement |
|------|-------------|
| RSH8g | A change of the push transport details sends a `GotPushDeviceDetails` event to the state machine |
| RSH3d3b | The PATCH body carries the changed push details — here an `apns` recipient, whose token field is `deviceToken` (see the token-to-recipient table in `mock_push_platform.md`) |

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = push_client(mock_storage, token: PushDeviceToken(transportType: "apns", token: "apns-token-1"), platform: "ios")
AWAIT client.push.activate()
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

### Test Steps
```pseudo
AWAIT client.push.updateToken(PushDeviceToken(transportType: "apns", token: "apns-token-2"))
poll_until(() => captured_requests.length == 2)
```

### Assertions
```pseudo
request = captured_requests[1]
ASSERT request.method == "PATCH"
ASSERT parse_json(request.body) == {
  "push": {"recipient": {"transportType": "apns", "deviceToken": "apns-token-2"}}
}
```

---

## RSH2f2 — updateToken requires an activated device, and does not disturb a later activation

**Test ID**: `rest/unit/RSH2f2/update-token-requires-activation-2`

**Spec requirement:** `RSH2f2` — `updateToken` requires that the device has completed activation (has a `deviceIdentityToken`); otherwise it is rejected with an error with `code` 40000, without any effect. The guard fires before any event reaches the state machine, so a subsequent `activate()` proceeds entirely normally.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = push_client(mock_storage)
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.updateToken(PushDeviceToken(transportType: "fcm", token: "fcm-token-2")) FAILS WITH error
ASSERT error.code == 40000

# Nothing reached the machine or the network
process_pending_events()
ASSERT captured_requests.length == 0

# A subsequent activation is unaffected by the rejected update
AWAIT client.push.activate()
ASSERT captured_requests.length == 1
ASSERT captured_requests[0].method == "POST"
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

---

## RSH8g, RSH3h — updateToken works from persisted state on a cold start, without activate() this session

**Test ID**: `rest/unit/RSH8g/update-token-cold-start-3`

| Spec | Requirement |
|------|-------------|
| RSH8g | A change of the push transport details sends a `GotPushDeviceDetails` event to the state machine |
| RSH3h | The state machine is initialised from the persisted Activation State Machine data when an event first needs to be delivered to it |
| RSH3d3b | The sync PATCH is addressed to the persisted device's id |

Tests that a fresh client over storage holding a registered device (persisted state `WaitingForNewPushDeviceDetails`) can deliver a rotated token without `activate()` having been called this session: the machine hydrates from storage and runs the RSH3d3 sync against the persisted registration.

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
restarted = push_client(mock_storage)
AWAIT restarted.push.updateToken(PushDeviceToken(transportType: "fcm", token: "fcm-token-2"))
poll_until(() => captured_requests.length == 2)
```

### Assertions
```pseudo
request = captured_requests[1]
ASSERT request.method == "PATCH"
# The restarted client loaded the persisted device id and addressed the same registration
ASSERT request.url.path == "/push/deviceRegistrations/" + encode_uri_component(device_id)
ASSERT parse_json(request.body)["push"]["recipient"]["registrationToken"] == "fcm-token-2"
```

---

## RSH3e3d, RSH3f1a — a failed sync is reported via updatedCallback; a retry re-validates per RSH3a2a

**Test ID**: `rest/unit/RSH3e3d/update-token-sync-failure-callback-4`

| Spec | Requirement |
|------|-------------|
| RSH3d3c | When the sync is done, a `RegistrationSynced` or `SyncRegistrationFailed` event is fired |
| RSH3e3d | On `SyncRegistrationFailed` (not entered via `CalledActivate`), calls the `updatedCallback` provided to `Push#activate` with the error |
| RSH3e3b | Transitions to `AfterRegistrationSyncFailed` |
| RSH3f1a | In `AfterRegistrationSyncFailed`, `GotPushDeviceDetails` does the same as RSH3a2a |
| RSH3a2a3 | Performs the RSH3d3b sync: an HTTP PATCH to `/push/deviceRegistrations/:deviceId` carrying the complete `push.recipient` |
| RSH3e2c | On `RegistrationSynced` (not entered via `CalledActivate`), calls the `updatedCallback` with no error |
| RSH3e2a | Transitions to `WaitingForNewPushDeviceDetails` |

Tests that a server rejection of the sync surfaces through the `updatedCallback` (not through `updateToken`, which has already resolved — the sync is fire-and-forget), that the rotated recipient is nonetheless persisted, and that a retry from `AfterRegistrationSyncFailed` re-runs the RSH3a2a validation — which per RSH3a2a3 is the same RSH3d3b PATCH sync. See Notes for the ably-js deviation this test records (`updateFailedCallback` instead of `updatedCallback`).

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
client = push_client(mock_storage)

sync_results = []
AWAIT client.push.activate(updatedCallback: (error) => sync_results.append(error))
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
device_id = mock_storage.dump()["ably.push.deviceId"]
```

### Test Steps and Assertions
```pseudo
# The sync is fire-and-forget: updateToken resolves despite the PATCH failing
AWAIT client.push.updateToken(PushDeviceToken(transportType: "fcm", token: "fcm-token-2"))

# RSH3e3d — the failure reaches the updatedCallback
poll_until(() => sync_results.length == 1)
ASSERT sync_results[0].code == 40199

# The rotated recipient was persisted even though the sync failed
ASSERT parse_json(mock_storage.dump()["ably.push.pushRecipient"]) == {
  "transportType": "fcm",
  "registrationToken": "fcm-token-2"
}

# RSH3e3b — the machine is in AfterRegistrationSyncFailed
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "AfterRegistrationSyncFailed")

# RSH3f1a — a retry with the server healthy re-runs the RSH3a2a validation, which
# per RSH3a2a3 is the same RSH3d3b sync: a second PATCH with the complete recipient
fail_patch = false
AWAIT client.push.updateToken(PushDeviceToken(transportType: "fcm", token: "fcm-token-2"))

poll_until(() => (captured_requests WHERE method == "PATCH").length == 2)
retry = (captured_requests WHERE method == "PATCH")[1]
ASSERT retry.url.path == "/push/deviceRegistrations/" + encode_uri_component(device_id)
retry_body = parse_json(retry.body)
ASSERT retry_body["push"]["recipient"]["registrationToken"] == "fcm-token-2"

# RSH3e2c — the successful sync reaches the updatedCallback with no error
poll_until(() => sync_results.length == 2)
ASSERT sync_results[1] == null

# RSH3e2a — settled back in WaitingForNewPushDeviceDetails
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

---

## RSH2f1 — malformed tokens are rejected without touching the machine, the network, or storage

**Test ID**: `rest/unit/RSH2f1/update-token-validation-5`

**Spec requirement:** `RSH2f1` — the provided token must carry a supported `transportType` and a non-empty `token`; an invalid token is rejected with an error with `code` 40000, without any effect on the `LocalDevice` or the state machine. A null token, a `"web"` transport (web recipients are not app-suppliable — see `mock_push_platform.md`), and an empty token string each fail, producing no `GotPushDeviceDetails` event, no HTTP request, and no storage change.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
persisted_before = mock_storage.dump()
```

### Test Steps and Assertions
```pseudo
FOR bad IN [null,
            PushDeviceToken(transportType: "web", token: "web-token-1"),
            PushDeviceToken(transportType: "fcm", token: "")]:
  AWAIT client.push.updateToken(bad) FAILS WITH error
  ASSERT error.code == 40000

process_pending_events()
ASSERT captured_requests.length == 1  # just the activation POST
ASSERT mock_storage.dump() == persisted_before  # storage untouched, recipient included
```

---

## RSH3d3a — a device activated via a custom registerCallback syncs through the same callback

**Test ID**: `rest/unit/RSH3d3a/update-token-register-callback-6`

| Spec | Requirement |
|------|-------------|
| RSH3d3a | If a custom `registerCallback` was provided to `Push#activate`, pass it the local `DeviceDetails` updated with the push details (instead of the PATCH of RSH3d3b) |
| RSH3d3c | When the sync is done, a `RegistrationSynced` or `SyncRegistrationFailed` event is fired |

Tests that the token-rotation sync is routed through the customer's registrar with the new recipient, and no HTTP request is made at any point.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = push_client(mock_storage)

registered_devices = []
FUNCTION register_callback(device):
  registered_devices.append(device)
  RETURN {"deviceIdentityToken": {"token": "custom-ident-1"}}

AWAIT client.push.activate(registerCallback: register_callback)
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

### Test Steps
```pseudo
AWAIT client.push.updateToken(PushDeviceToken(transportType: "fcm", token: "fcm-token-2"))
poll_until(() => registered_devices.length == 2)
```

### Assertions
```pseudo
# RSH3d3a — the sync went through the same registerCallback, with the new recipient
ASSERT registered_devices[1].push.recipient == {
  "transportType": "fcm",
  "registrationToken": "fcm-token-2"
}

# No HTTP at all: neither the registration nor the sync touched the network
ASSERT captured_requests.length == 0

# The rotated recipient was persisted
poll_until_success(() => parse_json(mock_storage.dump()["ably.push.pushRecipient"])["registrationToken"] == "fcm-token-2")
```

---

## RSH3e1a — activate during an in-flight token sync resolves immediately without a request

**Test ID**: `rest/unit/RSH3e1a/activate-during-token-sync-7`

| Spec | Requirement |
|------|-------------|
| RSH3d3d | `GotPushDeviceDetails` transitions to `WaitingForRegistrationSync` |
| RSH3e1a | In `WaitingForRegistrationSync` not entered via `CalledActivate`, on `CalledActivate`, makes `Push#activate` return with no error |
| RSH3e1b | Transitions to `WaitingForRegistrationSync` (self) |
| RSH3e2a | On `RegistrationSynced`, transitions to `WaitingForNewPushDeviceDetails` |

Tests that with the RSH3d3b PATCH held open — pinning the machine in `WaitingForRegistrationSync` entered via `GotPushDeviceDetails` — an `activate()` resolves with no error without waiting for the sync and without issuing any request (the `RSH3e1` "unless ... as a result of a `CalledActivate` event" carve-out does not apply here).

### Setup
```pseudo
held_patch = null
captured_requests = mock_registration_server(overrides: (req) => {
  IF req.method == "PATCH" AND held_patch == null:
    held_patch = req  # hold the sync open
    RETURN true
  RETURN false
})
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.updateToken(PushDeviceToken(transportType: "fcm", token: "fcm-token-2"))
poll_until(() => held_patch != null)  # machine now in WaitingForRegistrationSync (RSH3d3d)

# RSH3e1a — resolves while the PATCH is still held, so it did not wait for the sync
AWAIT client.push.activate()

# RSH3e1b — self-transition: no request was issued for the activate
process_pending_events()
ASSERT captured_requests.length == 2  # activation POST + held PATCH only

held_patch.respond_with(200, parse_json(held_patch.body))

# RSH3e2a — the released sync settles the machine in WaitingForNewPushDeviceDetails
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

---

## RSH4 — an update issued during an in-flight sync is queued and applied after it settles

**Test ID**: `rest/unit/RSH4/update-token-queued-behind-inflight-sync-8`

| Spec | Requirement |
|------|-------------|
| RSH4 | An event with no transition defined in the current state is queued, and dequeued after the next transition |
| RSH3d3b | The dequeued `GotPushDeviceDetails`, consumed in `WaitingForNewPushDeviceDetails`, issues its own changed-fields PATCH |

`WaitingForRegistrationSync` defines no transition for `GotPushDeviceDetails`, so the second update's event queues (RSH4) behind the held sync; when the first sync settles (`RegistrationSynced` → `WaitingForNewPushDeviceDetails`, `RSH3e2a`), the queued event is dequeued and consumed per RSH3d3.

### Setup
```pseudo
held_patch = null
captured_requests = mock_registration_server(overrides: (req) => {
  IF req.method == "PATCH" AND held_patch == null:
    held_patch = req  # hold the first sync open; later PATCHes use the default route
    RETURN true
  RETURN false
})
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
```

### Test Steps
```pseudo
AWAIT client.push.updateToken(PushDeviceToken(transportType: "fcm", token: "fcm-token-2"))
poll_until(() => held_patch != null)

# Resolves (recipient persisted, event handed over), but its sync is queued per RSH4
AWAIT client.push.updateToken(PushDeviceToken(transportType: "fcm", token: "fcm-token-3"))

process_pending_events()
ASSERT (captured_requests WHERE method == "PATCH").length == 1  # only the held one

held_patch.respond_with(200, parse_json(held_patch.body))
poll_until(() => (captured_requests WHERE method == "PATCH").length == 2)
```

### Assertions
```pseudo
patches = captured_requests WHERE method == "PATCH"
ASSERT parse_json(patches[1].body) == {
  "push": {"recipient": {"transportType": "fcm", "registrationToken": "fcm-token-3"}}
}

poll_until_success(() => parse_json(mock_storage.dump()["ably.push.pushRecipient"])["registrationToken"] == "fcm-token-3")
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

---

## RSH4 — an update racing a deactivation is discarded once the device is deregistered

**Test ID**: `rest/unit/RSH4/update-token-discarded-after-deregistration-9`

| Spec | Requirement |
|------|-------------|
| RSH4 | An event with no transition defined in the current state is queued, and dequeued after the next transition |
| RSH3a3a | In `NotActivated`, `GotPushDeviceDetails` is consumed with a self-transition |
| RSH3g2a | On `Deregistered`, clears all local `DeviceDetails` |

`WaitingForDeregistration` defines no transition for `GotPushDeviceDetails`, so the update's event queues (RSH4). Deregistration then lands the machine in `NotActivated`, where the dequeued event is consumed per RSH3a3a — so no sync PATCH is ever issued, and the recipient the update persisted has been cleared by RSH3g2a.

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
deactivation = client.push.deactivate()
poll_until(() => held_delete != null)

# The device still has its deviceIdentityToken, so the guard passes; the event queues
AWAIT client.push.updateToken(PushDeviceToken(transportType: "fcm", token: "fcm-token-2"))

held_delete.respond_with(204, "")
AWAIT deactivation
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")
```

### Assertions
```pseudo
# RSH4 + RSH3a3a — the queued event was consumed in NotActivated: no sync ever ran
process_pending_events()
ASSERT (captured_requests WHERE method == "PATCH").length == 0

# RSH3g2a — deregistration removed the recipient the update had persisted
ASSERT "ably.push.pushRecipient" NOT IN mock_storage.dump()
```

---

## RSH8l2, PCP3a — registering a push-to-start token adds a variant slot without disturbing the default token

**Test ID**: `rest/unit/RSH8l2/update-token-push-to-start-10`

| Spec | Requirement |
|------|-------------|
| RSH2f3 | The new details are applied to the recipient, for an `apns` token to the slot indicated by its `apnsTokenType` |
| PCP3a | Variant tokens are carried in the recipient's `apnsDeviceTokens` map, keyed by slot name |
| RSH8l2 | Registering a variant is a change of push transport details (`RSH8g`); the sync carries the complete updated recipient, including the unchanged variants |

Tests that delivering a Live Activity push-to-start token via `updateToken` on a device activated with a default APNs token adds the `pushToStart` slot to the recipient — and keeps the default token registered.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = AWAIT activate_into_apns(mock_storage)   # defined below
device_id = mock_storage.dump()["ably.push.deviceId"]

# Activation as in activate_into, but as an ios/apns device
FUNCTION activate_into_apns(storage):
  client = push_client(storage, token: PushDeviceToken(transportType: "apns", token: "apns-token-1"), platform: "ios")
  AWAIT client.push.activate()
  poll_until_success(() => storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
  RETURN client
```

### Test Steps
```pseudo
AWAIT client.push.updateToken(PushDeviceToken(
  transportType: "apns",
  token: "pts-token-1",
  apnsTokenType: "pushToStart"
))

poll_until(() => (captured_requests WHERE method == "PATCH").length == 1, interval: 50ms, timeout: 5 seconds)
```

### Assertions
```pseudo
patch = (captured_requests WHERE method == "PATCH")[0]
ASSERT patch.url.path == "/push/deviceRegistrations/" + encode_uri_component(device_id)

recipient = parse_json(patch.body)["push"]["recipient"]
ASSERT recipient["transportType"] == "apns"

# PCP3a — the variant landed in its slot
ASSERT recipient["apnsDeviceTokens"]["pushToStart"] == "pts-token-1"

# RSH8l2 — the default token was preserved (either representation per PCP3a)
ASSERT recipient["deviceToken"] == "apns-token-1" OR recipient["apnsDeviceTokens"]["default"] == "apns-token-1"

# The full recipient, variants included, is persisted
persisted_recipient = parse_json(mock_storage.dump()["ably.push.pushRecipient"])
ASSERT persisted_recipient["apnsDeviceTokens"]["pushToStart"] == "pts-token-1"
```

---

## RSH8l2 — rotating the default token preserves registered variant slots

**Test ID**: `rest/unit/RSH8l2/update-token-variant-preserves-others-11`

**Spec requirement:** `RSH8l2` — the registration, update or removal of any single variant is a change of the push transport details, and the ensuing sync carries the complete updated recipient *including the unchanged variants*. Rotating the default token after a `pushToStart` token has been registered must not drop the `pushToStart` slot.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = AWAIT activate_into_apns(mock_storage)   # as in update-token-push-to-start-10

AWAIT client.push.updateToken(PushDeviceToken(transportType: "apns", token: "pts-token-1", apnsTokenType: "pushToStart"))
poll_until(() => (captured_requests WHERE method == "PATCH").length == 1, interval: 50ms, timeout: 5 seconds)
```

### Test Steps
```pseudo
# Rotate the default token (apnsTokenType absent — defaults to "default" per PDT4)
AWAIT client.push.updateToken(PushDeviceToken(transportType: "apns", token: "apns-token-2"))

poll_until(() => (captured_requests WHERE method == "PATCH").length == 2, interval: 50ms, timeout: 5 seconds)
```

### Assertions
```pseudo
patch = (captured_requests WHERE method == "PATCH")[1]
recipient = parse_json(patch.body)["push"]["recipient"]

# The rotated default token
ASSERT recipient["deviceToken"] == "apns-token-2" OR recipient["apnsDeviceTokens"]["default"] == "apns-token-2"

# RSH8l2 — the pushToStart variant survived the default-token rotation
ASSERT recipient["apnsDeviceTokens"]["pushToStart"] == "pts-token-1"

persisted_recipient = parse_json(mock_storage.dump()["ably.push.pushRecipient"])
ASSERT persisted_recipient["apnsDeviceTokens"]["pushToStart"] == "pts-token-1"
```
