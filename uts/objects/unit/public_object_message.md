# PublicAPI::ObjectMessage and PublicAPI::ObjectOperation Tests

Spec points: `PAOM1`, `PAOM2`, `PAOM3`, `PAOOP1`, `PAOOP2`, `PAOOP3`

## Test Type
Unit test — pure data structure construction, no mocks required.

## Purpose

Tests the construction of `PublicAPI::ObjectMessage` from an internal `ObjectMessage`, and the construction of `PublicAPI::ObjectOperation` from an internal `ObjectOperation`. These are user-facing types exposed to subscription listeners so that user code can inspect the metadata of the message that triggered an object change.

Tests verify that all fields are correctly copied, that `channel` comes from the channel object (not from the ObjectMessage), that the `operation` is derived via PAOOP3, and that the `mapCreate`/`counterCreate` resolution logic handles direct, derived-from-WithObjectId, and absent cases correctly.

---

## PAOM3 - Construction copies all fields from source ObjectMessage

**Test ID**: `objects/unit/PAOM3/construction-all-fields-0`

| Spec | Requirement |
|------|-------------|
| PAOM3b | Set channel attribute to channel.name |
| PAOM3c | Copy id, clientId, connectionId, timestamp, serial, serialTimestamp, siteCode, extras from source |
| PAOM3d | Set operation to PublicAPI::ObjectOperation derived per PAOOP3 |

Tests that constructing a PublicAPI::ObjectMessage from a source ObjectMessage with all fields populated correctly copies every attribute and derives the operation.

### Setup
```pseudo
source = ObjectMessage(
  id: "msg-id-1",
  clientId: "client-1",
  connectionId: "conn-1",
  timestamp: 1700000000000,
  serial: "01",
  serialTimestamp: 1700000001000,
  siteCode: "site1",
  extras: { "key": "value" },
  operation: {
    action: "MAP_SET",
    objectId: "map:abc@1000",
    mapSet: { key: "name", value: { string: "Alice" } }
  }
)

channel = { name: "test-channel" }
```

### Test Steps
```pseudo
public_msg = PublicObjectMessage.fromObjectMessage(source, channel)
```

### Assertions
```pseudo
ASSERT public_msg.id == "msg-id-1"
ASSERT public_msg.clientId == "client-1"
ASSERT public_msg.connectionId == "conn-1"
ASSERT public_msg.timestamp == 1700000000000
ASSERT public_msg.channel == "test-channel"
ASSERT public_msg.serial == "01"
ASSERT public_msg.serialTimestamp == 1700000001000
ASSERT public_msg.siteCode == "site1"
ASSERT public_msg.extras == { "key": "value" }
ASSERT public_msg.operation IS NOT null
ASSERT public_msg.operation.action == "MAP_SET"
ASSERT public_msg.operation.objectId == "map:abc@1000"
ASSERT public_msg.operation.mapSet.key == "name"
```

---

## PAOM3 - Construction with optional fields missing

**Test ID**: `objects/unit/PAOM3/construction-optional-fields-missing-0`

| Spec | Requirement |
|------|-------------|
| PAOM2a | id is optional |
| PAOM2b | clientId is optional |
| PAOM2c | connectionId is optional |
| PAOM2d | timestamp is optional |
| PAOM2g | serial is optional |
| PAOM2h | serialTimestamp is optional |
| PAOM2i | siteCode is optional |
| PAOM2j | extras is optional |
| PAOM3c | Copy fields from source; absent fields remain null/undefined |

Tests that constructing a PublicAPI::ObjectMessage from a source ObjectMessage with only required fields works correctly, and optional fields are null/undefined.

### Setup
```pseudo
source = ObjectMessage(
  operation: {
    action: "COUNTER_INC",
    objectId: "counter:abc@1000",
    counterInc: { number: 5 }
  }
)

channel = { name: "my-channel" }
```

### Test Steps
```pseudo
public_msg = PublicObjectMessage.fromObjectMessage(source, channel)
```

### Assertions
```pseudo
ASSERT public_msg.id == null
ASSERT public_msg.clientId == null
ASSERT public_msg.connectionId == null
ASSERT public_msg.timestamp == null
ASSERT public_msg.channel == "my-channel"
ASSERT public_msg.serial == null
ASSERT public_msg.serialTimestamp == null
ASSERT public_msg.siteCode == null
ASSERT public_msg.extras == null
ASSERT public_msg.operation IS NOT null
ASSERT public_msg.operation.action == "COUNTER_INC"
```

---

## PAOM3b - Channel is set from channel.name, not from ObjectMessage

