# PresenceMap Tests

Spec points: `RTP2`, `RTP2a`, `RTP2b`, `RTP2b1`, `RTP2b1a`, `RTP2b2`, `RTP2c`, `RTP2d`, `RTP2d1`, `RTP2d2`, `RTP2h`, `RTP2h1`, `RTP2h1a`, `RTP2h1b`, `RTP2h2`, `RTP2h2a`, `RTP2h2b`

## Test Type
Unit test — pure data structure, no mocks required.

## Purpose

Tests the `PresenceMap` data structure that maintains a map of members currently present
on a channel. The map is keyed by `memberKey` (TP3h: `connectionId:clientId`) and stores
`PresenceMessage` values with action set to `PRESENT` (or `ABSENT` during sync).

This is a portable data structure test — no WebSocket, connection, or channel infrastructure
is needed. Tests operate directly on the PresenceMap by calling `put()` and `remove()` with
constructed `PresenceMessage` objects.

## Interface Under Test

```
PresenceMap:
  put(message: PresenceMessage) -> PresenceMessage?   # returns message to emit, or null if stale
  remove(message: PresenceMessage) -> PresenceMessage? # returns LEAVE to emit, or null
  get(memberKey: String) -> PresenceMessage?
  values() -> List<PresenceMessage>                    # only PRESENT members
  clear()
  startSync()
  endSync() -> List<PresenceMessage>                   # returns synthesized LEAVE events
  isSyncInProgress -> bool
```

---

## RTP2 - Basic put and get

**Test ID**: `realtime/unit/RTP2/basic-put-and-get-0`

**Spec requirement:** Use a PresenceMap to maintain a list of members present on a channel,
a map of memberKeys to presence messages.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
msg = PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000
)
result = map.put(msg)
```

### Assertions
```pseudo
ASSERT result IS NOT null
ASSERT map.get("conn-1:client-1") IS NOT null
ASSERT map.get("conn-1:client-1").clientId == "client-1"
ASSERT map.get("conn-1:client-1").connectionId == "conn-1"
```

---

## RTP2d2 - ENTER stored as PRESENT

**Test ID**: `realtime/unit/RTP2d2/enter-stored-as-present-0`

**Spec requirement:** When an ENTER, UPDATE, or PRESENT message is received, add to the
presence map with action set to PRESENT.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
enter_msg = PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000,
  data: "entered"
)
map.put(enter_msg)
```

### Assertions
```pseudo
stored = map.get("conn-1:client-1")
ASSERT stored IS NOT null
ASSERT stored.action == PRESENT    # RTP2d2: stored as PRESENT regardless of original action
ASSERT stored.data == "entered"
```

---

## RTP2d2 - UPDATE stored as PRESENT

**Test ID**: `realtime/unit/RTP2d2/update-stored-as-present-1`

**Spec requirement:** UPDATE messages are also stored with action PRESENT.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# First enter
map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000,
  data: "initial"
))

# Then update
map.put(PresenceMessage(
  action: UPDATE,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:1:0",
  timestamp: 2000,
  data: "updated"
))
```

### Assertions
```pseudo
stored = map.get("conn-1:client-1")
ASSERT stored.action == PRESENT
ASSERT stored.data == "updated"
```

---

## RTP2d2 - PRESENT stored as PRESENT

**Test ID**: `realtime/unit/RTP2d2/present-stored-as-present-2`

**Spec requirement:** PRESENT messages (from SYNC) are stored with action PRESENT.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(
  action: PRESENT,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000
))
```

### Assertions
```pseudo
stored = map.get("conn-1:client-1")
ASSERT stored IS NOT null
ASSERT stored.action == PRESENT
```

---

## RTP2d1 - put returns message with original action

**Test ID**: `realtime/unit/RTP2d1/put-returns-original-action-0`

**Spec requirement:** Emit to subscribers with the original action (ENTER, UPDATE, or PRESENT),
not the stored PRESENT action.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
emitted_enter = map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000
))

emitted_update = map.put(PresenceMessage(
  action: UPDATE,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:1:0",
  timestamp: 2000,
  data: "updated"
))
```

### Assertions
```pseudo
ASSERT emitted_enter IS NOT null
ASSERT emitted_enter.action == ENTER     # Original action preserved for emission

ASSERT emitted_update IS NOT null
ASSERT emitted_update.action == UPDATE   # Original action preserved for emission
```

---

## RTP2h1 - LEAVE outside sync removes member

**Test ID**: `realtime/unit/RTP2h1/leave-outside-sync-removes-0`

**Spec requirement:** When a LEAVE message is received and SYNC is NOT in progress,
emit LEAVE and delete from presence map.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# Add a member
map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000
))

# Remove the member
emitted = map.remove(PresenceMessage(
  action: LEAVE,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:1:0",
  timestamp: 2000
))
```

