# 8. Phase 6: validate the skill

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention). Links that climb out of the skill directory are spec-repo paths: resolve them against the spec clone, not against this file's installed location.

Contents:

- [8.1 Run the resolver on every module](#81-run-the-resolver-on-every-module)
- [8.2 Test the audit itself](#82-test-the-audit-itself)
- [8.3 Infra gate and selection dry run](#83-infra-gate-and-selection-dry-run)
- [8.4 Fix the cause](#84-fix-the-cause)
- [8.5 Exercise the skill's other paths](#85-exercise-the-skills-other-paths)
- [8.6 Lint and CI-strict compile](#86-lint-and-ci-strict-compile)
- [8.7 Verify the skill's own code](#87-verify-the-skills-own-code)
- [8.8 Reference tests: none yet](#88-reference-tests-none-yet)
- [8.9 Check the acceptance checklist](#89-check-the-acceptance-checklist)

**Goal:** evidence that the skill works on this repo, on top of the UTS infra you built, **without generating any spec-derived test**: the first come from the first real run of the skill. This phase is mandatory. Record every result in the Final report, and update the acceptance-checklist rows each step verifies, with their evidence ([9](../SKILL.md#9-phase-7-final-report-and-handover)). Independent steps (8.1, 8.5, 8.7) can run in parallel sub-agents ([parallel-work.md](parallel-work.md)). The 8.3 dry runs can be prepared in parallel, but their step F preflights compile and run the infra tests, so they run one at a time, like every other build and test run.

What these checks can't show is whether the skill's translations come out right; that shows at the first real translation run, and the fix-the-cause, regenerate and re-sync cycle (guide [section 9](../../../docs/writing-uts-spec-translator-skills.md#9-keeping-in-sync-with-spec-changes)) handles it there. The Final report says so in "Next steps".

## 8.1 Run the resolver on every module

Run the resolver on `<spec-clone>/uts/rest`, `<spec-clone>/uts/realtime` and `<spec-clone>/uts/objects`, whether or not they are in scope (an unmapped module must resolve with `mapped: false`, not crash). For each, check:

- [ ] `ok: true`; tiers `present` match `ls <spec-clone>/uts/<module>`.
- [ ] Spec counts match the files on disk minus the exclusions. A cross-check: `find <spec-clone>/uts/<module>/<tier> -name '*.md' -not -path '*/helpers/*'` (add the proxy exclusion for the integration tier).
- [ ] No helper spec, `README.md`, `PLAN.md` or `*_SUMMARY.md` appears in `specs`.
- [ ] Every `className` follows D-04 and is collected by the runner; no collisions (or the collision is reported).
- [ ] Every spec in a sub-directory resolves to the mirrored path: its `subDir`, `targetDir`, `testFile` and (where the language has one) namespace follow D-04 (guide 3.2 "Sub-directories are mirrored").
- [ ] The tier-level `targetDir`, namespace and build target match the mapping and the Design record; the test project and namespace root are derived, not read from the mapping.
- [ ] `infra` per tier: `tests` is the mapping's `testCommand` with `{tier}` expanded; `sources` follow the tier layout (the root's own files and `common/`, plus each tier directory on the path to the tier), with no file from the infra-tests tree; `testsRoot` exists. With the former key `harness` or an older mapping shape, the output carries the warning.
- [ ] An out-of-scope module (a module-level `unready`) reports every tier `ready: false` with that reason, and no tier paths are needed.
- [ ] A tier with a `translateOnly` entry (SDK-blocked, [12.5](liveobjects-support.md#125-an-sdk-blocked-objects-tier)) is reported `translateOnly` with its reason.
- [ ] The same module given as a `~`-prefixed path, and (on Windows) with backslash separators, resolves identically (guide [8.1](../../../docs/writing-uts-spec-translator-skills.md#81-resolver-resolve_utspy-must) "Validate the module").

Then give the resolver the clone root (`<spec-clone>`) and no argument: each prints the module listing (`rest`, `realtime`, `objects`, and nothing that lacks `unit/` or `integration/`, such as `docs`), with `offerable: false` and the mapping's reason for an `unready` module or an `unsupported` one without `extraTests`; an `unsupported` module with `extraTests` is offerable, for just those tests (guide 8.1 "Module listing"). A bare module name, if accepted, resolves like its module path in the shared clone.

Then run the negative cases and check each returns `ok: false` with the right code: a path whose parent isn't `uts`; a missing directory; a module with no tier directories (a scratch directory named `uts/<x>` will do); a mapping entry whose notes file is missing (use a scratch copy of the mapping); `--create` with an invalid name; `--create` on a scratch copy of a deliberately corrupt mapping (the file must be left unchanged).

## 8.2 Test the audit itself

Write one known-good test file by hand, with the correct tags (a fixture, never a translation), and make scratch copies for each mutation:

| Mutation | Expected audit result |
|---|---|
| Delete one assertion | A positive assertion shortfall for that test |
| Comment out one assertion | The same shortfall (commented assertions don't count) |
| Duplicate one test's tag | `duplicate` lists the ID; distinct non-zero exit |
| Add a tag that isn't in the spec | `orphan` lists it |
| Remove one tag | `missing` lists it |
| Add surplus waits to a test with a deleted assertion | The assertion shortfall is still reported (counts aren't summed) |
| Delete the native assertion that renders a spec `FAILS WITH` (awaited or not) | A positive assertion shortfall for that test |
| Delete the poll call that renders a spec `poll_until` (with no `AWAIT` on the spec line) | An await shortfall for that test (spec polls count as waits) |

**Whole-corpus sweep:** run the audit on every spec the resolver lists for each of the three modules, against an empty test file. Every run must print one parseable JSON object and exit with the "ID problems" code (or report "not verifiable" for ID-less specs such as `rest/unit/encoding/msgpack_interop.md`). No crashes. Cross-check the spec-side ID count per module against ``grep -rhoE '\*\*Test ID\*\*: `[^`]+`' <spec-clone>/uts/<module> | sort -u | wc -l``.

## 8.3 Infra gate and selection dry run

Neither part generates a test. In Upgrade/Fix, full gap audit, [11.6](upgrade-existing-skill.md#116-step-u5-validate-without-regressions) decides which of 8.1 to 8.9 run, and adds the baseline comparison; in Upgrade/Fix, diff-driven, section 10 says which checks to re-run.

**(a) The infra gate.** For each tier the skill supports, run the mapping's infra test command (after **STOP-6** for network tiers). The smoke tests and self-tests must be green; the one exception is an SDK-blocked objects tier ([12.5](liveobjects-support.md#125-an-sdk-blocked-objects-tier)), green except the SDK-blocked items. If network access is declined, that tier is reported as unvalidated. Record each result with the command and its exit status. Then run step F's Known-gaps match over every spec of each tier: a gap that matches most of a tier, or one with no failing self-test behind it, is suspect; check it before handover. A red gate, or a suspect gap that turns out false, is a defect ([8.4](#84-fix-the-cause)).

**(b) The selection dry run.** For each ready module × tier in scope, run the skill the way a user would, through steps 0 and A–F to a green preflight, and stop before step 1: it writes no test.

- **Loading the skill.** A skill created during a session may not be listed until a new session starts. Ask the user to start a new session of the same tool (Claude Code or Codex) in the repo, on an Opus-class model ([2.8](../SKILL.md#28-model-tier-and-sub-agents)) (or to reload skills, if their client supports it), and confirm `/uts-to-<lang>` is listed (and, if D-01 links the skill for Codex, that `$uts-to-<lang>` is listed in a new Codex session). A fresh session also tests that the skill is context-complete on its own (guide intent), so the dry run never consults the reference implementations. A sub-agent that reads the skill by path doesn't show that it is listed: that needs a new session, or 8.5 path 10.
- **Answering its questions.** The answers are D-03 (mapping confirmation), the tier, any one spec of that tier, and the mode D-28 implies (translate-only for a `translateOnly` tier; otherwise evaluate), then "stop before step 1". Either the user runs `/uts-to-<lang> <spec-clone>/uts/<module>` (Claude Code) or `$uts-to-<lang> <spec-clone>/uts/<module>` (Codex) in the new session and answers with them, or, if the skill is listed in a session you control, you invoke it and answer with exactly those choices. If you use a sub-agent, run it on an Opus-class model ([2.8](../SKILL.md#28-model-tier-and-sub-agents)), and give it only the invocation, these answers and the instruction to stop before step 1, none of this run's context. It must not consult the reference implementations or any other SDK's skill, because the dry run tests the skill alone. Record the session's or sub-agent's model with the dry-run results. Any other question goes to the user.
- **Record each question the skill asked,** what step 0 read, and the preflight result. More than the four questions, other than a stop the guide requires (an unmapped module's name at step B, a known gap or red infra tests at step F), or a question it should have answered from its own files, is a skill defect ([8.4](#84-fix-the-cause)).

The step F preflight runs the infra tests again for that tier (after **STOP-6** for network tiers); a dry run that ends on a red preflight is a defect, not a result.

## 8.4 Fix the cause

For every defect any Phase 6 check finds:

1. Classify it: a rule in `SKILL.md`, a mapping in the notes, a catalogue row, a resolver or audit bug, or an infra gap. A UTS spec error found here (for example, in a helper spec the UTS infra implements) is not a skill defect: record it, and **STOP-10**.
2. Fix that cause. An infra fix follows the rules of [5.1](phase-3-build-infra.md#51-step-3a-rules-while-building), adds or extends a self-test that would have caught the defect, re-runs the affected tiers' smoke tests and self-tests, and updates the infra README (and its Known gaps).
3. Re-run the check that found it.
4. Log the defect and the fix in the Design record's changelog.

**Bound:** three fix attempts per check. If it still fails, stop (**STOP-10**) with a summary of every defect found and fixed so far.

## 8.5 Exercise the skill's other paths

Run each path through the skill (in the fresh session from [8.3](#83-infra-gate-and-selection-dry-run), the dry run) and record the result:

1. **Usage guard and module selection** (dry runs: stop at the module question). No argument → the one-line shared-clone announcement; with `ABLY_SPEC_CLONE` set to a scratch path that doesn't exist, one question offering to clone it (decline); otherwise the sync per `ABLY_SPEC_SYNC` and the clone's state ("latest `main`" only after a successful sync); then the module question: the modules under `uts/`, an `unready` module (e.g. out of scope) or an `unsupported` one without `extraTests` shown with its reason and not selectable, an `unsupported` module with `extraTests` offered for just those tests, no recommendation. A clone path (`<spec-clone>`) that isn't the shared clone → the static not-synced warning, no fetch, then the same question (the shared clone given as a path is synced as usual, path 11). A module path or a bare module name → no module question. An argument that is none of these → the usage line, then stop.
2. **Bad module path:** a path whose parent isn't `uts` → the resolver's error relayed, then stop.
3. **Placeholder notes:** a module whose notes file is a placeholder → refused, with the reason.
4. **Unready tier:** a tier the mapping marks unready → not offered at step C, with its `blockedBy`; a module marked unready as a whole (a module-level `unready`, e.g. `objects` out of scope) → refused with its reason, no `--create` offered; an `unsupported` module (D-31) → refused with "unsupported: <reason>", and no build hint; a spec or Test ID under `capabilityInapplicable` → never selected, and reported with its reason; for a REST-only skill, the `realtime` module → only its `extraTests` offered ([7.1](phase-5-generate-skill.md#71-step-5a-create-the-layout-and-the-mapping-file)); a `translateOnly` tier (12.5) → step E offers only translate-only.
5. **Unmapped module:** on a scratch copy of the mapping, a module without an entry → step B asks for a name and runs `--create`, which writes the D-03 default layout and preserves the other entries.
6. **Re-sync** (if D-19 ships it): on a scratch copy of an existing UTS-derived test (Upgrade/Fix) or of the 8.2 fixture with a file header, set the header SHA to an older spec commit that changed that spec (`git -C <spec-clone> log --format=%H -- uts/<path>`), run `--resync`, and check the classification; stop before it regenerates anything. A change outside the pseudocode, such as `## Protocol Variants`, is reported as **changed**; so is an uncommitted edit to that spec, made in a scratch clone of the spec repo (`git clone <spec-clone> <scratch>`; the spec clone itself is never edited by hand, 2.2). The header update and the survivors in guide [9.2](../../../docs/writing-uts-spec-translator-skills.md#92-a-re-sync-mode-should) step 4 are verified at the first real re-sync. Delete the scratch copy afterwards.
7. **Commands:** every build, run, lint and audit command `SKILL.md` names has now been run, except the run of a generated class by filter: run that filter's syntax against an infra test class instead. The generated-class run first happens at the first real translation (its checklist row says so); fix any command that failed.
8. **Red infra:** on a scratch copy (or a temporary working-tree edit you revert afterwards), break one infra test (for example, make the WebSocket mock refuse every connection), or run an integration tier with the network unavailable → the skill stops at step F before generating anything, reports a UTS infra or environment problem (not an SDK deviation), and names the failing test. Restore the change and confirm the preflight is green again.
9. **Known gap:** select a spec that uses a construct the infra README lists under Known gaps → the preflight reports the conflict and stops to ask (guide 4 step F), rather than generating a substituted rendering. If Known gaps is empty, use a scratch copy of the README with an entry for a construct the selected spec uses.
10. **Second tool:** if D-01 links the skill for Codex, start a Codex session in the repo, invoke `$uts-to-<lang>` with no argument (the shared-clone announcement, then the module question; stop there) and with one module (step A runs the resolver from the skill's directory, not from `.claude/skills/`). Record whether Codex was available; if it wasn't, report this path as not run.
11. **Spec-clone sync** (D-32, unless declined): make a scratch clone of the spec repo (`git clone <spec-clone> <scratch>`, then `git -C <scratch> remote set-url origin https://github.com/ably/specification.git`, which uses no network, so the sync treats it as a real clone). First name it by the module path (`<scratch>/uts/<module>`), with `ABLY_SPEC_SYNC=auto`: the skill shows the static warning and never fetches (`FETCH_HEAD` and the reflog of `origin/main` don't change). Then make it the shared clone (`ABLY_SPEC_CLONE=<scratch>`): the same module path is now synced, because it is the shared clone. Run the skill once with `ABLY_SPEC_SYNC=off` (no fetch) and once with the scratch clone on another branch (reported, never switched or updated). Check that the final report records the SHA, the branch and the sync's outcome (or "not synced"), and that step 0 reads every source guide 4 step 0 lists from that clone, including, when the integration or proxy tier is offered, only the named sections of `integration-testing.md`.

## 8.6 Lint and CI-strict compile

Run the frontmatter validation of [7.6](phase-5-generate-skill.md#76-step-5f-write-skillmd). Run the repo's lint and format gates (P-06) over every file you created or changed, including the UTS infra, the skill's scripts and Markdown where the repo's EditorConfig covers them. Compile the test targets as strictly as CI does (warnings as errors, static analysis, type checkers). Run the skill's scripts on every developer platform you can, or note which you couldn't.

## 8.7 Verify the skill's own code

Every code example in `SKILL.md` and the notes must compile (guide [12](../../../docs/writing-uts-spec-translator-skills.md#12-lessons-learned)). For each example, either:

- name the real, compiled file it was copied from (and check it still matches), or
- paste it into a scratch file in the test target, compile, and delete the scratch file.

Then do the same for the **file template per tier** (with its header) and **every `mapped` construct-catalogue rendering**: paste them into one scratch file per tier in the test target, with the minimum scaffolding they need, and compile it CI-strict against the UTS infra. The scratch file is never run and never kept; delete it afterwards. This shows that the renderings name real symbols with real signatures and that each tier's file shape compiles: the same code a translation would produce, minus the spec-specific choices.

Record what was verified and how.

## 8.8 Reference tests: none yet

The skill's `SKILL.md` says `none yet` for each tier's reference test ([7.6](phase-5-generate-skill.md#76-step-5f-write-skillmd)); this phase names none, since it generates no test, and never names a smoke test. The generated skill proposes one after a tier's first reviewed translation, and records it if the user agrees (guide [4, step 3](../../../docs/writing-uts-spec-translator-skills.md#phase-2-per-spec-steps-17)). If the user declines, the next Upgrade/Fix run lists it as a gap item.

## 8.9 Check the acceptance checklist

Run the automated check on the generated skill. `check_acceptance.py` is this skill creator's script, in the spec clone (`<skill-dir>` below is this skill's directory there). It isn't copied into the generated skill, so every later re-run also runs it from the spec clone:

```
python3 <skill-dir>/scripts/check_acceptance.py <repo> <generated-skill-dir> [--records <dir>]
```

It runs the inspector's checks on the new skill ([11.2](upgrade-existing-skill.md#112-step-u1-understand-the-existing-skill)), reads the working records' `acceptance-checklist.md`, and checks:

- every row of the template is present, in guide §13 order, with a status: ✓ with evidence, "✓ static; behaviour at first translation" with evidence, ✗ or n/a with a reason, or open;
- every inspector `fail` is fixed, or its row is ✗ or n/a with the reason (a fail under a ✓ row is unexplained);
- the records it points to exist: the Repo profile, the infra design, the Design record and the infra README with its Known gaps (and, with `--final`, the Final report).

It prints JSON with a `summaryMarkdown` field (`--markdown` prints only that): the counts per status, the unexplained fails and the problems. Fix what it finds (8.4) and update the rows. Phase 7 runs it again with `--final` once the independent verification is recorded; `--final` also needs no open row and the verification line, and the completion gate follows its result ([9](../SKILL.md#9-phase-7-final-report-and-handover)). The check is regex and table parsing, not a review; the independent verifier is the review. Anyone can re-run it later, after a hand edit, a diff-driven run or a guide change.

**Phase 6 is done when:**

- the resolver passes on all three modules and all negative cases;
- the audit passes every mutation and the sweep;
- the infra gate is green for each supported tier (or SDK-blocked, 12.5, or network declined and reported as unvalidated), and every dry run reached a green preflight;
- every path in 8.5 behaves as expected (including the red-infra stop), and every command in `SKILL.md` has been run (the generated-class run by filter excepted, path 7);
- lint and the CI-strict compile pass;
- 8.7's examples, templates and catalogue renderings compile, and the scratch files are deleted;
- 8.9's automated check has no unexplained fail.

The independent verifier runs in Phase 7, before the completion gate, not here.

In Upgrade/Fix, full gap audit, 11.6's "Done when" replaces this list.
