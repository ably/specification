# Parent References Tests

Spec points: `RTLO3f`, `RTLO4g`, `RTLO4h`, `RTLO4f`, `RTO5c10`

## Test Type
Unit test — pure data structure, no mocks required.

## Purpose

Tests the `parentReferences` tracking on `LiveObject`, the `addParentReference` and `removeParentReference` methods, the `getFullPaths` graph traversal, and the post-sync rebuild of parentReferences by the ObjectsPool.

`parentReferences` is a `Dict<String, Set<String>>` keyed by parent InternalLiveMap objectId, with each value being the set of keys at which that InternalLiveMap references this LiveObject. These references allow `getFullPaths` to determine every key-path from root to a given object in the LiveObjects graph.

Tests operate directly on LiveObject/InternalLiveCounter/InternalLiveMap instances and on ObjectsPool for the post-sync rebuild tests.

## Shared Helpers

See `helpers/standard_test_pool.md` for builder functions and STANDARD_POOL_OBJECTS.

---

## RTLO3f2 - parentReferences initialized to empty map on InternalLiveCounter

**Test ID**: `objects/unit/RTLO3f2/init-empty-counter-0`

**Spec requirement:** parentReferences is set to an empty map when the LiveObject is initialized.

### Setup
```pseudo
counter = InternalLiveCounter(objectId: "counter:abc@1000")
```

### Assertions
```pseudo
ASSERT counter.parentReferences == {}
```

---

## RTLO3f2 - parentReferences initialized to empty map on InternalLiveMap

**Test ID**: `objects/unit/RTLO3f2/init-empty-map-0`

**Spec requirement:** parentReferences is set to an empty map when the LiveObject is initialized.

### Setup
```pseudo
map = InternalLiveMap(objectId: "map:abc@1000", semantics: "LWW")
```

### Assertions
```pseudo
ASSERT map.parentReferences == {}
```

---

## RTLO4g2 - addParentReference creates new entry for first reference

**Test ID**: `objects/unit/RTLO4g2/first-reference-new-entry-0`

| Spec | Requirement |
|------|-------------|
| RTLO4g2 | If parentReferences does not contain an entry for parent.objectId, insert a new entry with a set containing only key |

### Setup
```pseudo
child = InternalLiveCounter(objectId: "counter:child@1000")
parent = InternalLiveMap(objectId: "map:parent@1000", semantics: "LWW")
```

### Test Steps
```pseudo
child.addParentReference(parent, "score")
```

### Assertions
```pseudo
ASSERT "map:parent@1000" IN child.parentReferences
ASSERT child.parentReferences["map:parent@1000"] == {"score"}
```

---

## RTLO4g1 - addParentReference adds key to existing entry for same parent

**Test ID**: `objects/unit/RTLO4g1/second-key-same-parent-0`

| Spec | Requirement |
|------|-------------|
| RTLO4g1 | If parentReferences already contains an entry for parent.objectId, add key to that entry's set |

### Setup
```pseudo
child = InternalLiveCounter(objectId: "counter:child@1000")
parent = InternalLiveMap(objectId: "map:parent@1000", semantics: "LWW")
child.parentReferences = { "map:parent@1000": {"score"} }
```

### Test Steps
```pseudo
child.addParentReference(parent, "points")
```

### Assertions
```pseudo
ASSERT child.parentReferences["map:parent@1000"] == {"score", "points"}
```

---

## RTLO4g - addParentReference with different parent creates separate entry

**Test ID**: `objects/unit/RTLO4g/different-parent-separate-entry-0`

**Spec requirement:** Each parent InternalLiveMap gets its own entry in parentReferences.

### Setup
```pseudo
child = InternalLiveCounter(objectId: "counter:child@1000")
parent_a = InternalLiveMap(objectId: "map:a@1000", semantics: "LWW")
parent_b = InternalLiveMap(objectId: "map:b@1000", semantics: "LWW")
```

### Test Steps
```pseudo
child.addParentReference(parent_a, "x")
child.addParentReference(parent_b, "y")
```

### Assertions
```pseudo
ASSERT child.parentReferences["map:a@1000"] == {"x"}
ASSERT child.parentReferences["map:b@1000"] == {"y"}
```

---

## RTLO4g - addParentReference with multiple parents and multiple keys

**Test ID**: `objects/unit/RTLO4g/multiple-parents-multiple-keys-0`

