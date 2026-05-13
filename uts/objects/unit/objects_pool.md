# ObjectsPool Tests

Spec points: `RTO3`–`RTO9`

## Test Type
Unit test — pure data structure, no mocks required.

## Purpose

Tests the `ObjectsPool` internal data structure and sync state machine. ObjectsPool is a `Dict<String, LiveObject>` that manages all objects on a channel. It processes ATTACHED messages (to determine sync mode), OBJECT_SYNC messages (to build state from server), and OBJECT messages (to apply operations). It maintains a SyncObjectsPool for accumulating sync data, buffers operations during SYNCING, and manages the INITIALIZED -> SYNCING -> SYNCED state transitions.

Tests operate directly on ObjectsPool by calling `processAttached()`, `processObjectSync()`, and `processObjectMessage()`.

## Shared Helpers

See `helpers/standard_test_pool.md` for builder functions and STANDARD_POOL_OBJECTS.

---

## RTO3 - ObjectsPool initialization with root LiveMap

**Test ID**: `objects/unit/RTO3/pool-init-root-0`

| Spec | Requirement |
|------|-------------|
| RTO3a | ObjectsPool is Dict<String, LiveObject> |
| RTO3b | Must always contain a LiveMap with id "root" |
| RTO3b1 | On initialization, create zero-value LiveMap with objectId "root" |

### Setup
```pseudo
pool = ObjectsPool()
```

### Assertions
```pseudo
ASSERT "root" IN pool
ASSERT pool["root"] IS LiveMap
ASSERT pool["root"].data == {}
ASSERT pool["root"].objectId == "root"
```

---

## RTO4a - ATTACHED with HAS_OBJECTS flag starts SYNCING

**Test ID**: `objects/unit/RTO4/attached-has-objects-syncing-0`

| Spec | Requirement |
|------|-------------|
| RTO4c | Sync state transitions to SYNCING |
| RTO4d | bufferedObjectOperations cleared |
| RTO4a | HAS_OBJECTS=1 means server will send OBJECT_SYNC |

### Setup
```pseudo
pool = ObjectsPool()
```

### Test Steps
```pseudo
pool.processAttached(ProtocolMessage(
  action: ATTACHED,
  channel: "test",
  channelSerial: "sync1:cursor",
  flags: HAS_OBJECTS
))
```

### Assertions
```pseudo
ASSERT pool.syncState == SYNCING
```

---

## RTO4b - ATTACHED without HAS_OBJECTS clears pool and goes to SYNCED

**Test ID**: `objects/unit/RTO4b/attached-no-objects-synced-0`

| Spec | Requirement |
|------|-------------|
| RTO4b1 | Remove all objects except root |
| RTO4b2 | Clear root LiveMap data to zero-value |
| RTO4b2a | Emit LiveMapUpdate for root with removed entries |
| RTO4b4 | Perform sync completion actions |

### Setup
```pseudo
pool = ObjectsPool()
pool["counter:abc@1000"] = LiveCounter(objectId: "counter:abc@1000")
pool["root"].data = {
  "name": { data: { string: "Alice" }, timeserial: "01", tombstone: false }
}
```

### Test Steps
```pseudo
updates = []
pool["root"].subscribe((update) => updates.append(update))

pool.processAttached(ProtocolMessage(
  action: ATTACHED,
  channel: "test",
  flags: 0
))
```

### Assertions
```pseudo
ASSERT pool.syncState == SYNCED
ASSERT "counter:abc@1000" NOT IN pool
ASSERT "root" IN pool
ASSERT pool["root"].data == {}
ASSERT updates.length >= 1
ASSERT updates[0].update == { "name": "removed" }
```

---

## RTO5 - OBJECT_SYNC complete sequence

**Test ID**: `objects/unit/RTO5/sync-complete-sequence-0`

| Spec | Requirement |
|------|-------------|
| RTO5a1 | channelSerial is "sequenceId:cursor" |
| RTO5a4 | Sync complete when cursor is empty |
| RTO5f1 | Store new entries in SyncObjectsPool |
| RTO5c8 | Transition to SYNCED |

### Setup
```pseudo
pool = ObjectsPool()
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))
```

### Test Steps
```pseudo
pool.processObjectSync(build_object_sync_message("test", "sync1:", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: {
      semantics: "LWW",
      entries: { "name": { data: { string: "Alice" }, timeserial: "t:0" } }
    },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  }),
  build_object_state("counter:abc@1000", {"aaa": "t:0"}, {
    counter: { count: 42 },
    createOp: { counterCreate: { count: 42 } }
  })
]))
```

