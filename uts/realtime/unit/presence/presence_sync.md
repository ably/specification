# Presence Sync Tests

Spec points: `RTP18`, `RTP18a`, `RTP18b`, `RTP18c`, `RTP19`, `RTP19a`

## Test Type
Unit test — pure data structure, no mocks required.

## Purpose

Tests the sync protocol on the `PresenceMap` data structure. A presence sync allows the
server to send a complete list of members present on a channel. The sync lifecycle is:
1. `startSync()` — marks existing members as potentially stale (residual)
2. `put()` during sync — marks members as current (removes from residual set)
3. `endSync()` — removes stale members not seen during sync, returns synthesized LEAVE events

These tests operate directly on the PresenceMap, verifying the sync lifecycle without
any WebSocket, connection, or channel infrastructure.

## Interface Under Test

```
PresenceMap:
  put(message: PresenceMessage) -> PresenceMessage?
  remove(message: PresenceMessage) -> PresenceMessage?
  get(memberKey: String) -> PresenceMessage?
  values() -> List<PresenceMessage>
  clear()
  startSync()
  endSync() -> List<PresenceMessage>   # returns synthesized LEAVE events for stale members
  isSyncInProgress -> bool
```

---

## RTP18a - startSync sets isSyncInProgress

**Spec requirement:** A new sync has started. The client library must track that a sync
is in progress.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
ASSERT map.isSyncInProgress == false

map.startSync()
```

### Assertions
```pseudo
ASSERT map.isSyncInProgress == true
```

---

## RTP18b - endSync clears isSyncInProgress

**Spec requirement:** The sync operation has completed once the cursor is empty.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
map.startSync()
ASSERT map.isSyncInProgress == true

map.endSync()
```

### Assertions
```pseudo
ASSERT map.isSyncInProgress == false
```

---

## RTP19 - Stale members get LEAVE events after sync

**Spec requirement:** If the PresenceMap has existing members when a SYNC is started,
members no longer present on the channel are removed from the local PresenceMap once
the sync is complete. A LEAVE event should be emitted for each removed member.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# Pre-populate with two members
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100))
map.put(PresenceMessage(action: ENTER, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100))

ASSERT map.values().length == 2

# Start sync — only alice appears in the sync data
map.startSync()
map.put(PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:1:0", timestamp: 200))

# End sync — bob was not updated, gets removed
leave_events = map.endSync()
```

### Assertions
```pseudo
# Bob gets a synthesized LEAVE
ASSERT leave_events.length == 1
ASSERT leave_events[0].clientId == "bob"
ASSERT leave_events[0].action == LEAVE

# Only alice remains
ASSERT map.values().length == 1
ASSERT map.get("c1:alice") IS NOT null
ASSERT map.get("c2:bob") IS null
```

---

## RTP19 - Synthesized LEAVE has id=null and current timestamp

**Spec requirement:** The PresenceMessage emitted should contain the original attributes
of the presence member with the action set to LEAVE, PresenceMessage#id set to null,
and the timestamp set to the current time.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(
  action: ENTER,
  clientId: "bob",
  connectionId: "c2",
  id: "c2:0:0",
  timestamp: 100,
  data: "bob-data"
))

before_time = NOW()

map.startSync()
# No messages for bob during sync
leave_events = map.endSync()

after_time = NOW()
```

### Assertions
```pseudo
ASSERT leave_events.length == 1

leave = leave_events[0]
ASSERT leave.action == LEAVE
ASSERT leave.clientId == "bob"
ASSERT leave.connectionId == "c2"
ASSERT leave.data == "bob-data"       # Original attributes preserved
ASSERT leave.id IS null               # RTP19: id set to null
ASSERT leave.timestamp >= before_time # RTP19: timestamp set to current time
ASSERT leave.timestamp <= after_time
```

---

## RTP19 - Members updated during sync survive

**Spec requirement:** A member can be added or updated when received in a SYNC message
or when received in a PRESENCE message during the sync process. Members that have been
added or updated should NOT be removed.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# Pre-populate with three members
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100))
map.put(PresenceMessage(action: ENTER, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100))
map.put(PresenceMessage(action: ENTER, clientId: "carol", connectionId: "c3", id: "c3:0:0", timestamp: 100))

map.startSync()

