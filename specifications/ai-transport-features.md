---
title: AI Transport Features
---

## Overview

This document outlines the feature specification for the Ably AI Transport product.

The Ably AI Transport SDK provides transport and codec abstractions for building AI applications over Ably. It enables realtime streaming of AI model responses between server and client, with support for conversation history, branching, cancellation, and multi-client synchronization.

The key words "must", "must not", "required", "shall", "shall not", "should", "should not", "recommended", "may", and "optional" (whether lowercased or uppercased) in this document are to be interpreted as described in [RFC 2119](https://tools.ietf.org/html/rfc2119).

## AI Transport Specification Version {#version}

- `(AIT-V1)` **Specification Version**: This document defines the Ably AI Transport library features specification ('features spec').
  - `(AIT-V1a)` The current version of the AI Transport library feature specification is version `0.1.0`.

## General Principles {#general}

- `(AIT-GP1)` The SDK must be split into a generic layer and one or more framework-specific layers. The generic layer must have no dependencies on any AI framework (e.g. Vercel AI SDK). Framework-specific layers implement codecs and provide convenience wrappers.
- `(AIT-GP2)` All generic components must be parameterized by a `Codec` interface. The codec defines how application-level events are encoded to Ably messages and decoded back.
- `(AIT-GP3)` The generic layer must use only `x-ably-*` message headers. Domain-specific headers (e.g. headers specific to the Vercel AI SDK) must only appear in framework-specific layers.
- `(AIT-GP4)` A single shared Ably channel must be used per session instance. All features (streaming, cancellation, history) operate over this shared channel.
- `(AIT-GP5)` All dependencies must be passed through constructors or factory options. There must be no singletons, service locators, or global state.
- `(AIT-GP6)` When raising an `ErrorInfo`, avoid relying on the generic `40000` and `50000` codes.
  - `(AIT-GP6a)` Prefer codes already defined in `ably-common`, for example — use `InvalidArgument` (`40003`) for an invalid argument passed to a function.
  - `(AIT-GP6b)` If the error is AI Transport-specific, define a new code in the `104000–104999` range reserved for this SDK.
- `(AIT-GP7)` Error messages must follow the standard format `unable to <operation>; <reason>`.
  - `(AIT-GP7a)` Error messages must be written assuming that the audience is the customer developer, not an Ably engineer.

## Codec {#codec}

The codec layer defines the contract between domain event streams and Ably's native message primitives (publish, append, update, delete). It is split into a generic `Codec` interface and core encoder/decoder machinery.

### Encoder Core

- `(AIT-CD1)` The SDK must provide a `createEncoderCore` factory that returns an `EncoderCore`. The encoder core provides Ably primitives (publish, append, close, abort) that domain-specific encoders wire their event types to.
- `(AIT-CD2)` `startStream` must publish an Ably message with `x-ably-stream: "true"`, `x-ably-status: "streaming"`, and `x-ably-stream-id` set to the provided `streamId`. It must store the returned serial in a tracker keyed by `streamId`.
  - `(AIT-CD2a)` If the publish does not return a serial, `startStream` must raise an error.
- `(AIT-CD3)` `appendStream` must append a text delta to an active stream's tracked serial. The delta must be accumulated in the tracker for recovery purposes.
  - `(AIT-CD3a)` If no tracker exists for the given `streamId`, `appendStream` must raise an error.
- `(AIT-CD4)` `closeStream` must append a message with `x-ably-status: "finished"`. The closing append must repeat all persistent headers from the stream tracker. After enqueuing the closing append, `closeStream` must flush all pending appends and attempt recovery for any failures before returning.
  - `(AIT-CD4a)` If no tracker exists for the given `streamId`, `closeStream` must raise an error.
- `(AIT-CD5)` `abortStream` must mark the specified stream as aborted and append a message with `x-ably-status: "aborted"`. After enqueuing the abort append, it must flush all pending appends and attempt recovery before returning.
  - `(AIT-CD5a)` `abortAllStreams` must perform the same operation as `abortStream` for every active stream, then flush all pending appends.
  - `(AIT-CD5b)` If no tracker exists for the given `streamId`, `abortStream` must raise an error.
- `(AIT-CD6)` Flushing must await all pipelined appends. For any failed append, recovery must be attempted via `updateMessage` with the full accumulated text. If recovery also fails, the flush must raise an error with code `EncoderRecoveryFailed` (`104000`).

### Decoder Core

- `(AIT-CD7)` The SDK must provide a `createDecoderCore` factory that accepts domain-specific hooks and returns a `DecoderCore`. The decoder dispatches on Ably message actions (`message.create`, `message.append`, `message.update`, `message.delete`).
  - `(AIT-CD7a)` On `message.create`, the decoder must check the `x-ably-stream` header to determine whether the message enters the streaming path or the discrete path. Stream identity must be read from the `x-ably-stream-id` header.
- `(AIT-CD8)` On `message.append`, the decoder must accumulate the delta text in the stream tracker. If `x-ably-status` is `"finished"`, it must mark the stream as closed and emit end events. If `"aborted"`, it must mark the stream as closed without emitting end events.
- `(AIT-CD9)` On `message.update` with no existing tracker (first-contact), the decoder must create a new tracker. If the message data is non-empty, it must emit start, delta, and (if finished) end events. On `message.update` with an existing tracker where data is a prefix extension, it must emit only the new delta portion.
- `(AIT-CD10)` On `message.delete`, the decoder must invoke the `onStreamDelete` callback (if set) and mark the tracker as closed.

### Discrete Publishing

- `(AIT-CD11)` The encoder core must provide a `publishDiscrete` operation that publishes a standalone message with `x-ably-stream: "false"` and caller-provided headers merged with defaults.
  - `(AIT-CD11a)` `publishDiscreteBatch` must publish multiple discrete messages atomically in a single channel publish.

### Encoder Lifecycle

- `(AIT-CD12)` The encoder core must provide a `close` method that flushes all pending appends, clears all stream trackers, and rejects subsequent operations. Close must be idempotent.

### Lifecycle Tracker

- `(AIT-CD13)` The decoder must support a lifecycle tracker that synthesizes missing lifecycle events (e.g. `start`, `start-step`) when a client joins a stream mid-run. Phases must be emitted in configuration order before content events.

### Encoder Hooks

- `(AIT-CD14)` The encoder core must invoke an optional `onMessage` hook before each Ably message is published. The hook receives the message before it is sent to the channel writer. If the hook throws, the encoder must catch and log the exception without interrupting the publish.

## Agent Session {#agent-session}

The agent (server-side) session manages the run lifecycle over an Ably channel. It composes a `RunManager` for lifecycle event publishing and pipes event streams through the encoder.

### Factory

- `(AIT-ST1)` The SDK must provide a `createAgentSession` factory that accepts an `Ably.Realtime` client, a channel name, a codec, an optional logger, and an optional `onError` callback, and returns an `AgentSession`.
  - `(AIT-ST1a)` On construction the agent session must configure the supplied Realtime client to attribute usage to this SDK and resolve the channel by name. Configuration must be idempotent — repeated construction with the same client must leave the attribution state unchanged, so multiple sessions sharing one client are safe. The session must not close the client or release the channel on `close()`; the caller owns the client's lifecycle. The session owns its channel — callers must not also resolve the same channel name elsewhere with conflicting channel options. The attribution mechanism follows the fallback chain in `AIT-ST1a1`–`AIT-ST1a3`, modeled on chat spec [CHA-IN1](https://sdk.ably.com/builds/ably/specification/main/chat-features/#CHA-IN1).
    - `(AIT-ST1a1)` Where the underlying Realtime SDK exposes a wrapper-SDK proxy mechanism (per [CHA-IN1a](https://sdk.ably.com/builds/ably/specification/main/chat-features/#CHA-IN1a)), the session must use it with `{ agents: { 'ai-transport-js': VERSION } }` and use the proxy for all subsequent channel operations.
    - `(AIT-ST1a2)` Where the wrapper-SDK proxy mechanism does not exist (current ably-js), the session must inject `'ai-transport-js' -> VERSION` into the client's `options.agents` map AND pass `{ params: { agent: 'ai-transport-js/<VERSION>' } }` on `client.channels.get(channelName)`. Mirrors [CHA-IN1e](https://sdk.ably.com/builds/ably/specification/main/chat-features/#CHA-IN1e).
    - `(AIT-ST1a3)` SDK authors must register the agent identifiers used here in the common repository (`ably-common/protocol/agents.json`), per [RSC7d5](https://sdk.ably.com/builds/ably/specification/main/features/#RSC7d5).
- `(AIT-ST2)` `connect()` must subscribe to the cancel message name (`x-ably-cancel`) on the channel — subscribe implicitly attaches the channel — so that cancel messages from clients are routed to active runs. It must be idempotent: subsequent calls return the same promise. All run-lifecycle methods (`start`, `addMessages`, `addEvents`, `pipe`, `end`) must throw `InvalidArgument` until `connect()` resolves.

### Run Lifecycle

- `(AIT-ST3)` `createRun(invocation, runtime?)` must synchronously return a `Run` object. The {@link Invocation} carries identity (`runId`, `clientId`, `parent`, `forkOf`, `messages`, `history`, `events`); `runtime` carries per-request hooks (`signal`, `onMessage`, `onAbort`, `onCancel`, `onError`). No channel activity must occur until `start()` is called.
  - `(AIT-ST3a)` The run must be registered for cancel routing immediately on creation, so that cancel messages arriving before `start()` still fire the run's abort signal.
- `(AIT-ST4)` `start()` must publish a run-start event (`x-ably-run-start`) with the run's `x-ably-run-id` and `x-ably-run-client-id` headers. It must be idempotent.
  - `(AIT-ST4a)` If the run was cancelled before `start()`, `start()` must raise an error.
  - `(AIT-ST4b)` If the run-start publish fails, `start()` must reject with an `Ably.ErrorInfo` carrying code `RunLifecycleError` and wrapping the underlying error as `cause`. The per-run `onError` callback must NOT be invoked — the rejected promise is the sole delivery channel.
- `(AIT-ST5)` `addMessages()` must accept `MessageNode[]` and require that `start()` has been called. For each node, it must create a codec encoder with transport headers built from the node's typed fields (`msgId`, `parentId`, `forkOf`) merged with its `headers`, and publish the message through the encoder.
  - `(AIT-ST5a)` Per-node `parentId` and `forkOf` fields take precedence; run-level defaults apply when those fields are undefined.
  - `(AIT-ST5b)` `addMessages()` must return an `AddMessagesResult` containing the `msgId` of each published node, in order. This allows the caller to pass the last msg-id as the assistant message's parent.
  - `(AIT-ST5c)` If a publish fails in `addMessages()` or `addEvents()`, the method must reject with an `Ably.ErrorInfo` carrying code `RunLifecycleError` and wrapping the underlying error as `cause`. The per-run `onError` callback must NOT be invoked — the rejected promise is the sole delivery channel.
- `(AIT-ST6)` `pipe()` must require that `start()` has been called. It must create a codec encoder with transport headers (`x-ably-role: "assistant"`, `x-ably-run-id`, unique `x-ably-msg-id`, and parent/forkOf headers) and pipe the event stream through the encoder.
  - `(AIT-ST6a)` The assistant message's parent must be resolved in order: per-operation `parent` override, then run-level `parent`.
  - `(AIT-ST6b)` `pipe()` must return a `StreamResult` with a `reason` field indicating `"complete"`, `"cancelled"`, or `"error"`.
    - `(AIT-ST6b1)` Reason `"complete"`: the source stream was fully consumed and the encoder was closed.
    - `(AIT-ST6b2)` Reason `"cancelled"`: the run's abort signal fired. If an `onAbort` callback was provided in the runtime options, it must be invoked with a write function before the stream ends.
    - `(AIT-ST6b3)` Reason `"error"`: the source stream threw. The encoder must be closed best-effort; failure to close must not propagate. `pipe()` must not throw; it must return a `StreamResult` whose `error` field holds the original caught error (preserving provider-specific type information). The per-run `onError` callback must be invoked with an `Ably.ErrorInfo` wrapping the original error.
    - `(AIT-ST6b4)` Error details from `"error"` streams must NOT automatically propagate to the client session. The client receives only `reason: "error"` on the run-end event. Server implementations that need to surface error details to the client must do so explicitly — for example, by mutating the run-end message through the `onMessage` hook or by publishing application-defined events before `end()`. Rationale: automatic propagation could leak server internals and would impose a protocol contract on all codecs.
  - `(AIT-ST6c)` `pipe()` must NOT call `end()` — the caller is responsible for calling `end()` after the stream finishes.
- `(AIT-ST7)` `end()` must require that `start()` has been called. It must publish a run-end event (`x-ably-run-end`) with the run's ID, clientId, and reason header. It must be idempotent.
  - `(AIT-ST7a)` After `end()`, the run must be deregistered from cancel routing regardless of whether the publish succeeds.
  - `(AIT-ST7b)` If the run-end publish fails, `end()` must reject with an `Ably.ErrorInfo` carrying code `RunLifecycleError` and wrapping the underlying error as `cause`. The per-run `onError` callback must NOT be invoked. The run must still be deregistered from cancel routing (per `AIT-ST7a`).

### Cancel Routing

- `(AIT-ST8)` The agent session must route cancel messages from the channel to registered runs by parsing cancel filter headers from the incoming message.
  - `(AIT-ST8a)` `x-ably-cancel-run-id`: cancel a specific run by ID.
  - `(AIT-ST8b)` `x-ably-cancel-own` (value `"true"`): cancel all runs belonging to the sender's `clientId`.
  - `(AIT-ST8c)` `x-ably-cancel-client-id`: cancel all runs belonging to a specific `clientId`.
  - `(AIT-ST8d)` `x-ably-cancel-all` (value `"true"`): cancel all runs on the channel.
- `(AIT-ST9)` If a per-run `onCancel` hook is provided, it must be invoked before aborting. If it returns `false`, the run must not be aborted.
  - `(AIT-ST9a)` If the `onCancel` hook throws, the error must be reported via the per-run or session-level `onError` callback, and processing must continue for remaining matched runs.

### Session Close

- `(AIT-ST11)` `close()` must unsubscribe from cancel messages, abort all registered runs, and clean up the run manager. It must also stop listening for channel state changes (AIT-ST12). `close()` must be idempotent.

### Channel Continuity

- `(AIT-ST12)` The agent session must monitor the channel for continuity loss. Continuity is lost when the channel enters FAILED, SUSPENDED, or DETACHED, or re-attaches with `resumed: false`.
  - `(AIT-ST12a)` On continuity loss, the error must be emitted via the session-level `onError` callback with code `ChannelContinuityLost` (104006). Active runs must not be automatically aborted, and the per-run `onError` callback must not be invoked, since continuity loss is not scoped to any run. The SDK user is responsible for reacting (e.g. iterating active runs or aborting their own external signals) if they wish to terminate in-flight work.

### Invocation

- `(AIT-ST13)` The SDK must provide an `Invocation` class with a static `fromJSON(data: InvocationData)` factory that wraps the JSON wire body sent from the client to the agent endpoint. `InvocationData` carries `runId`, `clientId`, `sessionName`, optional `messages`, optional `history`, optional `events`, optional `parent`, and optional `forkOf`. Omitted optional fields default to empty arrays / `undefined` on the constructed `Invocation`.

### Presence

- `(AIT-ST14)` The agent session must expose the underlying Ably channel's presence object via a read-only `presence` accessor. The accessor must return the channel's `RealtimePresence` directly, applying no AI-Transport-specific semantics, and must be usable before `connect()` is called.

### LiveObjects

- `(AIT-ST15)` The agent session must expose the underlying Ably channel's LiveObjects entry point via a read-only `object` accessor. The accessor must return the channel's `RealtimeObject` directly, applying no AI-Transport-specific semantics, and must be usable before `connect()` is called. Operating on it requires the Realtime client to have been constructed with the LiveObjects plugin and the channel to have been attached with the object channel modes (AIT-ST16); when either is absent the underlying SDK throws and the session must not suppress the error.
- `(AIT-ST16)` The agent session must accept an optional `channelModes` option listing additional Ably channel modes to request on the session's channel (e.g. the object modes required by AIT-ST15). The AI-Transport SDK defines a base set of channel modes equal to the set Ably grants by default when a channel is attached without requesting any modes on the wire — namely `publish`, `subscribe`, `presence`, and `presence_subscribe`. When `channelModes` is provided, the session must request the union of this base set and the supplied modes, deduplicated and in a deterministic order; because the base set equals the default-granted set, requesting additional modes this way does not remove or alter any behaviour the channel would otherwise have. When `channelModes` is omitted, the session must not send any channel modes on the wire, so Ably grants the base set by default and the default attachment behaviour is preserved.

## Client Session {#client-session}

The client session manages the client-side conversation lifecycle over an Ably channel. It composes a Tree for branching message history, a StreamRouter for per-run event streams, and a codec decoder for processing incoming Ably messages.

### Factory

- `(AIT-CT1)` The SDK must provide a `createClientSession` factory that accepts an `Ably.Realtime` client, a channel name, a codec, and session options, and returns a `ClientSession`.
  - `(AIT-CT1a)` On construction the client session must configure the supplied Realtime client to attribute usage to this SDK and resolve the channel by name. Configuration must be idempotent — repeated construction with the same client must leave the attribution state unchanged, so multiple sessions sharing one client are safe. The session must not close the client or release the channel on `close()`; the caller owns the client's lifecycle. The session owns its channel — callers must not also resolve the same channel name elsewhere with conflicting channel options. The attribution mechanism follows the fallback chain in `AIT-CT1a1`–`AIT-CT1a3`, modeled on chat spec [CHA-IN1](https://sdk.ably.com/builds/ably/specification/main/chat-features/#CHA-IN1).
    - `(AIT-CT1a1)` Where the underlying Realtime SDK exposes a wrapper-SDK proxy mechanism (per [CHA-IN1a](https://sdk.ably.com/builds/ably/specification/main/chat-features/#CHA-IN1a)), the session must use it with `{ agents: { 'ai-transport-js': VERSION } }` and use the proxy for all subsequent channel operations.
    - `(AIT-CT1a2)` Where the wrapper-SDK proxy mechanism does not exist (current ably-js), the session must inject `'ai-transport-js' -> VERSION` into the client's `options.agents` map AND pass `{ params: { agent: 'ai-transport-js/<VERSION>' } }` on `client.channels.get(channelName)`. Mirrors [CHA-IN1e](https://sdk.ably.com/builds/ably/specification/main/chat-features/#CHA-IN1e).
    - `(AIT-CT1a3)` SDK authors must register the agent identifiers used here in the common repository (`ably-common/protocol/agents.json`), per [RSC7d5](https://sdk.ably.com/builds/ably/specification/main/features/#RSC7d5).
- `(AIT-CT2)` `connect()` must subscribe to the channel for incoming messages — subscribe implicitly attaches the channel (Ably RTL7g) to guarantee no messages are missed. It must be idempotent: subsequent calls return the same promise. All write methods (`send`, `regenerate`, `edit`, `update`, `cancel`, `waitForRun`) must throw `InvalidArgument` until `connect()` resolves.

### Send

- `(AIT-CT3)` `send()` must create a new run, optimistically insert user messages into the conversation tree, and return an `ActiveRun` handle containing a decoded event stream, the run ID, and a cancel function.
  - `(AIT-CT3a)` The HTTP POST to the agent must be fire-and-forget — the returned stream must be available immediately, without waiting for the POST to complete.
  - `(AIT-CT3b)` If the HTTP POST fails (network error or non-2xx response), the error must be emitted via `on('error')`, not thrown. The run's stream must be errored via `errorStream()` (AIT-CT14c) with code `SessionSendFailed` (104005). For non-2xx responses, the HTTP status code must be used as the `statusCode`. For network errors, the original error must be wrapped as the `cause`.
  - `(AIT-CT3c)` Each user message must be assigned a unique `x-ably-msg-id` and optimistically inserted into the conversation tree before the POST is sent.
  - `(AIT-CT3d)` If `parent` is not explicitly provided and `forkOf` is not set, the parent must be auto-computed from the last message in the current thread.
  - `(AIT-CT3e)` When multiple messages are sent in a single `send()` call, they must be chained — each subsequent message must parent off the previous message in the batch, not the original auto-computed parent.
- `(AIT-CT4)` `send()` must throw if the session is closed.

### Regenerate

- `(AIT-CT5)` `regenerate()` must create a new run that forks the target message with `forkOf` set to the target, `parent` set to the target's parent, and truncated history (everything before the target). No new user messages are sent.

### Edit

- `(AIT-CT6)` `edit()` must create a new run that forks the target message with replacement user messages. `forkOf` must be set to the target, `parent` to the target's parent.

### Cancel

- `(AIT-CT7)` `cancel()` must publish a cancel message to the channel with the appropriate filter headers and close matching local streams.
  - `(AIT-CT7a)` If no filter is provided, `cancel()` must default to `{ own: true }`.

### Event Subscription

- `(AIT-CT8)` The session must support event subscriptions via `on(event, handler)` returning an unsubscribe function.
  - `(AIT-CT8a)` `view.on('update')` must notify when the view's message list changes (messages added, updated, or removed).
  - `(AIT-CT8b)` `tree.on('run')` or `view.on('run')` must notify on run lifecycle events (start and end) with the run ID, client ID, and end reason.
  - `(AIT-CT8c)` `on('error')` must surface non-fatal session errors as `ErrorInfo`.
  - `(AIT-CT8d)` If the session is closed, `on()` must return a no-op unsubscribe function.
  - `(AIT-CT8e)` `tree.on('ably-message')` must notify when a raw Ably message is received.

### Message Access

- `(AIT-CT9)` `view.flattenNodes()` must return the flattened conversation tree as `MessageNode[]` along the view's selected branches, including typed `msgId`, `parentId`, `forkOf`, `headers`, and `serial` fields.
- `(AIT-CT10)` `session.tree` must expose the conversation tree for structural queries (sibling listing, node lookup).
- `(AIT-CT10a)` `session.view` must expose a default view for message access with history pagination and branch navigation.
- `(AIT-CT10b)` `session.createView()` must return a new independent view over the same tree. Each view must have independent branch selections and pagination state.
- `(AIT-CT10c)` `session.close()` must close all views created via `createView()` in addition to the default view.

### History

- `(AIT-CT11)` `view.loadOlder(limit)` must load decoded messages from channel history using `untilAttach` for gapless continuity with the live subscription.
  - `(AIT-CT11a)` History messages must be inserted into the conversation tree and trigger an `update` notification on the view.
  - `(AIT-CT11b)` The `limit` option must control the number of complete domain messages returned, not the number of Ably wire messages fetched. The implementation must page through Ably history until enough complete messages are assembled.
  - `(AIT-CT11c)` Older messages are withheld from `view.flattenNodes()` until released by subsequent `loadOlder()` calls.

### Close

- `(AIT-CT12)` `close()` must unsubscribe from the channel, close all active run streams, clear all event handlers, and prevent further operations.
  - `(AIT-CT12a)` An optional `cancel` filter must publish a cancel message before teardown. Cancel publish failure must be swallowed (best-effort).
  - `(AIT-CT12b)` `close()` must be idempotent.

### Conversation Tree

- `(AIT-CT13)` The SDK must provide a `Tree` that materializes a branching conversation from a flat oplog of messages. The tree owns structural data (nodes, sibling groups) but not branch selection state.
  - `(AIT-CT13a)` Messages must be ordered by Ably serial (lexicographic). Messages without a serial (optimistic inserts) must sort after all serial-bearing messages.
  - `(AIT-CT13b)` Fork points must create sibling groups. Messages with the same `x-ably-parent` whose `x-ably-fork-of` chains trace to a common root form a sibling group. The default selection (when no view-local selection exists) must be the latest sibling.
  - `(AIT-CT13c)` `view.select()` must update the active branch at a fork point for that view. `view.flattenNodes()` must reflect the view's selections. Each view maintains independent selections; selecting in one view must not affect another.
  - `(AIT-CT13d)` `upsert()` must promote null serials to server-assigned serials on relay, re-sorting the message in the list.
  - `(AIT-CT13e)` When a view initiates a fork via `send()`, `regenerate()`, or `edit()`, it must auto-select the new sibling. If the optimistic insert creates the sibling immediately (edit), selection must update synchronously. If no optimistic insert occurs (regenerate), selection must be deferred until the server response creates the new sibling in the tree.
  - `(AIT-CT13f)` When a new fork appears from an external source (another view, another client), views that were already showing the original message must pin their selection to the currently-visible sibling. This prevents unintended branch shifts.

### Stream Router

- `(AIT-CT14)` The client session must route decoded events to per-run `ReadableStream`s via a stream router.
  - `(AIT-CT14a)` Terminal events (as determined by the codec's `isTerminal` predicate) must close the stream after enqueue.
  - `(AIT-CT14b)` `closeStream()` must close the controller and remove the entry, allowing the consumer to read the stream to completion.
  - `(AIT-CT14c)` `errorStream()` must error the controller with the given error and remove the entry. The consumer's reader will reject with the error.

### Optimistic Reconciliation

- `(AIT-CT15)` Own messages (matched by `x-ably-msg-id`) must be detected as relayed messages and reconciled with optimistic entries, not inserted as duplicates.

### Observer / Multi-Client Sync

- `(AIT-CT16)` Events from non-own runs must be accumulated through the codec's `MessageAccumulator` and upserted into the conversation tree, enabling multi-client synchronization.
  - `(AIT-CT16a)` Run lifecycle events (`x-ably-run-start`, `x-ably-run-end`) must update active run tracking for all clients on the channel.

### Active Run Tracking

- `(AIT-CT17)` `tree.getActiveRunIds()` or `view.getActiveRunIds()` must return currently active runs grouped by client ID.

### Wait for Run

- `(AIT-CT18)` `waitForRun()` must return a promise that resolves when all active runs matching the filter have completed. It must resolve immediately if no matching runs are active. If no filter is provided, it must default to `{ own: true }`.

### Channel Continuity

- `(AIT-CT19)` The client session must monitor the channel for continuity loss. Continuity is lost when the channel enters FAILED, SUSPENDED, or DETACHED, or re-attaches with `resumed: false`.
  - `(AIT-CT19a)` On continuity loss, all active own-run streams must be errored via `errorStream()` (AIT-CT14c) with code `ChannelContinuityLost` (104006), and the error must be emitted via `on('error')`.

### Channel Health

- `(AIT-CT20)` `send()` must throw with code `ChannelNotReady` (104007) if the channel is not in the ATTACHED or ATTACHING state.

### Presence

- `(AIT-CT21)` The client session must expose the underlying Ably channel's presence object via a read-only `presence` accessor. The accessor must return the channel's `RealtimePresence` directly, applying no AI-Transport-specific semantics, and must be usable before `connect()` is called.

### LiveObjects

- `(AIT-CT22)` The client session must expose the underlying Ably channel's LiveObjects entry point via a read-only `object` accessor. The accessor must return the channel's `RealtimeObject` directly, applying no AI-Transport-specific semantics, and must be usable before `connect()` is called. Operating on it requires the Realtime client to have been constructed with the LiveObjects plugin and the channel to have been attached with the object channel modes (AIT-CT23); when either is absent the underlying SDK throws and the session must not suppress the error.
- `(AIT-CT23)` The client session must accept an optional `channelModes` option listing additional Ably channel modes to request on the session's channel (e.g. the object modes required by AIT-CT22). The AI-Transport SDK defines a base set of channel modes equal to the set Ably grants by default when a channel is attached without requesting any modes on the wire — namely `publish`, `subscribe`, `presence`, and `presence_subscribe`. When `channelModes` is provided, the session must request the union of this base set and the supplied modes, deduplicated and in a deterministic order, and must apply the same resolved modes to every resolution of the channel's options for the channel's lifetime — including any auxiliary consumers such as React channel providers — so that the modes cannot be silently reverted; because the base set equals the default-granted set, requesting additional modes this way does not remove or alter any behaviour the channel would otherwise have. When `channelModes` is omitted, the session must not send any channel modes on the wire, so Ably grants the base set by default and the default attachment behaviour is preserved.

## Common Error Codes used by AI Transport {#common-error-codes}

This section contains error codes that are common across Ably, but the AI Transport SDK makes use of. The status code for the error should align with the error code (i.e. 4xxxx and 5xxxx shall have statuses 400 and 500 respectively).

The codes listed here shall be defined in any error enums that exist in the client library.

        // The request was invalid.
        // To be accompanied by status code 400.
        BadRequest = 40000,

        // Invalid argument provided.
        // To be accompanied by status code 400.
        InvalidArgument = 40003,

## AI Transport-specific Error Codes {#error-codes}

This section contains error codes that are specific to AI Transport. If a specific error code is not listed for a given circumstance, the most appropriate general error code shall be used according to the guidelines of `AIT-GP6`. For example `400xx` for client errors or `500xx` for server errors.

The AI Transport reserved error code range is `104000 - 104999`.

The codes listed here shall be defined in any error enums that exist in the client library.

        // Encoder recovery failed after flush — one or more updateMessage calls
        // could not recover a failed append pipeline.
        // To be accompanied by status code 500.
        // Spec: AIT-CD6
        EncoderRecoveryFailed = 104000,

        // A session-level channel subscription callback threw unexpectedly.
        // To be accompanied by status code 500.
        SessionSubscriptionError = 104001,

        // Cancel listener or onCancel hook threw while processing a cancel message.
        // To be accompanied by status code 500.
        // Spec: AIT-ST9a
        CancelListenerError = 104002,

        // A publish within a run failed (lifecycle event, message, or event).
        // To be accompanied by status code 500.
        // Spec: AIT-ST4b, AIT-ST5c, AIT-ST7b
        RunLifecycleError = 104003,

        // An operation was attempted on a session that has already been closed.
        // To be accompanied by status code 400.
        // Spec: AIT-CT4, AIT-CT12, AIT-ST2 (connect after close)
        SessionClosed = 104004,

        // The HTTP POST to the agent endpoint failed (network error or non-2xx response).
        // To be accompanied by status code 500.
        // Spec: AIT-CT3b
        SessionSendFailed = 104005,

        // The Ably channel lost message continuity — the channel entered
        // FAILED, SUSPENDED, or DETACHED, or re-attached with resumed: false.
        // To be accompanied by status code 500.
        // Spec: AIT-CT19a
        ChannelContinuityLost = 104006,

        // An operation was attempted but the channel is not in a usable state
        // (not ATTACHED or ATTACHING).
        // To be accompanied by status code 400.
        // Spec: AIT-CT20
        ChannelNotReady = 104007,

        // The source event stream threw during piping (e.g. LLM provider rate
        // limit, model error, network failure).
        // To be accompanied by status code 500.
        // Spec: AIT-ST6b3
        StreamError = 104008,
