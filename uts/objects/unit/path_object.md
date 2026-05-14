# PathObject Read Operations Tests

Spec points: `RTPO1`–`RTPO14`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Shared Helpers

See `helpers/standard_test_pool.md` for `setup_synced_channel` and builder functions.

---

## RTPO4 - path() returns dot-delimited string

**Test ID**: `objects/unit/RTPO4/path-string-representation-0`

| Spec | Requirement |
|------|-------------|
| RTPO4a | Dot-delimited string of path segments |
| RTPO4c | Empty path returns empty string |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.path() == ""
ASSERT root.get("profile").path() == "profile"
ASSERT root.get("profile").get("email").path() == "profile.email"
```

---

## RTPO4b - path() escapes dots in segments

**Test ID**: `objects/unit/RTPO4b/path-escapes-dots-0`

**Spec requirement:** Dot characters within segments are escaped with backslash.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
po = root.get("a.b").get("c")
```

### Assertions
```pseudo
ASSERT po.path() == "a\\.b.c"
```

---

## RTPO5 - get() returns new PathObject with appended key

**Test ID**: `objects/unit/RTPO5/get-appends-key-0`

| Spec | Requirement |
|------|-------------|
| RTPO5c | New PathObject with key appended |
| RTPO5d | Purely navigational, no resolution |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
child = root.get("profile")
grandchild = child.get("email")
```

### Assertions
```pseudo
ASSERT child.path() == "profile"
ASSERT grandchild.path() == "profile.email"
ASSERT child IS NOT root
```

---

## RTPO5b - get() throws on non-string key

**Test ID**: `objects/unit/RTPO5b/get-non-string-throws-0`

**Spec requirement:** If key is not String, throw 40003.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
root.get(123) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40003
```

---

## RTPO6 - at() parses dot-delimited path

**Test ID**: `objects/unit/RTPO6/at-parses-path-0`

| Spec | Requirement |
|------|-------------|
| RTPO6b | Parses dots as separators, backslash-escaped dots as literal |
| RTPO6d | Equivalent to chained get() calls |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
po = root.at("profile.email")
```

### Assertions
```pseudo
ASSERT po.path() == "profile.email"
ASSERT po.value() == "alice@example.com"
```

---

## RTPO6 - at() respects escaped dots

**Test ID**: `objects/unit/RTPO6/at-escaped-dots-0`

**Spec requirement:** `\.` is a literal dot within a segment.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
po = root.at("a\\.b.c")
```

### Assertions
```pseudo
ASSERT po.path() == "a\\.b.c"
```

---

## RTPO7 - value() returns counter numeric value

**Test ID**: `objects/unit/RTPO7/value-counter-0`

**Spec requirement:** If resolved value is LiveCounter, returns numeric value.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.get("score").value() == 100
```

---

## RTPO7 - value() returns primitive value

**Test ID**: `objects/unit/RTPO7/value-primitive-0`

**Spec requirement:** If resolved value is a primitive, returns the value directly.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.get("name").value() == "Alice"
ASSERT root.get("age").value() == 30
ASSERT root.get("active").value() == true
```

---

## RTPO7d - value() returns null for LiveMap

**Test ID**: `objects/unit/RTPO7d/value-livemap-null-0`

**Spec requirement:** If resolved value is a LiveMap, returns null.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.get("profile").value() == null
```

---

## RTPO7e - value() returns null on resolution failure

**Test ID**: `objects/unit/RTPO7e/value-unresolvable-null-0`

**Spec requirement:** If path resolution fails, returns null.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.get("nonexistent").get("deep").value() == null
```

---

## RTPO8 - instance() returns Instance for LiveObject

**Test ID**: `objects/unit/RTPO8/instance-live-object-0`

| Spec | Requirement |
|------|-------------|
| RTPO8b | LiveMap or LiveCounter -> Instance wrapping that object |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
counter_inst = root.get("score").instance()
ASSERT counter_inst IS Instance
ASSERT counter_inst.id() == "counter:score@1000"

map_inst = root.get("profile").instance()
ASSERT map_inst IS Instance
ASSERT map_inst.id() == "map:profile@1000"
```

---

## RTPO8c - instance() returns null for primitive

**Test ID**: `objects/unit/RTPO8c/instance-primitive-null-0`

**Spec requirement:** If resolved value is a primitive, returns null.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.get("name").instance() == null
```

---

## RTPO9 - entries() yields [key, PathObject] pairs

**Test ID**: `objects/unit/RTPO9/entries-yields-pairs-0`

| Spec | Requirement |
|------|-------------|
| RTPO9b | Iterator of [key, PathObject] for LiveMap entries |
| RTPO9c | Only non-tombstoned entries |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
entries = {}
FOR [key, pathObj] IN root.entries():
  entries[key] = pathObj.path()
```

### Assertions
```pseudo
ASSERT entries["name"] == "name"
ASSERT entries["profile"] == "profile"
ASSERT entries.length == 7
```

---

## RTPO9d - entries() returns empty iterator for non-LiveMap

**Test ID**: `objects/unit/RTPO9d/entries-non-map-empty-0`

**Spec requirement:** If resolved value is not LiveMap or resolution fails, return empty iterator.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
entries = list(root.get("score").entries())
```

