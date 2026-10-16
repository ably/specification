# Parallel work: optional sub-agents

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention). Links that climb out of the skill directory are spec-repo paths: resolve them against the spec clone, not against this file's installed location.

Some of the procedure's work is independent and read-only. Where your tool supports sub-agents (Claude Code's Agent tool, and others where available), you can hand that work to them to cut the run's wall-clock time. Sub-agents are **optional, never required**: the procedure works end to end in one agent, and a run with sub-agents follows the same stop points and produces the same records as one without.

## Rules

- **You own** every stop point, the working records and the decision log. A sub-agent never asks the user anything and never crosses a stop point; one that needs a decision returns it as an open question, and you ask it.
- **Read-only by default.** A sub-agent writes only to the files assigned to it, disjoint from every other sub-agent's, or in its own worktree. You integrate its work and re-run the checks yourself.
- **Serialise** builds, test runs, and anything that touches the network or shared state: the SDK's build output and locks are shared (`obj/` and `bin/`, `.build`, Gradle). STOP-6 still applies to every network or full-suite run.
- **Each sub-agent gets** a pointer to `SKILL.md` section 2 (the ground rules), its exact task, the files it may read and write, and the output format: findings with file:line evidence, then open questions. Spot-check its claims before you record them.
- **Model:** Opus-class, recorded with its role in the Design record and the Final report ([2.8](../SKILL.md#28-model-tier-and-sub-agents)).
- **Cost:** more tokens in total. Use sub-agents only where the work is independent and large enough to save time. A side benefit: they return summaries, not file dumps, so your own context stays smaller and compacts less often.

## Where it helps

| Phase | Split? | How |
|---|---|---|
| 1b and 1c: the discovery checklist and the existing tests ([3.2](phase-1-understand-repo.md#32-step-1b-answer-the-discovery-checklist), [3.3](phase-1-understand-repo.md#33-step-1c-study-how-the-existing-tests-drive-the-sdk)) | **Yes**: read-only and independent | One sub-agent per group of discovery items: (a) build, CI and the runner (P-01 to P-08, P-12); (b) the async, concurrency and time models, SDK hooks, internal access and the API surface (P-09 to P-11, P-13 to P-15); (c) existing mocks, helpers and test support (P-16, P-17, step 1c); (d) sandbox, `ably-common` and network access (P-18, P-19, P-21); (e) existing UTS assets and skills (P-20). You merge them into the Repo profile and own STOP-2 |
| U1 and U2: the gap audit (Upgrade/Fix, [11.2](upgrade-existing-skill.md#112-step-u1-understand-the-existing-skill)) | **Yes**: read-only | One sub-agent per audit section or group of checklist rows (the skill, the UTS infra, the derived tests, the records). You merge, de-duplicate and own STOP-15. The baseline's test runs stay serial |
| 2: design the UTS infra | Mostly no | The design is one connected decision. A sub-agent may draft one tier's rows, but you own the design and STOP-3 |
| 3: build the UTS infra ([5.1](phase-3-build-infra.md#51-step-3a-rules-while-building)) | **Limited** | Each STOP-4 hook and the shared helpers are sequential. Self-tests for doubles already built, or tiers with disjoint new files, may be drafted in parallel, in disjoint files or separate worktrees. You integrate. Builds and test runs stay serial |
| 5: generate the skill ([7.4](phase-5-generate-skill.md#74-step-5d-fill-the-construct-catalogue), [7.5](phase-5-generate-skill.md#75-step-5e-write-the-module-notes)) | **Partly** | After STOP-8: the module notes, one per module, and the construct-catalogue sections in parallel. The layout, mapping, resolver and audit (7.1 to 7.3) stay sequential |
| 6: validate ([8.1](phase-6-validate-skill.md#81-run-the-resolver-on-every-module), [8.3](phase-6-validate-skill.md#83-infra-gate-and-selection-dry-run), [8.5](phase-6-validate-skill.md#85-exercise-the-skills-other-paths), [8.7](phase-6-validate-skill.md#87-verify-the-skills-own-code)) | **Yes** | Preparing the selection dry run per module and tier, each sub-agent given only the invocation and the answers (8.3); their step F preflights compile and run the infra tests, so they run one at a time; the resolver per module (8.1); checking the examples, templates and catalogue renderings (8.7); the other paths (8.5). A sub-agent doesn't show that the skill is *listed* in a new session: that needs a real new session, or 8.5 path 10. Test runs stay serial, and network tiers still need STOP-6 |
| 7: verify ([9](../SKILL.md#9-phase-7-final-report-and-handover)) | **Yes** | The independent acceptance-checklist verifier is a sub-agent by design: one that built nothing in this run |

## Measure first

Record each phase's start and end time, and each stop point's wait (asked, then answered), in the Design record's "Phase timings", with every sub-agent's role, model, task and the files it wrote. The Final report's "Run timings" gives the phase durations, so the next run can see where the time goes and judge whether a split helps.
