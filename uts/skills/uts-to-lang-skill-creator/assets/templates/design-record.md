# Design record: uts-to-<lang>

## Inputs at generation time
- Spec clone: <shared|env|explicit|skill-clone> <path>; <sha> on <branch|detached> (clean | dirty: <files>); on origin/main: <yes|no>; sync: <fast-forwarded <old8>..<new8> | up to date | not updated: <reason>, behind <n> as of last fetch | not synced (not the shared clone)>; guide/skill: <sha of last change>; uts-to-lang-skill-creator version <metadata.version>
- Repo: <sha>
- Repo profile confirmed: <date>; harness option at STOP-3: (a | b | c); harness confirmed: <date>
- Harness README: <full repo path>
- Model: <name and ID> (Opus-class: yes | no, departure in decision log #<n>); sub-agents: <role → model>, or none
- Eligibility: <owner/repo> via <remote> (accept | fork-confirmed) | user-named: <owner/repo> (<code>)
- Capabilities (D-31): rest <full|partial|absent>; realtime <full|partial|absent|unclear> (<sub-areas>); liveobjects <yes|no>; side: <none | core | server | device | both> (<clients it reaches>); scope: <full|rest-only|realtime-only> (<modules>[ + <n> REST-only tests under realtime]); unsupported: <modules> (<reason>); capability-inapplicable: <n> tests (listed in the <module> notes); names: <spec | fallback>
- State class (Orient): S0 | S1 | S2 | S3 | S4 (+ re-entry) — <reasons>; run mode (D-27): create | upgrade: diff-driven | upgrade: full audit | upgrade: regenerate (resumed | restarted <date>); target skill: <path> (origin …), or none
- Run status: in progress (Phase <n>, <date>) | finished (<date>)
  - After a context compaction: read the skill creator's whole SKILL.md again, then this line, then the current phase's reference, before your next action.
  - Finished only at the completion gate: the acceptance checklist has no open row, check_acceptance.py --final has no unexplained fail, the independent verification has no unresolved dispute, and the harness tests are green in CI at every supported tier (or the Final report says why not).
- LiveObjects evidence: detect_liveobjects.py → <yes | no | unclear>, <confidence>; decision at STOP-14 (D-28)

## Decisions
| ID | Decision | Choice | Guide-default? | Decided by | Rationale |
|---|---|---|---|---|---|
| D-01 | Skill name and location | | yes / no | user / agent / existing skill | |
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
| D-23 | Notes files per module (full / placeholder; objects per D-28) | | | | |
| D-24 | Working-records location | | | | |
| D-25 | Retired (no pilots): not used | — | — | — | — |
| D-26 | Model tier and pinning for skill runs | | | | |
| D-27 | Run mode and state class (STOP-13) | | | | |
| D-28 | LiveObjects support: full / placeholder / none; translate-only / evaluate; SDK-blocked tiers and evidence, if any (STOP-14, 12.5) | | | | |
| D-29 | Gap-audit choices: add / skip / defer per GA- or CH- item; preserve list (STOP-15; n/a in create mode) | | | | |
| D-30 | Provenance stamp (metadata.generated-by, metadata.records) and Run status | | | | |
| D-31 | Capability profile, skill scope and side: the UTS infrastructure plan (STOP-13 or STOP-17; side re-confirmed at STOP-3) | | | | |
| D-32 | Spec-clone sync in the generated skill (ensure_spec_clone.py copied; ABLY_SPEC_SYNC) | | | | |

### D-03 mapping
| Module | unit | integration | proxy | notes | readiness and scope markers (unready, unsupported, extraTests, capabilityInapplicable, translateOnly) | hand-maintained? |
|---|---|---|---|---|---|---|

- harness: root <dir>; readme <path>; testsRoot <dir>; testCommand <command with {tier}>
- Values the build can't give (each with why): <key → value: reason | none>
- Derived by the resolver, not stored: test project, namespace root, each tier's helper sources (tier layout), per-spec targetDir and testFile (sub-directories mirrored)

## Phase timings
| Phase | Started (date, time) | Ended (date, time) | Stop waits (STOP-n: asked → answered) | Sub-agents (role → model; task; files written) |
|---|---|---|---|---|

## Decision log
| # | Date and time | Phase | Question | Options | Answer | By | Supersedes |
|---|---|---|---|---|---|---|---|

## Reference-implementation reads (last resort, 2.1)
| # | Date | Question | Guide/UTS sections searched | Repo @ revision : path | Pattern learned (not copied) | Checked against Patterns to avoid | Access (local clone / GitHub, STOP-6 approval) |
|---|---|---|---|---|---|---|---|

## Changelog (fixes made to the skill, notes or harness)
| # | Date | Found by | Cause (skill / notes / catalogue / script / harness) | Fix | Closes (GA-nn / CH-nn / G-nn, if any) | Tests regenerated |
|---|---|---|---|---|---|---|
