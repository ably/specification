# 11. Upgrade mode: audit and upgrade an existing skill

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention). Links that climb out of the skill directory are spec-repo paths: resolve them against the spec clone, not against this file's installed location.

**Goal:** bring an existing `uts-to-<lang>` skill, its harness and its UTS-derived tests up to the guide, one item at a time and as the user chooses, while keeping everything that already conforms. Guide [9.5](../../../docs/writing-uts-spec-translator-skills.md#95-upgrading-an-existing-skill-should) is the requirement. The ground rules, the stop points and the phases all apply unchanged. This section says what is different. It is the full-gap-audit form of Upgrade/Fix, and it also serves regenerate-from-scratch (11.5) and a diff-driven Upgrade/Fix run that needs a conformance check ([section 10](upgrade-diff-driven.md#10-upgradefix-diff-driven)).

Contents:

- [11.1 When this mode applies](#111-when-this-mode-applies)
- [11.2 Step U1: understand the existing skill](#112-step-u1-understand-the-existing-skill)
- [11.3 Step U2: write the gap audit](#113-step-u2-write-the-gap-audit)
- [11.4 Step U3: STOP-15, choose per item](#114-step-u3-stop-15-choose-per-item)
- [11.5 Step U4: run the phases, scoped](#115-step-u4-run-the-phases-scoped)
- [11.6 Step U5: validate without regressions](#116-step-u5-validate-without-regressions)

## 11.1 When this mode applies

Orient (Step 0, [section 13](orient.md#13-step-0-orient)) decides it. This section runs when the user chooses, at STOP-13:

- **Upgrade/Fix with a full gap audit**: recommended for a skill of unknown origin (S3), and a choice for one this procedure built (S2);
- **regenerate from scratch**.

Diff-driven Upgrade/Fix for an S2 skill is [section 10](upgrade-diff-driven.md#10-upgradefix-diff-driven); it hands off to 11.2 and 11.3 when it needs a conformance check. The State summary already lists the offered tiers that lack harness smoke tests or self-tests (G-19, G-20). Whatever is chosen, those tiers get them built, or the skill refuses them until they exist ([4.9](phase-2-design-harness.md#49-step-2i-stop-3-approve-the-design-and-choose-the-scope)).

In Create mode for a repo with UTS-derived tests or harness code but no skill (S1), those assets are inputs:

- show them in the Repo profile (P-20) at STOP-2;
- let Phase 2 assess the harness (reuse, wrap, extend or build);
- propose D-03, D-06 and D-07 to match those tests where they conform, and list the mismatches;
- never rewrite the tests without the user's approval (2.2).

A user-level install of a `uts-to-*` skill (in `~/.claude/skills` or `~/.agents/skills`) is only reported; it isn't this repo's skill. In Upgrade/Fix the working records go where Orient found them; otherwise `<existing-skill-dir>/generation/` (D-24).

**The repo's own skill is an input, not a reference implementation.** The existing skill, harness and tests in the target repo belong to primary input 4, the target SDK repo ([2.1](../SKILL.md#21-your-inputs)). Reading them in full and editing them in place is the job, not copying. The last-resort rules of 2.1 still govern every *other* repo's skill. When the repo is itself one of the reference implementations (ably-cocoa or ably-java), seed the gap audit with the guide's [Patterns to avoid](../../../docs/writing-uts-spec-translator-skills.md#patterns-to-avoid) entries for that skill and its harness. Check each one against the current files, because some may have been fixed.

## 11.2 Step U1: understand the existing skill

Copy the [skill-gap-audit template](../assets/templates/skill-gap-audit.md) to the working-records directory as `skill-gap-audit.md` now (create any other working record that doesn't exist yet; update the ones that do, superseding entries in the decision log). Before you judge anything, understand the skill fully, and record what you find in the Repo profile (P-20) and in the gap audit's section A:

1. Read in full the existing `SKILL.md`, the mapping file, every script, every `references/` file, and any working records.
2. Take the **baseline** (11.6), working only on a scratch copy of the whole skill directory, outside any skills directory (so no tool loads it), because the scripts find the mapping relative to their own file:
    - run the resolver, if there is one, on `<spec-clone>/uts/rest`, `uts/realtime` and `uts/objects`, plus the 8.1 negative cases;
    - run the audit, if there is one, over every existing UTS-derived test, plus the 8.2 mutation tests;
    - record "none" for a script that doesn't exist.
3. Read the harness the skill points at:
    - its README and sources, from the mapping's `harness` entry, or, if there is none, from the candidates the inspector lists and from P-16, P-17 and P-20;
    - its smoke tests and self-tests, and the CI jobs that run them.

    Run the harness tests and the existing UTS-derived tests by filter, unit tier only, and record the results and the compile status in the baseline. Network tiers need **STOP-6** first.
4. Read at least one UTS-derived test file per module and tier, every `deviations.md`, and any other record of deviations or spec issues kept beside the tests.
5. Note where the skill describes something that doesn't exist (a suite, a flag or a helper); the guide lists this as a pattern to avoid.

`inspect_existing_skill.py` gives a first pass. Its checks are regex hits, not a review: every row you write in 11.3 rests on reading the file.

## 11.3 Step U2: write the gap audit

Fill in `skill-gap-audit.md`. Give every row of sections B and D an ID (GA-01, GA-02, …), so the decision, the change that closes it and the Final report can all name it.

- **Section B (conformance):** one row per row of the [acceptance checklist](../assets/templates/acceptance-checklist.md), apart from the Harness group. Copy the checklist's first column, so the guide's §13, the checklist and the audit stay one list. For each row, record:
  - the status: `conforms`, `partial`, `missing`, `non-conforming`, `n/a` (with the reason, for example a tier the skill doesn't support), or `unverified (checked in <step>)` where only a later step can tell (the construct table at 7.4, compiling the examples at 8.7, or a network tier after STOP-6);
  - the evidence: a file and heading or symbol, or a command and its result;
  - for every row that isn't `conforms`: the proposed change, the step that makes it (for example "7.3: write `audit_translation.py`"), its size (S, M or L), and whether it needs STOP-4 or STOP-5 approval.
- Two kinds of row are settled elsewhere. The `objects` half of the module-notes row takes its status from D-28 (STOP-14). The Creation-process rows (the model tier, reference-implementation reads, and the audit row itself) usually can't be judged for a skill of unknown origin: record "origin unknown; this run meets it for the artifacts it changes".
- Judge against the guide, not against another SDK's skill or against this procedure's own conventions. A *procedure recommendation* the skill doesn't follow is a proposed improvement, marked as such, not a non-conformance. Something that conforms in substance but differs in shape (for example, an audit output shape that `SKILL.md` documents) conforms.
- **Not applicable.** A row, or part of one, that needs a capability the SDK lacks (D-31) is `n/a — capability absent: <capability> (D-31)`, not a gap. One that was n/a when recorded and whose capability now exists is `missing`, marked "newly applicable" ([13.8](orient.md#138-capabilities-and-scope-stop-17-d-31)).
- **Section C (harness):** the gap-table rows G-01 to G-20, each with a quick status from the evidence in U1. Phase 2 does the detailed assessment, and the user decides these rows at STOP-3, not at STOP-15.
- **Section D (UTS-derived tests):** per module and tier, record:
  - the files and tags, and the tag style (D-06);
  - the header SHAs compared with the clone's HEAD, plus the files with no SHA or with a link to `main` (re-sync can't place those);
  - tagged tests outside the mapped tier directories;
  - the `deviations.md` files;
  - the compile result and the audit result.

  Propose follow-ups as their own items: a re-sync; regenerating the files with no SHA through the skill at the clone's HEAD (never stamping a SHA onto a test that wasn't regenerated from it, guide 9.1); moving tests into the mapped directories; fixing the tag style.
- **Section E (LiveObjects):** the STOP-14 decision ([12.2](liveobjects-support.md#122-stop-14-recommend-then-ask)), with the objects items it implies. It isn't asked again here.
- **Section F (preserve list):** what conforms and is kept as it is. This includes rules, names and idioms, verified notes content, hand-maintained mapping entries, and harness pieces that pass their checks.

## 11.4 Step U3: STOP-15, choose per item

Present section B, grouped as in the checklist, followed by the follow-ups from section D, each with your recommendation. Every item has the same three options:

| Item | Options | Effect in the Final report's acceptance checklist |
|---|---|---|
| A MUST row | **add**, **skip** or **defer** | Skip or defer: ✗ with the user's reason (and, for defer, a plan in Next steps), and "the skill doesn't conform to the guide until this is done" |
| A SHOULD row or a follow-up | **add**, **skip** or **defer** | Skip: ✗ with the user's reason. Defer: ✗ with a plan |

Recommend **add** for every MUST row. The user can also choose **regenerate from scratch instead** (13.4). Record every choice as D-29, and in the decision log.

The choices are provisional where a row is `unverified`. When its status changes, re-confirm it: at STOP-8 for rows settled by then, or after Phase 6 for rows settled there.

The harness rows are decided at STOP-3, where in upgrade mode the user chooses per row: build, plan (defer) or skip. The exception is G-19 and G-20 for every tier the skill keeps offering; those can't be skipped or deferred (4.9). STOP-7 still gates the skill files in this mode.

## 11.5 Step U4: run the phases, scoped

| Phase | In upgrade mode |
|---|---|
| 1 | Already done before U2 (Repo profile, STOP-2, STOP-14) |
| 2 | Start the gap table from section C. Assess the existing harness as 4.2 says ("check it, don't trust it"). Design only the rows the chosen items and the missing MUST rows need. At STOP-3, decide per row (11.4) |
| 3 | Build the rows chosen at STOP-3. Don't change the behaviour of any harness code that existing UTS-derived tests or native tests use (2.2). Re-run the existing harness tests before and after each change. STOP-7 as usual |
| 4 | Pre-fill D-01 to D-26 with what the existing skill does ("Decided by: existing skill"), and propose a change only where a chosen item needs one. Fill in D-27 to D-29. At STOP-8, show the changed decisions, and the rows from 11.3 whose status changed |
| 5 | Edit the files in place: <br>• Keep every section that conforms. <br>• Change the smallest unit that closes the item (a rule, a table row, a function). <br>• Keep the skill's names, idioms and verified notes. <br>• When the chosen item is a restructure (for example moving long sections into `references/` to meet the 3.4 outline), move the text rather than rewrite it. <br>• Write any new file (for example a missing `audit_translation.py`) from the guide, never from another SDK's skill (2.1). <br>• Log each change in the Design record's changelog, with the GA- or G- row it closes |
| 6 | 11.6 decides which of 8.1 to 8.8 run, and adds the baseline comparison |
| 7 | The Final report, with its "Existing assets and upgrade summary". If the user asks for commits, offer one per closed item, from the changelog, harness rows first ([9](../SKILL.md#9-phase-7-final-report-and-handover)) |

The acceptance items of 7.1 to 7.6 and the "Done when" of each phase apply to what this run changes. An item tied to a skipped or deferred gap-audit row is reported ✗ under D-29, not worked.

Existing UTS-derived tests are regenerated only through an item the user chose, such as a re-sync, and only through the skill (fix the cause, then regenerate). They are never hand-edited.

**Regenerate from scratch** runs U1 (section A and the baseline) and records sections D to F, then the create flow. Propose D-03, D-04, D-06 and D-07 to match the existing UTS-derived tests unless the user decides otherwise. The new skill is staged under `<working-records>/staging/uts-to-<lang>/`, which no tool loads as a skill. After Phase 5 (and any STOP-9), show the staged files and, on the user's approval, swap them in before Phase 6. The swap replaces the skill's files, never the working-records directory, even when that directory sits inside the skill (the D-24 default). If the old files are untracked, move them to `<working-records>/previous/` first; if they are tracked, git keeps them. The Final report lists what the old skill had that the new one lacks.

## 11.6 Step U5: validate without regressions

- Run the Phase 6 checks for every changed artifact, and for every row still `unverified`, changed or not:
  - 8.1 if the resolver or the mapping changed;
  - 8.2 if the audit is new or changed;
  - the 8.5 paths of every workflow step that changed;
  - the 8.6 frontmatter check, always;
  - 8.7 for every changed example, and 7.4 and 8.7 for `unverified` rows.
- **Compare with the baseline from U1.** The resolver output for all three modules, the audit results on the existing tests, the results of the harness tests and the existing UTS-derived tests, and the compile status must match the baseline, or every difference must be explained by a STOP-15 item or a STOP-3 row (for example a tier that is now refused until its smoke tests exist). Anything else is a regression: fix its cause.
- **Pilot** (8.3): at least one spec for each tier whose rules, notes or harness changed, in a fresh session. A pilot never overwrites an existing UTS-derived test: choose a spec that has no test, or ask first (8.3).
- Run the new or changed audit over the existing UTS-derived tests. Report what it finds in section D and the Final report, and regenerate tests only where the user chose to.

**Done when:** every item chosen at STOP-15, and every harness row chosen at STOP-3, is done and verified; every `unverified` row is settled and re-confirmed; nothing in the preserve list changed without a logged reason; the baseline comparison shows no unexplained difference; and the Final report's "Existing assets and upgrade summary" and acceptance checklist reflect every choice.
