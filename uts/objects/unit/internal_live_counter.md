# InternalLiveCounter Tests

Spec points: `RTLC1`, `RTLC3`, `RTLC4`, `RTLC6`, `RTLC7`, `RTLC8`, `RTLC9`, `RTLC14`, `RTLC16`, `RTLO3`, `RTLO4a`, `RTLO4b4d`, `RTLO4b4e`, `RTLO4e`, `RTLO5`, `RTLO6`

## Test Type
Unit test — pure data structure, no mocks required.

## Purpose

Tests the `InternalLiveCounter` CRDT data structure. InternalLiveCounter holds a 64-bit float and supports increment operations, create operations (initial value merge), data replacement during sync, tombstoning, and serial-based newness checks.

Tests operate directly on InternalLiveCounter by calling `applyOperation()` and `replaceData()` with constructed messages. No channel or connection infrastructure is needed.

## Shared Helpers

See `helpers/standard_test_pool.md` for `build_counter_inc`, `build_counter_create`, `build_object_delete`, `build_object_state`.

---

## RTLC4 - Zero-value InternalLiveCounter

**Test ID**: `objects/unit/RTLC4/zero-value-0`

**Spec requirement:** The zero-value InternalLiveCounter has data set to 0, empty siteTimeserials, createOperationIsMerged false, isTombstone false.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Assertions
```pseudo
ASSERT counter.data == 0
ASSERT counter.objectId == "counter:abc@1000"
ASSERT counter.isTombstone == false
ASSERT counter.tombstonedAt == null
ASSERT counter.createOperationIsMerged == false
ASSERT counter.siteTimeserials == {}
```

---

## RTLC9 - COUNTER_INC adds number to data

**Test ID**: `objects/unit/RTLC9/counter-inc-basic-0`

| Spec | Requirement |
|------|-------------|
| RTLC9f | Add `CounterInc.number` to data if it exists |
| RTLC9g | Return LiveCounterUpdate with amount set to the number and objectMessage set to the provided ObjectMessage |

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Test Steps
```pseudo
msg = build_counter_inc("counter:abc@1000", 5, "01", "site1")
update = counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT counter.data == 5
ASSERT update.noop == false
ASSERT update.update.amount == 5
ASSERT update.objectMessage == msg
```

---

## RTLC9 - COUNTER_INC with negative number

**Test ID**: `objects/unit/RTLC9/counter-inc-negative-0`

**Spec requirement:** COUNTER_INC with a negative number decrements the counter.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
counter.data = 10
counter.siteTimeserials = { "site1": "00" }
```

### Test Steps
```pseudo
msg = build_counter_inc("counter:abc@1000", -3, "01", "site1")
update = counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT counter.data == 7
ASSERT update.update.amount == -3
ASSERT update.objectMessage == msg
```

---

## RTLC9 - COUNTER_INC with missing number is noop

**Test ID**: `objects/unit/RTLC9/counter-inc-missing-number-0`

**Spec requirement:** If CounterInc.number does not exist, return noop.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
counter.data = 10
```

### Test Steps
```pseudo
msg = ObjectMessage(
  serial: "01",
  siteCode: "site1",
  operation: {
    action: "COUNTER_INC",
    objectId: "counter:abc@1000",
    counterInc: {}
  }
)
update = counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT counter.data == 10
ASSERT update.noop == true
```

---

## RTLC9 - Multiple COUNTER_INC operations accumulate

**Test ID**: `objects/unit/RTLC9/counter-inc-accumulate-0`

**Spec requirement:** Multiple increments accumulate additively.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Test Steps
```pseudo
counter.applyOperation(build_counter_inc("counter:abc@1000", 10, "01", "site1"), source: CHANNEL)
counter.applyOperation(build_counter_inc("counter:abc@1000", 20, "02", "site1"), source: CHANNEL)
counter.applyOperation(build_counter_inc("counter:abc@1000", -5, "01", "site2"), source: CHANNEL)
```

### Assertions
```pseudo
ASSERT counter.data == 25
```

---

## RTLC8, RTLC16 - COUNTER_CREATE merges initial count

**Test ID**: `objects/unit/RTLC8/counter-create-merge-0`

| Spec | Requirement |
|------|-------------|
| RTLC8c | Merge initial value via RTLC16 |
| RTLC16a | Add counterCreate.count to data |
| RTLC16b | Set createOperationIsMerged to true |
| RTLC16c | Return LiveCounterUpdate with amount = count and objectMessage set to the provided ObjectMessage |

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Test Steps
```pseudo
msg = build_counter_create("counter:abc@1000", { count: 42 }, "01", "site1")
update = counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT counter.data == 42
ASSERT counter.createOperationIsMerged == true
ASSERT update.update.amount == 42
ASSERT update.objectMessage == msg
```

