# 3. Phase 1: understand the repo

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention). Links that climb out of the skill directory are spec-repo paths: resolve them against the spec clone, not against this file's installed location.

**Goal:** a written, user-confirmed Repo profile that explains how the SDK is built, tested and mocked today, in enough depth to design the harness from it. This phase is mandatory and comes before anything else: the harness you design in Phase 2 should extend what the repo already has, follow its test style, and plug into its build and CI, and the skill's file locations, idioms and commands all derive from this profile.

## 3.1 Step 1a: read the repo's own instructions

Read these first, if they exist, and follow them for the rest of the run: `CLAUDE.md` (root and nested), `AGENTS.md`, `CONTRIBUTING.md`, `README.md`, `.editorconfig`, any `docs/` or `Docs/` pages about testing, and any existing `.claude/`, `.agents/` or `.codex/` directory (settings, skills, commands). Record any instruction that constrains you (for example "don't edit project file X", "use helper Y instead of Z").

## 3.2 Step 1b: answer the discovery checklist

Answer every item. For each, record the answer and its evidence in the Repo profile. The "how to find it" column lists starting points; follow the evidence wherever it leads.

**Build, test and CI**

| # | Find | How to find it |
|---|---|---|
| P-01 | **Language(s) and version(s)**: SDK language, test language (they can differ), toolchain version, language mode or edition | Toolchain pins (`global.json`, `.python-version`, `.nvmrc`, `go.mod`, `rust-toolchain*`, `Package.swift` tools version, Gradle `jvmToolchain`); `git ls-files` extension counts |
| P-02 | **Build system and commands**: build the SDK; build the tests; run all tests; run one class; run one test; run by filter; target-qualified filters | Build files (`*.sln`/`*.csproj`, `pyproject.toml`/`tox.ini`/`noxfile.py`, `package.json` scripts, `build.gradle*`, `Package.swift`, `Makefile`, wrapper scripts); CI workflow steps; CONTRIBUTING. **Run** the build-tests and single-class commands and record the exit status. For interpreted languages, "build the tests" means collection (e.g. `pytest --collect-only`) plus the repo's type checker. Record the command that lists collected tests (e.g. `pytest --collect-only -q`, `dotnet test --list-tests`) |
| P-03 | **Test framework(s)**: runner, assertion library, parameterisation, suite-level fixtures (before/after all), teardown hooks, **static and runtime skip idioms**, unconditional-fail idiom, **collection rules** (what names and files the runner picks up) | Test dependencies in the build files; existing tests; the runner's config (`pytest.ini`, `conftest.py`, `xunit.runner.json`, `jest.config.*`). Check whether a runtime skip needs an extra package (guide [7.1](../../../docs/translator-skills/writing-translator-skills.md#71-three-acceptable-end-states)) |
| P-04 | **Test layout and naming**: test projects/targets/source sets, their directories, naming conventions for files, classes and methods, shared test-support projects, and which test targets can see which code | Directory listing of test roots; build files for test targets |
| P-05 | **CI**: every workflow that builds or tests; which job runs which suites; OS and runtime matrix; network access; submodule checkout; secrets; how a new suite or test target would be picked up | `.github/workflows/*`, other CI configs; follow each test step to the command it runs |
| P-06 | **Lint, format and strictness gates**: EditorConfig, formatters, linters, static analysis, type checkers; whether CI treats warnings as errors; whether the local build is laxer than CI | Lint configs, `Makefile` lint targets, CI lint jobs, compiler flags in build files |
| P-07 | **Developer and CI platforms**: which OSes developers and CI use; whether the script runtime the skill will use (e.g. `python3`) is available on all of them; where a proxy binary would have to run | CONTRIBUTING, CI matrix, existing scripts |
| P-08 | **Repo conventions**: licence or file headers, comment style, line endings, commit message rules, files kept in sync (e.g. several dependency manifests), project files not discovered by the build | CLAUDE.md, CONTRIBUTING, `.editorconfig`, `.gitattributes`, recent commits |

**How the SDK is structured for testing**

