# 10. Maintenance

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention). Links that climb out of the skill directory are spec-repo paths: resolve them against the spec clone, not against this file's installed location.

The harness and the skill must stay in step with five things that change independently. Record the current state of each in the Design record ("Inputs at generation time"), so a later agent can diff against it.

| What changed | How to detect it | What to update |
|---|---|---|
| **The guide** | `git -C <spec-clone> diff <recorded-sha> -- uts/docs/translator-skills/ uts/skills/uts-to-lang-skill-creator/` (includes staged and unstaged changes; list untracked files with `git status --porcelain -- <paths>`) | Map each changed guide section to the artifacts that implement it, using the "Guide" columns in [6.1](phase-4-design-record.md#61-step-4a-draft-the-design-record) and [7.6](phase-5-generate-skill.md#76-step-5f-write-skillmd) and the gap table; update them; re-run the Phase 3 and Phase 6 checks for those artifacts |
| **The UTS docs or helper specs** | `git -C <spec-clone> diff <recorded-sha> -- uts/README.md uts/docs/ uts/objects/helpers uts/rest/unit/helpers uts/realtime/unit/helpers` | Re-run the Phase 2 assessment for the affected rows; update the harness, its smoke tests and self-tests, and its README (Known gaps), the catalogue rows and notes item 9; then re-sync the affected tests |
| **The UTS corpus** | The skill's own re-sync mode (guide [9.2](../../../docs/translator-skills/writing-translator-skills.md#92-a-re-sync-mode-should)), plus the construct scanner ([7.4](phase-5-generate-skill.md#74-step-5d-fill-the-construct-catalogue)) | New catalogue rows (stop and ask for any unmapped construct); new harness symbols the corpus uses; regenerated tests; renamed IDs handled per guide [9.3](../../../docs/translator-skills/writing-translator-skills.md#93-renamed-merged-and-added-ids) |
| **The harness itself** (a helper, mock, fixture or harness test changes) | Its smoke tests and self-tests in CI; the skill's preflight on every run | Fix a red harness test in the harness before any further translation; update the README and Known gaps; regenerate the tests whose rendering depends on the changed helper (guide 9.2) |
| **The SDK** (API, hooks, test layout, CI) | `git -C <repo> diff <recorded-sha>` (includes staged and unstaged changes; list untracked files with `git status --porcelain -- <paths>`) over the paths the Repo profile names | Repo profile; harness and hooks; notes (the SDK source is ground truth); mapping; then a re-sync if the harness or module helpers changed shape |

Rules for every maintenance run:

- Follow the same ground rules ([section 2](../SKILL.md#2-ground-rules)) and stop points, including the model tier ([2.8](../SKILL.md#28-model-tier-and-sub-agents)) and the last-resort rules for reference-implementation reads ([2.1](../SKILL.md#21-your-inputs)). If the guide's "as of" commits have moved since a recorded read, re-check that read's conclusion against the updated Patterns to avoid before relying on it again.
- Start from the working records; update the Repo profile and the harness design if anything they describe has changed.
- Regenerate tests through the skill; the only per-test state that survives is the list in guide 9.2 step 4 (DEVIATION gates, adapted assertions, `deviations.md` entries and, per `writing-derived-tests.md`, UTS-spec-error fail-fast placeholders until the spec is fixed) (guide [9.2](../../../docs/translator-skills/writing-translator-skills.md#92-a-re-sync-mode-should)).
- After any harness change, re-run every affected tier's smoke tests and self-tests, and regenerate the affected tests; after any script change, repeat [8.1](phase-6-validate-skill.md#81-run-the-resolver-on-every-module) and [8.2](phase-6-validate-skill.md#82-test-the-audit-itself).
- Record the new spec SHA and repo SHA in the Design record and append a changelog entry.
