# Push Activation Proxy Integration Tests

Spec points: `RSH3a2c`, `RSH3c3a`, `RSH3d2c1`, `RSH3e3d`, `RSH3f1`, `RSH3g2a`, `RSH3g3b`, `RSH4`

## Test Type

Proxy integration test — Ably sandbox via uts-proxy

## Proxy Infrastructure

See `uts/docs/proxy.md` for the full proxy infrastructure specification.

## Corresponding Unit Tests

- `uts/rest/unit/push/push_activation_state_machine.md` — `rest/unit/RSH3c3a/registration-failure-0`, `rest/unit/RSH3d2c1/deregister-401-succeeds-0`, `rest/unit/RSH3d2c1/deregister-40005-succeeds-1`, `rest/unit/RSH3g3b/deregister-failure-rollback-0` (mocked HTTP verifies the client-side classification and state transitions)
- `uts/rest/unit/push/push_activation_event_queue.md` — `rest/unit/RSH4/activate-queued-during-deregistration-0`, `rest/unit/RSH5/back-to-back-activate-deactivate-ordered-0` (mocked HTTP verifies event queueing and sequential handling)
- `uts/rest/unit/push/push_update_token.md` — `rest/unit/RSH3e3d/update-token-sync-failure-callback-4` (mocked HTTP verifies the fire-and-forget sync failure path)
- `uts/rest/unit/helpers/mock_push_platform.md` — the portable push platform primitives, `ably.push.*` storage keys, and `MockPushStorage`

## Purpose

The unit tier fully verifies the Activation State Machine's transitions with
mocked HTTP. What it cannot verify is that the SDK's error classification and
retry behaviour hold up against real HTTP framing, real status lines, and a
real server on the other side of the faulted requests. These tests run the
activation flows against the Ably sandbox through the proxy, injecting faults
on the registration endpoints, and add one assertion the unit tier cannot
make: a **direct** admin client (bypassing the proxy) inspects the server-side
registration, so a test can prove that a faulted DELETE never reached the
server — i.e. that the RSH3d2c1 classification of 401/40005 as `Deregistered`
is purely client-side.

Only the network is real. As in the unit tier, tests use `MockPushStorage`
and `install_push_platform` — a real platform push service is neither
available nor needed.

## Notes

### Pre-seeded ablyChannel recipient (RSH3a2c)

Tests pre-seed `ably.push.pushRecipient` in storage with an `ablyChannel`
recipient before creating the client:

```json
{
  "transportType": "ablyChannel",
  "channel": "<unique channel name>",
  "ablyKey": "<api key>",
  "ablyUrl": "<direct sandbox REST url>"
}
```

Per `RSH3a2c`, a local device that already has push details fires
`GotPushDeviceDetails` directly on `CalledActivate` — so `requestToken` is
never called, and no fake FCM/APNs token has to survive server-side recipient
validation. The `ablyUrl` MUST be the **direct** sandbox URL, not the proxy:
it is consumed server-side (the server publishes notifications to that URL),
so a proxy address would be meaningless outside the test host.

### Token auth through the proxy

The proxy serves plain HTTP (`tls: false`), and Basic auth is prohibited over
an insecure connection (RSA1). As in `rest_fallback.md`, clients therefore
authenticate via an `authCallback` whose inner client talks **directly** to
the sandbox (never through the proxy), so token requests are never
intercepted by fault-injection rules.

### Fault injection style

Deregistration and sync tests inject their faults **late** (rules added only
after a fully real activation through the proxy), per the guidance in
`uts/docs/integration-testing.md`. The `http_respond` action synthesises the
response without forwarding the request (Approach B) — here that is not a
compromise but the point: because the faulted request never reaches the
server, the direct admin client can prove the classification happened
client-side. The registration-failure and delay tests need their rule at
session creation, since the fault targets the first registration POST itself;
in each case every subsequent interaction passes through to the real server.

### Timeouts

