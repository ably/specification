# Gap audit: uts-to-<lang> in <repo name>

- Existing skill: <path> (installs: <.claude/skills/…, .agents/skills/… (symlink | copy)>); frontmatter version <metadata.version or none>
- Repo <sha> (clean | dirty: <files>)
- Spec clone: <shared|env|explicit|skill-clone> <path>; <sha> on <branch|detached> (clean | dirty: <files>); on origin/main: <yes|no>; sync: <fast-forwarded <old8>..<new8> | up to date | not updated: <reason>, behind <n> as of last fetch | not synced (not the shared clone)>
- State class (Orient): S2 | S3 | S4; mode at STOP-13: upgrade: diff-driven | upgrade: full audit | upgrade: regenerate — chosen by <user> on <date>
- inspect_existing_skill.py run: <date>; its checks are regex hints, every row below is confirmed by reading
- Capabilities: recorded D-31 <line or none> vs Orient now <profile; side>; delta: <none | capability added | side changed>

## A. Inventory
| Part | What exists (path, symbol, command → result) | Baseline result (resolver, audit, infra tests, compile) |
|---|---|---|
| SKILL.md (lines, headings, frontmatter fields) | | |
| uts-package-mapping.json (modules, tiers, notes, infra entry (or the former key `harness`) and its shape: `{root, readme, testsRoot, testCommand}` or older per-tier lists, unready data, `unsupported` / `capabilityInapplicable` / `extraTests` markers; keys the resolver could derive, e.g. file lists, a test project, a white-box list, dummy tier paths) | | |
| scripts/ (resolver, audit, scanner, others) | | |
| references/ (notes per module; placeholders) | | |
| UTS infra (root, README, Known gaps, smoke tests, self-tests, CI jobs) | | |
| UTS-derived tests (see D) | | |
| Working records | | |

## B. Conformance
One row per guide §13 item outside the UTS infra group, in §13 order (one per acceptance-checklist row). A row (or part of one) needing a capability the SDK lacks is "n/a — capability absent: <capability> (D-31)"; one that was n/a when recorded and whose capability now exists is "missing (newly applicable)". Each row and each section-D follow-up gets an ID (GA-01, GA-02, …) used by the decision, the changelog and the Final report. Status: conforms / partial / missing / non-conforming / n/a (reason) / unverified (checked in <step>). Choice at STOP-15: add / skip / defer (a skipped or deferred MUST row leaves the skill not conforming). The objects half of the module-notes row comes from D-28; Creation-process rows for a skill of unknown origin: "origin unknown; this run meets it for the artifacts it changes".

| # | Acceptance-checklist item | Level | Status | Evidence | Proposed change | Step | Size | Approval needed | Choice | Re-confirmed (STOP-8 or after Phase 6) |
|---|---|---|---|---|---|---|---|---|---|---|
| GA-01 | | MUST / SHOULD | | | | | | | | |

## C. UTS infra
Decided per row at STOP-3, not here; G-19/G-20 for offered tiers can't be skipped or deferred.

| Row | Capability | Quick status | Evidence | Note for Phase 2 |
|---|---|---|---|---|
| G-01 … G-20 | (from the uts-infra-design template) | | | |

G-13 restructure by tier (when the UTS infra isn't organised by tier; MUST): move list, each file from → to with its namespace or package change and any split by tier (e.g. a file mixing unit factories and every-tier waits); size; infra tests run green before and after; moving with no logic change keeps the preserve list's behaviour (not a rewrite); UTS-derived tests that reference the old namespace become regenerate candidates.

| From | To | Namespace or package change | Split? | Notes |
|---|---|---|---|---|

## D. UTS-derived tests
| # | Module × tier (or "outside mapped tiers") | Files | Tags | Tag style | Header SHAs (vs clone HEAD) | No SHA / links main | deviations.md and other deviation records | Compile | Audit | Follow-up proposed | Choice |
|---|---|---|---|---|---|---|---|---|---|---|---|

Lessons carried into the skill (the tests are evidence, not a constraint): <lesson from a deviation, a hand-patched or failing test, or an adapted assertion> → <the rule, note or infra row that now carries it>; "none" otherwise.

## E. LiveObjects (decided at STOP-14)
detect_liveobjects.py → <yes | no | unclear>, <confidence>; decision D-28: full | placeholder | none, translate-only | evaluate; SDK-blocked tiers (12.5): … ; objects items implied: …

## F. Preserve list
| What is kept as is | Where | Why it conforms |
|---|---|---|

## G. Decision at STOP-15
Chosen by <user> on <date>: add …; skip …; defer … (GA- and CH- items); or regenerate from scratch instead. Recorded as D-29.

## H. Changes since the recorded run (diff-driven Upgrade/Fix, section 10)
| # | What changed (guide / UTS docs / helper specs / corpus / UTS infra / SDK) | Evidence (diff paths) | Artifacts to update | Tests to regenerate | Choice |
|---|---|---|---|---|---|
| CH-01 | | | | | add / skip / defer |