---

## RTLC8 - COUNTER_CREATE noop when already merged

**Test ID**: `objects/unit/RTLC8/counter-create-already-merged-0`

**Spec requirement:** If createOperationIsMerged is true, log and return noop.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
counter.data = 42
counter.createOperationIsMerged = true
counter.siteTimeserials = { "site1": "00" }
```

### Test Steps
```pseudo
msg = build_counter_create("counter:abc@1000", { count: 99 }, "01", "site1")
update = counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT counter.data == 42
ASSERT update.noop == true
```

---

## RTLC16 - COUNTER_CREATE with missing count is noop

**Test ID**: `objects/unit/RTLC16/counter-create-no-count-0`

**Spec requirement:** If counterCreate.count does not exist, return noop.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Test Steps
```pseudo
msg = build_counter_create("counter:abc@1000", {}, "01", "site1")
update = counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT counter.data == 0
ASSERT counter.createOperationIsMerged == true
ASSERT update.noop == true
```

---

## RTLO4a - canApplyOperation allows when siteSerial is empty

**Test ID**: `objects/unit/RTLO4a/apply-empty-site-serial-0`

| Spec | Requirement |
|------|-------------|
| RTLO4a5 | If siteSerial is null or empty, return true |

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Test Steps
```pseudo
msg = build_counter_inc("counter:abc@1000", 5, "01", "site1")
result = counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT result IS NOT false
ASSERT counter.data == 5
```

---

## RTLO4a - canApplyOperation rejects stale serial

**Test ID**: `objects/unit/RTLO4a/reject-stale-serial-0`

| Spec | Requirement |
|------|-------------|
| RTLO4a6 | Return true only if serial is greater than siteSerial lexicographically |
| RTLC7b | If canApplyOperation returns false, discard and return false |

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
counter.siteTimeserials = { "site1": "05" }
counter.data = 10
```

### Test Steps
```pseudo
msg = build_counter_inc("counter:abc@1000", 99, "03", "site1")
result = counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT result == false
ASSERT counter.data == 10
```

---

## RTLO4a - canApplyOperation rejects equal serial

**Test ID**: `objects/unit/RTLO4a/reject-equal-serial-0`

**Spec requirement:** Serial must be strictly greater; equal serial is rejected.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
counter.siteTimeserials = { "site1": "05" }
counter.data = 10
```

### Test Steps
```pseudo
msg = build_counter_inc("counter:abc@1000", 99, "05", "site1")
result = counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT result == false
ASSERT counter.data == 10
```

---

## RTLO4a - canApplyOperation warns on empty serial or siteCode

**Test ID**: `objects/unit/RTLO4a/warn-invalid-serial-0`

**Spec requirement:** Both serial and siteCode must be non-empty strings. Otherwise, log warning and do not apply.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Test Steps
```pseudo
msg_no_serial = ObjectMessage(
  serial: "",
  siteCode: "site1",
  operation: { action: "COUNTER_INC", objectId: "counter:abc@1000", counterInc: { number: 5 } }
)
result1 = counter.applyOperation(msg_no_serial, source: CHANNEL)

