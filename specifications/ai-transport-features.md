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