### Assertions
```pseudo
# RTP2h1a: Emit LEAVE to subscribers
ASSERT emitted IS NOT null
ASSERT emitted.action == LEAVE

# RTP2h1b: Delete from presence map
ASSERT map.get("conn-1:client-1") IS null
ASSERT map.values().length == 0
```

---

## RTP2h1 - LEAVE for non-existent member returns null

**Test ID**: `realtime/unit/RTP2h1/leave-nonexistent-returns-null-1`

**Spec requirement:** If there is no matching memberKey in the map, there is nothing to remove.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
emitted = map.remove(PresenceMessage(
  action: LEAVE,
  clientId: "unknown",
  connectionId: "conn-x",
  id: "conn-x:0:0",
  timestamp: 1000
))
```

### Assertions
```pseudo
ASSERT emitted IS null
```

---

## RTP2h2a - LEAVE during sync stores as ABSENT

**Test ID**: `realtime/unit/RTP2h2a/leave-during-sync-stores-absent-0`

**Spec requirement:** If a SYNC is in progress and a LEAVE message is received,
store the member in the presence map with action set to ABSENT.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# Add a member
map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000
))

# Start sync
map.startSync()

# LEAVE during sync
emitted = map.remove(PresenceMessage(
  action: LEAVE,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:1:0",
  timestamp: 2000
))
```

### Assertions
```pseudo
# No LEAVE emitted during sync
ASSERT emitted IS null

# Member is stored as ABSENT (not deleted)
stored = map.get("conn-1:client-1")
ASSERT stored IS NOT null
ASSERT stored.action == ABSENT
```

---

## RTP2h2b - ABSENT members deleted on endSync

**Test ID**: `realtime/unit/RTP2h2b/absent-deleted-on-endsync-0`

**Spec requirement:** When SYNC completes, delete all members with action ABSENT.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# Add two members
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100))
map.put(PresenceMessage(action: ENTER, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100))

# Start sync
map.startSync()

# Alice gets updated during sync (still present)
map.put(PresenceMessage(action: PRESENT, clientId: "alice", connectionId: "c1", id: "c1:1:0", timestamp: 200))

# Bob sends LEAVE during sync (stored as ABSENT)
map.remove(PresenceMessage(action: LEAVE, clientId: "bob", connectionId: "c2", id: "c2:1:0", timestamp: 200))

# End sync
leave_events = map.endSync()
```

### Assertions
```pseudo
# Bob's ABSENT entry was deleted
ASSERT map.get("c2:bob") IS null

# Alice remains
ASSERT map.get("c1:alice") IS NOT null
ASSERT map.get("c1:alice").action == PRESENT

ASSERT map.values().length == 1
```

---

## RTP2b2 - Newness comparison by id (msgSerial:index)

**Test ID**: `realtime/unit/RTP2b2/newness-by-msgserial-index-0`

**Spec requirement:** When the connectionId IS an initial substring of the message id,
split the id into `connectionId:msgSerial:index` and compare msgSerial then index numerically.
Larger values are newer.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# Add initial message with msgSerial=5, index=0
map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:5:0",
  timestamp: 1000,
  data: "first"
))

# Try to put an older message (msgSerial=3)
stale_result = map.put(PresenceMessage(
  action: UPDATE,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:3:0",
  timestamp: 2000,
  data: "stale"
))

# Put a newer message (msgSerial=7)
newer_result = map.put(PresenceMessage(
  action: UPDATE,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:7:0",
  timestamp: 500,
  data: "newer"
))
```

### Assertions
```pseudo
# Stale message rejected (RTP2a)
ASSERT stale_result IS null
ASSERT map.get("conn-1:client-1").data == "first"

# Newer message accepted (even though timestamp is older)
ASSERT newer_result IS NOT null
ASSERT map.get("conn-1:client-1").data == "newer"
```

---

## RTP2b2 - Newness comparison by index when msgSerial equal

**Test ID**: `realtime/unit/RTP2b2/newness-by-index-same-serial-1`

**Spec requirement:** When msgSerial values are equal, compare by index.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:5:2",
  timestamp: 1000,
  data: "index-2"
))

# Same msgSerial, lower index — stale
stale = map.put(PresenceMessage(
  action: UPDATE,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:5:1",
  timestamp: 2000,
  data: "index-1"
))

# Same msgSerial, higher index — newer
newer = map.put(PresenceMessage(
  action: UPDATE,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:5:5",
  timestamp: 500,
  data: "index-5"
))
```

### Assertions
```pseudo
ASSERT stale IS null
ASSERT newer IS NOT null
ASSERT map.get("conn-1:client-1").data == "index-5"
```

---

## RTP2b1 - Newness comparison by timestamp (synthesized leave)

**Test ID**: `realtime/unit/RTP2b1/newness-by-timestamp-0`

**Spec requirement:** If either message has a connectionId which is NOT an initial substring
of its id, compare by timestamp. This handles "synthesized leave" events where the server
generates a LEAVE on behalf of a disconnected client.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
# Add member with normal id (connectionId is prefix of id)
map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000,
  data: "entered"
))

# Synthesized leave: id does NOT start with connectionId
# (server-generated, uses a different id format)
synth_leave = map.remove(PresenceMessage(
  action: LEAVE,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "synthesized-leave-id",
  timestamp: 2000
))
```

