---
title: Objects Features
---

## Overview

This document outlines the feature specification for the Objects feature of the Realtime system. It is currently under development and stored separately from the main specification to simplify the initial implementation of the feature in other SDKs. Once completed, it will be moved to the main [features](../features) spec.

Objects feature enables clients to store shared data as "objects" on a channel. When an object is updated, changes are automatically propagated to all subscribed clients in realtime, ensuring each client always sees the latest state.

### RealtimeObject {#realtime-objects}

- `(RTO1)` This clause has been replaced by [RTO23](#RTO23).
  - `(RTO1a)` This clause has been replaced by [RTO23a](#RTO23a).
  - `(RTO1b)` This clause has been replaced by [RTO23b](#RTO23b).
  - `(RTO1c)` This clause has been replaced by [RTO23c](#RTO23c).
  - `(RTO1d)` This clause has been replaced by [RTO23d](#RTO23d).
- `(RTO23)` `RealtimeObject#get` function:
  - `(RTO23a)` Requires the `OBJECT_SUBSCRIBE` channel mode to be granted per [RTO2](#RTO2)
  - `(RTO23b)` If the channel is in the `DETACHED` or `FAILED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
  - `(RTO23c)` If the [RTO17](#RTO17) sync state is not `SYNCED`, waits for the sync state to transition to `SYNCED`
  - `(RTO23d)` Returns a new `PathObject` ([RTPO1](#RTPO1)) with `path` ([RTPO2a](#RTPO2)) set to an empty list and `root` ([RTPO2b](#RTPO2)) set to the `LiveMap` with id `root` from the internal `ObjectsPool`
- `(RTO11)` This clause has been replaced by [RTLMV3](#RTLMV3).
  - `(RTO11a)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11a1)` This clause has been replaced by [RTLMV3](#RTLMV3).
  - `(RTO11b)` This clause has been replaced by [RTLMV3](#RTLMV3).
  - `(RTO11c)` This clause has been replaced by [RTLMV3](#RTLMV3).
  - `(RTO11d)` This clause has been replaced by [RTLMV3](#RTLMV3).
  - `(RTO11e)` This clause has been replaced by [RTLMV3](#RTLMV3).
  - `(RTO11f)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11f1)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11f2)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11f3)` This clause has been replaced by [RTLMV3](#RTLMV3).
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
    - `(RTO11f14)` This clause has been replaced by [RTLMV3](#RTLMV3).
      - `(RTO11f14a)` This clause has been replaced by [RTLMV3](#RTLMV3).
      - `(RTO11f14b)` This clause has been replaced by [RTLMV3](#RTLMV3).
      - `(RTO11f14c)` This clause has been replaced by [RTLMV3](#RTLMV3).
        - `(RTO11f14c1)` This clause has been replaced by [RTLMV3](#RTLMV3).
          - `(RTO11f14c1a)` This clause has been replaced by [RTLMV3](#RTLMV3).
          - `(RTO11f14c1b)` This clause has been replaced by [RTLMV3](#RTLMV3).
          - `(RTO11f14c1c)` This clause has been replaced by [RTLMV3](#RTLMV3).
          - `(RTO11f14c1d)` This clause has been replaced by [RTLMV3](#RTLMV3).
          - `(RTO11f14c1e)` This clause has been replaced by [RTLMV3](#RTLMV3).
          - `(RTO11f14c1f)` This clause has been replaced by [RTLMV3](#RTLMV3).
        - `(RTO11f14c2)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11f5)` This clause has been replaced by [RTO11f15](#RTO11f15) as of specification version 6.0.0.
    - `(RTO11f15)` This clause has been replaced by [RTLMV3](#RTLMV3).
      - `(RTO11f15a)` This clause has been replaced by [RTLMV3](#RTLMV3).
      - `(RTO11f15b)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11f6)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11f7)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11f8)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11f9)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11f10)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11f11)` This clause has been replaced by [RTO11f16](#RTO11f16) as of specification version 6.0.0.
    - `(RTO11f12)` This clause has been replaced by [RTO11f17](#RTO11f17) as of specification version 6.0.0.
    - `(RTO11f13)` This clause has been deleted as of specification version 6.0.0.
    - `(RTO11f16)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11f17)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11f18)` This clause has been replaced by [RTLMV4j5](#RTLMV4j5).
  - `(RTO11g)` This clause has been replaced by [RTO11i](#RTO11i)
  - `(RTO11i)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11i1)` This clause has been replaced by [RTLMV3](#RTLMV3).
  - `(RTO11h)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11h1)` This clause has been deleted.
    - `(RTO11h2)` This clause has been replaced by [RTLMV3](#RTLMV3).
    - `(RTO11h3)` This clause has been replaced by [RTLMV3](#RTLMV3).
      - `(RTO11h3a)` This clause has been deleted.
      - `(RTO11h3b)` This clause has been deleted.
      - `(RTO11h3c)` This clause has been deleted.
      - `(RTO11h3d)` This clause has been replaced by [RTLMV3](#RTLMV3).
- `(RTO12)` This clause has been replaced by [RTLCV3](#RTLCV3).
  - `(RTO12a)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12a1)` This clause has been replaced by [RTLCV3](#RTLCV3).
  - `(RTO12b)` This clause has been replaced by [RTLCV3](#RTLCV3).
  - `(RTO12c)` This clause has been replaced by [RTLCV3](#RTLCV3).
  - `(RTO12d)` This clause has been replaced by [RTLCV3](#RTLCV3).
  - `(RTO12e)` This clause has been replaced by [RTLCV3](#RTLCV3).
  - `(RTO12f)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12f1)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12f2)` This clause has been replaced by [RTO12f12](#RTO12f12) as of specification version 6.0.0.
      - `(RTO12f2a)` This clause has been replaced by [RTO12f12a](#RTO12f12a) as of specification version 6.0.0.
      - `(RTO12f2b)` This clause has been replaced by [RTO12f12b](#RTO12f12b) as of specification version 6.0.0.
    - `(RTO12f12)` This clause has been replaced by [RTLCV3](#RTLCV3).
      - `(RTO12f12a)` This clause has been replaced by [RTLCV3](#RTLCV3).
      - `(RTO12f12b)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12f3)` This clause has been replaced by [RTO12f13](#RTO12f13) as of specification version 6.0.0.
    - `(RTO12f13)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12f4)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12f5)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12f6)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12f7)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12f8)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12f9)` This clause has been replaced by [RTO12f14](#RTO12f14) as of specification version 6.0.0.
    - `(RTO12f10)` This clause has been replaced by [RTO12f15](#RTO12f15) as of specification version 6.0.0.
    - `(RTO12f11)` This clause has been deleted as of specification version 6.0.0.
    - `(RTO12f14)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12f15)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12f16)` This clause has been replaced by [RTLCV4g5](#RTLCV4g5).
  - `(RTO12g)` This clause has been replaced by [RTO12i](#RTO12i)
  - `(RTO12i)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12i1)` This clause has been replaced by [RTLCV3](#RTLCV3).
  - `(RTO12h)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12h1)` This clause has been deleted.
    - `(RTO12h2)` This clause has been replaced by [RTLCV3](#RTLCV3).
    - `(RTO12h3)` This clause has been replaced by [RTLCV3](#RTLCV3).
      - `(RTO12h3a)` This clause has been deleted.
      - `(RTO12h3b)` This clause has been deleted.
      - `(RTO12h3c)` This clause has been deleted.
      - `(RTO12h3d)` This clause has been replaced by [RTLCV3](#RTLCV3).
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
      - `(RTO4b2a)` Emit a `LiveMapUpdate` object for the `LiveMap` with ID `root`, with `LiveMapUpdate.update` consisting of entries for the keys that were removed, each set to `removed`, and without populating `LiveMapUpdate.objectMessage`
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
        - `(RTO5c1a1)` Replace the internal data for the object as described in [RTLC6](#RTLC6) or [RTLM6](#RTLM6) depending on the object type, passing in the current `ObjectMessage`
        - `(RTO5c1a2)` Store the `LiveObjectUpdate` object returned by the operation, along with a reference to the updated object
      - `(RTO5c1b)` If an object with `ObjectState.objectId` does not exist in the internal `ObjectsPool`:
        - `(RTO5c1b1)` Create a new `LiveObject` using the data from `ObjectState` and add it to the internal `ObjectsPool`:
          - `(RTO5c1b1a)` If `ObjectState.counter` is present, create a zero-value `LiveCounter` (per [RTLC4](#RTLC4)), set its private `objectId` equal to `ObjectState.objectId` and replace its internal data using the current `ObjectMessage` per [RTLC6](#RTLC6)
          - `(RTO5c1b1b)` If `ObjectState.map` is present, create a zero-value `LiveMap` (per [RTLM4](#RTLM4)), set its private `objectId` equal to `ObjectState.objectId`, set its private `semantics` equal to `ObjectState.map.semantics` and replace its internal data using the current `ObjectMessage` per [RTLM6](#RTLM6)
          - `(RTO5c1b1c)` This clause has been deleted (redundant to [RTO5f3](#RTO5f3)).
    - `(RTO5c2)` Remove any objects from the internal `ObjectsPool` for which `objectId`s were not received during the sync sequence
      - `(RTO5c2a)` The object with ID `root` must not be removed from `ObjectsPool`, as per [RTO3b](#RTO3b)
    - `(RTO5c10)` After re-establishing the `ObjectsPool` per [RTO5c1](#RTO5c1) and [RTO5c2](#RTO5c2), the client MUST rebuild every `parentReferences` map ([RTLO3f](#RTLO3f)). Specifically:
      - `(RTO5c10a)` For each `LiveObject` in the internal `ObjectsPool` ([RTO3](#RTO3)), reset its `parentReferences` to an empty map as defined in [RTLO3f1](#RTLO3f1)
      - `(RTO5c10b)` After [RTO5c10a](#RTO5c10a) has completed, for each `LiveMap` in the internal `ObjectsPool`, iterate its `LiveMap#entries` as per [RTLM11](#RTLM11)
        - `(RTO5c10b1)` For each iterated entry whose value type is `LiveObject`, call `addParentReference(parent, key)` on the `LiveObject` (per [RTLO4f](#RTLO4f)), passing the iterated `LiveMap` as `parent` and the iterated entry key as `key`
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
  - `(RTO7a)` The `RealtimeObject` instance has an internal attribute `bufferedObjectOperations`, which is an array of `ObjectMessage` instances. This is used to store the buffered `ObjectMessages`, as described in [RTO8a](#RTO8a).
    - `(RTO7a1)` This array is empty upon `RealtimeObject` initialization
  - `(RTO7b)` The `RealtimeObject` instance has an internal attribute `appliedOnAckSerials`, which is a set of strings. This is used to store the serial values of operations that have been applied upon receipt of an `ACK` but for which the echo has not yet been received.
    - `(RTO7b1)` This set is empty upon `RealtimeObject` initialization
- `(RTO8)` When the library receives a `ProtocolMessage` with an action of `OBJECT`, each member of the `ProtocolMessage.state` array (decoded into `ObjectMessage` objects) is passed to the `RealtimeObject` instance per [RTL1](../features#RTL1). Each `ObjectMessage` from `OBJECT` `ProtocolMessage` (also referred to as an `OBJECT` message) describes an operation to be applied to an object on a channel and must be handled as follows:
  - `(RTO8a)` If the [RTO17](#RTO17) sync state is not `SYNCED`, add the `ObjectMessages` to the internal `bufferedObjectOperations` array
  - `(RTO8b)` Otherwise, apply the `ObjectMessages` as described in [RTO9](#RTO9), passing `source` as `CHANNEL`
- `(RTO9)` `OBJECT` messages can be applied to `RealtimeObject` in the following way:
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
- `(RTO15)` Internal `RealtimeObject#publish` function:
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
- `(RTO20)` Internal `RealtimeObject#publishAndApply` function:
  - `(RTO20a)` Expects the following arguments:
    - `(RTO20a1)` `ObjectMessage[]` - an array of `ObjectMessage` to be published on a channel
  - `(RTO20b)` Calls `RealtimeObject#publish` ([RTO15](#RTO15)) with the provided `ObjectMessage[]` and awaits the `PublishResult`. If `publish` fails, rethrow the error and do not proceed
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
- `(RTO17)` The `RealtimeObject` instance must maintain an internal sync state to track the status of synchronising the local objects data with the Ably service.
  - `(RTO17a)` The sync state has type `ObjectsSyncState`, which is an enum with the following cases (note that their descriptions are purely informative; the rules for state transitions are described elsewhere in this specification):
    - `(RTO17a1)` `INITIALIZED` - the initial state when `RealtimeObject` is created
    - `(RTO17a2)` `SYNCING` - in this state, the local copy of objects on the channel is currently being synchronised with the Ably service
    - `(RTO17a3)` `SYNCED` - in this state, the local copy of objects on the channel has been synchronised with the Ably service
  - `(RTO17b)` When the sync state transitions, an event with the `ObjectsEvent` value matching the new state must be emitted to any listeners registered via `RealtimeObject#on` ([RTO18](#RTO18)).
- `(RTO18)` `RealtimeObject#on` function - registers a listener for sync state events
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
- `(RTO19)` `RealtimeObject#off` function - deregisters an event listener previously registered via `RealtimeObject#on` ([RTO18](#RTO18))
- `(RTO22)` `ObjectsOperationSource` is an internal enum describing the source of an operation being applied:
  - `(RTO22a)` `LOCAL` - an operation that originated locally, being applied upon receipt of the `ACK` from Realtime
  - `(RTO22b)` `CHANNEL` - an operation received over a Realtime channel
- `(RTO24)` Internal `PathObjectSubscriptionRegister` - manages path-based subscriptions for `PathObject#subscribe` ([RTPO19](#RTPO19))
  - `(RTO24a)` The `RealtimeObject` instance maintains a single `PathObjectSubscriptionRegister` that manages all path-based subscriptions for the channel
  - `(RTO24b)` Path-based subscription dispatch: given a `LiveObject` and a `LiveObjectUpdate`, the `PathObjectSubscriptionRegister` must determine which subscriptions should be notified by performing the following actions in order:
    - `(RTO24b1)` Let `pathsToThis` be the set of paths returned by calling `getFullPaths` ([RTLO4f](#RTLO4f)) on the `LiveObject`
    - `(RTO24b2)` For each `pathToThis` in `pathsToThis`:
      - `(RTO24b2a)` Construct an ordered list of candidate paths `candidatePaths`, in order of decreasing preference:
        - `(RTO24b2a1)` The first (most-preferred) candidate is `pathToThis` itself
        - `(RTO24b2a2)` If the `LiveObjectUpdate` is a `LiveMapUpdate`, then for each key in `LiveMapUpdate.update`, append a further candidate consisting of `pathToThis` extended by that key
      - `(RTO24b2b)` For each registered subscription, find the first `eventPath` in `candidatePaths` that the subscription covers per [RTO24c1](#RTO24c1). If no such `eventPath` exists, do nothing for this subscription. Otherwise, call the subscription's listener exactly once with a `PathObjectSubscriptionEvent` that has:
        - `(RTO24b2b1)` `object` - a new `PathObject` ([RTPO1](#RTPO1)) with `path` ([RTPO2a](#RTPO2)) set to `eventPath` and `root` ([RTPO2b](#RTPO2)) set to the `LiveMap` with id `root` from the internal `ObjectsPool`
        - `(RTO24b2b2)` `message` - if `LiveObjectUpdate.objectMessage` is populated and its `operation` field is populated, a `PublicAPI::ObjectMessage` derived from `LiveObjectUpdate.objectMessage` per [PAOM3](#PAOM3); otherwise omitted
      - `(RTO24b2c)` If a listener throws an error, the error must be caught and logged without affecting the dispatch to other subscriptions, nor to other `pathToThis` iterations
  - `(RTO24c)` Subscription coverage:
    - `(RTO24c1)` A subscription with subscribed path `subPath` and `depth` option is said to *cover* a path `eventPath` if and only if `subPath` is a prefix of `eventPath` (treating `subPath` as a prefix of itself, so that an exact path match also satisfies this condition), and either `depth` is undefined/null or `eventPath.length - subPath.length + 1 <= depth`
    - `(RTO24c2)` (non-normative) Coverage examples, for a subscription at path `["users"]`:
      - `(RTO24c2a)` With `depth` undefined/null: covers `["users"]`, `["users", "emma"]`, `["users", "emma", "visits"]`, and so on at any depth
      - `(RTO24c2b)` With `depth = 1`: covers `["users"]`; does not cover `["users", "emma"]` or any deeper path
      - `(RTO24c2c)` With `depth = 2`: covers `["users"]` and `["users", "emma"]`; does not cover `["users", "emma", "visits"]` or any deeper path
      - `(RTO24c2d)` With any `depth`: does not cover `["admins"]` or `["userPosts"]`, since the subscription path is not a prefix of either

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
<<<<<<< HEAD
// TODO: Sort out this conflict once I've understood Sachin's changes — the bottom half is my reworded thing that makes the values be strings (also I noticed it's a Set); need to make sure it's consistent with the way that Sachin has specified the manipulations of these values
  - `(RTLO3f)` protected `parentReferences` Map<LiveMap, String[]> - contains mapping from each parent `LiveMap` to the set of keys at which that `LiveMap` currently references this `LiveObject`. This map should be updated as `LiveMap` operations are applied so that path-based subscribers ([RTO24](#RTO24)) can determine every path the object currently occupies in the LiveObjects tree
    - `(RTLO3f1)` Set to an empty map when the `LiveObject` is initialized
=======
  - `(RTLO3f)` protected `parentReferences` `Dict<String, Set<String>>` - tracks which `LiveMap`s in the local `ObjectsPool` currently reference this `LiveObject`, and at which keys they do so. The mapping is keyed by the parent `LiveMap`'s `objectId`, with each value being the set of keys at which that `LiveMap` references this `LiveObject`. Used by `getFullPaths` ([RTLO4f](#RTLO4f)) to determine every path the object currently occupies in the LiveObjects tree
    - `(RTLO3f1)` This mapping is keyed by `objectId` for consistency with the rest of the LiveObjects spec, where references between objects are stored as `objectId`s and resolved via the `ObjectsPool` on demand. Implementations may store a direct reference to the parent `LiveMap` instead — for example to avoid an `ObjectsPool` lookup at each step of `getFullPaths` ([RTLO4f](#RTLO4f)) traversal — provided the observable behaviour is unchanged. Such implementations should be aware that this may introduce reference cycles between `LiveMap`s, and must ensure this does not cause memory leaks
    - `(RTLO3f2)` TODO: The detailed maintenance rules for `parentReferences` (across `MAP_SET`, `MAP_REMOVE`, `MAP_CLEAR`, `LiveMap` tombstoning, and post-sync rebuild) are to be specified by Sachin in a follow-up; see https://github.com/ably/specification/pull/480 for the in-progress draft
>>>>>>> origin/AIT-30/liveobjects-path-based-api-spec
- `(RTLO4)` `LiveObject` methods:
  - `(RTLO4b)` `subscribe` - subscribes a user to data updates on this `LiveObject` instance
    - `(RTLO4b1)` Requires the `OBJECT_SUBSCRIBE` channel mode to be granted per [RTO2](#RTO2)
    - `(RTLO4b2)` If the channel is in the `DETACHED` or `FAILED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
    - `(RTLO4b3)` A user may provide a listener to subscribe to data updates on this `LiveObject` instance
    - `(RTLO4b4)` An update to `LiveObject` data is communicated by internally emitting a `LiveObjectUpdate` object for this `LiveObject`, or in any other platform-appropriate manner:
      - `(RTLO4b4a)` `LiveObjectUpdate.update` contains the specific information about what was changed on the object. The exact type depends on the object type
      - `(RTLO4b4b)` The `LiveObjectUpdate.noop` internal property can be used to indicate that the update was a no-op
      - `(RTLO4b4d)` `LiveObjectUpdate.objectMessage` is an optional `ObjectMessage` - the source `ObjectMessage` that caused this update, if any
      - `(RTLO4b4c)` When a `LiveObjectUpdate` is emitted:
        - `(RTLO4b4c1)` If `LiveObjectUpdate` is indicated to be a no-op, do nothing
        - `(RTLO4b4c2)` This clause has been replaced by [RTLO4b4c3](#RTLO4b4c3) as of specification version 6.0.0.
        - `(RTLO4b4c3)` Otherwise:
          - `(RTLO4b4c3a)` The registered listener of each subscription created via `LiveObject#subscribe` ([RTLO4b](#RTLO4b)) on this `LiveObject` is called with the `LiveObjectUpdate`
          - `(RTLO4b4c3b)` Perform path-based subscription dispatch as described in [RTO24b](#RTO24b), passing this `LiveObject` and the `LiveObjectUpdate`
          - `(RTLO4b4c3c)` When a `LiveObjectUpdate` is emitted as a result of a tombstone - i.e. an `OBJECT_DELETE` operation or a sync state with `tombstone: true`, after all listeners have been invoked from [RTLO4b4c3a](#RTLO4b4c3a) and [RTLO4b4c3b](#RTLO4b4c3b), the library MUST deregister all listeners on this `LiveObject`. Path-based subscriptions ([RTPO19](#RTPO19)) are NOT affected by `tombstone` update.
    - `(RTLO4b5)` This clause has been replaced by [RTLO4b7](#RTLO4b7)
      - `(RTLO4b5a)` This clause has been replaced by [RTLO4b7](#RTLO4b7)
      - `(RTLO4b5b)` This clause has been replaced by [RTLO4b7](#RTLO4b7)
    - `(RTLO4b7)` Returns a [`Subscription`](../features#SUB1) object
    - `(RTLO4b6)` This operation must not have any side effects on `RealtimeObject`, the underlying channel, or their status
  - `(RTLO4c)` This clause has been deleted
    - `(RTLO4c1)` This clause has been deleted
    - `(RTLO4c2)` This clause has been deleted
    - `(RTLO4c3)` This clause has been deleted
    - `(RTLO4c4)` This clause has been deleted
  - `(RTLO4a)` protected `canApplyOperation` - a convenience method used to determine whether the `ObjectMessage.operation` should be applied to this object based on a serial value
    - `(RTLO4a1)` Expects the following arguments:
      - `(RTLO4a1a)` `ObjectMessage`
    - `(RTLO4a2)` Returns a boolean indicating whether the operation should be applied to this object
    - `(RTLO4a3)` Both `ObjectMessage.serial` and `ObjectMessage.siteCode` must be non-empty strings. Otherwise, log a warning that the object operation message has invalid serial values. The client library must not apply this operation to the object
    - `(RTLO4a4)` Get the `siteSerial` value stored for this `LiveObject` in the `siteTimeserials` map using the key `ObjectMessage.siteCode`
    - `(RTLO4a5)` If the `siteSerial` for this `LiveObject` is null or an empty string, return true
    - `(RTLO4a6)` If the `siteSerial` for this `LiveObject` is not an empty string, return true if `ObjectMessage.serial` is greater than `siteSerial` when compared lexicographically
  - `(RTLO4f)` internal `addParentReference(parent, key)` method - records that the `LiveMap` `parent` references this `LiveObject` at `key`
    - `(RTLO4f1)` If `parent` is already present in `parentReferences`, `key` MUST be added to the existing set associated with `parent`
    - `(RTLO4f2)` Otherwise, a new entry MUST be inserted into `parentReferences` for `parent` with a set containing only `key`
  - `(RTLO4g)` internal `removeParentReference(parent, key)` method - removes the recorded reference from `parent` at `key`
    - `(RTLO4g1)` If `parent` is not present in `parentReferences`, the call MUST be a no-op
    - `(RTLO4g2)` Otherwise, `key` MUST be removed from the set associated with `parent`
    - `(RTLO4g3)` If, as a result of [RTLO4g2](#RTLO4g2), the set associated with `parent` is empty, the `parent` entry MUST be removed from `parentReferences`
  - `(RTLO4e)` protected `tombstone` - a convenience method used to tombstone this `LiveObject`. The realtime system reserves the right to tombstone an object (i.e. mark it for deletion from the objects pool) by publishing an `OBJECT_DELETE` operation at any time if the object is orphaned (not a descendant of the root object) or remains uninitialized (no `*_CREATE` operation has been received) for an extended period. Only the realtime system may publish an `OBJECT_DELETE` operation; clients must never send it. This method describes the steps the client library must take when it needs to tombstone an object locally. Eventually, tombstoned objects will be garbage collected following the procedure described in [RTO10](#RTO10)
    - `(RTLO4e1)` Expects the following arguments:
      - `(RTLO4e1a)` `ObjectMessage`
    - `(RTLO4e2)` Set `LiveObject.isTombstone` to `true`
    - `(RTLO4e3)` Set `LiveObject.tombstonedAt` to the value calculated per [RTLO6](#RTLO6), using `ObjectMessage.serialTimestamp`
      - `(RTLO4e3a)` This clause has been replaced by [RTLO6a](#RTLO6a)
      - `(RTLO4e3b)` This clause has been replaced by [RTLO6b](#RTLO6b)
        - `(RTLO4e3b1)` This clause has been replaced by [RTLO6b1](#RTLO6b1)
    - `(RTLO4e5)` If the current `LiveObject` is of type `LiveMap`, then before [RTLO4e4](#RTLO4e4) is applied, do following:
      - `(RTLO4e5a)` For each iterated `entry` in current `LiveMap`'s private `data`:
        - `(RTLO4e5a1)` If `entry.value.data` have `objectId` as a field, retrieve corresponding child `LiveObject` from `ObjectsPool` using given `objectId`
        - `(RTLO4e5a2)` If child `LiveObject` exists, call its `removeParentReference(parent, key)` method per [RTLO4g](#RTLO4g), passing current `LiveMap` as `parent` and the iterated `entry.value` as `key`
    - `(RTLO4e4)` Set the data for the `LiveObject` to a zero-value, as described in [RTLC4](#RTLC4) or [RTLM4](#RTLM4) depending on the object type
  - `(RTLO4f)` internal `getFullPaths` function - returns the list of distinct paths from the root `LiveMap` (objectId `root`) to this `LiveObject`, computed by traversing `parentReferences` upward. Each returned path is an ordered sequence of keys from `root` to this `LiveObject`.
    - `(RTLO4f1)` `getFullPaths` MUST be implemented as an enumeration of all *simple paths* from this `LiveObject` to the root `LiveMap` over the inverse of the `parentReferences` graph (i.e. walking child → parent). A *simple path* is a path along which no `LiveObject` appears more than once. This is the standard graph problem, typically solved by a depth-first traversal with path-local backtracking equivalent to NetworkX's `all_simple_paths`. Implementation should choose iterative DFS with explicit stack (easier to read and debugging).
    - `(RTLO4f2)` If this `LiveObject` is the root `LiveMap` (objectId `root`), the returned list MUST contain exactly one path, and that path MUST be empty (zero key segments). This makes the root reachable from itself via the empty key sequence
    - `(RTLO4f3)` If this `LiveObject` is not the root `LiveMap` and has no entries in its `parentReferences` at the time of the call (e.g. orphaned, or not yet reachable from root), the returned list MUST be empty
    - `(RTLO4f4)` While traversing paths, suppress cyclic paths whenever a sibling branch had already revisited the same node. Reference behaviour on cyclic graphs is given by NetworkX's `all_simple_paths`, which implementations MAY consult for worked examples
    - `(RTLO4f5)` When a single parent `LiveMap` references this `LiveObject` at multiple keys, the returned list MUST contain one distinct path per such key, each ending at the corresponding key
    - `(RTLO4f6)` When this `LiveObject` is reachable via multiple distinct ancestor paths (either because it has multiple parents in `parentReferences`, or because any ancestor on the way to root itself has multiple paths to root), the returned list MUST contain one path per distinct ancestor path
    - `(RTLO4f7)` The order of paths in the returned list is not mandatory. Implementations MAY return paths in any order; callers requiring a stable order MUST sort the result themselves
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
  - `(RTLC12g)` Publishes the `ObjectMessage` from [RTLC12e](#RTLC12e) using `RealtimeObject#publishAndApply` ([RTO20](#RTO20)), passing the `ObjectMessage` as a single element in the array
- `(RTLC13)` `LiveCounter#decrement` function:
  - `(RTLC13a)` Expects the following arguments:
    - `(RTLC13a1)` `amount` `Number` - the amount by which to decrement the counter value
  - `(RTLC13b)` This is an alias for calling [`LiveCounter#increment`](#RTLC12) with a negative `amount` and must be implemented with the same behavior
  - `(RTLC13c)` If the client library chooses to delegate to `LiveCounter#increment` with a negated `amount`, then in languages where negating a non-number may result in implicit type coercion, the `amount` argument must first be validated as described in [RTLC12e1](#RTLC12e1) before proceeding
- `(RTLC6)` `LiveCounter`'s internal `data` can be replaced with the `ObjectState` from a provided `ObjectMessage` (which the caller must ensure has its `object` field populated; let `ObjectState` refer to `ObjectMessage.object`) in the following way:
  - `(RTLC6a)` Replace the private `siteTimeserials` of the `LiveCounter` with the value from `ObjectState.siteTimeserials`
  - `(RTLC6e)` If `LiveCounter.isTombstone` is `true`, finish processing the `ObjectState`
    - `(RTLC6e1)` Return a `LiveCounterUpdate` object with `LiveCounterUpdate.noop` set to `true`, indicating that no update was made to the object
  - `(RTLC6f)` If `ObjectState.tombstone` is `true`, tombstone the current `LiveCounter` using [`LiveObject.tombstone`](#RTLO4e), passing in the `ObjectMessage`. Finish processing the `ObjectState`
    - `(RTLC6f1)` Return a `LiveCounterUpdate` object with `LiveCounterUpdate.update.amount` set to the negative `data` value that this `LiveCounter` had before being tombstoned, and `LiveCounterUpdate.objectMessage` set to the provided `ObjectMessage`
  - `(RTLC6g)` Store the current `data` value as `previousData` for use in [RTLC6h](#RTLC6h)
  - `(RTLC6b)` Set the private flag `createOperationIsMerged` to `false`
  - `(RTLC6c)` Set `data` to the value of `ObjectState.counter.count`, or to 0 if it does not exist
  - `(RTLC6d)` If `ObjectState.createOp` is present, merge the initial value into the `LiveCounter` as described in [RTLC16](#RTLC16), passing in the `ObjectState.createOp` instance and the `ObjectMessage`. Discard the `LiveCounterUpdate` object returned by the merge operation
    - `(RTLC6d1)` This clause has been replaced by [RTLC10a](#RTLC10a)
    - `(RTLC6d2)` This clause has been replaced by [RTLC10b](#RTLC10b)
  - `(RTLC6h)` Calculate the diff between `previousData` from [RTLC6g](#RTLC6g) and the current `data` per [RTLC14](#RTLC14), set `LiveCounterUpdate.objectMessage` on the resulting update to the provided `ObjectMessage`, and return the resulting `LiveCounterUpdate` object
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
    - `(RTLC7d1)` If `ObjectMessage.operation.action` is set to `COUNTER_CREATE`, apply the operation as described in [RTLC8](#RTLC8), passing in `ObjectMessage.operation` and `ObjectMessage`
      - `(RTLC7d1a)` Emit the `LiveCounterUpdate` object returned as a result of applying the operation
      - `(RTLC7d1b)` Return `true`
    - `(RTLC7d2)` This clause has been replaced by [RTLC7d5](#RTLC7d5) as of specification version 6.0.0.
      - `(RTLC7d2a)` This clause has been replaced by [RTLC7d5a](#RTLC7d5a) as of specification version 6.0.0.
      - `(RTLC7d2b)` This clause has been replaced by [RTLC7d5b](#RTLC7d5b) as of specification version 6.0.0.
    - `(RTLC7d5)` If `ObjectMessage.operation.action` is set to `COUNTER_INC`, apply the operation as described in [RTLC9](#RTLC9), passing in `ObjectMessage.operation.counterInc` and `ObjectMessage`
      - `(RTLC7d5a)` Emit the `LiveCounterUpdate` object returned as a result of applying the operation
      - `(RTLC7d5b)` Return `true`
    - `(RTLC7d4)` If `ObjectMessage.operation.action` is set to `OBJECT_DELETE`, apply the operation as described in [RTLO5](#RTLO5), passing in `ObjectMessage`
      - `(RTLC7d4a)` Emit a `LiveCounterUpdate` object after applying the `OBJECT_DELETE` operation, with `LiveCounterUpdate.update.amount` set to the negated value that this `LiveCounter` held before the operation was applied and `LiveCounterUpdate.objectMessage` set to `ObjectMessage`
      - `(RTLC7d4b)` Return `true`
    - `(RTLC7d3)` Otherwise, log a warning that an object operation message with an unsupported action has been received, and discard the current `ObjectMessage` without taking any further action. No data update event is emitted. Return `false`
- `(RTLC8)` A `COUNTER_CREATE` operation can be applied to a `LiveCounter` in the following way:
  - `(RTLC8a)` Expects the following arguments:
    - `(RTLC8a1)` `ObjectOperation`
    - `(RTLC8a2)` `ObjectMessage` - the source `ObjectMessage` that contains the operation
  - `(RTLC8d)` The return type is a `LiveCounterUpdate` object, which indicates the data update for this `LiveCounter`
  - `(RTLC8b)` If the private flag `createOperationIsMerged` is `true`, log a debug or trace message indicating that the operation will not be applied because a `COUNTER_CREATE` operation has already been applied to this `LiveCounter`. Discard the operation without taking any further action, and return a `LiveCounterUpdate` object with `LiveCounterUpdate.noop` set to `true`, indicating that no update was made to the object
  - `(RTLC8c)` Otherwise merge the initial value into the `LiveCounter` as described in [RTLC16](#RTLC16), passing in the `ObjectOperation` instance and the `ObjectMessage`
  - `(RTLC8e)` Return the `LiveCounterUpdate` object returned by [RTLC16](#RTLC16)
- `(RTLC9)` A `COUNTER_INC` operation can be applied to a `LiveCounter` in the following way:
  - `(RTLC9a)` Expects the following arguments:
    - `(RTLC9a1)` This clause has been replaced by [RTLC9a2](#RTLC9a2) as of specification version 6.0.0.
    - `(RTLC9a2)` `CounterInc`
    - `(RTLC9a3)` `ObjectMessage` - the source `ObjectMessage` that contains the operation
  - `(RTLC9c)` The return type is a `LiveCounterUpdate` object, which indicates the data update for this `LiveCounter`
  - `(RTLC9b)` This clause has been replaced by [RTLC9f](#RTLC9f) as of specification version 6.0.0.
  - `(RTLC9d)` This clause has been replaced by [RTLC9g](#RTLC9g) as of specification version 6.0.0.
  - `(RTLC9e)` This clause has been replaced by [RTLC9h](#RTLC9h) as of specification version 6.0.0.
  - `(RTLC9f)` Add `CounterInc.number` to `data`, if it exists
  - `(RTLC9g)` If `CounterInc.number` exists, return a `LiveCounterUpdate` object with `LiveCounterUpdate.update.amount` set to `CounterInc.number` and `LiveCounterUpdate.objectMessage` set to the provided `ObjectMessage`
  - `(RTLC9h)` If `CounterInc.number` does not exist, return a `LiveCounterUpdate` object with `LiveCounterUpdate.noop` set to `true`
- `(RTLC10)` This clause has been replaced by [RTLC16](#RTLC16) as of specification version 6.0.0.
  - `(RTLC10a)` This clause has been replaced by [RTLC16a](#RTLC16a) as of specification version 6.0.0.
  - `(RTLC10b)` This clause has been replaced by [RTLC16b](#RTLC16b) as of specification version 6.0.0.
  - `(RTLC10c)` This clause has been replaced by [RTLC16c](#RTLC16c) as of specification version 6.0.0.
  - `(RTLC10d)` This clause has been replaced by [RTLC16d](#RTLC16d) as of specification version 6.0.0.
- `(RTLC16)` The initial value from an `ObjectOperation` can be merged into this `LiveCounter` in the following way. Expects an `ObjectOperation` and an `ObjectMessage` (the source `ObjectMessage` that contains the operation) as arguments. Let `counterCreate` be `ObjectOperation.counterCreate` if present, else the `CounterCreate` from which `ObjectOperation.counterCreateWithObjectId` was derived (see [RTLCV4g5](#RTLCV4g5)):
  - `(RTLC16a)` Add `counterCreate.count` to `data`, if it exists
  - `(RTLC16b)` Set the private flag `createOperationIsMerged` to `true`
  - `(RTLC16c)` If `counterCreate.count` exists, return a `LiveCounterUpdate` object with `LiveCounterUpdate.update.amount` set to `counterCreate.count` and `LiveCounterUpdate.objectMessage` set to the provided `ObjectMessage`
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
    - `(RTLM20a2)` This clause has been replaced by [RTLM20a3](#RTLM20a3).
    - `(RTLM20a3)` `value` `Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounterValueType | LiveMapValueType` - the value to assign to the key
  - `(RTLM20b)` Requires the `OBJECT_PUBLISH` channel mode to be granted per [RTO2](#RTO2)
  - `(RTLM20c)` If the channel is in the `DETACHED`, `FAILED` or `SUSPENDED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
  - `(RTLM20d)` If [`echoMessages`](../features#TO3h) client option is `false`, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40000, indicating that `echoMessages` must be enabled for this operation
  - `(RTLM20e)` Creates an `ObjectMessage` for a `MAP_SET` action in the following way:
    - `(RTLM20e1)` Validates the provided `key` and `value` in a similar way as described in [RTLMV4b](#RTLMV4b) and [RTLMV4c](#RTLMV4c)
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
      - `(RTLM20e7a)` This clause has been replaced by [RTLM20e7g](#RTLM20e7g).
      - `(RTLM20e7g)` If the `value` is of type `LiveCounterValueType` or `LiveMapValueType`:
        - `(RTLM20e7g1)` Evaluate the value type per [RTLCV4](#RTLCV4) or [RTLMV4](#RTLMV4) respectively. Collect all generated `ObjectMessages` into an ordered list — for [RTLCV4](#RTLCV4) the list contains the single returned `ObjectMessage`; for [RTLMV4](#RTLMV4) the list is the returned array
        - `(RTLM20e7g2)` Set `ObjectMessage.operation.mapSet.value.objectId` to the `objectId` from the final `ObjectMessage` in the list gathered in [`RTLM20e7g1`](#RTLM20e7g1)
      - `(RTLM20e7b)` If the `value` is of type `JsonArray` or `JsonObject`, set `ObjectMessage.operation.mapSet.value.json` to that value
      - `(RTLM20e7c)` If the `value` is of type `String`, set `ObjectMessage.operation.mapSet.value.string` to that value
      - `(RTLM20e7d)` If the `value` is of type `Number`, set `ObjectMessage.operation.mapSet.value.number` to that value
      - `(RTLM20e7e)` If the `value` is of type `Boolean`, set `ObjectMessage.operation.mapSet.value.boolean` to that value
      - `(RTLM20e7f)` If the `value` is of type `Binary`, set `ObjectMessage.operation.mapSet.value.bytes` to that value
  - `(RTLM20f)` This clause has been replaced by [RTLM20g](#RTLM20g)
  - `(RTLM20g)` This clause has been replaced by [RTLM20h](#RTLM20h).
  - `(RTLM20h)` Publishes all `ObjectMessages` using `RealtimeObject#publishAndApply` ([RTO20](#RTO20)):
    - `(RTLM20h1)` If the `value` is of type `LiveCounterValueType` or `LiveMapValueType`, the array contains the `*_CREATE` `ObjectMessages` collected in [RTLM20e7g1](#RTLM20e7g1) followed by the `MAP_SET` `ObjectMessage` from [RTLM20e](#RTLM20e)
    - `(RTLM20h2)` Otherwise, the `MAP_SET` `ObjectMessage` from [RTLM20e](#RTLM20e) is passed as a single element in the array
- `(RTLM21)` `LiveMap#remove` function:
  - `(RTLM21a)` Expects the following arguments:
    - `(RTLM21a1)` `key` `String` - the key to remove the value for
  - `(RTLM21b)` Requires the `OBJECT_PUBLISH` channel mode to be granted per [RTO2](#RTO2)
  - `(RTLM21c)` If the channel is in the `DETACHED`, `FAILED` or `SUSPENDED` state, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 90001
  - `(RTLM21d)` If [`echoMessages`](../features#TO3h) client option is `false`, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40000, indicating that `echoMessages` must be enabled for this operation
  - `(RTLM21e)` Creates an `ObjectMessage` for a `MAP_REMOVE` action in the following way:
    - `(RTLM21e1)` Validates the provided `key` in a similar way as described in [RTLMV4b](#RTLMV4b)
    - `(RTLM21e2)` Set `ObjectMessage.operation.action` to `ObjectOperationAction.MAP_REMOVE`
    - `(RTLM21e3)` Set `ObjectMessage.operation.objectId` to the Object ID of this `LiveMap`
    - `(RTLM21e4)` This clause has been replaced by [RTLM21e5](#RTLM21e5) as of specification version 6.0.0.
    - `(RTLM21e5)` Set `ObjectMessage.operation.mapRemove.key` to the provided `key` value
  - `(RTLM21f)` This clause has been replaced by [RTLM21g](#RTLM21g)
  - `(RTLM21g)` Publishes the `ObjectMessage` from [RTLM21e](#RTLM21e) using `RealtimeObject#publishAndApply` ([RTO20](#RTO20)), passing the `ObjectMessage` as a single element in the array
- `(RTLM14)` An `ObjectsMapEntry` in the internal `data` map can be checked for being tombstoned using the convenience method:
  - `(RTLM14a)` The method returns true if `ObjectsMapEntry.tombstone` is true
  - `(RTLM14c)` The method returns true if `ObjectsMapEntry.data.objectId` exists, there is an object in the local `ObjectsPool` with that id, and that `LiveObject.isTombstone` property is `true`
  - `(RTLM14b)` Otherwise, it returns false
- `(RTLM6)` `LiveMap` internal `data` can be replaced with the `ObjectState` from a provided `ObjectMessage` (which the caller must ensure has its `object` field populated; let `ObjectState` refer to `ObjectMessage.object`) in the following way:
  - `(RTLM6a)` Replace the private `siteTimeserials` of the `LiveMap` with the value from `ObjectState.siteTimeserials`
  - `(RTLM6e)` If `LiveMap.isTombstone` is `true`, finish processing the `ObjectState`
    - `(RTLM6e1)` Return a `LiveMapUpdate` object with `LiveMapUpdate.noop` set to `true`, indicating that no update was made to the object
  - `(RTLM6f)` If `ObjectState.tombstone` is `true`, tombstone the current `LiveMap` using [`LiveObject.tombstone`](#RTLO4e), passing in the `ObjectMessage`. Finish processing the `ObjectState`
    - `(RTLM6f1)` Return a `LiveMapUpdate` object with `LiveMapUpdate.update` consisting of entries for the keys that were removed as a result of the object being tombstoned, each set to `removed`, and `LiveMapUpdate.objectMessage` set to the provided `ObjectMessage`
  - `(RTLM6g)` Store the current `data` value as `previousData` for use in [RTLM6h](#RTLM6h)
  - `(RTLM6b)` Set the private flag `createOperationIsMerged` to `false`
  - `(RTLM6i)` Set the private `clearTimeserial` to `ObjectState.map.clearTimeserial`, or to `null` if not provided
  - `(RTLM6c)` Set `data` to `ObjectState.map.entries`, or to an empty map if it does not exist
    - `(RTLM6c1)` For each `ObjectsMapEntry` with `ObjectsMapEntry.tombstone` equal to `true`, additionally set the `ObjectsMapEntry.tombstonedAt` field to the value calculated per [RTLO6](#RTLO6), using `ObjectsMapEntry.serialTimestamp`
      - `(RTLM6c1a)` This clause has been replaced by [RTLO6a](#RTLO6a)
      - `(RTLM6c1b)` This clause has been replaced by [RTLO6b](#RTLO6b)
        - `(RTLM6c1b1)` This clause has been replaced by [RTLO6b1](#RTLO6b1)
  - `(RTLM6d)` If `ObjectState.createOp` is present, merge the initial value into the `LiveMap` as described in [RTLM23](#RTLM23), passing in the `ObjectState.createOp` instance and the `ObjectMessage`. Discard the `LiveMapUpdate` object returned by the merge operation
    - `(RTLM6d1)` This clause has been replaced by [RTLM17a](#RTLM17a)
      - `(RTLM6d1a)` This clause has been replaced by [RTLM17a1](#RTLM17a1)
      - `(RTLM6d1b)` This clause has been replaced by [RTLM17a2](#RTLM17a2)
    - `(RTLM6d2)` This clause has been replaced by [RTLM17b](#RTLM17b)
  - `(RTLM6h)` Calculate the diff between `previousData` from [RTLM6g](#RTLM6g) and the current `data` per [RTLM22](#RTLM22), set `LiveMapUpdate.objectMessage` on the resulting update to the provided `ObjectMessage`, and return the resulting `LiveMapUpdate` object
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
    - `(RTLM15d1)` If `ObjectMessage.operation.action` is set to `MAP_CREATE`, apply the operation as described in [RTLM16](#RTLM16), passing in `ObjectMessage.operation` and `ObjectMessage`
      - `(RTLM15d1a)` Emit the `LiveMapUpdate` object returned as a result of applying the operation
      - `(RTLM15d1b)` Return `true`
    - `(RTLM15d2)` This clause has been replaced by [RTLM15d6](#RTLM15d6) as of specification version 6.0.0.
      - `(RTLM15d2a)` This clause has been replaced by [RTLM15d6a](#RTLM15d6a) as of specification version 6.0.0.
      - `(RTLM15d2b)` This clause has been replaced by [RTLM15d6b](#RTLM15d6b) as of specification version 6.0.0.
    - `(RTLM15d6)` If `ObjectMessage.operation.action` is set to `MAP_SET`, apply the operation as described in [RTLM7](#RTLM7), passing in `ObjectMessage.operation.mapSet`, `ObjectMessage.serial`, and `ObjectMessage`
      - `(RTLM15d6a)` Emit the `LiveMapUpdate` object returned as a result of applying the operation
      - `(RTLM15d6b)` Return `true`
    - `(RTLM15d3)` This clause has been replaced by [RTLM15d7](#RTLM15d7) as of specification version 6.0.0.
      - `(RTLM15d3a)` This clause has been replaced by [RTLM15d7a](#RTLM15d7a) as of specification version 6.0.0.
      - `(RTLM15d3b)` This clause has been replaced by [RTLM15d7b](#RTLM15d7b) as of specification version 6.0.0.
    - `(RTLM15d7)` If `ObjectMessage.operation.action` is set to `MAP_REMOVE`, apply the operation as described in [RTLM8](#RTLM8), passing in `ObjectMessage.operation.mapRemove`, `ObjectMessage.serial`, `ObjectMessage.serialTimestamp`, and `ObjectMessage`
      - `(RTLM15d7a)` Emit the `LiveMapUpdate` object returned as a result of applying the operation
      - `(RTLM15d7b)` Return `true`
    - `(RTLM15d5)` If `ObjectMessage.operation.action` is set to `OBJECT_DELETE`, apply the operation as described in [RTLO5](#RTLO5), passing in `ObjectMessage`
      - `(RTLM15d5a)` Emit a `LiveMapUpdate` object with `LiveMapUpdate.update` consisting of entries for the keys that were removed as a result of applying the `OBJECT_DELETE` operation, each set to `removed`, and `LiveMapUpdate.objectMessage` set to `ObjectMessage`
      - `(RTLM15d5b)` Return `true`
    - `(RTLM15d8)` If `ObjectMessage.operation.action` is set to `MAP_CLEAR`, apply the operation as described in [RTLM24](#RTLM24), passing in `ObjectMessage.serial` and `ObjectMessage`
      - `(RTLM15d8a)` Emit the `LiveMapUpdate` object returned as a result of applying the operation
      - `(RTLM15d8b)` Return `true`
    - `(RTLM15d4)` Otherwise, log a warning that an object operation message with an unsupported action has been received, and discard the current `ObjectMessage` without taking any further action. No data update event is emitted. Return `false`
- `(RTLM16)` A `MAP_CREATE` operation can be applied to a `LiveMap` in the following way:
  - `(RTLM16a)` Expects the following arguments:
    - `(RTLM16a1)` `ObjectOperation`
    - `(RTLM16a2)` `ObjectMessage` - the source `ObjectMessage` that contains the operation
  - `(RTLM16e)` The return type is a `LiveMapUpdate` object, which indicates the data update for this `LiveMap`
  - `(RTLM16b)` If the private flag `createOperationIsMerged` is `true`, log a debug or trace message indicating that the operation will not be applied because a `MAP_CREATE` operation has already been applied to this `LiveMap`. Discard the operation without taking any further action, and return a `LiveMapUpdate` object with `LiveMapUpdate.noop` set to `true`, indicating that no update was made to the object
  - `(RTLM16c)` This clause has been deleted.
  - `(RTLM16d)` Otherwise merge the initial value into the `LiveMap` as described in [RTLM23](#RTLM23), passing in the `ObjectOperation` instance and the `ObjectMessage`
  - `(RTLM16f)` Return the `LiveMapUpdate` object returned by [RTLM23](#RTLM23)
- `(RTLM7)` A `MAP_SET` operation for a key can be applied to a `LiveMap` in the following way:
  - `(RTLM7d)` Expects the following arguments:
    - `(RTLM7d1)` This clause has been replaced by [RTLM7d3](#RTLM7d3) as of specification version 6.0.0.
    - `(RTLM7d3)` `MapSet`
    - `(RTLM7d2)` `serial` string - operation's serial value
    - `(RTLM7d4)` `ObjectMessage` - the source `ObjectMessage` that contains the operation
  - `(RTLM7e)` The return type is a `LiveMapUpdate` object, which indicates the data update for this `LiveMap`
  - `(RTLM7h)` If the private `clearTimeserial` is non-null, and the provided `serial` is null or the `clearTimeserial` is lexicographically greater than or equal to `serial`, discard the operation without taking any action. Return a `LiveMapUpdate` object with `LiveMapUpdate.noop` set to `true`, indicating that no update was made to the object
  - `(RTLM7a)` If an `ObjectsMapEntry` exists in the private `data` for the specified key:
    - `(RTLM7a1)` If the operation cannot be applied to the existing entry as per [RTLM9](#RTLM9), discard the operation without taking any action. Return a `LiveMapUpdate` object with `LiveMapUpdate.noop` set to `true`, indicating that no update was made to the object
    - `(RTLM7a3)` If the current `ObjectsMapEntry` is of type `LiveObject`, before [RTLM7a2](#RTLM7a2e) is applied, the parent reference recorded on existing `ObjectsMapEntry` MUST be removed:
      - `(RTLM7a3a)` To check `ObjectsMapEntry` is of type `LiveObject`, validate `ObjectsMapEntry.data` has a `objectId` field, retrieve corresponding `LiveObject` from `ObjectsPool` using given `objectId`
      - `(RTLM7a3b)` If `LiveObject` exists, call its `removeParentReference(parent, key)` method per [RTLO4g](#RTLO4g), passing this `LiveMap` as `parent` and the operation's key as `key`
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
  - `(RTLM7i)` A parent reference MUST be recorded on the `LiveObject` newly referenced by this entry (if any):
    - `(RTLM7i1)` If `MapSet.value.objectId` is not present, no action is required
    - `(RTLM7i2)` Otherwise, call `addParentReference(parent, key)` per [RTLO4f](#RTLO4f) on the `LiveObject` in the local `ObjectsPool` with `objectId` equal to `MapSet.value.objectId` (guaranteed to exist per [RTLM7g](#RTLM7g)), passing this `LiveMap` as `parent` and the operation's key as `key`
  - `(RTLM7f)` Return a `LiveMapUpdate` object with a `LiveMapUpdate.update` map containing the key used in this operation set to `updated`, and `LiveMapUpdate.objectMessage` set to the provided `ObjectMessage`
- `(RTLM8)` A `MAP_REMOVE` operation for a key can be applied to a `LiveMap` in the following way:
  - `(RTLM8c)` Expects the following arguments:
    - `(RTLM8c1)` This clause has been replaced by [RTLM8c4](#RTLM8c4) as of specification version 6.0.0.
    - `(RTLM8c4)` `MapRemove`
    - `(RTLM8c2)` `serial` string - operation's serial value
    - `(RTLM8c3)` `serialTimestamp` Time - operation's serial timestamp value
    - `(RTLM8c5)` `ObjectMessage` - the source `ObjectMessage` that contains the operation
  - `(RTLM8d)` The return type is a `LiveMapUpdate` object, which indicates the data update for this `LiveMap`
  - `(RTLM8g)` If the private `clearTimeserial` is non-null, and the provided `serial` is null or the `clearTimeserial` is lexicographically greater than or equal to `serial`, discard the operation without taking any action. Return a `LiveMapUpdate` object with `LiveMapUpdate.noop` set to `true`, indicating that no update was made to the object
  - `(RTLM8a)` If an `ObjectsMapEntry` exists in the private `data` for the specified key:
    - `(RTLM8a1)` If the operation cannot be applied to the existing entry as per [RTLM9](#RTLM9), discard the operation without taking any action. Return a `LiveMapUpdate` object with `LiveMapUpdate.noop` set to `true`, indicating that no update was made to the object
    - `(RTLM8a3)` If the current `ObjectsMapEntry` is of type `LiveObject`, before [RTLM8a2](#RTLM8a2) is applied, the parent reference recorded on existing `ObjectsMapEntry` MUST be removed:
      - `(RTLM8a3a)` To check `ObjectsMapEntry` is of type `LiveObject`, validate `ObjectsMapEntry.data` has a `objectId` field, retrieve corresponding `LiveObject` from `ObjectsPool` using given `objectId`
      - `(RTLM8a3b)` If `LiveObject` exists, call its `removeParentReference(parent, key)` method per [RTLO4g](#RTLO4g), passing this `LiveMap` as `parent` and the operation's key as `key`
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
  - `(RTLM8e)` Return a `LiveMapUpdate` object with a `LiveMapUpdate.update` map containing the key used in this operation set to `removed`, and `LiveMapUpdate.objectMessage` set to the provided `ObjectMessage`
- `(RTLM24)` A `MAP_CLEAR` operation can be applied to a `LiveMap` in the following way:
  - `(RTLM24a)` Expects the following arguments:
    - `(RTLM24a1)` `serial` string - the operation's serial value
    - `(RTLM24a2)` `ObjectMessage` - the source `ObjectMessage` that contains the operation
  - `(RTLM24b)` The return type is a `LiveMapUpdate` object, which indicates the data update for this `LiveMap`
  - `(RTLM24c)` If the private `clearTimeserial` is non-null and is lexicographically greater than the provided `serial`, discard the operation without taking any action. Return a `LiveMapUpdate` object with `LiveMapUpdate.noop` set to `true`, indicating that no update was made to the object
  - `(RTLM24d)` Set the private `clearTimeserial` to the provided `serial`
  - `(RTLM24e)` For each `ObjectsMapEntry` in the internal `data`:
    - `(RTLM24e1)` If `ObjectsMapEntry.timeserial` is null or omitted, or the `serial` is lexicographically greater than `ObjectsMapEntry.timeserial`:
      - `(RTLM24e1c)` If the current `ObjectsMapEntry` is of type `LiveObject`, the parent reference recorded on existing `ObjectsMapEntry` MUST be removed:
        - `(RTLM24e1c1)`  To check `ObjectsMapEntry` is of type `LiveObject`, validate `ObjectsMapEntry.data` has a `objectId` field, retrieve corresponding `LiveObject` from `ObjectsPool` using given `objectId`
        - `(RTLM24e1c2)` If `LiveObject` exists, call its `removeParentReference(parent, key)` method per [RTLO4g](#RTLO4g), passing this `LiveMap` as `parent` and the iterated entry key as `key`
      - `(RTLM24e1a)` Remove the entry from the internal `data` map. The entry is not retained as a tombstone.
      - `(RTLM24e1b)` Record the key for the `LiveMapUpdate` as `removed`
  - `(RTLM24f)` Return a `LiveMapUpdate` object with `LiveMapUpdate.update` containing each key recorded in [RTLM24e1b](#RTLM24e1b) set to `removed`, and `LiveMapUpdate.objectMessage` set to the provided `ObjectMessage`
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
- `(RTLM23)` The initial value from an `ObjectOperation` can be merged into this `LiveMap` in the following way. Expects an `ObjectOperation` and an `ObjectMessage` (the source `ObjectMessage` that contains the operation) as arguments. Let `mapCreate` be `ObjectOperation.mapCreate` if present, else the `MapCreate` from which `ObjectOperation.mapCreateWithObjectId` was derived (see [RTLMV4j5](#RTLMV4j5)):
  - `(RTLM23a)` For each key-`ObjectsMapEntry` pair in `mapCreate.entries`:
    - `(RTLM23a1)` If `ObjectsMapEntry.tombstone` is `false` or omitted, apply the `MAP_SET` operation to the current key as described in [RTLM7](#RTLM7), passing in `ObjectsMapEntry.data` and the current key as `MapSet`, `ObjectsMapEntry.timeserial` as `serial`, and the `ObjectMessage`. Store the returned `LiveMapUpdate` object for use in [RTLM23c](#RTLM23c)
    - `(RTLM23a2)` If `ObjectsMapEntry.tombstone` is `true`, apply the `MAP_REMOVE` operation to the current key as described in [RTLM8](#RTLM8), passing in the current key as `MapRemove`, `ObjectsMapEntry.timeserial` as `serial`, `ObjectsMapEntry.serialTimestamp` as `serialTimestamp`, and the `ObjectMessage`. Store the returned `LiveMapUpdate` object for use in [RTLM23c](#RTLM23c)
  - `(RTLM23b)` Set the private flag `createOperationIsMerged` to `true`
  - `(RTLM23c)` Return a single `LiveMapUpdate` object, where `LiveMapUpdate.update` is a merged map containing all key-value pairs from the `LiveMapUpdate.update` maps of the stored `LiveMapUpdate` objects (skipping any stored `LiveMapUpdate` objects marked as no-op), and `LiveMapUpdate.objectMessage` is set to the provided `ObjectMessage`
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

### LiveCounterValueType

A `LiveCounterValueType` is an immutable blueprint for creating a new `LiveCounter` object. It stores the desired initial count value and is evaluated when passed to a mutation method such as `LiveMap#set` ([RTLM20](#RTLM20)) or as an entry value in `LiveMapValueType.create` ([RTLMV3](#RTLMV3)).

- `(RTLCV1)` `LiveCounterValueType` is an immutable value type representing the intent to create a new `LiveCounter` with a specific initial count
- `(RTLCV2)` `LiveCounterValueType` has the following internal properties:
  - `(RTLCV2a)` `count` `Number` - the initial count value for the `LiveCounter` to be created
- `(RTLCV3)` `LiveCounterValueType.create` static factory function:
  - `(RTLCV3a)` Expects the following arguments:
    - `(RTLCV3a1)` `initialCount` `Number` (optional) - the initial count for the new `LiveCounter` object. Defaults to 0
  - `(RTLCV3b)` Returns a new `LiveCounterValueType` instance with the internal `count` set to the provided `initialCount` (or 0 if omitted)
  - `(RTLCV3c)` No input validation is performed at creation time. Validation is deferred to the evaluation procedure ([RTLCV4](#RTLCV4))
  - `(RTLCV3d)` The returned `LiveCounterValueType` is immutable and must not be modified after creation
- `(RTLCV4)` Internal evaluation procedure - when a `LiveCounterValueType` is evaluated by a mutation method (e.g. `LiveMap#set` or as an entry value during `LiveMapValueType` evaluation per [RTLMV4](#RTLMV4)), a `COUNTER_CREATE` `ObjectMessage` is generated as follows:
  - `(RTLCV4a)` If the internal `count` is not undefined and (is not of type `Number` or is not a finite number), the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40003, indicating that the counter value must be a valid number
  - `(RTLCV4b)` Create a `CounterCreate` object:
    - `(RTLCV4b1)` Set `CounterCreate.count` to the internal `count` value, or to 0 if undefined
  - `(RTLCV4c)` Create an initial value JSON string by generating a JSON string representation of the `CounterCreate` object
  - `(RTLCV4d)` Create a unique string nonce with 16+ characters
  - `(RTLCV4e)` Get the current server time as described in [RTO16](#RTO16)
  - `(RTLCV4f)` Create an `objectId` for the new `LiveCounter` as described in [RTO14](#RTO14), passing in `counter` as the `type`, the initial value JSON string from [RTLCV4c](#RTLCV4c), the nonce from [RTLCV4d](#RTLCV4d), and the server time from [RTLCV4e](#RTLCV4e)
  - `(RTLCV4g)` Create an `ObjectMessage` with:
    - `(RTLCV4g1)` `ObjectMessage.operation.action` set to `ObjectOperationAction.COUNTER_CREATE`
    - `(RTLCV4g2)` `ObjectMessage.operation.objectId` set to the `objectId` from [RTLCV4f](#RTLCV4f)
    - `(RTLCV4g3)` `ObjectMessage.operation.counterCreateWithObjectId.nonce` set to the nonce from [RTLCV4d](#RTLCV4d)
    - `(RTLCV4g4)` `ObjectMessage.operation.counterCreateWithObjectId.initialValue` set to the JSON string from [RTLCV4c](#RTLCV4c)
    - `(RTLCV4g5)` The client library must retain the `CounterCreate` object from [RTLCV4b](#RTLCV4b) alongside the `CounterCreateWithObjectId`. It is the operation from which the `CounterCreateWithObjectId` was derived, and is needed for message size calculation ([OOP4k2](../features#OOP4k2)) and local application of the operation ([RTLC16](#RTLC16)). This `CounterCreate` is for local use only and must not be sent over the wire.
  - `(RTLCV4h)` Return the `ObjectMessage`

### LiveMapValueType

A `LiveMapValueType` is an immutable blueprint for creating a new `LiveMap` object. It stores the desired initial entries and is evaluated when passed to a mutation method such as `LiveMap#set` ([RTLM20](#RTLM20)) or as an entry value in another `LiveMapValueType.create` ([RTLMV3](#RTLMV3)) call. Supports arbitrarily deep nesting of `LiveMapValueType` and `LiveCounterValueType` values within entries.

- `(RTLMV1)` `LiveMapValueType` is an immutable value type representing the intent to create a new `LiveMap` with specific initial entries
- `(RTLMV2)` `LiveMapValueType` has the following internal properties:
  - `(RTLMV2a)` `entries` `Dict<String, Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounterValueType | LiveMapValueType>` (optional) - the initial entries for the `LiveMap` to be created
- `(RTLMV3)` `LiveMapValueType.create` static factory function:
  - `(RTLMV3a)` Expects the following arguments:
    - `(RTLMV3a1)` `entries` `Dict<String, Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounterValueType | LiveMapValueType>` (optional) - the initial entries for the new `LiveMap` object
  - `(RTLMV3b)` Returns a new `LiveMapValueType` instance with the internal `entries` set to the provided `entries` (or undefined if omitted)
  - `(RTLMV3c)` No input validation is performed at creation time. Validation is deferred to the evaluation procedure ([RTLMV4](#RTLMV4))
  - `(RTLMV3d)` The returned `LiveMapValueType` is immutable and must not be modified after creation
- `(RTLMV4)` Internal evaluation procedure - when a `LiveMapValueType` is evaluated by a mutation method (e.g. `LiveMap#set` or as an entry value during another `LiveMapValueType` evaluation), `ObjectMessages` are generated as follows:
  - `(RTLMV4a)` If the internal `entries` is not undefined and (is null or is not of type `Dict`), the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40003, indicating that entries must be a `Dict`
  - `(RTLMV4b)` If any of the keys in the internal `entries` are not of type `String`, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40003, indicating that keys must be `String`
  - `(RTLMV4c)` If any of the values in the internal `entries` are not of an expected type, the library should throw an `ErrorInfo` error with `statusCode` 400 and `code` 40013, indicating that such data type is unsupported
  - `(RTLMV4d)` Build entries for the `MapCreate` object. For each key-value pair in the internal `entries` (if present), create an `ObjectsMapEntry` for the value:
    - `(RTLMV4d1)` If the value is of type `LiveCounterValueType`, evaluate it per [RTLCV4](#RTLCV4) to generate a `COUNTER_CREATE` `ObjectMessage`. Collect the generated `ObjectMessage` and set `ObjectsMapEntry.data.objectId` to the `objectId` from the `ObjectMessage`
    - `(RTLMV4d2)` If the value is of type `LiveMapValueType`, recursively evaluate it per [RTLMV4](#RTLMV4) to generate an ordered array of `ObjectMessages`. Collect all generated `ObjectMessages` and set `ObjectsMapEntry.data.objectId` to the `objectId` from the final `ObjectMessage` in the array
    - `(RTLMV4d3)` If the value is of type `JsonArray` or `JsonObject`, set `ObjectsMapEntry.data.json` to that value
    - `(RTLMV4d4)` If the value is of type `String`, set `ObjectsMapEntry.data.string` to that value
    - `(RTLMV4d5)` If the value is of type `Number`, set `ObjectsMapEntry.data.number` to that value
    - `(RTLMV4d6)` If the value is of type `Boolean`, set `ObjectsMapEntry.data.boolean` to that value
    - `(RTLMV4d7)` If the value is of type `Binary`, set `ObjectsMapEntry.data.bytes` to that value
  - `(RTLMV4e)` Create a `MapCreate` object:
    - `(RTLMV4e1)` Set `MapCreate.semantics` to `ObjectsMapSemantics.LWW`
    - `(RTLMV4e2)` Set `MapCreate.entries` to an empty map if the internal `entries` is undefined, otherwise to the entries built in [RTLMV4d](#RTLMV4d)
  - `(RTLMV4f)` Create an initial value JSON string based on the `MapCreate` object:
    - `(RTLMV4f1)` The `MapCreate` object may contain user-provided `ObjectData` that requires encoding. Encode the `ObjectData` values using the procedure described in [OD4](../features#OD4)
    - `(RTLMV4f2)` Return a JSON string representation of the encoded `MapCreate` object
  - `(RTLMV4g)` Create a unique string nonce with 16+ characters
  - `(RTLMV4h)` Get the current server time as described in [RTO16](#RTO16)
  - `(RTLMV4i)` Create an `objectId` for the new `LiveMap` as described in [RTO14](#RTO14), passing in `map` as the `type`, the initial value JSON string from [RTLMV4f](#RTLMV4f), the nonce from [RTLMV4g](#RTLMV4g), and the server time from [RTLMV4h](#RTLMV4h)
  - `(RTLMV4j)` Create an `ObjectMessage` with:
    - `(RTLMV4j1)` `ObjectMessage.operation.action` set to `ObjectOperationAction.MAP_CREATE`
    - `(RTLMV4j2)` `ObjectMessage.operation.objectId` set to the `objectId` from [RTLMV4i](#RTLMV4i)
    - `(RTLMV4j3)` `ObjectMessage.operation.mapCreateWithObjectId.nonce` set to the nonce from [RTLMV4g](#RTLMV4g)
    - `(RTLMV4j4)` `ObjectMessage.operation.mapCreateWithObjectId.initialValue` set to the JSON string from [RTLMV4f](#RTLMV4f)
    - `(RTLMV4j5)` The client library must retain the `MapCreate` object from [RTLMV4e](#RTLMV4e) alongside the `MapCreateWithObjectId`. It is the operation from which the `MapCreateWithObjectId` was derived, and is needed for message size calculation ([OOP4h2](../features#OOP4h2)) and local application of the operation ([RTLM23](#RTLM23)). This `MapCreate` is for local use only and must not be sent over the wire.
  - `(RTLMV4k)` Return an ordered array containing all `ObjectMessages` collected from nested value type evaluations in [RTLMV4d](#RTLMV4d) (in depth-first order), followed by the `MAP_CREATE` `ObjectMessage` from [RTLMV4j](#RTLMV4j)

### PathObject

A `PathObject` is a lazy, path-based reference into the LiveObjects tree. It stores a path (as an ordered list of string segments) from the root `LiveMap` and resolves it at the time each method is called. This means a `PathObject` survives object replacements: if the object at a given path changes (e.g. via a `MAP_SET` operation), the same `PathObject` will resolve to the new object on subsequent calls.

A `PathObject` is obtained from `RealtimeObject#get` ([RTO23](#RTO23)), which returns a `PathObject` rooted at the channel's root `LiveMap` with an empty path. Further `PathObjects` are obtained by navigating with `PathObject#get` or `PathObject#at`.

- `(RTPO1)` The `PathObject` class provides a path-based view over the LiveObjects tree
  - `(RTPO1a)` A specific SDK implementation may choose to expose a subset of the methods available on the `PathObject` class based on the expected type at the path. For example, when the user provides a type structure as a generic type parameter to `RealtimeObject#get`, the SDK may use type-specific class names (e.g. `LiveMapPathObject`, `LiveCounterPathObject`, `PrimitivePathObject`) that only expose the methods applicable to that type. The specification describes the general `PathObject` class with the full set of methods
- `(RTPO2)` `PathObject` has the following internal properties:
  - `(RTPO2a)` `path` - an ordered list of string segments representing the path from the root `LiveMap` to this position in the tree
  - `(RTPO2b)` `root` - a reference to the root `LiveMap` instance from the internal `ObjectsPool`
- `(RTPO3)` Internal path resolution procedure - resolves the stored `path` against the LiveObjects tree:
  - `(RTPO3a)` Starting from `root`, walk through the path segments in order. For each segment:
    - `(RTPO3a1)` The current object must be a `LiveMap`. If it is not, the resolution has failed
    - `(RTPO3a2)` Look up the segment as a key in the current `LiveMap` using `LiveMap#get` ([RTLM5](#RTLM5)). If the result is undefined/null, the resolution has failed
    - `(RTPO3a3)` The result becomes the current object for the next segment
  - `(RTPO3b)` If the path is empty, the result is the `root` `LiveMap` itself
  - `(RTPO3c)` On resolution failure:
    - `(RTPO3c1)` For read operations (`value`, `instance`, `entries`, `keys`, `values`, `size`, `compact`, `compactJson`), return undefined/null. The client library may log a debug or trace message
    - `(RTPO3c2)` For write operations (`set`, `remove`, `increment`, `decrement`), the library must throw an `ErrorInfo` error with `statusCode` 400 and `code` 92005, indicating that the path could not be resolved
- `(RTPO4)` `PathObject#path` function:
  - `(RTPO4a)` Returns a dot-delimited string representation of the stored path segments
  - `(RTPO4b)` Any dot characters (`.`) occurring within individual path segments must be escaped with a backslash (`\`) in the returned string. For example, a path with segments `["a", "b.c", "d"]` is represented as `a.b\.c.d`
  - `(RTPO4c)` An empty path (root `PathObject`) returns an empty string
- `(RTPO5)` `PathObject#get` function:
  - `(RTPO5a)` Expects the following arguments:
    - `(RTPO5a1)` `key` `String` - the key to navigate to
  - `(RTPO5b)` If `key` is not of type `String`, the library must throw an `ErrorInfo` error with `statusCode` 400 and `code` 40003, indicating that the key must be a `String`
  - `(RTPO5c)` Returns a new `PathObject` with the same `root` and with `key` appended to the current `path` segments
  - `(RTPO5d)` This is purely navigational and does not resolve the path or access any `LiveObject` data
- `(RTPO6)` `PathObject#at` function:
  - `(RTPO6a)` Expects the following arguments:
    - `(RTPO6a1)` `path` `String` - a dot-delimited path string
  - `(RTPO6b)` Parses the dot-delimited `path` string into individual segments, respecting backslash-escaped dots (a `\.` sequence is treated as a literal dot within a segment, not a separator)
  - `(RTPO6c)` Returns a new `PathObject` with the same `root` and with the parsed segments appended to the current `path` segments
  - `(RTPO6d)` This is a convenience for chaining multiple `PathObject#get` calls. For example, `pathObject.at("a.b.c")` is equivalent to `pathObject.get("a").get("b").get("c")`
- `(RTPO7)` `PathObject#value` function:
  - `(RTPO7a)` Resolves the path using the path resolution procedure ([RTPO3](#RTPO3))
  - `(RTPO7b)` If the resolved value is a `LiveCounter`, delegates to `LiveCounter#value` ([RTLC5](#RTLC5))
  - `(RTPO7c)` If the resolved value is a primitive (`Boolean`, `Binary`, `Number`, `String`, `JsonArray`, `JsonObject`), returns the value directly
  - `(RTPO7d)` If the resolved value is a `LiveMap`, returns undefined/null
  - `(RTPO7e)` If path resolution fails, returns undefined/null per [RTPO3c1](#RTPO3c1)
- `(RTPO8)` `PathObject#instance` function:
  - `(RTPO8a)` Resolves the path using the path resolution procedure ([RTPO3](#RTPO3))
  - `(RTPO8b)` If the resolved value is a `LiveObject` (i.e. a `LiveMap` or `LiveCounter`), returns a new `Instance` ([RTINS1](#RTINS1)) wrapping that `LiveObject`
  - `(RTPO8c)` If the resolved value is a primitive, returns undefined/null
  - `(RTPO8d)` If path resolution fails, returns undefined/null per [RTPO3c1](#RTPO3c1)
- `(RTPO9)` `PathObject#entries` function:
  - `(RTPO9a)` Resolves the path using the path resolution procedure ([RTPO3](#RTPO3))
  - `(RTPO9b)` If the resolved value is a `LiveMap`, delegates to `LiveMap#keys` ([RTLM12](#RTLM12)) and returns an array of `[key, PathObject]` pairs, where each `PathObject` is created as if by calling `PathObject#get` with the corresponding key on this `PathObject`
  - `(RTPO9c)` If the resolved value is not a `LiveMap`, or if path resolution fails, returns an empty array
- `(RTPO10)` `PathObject#keys` function:
  - `(RTPO10a)` Resolves the path using the path resolution procedure ([RTPO3](#RTPO3))
  - `(RTPO10b)` If the resolved value is a `LiveMap`, delegates to `LiveMap#keys` ([RTLM12](#RTLM12))
  - `(RTPO10c)` If the resolved value is not a `LiveMap`, or if path resolution fails, returns an empty array
- `(RTPO11)` `PathObject#values` function:
  - `(RTPO11a)` Resolves the path using the path resolution procedure ([RTPO3](#RTPO3))
  - `(RTPO11b)` If the resolved value is a `LiveMap`, delegates to `LiveMap#keys` ([RTLM12](#RTLM12)) and returns an array of `PathObject`s, where each `PathObject` is created as if by calling `PathObject#get` with the corresponding key on this `PathObject`
  - `(RTPO11c)` If the resolved value is not a `LiveMap`, or if path resolution fails, returns an empty array
- `(RTPO12)` `PathObject#size` function:
  - `(RTPO12a)` Resolves the path using the path resolution procedure ([RTPO3](#RTPO3))
  - `(RTPO12b)` If the resolved value is a `LiveMap`, delegates to `LiveMap#size` ([RTLM10](#RTLM10))
  - `(RTPO12c)` If the resolved value is not a `LiveMap`, or if path resolution fails, returns undefined/null
- `(RTPO13)` `PathObject#compact` function:
  - `(RTPO13a)` Resolves the path using the path resolution procedure ([RTPO3](#RTPO3))
  - `(RTPO13b)` If the resolved value is a `LiveMap`, returns a recursively compacted representation as a plain key-value object:
    - `(RTPO13b1)` Each entry in the `LiveMap` is included in the result. Tombstoned entries are excluded
    - `(RTPO13b2)` Nested `LiveMap` values are recursively compacted into nested plain key-value objects
    - `(RTPO13b3)` Nested `LiveCounter` values are resolved to their numeric value
    - `(RTPO13b4)` Primitive values (`Boolean`, `Binary`, `Number`, `String`, `JsonArray`, `JsonObject`) are included as-is
    - `(RTPO13b5)` Cyclic references (a `LiveMap` that has already been visited during this compaction) are represented by reusing the same in-memory object reference to the already-compacted result for that `LiveMap`
  - `(RTPO13c)` If the resolved value is a `LiveCounter`, returns its current numeric value (equivalent to `PathObject#value`)
  - `(RTPO13d)` If the resolved value is a primitive, returns the value directly (equivalent to `PathObject#value`)
  - `(RTPO13e)` If path resolution fails, returns undefined/null per [RTPO3c1](#RTPO3c1)
- `(RTPO14)` `PathObject#compactJson` function:
  - `(RTPO14a)` Behaves identically to `PathObject#compact` ([RTPO13](#RTPO13)) except for the following differences, which ensure the result is JSON-serializable:
    - `(RTPO14a1)` `Binary` values are encoded as base64 strings instead of being included as-is
    - `(RTPO14a2)` Cyclic references are represented as an object with a single `objectId` property containing the Object ID of the referenced `LiveMap`, instead of reusing the in-memory object reference
- `(RTPO15)` `PathObject#set` function:
  - `(RTPO15a)` Expects the following arguments:
    - `(RTPO15a1)` `key` `String` - the key to set the value for
    - `(RTPO15a2)` `value` - the value to assign to the key. Accepted types are the same as for `LiveMap#set` ([RTLM20](#RTLM20))
  - `(RTPO15b)` Resolves the path using the path resolution procedure ([RTPO3](#RTPO3)). On failure, throws per [RTPO3c2](#RTPO3c2)
  - `(RTPO15c)` If the resolved value is a `LiveMap`, delegates to `LiveMap#set` ([RTLM20](#RTLM20)) with the provided `key` and `value`
  - `(RTPO15d)` If the resolved value is not a `LiveMap`, the library must throw an `ErrorInfo` error with `statusCode` 400 and `code` 92007, indicating that the operation is not supported for the resolved object type
- `(RTPO16)` `PathObject#remove` function:
  - `(RTPO16a)` Expects the following arguments:
    - `(RTPO16a1)` `key` `String` - the key to remove the value for
  - `(RTPO16b)` Resolves the path using the path resolution procedure ([RTPO3](#RTPO3)). On failure, throws per [RTPO3c2](#RTPO3c2)
  - `(RTPO16c)` If the resolved value is a `LiveMap`, delegates to `LiveMap#remove` ([RTLM21](#RTLM21)) with the provided `key`
  - `(RTPO16d)` If the resolved value is not a `LiveMap`, the library must throw an `ErrorInfo` error with `statusCode` 400 and `code` 92007
- `(RTPO17)` `PathObject#increment` function:
  - `(RTPO17a)` Expects the following arguments:
    - `(RTPO17a1)` `amount` `Number` (optional) - the amount by which to increment the counter value. Defaults to 1
  - `(RTPO17b)` Resolves the path using the path resolution procedure ([RTPO3](#RTPO3)). On failure, throws per [RTPO3c2](#RTPO3c2)
  - `(RTPO17c)` If the resolved value is a `LiveCounter`, delegates to `LiveCounter#increment` ([RTLC12](#RTLC12)) with the provided `amount`
  - `(RTPO17d)` If the resolved value is not a `LiveCounter`, the library must throw an `ErrorInfo` error with `statusCode` 400 and `code` 92007
- `(RTPO18)` `PathObject#decrement` function:
  - `(RTPO18a)` Expects the following arguments:
    - `(RTPO18a1)` `amount` `Number` (optional) - the amount by which to decrement the counter value. Defaults to 1
  - `(RTPO18b)` Resolves the path using the path resolution procedure ([RTPO3](#RTPO3)). On failure, throws per [RTPO3c2](#RTPO3c2)
  - `(RTPO18c)` If the resolved value is a `LiveCounter`, delegates to `LiveCounter#decrement` ([RTLC13](#RTLC13)) with the provided `amount`
  - `(RTPO18d)` If the resolved value is not a `LiveCounter`, the library must throw an `ErrorInfo` error with `statusCode` 400 and `code` 92007
- `(RTPO19)` `PathObject#subscribe` function:
  - `(RTPO19a)` Expects the following arguments:
    - `(RTPO19a1)` `listener` - a callback function that receives a `PathObjectSubscriptionEvent` ([RTPO19d](#RTPO19d))
    - `(RTPO19a2)` `options` `PathObjectSubscriptionOptions` (optional) - subscription options
  - `(RTPO19b)` `PathObjectSubscriptionOptions` has the following properties:
    - `(RTPO19b1)` `depth` `Number` (optional) - controls how many levels deep in the subtree changes trigger the listener. Defaults to undefined/null. The `depth` value is interpreted by the subscription coverage rule in [RTO24c1](#RTO24c1); see [RTO24c2](#RTO24c2) for worked examples
      - `(RTPO19b1a)` If `depth` is provided and is not a positive integer, the library must throw an `ErrorInfo` error with `statusCode` 400 and `code` 40003
  - `(RTPO19c)` Returns a [`Subscription`](../features#SUB1) object
  - `(RTPO19d)` The listener receives a `PathObjectSubscriptionEvent` object with:
    - `(RTPO19d1)` `object` - a `PathObject` pointing to the path where the change occurred
    - `(RTPO19d2)` `message` `PublicAPI::ObjectMessage` (optional) - if `LiveObjectUpdate.objectMessage` from the [RTLO4b4](#RTLO4b4) emission that triggered this event is populated and its `operation` field is populated, a `PublicAPI::ObjectMessage` ([PAOM1](#PAOM1)) derived from it per [PAOM3](#PAOM3); otherwise omitted
  - `(RTPO19e)` Adds a subscription to the `RealtimeObject`'s `PathObjectSubscriptionRegister` ([RTO24](#RTO24)) with subscribed path equal to this `PathObject`'s `path` (per [RTPO2a](#RTPO2a)), the provided `listener`, and the provided `options.depth`
  - `(RTPO19f)` This operation must not have any side effects on `RealtimeObject`, the underlying channel, or their status

### Instance

An `Instance` holds a direct reference to a specific resolved `LiveObject` or primitive value. Unlike `PathObject` which is path-addressed and re-resolves on each call, `Instance` is identity-addressed: it follows the specific object it was created with, regardless of where that object sits in the tree.

- `(RTINS1)` The `Instance` class provides a direct-reference view of a `LiveObject` or primitive value
  - `(RTINS1a)` A specific SDK implementation may choose to expose a subset of the methods available on the `Instance` class based on the known underlying type. For example, the SDK may use type-specific class names (e.g. `LiveMapInstance`, `LiveCounterInstance`, `PrimitiveInstance`) that only expose the methods applicable to the wrapped type. The specification describes the general `Instance` class with the full set of methods
- `(RTINS2)` `Instance` has the following internal properties:
  - `(RTINS2a)` `value` - a reference to the wrapped `LiveObject` or primitive value
- `(RTINS3)` `Instance#id` property:
  - `(RTINS3a)` If the wrapped value is a `LiveObject`, returns the `objectId` of that object
  - `(RTINS3b)` If the wrapped value is a primitive, returns undefined/null
- `(RTINS4)` `Instance#value` function:
  - `(RTINS4a)` If the wrapped value is a `LiveCounter`, delegates to `LiveCounter#value` ([RTLC5](#RTLC5))
  - `(RTINS4b)` If the wrapped value is a primitive (`Boolean`, `Binary`, `Number`, `String`, `JsonArray`, `JsonObject`), returns the value directly
  - `(RTINS4c)` If the wrapped value is a `LiveMap`, returns undefined/null
- `(RTINS5)` `Instance#get` function:
  - `(RTINS5a)` Expects the following arguments:
    - `(RTINS5a1)` `key` `String` - the key to look up
  - `(RTINS5b)` If the wrapped value is a `LiveMap`, looks up the value at `key` using `LiveMap#get` ([RTLM5](#RTLM5)) and returns a new `Instance` wrapping the result. If the result is undefined/null, returns undefined/null
  - `(RTINS5c)` If the wrapped value is not a `LiveMap`, returns undefined/null
- `(RTINS6)` `Instance#entries` function:
  - `(RTINS6a)` If the wrapped value is a `LiveMap`, delegates to `LiveMap#entries` ([RTLM11](#RTLM11)) and returns an array of `[key, Instance]` pairs, where each `Instance` wraps the corresponding value
  - `(RTINS6b)` If the wrapped value is not a `LiveMap`, returns an empty array
- `(RTINS7)` `Instance#keys` function:
  - `(RTINS7a)` If the wrapped value is a `LiveMap`, delegates to `LiveMap#keys` ([RTLM12](#RTLM12))
  - `(RTINS7b)` If the wrapped value is not a `LiveMap`, returns an empty array
- `(RTINS8)` `Instance#values` function:
  - `(RTINS8a)` If the wrapped value is a `LiveMap`, delegates to `LiveMap#values` ([RTLM13](#RTLM13)) and returns an array of `Instance`s, where each `Instance` wraps the corresponding value
  - `(RTINS8b)` If the wrapped value is not a `LiveMap`, returns an empty array
- `(RTINS9)` `Instance#size` function:
  - `(RTINS9a)` If the wrapped value is a `LiveMap`, delegates to `LiveMap#size` ([RTLM10](#RTLM10))
  - `(RTINS9b)` If the wrapped value is not a `LiveMap`, returns undefined/null
- `(RTINS10)` `Instance#compact` function:
  - `(RTINS10a)` Behaves identically to `PathObject#compact` ([RTPO13](#RTPO13)), but operates on the wrapped value directly instead of resolving a path
- `(RTINS11)` `Instance#compactJson` function:
  - `(RTINS11a)` Behaves identically to `PathObject#compactJson` ([RTPO14](#RTPO14)), but operates on the wrapped value directly instead of resolving a path
- `(RTINS12)` `Instance#set` function:
  - `(RTINS12a)` Expects the following arguments:
    - `(RTINS12a1)` `key` `String` - the key to set the value for
    - `(RTINS12a2)` `value` - the value to assign to the key. Accepted types are the same as for `LiveMap#set` ([RTLM20](#RTLM20))
  - `(RTINS12b)` If the wrapped value is a `LiveMap`, delegates to `LiveMap#set` ([RTLM20](#RTLM20)) with the provided `key` and `value`
  - `(RTINS12c)` If the wrapped value is not a `LiveMap`, the library must throw an `ErrorInfo` error with `statusCode` 400 and `code` 92007
- `(RTINS13)` `Instance#remove` function:
  - `(RTINS13a)` Expects the following arguments:
    - `(RTINS13a1)` `key` `String` - the key to remove the value for
  - `(RTINS13b)` If the wrapped value is a `LiveMap`, delegates to `LiveMap#remove` ([RTLM21](#RTLM21)) with the provided `key`
  - `(RTINS13c)` If the wrapped value is not a `LiveMap`, the library must throw an `ErrorInfo` error with `statusCode` 400 and `code` 92007
- `(RTINS14)` `Instance#increment` function:
  - `(RTINS14a)` Expects the following arguments:
    - `(RTINS14a1)` `amount` `Number` (optional) - the amount by which to increment the counter value. Defaults to 1
  - `(RTINS14b)` If the wrapped value is a `LiveCounter`, delegates to `LiveCounter#increment` ([RTLC12](#RTLC12)) with the provided `amount`
  - `(RTINS14c)` If the wrapped value is not a `LiveCounter`, the library must throw an `ErrorInfo` error with `statusCode` 400 and `code` 92007
- `(RTINS15)` `Instance#decrement` function:
  - `(RTINS15a)` Expects the following arguments:
    - `(RTINS15a1)` `amount` `Number` (optional) - the amount by which to decrement the counter value. Defaults to 1
  - `(RTINS15b)` If the wrapped value is a `LiveCounter`, delegates to `LiveCounter#decrement` ([RTLC13](#RTLC13)) with the provided `amount`
  - `(RTINS15c)` If the wrapped value is not a `LiveCounter`, the library must throw an `ErrorInfo` error with `statusCode` 400 and `code` 92007
- `(RTINS16)` `Instance#subscribe` function:
  - `(RTINS16a)` Expects the following arguments:
    - `(RTINS16a1)` `listener` - a callback function that receives an `InstanceSubscriptionEvent` ([RTINS16d](#RTINS16d)) when the wrapped object is updated
  - `(RTINS16b)` If the wrapped value is not a `LiveObject` (i.e. it is a primitive), the library must throw an `ErrorInfo` error with `statusCode` 400 and `code` 92007, indicating that subscribe is not supported for primitive values
  - `(RTINS16c)` Subscribes to data updates on the underlying `LiveObject` using `LiveObject#subscribe` ([RTLO4b](#RTLO4b))
  - `(RTINS16d)` The listener receives an `InstanceSubscriptionEvent` object with:
    - `(RTINS16d1)` `object` - an `Instance` wrapping the underlying `LiveObject`
    - `(RTINS16d2)` `message` `PublicAPI::ObjectMessage` (optional) - if `LiveObjectUpdate.objectMessage` from the underlying `LiveObject#subscribe` notification is populated and its `operation` field is populated, a `PublicAPI::ObjectMessage` ([PAOM1](#PAOM1)) derived from it per [PAOM3](#PAOM3); otherwise omitted
  - `(RTINS16e)` Returns a [`Subscription`](../features#SUB1) object
  - `(RTINS16f)` The subscription is identity-based: it follows the specific `LiveObject` instance, regardless of where it sits in the tree
  - `(RTINS16g)` This operation must not have any side effects on `RealtimeObject`, the underlying channel, or their status

### PublicAPI::ObjectMessage

- `(PAOM1)` A `PublicAPI::ObjectMessage` is the user-facing representation of an inbound `ObjectMessage` ([OM1](../features#OM1)) that carried an operation. It is delivered to user subscription listeners (see [RTPO19d2](#RTPO19d2), [RTINS16d2](#RTINS16d2)) so that user code can inspect the metadata of the message that triggered an object change. The `PublicAPI::` prefix is used to avoid a name clash with `ObjectMessage`; SDKs expose this type to users as `ObjectMessage`.
- `(PAOM2)` The attributes available in a `PublicAPI::ObjectMessage` are:
  - `(PAOM2a)` `id` string (optional) - the `id` ([OM2a](../features#OM2a)) of the source `ObjectMessage`
  - `(PAOM2b)` `clientId` string (optional) - the `clientId` ([OM2b](../features#OM2b)) of the source `ObjectMessage`
  - `(PAOM2c)` `connectionId` string (optional) - the `connectionId` ([OM2c](../features#OM2c)) of the source `ObjectMessage`
  - `(PAOM2d)` `timestamp` Time (optional) - the `timestamp` ([OM2e](../features#OM2e)) of the source `ObjectMessage`
  - `(PAOM2e)` `channel` string - the name of the channel on which the source `ObjectMessage` was received
  - `(PAOM2f)` `operation` `PublicAPI::ObjectOperation` ([PAOOP1](#PAOOP1)) - a `PublicAPI::ObjectOperation` derived per [PAOOP3](#PAOOP3) from the `operation` ([OM2f](../features#OM2f)) of the source `ObjectMessage`
  - `(PAOM2g)` `serial` string (optional) - the `serial` ([OM2h](../features#OM2h)) of the source `ObjectMessage`
  - `(PAOM2h)` `serialTimestamp` Time (optional) - the `serialTimestamp` ([OM2j](../features#OM2j)) of the source `ObjectMessage`
  - `(PAOM2i)` `siteCode` string (optional) - the `siteCode` ([OM2i](../features#OM2i)) of the source `ObjectMessage`
  - `(PAOM2j)` `extras` JSON-encodable object (optional) - the `extras` ([OM2d](../features#OM2d)) of the source `ObjectMessage`
- `(PAOM3)` To construct a `PublicAPI::ObjectMessage` from a source `ObjectMessage` received on a channel `channel`:
  - `(PAOM3a)` Preconditions (callers are responsible for ensuring these):
    - `(PAOM3a1)` The source `ObjectMessage` has its `operation` ([OM2f](../features#OM2f)) field populated
  - `(PAOM3b)` Set the `channel` attribute to `channel.name`
  - `(PAOM3c)` Copy `id`, `clientId`, `connectionId`, `timestamp`, `serial`, `serialTimestamp`, `siteCode`, and `extras` from the source `ObjectMessage` to the corresponding attributes of the `PublicAPI::ObjectMessage`
  - `(PAOM3d)` Set `operation` to a `PublicAPI::ObjectOperation` derived per [PAOOP3](#PAOOP3) from the `operation` ([OM2f](../features#OM2f)) of the source `ObjectMessage`

### PublicAPI::ObjectOperation

- `(PAOOP1)` A `PublicAPI::ObjectOperation` is the user-facing representation of an `ObjectOperation` ([OOP1](../features#OOP1)). It is the type of the `operation` attribute of a `PublicAPI::ObjectMessage` ([PAOM2f](#PAOM2f)). The `PublicAPI::` prefix is used to avoid a name clash with `ObjectOperation`; SDKs expose this type to users as `ObjectOperation`. It differs from `ObjectOperation` in that it does not carry the `mapCreateWithObjectId` ([OOP3p](../features#OOP3p)) or `counterCreateWithObjectId` ([OOP3q](../features#OOP3q)) variants: these are outbound-only representations that are resolved back to their derived `MapCreate` / `CounterCreate` forms when constructing a `PublicAPI::ObjectOperation`.
- `(PAOOP2)` The attributes available in a `PublicAPI::ObjectOperation` are:
  - `(PAOOP2a)` `action` `ObjectOperationAction` ([OOP2](../features#OOP2)) - the `action` ([OOP3a](../features#OOP3a)) of the source `ObjectOperation`
  - `(PAOOP2b)` `objectId` string - the `objectId` ([OOP3b](../features#OOP3b)) of the source `ObjectOperation`
  - `(PAOOP2c)` `mapCreate` `MapCreate` (optional) - the `MapCreate` payload, if applicable (see [PAOOP3b](#PAOOP3b))
  - `(PAOOP2d)` `mapSet` `MapSet` (optional) - the `mapSet` ([OOP3k](../features#OOP3k)) of the source `ObjectOperation`
  - `(PAOOP2e)` `mapRemove` `MapRemove` (optional) - the `mapRemove` ([OOP3l](../features#OOP3l)) of the source `ObjectOperation`
  - `(PAOOP2f)` `counterCreate` `CounterCreate` (optional) - the `CounterCreate` payload, if applicable (see [PAOOP3c](#PAOOP3c))
  - `(PAOOP2g)` `counterInc` `CounterInc` (optional) - the `counterInc` ([OOP3n](../features#OOP3n)) of the source `ObjectOperation`
  - `(PAOOP2h)` `objectDelete` `ObjectDelete` (optional) - the `objectDelete` ([OOP3o](../features#OOP3o)) of the source `ObjectOperation`
  - `(PAOOP2i)` `mapClear` `MapClear` (optional) - the `mapClear` ([OOP3r](../features#OOP3r)) of the source `ObjectOperation`
- `(PAOOP3)` To construct a `PublicAPI::ObjectOperation` from a source `ObjectOperation`:
  - `(PAOOP3a)` Copy `action`, `objectId`, `mapSet`, `mapRemove`, `counterInc`, `objectDelete`, and `mapClear` from the source `ObjectOperation` to the corresponding attributes of the `PublicAPI::ObjectOperation`
  - `(PAOOP3b)` Set `mapCreate` as follows:
    - `(PAOOP3b1)` If `mapCreate` ([OOP3j](../features#OOP3j)) is present on the source, set `mapCreate` to that value
    - `(PAOOP3b2)` Else if `mapCreateWithObjectId` ([OOP3p](../features#OOP3p)) is present on the source, set `mapCreate` to the `MapCreate` from which it was derived (retained per [RTLMV4j5](#RTLMV4j5))
    - `(PAOOP3b3)` Otherwise omit `mapCreate`
  - `(PAOOP3c)` Set `counterCreate` as follows:
    - `(PAOOP3c1)` If `counterCreate` ([OOP3m](../features#OOP3m)) is present on the source, set `counterCreate` to that value
    - `(PAOOP3c2)` Else if `counterCreateWithObjectId` ([OOP3q](../features#OOP3q)) is present on the source, set `counterCreate` to the `CounterCreate` from which it was derived (retained per [RTLCV4g5](#RTLCV4g5))
    - `(PAOOP3c3)` Otherwise omit `counterCreate`

## Interface Definition {#idl}

Describes types for RealtimeObject.\
Types and their properties/methods are public and exposed to users by default. An `internal` label may be used to indicate that a type or its property/method must not be exposed to users and is intended for internal SDK use only.

    // Primitive is an alias used throughout the IDL
    type Primitive = Boolean | Binary | Number | String | JsonArray | JsonObject // internal

    class RealtimeObject: // RTO*
      get() => io PathObject // RTO23
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

    class LiveObject: // RTLO*, internal
      objectId: String // RTLO3a
      siteTimeserials: Dict<String, String> // RTLO3b
      createOperationIsMerged: Boolean // RTLO3c
      isTombstone: Boolean // RTLO3d
      tombstonedAt: Time? // RTLO3e
      parentReferences: Dict<String, Set<String>> // RTLO3f
      canApplyOperation(ObjectMessage) -> Boolean // RTLO4a
      addParentReference(parent, key) // RTLO4f
      removeParentReference(parent, key) // RTLO4g
      tombstone(ObjectMessage) // RTLO4e
      subscribe((LiveObjectUpdate) ->) -> Subscription // RTLO4b

    interface LiveObjectUpdate: // RTLO4b4, internal
      update: Object // RTLO4b4a
      noop: Boolean // RTLO4b4b
      objectMessage: ObjectMessage? // RTLO4b4d

    class LiveCounter extends LiveObject: // RTLC*, RTLC1, internal
      value() -> Number // RTLC5
      increment(Number amount) => io // RTLC12
      decrement(Number amount) => io // RTLC13

    interface LiveCounterUpdate extends LiveObjectUpdate: // RTLC11, RTLC11a, internal
      update: { amount: Number } // RTLC11b, RTLC11b1

    class LiveMap extends LiveObject: // RTLM*, RTLM1, internal
      clearTimeserial: String? // RTLM25
      get(key: String) -> (Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounter | LiveMap)? // RTLM5
      size() -> Number // RTLM10
      entries() -> [String, (Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounter | LiveMap)?][] // RTLM11
      keys() -> String[] // RTLM12
      values() -> (Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounter | LiveMap)?[] // RTLM13
      set(String key, (Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounterValueType | LiveMapValueType) value) => io // RTLM20
      remove(String key) => io // RTLM21

    interface LiveMapUpdate extends LiveObjectUpdate: // RTLM18, RTLM18a, internal
      update: Dict<String, 'updated' | 'removed'> // RTLM18b

    class LiveCounterValueType: // RTLCV*
      count: Number // RTLCV2a, internal
      static create(Number initialCount?) -> LiveCounterValueType // RTLCV3

    class LiveMapValueType: // RTLMV*
      entries: Dict<String, (Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounterValueType | LiveMapValueType)>? // RTLMV2a, internal
      static create(Dict<String, Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounterValueType | LiveMapValueType> entries?) -> LiveMapValueType // RTLMV3

    interface PathObjectSubscriptionEvent: // RTPO19d
      object: PathObject // RTPO19d1
      message: PublicAPI::ObjectMessage? // RTPO19d2

    interface PathObjectSubscriptionOptions: // RTPO19b
      depth: Number? // RTPO19b1

    interface InstanceSubscriptionEvent: // RTINS16d
      object: Instance // RTINS16d1
      message: PublicAPI::ObjectMessage? // RTINS16d2

    class PublicAPI::ObjectMessage: // PAOM*
      id: String? // PAOM2a
      clientId: String? // PAOM2b
      connectionId: String? // PAOM2c
      timestamp: Time? // PAOM2d
      channel: String // PAOM2e
      operation: PublicAPI::ObjectOperation // PAOM2f
      serial: String? // PAOM2g
      serialTimestamp: Time? // PAOM2h
      siteCode: String? // PAOM2i
      extras: JsonObject? // PAOM2j

    class PublicAPI::ObjectOperation: // PAOOP*
      action: ObjectOperationAction // PAOOP2a
      objectId: String // PAOOP2b
      mapCreate: MapCreate? // PAOOP2c
      mapSet: MapSet? // PAOOP2d
      mapRemove: MapRemove? // PAOOP2e
      counterCreate: CounterCreate? // PAOOP2f
      counterInc: CounterInc? // PAOOP2g
      objectDelete: ObjectDelete? // PAOOP2h
      mapClear: MapClear? // PAOOP2i

    class PathObject: // RTPO*
      path() -> String // RTPO4
      get(String key) -> PathObject // RTPO5
      at(String path) -> PathObject // RTPO6
      value() -> (Boolean | Binary | Number | String | JsonArray | JsonObject)? // RTPO7
      instance() -> Instance? // RTPO8
      entries() -> [String, PathObject][] // RTPO9
      keys() -> String[] // RTPO10
      values() -> PathObject[] // RTPO11
      size() -> Number? // RTPO12
      compact() -> Object? // RTPO13
      compactJson() -> Object? // RTPO14
      set(String key, (Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounterValueType | LiveMapValueType) value) => io // RTPO15
      remove(String key) => io // RTPO16
      increment(Number amount?) => io // RTPO17
      decrement(Number amount?) => io // RTPO18
      subscribe((PathObjectSubscriptionEvent) -> listener, PathObjectSubscriptionOptions? options) -> Subscription // RTPO19

    class Instance: // RTINS*
      id: String? // RTINS3
      value() -> (Boolean | Binary | Number | String | JsonArray | JsonObject)? // RTINS4
      get(String key) -> Instance? // RTINS5
      entries() -> [String, Instance][] // RTINS6
      keys() -> String[] // RTINS7
      values() -> Instance[] // RTINS8
      size() -> Number? // RTINS9
      compact() -> Object? // RTINS10
      compactJson() -> Object? // RTINS11
      set(String key, (Boolean | Binary | Number | String | JsonArray | JsonObject | LiveCounterValueType | LiveMapValueType) value) => io // RTINS12
      remove(String key) => io // RTINS13
      increment(Number amount?) => io // RTINS14
      decrement(Number amount?) => io // RTINS15
      subscribe((InstanceSubscriptionEvent) -> listener) -> Subscription // RTINS16
