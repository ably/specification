# UTS Test Specs for LiveObjects Path-Based API

## Context

The LiveObjects feature lets clients store shared CRDT data on realtime channels. The specification is at `specification/specifications/objects-features.md` — the path-based API version squashed as commit `a397e34` ("LiveObjects path-based API spec").

An earlier attempt at UTS test specs exists in `uts/test/realtime/unit/objects/` (14 files). It was written against a different spec namespace (PO* vs RTPO*/RTINS*/RTLCV*/RTLMV*), used v5 wire format field names, had apply-on-ACK contradictions, and duplicated setup across files. We're doing a clean rewrite using the correct spec, informed by that earlier work.

All new test files go in `specification/uts/objects/`.

## Spec Architecture Summary

**Internal (not user-facing):** LiveObject, LiveCounter (CRDT counter), LiveMap (LWW map), ObjectsPool (sync state machine), RealtimeObject (channel orchestrator with publishAndApply)

**Public (user-facing):** PathObject (lazy path reference), Instance (identity-bound reference), LiveCounterValueType/LiveMapValueType (creation descriptors via static `create()` factories), PublicAPI::ObjectMessage/ObjectOperation (user-facing event metadata)

**Wire protocol v6:** `counterInc.number`, `mapSet.{key,value}`, `mapRemove.key`, `mapCreate.{semantics,entries}`, `counterCreateWithObjectId.{nonce,initialValue}`, `mapCreateWithObjectId.{nonce,initialValue}`

**REST API:** Not specified in objects-features.md. ably-js has REST object tests but those are implementation-specific, not spec'd. No REST test files needed.

---

## File Organization

### Helper
| File | Purpose |
|------|---------|
| `helpers/standard_test_pool.md` | Shared: standard ObjectsPool fixture, protocol message builders, synced-channel setup pattern |

### Pure Unit Tests (no mocks)
| File | Spec Points | ~Tests |
|------|-------------|--------|
| `unit/live_counter.md` | RTLC1-4, RTLC6-9, RTLC14, RTLC16, RTLO3-6, RTLO4b4d-e | ~23 |
| `unit/live_map.md` | RTLM1-9, RTLM14-16, RTLM18-19, RTLM22-25, RTLO3-6, RTLO4g-h, RTLO4e9 | ~38 |
| `unit/objects_pool.md` | RTO3-9, RTO5c10 | ~28 |
| `unit/object_id.md` | RTO14 | ~5 |
| `unit/value_types.md` | RTLCV1-4, RTLMV1-4 (evaluation generates ObjectMessages with v6 wire format) | ~19 |
| `unit/parent_references.md` | RTLO3f, RTLO4f-h, RTO5c10 (parentReferences, getFullPaths, add/remove/rebuild) | ~20 |
| `unit/public_object_message.md` | PAOM1-3, PAOOP1-3 (PublicAPI::ObjectMessage/ObjectOperation construction) | ~13 |

### Mock WebSocket Unit Tests
| File | Spec Points | ~Tests |
|------|-------------|--------|
| `unit/realtime_object.md` | RTO2, RTO10, RTO15-20, RTO22-26 (sync events, publish, publishAndApply, GC, RTO24/25/26 preconditions) | ~36 |
| `unit/live_counter_api.md` | RTLC5, RTLC11-13 (value, increment, decrement through channel) | ~13 |
| `unit/live_map_api.md` | RTLM5, RTLM10-13, RTLM20-21, RTLM24, RTLCV4, RTLMV4 (reads + mutations, value type evaluation) | ~20 |
| `unit/live_object_subscribe.md` | RTLO4b, RTLO4b4c3, RTLO4b4d-e, RTLO4b7 (subscribe, dispatch chain, tombstone cleanup, Subscription) | ~11 |
| `unit/path_object.md` | RTPO1-14, RTO25 (navigation, value, instance, entries, compact, compactJson, access preconditions) | ~27 |
| `unit/path_object_mutations.md` | RTPO15-18, RTPO3c2, RTO26 (set, remove, increment, decrement, write preconditions) | ~14 |
| `unit/path_object_subscribe.md` | RTPO19, RTO24 (path subscriptions, depth filtering, dispatch, PAOM delivery) | ~22 |
| `unit/instance.md` | RTINS1-16 (id, value, get, entries, size, compact, set, remove, increment, subscribe, RTO25/26) | ~21 |