All `WITH timeout` and `poll_until` durations are **wall-clock (real) time**
(see `uts/docs/proxy.md` convention 11). Timeouts are generous because a real
network and sandbox are involved.

### ably-js deviation (RSH3e3d)

`RSH3e3d` routes sync failures to the `updatedCallback` provided to
`Push#activate`. ably-js currently delivers them to the deprecated
`updateFailedCallback` (`RSH3e3a`) instead; derived ably-js tests must adapt
the callback assertion in `sync-failure-recovery-0` accordingly (see the
Notes of `uts/rest/unit/push/push_update_token.md`).

## Sandbox Setup

Tests run against the Ably Sandbox via a programmable proxy.

### App Provisioning

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox.realtime.ably-nonprod.net/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox.realtime.ably-nonprod.net/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

App deletion removes any device registrations a test left behind; per-test
cleanup of server-side registrations is best-effort only.

### Common Cleanup

```pseudo
AFTER EACH TEST:
  IF session IS NOT null:
    session.close()
  uninstall_push_platform()
```

### Shared Helpers

```pseudo
SANDBOX_URL = "https://sandbox.realtime.ably-nonprod.net"

FUNCTION token_auth_callback(api_key):
  RETURN (params, cb) => {
    # A temporary Rest client pointed directly at the sandbox (bypassing the
    # proxy) obtains a TokenDetails object; token requests are never
    # intercepted by proxy fault-injection rules.
    inner_rest = Rest(options: ClientOptions(
      key: api_key,
      endpoint: SANDBOX_URL
    ))
    inner_rest.auth.requestToken().then(
      (token) => cb(null, token),
      (err) => cb(err, null)
    )
  }

# The server-consumable recipient pre-seeded into storage (see Notes).
# ablyUrl is the DIRECT sandbox URL — never the proxy.
FUNCTION ably_channel_recipient(channel_name):
  RETURN {
    "transportType": "ablyChannel",
    "channel": channel_name,
    "ablyKey": api_key,
    "ablyUrl": SANDBOX_URL
  }

# A push client routed through the proxy, over a fresh MockPushStorage
# pre-seeded with an ablyChannel recipient so that requestToken is never
# called (RSH3a2c). Each test creates its own storage and channel name.
FUNCTION proxy_push_client(session, storage, channel_name):
  storage.seed({
    "ably.push.pushRecipient": json_encode(ably_channel_recipient(channel_name))
  })
  install_push_platform(MockPushPlatform(
    platform: "android",
    formFactor: "phone",
    storage: storage,
    requestToken: () => RAISE Error("requestToken must not be called — recipient pre-seeded (RSH3a2c)")
  ))
  RETURN Rest(options: ClientOptions(
    authCallback: token_auth_callback(api_key),
    endpoint: "localhost",       # REC2c2: auto-disables fallback hosts
    port: session.proxy_port,
    tls: false,
    useBinaryProtocol: false
  ))

# An admin client that bypasses the proxy entirely — the source of
# server-side ground truth for these tests.
FUNCTION direct_admin_client():
  RETURN Rest(options: ClientOptions(
    key: api_key,
    endpoint: SANDBOX_URL,
    useBinaryProtocol: false
  ))

# Runs a fully real activation through the proxy (no rules firing) and
# returns the registered device id.
FUNCTION activate_through_proxy(client, storage):
  AWAIT client.push.activate() WITH timeout 15s
  poll_until_success(() => storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails", timeout: 10s)
  RETURN storage.dump()["ably.push.deviceId"]
```

---

## RSH3d2c1 — deregistration 401 is classified as Deregistered without the DELETE reaching the server

**Test ID**: `rest/proxy/RSH3d2c1/deregister-401-classified-0`

**Corresponding unit test**: `rest/unit/RSH3d2c1/deregister-401-succeeds-0` (`push_activation_state_machine.md`)