**Spec requirement:** parentReferences correctly tracks multiple keys across multiple parents.

### Setup
```pseudo
child = InternalLiveCounter(objectId: "counter:child@1000")
parent_a = InternalLiveMap(objectId: "map:a@1000", semantics: "LWW")
parent_b = InternalLiveMap(objectId: "map:b@1000", semantics: "LWW")
```

### Test Steps
```pseudo
child.addParentReference(parent_a, "x")
child.addParentReference(parent_a, "y")
child.addParentReference(parent_b, "p")
child.addParentReference(parent_b, "q")
```

### Assertions
```pseudo
ASSERT child.parentReferences["map:a@1000"] == {"x", "y"}
ASSERT child.parentReferences["map:b@1000"] == {"p", "q"}
```

---

## RTLO4h1 - removeParentReference no-op for non-existent parent

**Test ID**: `objects/unit/RTLO4h1/nonexistent-parent-noop-0`

**Spec requirement:** If parentReferences does not contain an entry for parent.objectId, do nothing.

### Setup
```pseudo
child = InternalLiveCounter(objectId: "counter:child@1000")
parent = InternalLiveMap(objectId: "map:parent@1000", semantics: "LWW")
```

### Test Steps
```pseudo
child.removeParentReference(parent, "score")
```

### Assertions
```pseudo
ASSERT child.parentReferences == {}
```

---

## RTLO4h2 - removeParentReference removes key but leaves other keys

**Test ID**: `objects/unit/RTLO4h2/remove-key-leaves-others-0`

| Spec | Requirement |
|------|-------------|
| RTLO4h2 | Remove key from that entry's set |

### Setup
```pseudo
child = InternalLiveCounter(objectId: "counter:child@1000")
parent = InternalLiveMap(objectId: "map:parent@1000", semantics: "LWW")
child.parentReferences = { "map:parent@1000": {"score", "points"} }
```

### Test Steps
```pseudo
child.removeParentReference(parent, "score")
```

### Assertions
```pseudo
ASSERT child.parentReferences["map:parent@1000"] == {"points"}
```

---

## RTLO4h3 - removeParentReference removes entry when set becomes empty

**Test ID**: `objects/unit/RTLO4h3/remove-last-key-removes-entry-0`

| Spec | Requirement |
|------|-------------|
| RTLO4h2 | Remove key from that entry's set |
| RTLO4h3 | If the entry's set is empty after removal, remove the entry from parentReferences |

### Setup
```pseudo
child = InternalLiveCounter(objectId: "counter:child@1000")
parent = InternalLiveMap(objectId: "map:parent@1000", semantics: "LWW")
child.parentReferences = { "map:parent@1000": {"score"} }
```

### Test Steps
```pseudo
child.removeParentReference(parent, "score")
```

### Assertions
```pseudo
ASSERT "map:parent@1000" NOT IN child.parentReferences
ASSERT child.parentReferences == {}
```

---

## RTLO4h - removeParentReference for non-existent key in existing parent

**Test ID**: `objects/unit/RTLO4h/remove-nonexistent-key-0`

**Spec requirement:** Removing a key that does not exist in the parent's set does not alter the existing keys.

### Setup
```pseudo
child = InternalLiveCounter(objectId: "counter:child@1000")
parent = InternalLiveMap(objectId: "map:parent@1000", semantics: "LWW")
child.parentReferences = { "map:parent@1000": {"score"} }
```

### Test Steps
```pseudo
child.removeParentReference(parent, "nonexistent")
```

### Assertions
```pseudo
ASSERT child.parentReferences["map:parent@1000"] == {"score"}
```

---

## RTLO4f2 - getFullPaths for root returns empty key-path

**Test ID**: `objects/unit/RTLO4f2/root-returns-empty-path-0`

| Spec | Requirement |
|------|-------------|
| RTLO4f2 | The empty simple path (which exists only when this LiveObject is itself root) contributes the empty key-path [] |

### Setup
```pseudo
pool = ObjectsPool()
root = pool["root"]
```

### Assertions
```pseudo
paths = root.getFullPaths()
ASSERT paths.length == 1
ASSERT paths CONTAINS []
```

---

## RTLO4f - getFullPaths for direct child of root

**Test ID**: `objects/unit/RTLO4f/direct-child-single-path-0`