### Integration Tests (sandbox)
| File | Spec Points | ~Tests |
|------|-------------|--------|
| `integration/objects_lifecycle_test.md` | RTO23, RTPO15, RTPO17 (create objects, mutate via PathObject, read back, REST provisioning) | ~6 |
| `integration/objects_sync_test.md` | RTO4, RTO5, RTO17 (attach, sync sequence, re-attach) | ~4 |
| ~~`integration/objects_batch_test.md`~~ | ~~Batch API not in current spec revision~~ | — |
| `integration/objects_gc_test.md` | RTO10, RTLM19 (behavioral GC verification with ADVANCE_TIME) | ~2 |

### Proxy Integration Tests
| File | Spec Points | ~Tests |
|------|-------------|--------|
| `integration/proxy/objects_faults.md` | RTO5a2, RTO7, RTO8, RTO17, RTO20e (sync interruption, mutation buffering during re-sync, server-initiated detach, publish failure on FAILED channel, publish during delayed sync) | ~5 |

**Totals: ~20 files, ~310 tests**

---

## Helper Spec Design

### `helpers/standard_test_pool.md`

**Standard test tree:**
```
root (LiveMap, objectId: "root")
  +-- "name" -> string "Alice"
  +-- "age" -> number 30
  +-- "active" -> boolean true
  +-- "score" -> objectId "counter:score@1000"
  +-- "profile" -> objectId "map:profile@1000"
  +-- "data" -> json {"tags": ["a", "b"]}
  +-- "avatar" -> bytes base64("AQID") (raw bytes: [1, 2, 3])

counter:score@1000 (LiveCounter, data: 100)

map:profile@1000 (LiveMap)
  +-- "email" -> string "alice@example.com"
  +-- "nested_counter" -> objectId "counter:nested@1000"
  +-- "prefs" -> objectId "map:prefs@1000"

counter:nested@1000 (LiveCounter, data: 5)

map:prefs@1000 (LiveMap)
  +-- "theme" -> string "dark"
```

**Builder functions:**
- `build_object_sync_message(channel, channelSerial, objectMessages[])` -> OBJECT_SYNC ProtocolMessage
- `build_object_message(channel, objectMessages[])` -> OBJECT ProtocolMessage
- `build_ack_message(msgSerial, serials[])` -> ACK ProtocolMessage with `res: [{ serials }]`
- `build_counter_inc(objectId, number, serial, siteCode)` -> ObjectMessage
- `build_map_set(objectId, key, value, serial, siteCode)` -> ObjectMessage
- `build_map_remove(objectId, key, serial, siteCode, serialTimestamp?)` -> ObjectMessage
- `build_map_clear(objectId, serial, siteCode)` -> ObjectMessage
- `build_object_delete(objectId, serial, siteCode, serialTimestamp?)` -> ObjectMessage
- `build_counter_create(objectId, counterCreate, serial, siteCode)` -> ObjectMessage
- `build_map_create(objectId, mapCreate, serial, siteCode)` -> ObjectMessage
- `build_object_state(objectId, siteTimeserials, {map?, counter?, tombstone?, createOp?})` -> ObjectMessage wrapping ObjectState