# Alice arrives via SYNC (PRESENT action)
map.put(PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:1:0", timestamp: 200))

# Bob arrives via PRESENCE during sync (UPDATE action)
map.put(PresenceMessage(action: UPDATE, clientId: "bob", connectionId: "c2", id: "c2:1:0", timestamp: 200, data: "new-data"))

# Carol does NOT appear during sync

leave_events = map.endSync()
```

### Assertions
```pseudo
# Only carol is stale
ASSERT leave_events.length == 1
ASSERT leave_events[0].clientId == "carol"

# Alice and bob survive
ASSERT map.values().length == 2
ASSERT map.get("c1:alice") IS NOT null
ASSERT map.get("c2:bob") IS NOT null
ASSERT map.get("c2:bob").data == "new-data"
```

---

## RTP18a - New sync discards previous in-flight sync

**Spec requirement:** If a new sequence identifier is sent from Ably, then the client
library must consider that to be the start of a new sync sequence and any previous
in-flight sync should be discarded.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# Pre-populate
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100))
map.put(PresenceMessage(action: ENTER, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100))

# First sync starts — only alice appears
map.startSync()
map.put(PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:1:0", timestamp: 200))

# Before first sync ends, a NEW sync starts (new sequence identifier)
# This discards the previous sync — bob is no longer marked as residual from the first sync
map.startSync()

# In the new sync, both alice and bob appear
map.put(PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:2:0", timestamp: 300))
map.put(PresenceMessage(action: PRESENT, clientId: "bob", connectionId: "c2", id: "c2:1:0", timestamp: 300))

leave_events = map.endSync()
```

### Assertions
```pseudo
# No stale members — both were seen in the new sync
ASSERT leave_events.length == 0

ASSERT map.values().length == 2
ASSERT map.get("c1:alice") IS NOT null
ASSERT map.get("c2:bob") IS NOT null
```

---

## RTP18c - Single-message sync (no channelSerial)

**Spec requirement:** A SYNC may also be sent with no channelSerial attribute. In this
case, the sync data is entirely contained within that ProtocolMessage. This is modeled
as a startSync + put + endSync in one step.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# Pre-populate with alice and bob
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100))
map.put(PresenceMessage(action: ENTER, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100))

# Single-message sync: start, put one member, end immediately
map.startSync()
map.put(PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:1:0", timestamp: 200))
leave_events = map.endSync()
```

### Assertions
```pseudo
# Bob was not in the sync — gets LEAVE
ASSERT leave_events.length == 1
ASSERT leave_events[0].clientId == "bob"
ASSERT leave_events[0].action == LEAVE

ASSERT map.values().length == 1
ASSERT map.get("c1:alice") IS NOT null
ASSERT map.isSyncInProgress == false
```

---

## RTP19a - ATTACHED without HAS_PRESENCE clears all members

**Spec requirement:** If the PresenceMap has existing members when an ATTACHED message
is received without a HAS_PRESENCE flag, emit a LEAVE event for each existing member
and remove all members from the PresenceMap.

Note: The detection of HAS_PRESENCE is handled by the RealtimeChannel, which calls
PresenceMap methods. At the data structure level, this scenario is equivalent to
startSync() followed immediately by endSync() with no puts — all existing members
become stale and are removed.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# Pre-populate with members
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100, data: "a"))
map.put(PresenceMessage(action: ENTER, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100, data: "b"))
map.put(PresenceMessage(action: ENTER, clientId: "carol", connectionId: "c3", id: "c3:0:0", timestamp: 100, data: "c"))

# No HAS_PRESENCE: immediate sync with no members
map.startSync()
leave_events = map.endSync()
```

### Assertions
```pseudo
# All members get LEAVE events
ASSERT leave_events.length == 3

# Verify each leave preserves original attributes
alice_leave = leave_events.find(e => e.clientId == "alice")
bob_leave = leave_events.find(e => e.clientId == "bob")
carol_leave = leave_events.find(e => e.clientId == "carol")

ASSERT alice_leave IS NOT null
ASSERT alice_leave.action == LEAVE
ASSERT alice_leave.data == "a"
ASSERT alice_leave.id IS null

ASSERT bob_leave IS NOT null
ASSERT bob_leave.action == LEAVE
ASSERT bob_leave.data == "b"
ASSERT bob_leave.id IS null

ASSERT carol_leave IS NOT null
ASSERT carol_leave.action == LEAVE
ASSERT carol_leave.data == "c"
ASSERT carol_leave.id IS null

# Map is empty
ASSERT map.values().length == 0
```

---

## RTP2h2a - LEAVE during sync stored as ABSENT (in sync context)

**Spec requirement:** If a SYNC is in progress and a LEAVE message is received, store
the member with action set to ABSENT. On endSync, ABSENT members are deleted (RTP2h2b).

This test verifies the interaction between LEAVE-during-sync and endSync cleanup.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# Pre-populate
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100))
map.put(PresenceMessage(action: ENTER, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100))

map.startSync()