### Assertions
```pseudo
ASSERT entries.length == 0
```

---

## RTPO12 - size() returns non-tombstoned count

**Test ID**: `objects/unit/RTPO12/size-count-0`

**Spec requirement:** For LiveMap, returns non-tombstoned entry count.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.size() == 7
ASSERT root.get("profile").size() == 3
```

---

## RTPO12c - size() returns null for non-LiveMap

**Test ID**: `objects/unit/RTPO12c/size-non-map-null-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.get("score").size() == null
ASSERT root.get("name").size() == null
```

---

## RTPO13 - compact() recursively compacts LiveMap tree

**Test ID**: `objects/unit/RTPO13/compact-recursive-0`

| Spec | Requirement |
|------|-------------|
| RTPO13b1 | Each entry included, tombstoned excluded |
| RTPO13b2 | Nested LiveMap recursively compacted |
| RTPO13b3 | Nested LiveCounter resolved to number |
| RTPO13b4 | Primitives as-is |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
result = root.compact()
```

### Assertions
```pseudo
ASSERT result["name"] == "Alice"
ASSERT result["age"] == 30
ASSERT result["active"] == true
ASSERT result["score"] == 100
ASSERT result["data"] == {"tags": ["a", "b"]}
ASSERT result["avatar"] IS bytes [1, 2, 3]
ASSERT result["profile"]["email"] == "alice@example.com"
ASSERT result["profile"]["nested_counter"] == 5
ASSERT result["profile"]["prefs"]["theme"] == "dark"
```

---

## RTPO13b5 - compact() handles cycles via shared reference

**Test ID**: `objects/unit/RTPO13b5/compact-cycle-detection-0`

**Spec requirement:** Cyclic references reuse the already-compacted in-memory object.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")

mock_ws.send_to_client(build_object_message("test", [
  build_map_set("map:prefs@1000", "back_ref", { objectId: "map:profile@1000" }, "99", "remote")
]))
```

### Test Steps
```pseudo
result = root.get("profile").compact()
```

### Assertions
```pseudo
ASSERT result["prefs"]["back_ref"] IS result
```

---

## RTPO13c - compact() returns number for LiveCounter

**Test ID**: `objects/unit/RTPO13c/compact-counter-0`

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.get("score").compact() == 100
```

---

## RTPO14 - compactJson() encodes binary as base64 and cycles as objectId

**Test ID**: `objects/unit/RTPO14/compact-json-0`

| Spec | Requirement |
|------|-------------|
| RTPO14a1 | Binary as base64 strings |
| RTPO14a2 | Cycles as {objectId: ...} |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")

mock_ws.send_to_client(build_object_message("test", [
  build_map_set("map:prefs@1000", "back_ref", { objectId: "map:profile@1000" }, "99", "remote")
]))
```

### Test Steps
```pseudo
result = root.get("profile").compactJson()
```

### Assertions
```pseudo
ASSERT result["prefs"]["back_ref"] == { "objectId": "map:profile@1000" }
```

---

## RTPO3 - Path resolution walks through LiveMaps

**Test ID**: `objects/unit/RTPO3/path-resolution-walk-0`

| Spec | Requirement |
|------|-------------|
| RTPO3a | Walk segments through LiveMaps |
| RTPO3b | Empty path resolves to root |

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.value() == null
ASSERT root.get("profile").get("prefs").get("theme").value() == "dark"
```

---

## RTPO3a1 - Resolution fails if intermediate is not LiveMap

**Test ID**: `objects/unit/RTPO3a1/intermediate-not-map-0`

**Spec requirement:** Current object must be a LiveMap. If not, resolution fails.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.get("score").get("something").value() == null
```

---

## RTPO3c1 - Read operation returns null on resolution failure

**Test ID**: `objects/unit/RTPO3c1/read-null-on-failure-0`

**Spec requirement:** For read operations, return null.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.get("nonexistent").value() == null
ASSERT root.get("nonexistent").instance() == null
ASSERT root.get("nonexistent").size() == null
ASSERT root.get("nonexistent").compact() == null
```

---

## RTPO6b - at() throws for non-string input

**Test ID**: `objects/unit/RTPO6b/at-non-string-throws-0`

**Spec requirement:** If path is not String, throw 40003.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
root.at(123) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error.code == 40003
```

---

## RTPO7 - value() returns bytes for binary entry

**Test ID**: `objects/unit/RTPO7/value-bytes-0`

**Spec requirement:** If resolved value is bytes, returns the raw binary data.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Assertions
```pseudo
ASSERT root.get("avatar").value() IS bytes [1, 2, 3]
```

---

## RTPO14 - compactJson() encodes bytes as base64 string

**Test ID**: `objects/unit/RTPO14/compact-json-bytes-0`

**Spec requirement:** Binary values encoded as base64 strings in JSON representation.

### Setup
```pseudo
{ client, channel, root, mock_ws } = AWAIT setup_synced_channel("test")
```

### Test Steps
```pseudo
result = root.compactJson()
```

### Assertions
```pseudo
ASSERT result["avatar"] == "AQID"
```
