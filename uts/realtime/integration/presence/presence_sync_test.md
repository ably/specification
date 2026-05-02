# Realtime Presence Sync Integration Tests

Spec points: `RTP2`, `RTP11a`

## Test Type
Integration test against Ably sandbox

## Purpose

End-to-end verification that the presence SYNC protocol delivers the correct
member set to a client that attaches to a channel with existing presence members.

The existing `presence_lifecycle_test.md` tests subscribe-time delivery of
enter/update/leave events. This test specifically targets the SYNC path: client B
attaches *after* client A has already entered, so B receives members via the
server-initiated SYNC rather than via real-time PRESENCE messages.

## Sandbox Setup

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

---

## RTP2, RTP11a - Presence SYNC delivers existing members

| Spec | Requirement |
|------|-------------|
| RTP2 | A PresenceMap is maintained via SYNC |
| RTP11a | presence.get() returns the list of current members, waiting for SYNC to complete |

**Spec requirement:** When client B attaches to a channel where client A is
already present, the server initiates a SYNC that delivers client A's presence
to client B. After SYNC completes, `presence.get()` returns the correct member list.

### Setup
```pseudo
channel_name = "presence-sync-" + random_id()

client_a = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  clientId: "sync-member-a",
  autoConnect: false,
  useBinaryProtocol: false
))

client_b = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps
```pseudo
# Connect client A and enter presence
client_a.connect()
AWAIT_STATE client_a.connection.state == CONNECTED

channel_a = client_a.channels.get(channel_name)
AWAIT channel_a.attach()
AWAIT channel_a.presence.enter(data: "sync-data")

# Now connect client B — client A is already present
client_b.connect()
AWAIT_STATE client_b.connection.state == CONNECTED

channel_b = client_b.channels.get(channel_name)
AWAIT channel_b.attach()

# presence.get() waits for SYNC to complete (RTP11a)
members = AWAIT channel_b.presence.get()
```

### Assertions
```pseudo
ASSERT members.length == 1
ASSERT members[0].clientId == "sync-member-a"
ASSERT members[0].data == "sync-data"
ASSERT members[0].action == PRESENT

CLOSE_CLIENT(client_a)
CLOSE_CLIENT(client_b)
```

---

## RTP2 - Presence SYNC with multiple members

| Spec | Requirement |
|------|-------------|
| RTP2 | PresenceMap maintained via SYNC contains all present members |

**Spec requirement:** When multiple members are present on a channel before
client B attaches, the SYNC delivers all of them.

### Setup
```pseudo
channel_name = "presence-sync-multi-" + random_id()
member_count = 10

client_a = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))

client_b = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps
```pseudo
# Connect client A and enter multiple members
client_a.connect()
AWAIT_STATE client_a.connection.state == CONNECTED

channel_a = client_a.channels.get(channel_name)
AWAIT channel_a.attach()

FOR i IN 0..member_count-1:
  AWAIT channel_a.presence.enterClient("sync-user-" + i, data: "data-" + i)

# Now connect client B
client_b.connect()
AWAIT_STATE client_b.connection.state == CONNECTED

channel_b = client_b.channels.get(channel_name)
AWAIT channel_b.attach()

# presence.get() waits for SYNC to complete
members = AWAIT channel_b.presence.get()
```

### Assertions
```pseudo
ASSERT members.length == member_count

FOR i IN 0..member_count-1:
  member = members.find(m => m.clientId == "sync-user-" + i)
  ASSERT member IS NOT NULL
  ASSERT member.data == "data-" + i

CLOSE_CLIENT(client_a)
CLOSE_CLIENT(client_b)
```
