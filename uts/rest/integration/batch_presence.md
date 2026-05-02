# Batch Presence Integration Tests

Spec points: `RSC24`, `BGR2`, `BGF2`

## Test Type
Integration test against Ably sandbox

## Purpose

End-to-end verification of `RestClient#batchPresence` against the Ably sandbox.
Client A enters presence members via Realtime, then the REST client calls
`batchPresence` and verifies the response structure and content.

These tests complement the unit tests (which use mock HTTP) by verifying that the
real server returns correct batch presence responses, including per-channel success
and failure results.

## Server Response Format

The Ably server returns batch presence in two formats depending on success:

- **All success (HTTP 200):** Body is a **plain array** of per-channel results:
  `[{"channel": "ch1", "presence": [...]}, {"channel": "ch2", "presence": [...]}]`

- **Mixed success/failure (HTTP 400):** Body is an object with an `error` field
  and a `batchResponse` array:
  `{"error": {"code": 40020, ...}, "batchResponse": [{"channel": "ch1", "presence": [...]}, {"channel": "ch2", "error": {...}}]}`

The `successCount` and `failureCount` fields (BAR2a, BAR2b) are computed
client-side from the per-channel results, not returned by the server.

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox-rest.ably.io`.

### App Provisioning

Uses `ably-common/test-resources/test-app-setup.json` which provides:
- `keys[0]` — full access (default capability `{"*":["*"]}`)
- `keys[2]` — per-channel capabilities including `"channel6":["*"]`

The restricted key uses an **explicit channel name** (not a wildcard pattern).
Wildcard capability patterns (e.g. `"allowed-*"`) do not work reliably with the
batch presence endpoint.

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  full_access_key = app_config.keys[0].key_str
  restricted_key = app_config.keys[2].key_str  # has "channel6":["*"]
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {full_access_key}
```

---

## RSC24, BGR2 - batchPresence returns members across multiple channels

**Spec requirement:** `batchPresence` sends a GET to `/presence` with a `channels`
query parameter and returns a `BatchResult` containing per-channel presence data.
Each successful result contains the channel name and an array of `PresenceMessage`.

This test enters members on two channels via Realtime, then queries both channels
in a single `batchPresence` call via REST and verifies the returned members.

### Setup
```pseudo
channel_a_name = "batch-presence-a-" + random_id()
channel_b_name = "batch-presence-b-" + random_id()

realtime = Realtime(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
```

### Test Steps
```pseudo
# Connect and enter members on two channels
realtime.connect()
AWAIT_STATE realtime.connection.state == ConnectionState.connected

ch_a = realtime.channels.get(channel_a_name)
AWAIT ch_a.attach()
AWAIT ch_a.presence.enterClient("user-1", data: "data-a1")
AWAIT ch_a.presence.enterClient("user-2", data: "data-a2")

ch_b = realtime.channels.get(channel_b_name)
AWAIT ch_b.attach()
AWAIT ch_b.presence.enterClient("user-3", data: "data-b1")

# Query via REST batchPresence (keep realtime open so presence persists)
rest = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

result = AWAIT rest.batchPresence([channel_a_name, channel_b_name])
```

### Assertions
```pseudo
ASSERT result.successCount == 2
ASSERT result.failureCount == 0
ASSERT result.results.length == 2

# Find results by channel name
result_a = result.results.find(r => r.channel == channel_a_name)
result_b = result.results.find(r => r.channel == channel_b_name)

ASSERT result_a IS BatchPresenceSuccessResult
ASSERT result_a.presence.length == 2
client_ids_a = [m.clientId FOR m IN result_a.presence]
ASSERT "user-1" IN client_ids_a
ASSERT "user-2" IN client_ids_a

# Verify data round-trips correctly
member_1 = result_a.presence.find(m => m.clientId == "user-1")
ASSERT member_1.data == "data-a1"

ASSERT result_b IS BatchPresenceSuccessResult
ASSERT result_b.presence.length == 1
ASSERT result_b.presence[0].clientId == "user-3"
ASSERT result_b.presence[0].data == "data-b1"
```

