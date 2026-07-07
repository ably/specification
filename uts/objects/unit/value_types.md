# Value Types Tests

Spec points: `RTLCV1`–`RTLCV4`, `RTLMV1`–`RTLMV4`

## Test Type
Unit test — pure construction and evaluation, no mocks required.

## Purpose

Tests `LiveCounter` and `LiveMap` — immutable blueprints created via `LiveCounter.create()` and `LiveMap.create()` static factories. When evaluated by a mutation method, they generate `ObjectMessages` with v6 wire format fields (`counterCreateWithObjectId`, `mapCreateWithObjectId`).

---

## RTLCV3 - LiveCounter.create with initial count

**Test ID**: `objects/unit/RTLCV3/create-with-count-0`

| Spec | Requirement |
|------|-------------|
| RTLCV3a1 | Accepts optional initialCount |
| RTLCV3b | Returns LiveCounter with internal count |
| RTLCV3d | Returned value is immutable |

### Test Steps
```pseudo
vt = LiveCounter.create(42)
```

### Assertions
```pseudo
ASSERT vt IS LiveCounter
ASSERT vt.count == 42
```

---

## RTLCV3 - LiveCounter.create defaults to 0

**Test ID**: `objects/unit/RTLCV3/create-default-zero-0`

**Spec requirement:** If initialCount omitted, defaults to 0.

### Test Steps
```pseudo
vt = LiveCounter.create()
```

### Assertions
```pseudo
ASSERT vt.count == 0
```

---

## RTLCV3c - No validation at creation time

**Test ID**: `objects/unit/RTLCV3c/no-validation-at-create-0`

**Spec requirement:** No input validation is performed at creation time; invalid
input is only rejected when the blueprint is evaluated (RTLCV4a).

### Test Steps
```pseudo
vt = LiveCounter.create("not_a_number")
```

### Assertions
```pseudo
ASSERT vt IS LiveCounter  // does not throw
```

---

## RTLCV4 - Evaluation generates COUNTER_CREATE ObjectMessage

**Test ID**: `objects/unit/RTLCV4/evaluate-generates-message-0`

| Spec | Requirement |
|------|-------------|
| RTLCV4b1 | CounterCreate.count set to internal count |
| RTLCV4c | Initial value JSON string from CounterCreate |
| RTLCV4d | Unique nonce with 16+ characters |
| RTLCV4f | objectId generated via RTO14 with type "counter" |
| RTLCV4g1 | action set to COUNTER_CREATE |
| RTLCV4g2 | objectId set |
| RTLCV4g3 | counterCreateWithObjectId.nonce set |
| RTLCV4g4 | counterCreateWithObjectId.initialValue set |

### Test Steps
```pseudo
vt = LiveCounter.create(42)
messages = evaluate(vt)
```

### Assertions
```pseudo
ASSERT messages.length == 1
msg = messages[0]
ASSERT msg.operation.action == "COUNTER_CREATE"
ASSERT msg.operation.objectId STARTS WITH "counter:"
ASSERT msg.operation.objectId CONTAINS "@"
ASSERT msg.operation.counterCreateWithObjectId IS NOT null
ASSERT msg.operation.counterCreateWithObjectId.nonce IS NOT null
ASSERT msg.operation.counterCreateWithObjectId.nonce.length >= 16
ASSERT msg.operation.counterCreateWithObjectId.initialValue IS NOT null
```

---

## RTLCV4g5 - Evaluation retains local CounterCreate

**Test ID**: `objects/unit/RTLCV4g5/retains-local-counter-create-0`

**Spec requirement:** Client must retain CounterCreate alongside CounterCreateWithObjectId for local use (RTLCV4g5). Needed for message size calculation and local application.

### Test Steps
```pseudo
vt = LiveCounter.create(42)
messages = evaluate(vt)
```

### Assertions
```pseudo
msg = messages[0]
ASSERT msg.operation.counterCreate IS NOT null
ASSERT msg.operation.counterCreate.count == 42
```

---

## RTLCV4a - Evaluation validates count type

**Test ID**: `objects/unit/RTLCV4a/evaluate-validates-count-0`

**Spec requirement:** If count is not undefined and (not a Number or not finite), throw 40003 (RTLCV4a). Validation happens during evaluation, not at creation time.

### Test Steps
```pseudo
vt = LiveCounter.create("not_a_number")
evaluate(vt) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40003
```

---

## RTLCV4 - Evaluation with count 0