# Alice appears in sync
map.put(PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:1:0", timestamp: 200))

# Bob sends LEAVE during sync — stored as ABSENT, not emitted yet
leave_result = map.remove(PresenceMessage(action: LEAVE, clientId: "bob", connectionId: "c2", id: "c2:1:0", timestamp: 200))

# Verify bob is ABSENT but still in map
ASSERT leave_result IS null
ASSERT map.get("c2:bob") IS NOT null
ASSERT map.get("c2:bob").action == ABSENT

# End sync
leave_events = map.endSync()
```

### Assertions
```pseudo
# Bob's ABSENT entry is cleaned up on endSync (RTP2h2b) — no synthesized
# LEAVE event is emitted for bob because he was explicitly marked ABSENT
# via a LEAVE message (not stale-by-absence-from-sync). ABSENT members
# are simply deleted on endSync without generating LEAVE events.
# Synthesized LEAVE events (RTP19) are only for PRESENT members that
# were not updated during sync (residuals).
ASSERT leave_events.length == 0
ASSERT map.get("c2:bob") IS null

# Alice survives
ASSERT map.values().length == 1
ASSERT map.get("c1:alice") IS NOT null
```

---

## RTP19 - Empty map sync produces no leave events

**Spec requirement:** If there are no existing members when sync starts, endSync
produces no leave events.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
map.startSync()
map.put(PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100))
leave_events = map.endSync()
```

### Assertions
```pseudo
ASSERT leave_events.length == 0
ASSERT map.values().length == 1
ASSERT map.get("c1:alice") IS NOT null
```

---

## RTP18 - endSync without startSync is a no-op

**Spec requirement:** Calling endSync when no sync is in progress should not
corrupt the map state.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100))

# endSync without startSync
leave_events = map.endSync()
```

### Assertions
```pseudo
ASSERT leave_events.length == 0
ASSERT map.values().length == 1
ASSERT map.get("c1:alice") IS NOT null
ASSERT map.isSyncInProgress == false
```

---

## RTP19 - Stale SYNC message still removes member from residuals

**Spec requirement:** When a member exists from a PRESENCE event and a SYNC starts,
a SYNC message arriving with the same or older id for that member is stale (rejected
by the newness check). However, the member has been "seen" during sync — it must NOT
be evicted as residual on endSync. The residual removal must happen before the newness
check in put().

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# Pre-populate with a member via ENTER
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:5:0", timestamp: 500, data: "original"))

# Start sync
map.startSync()

# SYNC message arrives with OLDER id (stale — same connectionId, lower msgSerial)
result = map.put(PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:3:0", timestamp: 300, data: "stale"))

leave_events = map.endSync()
```

### Assertions
```pseudo
# The stale put was rejected (returns null)
ASSERT result IS null

# But alice must NOT be evicted — she was "seen" during sync
ASSERT leave_events.length == 0
ASSERT map.values().length == 1
ASSERT map.get("c1:alice") IS NOT null

# Original data is preserved (stale message did not overwrite)
ASSERT map.get("c1:alice").data == "original"
```

---

## RTP19 - PRESENCE echoes followed by SYNC preserves all members

**Spec requirement:** When a client enters multiple members, the server echoes each
as a PRESENCE event. When the server subsequently sends a SYNC containing the same
members, all members should survive even though the SYNC messages may have the same
or older ids as the PRESENCE echoes.

This tests the real protocol flow where PRESENCE echoes populate the map before SYNC.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# Simulate server echoing PRESENCE events for 3 members
map.put(PresenceMessage(action: ENTER, clientId: "user-0", connectionId: "c1", id: "c1:0:0", timestamp: 100, data: "data-0"))
map.put(PresenceMessage(action: ENTER, clientId: "user-1", connectionId: "c1", id: "c1:1:0", timestamp: 100, data: "data-1"))
map.put(PresenceMessage(action: ENTER, clientId: "user-2", connectionId: "c1", id: "c1:2:0", timestamp: 100, data: "data-2"))

ASSERT map.values().length == 3

# Server starts SYNC — members already exist from PRESENCE echoes
map.startSync()

# SYNC messages arrive with the SAME ids as the PRESENCE echoes (stale)
map.put(PresenceMessage(action: PRESENT, clientId: "user-0", connectionId: "c1", id: "c1:0:0", timestamp: 100, data: "data-0"))
map.put(PresenceMessage(action: PRESENT, clientId: "user-1", connectionId: "c1", id: "c1:1:0", timestamp: 100, data: "data-1"))
map.put(PresenceMessage(action: PRESENT, clientId: "user-2", connectionId: "c1", id: "c1:2:0", timestamp: 100, data: "data-2"))

leave_events = map.endSync()
```

### Assertions
```pseudo
# No members evicted — all were seen during sync despite stale ids
ASSERT leave_events.length == 0
ASSERT map.values().length == 3

FOR i IN 0..2:
  member = map.get("c1:user-${i}")
  ASSERT member IS NOT null
  ASSERT member.data == "data-${i}"
```

---

## RTP19 - New member added during sync is not stale

**Spec requirement:** A member can be added during the sync process. New members
that did not exist before the sync should survive endSync.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# Pre-populate with alice only
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100))

map.startSync()

# Alice appears in sync
map.put(PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:1:0", timestamp: 200))

# Bob is NEW — entered via PRESENCE message during sync (not from SYNC data)
map.put(PresenceMessage(action: ENTER, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 200))

leave_events = map.endSync()
```

### Assertions
```pseudo
# No leave events — both alice and bob are current
ASSERT leave_events.length == 0
ASSERT map.values().length == 2
ASSERT map.get("c1:alice") IS NOT null
ASSERT map.get("c2:bob") IS NOT null
```
