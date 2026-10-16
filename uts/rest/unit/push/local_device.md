# LocalDevice Tests

Spec points: `RSH8`, `RSH8a`, `RSH8d`, `RSH8e`, `RSH8f`, `RSH8k`, `RSH8k1`, `RSH8k2`

## Test Type
Unit test with mocked HTTP client and mocked push platform

## Mock HTTP Infrastructure

See `uts/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

## Mock Push Platform Infrastructure

See `uts/rest/unit/helpers/mock_push_platform.md` for the portable push platform primitives (`PushKeyValueStorage`, `requestToken`, `PushPlatformConfig`), the standard `ably.push.*` storage keys, and the `MockPushStorage` mock.

## Notes

`RSH8` defines the `device` method on `RestClient`/`RealtimeClient`. SDKs whose push storage is asynchronous may expose this as an asynchronous accessor instead (ably-js's React Native plugin deprecates the synchronous `device()` in favour of `await getDevice()`). The pseudocode uses `AWAIT client.device()`; derived tests map this to whichever accessor the SDK exposes, and SDKs with synchronous storage simply drop the `AWAIT`.

These tests are **black-box**: they never construct state machine events or inspect machine state directly. State is observed through behaviour (which requests are made, which operations resolve or fail), through the returned `LocalDevice`, and, after operations settle, through the persisted `ably.push.*` keys.

Tests must not assert *when* `id`/`deviceSecret` are generated (see "Notes for Spec Authors" in `mock_push_platform.md`): some SDKs generate them eagerly on device load, others lazily per `RSH3a2b`. In particular, before any activation a test may only assert that `deviceIdentityToken` is null — not that `id`/`deviceSecret` are or aren't set.

The storage key under which the `LocalDevice` `clientId` is persisted is not standardised (the standard keys table in `mock_push_platform.md` deliberately has no entry for it). Tests therefore observe `RSH8d` persistence behaviourally — a fresh client over the same storage sees the `clientId` — rather than by inspecting a specific key.

Device authentication assertions follow `RSH6a` (`X-Ably-DeviceToken` header). An SDK using a different device-auth mechanism (e.g. an `Authorization` bearer header carrying the `deviceIdentityToken`) must record a deviation and adapt the assertion.

**Caveat for the RSH8d/RSH8e tests:** they depend on the client *becoming identified* after construction, per `RSA7b2`/`RSA7b3` (a token with a `clientId` is obtained by a previously unidentified client). SDKs that have not implemented this late-identification plumbing — the hook from auth into the `LocalDevice` and the Activation State Machine — must record a deviation and may skip the derived test.

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

# A client using token auth via authCallback, so that its identity can change
# after construction (RSA7b2/RSA7b3): the first token is anonymous, every later
# token is identified as "alice". No HTTP is involved — the callback returns
# TokenDetails directly (RSA8d).
FUNCTION late_identified_client(storage):
  auth_calls = 0
  install_push_platform(build_push_platform(storage))
  RETURN Rest(options: ClientOptions(
    authCallback: (tokenParams) => {
      auth_calls += 1
      IF auth_calls == 1:
        RETURN TokenDetails(token: "anon-token-1")
      RETURN TokenDetails(token: "alice-token-1", clientId: "alice")
    }
  ))
```

---

## RSH8, RSH8k1, RSH8k2 — the device accessor returns the activated LocalDevice

**Test ID**: `rest/unit/RSH8/device-returns-local-device-0`

| Spec | Requirement |
|------|-------------|
| RSH8 | The `device` method on the `RestClient` or `RealtimeClient` interfaces returns an instance of `LocalDevice` that represents the current state of the device in respect of it being a target for push notifications |
| RSH8k | `LocalDevice` has the attributes `deviceIdentityToken` and `deviceSecret` (with `id`, `platform`, `formFactor` and `push.recipient` inherited from `DeviceDetails`) |
| RSH8k1 | `deviceIdentityToken` string? — populated as described in RSH8c (set after successful registration) |
| RSH8k2 | `deviceSecret` string — populated as described in RSH8b |

