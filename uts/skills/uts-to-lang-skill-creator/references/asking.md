# Asking at a stop point

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention).

Every stop point (SKILL.md [2.3](../SKILL.md#23-stop-points)) is a question the user has to find, understand and answer. Ask each one the same way, so it stands out in a long run and every answer is unambiguous. This page is the format; the STOP table and the section each stop links to say what goes in it.

## The question

One decision per question, and one numbered option list per question. A second decision is a second question, never a lettered sub-question or a second list under the same heading.

1. **The heading:** the question in bold, numbered in the order you ask it, with the stop ID at the end in italics for the decision log: `` **Question 1: How should this run work on `.claude/skills/uts-to-csharp`?** *(STOP-13)* ``. Number from 1 in each message.
2. **Why:** at most one short sentence, in plain words.
3. **Evidence,** only what the decision needs: a few short bullets in plain words. Long lists stay in the records or the JSON.
4. **The options,** numbered, one line each: `1. <label> (recommended): <what it does>`. The recommended option comes first. "Stop" comes last wherever stopping is allowed. Mark an option recommended only when the evidence supports it; otherwise mark none.

End the message with one line: **Reply with a number per question, or `ok` to accept all recommendations.** If a question has no recommendation, say that it needs a number.

**Plain words.** What the user reads names no internal IDs and no mechanics. That rules out other stop IDs, record IDs (D-31), facts (P-13), gap-table rows (G-15), phase and step names (Phase 1, U1), section numbers, script flags (`--side`), and terms such as "door" or "provisional". Say "the audit", "the server entry point", "I'll check it again once I've read the test code". The IDs belong in the records and in your own reasoning. The stop ID after each heading is the one exception: it ties the answer to the decision log.

**A stop that lists many items** (STOP-15's gap-audit items, for example) is one question with a table instead of an option list. Each row has the item's ID, what it is, and the proposed choice. End with: "Reply with the items you want to change, such as `GA-03: defer`, or `ok` to accept the proposals."

## Orient's questions

Orient builds its questions in this format ([13.1](orient.md#131-run-it)):

- `questions.now`: STOP-13 (the run mode), then any STOP-17 question that doesn't depend on the run mode. Show `stateSummaryMarkdown` first, then these questions: `questionsMarkdown`, or the `askUserQuestion` form below.
- `followUpByOption`: for each STOP-13 option that needs more, the follow-up message (`questions`, `markdown`, `askUserQuestion`). Once the user answers, ask the follow-up for the option they chose, if there is one, in a second message. It comes from the same Orient output: don't rerun Orient first. Its plan already says what each client-setup answer would drop.

Use them as they are. If STOP-16, the sync question or STOP-1 go in the same message, ask them first and renumber Orient's questions to follow. When every question is answered, rerun Orient once with the answers (`--side`, any correction), so that `infraPlan` and D-31 match them; don't ask again what the user has answered.

## In Claude Code: the AskUserQuestion tool

In Claude Code, ask with the `AskUserQuestion` tool by default. First show the State summary as Markdown, then any evidence the questions need (`askUserQuestion.context`, such as the plan's bullets). Then call the tool with `askUserQuestion.questions`. Don't also print the same questions as Markdown: one form per message.

The tool takes one to four questions per call. Each question has two to four options and a header of at most 12 characters, and the tool adds an "Other" answer for free text. So:

- When a question has five options including "Stop", leave "Stop" out. The user can still type "stop" as Other.
- When a question still has more than four options, or a message has more than four questions, use the Markdown form for the whole message. `askUserQuestion` (or a follow-up's) is null then.
- A stop that lists many items always uses the Markdown form.

In Codex, which has no such tool in its default mode, use the Markdown form. Never use colour codes or other terminal escapes.

## Recording the answer

Record each question, with its stop ID, and the answer in the Design record's decision log (2.3). Then:

- **`ok`** accepts the recommended option of every question in the message. Restate what that means in one line per question ("Run mode: Upgrade/Fix, full audit"), then act. A question without a recommendation still needs its answer: ask it again.
- **A free-text answer,** or one that doesn't name an option: restate how you read it, and confirm before acting.
- **An answer that changes what Orient computed** reruns Orient with the matching option, and the change is recorded in D-31 ([13.8](orient.md#138-capabilities-and-scope-stop-17-d-31)). The timing depends on the answer:
  - "Change something" on the plan: rerun at once, show the new plan, and ask the plan question again.
  - A client-setup answer, or a correction given with an answer: keep it for the single rerun after every question, follow-ups included, is answered. A follow-up comes from the first Orient output; a rerun before it would drop it.

## Example: Upgrade/Fix, client setup found in the existing harness

On ably-dotnet the existing UTS code already creates its clients through the core constructors. That is a detected fact, so there is no client-setup question. The State summary shows it as a row (`` | Client setup | core constructors: … (existing harness: `UtsClients.cs` +2) | ``), and the audit checks it. The profile is full, so there is no plan question either:

> **Question 1: How should this run work on `.claude/skills/uts-to-csharp`?** *(STOP-13)*
> The skill wasn't made by this procedure, so its gaps against the guide are unknown.
>
> 1. Upgrade/Fix, full audit (recommended): check the skill, harness and tests against the guide, then choose what to fix
> 2. Regenerate from scratch: rebuild the skill and harness, approving each replacement
> 3. Stop
>
> Reply with a number, or `ok` to accept the recommendation.

## Example: Create, with the plan and the client setup open

An SDK with server and device entry points, and no UTS code yet to show which one the tests use. Both STOP-17 questions are needed whatever the run mode, so they follow STOP-13 in the same message:

> **Question 1: Should I create a UTS translator skill for ably-dotnet?** *(STOP-13)*
> There's no translator skill, harness or UTS test here yet.
>
> 1. Create (recommended): build the skill and its UTS test harness
> 2. Stop
>
> **Question 2: Is this harness plan right?** *(STOP-17)*
> I'll build this harness, and the skill can translate only the tests it covers.
>
> - REST unit tests: HTTP hook, MockHttpClient, fake clock, randomness hooks; smoke test; MockHttpClient and fake-clock self-tests.
> - Realtime unit tests: WebSocket hook, MockWebSocket, fake clock, network monitor, randomness hooks, MockVCDiff, MockNetworkListener, wait helpers; smoke test; MockWebSocket, fake-clock and wait-helper self-tests.
> - Sandbox integration tests: SandboxApp and fixtures; smoke test and self-tests.
> - Proxy integration tests: ProxyManager, ProxySession; smoke test and self-tests.
> - Every tier: log capture, file placement, a harness README with known gaps, the test target and CI, and a concurrency model.
> - Client setup: the next question.
> - Left out: nothing.
> - LiveObjects: a separate question later.
>
> 1. Yes (recommended): go ahead with this plan
> 2. Change something: tell me what
> 3. Stop
>
> **Question 3: How should the harness create clients?** *(STOP-17)*
> Every generated test sets up its clients this way.
>
> 1. Core constructors: `PubSubHttpClient`, `PubSubRealtimeClient`, through internal access
> 2. Server entry point: `CreateHttpClient`, `CreateRealtimeClient`
> 3. Device entry point: `CreateClient`; no REST client, so the REST tests are dropped
> 4. Both: server and device entry points as a harness setting; the suite runs once for each
> 5. Stop
>
> Reply with a number per question, or `ok` to accept all recommendations (Question 3 has no recommendation, so it needs a number).

In Claude Code, the same message is the State summary, then the plan's bullets under **Harness plan**, then one `AskUserQuestion` call with three questions: "Run mode", "Harness plan" and "Client setup". "Client setup" has five options, so "Stop" is left out of it.