### Assertions
```pseudo
# Timestamp 2000 > 1000, so the synthesized leave is newer
ASSERT synth_leave IS NOT null
ASSERT synth_leave.action == LEAVE
ASSERT map.get("conn-1:client-1") IS null
```

---

## RTP2b1 - Synthesized leave rejected when older by timestamp

**Test ID**: `realtime/unit/RTP2b1/older-synth-leave-rejected-1`

**Spec requirement:** When comparing by timestamp, an older synthesized leave is rejected.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 5000,
  data: "entered"
))

# Synthesized leave with older timestamp
result = map.remove(PresenceMessage(
  action: LEAVE,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "synthesized-leave-id",
  timestamp: 3000
))
```

### Assertions
```pseudo
# Rejected — existing message (timestamp 5000) is newer
ASSERT result IS null
ASSERT map.get("conn-1:client-1") IS NOT null
ASSERT map.get("conn-1:client-1").data == "entered"
```

---

## RTP2b1a - Equal timestamps: incoming message is newer

**Test ID**: `realtime/unit/RTP2b1a/equal-timestamps-incoming-wins-0`

**Spec requirement:** If timestamps are equal, the newly-incoming message is considered newer.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "synthesized-id-1",
  timestamp: 1000,
  data: "first"
))

# Same timestamp, incoming wins
result = map.put(PresenceMessage(
  action: UPDATE,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "synthesized-id-2",
  timestamp: 1000,
  data: "second"
))
```

### Assertions
```pseudo
ASSERT result IS NOT null
ASSERT map.get("conn-1:client-1").data == "second"
```

---

## RTP2c - SYNC messages use same newness comparison

**Test ID**: `realtime/unit/RTP2c/sync-uses-same-newness-0`

**Spec requirement:** Presence events from a SYNC must be compared for newness
the same way as PRESENCE messages.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
map.startSync()

# First SYNC message
map.put(PresenceMessage(
  action: PRESENT,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:5:0",
  timestamp: 1000,
  data: "sync-first"
))

# Second SYNC message with older serial — rejected
stale = map.put(PresenceMessage(
  action: PRESENT,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:3:0",
  timestamp: 2000,
  data: "sync-stale"
))

# Third SYNC message with newer serial — accepted
newer = map.put(PresenceMessage(
  action: PRESENT,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:8:0",
  timestamp: 500,
  data: "sync-newer"
))
```

### Assertions
```pseudo
ASSERT stale IS null
ASSERT newer IS NOT null
ASSERT map.get("conn-1:client-1").data == "sync-newer"
```

---

## RTP2 - Multiple members coexist

**Test ID**: `realtime/unit/RTP2/multiple-members-coexist-1`

**Spec requirement:** The presence map maintains multiple members with different memberKeys.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100))
map.put(PresenceMessage(action: ENTER, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100))
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c3", id: "c3:0:0", timestamp: 100))
```

### Assertions
```pseudo
# Three distinct members (alice on c1, bob on c2, alice on c3)
ASSERT map.values().length == 3
ASSERT map.get("c1:alice") IS NOT null
ASSERT map.get("c2:bob") IS NOT null
ASSERT map.get("c3:alice") IS NOT null
```

---

## RTP2 - values() excludes ABSENT members

**Test ID**: `realtime/unit/RTP2/values-excludes-absent-2`

**Spec requirement:** The values() method returns only PRESENT members.

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100))
map.put(PresenceMessage(action: ENTER, clientId: "bob", connectionId: "c2", id: "c2:0:0", timestamp: 100))

# Start sync and mark bob as ABSENT
map.startSync()
map.remove(PresenceMessage(action: LEAVE, clientId: "bob", connectionId: "c2", id: "c2:1:0", timestamp: 200))
```

### Assertions
```pseudo
# Bob is stored as ABSENT but excluded from values()
ASSERT map.get("c2:bob") IS NOT null
ASSERT map.get("c2:bob").action == ABSENT

members = map.values()
ASSERT members.length == 1
ASSERT members[0].clientId == "alice"
```

---

## clear() resets all state

**Test ID**: `realtime/unit/RTP2/clear-resets-state-3`

### Setup
```pseudo
map = PresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "c1", id: "c1:0:0", timestamp: 100))
map.startSync()

map.clear()
```

### Assertions
```pseudo
ASSERT map.values().length == 0
ASSERT map.get("c1:alice") IS null
ASSERT map.isSyncInProgress == false
```
