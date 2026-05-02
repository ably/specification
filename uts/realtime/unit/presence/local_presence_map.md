# LocalPresenceMap Tests

Spec points: `RTP17`, `RTP17b`, `RTP17h`

## Test Type
Unit test — pure data structure, no mocks required.

## Purpose

Tests the `LocalPresenceMap` (internal PresenceMap per RTP17) that maintains a map of
members entered by the current connection. This map is used for automatic re-entry
(RTP17i, RTP17g) when the channel reattaches.

Key differences from the main PresenceMap:
- Keyed by `clientId` only (RTP17h), not by `memberKey` (`connectionId:clientId`)
- Only stores members matching the current `connectionId` (RTP17b)
- Applies ENTER, PRESENT, UPDATE, and non-synthesized LEAVE events (RTP17b)
- Ignores synthesized LEAVE events — where connectionId is not a prefix of id (RTP17b, per RTP2b1)
- No sync protocol (startSync/endSync) — that is only on the main PresenceMap
- Messages are applied "in the same way as for the normal PresenceMap" (RTP17), including newness comparison (RTP2a, RTP2b)

## Interface Under Test

```
LocalPresenceMap:
  put(message: PresenceMessage)
  remove(message: PresenceMessage) -> bool   # returns true if removed, false if synthesized leave (ignored)
  get(clientId: String) -> PresenceMessage?
  values() -> List<PresenceMessage>
  clear()
```

---

## RTP17h - Keyed by clientId, not memberKey

**Spec requirement:** Unlike the main PresenceMap (keyed by memberKey), the RTP17
PresenceMap must be keyed only by clientId. Otherwise, entries associated with old
connectionIds would never be removed, even if the user deliberately leaves presence.

### Setup
```pseudo
map = LocalPresenceMap()
```

### Test Steps
```pseudo
msg1 = PresenceMessage(
  action: ENTER,
  clientId: "user-1",
  connectionId: "conn-A",
  id: "conn-A:0:0",
  timestamp: 1000,
  data: "first"
)
msg2 = PresenceMessage(
  action: ENTER,
  clientId: "user-1",
  connectionId: "conn-B",
  id: "conn-B:0:0",
  timestamp: 2000,
  data: "second"
)

map.put(msg1)
map.put(msg2)
```

### Assertions
```pseudo
# Only one entry — keyed by clientId, second put overwrites the first
ASSERT map.values().length == 1
ASSERT map.get("user-1") IS NOT null
ASSERT map.get("user-1").data == "second"
ASSERT map.get("user-1").connectionId == "conn-B"
```

---

## RTP17b - ENTER adds to map

**Spec requirement:** Any ENTER event with a connectionId matching the current client's
connectionId should be applied to the RTP17 presence map.

### Setup
```pseudo
map = LocalPresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000,
  data: "hello"
))
```

### Assertions
```pseudo
ASSERT map.get("client-1") IS NOT null
ASSERT map.get("client-1").action == PRESENT  # RTP2d2: stored action is always PRESENT
ASSERT map.get("client-1").data == "hello"
ASSERT map.values().length == 1
```

---

## RTP17b - UPDATE with no prior entry adds to map

**Spec requirement:** ENTER and UPDATE are interchangeable — both add a member to the
map. An UPDATE on a clientId that has no prior entry behaves identically to an ENTER.

### Setup
```pseudo
map = LocalPresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(
  action: UPDATE,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000,
  data: "from-update"
))
```

### Assertions
```pseudo
ASSERT map.get("client-1") IS NOT null
ASSERT map.get("client-1").action == PRESENT  # RTP2d2: stored action is always PRESENT
ASSERT map.get("client-1").data == "from-update"
ASSERT map.values().length == 1
```

---

## RTP17b - ENTER after ENTER overwrites

**Spec requirement:** ENTER and UPDATE are interchangeable. A second ENTER for the same
clientId overwrites the first, just as an UPDATE would.

### Setup
```pseudo
map = LocalPresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000,
  data: "first"
))

map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:1:0",
  timestamp: 2000,
  data: "second"
))
```

### Assertions
```pseudo
ASSERT map.values().length == 1
ASSERT map.get("client-1").action == PRESENT  # RTP2d2: stored action is always PRESENT
ASSERT map.get("client-1").data == "second"
```

---

## RTP17b - UPDATE after ENTER overwrites

**Spec requirement:** UPDATE overwrites a prior ENTER for the same clientId.

### Setup
```pseudo
map = LocalPresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000,
  data: "initial"
))

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
ASSERT map.values().length == 1
ASSERT map.get("client-1").action == PRESENT  # RTP2d2: stored action is always PRESENT
ASSERT map.get("client-1").data == "updated"
```

---

## RTP17b - PRESENT adds to map

**Spec requirement:** Any PRESENT event with a matching connectionId should be applied.

### Setup
```pseudo
map = LocalPresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(
  action: PRESENT,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000,
  data: "present"
))
```

### Assertions
```pseudo
ASSERT map.get("client-1") IS NOT null
ASSERT map.get("client-1").action == PRESENT
ASSERT map.get("client-1").data == "present"
```

---

## RTP17b - Non-synthesized LEAVE removes from map

**Spec requirement:** Any LEAVE event with a connectionId matching the current client's
connectionId that is NOT a synthesized leave should remove the member.

A non-synthesized leave has a connectionId that IS an initial substring of its id
(normal server-delivered leave, e.g. id="conn-1:1:0" starts with connectionId="conn-1").

