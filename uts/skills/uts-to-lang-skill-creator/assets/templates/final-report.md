# Final report: uts-to-<lang> for <repo>

- Spec clone <sha> (clean | dirty: <files>); repo <sha>; date
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
Each read from the Design record (question, repo @ revision : path, pattern learned, how it was checked against Patterns to avoid), with the guide gap it reveals and a draft guide fix. "None" if the guide sufficed.

## Suggested CI changes
<job, trigger, command, network/submodule/proxy needs> (not applied unless approved at STOP-5)

## Next steps
Which modules and tiers to translate next, in order, and why; harness work remaining.

## Acceptance checklist
(the acceptance-checklist template, filled)