### Assertions
```pseudo
ASSERT pool.syncState == SYNCED
ASSERT "root" IN pool
ASSERT "counter:abc@1000" IN pool
ASSERT pool["root"].data["name"].data == { string: "Alice" }
ASSERT pool["counter:abc@1000"].data == 42
```

---

## RTO5a2 - New sync sequence discards previous

**Test ID**: `objects/unit/RTO5a2/new-sequence-discards-old-0`

| Spec | Requirement |
|------|-------------|
| RTO5a2a | SyncObjectsPool must be cleared |
| RTO5a2 | New sequence id starts fresh sync |

### Setup
```pseudo
pool = ObjectsPool()
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "seq1:cursor", flags: HAS_OBJECTS
))
pool.processObjectSync(build_object_sync_message("test", "seq1:more", [
  build_object_state("counter:old@1000", {"aaa": "t:0"}, { counter: { count: 10 } })
]))
```

### Test Steps
```pseudo
pool.processObjectSync(build_object_sync_message("test", "seq2:", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: { semantics: "LWW", entries: {} },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  }),
  build_object_state("counter:new@1000", {"aaa": "t:0"}, { counter: { count: 99 } })
]))
```

### Assertions
```pseudo
ASSERT pool.syncState == SYNCED
ASSERT "counter:old@1000" NOT IN pool
ASSERT "counter:new@1000" IN pool
```

---

## RTO5f2a - Partial object state merge for maps

**Test ID**: `objects/unit/RTO5f2a/partial-map-merge-0`

| Spec | Requirement |
|------|-------------|
| RTO5f2 | Existing entry: partial state, merge into existing |
| RTO5f2a2 | Merge map entries from incoming into existing |

### Setup
```pseudo
pool = ObjectsPool()
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))
```

### Test Steps
```pseudo
pool.processObjectSync(build_object_sync_message("test", "sync1:more", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: {
      semantics: "LWW",
      entries: { "name": { data: { string: "Alice" }, timeserial: "t:0" } }
    }
  })
]))

pool.processObjectSync(build_object_sync_message("test", "sync1:", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: {
      semantics: "LWW",
      entries: { "age": { data: { number: 30 }, timeserial: "t:0" } }
    },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  })
]))
```

### Assertions
```pseudo
ASSERT pool["root"].data["name"].data == { string: "Alice" }
ASSERT pool["root"].data["age"].data == { number: 30 }
```

---

## RTO5c2 - Sync completion removes objects not in sync

**Test ID**: `objects/unit/RTO5c2/remove-absent-objects-0`

| Spec | Requirement |
|------|-------------|
| RTO5c2 | Remove objects not received during sync |
| RTO5c2a | root must not be removed |

### Setup
```pseudo
pool = ObjectsPool()
pool["counter:old@1000"] = LiveCounter(objectId: "counter:old@1000")
pool["counter:old@1000"].data = 99
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))
```

### Test Steps
```pseudo
pool.processObjectSync(build_object_sync_message("test", "sync1:", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: { semantics: "LWW", entries: {} },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  })
]))
```

### Assertions
```pseudo
ASSERT "counter:old@1000" NOT IN pool
ASSERT "root" IN pool
```

---

## RTO5c9 - Sync completion clears appliedOnAckSerials

**Test ID**: `objects/unit/RTO5c9/clear-applied-on-ack-serials-0`

**Spec requirement:** appliedOnAckSerials set must be cleared after sync.

### Setup
```pseudo
pool = ObjectsPool()
pool.appliedOnAckSerials = {"serial-1", "serial-2"}
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))
```

### Test Steps
```pseudo
pool.processObjectSync(build_object_sync_message("test", "sync1:", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: { semantics: "LWW", entries: {} },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  })
]))
```

### Assertions
```pseudo
ASSERT pool.appliedOnAckSerials == {}
```

---

## RTO7, RTO8a - OBJECT messages buffered during SYNCING

**Test ID**: `objects/unit/RTO8a/buffer-during-syncing-0`

| Spec | Requirement |
|------|-------------|
| RTO8a | If sync state is not SYNCED, buffer ObjectMessages |
| RTO7a | bufferedObjectOperations is an array |

### Setup
```pseudo
pool = ObjectsPool()
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))
```

### Test Steps
```pseudo
pool.processObjectMessage(build_object_message("test", [
  build_counter_inc("counter:abc@1000", 5, "01", "site1")
]))
```

### Assertions
```pseudo
ASSERT pool.syncState == SYNCING
ASSERT pool.bufferedObjectOperations.length == 1
ASSERT "counter:abc@1000" NOT IN pool
```