| Spec | Requirement |
|------|-------------|
| RSH3d2c1 | `Deregistered` should be fired if the DELETE returns a 2xx status, 401 (unauthorized), or error code 40005 (invalid credentials) |
| RSH3g2a | On `Deregistered`, clears all local `DeviceDetails` |

A fully real activation registers the device through the proxy. The proxy
then answers the deregistration DELETE with a synthetic 401 (real HTTP
framing and status line) **without forwarding it**. `deactivate()` must
resolve and clear local state — and, the assertion the unit tier cannot make:
the server-side registration still exists, proving the DELETE never reached
the server and the 401→`Deregistered` classification is client-side.

### Setup

```pseudo
session = create_proxy_session(endpoint: "nonprod:sandbox")

channel_name = "push-proxy-RSH3d2c1-401-" + random_string()
storage = MockPushStorage()
client = proxy_push_client(session, storage, channel_name)
admin = direct_admin_client()

# Real registration through the proxy
device_id = AWAIT activate_through_proxy(client, storage)

# Server-side ground truth: the registration exists
registered = AWAIT admin.push.admin.deviceRegistrations.get(device_id)
ASSERT registered.id == device_id

# Late fault injection: only the deregistration DELETE is faulted
session.add_rules([{
  "match": { "type": "http_request", "method": "DELETE", "pathContains": "/push/deviceRegistrations" },
  "action": {
    "type": "http_respond",
    "status": 401,
    "body": { "error": { "message": "unauthorized", "code": 40100, "statusCode": 401 } }
  },
  "times": 1,
  "comment": "RSH3d2c1: answer the deregistration DELETE with 401 without forwarding it"
}])
```

### Test Steps

```pseudo
# Resolves despite the 401 — classified as Deregistered
AWAIT client.push.deactivate() WITH timeout 15s
poll_until_success(() => storage.dump()["ably.push.activationState"] == "NotActivated", timeout: 10s)
```

### Assertions

```pseudo
# RSH3g2a — local state cleared
persisted = storage.dump()
ASSERT "ably.push.deviceIdentityToken" NOT IN persisted
ASSERT "ably.push.pushRecipient" NOT IN persisted

# The DELETE never reached the server: the registration STILL exists.
# The 401 → Deregistered classification is purely client-side.
still_registered = AWAIT admin.push.admin.deviceRegistrations.get(device_id)
ASSERT still_registered.id == device_id

# The proxy log confirms exactly one DELETE was issued (and answered by the rule)
log = session.get_log()
deletes = log.filter(e => e.type == "http_request" AND e.method == "DELETE" AND e.path CONTAINS "/push/deviceRegistrations")
ASSERT deletes.length == 1

# Best-effort cleanup of the orphaned server-side registration
AWAIT admin.push.admin.deviceRegistrations.remove(device_id)  # ignore errors
```

---

## RSH3d2c1 — deregistration error code 40005 is classified as Deregistered without the DELETE reaching the server

**Test ID**: `rest/proxy/RSH3d2c1/deregister-40005-classified-1`

**Corresponding unit test**: `rest/unit/RSH3d2c1/deregister-40005-succeeds-1` (`push_activation_state_machine.md`)

| Spec | Requirement |
|------|-------------|
| RSH3d2c1 | Error code 40005 (invalid credentials) is classified as `Deregistered` |
| RSH3g2a | On `Deregistered`, clears all local `DeviceDetails` |

As `deregister-401-classified-0`, but the injected fault is an HTTP 400 whose
body carries error code 40005 — exercising the body-code (rather than
status-code) branch of the classification against a real HTTP response.

### Setup

```pseudo
session = create_proxy_session(endpoint: "nonprod:sandbox")

channel_name = "push-proxy-RSH3d2c1-40005-" + random_string()
storage = MockPushStorage()
client = proxy_push_client(session, storage, channel_name)
admin = direct_admin_client()

device_id = AWAIT activate_through_proxy(client, storage)

session.add_rules([{
  "match": { "type": "http_request", "method": "DELETE", "pathContains": "/push/deviceRegistrations" },
  "action": {
    "type": "http_respond",
    "status": 400,
    "body": { "error": { "message": "invalid credentials", "code": 40005, "statusCode": 400 } }
  },
  "times": 1,
  "comment": "RSH3d2c1: answer the deregistration DELETE with 400/40005 without forwarding it"
}])
```

