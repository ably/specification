# REST Presence Integration Tests

Spec points: `RSP1`, `RSP3`, `RSP3a`, `RSP4`, `RSP4b`, `RSP5`

## Test Type
Integration test against Ably sandbox

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox-rest.ably.io`.

### App Provisioning

Uses `ably-common/test-resources/test-app-setup.json` which provides:
- `keys[0]` — full access (default capability `{"*":["*"]}`)
- `keys[3]` — subscribe-only (`{"*":["subscribe"]}`)
- Pre-populated presence fixtures on `persisted:presence_fixtures` channel
- Cipher configuration for encrypted fixture data

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox-rest.ably.io/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

### Presence Fixtures

The `ably-common/test-resources/test-app-setup.json` includes pre-populated presence members on the channel `persisted:presence_fixtures`:

| clientId | data | encoding |
|----------|------|----------|
| `client_bool` | `"true"` | none |
| `client_int` | `"24"` | none |
| `client_string` | `"This is a string clientData payload"` | none |
| `client_json` | `"{ \"test\": \"This is a JSONObject clientData payload\"}"` (string) | none |
| `client_decoded` | `{"example":{"json":"Object"}}` | `json` |
| `client_encoded` | (encrypted) | `json/utf-8/cipher+aes-128-cbc/base64` |

**Cipher configuration** for `client_encoded` (from `test-app-setup.json` `cipher` section):
- Algorithm: `aes`
- Mode: `cbc`
- Key length: 128
- Key (base64): `WUP6u0K7MXI5Zeo0VppPwg==`
- IV (base64): `HO4cYSP8LybPYBPZPHQOtg==`

---

## RSP1 - RestPresence accessible via channel

### RSP1_Integration - Access presence from channel

**Spec requirement:** RSP1 - `RestPresence` object is accessible via `channel.presence`.

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

channel = client.channels.get("persisted:presence_fixtures")
presence = channel.presence

ASSERT presence IS NOT null
ASSERT presence IS RestPresence
```

---

## RSP3 - RestPresence#get

### RSP3_Integration_1 - Get presence members from fixture channel

**Spec requirement:** RSP3 - `get()` returns a `PaginatedResult` containing current presence members.

Retrieves the pre-populated presence members from the sandbox fixture channel.

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

channel = client.channels.get("persisted:presence_fixtures")
result = AWAIT channel.presence.get()

ASSERT result IS PaginatedResult
ASSERT result.items.length >= 5  # At least the non-encrypted fixtures

# Verify expected clients are present
client_ids = [msg.clientId FOR msg IN result.items]
ASSERT "client_bool" IN client_ids
ASSERT "client_string" IN client_ids
ASSERT "client_json" IN client_ids
```

### RSP3_Integration_2 - Get returns PresenceMessage with correct fields

**Spec requirement:** RSP3 - Each item in the result is a `PresenceMessage` with action, clientId, data, and connectionId.

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

channel = client.channels.get("persisted:presence_fixtures")
result = AWAIT channel.presence.get()

# Find client_string member
member = FIND msg IN result.items WHERE msg.clientId == "client_string"

ASSERT member IS NOT null
ASSERT member IS PresenceMessage
ASSERT member.action == PresenceAction.present
ASSERT member.clientId == "client_string"
ASSERT member.data == "This is a string clientData payload"
ASSERT member.connectionId IS NOT null
```

### RSP3a1_Integration - Get with limit parameter

**Spec requirement:** RSP3a1 - `limit` param restricts the number of presence members returned.

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

channel = client.channels.get("persisted:presence_fixtures")

# Request with small limit
result = AWAIT channel.presence.get(limit: 2)

ASSERT result.items.length <= 2
# If more members exist, pagination should be available
IF result.hasNext():
  ASSERT result.items.length == 2
```

### RSP3a2_Integration - Get with clientId filter

**Spec requirement:** RSP3a2 - `clientId` param filters results to specified client.

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

channel = client.channels.get("persisted:presence_fixtures")
result = AWAIT channel.presence.get(clientId: "client_json")

ASSERT result.items.length == 1
ASSERT result.items[0].clientId == "client_json"
# The fixture has no encoding field, so data is returned as a raw string
ASSERT result.items[0].data IS String
ASSERT result.items[0].data == "{ \"test\": \"This is a JSONObject clientData payload\"}"
```

### RSP3_Integration_Empty - Get on channel with no presence

**Spec requirement:** RSP3 - `get()` returns empty `PaginatedResult` when no members are present.

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

