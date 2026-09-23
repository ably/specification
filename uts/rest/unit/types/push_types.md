# Push Type Tests

Spec points: `PCD1`, `PCD2`, `PCD3`, `PCD4`, `PCD5`, `PCD6`, `PCD7`, `PCP1`, `PCP2`, `PCP3`, `PCP4`, `PCS1`, `PCS2`, `PCS3`, `PCS4`, `PCS5`

## Test Type
Unit test — pure type construction and serialization, no HTTP mock needed.

## Notes

- **Push state wire casing (PCP4):** the feature spec names the `DevicePushDetails.state` values `Active`, `Failing`, `Failed`; ably-js (`src/common/lib/types/devicedetails.ts`) types the wire value as uppercase — `'ACTIVE' | 'FAILING' | 'FAILED'` — which these tests use as the wire form. Assertions on the parsed attribute use the spec's enum members (`DevicePushState.Active` etc.); an SDK that exposes the raw wire string, or that observes a different server casing, must adapt those assertions and record a deviation.
- **`errorReason` wire field (PCP2):** the spec names the attribute `errorReason`. ably-js's wire mapping writes the push error as `error` under `push` (see `toJSON()` in `devicedetails.ts`); ably-js derived tests may record a deviation on the wire field name.
- **`metadata` (PCD5):** the spec defines it as *"a map of string key/value pairs"*; ably-js currently types `metadata` as a plain string. These tests follow the spec (a map); ably-js derived tests may record a deviation.
- **PCS5 enforcement is language-specific:** *"precisely one of `deviceId` or `clientId` must be non-null -- this should be enforced by a mechanism appropriate to the language, for example one constructor that takes a device ID and one that takes a client ID."* The IDL prescribes the `+forDevice(channel, deviceId)` and `+forClientId(channel, clientId)` factories. ably-js currently exposes neither factory nor any exactly-one enforcement (`fromValues` copies fields as-received); ably-js derived tests may record deviations for the factory tests, constructing subscriptions by an equivalent means.

---

## PCD1–PCD7 — DeviceDetails round-trips all attributes through wire JSON

**Test ID**: `rest/unit/PCD1/device-details-round-trip-0`

| Spec | Requirement |
|------|-------------|
| PCD1 | `DeviceDetails` — details of a registered device, consisting of the following attributes |
| PCD2 | `id` string — the id of the device registration |
| PCD3 | `clientId` string — (optional, populated for device registrations associated with a `clientId`) |
| PCD4 | `formFactor` — the device formfactor |
| PCD5 | `metadata` — a map of string key/value pairs containing any other registered metadata |
| PCD6 | `platform` — the device platform |
| PCD7 | `push` `DevicePushDetails` — details of the push registration for this device |
| PCP2 | `errorReason` `ErrorInfo` — (optional) any error information associated with the registration |
| PCP3 | `recipient` — a map of string key/value pairs containing details of the push transport and address |
| PCP4 | `state` — the state of the push registration |

Tests that a full `DeviceDetails` parses every attribute from wire JSON, and that serializing it back reproduces the same wire fields.

### Test Steps
```pseudo
wire = {
  "id": "device-001",
  "clientId": "client-abc",
  "platform": "android",
  "formFactor": "phone",
  "metadata": {"environment": "test"},
  "push": {
    "recipient": {"transportType": "fcm", "registrationToken": "reg-token-1"},
    "state": "ACTIVE",
    "errorReason": {"code": 40000, "statusCode": 400, "message": "example error"}
  }
}

device = DeviceDetails.fromJson(wire)

ASSERT device.id == "device-001"                        # PCD2
ASSERT device.clientId == "client-abc"                  # PCD3
ASSERT device.formFactor == DeviceFormFactor.phone      # PCD4
ASSERT device.metadata == {"environment": "test"}       # PCD5
ASSERT device.platform == DevicePlatform.android        # PCD6

# PCD7 — push is a DevicePushDetails (PCP1)
ASSERT device.push IS DevicePushDetails
ASSERT device.push.recipient == {                       # PCP3
  "transportType": "fcm",
  "registrationToken": "reg-token-1"
}
ASSERT device.push.state == DevicePushState.Active      # PCP4
ASSERT device.push.errorReason IS ErrorInfo             # PCP2
ASSERT device.push.errorReason.code == 40000
ASSERT device.push.errorReason.statusCode == 400
ASSERT device.push.errorReason.message == "example error"

# Round trip — serialization reproduces the wire fields
json_data = device.toJson()
ASSERT json_data["id"] == "device-001"
ASSERT json_data["clientId"] == "client-abc"
ASSERT json_data["platform"] == "android"
ASSERT json_data["formFactor"] == "phone"
ASSERT json_data["metadata"] == {"environment": "test"}
ASSERT json_data["push"]["recipient"] == {
  "transportType": "fcm",
  "registrationToken": "reg-token-1"
}
ASSERT json_data["push"]["state"] == "ACTIVE"
ASSERT json_data["push"]["errorReason"]["code"] == 40000
```

