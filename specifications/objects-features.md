---
title: Objects Features
---

## Overview

This document outlines the feature specification for the Objects feature, including both its Realtime entry point ([RealtimeObjects](#realtime-objects)) and its REST entry point ([RestObject](#rest-object)). It is currently under development and stored separately from the main specification to simplify the initial implementation of the feature in other SDKs. Once completed, it will be moved to the main [features](../features) spec.

Objects feature enables clients to store shared data as "objects" on a channel. When an object is updated, changes are automatically propagated to all subscribed clients in realtime, ensuring each client always sees the latest state.

### RestObject {#rest-object}

- `(RSO1)` `RestObject` is the entry point for object operations performed by a REST client:
  - `(RSO1a)` There is one `RestObject` instance per `RestChannel`, accessed via the [`RestChannel#object`](../features#RSL16) attribute.
  - `(RSO1b)` The `LiveObjects` plugin that provides [`RealtimeObjects`](#RTO1) for realtime channels also provides `RestObject` for REST channels; see [PC5](../features#PC5).
- `(RSO2)` `RestObject#get` function:
  - `(RSO2a)` Expects the following arguments:
    - `(RSO2a1)` `params` `RestObjectGetParams` (optional) - the request parameters, with the following fields:
      - `(RSO2a1a)` `objectId` `String` (optional) - the identifier of the object to fetch. If omitted, the channel object is used as the target
      - `(RSO2a1b)` `path` `String` (optional) - a sub-path within the target, evaluated relative to the channel object or the specified `objectId`. The library must treat the value opaquely; see [RSO6](#RSO6)
      - `(RSO2a1c)` `compact` `Boolean` (optional, default `true`) - selects the response format
  - `(RSO2b)` The return type depends on `params.compact`:
    - `(RSO2b1)` When `params.compact` is `true` or omitted, returns a `RestObjectGetCompactResult` ([RSO8](#RSO8))
    - `(RSO2b2)` When `params.compact` is `false`, returns a `RestObjectGetFullResult` ([RSO9](#RSO9))
  - `(RSO2c)` Sends a `GET` request to `/channels/{channelName}/object`, with `/{objectId}` appended only if `params.objectId` is provided. The `objectId` path segment must be percent-encoded per [RFC 3986 §2.1](https://datatracker.ietf.org/doc/html/rfc3986#section-2.1).
  - `(RSO2d)` The `params.path` and `params.compact` fields, if provided, must be sent as URL query string parameters.
  - `(RSO2e)` The response body must be decoded per [RSC8](../features#RSC8).
  - `(RSO2f)` When `params.compact` is `true` or omitted, the decoded response body must be returned to the caller verbatim. The library must perform no further structural transformation or decoding.
  - `(RSO2g)` When `params.compact` is `false`, the library must decode the response as follows. Let `wireNode` be the decoded response body:
    - `(RSO2g1)` If `wireNode` has a `map` field, return a `RestLiveMap` ([RSO14](#RSO14)). Each `map.entries[key].data` must be recursively decoded by re-applying the rules of [RSO2g](#RSO2g) to the entry value
    - `(RSO2g2)` If `wireNode` has a `counter` field, return a `RestLiveCounter` ([RSO15](#RSO15)) without further decoding
    - `(RSO2g3)` Otherwise, treat `wireNode` as an [`ObjectData`](../features#OD1) leaf and decode it per [OD5](../features#OD5)
    - `(RSO2g4)` Unrecognized object shapes or `ObjectData` fields must be passed through to the caller unmodified, in accordance with [RSF1](../features#RSF1)
  - `(RSO2h)` The library must not perform client-side validation of `params.objectId` or `params.path` content; any server-returned error must be surfaced to the caller as a rejected `ErrorInfo`.
- `(RSO3)` `RestObject#publish` function:
  - `(RSO3a)` Expects the following arguments:
    - `(RSO3a1)` `op` `RestObjectOperation` ([RSO5](#RSO5)) or `RestObjectOperation[]` - a single operation or an array of operations to publish
  - `(RSO3b)` The return type is a `RestObjectPublishResult` ([RSO10](#RSO10)).
  - `(RSO3c)` When `op` is an array, all operations must be sent in a single server request.
  - `(RSO3d)` Constructs the wire payload for each operation as follows:
    - `(RSO3d1)` If the operation includes a `mapCreate.semantics` field, the library must encode the semantics value per [OMP2](../features#OMP2). If the value is unrecognized, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40003
    - `(RSO3d2)` Any [`ObjectData`](../features#OD1) values reachable from the operation must be encoded per [OD4](../features#OD4). This applies at least to `mapSet.value` and to the `data` field of each entry in `mapCreate.entries`
    - `(RSO3d3)` The `id`, `objectId`, and `path` fields of the operation, if provided by the caller, must be preserved verbatim in the wire payload
    - `(RSO3d4)` The library must not include an explicit [`ObjectOperationAction`](../features#OOP2) `action` field in the wire payload; the action is inferred from the operation-specific field that is set
  - `(RSO3e)` Sends a `POST` request to `/channels/{channelName}/object` with the encoded operations as a JSON array body, encoded per [RSC8](../features#RSC8).
  - `(RSO3f)` The library must not auto-generate `RestObjectOperation.id` values. The [`idempotentRestPublishing`](../features#TO3n) option ([RSL1k1](../features#RSL1k1)) does not apply to `RestObject#publish`.
  - `(RSO3g)` The library must not perform client-side validation of operation targeting (combinations of `objectId` and `path`); any server-returned error must be surfaced to the caller as a rejected `ErrorInfo`.
  - `(RSO3h)` The library must not enforce a client-side limit on the number of operations in a batch; any size limit is server-enforced and surfaced via the response as a rejected `ErrorInfo`.
- `(RSO4)` `RestObject#generateObjectId` function:
  - `(RSO4a)` Expects the following arguments:
    - `(RSO4a1)` `createBody` `RestObjectGenerateIdBody` ([RSO12](#RSO12)) - a body containing either a `mapCreate` or a `counterCreate` field
  - `(RSO4b)` The return type is a `RestObjectGenerateIdResult` ([RSO11](#RSO11)). The library performs no I/O for this function: the returned values are computed locally and are intended to be supplied by the caller to a subsequent `mapCreateWithObjectId` ([RSO5d](#RSO5d)) or `counterCreateWithObjectId` ([RSO5h](#RSO5h)) operation.
  - `(RSO4c)` If neither `createBody.mapCreate` nor `createBody.counterCreate` is provided, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40003.
  - `(RSO4d)` The `type` argument for [RTO14](#RTO14) is `map` if `createBody.mapCreate` was provided, or `counter` if `createBody.counterCreate` was provided.
  - `(RSO4e)` Constructs the JSON-encoded `initialValue` string as follows. The `initialValue` is always carried as a JSON string regardless of the connection's negotiated transport format, so encoding must use the JSON protocol rules from [OD4d](../features#OD4d):
    - `(RSO4e1)` If `createBody.mapCreate` was provided:
      - `(RSO4e1a)` The library must encode `createBody.mapCreate.semantics` per [OMP2](../features#OMP2). If the value is unrecognized, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40003
      - `(RSO4e1b)` For each entry in `createBody.mapCreate.entries`, the library must encode the entry's `data` value per [OD4d](../features#OD4d)
      - `(RSO4e1c)` The library must produce a JSON-string representation of the resulting body, equivalent to [RTO11f15](#RTO11f15)
    - `(RSO4e2)` If `createBody.counterCreate` was provided, the library must produce a JSON-string representation of the body, equivalent to [RTO12f13](#RTO12f13)
  - `(RSO4f)` Generates a unique string `nonce`, as described in [RTO11f6](#RTO11f6).
  - `(RSO4g)` Retrieves the current server time as described in [RTO16](#RTO16).
  - `(RSO4h)` Constructs an `objectId` as described in [RTO14](#RTO14), passing the `type` from [RSO4d](#RSO4d), the `initialValue` from [RSO4e](#RSO4e), the `nonce` from [RSO4f](#RSO4f), and the server time from [RSO4g](#RSO4g).
  - `(RSO4i)` Returns a `RestObjectGenerateIdResult` containing the `objectId`, `nonce`, and `initialValue`.
  - `(RSO4j)` Two invocations with the same `createBody` produce different `objectId` and `nonce` values, because `nonce` is freshly generated per call ([RSO4f](#RSO4f)) and feeds into the `objectId` derivation ([RTO14](#RTO14)).
  - `(RSO4k)` The `initialValue` is deterministic for a given `createBody`: identical input produces identical output. This follows from the encoding procedure in [RSO4e](#RSO4e), which depends only on the input.
- `(RSO5)` `RestObjectOperation` is the public input type accepted by [`RestObject#publish`](#RSO3). It is a tagged union of operation payloads:
  - `(RSO5a)` Common fields available on every `RestObjectOperation`:
    - `(RSO5a1)` `id` `String` (optional) - per-operation message ID for idempotent publishing; see [RSO3f](#RSO3f)
    - `(RSO5a2)` `objectId` `String` (optional) - targets a specific object by ID
    - `(RSO5a3)` `path` `String` (optional) - targets one or more objects by their location in the channel object; see [RSO6](#RSO6)
  - `(RSO5b)` Each `RestObjectOperation` must include exactly one of the operation-specific body fields defined in [RSO5c](#RSO5c) through [RSO5i](#RSO5i).
    - `(RSO5b1)` If a caller-supplied `RestObjectOperation` has zero, or more than one, of these body fields set, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40003 before sending any HTTP request.
  - `(RSO5c)` `mapCreate` operation - creates a new map. Body type is `RestObjectMapCreate`:
    - `(RSO5c1)` `semantics` `ObjectsMapSemantics` enum ([OMP2](../features#OMP2))
    - `(RSO5c2)` `entries` `Dict<String, RestObjectMapEntry>` ([RSO13](#RSO13)) - the initial entries for the map
    - `(RSO5c3)` The `objectId` common field ([RSO5a2](#RSO5a2)) must not be set; the `path` common field ([RSO5a3](#RSO5a3)) is optional. If `path` is also omitted, the operation creates a standalone object whose identifier is returned in the response.
  - `(RSO5d)` `mapCreateWithObjectId` operation - creates a new map using a client-supplied object ID generated via [`generateObjectId`](#RSO4). Body type is `RestObjectCreateWithObjectId`:
    - `(RSO5d1)` `initialValue` `String` - the JSON-encoded initial value used when generating the `objectId`. The caller must use the value returned by [`generateObjectId`](#RSO4) unchanged
    - `(RSO5d2)` `nonce` `String` - the nonce used when generating the `objectId`. The caller must use the value returned by [`generateObjectId`](#RSO4) unchanged
    - `(RSO5d3)` The `objectId` common field ([RSO5a2](#RSO5a2)) must be set to the `objectId` value returned by the [`generateObjectId`](#RSO4) call that produced `initialValue` and `nonce`; the `path` common field ([RSO5a3](#RSO5a3)) must not be set.
  - `(RSO5e)` `mapSet` operation - sets a key in an existing map. Body type is `RestObjectMapSet`:
    - `(RSO5e1)` `key` `String` - the key to set
    - `(RSO5e2)` `value` `PublishObjectData` ([RSO7](#RSO7)) - the value to assign to the key
    - `(RSO5e3)` Exactly one of the `objectId` ([RSO5a2](#RSO5a2)) or `path` ([RSO5a3](#RSO5a3)) common fields must be set.
  - `(RSO5f)` `mapRemove` operation - removes a key from an existing map. Body type is `RestObjectMapRemove`:
    - `(RSO5f1)` `key` `String` - the key to remove
    - `(RSO5f2)` Exactly one of the `objectId` ([RSO5a2](#RSO5a2)) or `path` ([RSO5a3](#RSO5a3)) common fields must be set.
  - `(RSO5g)` `counterCreate` operation - creates a new counter. Body type is `RestObjectCounterCreate`:
    - `(RSO5g1)` `count` `Number` - the initial value of the counter
    - `(RSO5g2)` The `objectId` common field ([RSO5a2](#RSO5a2)) must not be set; the `path` common field ([RSO5a3](#RSO5a3)) is optional. If `path` is also omitted, the operation creates a standalone object whose identifier is returned in the response.
  - `(RSO5h)` `counterCreateWithObjectId` operation - creates a new counter using a client-supplied object ID generated via [`generateObjectId`](#RSO4). Body type and field constraints (including the targeting rules of [RSO5d3](#RSO5d3)) are the same as [RSO5d](#RSO5d).
  - `(RSO5i)` `counterInc` operation - changes the value of an existing counter by a signed `Number` amount. Body type is `RestObjectCounterInc`:
    - `(RSO5i1)` `number` `Number` - the amount to add to the counter (use a negative value to decrement)
    - `(RSO5i2)` Exactly one of the `objectId` ([RSO5a2](#RSO5a2)) or `path` ([RSO5a3](#RSO5a3)) common fields must be set.
  - `(RSO5j)` For plain `mapCreate` ([RSO5c](#RSO5c)) and `counterCreate` ([RSO5g](#RSO5g)) operations, the server generates the `objectId` and returns it in [`RestObjectPublishResult.objectIds`](#RSO10c). This differs from [`RealtimeObjects#createMap`](#RTO11) and [`RealtimeObjects#createCounter`](#RTO12), where the client library generates the `objectId` locally per [RTO14](#RTO14) before publishing the create operation. The `mapCreateWithObjectId` ([RSO5d](#RSO5d)) and `counterCreateWithObjectId` ([RSO5h](#RSO5h)) operations provide equivalent client-side ID generation for REST callers via [`RestObject#generateObjectId`](#RSO4), which is useful when a batch needs to reference newly-created objects by ID before the server has assigned them.
- `(RSO6)` The library must pass caller-supplied `path` strings (in [`RestObject#get`](#RSO2) `params` and in [`RestObjectOperation`](#RSO5)) to the server without modification or normalization. Path semantics are server-defined.
- `(RSO7)` `PublishObjectData` is the user-facing leaf value type used in [`RestObjectOperation`](#RSO5) fields that carry a leaf value, such as the `value` field of [`mapSet`](#RSO5e) and the `data` field of each entry in `mapCreate.entries` ([RSO5c2](#RSO5c2)). Exactly one of the following typed fields must be set:
  - `(RSO7a)` `string` `String`
  - `(RSO7b)` `number` `Number`
  - `(RSO7c)` `boolean` `Boolean`
  - `(RSO7d)` `bytes` `Binary`
  - `(RSO7e)` `json` `JsonObject | JsonArray`
  - `(RSO7f)` `objectId` `String` - a reference to an existing object by its ID
- `(RSO8)` `RestObjectGetCompactResult` is the return type of [`RestObject#get`](#RSO2) when `params.compact` is `true` or omitted. The library returns the decoded response body verbatim per [RSO2f](#RSO2f); the shape and value formats are server-defined and are not transformed by the library.
- `(RSO9)` `RestObjectGetFullResult` is the return type of [`RestObject#get`](#RSO2) when `params.compact` is `false`. It is one of:
  - `(RSO9a)` `RestLiveMap` ([RSO14](#RSO14)), returned when the response body has a `map` field per [RSO2g1](#RSO2g1)
  - `(RSO9b)` `RestLiveCounter` ([RSO15](#RSO15)), returned when the response body has a `counter` field per [RSO2g2](#RSO2g2)
  - `(RSO9c)` A decoded [`ObjectData`](../features#OD1) leaf, returned when the response is a typed leaf value per [RSO2g3](#RSO2g3). The library must return an `ObjectData` instance with:
    - `(RSO9c1)` The [`objectId`](../features#OD2a) and [`encoding`](../features#OD2b) fields unset. (If the response carried an object reference, the result would instead be a `RestLiveMap` ([RSO9a](#RSO9a)), `RestLiveCounter` ([RSO9b](#RSO9b)), or unrecognized-object fallback ([RSO9d](#RSO9d)).)
    - `(RSO9c2)` Values decoded per [OD5](../features#OD5): in particular, `bytes` holds a native `Binary` value rather than a Base64-encoded string, and any JSON-encoded payload appears as the parsed `JsonObject` or `JsonArray` rather than as a JSON-encoded string
  - `(RSO9d)` For object types unrecognized by the library, an object containing at minimum `{ objectId: String }`, with additional fields passed through unmodified per [RSF1](../features#RSF1)
- `(RSO10)` `RestObjectPublishResult` is the return type of [`RestObject#publish`](#RSO3). Its attributes are:
  - `(RSO10a)` `messageId` `String`
  - `(RSO10b)` `channel` `String`
  - `(RSO10c)` `objectIds` `Array<String>` - the identifiers of the objects affected by the operations
- `(RSO11)` `RestObjectGenerateIdResult` is the return type of [`RestObject#generateObjectId`](#RSO4). Its attributes are:
  - `(RSO11a)` `objectId` `String` - the generated object identifier
  - `(RSO11b)` `nonce` `String` - the nonce used to derive the `objectId`; the caller passes this verbatim into the matching [RSO5d](#RSO5d) or [RSO5h](#RSO5h) operation
  - `(RSO11c)` `initialValue` `String` - the JSON-encoded initial value used to derive the `objectId`; the caller passes this verbatim into the matching [RSO5d](#RSO5d) or [RSO5h](#RSO5h) operation
- `(RSO12)` `RestObjectGenerateIdBody` is the argument type for [`RestObject#generateObjectId`](#RSO4). Exactly one of the following fields must be set:
  - `(RSO12a)` `mapCreate` `RestObjectMapCreate` ([RSO5c](#RSO5c))
  - `(RSO12b)` `counterCreate` `RestObjectCounterCreate` ([RSO5g](#RSO5g))
- `(RSO13)` `RestObjectMapEntry` is the user-facing entry type used in `RestObjectMapCreate.entries` ([RSO5c2](#RSO5c2)). Its attributes are:
  - `(RSO13a)` `data` `PublishObjectData` ([RSO7](#RSO7))
- `(RSO14)` `RestLiveMap` is the full-format representation of a map object returned by [`RestObject#get`](#RSO2) with `params.compact` set to `false`. Its attributes are:
  - `(RSO14a)` `objectId` `String` - the identifier of the map object
  - `(RSO14b)` `map.semantics` `ObjectsMapSemantics` ([OMP2](../features#OMP2)) - the conflict-resolution semantics. Unrecognized server values must be preserved per [RSF1](../features#RSF1)
  - `(RSO14c)` `map.entries` `Dict<String, RestLiveMapEntry>` ([RSO16](#RSO16))
- `(RSO15)` `RestLiveCounter` is the full-format representation of a counter object returned by [`RestObject#get`](#RSO2) with `params.compact` set to `false`. Its attributes are:
  - `(RSO15a)` `objectId` `String` - the identifier of the counter object
  - `(RSO15b)` `counter.data.number` `Number` - the current value of the counter
- `(RSO16)` `RestLiveMapEntry` is the entry type used in `RestLiveMap.map.entries` ([RSO14c](#RSO14c)). Its attributes are:
  - `(RSO16a)` `data` `RestObjectGetFullResult` ([RSO9](#RSO9)) - recursively decoded per [RSO2g](#RSO2g)

### RealtimeObjects {#realtime-objects}

- `(RTO1)` `RealtimeObjects#getRoot` function:
  - `(RTO1a)` Requires the `OBJECT_SUBSCRIBE` channel mode to be granted per [RTO2](#RTO2)
  - `(RTO1b)` If the channel is in the `DETACHED` or `FAILED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
  - `(RTO1c)` If the [RTO17](#RTO17) sync state is not `SYNCED`, waits for the sync state to transition to `SYNCED`
  - `(RTO1d)` Returns the object with id `root` from the internal `ObjectsPool` as a `LiveMap`
- `(RTO11)` `RealtimeObjects#createMap` function:
  - `(RTO11a)` Expects the following arguments:
    - `(RTO11a1)` `entries` `Dict<String, Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounter | LiveMap>` (optional) - the initial entries for the new `LiveMap` object
  - `(RTO11b)` The return type is a `LiveMap`, which is returned once the required I/O has successfully completed
  - `(RTO11c)` Requires the `OBJECT_PUBLISH` channel mode to be granted per [RTO2](#RTO2)
  - `(RTO11d)` If the channel is in the `DETACHED`, `FAILED` or `SUSPENDED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
  - `(RTO11e)` If [`echoMessages`](../features#TO3h) client option is `false`, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40000, indicating that `echoMessages` must be enabled for this operation
  - `(RTO11f)` Creates an `ObjectMessage` for a `MAP_CREATE` action in the following way:
    - `(RTO11f1)` If `entries` is null or not of type `Dict`, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40003, indicating that `entries` must be a `Dict`. Note that `entries` is an optional argument, and if omitted, this error must not be thrown
    - `(RTO11f2)` If any of the keys provided in `entries` are not of type `String`, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40003, indicating that keys must be `String`
    - `(RTO11f3)` If any of the values provided in `entries` are not of an expected type, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40013, indicating that such data type is unsupported
    - `(RTO11f4)` This clause has been replaced by [RTO11f14](#RTO11f14) as of specification version 6.0.0.
      - `(RTO11f4a)` This clause has been replaced by [RTO11f14a](#RTO11f14a) as of specification version 6.0.0.
      - `(RTO11f4b)` This clause has been replaced by [RTO11f14b](#RTO11f14b) as of specification version 6.0.0.
      - `(RTO11f4c)` This clause has been replaced by [RTO11f14c](#RTO11f14c) as of specification version 6.0.0.
        - `(RTO11f4c1)` This clause has been replaced by [RTO11f14c1](#RTO11f14c1) as of specification version 6.0.0.
          - `(RTO11f4c1a)` This clause has been replaced by [RTO11f14c1a](#RTO11f14c1a) as of specification version 6.0.0.
          - `(RTO11f4c1b)` This clause has been replaced by [RTO11f14c1b](#RTO11f14c1b) as of specification version 6.0.0.
          - `(RTO11f4c1c)` This clause has been replaced by [RTO11f14c1c](#RTO11f14c1c) as of specification version 6.0.0.
          - `(RTO11f4c1d)` This clause has been replaced by [RTO11f14c1d](#RTO11f14c1d) as of specification version 6.0.0.
          - `(RTO11f4c1e)` This clause has been replaced by [RTO11f14c1e](#RTO11f14c1e) as of specification version 6.0.0.
          - `(RTO11f4c1f)` This clause has been replaced by [RTO11f14c1f](#RTO11f14c1f) as of specification version 6.0.0.
        - `(RTO11f4c2)` This clause has been replaced by [RTO11f14c2](#RTO11f14c2) as of specification version 6.0.0.
    - `(RTO11f14)` Create a `MapCreate` object with the initial value for the new `LiveMap`:
      - `(RTO11f14a)` Set `MapCreate.semantics` to `ObjectsMapSemantics.LWW`
      - `(RTO11f14b)` Set `MapCreate.entries` to an empty map if `entries` is omitted
      - `(RTO11f14c)` Otherwise, set `MapCreate.entries` based on the provided `entries`. For each key-value pair in `entries`:
        - `(RTO11f14c1)` Create an `ObjectsMapEntry` for the current value:
          - `(RTO11f14c1a)` If the value is of type `LiveCounter` or `LiveMap`, set `ObjectsMapEntry.data.objectId` to the `objectId` of that object
          - `(RTO11f14c1b)` If the value is of type `JsonArray` or `JsonObject`, set `ObjectsMapEntry.data.json` to that value
          - `(RTO11f14c1c)` If the value is of type `String`, set `ObjectsMapEntry.data.string` to that value
          - `(RTO11f14c1d)` If the value is of type `Number`, set `ObjectsMapEntry.data.number` to that value
          - `(RTO11f14c1e)` If the value is of type `Boolean`, set `ObjectsMapEntry.data.boolean` to that value
          - `(RTO11f14c1f)` If the value is of type `Binary`, set `ObjectsMapEntry.data.bytes` to that value
        - `(RTO11f14c2)` Add a new entry to `MapCreate.entries` with the current key and the created `ObjectsMapEntry` as the value
    - `(RTO11f5)` This clause has been replaced by [RTO11f15](#RTO11f15) as of specification version 6.0.0.
    - `(RTO11f15)` Create an initial value JSON string based on `MapCreate` object from [RTO11f14](#RTO11f14) as follows:
      - `(RTO11f15a)` The `MapCreate` object may contain user-provided `ObjectData` that requires encoding. Encode the `ObjectData` values using the procedure described in [OD4](../features#OD4)
      - `(RTO11f15b)` Return a JSON string representation of the encoded `MapCreate` object
    - `(RTO11f6)` Create a unique string nonce with 16+ characters; the nonce is used to ensure object ID uniqueness across clients
    - `(RTO11f7)` Get the current server time as described in [RTO16](#RTO16)
    - `(RTO11f8)` Create an `objectId` for the new `LiveMap` object as described in [RTO14](#RTO14), passing in `map` string as the `type`, the initial value JSON string from [RTO11f15](#RTO11f15), the nonce from [RTO11f6](#RTO11f6), and the server time from [RTO11f7](#RTO11f7)
    - `(RTO11f9)` Set `ObjectMessage.operation.action` to `ObjectOperationAction.MAP_CREATE`
    - `(RTO11f10)` Set `ObjectMessage.operation.objectId` to the `objectId` created in [RTO11f8](#RTO11f8)
    - `(RTO11f11)` This clause has been replaced by [RTO11f16](#RTO11f16) as of specification version 6.0.0.
    - `(RTO11f12)` This clause has been replaced by [RTO11f17](#RTO11f17) as of specification version 6.0.0.
    - `(RTO11f13)` This clause has been deleted as of specification version 6.0.0.
    - `(RTO11f16)` Set `ObjectMessage.operation.mapCreateWithObjectId.nonce` to the nonce value created in [RTO11f6](#RTO11f6)
    - `(RTO11f17)` Set `ObjectMessage.operation.mapCreateWithObjectId.initialValue` to the JSON string created in [RTO11f15](#RTO11f15)
    - `(RTO11f18)` The client library must retain the `MapCreate` object from [RTO11f14](#RTO11f14) alongside the `MapCreateWithObjectId`. It is the operation from which the `MapCreateWithObjectId` was derived, and is needed for message size calculation ([OOP4h2](../features#OOP4h2)) and local application of the operation ([RTLM23](#RTLM23)). This `MapCreate` is for local use only and must not be sent over the wire.
  - `(RTO11g)` This clause has been replaced by [RTO11i](#RTO11i)
  - `(RTO11i)` Publishes the `ObjectMessage` from [RTO11f](#RTO11f) using `RealtimeObjects#publishAndApply` ([RTO20](#RTO20)), passing the `ObjectMessage` as a single element in the array
    - `(RTO11i1)` The client library waits for the publish operation I/O to complete. On failure, an error is returned to the caller; on success, the `createMap` operation continues
  - `(RTO11h)` Returns a `LiveMap` instance:
    - `(RTO11h1)` This clause has been deleted.
    - `(RTO11h2)` If an object with the `ObjectMessage.operation.objectId` exists in the internal `ObjectsPool`, return it
    - `(RTO11h3)` Otherwise, if the object does not exist in the internal `ObjectsPool`:
      - `(RTO11h3a)` This clause has been deleted.
      - `(RTO11h3b)` This clause has been deleted.
      - `(RTO11h3c)` This clause has been deleted.
      - `(RTO11h3d)` The library should throw an `ErrorInfo` error with `statusCode` 500 and `code` 50000 (Note: this is not expected to happen since the object should have been created as part of applying the `MAP_CREATE` operation via `publishAndApply` in [RTO11i](#RTO11i))
- `(RTO12)` `RealtimeObjects#createCounter` function:
  - `(RTO12a)` Expects the following arguments:
    - `(RTO12a1)` `count` `Number` (optional) - the initial count for the new `LiveCounter` object
  - `(RTO12b)` The return type is a `LiveCounter`, which is returned once the required I/O has successfully completed
  - `(RTO12c)` Requires the `OBJECT_PUBLISH` channel mode to be granted per [RTO2](#RTO2)
  - `(RTO12d)` If the channel is in the `DETACHED`, `FAILED` or `SUSPENDED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
  - `(RTO12e)` If [`echoMessages`](../features#TO3h) client option is `false`, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40000, indicating that `echoMessages` must be enabled for this operation
  - `(RTO12f)` Creates an `ObjectMessage` for a `COUNTER_CREATE` action in the following way:
    - `(RTO12f1)` If `count` is null, not of type `Number`, or not a finite number, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40003, indicating that `count` must be a valid number. Note that `count` is an optional argument, and if omitted, this error must not be thrown
    - `(RTO12f2)` This clause has been replaced by [RTO12f12](#RTO12f12) as of specification version 6.0.0.
      - `(RTO12f2a)` This clause has been replaced by [RTO12f12a](#RTO12f12a) as of specification version 6.0.0.
      - `(RTO12f2b)` This clause has been replaced by [RTO12f12b](#RTO12f12b) as of specification version 6.0.0.
    - `(RTO12f12)` Create a `CounterCreate` object with the initial value for the new `LiveCounter`:
      - `(RTO12f12a)` Set `CounterCreate.count` to 0 if `count` is omitted
      - `(RTO12f12b)` Otherwise, set `CounterCreate.count` to the provided `count` value
    - `(RTO12f3)` This clause has been replaced by [RTO12f13](#RTO12f13) as of specification version 6.0.0.
    - `(RTO12f13)` Create an initial value JSON string by generating a JSON string representation of the `CounterCreate` object from [RTO12f12](#RTO12f12)
    - `(RTO12f4)` Create a unique string nonce with 16+ characters; the nonce is used to ensure object ID uniqueness across clients
    - `(RTO12f5)` Get the current server time as described in [RTO16](#RTO16)
    - `(RTO12f6)` Create an `objectId` for the new `LiveCounter` object as described in [RTO14](#RTO14), passing in `counter` string as the `type`, the initial value JSON string from [RTO12f13](#RTO12f13), the nonce from [RTO12f4](#RTO12f4), and the server time from [RTO12f5](#RTO12f5)
    - `(RTO12f7)` Set `ObjectMessage.operation.action` to `ObjectOperationAction.COUNTER_CREATE`
    - `(RTO12f8)` Set `ObjectMessage.operation.objectId` to the `objectId` created in [RTO12f6](#RTO12f6)
    - `(RTO12f9)` This clause has been replaced by [RTO12f14](#RTO12f14) as of specification version 6.0.0.
    - `(RTO12f10)` This clause has been replaced by [RTO12f15](#RTO12f15) as of specification version 6.0.0.
    - `(RTO12f11)` This clause has been deleted as of specification version 6.0.0.

\* `(RTO12f14)` Set `ObjectMessage.operation.counterCreateWithObjectId.nonce` to the nonce value created in [RTO12f4](#RTO12f4)

\* `(RTO12f15)` Set `ObjectMessage.operation.counterCreateWithObjectId.initialValue` to the JSON string created in [RTO12f13](#RTO12f13)

\* `(RTO12f16)` The client library must retain the `CounterCreate` object from [RTO12f12](#RTO12f12) alongside the `CounterCreateWithObjectId`. It is the operation from which the `CounterCreateWithObjectId` was derived, and is needed for message size calculation ([OOP4k2](../features#OOP4k2)) and local application of the operation ([RTLC16](#RTLC16)). This `CounterCreate` is for local use only and must not be sent over the wire.

`(RTO12g)` This clause has been replaced by [RTO12i](#RTO12i)

`(RTO12i)` Publishes the `ObjectMessage` from [RTO12f](#RTO12f) using `RealtimeObjects#publishAndApply` ([RTO20](#RTO20)), passing the `ObjectMessage` as a single element in the array

\* `(RTO12i1)` The client library waits for the publish operation I/O to complete. On failure, an error is returned to the caller; on success, the `createCounter` operation continues

`(RTO12h)` Returns a `LiveCounter` instance:

\* `(RTO12h1)` This clause has been deleted.

\* `(RTO12h2)` If an object with the `ObjectMessage.operation.objectId` exists in the internal `ObjectsPool`, return it

\* `(RTO12h3)` Otherwise, if the object does not exist in the internal `ObjectsPool`:

`(RTO12h3a)` This clause has been deleted.

`(RTO12h3b)` This clause has been deleted.

`(RTO12h3c)` This clause has been deleted.

`(RTO12h3d)` The library should throw an `ErrorInfo` error with `statusCode` 500 and `code` 50000 (Note: this is not expected to happen since the object should have been created as part of applying the `COUNTER_CREATE` operation via `publishAndApply` in [RTO12i](#RTO12i))

- `(RTO2)` Certain object operations may require a specific channel mode to be set on a channel in order to be performed. If a specific channel mode is required by an operation, then:
  - `(RTO2a)` If the channel is in the `ATTACHED` state, the presence of the required channel mode is checked against the set of channel modes granted by the server per [RTL4m](../features#RTL4m) :
    - `(RTO2a1)` If the channel mode is in the set, the operation is allowed
    - `(RTO2a2)` If the channel mode is missing, unless otherwise specified by the operation, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40024, indicating that the operation cannot be performed without the required channel mode
  - `(RTO2b)` Otherwise, a best-effort attempt is made, and the channel mode is checked against the set of channel modes requested by the user per [TB2d](../features#TB2d) :
    - `(RTO2b1)` If the channel mode is in the set, the operation is allowed
    - `(RTO2b2)` If the channel mode is missing, unless otherwise specified by the operation, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40024, indicating that the operation cannot be performed without the required channel mode
- `(RTO3)` An internal `ObjectsPool` should be used to maintain the list of objects present on a channel
  - `(RTO3a)` `ObjectsPool` is a `Dict<String, LiveObject>` - a map of `LiveObject`s keyed by [`objectId`](../features#OST2a) string
  - `(RTO3b)` It must always contain a `LiveMap` object with id `root`
    - `(RTO3b1)` Upon initialization of the `ObjectsPool`, create a new `LiveMap` (per [RTLM4](#RTLM4)) with `objectId` set to `root` and add it to the `ObjectsPool`
- `(RTO4)` When a channel `ATTACHED` `ProtocolMessage` is received, the client library must perform the following actions in order. The `ProtocolMessage` may contain a `HAS_OBJECTS` bit flag (see [TR3](../features#TR3)); note that some of the following actions are conditional on this flag.
  - `(RTO4c)` The [RTO17](#RTO17) sync state must transition to `SYNCING` if not already `SYNCING`
  - `(RTO4d)` The `bufferedObjectOperations` list must be cleared without applying any buffered operations
  - `(RTO4a)` If the `HAS_OBJECTS` flag is 1, the server will shortly perform an `OBJECT_SYNC` sequence as described in [RTO5](#RTO5). Note that this does not imply that objects are definitely present on the channel, only that there may be; the `OBJECT_SYNC` message may be empty
  - `(RTO4b)` If the `HAS_OBJECTS` flag is 0 or there is no `flags` field, the sync sequence must be considered complete immediately, and the client library must perform the following actions in order:
    - `(RTO4b1)` All objects except the one with id `root` must be removed from the internal `ObjectsPool`
    - `(RTO4b2)` The data for the `LiveMap` with id `root` must be cleared by setting it to a zero-value per [RTLM4](#RTLM4). Note that the client SDK must not create a new `LiveMap` instance with id `root`; it must only clear the internal data of the existing `LiveMap` with id `root`
      - `(RTO4b2a)` Emit a `LiveMapUpdate` object for the `LiveMap` with ID `root`, with `LiveMapUpdate.update` consisting of entries for the keys that were removed, each set to `removed`
    - `(RTO4b3)` The `SyncObjectsPool` must be cleared
    - `(RTO4b5)` This clause has been replaced by [RTO4d](#RTO4d)
    - `(RTO4b4)` Perform the actions for objects sync completion as described in [RTO5c](#RTO5c)
- `(RTO5)` The realtime system reserves the right to initiate an objects sync of the objects on a channel at any point once a channel is attached. A server initiated objects sync provides Ably with a means to send a complete list of objects present on the channel at any point
  - `(RTO5d)` If an `OBJECT_SYNC` `ProtocolMessage` is received and [`ObjectMessage.object`](../features#TR4r) is null or omitted, the client library should skip processing that `ProtocolMessage`
  - `(RTO5e)` When an `OBJECT_SYNC` `ProtocolMessage` is received with a `channel` attribute matching the channel name, the [RTO17](#RTO17) sync state must transition to `SYNCING` if not already `SYNCING`. This must occur before performing any [RTO5c](#RTO5c) sync completion actions.
  - `(RTO5a)` When an `OBJECT_SYNC` `ProtocolMessage` is received with a `channel` attribute matching the channel name, the client library must parse the `channelSerial` attribute:
    - `(RTO5a1)` The `channelSerial` is used as the sync cursor and is a two-part identifier: `<sequence id>:<cursor value>`
    - `(RTO5a2)` If a new sequence id is sent from Ably, the client library must treat it as the start of a new objects sync sequence, and any previous in-flight sync must be discarded:
      - `(RTO5a2a)` The `SyncObjectsPool` must be cleared
      - `(RTO5a2b)` This clause has been replaced by [RTO4d](#RTO4d)
    - `(RTO5a3)` If the sequence id matches the previously received sequence id, the client library should continue the sync process
    - `(RTO5a4)` The objects sync sequence for that sequence identifier is considered complete once the cursor is empty; that is when the `channelSerial` looks like `<sequence id>:`
    - `(RTO5a5)` An `OBJECT_SYNC` may also be sent with no `channelSerial` attribute. In this case, the sync data is entirely contained within the `ProtocolMessage`
  - `(RTO5b)` This clause has been replaced by [RTO5f](#RTO5f)
  - `(RTO5f)` During the sync sequence, `ObjectMessages` from incoming `OBJECT_SYNC` `ProtocolMessages` must be temporarily stored in the internal `SyncObjectsPool`, keyed by `ObjectMessage.object.objectId`. The `SyncObjectsPool` stores one `ObjectMessage` per `objectId`, which may represent merged state from multiple incoming messages. For each `ObjectMessage` in the incoming `OBJECT_SYNC` `ProtocolMessage`, let `ObjectState` be `ObjectMessage.object`:
    - `(RTO5f3)` If neither `ObjectState.map` nor `ObjectState.counter` is present on the incoming message, log a warning that a state message with an unsupported object type was received and skip the incoming message
    - `(RTO5f1)` If an entry with the given `ObjectState.objectId` does not yet exist in the `SyncObjectsPool`, store the `ObjectMessage`
    - `(RTO5f2)` If an entry with the given `ObjectState.objectId` already exists in the `SyncObjectsPool`, this indicates a partial object state - the server has split a large object across multiple `OBJECT_SYNC` `ProtocolMessages`. The client must merge the partial state into the existing entry based on the object type:
      - `(RTO5f2a)` If `ObjectState.map` is present on the incoming message, merge the map state:
        - `(RTO5f2a1)` If the incoming `ObjectState.tombstone` is `true`, replace the existing entry in the `SyncObjectsPool` with the incoming `ObjectMessage` entirely
        - `(RTO5f2a2)` Otherwise, merge `ObjectState.map.entries` from the incoming message into the existing `ObjectState.map.entries`. During partial sync, no two messages for the same map object contain the same map key, so no conflict resolution is needed
      - `(RTO5f2b)` If `ObjectState.counter` is present on the incoming message, log an error indicating that an unexpected partial object state for a counter was received, and skip the incoming message
  - `(RTO5c)` When the objects sync has completed, the client library must perform the following actions in order:
    - `(RTO5c1)` For each `ObjectMessage` in the `SyncObjectsPool`, let `ObjectState` be `ObjectMessage.object`:
      - `(RTO5c1a)` If an object with `ObjectState.objectId` exists in the internal `ObjectsPool`:
        - `(RTO5c1a1)` Replace the internal data for the object as described in [RTLC6](#RTLC6) or [RTLM6](#RTLM6) depending on the object type, passing in current `ObjectState`
        - `(RTO5c1a2)` Store the `LiveObjectUpdate` object returned by the operation, along with a reference to the updated object
      - `(RTO5c1b)` If an object with `ObjectState.objectId` does not exist in the internal `ObjectsPool`:
        - `(RTO5c1b1)` Create a new `LiveObject` using the data from `ObjectState` and add it to the internal `ObjectsPool`:
          - `(RTO5c1b1a)` If `ObjectState.counter` is present, create a zero-value `LiveCounter` (per [RTLC4](#RTLC4)), set its private `objectId` equal to `ObjectState.objectId` and replace its internal data using the current `ObjectState` per [RTLC6](#RTLC6)
          - `(RTO5c1b1b)` If `ObjectState.map` is present, create a zero-value `LiveMap` (per [RTLM4](#RTLM4)), set its private `objectId` equal to `ObjectState.objectId`, set its private `semantics` equal to `ObjectState.map.semantics` and replace its internal data using the current `ObjectState` per [RTLM6](#RTLM6)
          - `(RTO5c1b1c)` This clause has been deleted (redundant to [RTO5f3](#RTO5f3)).
    - `(RTO5c2)` Remove any objects from the internal `ObjectsPool` for which `objectId`s were not received during the sync sequence
      - `(RTO5c2a)` The object with ID `root` must not be removed from `ObjectsPool`, as per [RTO3b](#RTO3b)
    - `(RTO5c7)` For each previously existing object that was updated as a result of [RTO5c1a](#RTO5c1a), emit the corresponding stored `LiveObjectUpdate` object from [RTO5c1a2](#RTO5c1a2)
    - `(RTO5c6)` `ObjectMessages` stored in the `bufferedObjectOperations` list are applied as described in [RTO9](#RTO9), passing `source` as `CHANNEL`
    - `(RTO5c3)` Clear any stored sync sequence identifiers and cursor values
    - `(RTO5c4)` The `SyncObjectsPool` must be cleared
    - `(RTO5c5)` The `bufferedObjectOperations` list must be cleared
    - `(RTO5c9)` The `appliedOnAckSerials` set ([RTO7b](#RTO7b)) must be cleared. A state sync causes the channel's LiveObjects data to be replaced, so after a state sync the `appliedOnAckSerials` no longer accurately describes which operations have been applied to the channel's LiveObjects data
    - `(RTO5c8)` The [RTO17](#RTO17) sync state must transition to `SYNCED`
- `(RTO6)` Certain object operations may require creating a zero-value object if one does not already exist in the internal `ObjectsPool` for the given `objectId`. This can be done as follows:
  - `(RTO6a)` If an object with `objectId` exists in `ObjectsPool`, do not create a new object
  - `(RTO6b)` The expected type of the object can be inferred from the provided `objectId`:
    - `(RTO6b1)` Split the `objectId` (formatted as `[type]:[hash]&#64;[timestamp]`, see [RTO14c](#RTO14c)) on the separator `:` and parse the first part as the type string
    - `(RTO6b2)` If the parsed type is `map`, create a zero-value `LiveMap` per [RTLM4](#RTLM4) in the `ObjectsPool`
    - `(RTO6b3)` If the parsed type is `counter`, create a zero-value `LiveCounter` per [RTLC4](#RTLC4) in the `ObjectsPool`
- `(RTO7)` The client library may receive `OBJECT` `ProtocolMessages` in realtime over the channel concurrently with `OBJECT_SYNC` `ProtocolMessages` during the object sync sequence ([RTO5](#RTO5)). Some of the incoming `OBJECT` messages may have already been applied to the objects described in the sync sequence, while others may not. Therefore, the client must buffer `OBJECT` messages during the sync sequence so that it can determine which of them should be applied to the objects once the sync is complete. See [RTO8](#RTO8)
  - `(RTO7a)` The `RealtimeObjects` instance has an internal attribute `bufferedObjectOperations`, which is an array of `ObjectMessage` instances. This is used to store the buffered `ObjectMessages`, as described in [RTO8a](#RTO8a).
    - `(RTO7a1)` This array is empty upon `RealtimeObjects` initialization
  - `(RTO7b)` The `RealtimeObjects` instance has an internal attribute `appliedOnAckSerials`, which is a set of strings. This is used to store the serial values of operations that have been applied upon receipt of an `ACK` but for which the echo has not yet been received.
    - `(RTO7b1)` This set is empty upon `RealtimeObjects` initialization
- `(RTO8)` When the library receives a `ProtocolMessage` with an action of `OBJECT`, each member of the `ProtocolMessage.state` array (decoded into `ObjectMessage` objects) is passed to the `RealtimeObjects` instance per [RTL1](../features#RTL1). Each `ObjectMessage` from `OBJECT` `ProtocolMessage` (also referred to as an `OBJECT` message) describes an operation to be applied to an object on a channel and must be handled as follows:
  - `(RTO8a)` If the [RTO17](#RTO17) sync state is not `SYNCED`, add the `ObjectMessages` to the internal `bufferedObjectOperations` array
  - `(RTO8b)` Otherwise, apply the `ObjectMessages` as described in [RTO9](#RTO9), passing `source` as `CHANNEL`
- `(RTO9)` `OBJECT` messages can be applied to `RealtimeObjects` in the following way:
  - `(RTO9b)` Expects the following arguments:
    - `(RTO9b1)` `ObjectMessage[]` - the list of `ObjectMessages` to apply
    - `(RTO9b2)` `source` `ObjectsOperationSource` - the source of the operation (see [RTO22](#RTO22))
  - `(RTO9a)` For each `ObjectMessage` in the provided list:
    - `(RTO9a1)` If `ObjectMessage.operation` is null or omitted, log a warning indicating that an unsupported object operation message has been received, and discard the current `ObjectMessage` without taking any action
    - `(RTO9a3)` If the `appliedOnAckSerials` set ([RTO7b](#RTO7b)) contains `ObjectMessage.serial`, log a debug or trace message indicating that the operation has already been applied upon receipt of the ACK, remove this value from the set, and discard the current `ObjectMessage` without taking any further action
    - `(RTO9a2)` The `ObjectMessage.operation.action` field (see [`ObjectOperationAction`](../features#OOP2)) determines the type of operation to apply:
      - `(RTO9a2a)` If `ObjectMessage.operation.action` is one of the following: `MAP_CREATE`, `MAP_SET`, `MAP_REMOVE`, `COUNTER_CREATE`, `COUNTER_INC`, `OBJECT_DELETE`, or `MAP_CLEAR`, then:
        - `(RTO9a2a1)` If it does not already exist, create a zero-value `LiveObject` in the internal `ObjectsPool` per [RTO6](#RTO6) using the `objectId` from `ObjectMessage.operation.objectId`
        - `(RTO9a2a2)` Get the `LiveObject` instance from the internal `ObjectsPool` using the `objectId` from `ObjectMessage.operation.objectId`
        - `(RTO9a2a3)` Apply the `ObjectMessage.operation` to the `LiveObject`; see [RTLC7](#RTLC7), [RTLM15](#RTLM15), passing the `source` parameter. The operation returns a boolean indicating whether the operation was successfully applied
        - `(RTO9a2a4)` If `source` is `LOCAL` and [RTO9a2a3](#RTO9a2a3) returned `true`, add `ObjectMessage.serial` to the internal `appliedOnAckSerials` set ([RTO7b](#RTO7b))
      - `(RTO9a2b)` Otherwise, log a warning that an object operation message with an unsupported action has been received, and discard the current `ObjectMessage` without taking any action
- `(RTO10)` The client library must have a process in place to regularly check for objects and map entries that have been tombstoned for a period of time, and release their resources so they can be garbage collected. Tombstoned objects and map entries are retained in memory for a sufficient grace period (at least \>2 minutes) to ensure that no late-arriving operation is mistakenly applied to an object or map entry the client has already "forgotten" about.
  - `(RTO10a)` The check should occur at regular intervals, for example, every 5 minutes
  - `(RTO10b)` The grace period for releasing resources for tombstoned objects and map entries is determined as follows:
    - `(RTO10b1)` It is equal to [`ConnectionDetails.objectsGCGracePeriod`](../features#CD2i) received in the `CONNECTED` `ProtocolMessage`
    - `(RTO10b2)` The grace period value is updated to match the new `ConnectionDetails.objectsGCGracePeriod` value whenever a new `CONNECTED` `ProtocolMessage` is received per [RTN24](../features#RTN24)
    - `(RTO10b3)` A default value of 86,400,000 milliseconds (24 hours) is used if `ConnectionDetails.objectsGCGracePeriod` is not provided
  - `(RTO10c)` On each check interval:
    - `(RTO10c1)` For each `LiveObject` in the `ObjectsPool`:
      - `(RTO10c1a)` Check if the `LiveObject` needs to release any resources, see [RTLM19](#RTLM19)
      - `(RTO10c1b)` If `LiveObject.isTombstone` is `true`, and the difference between the current time and `LiveObject.tombstonedAt` is greater than or equal to the [grace period](#RTO10b), remove the object from the `ObjectsPool` and release resources for the corresponding object entity to allow it to be garbage collected
- `(RTO13)` This clause has been deleted (redundant to [RTO11f15](#RTO11f15) and [RTO12f13](#RTO12f13)) as of specification version 6.0.0.
  - `(RTO13a)` This clause has been deleted as of specification version 6.0.0.
    - `(RTO13a1)` This clause has been deleted as of specification version 6.0.0.
  - `(RTO13b)` This clause has been deleted as of specification version 6.0.0.
  - `(RTO13c)` This clause has been deleted as of specification version 6.0.0.
- `(RTO14)` An Object ID can be created in the client library for a new `LiveObject` instance in the following way:
  - `(RTO14a)` Expects the following arguments:
    - `(RTO14a1)` `type` `String` - the type of object this Object ID is generated for. Must be one of `map` or `counter`
    - `(RTO14a2)` `initialValue` `String` - a JSON string representation of the initial value for the object. This protects against Object IDs being reused for create operations with differing content
    - `(RTO14a3)` `nonce` `String` - a random string to ensure uniqueness across clients
    - `(RTO14a4)` `timestamp` `Time` - the current server time. This protects against Object IDs being reused across time
  - `(RTO14b)` Generate a `hash` string for the Object ID:
    - `(RTO14b1)` Generate a SHA-256 digest from a UTF-8 encoded string in the format `[initialValue]:[nonce]`
    - `(RTO14b2)` Base64URL-encode the generated digest. This must follow the URL-safe Base64 encoding as described in [RFC 4648 s.5](https://datatracker.ietf.org/doc/html/rfc4648#section-5), not standard Base64 encoding
  - `(RTO14c)` Return an Object ID in the format `[type]:[hash]&#64;[timestamp]`, where `timestamp` is represented as milliseconds since the epoch
- `(RTO15)` Internal `RealtimeObjects#publish` function:
  - `(RTO15a)` Expects the following arguments:
    - `(RTO15a1)` `ObjectMessage[]` - an array of `ObjectMessage` to be published on a channel
  - `(RTO15b)` Must adhere to the same connection and channel state conditions as message publishing, see [RTL6c](../features#RTL6c)
  - `(RTO15c)` Must encode the provided `ObjectMessages` as described in [OM4](../features#OM4)
  - `(RTO15d)` Should validate that the total size of the encoded `ObjectMessages`, calculated as per [OM3](../features#OM3), does not exceed [`maxMessageSize`](#TO3l8). If it does, the client library must reject the publish and throw an `ErrorInfo` error with `statusCode` 400 and `code` 40009
  - `(RTO15e)` Must construct the following `ProtocolMessage`:
    - `(RTO15e1)` Set `ProtocolMessage.action` to `OBJECT`
    - `(RTO15e2)` Set `ProtocolMessage.channel` to the channel name
    - `(RTO15e3)` Set `ProtocolMessage.state` to the encoded `ObjectMessages`
  - `(RTO15f)` Must send the `ProtocolMessage` to the connection
  - `(RTO15g)` Must indicate success or failure of the publish (once `ACKed` or `NACKed`) in the same way as `RealtimeChannel#publish`
  - `(RTO15h)` Upon success, must return the `PublishResult` from the first element of the `ACK`'s `res` array ([TR4s](../features#TR4s)), in the same way as `RealtimeChannel#publish` ([RTL6j](../features#RTL6j))
- `(RTO20)` Internal `RealtimeObjects#publishAndApply` function:
  - `(RTO20a)` Expects the following arguments:
    - `(RTO20a1)` `ObjectMessage[]` - an array of `ObjectMessage` to be published on a channel
  - `(RTO20b)` Calls `RealtimeObjects#publish` ([RTO15](#RTO15)) with the provided `ObjectMessage[]` and awaits the `PublishResult`. If `publish` fails, rethrow the error and do not proceed
  - `(RTO20c)` If the information needed to apply the operations locally on ACK is not available, this is unexpected incorrect behaviour from the server. Log an error indicating the reason the operations will not be applied locally, and do not proceed with the remaining steps. (The operations have already been published successfully, but cannot be applied locally on ACK; they will instead be applied when the echoed messages are received from the server.) The required information is:
    - `(RTO20c1)` A `siteCode` from [CD2j](../features#CD2j) `ConnectionDetails.siteCode`
    - `(RTO20c2)` A `PublishResult.serials` array with the same length as the provided `ObjectMessage[]` argument
  - `(RTO20d)` Create a list of synthetic inbound `ObjectMessages` as follows. For each `ObjectMessage` in the provided `ObjectMessage[]` argument, paired with the corresponding serial from `PublishResult.serials` at the same index:
    - `(RTO20d1)` If the serial from the `PublishResult` is `null` (indicating that the operation was conflated --- not currently an expected behaviour but we wish to handle it gracefully if the server introduces this behaviour in the future), log a debug or trace message indicating that the operation will not be applied locally because it was not assigned a `serial`, and skip this `ObjectMessage` without adding it to the list
    - `(RTO20d2)` Create a synthetic inbound `ObjectMessage` by copying the outbound `ObjectMessage` and setting:
      - `(RTO20d2a)` `ObjectMessage.serial` to the serial from the `PublishResult`
      - `(RTO20d2b)` `ObjectMessage.siteCode` to the [CD2j](../features#CD2j) `ConnectionDetails.siteCode`
    - `(RTO20d3)` Add the synthetic `ObjectMessage` to the list
  - `(RTO20e)` If the [RTO17](#RTO17) sync state is not `SYNCED`, wait for the sync state to transition to `SYNCED`
    - `(RTO20e1)` If the channel enters the `DETACHED`, `SUSPENDED`, or `FAILED` state while waiting for the sync state to transition to `SYNCED`, the `publishAndApply` operation must fail with an `ErrorInfo` error with `code` `92008`, a `statusCode` of `400`, a `message` stating that the operation could not be applied locally due to the channel entering the respective state whilst waiting for objects sync to complete, and `cause` set to the `RealtimeChannel.errorReason` if it is set
  - `(RTO20f)` Apply the synthetic `ObjectMessages` as described in [RTO9](#RTO9), passing `source` as `LOCAL`
- `(RTO16)` Server time can be retrieved using [`RestClient#time`](../features#RSC16)
  - `(RTO16a)` The server time offset can be persisted by the client library and used to calculate the server time without making a request, in a similar way to how it is described in [RSA10k](../features#RSA10k). The persisted offset from either operation can be used interchangeably
- `(RTO17)` The `RealtimeObjects` instance must maintain an internal sync state to track the status of synchronising the local objects data with the Ably service.
  - `(RTO17a)` The sync state has type `ObjectsSyncState`, which is an enum with the following cases (note that their descriptions are purely informative; the rules for state transitions are described elsewhere in this specification):
    - `(RTO17a1)` `INITIALIZED` - the initial state when `RealtimeObjects` is created
    - `(RTO17a2)` `SYNCING` - in this state, the local copy of objects on the channel is currently being synchronised with the Ably service
    - `(RTO17a3)` `SYNCED` - in this state, the local copy of objects on the channel has been synchronised with the Ably service
  - `(RTO17b)` When the sync state transitions, an event with the `ObjectsEvent` value matching the new state must be emitted to any listeners registered via `RealtimeObjects#on` ([RTO18](#RTO18)).
- `(RTO18)` `RealtimeObjects#on` function - registers a listener for sync state events
  - `(RTO18a)` Expects the following arguments:
    - `(RTO18a1)` `event` - the event name to listen for, of type `ObjectsEvent` (see [RTO18b](#RTO18b))
    - `(RTO18a2)` `callback` - the event listener function to be called when the event is emitted
  - `(RTO18b)` `ObjectsEvent` is an enum with the following cases:
    - `(RTO18b1)` `SYNCING`: Indicates that the [RTO17](#RTO17) sync state has transitioned to `SYNCING`
    - `(RTO18b2)` `SYNCED`: Indicates that the [RTO17](#RTO17) sync state has transitioned to `SYNCED`
  - `(RTO18c)` Registers the provided listener for the specified event
  - `(RTO18d)` If `on` is called more than once with the same listener and event, the listener is added multiple times to the listener registry. As such, if the same listener is registered twice and an event is emitted once, the listener will be invoked twice
  - `(RTO18e)` When an event is emitted, all registered listeners for that event must be called with no arguments
  - `(RTO18f)` The client library may return a subscription object (or the idiomatic equivalent for the language) as a result of this operation:
    - `(RTO18f1)` The subscription object includes an `off` function
    - `(RTO18f2)` Calling `off` deregisters the listener previously registered by the user via the corresponding `on` call
- `(RTO19)` `RealtimeObjects#off` function - deregisters an event listener previously registered via `RealtimeObjects#on` ([RTO18](#RTO18))
- `(RTO22)` `ObjectsOperationSource` is an internal enum describing the source of an operation being applied:
  - `(RTO22a)` `LOCAL` - an operation that originated locally, being applied upon receipt of the `ACK` from Realtime
  - `(RTO22b)` `CHANNEL` - an operation received over a Realtime channel

### LiveObject

- `(RTLO1)` The `LiveObject` represents the common interface and includes shared functionality for concrete object types
- `(RTLO2)` The client library may choose to implement `LiveObject` as an abstract class
- `(RTLO3)` `LiveObject` properties:
  - `(RTLO3a)` protected `objectId` string - an Object ID for this object
    - `(RTLO3a1)` Must be provided and set in the constructor
  - `(RTLO3b)` protected `siteTimeserials` `Dict<String, String>` - a map of [serials](../features#OM2h) keyed by [siteCode](../features#OM2i), representing the last operations applied to this object
    - `(RTLO3b1)` Set to an empty map when the `LiveObject` is initialized, so that any future operation can be applied to this object
  - `(RTLO3c)` protected `createOperationIsMerged` boolean - a flag indicating whether the corresponding `MAP_CREATE` or `COUNTER_CREATE` operation has been applied to this `LiveObject` instance
    - `(RTLO3c1)` Set to `false` when the `LiveObject` is initialized
  - `(RTLO3d)` protected `isTombstone` boolean - a flag indicating whether this object has been tombstoned, i.e. marked for deletion from the objects pool
    - `(RTLO3d1)` Set to `false` when the `LiveObject` is initialized
  - `(RTLO3e)` protected `tombstonedAt` (optional) Time - a timestamp indicating when this object was tombstoned. This property is nullable, and specification points that manipulate this value maintain the invariant that it is non-null if and only if `isTombstone` is `true`
    - `(RTLO3e1)` Set to undefined/null when the `LiveObject` is initialized
- `(RTLO4)` `LiveObject` methods:
  - `(RTLO4b)` public `subscribe` - subscribes a user to data updates on this `LiveObject` instance
    - `(RTLO4b1)` Requires the `OBJECT_SUBSCRIBE` channel mode to be granted per [RTO2](#RTO2)
    - `(RTLO4b2)` If the channel is in the `DETACHED` or `FAILED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
    - `(RTLO4b3)` A user may provide a listener to subscribe to data updates on this `LiveObject` instance
    - `(RTLO4b4)` An update to `LiveObject` data is communicated by internally emitting a `LiveObjectUpdate` object for this `LiveObject`, or in any other platform-appropriate manner:
      - `(RTLO4b4a)` `LiveObjectUpdate.update` contains the specific information about what was changed on the object. The exact type depends on the object type
      - `(RTLO4b4b)` The `LiveObjectUpdate.noop` internal property can be used to indicate that the update was a no-op
      - `(RTLO4b4c)` When a `LiveObjectUpdate` is emitted:
        - `(RTLO4b4c1)` If `LiveObjectUpdate` is indicated to be a no-op, do nothing
        - `(RTLO4b4c2)` Otherwise, the registered listener is called with the `LiveObjectUpdate` object
    - `(RTLO4b5)` The client library may return a subscription object (or the idiomatic equivalent for the language) as a result of this operation:
      - `(RTLO4b5a)` The subscription object includes an `unsubscribe` function
      - `(RTLO4b5b)` Calling `unsubscribe` deregisters the listener previously registered by the user via the corresponding `subscribe` call
    - `(RTLO4b6)` This operation must not have any side effects on `RealtimeObjects`, the underlying channel, or their status
  - `(RTLO4c)` public `unsubscribe` - unsubscribes a previously registered listener
    - `(RTLO4c1)` This operation does not require any specific channel modes to be granted, nor does it require the channel to be in a specific state
    - `(RTLO4c2)` A user may provide a listener they wish to deregister from receiving data updates for this `LiveObject`
    - `(RTLO4c3)` Once deregistered, subsequent data updates for this `LiveObject` must not result in the listener being called
    - `(RTLO4c4)` This operation must not have any side effects on `RealtimeObjects`, the underlying channel, or their status
  - `(RTLO4a)` protected `canApplyOperation` - a convenience method used to determine whether the `ObjectMessage.operation` should be applied to this object based on a serial value
    - `(RTLO4a1)` Expects the following arguments:
      - `(RTLO4a1a)` `ObjectMessage`
    - `(RTLO4a2)` Returns a boolean indicating whether the operation should be applied to this object
    - `(RTLO4a3)` Both `ObjectMessage.serial` and `ObjectMessage.siteCode` must be non-empty strings. Otherwise, log a warning that the object operation message has invalid serial values. The client library must not apply this operation to the object
    - `(RTLO4a4)` Get the `siteSerial` value stored for this `LiveObject` in the `siteTimeserials` map using the key `ObjectMessage.siteCode`
    - `(RTLO4a5)` If the `siteSerial` for this `LiveObject` is null or an empty string, return true
    - `(RTLO4a6)` If the `siteSerial` for this `LiveObject` is not an empty string, return true if `ObjectMessage.serial` is greater than `siteSerial` when compared lexicographically
  - `(RTLO4e)` protected `tombstone` - a convenience method used to tombstone this `LiveObject`. The realtime system reserves the right to tombstone an object (i.e. mark it for deletion from the objects pool) by publishing an `OBJECT_DELETE` operation at any time if the object is orphaned (not a descendant of the root object) or remains uninitialized (no `*_CREATE` operation has been received) for an extended period. Only the realtime system may publish an `OBJECT_DELETE` operation; clients must never send it. This method describes the steps the client library must take when it needs to tombstone an object locally. Eventually, tombstoned objects will be garbage collected following the procedure described in [RTO10](#RTO10)
    - `(RTLO4e1)` Expects the following arguments:
      - `(RTLO4e1a)` `ObjectMessage`
    - `(RTLO4e2)` Set `LiveObject.isTombstone` to `true`
    - `(RTLO4e3)` Set `LiveObject.tombstonedAt` to the value calculated per [RTLO6](#RTLO6), using `ObjectMessage.serialTimestamp`
      - `(RTLO4e3a)` This clause has been replaced by [RTLO6a](#RTLO6a)
      - `(RTLO4e3b)` This clause has been replaced by [RTLO6b](#RTLO6b)
        - `(RTLO4e3b1)` This clause has been replaced by [RTLO6b1](#RTLO6b1)
    - `(RTLO4e4)` Set the data for the `LiveObject` to a zero-value, as described in [RTLC4](#RTLC4) or [RTLM4](#RTLM4) depending on the object type
- `(RTLO5)` An `OBJECT_DELETE` operation can be applied to a `LiveObject` in the following way:
  - `(RTLO5a)` Expects the following arguments:
    - `(RTLO5a1)` `ObjectMessage`
  - `(RTLO5b)` Tombstone the current `LiveObject` using [`LiveObject.tombstone`](#RTLO4e), passing in the `ObjectMessage`
- `(RTLO6)` A `tombstonedAt` value can be calculated from a provided `serialTimestamp` as follows:
  - `(RTLO6a)` It is equal to `serialTimestamp` if it exists
  - `(RTLO6b)` Otherwise, it is equal to the current time using the local clock
    - `(RTLO6b1)` Log a debug or trace message indicating that `serialTimestamp` was not provided and the local clock is being used instead for the tombstone timestamp

### LiveCounter

- `(RTLC1)` The `LiveCounter` extends `LiveObject`
- `(RTLC2)` Represents the counter object type for Object IDs of type `counter`
- `(RTLC3)` Holds a 64-bit floating-point number as a private `data`
- `(RTLC4)` The zero-value `LiveCounter` is a `LiveCounter` with `data` set to 0
- `(RTLC11)` Data updates for a `LiveCounter` are emitted using the `LiveCounterUpdate` object:
  - `(RTLC11a)` `LiveCounterUpdate` extends `LiveObjectUpdate`
  - `(RTLC11b)` `LiveCounterUpdate.update` has the following properties:
    - `(RTLC11b1)` `amount` number - the value by which the counter was incremented or decremented
- `(RTLC5)` `LiveCounter#value` function:
  - `(RTLC5a)` Requires the `OBJECT_SUBSCRIBE` channel mode to be granted per [RTO2](#RTO2)
  - `(RTLC5b)` If the channel is in the `DETACHED` or `FAILED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
  - `(RTLC5c)` Returns the current `data` value
- `(RTLC12)` `LiveCounter#increment` function:
  - `(RTLC12a)` Expects the following arguments:
    - `(RTLC12a1)` `amount` `Number` - the amount by which to increment the counter value
  - `(RTLC12b)` Requires the `OBJECT_PUBLISH` channel mode to be granted per [RTO2](#RTO2)
  - `(RTLC12c)` If the channel is in the `DETACHED`, `FAILED` or `SUSPENDED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
  - `(RTLC12d)` If [`echoMessages`](../features#TO3h) client option is `false`, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40000, indicating that `echoMessages` must be enabled for this operation
  - `(RTLC12e)` Creates an `ObjectMessage` for a `COUNTER_INC` action in the following way:
    - `(RTLC12e1)` If `amount` is null, not of type `Number`, not a finite number, or omitted, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40003, indicating that `amount` must be a valid number
    - `(RTLC12e2)` Set `ObjectMessage.operation.action` to `ObjectOperationAction.COUNTER_INC`
    - `(RTLC12e3)` Set `ObjectMessage.operation.objectId` to the Object ID of this `LiveCounter`
    - `(RTLC12e4)` This clause has been replaced by [RTLC12e5](#RTLC12e5) as of specification version 6.0.0.
    - `(RTLC12e5)` Set `ObjectMessage.operation.counterInc.number` to the provided `amount` value
  - `(RTLC12f)` This clause has been replaced by [RTLC12g](#RTLC12g)
  - `(RTLC12g)` Publishes the `ObjectMessage` from [RTLC12e](#RTLC12e) using `RealtimeObjects#publishAndApply` ([RTO20](#RTO20)), passing the `ObjectMessage` as a single element in the array
- `(RTLC13)` `LiveCounter#decrement` function:
  - `(RTLC13a)` Expects the following arguments:
    - `(RTLC13a1)` `amount` `Number` - the amount by which to decrement the counter value
  - `(RTLC13b)` This is an alias for calling [`LiveCounter#increment`](#RTLC12) with a negative `amount` and must be implemented with the same behavior
  - `(RTLC13c)` If the client library chooses to delegate to `LiveCounter#increment` with a negated `amount`, then in languages where negating a non-number may result in implicit type coercion, the `amount` argument must first be validated as described in [RTLC12e1](#RTLC12e1) before proceeding
- `(RTLC6)` `LiveCounter`'s internal `data` can be replaced with the provided `ObjectState` in the following way:
  - `(RTLC6a)` Replace the private `siteTimeserials` of the `LiveCounter` with the value from `ObjectState.siteTimeserials`
  - `(RTLC6e)` If `LiveCounter.isTombstone` is `true`, finish processing the `ObjectState`
    - `(RTLC6e1)` Return a `LiveCounterUpdate` object with `LiveCounterUpdate.noop` set to `true`, indicating that no update was made to the object
  - `(RTLC6f)` If `ObjectState.tombstone` is `true`, tombstone the current `LiveCounter` using [`LiveObject.tombstone`](#RTLO4e), passing in the outer `ObjectMessage` for the `ObjectState`. Finish processing the `ObjectState`
    - `(RTLC6f1)` Return a `LiveCounterUpdate` object with `LiveCounterUpdate.update.amount` set to the negative `data` value that this `LiveCounter` had before being tombstoned
  - `(RTLC6g)` Store the current `data` value as `previousData` for use in [RTLC6h](#RTLC6h)
  - `(RTLC6b)` Set the private flag `createOperationIsMerged` to `false`
  - `(RTLC6c)` Set `data` to the value of `ObjectState.counter.count`, or to 0 if it does not exist
  - `(RTLC6d)` If `ObjectState.createOp` is present, merge the initial value into the `LiveCounter` as described in [RTLC16](#RTLC16), passing in the `ObjectState.createOp` instance. Discard the `LiveCounterUpdate` object returned by the merge operation
    - `(RTLC6d1)` This clause has been replaced by [RTLC10a](#RTLC10a)
    - `(RTLC6d2)` This clause has been replaced by [RTLC10b](#RTLC10b)
  - `(RTLC6h)` Calculate the diff between `previousData` from [RTLC6g](#RTLC6g) and the current `data` per [RTLC14](#RTLC14), and return the resulting `LiveCounterUpdate` object
- `(RTLC7)` An `ObjectOperation` from `ObjectMessage.operation` can be applied to a `LiveCounter` by performing the following actions in order:
  - `(RTLC7f)` Expects the following arguments:
    - `(RTLC7f1)` `ObjectMessage` - an `ObjectMessage` instance with an existing `ObjectMessage.operation` object, with `ObjectMessage.operation.objectId` matching the Object ID of this `LiveCounter`. This `ObjectMessage` represents the operation to be applied to this `LiveCounter`
    - `(RTLC7f2)` `source` `ObjectsOperationSource` - the source of the operation (see [RTO22](#RTO22))
  - `(RTLC7g)` Returns a boolean indicating whether the operation was successfully applied
  - `(RTLC7a)` A client library may choose to implement this logic as a convenience method named `applyOperation`, which accepts the arguments described in [RTLC7f](#RTLC7f)
  - `(RTLC7b)` If `ObjectMessage.operation` cannot be applied based on the result of [`LiveObject.canApplyOperation`](#RTLO4a), log a debug or trace message indicating that the operation cannot be applied because its serial value is not newer than the object's, and discard the `ObjectMessage` without taking any further action. Return `false`
  - `(RTLC7c)` If `source` is `CHANNEL`, set the entry in the private `siteTimeserials` map at the key `ObjectMessage.siteCode` to equal `ObjectMessage.serial`
  - `(RTLC7e)` If `LiveCounter.isTombstone` is `true`, the operation cannot be applied to the object. Finish processing the `ObjectMessage` without taking any further action. No data update event is emitted. Return `false`
  - `(RTLC7d)` The `ObjectMessage.operation.action` field (see [`ObjectOperationAction`](../features#OOP2)) determines the type of operation to apply:
    - `(RTLC7d1)` If `ObjectMessage.operation.action` is set to `COUNTER_CREATE`, apply the operation as described in [RTLC8](#RTLC8), passing in `ObjectMessage.operation`
      - `(RTLC7d1a)` Emit the `LiveCounterUpdate` object returned as a result of applying the operation
      - `(RTLC7d1b)` Return `true`
    - `(RTLC7d2)` This clause has been replaced by [RTLC7d5](#RTLC7d5) as of specification version 6.0.0.
      - `(RTLC7d2a)` This clause has been replaced by [RTLC7d5a](#RTLC7d5a) as of specification version 6.0.0.
      - `(RTLC7d2b)` This clause has been replaced by [RTLC7d5b](#RTLC7d5b) as of specification version 6.0.0.
    - `(RTLC7d5)` If `ObjectMessage.operation.action` is set to `COUNTER_INC`, apply the operation as described in [RTLC9](#RTLC9), passing in `ObjectMessage.operation.counterInc`
      - `(RTLC7d5a)` Emit the `LiveCounterUpdate` object returned as a result of applying the operation
      - `(RTLC7d5b)` Return `true`
    - `(RTLC7d4)` If `ObjectMessage.operation.action` is set to `OBJECT_DELETE`, apply the operation as described in [RTLO5](#RTLO5), passing in `ObjectMessage`
      - `(RTLC7d4a)` Emit a `LiveCounterUpdate` object after applying the `OBJECT_DELETE` operation, with `LiveCounterUpdate.update.amount` set to the negated value that this `LiveCounter` held before the operation was applied
      - `(RTLC7d4b)` Return `true`
    - `(RTLC7d3)` Otherwise, log a warning that an object operation message with an unsupported action has been received, and discard the current `ObjectMessage` without taking any further action. No data update event is emitted. Return `false`
- `(RTLC8)` A `COUNTER_CREATE` operation can be applied to a `LiveCounter` in the following way:
  - `(RTLC8a)` Expects the following arguments:
    - `(RTLC8a1)` `ObjectOperation`
  - `(RTLC8d)` The return type is a `LiveCounterUpdate` object, which indicates the data update for this `LiveCounter`
  - `(RTLC8b)` If the private flag `createOperationIsMerged` is `true`, log a debug or trace message indicating that the operation will not be applied because a `COUNTER_CREATE` operation has already been applied to this `LiveCounter`. Discard the operation without taking any further action, and return a `LiveCounterUpdate` object with `LiveCounterUpdate.noop` set to `true`, indicating that no update was made to the object
  - `(RTLC8c)` Otherwise merge the initial value into the `LiveCounter` as described in [RTLC16](#RTLC16), passing in the `ObjectOperation` instance
  - `(RTLC8e)` Return the `LiveCounterUpdate` object returned by [RTLC16](#RTLC16)
- `(RTLC9)` A `COUNTER_INC` operation can be applied to a `LiveCounter` in the following way:
  - `(RTLC9a)` Expects the following arguments:
    - `(RTLC9a1)` This clause has been replaced by [RTLC9a2](#RTLC9a2) as of specification version 6.0.0.
    - `(RTLC9a2)` `CounterInc`
  - `(RTLC9c)` The return type is a `LiveCounterUpdate` object, which indicates the data update for this `LiveCounter`
  - `(RTLC9b)` This clause has been replaced by [RTLC9f](#RTLC9f) as of specification version 6.0.0.
  - `(RTLC9d)` This clause has been replaced by [RTLC9g](#RTLC9g) as of specification version 6.0.0.
  - `(RTLC9e)` This clause has been replaced by [RTLC9h](#RTLC9h) as of specification version 6.0.0.
  - `(RTLC9f)` Add `CounterInc.number` to `data`, if it exists
  - `(RTLC9g)` If `CounterInc.number` exists, return a `LiveCounterUpdate` object with `LiveCounterUpdate.update.amount` set to `CounterInc.number`
  - `(RTLC9h)` If `CounterInc.number` does not exist, return a `LiveCounterUpdate` object with `LiveCounterUpdate.noop` set to `true`
- `(RTLC10)` This clause has been replaced by [RTLC16](#RTLC16) as of specification version 6.0.0.
  - `(RTLC10a)` This clause has been replaced by [RTLC16a](#RTLC16a) as of specification version 6.0.0.
  - `(RTLC10b)` This clause has been replaced by [RTLC16b](#RTLC16b) as of specification version 6.0.0.
  - `(RTLC10c)` This clause has been replaced by [RTLC16c](#RTLC16c) as of specification version 6.0.0.
  - `(RTLC10d)` This clause has been replaced by [RTLC16d](#RTLC16d) as of specification version 6.0.0.
- `(RTLC16)` The initial value from an `ObjectOperation` can be merged into this `LiveCounter` in the following way. Let `counterCreate` be `ObjectOperation.counterCreate` if present, else the `CounterCreate` from which `ObjectOperation.counterCreateWithObjectId` was derived (see [RTO12f16](#RTO12f16)):
  - `(RTLC16a)` Add `counterCreate.count` to `data`, if it exists
  - `(RTLC16b)` Set the private flag `createOperationIsMerged` to `true`
  - `(RTLC16c)` If `counterCreate.count` exists, return a `LiveCounterUpdate` object with `LiveCounterUpdate.update.amount` set to `counterCreate.count`
  - `(RTLC16d)` If `counterCreate.count` does not exist, return a `LiveCounterUpdate` object with `LiveCounterUpdate.noop` set to `true`
- `(RTLC14)` The diff between two `LiveCounter` data values can be calculated in the following way:
  - `(RTLC14a)` Expects the following arguments:
    - `(RTLC14a1)` `previousData` `Number` - the previous `data` value
    - `(RTLC14a2)` `newData` `Number` - the new `data` value
  - `(RTLC14b)` Return a `LiveCounterUpdate` object with `LiveCounterUpdate.update.amount` set to `newData - previousData`

### LiveMap

- `(RTLM1)` The `LiveMap` extends `LiveObject`
- `(RTLM2)` Represents the map object type for Object IDs of type `map`
- `(RTLM3)` Holds a `Dict<String, ObjectsMapEntry>` as a private `data` map
  - `(RTLM3a)` `ObjectsMapEntry` entries in a `LiveMap` have the following attributes in addition to those defined in [OME2](../features#OME2):
    - `(RTLM3a1)` `tombstonedAt` (optional) Time - a timestamp indicating when this map entry was tombstoned. This property is nullable, and specification points that manipulate this value maintain the invariant that it is non-null if and only if the corresponding `ObjectsMapEntry.tombstone` is `true`
- `(RTLM25)` Holds a nullable private `clearTimeserial` string, initially `null`
- `(RTLM4)` The zero-value `LiveMap` is a `LiveMap` with `data` set to an empty map and `clearTimeserial` set to `null`
- `(RTLM18)` Data updates for a `LiveMap` are emitted using the `LiveMapUpdate` object:
  - `(RTLM18a)` `LiveMapUpdate` extends `LiveObjectUpdate`
  - `(RTLM18b)` `LiveMapUpdate.update` is of type `Dict<String, 'updated' | 'removed'>` - a map of `LiveMap` keys that were either updated or removed, with the corresponding value indicating the type of change for each key
- `(RTLM5)` `LiveMap#get` function:
  - `(RTLM5a)` Accepts a key of type String
  - `(RTLM5b)` Requires the `OBJECT_SUBSCRIBE` channel mode to be granted per [RTO2](#RTO2)
  - `(RTLM5c)` If the channel is in the `DETACHED` or `FAILED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
  - `(RTLM5e)` If `LiveMap.isTombstone` is `true`, return undefined/null
  - `(RTLM5d)` Returns the value from the current `data` at the specified key, as follows:
    - `(RTLM5d1)` If no `ObjectsMapEntry` exists at the key, return undefined/null
    - `(RTLM5d2)` If an `ObjectsMapEntry` exists at the key:
      - `(RTLM5d2a)` If `ObjectsMapEntry.tombstone` is `true`, return undefined/null
      - `(RTLM5d2b)` If `ObjectsMapEntry.data.boolean` exists, return it
      - `(RTLM5d2c)` If `ObjectsMapEntry.data.bytes` exists, return it
      - `(RTLM5d2d)` If `ObjectsMapEntry.data.number` exists, return it
      - `(RTLM5d2e)` If `ObjectsMapEntry.data.string` exists, return it
      - `(RTLM5d2f)` If `ObjectsMapEntry.data.objectId` exists, get the object stored at that `objectId` from the internal `ObjectsPool`:
        - `(RTLM5d2f1)` If an object with id `objectId` does not exist, return undefined/null
        - `(RTLM5d2f3)` If an object with id `objectId` exists and its `LiveObject.isTombstone` is `true`, return undefined/null
        - `(RTLM5d2f2)` Otherwise, return the object with id `objectId`
      - `(RTLM5d2g)` Otherwise, return undefined/null
- `(RTLM10)` `LiveMap#size`:
  - `(RTLM10a)` A method or property, depending on what is more idiomatic for the platform to use for a Map/Dictionary interface. For example, in JavaScript, this is a property similar to `Map.size` for the native `Map` class
  - `(RTLM10b)` Requires the `OBJECT_SUBSCRIBE` channel mode to be granted per [RTO2](#RTO2)
  - `(RTLM10c)` If the channel is in the `DETACHED` or `FAILED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
  - `(RTLM10d)` Returns the number of non-tombstoned entries (per [RTLM14](#RTLM14)) in the internal `data` map
- `(RTLM11)` `LiveMap#entries`:
  - `(RTLM11a)` A method or property, depending on what is more idiomatic for the platform to use for a Map/Dictionary interface. For example, in JavaScript, this is a method similar to `Map.entries()` for the native `Map` class
  - `(RTLM11b)` Requires the `OBJECT_SUBSCRIBE` channel mode to be granted per [RTO2](#RTO2)
  - `(RTLM11c)` If the channel is in the `DETACHED` or `FAILED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
  - `(RTLM11d)` Returns key-value pairs from the internal `data` map:
    - `(RTLM11d1)` Pairs with tombstoned entries (per [RTLM14](#RTLM14)) are not returned
    - `(RTLM11d3)` `ObjectsMapEntry` values are mapped to user-facing values following the same procedure as in [RTLM5d2](#RTLM5d2)
      - `(RTLM11d3a)` Note that if [RTLM5d2](#RTLM5d2) results in an `ObjectsMapEntry` being mapped to an undefined/null value, the corresponding key-value pair is still returned by this `LiveMap#entries` call
    - `(RTLM11d2)` The return type is idiomatic for the platform's analogous Map/Dictionary interface operation. For example, in JavaScript, it returns a map iterator object like the one returned by `Map.entries()` method for the native `Map` class
- `(RTLM12)` `LiveMap#keys`:
  - `(RTLM12a)` A method or property, depending on what is more idiomatic for the platform to use for a Map/Dictionary interface. For example, in JavaScript, this is a method similar to `Map.keys()` for the native `Map` class
  - `(RTLM12b)` The implementation is identical to `LiveMap#entries`, except that it returns only the keys from the internal `data` map
- `(RTLM13)` `LiveMap#values`:
  - `(RTLM13a)` A method or property, depending on what is more idiomatic for the platform to use for a Map/Dictionary interface. For example, in JavaScript, this is a method similar to `Map.values()` for the native `Map` class
  - `(RTLM13b)` The implementation is identical to `LiveMap#entries`, except that it returns only the values from the internal `data` map
- `(RTLM20)` `LiveMap#set` function:
  - `(RTLM20a)` Expects the following arguments:
    - `(RTLM20a1)` `key` `String` - the key to set the value for
    - `(RTLM20a2)` `value` `Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounter | LiveMap` - the value to assign to the key
  - `(RTLM20b)` Requires the `OBJECT_PUBLISH` channel mode to be granted per [RTO2](#RTO2)
  - `(RTLM20c)` If the channel is in the `DETACHED`, `FAILED` or `SUSPENDED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
  - `(RTLM20d)` If [`echoMessages`](../features#TO3h) client option is `false`, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40000, indicating that `echoMessages` must be enabled for this operation
  - `(RTLM20e)` Creates an `ObjectMessage` for a `MAP_SET` action in the following way:
    - `(RTLM20e1)` Validates the provided `key` and `value` in a similar way as described in [RTO11f2](#RTO11f2) and [RTO11f3](#RTO11f3)
    - `(RTLM20e2)` Set `ObjectMessage.operation.action` to `ObjectOperationAction.MAP_SET`
    - `(RTLM20e3)` Set `ObjectMessage.operation.objectId` to the Object ID of this `LiveMap`
    - `(RTLM20e4)` This clause has been replaced by [RTLM20e6](#RTLM20e6) as of specification version 6.0.0.
    - `(RTLM20e5)` This clause has been replaced by [RTLM20e7](#RTLM20e7) as of specification version 6.0.0.
      - `(RTLM20e5a)` This clause has been replaced by [RTLM20e7a](#RTLM20e7a) as of specification version 6.0.0.
      - `(RTLM20e5b)` This clause has been replaced by [RTLM20e7b](#RTLM20e7b) as of specification version 6.0.0.
      - `(RTLM20e5c)` This clause has been replaced by [RTLM20e7c](#RTLM20e7c) as of specification version 6.0.0.
      - `(RTLM20e5d)` This clause has been replaced by [RTLM20e7d](#RTLM20e7d) as of specification version 6.0.0.
      - `(RTLM20e5e)` This clause has been replaced by [RTLM20e7e](#RTLM20e7e) as of specification version 6.0.0.
      - `(RTLM20e5f)` This clause has been replaced by [RTLM20e7f](#RTLM20e7f) as of specification version 6.0.0.
    - `(RTLM20e6)` Set `ObjectMessage.operation.mapSet.key` to the provided `key` value
    - `(RTLM20e7)` Set `ObjectMessage.operation.mapSet.value` depending on the type of the provided `value`:
      - `(RTLM20e7a)` If the `value` is of type `LiveCounter` or `LiveMap`, set `ObjectMessage.operation.mapSet.value.objectId` to the `objectId` of that object
      - `(RTLM20e7b)` If the `value` is of type `JsonArray` or `JsonObject`, set `ObjectMessage.operation.mapSet.value.json` to that value
      - `(RTLM20e7c)` If the `value` is of type `String`, set `ObjectMessage.operation.mapSet.value.string` to that value
      - `(RTLM20e7d)` If the `value` is of type `Number`, set `ObjectMessage.operation.mapSet.value.number` to that value
      - `(RTLM20e7e)` If the `value` is of type `Boolean`, set `ObjectMessage.operation.mapSet.value.boolean` to that value
      - `(RTLM20e7f)` If the `value` is of type `Binary`, set `ObjectMessage.operation.mapSet.value.bytes` to that value
  - `(RTLM20f)` This clause has been replaced by [RTLM20g](#RTLM20g)
  - `(RTLM20g)` Publishes the `ObjectMessage` from [RTLM20e](#RTLM20e) using `RealtimeObjects#publishAndApply` ([RTO20](#RTO20)), passing the `ObjectMessage` as a single element in the array
- `(RTLM21)` `LiveMap#remove` function:
  - `(RTLM21a)` Expects the following arguments:
    - `(RTLM21a1)` `key` `String` - the key to remove the value for
  - `(RTLM21b)` Requires the `OBJECT_PUBLISH` channel mode to be granted per [RTO2](#RTO2)
  - `(RTLM21c)` If the channel is in the `DETACHED`, `FAILED` or `SUSPENDED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
  - `(RTLM21d)` If [`echoMessages`](../features#TO3h) client option is `false`, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40000, indicating that `echoMessages` must be enabled for this operation
  - `(RTLM21e)` Creates an `ObjectMessage` for a `MAP_REMOVE` action in the following way:
    - `(RTLM21e1)` Validates the provided `key` in a similar way as described in [RTO11f2](#RTO11f2)
    - `(RTLM21e2)` Set `ObjectMessage.operation.action` to `ObjectOperationAction.MAP_REMOVE`
    - `(RTLM21e3)` Set `ObjectMessage.operation.objectId` to the Object ID of this `LiveMap`
    - `(RTLM21e4)` This clause has been replaced by [RTLM21e5](#RTLM21e5) as of specification version 6.0.0.
    - `(RTLM21e5)` Set `ObjectMessage.operation.mapRemove.key` to the provided `key` value
  - `(RTLM21f)` This clause has been replaced by [RTLM21g](#RTLM21g)
  - `(RTLM21g)` Publishes the `ObjectMessage` from [RTLM21e](#RTLM21e) using `RealtimeObjects#publishAndApply` ([RTO20](#RTO20)), passing the `ObjectMessage` as a single element in the array
- `(RTLM14)` An `ObjectsMapEntry` in the internal `data` map can be checked for being tombstoned using the convenience method:
  - `(RTLM14a)` The method returns true if `ObjectsMapEntry.tombstone` is true
  - `(RTLM14c)` The method returns true if `ObjectsMapEntry.data.objectId` exists, there is an object in the local `ObjectsPool` with that id, and that `LiveObject.isTombstone` property is `true`
  - `(RTLM14b)` Otherwise, it returns false
- `(RTLM6)` `LiveMap` internal `data` can be replaced with the provided `ObjectState` in the following way:
  - `(RTLM6a)` Replace the private `siteTimeserials` of the `LiveMap` with the value from `ObjectState.siteTimeserials`
  - `(RTLM6e)` If `LiveMap.isTombstone` is `true`, finish processing the `ObjectState`
    - `(RTLM6e1)` Return a `LiveMapUpdate` object with `LiveMapUpdate.noop` set to `true`, indicating that no update was made to the object
  - `(RTLM6f)` If `ObjectState.tombstone` is `true`, tombstone the current `LiveMap` using [`LiveObject.tombstone`](#RTLO4e), passing in the outer `ObjectMessage` for the `ObjectState`. Finish processing the `ObjectState`
    - `(RTLM6f1)` Return a `LiveMapUpdate` object with `LiveMapUpdate.update` consisting of entries for the keys that were removed as a result of the object being tombstoned, each set to `removed`
  - `(RTLM6g)` Store the current `data` value as `previousData` for use in [RTLM6h](#RTLM6h)
  - `(RTLM6b)` Set the private flag `createOperationIsMerged` to `false`
  - `(RTLM6i)` Set the private `clearTimeserial` to `ObjectState.map.clearTimeserial`, or to `null` if not provided
  - `(RTLM6c)` Set `data` to `ObjectState.map.entries`, or to an empty map if it does not exist
    - `(RTLM6c1)` For each `ObjectsMapEntry` with `ObjectsMapEntry.tombstone` equal to `true`, additionally set the `ObjectsMapEntry.tombstonedAt` field to the value calculated per [RTLO6](#RTLO6), using `ObjectsMapEntry.serialTimestamp`
      - `(RTLM6c1a)` This clause has been replaced by [RTLO6a](#RTLO6a)
      - `(RTLM6c1b)` This clause has been replaced by [RTLO6b](#RTLO6b)
        - `(RTLM6c1b1)` This clause has been replaced by [RTLO6b1](#RTLO6b1)
  - `(RTLM6d)` If `ObjectState.createOp` is present, merge the initial value into the `LiveMap` as described in [RTLM23](#RTLM23), passing in the `ObjectState.createOp` instance. Discard the `LiveMapUpdate` object returned by the merge operation
    - `(RTLM6d1)` This clause has been replaced by [RTLM17a](#RTLM17a)
      - `(RTLM6d1a)` This clause has been replaced by [RTLM17a1](#RTLM17a1)
      - `(RTLM6d1b)` This clause has been replaced by [RTLM17a2](#RTLM17a2)
    - `(RTLM6d2)` This clause has been replaced by [RTLM17b](#RTLM17b)
  - `(RTLM6h)` Calculate the diff between `previousData` from [RTLM6g](#RTLM6g) and the current `data` per [RTLM22](#RTLM22), and return the resulting `LiveMapUpdate` object
- `(RTLM15)` An `ObjectOperation` from `ObjectMessage.operation` can be applied to a `LiveMap` by performing the following actions in order:
  - `(RTLM15f)` Expects the following arguments:
    - `(RTLM15f1)` `ObjectMessage` - an `ObjectMessage` instance with an existing `ObjectMessage.operation` object, with `ObjectMessage.operation.objectId` matching the Object ID of this `LiveMap`. This `ObjectMessage` represents the operation to be applied to this `LiveMap`
    - `(RTLM15f2)` `source` `ObjectsOperationSource` - the source of the operation (see [RTO22](#RTO22))
  - `(RTLM15g)` Returns a boolean indicating whether the operation was successfully applied
  - `(RTLM15a)` A client library may choose to implement this logic as a convenience method named `applyOperation`, which accepts the arguments described in [RTLM15f](#RTLM15f)
  - `(RTLM15b)` If `ObjectMessage.operation` cannot be applied based on the result of [`LiveObject.canApplyOperation`](#RTLO4a), log a debug or trace message indicating that the operation cannot be applied because its serial value is not newer than the object's, and discard the `ObjectMessage` without taking any further action. Return `false`
  - `(RTLM15c)` If `source` is `CHANNEL`, set the entry in the private `siteTimeserials` map at the key `ObjectMessage.siteCode` to equal `ObjectMessage.serial`
  - `(RTLM15e)` If `LiveMap.isTombstone` is `true`, the operation cannot be applied to the object. Finish processing the `ObjectMessage` without taking any further action. No data update event is emitted. Return `false`
  - `(RTLM15d)` The `ObjectMessage.operation.action` field (see [`ObjectOperationAction`](../features#OOP2)) determines the type of operation to apply:
    - `(RTLM15d1)` If `ObjectMessage.operation.action` is set to `MAP_CREATE`, apply the operation as described in [RTLM16](#RTLM16), passing in `ObjectMessage.operation`
      - `(RTLM15d1a)` Emit the `LiveMapUpdate` object returned as a result of applying the operation
      - `(RTLM15d1b)` Return `true`
    - `(RTLM15d2)` This clause has been replaced by [RTLM15d6](#RTLM15d6) as of specification version 6.0.0.
      - `(RTLM15d2a)` This clause has been replaced by [RTLM15d6a](#RTLM15d6a) as of specification version 6.0.0.
      - `(RTLM15d2b)` This clause has been replaced by [RTLM15d6b](#RTLM15d6b) as of specification version 6.0.0.
    - `(RTLM15d6)` If `ObjectMessage.operation.action` is set to `MAP_SET`, apply the operation as described in [RTLM7](#RTLM7), passing in `ObjectMessage.operation.mapSet` and `ObjectMessage.serial`
      - `(RTLM15d6a)` Emit the `LiveMapUpdate` object returned as a result of applying the operation
      - `(RTLM15d6b)` Return `true`
    - `(RTLM15d3)` This clause has been replaced by [RTLM15d7](#RTLM15d7) as of specification version 6.0.0.
      - `(RTLM15d3a)` This clause has been replaced by [RTLM15d7a](#RTLM15d7a) as of specification version 6.0.0.
      - `(RTLM15d3b)` This clause has been replaced by [RTLM15d7b](#RTLM15d7b) as of specification version 6.0.0.
    - `(RTLM15d7)` If `ObjectMessage.operation.action` is set to `MAP_REMOVE`, apply the operation as described in [RTLM8](#RTLM8), passing in `ObjectMessage.operation.mapRemove`, `ObjectMessage.serial` and `ObjectMessage.serialTimestamp`
      - `(RTLM15d7a)` Emit the `LiveMapUpdate` object returned as a result of applying the operation
      - `(RTLM15d7b)` Return `true`
    - `(RTLM15d5)` If `ObjectMessage.operation.action` is set to `OBJECT_DELETE`, apply the operation as described in [RTLO5](#RTLO5), passing in `ObjectMessage`
      - `(RTLM15d5a)` Emit a `LiveMapUpdate` object with `LiveMapUpdate.update` consisting of entries for the keys that were removed as a result of applying the `OBJECT_DELETE` operation, each set to `removed`
      - `(RTLM15d5b)` Return `true`
    - `(RTLM15d8)` If `ObjectMessage.operation.action` is set to `MAP_CLEAR`, apply the operation as described in [RTLM24](#RTLM24), passing in `ObjectMessage.serial`
      - `(RTLM15d8a)` Emit the `LiveMapUpdate` object returned as a result of applying the operation
      - `(RTLM15d8b)` Return `true`
    - `(RTLM15d4)` Otherwise, log a warning that an object operation message with an unsupported action has been received, and discard the current `ObjectMessage` without taking any further action. No data update event is emitted. Return `false`
- `(RTLM16)` A `MAP_CREATE` operation can be applied to a `LiveMap` in the following way:
  - `(RTLM16a)` Expects the following arguments:
    - `(RTLM16a1)` `ObjectOperation`
  - `(RTLM16e)` The return type is a `LiveMapUpdate` object, which indicates the data update for this `LiveMap`
  - `(RTLM16b)` If the private flag `createOperationIsMerged` is `true`, log a debug or trace message indicating that the operation will not be applied because a `MAP_CREATE` operation has already been applied to this `LiveMap`. Discard the operation without taking any further action, and return a `LiveMapUpdate` object with `LiveMapUpdate.noop` set to `true`, indicating that no update was made to the object
  - `(RTLM16c)` This clause has been deleted.
  - `(RTLM16d)` Otherwise merge the initial value into the `LiveMap` as described in [RTLM23](#RTLM23), passing in the `ObjectOperation` instance
  - `(RTLM16f)` Return the `LiveMapUpdate` object returned by [RTLM23](#RTLM23)
- `(RTLM7)` A `MAP_SET` operation for a key can be applied to a `LiveMap` in the following way:
  - `(RTLM7d)` Expects the following arguments:
    - `(RTLM7d1)` This clause has been replaced by [RTLM7d3](#RTLM7d3) as of specification version 6.0.0.
    - `(RTLM7d3)` `MapSet`
    - `(RTLM7d2)` `serial` string - operation's serial value
  - `(RTLM7e)` The return type is a `LiveMapUpdate` object, which indicates the data update for this `LiveMap`
  - `(RTLM7h)` If the private `clearTimeserial` is non-null, and the provided `serial` is null or the `clearTimeserial` is lexicographically greater than or equal to `serial`, discard the operation without taking any action. Return a `LiveMapUpdate` object with `LiveMapUpdate.noop` set to `true`, indicating that no update was made to the object
  - `(RTLM7a)` If an `ObjectsMapEntry` exists in the private `data` for the specified key:
    - `(RTLM7a1)` If the operation cannot be applied to the existing entry as per [RTLM9](#RTLM9), discard the operation without taking any action. Return a `LiveMapUpdate` object with `LiveMapUpdate.noop` set to `true`, indicating that no update was made to the object
    - `(RTLM7a2)` Otherwise, apply the operation to the existing entry:
      - `(RTLM7a2a)` This clause has been replaced by [RTLM7a2e](#RTLM7a2e) as of specification version 6.0.0.
      - `(RTLM7a2e)` Set `ObjectsMapEntry.data` to the `MapSet.value`
      - `(RTLM7a2b)` Set `ObjectsMapEntry.timeserial` to the provided `serial`
      - `(RTLM7a2c)` Set `ObjectsMapEntry.tombstone` to `false`
      - `(RTLM7a2d)` Set `ObjectsMapEntry.tombstonedAt` to undefined/null
  - `(RTLM7b)` If an entry does not exist in the private `data` for the specified key:
    - `(RTLM7b1)` This clause has been replaced by [RTLM7b4](#RTLM7b4) as of specification version 6.0.0.
    - `(RTLM7b4)` Create a new `ObjectsMapEntry` in `data` for the specified key, with `ObjectsMapEntry.data` set to `MapSet.value` and `ObjectsMapEntry.timeserial` set to `serial`
    - `(RTLM7b2)` Set `ObjectsMapEntry.tombstone` for the new entry to `false`
    - `(RTLM7b3)` Set `ObjectsMapEntry.tombstonedAt` for the new entry to undefined/null
  - `(RTLM7c)` This clause has been replaced by [RTLM7g](#RTLM7g) as of specification version 6.0.0.
    - `(RTLM7c1)` This clause has been replaced by [RTLM7g1](#RTLM7g1) as of specification version 6.0.0.
  - `(RTLM7g)` If `MapSet.value.objectId` is non-empty:
    - `(RTLM7g1)` Create a zero-value `LiveObject` for this `objectId` in the internal `ObjectsPool` per [RTO6](#RTO6)
  - `(RTLM7f)` Return a `LiveMapUpdate` object with a `LiveMapUpdate.update` map containing the key used in this operation set to `updated`
- `(RTLM8)` A `MAP_REMOVE` operation for a key can be applied to a `LiveMap` in the following way:
  - `(RTLM8c)` Expects the following arguments:
    - `(RTLM8c1)` This clause has been replaced by [RTLM8c4](#RTLM8c4) as of specification version 6.0.0.
    - `(RTLM8c4)` `MapRemove`
    - `(RTLM8c2)` `serial` string - operation's serial value
    - `(RTLM8c3)` `serialTimestamp` Time - operation's serial timestamp value
  - `(RTLM8d)` The return type is a `LiveMapUpdate` object, which indicates the data update for this `LiveMap`
  - `(RTLM8g)` If the private `clearTimeserial` is non-null, and the provided `serial` is null or the `clearTimeserial` is lexicographically greater than or equal to `serial`, discard the operation without taking any action. Return a `LiveMapUpdate` object with `LiveMapUpdate.noop` set to `true`, indicating that no update was made to the object
  - `(RTLM8a)` If an `ObjectsMapEntry` exists in the private `data` for the specified key:
    - `(RTLM8a1)` If the operation cannot be applied to the existing entry as per [RTLM9](#RTLM9), discard the operation without taking any action. Return a `LiveMapUpdate` object with `LiveMapUpdate.noop` set to `true`, indicating that no update was made to the object
    - `(RTLM8a2)` Otherwise, apply the operation to the existing entry:
      - `(RTLM8a2a)` Set `ObjectsMapEntry.data` to undefined/null
      - `(RTLM8a2b)` Set `ObjectsMapEntry.timeserial` to the provided `serial`
      - `(RTLM8a2c)` Set `ObjectsMapEntry.tombstone` to `true`
      - `(RTLM8a2d)` Set `ObjectsMapEntry.tombstonedAt` to the value calculated per [RTLO6](#RTLO6), using the provided `serialTimestamp`
  - `(RTLM8b)` If an entry does not exist in the private `data` for the specified key:
    - `(RTLM8b1)` Create a new `ObjectsMapEntry` in `data` for the specified key, with `ObjectsMapEntry.data` set to undefined/null and `ObjectsMapEntry.timeserial` set to the provided `serial`
    - `(RTLM8b2)` Set `ObjectsMapEntry.tombstone` for the new entry to `true`
    - `(RTLM8b3)` Set `ObjectsMapEntry.tombstonedAt` for the new entry to the value calculated per [RTLO6](#RTLO6), using the provided `serialTimestamp`
  - `(RTLM8f)` This clause has been replaced by [RTLO6](#RTLO6)
    - `(RTLM8f1)` This clause has been replaced by [RTLO6a](#RTLO6a)
    - `(RTLM8f2)` This clause has been replaced by [RTLO6b](#RTLO6b)
      - `(RTLM8f2a)` This clause has been replaced by [RTLO6b1](#RTLO6b1)
  - `(RTLM8e)` Return a `LiveMapUpdate` object with a `LiveMapUpdate.update` map containing the key used in this operation set to `removed`
- `(RTLM24)` A `MAP_CLEAR` operation can be applied to a `LiveMap` in the following way:
  - `(RTLM24a)` Expects the following arguments:
    - `(RTLM24a1)` `serial` string - the operation's serial value
  - `(RTLM24b)` The return type is a `LiveMapUpdate` object, which indicates the data update for this `LiveMap`
  - `(RTLM24c)` If the private `clearTimeserial` is non-null and is lexicographically greater than the provided `serial`, discard the operation without taking any action. Return a `LiveMapUpdate` object with `LiveMapUpdate.noop` set to `true`, indicating that no update was made to the object
  - `(RTLM24d)` Set the private `clearTimeserial` to the provided `serial`
  - `(RTLM24e)` For each `ObjectsMapEntry` in the internal `data`:
    - `(RTLM24e1)` If `ObjectsMapEntry.timeserial` is null or omitted, or the `serial` is lexicographically greater than `ObjectsMapEntry.timeserial`:
      - `(RTLM24e1a)` Remove the entry from the internal `data` map. The entry is not retained as a tombstone.
      - `(RTLM24e1b)` Record the key for the `LiveMapUpdate` as `removed`
  - `(RTLM24f)` Return a `LiveMapUpdate` object with `LiveMapUpdate.update` containing each key recorded in [RTLM24e1b](#RTLM24e1b) set to `removed`
- `(RTLM9)` Whether a map operation can be applied to a map entry is determined as follows:
  - `(RTLM9a)` For a `LiveMap` with `semantics` set to `ObjectsMapSemantics.LWW` (Last-Write-Wins CRDT semantics), the operation must only be applied if its serial is strictly greater ("after") than the entry's serial when compared lexicographically
  - `(RTLM9b)` If both the entry serial and the operation serial are null or empty strings, they are treated as the "earliest possible" serials and considered "equal", so the operation must not be applied
  - `(RTLM9c)` If only the entry serial exists and is not an empty string, the missing operation serial is considered lower than the existing entry serial, so the operation must not be applied
  - `(RTLM9d)` If only the operation serial exists and is not an empty string, it is considered greater than the missing entry serial, so the operation can be applied
  - `(RTLM9e)` If both serials exist and are not empty strings, compare them lexicographically and allow operation to be applied only if the operation's serial is greater than the entry's serial
- `(RTLM17)` This clause has been replaced by [RTLM23](#RTLM23) as of specification version 6.0.0.
  - `(RTLM17a)` This clause has been replaced by [RTLM23a](#RTLM23a) as of specification version 6.0.0.
    - `(RTLM17a1)` This clause has been replaced by [RTLM23a1](#RTLM23a1) as of specification version 6.0.0.
    - `(RTLM17a2)` This clause has been replaced by [RTLM23a2](#RTLM23a2) as of specification version 6.0.0.
  - `(RTLM17b)` This clause has been replaced by [RTLM23b](#RTLM23b) as of specification version 6.0.0.
  - `(RTLM17c)` This clause has been replaced by [RTLM23c](#RTLM23c) as of specification version 6.0.0.
- `(RTLM23)` The initial value from an `ObjectOperation` can be merged into this `LiveMap` in the following way. Let `mapCreate` be `ObjectOperation.mapCreate` if present, else the `MapCreate` from which `ObjectOperation.mapCreateWithObjectId` was derived (see [RTO11f18](#RTO11f18)):
  - `(RTLM23a)` For each key-`ObjectsMapEntry` pair in `mapCreate.entries`:
    - `(RTLM23a1)` If `ObjectsMapEntry.tombstone` is `false` or omitted, apply the `MAP_SET` operation to the current key as described in [RTLM7](#RTLM7), passing in `ObjectsMapEntry.data` and the current key as `MapSet`, and `ObjectsMapEntry.timeserial` as `serial`. Store the returned `LiveMapUpdate` object for use in [RTLM23c](#RTLM23c)
    - `(RTLM23a2)` If `ObjectsMapEntry.tombstone` is `true`, apply the `MAP_REMOVE` operation to the current key as described in [RTLM8](#RTLM8), passing in the current key as `MapRemove`, `ObjectsMapEntry.timeserial` as `serial`, and `ObjectsMapEntry.serialTimestamp` as `serialTimestamp`. Store the returned `LiveMapUpdate` object for use in [RTLM23c](#RTLM23c)
  - `(RTLM23b)` Set the private flag `createOperationIsMerged` to `true`
  - `(RTLM23c)` Return a single `LiveMapUpdate` object, where `LiveMapUpdate.update` is a merged map containing all key-value pairs from the `LiveMapUpdate.update` maps of the stored `LiveMapUpdate` objects. Skip any stored `LiveMapUpdate` objects marked as no-op
- `(RTLM19)` The `LiveMap` can be checked to determine whether it should release resources for its tombstoned `ObjectsMapEntry` entries as follows:
  - `(RTLM19a)` For each `ObjectsMapEntry` in the internal `data`:
    - `(RTLM19a1)` If `ObjectsMapEntry.tombstone` is `true`, and the difference between the current time and `ObjectsMapEntry.tombstonedAt` is greater than or equal to the [grace period](#RTO10b), remove the entry from the internal `data` map and release resources for the corresponding `ObjectsMapEntry` entity to allow it to be garbage collected
- `(RTLM22)` The diff between two `LiveMap` data values can be calculated in the following way:
  - `(RTLM22a)` Expects the following arguments:
    - `(RTLM22a1)` `previousData` `Dict<String, ObjectsMapEntry>` - the previous `data` value
    - `(RTLM22a2)` `newData` `Dict<String, ObjectsMapEntry>` - the new `data` value
  - `(RTLM22b)` Return a `LiveMapUpdate` object where `LiveMapUpdate.update` is calculated by considering only the non-tombstoned entries from `previousData` and `newData`. An entry is non-tombstoned if its `ObjectsMapEntry.tombstone` field is `false`. The update is populated as follows:
    - `(RTLM22b1)` For each key that exists in the non-tombstoned entries of `previousData` but does not exist in the non-tombstoned entries of `newData`, add the key to `LiveMapUpdate.update` with the value `removed`
    - `(RTLM22b2)` For each key that exists in the non-tombstoned entries of `newData` but does not exist in the non-tombstoned entries of `previousData`, add the key to `LiveMapUpdate.update` with the value `updated`
    - `(RTLM22b3)` For each key that exists in the non-tombstoned entries of both `previousData` and `newData`, perform a deep comparison of the `data` attributes from `previousData` and `newData`. If the data values differ, add the key to `LiveMapUpdate.update` with the value `updated`

## Interface Definition {#idl}

Describes types for RestObject and RealtimeObjects.\
Types and their properties/methods are public and exposed to users by default. An `internal` label may be used to indicate that a type or its property/method must not be exposed to users and is intended for internal SDK use only.

    class RestObject: // RSO*
      get(RestObjectGetParams params?) => io RestObjectGetCompactResult | RestObjectGetFullResult // RSO2
      publish(RestObjectOperation | RestObjectOperation[] op) => io RestObjectPublishResult // RSO3
      generateObjectId(RestObjectGenerateIdBody createBody) => RestObjectGenerateIdResult // RSO4

    class RestObjectGetParams: // RSO2a1
      objectId: String? // RSO2a1a
      path: String? // RSO2a1b
      compact: Boolean default true // RSO2a1c

    class RestObjectOperation: // RSO5
      id: String? // RSO5a1
      objectId: String? // RSO5a2
      path: String? // RSO5a3
      mapCreate: RestObjectMapCreate? // RSO5c
      mapCreateWithObjectId: RestObjectCreateWithObjectId? // RSO5d
      mapSet: RestObjectMapSet? // RSO5e
      mapRemove: RestObjectMapRemove? // RSO5f
      counterCreate: RestObjectCounterCreate? // RSO5g
      counterCreateWithObjectId: RestObjectCreateWithObjectId? // RSO5h
      counterInc: RestObjectCounterInc? // RSO5i

    class RestObjectMapCreate: // RSO5c
      semantics: ObjectsMapSemantics // RSO5c1
      entries: Dict<String, RestObjectMapEntry> // RSO5c2

    class RestObjectMapSet: // RSO5e
      key: String // RSO5e1
      value: PublishObjectData // RSO5e2

    class RestObjectMapRemove: // RSO5f
      key: String // RSO5f1

    class RestObjectCounterCreate: // RSO5g
      count: Number // RSO5g1

    class RestObjectCounterInc: // RSO5i
      number: Number // RSO5i1

    class RestObjectCreateWithObjectId: // RSO5d, RSO5h
      initialValue: String // RSO5d1
      nonce: String // RSO5d2

    class RestObjectMapEntry: // RSO13
      data: PublishObjectData // RSO13a

    class PublishObjectData: // RSO7
      string: String? // RSO7a
      number: Number? // RSO7b
      boolean: Boolean? // RSO7c
      bytes: Binary? // RSO7d
      json: JsonObject | JsonArray? // RSO7e
      objectId: String? // RSO7f

    class RestObjectGenerateIdBody: // RSO12
      mapCreate: RestObjectMapCreate? // RSO12a
      counterCreate: RestObjectCounterCreate? // RSO12b

    class RestObjectPublishResult: // RSO10
      messageId: String // RSO10a
      channel: String // RSO10b
      objectIds: [String] // RSO10c

    class RestObjectGenerateIdResult: // RSO11
      objectId: String // RSO11a
      nonce: String // RSO11b
      initialValue: String // RSO11c

    class RestLiveMap: // RSO14
      objectId: String // RSO14a
      map: { semantics: ObjectsMapSemantics, entries: Dict<String, RestLiveMapEntry> } // RSO14b, RSO14c

    class RestLiveCounter: // RSO15
      objectId: String // RSO15a
      counter: { data: { number: Number } } // RSO15b

    class RestLiveMapEntry: // RSO16
      data: RestObjectGetFullResult // RSO16a

    // RestObjectGetCompactResult (RSO8) is opaque to the library and not modelled here.
    // RestObjectGetFullResult (RSO9) is a discriminated union of RestLiveMap, RestLiveCounter,
    // ObjectData, and a forwards-compatibility fallback; see the corresponding spec clauses.

    class RealtimeObjects: // RTO*
      getRoot() => io LiveMap // RTO1
      createMap(Dict<String, Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounter | LiveMap> entries?) => io LiveMap // RTO11
      createCounter(Number count?) => io LiveCounter // RTO12
      on(ObjectsEvent event, (() ->) callback) -> StatusSubscription // RTO18
      off(() ->) // RTO19
      publish(ObjectMessage[]) => io PublishResult // RTO15, internal
      publishAndApply(ObjectMessage[]) => io // RTO20, internal

    enum ObjectsSyncState: // RTO17a
      INITIALIZED // RTO17a1
      SYNCING // RTO17a2
      SYNCED // RTO17a3

    enum ObjectsEvent: // RTO18b
      SYNCING // RTO18b1
      SYNCED // RTO18b2

    enum ObjectsOperationSource: // RTO22, internal
      LOCAL // RTO22a
      CHANNEL // RTO22b

    interface StatusSubscription: // RTO18f
      off() // RTO18f1

    class LiveObject: // RTLO*
      objectId: String // RTLO3a, internal
      siteTimeserials: Dict<String, String> // RTLO3b, internal
      createOperationIsMerged: Boolean // RTLO3c, internal
      isTombstone: Boolean // RTLO3d, internal
      tombstonedAt: Time? // RTLO3e, internal
      canApplyOperation(ObjectMessage) -> Boolean // RTLO4a, internal
      tombstone(ObjectMessage) // RTLO4e, internal
      subscribe((LiveObjectUpdate) ->) -> LiveObjectSubscription // RTLO4b
      unsubscribe((LiveObjectUpdate) ->) // RTLO4c

    interface LiveObjectSubscription: // RTLO4b5
      unsubscribe() // RTLO4b5a

    interface LiveObjectUpdate: // RTLO4b4
      update: Object // RTLO4b4a
      noop: Boolean // RTLO4b4b, internal

    class LiveCounter extends LiveObject: // RTLC*, RTLC1
      value() -> Number // RTLC5
      increment(Number amount) => io // RTLC12
      decrement(Number amount) => io // RTLC13

    interface LiveCounterUpdate extends LiveObjectUpdate: // RTLC11, RTLC11a
      update: { amount: Number } // RTLC11b, RTLC11b1

    class LiveMap extends LiveObject: // RTLM*, RTLM1
      clearTimeserial: String? // RTLM25, internal
      get(key: String) -> (Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounter | LiveMap)? // RTLM5
      size() -> Number // RTLM10
      entries() -> [String, (Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounter | LiveMap)?][] // RTLM11
      keys() -> String[] // RTLM12
      values() -> (Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounter | LiveMap)?[] // RTLM13
      set(String key, (Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounter | LiveMap) value) => io // RTLM20
      remove(String key) => io // RTLM21

    interface LiveMapUpdate extends LiveObjectUpdate: // RTLM18, RTLM18a
      update: Dict<String, 'updated' | 'removed'> // RTLM18b
