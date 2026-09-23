# Push Activation Persistence Tests

Spec points: `RSH3h`, `RSH3a2c`, `RSH8a`, `RSH8a1`, `RSH8b`, `RSH8c`

## Test Type
Unit test with mocked HTTP client and mocked push platform

## Mock HTTP Infrastructure

See `uts/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

## Mock Push Platform Infrastructure

See `uts/rest/unit/helpers/mock_push_platform.md` for the portable push platform primitives (`PushKeyValueStorage`, `requestToken`, `PushPlatformConfig`), the standard `ably.push.*` storage keys, and the `MockPushStorage` mock.

## Notes

These tests cover the persistence seam of push activation: what the SDK loads from storage on a fresh start (`RSH3h`, `RSH8a`, `RSH3a2c`), how it recovers from corrupt or partial persisted state (`RSH8a1`), how it behaves when persistence itself fails (`RSH8b`), and when the registration outcome is persisted (`RSH8c`).

These tests are **black-box**: they never construct state machine events or inspect machine state directly. Events are produced by driving the public API (`push.activate()`, `push.deactivate()`), by the mocked `requestToken`, and by responding to the mocked HTTP requests the machine issues. State is observed through behaviour (which requests are made, which operations resolve or fail) and, after operations settle, through the persisted `ably.push.activationState`.

Seeded storage simulates state persisted by a previous app run. Seeded values follow the persisted value representations in `mock_push_platform.md`: `deviceIdentityToken` is a JSON-encoded string, `pushRecipient` a JSON-encoded object, everything else a plain string.

To pin the machine in an intermediate state, tests hold a `PendingRequest` (capture it in the `onRequest` handler without responding) and release it later.

Tests must not assert *when* `id`/`deviceSecret` are generated (see "Notes for Spec Authors" in `mock_push_platform.md`): the `RSH8a1` test observes regeneration only through the registration request body, which is valid under both eager and lazy generation.

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
```

---

## RSH8a1, RSH3h — corrupt persisted device state discards all persisted state

**Test ID**: `rest/unit/RSH8a1/corrupt-device-state-discarded-0`

| Spec | Requirement |
|------|-------------|
| RSH8a1 | If loading the `LocalDevice` `id` or `deviceSecret` attributes fails, then: (1) all persisted `LocalDevice` attributes must be discarded; (2) all persisted Activation State Machine data must be discarded |
| RSH3h | (Combined with the above) this ensures that the state machine starts in `NotActivated` |

Storage is seeded with a `deviceId` but **no** `deviceSecret` — an incomplete pair, so the device load fails — plus a stale identity token and a machine state (`WaitingForNewPushDeviceDetails`) that, if honoured, would drive the `RSH3a2a` registration sync. Everything must instead be discarded: activation runs the full first-time registration (platform token request, then a POST — not a sync PATCH) with a freshly generated `id`, and the stale identity token is replaced by the newly registered one.

### Setup
```pseudo
token_requests = 0
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
mock_storage.seed({
  "ably.push.deviceId": "seeded-device-1",
  # deviceSecret missing — the id/secret pair is incomplete, so the device load must fail
  "ably.push.deviceIdentityToken": "\"stale-token\"",
  "ably.push.activationState": "WaitingForNewPushDeviceDetails"
})
client = push_client(mock_storage, requestToken: () => {
  token_requests += 1
  RETURN PushDeviceToken(transportType: "fcm", token: "fcm-token-1")
})
```

### Test Steps
```pseudo
AWAIT client.push.activate()
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

### Assertions
```pseudo
# Full first-time registration — not the registration sync the stale state would imply
ASSERT token_requests == 1
ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.url.path == "/push/deviceRegistrations"

# RSH8a1 (1) — the seeded device identity was discarded; a fresh id was generated
body = parse_json(request.body)
ASSERT body["id"] != "seeded-device-1"

