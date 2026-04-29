# CLAUDE.md

## What This Is

The Ably features specification — the authoritative, language-agnostic description of how Ably SDKs must behave. Consumed by SDK developers across all Ably SDK repositories (pub/sub, chat, objects).

## Files You'll Edit

The spec lives in `specifications/`:

- `features.md` — REST/Realtime spec; the main file.
- `chat-features.md` — Chat SDK spec.
- `objects-features.md` — LiveObjects spec.
- `api-docstrings.md` — language-agnostic docstrings that SDKs lightly edit and add to their code in order to support autocomplete and generate HTML documentation.
- `protocol.md`, `encryption.md`, `test-api.md`, `feature-prioritisation.md`, `index.md` — supporting docs, rarely edited.

## Spec Points — The Core Convention

See [`CONTRIBUTING.md` § Features Spec Points](CONTRIBUTING.md#features-spec-points) for the conventions around adding, modifying, removing, replacing, and deprecating spec items — you must read this before editing.

The contributing file describes how to run the linter. You should run this after adding any new spec items, it enforces uniqueness of spec IDs. Duplicates often arise from concurrent PRs; when resolving these, rename the later addition to the next available ID. (Don't run a local development server unless the user specifically asks you to. If they do, you may need to install hugo explicity, it is not done by npm install).

Spec items are the unit of meaning in this repo. They look like this in Markdown:

```
- `(RTN1)` Top-level behaviour.
  - `(RTN1a)` Subclause detail.
```

The ID pattern is a letter prefix + integer + optional lowercase/number suffixes (e.g. `RTN1`, `REC2c6`, `CHA-V1`, `RSH3a2b`). These IDs are referenced from every SDK's source code and test suite, so they are effectively a public API.

The main features spec is divided into sections, each about a different broad area, with its own spec prefix, eg RSL for Channel features in the REST client. When adding a new spec item, search thoroughly for existing relevant spec items, and add the new one in an appropriate place, which might be as a new sub-item nested under an existing one, or a new top-level item placed after related ones. Note that features exposed in both rest and realtime clients will need spec items in both, though the realtime items may reference the REST ones to avoid unnecessary duplication for items which work identically in both.

## Writing Principles

### Scope

The job of the SDK spec is to specify SDK behaviour.

In particular, it is _not_:
- user-facing documentation, or
- a description of how the platform taken as a whole (including the server) works, or
- a record of design decisions.

So if a clause doesn't impose a requirement on an SDK, or otherwise is not actionable for an SDK dev, it doesn't belong.

For example, the set of supported channel params is server-defined; the client's only job is to ensure that it correctly encodes and sends the ones that the user passes. So the spec should not try to list supported channel params, though it may (and does in RTL4j2) give an example of one that causes an easily-testable behaviour change, to allow an SDK developer to write a test ensuring that it's encoding sending them correctly.

The spec should not refer to any particular SDK's source code, nor to JIRA tickets.

The spec should not try to comprehensively describe what tests should exist. State the requirement; let implementers decide how to verify it (it goes without saying that the implementation should be tested). The spec may occasionally describe a particular test if that would not otherwise be obvious to an implementer (such as mentioning an easily-testable channel param).

Much of the existing spec (written long ago) violates these requirements. Adhere to them when writing new spec items or editing existing ones, but don't fix ones unrelated to your current task, the quality level will be improved gradually as parts are touched.

### Precision

The general principle is to reduce ambiguity as much as possible for implementers, to maximise consistency between implementations. Concretely:

- Use RFC 2119 keywords precisely. Avoid "will" (ambiguous between requirement and consequence) and "can" (not an RFC 2119 keyword — use "may").
- Be concrete about what the SDK should do. For example, "retry the attach cycle", if that isn't a term you've already defined, might be ambiguous. "immediately send a new `ATTACH` protocol message and transition the channel to the `ATTACHING` state" would be better.
- When specifying a sequence of actions that the SDK must perform, make it clear whether the order in which they are performed matters.
- Defer to other standards where possible; for example, when specifying how to percent-encode URL path variables, reference the rules and procedures of RFC 3986.

### Errors

- Whenever the specification states that the SDK must create an `ErrorInfo` (whether to throw it or to populate a `reason`), it must be explicit about which `code` and `statusCode` to use.
- When choosing a `code`, look for the most appropriate error code in `errors.json` in the `ably-common` repository. If there is no local copy at ../ably-comon/, you can see it at https://raw.githubusercontent.com/ably/ably-common/refs/heads/main/protocol/errors.json. If you can not find an appropriate error code, ask the user if you can create a new code (with an ably-common PR).
- When choosing a `statusCode`, in many cases the `code` is an extended `statusCode`, in which case you can just take the first three digits e.g. `40160` -> `401`. Where that's not the case, look at what other similar errors do and pick something sensible.

### Structure

- DRY via cross-reference. If a rule applies in two places, define it once and reference it. (Generally, realtime spec items should reference REST spec items rather than vice versa).
- features.md includes an IDL at the bottom. If making any changes that change the public api (fields or method signatures), it must be changed there too.
- If a spec item would require sdks implementing it to need docstrings, these must be added in api-docstrings.md. See the relevant sections of CONTRIBUTING.md on how that file is structured.
- Overview clauses whose rules are given by subclauses should be marked non-normative so readers don't implement the summary.
- If there exists some invariant that the SDK maintains (for example, that internal property `foo` is non-nil if and only if internal property `bar` has a specific value), then use a non-normative clause to explain the existence of this invariant, and normative clauses to explain the behaviours that the SDK needs to perform in order to maintain this invariant.

### Exceptions to rules

Some of the rules about editing vs replacing spec items in CONTRIBUTING.md are flexible based on common sense. If you're not sure whether an exception is justified, ask the user.

### Exploring existing SDK behaviour

Sometimes to decide the best approach (e.g. to standardise some currently-inconsistent behaviour) you may need to explore what existing SDKs do. When doing this, the relevant code SDK repositories are (in all cases under https://github.com/ably/ , also may have local copies as peer directories to the specification repo):

- ably-js
- ably-cocoa
- ably-java
- ably-go
- ably-python
- ably-ruby
- ably-ruby-rest
- ably-php
- ably-dotnet
- ably-flutter (wrapper)
- ably-rust (early-stage experimental)
- ably-swift (early-stage experimental)

Chat SDKs (also all under https://github.com/ably/):

- ably-chat-js
- ably-chat-swift
- ably-chat-kotlin

## Future direction: Universal Test Suite and feature discoverability

This section describes an intention for how the specification will evolve in the future, and what considerations should be made when adding new features in order to track the work needed for this future direction.

The intention is that the following will exist:

1. A _Universal Test Suite_ (UTS): a pseudo-code set of tests that we intend to use LLMs to port to all of our SDKs
2. A _feature discoverability mechanism_: an authoritative list of all Ably features, where a _feature_ is some behaviour that a client SDK is able to provoke, even if the SDK's only role is to relay a request that triggers behaviour on the server; a representative example is the aforementioned `remainPresentFor` transport param

As mentioned in the "Scope" section above, features that do not require any specific behaviour from a client SDK do not currently belong in the specification. However, when adding a new feature, if it becomes clear that the feature requires no new specification points, a sub-issue should be added to the Jira issue [PUB-3652](https://ably.atlassian.net/browse/PUB-3652), to ensure that, once the UTS and feature discoverability mechanism exist, this feature is covered by both. The title of the issue should be "Add non-spec feature to UTS and discoverability: <feature name>", e.g. "Add non-spec feature to UTS and discoverability: remainPresentFor".