**Standard synced-channel pattern** (referenced by all mock-WS test files):
```pseudo
setup_synced_channel(channel_name):
  mock_ws = MockWebSocket(
    onConnectionAttempt: (conn) => conn.respond_with_success(
      ProtocolMessage(action: CONNECTED, connectionDetails: {
        connectionId: "conn-1",
        siteCode: "test-site",
        objectsGCGracePeriod: 86400000
      })
    ),
    onMessageFromClient: (msg) => {
      IF msg.action == ATTACH:
        mock_ws.send_to_client(ProtocolMessage(
          action: ATTACHED, channel: msg.channel,
          channelSerial: "attach-serial-1",
          flags: HAS_OBJECTS
        ))
        mock_ws.send_to_client(build_object_sync_message(
          msg.channel, "sync1:", STANDARD_POOL_OBJECTS
        ))
      ELSE IF msg.action == OBJECT:
        // Auto-ACK with generated serials
        serials = msg.state.map((_, i) => "ack-serial-" + i)
        mock_ws.send_to_client(build_ack_message(msg.msgSerial, serials))
    }
  )
  install_mock(mock_ws)
  client = Realtime(options: {key: "fake:key", autoConnect: true})
  channel = client.channels.get(channel_name, {modes: ["OBJECT_SUBSCRIBE", "OBJECT_PUBLISH"]})
  root = AWAIT channel.object.get()
  RETURN {client, channel, root, mock_ws}
```

---

## Pure Unit Test Design

### `unit/live_counter.md` -- CRDT Counter Data Structure

Directly construct `LiveCounter`, call `applyOperation()` and `replaceData()`, assert internal state.

**Key test groups:**
1. **Zero value (RTLC4):** data=0, siteTimeserials={}, createOperationIsMerged=false, isTombstone=false
2. **COUNTER_INC (RTLC9):** adds `counterInc.number` to data; noop when number missing
3. **COUNTER_CREATE (RTLC8/RTLC16):** merges `counterCreate.count`; noop when already merged
4. **Newness check (RTLO4a):** empty siteSerial allows apply; stale serial rejected; empty serial/siteCode logs warning
5. **siteTimeserials (RTLC7c):** CHANNEL source updates map; LOCAL source does not
6. **applyOperation returns bool (RTLC7g):** true on success, false on rejection/tombstone
7. **Tombstone (RTLC7e, RTLO4e, RTLO5):** OBJECT_DELETE tombstones; ops on tombstoned counter rejected
8. **replaceData (RTLC6):** full replacement; tombstone handling; createOp merge; diff calculation
9. **tombstonedAt (RTLO6):** from serialTimestamp if present, else local clock

### `unit/live_map.md` -- LWW Map Data Structure

Same pattern. Key additional concerns:

1. **MAP_SET (RTLM7):** new entry, existing entry update, LWW rejection, clearTimeserial floor (RTLM7h), objectId creates zero-value object (RTLM7g)
2. **MAP_REMOVE (RTLM8):** tombstones entry, sets tombstonedAt via RTLO6, clearTimeserial floor (RTLM8g)
3. **MAP_CLEAR (RTLM24):** sets clearTimeserial, removes entries with serial <= clear serial, preserves newer entries
4. **Entry-level LWW (RTLM9):** 5 serial comparison cases
5. **MAP_CREATE (RTLM16/RTLM23):** merges entries via individual MAP_SET/MAP_REMOVE calls
6. **replaceData (RTLM6):** sets clearTimeserial from ObjectState.map.clearTimeserial (RTLM6i)
7. **get/size/entries (RTLM5/RTLM10/RTLM11):** value resolution, tombstone filtering, objectId reference resolution
8. **GC (RTLM19):** removes tombstoned entries past grace period
9. **Diff (RTLM22):** non-tombstoned entry comparison

### `unit/objects_pool.md` -- Pool + Sync State Machine

Directly construct ObjectsPool, call `processAttached()`, `processObjectSync()`, `processObjectMessage()`.

