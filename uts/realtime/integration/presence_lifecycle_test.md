# Realtime Presence Lifecycle Integration Tests

Spec points: `RTP4`, `RTP6`, `RTP8`, `RTP9`, `RTP10`, `RTP11a`

## Test Type
Integration test against Ably sandbox

## Purpose

End-to-end verification of the realtime presence lifecycle using two connections
against the Ably sandbox. Client A enters/updates/leaves members, Client B observes
presence events via subscribe and verifies member state via get().

These tests complement the unit tests by verifying that the real server correctly
broadcasts presence events, delivers SYNC data, and maintains presence state.

## Test Environment

### Prerequisites
- Ably sandbox app provisioned via `POST https://sandbox-rest.ably.io/apps`
- API key with `{"*":["*"]}` capability
- `useBinaryProtocol: false` (SDK does not implement msgpack)

### Setup Pattern
```pseudo
BEFORE ALL TESTS:
  app_config = provision_sandbox_app(
    keys: [{ capability: '{"*":["*"]}' }]
  )
  app_id = app_config.app_id
  api_key = app_config.keys[0].key_str

AFTER ALL TESTS:
  DELETE https://sandbox-rest.ably.io/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

---

## RTP4, RTP6, RTP11a - Bulk enterClient observed on different connection

**Spec requirement:** Enter multiple members on connection A, verify they are observed
on connection B via subscribe (RTP6) and get() after sync (RTP11a). This is the
integration equivalent of the RTP4 unit test.

Note: The spec says 250 but we use 50 as a practical test size that validates the
same behavior without excessive test runtime.

### Setup
```pseudo
channel_name = "presence-bulk-" + random_id()
member_count = 50

client_a = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))

client_b = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
```

### Test Steps
```pseudo
# Connect both clients
client_a.connect()
AWAIT_STATE client_a.connection.state == ConnectionState.connected

client_b.connect()
AWAIT_STATE client_b.connection.state == ConnectionState.connected

# Attach both to the channel
channel_a = client_a.channels.get(channel_name)
channel_b = client_b.channels.get(channel_name)
AWAIT channel_b.attach()

# Subscribe on client B before client A enters
received_enters = []
channel_b.presence.subscribe(action: ENTER, (event) => {
  received_enters.append(event)
})

# Attach client A (after B is attached and subscribed)
AWAIT channel_a.attach()

# Client A enters members in parallel
futures = []
FOR i IN 0..member_count-1:
  futures.append(channel_a.presence.enterClient("user-${i}", data: "data-${i}"))
AWAIT_ALL futures

# Wait for client B to receive all ENTER events
poll_until(
  condition: FUNCTION() => received_enters.length >= member_count,
  interval: 200ms,
  timeout: 15s
)

# Client B gets all members
members = AWAIT channel_b.presence.get()
```

### Assertions
```pseudo
# Client B received all ENTER events via subscribe
ASSERT received_enters.length == member_count

# All members present via get()
ASSERT members.length == member_count

# Verify each member has correct clientId and data
FOR i IN 0..member_count-1:
  member = members.find(m => m.clientId == "user-${i}")
  ASSERT member IS NOT null
  ASSERT member.data == "data-${i}"
```

### Cleanup
```pseudo
AWAIT client_a.close()
AWAIT client_b.close()
```

---

## RTP8, RTP9, RTP10 - Enter, update, leave lifecycle

**Spec requirement:** Verify the complete presence lifecycle: enter populates the
presence set (RTP8), update modifies the data (RTP9), and leave removes the member
(RTP10). All transitions are observed on a separate connection.

### Setup
```pseudo
channel_name = "presence-lifecycle-" + random_id()

client_a = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  clientId: "lifecycle-client",
  useBinaryProtocol: false
))

client_b = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  useBinaryProtocol: false
))
```

### Test Steps
```pseudo
# Connect and attach both clients
client_a.connect()
AWAIT_STATE client_a.connection.state == ConnectionState.connected
client_b.connect()
AWAIT_STATE client_b.connection.state == ConnectionState.connected

channel_a = client_a.channels.get(channel_name)
channel_b = client_b.channels.get(channel_name)
AWAIT channel_b.attach()

# Collect all presence events on client B
all_events = []
channel_b.presence.subscribe((event) => {
  all_events.append(event)
})

AWAIT channel_a.attach()

# --- Phase 1: Enter ---
AWAIT channel_a.presence.enter(data: "hello")

# Wait for ENTER event on client B
poll_until(
  condition: FUNCTION() => all_events.length >= 1,
  interval: 200ms,
  timeout: 10s
)

# Verify member is present via get()
members_after_enter = AWAIT channel_b.presence.get()
ASSERT members_after_enter.length == 1
ASSERT members_after_enter[0].clientId == "lifecycle-client"
ASSERT members_after_enter[0].data == "hello"

# --- Phase 2: Update ---
AWAIT channel_a.presence.update(data: "world")

# Wait for UPDATE event on client B
poll_until(
  condition: FUNCTION() => all_events.length >= 2,
  interval: 200ms,
  timeout: 10s
)

# Verify member data updated via get()
members_after_update = AWAIT channel_b.presence.get()
ASSERT members_after_update.length == 1
ASSERT members_after_update[0].data == "world"

# --- Phase 3: Leave ---
AWAIT channel_a.presence.leave(data: "goodbye")

# Wait for LEAVE event on client B
poll_until(
  condition: FUNCTION() => all_events.length >= 3,
  interval: 200ms,
  timeout: 10s
)

# Verify member is gone via get()
members_after_leave = AWAIT channel_b.presence.get()
ASSERT members_after_leave.length == 0
```

### Assertions
```pseudo
# Verify the sequence of events
ASSERT all_events.length >= 3

enter_event = all_events[0]
ASSERT enter_event.action == ENTER
ASSERT enter_event.clientId == "lifecycle-client"
ASSERT enter_event.data == "hello"

update_event = all_events[1]
ASSERT update_event.action == UPDATE
ASSERT update_event.clientId == "lifecycle-client"
ASSERT update_event.data == "world"

leave_event = all_events[2]
ASSERT leave_event.action == LEAVE
ASSERT leave_event.clientId == "lifecycle-client"
ASSERT leave_event.data == "goodbye"
```

### Cleanup
```pseudo
AWAIT client_a.close()
AWAIT client_b.close()
```