### Test Steps

```pseudo
# Resolves despite the 40005 — classified as Deregistered
AWAIT client.push.deactivate() WITH timeout 15s
poll_until_success(() => storage.dump()["ably.push.activationState"] == "NotActivated", timeout: 10s)
```

### Assertions

```pseudo
# RSH3g2a — local state cleared
persisted = storage.dump()
ASSERT "ably.push.deviceIdentityToken" NOT IN persisted
ASSERT "ably.push.pushRecipient" NOT IN persisted

# The DELETE never reached the server: the registration STILL exists
still_registered = AWAIT admin.push.admin.deviceRegistrations.get(device_id)
ASSERT still_registered.id == device_id

# Best-effort cleanup of the orphaned server-side registration
AWAIT admin.push.admin.deviceRegistrations.remove(device_id)  # ignore errors
```

---

## RSH3d2c1, RSH3g3b — deregistration failure fails deactivate and rolls back; the retry deregisters end-to-end

**Test ID**: `rest/proxy/RSH3d2c1/deregister-failure-rollback-2`

**Corresponding unit test**: `rest/unit/RSH3g3b/deregister-failure-rollback-0` (`push_activation_state_machine.md`)

| Spec | Requirement |
|------|-------------|
| RSH3d2c1 | Status codes other than 2xx/401/40005 fire `DeregistrationFailed` (40198 — a non-retriable 4xx, per the unit spec's convention) |
| RSH3g3a | Makes `Push#deactivate` return with the error |
| RSH3g3b | Transitions to the previous state (`WaitingForNewPushDeviceDetails` here) |

The first DELETE is answered with a synthetic 400/40198 (`times: 1`, not
forwarded), so `deactivate()` fails and the machine rolls back — verified
both locally (identity token survives) and server-side (registration still
exists). The rule is then consumed, so a second `deactivate()` runs
end-to-end against the real server: local state cleared AND the server-side
registration gone.

### Setup

```pseudo
session = create_proxy_session(endpoint: "nonprod:sandbox")

channel_name = "push-proxy-RSH3g3b-rollback-" + random_string()
storage = MockPushStorage()
client = proxy_push_client(session, storage, channel_name)
admin = direct_admin_client()

device_id = AWAIT activate_through_proxy(client, storage)

session.add_rules([{
  "match": { "type": "http_request", "method": "DELETE", "pathContains": "/push/deviceRegistrations" },
  "action": {
    "type": "http_respond",
    "status": 400,
    "body": { "error": { "message": "deregistration rejected", "code": 40198, "statusCode": 400 } }
  },
  "times": 1,
  "comment": "RSH3g3b: fail only the first deregistration DELETE with a non-retriable 400/40198"
}])
```

### Test Steps and Assertions

```pseudo
AWAIT client.push.deactivate() WITH timeout 15s FAILS WITH error
ASSERT error.code == 40198

# RSH3g3b — still registered locally: the identity token survives the rollback
ASSERT storage.dump()["ably.push.deviceIdentityToken"] IS NOT null

# ... and server-side: the faulted DELETE was never forwarded
still_registered = AWAIT admin.push.admin.deviceRegistrations.get(device_id)
ASSERT still_registered.id == device_id

# The rule is consumed — the retry deregisters end-to-end against the real server
AWAIT client.push.deactivate() WITH timeout 15s
poll_until_success(() => storage.dump()["ably.push.activationState"] == "NotActivated", timeout: 10s)

persisted = storage.dump()
ASSERT "ably.push.deviceIdentityToken" NOT IN persisted
ASSERT "ably.push.pushRecipient" NOT IN persisted

# Server-side registration is gone
AWAIT admin.push.admin.deviceRegistrations.get(device_id) FAILS WITH error
ASSERT error.statusCode == 404

# Two DELETEs were issued: the faulted one and the real one
log = session.get_log()
deletes = log.filter(e => e.type == "http_request" AND e.method == "DELETE" AND e.path CONTAINS "/push/deviceRegistrations")
ASSERT deletes.length == 2
```

---

## RSH3c3a — registration failure fails activate; the retry registers against the real server

**Test ID**: `rest/proxy/RSH3c3a/registration-failure-then-retry-0`

**Corresponding unit test**: `rest/unit/RSH3c3a/registration-failure-0` (`push_activation_state_machine.md`)

| Spec | Requirement |
|------|-------------|
| RSH3c3a | On `GettingDeviceRegistrationFailed`, makes `Push#activate` return with the error |
| RSH3c3b | Transitions to `NotActivated` |

The first registration POST is answered with a synthetic 500/50000
(`times: 1`), so `activate()` fails and the machine returns to
`NotActivated`. This is necessarily early fault injection — the fault under
test is the registration itself — but the retry then runs fully real, and a
direct admin get confirms the registration exists server-side.
`endpoint: "localhost"` disables fallback hosts (REC2c2) and none are
configured, so the 500 produces exactly one POST attempt.

### Setup

```pseudo
session = create_proxy_session(
  endpoint: "nonprod:sandbox",

  rules: [{
    "match": { "type": "http_request", "method": "POST", "pathContains": "/push/deviceRegistrations" },
    "action": {
      "type": "http_respond",
      "status": 500,
      "body": { "error": { "message": "internal error", "code": 50000, "statusCode": 500 } }
    },
    "times": 1,
    "comment": "RSH3c3a: fail only the first registration POST with a synthetic 500/50000"
  }]
)

channel_name = "push-proxy-RSH3c3a-retry-" + random_string()
storage = MockPushStorage()
client = proxy_push_client(session, storage, channel_name)
admin = direct_admin_client()
```

### Test Steps and Assertions

```pseudo
AWAIT client.push.activate() WITH timeout 15s FAILS WITH error
ASSERT error.code == 50000
poll_until_success(() => storage.dump()["ably.push.activationState"] == "NotActivated", timeout: 10s)

# RSH3c3b — from NotActivated the retry runs the full flow against the real server
AWAIT client.push.activate() WITH timeout 15s
poll_until_success(() => storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails", timeout: 10s)
device_id = storage.dump()["ably.push.deviceId"]

# Server-side ground truth: the retry's registration reached the real server
registered = AWAIT admin.push.admin.deviceRegistrations.get(device_id)
ASSERT registered.id == device_id

# Two POSTs were issued: the faulted one and the real one
log = session.get_log()
posts = log.filter(e => e.type == "http_request" AND e.method == "POST" AND e.path CONTAINS "/push/deviceRegistrations")
ASSERT posts.length == 2
```

---

## RSH4 — deactivate issued during an in-flight registration is queued, then deregisters after activation completes

**Test ID**: `rest/proxy/RSH4/deactivate-queued-behind-slow-registration-0`

**Corresponding unit tests**: `rest/unit/RSH4/activate-queued-during-deregistration-0`, `rest/unit/RSH5/back-to-back-activate-deactivate-ordered-0` (`push_activation_event_queue.md`)

| Spec | Requirement |
|------|-------------|
| RSH4 | An event with no transition defined in the current state is queued, and dequeued after the next transition |
| RSH3c2b | `GotDeviceRegistration` makes `Push#activate` return with no error |
| RSH3d2 | The dequeued `CalledDeactivate` (consumed in `WaitingForNewPushDeviceDetails`) deregisters the device |

The proxy holds the registration POST for 2 seconds (well under the default
`httpRequestTimeout`, so no timeout fires). Because the recipient is
pre-seeded (RSH3a2c), `activate()` passes straight through to
`WaitingForDeviceRegistration` with the POST in flight — and
`CalledDeactivate` has **no** defined transition there (contrast the RSH5
unit test, where it arrives in `WaitingForPushDeviceDetails` and RSH3b2
resolves it immediately with no registration). Per RSH4 it queues: the
activation resolves first when the delayed registration completes, then the
dequeued `CalledDeactivate` deregisters against the real server. The proxy
event log verifies the wire sequence: POST, then DELETE.

### Setup

```pseudo
session = create_proxy_session(
  endpoint: "nonprod:sandbox",

  rules: [{
    "match": { "type": "http_request", "method": "POST", "pathContains": "/push/deviceRegistrations" },
    "action": { "type": "http_delay", "delayMs": 2000 },
    "times": 1,
    "comment": "RSH4: hold the registration POST for 2s so CalledDeactivate arrives in WaitingForDeviceRegistration"
  }]
)

channel_name = "push-proxy-RSH4-queued-" + random_string()
storage = MockPushStorage()
client = proxy_push_client(session, storage, channel_name)
admin = direct_admin_client()
```

### Test Steps

```pseudo
resolution_order = []
activation = client.push.activate().then(() => resolution_order.append("activate"))

# Wait until the registration POST is in flight (visible in the proxy event
# log while the http_delay holds it)
poll_until(() => session.get_log()
  .filter(e => e.type == "http_request" AND e.method == "POST" AND e.path CONTAINS "/push/deviceRegistrations")
  .length == 1,
  timeout: 10s)

# The id is generated and persisted (RSH3a2b/RSH8b) before the POST is issued,
# so it is stable now. Capture it here: deregistration clears the local
# DeviceDetails (RSH3g2a) and resets the identity so the deregistered id is
# not reused — see the RSH4 worked-example unit test, which asserts a NEW id
# on re-activation.
device_id = storage.dump()["ably.push.deviceId"]

# CalledDeactivate: no transition defined in WaitingForDeviceRegistration → queued (RSH4)
deactivation = client.push.deactivate().then(() => resolution_order.append("deactivate"))

AWAIT activation WITH timeout 15s     # registration completes; activate resolves first (RSH3c2b)
AWAIT deactivation WITH timeout 15s   # dequeued CalledDeactivate → RSH3d2 deregistration
```

### Assertions

```pseudo
# Activation resolved before deactivation
ASSERT resolution_order == ["activate", "deactivate"]

poll_until_success(() => storage.dump()["ably.push.activationState"] == "NotActivated", timeout: 10s)
persisted = storage.dump()
ASSERT "ably.push.deviceIdentityToken" NOT IN persisted
ASSERT "ably.push.pushRecipient" NOT IN persisted

# Server-side: the registration was created, then removed
AWAIT admin.push.admin.deviceRegistrations.get(device_id) FAILS WITH error
ASSERT error.statusCode == 404

# Wire sequence: the registration POST strictly precedes the deregistration DELETE
log = session.get_log()
reg_requests = log.filter(e => e.type == "http_request" AND e.path CONTAINS "/push/deviceRegistrations")
ASSERT reg_requests.length == 2
ASSERT reg_requests[0].method == "POST"
ASSERT reg_requests[1].method == "DELETE"
```

---

## RSH3e3d, RSH3f1 — a failed registration sync is reported via updatedCallback; the next update syncs against the real server

**Test ID**: `rest/proxy/RSH3e3d/sync-failure-recovery-0`

**Corresponding unit test**: `rest/unit/RSH3e3d/update-token-sync-failure-callback-4` (`push_update_token.md`)

| Spec | Requirement |
|------|-------------|
| RSH3e3d | On `SyncRegistrationFailed` (not entered via `CalledActivate`), calls the `updatedCallback` provided to `Push#activate` with the error |
| RSH3e3b | Transitions to `AfterRegistrationSyncFailed` |
| RSH3f1 | In `AfterRegistrationSyncFailed`, `GotPushDeviceDetails` does the same as RSH3a2a (the RSH3d3b PATCH sync) |

An activated device receives a rotated token via `updateToken`. The proxy
fails the resulting sync PATCH with a synthetic 400/40199 (`times: 1`): the
fire-and-forget sync's failure must surface through the `updatedCallback`
(never through `updateToken`'s return value), leaving the machine in
`AfterRegistrationSyncFailed`. A second `updateToken` then finds the rule
consumed and syncs end-to-end — verified by polling the direct admin get
until the server-side recipient reflects the new token.

**Known server issue (fixed, pending deploy)**: the second (real) sync PATCH
targets a device whose stored recipient is `ablyChannel`, which a server bug
rejected with 400 `unknown transport type 'ablyChannel'` — fixed by
[ably/realtime#8591](https://github.com/ably/realtime/pull/8591); derived
tests should be skipped with a reason referencing that PR until it is
deployed to the sandbox, then unskipped. Note the rotated token is
necessarily `fcm` (RSH2f1 accepts only fcm/apns), so the successful re-sync
replaces the recipient cross-transport. See also the ably-js
`updatedCallback` deviation in the Notes above.

### Setup

```pseudo
session = create_proxy_session(endpoint: "nonprod:sandbox")

channel_name = "push-proxy-RSH3e3d-sync-" + random_string()
storage = MockPushStorage()
client = proxy_push_client(session, storage, channel_name)
admin = direct_admin_client()

updated_results = []
AWAIT client.push.activate(updatedCallback: (err) => updated_results.append(err)) WITH timeout 15s
poll_until_success(() => storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails", timeout: 10s)
device_id = storage.dump()["ably.push.deviceId"]

# Late fault injection: fail only the first sync PATCH
session.add_rules([{
  "match": { "type": "http_request", "method": "PATCH", "pathContains": "/push/deviceRegistrations" },
  "action": {
    "type": "http_respond",
    "status": 400,
    "body": { "error": { "message": "sync rejected", "code": 40199, "statusCode": 400 } }
  },
  "times": 1,
  "comment": "RSH3e3d: fail only the first token-rotation sync PATCH with 400/40199"
}])
```

### Test Steps and Assertions

```pseudo
# updateToken resolves (the sync is fire-and-forget) ...
AWAIT client.push.updateToken(PushDeviceToken(transportType: "fcm", token: "proxy-fcm-token-2")) WITH timeout 10s

# ... and the sync failure surfaces via the updatedCallback (RSH3e3d)
poll_until(() => updated_results.length == 1, timeout: 10s)
ASSERT updated_results[0] IS NOT null
ASSERT updated_results[0].code == 40199
poll_until_success(() => storage.dump()["ably.push.activationState"] == "AfterRegistrationSyncFailed", timeout: 10s)

# RSH3f1 — the next GotPushDeviceDetails re-runs the sync; the rule is
# consumed, so the PATCH reaches the real server
AWAIT client.push.updateToken(PushDeviceToken(transportType: "fcm", token: "proxy-fcm-token-3")) WITH timeout 10s

# Server-side ground truth: poll the direct admin get until the recipient
# reflects the new token
poll_until(() => {
  device = AWAIT admin.push.admin.deviceRegistrations.get(device_id)
  RETURN device.push.recipient["transportType"] == "fcm"
     AND device.push.recipient["registrationToken"] == "proxy-fcm-token-3"
}, timeout: 15s)

poll_until_success(() => storage.dump()["ably.push.activationState"] == "WaitingForNewPushDeviceDetails", timeout: 10s)

# Two PATCHes were issued: the faulted one and the real one
log = session.get_log()
patches = log.filter(e => e.type == "http_request" AND e.method == "PATCH" AND e.path CONTAINS "/push/deviceRegistrations")
ASSERT patches.length == 2
```