1. **Initialization (RTO3):** root LiveMap always present
2. **ATTACHED handling (RTO4):** HAS_OBJECTS -> SYNCING; no flag -> clear pool + immediate SYNCED
3. **OBJECT_SYNC sequence (RTO5/RTO5f):** accumulate in SyncObjectsPool; partial merge (RTO5f2a); cursor parsing; new sequence discards old (RTO5a2)
4. **Sync completion (RTO5c):** replace existing (RTO5c1a), create new (RTO5c1b), remove absent (RTO5c2), emit updates (RTO5c7), apply buffered ops (RTO5c6), clear appliedOnAckSerials (RTO5c9), transition to SYNCED (RTO5c8)
5. **Buffering (RTO7/RTO8):** OBJECT messages buffered during SYNCING, applied when SYNCED
6. **Operation application (RTO9):** appliedOnAckSerials dedup (RTO9a3), LOCAL source adds to set (RTO9a2a4), null op warning (RTO9a1), unsupported action warning (RTO9a2b)
7. **Zero-value creation (RTO6):** infer type from objectId prefix
8. **GC (RTO10):** tombstoned objects removed after grace period

### `unit/object_id.md` -- ObjectId Generation (RTO14)

Pure function tests:
1. Format: `{type}:{base64url(SHA-256(initialValue:nonce))}@{timestamp}`
2. SHA-256 of UTF-8 `{initialValue}:{nonce}` -> base64url (RFC 4648 s.5)
3. `map` and `counter` type prefixes
4. Deterministic: same inputs -> same objectId
5. Different nonce -> different objectId

### `unit/value_types.md` -- LiveCounterValueType / LiveMapValueType

Tests the static `create()` factories and evaluation procedure.

**LiveCounterValueType (RTLCV1-4):**
1. `LiveCounter.create(42)` -> immutable LiveCounterValueType with count=42
2. `LiveCounter.create()` -> count defaults to 0
3. Evaluation: validates count, builds CounterCreate, generates objectId, returns ObjectMessage with `counterCreateWithObjectId.{nonce, initialValue}`
4. Non-number count throws 40003 during evaluation

**LiveMapValueType (RTLMV1-4):**
1. `LiveMap.create({entries})` -> immutable LiveMapValueType
2. Evaluation: validates keys/values, builds entries, generates objectId, returns ObjectMessage with `mapCreateWithObjectId.{nonce, initialValue}`
3. Nested value types: LiveMapValueType containing LiveCounterValueType -> depth-first ObjectMessage array (inner creates before outer)
4. Retains local MapCreate/CounterCreate alongside wire format (RTLMV4j5/RTLCV4g5)

---

## Mock WebSocket Test Design

### `unit/realtime_object.md` -- Orchestration

Uses `setup_synced_channel()` from helper.

**Key tests:**
- **RTO23:** get() requires OBJECT_SUBSCRIBE, throws on DETACHED/FAILED, waits for SYNCED, returns PathObject
- **RTO2:** channel mode enforcement (granted vs requested modes)
- **RTO15/RTO15h:** publish sends OBJECT PM, returns PublishResult from ACK res array
- **RTO20:** publishAndApply: publishes, constructs synthetic messages with siteCode from ConnectionDetails, applies with source=LOCAL, adds to appliedOnAckSerials
- **RTO20c:** fails gracefully when siteCode or serials missing
- **RTO20d1:** null serial in PublishResult (conflated op) is skipped
- **RTO20e:** waits for SYNCED during SYNCING; fails with 92008 if channel enters DETACHED/SUSPENDED/FAILED
- **RTO17/RTO18/RTO19:** sync state events, on/off registration
- **RTO10:** GC with fake timers + ADVANCE_TIME

### `unit/path_object.md` -- Read Operations

- **RTPO4:** path() string representation with dot escaping
- **RTPO5/RTPO6:** get(key) / at("a.b.c") -- pure navigation, no resolution
- **RTPO7:** value() -- counter returns number, primitive returns value, LiveMap returns null, unresolvable returns null
- **RTPO8:** instance() -- LiveObject returns Instance, primitive returns null
- **RTPO9-11:** entries/keys/values -- yields [key, PathObject] pairs for LiveMap entries
- **RTPO12:** size() -- non-tombstoned entry count
- **RTPO13:** compact() -- recursive, cycle detection with shared object references
- **RTPO14:** compactJson() -- binary as base64, cycles as {objectId: ...}
- **RTPO3:** path resolution (RTPO3a): walk segments through LiveMaps; fail if intermediate not LiveMap

