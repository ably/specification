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
- `(AIT-GP4)` A single shared Ably channel must be used per transport instance. All features (streaming, cancellation, history) operate over this shared channel.
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

- `(AIT-CD13)` The decoder must support a lifecycle tracker that synthesizes missing lifecycle events (e.g. `start`, `start-step`) when a client joins a stream mid-turn. Phases must be emitted in configuration order before content events.

### Encoder Hooks

- `(AIT-CD14)` The encoder core must invoke an optional `onMessage` hook before each Ably message is published. The hook receives the message before it is sent to the channel writer. If the hook throws, the encoder must catch and log the exception without interrupting the publish.
