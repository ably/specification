# Mock Push Platform Infrastructure

This document specifies the mock push platform infrastructure for push activation unit tests, and — because no prior portable definition exists — the portable **push platform primitives interface** that the mocks stand in for. All unit tests for the Activation State Machine (`RSH3`), `LocalDevice` (`RSH8`), and platform push operations (`RSH2`) should reference this document.

## Purpose

Push activation requires two platform capabilities that the core SDK cannot provide itself:

1. **Persistent key/value storage** — the Activation State Machine and `LocalDevice` outlive the client instance and the process (`RSH3`), so their state must be persisted (`RSH8a`, `RSH8b`, `RSH8c`) and recovered on restart (`RSH3h`).
2. **Push transport token acquisition** — obtaining the platform's registration/device token (e.g. an FCM registration token or APNs device token) that becomes the `push.recipient` of the registered `DeviceDetails`.

The mock infrastructure enables unit testing of the activation flow without a real platform:

1. **In-memory storage** — inspect exactly what was persisted, seed pre-existing state to simulate an app restart, and inject storage failures
2. **Stubbed token acquisition** — return a configured token, or fail, without any platform push service

## Portable Platform Primitives Interface

This interface describes what a push platform must *provide* to the SDK; it deliberately does not prescribe how the SDK obtains it (see Installation Mechanism below). The shape matches ably-js's `ably/react-native-push` plugin, where the application supplies it; in other SDKs the same primitives may be sourced internally by the SDK (e.g. ably-java's `ActivationContext` reads Android `SharedPreferences`).

```pseudo
# Persistent string key/value storage supplied by the application or platform
# adapter. All methods are asynchronous (every real backend — AsyncStorage,
# SharedPreferences, Keychain, a file — is asynchronous or should be treated
# as such). An SDK may additionally support a synchronous storage variant as
# a platform-specific extension; that is outside the scope of these specs.
interface PushKeyValueStorage:
  getItem(key: String): Future<String | null>
  setItem(key: String, value: String): Future<void>
  removeItem(key: String): Future<void>

# A push transport token, tagged with its transport so the SDK can build the
# correct push recipient (PDT1-PDT4).
class PushDeviceToken:
  transportType: String   # "fcm" | "apns" | "web" (PDT2)
  token: String           # (PDT3)
  apnsTokenType: String?  # apns only: token slot per PCP3a — "default" (the
                          # default when absent) | "location" | "pushToStart";
                          # slot names are extensible (PDT4)

# Token acquisition. Called by the SDK whenever it needs the current push
# transport token (RSH3a2d). Requesting user notification permission
# beforehand is the application's responsibility, not the SDK's: platform
# tokens are generally obtainable without notification permission, which
# only gates displaying notifications.
requestToken: () => Future<PushDeviceToken>
```

The token-to-recipient mapping is:

| `transportType` | Recipient |
|---|---|
| `fcm` | `{ "transportType": "fcm", "registrationToken": <token> }` |
| `apns` (default slot) | `{ "transportType": "apns", "deviceToken": <token> }` |
| `apns` (variant slot, per `PCP3a`) | `{ "transportType": "apns", ..., "apnsDeviceTokens": { <apnsTokenType>: <token>, ... } }` — the slot map accumulates alongside any existing `deviceToken`; registering a variant must not discard other registered variants (`RSH8l2`) |
| `web` | web push recipients are constructed by the SDK's own web-platform flow (service worker + VAPID subscription), which is browser-specific and out of scope for these portable specs |

**Token rotation and variant registration** are delivered by the application calling `push.updateToken(token: PushDeviceToken)` (`RSH2f`; see `push_update_token.md`); the primitives interface deliberately has no callback/stream for rotation. Note the token-variant spec points (`RSH2f`, `RSH8l`, `PCP3a`, `PDT1`–`PDT4`) are part of the pending token-variants spec extension; they are drafted in `specifications/features.md` but not yet merged upstream.

### Push platform configuration

A client is configured with a push platform as a single object carrying the primitives plus the device attributes needed for registration:

```pseudo
PushPlatformConfig:
  platform: String       # "android" | "ios" | "browser" (PCD6)
  formFactor: String     # "phone" | "tablet" | "desktop" | ... (PCD4)
  storage: PushKeyValueStorage
  requestToken: () => Future<PushDeviceToken>
```

### Installation Mechanism

As with the other mock infrastructures (`mock_http.md`), the mechanism by which the SDK receives its push platform is implementation-specific and not part of the portable interface. The feature spec does not require the platform primitives to be application-supplied; how they reach the SDK is an SDK design decision. Possible approaches include:

