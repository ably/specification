---
name: uts-to-lang-skill-creator
description: "Builds or upgrades a uts-to-LANG translator skill, with the UTS test harness it runs on, for one Ably Pub/Sub SDK repository (ably-LANG or ably-pubsub-LANG: C#, Python, Go, JavaScript, Ruby, ...). Use it whenever asked to create a uts-to-csharp, uts-to-python or other uts-to-* skill; to audit, fix, upgrade or refresh one after the guide, UTS docs, corpus or SDK changed; to add LiveObjects (uts/objects) support; or to set up UTS test infrastructure (SDK test hooks, MockHttpClient, MockWebSocket, fake clock, sandbox and proxy helpers, harness smoke tests and self-tests). First checks the repo is an Ably Pub/Sub SDK, then detects what it has (uts-to-* skills and their origin, harness, UTS-tagged tests, LiveObjects API) and recommends Create or Upgrade/Fix, then runs a procedure with user stop points. Needs a local ably/specification clone. Not for Chat, Spaces, AI Transport, CLI or other non-Pub/Sub repos, for translating specs once a uts-to-* skill exists (use that skill), or for writing UTS specs."
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

Run this skill on an Opus-class model ([2.8](#28-model-tier-and-sub-agents)). It is a step-by-step procedure for an LLM agent to create or upgrade a `uts-to-<lang>` translator skill, and the UTS test infrastructure (the **harness**) it runs on, for one Ably Pub/Sub SDK repository. It always starts with [Step 0: orient](#step-0-orient). [Writing UTS Spec Translator Skills](../../docs/writing-uts-spec-translator-skills.md) (below, **the guide**) says **what** a good translator skill is and why; this skill says **how** to build one, in what order, with what checks, and where to stop and ask the user. It doesn't repeat the guide: wherever the reason or the detailed requirement lives in the guide, this skill links to it, and you must read the linked section.

The harness and the skill are **one deliverable** (guide [section 2](../../docs/writing-uts-spec-translator-skills.md#2-the-harness-uts-test-infrastructure)): the skill isn't complete until the harness's per-tier smoke tests and helper self-tests (guide [2.7](../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)) are green, and wired into CI, at every tier the skill supports. The harness is designed from the repo's existing test setup: every capability is reused, wrapped, extended or built ([4.2](references/phase-2-design-harness.md#42-step-2b-assess-each-capability-reuse-wrap-extend-or-build)). The phases run in a fixed order, because each stands on the one before it; a harness designed without studying the repo's existing tests duplicates or fights them.

"This skill" means this `SKILL.md` together with its `references/` and `assets/templates/`. The ground rules (section 2) and the inputs and outputs (section 1) are below; each phase's steps are in `references/`, and you read each one in full before its phase starts ([Phases at a glance](#phases-at-a-glance)). Section numbers (for example "4.6") are stable across the files ([Reference index](#reference-index)).

## Path convention

- **Files of this skill** (`references/`, `assets/templates/`, `scripts/`) are relative to the directory that contains this `SKILL.md`, wherever it is installed. Run scripts as `python3 <skill-dir>/scripts/<name>.py`, where `<skill-dir>` is the directory containing this `SKILL.md`.
- **Files of the spec repo** (the guide, the UTS docs, the helper specs, the corpus) are linked relative to this skill's place in a spec clone, `uts/skills/uts-to-lang-skill-creator/`, so the links work on GitHub. A link that climbs out of the skill directory (`../../…` from `SKILL.md`, `../../../…` from `references/`) is a spec-repo path; every other link is a file of this skill. At run time, never resolve a spec-repo path against the directory you loaded this skill from. Run `scripts/spec_clone_info.py` ([2.6](#26-pin-the-spec-clone)) and read each file at `<spec-clone>/uts/…`: a link to `…/docs/writing-uts-spec-translator-skills.md#31-layout` means `<spec-clone>/uts/docs/writing-uts-spec-translator-skills.md`, section 3.1. Never fetch them from GitHub.
- **Inputs** come from the user's words: the text after `/uts-to-lang-skill-creator` (Claude Code) or `$uts-to-lang-skill-creator` (Codex), or their message. Don't rely on argument substitution.

## Step 0: orient

Do this first, in every run, before any phase. It is read-only and quick: no build, no test, no network, no file written. [references/orient.md](references/orient.md) (section 13) has the detail.

1. Run `python3 <skill-dir>/scripts/orient.py <repo> [--spec-clone <path>]`. It runs `spec_clone_info.py` (which resolves the spec clone the others read), `check_repo_eligibility.py`, `inspect_existing_skill.py`, `detect_liveobjects.py` and `detect_capabilities.py`, then classifies the repo.
2. **Eligibility (STOP-16).** This procedure supports only the Ably Pub/Sub SDK repositories on the whitelist in `assets/eligibility.json` (current and legacy names), checked across all remotes; every other repository is rejected, and adding a new SDK repository means adding it there ([13.2](references/orient.md#132-repository-eligibility-stop-16)).
    - On a reject, show the script's message exactly and end the run. There is no override.
    - On an ask (a fork, no remote, too few source files to judge), ask the question first.
3. **STOP-1:** settle the model tier (2.8) and anything the spec clone needs (2.6).
4. **STOP-17** if the capability profile needs confirming (REST-only, realtime-only, partial or unclear realtime, doors with sides, wraps native SDKs, a capability override, names from the fallback, or changed since the recorded run): the harness and skill scope follow the SDK's REST and Realtime clients, not its name, and for an SDK with doors, the side the UTS tests use ([13.8](references/orient.md#138-capabilities-and-scope-stop-17-d-31)); record D-31.
5. **STOP-13, always.** Show the State summary: eligibility, capabilities and scope; the skills found, with origin and installs; inspector hints; harness; UTS-tagged tests; LiveObjects verdict; state class S0–S4, with re-entry if any. Recommend Create (S0, S1) or Upgrade/Fix (S2, S3), or ask which skill (S4), with a one-line reason ([13.3](references/orient.md#133-state-classes), [13.4](references/orient.md#134-the-state-summary-and-stop-13)). Record the answer as D-27.
6. Route per [13.5](references/orient.md#135-routing). After Orient (start of Phase 1), copy the design-record and repo-profile templates to the working-records directory, and copy the State summary into the Repo profile.

## 2. Ground rules

### 2.1 Your inputs

You work from four primary sources:

1. this skill;
2. the guide;
3. the local spec clone: the UTS docs (`uts/README.md`, `uts/docs/`), the helper specs, the UTS corpus (`uts/rest`, `uts/realtime`, `uts/objects`) and, for API and spec-error questions, the features specs under `specifications/`;
4. the target SDK repo.

and, only as a last resort, the reference implementations below.

**Reference implementations (last resort).** The guide covers what the two existing skills and harnesses teach, so you shouldn't need them. You MAY consult them, read-only. The guide's [Reference implementations (last resort)](../../docs/writing-uts-spec-translator-skills.md#reference-implementations-last-resort) lists the repos, paths and links. Consult them only when all of the following hold:

1. You have searched this skill, the guide, the UTS docs and the helper specs, and they don't answer the question.
2. You can read them without unapproved network access. Either read them from local clones the user named (input in [1.3](#13-required-inputs)) at their current HEAD (read the files, or use `git -C <clone> show HEAD:<path>`), never checking out, modifying, pulling or fetching on the user's behalf. Or read them from GitHub after **STOP-6**; the user may approve reference reads once for the whole run, and you record that approval. Fetching or pulling a clone is network access too.
3. You take a **pattern**, not text: how something was structured or solved. Never copy, port or translate code, scripts, prose, tables or examples verbatim. Write every hook, helper, script, rule and example yourself, in this language's idioms, from the guide, the UTS docs and the target repo.
4. You check what you took against the guide's [Patterns to avoid](../../docs/writing-uts-spec-translator-skills.md#patterns-to-avoid), and against the guide and the UTS docs, which always win ([1.6](#16-which-document-wins)). Patterns to avoid describes the existing skills when the guide was written; some may since have been fixed, so check what you take either way, and record the revision you read.
5. You record each consultation in the Design record ("Reference-implementation reads": repo, revision, path, question, what you learned, how you checked it), and list it in the Final report as a guide gap: a candidate guide improvement.

These rules govern other repos. The target repo's own `uts-to-*` skill, harness and UTS-derived tests are part of input 4, even when the target is ably-cocoa or ably-java: you read them in full and change them in place ([11.1](references/upgrade-existing-skill.md#111-when-this-mode-applies)). A read-only consultation needs no stop point of its own. Where the guide names another SDK's file, script, helper or test (as the origin of a lesson, or in the Swift and Kotlin cells of its construct tables), it is background, not a template. If the references don't resolve the question either, or the only answer they give departs from the guide, **STOP-12**. The generated skill never consults them (D-22), and the pilot never does either ([8.3](references/phase-6-validate-skill.md#83-pilot-translate-one-spec-per-available-tier)).

### 2.2 What you may change

| Action | Allowed? |
|---|---|
| Create and edit files under the skill directory, its `.agents/skills` link or copy (D-01), and the working-records directory | Yes (for an existing skill's files, see the row on existing skills below) |
| Create new test-only harness code (shared test library, module helpers, smoke tests, UTS test-project wiring) | Only after the user approves the harness design at [STOP-3](#23-stop-points), and only within the scope they approved |
| Change existing test-support code that the SDK's own tests use (shared fakes, fixtures, base classes) | Only with explicit approval for each change, and never in a way that changes behaviour for the existing tests. Prefer wrapping or extending to editing |
| Change SDK production code, including adding test hooks or raising visibility | **Only with explicit approval for each change** ([STOP-4](#23-stop-points)). Present the proposal first ([4.6](references/phase-2-design-harness.md#46-step-2f-propose-the-sdk-test-hooks)) |
| Change CI workflows, build scripts that CI runs, or dependency manifests (including adding a test dependency) | **Only with explicit approval** ([STOP-5](#23-stop-points)). Otherwise write the change as a suggestion in the Final report |
| Edit project or solution files needed to register new test files or projects (`.sln`, `.csproj`, `.projitems`, an Xcode project, etc.) | Only with explicit approval ([STOP-5](#23-stop-points)), recorded in the Design record (D-20). If the user declines, give them the exact entries to add, wait until they confirm, and list them in the Final report |
| Stage, commit, push, branch, or open a PR | **No, unless the user asks** |
| Edit anything in the spec clone | No. Report spec errors and doc gaps in the Final report with a draft fix |
| Delete or rewrite existing tests or existing UTS-derived tests | No, unless the user asks. Report their state in the Repo profile |
| Edit, replace or delete files of an existing `uts-to-*` skill or UTS harness that this run didn't create | Only for the items the user chose at STOP-15 (D-29) or the harness rows approved at STOP-3; the objects files that the STOP-14 decision (D-28) changes; when regenerating, replacements the user approves ([11.5](references/upgrade-existing-skill.md#115-step-u4-run-the-phases-scoped)); the provenance stamp in its frontmatter (D-30). Never delete without asking |
| Run the full test suite, or any integration or proxy test (network, sandbox, proxy binary download) | Ask first ([STOP-6](#23-stop-points)) |
| Fetch from the network for anything other than what the user approved (sandbox, proxy binary, dependencies, reference-implementation reads under [2.1](#21-your-inputs)) | No |

### 2.3 Stop points

At a stop point, present what you found and the options, then wait for the user's answer. Record the question and the answer in the decision log ([design-record template](assets/templates/design-record.md)).

| ID | Phase | When | What you present |
|---|---|---|---|
| **STOP-1** | 0 (Orient) | A required input is missing, the session's model isn't Opus-class ([1.3](#13-required-inputs), [2.8](#28-model-tier-and-sub-agents)), or `spec_clone_info.py` fails or reports `skillMatchesClone: false` ([2.6](#26-pin-the-spec-clone)) | The missing input (or the model found) and why it's needed |
| **STOP-2** | 1 (step 1d) | The Repo profile is written | The profile, for confirmation or correction |
| **STOP-3** | 2 (end) | The harness design is written | The gap table, the design and three options: (a) build the missing harness now, (b) plan it only, (c) scope the skill to the tiers possible today |
| **STOP-4** | 3 onwards | Before any SDK production-code change | The hook or visibility proposal ([4.6](references/phase-2-design-harness.md#46-step-2f-propose-the-sdk-test-hooks)) |
| **STOP-5** | 3 onwards | Before any CI, build-script, dependency-manifest or project/solution-file change (including creating a test project or adding one to a solution) | The diff you propose and why |
| **STOP-6** | 1 onwards | Before any network access (running network tests, reading or downloading proxy releases, reading a reference implementation on GitHub or fetching its clone, [2.1](#21-your-inputs)), or running a full suite | The command, the expected duration, what it touches; for reference reads, whether the approval covers the whole run |
| **STOP-7** | 3 (end) | The harness is built | The build results (smoke tests and self-tests per tier, CI wiring, updated tier feasibility), before any skill file is written |
| **STOP-8** | 4 (end) | The Design record is written | The Design record, for confirmation |
| **STOP-9** | 5 | Pseudocode constructs, helper symbols or spec shapes you can't map ([7.4](references/phase-5-generate-skill.md#74-step-5d-fill-the-construct-catalogue)); batch everything one scan finds into one stop | Each construct, where it occurs, a proposed rendering |
| **STOP-10** | 3, 6 | A Phase 3 build row or a pilot spec hits its attempt bound ([5.2](references/phase-3-build-harness.md#52-step-3b-build-in-order-with-acceptance-checks), [8.4](references/phase-6-validate-skill.md#84-fix-the-cause-then-regenerate)), or the pilot reveals a suspected UTS spec error | A summary: the failure, what you tried, your diagnosis (per `writing-derived-tests.md` Phase 2 for a test), the options, and a draft spec fix where relevant |
| **STOP-11** | Any | A conflict between the docs, or between the guide and the SDK, that changes what you would build or generate | Both statements, with paths and headings, and the reading you propose |
| **STOP-12** | Any | The guide, the UTS docs and the reference implementations ([2.1](#21-your-inputs)) together don't answer a question, or the only answer the references give would depart from the guide | The question; the guide and UTS sections you searched; the references you read (repo, revision, path) and what they showed; the reading you propose |
| **STOP-13** | 0 (Orient), every run | Always ([13.4](references/orient.md#134-the-state-summary-and-stop-13)) | The State summary, the state class (S0–S4, re-entry) and the options for it, with the recommended one: Create; Upgrade/Fix (diff-driven or full gap audit); regenerate from scratch; resume or restart; pick a skill (S4); stop |
| **STOP-14** | 1 (step 1e), every run | Always, in every mode ([12.2](references/liveobjects-support.md#122-stop-14-recommend-then-ask)) | The `detect_liveobjects.py` evidence (public-API, legacy, internal and wire-only names, with files and counts), its recommendation and yours, and the options: full objects support (translate-only if incomplete), placeholder, none now |
| **STOP-15** | 1 (step 1f), Upgrade/Fix | The gap audit, or the list of detected changes (diff-driven), is written ([11.4](references/upgrade-existing-skill.md#114-step-u3-stop-15-choose-per-item), [section 10](references/upgrade-diff-driven.md#10-upgradefix-diff-driven)) | Every non-conforming item or detected change, with the proposed change and the options add, skip or defer (a skipped or deferred MUST row leaves the skill not conforming); or regenerate from scratch instead |
| **STOP-16** | 0 (Orient), first check | `check_repo_eligibility.py` rejects the repo, or can't decide ([13.2](references/orient.md#132-repository-eligibility-stop-16)) | Reject: the exact message that this procedure supports only Ably Pub/Sub SDK repositories and needs upgrading for this one; the run ends, with no override. Ask: the remotes found and the question (confirm a fork, name the GitHub repository, check the path) |
| **STOP-17** | 0 (Orient), with STOP-13 | The capability profile isn't full, is unclear, has door sides, wraps native SDKs, comes from a capability override, uses fallback names, or changed since the recorded run ([13.8](references/orient.md#138-capabilities-and-scope-stop-17-d-31)) | The profile (REST, Realtime and its sub-areas, with evidence), the suggested scope (modules in scope; `unsupported` modules; capability-inapplicable tests), the delta if any; options: accept, correct with evidence and rerun, stop. With doors, also the side question: construct clients through the core constructors (sanctioned internal-access route), the server door, the device door, or both as a parameter; the scope follows the side |

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

In Orient (Step 0, which runs it for you), run `python3 <skill-dir>/scripts/spec_clone_info.py [<spec-clone>]`, passing the path the user gave, if any. It locates the clone (the path given; else `UTS_SPEC_CLONE`; else the clone this skill is symlinked from; a path inside a clone is walked up to its root), checks that the guide, the UTS docs and the helper specs exist, and runs `git rev-parse HEAD`, `git status --porcelain -- uts specifications` and `git log -1 --format='%H %cd' -- uts/docs/writing-uts-spec-translator-skills.md uts/skills/uts-to-lang-skill-creator`. It prints one JSON object.

- Any `ok: false` (for example `SPEC_CLONE_NOT_FOUND`, `NOT_A_SPEC_CLONE`, `GIT_ERROR`): **STOP-1**; ask for the clone's path.
- `foundBy` other than `argument`: tell the user which clone was found and how, and confirm it before Phase 1.
- `skillMatchesClone: false` (an installed copy that differs from this clone's copy of the skill): **STOP-1**; ask the user to refresh the install, or to confirm which version to follow.
- `skillMatchesClone: null` (the clone has no copy of this skill, for example an older checkout): tell the user and confirm before Phase 1.

Record the SHA, whether the clone is clean (and, if not, which files under `uts/` or `specifications/` are modified or untracked), the guide's and this skill's last-change commit (`guideLastChange`) and `skillVersion`. Read every spec-repo file at the absolute paths the script reports (`paths`), or under `specClone`. A spec you will translate that is itself modified or untracked is handled as in guide [9.1](../../docs/writing-uts-spec-translator-skills.md#91-record-what-you-translated-from-must) (stop and ask; if the user proceeds, stamp its blob hash). You MAY compare with `origin/main` if the user agrees to a `git fetch`; never pull or check out on their behalf. Read every doc and spec from this clone for the whole run. If the clone changes during the run, stop and ask whether to restart from the new SHA.

Untracked local notes in the clone (for example files matching `uts/UTS_*.md`) are not part of the corpus. Don't read them as specs.

### 2.7 Working style

- Do Step 0 (Orient) before anything else, then Phase 1; don't write harness code before the user approves the harness design (STOP-3), or skill files before the harness is verified (STOP-7).
- Escalate verification in the repo's own order (compile, then build tests, then a filtered run, then wider runs), as recorded in the Repo profile.
- Keep the working records up to date as you go, including the design record's Run status (13.7); they are also your memory if the session is interrupted. Orient finds them and offers to resume (13.6); then read them first.
- Use the repo's own conventions (file headers, line endings, naming, test style) for every file you create.

### 2.8 Model tier and sub-agents

- **Run this procedure on the most capable model tier available (Claude Opus or an equivalent Opus-class model; in another tool, such as Codex, its most capable tier, recorded by name): MUST.** The guide's [Model tier](../../docs/writing-uts-spec-translator-skills.md#model-tier) gives the reasons: long context, multi-file reasoning, fidelity, and few silent omissions in rules that every later run inherits. If your environment states your model, record it; otherwise ask the user. If you aren't on an Opus-class model, say so in Orient (**STOP-1**). If the user still wants to proceed, record it in the decision log as a departure from the guide, and state it in the Final report.
- **Sub-agents** you spawn for review, validation or the pilot ([8.3](references/phase-6-validate-skill.md#83-pilot-translate-one-spec-per-available-tier)) MUST also run on an Opus-class model. Where your tooling lets you choose a sub-agent's model, choose it explicitly rather than relying on a default. Use a cheaper model only for a clearly mechanical step whose output a script verifies (for example, running the [8.2](references/phase-6-validate-skill.md#82-test-the-audit-itself) corpus sweep and collecting its JSON), if at all, and record which steps used one.
- **Record** the model (name and ID) of this session and of every sub-agent in the Design record ("Inputs at generation time") and in the Final report.
- **State** the generated skill's model tier in its opening lines and `compatibility`; pin it only as D-26 decides.

## 1. Purpose and how to use this procedure

### 1.1 Who reads this

- **The executor** is an LLM agent working inside the target SDK repository, with shell access, file read/write access, and the ability to ask the user questions, running on an Opus-class model ([2.8](#28-model-tier-and-sub-agents)). Every instruction below is addressed to it ("you").
- **The user** is an SDK engineer who owns the target repository. They answer the questions at the stop points and approve every change outside the skill directory.
- **A reviewer** may skim the working records (Repo profile, Harness design, Design record, Final report) instead of the whole conversation. Any human may skim this skill to see what the agent will do and where it will ask for decisions.

### 1.2 Invocation

The user starts a run in the target SDK repo with one sentence, for example:

```
/uts-to-lang-skill-creator ~/src/specification realtime unit first        (Claude Code)
$uts-to-lang-skill-creator ~/src/specification realtime unit first        (Codex)
Create a uts-to-csharp skill for this repo; the spec clone is ~/src/specification.
Audit our uts-to-python skill against the guide and upgrade it; add LiveObjects support.
Read <spec-clone>/uts/skills/uts-to-lang-skill-creator/SKILL.md and follow it to create a uts-to-<lang> skill for this repo.   (any agent, skill not installed)
```

`<spec-clone>` is the user's local clone of `ably/specification`. Take it, and any goals, from the user's words; argument substitution isn't available in every tool. Installation (a symlink into `~/.claude/skills/` and `~/.agents/skills/`) is described in [`uts/README.md`](../../README.md#installing-the-skill-creator). If the user also states goals ("objects unit tier first", "rest and realtime only"), record them as inputs.

### 1.3 Required inputs

| Input | Example | If missing |
|---|---|---|
| Target SDK repo path | the current working directory | Ask. Don't assume the working directory is the SDK repo: Orient checks that it is an eligible Ably Pub/Sub SDK repository with SDK sources and tests (STOP-16) |
| Language (and the skill name it implies) | C# → `uts-to-csharp`; Python → `uts-to-python` | Infer from the repo in Phase 1, then confirm |
| Local spec clone path | `~/src/specification` (the directory that contains `uts/` and `specifications/`) | Located by `scripts/spec_clone_info.py` ([2.6](#26-pin-the-spec-clone)) and confirmed with the user; otherwise **stop and ask** ([STOP-1](#23-stop-points)). Never fetch the spec or the UTS docs from GitHub instead |
| User goals: modules and tiers wanted first | "realtime unit, then rest unit; objects later" | Ask. Default to every module (`rest`, `realtime`, `objects`) and every tier the SDK can support, prioritised by the user |
| Model tier | The session's model, Opus-class ([2.8](#28-model-tier-and-sub-agents)) | Take it from your environment if it states your model; otherwise ask. If the model isn't Opus-class: **STOP-1** |
| Local clones of ably-cocoa and ably-java (now `ably-pubsub-java`) (optional) | Clones of either repo, read at their current HEAD (ideally a recent `main`) | Not needed to start. Ask only if you reach the last-resort reference reads ([2.1](#21-your-inputs)); without clones, those reads go to GitHub after **STOP-6** |

### 1.4 Outputs

1. **The harness** for this language, in the target repo: the shared test library implementing the helper specs, wait and assertion helpers, sandbox and proxy helpers, module helpers, the per-tier smoke tests and helper self-tests (guide [2.7](../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must); permanent and run in CI), a harness README with its Known gaps and, with explicit approval, SDK test hooks. Built in Phase 3, unless the user scopes it down at [STOP-3](#23-stop-points).
2. **The skill** (in upgrade mode, the existing skill, upgraded in place), at `.claude/skills/uts-to-<lang>/` (linked from `.agents/skills/uts-to-<lang>/` for Codex, guide [3.1](../../docs/writing-uts-spec-translator-skills.md#31-layout)) unless the Design record says otherwise (D-01): `SKILL.md`, `uts-package-mapping.json`, `scripts/resolve_uts.py`, `scripts/audit_translation.py`, `references/<module>-mapping.md` and, if shipped (D-19), `scripts/scan_constructs.py` (layout: guide [3.1](../../docs/writing-uts-spec-translator-skills.md#31-layout)).
3. **Pilot-translated tests**, one spec per available tier (in upgrade mode, per tier whose rules changed, 11.6), produced by the new skill in Phase 6.
4. **Four working records** (five in Upgrade/Fix; *Procedure recommendation*), created after STOP-13, written as Markdown files in the working-records directory (default `.claude/skills/uts-to-<lang>/generation/`; confirmed in Phase 4, decision D-24):
    - `repo-profile.md` ([repo-profile template](assets/templates/repo-profile.md));
    - `uts-infra-design.md`: the gap table, the harness design and the build log ([uts-infra-design template](assets/templates/uts-infra-design.md));
    - `design-record.md` ([design-record template](assets/templates/design-record.md)), which also holds the decision log;
    - `final-report.md` ([final-report template](assets/templates/final-report.md)), with the acceptance checklist ([acceptance-checklist template](assets/templates/acceptance-checklist.md)) pasted into its "Acceptance checklist" section;
    - in Upgrade/Fix, also `skill-gap-audit.md` ([skill-gap-audit template](assets/templates/skill-gap-audit.md)).

Create each record by copying its template from `assets/templates/` (the repo-profile, uts-infra-design, design-record and final-report templates, and in Upgrade/Fix the skill-gap-audit template) to the working-records directory under the same file name, then fill it in.

Write them from STOP-13 on, at the location Orient's routing gives (13.5), by default using the language inferred so far for `<lang>`; if STOP-2 changes the language or D-24 chooses another location, move the files then. They are working notes, not skill files, so writing them before STOP-7 is allowed.

The working records are what a later agent reads to maintain or regenerate the skill ([section 10](references/upgrade-diff-driven.md#10-upgradefix-diff-driven)), so keep them accurate as you go, not only at the end.

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
| Questions none of the above answer, as a last resort only | The reference implementations, under [2.1](#21-your-inputs): never an authority |

If two documents disagree, follow the higher one in the table (and **STOP-11** if the conflict changes what you would build or generate), record the conflict in the Design record, and list it in the Final report under "Spec-repo doc issues". Don't patch the spec repo. A disagreement between a reference implementation and the guide or the UTS docs is never a STOP-11: follow the guide, and record the disagreement with the read ([2.1](#21-your-inputs)).

**Procedure recommendations.** Where this skill adds detail the guide doesn't have (for example: the working-records files and their location, tier-readiness data in the mapping, a mandatory `specRepo`, and requiring the audit's end-at-heading rule), it is marked *Procedure recommendation*: this skill's way of meeting the guide, not a guide requirement. Follow it unless the user decides otherwise, and record any departure in the decision log. Everything else either links to the guide or is procedure (order, checks, stop points).

## Run modes

Orient (Step 0) recommends the mode, and the user decides at STOP-13 (D-27). There are two user-facing modes, and the same phases, ground rules and stop points serve both:

| Mode | When | Read |
|---|---|---|
| **Create** | No `uts-to-*` skill yet (S0); or none, but UTS-tagged tests or harness code to adopt (S1, 2.2) | The phases below |
| **Upgrade/Fix** | A `uts-to-*` skill exists. **Diff-driven** for one this procedure built (S2): follow what changed since its recorded run ([section 10](references/upgrade-diff-driven.md#10-upgradefix-diff-driven)). **Full gap audit** for one of unknown origin (S3), or by choice: audit it, its harness and its UTS-derived tests against the guide, choose per item, upgrade in place ([section 11](references/upgrade-existing-skill.md#11-upgrade-mode-audit-and-upgrade-an-existing-skill)). **Regenerate from scratch** only by the user's choice ([11.5](references/upgrade-existing-skill.md#115-step-u4-run-the-phases-scoped)) | Sections 10 and 11 |

An interrupted run is resumed or restarted from its records (13.6). In every mode, Phase 1 also asks whether to add LiveObjects (`objects`) support (**STOP-14**), recommending an answer from `detect_liveobjects.py`'s evidence: [references/liveobjects-support.md](references/liveobjects-support.md) (section 12).

## Phases at a glance

Before starting a phase, read its reference file in full: this table is a map, not enough to act on. In Upgrade/Fix with a full gap audit, read [11.5](references/upgrade-existing-skill.md#115-step-u4-run-the-phases-scoped)'s row for each phase first (diff-driven: section 10): the phases are scoped to the chosen items, and acceptance items tied to a skipped or deferred gap-audit row are reported ✗ under D-29, not worked. In regenerate mode, read 11.5's last paragraph instead. On resuming an interrupted run, read the working records first, then the reference of the phase you are in.

| Phase | Goal | Read first | Writes | Ends at |
|---|---|---|---|---|
| 0. Orient | Eligibility, capabilities and scope, state class, mode | [Step 0](#step-0-orient); [references/orient.md](references/orient.md) | nothing | STOP-16 (if not eligible), STOP-1 (if needed), STOP-17 (if needed), STOP-13 |
| 1. Understand the repo | A confirmed Repo profile: how the SDK is built, tested and mocked today; the LiveObjects decision; in Upgrade/Fix, the gap audit or the change list | [references/phase-1-understand-repo.md](references/phase-1-understand-repo.md) (and sections 10, 11, 12) | `repo-profile.md`; in Upgrade/Fix `skill-gap-audit.md` | STOP-2, STOP-14 (STOP-15 in Upgrade/Fix) |
| 2. Design the harness | Reuse, wrap, extend or build each capability; hooks; placement; tier feasibility | [references/phase-2-design-harness.md](references/phase-2-design-harness.md) | `uts-infra-design.md` (uts-infra-design template) | STOP-3 |
| 3. Build and verify the harness | The approved harness, with green per-tier smoke tests and self-tests, wired into CI | [references/phase-3-build-harness.md](references/phase-3-build-harness.md) | harness code and README; build log | STOP-7 |
| 4. Skill design decisions | Decisions D-01 to D-31, confirmed | [references/phase-4-design-record.md](references/phase-4-design-record.md) | `design-record.md` (design-record template) | STOP-8 |
| 5. Generate the skill files | Mapping, resolver, audit, construct catalogue, module notes, `SKILL.md` | [references/phase-5-generate-skill.md](references/phase-5-generate-skill.md) | the `uts-to-<lang>` skill | (STOP-9 if constructs are unmapped) |
| 6. Validate the skill | Resolver, audit mutations, pilots, other paths, lint, examples | [references/phase-6-validate-skill.md](references/phase-6-validate-skill.md) | pilot tests; results | (STOP-10 at a bound) |
| 7. Final report and handover | Report and acceptance checklist | [section 9](#9-phase-7-final-report-and-handover) below | `final-report.md` (final-report and acceptance-checklist templates) | — |

## 9. Phase 7: final report and handover

1. Write `final-report.md` from the [final-report template](assets/templates/final-report.md). Set the design record's Run status to finished, and refresh the skill's provenance stamp (D-30, 13.7).
2. Fill the [acceptance checklist](assets/templates/acceptance-checklist.md): tick each item, mark it n/a with the reason ([13.8](references/orient.md#138-capabilities-and-scope-stop-17-d-31)), or explain why it isn't met (scoped out, planned, skipped or deferred at STOP-15).
3. Show the user the report, the list of changed and new files (harness, harness tests, hooks, skill, pilot tests), and the suggested CI changes. The run is complete only if the harness tests are green, and in CI, at every tier the skill supports; otherwise the report says which tiers aren't and why. **Don't commit** unless asked.
4. If the user asks for a commit, follow the repo's commit conventions (P-08) and, if the user agrees, keep the SDK hooks, the harness, the skill and the pilot tests in separate commits. In Upgrade/Fix, offer one commit per closed gap-audit item (from the Design record's changelog), harness rows first.

The acceptance checklist maps each item of the guide's [section 13 checklist](../../docs/writing-uts-spec-translator-skills.md#13-checklist-for-a-new-uts-to-lang-skill) to where this procedure produces and verifies it. Mark each ✓, ✗ (with the reason) or n/a (with the reason).

## Reference index

| File | Read it when | Sections |
|---|---|---|
| [references/phase-1-understand-repo.md](references/phase-1-understand-repo.md) | Starting Phase 1 | 3 |
| [references/phase-2-design-harness.md](references/phase-2-design-harness.md) | Starting Phase 2 | 4 |
| [references/phase-3-build-harness.md](references/phase-3-build-harness.md) | Starting Phase 3 | 5 |
| [references/phase-4-design-record.md](references/phase-4-design-record.md) | Starting Phase 4; mapping a guide change to decisions (Upgrade/Fix, diff-driven) | 6 |
| [references/phase-5-generate-skill.md](references/phase-5-generate-skill.md) | Starting Phase 5; listing corpus harness symbols in Phase 2 (7.4) | 7 |
| [references/phase-6-validate-skill.md](references/phase-6-validate-skill.md) | Starting Phase 6 | 8 |
| [references/orient.md](references/orient.md) | Step 0, every run | 13 |
| [references/upgrade-diff-driven.md](references/upgrade-diff-driven.md) | Upgrade/Fix, diff-driven (S2) | 10 |
| [references/upgrade-existing-skill.md](references/upgrade-existing-skill.md) | Upgrade/Fix, full gap audit or regenerate | 11 |
| [references/liveobjects-support.md](references/liveobjects-support.md) | Phase 1 step 1e (every run); writing the objects notes | 12 |
| [assets/templates/repo-profile.md](assets/templates/repo-profile.md) | Copy to the working-records directory at the start of Phase 1 | — |
| [assets/templates/uts-infra-design.md](assets/templates/uts-infra-design.md) | Copy at the start of Phase 2 | — |
| [assets/templates/design-record.md](assets/templates/design-record.md) | Copy after Orient, at the start of Phase 1 (it holds the decision log from Phase 1 on) | — |
| [assets/templates/final-report.md](assets/templates/final-report.md) | Copy in Phase 7 | — |
| [assets/templates/acceptance-checklist.md](assets/templates/acceptance-checklist.md) | Fill into the Final report in Phase 7 | — |
| [assets/templates/skill-gap-audit.md](assets/templates/skill-gap-audit.md) | Copy in Upgrade/Fix at U1 (diff-driven: before STOP-15, for section H) | — |
| [references/glossary.md](references/glossary.md) | A term is unclear | — |
| [references/failure-modes.md](references/failure-modes.md) | A harness check, a pilot test or a command fails in a way you don't recognise | — |

The templates are copied, not linked: they contain no links, so they stay valid in the SDK repo.

## Scripts

All read-only, Python 3, printing to stdout (no network); run them from anywhere as `python3 <skill-dir>/scripts/<name>.py`. What they know about Ably's repositories and SDK names that the spec can't give is data in `assets/eligibility.json` and `assets/capability-names.json`: update the data file, not the code ([section 10](references/upgrade-diff-driven.md#10-upgradefix-diff-driven)).

| Script | Use | Output |
|---|---|---|
| `orient.py <repo> [--spec-clone P] [--skill-dir P] [--records P] [--full]` | Step 0: run the scripts below in order, classify the repo and recommend a mode ([13.1](references/orient.md#131-run-it)) | `state` (class S0–S4 or INELIGIBLE, re-entry, reasons, recommended, options), `stateSummaryText`, and the facts behind them |
| `check_repo_eligibility.py <repo> [--spec-clone P]` | Is this repository on the whitelist? All remotes, canonical and planned names, the capability override, the definition gate ([13.2](references/orient.md#132-repository-eligibility-stop-16)) | `decision` (accept, reject, ask), `code`, `owner`, `repo`, `nameForm`, `canonical`, `plannedRename`, `capabilityOverride`, `message`, `fingerprint` |
| `detect_capabilities.py <repo> [--spec-clone P] [--include-submodules] [--capability-override rest=full,realtime=absent]` | The REST and Realtime capability profile (connection, channels, presence, transport), the door sides and the suggested scope ([13.8](references/orient.md#138-capabilities-and-scope-stop-17-d-31)) | `namesSource`, `specRevision`, `capabilities` (levels, clients, public reachability, evidence, `methodGapsAdvisory`), `source`, `sides`, `wrapsNativeSdk`, `scopeSuggestion` (`kind`, `modules`, `unsupported`, `capabilityInapplicable`, `extraTests`, `confirmAtStop17`), `reasons`, `summary` |
| `spec_names.py [--spec-clone P]` | The names the two detectors look for, read from the spec clone's IDL at run time, and the corpus's capability-inapplicable tests ([13.8](references/orient.md#138-capabilities-and-scope-stop-17-d-31)) | `source` (`spec` or `fallback`), `revision`, `warnings`, the client, channel, connection and presence names and members, the LiveObjects name sets, `capabilityInapplicable` |
| `spec_clone_info.py [SPEC_CLONE]` | Locate, validate and pin the spec clone ([2.6](#26-pin-the-spec-clone)). Discovery order: the path the user gave; `UTS_SPEC_CLONE`; the clone this skill is symlinked from | One JSON object: `specClone`, `foundBy`, `sha`, `dirty`, `dirtyFiles`, `guideLastChange`, `skillDir`, `skillRealpath`, `skillVersion`, `skillMatchesClone`, `warning` (if any), `paths` (guide, UTS docs, helper specs); or `ok: false` with a `code` |
| `survey_repo.py <repo> [<test-root> …]` | A first pass over the target repo for the discovery checklist ([3.2](references/phase-1-understand-repo.md#32-step-1b-answer-the-discovery-checklist)) | HEAD and status, extension counts, test roots, submodules, candidate mocks, `UTS:` tags, existing skills |
| `scan_constructs.py <spec-clone>/uts/<module>` | List the corpus's pseudocode constructs and harness calls ([7.4](references/phase-5-generate-skill.md#74-step-5d-fill-the-construct-catalogue)); copy it into the generated skill's `scripts/` (D-19) | Keyword and snake_case call counts |
| `inspect_existing_skill.py <repo> [<skill-dir>]` | Inventory an existing `uts-to-*` skill, its harness entry and its UTS-derived tests, for STOP-13 and the gap audit ([11.1](references/upgrade-existing-skill.md#111-when-this-mode-applies)); also lists user-level installs | Skills and their installs (copies compared), frontmatter, files, mapping, harness (from the mapping, or candidate READMEs, smoke-test files and CI lines), regex checks keyed to checklist items (hints, not a review); tag, header-SHA and `deviations.md` counts, tags outside the mapped tiers; working records |
| `detect_liveobjects.py <repo> [--spec-clone P] [--include-submodules]` | Evidence for the LiveObjects decision at STOP-14 ([12.1](references/liveobjects-support.md#121-gather-the-evidence-step-1b-p-15)); names from `spec_names.py` | `namesSource`, `specRevision`; a one-paragraph `summary`; a recommendation with reasons; per category (public API, accessor, legacy, shared, internal, wire-only), symbols with counts, files and declaration sites; the public names not found; plugin key, packaging, nested packages; exclusions |