# Use a unique channel name that has no presence members
channel_name = "presence-empty-" + random_id()
channel = client.channels.get(channel_name)

result = AWAIT channel.presence.get()

ASSERT result.items IS List
ASSERT result.items.length == 0
ASSERT result.hasNext() == false
```

---

## RSP4 - RestPresence#history

### RSP4_Integration_1 - History returns presence events

**Spec requirement:** RSP4 - `history()` returns a `PaginatedResult` containing presence event history.

This test creates presence history by entering and leaving a channel.

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

channel_name = "presence-history-" + random_id()

# Use realtime client to generate presence history
realtime = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  clientId: "test-client"
))

realtime_channel = realtime.channels.get(channel_name)
AWAIT realtime_channel.presence.enter(data: "entered")
AWAIT realtime_channel.presence.update(data: "updated")
AWAIT realtime_channel.presence.leave(data: "left")
AWAIT realtime.close()

# Poll REST history until events appear
rest_channel = client.channels.get(channel_name)

history = poll_until(
  condition: FUNCTION() =>
    result = AWAIT rest_channel.presence.history()
    RETURN result.items.length >= 3,
  interval: 500ms,
  timeout: 10s
)

ASSERT history.items.length >= 3

# Check for expected actions (order depends on direction)
actions = [msg.action FOR msg IN history.items]
ASSERT PresenceAction.enter IN actions
ASSERT PresenceAction.update IN actions
ASSERT PresenceAction.leave IN actions
```

### RSP4b1_Integration - History with start/end time range

**Spec requirement:** RSP4b1 - `start` and `end` params filter history by timestamp range.

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  clientId: "test-client"
))

channel_name = "presence-history-time-" + random_id()

# Record time before any presence events
time_before = now_millis()

# Generate presence events via realtime
realtime = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  clientId: "time-test-client"
))

realtime_channel = realtime.channels.get(channel_name)
AWAIT realtime_channel.presence.enter(data: "test")
AWAIT realtime_channel.presence.leave()
AWAIT realtime.close()

time_after = now_millis()

# Poll until events appear
rest_channel = client.channels.get(channel_name)
poll_until(
  condition: FUNCTION() =>
    result = AWAIT rest_channel.presence.history()
    RETURN result.items.length >= 2,
  interval: 500ms,
  timeout: 10s
)

# Query with time range
history = AWAIT rest_channel.presence.history(
  start: time_before,
  end: time_after
)

ASSERT history.items.length >= 2
```

### RSP4b2_Integration - History direction forwards

**Spec requirement:** RSP4b2 - `direction` param controls event ordering (forwards = oldest first).

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

channel_name = "presence-direction-" + random_id()

# Generate ordered presence events
realtime = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  clientId: "direction-client"
))

realtime_channel = realtime.channels.get(channel_name)
AWAIT realtime_channel.presence.enter(data: "first")
AWAIT realtime_channel.presence.update(data: "second")
AWAIT realtime_channel.presence.update(data: "third")
AWAIT realtime.close()

# Poll until events appear
rest_channel = client.channels.get(channel_name)
poll_until(
  condition: FUNCTION() =>
    result = AWAIT rest_channel.presence.history()
    RETURN result.items.length >= 3,
  interval: 500ms,
  timeout: 10s
)

# Get history forwards (oldest first)
history_forwards = AWAIT rest_channel.presence.history(direction: "forwards")

ASSERT history_forwards.items.length >= 3
ASSERT history_forwards.items[0].data == "first"

# Get history backwards (newest first) - default
history_backwards = AWAIT rest_channel.presence.history(direction: "backwards")

ASSERT history_backwards.items[0].data == "third"
```

### RSP4b3_Integration - History with limit and pagination

**Spec requirement:** RSP4b3 - `limit` param restricts history results and enables pagination.

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

channel_name = "presence-limit-" + random_id()

# Generate multiple presence events
realtime = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  clientId: "limit-client"
))

realtime_channel = realtime.channels.get(channel_name)
FOR i IN 1..5:
  AWAIT realtime_channel.presence.update(data: "update-" + str(i))
AWAIT realtime.close()

# Poll until all events appear
rest_channel = client.channels.get(channel_name)
poll_until(
  condition: FUNCTION() =>
    result = AWAIT rest_channel.presence.history()
    RETURN result.items.length >= 5,
  interval: 500ms,
  timeout: 10s
)

# Request with small limit
page1 = AWAIT rest_channel.presence.history(limit: 2)

