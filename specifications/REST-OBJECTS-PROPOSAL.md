# REST Objects API Specification — Proposal

## Overview

This document proposes additions to the [Objects Features](./objects-features.md) specification to cover the **REST Objects API**. This API allows clients to read and modify LiveObjects state via REST, without maintaining a realtime connection.

The REST Objects API is accessed via `RestChannel#object`, which returns a `RestObject` instance. It provides three operations:

- **`get`** — read object state (compact or full)
- **`publish`** — modify objects (create, set, remove, increment)
- **`generateObjectId`** — pre-compute object IDs for batch operations

The ably-js implementation shipped in [PR #2109](https://github.com/ably/ably-js/pull/2109). This proposal derives its assertions from that implementation and its test suite.

---

## 1. Types Required

### 1.1 Types that need new spec definitions

These types are new to the REST Objects API and don't exist in the current specification:

| Type | Purpose |
|------|---------|
| `RestObject` | Main class; accessed via `RestChannel#object` |
| `RestObjectGetParams` | Parameters for `RestObject#get` |
| `RestObjectGetCompactResult` | Response type when `compact` is true (default) |
| `RestObjectGetFullResult` | Response type when `compact` is false |
| `RestLiveMap` | Full-mode representation of a map object |
| `RestLiveCounter` | Full-mode representation of a counter object |
| `RestObjectData` | Decoded leaf value in full-mode responses |
| `RestObjectOperation` | Union of all publish operation types |
| `PublishObjectData` | User-facing value type for publish operations |
| `RestObjectPublishResult` | Response from `publish` |
| `RestObjectGenerateIdResult` | Response from `generateObjectId` |

### 1.2 Existing types referenced (no changes needed)

| Type | Spec location | Usage |
|------|--------------|-------|
| `ObjectData` | [OD1-OD5](./features.md#OD1) | Wire-format leaf values; `RestObjectData` is the decoded form |
| `ObjectsMapSemantics` | [objects-features.md IDL](#idl) | Map semantics enum (`LWW`) |
| `ObjectOperationAction` | [OOP2](./features.md#OOP2) | Operation action enum |
| `ErrorInfo` | [features.md](./features.md) | Error reporting |

### 1.3 Spec points in features.md that need amending

| Spec point | Change needed |
|-----------|--------------|
| `RSL` (RestChannel) | Add `RSL16` for `RestChannel#object` attribute (parallels `RSL3` for presence, `RSL10` for annotations) |
| `PC5` (Objects plugin) | Extend to cover REST channels (currently only references realtime channels) |

---

## 2. Proposed Spec Point Prefix

Following the convention:
- `RSP` = RestPresence
- `RSAN` = RestAnnotations
- `RTL27` = RealtimeChannel#objects

Proposed prefix: **`RSO`** (Rest Object)

---

## 3. Proposed Specification

### 3.1 Amendments to features.md

#### RestChannel (additions)

```
- (RSL16) `RestChannel#object` attribute:
  - (RSL16a) Returns the `RestObject` object for this channel (RSO1)
  - (RSL16b) It is a programmer error to access this property without first
    providing the `Objects` plugin (PC5) in the client options. This programmer
    error should be handled in an idiomatic fashion; if this means accessing
    the property should throw an error, then the error should be an `ErrorInfo`
    with `statusCode` 400 and `code` 40019.
```

#### Plugin (amendment to PC5)

```
- (PC5) A plugin provided with the `PluginType` enum key value of `Objects`
  should provide the RealtimeObjects feature functionality for realtime
  channels (RTL27) and the RestObject feature functionality for REST
  channels (RSL16). ...
```

### 3.2 Additions to objects-features.md

---

### RestObject {#rest-object}

- `(RSO1)` `RestObject` is associated with a single channel and is accessible through `RestChannel#object`
  - `(RSO1a)` The `Objects` plugin ([PC5](../features#PC5)) must be provided in the client options for `RestObject` to be available

#### RestObject#get

- `(RSO2)` `RestObject#get` function:
  - `(RSO2a)` Expects an optional `RestObjectGetParams` argument with the following attributes:
    - `(RSO2a1)` `objectId` string (optional) — the object ID to fetch. If omitted, fetches the channel's root object
    - `(RSO2a2)` `path` string (optional) — a dot-separated path to navigate within the target object. When used with `objectId`, the path is relative to that object; otherwise relative to the root
    - `(RSO2a3)` `compact` boolean (optional, default `true`) — controls the response format. When `true`, returns a compact representation; when `false`, returns the full representation with object metadata
  - `(RSO2b)` Makes an HTTP GET request to `/channels/{channelName}/object` if no `objectId` is provided, or to `/channels/{channelName}/object/{objectId}` if one is provided
    - `(RSO2b1)` The `path` parameter, if provided, is included as a query parameter
    - `(RSO2b2)` The `compact` parameter, if provided, is included as a query parameter
  - `(RSO2c)` When `compact` is `true` (the default), returns a `RestObjectGetCompactResult`:
    - `(RSO2c1)` A `LiveCounter` is represented as a `Number`
    - `(RSO2c2)` A `LiveMap` is represented as a JSON object (`Dict`) whose keys are the non-tombstoned map entries. Each value is recursively compacted: `LiveCounter`s become numbers, nested `LiveMap`s become nested objects, and leaf values are returned as their native types (`String`, `Number`, `Boolean`)
    - `(RSO2c3)` A `bytes` leaf value is returned as a base64-encoded string when using the JSON protocol, or as a `Binary` when using the binary (MessagePack) protocol
    - `(RSO2c4)` A JSON-encoded leaf value (`JsonObject` or `JsonArray`) is returned as its JSON string representation (not parsed)
    - `(RSO2c5)` A cyclic object reference is represented as `{ objectId: String }` to avoid infinite structures
  - `(RSO2d)` When `compact` is `false`, returns a `RestObjectGetFullResult`:
    - `(RSO2d1)` If the target resolves to a `LiveMap`, the result is a `RestLiveMap` containing:
      - `(RSO2d1a)` `objectId` string — the object's ID. The root object has the ID `"root"`
      - `(RSO2d1b)` `map` object containing:
        - `(RSO2d1b1)` `semantics` `ObjectsMapSemantics` string — the map's conflict resolution semantics (e.g. `"lww"`)
        - `(RSO2d1b2)` `entries` `Dict<String, RestObjectDataMapEntry | RestLiveObjectMapEntry>` — the map's non-tombstoned entries, where each entry contains a `data` field. If the entry's value is a leaf, `data` is a `RestObjectData`; if it references another object, `data` is a `RestLiveObject` (nested recursively)
    - `(RSO2d2)` If the target resolves to a `LiveCounter`, the result is a `RestLiveCounter` containing:
      - `(RSO2d2a)` `objectId` string — the object's ID
      - `(RSO2d2b)` `counter` object containing:
        - `(RSO2d2b1)` `data` object containing `number` `Number` — the counter's current value
    - `(RSO2d3)` If the target resolves to a leaf value, the result is a `RestObjectData` object containing exactly one of the following fields:
      - `(RSO2d3a)` `string` string
      - `(RSO2d3b)` `number` number
      - `(RSO2d3c)` `boolean` boolean
      - `(RSO2d3d)` `bytes` `Binary` — decoded from base64 (JSON protocol) or received as binary (MessagePack protocol)
      - `(RSO2d3e)` `json` `JsonObject | JsonArray` — decoded (parsed) from the JSON string representation
  - `(RSO2e)` If the `objectId` does not exist, the library should indicate an error
  - `(RSO2f)` If the `path` does not resolve, the library should indicate an error

#### RestObject#publish

- `(RSO3)` `RestObject#publish` function:
  - `(RSO3a)` Expects a `RestObjectOperation` or an array of `RestObjectOperation` objects
  - `(RSO3b)` Makes an HTTP POST request to `/channels/{channelName}/object` with the operation(s) encoded in the request body
    - `(RSO3b1)` `ObjectData` values within the operations are encoded per [OD4](../features#OD4) before being sent to the server
  - `(RSO3c)` On success, returns a `RestObjectPublishResult` containing:
    - `(RSO3c1)` `messageId` string — the ID of the message containing the published operations
    - `(RSO3c2)` `channel` string — the channel name
    - `(RSO3c3)` `objectIds` array of string — the object IDs affected by the operation(s)
  - `(RSO3d)` A `RestObjectOperation` targets an object either by `objectId` string or by `path` string (dot-separated notation), but not both:
    - `(RSO3d1)` `objectId` string (optional) — the ID of the object to operate on
    - `(RSO3d2)` `path` string (optional) — a dot-separated path relative to the root object. A `*` wildcard segment matches all entries of the parent map at that level
    - `(RSO3d3)` For `mapCreate` and `counterCreate` operations, both `objectId` and `path` may be omitted (creates a standalone/orphaned object)
    - `(RSO3d4)` `id` string (optional) — an idempotency key. If two operations with the same `id` are published, only the first is applied
  - `(RSO3e)` A `RestObjectOperation` contains exactly one of the following operation-specific fields:
    - `(RSO3e1)` `mapCreate` — creates a new `LiveMap`:
      - `(RSO3e1a)` `semantics` `ObjectsMapSemantics` string — the conflict resolution semantics (e.g. `"lww"`)
      - `(RSO3e1b)` `entries` `Dict<String, { data: PublishObjectData }>` — the initial entries for the map. Each entry's `data` is a `PublishObjectData`
      - `(RSO3e1c)` When a `path` is provided, the server creates the map and sets the terminal key on the parent map to reference the new map
      - `(RSO3e1d)` When no `path` or `objectId` is provided, the map is created as a standalone object. Its `objectId` is returned in `RestObjectPublishResult.objectIds`
    - `(RSO3e2)` `counterCreate` — creates a new `LiveCounter`:
      - `(RSO3e2a)` `count` `Number` — the initial count value
      - `(RSO3e2b)` When a `path` is provided, the server creates the counter and sets the terminal key on the parent map to reference the new counter
      - `(RSO3e2c)` When no `path` or `objectId` is provided, the counter is created as a standalone object
    - `(RSO3e3)` `mapSet` — sets a key on a map:
      - `(RSO3e3a)` `key` string — the key to set
      - `(RSO3e3b)` `value` `PublishObjectData` — the value to set. May be a primitive value or an `objectId` reference
    - `(RSO3e4)` `mapRemove` — removes a key from a map:
      - `(RSO3e4a)` `key` string — the key to remove
    - `(RSO3e5)` `counterInc` — increments (or decrements) a counter:
      - `(RSO3e5a)` `number` `Number` — the amount to increment by (negative to decrement)
    - `(RSO3e6)` `mapCreateWithObjectId` — creates a map with a pre-computed object ID:
      - `(RSO3e6a)` `initialValue` string — the JSON-encoded initial value (as returned by `generateObjectId`)
      - `(RSO3e6b)` `nonce` string — the nonce used to generate the object ID (as returned by `generateObjectId`)
      - `(RSO3e6c)` The operation must also provide `objectId` — the pre-computed ID
    - `(RSO3e7)` `counterCreateWithObjectId` — creates a counter with a pre-computed object ID:
      - `(RSO3e7a)` `initialValue` string — the JSON-encoded initial value (as returned by `generateObjectId`)
      - `(RSO3e7b)` `nonce` string — the nonce used to generate the object ID (as returned by `generateObjectId`)
      - `(RSO3e7c)` The operation must also provide `objectId` — the pre-computed ID
  - `(RSO3f)` When an array of operations is provided, all operations are published atomically in a single request

#### RestObject#generateObjectId

- `(RSO4)` `RestObject#generateObjectId` function:
  - `(RSO4a)` Expects a `RestObjectCreateBody` argument containing exactly one of:
    - `(RSO4a1)` `mapCreate` — with `semantics` and `entries` as in [RSO3e1](#RSO3e1)
    - `(RSO4a2)` `counterCreate` — with `count` as in [RSO3e2](#RSO3e2)
  - `(RSO4b)` If neither `mapCreate` nor `counterCreate` is provided, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40003
  - `(RSO4c)` Generates a deterministic object ID using the following procedure:
    - `(RSO4c1)` Encodes the provided create body to a JSON string (the `initialValue`)
    - `(RSO4c2)` Generates a unique random nonce string
    - `(RSO4c3)` Obtains the current server time (as per [RTO16](../objects-features#RTO16))
    - `(RSO4c4)` Creates an `objectId` per [RTO14](../objects-features#RTO14), using `"map"` or `"counter"` as the type
  - `(RSO4d)` Returns a `RestObjectGenerateIdResult` containing:
    - `(RSO4d1)` `objectId` string — the generated object ID, matching the format `{type}:{base64url(SHA-256(initialValue:nonce))}@{msTimestamp}`
    - `(RSO4d2)` `nonce` string — the random nonce used in generation
    - `(RSO4d3)` `initialValue` string — the JSON-encoded initial value
  - `(RSO4e)` Each call generates a different `objectId` and `nonce` for the same input, because the nonce is random
  - `(RSO4f)` The `initialValue` is deterministic for the same input (same create body produces same `initialValue`)
  - `(RSO4g)` The returned values can be used directly with `mapCreateWithObjectId` or `counterCreateWithObjectId` in a subsequent `publish` call

#### PublishObjectData

- `(RSO5)` `PublishObjectData` represents a user-provided value for publish operations. It is a discriminated type where exactly one field is set:
  - `(RSO5a)` `string` string — a string value
  - `(RSO5b)` `number` `Number` — a numeric value
  - `(RSO5c)` `boolean` boolean — a boolean value
  - `(RSO5d)` `bytes` `Binary` — a binary value
  - `(RSO5e)` `json` `JsonObject | JsonArray` — a JSON-encodable value
  - `(RSO5f)` `objectId` string — a reference to another object by its object ID

---

### 3.3 Proposed IDL additions (for objects-features.md IDL section)

```
class RestObject: // RSO*
  get(RestObjectGetParams?) => io (RestObjectGetCompactResult | RestObjectGetFullResult) // RSO2
  publish(RestObjectOperation | [RestObjectOperation]) => io RestObjectPublishResult // RSO3
  generateObjectId(RestObjectCreateBody) => io RestObjectGenerateIdResult // RSO4

interface RestObjectGetParams: // RSO2a
  objectId: String? // RSO2a1
  path: String? // RSO2a2
  compact: Boolean? // RSO2a3, default true

// RestObjectGetCompactResult is not a class — it is a recursive JSON value:
// Number (for counters), Dict (for maps), String, Number, Boolean,
// String|Binary (for bytes), String (for JSON). See RSO2c.

interface RestLiveMap: // RSO2d1
  objectId: String // RSO2d1a
  map: { semantics: ObjectsMapSemantics, entries: Dict<String, { data: (RestObjectData | RestLiveObject) }> } // RSO2d1b

interface RestLiveCounter: // RSO2d2
  objectId: String // RSO2d2a
  counter: { data: { number: Number } } // RSO2d2b

// RestLiveObject = RestLiveMap | RestLiveCounter

interface RestObjectData: // RSO2d3
  string: String? // RSO2d3a
  number: Number? // RSO2d3b
  boolean: Boolean? // RSO2d3c
  bytes: Binary? // RSO2d3d
  json: (JsonObject | JsonArray)? // RSO2d3e

interface RestObjectOperation: // RSO3d, RSO3e
  objectId: String? // RSO3d1
  path: String? // RSO3d2
  id: String? // RSO3d4
  mapCreate: { semantics: ObjectsMapSemantics, entries: Dict<String, { data: PublishObjectData }> }? // RSO3e1
  counterCreate: { count: Number }? // RSO3e2
  mapSet: { key: String, value: PublishObjectData }? // RSO3e3
  mapRemove: { key: String }? // RSO3e4
  counterInc: { number: Number }? // RSO3e5
  mapCreateWithObjectId: { initialValue: String, nonce: String }? // RSO3e6
  counterCreateWithObjectId: { initialValue: String, nonce: String }? // RSO3e7

interface PublishObjectData: // RSO5
  string: String? // RSO5a
  number: Number? // RSO5b
  boolean: Boolean? // RSO5c
  bytes: Binary? // RSO5d
  json: (JsonObject | JsonArray)? // RSO5e
  objectId: String? // RSO5f

interface RestObjectPublishResult: // RSO3c
  messageId: String // RSO3c1
  channel: String // RSO3c2
  objectIds: [String] // RSO3c3

interface RestObjectGenerateIdResult: // RSO4d
  objectId: String // RSO4d1
  nonce: String // RSO4d2
  initialValue: String // RSO4d3
```

---

## 4. Behavioral Assertions (derived from ably-js test suite)

These are the testable assertions implied by the specification above, mapped to the test scenarios in `ably-js/test/rest/liveobjects.test.js`:

### 4.1 Plugin requirement

| Assertion | Spec |
|-----------|------|
| Accessing `channel.object` without the Objects plugin throws an error | RSL16b |
| Accessing `channel.object` with the Objects plugin returns a `RestObject` instance | RSL16a, RSO1 |

### 4.2 RestObject#get — compact mode (default)

| Assertion | Spec |
|-----------|------|
| Returns root object by default (no params) | RSO2a, RSO2b |
| Compact is the default format | RSO2a3 |
| Counters appear as numbers | RSO2c1 |
| Maps appear as plain objects | RSO2c2 |
| Empty maps appear as `{}` | RSO2c2 |
| Path parameter navigates to nested objects | RSO2a2 |
| All primitive data types returned correctly (string, number, boolean) | RSO2c2 |
| Bytes returned as base64 string (JSON) or binary (MessagePack) | RSO2c3 |
| JSON object values returned as JSON string (not parsed) | RSO2c4 |
| JSON array values returned as JSON string (not parsed) | RSO2c4 |

### 4.3 RestObject#get — full mode

| Assertion | Spec |
|-----------|------|
| Map result includes `objectId` and `map.semantics` = `"lww"` | RSO2d1a, RSO2d1b1 |
| Map result includes entries with typed data | RSO2d1b2 |
| Counter result includes `objectId` and `counter.data.number` | RSO2d2a, RSO2d2b1 |
| Root object has `objectId` = `"root"` | RSO2d1a |
| String leaf returns `{ string: ... }` | RSO2d3a |
| Number leaf returns `{ number: ... }` | RSO2d3b |
| Boolean leaf returns `{ boolean: ... }` | RSO2d3c |
| Bytes leaf returns `{ bytes: Binary }` (decoded) | RSO2d3d |
| JSON object leaf returns `{ json: parsed object }` | RSO2d3e |
| JSON array leaf returns `{ json: parsed array }` | RSO2d3e |

### 4.4 RestObject#get — objectId parameter

| Assertion | Spec |
|-----------|------|
| Fetch specific object by ID | RSO2a1, RSO2b |
| Combine objectId + path | RSO2a1, RSO2a2 |
| Non-existent objectId throws error | RSO2e |
| Non-existent path throws error | RSO2f |

### 4.5 RestObject#publish — mapSet

| Assertion | Spec |
|-----------|------|
| mapSet via objectId with all data types (string, number, boolean, bytes, json) | RSO3e3, RSO5 |
| mapSet via path | RSO3d2, RSO3e3 |
| mapSet via wildcard path (`*`) sets key on all children | RSO3d2, RSO3e3 |
| mapSet with objectId reference | RSO5f |
| Publish result contains messageId, channel, objectIds | RSO3c |

### 4.6 RestObject#publish — mapRemove

| Assertion | Spec |
|-----------|------|
| mapRemove via objectId | RSO3d1, RSO3e4 |
| mapRemove via path | RSO3d2, RSO3e4 |
| mapRemove via wildcard path | RSO3d2, RSO3e4 |
| Removed key no longer present in subsequent get | RSO3e4 |

### 4.7 RestObject#publish — counterInc

| Assertion | Spec |
|-----------|------|
| counterInc via objectId | RSO3d1, RSO3e5 |
| counterInc via path | RSO3d2, RSO3e5 |
| counterInc via wildcard path | RSO3d2, RSO3e5 |
| Counter value reflects increment | RSO3e5 |

### 4.8 RestObject#publish — mapCreate

| Assertion | Spec |
|-----------|------|
| mapCreate without path creates standalone object | RSO3e1d |
| mapCreate with path creates map and links to parent | RSO3e1c |
| mapCreate with all data types in entries | RSO3e1b, RSO5 |
| mapCreate with objectId reference entries | RSO5f |
| Created object retrievable by returned objectId | RSO3c3 |

### 4.9 RestObject#publish — counterCreate

| Assertion | Spec |
|-----------|------|
| counterCreate without path creates standalone counter | RSO3e2c |
| counterCreate with path creates counter and links to parent | RSO3e2b |

### 4.10 RestObject#publish — pre-computed IDs

| Assertion | Spec |
|-----------|------|
| mapCreateWithObjectId creates map with specified ID | RSO3e6 |
| counterCreateWithObjectId creates counter with specified ID | RSO3e7 |
| Returned objectIds array contains the pre-computed ID | RSO3c3, RSO3e6c |

### 4.11 RestObject#publish — idempotency

| Assertion | Spec |
|-----------|------|
| Duplicate publish with same `id` applied only once | RSO3d4 |

### 4.12 RestObject#generateObjectId

| Assertion | Spec |
|-----------|------|
| mapCreate body returns objectId matching `/^map:/` | RSO4d1 |
| counterCreate body returns objectId matching `/^counter:/` | RSO4d1 |
| Returns nonce (string) | RSO4d2 |
| Returns initialValue (valid JSON string) | RSO4d3 |
| Different calls for same payload produce different objectId and nonce | RSO4e |
| Same payload produces same initialValue | RSO4f |
| Missing mapCreate and counterCreate throws error (code 40003, statusCode 400) | RSO4b |
| Generated map ID works with mapCreateWithObjectId in publish | RSO4g |
| Generated counter ID works with counterCreateWithObjectId in publish | RSO4g |

---

## 5. Open Questions

1. **`RestObjectData` vs `ObjectData`**: The full-mode GET response returns decoded data (`bytes` as `Binary`, `json` as parsed object), which differs from the wire-format `ObjectData` ([OD2](../features#OD2)) where `bytes` is base64 and JSON is stored in `string` with `encoding: "json"`. Should `RestObjectData` be defined as "the result of decoding an `ObjectData` per [OD5](../features#OD5)"? Or is it a distinct type?

2. **Wildcard path semantics**: The `*` wildcard in paths is a server-side feature. The spec should clarify whether the SDK validates path syntax or passes it through to the server opaquely.

3. **Batch atomicity**: The tests imply that an array of operations is sent in a single HTTP request. Should the spec state whether the server applies them atomically (all-or-nothing), or is this a server-side concern outside the SDK spec?

4. **Error codes**: The ably-js tests only explicitly check one error code (40003 for missing create body in `generateObjectId`). The spec should define error codes for other failure cases (non-existent objectId, non-existent path) — or state that these are server-defined errors passed through by the SDK.

5. **Channel modes**: The realtime Objects API requires `OBJECT_SUBSCRIBE` and `OBJECT_PUBLISH` channel modes. Do these apply to the REST API, or are REST operations authorized purely via API key/token capabilities?

6. **Relationship to `RealtimeObjects`**: The realtime `createMap`/`createCounter` operations ([RTO11](../objects-features#RTO11), [RTO12](../objects-features#RTO12)) involve client-side ID generation and `publishAndApply`. The REST `mapCreate`/`counterCreate` operations delegate ID generation to the server (unless using `*WithObjectId`). Should the spec explicitly call out this difference?

7. **Discriminated unions and cross-language portability**: The proposed `RestObjectOperation` type is modeled as a discriminated union — a single type with optional `objectId`/`path`/`id` targeting fields and exactly one operation-specific field (`mapCreate`, `mapSet`, `counterInc`, etc.) set at a time. This mirrors the ably-js TypeScript types and the wire format directly. TypeScript models this naturally. Most other target languages (Dart, Java, Go, Python) do not have discriminated unions.

   The existing realtime spec avoids this problem entirely — `LiveMap#set()`, `LiveMap#remove()`, `LiveCounter#increment()`, `RealtimeObjects#createMap()` are all separate methods on separate classes. There is no "pass a polymorphic operation" pattern in the realtime public API. But the REST API needs one because `publish` supports **batch operations of mixed types** in a single request.

   **Option A — Keep the "flat" discriminated type** (as proposed). Each language adapts idiomatically: Dart uses sealed classes, Java uses a class hierarchy or builder, Go uses an interface. The spec describes the conceptual shape and leaves representation to implementations. This matches the existing `ObjectData` (OD2) pattern ("exactly one field set"), which every SDK already handles for the wire protocol.

   **Option B — Specify a class hierarchy.** An abstract `RestObjectOperation` base with concrete subtypes:

   ```
   class RestObjectOperation:          // abstract base
     objectId: String?                 // targeting
     path: String?
     id: String?                       // idempotency key

   class RestMapCreateOp extends RestObjectOperation:
     semantics: ObjectsMapSemantics
     entries: Dict<String, { data: PublishObjectData }>

   class RestMapSetOp extends RestObjectOperation:
     key: String
     value: PublishObjectData

   class RestMapRemoveOp extends RestObjectOperation:
     key: String

   class RestCounterCreateOp extends RestObjectOperation:
     count: Number

   class RestCounterIncOp extends RestObjectOperation:
     number: Number

   class RestMapCreateWithIdOp extends RestObjectOperation:
     initialValue: String
     nonce: String

   class RestCounterCreateWithIdOp extends RestObjectOperation:
     initialValue: String
     nonce: String
   ```

   Then `publish([RestObjectOperation])` works in every language — you pass an array of the base type, each element constructed as the appropriate subclass. This also parallels `ObjectOperation` (OOP3) which has an `action` enum and conditional fields — the class hierarchy is just a cleaner articulation of the same concept for a public API type.

   **Option B also affects response types.** `RestObjectGetFullResult` being `RestLiveMap | RestLiveCounter | RestObjectData` has the same issue in milder form — solvable with a common base type or a wrapper with a type discriminator field.

   The same concern applies more mildly to `PublishObjectData` (RSO5) — "exactly one of 6 fields" — though this matches the existing `ObjectData` (OD2) pattern that every SDK already handles.

   **Recommendation:** Option B (class hierarchy) for `RestObjectOperation` because it is user-constructed and the variants have structurally different shapes. Keep the "one-of" pattern for `PublishObjectData` and `RestObjectData` because they are leaf value containers matching the existing `ObjectData` precedent.
