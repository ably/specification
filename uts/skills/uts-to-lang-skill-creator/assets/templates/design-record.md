# Design record: uts-to-<lang>

## Inputs at generation time
- Spec clone: <sha> (clean | dirty: <files>); guide/skill: <sha of last change>; uts-to-lang-skill-creator version <metadata.version>
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
