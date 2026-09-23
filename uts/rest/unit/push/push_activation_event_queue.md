# Push Activation Event Queue Tests

Spec points: `RSH3a2a3`, `RSH3a2a4`, `RSH3a2b`, `RSH3a2d`, `RSH3a2e`, `RSH3a3a`, `RSH3b2a`, `RSH3b2b`, `RSH3b3b`, `RSH3c2b`, `RSH3d1a`, `RSH3e1`, `RSH3e2a`, `RSH3e2b`, `RSH3g2a`, `RSH3g2b`, `RSH3g2c`, `RSH4`, `RSH5`

## Test Type
Unit test with mocked HTTP client and mocked push platform

## Mock HTTP Infrastructure

See `uts/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

## Mock Push Platform Infrastructure

See `uts/rest/unit/helpers/mock_push_platform.md` for the portable push platform primitives (`PushKeyValueStorage`, `requestToken`, `PushPlatformConfig`), the standard `ably.push.*` storage keys, and the `MockPushStorage` mock.

## Notes

These tests exercise the Activation State Machine's pending-event queue and its event-handling discipline:

> `(RSH4)` When an event is fired and a transition from the current state is not defined for such event, the event is put into a queue. Then, whenever a transition happens, an event is dequeued from the queue. If a transition from the new current state is defined for the dequeued event, such transition happens. If not, the event is put back in its place in the queue. E. g. we're `WaitingForDeregistration`, and an event `CalledActivate` happens. This event will be put in the queue, since there's no transition defined for it. Then, an event `Deregistered` arrives, causing a transition to `NotActivated`. Now we peek the next item on the queue: `CalledActivate`. Because `NotActivated` transitions on `CalledActivate`, the event is consumed and the machine transitions.

> `(RSH5)` Event handling is atomic and sequential: while an event is being handled, the next one should be handled only after the current one has caused a state transition or has been put into the pending events queue.

Also relevant is `RSH3e1`'s carve-out: in `WaitingForRegistrationSync`, `CalledActivate` has a defined transition **unless** the machine is in that state as a result of a `CalledActivate` event — in which case the event queues per `RSH4`.

These tests are **black-box**, following `push_activation_state_machine.md`: they never construct events or inspect machine state (or the queue) directly. Events are produced by driving the public API (`push.activate()`, `push.deactivate()` — `RSH2a`/`RSH2b`), by the mocked `requestToken`, and by responding to the mocked HTTP requests the machine issues. Queuing is observed through behaviour: while an event is queued, no request attributable to it is made; once the unblocking transition happens, its consumption becomes visible as requests and operation resolutions. To pin the machine in an intermediate state, tests hold a `PendingRequest` (capture it in the `onRequest` handler without responding) or a pending `requestToken` (a `Deferred<T>`, as defined in `push_activation_state_machine.md`), and release it later.

**Known ably-js deviation** (record in derived tests): ably-js does not implement the `RSH3a2a3` registration sync — a `CalledActivate` on a device that already has a `deviceIdentityToken` re-queues the event into `WaitingForNewPushDeviceDetails` and resolves `activate()` immediately, with no validation request. Consequently the `WaitingForRegistrationSync`-entered-via-`CalledActivate` scenario of `second-activate-queued-during-activate-sync-1` is not reachable in ably-js as specced; a derived ably-js test must record a deviation.

## Shared Test Setup

All tests use the following helpers from `push_activation_state_machine.md`, plus the `BEFORE EACH TEST` / `AFTER EACH TEST` isolation from `mock_push_platform.md`.

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

## RSH4 — activate queued during deregistration is consumed after it and re-registers a new device

**Test ID**: `rest/unit/RSH4/activate-queued-during-deregistration-0`

| Spec | Requirement |
|------|-------------|
| RSH4 | `WaitingForDeregistration` defines no transition for `CalledActivate`, so the event queues; on the `Deregistered` → `NotActivated` transition it is dequeued and consumed (the spec's own worked example) |
| RSH3g2a | On `Deregistered`, clears all local `DeviceDetails` |
| RSH3g2b | Makes `Push#deactivate` return with no error |
| RSH3g2c | Transitions to `NotActivated` |
| RSH3a2b | The cleared device has no `id`/`deviceSecret`, so new ones are generated |
| RSH3a2d | The cleared device has no push details, so they are requested from the platform again |
| RSH3b3b | The consumed `CalledActivate` drives a full re-registration POST |
| RSH3c2b | `Push#activate` resolves when the re-registration completes |

