# LiveMap Tests

Spec points: `RTLM1`–`RTLM9`, `RTLM14`–`RTLM16`, `RTLM18`–`RTLM19`, `RTLM22`–`RTLM25`, `RTLO3`, `RTLO4a`, `RTLO4e`, `RTLO5`, `RTLO6`

## Test Type
Unit test — pure data structure, no mocks required.

## Purpose

Tests the `LiveMap` LWW-map CRDT data structure. LiveMap holds a dictionary of `ObjectsMapEntry` values with entry-level last-write-wins semantics, supports set/remove/clear operations, create operations (initial entries merge), data replacement during sync, tombstoning, GC of tombstoned entries, and diff calculation.

Tests operate directly on LiveMap by calling `applyOperation()` and `replaceData()` with constructed messages.

## Shared Helpers

See `helpers/standard_test_pool.md` for builder functions.

---

## RTLM4 - Zero-value LiveMap

**Test ID**: `objects/unit/RTLM4/zero-value-0`

| Spec | Requirement |
|------|-------------|
| RTLM4 | Zero-value LiveMap has empty data map and null clearTimeserial |
| RTLM25 | clearTimeserial initially null |

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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
| RTLM7f | Return LiveMapUpdate with key set to "updated" |

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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
```

---

## RTLM7 - MAP_SET updates existing entry

**Test ID**: `objects/unit/RTLM7/map-set-update-entry-0`

| Spec | Requirement |
|------|-------------|
| RTLM7a2e | Set data to MapSet.value |
| RTLM7a2b | Set timeserial to the provided serial |
| RTLM7a2c | Set tombstone to false |

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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
map = LiveMap(objectId: "root", semantics: "LWW")
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
map = LiveMap(objectId: "root", semantics: "LWW")
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
map = LiveMap(objectId: "root", semantics: "LWW")
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
ASSERT update.noop == true
```

---

## RTLM9d - Missing entry serial allows operation

**Test ID**: `objects/unit/RTLM9d/missing-entry-serial-allows-0`

**Spec requirement:** If only the operation serial exists and is non-empty, it is greater than the missing entry serial.

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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
```

---

## RTLM7h - MAP_SET rejected when serial <= clearTimeserial

**Test ID**: `objects/unit/RTLM7h/map-set-clear-timeserial-floor-0`

**Spec requirement:** If clearTimeserial is non-null and >= serial, discard operation.

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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

This test requires an ObjectsPool to be passed alongside the LiveMap. The LiveMap creates a zero-value object in the pool when it encounters an objectId reference.

### Setup
```pseudo
pool = ObjectsPool()
map = LiveMap(objectId: "root", semantics: "LWW", pool: pool)
```

### Test Steps
```pseudo
msg = build_map_set("root", "score", { objectId: "counter:new@2000" }, "01", "site1")
map.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT "counter:new@2000" IN pool
ASSERT pool["counter:new@2000"] IS LiveCounter
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
| RTLM8e | Return LiveMapUpdate with key set to "removed" |

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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
```

---

## RTLM8 - MAP_REMOVE creates tombstoned entry if not exists

**Test ID**: `objects/unit/RTLM8/map-remove-nonexistent-0`

| Spec | Requirement |
|------|-------------|
| RTLM8b1 | Create new entry with data null and timeserial |
| RTLM8b2 | Set tombstone to true |
| RTLM8b3 | Set tombstonedAt via RTLO6 |

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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
```

---

## RTLM8g - MAP_REMOVE rejected when serial <= clearTimeserial

**Test ID**: `objects/unit/RTLM8g/map-remove-clear-timeserial-floor-0`

**Spec requirement:** If clearTimeserial is non-null and >= serial, discard operation.

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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
| RTLM24f | Return LiveMapUpdate with removed keys |

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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
ASSERT "same" NOT IN map.data
ASSERT "new" IN map.data
ASSERT update.update == { "old": "removed", "same": "removed" }
```

---

## RTLM24c - MAP_CLEAR rejected when clearTimeserial is already greater

**Test ID**: `objects/unit/RTLM24c/map-clear-stale-0`

**Spec requirement:** If existing clearTimeserial is greater than provided serial, discard.

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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

### Setup
```pseudo
map = LiveMap(objectId: "map:test@1000", semantics: "LWW")
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
```

---

## RTLM16b - MAP_CREATE noop when already merged

**Test ID**: `objects/unit/RTLM16b/map-create-already-merged-0`

**Spec requirement:** If createOperationIsMerged is true, return noop.

### Setup
```pseudo
map = LiveMap(objectId: "map:test@1000", semantics: "LWW")
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
map = LiveMap(objectId: "root", semantics: "LWW")
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
map = LiveMap(objectId: "root", semantics: "LWW")
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
| RTLM15d5a | Emit LiveMapUpdate with removed keys |
| RTLM15d5b | Return true |

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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
tombstoned_counter = LiveCounter(objectId: "counter:dead@1000")
tombstoned_counter.isTombstone = true
pool["counter:dead@1000"] = tombstoned_counter

map = LiveMap(objectId: "root", semantics: "LWW", pool: pool)
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
| RTLM6h | Return diff LiveMapUpdate |

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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
```

---

## RTLM6c1 - replaceData sets tombstonedAt on tombstoned entries

**Test ID**: `objects/unit/RTLM6c1/replace-data-tombstoned-entries-0`

**Spec requirement:** For each tombstoned entry, set tombstonedAt via RTLO6.

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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

**Spec requirement:** If createOp present, merge via RTLM23.

### Setup
```pseudo
map = LiveMap(objectId: "map:test@1000", semantics: "LWW")
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

## RTLM19 - GC removes tombstoned entries past grace period

**Test ID**: `objects/unit/RTLM19/gc-tombstoned-entries-0`

**Spec requirement:** Entries where tombstonedAt + gracePeriod <= currentTime are removed.

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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
update = LiveMap.diff(previousData, newData)
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
map = LiveMap(objectId: "root", semantics: "LWW")
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
map = LiveMap(objectId: "root", semantics: "LWW")
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
tombstoned_counter = LiveCounter(objectId: "counter:dead@1000")
tombstoned_counter.isTombstone = true
pool["counter:dead@1000"] = tombstoned_counter

map = LiveMap(objectId: "root", semantics: "LWW", pool: pool)
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

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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
```

---

## RTLM24 - MAP_CLEAR preserves entries with newer serial

**Test ID**: `objects/unit/RTLM24/map-clear-preserves-newer-0`

**Spec requirement:** Only entries with timeserial null or <= serial are removed.

### Setup
```pseudo
map = LiveMap(objectId: "root", semantics: "LWW")
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
```