| Spec | Requirement |
|------|-------------|
| RTLO4f1 | Graph G has directed edges from parent to child labelled with key, derived from parentReferences |
| RTLO4f2 | Each simple path from root to this LiveObject contributes one key-path |

Tests that a LiveObject referenced directly from root at key "score" returns [["score"]].

### Setup
```pseudo
pool = ObjectsPool()
counter = InternalLiveCounter(objectId: "counter:score@1000")
pool["counter:score@1000"] = counter

root = pool["root"]
counter.addParentReference(root, "score")
```

### Assertions
```pseudo
paths = counter.getFullPaths()
ASSERT paths.length == 1
ASSERT paths CONTAINS ["score"]
```

---

## RTLO4f - getFullPaths for deeply nested object

**Test ID**: `objects/unit/RTLO4f/deep-nesting-0`

**Spec requirement:** getFullPaths traverses multiple levels of parentReferences to find all key-paths from root.

Tests the path root --"profile"--> map:profile --"prefs"--> map:prefs --"theme_counter"--> counter:theme.

### Setup
```pseudo
pool = ObjectsPool()
root = pool["root"]

profile = InternalLiveMap(objectId: "map:profile@1000", semantics: "LWW")
pool["map:profile@1000"] = profile
profile.addParentReference(root, "profile")

prefs = InternalLiveMap(objectId: "map:prefs@1000", semantics: "LWW")
pool["map:prefs@1000"] = prefs
prefs.addParentReference(profile, "prefs")

theme_counter = InternalLiveCounter(objectId: "counter:theme@1000")
pool["counter:theme@1000"] = theme_counter
theme_counter.addParentReference(prefs, "theme_counter")
```

### Assertions
```pseudo
paths = theme_counter.getFullPaths()
ASSERT paths.length == 1
ASSERT paths CONTAINS ["profile", "prefs", "theme_counter"]
```

---

## RTLO4f - getFullPaths with multiple parents (diamond graph)

**Test ID**: `objects/unit/RTLO4f/diamond-graph-0`

| Spec | Requirement |
|------|-------------|
| RTLO4f2 | Each simple path from root to this LiveObject contributes one key-path |
| RTLO4f3 | Each key-path appears exactly once; order is unspecified |

Tests a diamond: root --"a"--> map:A --"x"--> counter:leaf, and root --"b"--> map:B --"y"--> counter:leaf.

### Setup
```pseudo
pool = ObjectsPool()
root = pool["root"]

map_a = InternalLiveMap(objectId: "map:a@1000", semantics: "LWW")
pool["map:a@1000"] = map_a
map_a.addParentReference(root, "a")

map_b = InternalLiveMap(objectId: "map:b@1000", semantics: "LWW")
pool["map:b@1000"] = map_b
map_b.addParentReference(root, "b")

leaf = InternalLiveCounter(objectId: "counter:leaf@1000")
pool["counter:leaf@1000"] = leaf
leaf.addParentReference(map_a, "x")
leaf.addParentReference(map_b, "y")
```

### Assertions
```pseudo
paths = leaf.getFullPaths()
ASSERT paths.length == 2
ASSERT paths CONTAINS ["a", "x"]
ASSERT paths CONTAINS ["b", "y"]
```

---

## RTLO4f - getFullPaths with single parent referencing at multiple keys

**Test ID**: `objects/unit/RTLO4f/single-parent-multiple-keys-0`

| Spec | Requirement |
|------|-------------|
| RTLO4f2 | Each simple path from root contributes one key-path |
| RTLO4f3 | Each key-path appears exactly once |

Tests that when a parent map references the same child at two different keys, two distinct key-paths are returned.

### Setup
```pseudo
pool = ObjectsPool()
root = pool["root"]

child = InternalLiveCounter(objectId: "counter:child@1000")
pool["counter:child@1000"] = child
child.addParentReference(root, "primary")
child.addParentReference(root, "alias")
```

### Assertions
```pseudo
paths = child.getFullPaths()
ASSERT paths.length == 2
ASSERT paths CONTAINS ["primary"]
ASSERT paths CONTAINS ["alias"]
```

---

## RTLO4f - getFullPaths for orphan returns empty list

**Test ID**: `objects/unit/RTLO4f/orphan-returns-empty-0`

**Spec requirement:** An object with no parentReferences path leading to root has no key-paths.