**Test ID**: `objects/unit/PAOM3/channel-from-channel-name-0`

**Spec requirement:** The `channel` attribute is set to `channel.name`, not derived from any field on the ObjectMessage itself.

Tests that the channel field on the PublicAPI::ObjectMessage comes from the channel object's name property.

### Setup
```pseudo
source = ObjectMessage(
  operation: {
    action: "OBJECT_DELETE",
    objectId: "counter:abc@1000"
  }
)

channel = { name: "different-channel-name" }
```

### Test Steps
```pseudo
public_msg = PublicObjectMessage.fromObjectMessage(source, channel)
```

### Assertions
```pseudo
ASSERT public_msg.channel == "different-channel-name"
```

---

## PAOOP3a - MAP_SET operation copies mapSet, omits unrelated fields

**Test ID**: `objects/unit/PAOOP3/map-set-copies-fields-0`

| Spec | Requirement |
|------|-------------|
| PAOOP3a | Copy action, objectId, mapSet, mapRemove, counterInc, objectDelete, mapClear directly |
| PAOOP2d | mapSet is the mapSet of the source ObjectOperation |

Tests that constructing a PublicAPI::ObjectOperation from a MAP_SET source copies action, objectId, and mapSet, and omits all other operation-specific fields.

### Setup
```pseudo
source_operation = {
  action: "MAP_SET",
  objectId: "map:abc@1000",
  mapSet: { key: "color", value: { string: "blue" } }
}
```

### Test Steps
```pseudo
public_op = PublicObjectOperation.fromObjectOperation(source_operation)
```

### Assertions
```pseudo
ASSERT public_op.action == "MAP_SET"
ASSERT public_op.objectId == "map:abc@1000"
ASSERT public_op.mapSet.key == "color"
ASSERT public_op.mapSet.value.string == "blue"
ASSERT public_op.mapCreate == null
ASSERT public_op.mapRemove == null
ASSERT public_op.counterCreate == null
ASSERT public_op.counterInc == null
ASSERT public_op.objectDelete == null
ASSERT public_op.mapClear == null
```

---

## PAOOP3a - MAP_REMOVE operation copies mapRemove, omits unrelated fields

**Test ID**: `objects/unit/PAOOP3/map-remove-copies-fields-0`

| Spec | Requirement |
|------|-------------|
| PAOOP3a | Copy mapRemove directly from source |
| PAOOP2e | mapRemove is the mapRemove of the source ObjectOperation |

Tests that constructing a PublicAPI::ObjectOperation from a MAP_REMOVE source copies action, objectId, and mapRemove, and omits all other operation-specific fields.

### Setup
```pseudo
source_operation = {
  action: "MAP_REMOVE",
  objectId: "map:abc@1000",
  mapRemove: { key: "old-key" }
}
```

### Test Steps
```pseudo
public_op = PublicObjectOperation.fromObjectOperation(source_operation)
```

### Assertions
```pseudo
ASSERT public_op.action == "MAP_REMOVE"
ASSERT public_op.objectId == "map:abc@1000"
ASSERT public_op.mapRemove.key == "old-key"
ASSERT public_op.mapCreate == null
ASSERT public_op.mapSet == null
ASSERT public_op.counterCreate == null
ASSERT public_op.counterInc == null
ASSERT public_op.objectDelete == null
ASSERT public_op.mapClear == null
```

---

## PAOOP3a - COUNTER_INC operation copies counterInc, omits unrelated fields

**Test ID**: `objects/unit/PAOOP3/counter-inc-copies-fields-0`

| Spec | Requirement |
|------|-------------|
| PAOOP3a | Copy counterInc directly from source |
| PAOOP2g | counterInc is the counterInc of the source ObjectOperation |

Tests that constructing a PublicAPI::ObjectOperation from a COUNTER_INC source copies action, objectId, and counterInc, and omits all other operation-specific fields.

### Setup
```pseudo
source_operation = {
  action: "COUNTER_INC",
  objectId: "counter:abc@1000",
  counterInc: { number: 42 }
}
```

### Test Steps
```pseudo
public_op = PublicObjectOperation.fromObjectOperation(source_operation)
```

### Assertions
```pseudo
ASSERT public_op.action == "COUNTER_INC"
ASSERT public_op.objectId == "counter:abc@1000"
ASSERT public_op.counterInc.number == 42
ASSERT public_op.mapCreate == null
ASSERT public_op.mapSet == null
ASSERT public_op.mapRemove == null
ASSERT public_op.counterCreate == null
ASSERT public_op.objectDelete == null
ASSERT public_op.mapClear == null
```