Tests that after a full activation the device accessor reflects the registered device: identifiers, identity token, platform attributes and push recipient.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = AWAIT activate_into(mock_storage)
```

### Test Steps
```pseudo
device = AWAIT client.device()
```

### Assertions
```pseudo
persisted = mock_storage.dump()
ASSERT device.id == persisted["ably.push.deviceId"]
ASSERT device.deviceSecret IS NOT null                 # RSH8k2
ASSERT device.deviceIdentityToken == "ident-token-1"   # RSH8k1
ASSERT device.platform == "android"
ASSERT device.formFactor == "phone"
ASSERT device.push.recipient == {
  "transportType": "fcm",
  "registrationToken": "fcm-token-1"
}
```

---

## RSH8a — LocalDevice is populated from persisted state without any request

**Test ID**: `rest/unit/RSH8a/device-populated-from-persisted-state-0`

**Spec requirement:** RSH8a — The `LocalDevice` is initialised when first required, either as a result of a call to `RestClient#device` or `RealtimeClient#device`, or as a result of the Activation State Machine being initialised. The `id`, `clientId`, `deviceSecret` and `deviceIdentityToken` attributes are populated, together with any `recipient`-related attributes, to the extent that they exist, from the persisted state.

Tests that a fresh client over storage holding a registered device returns the same `LocalDevice` attributes, and that the device accessor itself is a pure load from persisted state — it makes no HTTP request.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
AWAIT activate_into(mock_storage)   # client1: register and persist
persisted = mock_storage.dump()
```

### Test Steps
```pseudo
# A fresh client over the same storage simulates an app restart
client2 = push_client(mock_storage)
requests_before = captured_requests.length
device = AWAIT client2.device()
```

### Assertions
```pseudo
ASSERT device.id == persisted["ably.push.deviceId"]
ASSERT device.deviceSecret == persisted["ably.push.deviceSecret"]
ASSERT device.deviceIdentityToken == "ident-token-1"
ASSERT device.push.recipient == {
  "transportType": "fcm",
  "registrationToken": "fcm-token-1"
}

# The device accessor made no HTTP request of its own
ASSERT captured_requests.length == requests_before
```

---

## RSH8k1 — deviceIdentityToken is null before registration

**Test ID**: `rest/unit/RSH8k1/device-identity-token-null-before-registration-0`

**Spec requirement:** RSH8k1 — `deviceIdentityToken` string? — populated as described in RSH8c, i.e. only following successful registration. Before any activation it is unset.

Tests that the device accessor on a never-activated client returns a `LocalDevice` with no `deviceIdentityToken`. The test deliberately asserts nothing about `id`/`deviceSecret`: whether they are already set at this point diverges between eager and lazy generation (see "Notes for Spec Authors" in `mock_push_platform.md`).

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = push_client(mock_storage)
```

### Test Steps
```pseudo
device = AWAIT client.device()
```

### Assertions
```pseudo
ASSERT device.deviceIdentityToken == null
# Deliberately no assertion on device.id / device.deviceSecret — see Notes
```

---

## RSH8f — clientId from the registration response is set on the LocalDevice

**Test ID**: `rest/unit/RSH8f/clientid-from-registration-response-0`

**Spec requirement:** RSH8f — If the `LocalDevice` is created by an unidentified client (see RSA7) and therefore has no `clientId` set, but on receipt of a registration response (see RSH3c2) the registered device has a non-empty `clientId`, then the `LocalDevice` `clientId` is set with that `clientId`.

Tests that when the server's registration response carries a `clientId` (e.g. one implied by the authenticating token), the unidentified client's `LocalDevice` adopts it.

### Setup
```pseudo
captured_requests = mock_registration_server(overrides: (req) => {
  IF req.method == "POST" AND req.url.path == "/push/deviceRegistrations":
    body = parse_json(req.body)
    req.respond_with(201, merge(body, {
      "deviceIdentityToken": {"token": "ident-token-1"},
      "clientId": "client-from-server"
    }))
    RETURN true
  RETURN false
})
mock_storage = MockPushStorage()
client = push_client(mock_storage)   # no clientId — unidentified (RSA7)
```

### Test Steps
```pseudo
AWAIT client.push.activate()
device = AWAIT client.device()
```

### Assertions
```pseudo
ASSERT device.clientId == "client-from-server"
```

---

## RSH8d — a clientId acquired after registration is set and persisted

