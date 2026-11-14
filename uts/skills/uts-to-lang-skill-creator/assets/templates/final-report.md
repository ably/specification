# Final report: uts-to-<lang> for <repo>

- Spec clone: <shared|env|explicit|skill-clone> <path>; <sha> on <branch|detached> (clean | dirty: <files>); on origin/main: <yes|no>; sync: <fast-forwarded <old8>..<new8> | up to date | not updated: <reason>, behind <n> as of last fetch | not synced (not the shared clone)>; repo <sha>; date
- Spec SHA not on origin/main (a branch run): <none | sha: the stamp and any test headers that carry it may stop resolving once that branch is deleted>
- Model: <name and ID> (Opus-class: yes | no, and why); sub-agents: <role → model>, or none
- Scope: <modules × tiers covered>; out of scope and why
- Conforms to the guide: yes | no (MUST rows ✗: …)
- Eligibility: <owner/repo> via <remote> (accept | fork-confirmed) | user-named: <owner/repo> (<code>)
- Capabilities (D-31): rest …; realtime …; side: <none | core | server | device | both>; scope: <modules>; unsupported: … (capability absent); capability-inapplicable: <n> tests; partial skill: yes, extend by Upgrade/Fix when <capability> appears | no
- State class: S0 | S1 | S2 | S3 | S4 (+ re-entry); run mode: create | upgrade: diff-driven | upgrade: full audit | upgrade: regenerate (resumed | restarted); LiveObjects: full | placeholder | none (translate-only | evaluate), from detector recommendation <yes | no | unclear>

## Files created or changed
| Path | New / changed | Kind (hook, UTS infra, smoke test, skill, script, notes, CI suggestion) | Item (GA-nn / CH-nn / G-nn, Upgrade/Fix) | Approved at |
|---|---|---|---|---|
Hand-maintained project files the user must update: …

## Existing assets and upgrade summary
Create (S1): the UTS-derived tests and infra code found (P-20), whether they match D-03, D-06 and D-07, and the follow-ups proposed.
Upgrade/Fix: items added, skipped (with the reason) and deferred (with the plan), by GA-/CH-/G- ID, from skill-gap-audit.md; infra rows decided at STOP-3; preserve list kept; baseline comparison (resolver, audit, infra tests): differences and the item that explains each; derived tests made stale, and whether they were regenerated; what the old skill had that the new one lacks (regenerate only).

## Repo profile
Link to repo-profile.md; corrections made at STOP-2.

## UTS infra
Gap table status after this run (rows reused, wrapped, extended, built, planned, open); option chosen at STOP-3; hooks added (with approvals); smoke-test and self-test results per tier, and their CI jobs; the infra gate and dry-run preflight results per tier; infra changes made during Phase 6 (with the self-tests added); the README's Known gaps; the plan for any remaining rows. Link to uts-infra-design.md and the infra README.

## SDK production changes
| Production file | Change (lines) | Hook | Approved at (STOP-4, decision #) |
|---|---|---|---|
The production diffstat from the build log, matched against each approved proposal's file list. "None" if the run changed no SDK source.

## Design decisions
Link to design-record.md; decisions that depart from the guide's defaults, and why.

## Validation results
- Resolver: rest / realtime / objects → ok, spec counts; negative cases → codes
- Audit self-test: each mutation → result; corpus sweep → N specs, 0 crashes, unverifiable specs listed
- Lint: …; CI-strict compile: …; examples, per-tier templates and catalogue renderings verified: N of N (how; scratch files deleted)
- Infra gate per tier: <command → green | SDK-blocked (12.5) | unvalidated: network declined>
- Other paths (8.5): each path → result, or not run and why
- Automated check (check_acceptance.py --final): <its summary: rows per status, unexplained fails, missing records>
- Independent verification: <verifier → model>; agree <n>, disputed <n> (each dispute and how it was resolved) | not independent: <why>
- Fixes made to the skill, notes or UTS infra during Phase 6 (from the changelog): …

## Selection dry runs
| Module × tier | Model (session or sub-agent) | Questions asked | Step 0 read | Preflight |
|---|---|---|---|---|
Reference tests named in SKILL.md: none yet (the skill proposes one after a tier's first reviewed translation).

## Verified at the first real translation
The acceptance-checklist rows marked "✓ static; behaviour at first translation", each with its static evidence. These checks show the skill conforms to the guide; they can't show its translations come out right. That shows at the first real translation run, and the fix-the-cause, regenerate and re-sync cycle handles it there.

## SDK-blocked objects tiers
<tier>: <feature> — <evidence (error naming the SDK symbol, file:line)>; translate-only until the smoke test passes; acceptance row "Infra smoke tests …" ✗ (SDK-blocked). "None" otherwise.

## Known limitations
Tiers not ready; `not available` catalogue rows; infra capabilities missing; audit SHOULD items not implemented; platforms the scripts weren't run on.

## Deviations and spec issues found
- SDK deviations (recorded in deviations.md): …
- Suspected UTS spec errors or gaps: <id> — <one line>; draft fix: …
- Spec-repo doc issues (contradictions between guide and UTS docs; guide gaps revealed by reference-implementation reads): …

## Native test findings (not fixed)
The SDK's own tests are out of scope: they are reported, never fixed, skipped or rewritten.
- Failing or flaky native tests: <test> — <evidence: before/after results, passes alone, repeat runs>
- SDK bugs found while building: <symptom> — <evidence (file:line, test or log)>
"None" otherwise.

## Reference-implementation reads
Each read from the Design record (question, repo @ revision : path, pattern learned, how it was checked against Patterns to avoid), with the guide gap it reveals and a draft guide fix. "None" if the guide sufficed.

## Suggested CI changes
<job, trigger, command, network/submodule/proxy needs> (not applied unless approved at STOP-5)

## Next steps
Run the skill on one module per tier first (no spec-derived test exists yet), and review the result against "Verified at the first real translation"; then which modules and tiers to translate next, in order, and why; infra work remaining; deferred gap-audit items with their plan.

## Run timings
| Phase | Start | End | Duration | Waiting at stop points | Sub-agents (role → model) |
|---|---|---|---|---|---|
From the Design record's Phase timings. Totals: the run, the time waiting for answers, and the time the sub-agents saved, if any.

## Upgrade/Fix runs (dated)
One entry per diff-driven run (section 10): date; the changes detected (CH- items); the artifacts updated; the checks re-run; the acceptance-checklist rows re-marked. "None" otherwise.

## Acceptance checklist
(the working records' acceptance-checklist.md, completed: its two result lines and its table, with the Evidence column)