msg_no_site = ObjectMessage(
  serial: "01",
  siteCode: "",
  operation: { action: "COUNTER_INC", objectId: "counter:abc@1000", counterInc: { number: 5 } }
)
result2 = counter.applyOperation(msg_no_site, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT counter.data == 0
ASSERT result1 == false
ASSERT result2 == false
```

---

## RTLC7c - CHANNEL source updates siteTimeserials

**Test ID**: `objects/unit/RTLC7c/channel-source-updates-serials-0`

**Spec requirement:** If source is CHANNEL, set siteTimeserials[siteCode] = serial.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Test Steps
```pseudo
msg = build_counter_inc("counter:abc@1000", 5, "01", "site1")
counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT counter.siteTimeserials["site1"] == "01"
```

---

## RTLC7c - LOCAL source does not update siteTimeserials

**Test ID**: `objects/unit/RTLC7c/local-source-no-serial-update-0`

**Spec requirement:** If source is LOCAL, siteTimeserials must not be updated.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Test Steps
```pseudo
msg = build_counter_inc("counter:abc@1000", 5, "01", "site1")
counter.applyOperation(msg, source: LOCAL)
```

### Assertions
```pseudo
ASSERT counter.siteTimeserials == {}
ASSERT counter.data == 5
```

---

## RTLC7g - applyOperation returns true on success

**Test ID**: `objects/unit/RTLC7g/apply-returns-true-0`

**Spec requirement:** Returns a boolean indicating whether the operation was successfully applied.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Test Steps
```pseudo
msg = build_counter_inc("counter:abc@1000", 5, "01", "site1")
result = counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT result == true
```

---

## RTLO4e, RTLO5 - OBJECT_DELETE tombstones counter

**Test ID**: `objects/unit/RTLO5/object-delete-tombstones-0`

| Spec | Requirement |
|------|-------------|
| RTLO5b | Tombstone the LiveObject |
| RTLO5c | Return the LiveObjectUpdate returned by tombstone |
| RTLO4e2 | Set isTombstone to true |
| RTLO4e4 | Set data to zero-value |
| RTLO4e5 | Compute diff for the tombstone update |
| RTLO4e6 | Set tombstone flag on the update |
| RTLO4e7 | Set objectMessage on the update |
| RTLC7d4c | Emit LiveCounterUpdate returned by RTLO5 |

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
counter.data = 42
counter.siteTimeserials = { "site1": "00" }
```

### Test Steps
```pseudo
msg = build_object_delete("counter:abc@1000", "01", "site1", 1700000000000)
update = counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT counter.isTombstone == true
ASSERT counter.data == 0
ASSERT counter.tombstonedAt == 1700000000000
ASSERT update.update.amount == -42
ASSERT update.tombstone == true
ASSERT update.objectMessage == msg
```

---

## RTLC7e - Operations on tombstoned counter are rejected

**Test ID**: `objects/unit/RTLC7e/tombstoned-reject-ops-0`

**Spec requirement:** If isTombstone is true, the operation cannot be applied. Return false.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
counter.isTombstone = true
counter.tombstonedAt = 1700000000000
```

### Test Steps
```pseudo
msg = build_counter_inc("counter:abc@1000", 5, "01", "site1")
result = counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT result == false
ASSERT counter.data == 0
```

---

## RTLO6 - tombstonedAt from serialTimestamp

**Test ID**: `objects/unit/RTLO6/tombstoned-at-from-serial-timestamp-0`

| Spec | Requirement |
|------|-------------|
| RTLO6a | tombstonedAt equals serialTimestamp if it exists |

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Test Steps
```pseudo
msg = build_object_delete("counter:abc@1000", "01", "site1", 1700000050000)
counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT counter.tombstonedAt == 1700000050000
```

---

## RTLO6 - tombstonedAt from local clock when no serialTimestamp

**Test ID**: `objects/unit/RTLO6/tombstoned-at-local-clock-0`

| Spec | Requirement |
|------|-------------|
| RTLO6b | tombstonedAt equals current local time if serialTimestamp not provided |

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
before_time = current_time()
```

### Test Steps
```pseudo
msg = build_object_delete("counter:abc@1000", "01", "site1")
counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
after_time = current_time()
ASSERT counter.tombstonedAt >= before_time
ASSERT counter.tombstonedAt <= after_time
```

---

## RTLC7d3 - Unsupported action is discarded

**Test ID**: `objects/unit/RTLC7d3/unsupported-action-0`

**Spec requirement:** Log warning, discard without action, return false.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Test Steps
```pseudo
msg = ObjectMessage(
  serial: "01",
  siteCode: "site1",
  operation: { action: "MAP_SET", objectId: "counter:abc@1000", mapSet: { key: "x", value: { string: "y" } } }
)
result = counter.applyOperation(msg, source: CHANNEL)
```

### Assertions
```pseudo
ASSERT result == false
ASSERT counter.data == 0
```

---

## RTLC6 - replaceData sets data from ObjectState

**Test ID**: `objects/unit/RTLC6/replace-data-basic-0`

| Spec | Requirement |
|------|-------------|
| RTLC6a | Replace siteTimeserials from ObjectState |
| RTLC6b | Set createOperationIsMerged to false |
| RTLC6c | Set data to counter.count |
| RTLC6h | Return diff as LiveCounterUpdate with objectMessage set to the provided ObjectMessage |

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
counter.data = 10
counter.createOperationIsMerged = true
counter.siteTimeserials = { "site1": "00" }
```

### Test Steps
```pseudo
state_msg = build_object_state("counter:abc@1000", {"site2": "05"}, {
  counter: { count: 50 }
})
update = counter.replaceData(state_msg)
```

### Assertions
```pseudo
ASSERT counter.data == 50
ASSERT counter.siteTimeserials == { "site2": "05" }
ASSERT counter.createOperationIsMerged == false
ASSERT update.update.amount == 40
ASSERT update.objectMessage == state_msg
```

---

## RTLC6 - replaceData with createOp merges initial value

**Test ID**: `objects/unit/RTLC6/replace-data-with-create-op-0`

| Spec | Requirement |
|------|-------------|
| RTLC6c | Set data to counter.count |
| RTLC6d | If createOp present, merge via RTLC16 |

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Test Steps
```pseudo
state_msg = build_object_state("counter:abc@1000", {"site1": "01"}, {
  counter: { count: 100 },
  createOp: { counterCreate: { count: 50 } }
})
update = counter.replaceData(state_msg)
```

### Assertions
```pseudo
ASSERT counter.data == 150
ASSERT counter.createOperationIsMerged == true
ASSERT update.update.amount == 150
ASSERT update.objectMessage == state_msg
```

---

## RTLC6e - replaceData on tombstoned counter is noop

**Test ID**: `objects/unit/RTLC6e/replace-data-tombstoned-noop-0`

**Spec requirement:** If isTombstone is true, finish processing. Return noop.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
counter.isTombstone = true
counter.tombstonedAt = 1700000000000
counter.data = 0
```

### Test Steps
```pseudo
state_msg = build_object_state("counter:abc@1000", {"site1": "01"}, {
  counter: { count: 999 }
})
update = counter.replaceData(state_msg)
```

### Assertions
```pseudo
ASSERT counter.data == 0
ASSERT update.noop == true
```

---

## RTLC6f - replaceData with tombstone flag tombstones counter

**Test ID**: `objects/unit/RTLC6f/replace-data-tombstone-flag-0`

| Spec | Requirement |
|------|-------------|
| RTLC6f | If ObjectState.tombstone is true, tombstone the counter via LiveObject.tombstone |
| RTLC6f2 | Return the LiveCounterUpdate returned by LiveObject.tombstone |
| RTLO4e6 | Tombstone flag set on the update |
| RTLO4e7 | objectMessage set on the update |

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
counter.data = 30
```

### Test Steps
```pseudo
state_msg = build_object_state("counter:abc@1000", {"site1": "01"}, {
  counter: { count: 0 },
  tombstone: true
})
update = counter.replaceData(state_msg)
```

### Assertions
```pseudo
ASSERT counter.isTombstone == true
ASSERT counter.data == 0
ASSERT update.update.amount == -30
ASSERT update.tombstone == true
ASSERT update.objectMessage == state_msg
```

---

## RTLC6 - replaceData with missing counter.count defaults to 0

**Test ID**: `objects/unit/RTLC6/replace-data-missing-count-0`

**Spec requirement:** Set data to counter.count, or to 0 if it does not exist.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
counter.data = 42
```

### Test Steps
```pseudo
state_msg = build_object_state("counter:abc@1000", {"site1": "01"}, {
  counter: {}
})
update = counter.replaceData(state_msg)
```

### Assertions
```pseudo
ASSERT counter.data == 0
ASSERT update.update.amount == -42
ASSERT update.objectMessage == state_msg
```

---

## RTLC14 - Diff calculation

**Test ID**: `objects/unit/RTLC14/diff-calculation-0`

**Spec requirement:** Return LiveCounterUpdate with amount = newData - previousData.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
counter.data = 20
```

### Test Steps
```pseudo
state_msg = build_object_state("counter:abc@1000", {"site1": "01"}, {
  counter: { count: 75 }
})
update = counter.replaceData(state_msg)
```

### Assertions
```pseudo
ASSERT update.update.amount == 55
ASSERT update.objectMessage == state_msg
```

---

## RTLC8, RTLC16 - COUNTER_CREATE then COUNTER_INC accumulates

**Test ID**: `objects/unit/RTLC8/create-then-inc-0`

**Spec requirement:** Create operation merges initial count, then increment adds to it.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Test Steps
```pseudo
counter.applyOperation(
  build_counter_create("counter:abc@1000", { count: 100 }, "01", "site1"),
  source: CHANNEL
)
counter.applyOperation(
  build_counter_inc("counter:abc@1000", 25, "02", "site1"),
  source: CHANNEL
)
```

### Assertions
```pseudo
ASSERT counter.data == 125
ASSERT counter.createOperationIsMerged == true
```

---

## RTLO3 - LiveObject properties initialized correctly

**Test ID**: `objects/unit/RTLO3/live-object-init-properties-0`

| Spec | Requirement |
|------|-------------|
| RTLO3a1 | objectId must be provided in constructor |
| RTLO3b1 | siteTimeserials set to empty map |
| RTLO3c1 | createOperationIsMerged set to false |
| RTLO3d1 | isTombstone set to false |
| RTLO3e1 | tombstonedAt set to null |

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:test@2000")
```

### Assertions
```pseudo
ASSERT counter.objectId == "counter:test@2000"
ASSERT counter.siteTimeserials == {}
ASSERT counter.createOperationIsMerged == false
ASSERT counter.isTombstone == false
ASSERT counter.tombstonedAt == null
```
