<!-- Copy to the working records as acceptance-checklist.md at the start of Phase 2 (Upgrade/Fix: pre-filled from the gap audit's section B). Update the rows each phase produces or verifies when it ends; in Phase 7, copy the completed file into final-report.md, "Acceptance checklist". One row per guide §13 item, in §13 order: don't add, drop, reorder or reword rows (check_acceptance.py matches them against this template). Evidence: a command and its result, file:line, or a record ID (G-nn, D-nn, decision log #n); "Verified in" only names where to look. Status: ✓ (a ✓ without evidence counts as open); "✓ static; behaviour at first translation" (the rule's file:line plus the checks named; for a row whose Verified in says "at first translation"); ✗ (reason: scoped out, planned, skipped or deferred at STOP-15, SDK-blocked); n/a (reason; skill section 13.8); or open. The "Steps 1–7 … a reference test per tier …" row: its reference-test part is "✗ (first translation pending)" until a reference test is named, so mark the row that way, with the evidence for the rest of it (which is "✓ static; behaviour at first translation"); once a reference test is named, the row is "✓ static; behaviour at first translation". -->

- Automated check (check_acceptance.py): <date>; <n> open rows, <n> unexplained fails | not run yet
- Independent verification: <verifier role → model>, <date>; agree <n>, disputed <n>, unresolved <n> | not independent: <why> | not run yet

| Guide §13 item | Produced in | Verified in | Evidence | Status |
|---|---|---|---|---|
| **UTS infra** | | | | |
| SDK test hooks (5), clock covering blocking waits and async-runtime timers, injected at construction; existing seams first; each new hook minimal, approved and needed by a spec | 4.6; 5.2 rows 3–4 | 5.2 acceptance; G-01…G-05; 4.6 seams and alternatives recorded | | |
| Shared test library per helper spec (incl. legacy `queue_*` and `mock_http.captured_requests`; `mock_websocket.md` async close, CONNECTED ordering, raw frames, alternative API and undocumented members; vcdiff; test pool; `MockNetworkListener`) | 4.3; 5.2 rows 5–6, 8, 11 | smoke tests; G-06…G-10 | | |
| Wait helpers (latched, fail-fast `AWAIT_STATE`; value-returning `poll_until`; `poll_until_success`; `process_pending_events`; wall-clock wrapper; fake-time-safe deadlines) | 4.4; 5.2 row 7 | helper tests; G-11 | | |
| Thread-safe capture, log sink, `assertContainsInOrder`, caller-attributed failures | 4.4; 5.2 row 2 | helper tests; G-12 | | |
| UTS infra designed from the repo's existing test setup (reuse, wrap, extend or build, 2.2); shared vs port-only placement; organised by tier (MUST; names SHOULD): proxy under integration, placement by use, names following folders; fixture-helper scope documented | 4.2; 4.7 (Placement table); 5.2 row 1; 5.3; notes item 9 | G-13; 5.2 layout check; inspector T-tier-layout | | |
| Infra README with a Known gaps section (MUST) | 5.3; 5.2 row 12 | G-14; 8.5 path 9 | | |
| Infra smoke tests per tier and helper self-tests: permanent, in CI, ungated, untagged, in a tree by tier, outside generated-test directories (MUST) | 4.7; 5.2 rows 1–11, 13 | STOP-7; G-19, G-20; 8.3 infra gate; 8.5 path 8 (✗ "SDK-blocked" while an objects smoke test is SDK-blocked, 12.5) | | |
| `SandboxApp` (idempotent retries only); `ably-common` | 4.5; 5.2 row 9 | smoke integration test; G-15 | | |
| `ProxyManager` (pinned, every OS, verified download, health check, port handling); `ProxySession`; string `match.action`; proxy auth decided and commented | 4.5; 5.2 row 10; D-18 | smoke proxy test; G-16 | | |
| One CI home per suite (MUST); per-tier jobs (SHOULD) | 5.2 row 13 or suggested CI changes | G-17; Final report | | |
| Concurrency, time, parallelism, visibility models documented | Phase 1 (P-09 to P-14) | STOP-2; G-18 | | |
| **Skill files** | | | | |
| `SKILL.md` frontmatter portable across Claude Code and Codex: `name` equal to the directory; pushy third-person description of at most 1,024 characters, no `<` or `>`, a "Not for" boundary; string-valued `metadata`; Claude Code-only fields only if accepted as non-portable | 7.6; D-22; D-26 | 7.6 acceptance; 8.6 | | |
| `SKILL.md`: usage guard that doesn't rely on `$ARGUMENTS` and never guesses a module (optional argument; a module question when none is named); own files referred to relative to the skill directory, in `SKILL.md` and the scripts; placeholder paths; 3.4 outline incl. the Infra reference | 7.6 | 7.6 acceptance; 8.5 paths 1 and 10; 8.9 (inspector) | | |
| Installed for both tools from one source (`.claude/skills/` and `.agents/skills/`, by in-repo symlink or a CI-checked copy) (SHOULD) | D-01; 7.1 | 8.3 dry run in a new session, where the skill is listed (a sub-agent reading it by path doesn't show this); 8.5 path 10 | | |
| `uts-package-mapping.json`: one path per tier, unique namespaces, `notes` relative, hand-maintained entries marked, `infra` entry (`root`, `readme`, `testsRoot`, `testCommand`); nothing the resolver can derive | 7.1; D-03 | 7.1 acceptance; 8.1 | | |
| `resolve_uts.py`: validation (incl. a clone root) and a module listing, errors, output contract, path tiers, relative exclusions, collectable names, mirrored sub-directories, collisions, validate-then-write `--create` preserving other entries, `infra` output derived from the mapping, older mapping shapes read with a warning | 7.2; D-04; D-05 | 8.1 | | |
| `audit_translation.py`: parsing contract, ID coverage, duplicates, separate counts, ignores commented assertions, never crashes, flags unverifiable; mutation-tested | 7.3 | 8.2 | | |
| Module notes for every diverging module; `objects` decided from evidence of the LiveObjects public API (full notes if exposed, even if incomplete; a placeholder, or an entry marked not ready as a whole, otherwise) | 7.5; D-23; 12.1–12.3; D-28 (decided at STOP-14) | 7.5 acceptance; 8.5 paths 3–4 | | |
| Scripts run on every developer platform (path handling, UTF-8, LF) | 7.1–7.3; D-02 | 8.1 (path parts, `~`), 8.6 (platforms) | | |
| **Workflow** | | | | |
| Required reading incl. features specs, from the same clone, synced first (SHOULD; D-32) | 7.6 (step 0) | 8.3 dry run (what step 0 read, recorded); 8.5 path 11 | | |
| Steps 0 and A–F: the four questions and the infra preflight (stop on red) | 7.6 | 8.3 dry run (green preflight); 8.5 paths 2–5, 8–9 | | |
| Steps 1–7 with batching; a reference test per tier; review in both modes | 7.6; 8.8 | 7.6 text; 8.9 (inspector `B-reference-tests`); verifier; at first translation: steps 1–7 run, and the reference test (`none yet`, 8.8) is proposed | | |
| Unmapped constructs stop and ask; corpus scanner in `scripts/` (SHOULD) | 7.4; 7.6; D-19 | 7.4 acceptance (scanner over every covered module, every hit accounted for); 8.5 path 6; at first translation: the stop | | |
| Re-sync mode; fix the cause, then regenerate | 7.6; D-19 | 8.5 path 6 (classification); 7.6 text; at first translation (the first real re-sync): regeneration | | |
| Mid-run infra changes re-run the smoke tests and self-tests and are reported separately | 7.6 (Infra reference) | 7.6 text; verifier; at first translation | | |
| **Translation rules in `SKILL.md`** | | | | |
| One verbatim `UTS: <id>` per test; no invented tags; spec point in a collectable name | 7.6; D-04, D-06 | 8.2 (the audit enforces it on every file) | | |
| File header: source spec, tier, spec SHA, disclosures, corresponding unit spec | 7.6; D-07 | 8.7 (the per-tier template compiles with its header); 8.5 path 6 (header read) | | |
| Verbatim comments, spec variable names, section headings, spec order | 7.6 | 7.6 text; verifier (guide §5); at first translation | | |
| Annotate, never drop, every `ASSERT`/`AWAIT`; never substitute a similar mock outcome | 7.6; 7.4 | 8.2 (shortfall mutations); 7.4 (no substitution rows) | | |
| Policies for sub-cases, groupers, test-case tables, delegating tests, ID-less tests | 7.6; D-13 | 7.6 text; D-13; verifier (guide §5); at first translation | | |
| Protocol variants parameterised; tag singular; proxy JSON only | 7.6; D-16 | 8.7 (template and catalogue row compile); verifier | | |
| Clients closed in teardown; mocks restored; stop on a failed wait | 7.6; D-15 | infra self-tests (teardown, waits); 8.7 renderings; verifier; at first translation: the translation side | | |
| Unique channel names; own proxy session per test | 7.6 | infra self-tests (proxy session per test); 8.7 renderings; verifier; at first translation: the translation side | | |
| Unit: fake time and flushes, no real timers. Integration: wall-clock | 7.6; 7.4; D-17 | infra self-tests (fake clock); 8.7 renderings; verifier; at first translation: the translation side | | |
| Record-and-verify for transient states; polls return the settled value | 7.6; 7.4 | infra self-tests (waits, polls); 8.7 renderings; verifier; at first translation: the translation side | | |
| No accommodate-both assertions; `IS <Type>` per typing discipline | 7.6 | 7.6 text; verifier (guide §5); at first translation | | |
| Public-API specs stay public; internal-access ladder with escalation stop | 7.6; 7.5 item 8; D-12 | 7.6 text; 7.5 item 8; D-12; verifier (guide §5); at first translation | | |
| Construct table filled for every row | 7.4 | 7.4 acceptance; 8.7 (every `mapped` rendering compiles); verifier (guide §6) | | |
| **Evaluation** | | | | |
| Three end states; runtime skip and fail-fast idioms; `RUN_DEVIATIONS` command | 7.6; D-09, D-10 | 8.7 (the skip and fail-fast idioms compile); 7.6 text; verifier; at first translation | | |
| `deviations.md` location; format deferred; written at the right time | 7.6; D-08 | 7.6 text; D-08; verifier; at first translation | | |
| Infra stand-ins in comments, not `deviations.md` | 7.4; 7.6 | 7.4 `stand-in` rows; 7.6 text; verifier; at first translation | | |
| Language-inapplicable inputs (cases a–c) noted in the test file | 7.6; D-11 | 7.6 text; D-11; verifier; at first translation | | |
| Stopping rules and spec-error escalation | 7.6; D-21 | 7.6 text; D-21; verifier; at first translation | | |
| **Verification** | | | | |
| Compile (or collect), lint, CI-strict compile, filtered run | 7.6 | 8.6; 8.7; 8.5 path 7 (the filter syntax on an infra class); at first translation: the generated-class run | | |
| No commits by default; changed files listed | 7.6; D-20 | Phase 7 | | |
| Final report format | 7.6 | 7.6 text; verifier (guide §11); at first translation | | |
| The skill's own examples compile | 7.5 item 12; 7.6 | 8.7 | | |
| **Creation process** | | | | |
| Skill and UTS infra created on an Opus-class model (MUST); model stated for runs, or pinned where the tool supports that (SHOULD), and recorded in the skill's final report | 2.8; D-26; 7.6 (frontmatter, final report) | Design record "Inputs at generation time" (Model line, with the dry-run and verifier sub-agents' models); Final report header | | |
| Reference-implementation reads, if any, last resort only, recorded and reported as guide gaps | 2.1; design-record template | Final report "Reference-implementation reads" | | |
| An existing skill, its UTS infra and its UTS-derived tests audited against this checklist before being changed; gaps listed for the owner to choose; working parts preserved (SHOULD) | 13 (Orient); 10; 11.2–11.5; D-27; D-29; skill-gap-audit template | STOP-15; 11.6; Final report "Existing assets and upgrade summary" (n/a in create mode) | | |
