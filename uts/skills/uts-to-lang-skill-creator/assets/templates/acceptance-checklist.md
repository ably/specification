<!-- Paste this table into the Final report's "Acceptance checklist" section. One row per item of the guide's section 13 checklist (uts/docs/writing-uts-spec-translator-skills.md), with where the procedure produces and verifies it. Mark each ✓, ✗ (with the reason) or n/a (with the reason). A row that wholly needs a capability the SDK lacks is "n/a — capability absent: <capability> (D-31)"; a row where only parts do is ✓ with those parts named n/a. n/a never counts as ✗; a scope the user chose to cut is ✗. -->

| Guide §13 item | Produced in | Verified in | Status |
|---|---|---|---|
| **Harness** | | | |
| SDK test hooks (5), clock covering blocking waits and async-runtime timers, injected at construction | 4.6; 5.2 rows 3–4 | 5.2 acceptance; G-01…G-05 | |
| Shared test library per helper spec (incl. legacy `queue_*` and `mock_http.captured_requests`; `mock_websocket.md` async close, CONNECTED ordering, raw frames, alternative API and undocumented members; vcdiff; test pool; `MockNetworkListener`) | 4.3; 5.2 rows 5–6, 8, 11 | smoke tests; G-06…G-10 | |
| Wait helpers (latched, fail-fast `AWAIT_STATE`; value-returning `poll_until`; `poll_until_success`; `process_pending_events`; wall-clock wrapper; fake-time-safe deadlines) | 4.4; 5.2 row 7 | helper tests; G-11 | |
| Thread-safe capture, log sink, `assertContainsInOrder`, caller-attributed failures | 4.4; 5.2 row 2 | helper tests; G-12 | |
| Harness designed from the repo's existing test setup (reuse, wrap, extend or build, 2.2); shared vs port-only placement; recommended harness layout; fixture-helper scope documented | 4.2; 4.7; 5.3; notes item 9 | G-13 | |
| Harness README with a Known gaps section (MUST) | 5.3; 5.2 row 12 | G-14; 8.5 path 9 | |
| Harness smoke tests per tier and helper self-tests: permanent, in CI, ungated, untagged, outside generated-test directories (MUST) | 4.7; 5.2 rows 1–11, 13 | STOP-7; G-19, G-20; 8.5 path 8 (✗ "SDK-blocked" while an objects smoke test is SDK-blocked, 12.5) | |
| `SandboxApp` (idempotent retries only); `ably-common` | 4.5; 5.2 row 9 | smoke integration test; G-15 | |
| `ProxyManager` (pinned, every OS, verified download, health check, port handling); `ProxySession`; string `match.action`; proxy auth decided and commented | 4.5; 5.2 row 10; D-18 | smoke proxy test; G-16 | |
| One CI home per suite (MUST); per-tier jobs (SHOULD) | 5.2 row 13 or suggested CI changes | G-17; Final report | |
| Concurrency, time, parallelism, visibility models documented | Phase 1 (P-09 to P-14) | STOP-2; G-18 | |
| **Skill files** | | | |
| `SKILL.md` frontmatter portable across Claude Code and Codex: `name` equal to the directory; pushy third-person description of at most 1,024 characters, no `<` or `>`, a "Not for" boundary; string-valued `metadata`; Claude Code-only fields only if accepted as non-portable | 7.6; D-22; D-26 | 7.6 acceptance; 8.6 | |
| `SKILL.md`: usage guard that doesn't rely on `$ARGUMENTS`; own files referred to relative to the skill directory, in `SKILL.md` and the scripts; placeholder paths; 3.4 outline incl. the Harness reference | 7.6 | 7.6 acceptance; 8.3; 8.5 paths 1 and 10 | |
| Installed for both tools from one source (`.claude/skills/` and `.agents/skills/`, by in-repo symlink or a CI-checked copy) (SHOULD) | D-01; 7.1 | 8.3; 8.5 path 10 | |
| `uts-package-mapping.json`: one path per tier, unique namespaces, `notes` relative, hand-maintained entries marked, `harness` entry | 7.1 | 7.1 acceptance; 8.1 | |
| `resolve_uts.py`: validation, errors, output contract, path tiers, relative exclusions, collectable names, collisions, validate-then-write `--create` preserving other entries, `harness` output | 7.2 | 8.1 | |
| `audit_translation.py`: parsing contract, ID coverage, duplicates, separate counts, ignores commented assertions, never crashes, flags unverifiable; mutation-tested | 7.3 | 8.2 | |
| Module notes for every diverging module; `objects` decided from evidence of the LiveObjects public API (full notes if exposed, even if incomplete; a placeholder or an entry with every tier marked not ready otherwise) | 7.5; D-23; 12.1–12.3; D-28 (decided at STOP-14) | 7.5 acceptance; 8.5 paths 3–4 | |
| Scripts run on every developer platform (path handling, UTF-8, LF) | 7.1–7.3; D-02 | 8.1 (path parts, `~`), 8.6 (platforms) | |
| **Workflow** | | | |
| Required reading incl. features specs, from the same clone | 7.6 (step 0) | 8.3 pilot | |
| Steps 0 and A–F: the four questions and the harness preflight (stop on red) | 7.6 | 8.3 pilot (green preflight first); 8.5 paths 8–9 | |
| Steps 1–7 with batching; a reference test per tier; review in both modes | 7.6; 8.8 | 8.3 pilot; 8.8 | |
| Unmapped constructs stop and ask; corpus scanner in `scripts/` (SHOULD) | 7.4; 7.6; D-19 | 8.3 pilot; 8.5 (re-sync) | |
| Re-sync mode; fix the cause, then regenerate | 7.6; D-19 | 8.5 (re-sync); 8.4 (fix and regenerate) | |
| Mid-run harness changes re-run the smoke tests and self-tests and are reported separately | 7.6 (Harness reference) | 8.4 step 2; final report | |
| **Translation rules in `SKILL.md`** | | | |
| One verbatim `UTS: <id>` per test; no invented tags; spec point in a collectable name | 7.6; D-04, D-06 | 8.2, 8.3 | |
| File header: source spec, tier, spec SHA, disclosures, corresponding unit spec | 7.6; D-07 | 8.3 | |
| Verbatim comments, spec variable names, section headings, spec order | 7.6 | 8.3 review | |
| Annotate, never drop, every `ASSERT`/`AWAIT`; never substitute a similar mock outcome | 7.6; 7.4 | 8.3 audit | |
| Policies for sub-cases, groupers, test-case tables, delegating tests, ID-less tests | 7.6; D-13 | 8.3 (where the pilot has them) | |
| Protocol variants parameterised; tag singular; proxy JSON only | 7.6; D-16 | 8.3 integration pilot | |
| Clients closed in teardown; mocks restored; stop on a failed wait | 7.6; D-15 | 8.3 | |
| Unique channel names; own proxy session per test | 7.6 | 8.3 integration/proxy pilots | |
| Unit: fake time and flushes, no real timers. Integration: wall-clock | 7.6; 7.4; D-17 | 8.3 | |
| Record-and-verify for transient states; polls return the settled value | 7.6; 7.4 | 8.3 | |
| No accommodate-both assertions; `IS <Type>` per typing discipline | 7.6 | 8.3 review | |
| Public-API specs stay public; internal-access ladder with escalation stop | 7.6; 7.5 item 8; D-12 | 8.3 | |
| Construct table filled for every row | 7.4 | 7.4 acceptance | |
| **Evaluation** | | | |
| Three end states; runtime skip and fail-fast idioms; `RUN_DEVIATIONS` command | 7.6; D-09, D-10 | 8.3 (evaluate) | |
| `deviations.md` location; format deferred; written at the right time | 7.6; D-08 | 8.3 (evaluate) | |
| Harness stand-ins in comments, not `deviations.md` | 7.4; 7.6 | 8.3 review | |
| Language-inapplicable inputs (cases a–c) noted in the test file | 7.6; D-11 | 8.3 (where they occur) | |
| Stopping rules and spec-error escalation | 7.6; D-21 | 8.4 | |
| **Verification** | | | |
| Compile (or collect), lint, CI-strict compile, filtered run | 7.6 | 8.3, 8.6 | |
| No commits by default; changed files listed | 7.6; D-20 | Phase 7 | |
| Final report format | 7.6 | 8.3 (the skill's report) | |
| The skill's own examples compile | 7.5 item 12; 7.6 | 8.7 | |
| **Creation process** | | | |
| Skill and harness created on an Opus-class model (MUST); model stated for runs, or pinned where the tool supports that (SHOULD), and recorded in the skill's final report | 2.8; D-26; 7.6 (frontmatter, final report) | Design record "Inputs at generation time" (Model line); 8.3 (pilot model recorded); Final report header | |
| Reference-implementation reads, if any, last resort only, recorded and reported as guide gaps | 2.1; design-record template | Final report "Reference-implementation reads" | |
| An existing skill, its harness and its UTS-derived tests audited against this checklist before being changed; gaps listed for the owner to choose; working parts preserved (SHOULD) | 13 (Orient); 10; 11.2–11.5; D-27; D-29; skill-gap-audit template | STOP-15; 11.6; Final report "Existing assets and upgrade summary" (n/a in create mode) | |