This is the worked example from RSH4's own text, driven black-box: with the deregistration DELETE held open, an `activate()` produces a `CalledActivate` with no defined transition in `WaitingForDeregistration` — observable as no new request while the DELETE is held. Releasing the DELETE lands the machine in `NotActivated`, where the queued event is consumed and the full registration flow re-runs against a **new** device identity (RSH3g2a cleared the old one).

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

token_requests = 0
client = push_client(mock_storage, requestToken: () => {
  token_requests += 1
  RETURN PushDeviceToken(transportType: "fcm", token: "fcm-token-1")
})
AWAIT client.push.activate()
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

### Test Steps
```pseudo
deactivation = client.push.deactivate()
poll_until(() => held_delete != null)

# No transition defined for CalledActivate in WaitingForDeregistration: it queues (RSH4)
activation = client.push.activate()
process_pending_events()
ASSERT captured_requests.length == 2  # activation POST + held DELETE; nothing new while queued

held_delete.respond_with(204, "")

AWAIT deactivation  # RSH3g2b
AWAIT activation    # RSH3c2b — resolves after the dequeued event's full re-registration
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

### Assertions
```pseudo
# RSH3a2d — the platform token was requested again for the re-registration
ASSERT token_requests == 2

# RSH3b3b — a second registration POST ran after the deregistration
post_requests = captured_requests WHERE method == "POST"
ASSERT post_requests.length == 2

# RSH3g2a + RSH3a2b — the old device was cleared, so a NEW deviceId was registered
first_id = parse_json(post_requests[0].body)["id"]
second_id = parse_json(post_requests[1].body)["id"]
ASSERT second_id != first_id
ASSERT mock_storage.dump()["ably.push.deviceId"] == second_id
```

---

## RSH5 — back-to-back activate then deactivate are handled strictly in order

**Test ID**: `rest/unit/RSH5/back-to-back-activate-deactivate-ordered-0`

| Spec | Requirement |
|------|-------------|
| RSH5 | Event handling is atomic and sequential: the next event is handled only after the current one has caused a transition or been queued |
| RSH3a2e | `CalledActivate` (handled first) transitions to `WaitingForPushDeviceDetails` |
| RSH3b2a | `CalledDeactivate` (handled second, in `WaitingForPushDeviceDetails`) makes `Push#deactivate` return with no error |
| RSH3b2b | Transitions to `NotActivated` |
| RSH3a3a | The late-arriving `GotPushDeviceDetails` is consumed in `NotActivated` with a self-transition |

With `requestToken` pending on a `Deferred`, `activate()` and `deactivate()` are called back-to-back without awaiting. Per RSH5 the events are handled strictly in call order: `CalledActivate` → `WaitingForPushDeviceDetails` (token acquisition initiated, RSH3a2d), then `CalledDeactivate` → RSH3b2 → `NotActivated`. Completing the deferred token afterwards delivers `GotPushDeviceDetails` into `NotActivated`, where RSH3a3a consumes it — so **no registration POST is ever made**. (Had the ordering not been respected — `CalledDeactivate` handled first in `NotActivated` per RSH3a1d — the activation would then have proceeded to register, which the zero-requests assertion rules out.)

The spec defines no resolution for the in-flight `activate()` in this scenario (RSH3b2 resolves only `deactivate`), so the test does not await `activation`.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()