### `unit/path_object_mutations.md` -- Write Operations

- **RTPO15:** set(value) -- constructs ObjectMessages, calls publishAndApply
- **RTPO16:** remove() -- constructs MAP_REMOVE ObjectMessage
- **RTPO17:** increment(n) -- constructs COUNTER_INC ObjectMessage
- **RTPO18:** decrement(n) -- delegates to increment(-n)
- **RTPO3c2:** mutation on unresolvable path throws 92007

### `unit/path_object_subscribe.md` -- Path-Based Subscriptions

- **RTPO19:** subscribe returns Subscription (RTPO19d), listener receives PathObjectSubscriptionEvent (RTPO19e)
- **RTPO19b:** checks RTO25 access API preconditions
- **RTPO19c1:** depth filtering -- depth=1 (self only), depth=2 (self+children), undefined (all)
- **RTPO19c1a:** non-positive depth throws 40003
- **RTPO19e2:** event.message carries PublicAPI::ObjectMessage when operation present
- **RTPO19f:** follows path not identity -- object replacement at path -> subscription tracks new object
- **RTO24b2a:** candidate path construction includes map update keys
- **RTO24c1:** coverage rule: prefix match + depth constraint
- **RTO24b2c:** listener exception caught, doesn't affect other listeners
- **RTO24b1:** multi-path dispatch via getFullPaths

### `unit/instance.md` -- Identity-Bound Reference

- **RTINS1:** id property returns objectId
- **RTINS2:** value() -- counter returns number, map returns null
- **RTINS3-5:** get(key), entries(), keys(), values() -- delegate to underlying LiveMap
- **RTINS6:** size() -- non-tombstoned entry count
- **RTINS7:** compact() -- recursive with cycle detection
- **RTINS8:** compactJson()
- **RTINS9-12:** set, remove, increment, decrement -- construct ObjectMessages, call publishAndApply
- **RTINS13-16:** subscribe/unsubscribe with depth filtering
- **RTINS17:** instance follows identity not path -- object replacement at path doesn't affect Instance
- **RTINS18:** operations on tombstoned Instance throw error

### `unit/live_counter_api.md` -- Counter Through Channel

- **RTLC5:** value property returns current data
- **RTLC11/RTLC12:** increment/decrement construct correct v6 wire ObjectMessage
- **RTLC12d:** echoMessages=false skips publishAndApply, uses publish
- **RTLC13:** increment with non-number throws 40003

### `unit/live_map_api.md` -- Map Through Channel

- **RTLM5:** get(key) returns resolved value
- **RTLM10/RTLM11:** entries/keys/values iterate non-tombstoned entries
- **RTLM12/RTLM13:** set/remove construct correct v6 wire ObjectMessages
- **RTLM20:** set with LiveCounterValueType/LiveMapValueType evaluates value type
- **RTLM20d/RTLM21d:** echoMessages=false uses publish instead of publishAndApply
- **RTLM24:** clear constructs MAP_CLEAR ObjectMessage

### `unit/live_object_subscribe.md` -- Internal Subscription

- **RTLO4b:** subscribe(listener) registers on internal LiveObject, returns Subscription (RTLO4b7)
- **RTLO4b4c3:** dispatch chain: direct listeners → path dispatch → tombstone cleanup
- **RTLO4b4d/e:** LiveObjectUpdate carries objectMessage and tombstone fields
- Subscription#unsubscribe deregisters (idempotent)
- Tombstone update deregisters all direct listeners (RTLO4b4c3c)

### `unit/parent_references.md` -- parentReferences Tracking

- **RTLO3f:** parentReferences initialized to empty Dict<String, Set<String>>
- **RTLO4g/RTLO4h:** addParentReference/removeParentReference methods
- **RTLO4f:** getFullPaths — DFS traversal of inverse parentReferences graph, simple paths only
- **RTO5c10:** post-sync parentReferences rebuild from LiveMap entries