**Test ID**: `rest/unit/RSH8d/late-clientid-persisted-0`

**Spec requirement:** RSH8d — If the `LocalDevice` is created by an unidentified client (see RSA7) and therefore has no `clientId` set, but the client subsequently becomes identified (as a result of RSA7b2 or RSA7b3), then the `LocalDevice` `clientId` is set and persisted.

An unidentified token-auth client activates; it then becomes identified by obtaining a token whose `clientId` is `"alice"` via `Auth#authorize`. The `LocalDevice` `clientId` must be set, and persisted — observed via a fresh client over the same storage (see Notes: the storage key for `clientId` is not standardised, so persistence is asserted behaviourally). See the Notes caveat: SDKs without late-identification plumbing must record a deviation and may skip the derived test.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = late_identified_client(mock_storage)
```

### Test Steps
```pseudo
AWAIT client.push.activate()
device = AWAIT client.device()
ASSERT device.deviceIdentityToken == "ident-token-1"
ASSERT device.clientId == null   # registered while unidentified

# The client becomes identified: the second token carries clientId "alice" (RSA7b2)
tokenDetails = AWAIT client.auth.authorize()
ASSERT tokenDetails.clientId == "alice"
```

### Assertions
```pseudo
# RSH8d — the LocalDevice clientId is set...
poll_until_success(() => (AWAIT client.device()).clientId == "alice")

# ...and persisted: a fresh client over the same storage sees it (polled,
# because persistence may settle asynchronously after the clientId is set)
device2 = poll_until_success(() => {
  d = AWAIT push_client(mock_storage).device()
  IF d.clientId == "alice":
    RETURN d
  RETURN null
})
ASSERT device2.id == device.id
ASSERT device2.clientId == "alice"
```

---

## RSH8e — a late clientId on a registered device triggers a registration sync

**Test ID**: `rest/unit/RSH8e/late-clientid-triggers-sync-0`

| Spec | Requirement |
|------|-------------|
| RSH8e | If the `LocalDevice` `clientId` becomes set as a result of RSH8d, and the `LocalDevice` is already registered (ie the `deviceIdentityToken` is set), and the ActivationStateMachine is in any state other than `NotActivated`, then a `GotPushDeviceDetails` event is sent to the state machine once the effects of RSH8d are visible, ie. once `LocalDevice` `clientId` is set |
| RSH3d3b | (In `WaitingForNewPushDeviceDetails`, on `GotPushDeviceDetails`) make an asynchronous PATCH HTTP request to `/push/deviceRegistrations/:deviceId` using the local `DeviceDetails`'s push details as body. This operation requires push device authentication |

Continuation of the RSH8d scenario: after activation the machine is in `WaitingForNewPushDeviceDetails` (not `NotActivated`) and the device is registered, so the `GotPushDeviceDetails` event fired when the `clientId` becomes set is observable as a registration sync — a PATCH to the device-specific path with push device authentication. See the Notes caveat: SDKs without late-identification plumbing must record a deviation and may skip the derived test.

### Setup
```pseudo
captured_requests = mock_registration_server()
mock_storage = MockPushStorage()
client = late_identified_client(mock_storage)
```

### Test Steps
```pseudo
AWAIT client.push.activate()   # registered; machine in WaitingForNewPushDeviceDetails
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
device_id = mock_storage.dump()["ably.push.deviceId"]

AWAIT client.auth.authorize()  # client becomes identified as "alice" (RSA7b2), RSH8d sets clientId

# RSH8e — GotPushDeviceDetails is sent once the clientId is set, observable
# as the RSH3d3b registration sync
patch = poll_until_success(() => {
  patches = captured_requests WHERE method == "PATCH"
  IF patches.length > 0:
    RETURN patches[0]
  RETURN null
})
```

### Assertions
```pseudo
ASSERT patch.url.path == "/push/deviceRegistrations/" + encode_uri_component(device_id)

# RSH3d3b + RSH6a — push device authentication
ASSERT patch.headers["X-Ably-DeviceToken"] == "ident-token-1"

# The sync completes and the machine settles back into WaitingForNewPushDeviceDetails
# (RSH3d3d -> WaitingForRegistrationSync, then RegistrationSynced -> RSH3e2a)
poll_until_success(() => mock_storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails")
```
