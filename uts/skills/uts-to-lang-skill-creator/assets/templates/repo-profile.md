# Repo profile: <repo name>

- Repo: <path>, HEAD <sha> (clean | dirty: <files>)
- Spec clone: <path>, HEAD <sha> (clean | dirty: <files>); guide/skill last changed in <sha>; skill version <metadata.version>
- Date: <yyyy-mm-dd>; confirmed by the user on <date> (STOP-2)
- User goals: <modules and tiers, in priority order>

## Build, test and CI
| # | Item | Answer | Evidence (path, symbol or command → result) | Verified? |
|---|---|---|---|---|
| P-01 | Language(s) and version(s) | | | |
| P-02 | Build and test commands (build, build tests, all, class, single test, filter, target-qualified filter) | | | ran / unverified: <why> |
| P-03 | Test framework, runner, assertions, parameterisation, fixtures, teardown, static and runtime skip, fail idiom, collection rules | | | |
| P-04 | Test layout, naming, targets, shared test-support code | | | |
| P-05 | CI workflows, jobs → suites, matrix, network, submodules, secrets | | | |
| P-06 | Lint/format gates, static analysis, type checkers, warnings-as-errors | | | |
| P-07 | Developer and CI platforms; script runtime availability | | | |
| P-08 | Repo conventions; hand-maintained project files; synced manifests | | | |

## SDK structure for testing
| # | Item | Answer | Evidence | Verified? |
|---|---|---|---|---|
| P-09 | Async model; runner async support; virtual time | | | |
| P-10 | Threading, callback queues, internal-queue drain, compile-time concurrency checks | | | |
| P-11 | Every time source (timers, timed waits, delayed callbacks, clock reads) | | | |
| P-12 | Runner parallelism and how to serialise | | | |
| P-13 | Hooks: WS factory / HTTP / clock / network monitor / randomness (symbol, how set, when, per-client or global) | | | |
| P-14 | Internal-access mechanism and current use | | | |
| P-15 | API surface vs pseudocode, per module (rest / realtime / objects) | | | |

## Existing native test support
| # | Item | Answer | Evidence | Verified? |
|---|---|---|---|---|
| P-16 | Existing mocks, fakes, test doubles (capabilities, style, global?, users) | | | |
| P-17 | Existing test helpers (waits, polls, capture, log capture, assertions, factories) | | | |
| P-18 | Existing sandbox/integration support; fault-injection tooling | | | |
| P-19 | ably-common submodule (path, initialised, fixture files) | | | |
| P-20 | Existing UTS assets and their state | | | |
| P-21 | Sandbox access from developer machines and CI | | | |

## How the existing tests drive the SDK (step 1c)
| Kind | Test read (path, test name) | Pattern: create client / install double / wait / assert / clean up |
|---|---|---|
| REST request | | |
| Realtime connection state | | |
| Timer-driven behaviour | | |
| Negative assertion | | |
| Internal state | | |
| Sandbox integration | | |
| Plugin module | | |

- Doubles that already meet helper-spec semantics: …
- Doubles that differ (and how): …
- Race-free waits vs sampling or sleeping waits: …
- Known flakiness and workarounds: …

## API divergences per module
- rest: …
- realtime: …
- objects: … (implemented? plugin? typed? IDL followed?)

## Unknowns and questions for the user
- …