### `unit/public_object_message.md` -- User-Facing Event Types

- **PAOM1-3:** PublicAPI::ObjectMessage construction from internal ObjectMessage
- **PAOOP1-3:** PublicAPI::ObjectOperation construction, mapCreate/counterCreate resolution from *WithObjectId variants

---

## Apply-on-ACK Testing Strategy

The RTO20 publishAndApply flow:
1. Client publishes OBJECT PM
2. Server returns ACK with `res: [{ serials: [...] }]`
3. Client constructs synthetic inbound ObjectMessages (serial + siteCode from ConnectionDetails)
4. Applies via RTO9 with source=LOCAL -> adds serials to `appliedOnAckSerials`
5. When echoed OBJECT PM arrives with same serial -> RTO9a3 deduplicates and removes from set

**Mock WS handler for mutation tests:**
```pseudo
onMessageFromClient: (msg) => {
  IF msg.action == OBJECT:
    serials = []
    FOR i IN 0..msg.state.length-1:
      serials.append("ack-" + msg.msgSerial + "-" + i)
    mock_ws.send_to_client(build_ack_message(msg.msgSerial, serials))
}
```

**Tests verify:**
1. After `AWAIT pathObject.set(...)`, local state reflects the change
2. The correct OBJECT PM was sent (v6 wire format)
3. When echo arrives with same serial, no double-application
4. If ACK arrives during SYNCING (RTO20e), publishAndApply waits for SYNCED

---

## Dependency Ordering (write order)

1. `helpers/standard_test_pool.md`
2. `unit/parent_references.md` -- foundational for graph tracking
3. `unit/public_object_message.md` -- standalone type construction
4. `unit/live_counter.md` -- no dependencies
5. `unit/live_map.md` -- no dependencies
6. `unit/object_id.md` -- no dependencies
7. `unit/objects_pool.md` -- uses LiveCounter/LiveMap concepts
8. `unit/value_types.md` -- uses objectId generation
9. `unit/realtime_object.md` -- uses helper, tests orchestration
10. `unit/live_counter_api.md` -- uses helper
11. `unit/live_map_api.md` -- uses helper
12. `unit/live_object_subscribe.md` -- uses helper
13. `unit/path_object.md` -- uses helper
14. `unit/instance.md` -- uses helper
15. `unit/path_object_mutations.md` -- uses helper
16. `unit/path_object_subscribe.md` -- uses helper
17. `integration/objects_lifecycle_test.md`
18. `integration/objects_sync_test.md`
19. `integration/objects_gc_test.md`
20. `integration/proxy/objects_faults.md`

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Wire format v6 everywhere | Spec branch uses v6 field names; old v5 names are "replaced by" stubs |
| `appliedOnAckSerials` on RealtimeObject (RTO7b), not on pool | Matches spec's placement; cleared at sync completion (RTO5c9) |
| No REST test files | objects-features.md has no REST API spec points; REST used only for integration fixture provisioning |
| `echoMessages` check moved to RTO26 | RTO26c checks echoMessages=false; callers (PathObject/Instance) enforce via RTO26 |
| Batch API deferred | Not included in current spec revision (a397e34); may be added in a future spec update |
| LiveObject/LiveMap/LiveCounter marked internal but still unit-tested | Direct testing of CRDT logic is essential; public API tests can't cover all edge cases |
| Test IDs use `objects/unit/` prefix | Matches directory structure, not nested under `realtime/` |
| Behavioral GC testing via ADVANCE_TIME | Verify GC through observable consequences (value becomes null, object recreatable) rather than internal pool state inspection |
| Table-driven tests for input validation | Use FOR loops over scenario arrays (like ably-js forScenarios) to test all invalid/valid type combinations |
| Bytes data type coverage | Standard test pool includes "avatar" bytes entry; compact/compactJson/value tests verify base64 encoding |