# The stale identity token was discarded and replaced by the registration result
persisted = mock_storage.dump()
ASSERT persisted["ably.push.deviceId"] != "seeded-device-1"
ASSERT parse_json(persisted["ably.push.deviceIdentityToken"]) == "ident-token-1"
```

---

## RSH8a1, RSH3h — corrupt persisted machine state recovers without crashing

**Test ID**: `rest/unit/RSH8a1/corrupt-machine-state-recovers-1`

| Spec | Requirement |
|------|-------------|
| RSH3h | (2) the in-memory state machine is then constructed from the persisted Activation State Machine data, or starts in `NotActivated` if no such data is persisted |
| RSH8a1 | (Mirror scenario) here the device load *succeeds* — only the machine data is unusable, so the `LocalDevice` attributes must survive |

Storage is seeded with a complete, valid registered device but an unrecognisable machine state name. The machine cannot be constructed from this data; per `RSH3h` it must treat it as absent and fall back to `NotActivated` rather than crash. From `NotActivated`, `activate()` on a device that has a `deviceIdentityToken` behaves per `RSH3a2a`: a PATCH sync of the existing registration, resolving successfully.

**Note:** if an SDK instead discards *everything* on unparseable machine state (so `activate()` performs a full POST registration rather than the registration sync), record a deviation — the essential assertion is that activation completes without crashing.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
mock_storage.seed({
  "ably.push.deviceId": "seeded-device-1",
  "ably.push.deviceSecret": "seeded-secret",
  "ably.push.deviceIdentityToken": "\"seeded-ident-token\"",
  "ably.push.pushRecipient": "{\"transportType\":\"fcm\",\"registrationToken\":\"seeded-token-1\"}",
  "ably.push.activationState": "BogusStateName"
})
client = push_client(mock_storage)
```

### Test Steps and Assertions
```pseudo
# Must not crash: the machine falls back to NotActivated (RSH3h), where the
# registered device (it has a deviceIdentityToken) is validated per RSH3a2a
AWAIT client.push.activate()

ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.method == "PATCH"
ASSERT request.url.path == "/push/deviceRegistrations/" + encode_uri_component("seeded-device-1")
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

---

## RSH3a2c, RSH8a — persisted push details skip the platform token request

**Test ID**: `rest/unit/RSH3a2c/existing-push-details-skip-token-request-0`

| Spec | Requirement |
|------|-------------|
| RSH3a2c | If the local device has the necessary push details (registration token, etc.), sends a `GotPushDeviceDetails` event |
| RSH8a | The `LocalDevice` attributes are populated, together with any `recipient`-related attributes, to the extent that they exist, from the persisted state |

Storage is seeded with a valid device pair and a persisted push recipient, but no identity token (not yet registered, so `RSH3a2a` does not apply) and machine state `NotActivated`. On `activate()` the device already has the necessary push details, so `GotPushDeviceDetails` is sent **without consulting the platform**: `requestToken` must not be called, and the registration POST carries the persisted recipient. (Verified against ably-js: `NotActivated` checks the device's `push.recipient` before consulting the platform's token acquisition, so ably-js conforms.)

### Setup
```pseudo
token_requests = 0
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
mock_storage.seed({
  "ably.push.deviceId": "seeded-device-1",
  "ably.push.deviceSecret": "seeded-secret",
  # no deviceIdentityToken — the device is not yet registered
  "ably.push.pushRecipient": "{\"transportType\":\"fcm\",\"registrationToken\":\"persisted-token-1\"}",
  "ably.push.activationState": "NotActivated"
})
client = push_client(mock_storage, requestToken: () => {
  token_requests += 1
  RETURN PushDeviceToken(transportType: "fcm", token: "unexpected-token")
})
```

### Test Steps
```pseudo
AWAIT client.push.activate()
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

