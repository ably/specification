---
name: uts-to-lang-skill-creator
description: "Builds or upgrades a uts-to-LANG translator skill, with the UTS test harness it runs on, for one Ably Pub/Sub SDK repository on this skill's whitelist (C#, Python, Go, JavaScript, Ruby, ...). Use it whenever asked to create a uts-to-* skill; to audit, fix, upgrade or refresh one after the guide, UTS docs, corpus or SDK changed; to add LiveObjects (uts/objects) support; or to set up UTS test infrastructure (SDK test hooks, MockHttpClient, MockWebSocket, fake clock, sandbox and proxy helpers, harness smoke tests and self-tests). First checks the repo is on the whitelist, then detects what it has (uts-to-* skills and their origin, harness, UTS-tagged tests, REST and Realtime capabilities and scope, LiveObjects API) and recommends Create or Upgrade/Fix, then runs a procedure with user stop points. Needs a local ably/specification clone. Not for Chat, Spaces, AI Transport, CLI or other non-Pub/Sub repos, for translating specs once a uts-to-* skill exists (use that skill), or for writing UTS specs."
license: Apache-2.0
compatibility: "Claude Code or Codex, on an Opus-class model. Needs shell and file access, git, Python 3.8+, a local clone of ably/specification, and the target SDK's build toolchain."
allowed-tools: Read Grep Glob
metadata:
  team: "engineering"
  version: "1.0.0"
  tags: "testing, uts, translator-skill, skill-creator, harness, ably-specification"
  marketplace: "false"
  short-description: "Detect, then build or upgrade a uts-to-LANG skill and its harness"
---

# UTS-to-Lang Skill Creator

**After a context compaction:** this file may be in your context only in part (Claude Code keeps only its start; Codex may keep none of it). Before your next action, read this whole `SKILL.md` again, then the Design record's Run status if the records exist ([13.7](references/orient.md#137-provenance-d-30)), then the reference of the phase you are in. Never act at a stop point from memory.