---

## RTO5c6, RTO8b - Buffered operations applied on sync completion

**Test ID**: `objects/unit/RTO5c6/apply-buffered-on-sync-0`

| Spec | Requirement |
|------|-------------|
| RTO5c6 | Apply buffered operations with source CHANNEL |
| RTO8b | When SYNCED, apply directly |

### Setup
```pseudo
pool = ObjectsPool()
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))

pool.processObjectMessage(build_object_message("test", [
  build_counter_inc("counter:abc@1000", 10, "02", "site1")
]))
```

### Test Steps
```pseudo
pool.processObjectSync(build_object_sync_message("test", "sync1:", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: { semantics: "LWW", entries: {} },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  }),
  build_object_state("counter:abc@1000", {"aaa": "t:0"}, {
    counter: { count: 100 },
    createOp: { counterCreate: { count: 100 } }
  })
]))
```

### Assertions
```pseudo
ASSERT pool["counter:abc@1000"].data == 110
ASSERT pool.bufferedObjectOperations.length == 0
```

---

## RTO9a1 - Null operation is discarded with warning

**Test ID**: `objects/unit/RTO9a1/null-operation-warning-0`

**Spec requirement:** If ObjectMessage.operation is null or omitted, log warning and discard.

### Setup
```pseudo
pool = ObjectsPool()
pool.syncState = SYNCED
```

### Test Steps
```pseudo
pool.processObjectMessage(build_object_message("test", [
  ObjectMessage(serial: "01", siteCode: "site1", operation: null)
]))
```

### Assertions
```pseudo
ASSERT pool.keys().length == 1
```

---

## RTO9a3 - appliedOnAckSerials deduplication

**Test ID**: `objects/unit/RTO9a3/dedup-applied-on-ack-0`

**Spec requirement:** If appliedOnAckSerials contains the serial, log debug, remove from set, and discard.

### Setup
```pseudo
pool = ObjectsPool()
pool.syncState = SYNCED
pool["counter:abc@1000"] = LiveCounter(objectId: "counter:abc@1000")
pool["counter:abc@1000"].data = 10
pool.appliedOnAckSerials = {"echo-serial-1"}
```

### Test Steps
```pseudo
pool.processObjectMessage(build_object_message("test", [
  ObjectMessage(
    serial: "echo-serial-1",
    siteCode: "site1",
    operation: { action: "COUNTER_INC", objectId: "counter:abc@1000", counterInc: { number: 5 } }
  )
]))
```

### Assertions
```pseudo
ASSERT pool["counter:abc@1000"].data == 10
ASSERT "echo-serial-1" NOT IN pool.appliedOnAckSerials
```

---

## RTO9a2a4 - LOCAL source adds serial to appliedOnAckSerials

**Test ID**: `objects/unit/RTO9a2a4/local-source-adds-serial-0`

**Spec requirement:** If source is LOCAL and operation was applied successfully, add serial to appliedOnAckSerials.

### Setup
```pseudo
pool = ObjectsPool()
pool.syncState = SYNCED
pool["counter:abc@1000"] = LiveCounter(objectId: "counter:abc@1000")
```

### Test Steps
```pseudo
pool.applyObjectMessages([
  build_counter_inc("counter:abc@1000", 5, "local-serial-1", "test-site")
], source: LOCAL)
```

### Assertions
```pseudo
ASSERT "local-serial-1" IN pool.appliedOnAckSerials
ASSERT pool["counter:abc@1000"].data == 5
```

---

## RTO9a2b - Unsupported action is discarded with warning

**Test ID**: `objects/unit/RTO9a2b/unsupported-action-warning-0`

**Spec requirement:** Log warning, discard.

### Setup
```pseudo
pool = ObjectsPool()
pool.syncState = SYNCED
```

### Test Steps
```pseudo
pool.processObjectMessage(build_object_message("test", [
  ObjectMessage(
    serial: "01", siteCode: "site1",
    operation: { action: "UNKNOWN_ACTION", objectId: "counter:abc@1000" }
  )
]))
```

### Assertions
```pseudo
ASSERT pool.keys().length == 1
```

---

## RTO6 - Zero-value object creation from objectId prefix

**Test ID**: `objects/unit/RTO6/zero-value-from-prefix-0`

| Spec | Requirement |
|------|-------------|
| RTO6b1 | Parse type from objectId prefix before ":" |
| RTO6b2 | "map" prefix creates zero-value LiveMap |
| RTO6b3 | "counter" prefix creates zero-value LiveCounter |
| RTO6a | Skip if object already exists |