### Setup
```pseudo
pool = ObjectsPool()

orphan = InternalLiveCounter(objectId: "counter:orphan@1000")
pool["counter:orphan@1000"] = orphan
```

### Assertions
```pseudo
paths = orphan.getFullPaths()
ASSERT paths.length == 0
```

---

## RTLO4f - getFullPaths suppresses cycles

**Test ID**: `objects/unit/RTLO4f/cycle-suppression-0`

| Spec | Requirement |
|------|-------------|
| RTLO4f2 | A simple path visits each node at most once |
| RTLO4f4 | (non-normative) Typical approach skips branches that would revisit a node |

Tests that a cycle in parentReferences does not cause infinite traversal. Graph: root --"a"--> map:A --"b"--> map:B --"a"--> map:A (cycle). The only valid simple path to map:B is ["a", "b"].

### Setup
```pseudo
pool = ObjectsPool()
root = pool["root"]

map_a = InternalLiveMap(objectId: "map:a@1000", semantics: "LWW")
pool["map:a@1000"] = map_a
map_a.addParentReference(root, "a")

map_b = InternalLiveMap(objectId: "map:b@1000", semantics: "LWW")
pool["map:b@1000"] = map_b
map_b.addParentReference(map_a, "b")

# Create a cycle: map:A also has map:B as a parent
map_a.addParentReference(map_b, "a")
```

### Assertions
```pseudo
paths_b = map_b.getFullPaths()
ASSERT paths_b.length == 1
ASSERT paths_b CONTAINS ["a", "b"]

paths_a = map_a.getFullPaths()
ASSERT paths_a.length == 1
ASSERT paths_a CONTAINS ["a"]
```

---

## RTLO4f - getFullPaths with complex diamond and deep nesting

**Test ID**: `objects/unit/RTLO4f/complex-diamond-deep-0`

**Spec requirement:** getFullPaths returns all distinct simple paths from root, including through multiple intermediate nodes.

Tests a graph where root has two branches that converge on a deeply nested object:
- root --"left"--> map:L --"mid"--> map:M --"target"--> counter:T
- root --"right"--> map:R --"target"--> counter:T

### Setup
```pseudo
pool = ObjectsPool()
root = pool["root"]

map_l = InternalLiveMap(objectId: "map:l@1000", semantics: "LWW")
pool["map:l@1000"] = map_l
map_l.addParentReference(root, "left")

map_r = InternalLiveMap(objectId: "map:r@1000", semantics: "LWW")
pool["map:r@1000"] = map_r
map_r.addParentReference(root, "right")

map_m = InternalLiveMap(objectId: "map:m@1000", semantics: "LWW")
pool["map:m@1000"] = map_m
map_m.addParentReference(map_l, "mid")

target = InternalLiveCounter(objectId: "counter:t@1000")
pool["counter:t@1000"] = target
target.addParentReference(map_m, "target")
target.addParentReference(map_r, "target")
```

### Assertions
```pseudo
paths = target.getFullPaths()
ASSERT paths.length == 2
ASSERT paths CONTAINS ["left", "mid", "target"]
ASSERT paths CONTAINS ["right", "target"]
```

---

## RTO5c10 - Post-sync rebuild populates parentReferences from InternalLiveMap entries

**Test ID**: `objects/unit/RTO5c10/rebuild-from-sync-0`

| Spec | Requirement |
|------|-------------|
| RTO5c10a | For each LiveObject in the ObjectsPool, reset parentReferences to empty map |
| RTO5c10b | For each InternalLiveMap, iterate entries; for each entry whose value is a LiveObject, call addParentReference on that LiveObject |

Tests that after a sync completes, parentReferences are rebuilt from the InternalLiveMap entries received during sync.

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
      entries: {
        "score": { data: { objectId: "counter:score@1000" }, timeserial: "t:0" },
        "profile": { data: { objectId: "map:profile@1000" }, timeserial: "t:0" }
      }
    },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  }),
  build_object_state("counter:score@1000", {"aaa": "t:0"}, {
    counter: { count: 100 },
    createOp: { counterCreate: { count: 100 } }
  }),
  build_object_state("map:profile@1000", {"aaa": "t:0"}, {
    map: {
      semantics: "LWW",
      entries: {
        "nested": { data: { objectId: "counter:nested@1000" }, timeserial: "t:0" }
      }
    },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  }),
  build_object_state("counter:nested@1000", {"aaa": "t:0"}, {
    counter: { count: 5 },
    createOp: { counterCreate: { count: 5 } }
  })
]))
```

### Assertions
```pseudo
ASSERT pool.syncState == SYNCED