---

## PCD4 — all DeviceFormFactor values are accepted

**Test ID**: `rest/unit/PCD4/form-factor-values-0`

**Spec requirement:** PCD4 — `formFactor` is *"the device formfactor, one of `phone`, `tablet`, `desktop`, `tv`, `watch`, `car`, `embedded`, `other`"*.

### Test Steps
```pseudo
form_factors = ["phone", "tablet", "desktop", "tv", "watch", "car", "embedded", "other"]

FOR EACH form_factor IN form_factors:
  device = DeviceDetails.fromJson({
    "id": "device-001",
    "platform": "android",
    "formFactor": form_factor
  })

  # DeviceFormFactor(x) denotes the enum member whose wire value is x
  ASSERT device.formFactor == DeviceFormFactor(form_factor)
  ASSERT device.toJson()["formFactor"] == form_factor
```

---

## PCD6 — all DevicePlatform values are accepted

**Test ID**: `rest/unit/PCD6/platform-values-0`

**Spec requirement:** PCD6 — `platform` is *"the device platform, one of `android`, `ios`, `browser`"*.

### Test Steps
```pseudo
platforms = ["android", "ios", "browser"]

FOR EACH platform IN platforms:
  device = DeviceDetails.fromJson({
    "id": "device-001",
    "platform": platform,
    "formFactor": "phone"
  })

  # DevicePlatform(x) denotes the enum member whose wire value is x
  ASSERT device.platform == DevicePlatform(platform)
  ASSERT device.toJson()["platform"] == platform
```

---

## PCP2, PCP3, PCP4 — DevicePushDetails state values, errorReason, and recipient parse from wire JSON

**Test ID**: `rest/unit/PCP4/device-push-state-values-0`

| Spec | Requirement |
|------|-------------|
| PCP4 | `state` — the state of the push registration, one of `Active`, `Failing`, `Failed` |
| PCP2 | `errorReason` `ErrorInfo` — (optional) any error information associated with the registration |
| PCP3 | `recipient` — a map of string key/value pairs containing details of the push transport and address |