### Setup
```pseudo
pool = ObjectsPool()
pool.syncState = SYNCED
```

### Test Steps
```pseudo
pool.processObjectMessage(build_object_message("test", [
  build_counter_inc("counter:new@2000", 5, "01", "site1")
]))
pool.processObjectMessage(build_object_message("test", [
  build_map_set("map:new@2000", "key", { string: "val" }, "01", "site1")
]))
```

### Assertions
```pseudo
ASSERT "counter:new@2000" IN pool
ASSERT pool["counter:new@2000"] IS LiveCounter
ASSERT pool["counter:new@2000"].data == 5

ASSERT "map:new@2000" IN pool
ASSERT pool["map:new@2000"] IS LiveMap
ASSERT pool["map:new@2000"].data["key"].data == { string: "val" }
```

---

## RTO5d - OBJECT_SYNC with null object field is skipped

**Test ID**: `objects/unit/RTO5d/null-object-skipped-0`

**Spec requirement:** If ObjectMessage.object is null or omitted, skip processing.

### Setup
```pseudo
pool = ObjectsPool()
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))
```

### Test Steps
```pseudo
pool.processObjectSync(build_object_sync_message("test", "sync1:", [
  ObjectMessage(object: null),
  build_object_state("root", {"aaa": "t:0"}, {
    map: { semantics: "LWW", entries: {} },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  })
]))
```

### Assertions
```pseudo
ASSERT pool.syncState == SYNCED
```

---

## RTO5f3 - OBJECT_SYNC with unsupported object type is skipped

**Test ID**: `objects/unit/RTO5f3/unsupported-type-skipped-0`

**Spec requirement:** If neither map nor counter is present, log warning and skip.

### Setup
```pseudo
pool = ObjectsPool()
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))
```

### Test Steps
```pseudo
pool.processObjectSync(build_object_sync_message("test", "sync1:", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: { semantics: "LWW", entries: {} },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  }),
  ObjectMessage(object: { objectId: "unknown:xyz@1000", siteTimeserials: {} })
]))
```

### Assertions
```pseudo
ASSERT pool.syncState == SYNCED
ASSERT "unknown:xyz@1000" NOT IN pool
```

---

## RTO5e - OBJECT_SYNC transitions to SYNCING

**Test ID**: `objects/unit/RTO5e/object-sync-transitions-syncing-0`

**Spec requirement:** When OBJECT_SYNC received, sync state must transition to SYNCING if not already.

### Setup
```pseudo
pool = ObjectsPool()
```

### Test Steps
```pseudo
pool.processObjectSync(build_object_sync_message("test", "sync1:more", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: { semantics: "LWW", entries: {} }
  })
]))
```

### Assertions
```pseudo
ASSERT pool.syncState == SYNCING
```

---

## RTO5c7 - Sync completion emits updates for existing objects

**Test ID**: `objects/unit/RTO5c7/sync-emits-updates-0`

**Spec requirement:** For each previously existing object updated by sync, emit the stored LiveObjectUpdate.

### Setup
```pseudo
pool = ObjectsPool()
pool["root"].data = {
  "name": { data: { string: "Old" }, timeserial: "01", tombstone: false }
}

updates = []
pool["root"].subscribe((update) => updates.append(update))

pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))
```

### Test Steps
```pseudo
pool.processObjectSync(build_object_sync_message("test", "sync1:", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: {
      semantics: "LWW",
      entries: { "name": { data: { string: "New" }, timeserial: "t:0" } }
    },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  })
]))
```

### Assertions
```pseudo
ASSERT updates.length >= 1
ASSERT "name" IN updates[0].update
ASSERT updates[0].update["name"] == "updated"
```

---

## RTO5f2b - Partial counter state logs error

**Test ID**: `objects/unit/RTO5f2b/partial-counter-error-0`

**Spec requirement:** If counter is present on partial merge, log error and skip.

### Setup
```pseudo
pool = ObjectsPool()
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))
```

### Test Steps
```pseudo
pool.processObjectSync(build_object_sync_message("test", "sync1:more", [
  build_object_state("counter:abc@1000", {"aaa": "t:0"}, { counter: { count: 10 } })
]))
pool.processObjectSync(build_object_sync_message("test", "sync1:", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: { semantics: "LWW", entries: {} },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  }),
  build_object_state("counter:abc@1000", {"aaa": "t:0"}, { counter: { count: 5 } })
]))
```

### Assertions
```pseudo
ASSERT pool["counter:abc@1000"].data == 10
```

---

## RTO4d - ATTACHED clears buffered operations

**Test ID**: `objects/unit/RTO4d/attached-clears-buffer-0`

