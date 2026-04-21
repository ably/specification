# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

The Ably features specification — the authoritative, language-agnostic description of how Ably SDKs must behave. Consumed by SDK developers across all Ably SDK repositories (pub/sub, chat, objects).

## Files You'll Edit

The spec lives in `specifications/`:

- `features.md` — REST/Realtime spec; the main file.
- `chat-features.md` — Chat SDK spec.
- `objects-features.md` — LiveObjects spec.
- `api-docstrings.md` — language-agnostic docstrings that SDKs lightly edit and add to their code in order to support autocomplete and generate HTML documentation.
- `protocol.md`, `encryption.md`, `test-api.md`, `feature-prioritisation.md`, `index.md` — supporting docs, rarely edited.

## Previewing Locally

```sh
cd build
npm install           # once per clone
npm run build         # regenerate public/
open public/index.html
```

Hugo must be installed separately. There is no dev server — rebuild after edits.

## Spec Points — The Core Convention

Spec items are the unit of meaning in this repo. They look like this in Markdown:

```
- `(RTN1)` Top-level behaviour.
  - `(RTN1a)` Subclause detail.
```

The ID pattern is a letter prefix + integer + optional lowercase/number suffixes (e.g. `RTN1`, `REC2c6`, `CHA-V1`, `RSH3a2b`). These IDs are referenced from every SDK's source code and test suite, so **they are effectively a public API**.

See [`CONTRIBUTING.md` § Features Spec Points](CONTRIBUTING.md#features-spec-points) for the conventions around adding, modifying, removing, replacing, and deprecating spec items — read it before editing.

`npm run lint` enforces uniqueness of IDs across `features.md`, `chat-features.md`, `objects-features.md`. Duplicates typically arise from concurrent PRs being merged — when resolving, rename the later addition to the next available ID.

## Writing Principles

These principles are a WIP distilled from review comments left on the spec by Lawrence and Simon. Given this provenance, they skew towards things _not_ to do; more positive principles will be added over time.

### Scope

- Specify what SDKs must do, not what the server does. If a clause doesn't impose a requirement on an SDK, it doesn't belong here, even as "informational". For example, the `remainPresentFor` transport param, which specifies the duration that the server should wait before emitting a `leave` event after an abrupt disconnection, is a purely server-side behaviour (the client's only job in enabling this feature is to ensure that it sends the transport params that the user passes) and thus should not be mentioned in the spec.
- Keep the spec self-contained. Don't tell the reader to consult another SDK's source code to understand a clause.
- Don't prescribe tests ("A test should exist that…"). State the requirement; let implementers decide how to verify it.

### Precision

The general principle is to reduce ambiguity as much as possible for implementers, to maximise consistency between implementations. Here are some concrete examples.

- Use RFC 2119 keywords precisely. The preamble of `features.md` and `chat-features.md` declares that the keywords carry their RFC 2119 meaning whether lowercase or uppercase, and existing text is overwhelmingly lowercase — match the surrounding style. Avoid "will" (ambiguous between requirement and consequence) and "can" (not an RFC 2119 keyword — use "may").
- Define every term you introduce. For example, don't say "retry the detachment cycle after a short pause" unless it's very clear from context what a "detachment cycle" means.
- Be concrete. For example, no "a short pause" — give a duration.
- When specifying a sequence of actions that the SDK must perform, make it clear whether the order in which they are performed matters.
- Defer to other standards where possible; for example, when specifying how to percent-encode URL path variables, reference the rules and procedures of RFC 3986.

### Errors

- Whenever the specification states that the SDK must create an `ErrorInfo` (whether to throw it or to populate a `reason`), it must be explicit about which `code` and `statusCode` to use.
- When choosing a `code`, look for the most appropriate error code in `errors.json` in the `ably-common` repository. If you haven't been told where to find a local copy of this repository, ask the user. If you can not find an appropriate error code, ask the user how to proceed.
- When choosing a `statusCode`, try to proceed by analogy with other similar errors. Explain your logic to the user and ask them for clarification if the correct `statusCode` is unclear. (TODO: This is a bit hand-wavey because I — Lawrence — don't have a great sense of our rules for choosing status codes and often end up just choosing by analogy. But I imagine we can offer Claude better rules here.)

### Structure

- DRY via cross-reference. If a rule applies in two places, define it once and reference it.
- TODO make sure we're covering the rules re updating docstrings and IDL; double-check the CONTRIBUING.md section to make sure it includes IDL too, and link to it
- Rationale ("why") belongs in a design record, not in the normative clause.
- Overview clauses whose rules are given by subclauses should be marked non-normative so readers don't implement the summary.
- If there exists some invariant that the SDK maintains (for example, that internal property `foo` is non-nil if and only if internal property `bar` has a specific value), then use a non-normative clause to explain the existence of this invariant, and normative clauses to explain the behaviours that the SDK needs to perform in order to maintain this invariant.

### Exceptions to rules

- We sometimes bend the rules about immutability of specification points. In particular, if a spec point (or an entire spec document) is very new or has been implemented by a small (possibly zero) number of SDKs, then we may just modify or delete spec points without adding mutation markers in order to reduce spec point churn, and fix up the references in the affected SDKs. If you're unsure about whether it's OK to bend the rules for a given modification, ask the user.

## Future direction: Universal Test Suite and feature discoverability

This section describes an intention for how the specification will evolve in the future, and what considerations should be made when adding new features in order to track the work needed for this future direction.

The intention is that the following will exist:

1. A _Universal Test Suite_ (UTS): a pseudo-code set of tests that we intend to use LLMs to port to all of our SDKs
2. A _feature discoverability mechanism_: an authoritative list of all Ably features, where a _feature_ is some behaviour that a client SDK is able to provoke, even if the SDK's only role is to relay a request that triggers behaviour on the server; a representative example is the aforementioned `remainPresentFor` transport param

As mentioned in the "Scope" section above, features that do not require any specific behaviour from a client SDK do not currently belong in the specification. However, when adding a new feature, if it becomes clear that the feature requires no new specification points, a sub-issue should be added to the Jira issue [PUB-3652](https://ably.atlassian.net/browse/PUB-3652), to ensure that, once the UTS and feature discoverability mechanism exist, this feature is covered by both. The title of the issue should be "Add non-spec feature to UTS and discoverability: <feature name>", e.g. "Add non-spec feature to UTS and discoverability: remainPresentFor".