Tests each `DevicePushDetails.state` value parsed from its wire form (uppercase, per ably-js's type declarations — see Notes), that `errorReason` parses as an `ErrorInfo`, and that `recipient` is preserved as an opaque string map.

### Test Cases

| Wire state | Enum member |
|------------|-------------|
| `"ACTIVE"` | `DevicePushState.Active` |
| `"FAILING"` | `DevicePushState.Failing` |
| `"FAILED"` | `DevicePushState.Failed` |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  device = DeviceDetails.fromJson({
    "id": "device-001",
    "platform": "ios",
    "formFactor": "phone",
    "push": {
      "recipient": {"transportType": "apns", "deviceToken": "apns-token-1"},
      "state": test_case.wire_state,
      "errorReason": {"code": 71103, "statusCode": 500, "message": "upstream failure"}
    }
  })

  # PCP4 — state parses to the corresponding enum member
  ASSERT device.push.state == test_case.enum_member

  # PCP2 — errorReason parses as ErrorInfo
  ASSERT device.push.errorReason IS ErrorInfo
  ASSERT device.push.errorReason.code == 71103

  # PCP3 — recipient is an opaque string map, preserved as-received
  ASSERT device.push.recipient == {
    "transportType": "apns",
    "deviceToken": "apns-token-1"
  }
```

---

## PCS5 — forDevice sets channel and deviceId, leaving clientId null

**Test ID**: `rest/unit/PCS5/push-channel-subscription-for-device-0`

| Spec | Requirement |
|------|-------------|
| PCS2 | `deviceId` string — (optional, populated for subscriptions made for a specific device registration) |
| PCS4 | `channel` string — the channel name associated with this subscription |
| PCS5 | Precisely one of `deviceId` or `clientId` must be non-null — e.g. *"one constructor that takes a device ID"* (the IDL's `+forDevice(channel, deviceId)`) |

Tests that the device-targeted factory populates exactly `channel` and `deviceId`, and that serialization contains exactly those fields.

### Test Steps
```pseudo
subscription = PushChannelSubscription.forDevice("push-test-channel", "device-001")

ASSERT subscription.channel == "push-test-channel"   # PCS4
ASSERT subscription.deviceId == "device-001"         # PCS2
ASSERT subscription.clientId IS null                 # PCS5 — the other identifier stays null

json_data = subscription.toJson()
ASSERT json_data["channel"] == "push-test-channel"
ASSERT json_data["deviceId"] == "device-001"
ASSERT "clientId" NOT IN json_data OR json_data["clientId"] IS null
```

---

## PCS5 — forClientId sets channel and clientId, leaving deviceId null

**Test ID**: `rest/unit/PCS5/push-channel-subscription-for-client-1`

| Spec | Requirement |
|------|-------------|
| PCS3 | `clientId` string — (optional, populated for subscriptions made for a specific `clientId`) |
| PCS4 | `channel` string — the channel name associated with this subscription |
| PCS5 | Precisely one of `deviceId` or `clientId` must be non-null — e.g. *"one … that takes a client ID"* (the IDL's `+forClientId(channel, clientId)`) |

Tests that the client-targeted factory populates exactly `channel` and `clientId`, and that serialization contains exactly those fields.

### Test Steps
```pseudo
subscription = PushChannelSubscription.forClientId("push-test-channel", "client-abc")

ASSERT subscription.channel == "push-test-channel"   # PCS4
ASSERT subscription.clientId == "client-abc"         # PCS3
ASSERT subscription.deviceId IS null                 # PCS5 — the other identifier stays null

json_data = subscription.toJson()
ASSERT json_data["channel"] == "push-test-channel"
ASSERT json_data["clientId"] == "client-abc"
ASSERT "deviceId" NOT IN json_data OR json_data["deviceId"] IS null
```

---

## PCS5 — precisely one of deviceId or clientId is non-null

**Test ID**: `rest/unit/PCS5/exactly-one-of-device-client-2`

**Spec requirement:** PCS5 — *"precisely one of `deviceId` or `clientId` must be non-null -- this should be enforced by a mechanism appropriate to the language, for example one constructor that takes a device ID and one that takes a client ID."*

The enforcement mechanism is deliberately language-specific, so this test asserts two portable facets:

1. **Construction:** the factory-based API offers no way to construct a subscription carrying both identifiers — each factory takes exactly one, and leaves the other null (asserted below; in statically typed languages this is additionally a compile-time property).
2. **Wire parsing:** a (server-invalid) wire object carrying *both* identifiers is handled deterministically — the SDK either rejects it with a parse error, or exposes the object as-received. The derived test asserts whichever branch its SDK takes and records the choice as a deviation note. ably-js takes the as-received branch (`fromValues` copies fields without validation).

### Test Steps
```pseudo
# 1. Construction — each factory populates exactly one identifier (PCS5)
ASSERT PushChannelSubscription.forDevice("ch", "device-001").clientId IS null
ASSERT PushChannelSubscription.forClientId("ch", "client-abc").deviceId IS null

# 2. Wire parsing — both identifiers present: reject, or expose as-received
wire = {"channel": "ch", "deviceId": "device-001", "clientId": "client-abc"}

EITHER:
  PushChannelSubscription.fromJson(wire) FAILS WITH error   # (a) rejected on parse
OR:
  subscription = PushChannelSubscription.fromJson(wire)     # (b) exposed as-received
  ASSERT subscription.channel == "ch"
  ASSERT subscription.deviceId == "device-001"
  ASSERT subscription.clientId == "client-abc"
```