**Test ID**: `objects/unit/RTLCV4/evaluate-zero-count-0`

**Spec requirement:** count=0 is valid and should be included in CounterCreate.

### Test Steps
```pseudo
vt = LiveCounter.create(0)
messages = evaluate(vt)
```

### Assertions
```pseudo
msg = messages[0]
ASSERT msg.operation.counterCreate.count == 0
```

---

## RTLMV3 - LiveMap.create with entries

**Test ID**: `objects/unit/RTLMV3/create-with-entries-0`

| Spec | Requirement |
|------|-------------|
| RTLMV3a1 | Accepts optional entries dict |
| RTLMV3b | Returns LiveMap with internal entries |
| RTLMV3d | Returned value is immutable |

### Test Steps
```pseudo
vt = LiveMap.create({
  "name": "Alice",
  "age": 30
})
```

### Assertions
```pseudo
ASSERT vt IS LiveMap
ASSERT vt.entries["name"] == "Alice"
ASSERT vt.entries["age"] == 30
```

---

## RTLMV3 - LiveMap.create with no entries

**Test ID**: `objects/unit/RTLMV3/create-no-entries-0`

**Spec requirement:** If entries omitted, internal entries is undefined.

### Test Steps
```pseudo
vt = LiveMap.create()
```

### Assertions
```pseudo
ASSERT vt IS LiveMap
```

---

## RTLMV4 - Evaluation generates MAP_CREATE ObjectMessage

**Test ID**: `objects/unit/RTLMV4/evaluate-generates-message-0`

| Spec | Requirement |
|------|-------------|
| RTLMV4e1 | MapCreate.semantics set to LWW |
| RTLMV4f | Initial value JSON string |
| RTLMV4g | Unique nonce 16+ chars |
| RTLMV4i | objectId via RTO14 with type "map" |
| RTLMV4j1 | action set to MAP_CREATE |
| RTLMV4j3 | mapCreateWithObjectId.nonce set |
| RTLMV4j4 | mapCreateWithObjectId.initialValue set |

### Test Steps
```pseudo
vt = LiveMap.create({ "name": "Alice" })
messages = evaluate(vt)
```

### Assertions
```pseudo
ASSERT messages.length == 1
msg = messages[0]
ASSERT msg.operation.action == "MAP_CREATE"
ASSERT msg.operation.objectId STARTS WITH "map:"
ASSERT msg.operation.mapCreateWithObjectId IS NOT null
ASSERT msg.operation.mapCreateWithObjectId.nonce.length >= 16
ASSERT msg.operation.mapCreateWithObjectId.initialValue IS NOT null
```

---

## RTLMV4j5 - Evaluation retains local MapCreate

**Test ID**: `objects/unit/RTLMV4j5/retains-local-map-create-0`

**Spec requirement:** Client must retain MapCreate alongside MapCreateWithObjectId for local use (RTLMV4j5). Needed for message size calculation and local application.

### Test Steps
```pseudo
vt = LiveMap.create({ "name": "Alice" })
messages = evaluate(vt)
```

### Assertions
```pseudo
msg = messages[0]
ASSERT msg.operation.mapCreate IS NOT null
ASSERT msg.operation.mapCreate.semantics == "LWW"
ASSERT msg.operation.mapCreate.entries["name"].data.string == "Alice"
```

---

## RTLMV4d - Entry value type mapping

**Test ID**: `objects/unit/RTLMV4d/entry-value-types-0`

| Spec | Requirement |
|------|-------------|
| RTLMV4d3 | JsonArray/JsonObject -> data.json |
| RTLMV4d4 | String -> data.string |
| RTLMV4d5 | Number -> data.number |
| RTLMV4d6 | Boolean -> data.boolean |
| RTLMV4d7 | Binary -> data.bytes |

### Test Steps
```pseudo
vt = LiveMap.create({
  "str": "hello",
  "num": 42,
  "bool": true,
  "json_arr": [1, 2, 3],
  "json_obj": { "key": "value" }
})
messages = evaluate(vt)
```

### Assertions
```pseudo
msg = messages[0]
entries = msg.operation.mapCreate.entries
ASSERT entries["str"].data.string == "hello"
ASSERT entries["num"].data.number == 42
ASSERT entries["bool"].data.boolean == true
ASSERT entries["json_arr"].data.json == [1, 2, 3]
ASSERT entries["json_obj"].data.json == { "key": "value" }
```

---