---

## PAOOP3a - OBJECT_DELETE operation copies objectDelete, omits unrelated fields

**Test ID**: `objects/unit/PAOOP3/object-delete-copies-fields-0`

| Spec | Requirement |
|------|-------------|
| PAOOP3a | Copy objectDelete directly from source |
| PAOOP2h | objectDelete is the objectDelete of the source ObjectOperation |

Tests that constructing a PublicAPI::ObjectOperation from an OBJECT_DELETE source copies action, objectId, and objectDelete, and omits all other operation-specific fields.

### Setup
```pseudo
source_operation = {
  action: "OBJECT_DELETE",
  objectId: "counter:abc@1000",
  objectDelete: {}
}
```

### Test Steps
```pseudo
public_op = PublicObjectOperation.fromObjectOperation(source_operation)
```

### Assertions
```pseudo
ASSERT public_op.action == "OBJECT_DELETE"
ASSERT public_op.objectId == "counter:abc@1000"
ASSERT public_op.objectDelete IS NOT null
ASSERT public_op.mapCreate == null
ASSERT public_op.mapSet == null
ASSERT public_op.mapRemove == null
ASSERT public_op.counterCreate == null
ASSERT public_op.counterInc == null
ASSERT public_op.mapClear == null
```

---

## PAOOP3a - MAP_CLEAR operation copies mapClear, omits unrelated fields

**Test ID**: `objects/unit/PAOOP3/map-clear-copies-fields-0`

| Spec | Requirement |
|------|-------------|
| PAOOP3a | Copy mapClear directly from source |
| PAOOP2i | mapClear is the mapClear of the source ObjectOperation |

Tests that constructing a PublicAPI::ObjectOperation from a MAP_CLEAR source copies action, objectId, and mapClear, and omits all other operation-specific fields.

### Setup
```pseudo
source_operation = {
  action: "MAP_CLEAR",
  objectId: "map:abc@1000",
  mapClear: {}
}
```

### Test Steps
```pseudo
public_op = PublicObjectOperation.fromObjectOperation(source_operation)
```

### Assertions
```pseudo
ASSERT public_op.action == "MAP_CLEAR"
ASSERT public_op.objectId == "map:abc@1000"
ASSERT public_op.mapClear IS NOT null
ASSERT public_op.mapCreate == null
ASSERT public_op.mapSet == null
ASSERT public_op.mapRemove == null
ASSERT public_op.counterCreate == null
ASSERT public_op.counterInc == null
ASSERT public_op.objectDelete == null
```

---

## PAOOP3b1 - MAP_CREATE with mapCreate directly present

**Test ID**: `objects/unit/PAOOP3/map-create-direct-0`

| Spec | Requirement |
|------|-------------|
| PAOOP3b1 | If mapCreate is present on the source, set mapCreate to that value |

Tests that when the source ObjectOperation has a `mapCreate` field, the PublicAPI::ObjectOperation uses it directly.

### Setup
```pseudo
source_operation = {
  action: "MAP_CREATE",
  objectId: "map:new@2000",
  mapCreate: { semantics: "LWW", entries: { "key1": { data: { string: "val1" } } } }
}
```

### Test Steps
```pseudo
public_op = PublicObjectOperation.fromObjectOperation(source_operation)
```

### Assertions
```pseudo
ASSERT public_op.action == "MAP_CREATE"
ASSERT public_op.objectId == "map:new@2000"
ASSERT public_op.mapCreate IS NOT null
ASSERT public_op.mapCreate.semantics == "LWW"
ASSERT public_op.mapCreate.entries["key1"].data.string == "val1"
ASSERT public_op.counterCreate == null
```

---

## PAOOP3b2 - MAP_CREATE resolved from mapCreateWithObjectId

**Test ID**: `objects/unit/PAOOP3/map-create-from-with-object-id-0`

| Spec | Requirement |
|------|-------------|
| PAOOP3b2 | If mapCreateWithObjectId is present on the source, set mapCreate to the MapCreate from which it was derived |

Tests that when the source ObjectOperation has `mapCreateWithObjectId` but not `mapCreate`, the PublicAPI::ObjectOperation resolves `mapCreate` to the derived MapCreate.

### Setup
```pseudo
derived_map_create = { semantics: "LWW", entries: { "x": { data: { number: 10 } } } }

source_operation = {
  action: "MAP_CREATE",
  objectId: "map:derived@3000",
  mapCreateWithObjectId: {
    objectId: "map:derived@3000",
    semantics: "LWW",
    entries: { "x": { data: { number: 10 } } },
    _derivedFrom: derived_map_create
  }
}
```

