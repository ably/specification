# UTS-to-Lang Skill Creator

This is a step-by-step procedure for an LLM agent (for example Claude Code) to create a `uts-to-<lang>` translator skill for one Ably SDK repository. [Writing UTS Translator Skills](writing-translator-skills.md) (below, **the guide**) says **what** a good translator skill is and why. This document says **how** to build one, in what order, with what checks, and where to stop and ask the user. It doesn't repeat the guide: wherever the reason or the detailed requirement lives in the guide, this document links to it, and you must read the linked section.

The order is fixed, because each step stands on the one before it:

1. **Understand the repo:** how the SDK is built, tested and mocked today (Phase 1).
2. **Design the UTS test infrastructure (the harness)** for this language from what you found: what to reuse, what to wrap, what to build (Phase 2).
3. **Build and verify the harness** (Phase 3).
4. **Create the `uts-to-<lang>` skill on top of it** (Phases 4 and 5).
5. **Validate the skill with pilot translations** (Phase 6), then report (Phase 7).

The harness and the skill are **one deliverable** (guide [section 2](writing-translator-skills.md#2-the-harness-uts-test-infrastructure)): the skill isn't complete until the harness's per-tier smoke tests and helper self-tests (guide [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)) are green, and wired into CI, at every tier the skill supports. The harness is designed from the repo's existing test setup: every capability is reused, wrapped, extended or built ([4.2](#42-step-2b-assess-each-capability-reuse-wrap-extend-or-build)).

A harness designed without studying the repo's existing tests duplicates or fights them. A human may skim this document to see what the agent will do and where it will ask for decisions.

## Contents

1. [Purpose and how to use this procedure](#1-purpose-and-how-to-use-this-procedure)
2. [Ground rules](#2-ground-rules)
3. [Phase 1: understand the repo](#3-phase-1-understand-the-repo)
4. [Phase 2: design the harness](#4-phase-2-design-the-harness)
5. [Phase 3: build and verify the harness](#5-phase-3-build-and-verify-the-harness)
6. [Phase 4: skill design decisions](#6-phase-4-skill-design-decisions)
7. [Phase 5: generate the skill files](#7-phase-5-generate-the-skill-files)
8. [Phase 6: validate the skill](#8-phase-6-validate-the-skill)
9. [Phase 7: final report and handover](#9-phase-7-final-report-and-handover)
10. [Maintenance](#10-maintenance)
- [Appendix A: Repo profile template](#appendix-a-repo-profile-template)
- [Appendix B: Gap table and harness design template](#appendix-b-gap-table-and-harness-design-template)
- [Appendix C: Design record template](#appendix-c-design-record-template)
- [Appendix D: Final report template](#appendix-d-final-report-template)
- [Appendix E: Acceptance checklist (guide section 13)](#appendix-e-acceptance-checklist-guide-section-13)
- [Appendix F: Glossary](#appendix-f-glossary)
- [Appendix G: Common failure modes and remedies](#appendix-g-common-failure-modes-and-remedies)

---

## 1. Purpose and how to use this procedure

### 1.1 Who reads this

- **The executor** is an LLM agent working inside the target SDK repository, with shell access, file read/write access, and the ability to ask the user questions, running on an Opus-class model ([2.8](#28-model-tier-and-sub-agents)). Every instruction below is addressed to it ("you").
- **The user** is an SDK engineer who owns the target repository. They answer the questions at the stop points and approve every change outside the skill directory.
- **The lead reviewer** may skim the working records (Repo profile, Harness design, Design record, Final report) instead of the whole conversation.

### 1.2 Invocation

The user starts a run with one sentence, for example:

```
Follow <spec-clone>/uts/docs/translator-skills/uts-to-lang-skill-creator.md to create a uts-to-<lang> skill for this repo.
```

`<spec-clone>` is the user's local clone of `ably/specification`. If the user also states goals ("objects unit tier first", "rest and realtime only"), record them as inputs.

### 1.3 Required inputs

| Input | Example | If missing |
|---|---|---|
| Target SDK repo path | the current working directory | Ask. Don't assume the working directory is the SDK repo; confirm it has SDK sources and tests |
| Language (and the skill name it implies) | C# → `uts-to-csharp`; Python → `uts-to-python` | Infer from the repo in Phase 1, then confirm |
| Local spec clone path | `~/src/specification` (the directory that contains `uts/` and `specifications/`) | **Stop and ask** ([STOP-1](#23-stop-points)). Never fetch the spec or the UTS docs from GitHub instead |
| User goals: modules and tiers wanted first | "realtime unit, then rest unit; objects later" | Ask. Default to every module (`rest`, `realtime`, `objects`) and every tier the SDK can support, prioritised by the user |
| Model tier | The session's model, Opus-class ([2.8](#28-model-tier-and-sub-agents)) | Take it from your environment if it states your model; otherwise ask. If the model isn't Opus-class: **STOP-1** |
| Local clones of ably-cocoa and ably-java (optional) | Clones that contain commits `b5074d9b` and `0ff24017` | Not needed to start. Ask only if you reach the last-resort reference reads ([2.1](#21-your-inputs)); without clones, those reads go to GitHub after **STOP-6** |

### 1.4 Outputs

1. **The harness** for this language, in the target repo: the shared test library implementing the helper specs, wait and assertion helpers, sandbox and proxy helpers, module helpers, the per-tier smoke tests and helper self-tests (guide [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must); permanent and run in CI), a harness README with its Known gaps and, with explicit approval, SDK test hooks. Built in Phase 3, unless the user scopes it down at [STOP-3](#23-stop-points).
2. **The skill**, at `.claude/skills/uts-to-<lang>/` unless the Design record says otherwise: `SKILL.md`, `uts-package-mapping.json`, `scripts/resolve_uts.py`, `scripts/audit_translation.py`, `references/<module>-mapping.md` and, if shipped (D-19), `scripts/scan_constructs.py` (layout: guide [3.1](writing-translator-skills.md#31-layout)).
3. **Pilot-translated tests**, one spec per available tier, produced by the new skill in Phase 6.
4. **Four working records** (*Procedure recommendation*), written as Markdown files in the working-records directory (default `.claude/skills/uts-to-<lang>/generation/`; confirmed in Phase 4, decision D-24):
    - `repo-profile.md` ([Appendix A](#appendix-a-repo-profile-template));
    - `uts-infra-design.md`: the gap table, the harness design and the build log ([Appendix B](#appendix-b-gap-table-and-harness-design-template));
    - `design-record.md` ([Appendix C](#appendix-c-design-record-template)), which also holds the decision log;
    - `final-report.md` ([Appendix D](#appendix-d-final-report-template)), with the acceptance checklist ([Appendix E](#appendix-e-acceptance-checklist-guide-section-13)).

Write them at the default location from Phase 1 on; if D-24 chooses another location, move the files then. They are working notes, not skill files, so writing them before STOP-7 is allowed.

The working records are what a later agent reads to maintain or regenerate the skill ([section 10](#10-maintenance)), so keep them accurate as you go, not only at the end.

### 1.5 Intent

The guide's intent ([introduction](writing-translator-skills.md)) applies to this procedure too: if the skill you generate produces a wrong test, fix the skill, its notes or the harness and regenerate. Never hand-fix a pilot test and call the skill done.

### 1.6 Which document wins

| Question | Authority |
|---|---|
| What a faithful translation is; how a failure is diagnosed; the `deviations.md` format | [`writing-derived-tests.md`](../writing-derived-tests.md) |
| What pseudocode means | [`uts/README.md`](../../README.md) and [`writing-test-specs.md`](../writing-test-specs.md) |
| Integration and proxy tiers | [`integration-testing.md`](../integration-testing.md), [`proxy.md`](../proxy.md) |
| Mock and fixture behaviour | the helper specs: [`mock_http.md`](../../rest/unit/helpers/mock_http.md), [`mock_websocket.md`](../../realtime/unit/helpers/mock_websocket.md), [`mock_vcdiff.md`](../../realtime/unit/helpers/mock_vcdiff.md), [`standard_test_pool.md`](../../objects/helpers/standard_test_pool.md) |
| What the harness and the skill must contain, and why | the guide ([How it relates to the other UTS docs](writing-translator-skills.md#how-it-relates-to-the-other-uts-docs)) |
| How and in what order you build them | this document |
| The SDK's actual API | the SDK source (guide [3.1](writing-translator-skills.md#31-layout), "The notes are a map, not an authority") |
| Questions none of the above answer, as a last resort only | The reference implementations, under [2.1](#21-your-inputs): never an authority |

If two documents disagree, follow the higher one in the table (and **STOP-11** if the conflict changes what you would build or generate), record the conflict in the Design record, and list it in the Final report under "Spec-repo doc issues". Don't patch the spec repo. A disagreement between a reference implementation and the guide or the UTS docs is never a STOP-11: follow the guide, and record the disagreement with the read ([2.1](#21-your-inputs)).

**Procedure recommendations.** Where this document adds detail the guide doesn't have (for example: the working-records files and their location, tier-readiness data in the mapping, a mandatory `specRepo`, and requiring the audit's end-at-heading rule), it is marked *Procedure recommendation*: this document's way of meeting the guide, not a guide requirement. Follow it unless the user decides otherwise, and record any departure in the decision log. Everything else either links to the guide or is procedure (order, checks, stop points).

---

## 2. Ground rules

### 2.1 Your inputs

You work from four primary sources:

1. this document;
2. the guide;
3. the local spec clone: the UTS docs (`uts/README.md`, `uts/docs/`), the helper specs, the UTS corpus (`uts/rest`, `uts/realtime`, `uts/objects`) and, for API and spec-error questions, the features specs under `specifications/`;
4. the target SDK repo.

and, only as a last resort, the reference implementations below.

**Reference implementations (last resort).** The guide distils the lessons of the two existing skills and harnesses, so you shouldn't need them. You MAY consult them, read-only, at the commits the guide pins. The guide's [Reference implementations (last resort)](writing-translator-skills.md#reference-implementations-last-resort) lists the repos, paths and links. Consult them only when all of the following hold:

1. You have searched this document, the guide, the UTS docs and the helper specs, and they don't answer the question.
2. You can read them without unapproved network access. Either read them from local clones the user named (input in [1.3](#13-required-inputs)) with `git -C <clone> show <sha>:<path>` and `git -C <clone> ls-tree -r --name-only <sha> -- <path>`, never checking out, pulling or fetching on the user's behalf. Or read them from GitHub after **STOP-6**; the user may approve reference reads once for the whole run, and you record that approval. If a clone lacks the pinned commit, fetching it is network access too.
3. You take a **pattern**, not text: how something was structured or solved. Never copy, port or translate code, scripts, prose, tables or examples verbatim. Write every hook, helper, script, rule and example yourself, in this language's idioms, from the guide, the UTS docs and the target repo.
4. You check what you took against the guide's [Patterns to avoid](writing-translator-skills.md#patterns-to-avoid), and against the guide and the UTS docs, which always win ([1.6](#16-which-document-wins)). If you read `main` instead of the pinned commits, record the revision and re-check against Patterns to avoid.
5. You record each consultation in the Design record ("Reference-implementation reads": repo, commit, path, question, what you learned, how you checked it), and list it in the Final report as a guide gap: a candidate guide improvement.

A read-only consultation needs no stop point of its own. Where the guide names another SDK's file, script, helper or test (as the origin of a lesson, or in the Swift and Kotlin cells of its construct tables), it is background, not a template. If the references don't resolve the question either, or the only answer they give departs from the guide, **STOP-12**. The generated skill never consults them (D-22), and the pilot never does either ([8.3](#83-pilot-translate-one-spec-per-available-tier)).

### 2.2 What you may change

| Action | Allowed? |
|---|---|
| Create and edit files under the skill directory and the working-records directory | Yes |
| Create new test-only harness code (shared test library, module helpers, smoke tests, UTS test-project wiring) | Only after the user approves the harness design at [STOP-3](#23-stop-points), and only within the scope they approved |
| Change existing test-support code that the SDK's own tests use (shared fakes, fixtures, base classes) | Only with explicit approval for each change, and never in a way that changes behaviour for the existing tests. Prefer wrapping or extending to editing |
| Change SDK production code, including adding test hooks or raising visibility | **Only with explicit approval for each change** ([STOP-4](#23-stop-points)). Present the proposal first ([4.6](#46-step-2f-propose-the-sdk-test-hooks)) |
| Change CI workflows, build scripts that CI runs, or dependency manifests (including adding a test dependency) | **Only with explicit approval** ([STOP-5](#23-stop-points)). Otherwise write the change as a suggestion in the Final report |
| Edit project or solution files needed to register new test files or projects (`.sln`, `.csproj`, `.projitems`, an Xcode project, etc.) | Only with explicit approval ([STOP-5](#23-stop-points)), recorded in the Design record (D-20). If the user declines, give them the exact entries to add, wait until they confirm, and list them in the Final report |
| Stage, commit, push, branch, or open a PR | **No, unless the user asks** |
| Edit anything in the spec clone | No. Report spec errors and doc gaps in the Final report with a draft fix |
| Delete or rewrite existing tests or existing UTS-derived tests | No, unless the user asks. Report their state in the Repo profile |
| Run the full test suite, or any integration or proxy test (network, sandbox, proxy binary download) | Ask first ([STOP-6](#23-stop-points)) |
| Fetch from the network for anything other than what the user approved (sandbox, proxy binary, dependencies, reference-implementation reads under [2.1](#21-your-inputs)) | No |

### 2.3 Stop points

At a stop point, present what you found and the options, then wait for the user's answer. Record the question and the answer in the decision log ([Appendix C](#appendix-c-design-record-template)).

| ID | Phase | When | What you present |
|---|---|---|---|
| **STOP-1** | Start | A required input is missing, or the session's model isn't Opus-class ([1.3](#13-required-inputs), [2.8](#28-model-tier-and-sub-agents)) | The missing input (or the model found) and why it's needed |
| **STOP-2** | 1 (end) | The Repo profile is written | The profile, for confirmation or correction |
| **STOP-3** | 2 (end) | The harness design is written | The gap table, the design and three options: (a) build the missing harness now, (b) plan it only, (c) scope the skill to the tiers possible today |
| **STOP-4** | 3 onwards | Before any SDK production-code change | The hook or visibility proposal ([4.6](#46-step-2f-propose-the-sdk-test-hooks)) |
| **STOP-5** | 3 onwards | Before any CI, build-script, dependency-manifest or project/solution-file change (including creating a test project or adding one to a solution) | The diff you propose and why |
| **STOP-6** | 1 onwards | Before any network access (running network tests, reading or downloading proxy releases, reading a reference implementation on GitHub or fetching its commit, [2.1](#21-your-inputs)), or running a full suite | The command, the expected duration, what it touches; for reference reads, whether the approval covers the whole run |
| **STOP-7** | 3 (end) | The harness is built | The build results (smoke tests and self-tests per tier, CI wiring, updated tier feasibility), before any skill file is written |
| **STOP-8** | 4 (end) | The Design record is written | The Design record, for confirmation |
| **STOP-9** | 5 | Pseudocode constructs, helper symbols or spec shapes you can't map ([7.4](#74-step-5d-fill-the-construct-catalogue)); batch everything one scan finds into one stop | Each construct, where it occurs, a proposed rendering |
| **STOP-10** | 3, 6 | A Phase 3 build row or a pilot spec hits its attempt bound ([5.2](#52-step-3b-build-in-order-with-acceptance-checks), [8.4](#84-fix-the-cause-then-regenerate)), or the pilot reveals a suspected UTS spec error | A summary: the failure, what you tried, your diagnosis (per `writing-derived-tests.md` Phase 2 for a test), the options, and a draft spec fix where relevant |
| **STOP-11** | Any | A conflict between the docs, or between the guide and the SDK, that changes what you would build or generate | Both statements, with paths and headings, and the reading you propose |
| **STOP-12** | Any | The guide, the UTS docs and the reference implementations ([2.1](#21-your-inputs)) together don't answer a question, or the only answer the references give would depart from the guide | The question; the guide and UTS sections you searched; the references you read (repo, commit, path) and what they showed; the reading you propose |

### 2.4 Never guess

- **Spec content:** quote the spec, a helper spec or a UTS doc from the clone, with its path and heading. Don't rely on memory of the Ably specification.
- **API signatures:** read the SDK source and the harness source before writing any call. A signature you haven't read is a guess.
- **Commands:** run every build, test, lint and script command you record, and record its exit status. A command you haven't run is marked "unverified" in the working records.
- **Facts about the repo:** every Repo profile entry has evidence (a file path, a symbol or a command and its output). "Unknown" is allowed only with the reason and a question for the user.
- **Undocumented corpus constructs:** the guide marks some constructs *(undocumented)*; their meaning is inferred from usage. Read each use in the corpus before choosing a rendering, and say in the catalogue that the meaning is inferred.
- **Reference-implementation reads:** what another SDK's skill or harness does is evidence of one SDK's choice, not of the spec or of this SDK. Confirm it against the guide or the UTS docs before relying on it. Where they are silent, record the choice as yours in the decision log, citing the read.

### 2.5 Record every decision

Every choice you make that isn't forced by the guide or the UTS docs goes into the decision log in the Design record, with the options, the choice, who made it (you or the user) and the reason. That includes harness choices in Phases 2 and 3 (reuse vs build, hook shapes, placement), not only the skill decisions in Phase 4. If a later phase changes an earlier decision, add a new log entry that supersedes the old one; don't edit history.

### 2.6 Pin the spec clone

At the start of the run:

```sh
git -C <spec-clone> rev-parse HEAD                  # full SHA
git -C <spec-clone> status --porcelain -- uts specifications
git -C <spec-clone> log -1 --format='%H %cd' -- uts/docs/translator-skills
```

Record the SHA, whether the clone is clean (and, if not, which files under `uts/` or `specifications/` are modified or untracked), and the guide's last-change commit. You MAY compare with `origin/main` if the user agrees to a `git fetch`; never pull or check out on their behalf. Read every doc and spec from this clone for the whole run. If the clone changes during the run, stop and ask whether to restart from the new SHA.

Untracked local notes in the clone (for example files matching `uts/UTS_*.md`) are not part of the corpus. Don't read them as specs.

### 2.7 Working style

- Do Phase 1 before anything else, and don't write harness code before the user approves the harness design (STOP-3), or skill files before the harness is verified (STOP-7).
- Escalate verification in the repo's own order (compile, then build tests, then a filtered run, then wider runs), as recorded in the Repo profile.
- Keep the working records up to date as you go; they are also your memory if the session is interrupted. On resuming, read them first.
- Use the repo's own conventions (file headers, line endings, naming, test style) for every file you create.

### 2.8 Model tier and sub-agents

- **Run this procedure on the most capable model tier available (Claude Opus or an equivalent Opus-class model): MUST.** The guide's [Model tier](writing-translator-skills.md#model-tier) gives the reasons: long context, multi-file reasoning, fidelity, and few silent omissions in rules that every later run inherits. If your environment states your model, record it; otherwise ask the user. If you aren't on an Opus-class model, say so before Phase 1 (**STOP-1**). If the user still wants to proceed, record it in the decision log as a departure from the guide, and state it in the Final report.
- **Sub-agents** you spawn for review, validation or the pilot ([8.3](#83-pilot-translate-one-spec-per-available-tier)) MUST also run on an Opus-class model. Where your tooling lets you choose a sub-agent's model, choose it explicitly rather than relying on a default. Use a cheaper model only for a clearly mechanical step whose output a script verifies (for example, running the [8.2](#82-test-the-audit-itself) corpus sweep and collecting its JSON), if at all, and record which steps used one.
- **Record** the model (name and ID) of this session and of every sub-agent in the Design record ("Inputs at generation time") and in the Final report.
- **Pin** the generated skill's model where the tooling allows (D-26).

---

## 3. Phase 1: understand the repo

**Goal:** a written, user-confirmed Repo profile that explains how the SDK is built, tested and mocked today, in enough depth to design the harness from it. This phase is mandatory and comes before anything else: the harness you design in Phase 2 should extend what the repo already has, follow its test style, and plug into its build and CI, and the skill's file locations, idioms and commands all derive from this profile.

### 3.1 Step 1a: read the repo's own instructions

Read these first, if they exist, and follow them for the rest of the run: `CLAUDE.md` (root and nested), `AGENTS.md`, `CONTRIBUTING.md`, `README.md`, `.editorconfig`, any `docs/` or `Docs/` pages about testing, and any existing `.claude/` directory (settings, skills, commands). Record any instruction that constrains you (for example "don't edit project file X", "use helper Y instead of Z").

### 3.2 Step 1b: answer the discovery checklist

Answer every item. For each, record the answer and its evidence in the Repo profile. The "how to find it" column lists starting points; follow the evidence wherever it leads.

**Build, test and CI**

| # | Find | How to find it |
|---|---|---|
| P-01 | **Language(s) and version(s)**: SDK language, test language (they can differ), toolchain version, language mode or edition | Toolchain pins (`global.json`, `.python-version`, `.nvmrc`, `go.mod`, `rust-toolchain*`, `Package.swift` tools version, Gradle `jvmToolchain`); `git ls-files` extension counts |
| P-02 | **Build system and commands**: build the SDK; build the tests; run all tests; run one class; run one test; run by filter; target-qualified filters | Build files (`*.sln`/`*.csproj`, `pyproject.toml`/`tox.ini`/`noxfile.py`, `package.json` scripts, `build.gradle*`, `Package.swift`, `Makefile`, wrapper scripts); CI workflow steps; CONTRIBUTING. **Run** the build-tests and single-class commands and record the exit status. For interpreted languages, "build the tests" means collection (e.g. `pytest --collect-only`) plus the repo's type checker. Record the command that lists collected tests (e.g. `pytest --collect-only -q`, `dotnet test --list-tests`) |
| P-03 | **Test framework(s)**: runner, assertion library, parameterisation, suite-level fixtures (before/after all), teardown hooks, **static and runtime skip idioms**, unconditional-fail idiom, **collection rules** (what names and files the runner picks up) | Test dependencies in the build files; existing tests; the runner's config (`pytest.ini`, `conftest.py`, `xunit.runner.json`, `jest.config.*`). Check whether a runtime skip needs an extra package (guide [7.1](writing-translator-skills.md#71-three-acceptable-end-states)) |
| P-04 | **Test layout and naming**: test projects/targets/source sets, their directories, naming conventions for files, classes and methods, shared test-support projects, and which test targets can see which code | Directory listing of test roots; build files for test targets |
| P-05 | **CI**: every workflow that builds or tests; which job runs which suites; OS and runtime matrix; network access; submodule checkout; secrets; how a new suite or test target would be picked up | `.github/workflows/*`, other CI configs; follow each test step to the command it runs |
| P-06 | **Lint, format and strictness gates**: EditorConfig, formatters, linters, static analysis, type checkers; whether CI treats warnings as errors; whether the local build is laxer than CI | Lint configs, `Makefile` lint targets, CI lint jobs, compiler flags in build files |
| P-07 | **Developer and CI platforms**: which OSes developers and CI use; whether the script runtime the skill will use (e.g. `python3`) is available on all of them; where a proxy binary would have to run | CONTRIBUTING, CI matrix, existing scripts |
| P-08 | **Repo conventions**: licence or file headers, comment style, line endings, commit message rules, files kept in sync (e.g. several dependency manifests), project files not discovered by the build | CLAUDE.md, CONTRIBUTING, `.editorconfig`, `.gitattributes`, recent commits |

**How the SDK is structured for testing**

| # | Find | How to find it |
|---|---|---|
| P-09 | **Async model**: callbacks, futures/promises, `async`/`await`, coroutines; whether SDK APIs are callback-based, async, or both; the test runner's async support and its mode; whether the runner **virtualises time** | SDK public API signatures; runner plugins (e.g. pytest-asyncio mode); existing async tests (guide [2.6](writing-translator-skills.md#26-understand-the-sdks-concurrency-model-must)) |
| P-10 | **Concurrency and threading**: which thread, queue or loop SDK callbacks run on; whether listeners can run concurrently with the test body; how to drain the SDK's internal work queue (this becomes `process_pending_events()`); whether the language checks concurrency safety at compile time | SDK source: dispatch, executor or event-loop code; how existing tests wait for callbacks |
| P-11 | **Time model**: **every time source** the SDK uses: timers, timed blocking waits, scheduled or delayed callbacks, wall-clock and monotonic reads | Grep the SDK source for the language's sleep, timer, wait, delay and now APIs; list each call site's owner (guide [2.1](writing-translator-skills.md#21-sdk-test-hooks-must)) |
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
| P-20 | **Existing UTS assets and their state**: any UTS harness, UTS-derived tests (`UTS:` tags), `deviations.md` files, previous `uts-to-*` skills in this repo. For each asset: does it compile, do its tests pass, which spec SHA do headers name, which helper-spec symbols exist | `grep -rn "UTS:" <test-roots>`; search for `MockWebSocket`, `MockHttpClient`, `SandboxApp`, `uts-proxy`, `deviations.md`, `.claude/skills/uts-*` |
| P-21 | **Sandbox access**: whether tests can reach `sandbox.realtime.ably-nonprod.net` from developer machines and CI | Existing integration tests; CI network settings (guide [2.3](writing-translator-skills.md#23-sandbox-provisioning-and-fixtures-must-for-integration-tiers)). Probing the sandbox, or running existing integration tests for P-20, is network access: **STOP-6** first |

Useful generic commands (adapt to the platform):

```sh
git -C <repo> rev-parse HEAD; git -C <repo> status --porcelain
git -C <repo> ls-files | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20   # extension counts
git -C <repo> ls-files | grep -iE '(^|/)(test|tests|spec)s?/' | head -50          # test roots
git -C <repo> submodule status
grep -rnE "class (Mock|Fake|Stub)|(Mock|Fake)[A-Z][A-Za-z]*(Transport|Http|Clock|Timer|Socket)" <test-roots> | head -40
grep -rn "UTS:" <test-roots> | head                                               # previous UTS ports
```

### 3.3 Step 1c: study how the existing tests drive the SDK

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

- Which existing doubles behave like the helper specs need (see the semantics in [4.3](#43-step-2c-map-each-helper-spec-to-native-code)), and which differ?
- Which existing waits are race-free (subscribe first, then check), and which sample state or sleep?
- Where do the existing tests flake or carry workarounds (retries, sleeps, `@Ignore`/skip with a reason, comments about races)? These mark concurrency or timing problems the harness must avoid.

### 3.4 Step 1d: write and confirm the Repo profile

Write `repo-profile.md` from [Appendix A](#appendix-a-repo-profile-template). Record the repo's HEAD SHA and whether it is dirty. Then **STOP-2**: show the user the profile, highlight every "unknown" and every inference, and ask them to confirm or correct it. Apply their corrections before continuing.

**Done when:** every P-row has an answer with evidence or an explicit "unknown" with a question; the build-tests and single-class commands have been run (or marked unverified with the reason); the existing-test patterns of 3.3 are written down; the user has confirmed the profile.

---

## 4. Phase 2: design the harness

**Goal:** a written design for the harness in this language, derived from the Repo profile: for every capability guide [section 2](writing-translator-skills.md#2-the-harness-uts-test-infrastructure) requires, whether to **reuse** what exists, **wrap** it, **extend** it or **build** it new; how each helper spec maps to native code; which SDK hooks are still needed; where the code lives; and how each piece will be accepted. The user approves the design before you build anything.

Design principles:

- **Follow guide [2.2](writing-translator-skills.md#22-a-shared-test-library-implementing-the-helper-specs-must)**: implement each helper spec once, and build the harness to look like the pseudocode. When an existing double has the right behaviour but a different shape, **wrap it in a pseudocode-shaped facade** rather than teaching the skill to translate into the old shape.
- **Reuse what is correct; don't reuse what is subtly wrong.** An existing double that misses a helper-spec guarantee (for example a synchronous `close()`) will make the UTS ports flaky. Extend or replace it for the UTS ports, leaving the native tests' behaviour unchanged.
- **Hooks** are injected at client construction, per-client where the SDK allows (guide [2.1](writing-translator-skills.md#21-sdk-test-hooks-must), [2.6](writing-translator-skills.md#26-understand-the-sdks-concurrency-model-must)).

### 4.1 Step 2a: list the required capabilities

Start the gap table from rows G-01 to G-20 of [Appendix B](#appendix-b-gap-table-and-harness-design-template), which cover every requirement of guide [2.1](writing-translator-skills.md#21-sdk-test-hooks-must) to [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must). Split a row where its parts get different approaches (e.g. `MockWebSocket` reused but its alternative API built). Rows for concurrency knowledge (G-18) come from the Repo profile (P-09 to P-14) and are "missing" if the profile left them unknown.

**Check:** every bullet and table row of guide section 2 maps to a gap-table row.

### 4.2 Step 2b: assess each capability: reuse, wrap, extend or build

This is the guide's "Reuse before you build" ([2.2](writing-translator-skills.md#22-a-shared-test-library-implementing-the-helper-specs-must)) applied to every row. For each row, record the status (`present`, `partial`, `missing`, `n/a`), the evidence (file and symbol, or what you searched for), and the **approach**:

| Approach | When |
|---|---|
| **Reuse** | An existing component already meets the requirement's semantics and shape (verified, not assumed) |
| **Wrap** | The semantics are right but the shape differs from the pseudocode; add a facade with the spec's names |
| **Extend** | The component is close but lacks capabilities (e.g. no WS-level timeout, no raw frames); add them without changing existing behaviour |
| **Build** | Nothing suitable exists, or what exists is semantically wrong for UTS |
| **n/a** | The SDK lacks the feature (e.g. `MockVCDiff*` when the SDK has no delta support); confirm against the features spec in the clone and give the reason |

Also record which tiers and modules each row blocks, whether closing it needs a production-code change, and a size (S/M/L). "Partial" always says what is missing.

If harness code already exists, **check it, don't trust it**: compile it, run its tests by filter, and compare its behaviour with the semantics in 4.3 and 4.4.

### 4.3 Step 2c: map each helper spec to native code

Read each helper spec in full, then design its native implementation. For each, produce a symbol table in `uts-infra-design.md`: every symbol the helper spec declares **and** every harness symbol the corpus uses (find them with the scanner in [7.4](#74-step-5d-fill-the-construct-catalogue); the corpus uses members the helper specs don't declare) → native type and member → approach (reuse, wrap, extend, build) → the existing component it builds on, if any.

| Helper spec | Design questions to answer | Requirements to check against |
|---|---|---|
| [`mock_http.md`](../../rest/unit/helpers/mock_http.md) | Which HTTP hook does `install_mock` use? Does an existing HTTP double capture method, URL, headers and body? Can it fail at connection level separately from request level? Will the legacy `queue_*` calls be implemented, or mapped onto `onRequest` handlers in the skill? | The helper spec; guide 2.2 `mock_http.md` row |
| [`mock_websocket.md`](../../realtime/unit/helpers/mock_websocket.md) | Which transport hook installs it? Does an existing transport double exist, and is its `close()` asynchronous? How are typed messages and raw untyped frames sent to the client? How are client frames captured? | The helper spec (including "Async Behavior and Event Loop Considerations"); guide 2.2 `mock_websocket.md` row and the notes below it |
| [`mock_vcdiff.md`](../../realtime/unit/helpers/mock_vcdiff.md) | Does the SDK support deltas, and how is a decoder registered? | The helper spec; guide 2.2 |
| [`standard_test_pool.md`](../../objects/helpers/standard_test_pool.md) | Which channel and plugin setup does `setup_synced_channel` need? Where do module helpers live (where internals are visible, if white-box specs need them)? How is the plugin registered in a client-options builder? | The helper spec; guide 2.2 `standard_test_pool.md` row and "Document each fixture helper's scope" |
| *(no helper spec)* `MockNetworkListener` | Is there a network-monitor hook? | guide 2.2 last table row; `realtime/unit/connection/network_change_test.md` |

Where a design question can only be answered by a production change, it becomes a hook proposal (4.6).

### 4.4 Step 2d: design the wait and assertion helpers

Design these against the async and concurrency model from P-09 to P-12 and the existing helpers from P-17. For each, record the native symbol and whether you reuse an existing helper (only if it already meets the requirements), wrap it, or build it. The requirements are in the sources below; the self-tests that prove them (guide [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)) are in [5.2](#52-step-3b-build-in-order-with-acceptance-checks), rows 2, 4 and 7.

| Helper | Requirements |
|---|---|
| `AWAIT_STATE` (connection and channel) | guide [5.7](writing-translator-skills.md#57-waits-must-catch-events); `writing-test-specs.md` "State Transitions" |
| `poll_until`, `poll_until_success` | `writing-test-specs.md`; `uts/README.md`; guide 5.7; `writing-derived-tests.md` "No real timers in unit tests" (deadlines) |
| `process_pending_events()` | `uts/README.md`; guide [2.6](writing-translator-skills.md#26-understand-the-sdks-concurrency-model-must) |
| Wall-clock timeout wrapper | `writing-derived-tests.md` "Integration timeouts are wall-clock"; guide [5.6](writing-translator-skills.md#56-time-and-waiting) |
| Fake clock driver (`enable_fake_timers`, `ADVANCE_TIME`) | guide [2.1](writing-translator-skills.md#21-sdk-test-hooks-must), [5.6](writing-translator-skills.md#56-time-and-waiting); covers every time source in P-11 |
| Thread-safe capture, log sink, caller-attributed failures | guide 2.2 |
| `assertContainsInOrder` | guide [6.7](writing-translator-skills.md#67-notes-on-the-catalogue) |

### 4.5 Step 2e: design the sandbox and proxy helpers

- **Sandbox** (guide [2.3](writing-translator-skills.md#23-sandbox-provisioning-and-fixtures-must-for-integration-tiers)): check the native integration tests' provisioning (P-18) against guide 2.3; reuse or wrap it if it meets every point, otherwise build `SandboxApp`. Decide how clients are pointed at the sandbox and how per-run vs per-test provisioning maps to the runner's suite fixtures (P-03).
- **Proxy** (guide [2.4](writing-translator-skills.md#24-the-proxy-must-for-the-proxy-tier), [`proxy.md`](../proxy.md)): design `ProxyManager` and `ProxySession` to every point of guide 2.4. Checking that the pinned release has a binary for every developer OS in P-07 is a network read: ask first (**STOP-6**), or mark it unverified until Phase 3 row 10 and plan platform gating where it can't run. Include every operational requirement in guide 2.4. Default the session's endpoint to the sandbox, because two corpus specs pass only `rules:` (guide [6.7](writing-translator-skills.md#67-notes-on-the-catalogue)). Decide auth through the proxy (D-18).

### 4.6 Step 2f: propose the SDK test hooks

For every hook row that isn't `present`, write a proposal in `uts-infra-design.md`:

- the API (name, type, where it is set), modelled on the repo's existing test options if it has any (P-13);
- the default behaviour (unchanged for users);
- its visibility (test-only if the language allows);
- every production file it touches;
- how the harness installs it at client construction, and whether it is per-client;
- for the clock hook, the list of time sources from P-11 it covers, including timed blocking waits and the async runtime's timers.

These proposals are presented at STOP-3 and need individual approval at **STOP-4** before you implement them.

### 4.7 Step 2g: plan placement, harness tests and build order

- **Placement** (guide 2.2, "Placement" and "Recommended layout"): name the harness library and its per-tier directories, the directory and target for shared test-support code (importing no test framework), port-only harness code, and each module's helpers. Put white-box suites, and module helpers they need, where internals are visible (P-14; guide 2.6).
- **Harness tests:** the per-tier smoke tests and helper self-tests of guide [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must), item by item, for every tier you plan to support. They are permanent and run in CI; they carry no `UTS:` tag and are never copied by the skill; they live outside every directory the mapping will give the resolver as a `targetDir`. Name the command that runs each tier's set plus the common self-tests (guide 2.7 "Selectable"); it goes into the mapping's `harness` entry (D-03). Name the CI job that runs it (5.2 row 13). The acceptance checks in [5.2](#52-step-3b-build-in-order-with-acceptance-checks) say what each must prove.
- **Build order:** follow the order in 5.2, dropping rows that are `present` or out of scope.

### 4.8 Step 2h: derive tier feasibility

Fill a module × tier matrix: for each of `rest`, `realtime`, `objects` and each of unit, integration, proxy, mark **ready**, **ready after building rows X, Y**, or **not possible** (with the reason, e.g. "not possible until the SDK has an objects API (placeholder notes; the skill refuses the module)"). A tier the corpus doesn't have for a module is `n/a` (check with `ls <spec-clone>/uts/<module>`). A tier is **ready** only when its G-19 and G-20 rows (smoke tests and self-tests, guide 2.7) are present, green and wired into CI (or the CI change was declined at STOP-5 and is reported as unmet, 5.4), or will be built in Phase 3.

### 4.9 Step 2i: STOP-3, approve the design and choose the scope

Present `uts-infra-design.md`: the gap table, the helper-spec mappings, the wait-helper design, the sandbox and proxy design, the hook proposals, placement, the build order and the tier matrix. Ask the user to choose:

- **(a) Build the missing harness now**, all or a named subset. Recommend this option (the skill depends on the harness), but the user chooses. Continue with Phase 3.
- **(b) Plan it only.** Keep the build order, with each row's acceptance check and size, as the plan in `uts-infra-design.md`. Phase 3 is skipped for the planned rows; the skill is generated for the tiers that are already ready, and the unready tiers stay in the mapping but the skill must refuse them with a message naming the missing harness piece, as guide [4, step C](writing-translator-skills.md#phase-1-selection-steps-0-and-af) requires (see the readiness data in [7.1](#71-step-5a-create-the-layout-and-the-mapping-file)).
- **(c) Scope the skill to the tiers possible today.** As (b), without the plan.

Under (b) and (c), G-19 and G-20 for every tier the skill will offer can't be planned or scoped out; Phase 3 and STOP-7 still run for them.

Record the answer and any design changes the user asked for. Under (b) and (c), the skill's tier step (C) must offer only ready tiers, and the Final report lists the rest as known limitations.

---

## 5. Phase 3: build and verify the harness

**Goal:** the approved harness exists, compiles under the repo's strictest settings, and each supported tier has green smoke tests and helper self-tests (guide [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)), wired into CI. This is part of the skill's deliverable, not a preliminary. Skip the rows the user didn't choose to build at STOP-3.

### 5.1 Step 3a: rules while building

- **Production hooks only after STOP-4 approval**, one proposal at a time, in the smallest form that works.
- **Don't change existing behaviour** of doubles or helpers the native tests use; extend, wrap or add new code instead (see [2.2](#22-what-you-may-change)).
- Follow the repo's test style (P-03, P-04, P-08): naming, file headers, assertion library, formatting.
- Run the existing tests that touch anything you changed, by filter, before and after the change.
- Log every design change you make while building in the decision log; update `uts-infra-design.md`.

### 5.2 Step 3b: build in order, with acceptance checks

Each step has an acceptance check; don't start the next step until it passes (or the user accepts a documented exception). **Bound:** if a row's check still fails after three fix attempts, stop (**STOP-10**) with a summary: the failure, what you tried, your diagnosis, and the options (change the design and log it, accept a documented exception, or descope the tiers the row blocks).

The smoke tests and self-tests in the checks below are the permanent harness tests of guide [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must) (MUST): build them as this phase's gates, and keep them in the repo and in CI afterwards, where the generated skill's preflight runs them. Each row's check is an explicit assertion in a harness test, not a manual observation.

Rows 4–7 depend on each other: build them in order, but run an acceptance item that needs a component from a later row as soon as that component exists (the fake-clock check needs a transport mock; the REST row's realtime-driven request needs `MockWebSocket`; the realtime row's state waits need row 7), and don't leave row 7 until every row 4–7 item passes. Common items that need an integration component (the integration state-wait helper, integration teardown) run at row 9, once that component exists; they are part of row 9's acceptance.

| Order | Build | Acceptance check |
|---|---|---|
| 1 | UTS test target/project and its tier selection (directories or filters per tier), wired so that `build-tests` compiles it | A minimal harness test (one trivial passing test; delete it once row 2's self-tests exist) compiles, is collected and passes under the single-class filter and under the tier's harness-test command |
| 2 | Library core: thread-safe capture, log sink, `assertContainsInOrder`, caller-attributed failure helper | Tests of the helpers themselves: `assertContainsInOrder` passes on `[connecting, disconnected, connecting, connected]` vs `[disconnected, connecting, connected]` and fails when the order is broken, and a repeated state passes (guide [6.7](writing-translator-skills.md#67-notes-on-the-catalogue)); capture lists are safe under concurrent appends; a failing helper reports the caller's line |
| 3 | Approved SDK hooks | Each hook replaces the real implementation for one client without affecting another client created afterwards (or, if process-global, that fact is recorded for decision D-14); the existing tests still pass |
| 4 | Fake clock wired through the clock hook | A timer-driven SDK behaviour doesn't happen before `ADVANCE_TIME` and does happen after it; a timed blocking wait in the SDK (if P-11 found any) is also driven by the fake clock; the async runtime's timers fire under it, and nothing waits on the real clock (guide [2.1](writing-translator-skills.md#21-sdk-test-hooks-must)); one advance runs cascaded work to quiescence (zero-delay reschedules and timers created mid-advance) |
| 5 | `MockHttpClient` per `mock_http.md`, plus the legacy `queue_*` API or its documented mapping | **REST unit smoke test and self-tests:** Every item in guide [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)'s Unit, REST entry, each as an explicit assertion |
| 6 | `MockWebSocket` per `mock_websocket.md`, including the alternative API, undocumented members and raw frames | **Realtime unit smoke test and self-tests:** Every item in guide [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)'s Unit, realtime entry, each as an explicit assertion |
| 7 | Wait helpers per [4.4](#44-step-2d-design-the-wait-and-assertion-helpers) | **Helper self-tests:** every item in guide [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)'s Common and Unit, fake clock entries, each as an explicit assertion; in addition, `AWAIT_STATE` completes for a state reached before or during the wait (the teardown self-test follows your SDK's `close()` behaviour, guide 5.4) |
| 8 | `MockNetworkListener` (if the SDK has a network monitor), `MockVCDiff*` (if the SDK supports deltas) | A smoke test drives each one |
| 9 | `SandboxApp`, `ably-common` access (after **STOP-6**) | **Direct integration smoke test and self-tests:** Every item in guide [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)'s Direct sandbox entry, each as an explicit assertion |
| 10 | `ProxyManager` and `ProxySession` (pinned version; every developer OS) (after **STOP-6**) | **Proxy smoke test and self-tests:** Every item in guide [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)'s Proxy entry, each as an explicit assertion; clients authenticate as decided in D-18 |
| 11 | Module helpers, e.g. the `standard_test_pool.md` implementation and a plugin client-options builder | **Objects unit smoke test and self-tests:** Every item in guide [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)'s Unit, objects entry, each as an explicit assertion. The smoke test lives beside the module helpers (outside every `targetDir`) and is selected by the unit tier's harness command |
| 12 | Harness README describing what exists, with its Known gaps | See [5.3](#53-step-3c-write-the-harness-readme) |
| 13 | CI wiring (needs **STOP-5** approval), or a suggested change for the Final report | Each suite runs in exactly one CI job per platform it targets; nothing reports green without executing; each tier's smoke tests and self-tests run, ungated, in that tier's job (guide [2.5](writing-translator-skills.md#25-build-and-ci-wiring-must), [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)); the repo's existing test commands and jobs (e.g. bare `pytest`, `dotnet test` on the solution) don't also collect the UTS or harness tests (exclude them via `testpaths`/`--ignore`, a solution filter or a separate project), unless that job is deliberately their one CI home |

Then compile all test targets as strictly as CI does (P-06) and run the repo's lint gates over the new code.

### 5.3 Step 3c: write the harness README

Write a README next to the harness covering everything guide [3.1](writing-translator-skills.md#31-layout) and [2.2](writing-translator-skills.md#22-a-shared-test-library-implementing-the-helper-specs-must) say it should cover (3.1's list, and 2.2's threading facts for `mock_websocket.md`). Procedure detail:

- take the symbol map from the [4.3](#43-step-2c-map-each-helper-spec-to-native-code) tables as built, and the known gaps from the gap table's `partial` and `missing` rows;
- add the layout (shared, port-only, module helpers, test targets) and the complete command that runs each tier's smoke tests and self-tests;
- write the **Known gaps** section (MUST): every helper-spec member, contract point or corpus construct the harness doesn't implement, by tier, as a table whose first column is the exact pseudocode token, matched by grepping the selected specs' `pseudo` fences (guide 3.1), then status and workaround, so the skill's preflight can match it against selected specs;
- index every module's fixture helpers in one place, even those in a separate test-support module;
- link each fixture helper's scope to the module notes (item 9), where guide 2.2 puts it;
- record the README's full repo path in the Design record.

### 5.4 Step 3d: STOP-7, confirm the harness

Re-run the assessment of [4.2](#42-step-2b-assess-each-capability-reuse-wrap-extend-or-build) and the tier matrix of [4.8](#48-step-2h-derive-tier-feasibility), and update `uts-infra-design.md` with the build log. Show the user the smoke-test and self-test results per tier (each run by its tier's filter), their CI wiring, the files created or changed, and the updated tier matrix. Only then continue to the skill.

**Done when:** every row the user chose to build is `present`; each supported tier has green smoke tests and self-tests covering guide 2.7, wired into CI (or, if the user declined the CI change at STOP-5, listed in the Final report as an unmet requirement; the tier stays ready, because the skill's preflight still runs the harness tests locally on every run, and the harness README states that CI doesn't yet run them); the strict compile and lint pass; the harness README exists; the user has confirmed at STOP-7. If the user declines network access at STOP-6, the integration and proxy tiers aren't supported: mark them unready (`blockedBy`: harness tests not run) and list them in the Final report.

---

## 6. Phase 4: skill design decisions

**Goal:** every choice the skill bakes in is made once, with the user, and written down.

### 6.1 Step 4a: draft the Design record

For each decision below, propose an answer derived from the Repo profile, the built harness and the guide, then present them together. Write them into `design-record.md` ([Appendix C](#appendix-c-design-record-template)).

| ID | Decision | Guide reference | How to propose it |
|---|---|---|---|
| D-01 | Skill name and location | [3.1](writing-translator-skills.md#31-layout), [3.3](writing-translator-skills.md#33-frontmatter-and-arguments) | `uts-to-<lang>` at `.claude/skills/uts-to-<lang>/` |
| D-02 | Script language and minimum runtime version | [3.1](writing-translator-skills.md#31-layout), [8.1](writing-translator-skills.md#81-resolver-resolve_utspy-must), [10](writing-translator-skills.md#10-verification-and-ci) | Python 3 unless P-07 shows it isn't available on every developer platform |
| D-03 | **Target directory per module × tier** (the mapping), unique namespaces, hand-maintained entries | [3.2](writing-translator-skills.md#32-the-mapping-file), [2.6](writing-translator-skills.md#26-understand-the-sdks-concurrency-model-must) (placement follows visibility) | Follow the UTS test target from Phase 3 and the placement from [4.7](#47-step-2g-plan-placement-harness-tests-and-build-order). Keep a module segment after the tier. Also record the default layout `--create <name>` scaffolds for a new module (e.g. `<uts-root>/<tier-path>/<name>`); the resolver implements exactly that. Record the mapping's `harness` entry (root, README, per-tier sources and harness-test commands from 4.7) |
| D-04 | **Naming**: file, class/suite and test-function names; the resolver's name derivation; runner collection rules | [5.1](writing-translator-skills.md#51-traceability), [8.1](writing-translator-skills.md#81-resolver-resolve_utspy-must) | Give three worked examples (a `_test.md` spec, a plain spec, one in a sub-directory) and confirm the runner collects each name (P-03) |
| D-05 | Name collisions with native tests | [8.1](writing-translator-skills.md#81-resolver-resolve_utspy-must) | Detect in the resolver, or always run with a target-qualified filter. Where the runner imports test files by basename, also apply guide 8.1's file-name uniqueness rule across the whole mapping |
| D-06 | **Tag syntax** | [5.1](writing-translator-skills.md#51-traceability) | `// UTS: <id>`, or the language's line-comment marker (`# UTS: <id>`), immediately above the test, before its attributes or decorators (guide 3.4 file outline) |
| D-07 | File header format | [5.1](writing-translator-skills.md#51-traceability), [9.1](writing-translator-skills.md#91-record-what-you-translated-from-must) | Source spec path, tier, `ably/specification@<full-sha>`, disclosures; integration/proxy also the corresponding unit spec |
| D-08 | **`deviations.md` location** per owning test module | [7.3](writing-translator-skills.md#73-deviationsmd) | One per owning test module, next to its suites |
| D-09 | **Runtime skip idiom** (env-gated on `RUN_DEVIATIONS`) and the reproduction command | [7.1](writing-translator-skills.md#71-three-acceptable-end-states) | From P-03; must read the environment at run time |
| D-10 | **Fail-fast idiom** for UTS spec errors | [7.1](writing-translator-skills.md#71-three-acceptable-end-states) | The framework's unconditional failure with the message `UTS spec error <id> — fix the spec first; see deviations.md` |
| D-11 | Pending idiom for a missing API (registered, skipped, not commented out) | [7.1](writing-translator-skills.md#71-three-acceptable-end-states), [7.4](writing-translator-skills.md#74-language-inapplicable-inputs) | The framework's static skip or pending marker |
| D-12 | **Internal-access ladder**: the existing exposure to check first, the sanctioned way to add a test-only exposure, who to escalate to; where the white-box spec list lives | [5.9](writing-translator-skills.md#59-internal-access-white-box-unit-specs) | From P-14. List white-box specs in the module notes or the mapping file |
| D-13 | **Delegation policy** for delegating specs and tests | [5.3](writing-translator-skills.md#53-structural-variants) | The guide's recommendation (one test with the delegating tag, running the referenced REST cases through a shared helper; else pending with a `NOTE`). The guide calls this new policy: confirm with the user |
| D-14 | Parallelism: serialise UTS suites, or rely on per-client hooks | [2.6](writing-translator-skills.md#26-understand-the-sdks-concurrency-model-must) | From P-12 and the hooks as built |
| D-15 | Teardown mechanism (scope, hook, `finally`) and suite-level fixtures for `BEFORE ALL TESTS` | [5.4](writing-translator-skills.md#54-setup-and-teardown) | From P-03 and the harness |
| D-16 | Protocol-variant rendering (`PROTOCOL`) | [5.3](writing-translator-skills.md#53-structural-variants) | The framework's parameterisation over `json`/`msgpack`; tag stays singular |
| D-17 | Default timeouts and poll interval | [5.6](writing-translator-skills.md#56-time-and-waiting) | As guide 5.6 "Every wait is bounded": the spec's timeout where it states one; otherwise an explicit 10–30 s timeout on every integration `poll_until` and 10–15 s helper defaults for state waits. Record the chosen values |
| D-18 | Auth through the proxy | [2.4](writing-translator-skills.md#24-the-proxy-must-for-the-proxy-tier) | As designed in [4.5](#45-step-2e-design-the-sandbox-and-proxy-helpers) |
| D-19 | **Re-sync mode**: flag name, whether to keep a per-module manifest | [9.2](writing-translator-skills.md#92-a-re-sync-mode-should) | `--resync`; manifest optional; ship the corpus scanner in `scripts/` (guide [6](writing-translator-skills.md#6-pseudocode-construct-catalogue) SHOULD; [7.4](#74-step-5d-fill-the-construct-catalogue)) |
| D-20 | **Commit policy**; project/solution-file edits | [10](writing-translator-skills.md#10-verification-and-ci) | No commits by default; list changed files. Record each project/solution-file edit approved at STOP-5, and any the user chose to make by hand |
| D-21 | Fix-attempt bounds: per test in the skill's evaluate mode; per pilot spec in Phase 6 | [7.5](writing-translator-skills.md#75-stopping-rules-for-evaluate-mode-should) | Three in both cases; in the pilot, count every regeneration of a spec, whatever the defect |
| D-22 | `allowed-tools` and remote access | [3.3](writing-translator-skills.md#33-frontmatter-and-arguments), [9.4](writing-translator-skills.md#94-local-clone-vs-fetching-main) | `Bash, Read, Edit, Write`; no `WebFetch`, because everything is read from the local clone (the skill never consults the reference implementations, [2.1](#21-your-inputs)) |
| D-23 | Which modules get notes files, and which are placeholders | [3.1](writing-translator-skills.md#31-layout), [4](writing-translator-skills.md#phase-1-selection-steps-0-and-af) | A notes file for every module whose surface diverges from the pseudocode (P-15); at least `objects`, if the SDK implements it (a placeholder otherwise) |
| D-24 | Location of the working records, and whether they are kept in the repo | [1.4](#14-outputs) of this document | Default `.claude/skills/uts-to-<lang>/generation/`, kept for maintenance |
| D-25 | Pilot specs and mode per tier | [8.3](#83-pilot-translate-one-spec-per-available-tier) of this document | One per ready module × tier in scope, and at least one per module with a full notes file, chosen by the criteria there |
| D-26 | Model tier for skill runs: pin the model, or state it | [Model tier](writing-translator-skills.md#model-tier), [3.3](writing-translator-skills.md#33-frontmatter-and-arguments) | Pin to an Opus-class model if the tooling supports it (verify the mechanism in the current Claude Code documentation; don't assume a frontmatter field); otherwise state it in the opening lines of `SKILL.md`. Either way, the skill's final report records the model |

### 6.2 Step 4b: STOP-8, confirm

Show the Design record. Make clear which decisions follow directly from the guide (the user may still override them, but should know they are departing from it) and which are genuine choices. Record the answers. Don't generate any skill file before this confirmation.

---

## 7. Phase 5: generate the skill files

Generate the files in this order: each one depends on the previous ones. `SKILL.md` comes last because it references all the others; its outline is fixed by the guide, so you can draft it early, but finish it last.

### 7.1 Step 5a: create the layout and the mapping file

1. Create the directory layout from guide [3.1](writing-translator-skills.md#31-layout) (plus the working-records directory, D-24).
2. Write `uts-package-mapping.json` from D-03, in the shape of guide [3.2](writing-translator-skills.md#32-the-mapping-file).
3. Record tier readiness as data in the mapping (guide 3.2 allows per-module defaults as data, and guide [4, step C](writing-translator-skills.md#phase-1-selection-steps-0-and-af) refuses unready tiers), so the skill can read it without the working records. *Procedure recommendation:* an `unready` object per module, e.g. `"unready": {"proxy": "G-16: ProxySession not built"}`, which the resolver reports as `tiers.<tier>.ready: false` with `blockedBy`.

**Acceptance:**

- [ ] Every module the user wants has an entry; every tier value is one path relative to the repo (or a declared root), never machine-absolute.
- [ ] Every derived namespace is unique (a module segment after the tier, or a module-specific prefix).
- [ ] `notes` paths are relative to the skill directory and the files exist (placeholders at this point are fine).
- [ ] Hand-maintained entries are marked (e.g. in `_comment`) and listed in the Design record.
- [ ] Every tier the harness design marks unready has an `unready` entry with the blocking gap-table row.
- [ ] The mapping has a `harness` entry (root, README, per-tier sources and the complete smoke-test and self-test command), every path in it exists, no harness test lies inside any tier `targetDir`, and no `targetDir` lies inside the harness root (guide [3.2](writing-translator-skills.md#32-the-mapping-file), [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)).
- [ ] The file is valid JSON, UTF-8, LF line endings.

### 7.2 Step 5b: write the resolver

Implement `scripts/resolve_uts.py` (or the language chosen in D-02) to every row of guide [8.1](writing-translator-skills.md#81-resolver-resolve_utspy-must). It prints exactly one JSON object.

Output contract: the fields of guide 8.1, including `harness` (the mapping's harness entry with paths validated, still repo-relative), `testRoot` when the mapping declares a root, including `testFile` wherever the target file name isn't `<className>.<ext>`, plus `ready` and `blockedBy` per tier (*procedure recommendation*: from the mapping's `unready` data, [7.1](#71-step-5a-create-the-layout-and-the-mapping-file)). Also implement the optional `specRepo` (`{sha, dirty}`; making it mandatory is a *procedure recommendation*), so the skill takes the clone's state for headers and reports ([8.1](writing-translator-skills.md#81-resolver-resolve_utspy-must), [9.1](writing-translator-skills.md#91-record-what-you-translated-from-must), [9.4](writing-translator-skills.md#94-local-clone-vs-fetching-main)) from the script rather than recomputing it. Choose the namespace and build-target field names and document them in `SKILL.md`. For example:

```json
{
  "ok": true,
  "sourceModule": "realtime",
  "specRepo": { "sha": "<full-sha>", "dirty": false },
  "mapped": true,
  "translationNotes": "<abs path to references/realtime-mapping.md, or null if none declared>",
  "harness": {
    "root": "<repo-relative harness root>",
    "readme": "<repo-relative harness README>",
    "tiers": { "unit": { "sources": ["..."], "tests": "<command>" }, "integration": { "...": "..." }, "proxy": { "...": "..." } }
  },
  "tiers": {
    "unit": {
      "present": true,
      "sourceDir": "<spec-clone>/uts/realtime/unit",
      "targetDir": "<repo-relative target dir>",
      "namespace": "<derived namespace/package, if the language has one>",
      "buildTarget": "<derived test project/target/module>",
      "ready": true,
      "specs": [ { "file": "connection/connection_failures_test.md", "className": "ConnectionFailuresTests" } ]
    },
    "integration": { "present": true, "...": "..." },
    "proxy": { "present": true, "ready": false, "blockedBy": "G-16: ProxySession not built", "...": "..." }
  }
}
```

Errors are `{"ok": false, "code": "<CODE>", "message": "<text>"}`, with a distinct code for each failure guide 8.1 describes (not a UTS module path, directory not found, no tier directories, mapping missing or malformed, bad target name; the guide's example codes are a fine naming), plus one for a declared notes file that is missing (e.g. `NOTES_NOT_FOUND`) and one for a name collision (e.g. `NAME_COLLISION`).

**Acceptance** (each verified by running the script in [8.1](#81-run-the-resolver-on-every-module)):

- [ ] Every row of guide 8.1 is implemented: validation, error objects, output contract, path-only tier detection (including specs in tier sub-directories, e.g. `realtime/integration/channels/`), exclusions relative to the tier base, deterministic runner-collectable naming (D-04), collision detection (D-05, including file-name uniqueness where the runner needs it), validate-then-write `--create` writing the D-03 default layout, an error for a missing notes file.
- [ ] `harness` matches the mapping, with every path validated (repo-relative) and existing; `ready`/`blockedBy` match the mapping's `unready` data; `testFile` is present wherever the file name isn't derived from `className`.
- [ ] Never crashes: any exception becomes `ok: false` with a code.

### 7.3 Step 5c: write the audit

Implement `scripts/audit_translation.py` to every row and the parsing contract of guide [8.2](writing-translator-skills.md#82-audit-audit_translationpy-must). The spec-side parser is language-independent; write it yourself from the parsing contract (never by porting another SDK's audit, [2.1](#21-your-inputs)). The test side needs four language-specific patterns, taken from the Design record, the harness and the construct catalogue:

| Test-side pattern | Source |
|---|---|
| Tag marker (`UTS:` after the line-comment marker) | D-06 |
| Assertion calls (every assertion form the catalogue maps `ASSERT …` and `FAILS WITH` to) | [7.4](#74-step-5d-fill-the-construct-catalogue) |
| Wait calls (every harness helper the catalogue maps `AWAIT`, `AWAIT_STATE`, `poll_until`, … to) | [7.4](#74-step-5d-fill-the-construct-catalogue); the harness README |
| Comment syntax (line and block), so commented-out assertions are ignored | P-01 |

Write these as data at the top of the script, so a catalogue change is a one-line edit. Match the longest keyword first on both sides.

Output: use the shape in guide 8.2 "Output shape (SHOULD)", including `notVerifiable` for a spec with no `**Test ID**` lines (not zero tests); if you depart from it, document your shape in `SKILL.md`. Use one exit code for clean, a distinct one for ID problems (missing, orphan, duplicate) and another for "couldn't run".

**Acceptance** (verified in [8.2](#82-test-the-audit-itself)):

- [ ] Every MUST row and the whole parsing contract of guide 8.2 are implemented, including the end-at-heading rule (a guide SHOULD that this procedure requires: *procedure recommendation*): ID coverage (`missing`, `orphan`, `duplicate`, distinct non-zero exit), per-test ledger, separate assert and await counts (spec-side `poll_until` / `poll_until_success` / `POLL_UNTIL` / `AWAIT UNTIL` / `WAIT_FOR` lines counted as waits, matching the test side), commented-out assertions ignored, never crashes, unverifiable specs reported.
- [ ] Where your parsing differs from the contract, `SKILL.md` says so (guide 8.2 "Implement exactly this, or say where yours differs").
- [ ] SHOULD items you implemented are listed in `SKILL.md`; the ones you didn't are listed in the Final report.

### 7.4 Step 5d: fill the construct catalogue

This step produces the construct table that goes into `SKILL.md` (and, for module-specific rows, into the notes).

1. **Start from every row of guide [section 6](writing-translator-skills.md#6-pseudocode-construct-catalogue)** (6.1 to 6.6) and the notes in [6.7](writing-translator-skills.md#67-notes-on-the-catalogue). Copy the "Construct" and "Meaning" columns; replace the Swift and Kotlin columns with one column for this repo.
2. **Fill the rendering for each row** from the harness you built and the SDK: the exact helper or framework call, with its real signature (read it from the source). Don't copy the guide's Swift or Kotlin cells, or anything seen in a reference-implementation read ([2.1](#21-your-inputs)); they illustrate other SDKs.
3. **Scan the corpus for constructs the guide doesn't list** (guide section 6 says the catalogue isn't exhaustive). Run the scanner below over each module the skill covers, and add a row for every uppercase keyword or snake_case call you can't account for.
4. **Give every row a status:**
    - `mapped`: a direct rendering;
    - `mapped (inferred)`: an *(undocumented)* construct, meaning inferred from its uses (list one use);
    - `stand-in`: a sanctioned harness stand-in, disclosed in the file header (guide [7.2](writing-translator-skills.md#72-harness-stand-ins-are-not-deviations));
    - `not available`: the harness lacks the capability; the rendering says what the skill does (extend the mock, or record a Mock Infrastructure Limitation; never substitute a similar mock outcome, guide [5.2](writing-translator-skills.md#52-fidelity)), and the Final report has a plan;
    - `n/a`: no spec in the covered modules uses it (say so after scanning).
5. **No blank cells.** Collect every row the skill can't render and has no plan for, from one scan, into a single **STOP-9**.

Corpus scanner (prints the uppercase keywords and snake_case calls used in `pseudo` fences, outside comments and string literals, with counts; compare its output with the catalogue, and use it in Phase 2 to list the harness symbols the corpus uses):

```python
# scan_constructs.py <spec-clone>/uts/<module>
import collections, pathlib, re, sys

root = pathlib.Path(sys.argv[1])
keywords, calls = collections.Counter(), collections.Counter()
for path in root.rglob("*.md"):
    in_pseudo = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("```"):
            in_pseudo = (line.strip() == "```pseudo") if not in_pseudo else False
            continue
        if not in_pseudo or line.lstrip().startswith(("#", "//")):
            continue
        line = re.sub(r'"[^"]*"', '""', line)                 # ignore string literals
        line = re.split(r"\s(?:#|//)\s", line, maxsplit=1)[0]  # drop trailing comments
        keywords.update(re.findall(r"\b[A-Z][A-Z_]{2,}\b", line))
        calls.update(re.findall(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\s*\(", line))
for title, counter in (("KEYWORDS", keywords), ("SNAKE_CASE CALLS", calls)):
    print("==", title)
    for name, count in sorted(counter.items()):
        print(f"{count:6d}  {name}")
```

The keyword list also contains wire constants and enum values (`ATTACHED`, `MAP_SET`, `LWW`); classify those under the guide's "wire constants" and enum rows rather than as new constructs. The scanner sees only `snake_case(` calls; method-style harness calls such as `mock_ws.active_connection.send_to_client(…)` are caught, but camelCase members (`onConnectionAttempt`) are not, so also read the helper specs' interfaces. Ship it as `scripts/scan_constructs.py` in the skill, as guide [section 6](writing-translator-skills.md#6-pseudocode-construct-catalogue) and [3.1](writing-translator-skills.md#31-layout) recommend (SHOULD), because a re-sync re-scans the corpus (guide [9.2](writing-translator-skills.md#92-a-re-sync-mode-should) step 2); record the choice in the Design record (D-19).

**Acceptance:**

- [ ] Every guide section 6 row is present with a rendering and a status; none blank.
- [ ] Every scanner hit in the covered modules is either a catalogue row, a wire constant or enum value, a spec-local name, or internal pseudocode of a helper spec or `objects/PLAN.md` (implemented as harness or ignored, never translated).
- [ ] Every rendering names a symbol that exists in the harness or the SDK (you read it), or is marked `not available` with a plan.
- [ ] The guide's flagged traps are rendered correctly: `CONTAINS_IN_ORDER` as a subsequence; `poll_until` returns the settled value; `poll_until_success` as a separate helper; `AWAIT_STATE` race-free and failing fast on FAILED; both `AWAIT_STATE` spellings; `create_proxy_session(endpoint:)` per `proxy.md`, with the endpoint defaulted when a spec passes only `rules:` (guide [5.7](writing-translator-skills.md#57-waits-must-catch-events), [6.7](writing-translator-skills.md#67-notes-on-the-catalogue)).

### 7.5 Step 5e: write the module notes

Write `references/<module>-mapping.md` for every module chosen in D-23. Cover the thirteen items in guide [3.4](writing-translator-skills.md#34-recommended-outlines-should) ("A module notes file should cover"), in that order. For each item, either fill it or write "Not applicable: <reason>". The items that most need evidence:

- **Item 1 (source of truth and runtime status):** name the IDL the notes apply (for `objects`, check whether the SDK follows `objects-features.md` in the clone or another variant; guide 3.4 item 1 explains the typed-SDK case) and whether the module is implemented, which decides whether evaluate mode is possible.
- **Item 5 (type mapping):** for every polymorphic or union type in the pseudocode, the SDK type and which conversions throw or return null. Read the SDK source for each.
- **Item 8 (internal access):** the ladder from D-12 and the list of white-box specs. To find candidates, look for specs that construct internal classes or call members the public API doesn't have (the guide's white-box row in [6.6](writing-translator-skills.md#66-mocks-fixtures-and-harness) lists examples), then confirm each against the SDK's public surface.
- **Item 9 (helper-spec coverage):** the module's rows of the symbol tables from [4.3](#43-step-2c-map-each-helper-spec-to-native-code), as built, with each fixture helper's scope and every sanctioned stand-in.
- **Item 12 (worked example):** translate one short real test from the module by hand, name each mechanical rewrite, and make sure it compiles (it becomes one of the skill's examples; [8.7](#87-verify-the-skills-own-examples)).

A module whose mapping you can't author yet gets a **placeholder** notes file that says so; the skill must then refuse that module (guide [4](writing-translator-skills.md#phase-1-selection-steps-0-and-af), "If the module's notes file exists but is only a placeholder").

**Acceptance:**

- [ ] All thirteen items present or marked not applicable with a reason.
- [ ] Every SDK and harness symbol named in the notes exists at the recorded repo SHA.
- [ ] Overrides of the generic flow (reading list, naming rendering, deviations location, expected audit shortfalls) are explicit, and no naming override drops the spec point from test names (guide [5.1](writing-translator-skills.md#51-traceability)), so the skill can say "the notes win" (guide [4, step 1](writing-translator-skills.md#phase-2-per-spec-steps-17)).
- [ ] No line numbers; cite symbols and headings (guide [12](writing-translator-skills.md#12-lessons-learned)).

### 7.6 Step 5f: write `SKILL.md`

Follow the outline in guide [3.4](writing-translator-skills.md#34-recommended-outlines-should). Write each part as the language rendering of the guide's rule, and link to the UTS doc that defines the meaning rather than copying it (guide ["What the skill owns, and what it defers"](writing-translator-skills.md#what-the-skill-owns-and-what-it-defers)).

| Part of `SKILL.md` | Content | Guide |
|---|---|---|
| Frontmatter | `name: uts-to-<lang>`; a pushy `description` with trigger phrases; `argument-hint`; `allowed-tools` from D-22; the model pin from D-26, where the tooling supports one (otherwise the model statement in the opening lines) | [3.3](writing-translator-skills.md#33-frontmatter-and-arguments) |
| Usage guard | Empty argument → print the usage line and stop; placeholder paths only | [3.3](writing-translator-skills.md#33-frontmatter-and-arguments) |
| Required reading (step 0) | As guide 4 step 0 (including the "Pseudocode Conventions" section of `uts/README.md`), from the same clone as the module; record its SHA and dirty state | [4](writing-translator-skills.md#phase-1-selection-steps-0-and-af), [9.4](writing-translator-skills.md#94-local-clone-vs-fetching-main) |
| Skill Phase 1 (selection), steps A–E | As guide 4, with this repo's resolver commands; step C offers only tiers the resolver reports `present` and `ready`, and names `blockedBy` for the others | [4](writing-translator-skills.md#phase-1-selection-steps-0-and-af) |
| Harness preflight (step F) | As guide 4 step F: compile (or collect) the harness and the test target; run the chosen tier's smoke tests and self-tests with the resolver's `harness` command; check the harness README's Known gaps against the selected specs; on red, stop and report a harness or environment problem, never an SDK deviation; record the result for the final report | [4](writing-translator-skills.md#phase-1-selection-steps-0-and-af), [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must) |
| Harness reference | Per tier, from the resolver's `harness` output: harness root and README (full repo path), helper sources to read, smoke-test and self-test locations and run commands, the generated-test run command, and a pointer to the README's Known gaps; no inlined helper signatures; smoke tests named as wiring examples only. Also the mid-run harness-change rule (guide 5) | [3.4](writing-translator-skills.md#34-recommended-outlines-should), [2.7](writing-translator-skills.md#27-harness-smoke-tests-and-self-tests-must) |
| Skill Phase 2 (per spec), steps 1–7 | As guide 4, with this repo's commands; the harness README and helper sources from the resolver's `harness` output; for the reference test per tier, write `none yet` until [8.8](#88-name-the-reference-tests) names one | [4](writing-translator-skills.md#phase-2-per-spec-steps-17), [8.3](writing-translator-skills.md#83-review-checklist-must-after-the-audit) |
| Translation rules | The language rendering of every rule in 5.1–5.9, including the decisions D-04 to D-18 | [5](writing-translator-skills.md#5-translation-rules) |
| Construct table | The catalogue from [7.4](#74-step-5d-fill-the-construct-catalogue), with the stop-and-ask rule for anything unmapped | [6](writing-translator-skills.md#6-pseudocode-construct-catalogue) |
| File template per tier | Header, imports, suite (serialised if D-14 says so), per-test shape; from the outline in 3.4 | [3.4](writing-translator-skills.md#34-recommended-outlines-should) |
| Evaluation | Guide 7 rendered with D-08 to D-11 and D-21 | [7](writing-translator-skills.md#7-evaluation-and-deviations) |
| Integration tiers | Direct-sandbox and proxy wiring with this harness's symbols (D-15, D-18); file templates | [2.3](writing-translator-skills.md#23-sandbox-provisioning-and-fixtures-must-for-integration-tiers), [2.4](writing-translator-skills.md#24-the-proxy-must-for-the-proxy-tier), [5.5](writing-translator-skills.md#55-integration-tier-hygiene) |
| Verification | Guide 10 with the exact commands from the Repo profile | [10](writing-translator-skills.md#10-verification-and-ci) |
| Re-sync mode | Guide 9.2 and 9.3, with D-19 | [9.2](writing-translator-skills.md#92-a-re-sync-mode-should), [9.3](writing-translator-skills.md#93-renamed-merged-and-added-ids) |
| Final report | The format, including the model line | [11](writing-translator-skills.md#11-final-report-format) |
| Commits | No commits by default; list changed files and hand-maintained project files (D-20) | [10](writing-translator-skills.md#10-verification-and-ci) |

**Acceptance:**

- [ ] Every part in the table is present.
- [ ] The skill is module-generic: module-specific rules live in the notes.
- [ ] No inline copy of a semantic rule where a link to its source would do; in particular the `deviations.md` format is referenced, not redefined.
- [ ] No line numbers; no personal or machine-absolute paths; no reference to other SDKs' skills (reference-implementation reads during creation are recorded in the working records, never cited in the skill).
- [ ] None of the guide's [Patterns to avoid](writing-translator-skills.md#patterns-to-avoid) appears in the skill, its notes, its scripts or the harness.
- [ ] The Harness reference names only files, filters and commands that exist, and doesn't inline helper signatures.
- [ ] Every command in it is one the Repo profile records as run. (Running each through the skill, and compiling every example, are Phase 6 checks: [8.5](#85-exercise-the-skills-other-paths), [8.7](#87-verify-the-skills-own-examples).)
- [ ] Every helper or SDK symbol it names exists.

---

## 8. Phase 6: validate the skill

**Goal:** evidence that the skill works on this repo, on top of the harness you built. This phase is mandatory. Record every result in the Final report.

### 8.1 Run the resolver on every module

Run the resolver on `<spec-clone>/uts/rest`, `<spec-clone>/uts/realtime` and `<spec-clone>/uts/objects`, whether or not they are in scope (an unmapped module must resolve with `mapped: false`, not crash). For each, check:

- [ ] `ok: true`; tiers `present` match `ls <spec-clone>/uts/<module>`.
- [ ] Spec counts match the files on disk minus the exclusions. A cross-check: `find <spec-clone>/uts/<module>/<tier> -name '*.md' -not -path '*/helpers/*'` (add the proxy exclusion for the integration tier).
- [ ] No helper spec, `README.md`, `PLAN.md` or `*_SUMMARY.md` appears in `specs`.
- [ ] Every `className` follows D-04 and is collected by the runner; no collisions (or the collision is reported).
- [ ] `targetDir`, namespace and build target match the mapping and the Design record.
- [ ] The same module given as a `~`-prefixed path, and (on Windows) with backslash separators, resolves identically (guide [8.1](writing-translator-skills.md#81-resolver-resolve_utspy-must) "Validate the module").

Then run the negative cases and check each returns `ok: false` with the right code: a path whose parent isn't `uts`; a missing directory; a module with no tier directories (a scratch directory named `uts/<x>` will do); a mapping entry whose notes file is missing (use a scratch copy of the mapping); `--create` with an invalid name; `--create` on a scratch copy of a deliberately corrupt mapping (the file must be left unchanged).

### 8.2 Test the audit itself

Use one known-good test file (the pilot output from [8.3](#83-pilot-translate-one-spec-per-available-tier) once it is reviewed; until then, a hand-written file with the correct tags) and make scratch copies for each mutation. If you started with the hand-written file, run the mutations again once the pilot output passes review:

| Mutation | Expected audit result |
|---|---|
| Delete one assertion | A positive assertion shortfall for that test |
| Comment out one assertion | The same shortfall (commented assertions don't count) |
| Duplicate one test's tag | `duplicate` lists the ID; distinct non-zero exit |
| Add a tag that isn't in the spec | `orphan` lists it |
| Remove one tag | `missing` lists it |
| Add surplus waits to a test with a deleted assertion | The assertion shortfall is still reported (counts aren't summed) |
| Delete the poll call that renders a spec `poll_until` (with no `AWAIT` on the spec line) | An await shortfall for that test (spec polls count as waits) |

**Whole-corpus sweep:** run the audit on every spec the resolver lists for each of the three modules, against an empty test file. Every run must print one parseable JSON object and exit with the "ID problems" code (or report "not verifiable" for ID-less specs such as `rest/unit/encoding/msgpack_interop.md`). No crashes. Cross-check the spec-side ID count per module against ``grep -rhoE '\*\*Test ID\*\*: `[^`]+`' <spec-clone>/uts/<module> | sort -u | wc -l`` (as of `12540dcf`: rest 571, realtime 554, objects 339).

### 8.3 Pilot-translate one spec per available tier

Choose one spec per ready module × tier in scope, and at least one per module with a full notes file (D-25). A good pilot is short, representative of the tier, and uses the harness features most likely to be wrong:

| Tier | Choose a spec that uses | Example candidates in the corpus |
|---|---|---|
| REST unit | `MockHttpClient`, request capture, `FAILS WITH` | `rest/unit/time.md` |
| Realtime unit | `MockWebSocket`, `enable_fake_timers`, `ADVANCE_TIME`, `AWAIT_STATE` | `realtime/unit/connection/when_state_test.md` |
| Objects unit | `setup_synced_channel`, builders, serial helpers | `objects/unit/internal_live_counter_api.md` (then a mutation spec) |
| Direct integration | `SandboxApp`, `BEFORE ALL TESTS`, `## Protocol Variants` | `rest/integration/publish.md` (has `## Protocol Variants`), or `rest/integration/time_stats.md` then `realtime/integration/channel_history_test.md` |
| Proxy | `create_proxy_session`, rules, the event log | `rest/integration/proxy/rest_fallback.md` or `realtime/integration/proxy/connection_resume.md` |

The candidates are examples only. Before choosing one, confirm it exists in your clone (`ls <spec-clone>/uts/<path>`) and still uses the features listed (grep for them); check it against the module's scope and the SDK's features. Prefer specs with no existing UTS-derived test in the repo (P-20); if the best candidate has one, ask the user before the skill adds to or regenerates it.

**Run the pilot the way a user would.**

- **Loading the skill.** A skill created during a session may not be listed until a new session starts. Ask the user to start a new Claude Code session in the repo, on an Opus-class model ([2.8](#28-model-tier-and-sub-agents)) (or to reload skills, if their client supports it), and confirm `/uts-to-<lang>` is listed. A fresh session also tests that the skill is context-complete on its own (guide intent), so the pilot never consults the reference implementations.
- **Answering its questions.** The answers are D-03 (mapping confirmation) and D-25 (tier, specs, mode), confirmed at STOP-8. Either the user runs `/uts-to-<lang> <spec-clone>/uts/<module>` in the new session and answers with them, or, if the skill is listed in a session you control, you invoke it and answer with exactly those choices. If you use a subagent, run it on an Opus-class model ([2.8](#28-model-tier-and-sub-agents)), and give it only the invocation and the D-25 answers, none of this run's context. It must not consult the reference implementations or any other SDK's skill, because the pilot tests the skill alone. Record the pilot session's or subagent's model with the pilot results. Any answer not covered by D-25 goes to the user.
- **Record each question the skill asked.** More than the four questions, other than a stop the guide requires (an unmapped module's name at step B, a known gap or red harness at step F, an unmapped construct, the fix-attempt bound), or a question it should have answered from its own files, is a skill defect ([8.4](#84-fix-the-cause-then-regenerate)).

**A green preflight comes first.** The skill's step F (after **STOP-6** for network tiers) must pass for the pilot's tier before the pilot translates anything; a pilot run on a red harness doesn't count. Record the preflight result with the pilot. If network access is declined, that tier's pilot isn't run and is reported as unvalidated.

Use translate-only mode if the SDK lacks the feature; otherwise evaluate. Then:

1. Compile (and collect: every tagged test function is collected; count a parameterised or protocol-variant test once).
2. Audit; walk the review checklist (guide [8.3](writing-translator-skills.md#83-review-checklist-must-after-the-audit)).
3. In evaluate mode, and after **STOP-6** for network tiers, run the class by filter and diagnose per `writing-derived-tests.md` Phase 2.
4. Review the generated file line by line against the spec yourself, and show it to the user.

### 8.4 Fix the cause, then regenerate

For every defect in a pilot test:

1. Classify it: a rule in `SKILL.md`, a mapping in the notes, a catalogue row, a resolver or audit bug, or a harness gap. (A UTS spec error is not a skill defect: record it, emit the fail-fast test per D-10, and **STOP-10**.)
2. Fix that cause. **Never edit only the generated test.** A harness fix follows the rules of [5.1](#51-step-3a-rules-while-building), adds or extends a self-test that would have caught the defect, re-runs the affected tiers' smoke tests and self-tests, and updates the harness README (and its Known gaps).
3. Delete the generated test and regenerate it with the skill.
4. Re-audit, recompile and, in evaluate mode, re-run.
5. Log the defect and the fix in the Design record's changelog.

**Bound:** once a pilot spec has been regenerated three times (or the D-21 count) without a clean audit and, in evaluate mode, one of the three end states, stop (**STOP-10**) with a summary of every defect found and fixed so far. Count all regenerations of that spec together, not per defect.

### 8.5 Exercise the skill's other paths

Run each path through the skill (in the session from [8.3](#83-pilot-translate-one-spec-per-available-tier)) and record the result:

1. **Usage guard:** no argument → the usage line, then stop.
2. **Bad module path:** a path whose parent isn't `uts` → the resolver's error relayed, then stop.
3. **Placeholder notes:** a module whose notes file is a placeholder → refused, with the reason.
4. **Unready tier:** a tier the mapping marks unready → not offered at step C, with its `blockedBy`.
5. **Unmapped module:** on a scratch copy of the mapping, a module without an entry → step B asks for a name and runs `--create`, which writes the D-03 default layout and preserves the other entries.
6. **Re-sync** (if D-19 ships it): set a pilot file's header SHA to an older spec commit that changed that spec (`git -C <spec-clone> log --format=%H -- uts/<path>`), run `--resync`, and check the classification, that the header SHA is updated, and that only the survivors in guide [9.2](writing-translator-skills.md#92-a-re-sync-mode-should) step 4 are preserved. Restore the file afterwards.
7. **Commands:** every build, run, lint and audit command `SKILL.md` names has now been run through the skill; fix any that failed.
8. **Red harness:** on a scratch copy (or a temporary working-tree edit you revert afterwards), break one harness test (for example, make the WebSocket mock refuse every connection), or run an integration tier with the network unavailable → the skill stops at step F before generating anything, reports a harness or environment problem (not an SDK deviation), and names the failing test. Restore the change and confirm the preflight is green again.
9. **Known gap:** select a spec that uses a construct the harness README lists under Known gaps → the preflight reports the conflict and stops to ask (guide 4 step F), rather than generating a substituted rendering. If Known gaps is empty, use a scratch copy of the README with an entry for a construct the selected spec uses.

### 8.6 Lint and CI-strict compile

Run the repo's lint and format gates (P-06) over every file you created or changed, including the harness, the skill's scripts and Markdown where the repo's EditorConfig covers them. Compile the test targets as strictly as CI does (warnings as errors, static analysis, type checkers). Run the skill's scripts on every developer platform you can, or note which you couldn't.

### 8.7 Verify the skill's own examples

Every code example in `SKILL.md` and the notes must compile (guide [12](writing-translator-skills.md#12-lessons-learned)). For each example, either:

- name the real, compiled file it was copied from (and check it still matches), or
- paste it into a scratch file in the test target, compile, and delete the scratch file.

Record which examples were verified and how.

### 8.8 Name the reference tests

After review, name one spec-derived test file per tier in `SKILL.md` as the file to read first (guide [4, step 3](writing-translator-skills.md#phase-2-per-spec-steps-17)). Never name a smoke test.

**Phase 6 is done when:** the resolver passes on all three modules and all negative cases; every path in 8.5 behaves as expected (including the red-harness stop) and every command in `SKILL.md` has been run; every pilot ran after a green preflight; the audit passes every mutation and the sweep; each pilot compiles, audits clean (or every shortfall is accounted for) and, in evaluate mode, ends in one of the three end states; lint and the CI-strict compile pass; every example is verified.

---

## 9. Phase 7: final report and handover

1. Write `final-report.md` from [Appendix D](#appendix-d-final-report-template).
2. Fill the acceptance checklist in [Appendix E](#appendix-e-acceptance-checklist-guide-section-13): tick each item, or explain why it isn't met (scoped out, planned, not applicable).
3. Show the user the report, the list of changed and new files (harness, harness tests, hooks, skill, pilot tests), and the suggested CI changes. The run is complete only if the harness tests are green, and in CI, at every tier the skill supports; otherwise the report says which tiers aren't and why. **Don't commit** unless asked.
4. If the user asks for a commit, follow the repo's commit conventions (P-08) and, if the user agrees, keep the SDK hooks, the harness, the skill and the pilot tests in separate commits.

---

## 10. Maintenance

The harness and the skill must stay in step with five things that change independently. Record the current state of each in the Design record ("Inputs at generation time"), so a later agent can diff against it.

| What changed | How to detect it | What to update |
|---|---|---|
| **The guide** | `git -C <spec-clone> diff <recorded-sha>..HEAD -- uts/docs/translator-skills/` | Map each changed guide section to the artifacts that implement it, using the "Guide" columns in [6.1](#61-step-4a-draft-the-design-record) and [7.6](#76-step-5f-write-skillmd) and the gap table; update them; re-run the Phase 3 and Phase 6 checks for those artifacts |
| **The UTS docs or helper specs** | `git -C <spec-clone> diff <recorded-sha>..HEAD -- uts/README.md uts/docs/ uts/objects/helpers uts/rest/unit/helpers uts/realtime/unit/helpers` | Re-run the Phase 2 assessment for the affected rows; update the harness, its smoke tests and self-tests, and its README (Known gaps), the catalogue rows and notes item 9; then re-sync the affected tests |
| **The UTS corpus** | The skill's own re-sync mode (guide [9.2](writing-translator-skills.md#92-a-re-sync-mode-should)), plus the construct scanner ([7.4](#74-step-5d-fill-the-construct-catalogue)) | New catalogue rows (stop and ask for any unmapped construct); new harness symbols the corpus uses; regenerated tests; renamed IDs handled per guide [9.3](writing-translator-skills.md#93-renamed-merged-and-added-ids) |
| **The harness itself** (a helper, mock, fixture or harness test changes) | Its smoke tests and self-tests in CI; the skill's preflight on every run | Fix a red harness test in the harness before any further translation; update the README and Known gaps; regenerate the tests whose rendering depends on the changed helper (guide 9.2) |
| **The SDK** (API, hooks, test layout, CI) | `git -C <repo> diff <recorded-sha>..HEAD` over the paths the Repo profile names | Repo profile; harness and hooks; notes (the SDK source is ground truth); mapping; then a re-sync if the harness or module helpers changed shape |

Rules for every maintenance run:

- Follow the same ground rules ([section 2](#2-ground-rules)) and stop points, including the model tier ([2.8](#28-model-tier-and-sub-agents)) and the last-resort rules for reference-implementation reads ([2.1](#21-your-inputs)). If the guide's "as of" commits have moved since a recorded read, re-check that read's conclusion against the updated Patterns to avoid before relying on it again.
- Start from the working records; update the Repo profile and the harness design if anything they describe has changed.
- Regenerate tests through the skill; the only per-test state that survives is the list in guide 9.2 step 4 (DEVIATION gates, adapted assertions, `deviations.md` entries and, per `writing-derived-tests.md`, UTS-spec-error fail-fast placeholders until the spec is fixed) (guide [9.2](writing-translator-skills.md#92-a-re-sync-mode-should)).
- After any harness change, re-run every affected tier's smoke tests and self-tests, and regenerate the affected tests; after any script change, repeat [8.1](#81-run-the-resolver-on-every-module) and [8.2](#82-test-the-audit-itself).
- Record the new spec SHA and repo SHA in the Design record and append a changelog entry.

---

## Appendix A: Repo profile template

```markdown
# Repo profile: <repo name>

- Repo: <path>, HEAD <sha> (clean | dirty: <files>)
- Spec clone: <path>, HEAD <sha> (clean | dirty: <files>); guide last changed in <sha>
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
```

## Appendix B: Gap table and harness design template

```markdown
# Harness design: <repo name> @ <sha>

## Gap table
| # | Capability | Guide | Status | Evidence | Approach (reuse / wrap / extend / build / n/a) | Builds on | Blocks (module/tier) | Production change? | Size | Acceptance check |
|---|---|---|---|---|---|---|---|---|---|---|
| G-01 | WebSocket transport factory hook | 2.1 | present / partial / missing / n/a | | | | realtime/unit, objects/unit | yes / no | S/M/L | |
| G-02 | HTTP client hook | 2.1 | | | | | rest/unit | | | |
| G-03 | Clock hook (timers, timed waits, async-runtime timers) | 2.1 | | | | | | | | |
| G-04 | Network-monitor hook | 2.1 | | | | | | | | |
| G-05 | Randomness hooks (jitter, host shuffle) | 2.1 | | | | | | | | |
| G-06 | MockHttpClient (+ legacy queue_*) | 2.2, mock_http.md | | | | | | | | |
| G-07 | MockWebSocket (+ alternative API, undocumented members, raw frames, ping) | 2.2, mock_websocket.md | | | | | | | | |
| G-08 | MockVCDiff encoder/decoders | 2.2, mock_vcdiff.md | | | | | | | | |
| G-09 | MockNetworkListener | 2.2 | | | | | | | | |
| G-10 | standard_test_pool.md implementation; plugin options builder | 2.2, standard_test_pool.md | | | | | | | | |
| G-11 | Wait helpers (AWAIT_STATE, poll_until, poll_until_success, process_pending_events, wall-clock wrapper, fake clock driver) | 2.2, 5.6, 5.7 | | | | | | | | |
| G-12 | Thread-safe capture, log sink, assertContainsInOrder, caller-attributed failures | 2.2 | | | | | | | | |
| G-13 | Placement and recommended harness layout (shared / port-only / module helpers); fixture-helper scope documented in the module notes | 2.2 | | | | | | | | |
| G-14 | Harness README with Known gaps; mapping `harness` entry (root, README, per-tier sources and harness-test commands) | 3.1, 3.2 | | | | | | | | |
| G-15 | SandboxApp; ably-common | 2.3 | | | | | */integration | | | |
| G-16 | ProxyManager (pinned, every OS); ProxySession; rule builders; proxy auth | 2.4 | | | | | */proxy | | | |
| G-17 | UTS test target; per-tier selection and filters; one CI home per suite | 2.5 | | | | | | | | |
| G-18 | Concurrency, time, parallelism and visibility models known | 2.6 | | | | | | | | |
| G-19 | Per-tier smoke tests (permanent, in CI, outside generated dirs) | 2.7 | | | | | | | | |
| G-20 | Helper self-tests (common, unit, fake clock, REST, objects, sandbox, proxy) | 2.7 | | | | | | | | |

## Helper-spec symbol maps (one table per helper spec)
### mock_http.md
| Spec symbol (declared or corpus-only) | Native type.member | Approach | Builds on | Notes |
|---|---|---|---|---|
### mock_websocket.md
### mock_vcdiff.md
### standard_test_pool.md
### MockNetworkListener (no helper spec)

## Wait and assertion helpers
| Helper | Native symbol | Approach | Guarantees checked by |
|---|---|---|---|

## Sandbox and proxy
- Sandbox provisioning: …; client targeting (endpoint or hosts): …; suite fixture mapping: …
- Proxy: version …; binaries per OS …; local override …; auth through the proxy …; platform gating …

## Hook proposals (each needs STOP-4 approval)
| Hook | API | Default behaviour | Visibility | Files touched | Installed how | Per-client? | Approved on |
|---|---|---|---|---|---|---|---|

## Placement
- Shared test-support: <dir/target>; port-only harness: <dir/target>; module helpers: <dir per module>

## Tier feasibility
| Module | unit | integration | proxy |
|---|---|---|---|
| rest | ready / after G-.. / not possible: <why> / n/a | | |
| realtime | | | |
| objects | | | |

## Decision at STOP-3
(a) build now: <rows> | (b) plan only | (c) scope to ready tiers — chosen by <user> on <date>; design changes requested: …

## Build log (Phase 3) / plan (option b)
| Order | Row | Work | Acceptance check | Result | Date |
|---|---|---|---|---|---|

## Confirmation at STOP-7
Smoke tests and self-tests per tier (filter, result, CI job): …; updated tier matrix: …; confirmed on <date>
```

## Appendix C: Design record template

```markdown
# Design record: uts-to-<lang>

## Inputs at generation time
- Spec clone: <sha> (clean | dirty); guide: <sha of last change>
- Repo: <sha>
- Repo profile confirmed: <date>; harness option at STOP-3: (a | b | c); harness confirmed: <date>
- Harness README: <full repo path>
- Model: <name and ID> (Opus-class: yes | no, departure in decision log #<n>); sub-agents: <role → model>, or none

## Decisions
| ID | Decision | Choice | Guide-default? | Decided by | Rationale |
|---|---|---|---|---|---|
| D-01 | Skill name and location | | yes / no | user / agent | |
| D-02 | Script language and runtime | | | | |
| D-03 | Mapping: module × tier → target dir (hand-maintained entries marked) | (table below) | | | |
| D-04 | Naming and collection rules (with three worked examples) | | | | |
| D-05 | Collision handling | | | | |
| D-06 | Tag syntax | | | | |
| D-07 | File header format | | | | |
| D-08 | deviations.md location(s) | | | | |
| D-09 | Runtime skip idiom; RUN_DEVIATIONS command | | | | |
| D-10 | Fail-fast idiom | | | | |
| D-11 | Pending idiom for missing APIs | | | | |
| D-12 | Internal-access ladder; white-box spec list location | | | | |
| D-13 | Delegation policy | | | | |
| D-14 | Parallelism policy | | | | |
| D-15 | Teardown; suite-level fixtures | | | | |
| D-16 | Protocol-variant rendering | | | | |
| D-17 | Default timeouts and poll interval | | | | |
| D-18 | Auth through the proxy | | | | |
| D-19 | Re-sync flag; manifest; corpus scanner shipped? | | | | |
| D-20 | Commit policy; project/solution-file edits (approved / left to the user) | | | | |
| D-21 | Fix-attempt bound | | | | |
| D-22 | allowed-tools; remote access | | | | |
| D-23 | Notes files per module (full / placeholder) | | | | |
| D-24 | Working-records location | | | | |
| D-25 | Pilot specs and mode per tier | | | | |
| D-26 | Model tier and pinning for skill runs | | | | |

### D-03 mapping
| Module | unit | integration | proxy | notes | hand-maintained? |
|---|---|---|---|---|---|

## Decision log
| # | Date | Phase | Question | Options | Answer | By | Supersedes |
|---|---|---|---|---|---|---|---|

## Reference-implementation reads (last resort, 2.1)
| # | Date | Question | Guide/UTS sections searched | Repo @ commit : path | Pattern learned (not copied) | Checked against Patterns to avoid | Access (local clone / GitHub, STOP-6 approval) |
|---|---|---|---|---|---|---|---|

## Changelog (fixes made to the skill, notes or harness)
| # | Date | Found by | Cause (skill / notes / catalogue / script / harness) | Fix | Tests regenerated |
|---|---|---|---|---|---|
```

## Appendix D: Final report template

```markdown
# Final report: uts-to-<lang> for <repo>

- Spec clone <sha> (clean | dirty); repo <sha>; date
- Model: <name and ID> (Opus-class: yes | no, and why); sub-agents: <role → model>, or none
- Scope: <modules × tiers covered>; out of scope and why

## Files created or changed
| Path | New / changed | Kind (hook, harness, smoke test, skill, script, notes, pilot test, CI suggestion) | Approved at |
|---|---|---|---|
Hand-maintained project files the user must update: …

## Repo profile
Link to repo-profile.md; corrections made at STOP-2.

## Harness
Gap table status after this run (rows reused, wrapped, extended, built, planned, open); option chosen at STOP-3; hooks added (with approvals); smoke-test and self-test results per tier, and their CI jobs; preflight results from the pilot runs; harness changes made during Phase 6 (with the self-tests added); the README's Known gaps; the plan for any remaining rows. Link to uts-infra-design.md and the harness README.

## Design decisions
Link to design-record.md; decisions that depart from the guide's defaults, and why.

## Validation results
- Resolver: rest / realtime / objects → ok, spec counts; negative cases → codes
- Audit self-test: each mutation → result; corpus sweep → N specs, 0 crashes, unverifiable specs listed
- Lint: …; CI-strict compile: …; examples verified: N of N (how)

## Pilot results
(each pilot run's full section-11 report as the skill printed it: the header line, the table row, and every labelled line, including not-applicable omissions, missing APIs, mock-capability gaps, harness stand-ins and constructs it couldn't map; the table below collects the rows)
| Spec file | Test file | IDs (spec/test) | Audit | Shortfall accounted | Compile | Run | Deviations added |
|---|---|---|---|---|---|---|---|
Fixes made to the skill, notes or harness during the pilot (from the changelog): …
Reference tests named in SKILL.md: <tier → file>

## Known limitations
Tiers not ready; `not available` catalogue rows; harness capabilities missing; audit SHOULD items not implemented; platforms the scripts weren't run on.

## Deviations and spec issues found
- SDK deviations (recorded in deviations.md): …
- Suspected UTS spec errors or gaps: <id> — <one line>; draft fix: …
- Spec-repo doc issues (contradictions between guide and UTS docs; guide gaps revealed by reference-implementation reads): …

## Reference-implementation reads
Each read from the Design record (question, repo @ commit : path, pattern learned, how it was checked against Patterns to avoid), with the guide gap it reveals and a draft guide fix. "None" if the guide sufficed.

## Suggested CI changes
<job, trigger, command, network/submodule/proxy needs> (not applied unless approved at STOP-5)

## Next steps
Which modules and tiers to translate next, in order, and why; harness work remaining.

## Acceptance checklist
(Appendix E, filled)
```

## Appendix E: Acceptance checklist (guide section 13)

Fill this in the Final report. Each row is one item of the guide's [checklist](writing-translator-skills.md#13-checklist-for-a-new-uts-to-lang-skill), with where this procedure produces or verifies it. Mark each ✓, ✗ (with the reason) or n/a (with the reason).

| Guide §13 item | Produced in | Verified in | Status |
|---|---|---|---|
| **Harness** | | | |
| SDK test hooks (5), clock covering blocking waits and async-runtime timers, injected at construction | 4.6; 5.2 rows 3–4 | 5.2 acceptance; G-01…G-05 | |
| Shared test library per helper spec (incl. legacy `queue_*` and `mock_http.captured_requests`; `mock_websocket.md` async close, CONNECTED ordering, raw frames, alternative API and undocumented members; vcdiff; test pool; `MockNetworkListener`) | 4.3; 5.2 rows 5–6, 8, 11 | smoke tests; G-06…G-10 | |
| Wait helpers (latched, fail-fast `AWAIT_STATE`; value-returning `poll_until`; `poll_until_success`; `process_pending_events`; wall-clock wrapper; fake-time-safe deadlines) | 4.4; 5.2 row 7 | helper tests; G-11 | |
| Thread-safe capture, log sink, `assertContainsInOrder`, caller-attributed failures | 4.4; 5.2 row 2 | helper tests; G-12 | |
| Harness designed from the repo's existing test setup (reuse, wrap, extend or build, 2.2); shared vs port-only placement; recommended harness layout; fixture-helper scope documented | 4.2; 4.7; 5.3; notes item 9 | G-13 | |
| Harness README with a Known gaps section (MUST) | 5.3; 5.2 row 12 | G-14; 8.5 path 9 | |
| Harness smoke tests per tier and helper self-tests: permanent, in CI, ungated, untagged, outside generated-test directories (MUST) | 4.7; 5.2 rows 1–11, 13 | STOP-7; G-19, G-20; 8.5 path 8 | |
| `SandboxApp` (idempotent retries only); `ably-common` | 4.5; 5.2 row 9 | smoke integration test; G-15 | |
| `ProxyManager` (pinned, every OS, verified download, health check, port handling); `ProxySession`; string `match.action`; proxy auth decided and commented | 4.5; 5.2 row 10; D-18 | smoke proxy test; G-16 | |
| One CI home per suite (MUST); per-tier jobs (SHOULD) | 5.2 row 13 or suggested CI changes | G-17; Final report | |
| Concurrency, time, parallelism, visibility models documented | Phase 1 (P-09 to P-14) | STOP-2; G-18 | |
| **Skill files** | | | |
| `SKILL.md`: name, pushy description, `argument-hint`, usage guard, placeholder paths, 3.4 outline incl. the Harness reference | 7.6 | 7.6 acceptance; 8.3 | |
| `uts-package-mapping.json`: one path per tier, unique namespaces, `notes` relative, hand-maintained entries marked, `harness` entry | 7.1 | 7.1 acceptance; 8.1 | |
| `resolve_uts.py`: validation, errors, output contract, path tiers, relative exclusions, collectable names, collisions, validate-then-write `--create` preserving other entries, `harness` output | 7.2 | 8.1 | |
| `audit_translation.py`: parsing contract, ID coverage, duplicates, separate counts, ignores commented assertions, never crashes, flags unverifiable; mutation-tested | 7.3 | 8.2 | |
| Module notes for every diverging module (at least `objects`) | 7.5; D-23 | 7.5 acceptance | |
| Scripts run on every developer platform (path handling, UTF-8, LF) | 7.1–7.3; D-02 | 8.1 (path parts, `~`), 8.6 (platforms) | |
| **Workflow** | | | |
| Required reading incl. features specs, from the same clone | 7.6 (step 0) | 8.3 pilot | |
| Steps 0 and A–F: the four questions and the harness preflight (stop on red) | 7.6 | 8.3 pilot (green preflight first); 8.5 paths 8–9 | |
| Steps 1–7 with batching; a reference test per tier; review in both modes | 7.6; 8.8 | 8.3 pilot; 8.8 | |
| Unmapped constructs stop and ask; corpus scanner in `scripts/` (SHOULD) | 7.4; 7.6; D-19 | 8.3 pilot; 8.5 (re-sync) | |
| Re-sync mode; fix the cause, then regenerate | 7.6; D-19 | 8.5 (re-sync); 8.4 (fix and regenerate) | |
| Mid-run harness changes re-run the smoke tests and self-tests and are reported separately | 7.6 (Harness reference) | 8.4 step 2; final report | |
| **Translation rules in `SKILL.md`** | | | |
| One verbatim `UTS: <id>` per test; no invented tags; spec point in a collectable name | 7.6; D-04, D-06 | 8.2, 8.3 | |
| File header: source spec, tier, spec SHA, disclosures, corresponding unit spec | 7.6; D-07 | 8.3 | |
| Verbatim comments, spec variable names, section headings, spec order | 7.6 | 8.3 review | |
| Annotate, never drop, every `ASSERT`/`AWAIT`; never substitute a similar mock outcome | 7.6; 7.4 | 8.3 audit | |
| Policies for sub-cases, groupers, test-case tables, delegating tests, ID-less tests | 7.6; D-13 | 8.3 (where the pilot has them) | |
| Protocol variants parameterised; tag singular; proxy JSON only | 7.6; D-16 | 8.3 integration pilot | |
| Clients closed in teardown; mocks restored; stop on a failed wait | 7.6; D-15 | 8.3 | |
| Unique channel names; own proxy session per test | 7.6 | 8.3 integration/proxy pilots | |
| Unit: fake time and flushes, no real timers. Integration: wall-clock | 7.6; 7.4; D-17 | 8.3 | |
| Record-and-verify for transient states; polls return the settled value | 7.6; 7.4 | 8.3 | |
| No accommodate-both assertions; `IS <Type>` per typing discipline | 7.6 | 8.3 review | |
| Public-API specs stay public; internal-access ladder with escalation stop | 7.6; 7.5 item 8; D-12 | 8.3 | |
| Construct table filled for every row | 7.4 | 7.4 acceptance | |
| **Evaluation** | | | |
| Three end states; runtime skip and fail-fast idioms; `RUN_DEVIATIONS` command | 7.6; D-09, D-10 | 8.3 (evaluate) | |
| `deviations.md` location; format deferred; written at the right time | 7.6; D-08 | 8.3 (evaluate) | |
| Harness stand-ins in comments, not `deviations.md` | 7.4; 7.6 | 8.3 review | |
| Language-inapplicable inputs (cases a–c) noted in the test file | 7.6; D-11 | 8.3 (where they occur) | |
| Stopping rules and spec-error escalation | 7.6; D-21 | 8.4 | |
| **Verification** | | | |
| Compile (or collect), lint, CI-strict compile, filtered run | 7.6 | 8.3, 8.6 | |
| No commits by default; changed files listed | 7.6; D-20 | Phase 7 | |
| Final report format | 7.6 | 8.3 (the skill's report) | |
| The skill's own examples compile | 7.5 item 12; 7.6 | 8.7 | |
| **Creation process** | | | |
| Skill and harness created on an Opus-class model (MUST); model pinned or stated for runs (SHOULD) and recorded in the skill's final report | 2.8; D-26; 7.6 (frontmatter, final report) | Design record "Inputs at generation time" (Model line); 8.3 (pilot model recorded); Final report header | |
| Reference-implementation reads, if any, last resort only, recorded and reported as guide gaps | 2.1; Appendix C | Final report "Reference-implementation reads" | |

## Appendix F: Glossary

| Term | Meaning |
|---|---|
| **UTS** | Universal Test Suite: language-neutral pseudocode test specs in `uts/` of the spec repo |
| **Module** | A top-level corpus directory: `rest`, `realtime`, `objects` |
| **Tier** | `unit` (mocked transports), `integration` (direct sandbox), `proxy` (sandbox through `uts-proxy`), detected by path |
| **Spec** | One Markdown file of UTS tests; **features spec** means the Ably specification under `specifications/` |
| **Test ID / tag** | The `**Test ID**` of a spec test; the `UTS: <id>` comment above the derived test |
| **Helper spec** | A spec of harness behaviour (`mock_http.md`, `mock_websocket.md`, `mock_vcdiff.md`, `standard_test_pool.md`); implemented once, never translated |
| **Hook** | An injection point in SDK production code that the harness uses (transport, HTTP, clock, network monitor, randomness) |
| **Harness (UTS test infrastructure)** | The native test library implementing the helper specs, wait helpers, sandbox and proxy helpers and fixtures |
| **Reuse / wrap / extend / build** | The four ways to provide a harness capability from what the repo has ([4.2](#42-step-2b-assess-each-capability-reuse-wrap-extend-or-build)) |
| **Shared / port-only** | Harness code used by native tests and UTS ports alike / used only by UTS ports |
| **Smoke test** | A per-tier harness test that drives one tier end to end through the real hooks (guide 2.7); permanent, in CI, not spec-derived, no tag, never a reference test |
| **Self-test** | A harness test that checks one helper obeys its helper-spec contract (guide 2.7); permanent, in CI, no tag |
| **Preflight** | The generated skill's step F: compile, run the tier's smoke tests and self-tests, check Known gaps; stop on red |
| **Reference test** | A reviewed, spec-derived test per tier that the skill reads before generating |
| **Reference implementations** | The existing `uts-to-swift` (ably-cocoa) and `uts-to-kotlin` (ably-java) skills and their harnesses, at the commits the guide pins: a last-resort, read-only reference for patterns, never copied and never an authority ([2.1](#21-your-inputs)). Not a reference test |
| **Opus-class model** | The most capable model tier available (Claude Opus or an equivalent); required for this procedure and its sub-agents ([2.8](#28-model-tier-and-sub-agents)) |
| **Notes** | `references/<module>-mapping.md`: how ably-js-shaped pseudocode maps to this SDK for one module |
| **Resolver** | `resolve_uts.py`: validates a module and derives targets and names; its output is the single source of truth |
| **Audit** | `audit_translation.py`: compares a spec with its test file (IDs, ledger, counts) |
| **Ledger / shortfall** | The per-test list of spec lines by kind / spec count minus test count, for assertions and waits separately |
| **Translate-only / evaluate** | Generate and statically check / also run and diagnose |
| **Deviation** | An SDK behaviour that differs from a correct spec, recorded in `deviations.md` |
| **Stand-in** | A harness-level difference in how a test drives the SDK; disclosed in a comment, not a deviation |
| **White-box spec** | A unit spec that drives internal APIs; listed in the notes |
| **Delegating spec/test** | One that says to run another module's tests against this client |
| **Re-sync** | Re-auditing a module against a newer spec SHA and regenerating what changed |
| **Spec SHA** | The commit of the local spec clone that a test, or the skill, was derived from |
| **Phase N / skill Phase 1–2** | "Phase N" (1–7) is a phase of this procedure. "Skill Phase 1" (selection, steps 0 and A–F) and "skill Phase 2" (per spec, steps 1–7) are the generated skill's workflow (guide [4](writing-translator-skills.md#4-the-workflow-the-skill-must-implement)). `writing-derived-tests.md` Phase 1/2 is always named with that document |
| **Working records** | Repo profile, Harness design (with the gap table), Design record, Final report |

## Appendix G: Common failure modes and remedies

All from the guide and the UTS docs; follow the link for the detail.

| Symptom | Likely cause | Remedy | Source |
|---|---|---|---|
| Tests compile but the runner collects none (or fewer than the tags) | Names don't match the runner's collection rules | Fix the resolver's naming (D-04); compare the distinct collected test functions (a parameterised test counted once) with the tag count | guide [10](writing-translator-skills.md#10-verification-and-ci), [5.1](writing-translator-skills.md#51-traceability) |
| Integration waits time out instantly with a misleading timeout message | The runner virtualises time; the timeout measures virtual time | Wrap every real-network wait in a wall-clock helper | `writing-derived-tests.md` "Integration timeouts are wall-clock"; guide [5.6](writing-translator-skills.md#56-time-and-waiting) |
| A poll under fake timers never expires | The poll deadline reads the faked clock | Restructure to avoid stubbing the wall clock, or read a monotonic clock | `writing-derived-tests.md` "No real timers in unit tests"; guide [5.6](writing-translator-skills.md#56-time-and-waiting) |
| Retries fire on wall-clock time despite `ADVANCE_TIME` | A timed blocking wait or a runtime timer isn't on the fake clock | Extend the clock hook to every time source (P-11) | guide [2.1](writing-translator-skills.md#21-sdk-test-hooks-must) |
| A wait misses a transient state | Sampling wait, or check-before-subscribe race | Event-latched `AWAIT_STATE`; record-and-verify with `CONTAINS_IN_ORDER` | guide [5.7](writing-translator-skills.md#57-waits-must-catch-events) |
| `CONTAINS_IN_ORDER` fails although the states occurred | Rendered as a contiguous prefix or an exact filtered list | Subsequence helper | guide [6.7](writing-translator-skills.md#67-notes-on-the-catalogue) |
| A state wait runs out the timeout after the connection failed | No fail-fast on FAILED | Fail immediately on FAILED, except when the test just requested a transition out of it | guide [5.7](writing-translator-skills.md#57-waits-must-catch-events) |
| Assertions after a poll see fewer items | The test re-reads after polling an eventually-consistent store | Use the value the poll returned | guide [5.7](writing-translator-skills.md#57-waits-must-catch-events) |
| `poll_until_success` times out with no useful error | Emulated with a reader that swallows errors | A separate helper that rethrows the last error | guide [5.7](writing-translator-skills.md#57-waits-must-catch-events); `uts/README.md` |
| Negative assertions pass or fail at random | One zero-delay yield doesn't drain chained callbacks | Drain until the internal queue is empty; or the quiescence control-listener | guide [2.6](writing-translator-skills.md#26-understand-the-sdks-concurrency-model-must); `standard_test_pool.md` "Negative-assertion quiescence" |
| Tests pass alone, fail together | Process-global hooks with a parallel runner; leaked clients or timers | Serialise or make hooks per-client (D-14); close clients and restore mocks in teardown | guide [2.6](writing-translator-skills.md#26-understand-the-sdks-concurrency-model-must), [5.4](writing-translator-skills.md#54-setup-and-teardown) |
| State machine misbehaves only under the mock | Mock `close()` calls `onClose` synchronously, or CONNECTED arrives before the connection completes (often an existing double reused unchanged) | Fix or wrap the mock per `mock_websocket.md` | guide [2.2](writing-translator-skills.md#22-a-shared-test-library-implementing-the-helper-specs-must) |
| An objects test's operation is silently ignored | Hand-written serial literal sorts before the pool serial | Use the serial helpers | `standard_test_pool.md`; guide 2.2 |
| Proxy session creation fails with HTTP 400 | Numeric `match.action` | Stringify it in the rule builder | guide [2.4](writing-translator-skills.md#24-the-proxy-must-for-the-proxy-tier); `proxy.md` |
| A proxy rule never fires | Action name beyond the proxy's name table (`OBJECT`, `OBJECT_SYNC`, `ANNOTATION`) | Use numeric strings (`"19"`, `"20"`, `"21"`) | `proxy.md` "Match Conditions"; guide [2.4](writing-translator-skills.md#24-the-proxy-must-for-the-proxy-tier) |
| Proxied client fails to authenticate | Basic auth over the plain proxy hop (RSA1) | Token auth through the proxy, with a comment | guide [2.4](writing-translator-skills.md#24-the-proxy-must-for-the-proxy-tier) |
| Duplicate sandbox apps; flaky provisioning | `POST /apps` retried | Retry only idempotent requests; check the status before parsing | guide [2.3](writing-translator-skills.md#23-sandbox-provisioning-and-fixtures-must-for-integration-tiers) |
| Resource leaks after objects integration tests | REST provisioning client not closed | Close it | `standard_test_pool.md` "REST Fixture Provisioning"; guide [2.2](writing-translator-skills.md#22-a-shared-test-library-implementing-the-helper-specs-must) |
| Under virtual-time advances, the idle timer disconnects an objects fixture | The fixture's idle interval is shorter than the advance | Set a large idle interval in the fake-clock fixture variant and document it in the notes | guide [2.2](writing-translator-skills.md#22-a-shared-test-library-implementing-the-helper-specs-must), "Document each fixture helper's scope" |
| Audit says clean but an assertion is missing | Counts summed with waits; commented assertions counted; helpers after the last test attributed to it | Fix the audit; keep shared helpers before the first test or in a separate file | guide [8.2](writing-translator-skills.md#82-audit-audit_translationpy-must) |
| Generated class clashes with a native test class | Name collision across targets | Collision detection or target-qualified filters | guide [8.1](writing-translator-skills.md#81-resolver-resolve_utspy-must) |
| Module translated with a guessed mapping | Notes file missing (silent `null`) or a placeholder | Resolver error for a missing notes file; refuse placeholder modules | guide [8.1](writing-translator-skills.md#81-resolver-resolve_utspy-must), [4](writing-translator-skills.md#phase-1-selection-steps-0-and-af) |
| Local build green, CI red | CI is stricter (warnings as errors, static analysis, type checking) | Compile as strictly as CI in the skill | guide [10](writing-translator-skills.md#10-verification-and-ci); `writing-derived-tests.md` "Build pipeline and CI checks" |
| A test fixed by hand reverts on the next run | The fix was made only in the generated file | Fix the skill, notes or harness; regenerate | guide [5](writing-translator-skills.md#5-translation-rules) |
| Stale tests after a spec update | Renamed or merged IDs not followed | Re-sync mode; pair missing and orphan IDs; re-check assertions | guide [9.3](writing-translator-skills.md#93-renamed-merged-and-added-ids) |
| Rules in the skill and the manual disagree | The skill inlined a copy of a semantic rule | Link to the source instead | guide ["What the skill owns"](writing-translator-skills.md#what-the-skill-owns-and-what-it-defers), [12](writing-translator-skills.md#12-lessons-learned) |