## RTLMV4d1, RTLMV4d2 - Nested value types produce depth-first ObjectMessages

**Test ID**: `objects/unit/RTLMV4d1/nested-value-types-0`

| Spec | Requirement |
|------|-------------|
| RTLMV4d1 | LiveCounter evaluated, ObjectMessage collected, objectId set |
| RTLMV4d2 | LiveMap recursively evaluated, all ObjectMessages collected |
| RTLMV4k | Return depth-first order: inner creates before outer |

### Test Steps
```pseudo
inner_counter = LiveCounter.create(10)
inner_map = LiveMap.create({
  "nested_count": inner_counter
})
outer = LiveMap.create({
  "child": inner_map
})
messages = evaluate(outer)
```

### Assertions
```pseudo
ASSERT messages.length == 3
ASSERT messages[0].operation.action == "COUNTER_CREATE"
ASSERT messages[0].operation.objectId STARTS WITH "counter:"
ASSERT messages[1].operation.action == "MAP_CREATE"
ASSERT messages[1].operation.objectId STARTS WITH "map:"
ASSERT messages[2].operation.action == "MAP_CREATE"
ASSERT messages[2].operation.objectId STARTS WITH "map:"

inner_counter_id = messages[0].operation.objectId
inner_map_id = messages[1].operation.objectId
outer_map_id = messages[2].operation.objectId

ASSERT messages[1].operation.mapCreate.entries["nested_count"].data.objectId == inner_counter_id
ASSERT messages[2].operation.mapCreate.entries["child"].data.objectId == inner_map_id
```

---

## RTLMV4a - Evaluation validates entries type

**Test ID**: `objects/unit/RTLMV4a/evaluate-validates-entries-0`

**Spec requirement:** If entries is not undefined and (is null or not Dict), throw 40003 (RTLMV4a). Validation happens during evaluation, not at creation time.

### Test Steps
```pseudo
vt = LiveMap.create(null)
evaluate(vt) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40003
```

---

## RTLMV4b - Evaluation validates key types

**Test ID**: `objects/unit/RTLMV4b/evaluate-validates-keys-0`

**Spec requirement:** If any key is not String, throw 40003 (RTLMV4b).

### Test Steps
```pseudo
vt = LiveMap.create({ 123: "value" })
evaluate(vt) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40003
```

---

## RTLMV4c - Evaluation validates value types

**Test ID**: `objects/unit/RTLMV4c/evaluate-validates-values-0`

**Spec requirement:** If any value is not an expected type, throw 40013 (RTLMV4c).

### Test Steps
```pseudo
vt = LiveMap.create({ "fn": some_function })
evaluate(vt) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40013
```

---

## RTLMV4e2 - Empty entries produces MapCreate with empty entries

**Test ID**: `objects/unit/RTLMV4e2/empty-entries-0`

**Spec requirement:** If internal entries is undefined, MapCreate.entries is empty map.

### Test Steps
```pseudo
vt = LiveMap.create()
messages = evaluate(vt)
```

### Assertions
```pseudo
msg = messages[0]
ASSERT msg.operation.mapCreate.entries == {}
```

---

## RTLMV4d - Table-driven MAP_SET value type mapping

**Test ID**: `objects/unit/RTLMV4d/map-set-all-types-table-0`

**Spec requirement:** Every supported value type maps to the correct data field.

### Test Steps
```pseudo
type_scenarios = [
  { input: "hello",           expected_field: "string",  expected_value: "hello" },
  { input: 42,                expected_field: "number",  expected_value: 42 },
  { input: 3.14,              expected_field: "number",  expected_value: 3.14 },
  { input: 0,                 expected_field: "number",  expected_value: 0 },
  { input: -1,                expected_field: "number",  expected_value: -1 },
  { input: true,              expected_field: "boolean", expected_value: true },
  { input: false,             expected_field: "boolean", expected_value: false },
  { input: [1, "a", null],    expected_field: "json",    expected_value: [1, "a", null] },
  { input: { "k": "v" },      expected_field: "json",    expected_value: { "k": "v" } },
  { input: bytes([1, 2, 3]),  expected_field: "bytes",   expected_value: "AQID" }
]

FOR scenario IN type_scenarios:
  vt = LiveMap.create({ "test_key": scenario.input })
  messages = evaluate(vt)
  entry = messages[0].operation.mapCreate.entries["test_key"]
  ASSERT entry.data[scenario.expected_field] == scenario.expected_value
```