Run this skill on an Opus-class model ([2.8](#28-model-tier-and-sub-agents)). It is a step-by-step procedure for an LLM agent to create or upgrade a `uts-to-<lang>` translator skill, and the UTS test infrastructure (the **harness**) it runs on, for one Ably Pub/Sub SDK repository, starting with [Step 0: Orient](#step-0-orient). [Writing UTS Spec Translator Skills](../../docs/writing-uts-spec-translator-skills.md) (hereafter **the guide**) says what a good translator skill is and why; this skill says how to build one: in what order, with what checks, and where to stop and ask the user. Where the guide holds the reason or the detailed requirement, this skill links to it instead of repeating it; read the linked section.

The harness and the skill are one deliverable (guide [section 2](../../docs/writing-uts-spec-translator-skills.md#2-the-harness-uts-test-infrastructure)): the skill isn't complete until the harness's per-tier smoke tests and helper self-tests (guide [2.7](../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)) are green, and wired into CI, at every tier it supports. The harness reuses, wraps, extends or builds on the repo's existing tests ([4.2](references/phase-2-design-harness.md#42-step-2b-assess-each-capability-reuse-wrap-extend-or-build)), so the phases run in a fixed order.

"This skill" is this `SKILL.md` with its `references/` and `assets/templates/`. Section numbers are stable across the files: section n+2 holds Phase n and Orient is section 13; section 2 comes before section 1 so that it survives context compaction. MUST, SHOULD and MAY cite the guide's requirement levels; this skill's own instructions are imperatives.

## Path convention

- **Files of this skill** (`references/`, `assets/templates/`, `scripts/`) are relative to `<skill-dir>`, the directory that contains this `SKILL.md`, wherever it is installed. Run scripts as `python3 <skill-dir>/scripts/<name>.py`.
- **Files of the spec repo** (the guide, the UTS docs, the helper specs, the corpus) are linked relative to this skill's place in a spec clone, `uts/skills/uts-to-lang-skill-creator/`, so the links work on GitHub. A link that climbs out of the skill directory (`../../…` from `SKILL.md`, `../../../…` from `references/`) is a spec-repo path; every other link is a file of this skill. At run time, read a spec-repo path in the clone Orient pinned ([2.6](#26-pin-the-spec-clone)), never against the directory you loaded this skill from and never from GitHub: `…/docs/writing-uts-spec-translator-skills.md#31-layout` means section 3.1 of `<spec-clone>/uts/docs/writing-uts-spec-translator-skills.md`.
- **Inputs** come from the user's words: the text after `/uts-to-lang-skill-creator` (Claude Code) or `$uts-to-lang-skill-creator` (Codex), or their message. Don't rely on argument substitution.

## Step 0: Orient

Do this first, in every run, before any phase. It is read-only: no build, no test, no network, no file written. Run `python3 <skill-dir>/scripts/orient.py <repo> [--spec-clone <path>]` ([13.1](references/orient.md#131-run-it)), then settle its stops in this order; [references/orient.md](references/orient.md) (section 13) has the rules:

1. **STOP-16**, if the repo isn't plainly eligible ([13.2](references/orient.md#132-repository-eligibility-stop-16)). On a reject, show the script's message exactly and end the run; there is no override.
2. **STOP-1**, if needed: the model tier (2.8) and anything in `stop1`, such as the spec clone (2.6).
3. **STOP-17**, when `stop17` is set: the capability profile and scope ([13.8](references/orient.md#138-capabilities-and-scope-stop-17-d-31)). Record D-31.
4. **STOP-13**, always: the State summary and the recommended mode ([13.4](references/orient.md#134-the-state-summary-and-stop-13)). Record D-27, then route per [13.5](references/orient.md#135-routing).

## 2. Ground rules

### 2.1 Your inputs

You work from four primary sources:

1. this skill;
2. the guide;
3. the local spec clone: the UTS docs (`uts/README.md`, `uts/docs/`), the helper specs, the UTS corpus (`uts/rest`, `uts/realtime`, `uts/objects`) and, for API and spec-error questions, the features specs under `specifications/`;
4. the target SDK repo.

and, only as a last resort, the reference implementations.

**Reference implementations (last resort):** consult the existing `uts-to-swift` and `uts-to-kotlin` skills and harnesses only under [Reference implementations (last resort)](#reference-implementations-last-resort) below. Those rules govern other repos: the target repo's own `uts-to-*` skill, harness and UTS-derived tests are input 4; read them in full and change them in place ([11.1](references/upgrade-existing-skill.md#111-when-this-mode-applies)).

### 2.2 What you may change

| Action | Allowed? |
|---|---|
| Create and edit files under the skill directory, its `.agents/skills` link or copy (D-01), and the working-records directory | Yes (an existing skill's files: see below) |
| Create new test-only harness code (shared test library, module helpers, smoke tests, UTS test-project wiring) | Only after the user approves the harness design at [STOP-3](#23-stop-points), and only within the scope they approved |
| Change existing test-support code that the SDK's own tests use (shared fakes, fixtures, base classes) | Only with explicit approval for each change, and never in a way that changes behaviour for the existing tests. Prefer wrapping or extending to editing |
| Change SDK production code, including adding test hooks or raising visibility | **Only with explicit approval for each change** ([STOP-4](#23-stop-points)). Present the proposal first ([4.6](references/phase-2-design-harness.md#46-step-2f-propose-the-sdk-test-hooks)) |
| Change CI workflows, build scripts that CI runs, or dependency manifests (including adding a test dependency) | **Only with explicit approval** ([STOP-5](#23-stop-points)). Otherwise write the change as a suggestion in the Final report |
| Edit project or solution files needed to register new test files or projects (`.sln`, `.csproj`, `.projitems`, an Xcode project) | Only with explicit approval ([STOP-5](#23-stop-points)), recorded in the Design record (D-20). If the user declines, give them the exact entries to add, wait until they confirm, and list them in the Final report |
| Stage, commit, push, branch, or open a PR | **No, unless the user asks** |
| Edit anything in the spec clone | No. Report spec errors and doc gaps in the Final report with a draft fix |
| Delete or rewrite existing tests or existing UTS-derived tests | No, unless the user asks. Report their state in the Repo profile |
| Edit, replace or delete files of an existing `uts-to-*` skill or UTS harness that this run didn't create | Only for the items the user chose at STOP-15 (D-29) or the harness rows approved at STOP-3; the objects files that the STOP-14 decision (D-28) changes; when regenerating, replacements the user approves ([11.5](references/upgrade-existing-skill.md#115-step-u4-run-the-phases-scoped)); the provenance stamp in its frontmatter (D-30). Never delete without asking |
| Run the full test suite, or any integration or proxy test (network, sandbox, proxy binary download) | Ask first ([STOP-6](#23-stop-points)) |
| Fetch from the network for anything other than what the user approved (sandbox, proxy binary, dependencies, reference-implementation reads under [2.1](#21-your-inputs)) | No |

### 2.3 Stop points

At a stop point, present what you found and the options, then wait for the user's answer. Record the question and the answer in the decision log ([design-record template](assets/templates/design-record.md)). Orient's stops are recorded once the records exist; a STOP-16 reject ends the run.

| ID | Phase | When | What you present |
|---|---|---|---|
| **STOP-1** | 0 (Orient) | A required input is missing, the session's model isn't Opus-class ([2.8](#28-model-tier-and-sub-agents)), or `spec_clone_info.py` fails or reports `skillMatchesClone: false` ([2.6](#26-pin-the-spec-clone)) | The missing input (or the model found) and why it's needed |
| **STOP-2** | 1 (step 1d) | The Repo profile is written | The profile, for confirmation or correction |
| **STOP-3** | 2 (end) | The harness design is written | The gap table, the design and three options: (a) build the missing harness now, (b) plan it only, (c) scope the skill to the tiers possible today |
| **STOP-4** | 3 onwards | Before any SDK production-code change | The hook or visibility proposal ([4.6](references/phase-2-design-harness.md#46-step-2f-propose-the-sdk-test-hooks)) |
| **STOP-5** | 3 onwards | Before any CI, build-script, dependency-manifest or project/solution-file change (including creating a test project or adding one to a solution) | The diff you propose and why |
| **STOP-6** | 1 onwards | Before any network access (network tests, proxy releases, a reference implementation on GitHub or fetching its clone, [2.1](#21-your-inputs)), or running a full suite | The command, the expected duration, what it touches; for reference reads, whether the approval covers the whole run |
| **STOP-7** | 3 (end) | The harness is built | The build results (smoke tests and self-tests per tier, CI wiring, updated tier feasibility), before any skill file is written |
| **STOP-8** | 4 (end) | The Design record is written | The Design record, for confirmation |
| **STOP-9** | 5 | Pseudocode constructs, helper symbols or spec shapes you can't map ([7.4](references/phase-5-generate-skill.md#74-step-5d-fill-the-construct-catalogue)); batch everything one scan finds into one stop | Each construct, where it occurs, a proposed rendering |
| **STOP-10** | 3, 6 | A Phase 3 build row or a pilot spec hits its attempt bound ([5.2](references/phase-3-build-harness.md#52-step-3b-build-in-order-with-acceptance-checks), [8.4](references/phase-6-validate-skill.md#84-fix-the-cause-then-regenerate)), or the pilot reveals a suspected UTS spec error | A summary: the failure, what you tried, your diagnosis (per `writing-derived-tests.md` Phase 2 for a test), the options, and a draft spec fix where relevant |
| **STOP-11** | Any | A conflict between the docs, or between the guide and the SDK, that changes what you would build or generate | Both statements, with paths and headings, and the reading you propose |
| **STOP-12** | Any | The guide, the UTS docs and the reference implementations ([2.1](#21-your-inputs)) together don't answer a question, or the only answer the references give would depart from the guide | The question; the guide and UTS sections searched; the references read (repo, revision, path) and what they showed; your proposed reading |
| **STOP-13** | 0 (Orient), every run | Always ([13.4](references/orient.md#134-the-state-summary-and-stop-13)) | The State summary, the state class (S0–S4, re-entry) and the options for it, with the recommended one: Create; Upgrade/Fix (diff-driven or full gap audit); regenerate from scratch; resume or restart; for S4, pick a skill, create a new skill or repair the installs first; stop |
| **STOP-14** | 1 (step 1e), every run | Always, in every mode ([12.2](references/liveobjects-support.md#122-stop-14-recommend-then-ask)) | The `detect_liveobjects.py` evidence (names per category, with files and counts), its recommendation and yours; options: full objects support (translate-only if incomplete), placeholder, none now |
| **STOP-15** | 1 (step 1f), Upgrade/Fix | The gap audit, or the list of detected changes (diff-driven), is written ([11.4](references/upgrade-existing-skill.md#114-step-u3-stop-15-choose-per-item), [section 10](references/upgrade-diff-driven.md#10-upgradefix-diff-driven)) | Every non-conforming item or detected change, with the proposed change and the options add, skip or defer (a skipped or deferred MUST row leaves the skill not conforming); or regenerate from scratch instead |
| **STOP-16** | 0 (Orient), first stop after the spec clone resolves | `check_repo_eligibility.py` rejects the repo, or can't decide ([13.2](references/orient.md#132-repository-eligibility-stop-16)) | Reject: the script's exact message (not on the whitelist; or, for `NO_CLIENT_DEFINITION`, no client defined in this checkout); the run ends, with no override. Ask: the remotes found and the question (confirm a fork, name the GitHub repository, check the path) |
| **STOP-17** | 0 (Orient), with STOP-13 | Orient sets `stop17`: the capability profile needs confirming ([13.8](references/orient.md#138-capabilities-and-scope-stop-17-d-31) lists the triggers) | The profile (REST, Realtime and its sub-areas, with evidence), the suggested scope (modules; `unsupported` modules; capability-inapplicable tests) and any delta; options: accept, correct with evidence and rerun, stop. With doors, also the side question: the core constructors (sanctioned internal-access route), the server door, the device door, or both as a parameter; the scope follows the side |

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

Orient runs `scripts/spec_clone_info.py` with the path the user gave, if any. It locates the clone, checks that the guide, the UTS docs and the helper specs exist, and reads the clone's git state; [13.1](references/orient.md#131-run-it) gives the discovery order, the outcomes and the stop or confirmation each needs.

Record the SHA, whether the clone is clean (and, if not, which files under `uts/` or `specifications/` are modified or untracked), the guide's and this skill's last-change commit (`guideLastChange`) and `skillVersion`. Read every spec-repo file at the absolute paths the script reports (`paths`), or under `specClone`, and from this clone for the whole run. A spec you will translate that is itself modified or untracked is handled as in guide [9.1](../../docs/writing-uts-spec-translator-skills.md#91-record-what-you-translated-from-must) (stop and ask; if the user proceeds, stamp its blob hash). Compare with `origin/main` only if the user agrees to a `git fetch`; never pull or check out on their behalf. If the clone changes during the run, stop and ask whether to restart from the new SHA.

Untracked local notes in the clone (for example files matching `uts/UTS_*.md`) are not part of the corpus. Don't read them as specs.

### 2.7 Working style

- Do Step 0 (Orient) before anything else, then Phase 1; don't write harness code before the user approves the harness design (STOP-3), or skill files before the harness is verified (STOP-7).
- Escalate verification in the repo's own order (compile, then build tests, then a filtered run, then wider runs), as recorded in the Repo profile.
- Keep the working records up to date as you go, including the Design record's Run status (13.7); they are also your memory if the session is interrupted. Orient finds them and offers to resume (13.6); then read them first.
- Use the repo's own conventions (file headers, line endings, naming, test style) for every file you create.

### 2.8 Model tier and sub-agents

- **Model:** run this procedure on the most capable model tier available: Claude Opus or an equivalent Opus-class model; in another tool, such as Codex, its most capable tier, recorded by name (guide [Model tier](../../docs/writing-uts-spec-translator-skills.md#model-tier): MUST, with the reasons). If your environment states your model, record it; otherwise ask the user. If it isn't Opus-class, say so in Orient (STOP-1); if the user still wants to proceed, record it in the decision log as a departure from the guide, and state it in the Final report.
- **Sub-agents** you spawn for review, validation or the pilot ([8.3](references/phase-6-validate-skill.md#83-pilot-translate-one-spec-per-available-tier)) MUST also run on an Opus-class model. Where your tooling lets you choose a sub-agent's model, choose it explicitly rather than relying on a default. Use a cheaper model only for a clearly mechanical step whose output a script verifies (for example, the [8.2](references/phase-6-validate-skill.md#82-test-the-audit-itself) corpus sweep), if at all, and record which steps used one.
- **Record** the model (name and ID) of this session and of every sub-agent in the Design record ("Inputs at generation time") and in the Final report. **State** the generated skill's model tier in its opening lines and `compatibility`; pin it only as D-26 decides.

## Run modes

Orient recommends the mode, and the user decides at STOP-13 (D-27). The same phases, ground rules and stop points serve both modes:

| Mode | When | Read |
|---|---|---|
| **Create** | No `uts-to-*` skill yet (S0); or none, but UTS-tagged tests or harness code to adopt (S1, 2.2) | The phases below |
| **Upgrade/Fix** | A `uts-to-*` skill exists. **Diff-driven** for one this procedure built (S2): follow what changed since its recorded run. **Full gap audit** for one of unknown origin (S3), or by choice: audit the skill, its harness and its UTS-derived tests against the guide, choose per item, upgrade in place. **Regenerate from scratch** only by the user's choice ([11.5](references/upgrade-existing-skill.md#115-step-u4-run-the-phases-scoped)) | [Section 10](references/upgrade-diff-driven.md#10-upgradefix-diff-driven) (diff-driven), [section 11](references/upgrade-existing-skill.md#11-upgradefix-full-gap-audit) |

An interrupted run is resumed or restarted from its records (13.6). In every mode, Phase 1 also asks whether to add LiveObjects (`objects`) support (STOP-14), recommending an answer from `detect_liveobjects.py`'s evidence ([section 12](references/liveobjects-support.md#12-liveobjects-objects-support)).

## Phases at a glance

Before starting a phase, read its reference file in full: this table is a map, not enough to act on. In Upgrade/Fix, full gap audit, read [11.5](references/upgrade-existing-skill.md#115-step-u4-run-the-phases-scoped)'s row for each phase first (diff-driven: section 10): the phases are scoped to the chosen items, and acceptance items tied to a skipped or deferred gap-audit row are reported ✗ under D-29, not worked. When regenerating from scratch, read 11.5's last paragraph instead. On resuming an interrupted run, read the working records first, then the reference of the phase you are in.

| Phase | Goal | Read first | Writes | Ends at |
|---|---|---|---|---|
| 0. Orient | Eligibility, capabilities and scope, state class, mode | [Step 0](#step-0-orient); [orient.md](references/orient.md) | nothing | STOP-16 (if not eligible), STOP-1 (if needed), STOP-17 (if needed), STOP-13 |
| 1. Understand the repo | A confirmed Repo profile: how the SDK is built, tested and mocked today; the LiveObjects decision; in Upgrade/Fix, the gap audit or the change list | [phase-1](references/phase-1-understand-repo.md) (and sections 10, 11, 12) | `repo-profile.md`; in Upgrade/Fix `skill-gap-audit.md` | STOP-2, STOP-14 (STOP-15 in Upgrade/Fix) |
| 2. Design the harness | Reuse, wrap, extend or build each capability; hooks; placement; tier feasibility | [phase-2](references/phase-2-design-harness.md) | `uts-infra-design.md` | STOP-3 |
| 3. Build and verify the harness | The approved harness, with green per-tier smoke tests and self-tests, wired into CI | [phase-3](references/phase-3-build-harness.md) | harness code and README; build log | STOP-7 |
| 4. Skill design decisions | D-01 to D-26 decided; D-27 to D-31 confirmed | [phase-4](references/phase-4-design-record.md) | `design-record.md` | STOP-8 |
| 5. Generate the skill files | Mapping, resolver, audit, construct catalogue, module notes, `SKILL.md` | [phase-5](references/phase-5-generate-skill.md) | the `uts-to-<lang>` skill | (STOP-9 if constructs are unmapped) |
| 6. Validate the skill | Resolver, audit mutations, pilots, other paths, lint, examples | [phase-6](references/phase-6-validate-skill.md) | pilot tests; results | (STOP-10 at a bound) |
| 7. Final report and handover | Report and acceptance checklist | [section 9](#9-phase-7-final-report-and-handover) | `final-report.md` with the acceptance checklist | — |

## 1. Purpose and how to use this procedure

### 1.1 Who reads this

- **The executor** is an LLM agent working inside the target SDK repository, with shell and file access and the ability to ask the user questions. Every instruction is addressed to it ("you").
- **The user** is an SDK engineer who owns the target repository. They answer at the stop points and approve every change outside the skill directory.
- **A reviewer** may read the working records (Repo profile, Harness design, Design record, Final report) instead of the whole conversation, or this skill to see what the agent will do and where it will ask.

### 1.2 Invocation

The user starts a run in the target SDK repo with one sentence, for example:

```
/uts-to-lang-skill-creator ~/src/specification realtime unit first     (Claude Code; $uts-to-lang-skill-creator in Codex)
Audit our uts-to-python skill against the guide and upgrade it; add LiveObjects support.
Read <spec-clone>/uts/skills/uts-to-lang-skill-creator/SKILL.md and follow it to create a uts-to-<lang> skill for this repo.   (skill not installed)
```

`<spec-clone>` is the user's local clone of `ably/specification`. Take it, and any goals ("objects unit tier first", "rest and realtime only"), from the user's words, and record the goals as inputs. Installation is described in [`uts/README.md`](../../README.md#installing-the-skill-creator).

### 1.3 Required inputs

| Input | Example | If missing |
|---|---|---|
| Target SDK repo path | the current working directory | Ask. Don't assume the working directory is the SDK repo: Orient checks that it is an eligible Ably Pub/Sub SDK repository with SDK sources and tests (STOP-16) |
| Language (and the skill name it implies) | C# → `uts-to-csharp`; Python → `uts-to-python` | Infer from the repo in Phase 1, then confirm |
| Local spec clone path | `~/src/specification` (the directory that contains `uts/` and `specifications/`) | Located by `scripts/spec_clone_info.py` ([2.6](#26-pin-the-spec-clone)) and confirmed with the user; otherwise stop and ask ([STOP-1](#23-stop-points)). Never fetch the spec or the UTS docs from GitHub instead |
| User goals: modules and tiers wanted first | "realtime unit, then rest unit; objects later" | Ask. Default to every module (`rest`, `realtime`, `objects`) and every tier the SDK can support, prioritised by the user |
| Model tier | The session's model | See [2.8](#28-model-tier-and-sub-agents) (STOP-1 if it isn't Opus-class) |
| Local clones of ably-cocoa and ably-java (now `ably-pubsub-java`) (optional) | Clones of either repo, read at their current HEAD (ideally a recent `main`) | Not needed to start. Ask only if you reach the last-resort reference reads ([2.1](#21-your-inputs)); without clones, those reads go to GitHub after STOP-6 |

### 1.4 Outputs

1. **The harness** for this language, in the target repo: the shared test library implementing the helper specs, wait and assertion helpers, sandbox and proxy helpers, module helpers, the per-tier smoke tests and helper self-tests (guide [2.7](../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must); permanent and run in CI), a harness README with its Known gaps and, with explicit approval, SDK test hooks. Built in Phase 3, unless the user scopes it down at STOP-3.
2. **The skill** (in Upgrade/Fix, the existing skill, upgraded in place), at `.claude/skills/uts-to-<lang>/`, linked from `.agents/skills/uts-to-<lang>/` for Codex, unless D-01 says otherwise: `SKILL.md`, `uts-package-mapping.json`, `scripts/resolve_uts.py`, `scripts/audit_translation.py`, `references/<module>-mapping.md` and, if D-19 ships it, `scripts/scan_constructs.py` (guide [3.1](../../docs/writing-uts-spec-translator-skills.md#31-layout)).
3. **Pilot-translated tests**, one spec per available tier (in Upgrade/Fix, per tier whose rules changed, 11.6), produced by the new skill in Phase 6.
4. **Working records** (*procedure recommendation*): Markdown files in the working-records directory (default `.claude/skills/uts-to-<lang>/generation/`; D-24, confirmed in Phase 4). Copy each template from `assets/templates/` there under the same file name, then fill it in:
    - [repo-profile](assets/templates/repo-profile.md) and [design-record](assets/templates/design-record.md) (which holds the decision log), at the start of Phase 1;
    - [uts-infra-design](assets/templates/uts-infra-design.md) (the gap table, the harness design and the build log), at the start of Phase 2;
    - [final-report](assets/templates/final-report.md), in Phase 7, with the [acceptance checklist](assets/templates/acceptance-checklist.md) filled into its "Acceptance checklist" section;
    - in Upgrade/Fix, [skill-gap-audit](assets/templates/skill-gap-audit.md), at U1 (diff-driven: before STOP-15, for section H).

The templates contain no links, so they stay valid in the SDK repo. Write the records from STOP-13 on, at the location Orient's routing gives (13.5), using the language inferred so far for `<lang>`; if STOP-2 changes the language or D-24 chooses another location, move the files then. They are working notes, not skill files, so writing them before STOP-7 is allowed. A later agent reads them to maintain or regenerate the skill ([section 10](references/upgrade-diff-driven.md#10-upgradefix-diff-driven)), so keep them accurate as you go, not only at the end.

### 1.5 Intent

The guide's intent ([introduction](../../docs/writing-uts-spec-translator-skills.md)) applies to this procedure too: if the skill you generate produces a wrong test, fix the skill, its notes or the harness and regenerate. Never hand-fix a pilot test and call the skill done.

### 1.6 Which document wins

| Question | Authority |
|---|---|
| What a faithful translation is; how a failure is diagnosed; the `deviations.md` format | [`writing-derived-tests.md`](../../docs/writing-derived-tests.md) |
| What pseudocode means | [`uts/README.md`](../../README.md) and [`writing-test-specs.md`](../../docs/writing-test-specs.md) |
| Integration and proxy tiers | [`integration-testing.md`](../../docs/integration-testing.md), [`proxy.md`](../../docs/proxy.md) |
| Mock and fixture behaviour | the helper specs: [`mock_http.md`](../../rest/unit/helpers/mock_http.md), [`mock_websocket.md`](../../realtime/unit/helpers/mock_websocket.md), [`mock_vcdiff.md`](../../realtime/unit/helpers/mock_vcdiff.md), [`standard_test_pool.md`](../../objects/helpers/standard_test_pool.md) |
| What the harness and the skill must contain, and why | the guide ([How it relates to the other UTS docs](../../docs/writing-uts-spec-translator-skills.md#how-it-relates-to-the-other-uts-docs)) |
| How and in what order you build them | this skill |
| The SDK's actual API | the SDK source (guide [3.1](../../docs/writing-uts-spec-translator-skills.md#31-layout), "The notes are a map, not an authority") |
| Questions none of the above answer, as a last resort only | The reference implementations, under [Reference implementations (last resort)](#reference-implementations-last-resort): never an authority |

If two documents disagree, follow the higher one in the table (and STOP-11 if the conflict changes what you would build or generate), record the conflict in the Design record, and list it in the Final report under "Spec-repo doc issues". Don't patch the spec repo. A disagreement between a reference implementation and the guide or the UTS docs is never a STOP-11: follow the guide, and record the disagreement with the read ([2.1](#21-your-inputs)).

**Procedure recommendations.** Where this skill adds detail the guide doesn't have (for example: the working-records files and their location, tier-readiness data in the mapping, a mandatory `specRepo`, and requiring the audit's end-at-heading rule), it is marked *procedure recommendation*: this skill's way of meeting the guide, not a guide requirement. Follow it unless the user decides otherwise, and record any departure in the decision log. Everything else either links to the guide or is procedure (order, checks, stop points).

## 9. Phase 7: final report and handover

1. Write `final-report.md` from the [final-report template](assets/templates/final-report.md). Set the Design record's Run status to finished, and refresh the skill's provenance stamp (D-30, 13.7).
2. Fill the [acceptance checklist](assets/templates/acceptance-checklist.md): it maps each item of the guide's [section 13 checklist](../../docs/writing-uts-spec-translator-skills.md#13-checklist-for-a-new-uts-to-lang-skill) to where this procedure produces and verifies it. Mark each item ✓, n/a with the reason ([13.8](references/orient.md#138-capabilities-and-scope-stop-17-d-31)), or ✗ with why it isn't met (scoped out, planned, skipped or deferred at STOP-15).
3. Show the user the report, the list of changed and new files (harness, harness tests, hooks, skill, pilot tests), and the suggested CI changes. The run is complete only if the harness tests are green, and in CI, at every tier the skill supports; otherwise the report says which tiers aren't and why. **Don't commit** unless asked.
4. If the user asks for a commit, follow the repo's commit conventions (P-08) and, if the user agrees, keep the SDK hooks, the harness, the skill and the pilot tests in separate commits. In Upgrade/Fix, offer one commit per closed gap-audit or change item (from the Design record's changelog), harness rows first.

## Reference implementations (last resort)

This section expands the last resort of [2.1](#21-your-inputs). The guide covers what the existing `uts-to-swift` and `uts-to-kotlin` skills and harnesses teach, so you shouldn't need them. You MAY consult them, read-only, under the guide's [Reference implementations (last resort)](../../docs/writing-uts-spec-translator-skills.md#reference-implementations-last-resort) rules 1 to 5 (the guide wins, learn the pattern and never copy, check against Patterns to avoid, record each consultation, creation only); that section also lists the repos and paths. This skill adds:

- **When:** only after this skill, the guide, the UTS docs and the helper specs fail to answer the question. The guide and the UTS docs always win ([1.6](#16-which-document-wins)).
- **Access:** read local clones the user named ([1.3](#13-required-inputs)) at their current HEAD (read the files, or `git -C <clone> show HEAD:<path>`); never check out, modify, pull or fetch them on the user's behalf (fetching or pulling is network access). Otherwise read GitHub after STOP-6; the user may approve reference reads once for the whole run, and you record that approval.
- **Recording:** record each read in the Design record ("Reference-implementation reads": repo, revision, path, question, what you learned, how you checked it), and list it in the Final report as a guide gap.

These rules govern other repos. The target repo's own `uts-to-*` skill, harness and UTS-derived tests are input 4, even in ably-cocoa or ably-java: read them in full and change them in place ([11.1](references/upgrade-existing-skill.md#111-when-this-mode-applies)). A read-only consultation needs no stop point of its own. Where the guide names another SDK's file, script, helper or test (as the origin of a lesson, or in the Swift and Kotlin cells of its construct tables), it is background, not a template. If the references don't resolve the question either, or their only answer departs from the guide, STOP-12. The generated skill never consults them (D-22), and neither does the pilot ([8.3](references/phase-6-validate-skill.md#83-pilot-translate-one-spec-per-available-tier)).

## Reference index

Each phase's reference (sections 3 to 8) is linked from [Phases at a glance](#phases-at-a-glance), and each template from [1.4](#14-outputs). Also read:

| File | Read it when | Sections |
|---|---|---|
| [orient.md](references/orient.md) | Step 0, every run | 13 |
| [upgrade-diff-driven.md](references/upgrade-diff-driven.md) | Upgrade/Fix, diff-driven (S2) | 10 |
| [upgrade-existing-skill.md](references/upgrade-existing-skill.md) | Upgrade/Fix, full gap audit, or regenerating from scratch | 11 |
| [liveobjects-support.md](references/liveobjects-support.md) | Phase 1 step 1e (every run); writing the objects notes | 12 |
| [phase-4-design-record.md](references/phase-4-design-record.md) | Mapping a guide change to decisions (Upgrade/Fix, diff-driven) | 6 |
| [phase-5-generate-skill.md](references/phase-5-generate-skill.md) | Listing the corpus harness symbols in Phase 2 (7.4) | 7 |
| [glossary.md](references/glossary.md) | A term is unclear | — |
| [failure-modes.md](references/failure-modes.md) | A harness check, a pilot test or a command fails in a way you don't recognise | — |

## Scripts

All are read-only Python 3, with no network access; they print to stdout and run from anywhere as `python3 <skill-dir>/scripts/<name>.py`. `--help` prints a script's docstring (purpose, usage, output and exit codes) and exits 0; a usage error prints the usage to stderr and exits 2. Each row's linked section has the rules.

| Script | Use |
|---|---|
| `orient.py <repo> [--spec-clone P] [--skill-dir P] [--records P] [--include-submodules] [--full]` | Step 0: runs `spec_clone_info.py`, the eligibility check, the inspector and both detectors, classifies the repo, recommends a mode ([13.1](references/orient.md#131-run-it)) |
| `spec_clone_info.py [SPEC_CLONE \| --spec-clone P]` | Locate, validate and pin the spec clone; `warnings` is a list, possibly empty ([13.1](references/orient.md#131-run-it)) |
| `check_repo_eligibility.py <repo> [--spec-clone P]` | Is the repository on the whitelist? ([13.2](references/orient.md#132-repository-eligibility-stop-16)) |
| `detect_capabilities.py <repo> [--spec-clone P] [--include-submodules] [--capability-override rest=full,realtime=absent]` | Capability profile, door sides, suggested scope ([13.8](references/orient.md#138-capabilities-and-scope-stop-17-d-31)) |
| `spec_names.py [--spec-clone P]` | The detectors' names, from the spec clone's IDL, and the capability-inapplicable tests ([13.8](references/orient.md#138-capabilities-and-scope-stop-17-d-31)) |
| `survey_repo.py <repo> [<test-root> …]` | First pass for the discovery checklist ([3.2](references/phase-1-understand-repo.md#32-step-1b-answer-the-discovery-checklist)) |
| `scan_constructs.py <spec-clone>/uts/<module>` | The corpus's constructs and harness calls ([7.4](references/phase-5-generate-skill.md#74-step-5d-fill-the-construct-catalogue)); copied into the generated skill (D-19) |
| `inspect_existing_skill.py <repo> [<skill-dir>] [--records <dir>]` | Inventory of an existing `uts-to-*` skill, its installs, harness, UTS-derived tests and records; regex hints, not a review ([11.2](references/upgrade-existing-skill.md#112-step-u1-understand-the-existing-skill)) |
| `detect_liveobjects.py <repo> [--spec-clone P] [--include-submodules]` | Evidence for the LiveObjects decision at STOP-14 ([12.1](references/liveobjects-support.md#121-gather-the-evidence-step-1b-p-15)) |
| `check_layout.py [SKILL_MD]` | For maintainers, not a run: do the stop table and the ground rules still end within the compaction window? ([Maintaining this skill](#maintaining-this-skill)) |

### Maintaining this skill

What the scripts know about Ably's repositories and SDK names that the spec can't give is data: update the data file, not the code.

- [`assets/eligibility.json`](assets/eligibility.json) is the whitelist: adding a new SDK repository means adding its name to `repositories`. Update it too when Ably renames or retires a repository (the canonical and planned names), and for the capability overrides and the definition gate's threshold.
- [`assets/capability-names.json`](assets/capability-names.json): update it when an SDK adds a client alias or a door factory, or the spec renames a LiveObjects name its IDL no longer shows.

Each file starts with one `_description` (what the file is and when to update it); add a `_comment` key only where an entry would otherwise puzzle a maintainer. The scripts ignore `_` keys, check the shape, and report a malformed file as `DATA_FILE_ERROR`, naming the file and the key. Client, channel, connection, presence and LiveObjects names come from the spec clone at run time (13.8) and need no edit. After an edit, rerun Orient on a repository the change affects.

After a context compaction, Claude Code keeps only the start of this `SKILL.md`: about 5,000 tokens, which it counts as about 20,000 characters of the text after the frontmatter, including a line with the install path. Codex may keep none of it. So Step 0, the stop table and the ground rules (section 2) come first, and everything else follows section 2. After editing anything before the end of section 2, run `python3 <skill-dir>/scripts/check_layout.py`: it measures, in characters after the frontmatter, where the stop table and section 2 end, and fails above 16,000 and 18,500. Move material out of the way rather than raising the limits.