**Spec requirement:** On ATTACHED, bufferedObjectOperations is cleared.

### Setup
```pseudo
pool = ObjectsPool()
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))

pool.processObjectMessage(build_object_message("test", [
  build_counter_inc("counter:abc@1000", 5, "01", "site1")
]))
ASSERT pool.bufferedObjectOperations.length == 1
```

### Test Steps
```pseudo
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync2:cursor", flags: HAS_OBJECTS
))
```

### Assertions
```pseudo
ASSERT pool.bufferedObjectOperations.length == 0
```

---

## RTO4, RTO5 - ATTACHED during SYNCING resets sync

**Test ID**: `objects/unit/RTO4-RTO5/attached-during-syncing-resets-0`

**Spec requirement:** A new ATTACHED message during SYNCING resets the sync state machine.

### Setup
```pseudo
pool = ObjectsPool()
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))
pool.processObjectSync(build_object_sync_message("test", "sync1:more", [
  build_object_state("counter:old@1000", {"aaa": "t:0"}, { counter: { count: 10 } })
]))
ASSERT pool.syncState == SYNCING
```

### Test Steps
```pseudo
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync2:cursor", flags: HAS_OBJECTS
))

pool.processObjectSync(build_object_sync_message("test", "sync2:", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: { semantics: "LWW", entries: {} },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  }),
  build_object_state("counter:new@1000", {"aaa": "t:0"}, { counter: { count: 99 } })
]))
```

### Assertions
```pseudo
ASSERT pool.syncState == SYNCED
ASSERT "counter:old@1000" NOT IN pool
ASSERT "counter:new@1000" IN pool
```

---

## RTO5, RTO7 - New OBJECT_SYNC sequence does NOT clear buffer

**Test ID**: `objects/unit/RTO5-RTO7/new-sync-keeps-buffer-0`

**Spec requirement:** When a new OBJECT_SYNC sequence starts (RTO5a2), only the SyncObjectsPool is discarded. Buffered OBJECT messages are retained for application after sync completion.

### Setup
```pseudo
pool = ObjectsPool()
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))

pool.processObjectMessage(build_object_message("test", [
  build_counter_inc("counter:abc@1000", 5, "01", "site1")
]))
ASSERT pool.bufferedObjectOperations.length == 1
```

### Test Steps
```pseudo
pool.processObjectSync(build_object_sync_message("test", "seq2:", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: { semantics: "LWW", entries: {} },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  }),
  build_object_state("counter:abc@1000", {"aaa": "t:0"}, {
    counter: { count: 100 },
    createOp: { counterCreate: { count: 100 } }
  })
]))
```

### Assertions
```pseudo
ASSERT pool.syncState == SYNCED
ASSERT pool["counter:abc@1000"].data == 105
```

---

## RTO7, RTO8 - OBJECT messages buffered even without preceding ATTACHED

**Test ID**: `objects/unit/RTO7-RTO8/buffer-without-attached-0`

**Spec requirement:** RTO8a: if sync state is not SYNCED, buffer ObjectMessages. This applies regardless of whether ATTACHED was received — INITIALIZED state also buffers.

### Setup
```pseudo
pool = ObjectsPool()
ASSERT pool.syncState == INITIALIZED
```

### Test Steps
```pseudo
pool.processObjectMessage(build_object_message("test", [
  build_counter_inc("counter:abc@1000", 5, "01", "site1")
]))
```

### Assertions
```pseudo
ASSERT pool.bufferedObjectOperations.length == 1
```

---

## RTO5c, RTLM23 - Sync with clearTimeserial hides initial createOp entries

**Test ID**: `objects/unit/RTO5c-RTLM23/sync-clear-timeserial-hides-create-entries-0`

**Spec requirement:** When a map's ObjectState includes a clearTimeserial, createOp entries with serials <= clearTimeserial are rejected during merge.

### Setup
```pseudo
pool = ObjectsPool()
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))
```

### Test Steps
```pseudo
pool.processObjectSync(build_object_sync_message("test", "sync1:", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: {
      semantics: "LWW",
      entries: {},
      clearTimeserial: "05"
    },
    createOp: {
      mapCreate: {
        semantics: "LWW",
        entries: {
          "old_key": { data: { string: "old" }, timeserial: "03" },
          "new_key": { data: { string: "new" }, timeserial: "07" }
        }
      }
    }
  })
]))
```

### Assertions
```pseudo
ASSERT pool.syncState == SYNCED
ASSERT "old_key" NOT IN pool["root"].data
ASSERT pool["root"].data["new_key"].data == { string: "new" }
```
