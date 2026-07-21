# InternalLiveMap Tests

Spec points: `RTLM1`–`RTLM9`, `RTLM14`–`RTLM16`, `RTLM18`–`RTLM19`, `RTLM22`–`RTLM25`, `RTLO3`, `RTLO4a`, `RTLO4e`, `RTLO4g`, `RTLO4h`, `RTLO5`, `RTLO6`

## Test Type
Unit test — pure data structure, no mocks required.

## Purpose

Tests the `InternalLiveMap` LWW-map CRDT data structure. InternalLiveMap holds a dictionary of `ObjectsMapEntry` values with entry-level last-write-wins semantics, supports set/remove/clear operations, create operations (initial entries merge), data replacement during sync, tombstoning, GC of tombstoned entries, diff calculation, and parentReferences maintenance.

Tests operate directly on InternalLiveMap by calling `applyOperation()` and `replaceData()` with constructed messages.

## Shared Helpers

See `helpers/standard_test_pool.md` for builder functions.

---

## RTLM4 - Zero-value InternalLiveMap

**Test ID**: `objects/unit/RTLM4/zero-value-0`

| Spec | Requirement |
|------|-------------|
| RTLM4 | Zero-value InternalLiveMap has empty data map and null clearTimeserial |
| RTLM25 | clearTimeserial initially null |

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
```

### Assertions
```pseudo
ASSERT map.data == {}
ASSERT map.clearTimeserial == null
ASSERT map.isTombstone == false
ASSERT map.createOperationIsMerged == false
ASSERT map.siteTimeserials == {}
```

---

## RTLM7 - MAP_SET creates new entry

**Test ID**: `objects/unit/RTLM7/map-set-new-entry-0`

| Spec | Requirement |
|------|-------------|
| RTLM7b4 | Create new ObjectsMapEntry with data and timeserial |
| RTLM7f | Return LiveMapUpdate with key set to "updated" and objectMessage set to the provided ObjectMessage |

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
```

### Test Steps
```pseudo
msg = build_map_set("root", "name", { string: "Alice" }, "01", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["name"].data == { string: "Alice" }
ASSERT map.data["name"].timeserial == "01"
ASSERT map.data["name"].tombstone == false
ASSERT update.update == { "name": "updated" }
ASSERT update.objectMessage == msg
```

---

## RTLM7 - MAP_SET updates existing entry

**Test ID**: `objects/unit/RTLM7/map-set-update-entry-0`