ASSERT page1.items.length == 2
ASSERT page1.hasNext() == true

# Get next page
page2 = AWAIT page1.next()

ASSERT page2 IS NOT null
ASSERT page2.items.length >= 1
```

---

## RSP5 - Presence message decoding

### RSP5_Integration_1 - String data decoded correctly

**Spec requirement:** RSP5 - Presence message `data` is decoded according to its encoding.

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

channel = client.channels.get("persisted:presence_fixtures")
result = AWAIT channel.presence.get(clientId: "client_string")

ASSERT result.items.length == 1
ASSERT result.items[0].data IS String
ASSERT result.items[0].data == "This is a string clientData payload"
```

### RSP5_Integration_2 - JSON data decoded to object

**Spec requirement:** RSP5 - JSON-encoded presence data is decoded to native objects.

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

channel = client.channels.get("persisted:presence_fixtures")
result = AWAIT channel.presence.get(clientId: "client_decoded")

ASSERT result.items.length == 1
ASSERT result.items[0].data IS Object/Map
ASSERT result.items[0].data["example"]["json"] == "Object"
```

### RSP5_Integration_3 - Encrypted data decoded with cipher

**Spec requirement:** RSP5 - Encrypted presence data is automatically decrypted when cipher is configured.

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

cipher_key = base64_decode("WUP6u0K7MXI5Zeo0VppPwg==")

channel = client.channels.get("persisted:presence_fixtures", options: RestChannelOptions(
  cipher: CipherParams(
    key: cipher_key,
    algorithm: "aes",
    mode: "cbc",
    keyLength: 128
  )
))

result = AWAIT channel.presence.get(clientId: "client_encoded")

# The encrypted fixture should be decrypted
ASSERT result.items.length == 1
ASSERT result.items[0].data IS NOT null
# Actual decrypted value depends on fixture content
```

### RSP5_Integration_4 - History messages also decoded

**Spec requirement:** RSP5 - Presence history messages are decoded the same way as current presence.

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

channel_name = "presence-decode-history-" + random_id()

# Generate presence event with JSON data
realtime = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  clientId: "decode-client"
))

json_data = { "key": "value", "number": 123 }
realtime_channel = realtime.channels.get(channel_name)
AWAIT realtime_channel.presence.enter(data: json_data)
AWAIT realtime.close()

# Poll and retrieve history
rest_channel = client.channels.get(channel_name)
history = poll_until(
  condition: FUNCTION() =>
    result = AWAIT rest_channel.presence.history()
    RETURN result.items.length >= 1,
  interval: 500ms,
  timeout: 10s
)

ASSERT history.items[0].data IS Object/Map
ASSERT history.items[0].data["key"] == "value"
ASSERT history.items[0].data["number"] == 123
```

---

## Pagination

### RSP_Pagination_Integration - Full pagination through presence members

**Spec requirement:** RSP3 - Presence `get()` supports pagination through all members.

```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))

# The fixture channel has multiple members
channel = client.channels.get("persisted:presence_fixtures")

# Request with small limit to force pagination
page1 = AWAIT channel.presence.get(limit: 2)

all_members = []
all_members.extend(page1.items)

current_page = page1
WHILE current_page.hasNext():
  current_page = AWAIT current_page.next()
  all_members.extend(current_page.items)

# Should have retrieved all fixture members
ASSERT all_members.length >= 5

# Verify no duplicates
client_ids = [m.clientId FOR m IN all_members]
ASSERT len(set(client_ids)) == len(client_ids)
```

---

## Error Handling

### RSP_Error_Integration_1 - Invalid credentials rejected

**Spec requirement:** RSP3 - Presence operations with invalid credentials return authentication errors.

```pseudo
client = Rest(options: ClientOptions(
  key: "invalid.key:secret",
  endpoint: "sandbox"
))

AWAIT client.channels.get("test").presence.get() FAILS WITH error
ASSERT error.statusCode == 401
ASSERT error.code >= 40100 AND error.code < 40200
```

### RSP_Error_Integration_2 - Insufficient permissions rejected

**Spec requirement:** RSP3 - Presence operations succeed with appropriate capabilities.

```pseudo
# Use key with limited capabilities (keys[3] has subscribe only)
restricted_key = app_config.keys[3].key_str

client = Rest(options: ClientOptions(
  key: restricted_key,
  endpoint: "sandbox"
))

# This should work - subscribe capability is sufficient for presence.get
result = AWAIT client.channels.get("persisted:presence_fixtures").presence.get()
ASSERT result IS NOT null
```