### Assertions
```pseudo
# RSH3a2c — the platform was not consulted
ASSERT token_requests == 0

ASSERT captured_requests.length == 1
request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.url.path == "/push/deviceRegistrations"

body = parse_json(request.body)
# RSH3a2b — id and deviceSecret already exist, so they are not regenerated
ASSERT body["id"] == "seeded-device-1"
# RSH8a — the recipient came from persisted state
ASSERT body["push"]["recipient"] == {
  "transportType": "fcm",
  "registrationToken": "persisted-token-1"
}
```

---

## RSH8b — a persistence failure fails activate; activation recovers once it clears

**Test ID**: `rest/unit/RSH8b/persist-failure-fails-activate-then-recovers-0`

**Spec requirement:** RSH8b — The `LocalDevice` `id` and `deviceSecret` attributes are generated, **and persisted** as part of the `LocalDevice` state. Persistence is integral to the generation step: if the generated identifiers cannot be persisted, activation must fail — before any network request — and a later `activate()` on the same client must be able to succeed once storage works again (the failed device load must not be cached).

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
mock_storage.fail_writes = true
client = push_client(mock_storage)
```

### Test Steps and Assertions
```pseudo
# The generated identifiers cannot be persisted: activation fails, no HTTP request
AWAIT client.push.activate() FAILS WITH error
ASSERT captured_requests.length == 0

# Once storage works again, the SAME client can activate: the failed device
# load must not be cached
mock_storage.fail_writes = false
AWAIT client.push.activate()

ASSERT captured_requests.length == 1
ASSERT captured_requests[0].method == "POST"
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```

---

## RSH8c — deviceIdentityToken is persisted only after successful registration

**Test ID**: `rest/unit/RSH8c/identity-token-persisted-only-after-registration-0`

**Spec requirement:** RSH8c — Following successful registration of a `LocalDevice`, following the procedure in RSH3c2a, the now known `deviceIdentityToken` is set and persisted. It therefore must not appear in storage while the registration request is still in flight.

The registration POST is held open (captured without responding). While held, storage must contain no `ably.push.deviceIdentityToken`; after the response is released and the writes settle, the returned token is persisted.

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
activation = client.push.activate()
poll_until_success(() => held_post != null)

# Registration in flight: the identity token must not be persisted yet
ASSERT "ably.push.deviceIdentityToken" NOT IN mock_storage.dump()

held_post.respond_with(201, merge(parse_json(held_post.body), {"deviceIdentityToken": {"token": "ident-token-1"}}))
AWAIT activation
```

### Assertions
```pseudo
# After activate resolves and the fire-and-forget writes settle
poll_until_success(() => mock_storage.dump()["ably.push.deviceIdentityToken"] != null)
ASSERT parse_json(mock_storage.dump()["ably.push.deviceIdentityToken"]) == "ident-token-1"
```

---

## RSH3h — with no persisted state the machine starts in NotActivated

**Test ID**: `rest/unit/RSH3h/no-persisted-state-starts-not-activated-0`

| Spec | Requirement |
|------|-------------|
| RSH3h | (2) the in-memory state machine is then constructed from the persisted Activation State Machine data, or starts in `NotActivated` if no such data is persisted |
| RSH3a1d | (In `NotActivated`, on `CalledDeactivate`, no `deviceIdentityToken`) does the same as RSH3g2: `deactivate()` resolves with no error |

Anchors `RSH3h` clause (2) over completely empty storage: the initial state is `NotActivated`, so `deactivate()` resolves immediately with no requests, and `activate()` then runs the full first-time registration flow.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = push_client(mock_storage)
```

### Test Steps and Assertions
```pseudo
# NotActivated is the initial state: deactivate resolves immediately (RSH3a1d)
AWAIT client.push.deactivate()
ASSERT captured_requests.length == 0

# and activate runs the full first-time registration flow from NotActivated
AWAIT client.push.activate()
ASSERT captured_requests.length == 1
ASSERT captured_requests[0].method == "POST"
ASSERT captured_requests[0].url.path == "/push/deviceRegistrations"
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```