| Spec | Requirement |
|------|-------------|
| RTLM7a2e | Set data to MapSet.value |
| RTLM7a2b | Set timeserial to the provided serial |
| RTLM7a2c | Set tombstone to false |
| RTLM7f | Return LiveMapUpdate with objectMessage set to the provided ObjectMessage |

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.data = {
  "name": { data: { string: "Alice" }, timeserial: "01", tombstone: false }
}
```

### Test Steps
```pseudo
msg = build_map_set("root", "name", { string: "Bob" }, "02", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["name"].data == { string: "Bob" }
ASSERT map.data["name"].timeserial == "02"
ASSERT update.update == { "name": "updated" }
ASSERT update.objectMessage == msg
```

---

## RTLM9 - LWW rejects stale serial on existing entry

**Test ID**: `objects/unit/RTLM9/lww-reject-stale-0`

| Spec | Requirement |
|------|-------------|
| RTLM9a | Operation serial must be strictly greater than entry serial |
| RTLM9e | Compare lexicographically |

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.data = {
  "name": { data: { string: "Alice" }, timeserial: "05", tombstone: false }
}
```

### Test Steps
```pseudo
msg = build_map_set("root", "name", { string: "Bob" }, "03", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["name"].data == { string: "Alice" }
ASSERT update.noop == true
```

---

## RTLM9 - LWW rejects equal serial

**Test ID**: `objects/unit/RTLM9/lww-reject-equal-0`

**Spec requirement:** Equal serials are rejected — must be strictly greater.

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.data = {
  "name": { data: { string: "Alice" }, timeserial: "05", tombstone: false }
}
```

### Test Steps
```pseudo
msg = build_map_set("root", "name", { string: "Bob" }, "05", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["name"].data == { string: "Alice" }
ASSERT update.noop == true
```

---

## RTLM9b - Both serials empty rejects operation

**Test ID**: `objects/unit/RTLM9b/both-empty-reject-0`

**Spec requirement:** If both the entry serial and operation serial are null/empty, considered equal, so operation is not applied.

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.data = {
  "name": { data: { string: "Alice" }, timeserial: "", tombstone: false }
}
```

### Test Steps
```pseudo
msg = build_map_set("root", "name", { string: "Bob" }, "", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["name"].data == { string: "Alice" }
# The op's ObjectMessage.serial is empty, so the OBJECT-level gate (RTLO4a3, via canApplyOperation)
# rejects it before the entry-level RTLM9b comparison, and applyOperation returns false (RTLM15b).
# (NOTE: RTLM9b's "both serials empty" case is thus unreachable via applyOperation — a spec layering
# tension worth raising upstream; the observable result here is a plain false, not a noop update.)
ASSERT update == false
```

---

## RTLM9d - Missing entry serial allows operation

**Test ID**: `objects/unit/RTLM9d/missing-entry-serial-allows-0`

**Spec requirement:** If only the operation serial exists and is non-empty, it is greater than the missing entry serial.

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.data = {
  "name": { data: { string: "Alice" }, timeserial: null, tombstone: false }
}
```

### Test Steps
```pseudo
msg = build_map_set("root", "name", { string: "Bob" }, "01", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["name"].data == { string: "Bob" }
ASSERT update.update == { "name": "updated" }
ASSERT update.objectMessage == msg
```

---

## RTLM7h - MAP_SET rejected when serial <= clearTimeserial

**Test ID**: `objects/unit/RTLM7h/map-set-clear-timeserial-floor-0`

**Spec requirement:** If clearTimeserial is non-null and >= serial, discard operation.

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.clearTimeserial = "05"
```

### Test Steps
```pseudo
msg = build_map_set("root", "name", { string: "Alice" }, "03", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT "name" NOT IN map.data
ASSERT update.noop == true
```

---

## RTLM7g - MAP_SET with objectId creates zero-value object

**Test ID**: `objects/unit/RTLM7g/map-set-objectid-creates-zero-value-0`

| Spec | Requirement |
|------|-------------|
| RTLM7g | If MapSet.value.objectId is non-empty, create zero-value LiveObject |
| RTLM7g1 | Create via RTO6 |

This test requires an ObjectsPool to be passed alongside the InternalLiveMap. The InternalLiveMap creates a zero-value object in the pool when it encounters an objectId reference.

### Setup
```pseudo
pool = ObjectsPool()
map = InternalLiveMap(objectId: "root", semantics: "LWW", pool: pool)
```

### Test Steps
```pseudo
msg = build_map_set("root", "score", { objectId: "counter:new@2000" }, "01", "site1")
map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT "counter:new@2000" IN pool
ASSERT pool["counter:new@2000"] IS InternalLiveCounter
ASSERT pool["counter:new@2000"].data == 0
```

---

## RTLM8 - MAP_REMOVE tombstones existing entry

**Test ID**: `objects/unit/RTLM8/map-remove-existing-0`

| Spec | Requirement |
|------|-------------|
| RTLM8a2a | Set data to null |
| RTLM8a2b | Set timeserial to serial |
| RTLM8a2c | Set tombstone to true |
| RTLM8a2d | Set tombstonedAt via RTLO6 |
| RTLM8e | Return LiveMapUpdate with key set to "removed" and objectMessage set to the provided ObjectMessage |

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.data = {
  "name": { data: { string: "Alice" }, timeserial: "01", tombstone: false }
}
```

### Test Steps
```pseudo
msg = build_map_remove("root", "name", "02", "site1", 1700000000000)
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["name"].data == null
ASSERT map.data["name"].tombstone == true
ASSERT map.data["name"].timeserial == "02"
ASSERT map.data["name"].tombstonedAt == 1700000000000
ASSERT update.update == { "name": "removed" }
ASSERT update.objectMessage == msg
```

---

## RTLM8 - MAP_REMOVE creates tombstoned entry if not exists

**Test ID**: `objects/unit/RTLM8/map-remove-nonexistent-0`

| Spec | Requirement |
|------|-------------|
| RTLM8b1 | Create new entry with data null and timeserial |
| RTLM8b2 | Set tombstone to true |
| RTLM8b3 | Set tombstonedAt via RTLO6 |
| RTLM8e | Return LiveMapUpdate with objectMessage set to the provided ObjectMessage |

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
```

### Test Steps
```pseudo
msg = build_map_remove("root", "ghost", "01", "site1", 1700000000000)
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["ghost"].tombstone == true
ASSERT map.data["ghost"].tombstonedAt == 1700000000000
ASSERT update.update == { "ghost": "removed" }
ASSERT update.objectMessage == msg
```

---

## RTLM8g - MAP_REMOVE rejected when serial <= clearTimeserial

**Test ID**: `objects/unit/RTLM8g/map-remove-clear-timeserial-floor-0`

**Spec requirement:** If clearTimeserial is non-null and >= serial, discard operation.

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.clearTimeserial = "05"
map.data = {
  "name": { data: { string: "Alice" }, timeserial: "04", tombstone: false }
}
```

### Test Steps
```pseudo
msg = build_map_remove("root", "name", "03", "site1", 1700000000000)
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["name"].data == { string: "Alice" }
ASSERT map.data["name"].tombstone == false
ASSERT update.noop == true
```

---

## RTLM24 - MAP_CLEAR sets clearTimeserial and removes older entries

**Test ID**: `objects/unit/RTLM24/map-clear-basic-0`

| Spec | Requirement |
|------|-------------|
| RTLM24d | Set clearTimeserial to serial |
| RTLM24e1a | Remove entries with timeserial null or < serial |
| RTLM24f | Return LiveMapUpdate with removed keys and objectMessage set to the provided ObjectMessage |

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.data = {
  "old":  { data: { string: "old" },  timeserial: "02", tombstone: false },
  "new":  { data: { string: "new" },  timeserial: "06", tombstone: false },
  "same": { data: { string: "same" }, timeserial: "04", tombstone: false }
}
```

### Test Steps
```pseudo
msg = build_map_clear("root", "04", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.clearTimeserial == "04"
ASSERT "old" NOT IN map.data
# RTLM24e1: an entry is removed only if the clear serial is lexicographically GREATER than the entry's
# timeserial. "same" has timeserial "04" == the clear serial "04" (not greater), so it is KEPT.
ASSERT "same" IN map.data
ASSERT "new" IN map.data
ASSERT update.update == { "old": "removed" }
ASSERT update.objectMessage == msg
```

---

## RTLM24c - MAP_CLEAR rejected when clearTimeserial is already greater

**Test ID**: `objects/unit/RTLM24c/map-clear-stale-0`

**Spec requirement:** If existing clearTimeserial is greater than provided serial, discard.

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.clearTimeserial = "10"
```

### Test Steps
```pseudo
msg = build_map_clear("root", "05", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.clearTimeserial == "10"
ASSERT update.noop == true
```

---

## RTLM16, RTLM23 - MAP_CREATE merges entries

**Test ID**: `objects/unit/RTLM16/map-create-merge-0`

| Spec | Requirement |
|------|-------------|
| RTLM16d | Merge via RTLM23 |
| RTLM23a1 | Non-tombstoned entries merged via MAP_SET logic |
| RTLM23a2 | Tombstoned entries merged via MAP_REMOVE logic |
| RTLM23b | Set createOperationIsMerged to true |
| RTLM23c | Return LiveMapUpdate with merged update map and objectMessage set to the provided ObjectMessage |

### Setup
```pseudo
map = InternalLiveMap(objectId: "map:test@1000", semantics: "LWW")
```

### Test Steps
```pseudo
msg = build_map_create("map:test@1000", {
  semantics: "LWW",
  entries: {
    "name": { data: { string: "Alice" }, timeserial: "01" },
    "removed_key": { tombstone: true, timeserial: "01", serialTimestamp: 1700000000000 }
  }
}, "02", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["name"].data == { string: "Alice" }
ASSERT map.data["removed_key"].tombstone == true
ASSERT map.createOperationIsMerged == true
ASSERT update.update == { "name": "updated", "removed_key": "removed" }
ASSERT update.objectMessage == msg
```

---

## RTLM16b - MAP_CREATE noop when already merged

**Test ID**: `objects/unit/RTLM16b/map-create-already-merged-0`

**Spec requirement:** If createOperationIsMerged is true, return noop.

### Setup
```pseudo
map = InternalLiveMap(objectId: "map:test@1000", semantics: "LWW")
map.createOperationIsMerged = true
map.siteTimeserials = { "site1": "00" }
```

### Test Steps
```pseudo
msg = build_map_create("map:test@1000", {
  semantics: "LWW",
  entries: { "name": { data: { string: "Bob" }, timeserial: "01" } }
}, "01", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT "name" NOT IN map.data
ASSERT update.noop == true
```

---

## RTLM15c - CHANNEL source updates siteTimeserials

**Test ID**: `objects/unit/RTLM15c/channel-source-updates-serials-0`

**Spec requirement:** If source is CHANNEL, set siteTimeserials[siteCode] = serial.

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
```

### Test Steps
```pseudo
msg = build_map_set("root", "x", { number: 1 }, "01", "site1")
map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.siteTimeserials["site1"] == "01"
```

---

## RTLM15e - Operations on tombstoned map are rejected

**Test ID**: `objects/unit/RTLM15e/tombstoned-reject-ops-0`

**Spec requirement:** If isTombstone is true, finish without action, return false.

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.isTombstone = true
```

### Test Steps
```pseudo
msg = build_map_set("root", "x", { number: 1 }, "01", "site1")
result = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT result == false
ASSERT map.data == {}
```

---

## RTLO5 - OBJECT_DELETE tombstones map

**Test ID**: `objects/unit/RTLO5/object-delete-tombstones-map-0`

| Spec | Requirement |
|------|-------------|
| RTLM15d5c | Emit LiveMapUpdate returned by RTLO5 |
| RTLM15d5b | Return true |
| RTLO4e5 | Compute diff for the tombstone update |
| RTLO4e6 | Set tombstone flag on the update |
| RTLO4e7 | Set objectMessage on the update |

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.data = {
  "name": { data: { string: "Alice" }, timeserial: "01", tombstone: false },
  "age":  { data: { number: 30 },      timeserial: "01", tombstone: false }
}
map.siteTimeserials = { "site1": "00" }
```

### Test Steps
```pseudo
msg = build_object_delete("root", "01", "site1", 1700000000000)
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.isTombstone == true
ASSERT map.data == {}
ASSERT update.update == { "name": "removed", "age": "removed" }
ASSERT update.tombstone == true
ASSERT update.objectMessage == msg
```

---

## RTLM14, RTLM14c - Tombstoned entry check includes objectId reference

**Test ID**: `objects/unit/RTLM14/tombstone-check-objectid-ref-0`

| Spec | Requirement |
|------|-------------|
| RTLM14a | Entry is tombstoned if entry.tombstone is true |
| RTLM14c | Entry is tombstoned if referenced LiveObject.isTombstone is true |

### Setup
```pseudo
pool = ObjectsPool()
tombstoned_counter = InternalLiveCounter(objectId: "counter:dead@1000")
tombstoned_counter.isTombstone = true
pool["counter:dead@1000"] = tombstoned_counter

map = InternalLiveMap(objectId: "root", semantics: "LWW", pool: pool)
map.data = {
  "alive":     { data: { string: "ok" },                         timeserial: "01", tombstone: false },
  "dead_entry": { data: null,                                     timeserial: "01", tombstone: true },
  "dead_ref":   { data: { objectId: "counter:dead@1000" },        timeserial: "01", tombstone: false }
}
```

### Assertions
```pseudo
ASSERT isTombstoned(map.data["alive"]) == false
ASSERT isTombstoned(map.data["dead_entry"]) == true
ASSERT isTombstoned(map.data["dead_ref"]) == true
```

---

## RTLM6 - replaceData sets data from ObjectState

**Test ID**: `objects/unit/RTLM6/replace-data-basic-0`

| Spec | Requirement |
|------|-------------|
| RTLM6a | Replace siteTimeserials |
| RTLM6b | Set createOperationIsMerged to false |
| RTLM6i | Set clearTimeserial from ObjectState.map.clearTimeserial |
| RTLM6c | Set data to ObjectState.map.entries |
| RTLM6h | Return diff LiveMapUpdate with objectMessage set to the provided ObjectMessage |

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.data = {
  "old": { data: { string: "old" }, timeserial: "01", tombstone: false }
}
map.createOperationIsMerged = true
```

### Test Steps
```pseudo
state_msg = build_object_state("root", {"site2": "05"}, {
  map: {
    semantics: "LWW",
    clearTimeserial: "03",
    entries: {
      "new": { data: { string: "new" }, timeserial: "04", tombstone: false }
    }
  }
})
update = map.replaceData(state_msg)
```

### Assertions
```pseudo
ASSERT map.siteTimeserials == { "site2": "05" }
ASSERT map.createOperationIsMerged == false
ASSERT map.clearTimeserial == "03"
ASSERT "old" NOT IN map.data
ASSERT map.data["new"].data == { string: "new" }
ASSERT update.update == { "old": "removed", "new": "updated" }
ASSERT update.objectMessage == state_msg
```

---

## RTLM6c1 - replaceData sets tombstonedAt on tombstoned entries

**Test ID**: `objects/unit/RTLM6c1/replace-data-tombstoned-entries-0`

**Spec requirement:** For each tombstoned entry, set tombstonedAt via RTLO6.

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
```

### Test Steps
```pseudo
state_msg = build_object_state("root", {"site1": "01"}, {
  map: {
    semantics: "LWW",
    entries: {
      "dead": { tombstone: true, timeserial: "01", serialTimestamp: 1700000050000 }
    }
  }
})
map.replaceData(state_msg)
```

### Assertions
```pseudo
ASSERT map.data["dead"].tombstonedAt == 1700000050000
```

---

## RTLM6d - replaceData with createOp merges initial entries

**Test ID**: `objects/unit/RTLM6d/replace-data-with-create-op-0`

**Spec requirement:** If createOp present, merge via RTLM23, passing in the ObjectMessage.

### Setup
```pseudo
map = InternalLiveMap(objectId: "map:test@1000", semantics: "LWW")
```

### Test Steps
```pseudo
state_msg = build_object_state("map:test@1000", {"site1": "01"}, {
  map: {
    semantics: "LWW",
    entries: {
      "from_sync": { data: { string: "synced" }, timeserial: "01" }
    }
  },
  createOp: {
    mapCreate: {
      semantics: "LWW",
      entries: {
        "from_create": { data: { string: "created" }, timeserial: "00" }
      }
    }
  }
})
map.replaceData(state_msg)
```

### Assertions
```pseudo
ASSERT map.data["from_sync"].data == { string: "synced" }
ASSERT map.data["from_create"].data == { string: "created" }
ASSERT map.createOperationIsMerged == true
```

---

## RTLM6f - replaceData with tombstone flag tombstones map

**Test ID**: `objects/unit/RTLM6f/replace-data-tombstone-flag-0`

| Spec | Requirement |
|------|-------------|
| RTLM6f | If ObjectState.tombstone is true, tombstone the map via LiveObject.tombstone |
| RTLM6f2 | Return the LiveMapUpdate returned by LiveObject.tombstone |
| RTLO4e6 | Tombstone flag set on the update |
| RTLO4e7 | objectMessage set on the update |

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.data = {
  "name": { data: { string: "Alice" }, timeserial: "01", tombstone: false }
}
```

### Test Steps
```pseudo
state_msg = build_object_state("root", {"site1": "01"}, {
  map: { semantics: "LWW", entries: {} },
  tombstone: true
})
update = map.replaceData(state_msg)
```

### Assertions
```pseudo
ASSERT map.isTombstone == true
ASSERT map.data == {}
ASSERT update.update == { "name": "removed" }
ASSERT update.tombstone == true
ASSERT update.objectMessage == state_msg
```

---

## RTLM19 - GC removes tombstoned entries past grace period

**Test ID**: `objects/unit/RTLM19/gc-tombstoned-entries-0`

**Spec requirement:** Entries where tombstonedAt + gracePeriod <= currentTime are removed.

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
grace_period = 86400000
now = 1700100000000

map.data = {
  "recent_dead": { data: null, timeserial: "01", tombstone: true, tombstonedAt: now - 1000 },
  "old_dead":    { data: null, timeserial: "01", tombstone: true, tombstonedAt: now - grace_period - 1 },
  "alive":       { data: { string: "ok" }, timeserial: "01", tombstone: false }
}
```

### Test Steps
```pseudo
map.gcTombstonedEntries(grace_period, now)
```

### Assertions
```pseudo
ASSERT "recent_dead" IN map.data
ASSERT "old_dead" NOT IN map.data
ASSERT "alive" IN map.data
```

---

## RTLM22 - Diff between two data states

**Test ID**: `objects/unit/RTLM22/diff-calculation-0`

| Spec | Requirement |
|------|-------------|
| RTLM22b1 | Key in previous but not new -> removed |
| RTLM22b2 | Key in new but not previous -> updated |
| RTLM22b3 | Key in both with different data -> updated |
| RTLM22b | Only non-tombstoned entries are considered |

### Setup
```pseudo
previousData = {
  "removed":   { data: { string: "gone" },    timeserial: "01", tombstone: false },
  "changed":   { data: { string: "old" },      timeserial: "01", tombstone: false },
  "unchanged": { data: { string: "same" },     timeserial: "01", tombstone: false },
  "was_dead":  { data: null,                    timeserial: "01", tombstone: true }
}

newData = {
  "added":     { data: { string: "new" },      timeserial: "02", tombstone: false },
  "changed":   { data: { string: "new_val" },  timeserial: "02", tombstone: false },
  "unchanged": { data: { string: "same" },     timeserial: "01", tombstone: false },
  "now_dead":  { data: null,                    timeserial: "02", tombstone: true }
}
```

### Test Steps
```pseudo
update = InternalLiveMap.diff(previousData, newData)
```

### Assertions
```pseudo
ASSERT update.update["removed"] == "removed"
ASSERT update.update["added"] == "updated"
ASSERT update.update["changed"] == "updated"
ASSERT "unchanged" NOT IN update.update
ASSERT "was_dead" NOT IN update.update
ASSERT "now_dead" NOT IN update.update
```

---

## RTLM15d4 - Unsupported action is discarded

**Test ID**: `objects/unit/RTLM15d4/unsupported-action-0`

**Spec requirement:** Log warning, discard, return false.

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
```

### Test Steps
```pseudo
msg = ObjectMessage(
  serial: "01", siteCode: "site1",
  operation: { action: "COUNTER_INC", objectId: "root", counterInc: { number: 5 } }
)
result = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT result == false
```

---

## RTLM6i - replaceData without clearTimeserial resets to null

**Test ID**: `objects/unit/RTLM6i/replace-data-resets-clear-timeserial-0`

**Spec requirement:** If ObjectState.map.clearTimeserial is absent, clearTimeserial is reset to null.

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.clearTimeserial = "05"
map.data = {
  "x": { data: { number: 1 }, timeserial: "03", tombstone: false }
}
```

### Test Steps
```pseudo
state_msg = build_object_state("root", {"site1": "01"}, {
  map: {
    semantics: "LWW",
    entries: {
      "y": { data: { number: 2 }, timeserial: "01" }
    }
  }
})
map.replaceData(state_msg)
```

### Assertions
```pseudo
ASSERT map.clearTimeserial == null
ASSERT "y" IN map.data
```

---

## RTLM14c, RTLM5 - MAP_SET referencing tombstoned objectId yields null value

**Test ID**: `objects/unit/RTLM14c/tombstoned-ref-yields-null-0`

**Spec requirement:** If entry references an objectId whose LiveObject is tombstoned, the entry is treated as tombstoned (RTLM14c). Value resolution returns null.

### Setup
```pseudo
pool = ObjectsPool()
tombstoned_counter = InternalLiveCounter(objectId: "counter:dead@1000")
tombstoned_counter.isTombstone = true
pool["counter:dead@1000"] = tombstoned_counter

map = InternalLiveMap(objectId: "root", semantics: "LWW", pool: pool)
map.data = {
  "ref": { data: { objectId: "counter:dead@1000" }, timeserial: "01", tombstone: false }
}
```

### Assertions
```pseudo
// The entry itself is not tombstoned, but the referenced object is
ASSERT map.data["ref"].tombstone == false
// size() should NOT count this entry because RTLM14c makes it tombstoned
ASSERT map.size() == 0
// get() should return null for the value
ASSERT map.get("ref") == null
```

---

## RTLM7 - MAP_SET revives tombstoned entry

**Test ID**: `objects/unit/RTLM7/map-set-revives-tombstoned-0`

| Spec | Requirement |
|------|-------------|
| RTLM7a2c | Set tombstone to false |
| RTLM7a2d | Set tombstonedAt to null |
| RTLM7f | Return LiveMapUpdate with objectMessage set to the provided ObjectMessage |

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.data = {
  "name": { data: null, timeserial: "01", tombstone: true, tombstonedAt: 1700000000000 }
}
```

### Test Steps
```pseudo
msg = build_map_set("root", "name", { string: "Alice" }, "02", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["name"].data == { string: "Alice" }
ASSERT map.data["name"].tombstone == false
ASSERT map.data["name"].tombstonedAt == null
ASSERT update.update == { "name": "updated" }
ASSERT update.objectMessage == msg
```

---

## RTLM24 - MAP_CLEAR preserves entries with newer serial

**Test ID**: `objects/unit/RTLM24/map-clear-preserves-newer-0`

**Spec requirement:** Only entries with timeserial null or <= serial are removed.

### Setup
```pseudo
map = InternalLiveMap(objectId: "root", semantics: "LWW")
map.data = {
  "before":  { data: { string: "a" }, timeserial: "03", tombstone: false },
  "after":   { data: { string: "b" }, timeserial: "07", tombstone: false },
  "no_ts":   { data: { string: "c" }, timeserial: null,  tombstone: false }
}
```

### Test Steps
```pseudo
msg = build_map_clear("root", "05", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT "before" NOT IN map.data
ASSERT "no_ts" NOT IN map.data
ASSERT map.data["after"].data == { string: "b" }
ASSERT "before" IN update.update
ASSERT "no_ts" IN update.update
ASSERT "after" NOT IN update.update
ASSERT update.objectMessage == msg
```

---

## RTLM7a3, RTLM7g2 - parentReferences: MAP_SET overwrites entry referencing LiveObject

**Test ID**: `objects/unit/RTLM7a3/map-set-overwrite-objectid-parent-refs-0`

| Spec | Requirement |
|------|-------------|
| RTLM7a3a | Before overwriting, check if existing entry has objectId |
| RTLM7a3b | If old entry references a LiveObject, call removeParentReference on old child |
| RTLM7g2 | After setting new objectId value, call addParentReference on new child |

Tests that when MAP_SET overwrites an entry whose value is a LiveObject with a new LiveObject value, removeParentReference is called on the old child and addParentReference is called on the new child.

### Setup
```pseudo
pool = ObjectsPool()
old_counter = InternalLiveCounter(objectId: "counter:old@1000")
new_counter = InternalLiveCounter(objectId: "counter:new@2000")
pool["counter:old@1000"] = old_counter
pool["counter:new@2000"] = new_counter

map = InternalLiveMap(objectId: "root", semantics: "LWW", pool: pool)
map.data = {
  "ref": { data: { objectId: "counter:old@1000" }, timeserial: "01", tombstone: false }
}
// Simulate existing parentReference
old_counter.parentReferences = { "root": {"ref"} }
```

### Test Steps
```pseudo
msg = build_map_set("root", "ref", { objectId: "counter:new@2000" }, "02", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["ref"].data == { objectId: "counter:new@2000" }
// removeParentReference was called on the old child
ASSERT "root" NOT IN old_counter.parentReferences OR "ref" NOT IN old_counter.parentReferences["root"]
// addParentReference was called on the new child
ASSERT "root" IN new_counter.parentReferences
ASSERT "ref" IN new_counter.parentReferences["root"]
ASSERT update.update == { "ref": "updated" }
ASSERT update.objectMessage == msg
```

---

## RTLM7g2 - parentReferences: MAP_SET new entry referencing LiveObject

**Test ID**: `objects/unit/RTLM7g2/map-set-new-entry-add-parent-ref-0`

| Spec | Requirement |
|------|-------------|
| RTLM7g2 | After setting new objectId value, call addParentReference on the new child |

Tests that when MAP_SET creates a new entry whose value is a LiveObject, addParentReference is called on the child.

### Setup
```pseudo
pool = ObjectsPool()
child_counter = InternalLiveCounter(objectId: "counter:child@1000")
pool["counter:child@1000"] = child_counter

map = InternalLiveMap(objectId: "root", semantics: "LWW", pool: pool)
```

### Test Steps
```pseudo
msg = build_map_set("root", "score", { objectId: "counter:child@1000" }, "01", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["score"].data == { objectId: "counter:child@1000" }
ASSERT "root" IN child_counter.parentReferences
ASSERT "score" IN child_counter.parentReferences["root"]
ASSERT update.objectMessage == msg
```

---

## RTLM7 - parentReferences: MAP_SET with non-LiveObject value does not affect parentReferences

**Test ID**: `objects/unit/RTLM7/map-set-primitive-no-parent-refs-0`

**Spec requirement:** parentReferences operations only apply when the entry value contains an objectId. Primitive values do not trigger addParentReference or removeParentReference.

### Setup
```pseudo
pool = ObjectsPool()
old_counter = InternalLiveCounter(objectId: "counter:old@1000")
pool["counter:old@1000"] = old_counter

map = InternalLiveMap(objectId: "root", semantics: "LWW", pool: pool)
map.data = {
  "ref": { data: { objectId: "counter:old@1000" }, timeserial: "01", tombstone: false }
}
old_counter.parentReferences = { "root": {"ref"} }
```

### Test Steps
```pseudo
msg = build_map_set("root", "ref", { string: "plain_value" }, "02", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["ref"].data == { string: "plain_value" }
// removeParentReference was called on old child (entry previously had objectId)
ASSERT "root" NOT IN old_counter.parentReferences OR "ref" NOT IN old_counter.parentReferences["root"]
// No addParentReference call because new value is a primitive
ASSERT update.update == { "ref": "updated" }
ASSERT update.objectMessage == msg
```

---

## RTLM8a3 - parentReferences: MAP_REMOVE entry referencing LiveObject

**Test ID**: `objects/unit/RTLM8a3/map-remove-objectid-parent-refs-0`

| Spec | Requirement |
|------|-------------|
| RTLM8a3a | Before tombstoning, check if existing entry has objectId |
| RTLM8a3b | If entry references a LiveObject, call removeParentReference on the child |

Tests that when MAP_REMOVE tombstones an entry whose value is a LiveObject, removeParentReference is called on the child.

### Setup
```pseudo
pool = ObjectsPool()
child_counter = InternalLiveCounter(objectId: "counter:child@1000")
pool["counter:child@1000"] = child_counter

map = InternalLiveMap(objectId: "root", semantics: "LWW", pool: pool)
map.data = {
  "score": { data: { objectId: "counter:child@1000" }, timeserial: "01", tombstone: false }
}
child_counter.parentReferences = { "root": {"score"} }
```

### Test Steps
```pseudo
msg = build_map_remove("root", "score", "02", "site1", 1700000000000)
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["score"].tombstone == true
// removeParentReference was called on the child
ASSERT "root" NOT IN child_counter.parentReferences OR "score" NOT IN child_counter.parentReferences["root"]
ASSERT update.update == { "score": "removed" }
ASSERT update.objectMessage == msg
```

---

## RTLM8 - parentReferences: MAP_REMOVE entry with non-LiveObject value

**Test ID**: `objects/unit/RTLM8/map-remove-primitive-no-parent-refs-0`

**Spec requirement:** MAP_REMOVE on a primitive-valued entry does not call removeParentReference because there is no objectId.

### Setup
```pseudo
pool = ObjectsPool()
map = InternalLiveMap(objectId: "root", semantics: "LWW", pool: pool)
map.data = {
  "name": { data: { string: "Alice" }, timeserial: "01", tombstone: false }
}
```

### Test Steps
```pseudo
msg = build_map_remove("root", "name", "02", "site1", 1700000000000)
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["name"].tombstone == true
ASSERT update.update == { "name": "removed" }
ASSERT update.objectMessage == msg
// No parentReference calls needed -- test passes without errors
```

---

## RTLM24e1c - parentReferences: MAP_CLEAR removes parent references for cleared entries

**Test ID**: `objects/unit/RTLM24e1c/map-clear-parent-refs-0`

| Spec | Requirement |
|------|-------------|
| RTLM24e1c1 | Before removing entry, check if it has objectId |
| RTLM24e1c2 | If entry references a LiveObject, call removeParentReference on the child |

Tests that when MAP_CLEAR removes entries that reference LiveObjects, removeParentReference is called for each.

### Setup
```pseudo
pool = ObjectsPool()
counter_a = InternalLiveCounter(objectId: "counter:a@1000")
counter_b = InternalLiveCounter(objectId: "counter:b@1000")
pool["counter:a@1000"] = counter_a
pool["counter:b@1000"] = counter_b

map = InternalLiveMap(objectId: "root", semantics: "LWW", pool: pool)
map.data = {
  "ref_a":     { data: { objectId: "counter:a@1000" }, timeserial: "02", tombstone: false },
  "ref_b":     { data: { objectId: "counter:b@1000" }, timeserial: "02", tombstone: false },
  "primitive": { data: { string: "hello" },            timeserial: "02", tombstone: false },
  "newer":     { data: { string: "kept" },             timeserial: "09", tombstone: false }
}
counter_a.parentReferences = { "root": {"ref_a"} }
counter_b.parentReferences = { "root": {"ref_b"} }
```

### Test Steps
```pseudo
msg = build_map_clear("root", "05", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
// ref_a and ref_b removed (timeserial "02" < "05"), newer kept (timeserial "09" > "05")
ASSERT "ref_a" NOT IN map.data
ASSERT "ref_b" NOT IN map.data
ASSERT "primitive" NOT IN map.data
ASSERT "newer" IN map.data
// removeParentReference was called on both child counters
ASSERT "root" NOT IN counter_a.parentReferences OR "ref_a" NOT IN counter_a.parentReferences["root"]
ASSERT "root" NOT IN counter_b.parentReferences OR "ref_b" NOT IN counter_b.parentReferences["root"]
ASSERT update.update == { "ref_a": "removed", "ref_b": "removed", "primitive": "removed" }
ASSERT update.objectMessage == msg
```

---

## RTLO4e9 - parentReferences: tombstone InternalLiveMap removes parent references for all entries

**Test ID**: `objects/unit/RTLO4e9/tombstone-map-parent-refs-0`

| Spec | Requirement |
|------|-------------|
| RTLO4e9a | Before clearing data, for each entry check if it has objectId |
| RTLO4e9b | If entry references a LiveObject, call removeParentReference on the child |

Tests that when an InternalLiveMap is tombstoned (via OBJECT_DELETE), removeParentReference is called for each entry that references a LiveObject before the data is cleared.

### Setup
```pseudo
pool = ObjectsPool()
child_counter = InternalLiveCounter(objectId: "counter:child@1000")
child_map = InternalLiveMap(objectId: "map:child@1000", semantics: "LWW")
pool["counter:child@1000"] = child_counter
pool["map:child@1000"] = child_map

map = InternalLiveMap(objectId: "root", semantics: "LWW", pool: pool)
map.data = {
  "counter_ref": { data: { objectId: "counter:child@1000" }, timeserial: "01", tombstone: false },
  "map_ref":     { data: { objectId: "map:child@1000" },     timeserial: "01", tombstone: false },
  "name":        { data: { string: "Alice" },                 timeserial: "01", tombstone: false }
}
map.siteTimeserials = { "site1": "00" }
child_counter.parentReferences = { "root": {"counter_ref"} }
child_map.parentReferences = { "root": {"map_ref"} }
```

### Test Steps
```pseudo
msg = build_object_delete("root", "01", "site1", 1700000000000)
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.isTombstone == true
ASSERT map.data == {}
// removeParentReference was called on both children
ASSERT "root" NOT IN child_counter.parentReferences OR "counter_ref" NOT IN child_counter.parentReferences["root"]
ASSERT "root" NOT IN child_map.parentReferences OR "map_ref" NOT IN child_map.parentReferences["root"]
ASSERT update.update == { "counter_ref": "removed", "map_ref": "removed", "name": "removed" }
ASSERT update.tombstone == true
ASSERT update.objectMessage == msg
```

---

## RTLM7a3, RTLM7g2 - parentReferences: MAP_SET overwriting LiveObject with LiveObject calls both remove and add

**Test ID**: `objects/unit/RTLM7a3/map-set-replace-objectid-both-refs-0`

| Spec | Requirement |
|------|-------------|
| RTLM7a3b | removeParentReference called on old child before overwrite |
| RTLM7g2 | addParentReference called on new child after set |

Tests that both removeParentReference and addParentReference are called in the correct order when replacing one LiveObject reference with another.

### Setup
```pseudo
pool = ObjectsPool()
old_map = InternalLiveMap(objectId: "map:old@1000", semantics: "LWW")
new_map = InternalLiveMap(objectId: "map:new@2000", semantics: "LWW")
pool["map:old@1000"] = old_map
pool["map:new@2000"] = new_map

map = InternalLiveMap(objectId: "root", semantics: "LWW", pool: pool)
map.data = {
  "child": { data: { objectId: "map:old@1000" }, timeserial: "01", tombstone: false }
}
old_map.parentReferences = { "root": {"child"} }
```

### Test Steps
```pseudo
msg = build_map_set("root", "child", { objectId: "map:new@2000" }, "02", "site1")
update = map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT map.data["child"].data == { objectId: "map:new@2000" }
// Old child no longer references root
ASSERT "root" NOT IN old_map.parentReferences OR "child" NOT IN old_map.parentReferences["root"]
// New child references root
ASSERT "root" IN new_map.parentReferences
ASSERT "child" IN new_map.parentReferences["root"]
ASSERT update.update == { "child": "updated" }
ASSERT update.objectMessage == msg
```