token_deferred = Deferred<PushDeviceToken>()
client = push_client(mock_storage, requestToken: () => token_deferred.future)
```

### Test Steps
```pseudo
activation = client.push.activate()      # RSH3a2e — handled first
deactivation = client.push.deactivate()  # RSH5 — handled only after CalledActivate has transitioned

AWAIT deactivation  # RSH3b2a — resolves with no error
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "NotActivated")

# The token arrives late: RSH3a3a — consumed in NotActivated, no registration
token_deferred.complete(PushDeviceToken(transportType: "fcm", token: "fcm-token-1"))
```

### Assertions
```pseudo
process_pending_events()
ASSERT captured_requests.length == 0
ASSERT mock_storage.dump()["ably.push.activationState"] == "NotActivated"
```

---

## RSH3e1, RSH4 — a second activate during an activate-triggered sync queues until the sync settles

**Test ID**: `rest/unit/RSH4/second-activate-queued-during-activate-sync-1`

| Spec | Requirement |
|------|-------------|
| RSH3a2a3 | `CalledActivate` on a registered device performs the RSH3d3b sync: an HTTP PATCH to `/push/deviceRegistrations/:deviceId` |
| RSH3a2a4 | Transitions to `WaitingForRegistrationSync` |
| RSH3e1 | In `WaitingForRegistrationSync`, `CalledActivate` has a defined transition **unless** the state was entered as a result of a `CalledActivate` event — here it was, so the transition is not defined |
| RSH4 | The undefined event queues; it is dequeued after the next transition |
| RSH3e2b | On `RegistrationSynced` (entered via `CalledActivate`), makes the first `Push#activate` return with no error |
| RSH3e2a | Transitions to `WaitingForNewPushDeviceDetails` |
| RSH3d1a | The dequeued `CalledActivate`, consumed in `WaitingForNewPushDeviceDetails`, makes the second `Push#activate` return with no error |

Contrast with `activate-during-token-sync-7` in `push_update_token.md`, where the machine entered `WaitingForRegistrationSync` via `GotPushDeviceDetails` and RSH3e1a resolved the `activate()` immediately: here the state was entered via `CalledActivate`, so the second `CalledActivate` must queue (RSH4) — observable as its resolution being deferred until the held PATCH is released, with no additional request. See Notes for the ably-js deviation.

### Setup
```pseudo
held_patch = null
captured_requests = mock_registration_server(overrides: (req) => {
  IF req.method == "PATCH" AND held_patch == null:
    held_patch = req  # hold the validation sync open
    RETURN true
  RETURN false
})
mock_storage = MockPushStorage()
AWAIT activate_into(mock_storage)
device_id = mock_storage.dump()["ably.push.deviceId"]
```

### Test Steps
```pseudo
# A fresh client over registered storage: activate syncs the registration via PATCH (RSH3a2a3)
client = push_client(mock_storage)
first = client.push.activate()
poll_until(() => held_patch != null)  # machine in WaitingForRegistrationSync via CalledActivate (RSH3a2a4)

# RSH3e1 carve-out applies: no transition defined, so the event queues (RSH4)
second = client.push.activate()
process_pending_events()
ASSERT captured_requests.length == 2  # seeding POST + held PATCH; no additional request

held_patch.respond_with(200, parse_json(held_patch.body))

AWAIT first   # RSH3e2b
AWAIT second  # RSH3d1a — the dequeued CalledActivate resolves it from WaitingForNewPushDeviceDetails
```

### Assertions
```pseudo
# Exactly one sync PATCH: the queued CalledActivate was consumed by RSH3d1a, not by a second validation
patch_requests = captured_requests WHERE method == "PATCH"
ASSERT patch_requests.length == 1
ASSERT patch_requests[0].url.path == "/push/deviceRegistrations/" + encode_uri_component(device_id)

poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```