| # | Find | How to find it |
|---|---|---|
| P-09 | **Async model**: callbacks, futures/promises, `async`/`await`, coroutines; whether SDK APIs are callback-based, async, or both; the test runner's async support and its mode; whether the runner **virtualises time** | SDK public API signatures; runner plugins (e.g. pytest-asyncio mode); existing async tests (guide [2.6](../../../docs/translator-skills/writing-translator-skills.md#26-understand-the-sdks-concurrency-model-must)) |
| P-10 | **Concurrency and threading**: which thread, queue or loop SDK callbacks run on; whether listeners can run concurrently with the test body; how to drain the SDK's internal work queue (this becomes `process_pending_events()`); whether the language checks concurrency safety at compile time | SDK source: dispatch, executor or event-loop code; how existing tests wait for callbacks |
| P-11 | **Time model**: **every time source** the SDK uses: timers, timed blocking waits, scheduled or delayed callbacks, wall-clock and monotonic reads | Grep the SDK source for the language's sleep, timer, wait, delay and now APIs; list each call site's owner (guide [2.1](../../../docs/translator-skills/writing-translator-skills.md#21-sdk-test-hooks-must)) |
| P-12 | **Runner parallelism**: are tests run in parallel by default, and how is it turned off per suite? | Runner docs and config; existing serialisation attributes or collection settings |
| P-13 | **Injection points (test hooks)** for each of: WebSocket transport, HTTP client, clock/timers, reachability/network monitor, randomness (retry jitter, fallback-host shuffle). For each: symbol, how it is set (option, constructor argument, global, subclass), whether it is set at client construction, per-client or process-global, test-only or public | SDK client-options and any debug/test-options types; constructors of the transport, HTTP, timer and network layers; existing tests that replace them |
| P-14 | **Internal-access mechanism**: how tests reach non-public code, and where the repo already uses it | e.g. `InternalsVisibleTo`, `@testable import`, private headers and module maps, same-package placement, `_`-prefixed conventions; grep for existing test-only accessors |
| P-15 | **SDK API surface vs the pseudocode, per module**: client constructors and options, async return types, the error type and how `ErrorInfo` fields (`code`, `statusCode`, `message`, cause) are read, enum renderings, protocol-format option (JSON vs msgpack), `endpoint` vs explicit hosts, the plugin mechanism. For `objects` (LiveObjects): is it implemented, where, as a plugin or built in, typed or dynamic, and which spec IDL it follows | Public API; compare with the pseudocode in two or three specs per module and with `specifications/features.md` / `objects-features.md` in the clone. Produce a short divergence list per module |

**Existing native test support**

| # | Find | How to find it |
|---|---|---|
| P-16 | **Existing mocks, fakes and test doubles**: for HTTP, WebSocket/transport, clock/timers, network monitor, randomness, delta decoding, plugins. For each: file and symbol, what it can do (capture requests or frames, inject responses or server messages, simulate refusal, timeout, DNS failure, disconnect), its style (handler/callback, queued responses, await), whether it is process-global, and which native tests use it | Search the test roots for `Mock`, `Fake`, `Stub`, `Test*Transport`, `*Handler`, clock or timer types; follow the hook symbols from P-13 to their test-side implementations |
| P-17 | **Existing test helpers**: state waits, polling helpers, async-to-sync bridges, event capture or recorder types, log capture, custom assertions, client factories, test-options builders | Shared test-support code; base test classes; helpers used by many test files |
| P-18 | **Existing sandbox and integration support**: how native integration tests provision a sandbox app (from `test-app-setup.json`?), point clients at the sandbox, retry, clean up; any proxy or fault-injection tooling | Integration test directories and their fixtures; environment variables they read |
| P-19 | **`ably-common`**: submodule path and name (it may not be called `ably-common`), whether it is initialised, and whether `test-resources/test-app-setup.json`, `msgpack_test_fixtures.json` and `encoding.json` are present | `.gitmodules`; `git submodule status`; list the files |
| P-20 | **Existing UTS assets and their state**: any UTS harness, UTS-derived tests (`UTS:` tags), `deviations.md` files, previous `uts-to-*` skills in this repo. For each asset: does it compile, do its tests pass, which spec SHA do headers name, which helper-spec symbols exist | `grep -rn "UTS:" <test-roots>`; search for `MockWebSocket`, `MockHttpClient`, `SandboxApp`, `uts-proxy`, `deviations.md`, `.claude/skills/uts-*`, `.agents/skills/uts-*`, `.codex/skills/uts-*` |
| P-21 | **Sandbox access**: whether tests can reach `sandbox.realtime.ably-nonprod.net` from developer machines and CI | Existing integration tests; CI network settings (guide [2.3](../../../docs/translator-skills/writing-translator-skills.md#23-sandbox-provisioning-and-fixtures-must-for-integration-tiers)). Probing the sandbox, or running existing integration tests for P-20, is network access: **STOP-6** first |

For a first pass, run `python3 <skill-dir>/scripts/survey_repo.py <repo> [<test-root> …]` (read-only; it prints the HEAD SHA and dirty state, extension counts, likely test roots, submodule status, candidate mocks and fakes, existing `UTS:` tags and existing skills). It is a starting point, not an answer: adapt or extend the searches for the repo's language, and record each answer's evidence.

## 3.3 Step 1c: study how the existing tests drive the SDK

The checklist tells you what exists; this step tells you how it is used. Read, in full, at least one existing native test of each kind below (if the repo has it), and write down the pattern each follows: how the client is created, how the double is installed, how the test waits, how it asserts, how it cleans up.

| Kind | What to learn from it |
|---|---|
| A REST test that checks an outgoing request | How HTTP is intercepted; how requests are captured and responses injected |
| A realtime test that drives connection state | How the transport is replaced; how server messages are injected; how state changes are awaited |
| A test of timer-driven behaviour (retry, timeout, heartbeat) | Whether time is faked or real, and how it is advanced |
| A test that checks something did **not** happen | How the test flushes pending work before a negative assertion |
| A test that reaches internal state | The internal-access mechanism in practice |
| An integration test against the sandbox | Provisioning, client options, timeouts, cleanup |
| A test from each plugin or optional module (e.g. LiveObjects) | How the plugin is registered in tests; its own test helpers |

Then answer, in the Repo profile:

- Which existing doubles behave like the helper specs need (see the semantics in [4.3](phase-2-design-harness.md#43-step-2c-map-each-helper-spec-to-native-code)), and which differ?
- Which existing waits are race-free (subscribe first, then check), and which sample state or sleep?
- Where do the existing tests flake or carry workarounds (retries, sleeps, `@Ignore`/skip with a reason, comments about races)? These mark concurrency or timing problems the harness must avoid.

## 3.4 Step 1d: write and confirm the Repo profile

Write `repo-profile.md` from the [repo-profile template](../assets/templates/repo-profile.md). Record the repo's HEAD SHA and whether it is dirty. Then **STOP-2**: show the user the profile, highlight every "unknown" and every inference, and ask them to confirm or correct it. Apply their corrections before continuing.

**Done when:** every P-row has an answer with evidence or an explicit "unknown" with a question; the build-tests and single-class commands have been run (or marked unverified with the reason); the existing-test patterns of 3.3 are written down; the user has confirmed the profile.
