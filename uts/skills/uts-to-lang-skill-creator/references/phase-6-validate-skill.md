# 8. Phase 6: validate the skill

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention). Links that climb out of the skill directory are spec-repo paths: resolve them against the spec clone, not against this file's installed location.

Contents:

- [8.1 Run the resolver on every module](#81-run-the-resolver-on-every-module)
- [8.2 Test the audit itself](#82-test-the-audit-itself)
- [8.3 Pilot-translate one spec per available tier](#83-pilot-translate-one-spec-per-available-tier)
- [8.4 Fix the cause, then regenerate](#84-fix-the-cause-then-regenerate)
- [8.5 Exercise the skill's other paths](#85-exercise-the-skills-other-paths)
- [8.6 Lint and CI-strict compile](#86-lint-and-ci-strict-compile)
- [8.7 Verify the skill's own examples](#87-verify-the-skills-own-examples)
- [8.8 Name the reference tests](#88-name-the-reference-tests)

**Goal:** evidence that the skill works on this repo, on top of the harness you built. This phase is mandatory. Record every result in the Final report.

## 8.1 Run the resolver on every module

Run the resolver on `<spec-clone>/uts/rest`, `<spec-clone>/uts/realtime` and `<spec-clone>/uts/objects`, whether or not they are in scope (an unmapped module must resolve with `mapped: false`, not crash). For each, check:

- [ ] `ok: true`; tiers `present` match `ls <spec-clone>/uts/<module>`.
- [ ] Spec counts match the files on disk minus the exclusions. A cross-check: `find <spec-clone>/uts/<module>/<tier> -name '*.md' -not -path '*/helpers/*'` (add the proxy exclusion for the integration tier).
- [ ] No helper spec, `README.md`, `PLAN.md` or `*_SUMMARY.md` appears in `specs`.
- [ ] Every `className` follows D-04 and is collected by the runner; no collisions (or the collision is reported).
- [ ] `targetDir`, namespace and build target match the mapping and the Design record.
- [ ] The same module given as a `~`-prefixed path, and (on Windows) with backslash separators, resolves identically (guide [8.1](../../../docs/writing-uts-spec-translator-skills.md#81-resolver-resolve_utspy-must) "Validate the module").

Then run the negative cases and check each returns `ok: false` with the right code: a path whose parent isn't `uts`; a missing directory; a module with no tier directories (a scratch directory named `uts/<x>` will do); a mapping entry whose notes file is missing (use a scratch copy of the mapping); `--create` with an invalid name; `--create` on a scratch copy of a deliberately corrupt mapping (the file must be left unchanged).

## 8.2 Test the audit itself

Use one known-good test file (the pilot output from [8.3](#83-pilot-translate-one-spec-per-available-tier) once it is reviewed; until then, a hand-written file with the correct tags) and make scratch copies for each mutation. If you started with the hand-written file, run the mutations again once the pilot output passes review:

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

## 8.3 Pilot-translate one spec per available tier

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

- **Loading the skill.** A skill created during a session may not be listed until a new session starts. Ask the user to start a new session of the same tool (Claude Code or Codex) in the repo, on an Opus-class model ([2.8](../SKILL.md#28-model-tier-and-sub-agents)) (or to reload skills, if their client supports it), and confirm `/uts-to-<lang>` is listed (and, if D-01 links the skill for Codex, that `$uts-to-<lang>` is listed in a new Codex session). A fresh session also tests that the skill is context-complete on its own (guide intent), so the pilot never consults the reference implementations.
- **Answering its questions.** The answers are D-03 (mapping confirmation) and D-25 (tier, specs, mode), confirmed at STOP-8. Either the user runs `/uts-to-<lang> <spec-clone>/uts/<module>` (Claude Code) or `$uts-to-<lang> <spec-clone>/uts/<module>` (Codex) in the new session and answers with them, or, if the skill is listed in a session you control, you invoke it and answer with exactly those choices. If you use a subagent, run it on an Opus-class model ([2.8](../SKILL.md#28-model-tier-and-sub-agents)), and give it only the invocation and the D-25 answers, none of this run's context. It must not consult the reference implementations or any other SDK's skill, because the pilot tests the skill alone. Record the pilot session's or subagent's model with the pilot results. Any answer not covered by D-25 goes to the user.
- **Record each question the skill asked.** More than the four questions, other than a stop the guide requires (an unmapped module's name at step B, a known gap or red harness at step F, an unmapped construct, the fix-attempt bound), or a question it should have answered from its own files, is a skill defect ([8.4](#84-fix-the-cause-then-regenerate)).

**A green preflight comes first.** The skill's step F (after **STOP-6** for network tiers) must pass for the pilot's tier before the pilot translates anything; a pilot run on a red harness doesn't count. Record the preflight result with the pilot. If network access is declined, that tier's pilot isn't run and is reported as unvalidated.

Use translate-only mode if the SDK lacks the feature; otherwise evaluate. Then:

1. Compile (and collect: every tagged test function is collected; count a parameterised or protocol-variant test once).
2. Audit; walk the review checklist (guide [8.3](../../../docs/writing-uts-spec-translator-skills.md#83-review-checklist-must-after-the-audit)).
3. In evaluate mode, and after **STOP-6** for network tiers, run the class by filter and diagnose per `writing-derived-tests.md` Phase 2.
4. Review the generated file line by line against the spec yourself, and show it to the user.

## 8.4 Fix the cause, then regenerate

For every defect in a pilot test:

1. Classify it: a rule in `SKILL.md`, a mapping in the notes, a catalogue row, a resolver or audit bug, or a harness gap. (A UTS spec error is not a skill defect: record it, emit the fail-fast test per D-10, and **STOP-10**.)
2. Fix that cause. **Never edit only the generated test.** A harness fix follows the rules of [5.1](phase-3-build-harness.md#51-step-3a-rules-while-building), adds or extends a self-test that would have caught the defect, re-runs the affected tiers' smoke tests and self-tests, and updates the harness README (and its Known gaps).
3. Delete the generated test and regenerate it with the skill.
4. Re-audit, recompile and, in evaluate mode, re-run.
5. Log the defect and the fix in the Design record's changelog.

**Bound:** once a pilot spec has been regenerated three times (or the D-21 count) without a clean audit and, in evaluate mode, one of the three end states, stop (**STOP-10**) with a summary of every defect found and fixed so far. Count all regenerations of that spec together, not per defect.

## 8.5 Exercise the skill's other paths

Run each path through the skill (in the session from [8.3](#83-pilot-translate-one-spec-per-available-tier)) and record the result:

1. **Usage guard:** no argument → the usage line, then stop.
2. **Bad module path:** a path whose parent isn't `uts` → the resolver's error relayed, then stop.
3. **Placeholder notes:** a module whose notes file is a placeholder → refused, with the reason.
4. **Unready tier:** a tier the mapping marks unready → not offered at step C, with its `blockedBy`.
5. **Unmapped module:** on a scratch copy of the mapping, a module without an entry → step B asks for a name and runs `--create`, which writes the D-03 default layout and preserves the other entries.
6. **Re-sync** (if D-19 ships it): set a pilot file's header SHA to an older spec commit that changed that spec (`git -C <spec-clone> log --format=%H -- uts/<path>`), run `--resync`, and check the classification (including a change outside the pseudocode, such as `## Protocol Variants`, reported as **changed**, and, run against a scratch clone of the spec repo (`git clone <spec-clone> <scratch>`; the spec clone itself is never edited, 2.2), an uncommitted edit to that spec reported as **changed**), that the header SHA is updated, and that only the survivors in guide [9.2](../../../docs/writing-uts-spec-translator-skills.md#92-a-re-sync-mode-should) step 4 are preserved. Restore the file afterwards.
7. **Commands:** every build, run, lint and audit command `SKILL.md` names has now been run through the skill; fix any that failed.
8. **Red harness:** on a scratch copy (or a temporary working-tree edit you revert afterwards), break one harness test (for example, make the WebSocket mock refuse every connection), or run an integration tier with the network unavailable → the skill stops at step F before generating anything, reports a harness or environment problem (not an SDK deviation), and names the failing test. Restore the change and confirm the preflight is green again.
9. **Known gap:** select a spec that uses a construct the harness README lists under Known gaps → the preflight reports the conflict and stops to ask (guide 4 step F), rather than generating a substituted rendering. If Known gaps is empty, use a scratch copy of the README with an entry for a construct the selected spec uses.
10. **Second tool:** if D-01 links the skill for Codex, start a Codex session in the repo, invoke `$uts-to-<lang>` with no argument (usage line, then stop) and with one module (step A runs the resolver from the skill's directory, not from `.claude/skills/`). Record whether Codex was available; if it wasn't, report this path as not run.

## 8.6 Lint and CI-strict compile

Run the frontmatter validation of [7.6](phase-5-generate-skill.md#76-step-5f-write-skillmd). Run the repo's lint and format gates (P-06) over every file you created or changed, including the harness, the skill's scripts and Markdown where the repo's EditorConfig covers them. Compile the test targets as strictly as CI does (warnings as errors, static analysis, type checkers). Run the skill's scripts on every developer platform you can, or note which you couldn't.

## 8.7 Verify the skill's own examples

Every code example in `SKILL.md` and the notes must compile (guide [12](../../../docs/writing-uts-spec-translator-skills.md#12-lessons-learned)). For each example, either:

- name the real, compiled file it was copied from (and check it still matches), or
- paste it into a scratch file in the test target, compile, and delete the scratch file.

Record which examples were verified and how.

## 8.8 Name the reference tests

After review, name one spec-derived test file per tier in `SKILL.md` as the file to read first (guide [4, step 3](../../../docs/writing-uts-spec-translator-skills.md#phase-2-per-spec-steps-17)). Never name a smoke test.

**Phase 6 is done when:** the resolver passes on all three modules and all negative cases; every path in 8.5 behaves as expected (including the red-harness stop) and every command in `SKILL.md` has been run; every pilot ran after a green preflight; the audit passes every mutation and the sweep; each pilot compiles, audits clean (or every shortfall is accounted for) and, in evaluate mode, ends in one of the three end states; lint and the CI-strict compile pass; every example is verified.