### Cleanup
```pseudo
AWAIT realtime.close()
```

---

## RSC24, BGF2 - Restricted key returns per-channel failure for unauthorized channels

**Spec requirement:** When a key lacks capability for a channel, the per-channel
result is a `BatchPresenceFailureResult` containing an `ErrorInfo`. Channels the key
does have access to return success results in the same batch response.

The server returns HTTP 400 with `{"error": {"code": 40020, ...}, "batchResponse": [...]}`
when the batch contains any per-channel errors. The client extracts the `batchResponse`
array and builds results from it.

### Setup
```pseudo
# Use the fixed channel name matching keys[2] capability from ably-common
allowed_channel = "channel6"
denied_channel = "denied-batch-" + random_id()

# Enter members on both channels using the full-access key
realtime = Realtime(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

realtime.connect()
AWAIT_STATE realtime.connection.state == ConnectionState.connected

ch_allowed = realtime.channels.get(allowed_channel)
AWAIT ch_allowed.attach()
AWAIT ch_allowed.presence.enterClient("member-1", data: "hello")

ch_denied = realtime.channels.get(denied_channel)
AWAIT ch_denied.attach()
AWAIT ch_denied.presence.enterClient("member-2", data: "world")

AWAIT realtime.close()
```

### Test Steps
```pseudo
# Query with restricted key (only has access to "batch-allowed" channel)
restricted_rest = Rest(options: ClientOptions(
  key: restricted_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

result = AWAIT restricted_rest.batchPresence([allowed_channel, denied_channel])
```

### Assertions
```pseudo
ASSERT result.successCount == 1
ASSERT result.failureCount == 1
ASSERT result.results.length == 2

# Find results by channel name
success = result.results.find(r => r.channel == allowed_channel)
failure = result.results.find(r => r.channel == denied_channel)

# Allowed channel succeeds with presence data
ASSERT success IS BatchPresenceSuccessResult
ASSERT success.presence.length == 1
ASSERT success.presence[0].clientId == "member-1"

# Denied channel fails with capability error
ASSERT failure IS BatchPresenceFailureResult
ASSERT failure.error IS ErrorInfo
ASSERT failure.error.code == 40160
ASSERT failure.error.statusCode == 401
```

### Cleanup

No cleanup needed — the Realtime client was already closed during setup,
and the REST client has no persistent connection to close.

---

## RSC24 - batchPresence with empty channel returns empty presence array

**Spec requirement:** A channel with no presence members returns a success result
with an empty `presence` array.

### Setup
```pseudo
empty_channel = "batch-empty-" + random_id()
populated_channel = "batch-populated-" + random_id()

# Enter a member on only the populated channel
realtime = Realtime(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

realtime.connect()
AWAIT_STATE realtime.connection.state == ConnectionState.connected

ch = realtime.channels.get(populated_channel)
AWAIT ch.attach()
AWAIT ch.presence.enterClient("someone", data: "here")

# NOTE: Keep realtime open during the REST query so the presence member
# persists on the server. Closing realtime before the query would cause
# the member to leave.
```

### Test Steps
```pseudo
rest = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

result = AWAIT rest.batchPresence([empty_channel, populated_channel])
```

### Assertions
```pseudo
ASSERT result.successCount == 2
ASSERT result.failureCount == 0
ASSERT result.results.length == 2

empty_result = result.results.find(r => r.channel == empty_channel)
populated_result = result.results.find(r => r.channel == populated_channel)

# Empty channel succeeds with no members
ASSERT empty_result IS BatchPresenceSuccessResult
ASSERT empty_result.presence.length == 0

# Populated channel succeeds with the member
ASSERT populated_result IS BatchPresenceSuccessResult
ASSERT populated_result.presence.length == 1
ASSERT populated_result.presence[0].clientId == "someone"
```

### Cleanup
```pseudo
AWAIT realtime.close()
```