# counter:score@1000 is referenced by root at key "score"
score = pool["counter:score@1000"]
ASSERT score.parentReferences["root"] == {"score"}

# map:profile@1000 is referenced by root at key "profile"
profile = pool["map:profile@1000"]
ASSERT profile.parentReferences["root"] == {"profile"}

# counter:nested@1000 is referenced by map:profile@1000 at key "nested"
nested = pool["counter:nested@1000"]
ASSERT nested.parentReferences["map:profile@1000"] == {"nested"}

# root has no parent references
ASSERT pool["root"].parentReferences == {}

# getFullPaths works correctly after rebuild
ASSERT score.getFullPaths() CONTAINS ["score"]
ASSERT nested.getFullPaths() CONTAINS ["profile", "nested"]
```

---

## RTO5c10a - Post-sync rebuild clears stale parentReferences

**Test ID**: `objects/unit/RTO5c10a/rebuild-clears-stale-refs-0`

| Spec | Requirement |
|------|-------------|
| RTO5c10a | For each LiveObject, reset parentReferences to the initial value (empty map) |
| RTO5c10b | Then rebuild from current InternalLiveMap entries |

Tests that parentReferences from a previous sync are cleared and rebuilt from the new sync data, even when objects are reused across syncs.

### Setup
```pseudo
pool = ObjectsPool()

# First sync: root --"score"--> counter:abc@1000
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync1:cursor", flags: HAS_OBJECTS
))
pool.processObjectSync(build_object_sync_message("test", "sync1:", [
  build_object_state("root", {"aaa": "t:0"}, {
    map: {
      semantics: "LWW",
      entries: {
        "score": { data: { objectId: "counter:abc@1000" }, timeserial: "t:0" }
      }
    },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  }),
  build_object_state("counter:abc@1000", {"aaa": "t:0"}, {
    counter: { count: 10 },
    createOp: { counterCreate: { count: 10 } }
  })
]))
ASSERT pool["counter:abc@1000"].parentReferences["root"] == {"score"}
```

### Test Steps
```pseudo
# Second sync: root --"points"--> counter:abc@1000 (key changed from "score" to "points")
pool.processAttached(ProtocolMessage(
  action: ATTACHED, channel: "test", channelSerial: "sync2:cursor", flags: HAS_OBJECTS
))
pool.processObjectSync(build_object_sync_message("test", "sync2:", [
  build_object_state("root", {"aaa": "t:1"}, {
    map: {
      semantics: "LWW",
      entries: {
        "points": { data: { objectId: "counter:abc@1000" }, timeserial: "t:1" }
      }
    },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  }),
  build_object_state("counter:abc@1000", {"aaa": "t:1"}, {
    counter: { count: 20 },
    createOp: { counterCreate: { count: 20 } }
  })
]))
```

### Assertions
```pseudo
counter = pool["counter:abc@1000"]

# Old "score" reference should be gone, replaced by "points"
ASSERT counter.parentReferences["root"] == {"points"}
ASSERT counter.getFullPaths() CONTAINS ["points"]

paths = counter.getFullPaths()
ASSERT paths.length == 1
```

---

## RTO5c10 - Post-sync unreferenced objects have empty parentReferences

**Test ID**: `objects/unit/RTO5c10/unreferenced-empty-refs-0`

**Spec requirement:** Objects that exist in the pool but are not referenced by any InternalLiveMap entry have empty parentReferences after rebuild.

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
      entries: {
        "name": { data: { string: "Alice" }, timeserial: "t:0" }
      }
    },
    createOp: { mapCreate: { semantics: "LWW", entries: {} } }
  }),
  build_object_state("counter:orphan@1000", {"aaa": "t:0"}, {
    counter: { count: 42 },
    createOp: { counterCreate: { count: 42 } }
  })
]))
```

### Assertions
```pseudo
ASSERT pool.syncState == SYNCED

# The counter exists in the pool but no InternalLiveMap entry points to it
orphan = pool["counter:orphan@1000"]
ASSERT orphan.parentReferences == {}

# getFullPaths returns empty list for unreferenced object
ASSERT orphan.getFullPaths().length == 0
```
