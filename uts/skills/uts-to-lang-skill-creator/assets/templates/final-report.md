# Final report: uts-to-<lang> for <repo>

- Spec clone <sha> (clean | dirty: <files>); repo <sha>; date
- Model: <name and ID> (Opus-class: yes | no, and why); sub-agents: <role → model>, or none
- Scope: <modules × tiers covered>; out of scope and why
- Conforms to the guide: yes | no (MUST rows ✗: …)
- Eligibility: <owner/repo> via <remote> (accept | fork-confirmed) | user-named: <owner/repo> (<code>)
- Capabilities (D-31): rest …; realtime …; side: <none | core | server | device | both>; scope: <modules>; unsupported: … (capability absent); capability-inapplicable: <n> tests; partial skill: yes, extend by Upgrade/Fix when <capability> appears | no
- State class: S0 | S1 | S2 | S3 | S4 (+ re-entry); run mode: create | upgrade: diff-driven | upgrade: full audit | upgrade: regenerate (resumed | restarted); LiveObjects: full | placeholder | none (translate-only | evaluate), from detector recommendation <yes | no | unclear>

## Files created or changed
| Path | New / changed | Kind (hook, harness, smoke test, skill, script, notes, pilot test, CI suggestion) | Item (GA-nn / CH-nn / G-nn, upgrade mode) | Approved at |
|---|---|---|---|---|
Hand-maintained project files the user must update: …

## Existing assets and upgrade summary
Create (S1): the UTS-derived tests and harness code found (P-20), whether they match D-03, D-06 and D-07, and the follow-ups proposed.
Upgrade/Fix: items added, skipped (with the reason) and deferred (with the plan), by GA-/CH-/G- ID, from skill-gap-audit.md; harness rows decided at STOP-3; preserve list kept; baseline comparison (resolver, audit, harness tests, existing UTS-derived tests): differences and the item that explains each; what the old skill had that the new one lacks (regenerate only).

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

## SDK-blocked objects tiers
<tier>: <feature> — <evidence (error naming the SDK symbol, file:line)>; translate-only until the smoke test passes; acceptance row "Harness smoke tests …" ✗ (SDK-blocked). "None" otherwise.

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
Which modules and tiers to translate next, in order, and why; harness work remaining; deferred gap-audit items with their plan.

## Acceptance checklist
(the acceptance-checklist template, filled)