### Setup
```pseudo
map = LocalPresenceMap()
```

### Test Steps
```pseudo
# Add member
map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000
))

ASSERT map.get("client-1") IS NOT null

# Non-synthesized LEAVE: connectionId "conn-1" IS an initial substring of id "conn-1:1:0"
result = map.remove(PresenceMessage(
  action: LEAVE,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:1:0",
  timestamp: 2000
))
```

### Assertions
```pseudo
ASSERT result == true
ASSERT map.get("client-1") IS null
ASSERT map.values().length == 0
```

---

## RTP17b - Synthesized LEAVE is ignored

**Spec requirement:** A synthesized leave event (where connectionId is NOT an initial
substring of its id, per RTP2b1) should NOT be applied to the RTP17 presence map.
The remove method checks whether the connectionId is a prefix of the message id.
If it is not, the leave is synthesized and the member must NOT be removed.

> **Implementation note:** Synthesized-LEAVE filtering (checking whether the LEAVE's
> connectionId matches the local connection) may be implemented either inside the
> presence map's `remove()` method, or at the calling level (e.g., in RealtimePresence).
> The key requirement is that synthesized LEAVEs are not applied to the local presence
> map — the level at which this is enforced is implementation-dependent.

### Setup
```pseudo
map = LocalPresenceMap()
```

### Test Steps
```pseudo
# Add member
map.put(PresenceMessage(
  action: ENTER,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "conn-1:0:0",
  timestamp: 1000,
  data: "entered"
))

# Synthesized LEAVE: connectionId "conn-1" is NOT an initial substring of id "synthesized-leave-id"
result = map.remove(PresenceMessage(
  action: LEAVE,
  clientId: "client-1",
  connectionId: "conn-1",
  id: "synthesized-leave-id",
  timestamp: 2000
))
```

### Assertions
```pseudo
# remove returns false — synthesized leave was ignored
ASSERT result == false

# Member is still present
ASSERT map.get("client-1") IS NOT null
ASSERT map.get("client-1").data == "entered"
ASSERT map.values().length == 1
```

---

## RTP17 - Multiple clientIds coexist

**Spec requirement:** The local presence map can contain multiple members with different
clientIds (e.g., when a single connection enters presence with multiple clientIds using
enterClient).

### Setup
```pseudo
map = LocalPresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "conn-1", id: "conn-1:0:0", timestamp: 100, data: "alice-data"))
map.put(PresenceMessage(action: ENTER, clientId: "bob", connectionId: "conn-1", id: "conn-1:0:1", timestamp: 100, data: "bob-data"))
map.put(PresenceMessage(action: ENTER, clientId: "carol", connectionId: "conn-1", id: "conn-1:0:2", timestamp: 100, data: "carol-data"))
```

### Assertions
```pseudo
ASSERT map.values().length == 3
ASSERT map.get("alice") IS NOT null
ASSERT map.get("bob") IS NOT null
ASSERT map.get("carol") IS NOT null
ASSERT map.get("alice").data == "alice-data"
ASSERT map.get("bob").data == "bob-data"
ASSERT map.get("carol").data == "carol-data"
```

---

## RTP17 - Remove one of multiple members

### Setup
```pseudo
map = LocalPresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "conn-1", id: "conn-1:0:0", timestamp: 100))
map.put(PresenceMessage(action: ENTER, clientId: "bob", connectionId: "conn-1", id: "conn-1:0:1", timestamp: 100))

map.remove(PresenceMessage(action: LEAVE, clientId: "alice", connectionId: "conn-1", id: "conn-1:1:0", timestamp: 200))
```

### Assertions
```pseudo
ASSERT map.get("alice") IS null
ASSERT map.get("bob") IS NOT null
ASSERT map.values().length == 1
```

---

## clear() resets all state

**Spec requirement (RTP5a):** When the channel enters DETACHED or FAILED state, the
internal PresenceMap is cleared. This ensures members are not automatically re-entered
if the channel later becomes attached.

### Setup
```pseudo
map = LocalPresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "conn-1", id: "conn-1:0:0", timestamp: 100))
map.put(PresenceMessage(action: ENTER, clientId: "bob", connectionId: "conn-1", id: "conn-1:0:1", timestamp: 100))

ASSERT map.values().length == 2

map.clear()
```

### Assertions
```pseudo
ASSERT map.values().length == 0
ASSERT map.get("alice") IS null
ASSERT map.get("bob") IS null
```

---

## RTP17 - Get returns null for unknown clientId

### Setup
```pseudo
map = LocalPresenceMap()
```

### Test Steps
```pseudo
result = map.get("nonexistent")
```

### Assertions
```pseudo
ASSERT result IS null
```

---

## RTP17 - Remove for unknown clientId is a no-op

### Setup
```pseudo
map = LocalPresenceMap()
```

### Test Steps
```pseudo
map.put(PresenceMessage(action: ENTER, clientId: "alice", connectionId: "conn-1", id: "conn-1:0:0", timestamp: 100))

# Remove a clientId that was never added (non-synthesized leave)
map.remove(PresenceMessage(action: LEAVE, clientId: "nonexistent", connectionId: "conn-1", id: "conn-1:1:0", timestamp: 200))
```

### Assertions
```pseudo
# Original member is unaffected
ASSERT map.get("alice") IS NOT null
ASSERT map.values().length == 1
```