- Plugin or client-options configuration (ably-js: `ClientOptions.plugins.Push`, created via `ReactNativePush.create({storage, requestToken})`)
- An activation context bound to the application environment, with storage sourced internally (ably-java: `ActivationContext` over the Android `Context`, storage from `SharedPreferences` — the test subclasses the context)
- Dependency injection or test doubles

In pseudocode, tests install the mock platform with a harness construct, mirroring `install_mock(mock_http)`:

```pseudo
install_push_platform(mock_push_platform)
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

`install_push_platform` must be called before the client first touches any push functionality (device load or the first activation event). Only one push platform is installed at a time: a fresh `install_push_platform` replaces the previous one, so a test that constructs several clients over different storages must not interleave push operations on clients built under different installs. `install_mock(mock_http)` is still required alongside it for the HTTP mock.

### Persisted state: standard keys

The feature spec deliberately does not prescribe storage keys (`RSH3` says only that state "must be persisted"). For portability of these test specs, the following keys — already used by ably-js — are standardised. New SDK implementations should adopt them; an SDK with pre-existing different keys must record a deviation and adapt the derived tests' storage assertions.

| Key | Value representation | Written when |
|---|---|---|
| `ably.push.deviceId` | plain string | `RSH8b` (id/secret generation) |
| `ably.push.deviceSecret` | plain string | `RSH8b` |
| `ably.push.deviceIdentityToken` | JSON-encoded string | `RSH8c` (after successful registration) |
| `ably.push.pushRecipient` | JSON-encoded object | when push device details are obtained or updated |
| `ably.push.activationState` | plain string (state name) | on each transition to a persistent state |

Two further conventions tests may rely on:

- Deactivation (`RSH3g2a` "clears all local `DeviceDetails`") removes `ably.push.deviceIdentityToken` and `ably.push.pushRecipient` from storage — not merely from the in-memory device — so a later load cannot resurrect them.
- Only a subset of states needs to be persisted. Transient states (those with an in-flight request or an unresolved platform interaction) may be persisted as the stable state they will be recovered into. Tests therefore assert persisted state **only after an operation has settled**, and assert in-memory state via observable behaviour, never by reading `ably.push.activationState` mid-operation.

## Mock Interface

```pseudo
interface MockPushStorage:  # implements PushKeyValueStorage
  # Optional observation/interception handler, mirroring mock_http's
  # onRequest: called synchronously before each operation is applied.
  # If the handler RAISEs, the operation fails (the returned future
  # rejects with the raised error) and the contents are not modified.
  MockPushStorage(onOperation?: (op: StorageOperation) => void)

  getItem(key: String): Future<String | null>
  setItem(key: String, value: String): Future<void>
  removeItem(key: String): Future<void>

  # Test-only synchronous inspection: the current contents as a plain map
  dump(): Map<String, String>

  # Test-only seeding: pre-populate contents before the client is created,
  # to simulate state persisted by a previous app run
  seed(entries: Map<String, String>)

  # Blanket fault injection: when true, the corresponding operations fail
  # (the returned future rejects with an error). The onOperation handler
  # runs first; these flags apply to operations the handler did not fail.
  fail_writes: Boolean  # affects setItem / removeItem
  fail_reads: Boolean   # affects getItem

# The record passed to onOperation
StorageOperation:
  type: String   # "getItem" | "setItem" | "removeItem"
  key: String
  value: String? # setItem only
```

As with the HTTP mock, tests that need the operation history capture it into a **local** array via the handler — a `mock_storage.captured_operations` property is deliberately not provided (Common Mistakes #2/#3 in `writing-test-specs.md`):

```pseudo
captured_operations = []
mock_storage = MockPushStorage(onOperation: (op) => captured_operations.append(op))
```

Use `dump()` to assert **end state** (what is persisted once an operation settles) and a captured-operations array to assert **sequence and timing** — e.g. that a key was removed rather than never written, that nothing was written while a request was held, or the relative order of a persist and an HTTP request. Per-key fault injection uses a raising handler; the `fail_writes`/`fail_reads` flags remain for the blanket case:

```pseudo
# Fail only the identity-token persist
mock_storage = MockPushStorage(onOperation: (op) => {
  IF op.type == "setItem" AND op.key == "ably.push.deviceIdentityToken":
    RAISE Error("storage unavailable")
})
```

The token provider needs no mock class — tests supply a closure as `requestToken` and count or gate calls with local variables:

```pseudo
mock_push_platform = MockPushPlatform(
  platform: "android",
  formFactor: "phone",
  storage: mock_storage,
  requestToken: () => PushDeviceToken(transportType: "fcm", token: "fcm-token-1")
)
```

## Example: Successful Activation

Activation drives both the push platform mock and the HTTP mock (see `uts/rest/unit/helpers/mock_http.md`): the token comes from `requestToken`, the registration is a `POST /push/deviceRegistrations`, and the resulting identity token is persisted.

```pseudo
captured_requests = []
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    IF req.method == "POST" AND req.url.path == "/push/deviceRegistrations":
      body = parse_json(req.body)
      req.respond_with(201, merge(body, {"deviceIdentityToken": {"token": "ident-token-1"}}))
    ELSE:
      req.respond_with(500, {"error": {"message": "unexpected request"}})
  }
)
install_mock(mock_http)