### Test Steps
```pseudo
public_op = PublicObjectOperation.fromObjectOperation(source_operation)
```

### Assertions
```pseudo
ASSERT public_op.action == "MAP_CREATE"
ASSERT public_op.objectId == "map:derived@3000"
ASSERT public_op.mapCreate IS NOT null
ASSERT public_op.mapCreate.semantics == "LWW"
ASSERT public_op.mapCreate.entries["x"].data.number == 10
ASSERT public_op.counterCreate == null
```

---

## PAOOP3c2 - COUNTER_CREATE resolved from counterCreateWithObjectId

**Test ID**: `objects/unit/PAOOP3/counter-create-from-with-object-id-0`

| Spec | Requirement |
|------|-------------|
| PAOOP3c2 | If counterCreateWithObjectId is present on the source, set counterCreate to the CounterCreate from which it was derived |

Tests that when the source ObjectOperation has `counterCreateWithObjectId` but not `counterCreate`, the PublicAPI::ObjectOperation resolves `counterCreate` to the derived CounterCreate.

### Setup
```pseudo
derived_counter_create = { count: 100 }

source_operation = {
  action: "COUNTER_CREATE",
  objectId: "counter:derived@3000",
  counterCreateWithObjectId: {
    objectId: "counter:derived@3000",
    count: 100,
    _derivedFrom: derived_counter_create
  }
}
```

### Test Steps
```pseudo
public_op = PublicObjectOperation.fromObjectOperation(source_operation)
```

### Assertions
```pseudo
ASSERT public_op.action == "COUNTER_CREATE"
ASSERT public_op.objectId == "counter:derived@3000"
ASSERT public_op.counterCreate IS NOT null
ASSERT public_op.counterCreate.count == 100
ASSERT public_op.mapCreate == null
```

---

## PAOOP3b3, PAOOP3c3 - Create payloads omitted when neither variant is present

**Test ID**: `objects/unit/PAOOP3/create-payloads-omitted-0`

| Spec | Requirement |
|------|-------------|
| PAOOP3b3 | If neither mapCreate nor mapCreateWithObjectId is present, omit mapCreate |
| PAOOP3c3 | If neither counterCreate nor counterCreateWithObjectId is present, omit counterCreate |

Tests that when the source ObjectOperation has no create payloads (neither direct nor WithObjectId variants), both `mapCreate` and `counterCreate` are omitted on the resulting PublicAPI::ObjectOperation.

### Setup
```pseudo
source_operation = {
  action: "MAP_SET",
  objectId: "map:abc@1000",
  mapSet: { key: "k", value: { string: "v" } }
}
```

### Test Steps
```pseudo
public_op = PublicObjectOperation.fromObjectOperation(source_operation)
```

### Assertions
```pseudo
ASSERT public_op.mapCreate == null
ASSERT public_op.counterCreate == null
```

---

## PAOOP3 - Only the relevant operation field is present per action type

**Test ID**: `objects/unit/PAOOP3/only-relevant-field-per-action-0`

| Spec | Requirement |
|------|-------------|
| PAOOP3a | Copy only the fields that exist on the source; unrelated fields are omitted |
| PAOOP2c | mapCreate is optional |
| PAOOP2d | mapSet is optional |
| PAOOP2e | mapRemove is optional |
| PAOOP2f | counterCreate is optional |
| PAOOP2g | counterInc is optional |
| PAOOP2h | objectDelete is optional |
| PAOOP2i | mapClear is optional |

Tests that for a COUNTER_CREATE operation with `counterCreate` directly present, only `counterCreate` is set and all other operation-specific fields are null.

### Setup
```pseudo
source_operation = {
  action: "COUNTER_CREATE",
  objectId: "counter:new@2000",
  counterCreate: { count: 50 }
}
```

### Test Steps
```pseudo
public_op = PublicObjectOperation.fromObjectOperation(source_operation)
```

### Assertions
```pseudo
ASSERT public_op.action == "COUNTER_CREATE"
ASSERT public_op.objectId == "counter:new@2000"
ASSERT public_op.counterCreate IS NOT null
ASSERT public_op.counterCreate.count == 50
ASSERT public_op.mapCreate == null
ASSERT public_op.mapSet == null
ASSERT public_op.mapRemove == null
ASSERT public_op.counterInc == null
ASSERT public_op.objectDelete == null
ASSERT public_op.mapClear == null
```
