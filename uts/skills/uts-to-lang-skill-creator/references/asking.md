# Asking at a stop point

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention).

Every stop point (SKILL.md [2.3](../SKILL.md#23-stop-points)) is a question the user has to find, understand and answer. Lay each one out the same way, so it stands out in a long run and the answer is unambiguous. This page is the format; the STOP table and the section each stop links to say what to put in it.

## The block

One block per stop, in Markdown (Claude Code and Codex both render it):

1. **A heading:** `### STOP-n: <title>`, for example `### STOP-13: Run mode`.
2. **The question,** in bold, on one line. One question per block: a second decision (such as STOP-17's side) is a lettered sub-question inside the same block, or its own block.
3. **Why it matters:** one sentence on what the answer changes.
4. **The evidence** the decision needs, and no more: at most three to five short bullets, or a small table. Long lists stay in the working records or the JSON, with a pointer.
5. **The options,** numbered (`1.`, `2.`, …); a sub-question's options are lettered (`a.`, `b.`, …). The recommended option comes first and is marked "(recommended)", followed by its reason after a colon. "Stop" is the last option wherever stopping is allowed.

End the message with one line: **Reply with:** and an example answer that names each block, for example `17: 1, side: a, 13: 1`.

When a stop lists many items, as STOP-15 does, give each item its ID in a table, with the proposed choice per item, and accept answers per ID (for example `GA-01: add, GA-03: defer; others as proposed`).

## Several stops in one message

Orient settles its stops in as few messages as possible ([13.1](orient.md#131-run-it)). Keep a separate block for each stop, in the order of 13.1, and one **Reply with:** line at the end. Show Orient's State summary (`stateSummaryMarkdown`, [13.4](orient.md#134-the-state-summary-and-stop-13)) before the blocks, with its warnings first. Use a block a script gives ready-made, such as `stop17Markdown`, as it is: it already lists the recommended option first.

## Example: STOP-17 and STOP-13 (an S3 run with doors)

> ### STOP-17: UTS infrastructure plan
> **Which entry point should the harness use to create clients?**
> Why it matters: it sets the harness's client factory and every generated test's setup; the full design comes at STOP-3.
>
> Existing harness: `Uts/README.md` (candidate). In Upgrade/Fix it is audited at U1 and STOP-15, not planned here.
>
> **How the harness creates clients** (provisional; re-confirmed at STOP-3):
> a. Core constructors through the sanctioned internal-access route (recommended): the repo's UTS code already does this
> b. Server door
> c. Device door (no REST client: the plan drops those tiers)
> d. Both doors as a harness parameter
>
> 1. Accept the plan (recommended)
> 2. Adjust: say what, with evidence
> 3. Stop
>
> ### STOP-13: Run mode
> **How should this run work on `.claude/skills/uts-to-<lang>`?**
> Why it matters: the skill has no records or provenance from this procedure (S3), so its gaps are unknown.
>
> 1. Upgrade/Fix, full gap audit (recommended): audit the skill, harness and tests against the guide, then choose per item
> 2. Regenerate from scratch (staged)
> 3. Stop
>
> **Reply with:** e.g. `17: 1, side: a, 13: 1`

## The structured question tool

The Markdown block is the canonical form: it reads the same in Claude Code and Codex, and it is what the decision log records. In Claude Code, where the `AskUserQuestion` tool is available, you may also ask a stop through it, after showing the block, when the stop has two to four options; one tool question per stop. Codex has no equivalent in its default mode, so there the block is the question. Never use colour codes or other terminal escapes.

## Recording the answer

Record each question and answer in the Design record's decision log (2.3). If the answer is free text, or doesn't name an option, restate how you read it and confirm before acting. An answer that changes something Orient computed (a capability, the side) reruns Orient with the matching option ([13.8](orient.md#138-capabilities-and-scope-stop-17-d-31)).