mock_storage = MockPushStorage()
mock_push_platform = MockPushPlatform(
  platform: "android",
  formFactor: "phone",
  storage: mock_storage,
  requestToken: () => PushDeviceToken(transportType: "fcm", token: "fcm-token-1")
)

install_push_platform(mock_push_platform)
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

AWAIT client.push.activate()

ASSERT captured_requests.length == 1
persisted = mock_storage.dump()
ASSERT persisted["ably.push.deviceId"] IS NOT null
ASSERT parse_json(persisted["ably.push.pushRecipient"]) == {
  "transportType": "fcm",
  "registrationToken": "fcm-token-1"
}
```

## Example: Seeded Storage (App Restart)

A fresh client over seeded storage simulates a new process recovering persisted state (`RSH3h`, `RSH8a`). The idiomatic way to seed realistic values is to run a first client to completion, then construct a second client over the same storage:

```pseudo
# First app run: activate and let state persist
install_push_platform(mock_push_platform)
client1 = Rest(options: ClientOptions(key: ...))
AWAIT client1.push.activate()

# Second app run: same platform (same storage), fresh client
client2 = Rest(options: ClientOptions(key: ...))
AWAIT client2.push.activate()

# The machine recovered into WaitingForNewPushDeviceDetails, so the second
# activate() syncs or resolves without re-registering (RSH3a2a / RSH3d1)
```

Hand-crafted seeding is also possible for corruption tests (`RSH8a1`):

```pseudo
mock_storage.seed({
  "ably.push.deviceId": "device-1",
  # deviceSecret missing — device load must fail and discard everything
  "ably.push.activationState": "WaitingForNewPushDeviceDetails"
})
```

## Example: Token Acquisition Failure

```pseudo
mock_push_platform = MockPushPlatform(
  platform: "android",
  formFactor: "phone",
  storage: mock_storage,
  requestToken: () => RAISE Error("permission denied")
)
install_push_platform(mock_push_platform)

client = Rest(options: ClientOptions(key: ...))

AWAIT client.push.activate() FAILS WITH error   # RSH8h -> RSH3b4
ASSERT error.message CONTAINS "permission denied"
```

## Test Isolation

Each test should create a fresh `MockPushStorage` and install a fresh mock platform, mirroring the HTTP mock's install/uninstall lifecycle:

```pseudo
BEFORE EACH TEST:
  mock_http = MockHttpClient(...)
  install_mock(mock_http)
  mock_storage = MockPushStorage()
  install_push_platform(MockPushPlatform(..., storage: mock_storage, ...))

AFTER EACH TEST:
  uninstall_mock()
  uninstall_push_platform()
```

(In practice the spec files install the platform via their `push_client(...)` shared helper rather than in `BEFORE EACH TEST`, because many tests configure a per-test `requestToken`.)

## Notes for Spec Authors

- **When `id`/`deviceSecret` are generated is not portable.** Per the note on `RSH8k2`, ably-cocoa and ably-js generate them eagerly when the `LocalDevice` is first loaded, while `RSH3a2b` (followed by ably-java) generates them lazily on `CalledActivate`. Tests must not assert that storage is empty of `ably.push.deviceId`/`ably.push.deviceSecret` before activation, and must not assert exactly when they appear — only that they exist (and are stable) at points the spec requires them to exist.
- **Fire-and-forget persistence.** State-machine transitions may persist asynchronously after the triggering operation resolves. Tests should allow pending writes to settle (e.g. `poll_until(() => mock_storage.dump()["ably.push.activationState"] == "...")`) rather than asserting storage contents immediately.
- **The machine must not process events before initialisation completes** (`RSH3h`). With asynchronous storage this means `activate()`/`deactivate()` internally await hydration; tests do not need to (and must not) call any explicit initialisation API.
