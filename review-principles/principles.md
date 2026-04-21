# Spec-writing principles derived from review comments

## Provenance

- **Created:** 2026-04-21 (Claude Code session, Claude Opus 4.7 1M)
- **Source repo:** [ably/specification](https://github.com/ably/specification)
- **PR date range covered:** 2022-10-03 (PR #88) to 2026-04-17 (PR #448)
- **Commenters surveyed:** [lawrence-forooghian](https://github.com/lawrence-forooghian) and [SimonWoolf](https://github.com/SimonWoolf)
- **Selection rule:** every PR on `ably/specification`, across all states (open, closed, merged), where either user appears as a commenter — enumerated via `gh search prs --repo ably/specification --commenter <user>`. 118 PRs for Lawrence, 74 for Simon, 161 unique after union.
- **Comment sources per PR:**
  - Issue comments (`gh api /repos/ably/specification/issues/{n}/comments`)
  - Line-level PR review comments (`gh api /repos/ably/specification/pulls/{n}/comments`)
  - Review bodies (`gh api /repos/ably/specification/pulls/{n}/reviews`)
- **Filtering:** four parallel subagents triaged every raw comment authored by either user. They **dropped** trivial acknowledgements ("LGTM", "thanks", "done", emoji-only), procedural nudges ("rebase please", "CI failed", "poke"), pure cross-references without content, and one-line typo fixes that expressed no principle. They **kept** comments expressing opinions about structure, wording, sequencing, scope, backwards compatibility, naming, or spec conventions. 484 comments survived the filter.
- **Synthesis method:** a fifth subagent clustered the 484 retained comments (each tagged with a short `principle_hint`) into principles, grouping by theme and selecting 2–4 representative citations per principle. Clusters with fewer than three distinct PRs as evidence were dropped.
- **Important caveat — excerpts are paraphrases, not quotes.** The `excerpt` for each comment below is an LLM-generated summary of the original comment, not the reviewer's verbatim words. URLs point to the real comments; the wording attributed to Lawrence or Simon in the prose is our summary of their stated position, not text they wrote. If you are citing any of this externally, follow the link and quote from the source.
- **Scope caveats.**
  - This only reflects Lawrence and Simon's review comments. Other reviewers (e.g. VeskeR, AndyTWF, paddybyers, mattheworiordan, owenpearson, QuintinWillison) also have strong opinions that are not captured here.
  - Authored content by these two (PR descriptions, their own commits) is not included — only comments.
  - Early comments may have been deleted from GitHub over the years and would not appear in API results.
- **Source data location:** the raw paraphrased data and the PR lists used to generate this document are in the sibling files of this directory:
  - `all_comments.jsonl` — 484 JSONL lines, one per kept comment, with fields `pr`, `pr_title`, `author`, `url`, `path`, `excerpt`, `principle_hint`.
  - `lawrence_spec_prs.txt` — 118 rows, Lawrence's PR involvements (pipe-delimited: number, state, date, author, title).
  - `simon_spec_prs.txt` — 74 rows, same format for Simon.
  - `all_prs.txt` — 161 unique PR numbers (the union), one per line.
  - A full per-PR inline appendix is at the end of this document.

---

## Scope and audience

### Spec SDK behaviour, not server behaviour or customer documentation

The features spec exists to tell SDK implementers what their library must do. It is not customer documentation, not a wire-protocol reference, and not a test plan for the Ably service. When a proposed spec point describes how the server behaves, or states facts that impose no requirement on the SDK, Simon in particular pushes back hard: informational statements about the server belong in protocol docs or in the realtime repo's test suite, not here. Similarly, avoid explaining what a field means *to the app developer* — the SDK only needs to know how to handle it correctly.

Supporting comments:
- [PR #433](https://github.com/ably/specification/pull/433#discussion_r2889860425) — "None of these belong in the SDK spec; they instruct the server, not the SDK."
- [PR #259](https://github.com/ably/specification/pull/259#discussion_r1890228871) — Rejects informational statements that impose no SDK requirement.
- [PR #279](https://github.com/ably/specification/pull/279#discussion_r2002992179) — Server-side concepts (timeserial, siteCode) should not be exposed in the SDK spec.
- [PR #235](https://github.com/ably/specification/pull/235#discussion_r1851947835) — "This is an SDK spec, not customer documentation."

### Keep the spec self-contained

A reader of the spec should not have to chase external repositories, READMEs, `package.json` files, or other SDKs' source code to understand what a clause means. If a concept depends on an external definition, inline it or give an explicit, stable reference. Simon raised this on PR #105 against defining versioning components via the repo's own build files; Lawrence raised it on PR #200 against "see the Ruby implementation" asides.

Supporting comments:
- [PR #105](https://github.com/ably/specification/pull/105#discussion_r1000849566) — Readers shouldn't need to consult README/package.json to know what the spec refers to.
- [PR #200](https://github.com/ably/specification/pull/200#discussion_r1734259831) — Inline the information rather than pointing at another SDK.
- [PR #58 equivalent; see PR #200 note on "see Ruby for more info"] — Prior cleanup removed such cross-references from the main spec.

### Don't prescribe tests — describe behaviour

Spec points of the form "A test should exist that..." are a recurring Simon nit. The spec's job is to define correct behaviour; deciding which tests to write, and at what granularity, is the implementer's problem. The `Testable` tag exists for tooling, but the text itself should state the requirement, not the verification. A corollary: don't write spec points for states that can't actually arise, and don't mandate that every SDK carry a regression test for a server guarantee.

Supporting comments:
- [PR #166](https://github.com/ably/specification/pull/166#discussion_r1320080062) — Objects to "A test should exist that..." spec items.
- [PR #191](https://github.com/ably/specification/pull/191#issuecomment-2123003416) — Same objection, reiterated.
- [PR #433](https://github.com/ably/specification/pull/433#discussion_r2889865659) — Opposes mandating an SDK test for server-side behaviour.
- [PR #432](https://github.com/ably/specification/pull/432#discussion_r2912256668) — Don't write checks (or tests) for states that cannot occur.

## Clarity and precision

### Use RFC 2119 keywords precisely; avoid "will" and "can"

Both reviewers are strict about normative vocabulary. "Will" is ambiguous between a requirement and a consequence and should not appear in normative text; "can" is not an RFC 2119 level and should be "MAY" if it is a real option. MUST is reserved for genuine SDK requirements — optional behaviours that the team has not committed to implementing should be MAY, not elevated by loose wording. Do not use MUST when describing what the server does.

Supporting comments:
- [PR #400](https://github.com/ably/specification/pull/400#discussion_r2481984842) — "Will" has no RFC 2119 meaning; ambiguous between requirement and consequence.
- [PR #400](https://github.com/ably/specification/pull/400#discussion_r2486406293) — Agrees, plans a systematic sweep.
- [PR #210](https://github.com/ably/specification/pull/210#discussion_r1821615817) — "Can" isn't RFC 2119; use MAY when some libraries should do it.
- [PR #331](https://github.com/ably/specification/pull/331#discussion_r2143315807) — Optional behaviour we aren't funding should be MAY, not elevated to a requirement.

### Define every term you introduce; avoid coined or overloaded names

Undefined domain terms ("detachment cycle", "retry loop", "origin timeserial", "site code") are routinely flagged: either define them, or rewrite using an already-defined concept. Don't introduce a synonym for an existing term (e.g. "type" for "action") — that only invites confusion. Where established terminology exists (RFCs, OSI, REST API docs), prefer it over in-house inventions. When a synonym is unavoidable, mark which name is canonical and which is deprecated.

Supporting comments:
- [PR #200](https://github.com/ably/specification/pull/200#discussion_r1763798318) — Asks for an alternative to the undefined "detachment cycle".
- [PR #279](https://github.com/ably/specification/pull/279#discussion_r1998776708) — Is "origin timeserial" defined anywhere?
- [PR #210](https://github.com/ably/specification/pull/210#discussion_r1821622687) — Rejects "type" as a synonym for "action".
- [PR #212](https://github.com/ably/specification/pull/212#issuecomment-2430469206) — Identify the canonical vs deprecated name when both exist.

### Be concrete about durations, orderings and error fields

Vague timing ("a short pause", "a short wait"), unspecified retry termination, and unordered sequences draw persistent "with what duration?" / "in what order?" questions from Lawrence. Ditto for errors: every clause that says "throw an error" or "transition to FAILED" must specify the `code` and `statusCode`, not just reference "an error". When one spec point mentions several errors, disambiguate which later references point to which.

Supporting comments:
- [PR #200](https://github.com/ably/specification/pull/200#discussion_r1763799223) — Why is "short pause" unspecified?
- [PR #200](https://github.com/ably/specification/pull/200#discussion_r1765372854) — Asks for exact ordering of FAILED-check vs wait in a retry loop.
- [PR #200](https://github.com/ably/specification/pull/200#discussion_r1827819961) — "With what error?" on a state transition (one of four such nits on the same PR).
- [PR #333](https://github.com/ably/specification/pull/333#discussion_r2152430253) — Every thrown error needs a statusCode, not just a code.

### Prefer direct wording and split nested conditionals

Nested "if X, otherwise Y" where one branch restates the condition, `unless`-clauses, and conditionals whose alternative branch is never reached all get flagged as noise. Collapse convoluted logic into a clear statement; or split each branch into its own subclause. CONTRIBUTING.md already discourages conditionals-in-one-item, but the nuance in review is that even after splitting, each branch should state its action completely (rather than relying on a parent clause for half the picture).

Supporting comments:
- [PR #200](https://github.com/ably/specification/pull/200#discussion_r1775788715) — Consolidate a convoluted conditional into one clear statement of trigger + transition.
- [PR #282](https://github.com/ably/specification/pull/282#discussion_r2013976878) — Drop a conditional whose alternative branch is impossible.
- [PR #333](https://github.com/ably/specification/pull/333#discussion_r2152356408) — Split conditional into "discard if precondition fails, otherwise apply" with cross-reference.
- [PR #281](https://github.com/ably/specification/pull/281#pullrequestreview-2686364070) — Prefers each branch list the full set of actions rather than mixing with an overarching clause.

## Structure and cross-document consistency

### DRY: cross-reference rather than duplicate

Never restate the same condition in two places with slightly different wording — the wordings will drift. When a rule applies in several contexts, define it once and reference it. Simon flags this forcefully on PR #167 and PR #195; Lawrence echoes the point when spotting duplicated clientId checks, duplicated channel-name statements, and copy-pasted `Message`/`PresenceMessage`/`Annotation` rules.

Supporting comments:
- [PR #167](https://github.com/ably/specification/pull/167#discussion_r1330652646) — "Refer back to the defining spec item rather than repeating it."
- [PR #195](https://github.com/ably/specification/pull/195#discussion_r1666995784) — RSA7c is the canonical clientId definition; don't add restrictions elsewhere.
- [PR #331](https://github.com/ably/specification/pull/331#discussion_r2143300144) — Write shared spec once; reference from Message, PresenceMessage, Annotation.
- [PR #282](https://github.com/ably/specification/pull/282#discussion_r2012264825) — Name the channel in one authoritative place, not per-feature.

### Apply parallel treatment to parallel spec points

ATTACH and DETACH, publish and subscribe, annotations and messages: analogous operations should receive analogous wording. A clarification added to one side should be mirrored on the other; asymmetry requires justification. Simon flags lifecycle asymmetries (implicit attach without implicit detach); Lawrence flags wording drift between sibling points and inconsistency between related size-check or mode-check rules.

Supporting comments:
- [PR #200](https://github.com/ably/specification/pull/200#discussion_r1755533396) — Clarifications applied to ATTACH should apply to the parallel DETACH points.
- [PR #331](https://github.com/ably/specification/pull/331#discussion_r2150363207) — Use identical wording ("UTF-8 encoded length in bytes") for all string-size components.
- [PR #292](https://github.com/ably/specification/pull/292#discussion_r2045165536) — Is the asymmetry between message and annotation size checks intentional?
- [PR #301](https://github.com/ably/specification/pull/301#discussion_r2056408000) — Align REC1c wording with REC1b4 so all derived points read consistently.

### Respect the parent–child structure of subclauses

CONTRIBUTING.md says parent clauses should be headers, but reviewers go further: a child must genuinely be a sub-scenario of its parent. Don't slot a new sub-item into the middle of a disjunction whose existing children each cover one outcome. Don't scope a child more narrowly than its parent unless that is the intent. Audit optionality and qualifying clauses across siblings — a qualifier in one subclause may be redundant given its sibling's wording.

Supporting comments:
- [PR #167](https://github.com/ably/specification/pull/167#discussion_r1326118316) — A shared requirement across disjunctive siblings shouldn't be added as a sibling itself.
- [PR #413](https://github.com/ably/specification/pull/413#discussion_r2741526620) — Child's scope is narrower than the parent describes.
- [PR #139](https://github.com/ably/specification/pull/139#discussion_r1269523776) — Audit optionality and redundancy across sibling subclauses.

### Keep IDL, prose, api-docstrings and typings in sync

Review catches IDL–prose mismatches, stale field names in IDL after prose renames, and typings that don't reflect what the spec permits. CONTRIBUTING.md already requires api-docstrings in the same PR; the review nuance is that the wording in api-docstrings should match the docstring text SDK authors will paste, and that IDL syntax conventions (optionality marker, argument ordering) should stay consistent. When spec wording is finalised late in review, explicitly update IDL and docstrings before merge.

Supporting comments:
- [PR #139](https://github.com/ably/specification/pull/139#discussion_r1269529397) — IDL and prose disagree on field types.
- [PR #160](https://github.com/ably/specification/pull/160#discussion_r1269571462) — Callback still has its pre-rename name in the IDL.
- [PR #375](https://github.com/ably/specification/pull/375#discussion_r2334089225) — api-docstrings wording should match the docstring text SDKs will use.
- [PR #292](https://github.com/ably/specification/pull/292#discussion_r2095278377) — Update IDL and docstrings to match the newly-agreed wording.

### Separate normative from non-normative text

Rationale ("why") has no place inside a normative clause; it either belongs in a design record or, at most, in clearly-marked informative prose. Overview clauses whose concrete rules are given by their sub-points should be labelled non-normative to avoid being read as a second source of truth. When a spec point is a summary, flag it as such so readers don't try to implement the summary directly.

Supporting comments:
- [PR #170](https://github.com/ably/specification/pull/170#discussion_r1369215876) — Pare back rationale-heavy wording to the normative requirement.
- [PR #416](https://github.com/ably/specification/pull/416#issuecomment-3781020868) — Spec describes "what", not "why"; rationale belongs in DRs.
- [PR #419](https://github.com/ably/specification/pull/419#discussion_r2721532253) — Don't include in-spec rationale for skipping a field.
- [PR #277](https://github.com/ably/specification/pull/277#discussion_r2021028332) — Make the overview non-normative; put concrete rules in subclauses.

## Cross-SDK considerations

### Write in language-agnostic terms; accommodate language idioms

The spec is consumed by ~20 SDKs across languages with very different idioms (Go has no overloads; Swift treats programmer errors as irrecoverable; JS collapses errors into promise rejection). Write requirements so each language can satisfy them idiomatically — for example, leave the concrete return type of an unsubscribe API unspecified, and allow programmer-error handling to use whichever mechanism suits the host language. MAY is the right tool when languages legitimately differ.

Supporting comments:
- [PR #209](https://github.com/ably/specification/pull/209#discussion_r1793367421) — Prefer language-agnostic wording over listing each language's return type.
- [PR #139](https://github.com/ably/specification/pull/139#discussion_r1182377129) — A Go-unfriendly overload should be made optional.
- [PR #209](https://github.com/ably/specification/pull/209#discussion_r1793698634) — Per-language choice of statusCode/code for programmer errors.
- [PR #292](https://github.com/ably/specification/pull/292#discussion_r2054800114) — Allow warn-log as an alternative to throwing when neither error category fits.

### Cross-SDK consistency sometimes outweighs local aesthetics

Even where one SDK's API could be cleaner in isolation, reviewers accept compromises to keep behaviour uniform across libraries. If diverging would break existing users of another SDK, consistency wins. This is the counterweight to the principle above: languages may vary in form, but user-visible behaviour should not.

Supporting comments:
- [PR #448](https://github.com/ably/specification/pull/448#discussion_r3112951235) — Would prefer release() surface an error, but cross-SDK uniformity matters more.
- [PR #179](https://github.com/ably/specification/pull/179#pullrequestreview-1830062473) — A nicer API rejected because of the cost across SDKs.
- [PR #206](https://github.com/ably/specification/pull/206#issuecomment-2341964192) — Rejected simplification because it would be a breaking API change.

### Treat already-implemented spec points as public API

Once an ID is referenced from SDK source code, it is part of a public contract with implementers. Don't rename IDs when the content barely changes, don't silently edit wording to match a new implementation, and don't re-label a behaviour change as a "clarification". Mark replaced points per CONTRIBUTING.md rather than mutating in place — even if the new wording is "just clearer". Conversely, don't churn IDs for pure rewording: preserve them so SDK comment references don't all need updating.

Supporting comments:
- [PR #182](https://github.com/ably/specification/pull/182#discussion_r1486624999) — Spec points can't be silently edited; follow the Modification guidance.
- [PR #400](https://github.com/ably/specification/pull/400#discussion_r2481968478) — Don't call a behaviour change a "clarification".
- [PR #356](https://github.com/ably/specification/pull/356#discussion_r2279119351) — Reword-for-clarity doesn't require deprecating IDs; SDK code comments reference them.
- [PR #312](https://github.com/ably/specification/pull/312#pullrequestreview-2794460297) — Skip version tombstones for clarity-only rewords.

## PR and review mechanics

### Keep PRs scoped; split bug fixes out

Even when an improvement is clearly correct, reviewers defer it to a separate PR if it is outside the stated scope. Latent bug fixes bundled into a feature PR get flagged and asked to be extracted so they can be merged with their own commit message and context. The reviewer accepting "yes, that's worth fixing, but not here" is common on both sides.

Supporting comments:
- [PR #292](https://github.com/ably/specification/pull/292#discussion_r2045101056) — Is this actually a bug fix? Split it out.
- [PR #292](https://github.com/ably/specification/pull/292#discussion_r2054243035) — Harmonising unknown-enum handling is outside this PR's scope.
- [PR #311](https://github.com/ably/specification/pull/311#discussion_r2064127389) — Declines to expand scope to unrelated wording tweaks.
- [PR #419](https://github.com/ably/specification/pull/419#discussion_r2817991318) — Broader cross-cutting concern out of scope here.

### One spec item per line; no wrapping

Line-wrapping inside spec items breaks `git show --word-diff`, confuses LLM-assisted edits, and requires an autoformatter to stay consistent. The agreed convention is one line per spec item. Simon would tolerate wrapping only if paired with editorconfig and an autoformatter; Lawrence leans the same way.

Supporting comments:
- [PR #434](https://github.com/ably/specification/pull/434#issuecomment-4011497498) — Spec items one per line; git and LLM tooling rely on it.
- [PR #434](https://github.com/ably/specification/pull/434#pullrequestreview-3902798713) — Opposes wrapping; if used, requires autoformatter + max_line_length.

## Notable disputed/ambiguous points

- **Line wrapping (PR #434).** Simon opposed the decision to wrap lines in the Markdown migration; Lawrence agreed with him that wrapping should be avoided. There is no true disagreement between reviewers, but the migration itself introduced wrapping that both reviewers then pushed back on — so the merged state of the repo and the reviewers' preference are in tension.
- **"Clarification" vs behavioural change (PRs #312, #356, #400).** Both reviewers agree that genuine behavioural changes must not be labelled clarifications. But they also agree that genuine clarifications don't need version tombstones or new IDs. The line between the two is judgement-based and gets re-litigated per PR; expect pushback either way if you mis-classify.
- **Prescriptiveness in spec text.** Simon tends to push for the spec to describe fewer things (omit server behaviour, drop rationale, drop tests); Lawrence tends to push for the spec to describe more things (initial values of private state, concrete wait durations, exact error codes). These are complementary rather than contradictory — Simon trims scope, Lawrence tightens what's in scope — but a contributor should expect pressure in both directions on the same PR.

---

## Appendix: raw comment data

All 484 paraphrased comments that fed into this document, grouped by PR and ordered newest-first. Each line gives the author, a link to the original comment, the `principle_hint` tag, the file path (where applicable), and the paraphrased excerpt. Excerpts are paraphrases, not quotes — follow the link for the original wording.

The same data in JSONL form is in the sibling file `all_comments.jsonl`.

### PR #448 — Add some warnings on channels.release()

- **SimonWoolf** — [ensure spec decisions are actually implemented](https://github.com/ably/specification/pull/448#discussion_r3101090786) (specifications/api-docstrings.md:258)
  - Questions whether the use case justifies the spec change (why would bringing React components in/out of scope need release?) and notes frustration at discovering an earlier decision to make release() implicitly detach was never implemented in ably-js.
- **SimonWoolf** — [flag 'advanced/unsafe' APIs in docstrings](https://github.com/ably/specification/pull/448#discussion_r3101172119) (specifications/api-docstrings.md:258)
  - Concedes the point and suggests removing the required-channel-state bit and making ably-js detach on release, but argues the docstring should still warn people off release() since it was always an advanced-user API without guardrails.
- **SimonWoolf** — [cross-SDK consistency outweighs individual API aesthetics](https://github.com/ably/specification/pull/448#discussion_r3112951235) (specifications/api-docstrings.md:258)
  - Would prefer release() surface an error rather than be automagic, but accepts cross-SDK uniformity matters more, since changing other SDKs to ably-js semantics would be a breaking change.

### PR #434 — feat!: textile to md migration

- **lawrence-forooghian** — [one spec item per line; no line wrapping](https://github.com/ably/specification/pull/434#issuecomment-4011497498)
  - Agrees spec items should be one per line without wrapping since no autoformatter will maintain wrapping during edits; also notes tools like git show --word-diff play poorly with wrapped lines.
- **SimonWoolf** — [one spec item per line; add autoformatter if wrapping](https://github.com/ably/specification/pull/434#pullrequestreview-3902798713)
  - Opposes the decision to wrap lines in the Markdown migration; one line per spec item is easier for LLMs and gives cleaner diffs. If wrapping is used, an autoformatter and max_line_length in editorconfig are required.

### PR #433 — feat: add channel-level echo suppression spec points

- **SimonWoolf** — [spec is for SDK behaviour, not server behaviour](https://github.com/ably/specification/pull/433#discussion_r2889860425) (textile/features.textile:745)
  - Argues that none of the new spec items belong in the SDK spec because they instruct the server, not the SDK; it's not the SDK's job to interpret, validate, or act on params — RTL4k already specifies the SDK must encode and send them.
- **SimonWoolf** — [don't mandate SDK tests for server-side behaviour](https://github.com/ably/specification/pull/433#discussion_r2889865659) (textile/features.textile:798)
  - Opposes mandating that every SDK have a test for server-side behaviour.
- **SimonWoolf** — [separate SDK requirements from user documentation](https://github.com/ably/specification/pull/433#discussion_r2889877879) (textile/features.textile:540)
  - Distinguishes the SDK instruction (turn echoMessages into an echo querystring param) from explanatory docstring-style content; the latter is user-facing documentation, not actionable for an SDK dev, and shouldn't be in the spec.
- **SimonWoolf** — [user docstrings shouldn't reference spec item ids](https://github.com/ably/specification/pull/433#discussion_r2889890147) (textile/api-docstrings.md:334)
  - User-visible docstrings shouldn't be wordy or try to enumerate params (the linked user docs already have the list), and shouldn't reference a spec item identifier, which is meaningless to users integrating the library.
- **lawrence-forooghian** — [don't spec client logic for server behaviour](https://github.com/ably/specification/pull/433#discussion_r2893231580) (textile/features.textile:745)
  - Agrees with Simon that end-to-end behaviour spec points are actively confusing because they invite agents to implement client logic that shouldn't exist (cites RTP9b presence where an agent wrote a local-check-then-ENTER path). Supports test-assertion spec points as a cross-SDK way to enforce end-to-end behaviour when no better mechanism exists.
- **SimonWoolf** — [keep SDK spec focused; use realtime repo for server tests](https://github.com/ably/specification/pull/433#discussion_r2895150397) (textile/features.textile:745)
  - Rejects the notion that RTL4j2 is a precedent for speccing out all server behaviour — only one channelparams test is needed to verify encoding. Argues SDK test suites shouldn't aim to be comprehensive server-behaviour tests (that's realtime repo's job) and that merging SDK spec with user docs would cause scope bloat and incoherence; better to keep the spec focused and cross-reference docs.

### PR #432 — [AIT-466] Spec for MAP_CLEAR operation

- **lawrence-forooghian** — [define semantics of shared flags precisely](https://github.com/ably/specification/pull/432#issuecomment-4033642443)
  - Asks what clearTimeserial of the root map should be in the ATTACH-with-!HAS_OBJECTS case (RTO4b) and whether !HAS_OBJECTS can ever follow a root-map clear; notes ambiguity about the semantics of HAS_OBJECTS itself.
- **lawrence-forooghian** — [avoid state unless it is actually needed](https://github.com/ably/specification/pull/432#discussion_r2897211863) (textile/objects-features.textile:672)
  - Questions why we tombstone entries rather than simply remove them, because the RTLM7h check already prevents MAP_SET resurrecting them.
- **lawrence-forooghian** — [apply analogous checks to analogous operations](https://github.com/ably/specification/pull/432#discussion_r2897301718) (textile/objects-features.textile:621)
  - Suggests applying an analogous check for MAP_REMOVE, based on a preceding Slack discussion.
- **lawrence-forooghian** — [get link syntax right for spec site rendering](https://github.com/ably/specification/pull/432#discussion_r2897340929) (textile/features.textile:1766)
  - Flags missing colon needed for a Textile link to render.
- **lawrence-forooghian** — [distinguish invariants from imperative requirements](https://github.com/ably/specification/pull/432#discussion_r2897345225) (textile/objects-features.textile:465)
  - Points out a line reads like an instruction but is really an invariant maintained by other spec points; wording should reflect that it's an invariant.
- **lawrence-forooghian** — [define terms precisely; avoid tests for impossible states](https://github.com/ably/specification/pull/432#discussion_r2912256668) (specifications/objects-features.md:682)
  - Asks what 'empty' means (empty string?) and whether that can actually happen; if not, the associated checks and tests Claude started writing aren't needed.
- **lawrence-forooghian** — [be careful with inclusive vs strict comparisons](https://github.com/ably/specification/pull/432#discussion_r2912311360) (specifications/objects-features.md:682)
  - Flags a comparison operator that likely should be strict rather than 'or equal to'.

### PR #426 — [AIT-313] Add spec for new fields for ObjectOperation in protocol v6+

- **lawrence-forooghian** — [order spec changes to match implementation stacking](https://github.com/ably/specification/pull/426#issuecomment-3946489781)
  - Asks that the order of spec branches be swapped (ObjectState changes first, then sync) because that's the order SDKs must implement them in and it matches the stacking of ably-js branches.
- **lawrence-forooghian** — [spec must cover operations the SDK actually uses](https://github.com/ably/specification/pull/426#discussion_r2842315082) (textile/features.textile:1591)
  - Spec must include the mapCreateWithObjectId / counterCreateWithObjectId operation variants because those are what the SDK actually sends.
- **lawrence-forooghian** — [cover all operation variants apply-on-ACK may see](https://github.com/ably/specification/pull/426#discussion_r2849354510) (textile/objects-features.textile:662)
  - Argues the RTLM23 apply logic must handle both mapCreate and mapCreateWithObjectId because apply-on-ACK will hit the latter variant; same for counter.
- **lawrence-forooghian** — [weigh trade-offs between consistency and efficiency](https://github.com/ably/specification/pull/426#discussion_r2849437187) (textile/objects-features.textile:662)
  - Notes that requiring decode of initialValue to apply WithObjectId variants is unfortunate (we created it locally, and it's only ever created locally) but necessary if we want apply-on-ACK to remain 'apply what you send'. Acknowledges alternatives would mean complicating publishAndApply.
- **lawrence-forooghian** — [consider API shapes that keep send/apply distinct](https://github.com/ably/specification/pull/426#discussion_r2849510424) (textile/objects-features.textile:662)
  - Explores an alternative spec where publishAndApply accepts pairs of ObjectOperations (send + apply) to avoid the decode round-trip, but worries it is less consistent. Also notes publishAndApply should probably take an ObjectOperation and build the ObjectMessage itself.
- **lawrence-forooghian** — [spec should not enforce one implementation approach](https://github.com/ably/specification/pull/426#discussion_r2855329504) (textile/objects-features.textile:662)
  - Proposes a spec draft that avoids 'misusing' the *Create properties on ObjectOperation while remaining implementation-agnostic, so JS's approach still satisfies the spec but other SDKs can implement differently.

### PR #419 — [AIT-280] Apply LiveObjects operations on ACK

- **lawrence-forooghian** — [reference existing spec rather than duplicate](https://github.com/ably/specification/pull/419#discussion_r2721444166) (textile/objects-features.textile:215)
  - Suggests saying 'in the same way as RealtimeChannel#publish' and referencing RTL6j rather than re-describing the behaviour.
- **lawrence-forooghian** — [link text should be the spec point id](https://github.com/ably/specification/pull/419#discussion_r2721448807) (textile/objects-features.textile:219)
  - Notes the convention that link text is always the name of a spec point item, and asks this be applied throughout the commit.
- **lawrence-forooghian** — [follow convention for property reference formatting](https://github.com/ably/specification/pull/419#discussion_r2721456712) (textile/objects-features.textile:223)
  - States the convention for referencing properties: write '<spec point id> <property name>' consistently.
- **lawrence-forooghian** — [collapse spec points when one sentence suffices](https://github.com/ably/specification/pull/419#discussion_r2721497659) (textile/objects-features.textile:219)
  - Suggests simplifying by just saying 'if publish fails we rethrow the error and do not proceed' and removing an extra spec point.
- **lawrence-forooghian** — [follow CONTRIBUTING.md for replacing spec points](https://github.com/ably/specification/pull/419#discussion_r2721508652) (textile/objects-features.textile:55)
  - Instructs the author to introduce new spec points for places that previously called publishAndApply, following CONTRIBUTING.md (and notes they can skip the 'was valid up to' part).
- **lawrence-forooghian** — [omit data details not relevant at the call site](https://github.com/ably/specification/pull/419#discussion_r2721517759) (textile/objects-features.textile:162)
  - Says the spec shouldn't include the details of what's in the message at this point.
- **lawrence-forooghian** — [procedures should declare accepted arguments explicitly](https://github.com/ably/specification/pull/419#discussion_r2721523383) (textile/objects-features.textile:168)
  - Proposes making a procedure parameter non-optional, giving procedures an explicit arguments section, and updating callers without marking them as replaced; apply this pattern to RTLC7 and RTLM15 too.
- **lawrence-forooghian** — [cite exact spec point identifiers](https://github.com/ably/specification/pull/419#discussion_r2721529223) (textile/objects-features.textile:226)
  - Asks for a specific spec-point reference (RTO5c10b) rather than a vaguer pointer.
- **lawrence-forooghian** — [omit inline 'why' in normative spec text](https://github.com/ably/specification/pull/419#discussion_r2721532253) (textile/objects-features.textile:253)
  - Says the spec shouldn't include rationale for why siteTimeserials is being skipped in the update.
- **lawrence-forooghian** — [prefer simpler patterns that mirror existing ones](https://github.com/ably/specification/pull/419#discussion_r2747222232) (textile/objects-features.textile:236)
  - Questions the need to specify a bufferedAcks list at all; proposes instead requiring callers to wait until SYNCED before proceeding, mirroring the pattern used by .getRoot() in RTO1c.
- **lawrence-forooghian** — [distinguish separate protocol concerns in spec](https://github.com/ably/specification/pull/419#discussion_r2812410564) (textile/objects-features.textile:228)
  - Separates two conflated concerns: does an ACK always contain serials (yes per protocol), and can a serial element be null (yes, per conflation rule docs); the spec point should handle the relevant one and JS internal types need a separate fix.
- **lawrence-forooghian** — [seek consistent handling of server protocol violations](https://github.com/ably/specification/pull/419#discussion_r2813876031) (textile/objects-features.textile:228)
  - Raises that the spec currently brushes over 'server does not supply data it is meant to' cases; asks whether there's any precedent or spec point for treating such situations as protocol errors that invalidate the transport.
- **lawrence-forooghian** — [preserve simple API contracts; opt-in to complication](https://github.com/ably/specification/pull/419#discussion_r2813951538) (textile/objects-features.textile:228)
  - Argues that if conflation were ever introduced for LiveObjects operations it would need to be user-opt-in, because apply-on-ack's simple contract ('success means applied') would otherwise be undermined by many caveats. Also notes 'empty serials' shouldn't be possible per protocol docs.
- **lawrence-forooghian** — [bound PR scope; defer cross-cutting concerns](https://github.com/ably/specification/pull/419#discussion_r2817991318) (textile/objects-features.textile:228)
  - Observes the broader topic of how to generically handle unexpected server behaviour is worth addressing but is out of scope for this PR.
- **lawrence-forooghian** — [prefer explicit errors over silent failure](https://github.com/ably/specification/pull/419#discussion_r2823860348) (textile/objects-features.textile:230)
  - Defends keeping 'fail loudly' behaviour for the best-effort edge cases rather than silently failing, and improves the error message to describe the specific state-change cause.

### PR #418 — spec: add siteCode to connectionDetails

- **lawrence-forooghian** — [don't restate globally-understood versioning assumptions](https://github.com/ably/specification/pull/418#discussion_r2721377991) (textile/features.textile:1917)
  - A given spec version targets a given protocol version (CSV2), so adding a sentence saying so for one feature is redundant.

### PR #417 — Downcase `BufferedObjectOperations` and clarify its scope

- **lawrence-forooghian** — [naming internal state is fine given precedent](https://github.com/ably/specification/pull/417#issuecomment-3790488227)
  - Argues there's little difference between 'it needs this data structure' and 'it needs an attribute with this name'; both are prescriptive and internals are up to implementers. Cites precedent (RTN16f msgSerial) and chooses consistency with presence.

### PR #416 — [AIT-286] Fix rules for buffering of incoming object operations during LiveObjects sync

- **lawrence-forooghian** — [put 'why' in DRs; keep spec focused on 'what'](https://github.com/ably/specification/pull/416#issuecomment-3781020868)
  - Argues the spec generally describes 'what' not 'why', and when it does, it does so concisely and avoids Realtime implementation details. Proposes capturing the rationale for this change in a separate Decision Record (DR) covering why applying buffered ops post-discontinuity would be incorrect and the best-effort RTO5f behaviour, rather than inlining explanation into spec points.
- **lawrence-forooghian** — [commit messages must match actual changes](https://github.com/ably/specification/pull/416#issuecomment-3967788989)
  - Requests the commit message be updated because it references behaviour (OBJECT_SYNC without preceding ATTACHED) that isn't touched in the PR.
- **lawrence-forooghian** — [use 'replaced' not 'deleted' for superseded items](https://github.com/ably/specification/pull/416#discussion_r2712630058) (textile/objects-features.textile:124)
  - Prefers the terminology 'replaced' over 'deleted' for a spec point being superseded.

### PR #415 — Add specification for apply operations on ACK (LODR-054)

- **lawrence-forooghian** — [avoid unnecessary external links in spec](https://github.com/ably/specification/pull/415#discussion_r2698012320) (textile/features.textile:1917)
  - Says a set of links added to the spec aren't needed.

### PR #413 — [AIT-236] Add partial object sync specification for protocol version 6+

- **lawrence-forooghian** — [include implementers as spec PR reviewers](https://github.com/ably/specification/pull/413#issuecomment-3756170930)
  - Requests that implementers of a feature be added as reviewers on the spec PR once the protocol is agreed.
- **lawrence-forooghian** — [spec targets one protocol version at a time](https://github.com/ably/specification/pull/413#discussion_r2741513316) (textile/objects-features.textile:125)
  - States that the spec targets a single protocol version (given by CSV2b) so there's no need to maintain the old v5 behaviour description alongside the new one.
- **lawrence-forooghian** — [child spec points must be sub-scenarios of parent](https://github.com/ably/specification/pull/413#discussion_r2741526620) (textile/objects-features.textile:127)
  - Objects to a parent spec point that describes behaviour 'when receiving partial ObjectState messages for the same objectId' if its child is about when that objectId does not yet exist — the child is not a sub-scenario of the parent.
- **lawrence-forooghian** — [omit details clients don't need to act on](https://github.com/ably/specification/pull/413#discussion_r2741543253) (textile/objects-features.textile:126)
  - Argues a mention of duplicate channelSerials across OBJECT_SYNC messages is an unnecessary and confusing detail that clients shouldn't have to think about — they only care about 'is this new?' and 'is this the end?'.
- **lawrence-forooghian** — [define discriminator logic explicitly](https://github.com/ably/specification/pull/413#discussion_r2741550401) (textile/objects-features.textile:129)
  - Asks how the spec determines 'for a map object' from a given ObjectState, suggesting the check (e.g. presence of ObjectState.map) must be written down.
- **lawrence-forooghian** — [specify which source value to use when multiple exist](https://github.com/ably/specification/pull/413#discussion_r2741637177) (textile/objects-features.textile:129)
  - Notes the spec must describe which of several ObjectMessages' serialTimestamp values should be used when tombstoning during sync pool application.

### PR #412 — Add docstrings for RealtimeChannel publish-y params arg

- **SimonWoolf** — [keep opaque params opaque; don't enumerate in types](https://github.com/ably/specification/pull/412#pullrequestreview-3638924608)
  - Argues SDK docs for params/transportParams should intentionally remain vague since the point of opaque params is to avoid needing SDK changes for new options, and that known params shouldn't be baked into typings.

### PR #411 — RTL5: allow detach() to just detach immediately if the connection state is suspended/disconnected

- **lawrence-forooghian** — [verify spec changes preserve user-facing guarantees](https://github.com/ably/specification/pull/411#pullrequestreview-3638871299)
  - Raises a design concern that if detach() represents a user request to immediately release a potentially-billable resource, skipping the DETACH send might not honour that intent, and asks for confirmation this isn't a problem.

### PR #408 — Remove bundling and fix deprecated spec item version references

- **lawrence-forooghian** — [update contributor guide alongside spec conventions](https://github.com/ably/specification/pull/408#discussion_r2664389743) (textile/features.textile:391)
  - Notes that the wording 'valid up to and including' comes from CONTRIBUTING guidance, so if it's wrong the guide must be updated too.

### PR #406 — Implement spec for protocol v5 (publish result, realtime update/delete, append)

- **lawrence-forooghian** — [explicitly state inherited/shared semantics](https://github.com/ably/specification/pull/406#discussion_r2661098242) (textile/features.textile:852)
  - Asks whether the same queueing rules and state conditions as publish apply to this new method, so the spec should make that explicit.

### PR #404 — objects: Specify `SYNCING` and `SYNCED` events

- **lawrence-forooghian** — [align spec wording with implementation semantics](https://github.com/ably/specification/pull/404#discussion_r2685783582) (textile/objects-features.textile:117)
  - Highlights that JS's notion of 'new sync sequence' is broader than the spec's RTO5a2 (it includes the case where no prior sync existed) and the spec needs to reconcile this.
- **lawrence-forooghian** — [keep spec text lean; explanations sparingly](https://github.com/ably/specification/pull/404#discussion_r2685892766) (textile/objects-features.textile:205)
  - Acknowledges reviewer concern about explanatory text bloating the spec and agrees to remove, while noting some explanatory context is nice to have.
- **lawrence-forooghian** — [surface and justify non-obvious spec behaviour](https://github.com/ably/specification/pull/404#discussion_r2690884716) (textile/objects-features.textile:117)
  - Flags confusion about why BufferedObjectOperations is cleared on a new sync sequence, especially when there wasn't a prior sync; suggests the rationale needs surfacing or re-examining.

### PR #401 — CHA-M5b1 and CHA-M13a1 proposals.

- **lawrence-forooghian** — [nail down upstream spec before relying on it](https://github.com/ably/specification/pull/401#discussion_r2498638344) (textile/chat-features.textile:413)
  - Raises that the core SDK behaviour on non-2xx responses is under-specified and that Chat depends on behaviour that ought first to be pinned down in the core spec.
- **lawrence-forooghian** — [handle distinct conditions explicitly, not by conflation](https://github.com/ably/specification/pull/401#discussion_r2498712140) (textile/chat-features.textile:413)
  - Notes an inconsistency between HP5 (HTTPPaginatedResponse.success) and the claim that core SDKs intercept non-2xx, and suggests that 'empty response' cases should be handled explicitly rather than conflated with 'not found'.
- **lawrence-forooghian** — [make triggering conditions explicit](https://github.com/ably/specification/pull/401#discussion_r2498781084) (textile/chat-features.textile:399)
  - Asks for the spec to be more explicit about the triggering condition (e.g. 'when the channel next transitions to the ATTACHED state').

### PR #400 — Clarify some points about encoding and decoding message data

- **SimonWoolf** — [don't label behaviour changes as 'clarifications'](https://github.com/ably/specification/pull/400#discussion_r2481968478) (textile/features.textile:364)
  - Opposes using 'clarification' wording in spec points where actual behaviour is being changed.
- **SimonWoolf** — [use precise types and RFC 2119 keywords (avoid 'will')](https://github.com/ably/specification/pull/400#discussion_r2481984842) (textile/features.textile:375)
  - Nitpicks that JSON is a serialisation format not a data type, and notes a personal dislike of 'will' in the spec since it has no RFC 2119 meaning and may describe either a requirement or a consequence.
- **SimonWoolf** — [remove redundancy rather than annotate it](https://github.com/ably/specification/pull/400#discussion_r2481994943) (textile/features.textile:774)
  - Argues redundancy should be removed from the spec rather than merely lampshaded/commented on.
- **lawrence-forooghian** — [avoid ambiguous 'will'; prefer RFC 2119 language](https://github.com/ably/specification/pull/400#discussion_r2486406293) (textile/features.textile:375)
  - Agrees 'will' is ambiguous (requirement vs consequence) and plans to address it systematically via a separate issue, possibly with Claude's help.

### PR #399 — chat: add missing Closing and Closed statuses

- **lawrence-forooghian** — [avoid mirrored documentation of upstream behaviour](https://github.com/ably/specification/pull/399#pullrequestreview-3393653681)
  - Questions whether per-status descriptions are still needed once they merely mirror the core SDK values.

### PR #394 — chat: error code review

- **lawrence-forooghian** — [remove redundant/duplicated requirements](https://github.com/ably/specification/pull/394#discussion_r2441033899) (textile/chat-features.textile:1604)
  - Flags that a status code mention in one spec point is redundant given the same info in the newly added section.
- **lawrence-forooghian** — [place normative text in the correct section](https://github.com/ably/specification/pull/394#discussion_r2441037010) (textile/chat-features.textile:1636)
  - Suggests moving a paragraph to the section it actually pertains to, and notes that the non-chat-specific error codes already have their status codes specified elsewhere.
- **lawrence-forooghian** — [prefer named references over literal codes](https://github.com/ably/specification/pull/394#discussion_r2441038657) (textile/chat-features.textile:1608)
  - Asks that other references to the numeric error code (40003) be updated to reference the new named spec point instead.
- **lawrence-forooghian** — [keep spec scope limited to SDK responsibilities](https://github.com/ably/specification/pull/394#discussion_r2441043103) (textile/chat-features.textile:1620)
  - Argues that the error-codes section should only list codes thrown by Chat itself and not codes bubbled up from core or the server; listing those is out of scope for this spec.
- **lawrence-forooghian** — [eliminate duplicate normative requirements](https://github.com/ably/specification/pull/394#discussion_r2441050299) (textile/chat-features.textile:1655)
  - Points out that an existing spec point's status code requirement is now redundant with the new wording.
- **lawrence-forooghian** — [every declared entity should be referenced](https://github.com/ably/specification/pull/394#discussion_r2441051722) (textile/chat-features.textile:1659)
  - Notes that an error code listed here isn't referenced anywhere else in the spec and queries whether it should be linked to CHA-RC1f1.
- **lawrence-forooghian** — [declared error codes must be used in spec](https://github.com/ably/specification/pull/394#discussion_r2441054701) (textile/chat-features.textile:1667)
  - Flags another error code declared here but not referenced in the spec; it shouldn't be in the common-error-codes section if nothing uses it.
- **lawrence-forooghian** — [section titles should precisely describe scope](https://github.com/ably/specification/pull/394#discussion_r2441131483) (textile/chat-features.textile:1594)
  - Suggests re-titling the section to 'Common Error Codes used by Chat' to clarify scope.
- **lawrence-forooghian** — [flag silent narrowing of permitted values](https://github.com/ably/specification/pull/394#discussion_r2445198012) (textile/chat-features.textile:207)
  - Asks whether it was intentional to restrict an error code to a single status code when previously it admitted multiple.

### PR #393 — chat: Specify `MessageReactions.clientReactions`

- **lawrence-forooghian** — [naming decisions should reflect real code clarity](https://github.com/ably/specification/pull/393#discussion_r2432281151) (textile/chat-features.textile:467)
  - Pushes back on a readability concern about using prepositions in argument labels, noting it isn't actually confusing in the code.

### PR #387 — Clarify Chat URL-encoding requirements

- **lawrence-forooghian** — [state the problem the spec clause solves](https://github.com/ably/specification/pull/387#issuecomment-3385509970)
  - Asks to clearly articulate the underlying problem (we want to escape slashes so they aren't mistaken for path separators) and be more explicit in the spec about exactly what escaping is required.
- **lawrence-forooghian** — [specify encoding rules unambiguously](https://github.com/ably/specification/pull/387#issuecomment-3385643916)
  - Argues that 'encode' is ambiguous without precise rules (e.g. slash is allowed in a path) and the spec must specify the encoding rule rather than defer to vague conventions.
- **lawrence-forooghian** — [ground requirements in established RFCs/standards](https://github.com/ably/specification/pull/387#issuecomment-3385741354)
  - Proposes grounding the encoding requirement in RFC 3986's 'segment' definition rather than inventing a new rule.
- **SimonWoolf** — [avoid mandating behaviour unnecessary for interop](https://github.com/ably/specification/pull/387#issuecomment-3389215520)
  - Summarises the competing constraints (let JS use encodeURIComponent, let Go use url.PathEscape, encode '/', etc.) and proposes a relaxed wording that doesn't mandate the exact same set of encoded characters across SDKs so long as problematic ones are covered.
- **lawrence-forooghian** — [express requirement precisely while allowing implementation latitude](https://github.com/ably/specification/pull/387#issuecomment-3393701548)
  - Pushes back by re-reading RFC 3986 'pchar' and showing that both encodeURIComponent and url.PathEscape are strictly more aggressive than the segment rule, so referring to 'segment' lets SDKs use their built-in functions.
- **lawrence-forooghian** — [specify minimum requirement and permit stricter implementations](https://github.com/ably/specification/pull/387#issuecomment-3423428856)
  - Proposes explicit wording referencing RFC 3986 sections, requiring pchar-level encoding and explicitly permitting implementations to encode further so they may use standard library helpers.

### PR #381 — Clarify how to handle msgSerial when RTN15 check fails

- **SimonWoolf** — [extract shared concepts into single spec points](https://github.com/ably/specification/pull/381#issuecomment-3324525036)
  - Proposes factoring the repeated concept of 'clearing the connection state' into a dedicated spec point (listing what that entails) and referencing it from each place instead of duplicating the definition.

### PR #375 — v4: add spec items for Protocol V4

- **SimonWoolf** — [bump meta.yaml and docstrings with protocol changes](https://github.com/ably/specification/pull/375#issuecomment-3267638552)
  - Reminds the author that a protocol-bumping PR also needs to bump the spec and protocol major version in meta.yaml and update api-docstrings.
- **SimonWoolf** — [only change spec points whose requirements actually change](https://github.com/ably/specification/pull/375#discussion_r2331094892) (textile/features.textile:1445)
  - Argues that TM2f should not be changed because it describes how the SDK handles the timestamp, not its semantic meaning, which hasn't changed.
- **SimonWoolf** — [be explicit about absent/default field behaviour](https://github.com/ably/specification/pull/375#discussion_r2331121476) (textile/features.textile:1448)
  - The phrase 'may not be populated - see individual items' is too vague; spec needs to explicitly state the behaviour when the wire message lacks a serial and weighs the tradeoffs between making the field nullable vs. always initialising it for statically typed languages.
- **SimonWoolf** — [prefer concrete types over generic 'object'](https://github.com/ably/specification/pull/375#discussion_r2331126097) (textile/features.textile:1453)
  - Objects declared as generic 'object' should be typed as a concrete Dict<String, string> in the spec.
- **SimonWoolf** — [group added/deleted spec items for readability](https://github.com/ably/specification/pull/375#discussion_r2331129811) (textile/features.textile:1455)
  - Suggests grouping new items all before or all after deleted items rather than interspersing them to improve readability.
- **SimonWoolf** — [mark removed items as deleted per contributing guide](https://github.com/ably/specification/pull/375#discussion_r2331131937) (textile/features.textile:1461)
  - Flags that a removed item should be marked 'deleted' per the conventions rather than simply removed.
- **SimonWoolf** — [avoid broken/unnecessary cross-references](https://github.com/ably/specification/pull/375#discussion_r2331133335) (textile/features.textile:1464)
  - Notes a broken reference ('TM2a' doesn't exist) and suggests inlining the description rather than cross-referencing another spec item.
- **SimonWoolf** — [make default initialisation of fields explicit](https://github.com/ably/specification/pull/375#discussion_r2331134216) (textile/features.textile:1463)
  - Again asks for explicit default/initialisation behaviour (e.g. 'must set it to an empty Annotations object') rather than vague language about population.
- **SimonWoolf** — [avoid sentinel values that break documented invariants](https://github.com/ably/specification/pull/375#discussion_r2332686194) (textile/features.textile:1448)
  - Pushes back on using empty string as a sentinel for missing serial because it breaks the documented uniqueness invariant and is inconsistent with how other string fields (e.g. clientId) handle absence.
- **SimonWoolf** — [keep api-docstrings aligned with SDK docstrings](https://github.com/ably/specification/pull/375#discussion_r2334089225) (textile/api-docstrings.md:824)
  - The api-docstrings wording should match the docstring text used in SDK PRs, since the point of api-docstrings is to provide copy-pasteable text for SDK devs.

### PR #370 — [WIP] Rename `SyncObjectsPool` to `SyncObjectMessages` and clarify its type

- **lawrence-forooghian** — [keep spec body consistent with PR rationale](https://github.com/ably/specification/pull/370#discussion_r2323505792) (textile/objects-features.textile:122)
  - Points out that because the PR description explains needing information from the outer ObjectMessage, the referenced spec point and its subpoint probably need changing to reflect that.

### PR #356 — Clarify the rules for deriving the delta base payload

- **lawrence-forooghian** — [distinguish processed vs. unprocessed fields](https://github.com/ably/specification/pull/356#discussion_r2274026033) (textile/features.textile:807)
  - Clarifies the intended meaning: to derive the base payload, the unprocessed data property must be processed; asks what contradiction the reviewer sees.
- **SimonWoolf** — [preserve spec IDs on non-substantive rewords](https://github.com/ably/specification/pull/356#discussion_r2279119351) (textile/features.textile:816)
  - Argues that a reword-for-clarity (with added sub-items) doesn't require deprecating existing spec IDs — keep the old IDs for the rewritten content so SDK code comments referencing them don't all need updating.

### PR #353 — [PUB-1829] Add object-level write API spec for RealtimeObjects

- **lawrence-forooghian** — [track cross-PR consistency dependencies](https://github.com/ably/specification/pull/353#discussion_r2228017382) (textile/objects-features.textile:53)
  - Flags a cross-PR dependency: OOP5 needs to be updated to remove initialValueEncoding and make initialValue a string, presumably coordinated with another PR.
- **lawrence-forooghian** — [specify acceptable identifier formats](https://github.com/ably/specification/pull/353#discussion_r2228252389) (textile/objects-features.textile:77)
  - Asks for guidance on the acceptable format of an identifier — specifically, whether a UUID would suffice.
- **lawrence-forooghian** — [avoid specifying argument-type validation](https://github.com/ably/specification/pull/353#discussion_r2322400100) (textile/objects-features.textile:295)
  - Questions whether the spec should explicitly cover incorrect argument types in dynamically-typed languages; it bulks up the spec for something individual languages can reasonably handle themselves.
- **lawrence-forooghian** — [check for precedent of validation checks in spec](https://github.com/ably/specification/pull/353#discussion_r2322403110) (textile/objects-features.textile:295)
  - Follow-up noting he hasn't checked precedent but has seen many similar validation checks in LiveObjects PRs.

### PR #351 — chore: update `msgSerial` spec point

- **SimonWoolf** — [put behaviour in behavioural section, not field list](https://github.com/ably/specification/pull/351#pullrequestreview-3029647552)
  - Argues this sort of behavioural requirement does not belong in the TRxx section (which lists ProtocolMessage fields) but in RTN. RTN15g already implicitly covers it via 'clear the local connection state' and could be reworded to be explicit about what must be cleared.

### PR #350 — [PUB-1828] Add Objects spec for object and map entry tombstones, and OBJECT_DELETE message handling

- **lawrence-forooghian** — [state invariants linking related fields](https://github.com/ably/specification/pull/350#discussion_r2213873291) (textile/objects-features.textile:227)
  - Asks that a property be described as nullable and that the invariant ('non-null iff tombstone is true') be stated in the spec.
- **lawrence-forooghian** — [make IDL nullability match spec text](https://github.com/ably/specification/pull/350#discussion_r2213879980) (textile/features.textile:2596)
  - Points out that OM2j and RTLM8f1 imply this field should be nullable in the IDL.
- **lawrence-forooghian** — [enforce nullability consistency in IDL](https://github.com/ably/specification/pull/350#discussion_r2213889762) (textile/objects-features.textile:335)
  - Asks whether the IDL type should be Number? rather than Number, per OM2j and OME2d.
- **lawrence-forooghian** — [use domain types (Time) when semantics require](https://github.com/ably/specification/pull/350#discussion_r2213892736) (textile/features.textile:2596)
  - Asks whether the IDL type should be Time (rather than a generic number type) given the field is compared with locally-generated times per RTLM19a1.
- **lawrence-forooghian** — [align field types with semantic role](https://github.com/ably/specification/pull/350#discussion_r2213893351) (textile/objects-features.textile:114)
  - Asks whether Time is a more appropriate type for tombstonedAt fields.
- **lawrence-forooghian** — [state and assign ownership of invariants](https://github.com/ably/specification/pull/350#discussion_r2213895661) (textile/objects-features.textile:114)
  - Requests that the spec explicitly state the SDK maintains the invariant that this field is non-nil iff isTombstone is true.
- **lawrence-forooghian** — [justify differences in event-emission ordering](https://github.com/ably/specification/pull/350#discussion_r2216102186) (textile/objects-features.textile:199)
  - Asks why this spec point emits the event before applying OBJECT_DELETE but RTLM15d5 doesn't do the same; inconsistency suggests one is wrong.
- **lawrence-forooghian** — [define 'no action' precisely relative to side effects](https://github.com/ably/specification/pull/350#discussion_r2218718854) (textile/objects-features.textile:192)
  - Asks what 'without taking any action' means precisely: does it exclude updating siteTimeserials (RTLC7c)? Similar question for LiveMap.
- **lawrence-forooghian** — [apply clarifications across analogous methods](https://github.com/ably/specification/pull/350#discussion_r2218766989) (textile/objects-features.textile:192)
  - Extends prior question to 'replace data' methods, though notes those are already more clearly worded.
- **lawrence-forooghian** — [deduplicate checks via cross-reference](https://github.com/ably/specification/pull/350#discussion_r2222144492) (textile/objects-features.textile:249)
  - Asks whether this spec point and RTLM5d2a are just re-statements of the RTLM14 check, so the spec could defer to that check instead.
- **lawrence-forooghian** — [frame invariants as spec-maintained, not implementer-maintained](https://github.com/ably/specification/pull/350#discussion_r2322347934) (textile/objects-features.textile:227)
  - Proposes more explicit wording that frames the invariant as something the spec's own points maintain, not something implementers must figure out alone.

### PR #346 — [PUB-1827] Add Objects spec for subscriptions

- **lawrence-forooghian** — [define return values for API methods](https://github.com/ably/specification/pull/346#discussion_r2201363446) (textile/objects-features.textile:58)
  - Points out that RTLC6 and RTLM6 don't define a return value but seem to need one.
- **lawrence-forooghian** — [clarify identity stability of key objects](https://github.com/ably/specification/pull/346#discussion_r2201434895) (textile/objects-features.textile:39)
  - Suggests the spec clarify that the root LiveMap has stable identity and is not replaced, resolving an earlier ambiguity.

### PR #345 — Add IDL of Objects features

- **lawrence-forooghian** — [enumerate permitted types precisely in IDL](https://github.com/ably/specification/pull/345#discussion_r2322308507) (textile/objects-features.textile:273)
  - Proposes making the IDL return type for get() nullable, listing all permitted primitive/structured types (Boolean, Binary, Number, String, JsonArray, JsonObject, LiveCounter, LiveMap).
- **lawrence-forooghian** — [propagate type choices across related IDL methods](https://github.com/ably/specification/pull/345#discussion_r2322311447) (textile/objects-features.textile:275)
  - Proposes making entries() return a list of (key, nullable-value) pairs with the full type union, consistent with the get() suggestion.
- **lawrence-forooghian** — [unify IDL return-type conventions](https://github.com/ably/specification/pull/345#discussion_r2322312764) (textile/objects-features.textile:277)
  - Proposes making values() return a nullable list element with the full type union, for consistency with the preceding IDL changes.

### PR #343 — [PUB-1825, PUB-1826] Add spec for applying incoming OBJECT messages

- **lawrence-forooghian** — [identify unreachable branches as programmer error](https://github.com/ably/specification/pull/343#discussion_r2190855188) (textile/objects-features.textile:202)
  - Asks whether the described mismatch can ever actually occur under the spec's rules, or if it represents programmer error.
- **lawrence-forooghian** — [ensure fields used in checks are set in all paths](https://github.com/ably/specification/pull/343#discussion_r2192784482) (textile/objects-features.textile:212)
  - Highlights that semantics is only set during sync (RTO5c1b1b); for maps created in response to OBJECT messages, the check will always fail because semantics is null, so the spec probably needs to set semantics somewhere during OBJECT handling.
- **lawrence-forooghian** — [call out deferred behaviour explicitly](https://github.com/ably/specification/pull/343#discussion_r2193126548) (textile/objects-features.textile:84)
  - Asks whether OBJECT_DELETE handling is deferred to a later PR.

### PR #341 — Add Objects Access API spec

- **lawrence-forooghian** — [ensure return-shape mappings are consistent](https://github.com/ably/specification/pull/341#discussion_r2185835601) (textile/objects-features.textile:124)
  - Points out that since entries() does not return ObjectsMapEntry values, it presumably needs to apply the same mapping rule as RTLM5d2.
- **lawrence-forooghian** — [specify edge-case handling in iteration APIs](https://github.com/ably/specification/pull/341#discussion_r2185866646) (textile/objects-features.textile:124)
  - Asks how entries() handles edge cases: missing referenced object, unrecognised entry data; whether such entries are dropped or represented with a null/undefined value.
- **lawrence-forooghian** — [require consistent behaviour across related methods](https://github.com/ably/specification/pull/341#discussion_r2185912666) (textile/objects-features.textile:124)
  - Follow-up asking whether size() should behave consistently with whatever entries() does about missing entries.
- **lawrence-forooghian** — [use explicit sentinels for unrepresentable values](https://github.com/ably/specification/pull/341#discussion_r2322270792) (textile/objects-features.textile:124)
  - Notes that a LiveMap containing 'undefined' entries (as JS does) is confusing; suggests either explaining what undefined means or using a sentinel representing 'entry exists but unrepresentable'.

### PR #335 — Add spec for `ObjectMessage` encoding and decoding

- **lawrence-forooghian** — [don't introduce new explicit rules mid-PR](https://github.com/ably/specification/pull/335#issuecomment-2997577515)
  - Considers an ad-hoc request to be explicit that enum values are wire-encoded as their numeric value, and recommends not introducing such a requirement in this PR since it's implicit elsewhere (e.g. PresenceAction, ProtocolMessageAction).
- **lawrence-forooghian** — [avoid over-prescribing wire encoding](https://github.com/ably/specification/pull/335#discussion_r2152569949) (textile/features.textile:1647)
  - Asks whether the spec should prescribe which MessagePack numeric type (Float vs Integer) is used; suggests giving implementations flexibility to maximise fidelity when decoding.
- **lawrence-forooghian** — [cite RFCs and IDL types for precise semantics](https://github.com/ably/specification/pull/335#discussion_r2152592388) (textile/features.textile:1643)
  - Asks to be more precise than 'objects capable of JSON representation' — e.g. RFC4627 object or array types; IDL already defines JSONObject/JSONArray.
- **lawrence-forooghian** — [cover degenerate/missing cases explicitly](https://github.com/ably/specification/pull/335#discussion_r2152596068) (textile/features.textile:1658)
  - Asks what happens if none of the listed fields are populated when decoding, and whether that case is in scope of this PR.
- **lawrence-forooghian** — [align spec with practical encoder capabilities](https://github.com/ably/specification/pull/335#discussion_r2159705477) (textile/features.textile:1647)
  - Notes Swift can encode as float64 but JS may not have that control; suggests checking with the Realtime team about how prescriptive the spec needs to be for on-wire numeric type.
- **lawrence-forooghian** — [separate API-level and wire-level type rules](https://github.com/ably/specification/pull/335#discussion_r2322210600) (textile/features.textile:1647)
  - Asks how to word a spec requirement that ObjectData.number is float64 at the API level while the underlying MessagePack type may differ per SDK.
- **lawrence-forooghian** — [constrain public API, free wire-encoding choice](https://github.com/ably/specification/pull/335#discussion_r2322215886) (textile/features.textile:1647)
  - Clarifies conclusion: SDKs should have freedom over MessagePack encoding but the public API must constrain users to float64.

### PR #333 — [PUB-1041] OBJECT_SYNC spec

- **lawrence-forooghian** — [align new spec with prior analogous decision](https://github.com/ably/specification/pull/333#discussion_r2152297442) (textile/objects-features.textile:26)
  - Suggests aligning channel-mode-checking behaviour with the annotations decision in RTAN4e — only check against server-granted modes, and allow SDKs to warn-log instead of throwing an error, motivated by type-system differences across languages.
- **lawrence-forooghian** — [remove ambiguity about waiting conditions](https://github.com/ably/specification/pull/333#discussion_r2152307145) (textile/objects-features.textile:21)
  - Points out that 'waits for sync to complete' is too vague: applies when no sync is in progress? conditions for in-progress? which sync sequence it waits for?
- **lawrence-forooghian** — [specify initial state of introduced objects](https://github.com/ably/specification/pull/333#discussion_r2152312933) (textile/objects-features.textile:32)
  - Asks how the root LiveObject is initialised upon pool creation.
- **lawrence-forooghian** — [define data-structure roles precisely](https://github.com/ably/specification/pull/333#discussion_r2152321056) (textile/objects-features.textile:39)
  - Asks whether SyncObjectsPool is a second ObjectsPool used for staging during sync to achieve atomicity.
- **lawrence-forooghian** — [specify map key semantics](https://github.com/ably/specification/pull/333#discussion_r2152327485) (textile/objects-features.textile:49)
  - Asks whether the pool is keyed by ObjectState.objectId.
- **lawrence-forooghian** — [choose precise verbs for data-mutation semantics](https://github.com/ably/specification/pull/333#discussion_r2152330751) (textile/objects-features.textile:52)
  - Objects to the word 'override' because it implies data is shadowed rather than replaced; 'replace' better captures that internal data is being overwritten.
- **lawrence-forooghian** — [define types before first reference](https://github.com/ably/specification/pull/333#discussion_r2152333487) (textile/objects-features.textile:95)
  - Asks whether LiveObject is defined later, since it isn't defined at the point of first use.
- **lawrence-forooghian** — [cross-link implicit inputs to their definition](https://github.com/ably/specification/pull/333#discussion_r2152340117) (textile/objects-features.textile:141)
  - Asks how the LiveMap semantics are determined when applying an operation — presumably via the private semantics field from RTO5c1b1b.
- **lawrence-forooghian** — [use the precise type name consistently](https://github.com/ably/specification/pull/333#discussion_r2152344690) (textile/objects-features.textile:123)
  - Recommends replacing 'serial' with 'timeserial' consistently where the spec refers to the timeserial type, since 'serial' is ambiguous.
- **lawrence-forooghian** — [design structures for future spec points](https://github.com/ably/specification/pull/333#discussion_r2152351304) (textile/objects-features.textile:124)
  - Checks understanding that MAP_* operations will also apply to OBJECT ProtocolMessages in future spec work, which explains the current structure.
- **lawrence-forooghian** — [state operation arguments explicitly](https://github.com/ably/specification/pull/333#discussion_r2152354953) (textile/objects-features.textile:124)
  - Asks the author to spell out the arguments an operation takes (e.g. timeserial and data) rather than leaving them implicit.
- **lawrence-forooghian** — [split conditionals into subclauses](https://github.com/ably/specification/pull/333#discussion_r2152356408) (textile/objects-features.textile:132)
  - Proposes rewording to split conditional into a clear 'discard if precondition fails, otherwise apply' structure, with cross-reference to the precondition rule.
- **lawrence-forooghian** — [simplify when behaviour is equivalent to a primitive](https://github.com/ably/specification/pull/333#discussion_r2152365774) (textile/objects-features.textile:121)
  - Asks whether the described process is really just entry replacement, and if so whether the long-winded wording could be simplified.
- **lawrence-forooghian** — [cross-reference related spec points](https://github.com/ably/specification/pull/333#discussion_r2152368733) (textile/objects-features.textile:129)
  - Proposes rewording to say that the spec creates a zero-value LiveObject for the given objectId in the internal ObjectsPool, cross-referring to the pool spec.
- **lawrence-forooghian** — [specify initial private-state values](https://github.com/ably/specification/pull/333#discussion_r2152377817) (textile/objects-features.textile:86)
  - Notes the spec doesn't set initial values for private properties (siteTimeserials, createOperationIsMerged, semantics) and asks whether it should.
- **lawrence-forooghian** — [accompany error codes with status codes](https://github.com/ably/specification/pull/333#discussion_r2152430253) (textile/objects-features.textile:20)
  - Requests that every spec point which instructs throwing an error also state the accompanying statusCode.
- **lawrence-forooghian** — [keep spec and typings consistent on value shapes](https://github.com/ably/specification/pull/333#discussion_r2164561055) (textile/objects-features.textile:110)
  - Notes inconsistency: OD5b3 says ObjectData.string may be a JSON object/array, but JS typings for LiveMap.get don't expose that possibility, and asks whether it should.
- **lawrence-forooghian** — [define 'exists' precisely for each context](https://github.com/ably/specification/pull/333#discussion_r2167152480) (textile/objects-features.textile:143)
  - Asks whether 'exists' in these spec points means non-null or also non-empty (cf. RTLM9b).
- **lawrence-forooghian** — [spec assumes single-threaded execution model](https://github.com/ably/specification/pull/333#discussion_r2177422727) (textile/objects-features.textile:87)
  - Reminds reviewers that the features spec has historically assumed a single-threaded world, leaving concurrency to individual platforms.
- **lawrence-forooghian** — [treat absent and false separately in spec](https://github.com/ably/specification/pull/333#discussion_r2183327198) (textile/objects-features.textile:115)
  - Points out that 'false' isn't the only missing-value case; the field could also be absent.
- **lawrence-forooghian** — [clarify replace-vs-mutate semantics](https://github.com/ably/specification/pull/333#discussion_r2183493458) (textile/objects-features.textile:37)
  - Asks for clarification: is the root LiveMap replaced on sync, or is its internal data manipulated in place?
- **lawrence-forooghian** — [consider implicit-attach behaviour in access APIs](https://github.com/ably/specification/pull/333#discussion_r2243107561) (textile/objects-features.textile:18)
  - Reports being caught out by a method hanging because the channel wasn't attached; asks whether JS does implicit attach here.
- **lawrence-forooghian** — [core-SDK features warrant implicit attach](https://github.com/ably/specification/pull/333#discussion_r2244657679) (textile/objects-features.textile:18)
  - Argues that Objects is a core-SDK feature (like presence.enter) and therefore should arguably have implicit-attach behaviour like presence enters.
- **lawrence-forooghian** — [use identical names for identical values](https://github.com/ably/specification/pull/333#discussion_r2323522273) (textile/objects-features.textile:123)
  - Points out that two different spec points use 'ObjectsMapEntry.timeserial' and 'operation's serial' for the same value and it isn't obvious they refer to the same thing.

### PR #332 — Add spec points to describe the `Objects` plugin

- **lawrence-forooghian** — [leave plugin internals to SDK implementations](https://github.com/ably/specification/pull/332#discussion_r2150552581) (textile/features.textile:389)
  - Rejects referring to an 'ObjectsPlugin' interface that neither exists nor should be cross-SDK uniform; proposes wording that explicitly leaves the plugin object's type and integration mechanism up to each implementation.
- **lawrence-forooghian** — [defer idiomatic error handling to SDKs](https://github.com/ably/specification/pull/332#discussion_r2150559552) (textile/features.textile:782)
  - Suggests mentioning that SDKs handle access to the objects property without the plugin in a language-idiomatic way (throwing an ErrorInfo or a language-appropriate programmer error).
- **lawrence-forooghian** — [keep plugin specs loose and non-exhaustive](https://github.com/ably/specification/pull/332#pullrequestreview-2932983713)
  - Sets expectation that plugin spec can be loose and non-exhaustive because plugin mechanism varies by implementation.

### PR #331 — Message/PresenceMessage/Annotation size

- **SimonWoolf** — [factor out duplicated spec into single reference](https://github.com/ably/specification/pull/331#discussion_r2143300144) (textile/features.textile:1665)
  - Questions copying and pasting identical spec points across Message, PresenceMessage and Annotation; suggests writing it once and referencing it from the other types so the shared implementation is obvious.
- **SimonWoolf** — [use RFC-2119 MUST/MAY precisely](https://github.com/ably/specification/pull/331#discussion_r2143315807) (textile/features.textile:1659)
  - Emphasises the distinction between MUST and MAY per RFC 2119: optional behaviour that we aren't allocating effort to should be MAY, not be elevated to a requirement for spec-version adherence.
- **SimonWoolf** — [use identical wording for analogous size calculations](https://github.com/ably/specification/pull/331#discussion_r2150363207) (textile/features.textile:1458)
  - Argues the same wording ('UTF-8 encoded length in bytes') should be used for all string-size components (name, clientId, data, json-encoded extras) for consistency and correctness over the wire.

### PR #328 — Update internal Objects interface names to have Object*/Objects* prefix

- **lawrence-forooghian** — [use plural-feature prefix for feature-scoped types](https://github.com/ably/specification/pull/328#discussion_r2136056563) (textile/features.textile:1497)
  - Argues that singular-'Object' prefix makes sense only for types describing a generic object (ObjectOperation, ObjectState); for concrete type-specific names, the plural 'Objects' prefix would clarify that the type belongs to the Objects feature.
- **lawrence-forooghian** — [choose names that convey feature membership](https://github.com/ably/specification/pull/328#discussion_r2136059010) (textile/features.textile:1497)
  - Illustrates the naming concern: 'ObjectCounter' reads as 'a counter of objects', whereas 'ObjectsCounter' signals membership in the Objects feature.
- **lawrence-forooghian** — [use spec-level namespaces for feature grouping](https://github.com/ably/specification/pull/328#discussion_r2136063956) (textile/features.textile:1497)
  - Proposes introducing a namespace ('Objects.Counter' etc.) in the spec to clarify grouping, letting each SDK adapt the syntax to its language.
- **lawrence-forooghian** — [rename minimally; don't propagate local conflicts](https://github.com/ably/specification/pull/328#discussion_r2145256764) (textile/features.textile:1497)
  - Argues that if only two ably-js types are problematic, rename only those two rather than prefixing every LiveObjects type; questions why JS used 'ObjectCounter' at all.

### PR #327 — Update ObjectData value properties spec to match latest implementation

- **lawrence-forooghian** — [tombstone or edit based on implementation maturity](https://github.com/ably/specification/pull/327#discussion_r2136038291) (textile/features.textile:1555)
  - Suggests judgement-based approach to spec edits vs. tombstones: if the spec point being replaced is recent (i.e. not yet widely implemented), edit in place; otherwise tombstone.

### PR #318 — Add side effects of more connection states for `DETACHING` channels

- **lawrence-forooghian** — [make error propagation between layers explicit](https://github.com/ably/specification/pull/318#issuecomment-2900662464)
  - Notes open question: should connection errors propagate into channel error, and should this be made explicit for other RTL4* spec points that omit it.

### PR #315 — Fix documentation of `deviceIdentityToken`

- **lawrence-forooghian** — [record clarifications that disambiguate overloaded terms](https://github.com/ably/specification/pull/315#discussion_r2069091092) (textile/api-docstrings.md:832)
  - Clarifies for future readers that 'authentication' in this passage refers to device authentication, not user authentication.

### PR #312 — Remove RTL4e

- **SimonWoolf** — [skip version tombstones for clarity-only rewords](https://github.com/ably/specification/pull/312#pullrequestreview-2794460297)
  - Argues that the 'valid up to and including specification version X' tombstone language is unnecessary for changes that merely improve clarity without altering expected behaviour.

### PR #311 — Clarify when connection state should fail `ACK`-pending messages

- **lawrence-forooghian** — [keep PRs scoped; defer unrelated wording tweaks](https://github.com/ably/specification/pull/311#discussion_r2064127389) (textile/features.textile:515)
  - Declines to expand scope to include language tweaks on a focused PR; invites a separate PR for those edits.

### PR #308 — Simplify language of `queueMessages` condition

- **lawrence-forooghian** — [don't state client-option defaults inconsistently](https://github.com/ably/specification/pull/308#discussion_r2064110639) (textile/features.textile:706)
  - States that the spec generally does not mention default values of client options; if it did so it should be done consistently, so the current PR won't introduce a one-off mention.

### PR #302 — Make `endpoint` special-case `localhost` and IP addresses

- **lawrence-forooghian** — [add new spec point instead of mutating existing one](https://github.com/ably/specification/pull/302#discussion_r2050493860) (textile/features.textile:78)
  - Argues that any modification to a spec point — even an additive one — should introduce a new point rather than edit in place, so tooling claims of 'full spec point implemented' remain accurate. Acknowledges occasional bending of the rule.
- **lawrence-forooghian** — [follow documented spec-modification process](https://github.com/ably/specification/pull/302#discussion_r2054014922) (textile/features.textile:78)
  - Points to CONTRIBUTING.md's process for spec modifications and reflects: tombstones clutter, the versioning/release process exists but is under-used, and external references to spec points (e.g. Slack) cannot retroactively carry version context.

### PR #301 — Readability tweaks for new domain logic

- **lawrence-forooghian** — [explain wording intent via commit messages](https://github.com/ably/specification/pull/301#discussion_r2056402046) (textile/features.textile:96)
  - Cites the commit message explaining that prior wording implied the primary domain equals the routing policy name when in fact it doesn't; invites reviewer to push back.
- **lawrence-forooghian** — [keep parallel spec points stylistically consistent](https://github.com/ably/specification/pull/301#discussion_r2056408000) (textile/features.textile:83)
  - Proposes rewording REC1c to match REC1b4 style using bracketed 'id' notation, so all derived-from-routing-policy-id points are consistent.
- **lawrence-forooghian** — [define and cite terminology decisions](https://github.com/ably/specification/pull/301#discussion_r2056485082) (textile/features.textile:83)
  - Distinguishes routing policy 'name' (nonprod:[id]) from routing policy 'id' (the id component), attributing the terminology to a prior Slack discussion referenced in the commit.
- **lawrence-forooghian** — [abstract over varying formulations for consistency](https://github.com/ably/specification/pull/301#discussion_r2056500896) (textile/features.textile:96)
  - Explains that fallback-host spec points are written in terms of 'primary domain' so they stay consistent across points that aren't phrased in terms of endpoint, but offers to rephrase if reviewer finds it confusing.
- **lawrence-forooghian** — [align terminology across stakeholders](https://github.com/ably/specification/pull/301#discussion_r2056531350) (textile/features.textile:83)
  - Asks reviewer to agree naming terminology with two other team members so the spec wording can be settled.

### PR #299 — Reword channel state publish conditions

- **lawrence-forooghian** — [don't couple publish semantics to attach state](https://github.com/ably/specification/pull/299#discussion_r2053977423) (textile/features.textile:703)
  - Notes that from the SDK's perspective being attached is unrelated to publishing, referencing transient publish docs.
- **lawrence-forooghian** — [clarify reword-only PRs don't change behaviour](https://github.com/ably/specification/pull/299#discussion_r2053979144) (textile/features.textile:703)
  - Reminds reviewer that this PR is a rewording only and does not change behaviour.

### PR #296 — Specify the behaviour of `#connect` when `CONNECTING`

- **lawrence-forooghian** — [don't delete foundational behaviour statements](https://github.com/ably/specification/pull/296#discussion_r2048866960) (textile/features.textile:529)
  - Points out that after the proposed edit there's no spec point stating that calling #connect actually triggers a connection attempt, so the basic behaviour is lost.

### PR #292 — Support annotations

- **SimonWoolf** — [keep test/infrastructure fixtures out of features spec](https://github.com/ably/specification/pull/292#issuecomment-2959911340)
  - Argues the features spec should not specify fixture/test setup details like creating namespaces for mutable messages; such things belong outside the features spec.
- **lawrence-forooghian** — [treat enum renames as breaking changes](https://github.com/ably/specification/pull/292#discussion_r2045092745) (textile/api-docstrings.md:624)
  - Questions whether renaming an enum case is a breaking change for users relying on the old name.
- **lawrence-forooghian** — [isolate bug fixes from feature PRs](https://github.com/ably/specification/pull/292#discussion_r2045101056) (textile/features.textile:788)
  - Asks whether a subtle change included in this PR is actually a latent bug fix affecting existing users, suggesting it should be split into its own PR.
- **lawrence-forooghian** — [distinguish parameter names from what they represent](https://github.com/ably/specification/pull/292#discussion_r2045122958) (textile/features.textile:426)
  - Suggests rewording so the text distinguishes between the parameter name 'messageSerial' and what it semantically represents (the Message's serial), to make downstream spec points intelligible.
- **lawrence-forooghian** — [justify asymmetries between related operations](https://github.com/ably/specification/pull/292#discussion_r2045165536) (textile/features.textile:432)
  - Asks whether the asymmetry — client-side size check for message publishes but not for annotation publishes/deletes — is intentional, and likewise for realtime.
- **lawrence-forooghian** — [specify statusCode alongside error codes](https://github.com/ably/specification/pull/292#discussion_r2045180736) (textile/features.textile:935)
  - Asks what statusCode accompanies the error code cited in the spec point.
- **lawrence-forooghian** — [extend idempotency semantics consistently](https://github.com/ably/specification/pull/292#discussion_r2045208681) (textile/features.textile:432)
  - Asks whether library-generated idempotency keys should be supported for REST annotation publishing, by analogy with messages (RSL1k1).
- **lawrence-forooghian** — [update global ACK/protocol lists for new message types](https://github.com/ably/specification/pull/292#discussion_r2045211221) (textile/features.textile:943)
  - Notes that RTN7a (which lists ACK-requiring ProtocolMessage types) needs to be updated to include annotations.
- **lawrence-forooghian** — [name the exact trigger for listener callbacks](https://github.com/ably/specification/pull/292#discussion_r2045216543) (textile/features.textile:948)
  - Requests explicit wording about what triggers listener invocation — presumably receipt of an ANNOTATION ProtocolMessage.
- **lawrence-forooghian** — [acknowledge best-effort nature of client-side checks](https://github.com/ably/specification/pull/292#discussion_r2045250422) (textile/features.textile:935)
  - Raises three concerns: whether adding the listener becomes async, whether attach should be implicit, and that the check is inherently best-effort because attachOnSubscribe may be off or the attach may fail.
- **lawrence-forooghian** — [minimise overlapping terms for related concepts](https://github.com/ably/specification/pull/292#discussion_r2045323098) (textile/api-docstrings.md:696)
  - Argues that introducing a third term 'aggregation type' alongside 'annotation type' and 'aggregation method' is confusing; suggests collapsing to 'aggregation method'.
- **lawrence-forooghian** — [link to external docs only when they exist](https://github.com/ably/specification/pull/292#discussion_r2045333276) (textile/api-docstrings.md:696)
  - Questions whether the referenced aggregation-types documentation is in scope for this PR and whether an existing docs URL could be linked.
- **lawrence-forooghian** — [match spec to actual language typings](https://github.com/ably/specification/pull/292#discussion_r2045352245) (textile/api-docstrings.md:775)
  - Points out that JS typings treat the union as exhaustive and do not allow a generic JSON object fallback in Message.summary, contradicting the spec's implied looseness.
- **lawrence-forooghian** — [document key schemas in map-like types](https://github.com/ably/specification/pull/292#discussion_r2045364069) (textile/api-docstrings.md:771)
  - Asks for explanation of what the map keys are and how they relate to Annotation.type.
- **lawrence-forooghian** — [specify enum extensibility and unknown-value handling](https://github.com/ably/specification/pull/292#discussion_r2045375887) (textile/features.textile:2522)
  - Asks whether the enum is frozen or is expected to grow, and how SDKs should represent an unknown action value in the emitted Annotation.
- **lawrence-forooghian** — [design types for strongly-typed languages too](https://github.com/ably/specification/pull/292#discussion_r2045398430) (textile/features.textile:2562)
  - Raises concern that a loose JSON-object type pushes work onto users in strongly-typed languages like Swift; proposes exposing SummaryEntry variants as public API so SDKs or users can convert from a JSONObject to a typed value.
- **lawrence-forooghian** — [avoid colliding with field names in prose](https://github.com/ably/specification/pull/292#discussion_r2045402241) (textile/api-docstrings.md:702)
  - Warns that the phrase 'typically some name' invites confusion with the Annotation's 'name' property and suggests avoiding the overlap.
- **lawrence-forooghian** — [define 'ignore' concretely per type](https://github.com/ably/specification/pull/292#discussion_r2046933547) (textile/features.textile:2522)
  - Notes that RTF1 says unrecognised values 'must be ignored' but that 'ignoring' an unrecognised AnnotationAction is not a meaningful instruction and needs more precise wording.
- **SimonWoolf** — [use MAY for optional behaviours lacking consensus](https://github.com/ably/specification/pull/292#discussion_r2047667506) (textile/features.textile:432)
  - Observes that presence messages are also exempt from client-side size checks, that adding one universally would be the right approach, and suggests specifying it as MAY rather than MUST for now.
- **SimonWoolf** — [permit rename when field is not yet publicly relied on](https://github.com/ably/specification/pull/292#discussion_r2047667603) (textile/api-docstrings.md:624)
  - Cross-references an explanation that although enum renaming is technically a breaking change, Message.action was only recently introduced, isn't in main public docs, and is unlikely to have users relying on it.
- **lawrence-forooghian** — [separate bug fixes into their own PR with context](https://github.com/ably/specification/pull/292#discussion_r2049305455) (textile/features.textile:788)
  - Asks that the bug-fix change be pulled into a separate PR with an explanatory commit message so it can be merged independently.
- **lawrence-forooghian** — [prefer specific types plus JSON fallback to union-of-unknown](https://github.com/ably/specification/pull/292#discussion_r2049318091) (textile/api-docstrings.md:775)
  - Challenges the value of including `unknown` in a union type for Message.summary and proposes keeping individual SummaryEntry types but dropping the aggregated union, in favour of a JSON object.
- **lawrence-forooghian** — [put cross-SDK types into spec, not just typings](https://github.com/ably/specification/pull/292#discussion_r2049327942) (textile/features.textile:2562)
  - Proposes adding the TypeScript SummaryEntry sub-types to the spec and adding a spec point requiring a user-driven mechanism for converting Message.summary into a selected typed variant.
- **lawrence-forooghian** — [avoid error paths that reinforce deprecated mental models](https://github.com/ably/specification/pull/292#discussion_r2049343840) (textile/features.textile:935)
  - Questions whether to keep this error at all: it reinforces the attach/subscribe mental model that internal work is trying to move away from, so may confuse users.
- **SimonWoolf** — [use object signature for JSON fallbacks in unions](https://github.com/ably/specification/pull/292#discussion_r2049348184) (textile/api-docstrings.md:775)
  - Explains that `| unknown` collapses the union and proposes `| {[k: string]: unknown}` instead so go-to-type still works; argues the union type itself remains useful.
- **SimonWoolf** — [justify checks independent of attach state](https://github.com/ably/specification/pull/292#discussion_r2049355195) (textile/features.textile:935)
  - Argues that the subscribe-mode check is valid regardless of attach state and could even be based on requested modes alone; not primarily about implicit attach.
- **lawrence-forooghian** — [annotate non-obvious type choices in IDL/typings](https://github.com/ably/specification/pull/292#discussion_r2049360146) (textile/api-docstrings.md:775)
  - Accepts the proposed typing and suggests adding a comment alongside the TS union definition explaining its purpose, to deter future contributors from removing it.
- **lawrence-forooghian** — [consider documentation implications of error conditions](https://github.com/ably/specification/pull/292#discussion_r2049366076) (textile/features.textile:935)
  - Argues that any documentation of the error condition has to mention the channel being attached, which risks cementing the attach/subscribe relation in users' minds.
- **lawrence-forooghian** — [spec must match real SDK behaviour on unknown enums](https://github.com/ably/specification/pull/292#discussion_r2049389414) (textile/features.textile:2522)
  - Observes that SDKs currently mishandle unknown enum values (e.g. JS populates an 'always-populated' field with undefined; Swift/Cocoa lets invalid C enum values through); shows that the spec's handling of unknown enums isn't actually implemented.
- **SimonWoolf** — [treat dev-aid exceptions as convenience, not contract](https://github.com/ably/specification/pull/292#discussion_r2054238164) (textile/features.textile:935)
  - Argues that the exception is a convenience to help developers catch misconfiguration (wrong mode) early; the underlying programmer error is not requesting the right mode, not the exception itself. Does not plan exhaustive documentation of the exception conditions.
- **SimonWoolf** — [scope spec change narrowly, defer broader cleanup](https://github.com/ably/specification/pull/292#discussion_r2054243035) (textile/features.textile:2522)
  - Acknowledges SDKs are inconsistent on unknown-enum handling and that harmonising the behaviour is a good idea but outside this PR's scope.
- **lawrence-forooghian** — [allow language-idiomatic error vs. warning choice](https://github.com/ably/specification/pull/292#discussion_r2054800114) (textile/features.textile:935)
  - Argues that throwing an error for bad channel modes fits neither programmer-error nor runtime-error categories in Swift; prefers that the spec allow a warn log as an alternative, so SDKs can adopt what's idiomatic for their language.
- **SimonWoolf** — [allow language-idiomatic error handling choice](https://github.com/ably/specification/pull/292#discussion_r2055473046) (textile/features.textile:935)
  - Accepts making the subscribe error discretionary; reflects on how JS's async functions collapse programmer and runtime errors into promise rejection, which is sometimes worse for API clarity.
- **lawrence-forooghian** — [verify split-out PRs actually land](https://github.com/ably/specification/pull/292#discussion_r2095217305) (textile/features.textile:788)
  - Follows up asking whether the PR that was supposed to pull out an unrelated change was ever opened.
- **lawrence-forooghian** — [keep docstrings and IDL in sync with spec](https://github.com/ably/specification/pull/292#discussion_r2095278377) (textile/features.textile:2562)
  - Asks author to update the docstrings and IDL to match the newly-agreed spec wording.
- **SimonWoolf** — [honour prior ADR/RTF decisions absent strong justification](https://github.com/ably/specification/pull/292#discussion_r2136039216) (textile/api-docstrings.md:706)
  - Rejects a field-rename request because the name was agreed in an ADR and RTF and is already in a released ably-js version; absent strong justification, PRs documenting agreed APIs should not rename fields.
- **SimonWoolf** — [prefer user-selected decoder over auto-detection](https://github.com/ably/specification/pull/292#discussion_r2138291502) (textile/features.textile:2562)
  - Explains the pattern Lawrence proposed: explicit per-aggregation decoder functions taking a JsonObject, with the user responsible for picking the right one. Contrasts with an auto-detection API that was considered and rejected.
- **SimonWoolf** — [spec suggests capabilities, not specific method shape](https://github.com/ably/specification/pull/292#discussion_r2138302750) (textile/api-docstrings.md:791)
  - Accepts that TM7 can be loosened to not require static factory methods on Message, but instead to suggest SDK-idiomatic utility methods.
- **SimonWoolf** — [spec defines intent, tolerates minor implementation detail](https://github.com/ably/specification/pull/292#discussion_r2138314467) (textile/features.textile:438)
  - Clarifies that as far as the spec is concerned publish() produces CREATEs and delete() produces DELETEs; the ably-js implementation detail of delete() calling publish() is a non-material deviation.
- **SimonWoolf** — [spec only lists errors when SDK behaviour differs](https://github.com/ably/specification/pull/292#discussion_r2138325201) (textile/features.textile:443)
  - Argues that listing error codes belongs in user documentation, not the features spec, unless SDK behaviour varies by code.
- **SimonWoolf** — [choose method names that convey side effects](https://github.com/ably/specification/pull/292#discussion_r2138369179) (textile/features.textile:438)
  - Argues that 'create()' sounds like a constructor and not like a method that publishes to a channel, so it would be the wrong name for publish().

### PR #282 — chat single channel

- **lawrence-forooghian** — [stack PRs to enable downstream implementation testing](https://github.com/ably/specification/pull/282#issuecomment-2759056840)
  - Requests that the PR be rebased on top of another open PR so that a combined branch exists which a spec conformance tool can be pointed at for downstream implementation work.
- **lawrence-forooghian** — [state baselines explicitly before describing deviations](https://github.com/ably/specification/pull/282#discussion_r2012149261) (textile/chat-features.textile:441)
  - Challenges the word 'omitted' because the surrounding spec does not state which channel modes are the baseline, so 'omitted from what?' is ambiguous.
- **lawrence-forooghian** — [consolidate duplicated facts into single source of truth](https://github.com/ably/specification/pull/282#discussion_r2012264825) (textile/chat-features.textile:272)
  - If all chat features now share a single channel, that should be stated in one authoritative spec point naming the channel, and the per-feature spec points redundantly naming channels should be removed.
- **lawrence-forooghian** — [cascade consolidation edits across related spec points](https://github.com/ably/specification/pull/282#discussion_r2012405501) (textile/chat-features.textile:447)
  - Asks whether CHA-T1 also needs updating or removing as part of the consolidation of channel-naming spec points.
- **lawrence-forooghian** — [every testable point needs a concrete test strategy](https://github.com/ably/specification/pull/282#discussion_r2012729669) (textile/chat-features.textile:277)
  - Notes that he cannot think of a way to test this spec point and asks what the author had in mind.
- **lawrence-forooghian** — [every new error code must have a referenced use](https://github.com/ably/specification/pull/282#discussion_r2012734358) (textile/chat-features.textile:988)
  - Questions the purpose of a newly added error code that isn't referenced elsewhere, and asks whether the existing spec point referring to the numeric code should be updated to use the new symbolic name.
- **lawrence-forooghian** — [check cross-references when removing spec items](https://github.com/ably/specification/pull/282#discussion_r2012736557) (textile/chat-features.textile:1082)
  - Flags that an error being removed is still referred to elsewhere in the spec.
- **lawrence-forooghian** — [remove untestable conditionals with no contrast case](https://github.com/ably/specification/pull/282#discussion_r2013976878) (textile/chat-features.textile:444)
  - Argues for dropping a conditional ('if no modes have been explicitly set yet') because the condition cannot be tested: nowhere else in the spec sets channel modes, so the condition is trivially always true.
- **lawrence-forooghian** — [mark informative text as non-normative](https://github.com/ably/specification/pull/282#discussion_r2014084666) (textile/chat-features.textile:115)
  - Requests that informative (non-normative) descriptions of internal flags be explicitly marked as informative, with the actual manipulation specified in subsequent spec points.
- **lawrence-forooghian** — [specify initial values for declared state](https://github.com/ably/specification/pull/282#discussion_r2014086151) (textile/chat-features.textile:116)
  - Asks what the initial value of the described field is.
- **lawrence-forooghian** — [prefer direct wording when conditionals add no testable branch](https://github.com/ably/specification/pull/282#discussion_r2014193261) (textile/chat-features.textile:444)
  - Proposes exact replacement wording that removes the ambiguous conditional because no other place in the Chat SDK sets channel modes, so making the condition explicit is misleading.
- **lawrence-forooghian** — [preserve tombstones when editing surrounding spec](https://github.com/ably/specification/pull/282#discussion_r2014369024) (textile/chat-features.textile:138)
  - Points out that a tombstone marker for a removed spec point was accidentally dropped in the edit.
- **lawrence-forooghian** — [spell out exact error source and derivation](https://github.com/ably/specification/pull/282#discussion_r2014648736) (textile/chat-features.textile:150)
  - Proposes a rewording clarifying that on failure the detach error is an ErrorInfo from the underlying channel operation and the room status is derived from the current channel state.
- **lawrence-forooghian** — [only tag leaf behaviours as Testable](https://github.com/ably/specification/pull/282#discussion_r2014844456) (textile/chat-features.textile:168)
  - Argues that a spec point tagged 'Testable' is actually just an overview of its subpoints rather than a testable behaviour and should therefore not be marked Testable.
- **lawrence-forooghian** — [question whether timeouts apply in error branches](https://github.com/ably/specification/pull/282#discussion_r2014948411) (textile/chat-features.textile:171)
  - Asks whether it's intentional that a fixed 250ms wait still applies even when detach() caused the channel to enter FAILED, because that behaviour may be surprising.
- **lawrence-forooghian** — [name specific flags and error fields precisely](https://github.com/ably/specification/pull/282#discussion_r2016749092) (textile/chat-features.textile:233)
  - Proposes a rewording that clarifies the discontinuity event emission conditions by naming the flags explicitly and naming the ErrorInfo fields.
- **lawrence-forooghian** — [flag dead/unreachable state in spec](https://github.com/ably/specification/pull/282#discussion_r2017488723) (textile/chat-features.textile:115)
  - Observes that a flag appears to only ever be set to false and never flipped to true, suggesting it is vestigial or mis-specified.
- **lawrence-forooghian** — [optimise current readability over future-proofing wording](https://github.com/ably/specification/pull/282#discussion_r2033301892) (textile/chat-features.textile:444)
  - Prefers keeping the spec immediately understandable (removing a confusing conditional) and tightening language later if future features need the broader form, rather than leaving aspirational wording now.
- **lawrence-forooghian** — [disambiguate overloaded SDK terminology in spec](https://github.com/ably/specification/pull/282#discussion_r2036064674) (textile/chat-features.textile:228)
  - Suggests saying 'non-UPDATE channel state events' rather than 'channel state change' because the core SDK term is ambiguous and can refer to both state transitions and UPDATE events.
- **lawrence-forooghian** — [link clauses to their antecedent definitions](https://github.com/ably/specification/pull/282#discussion_r2036066337) (textile/chat-features.textile:230)
  - Proposes rewording to tie the clause explicitly back to the events defined in the preceding spec point and to drop an unintended no-op mention.
- **lawrence-forooghian** — [state no-op behaviour explicitly](https://github.com/ably/specification/pull/282#discussion_r2036066909) (textile/chat-features.textile:229)
  - Suggests rewording to clarify that the operation itself is a no-op when a channel state event is received while a room lifecycle operation is in progress.
- **lawrence-forooghian** — [enumerate subscribed event kinds explicitly](https://github.com/ably/specification/pull/282#discussion_r2036072139) (textile/chat-features.textile:232)
  - Suggests clarifying which underlying channel state events are subscribed to (UPDATE and ATTACHED).
- **lawrence-forooghian** — [use named properties instead of vague phrases](https://github.com/ably/specification/pull/282#discussion_r2036072351) (textile/chat-features.textile:233)
  - Proposes a rewording that names specific properties like hasAttachedOnce and isExplicitlyDetached to make the discontinuity-event emission rules exact.

### PR #281 — fix: updated `RTN11` spec point

- **SimonWoolf** — [avoid redundant coverage of the same state](https://github.com/ably/specification/pull/281#pullrequestreview-2685460357)
  - Points out that RTN11b already covers the CLOSING state, so duplicate handling may exist above.
- **SimonWoolf** — [prefer self-contained per-branch action lists](https://github.com/ably/specification/pull/281#pullrequestreview-2686364070)
  - Observes that the surrounding spec area mixes two patterns: an overarching clause (RTN11a) combined with per-branch additional actions, instead of each branch listing the full set of actions for its state. Prefers the latter pattern but is willing to accept the inconsistency rather than widen the PR.

### PR #280 — Add `ACTIVATE` ProtocolMessage Action

- **SimonWoolf** — [mark deprecated protocol actions explicitly](https://github.com/ably/specification/pull/280#issuecomment-2721136258)
  - Advised not documenting ACTIVATE because it is deprecated and should not be implemented; suggested the placeholder "(reserved for a deprecated use)".

### PR #279 — [PUB-925] Add new protocol message flags, actions, channel modes and message types for Objects

- **SimonWoolf** — [exclude transport-specific fields irrelevant to SDK spec](https://github.com/ably/specification/pull/279#discussion_r1996035652) (textile/features.textile:1420)
  - Agreed that no `channel` field exists on Message/PresenceMessage in the Ably wire protocol (only in SSE, which is out of scope for SDK spec).
- **SimonWoolf** — [use precise enumerated operation names](https://github.com/ably/specification/pull/279#discussion_r1996039339) (textile/features.textile:1448)
  - Asked for unambiguous operation names rather than the phrase "objects create"; suggested explicitly listing COUNTER_CREATE and MAP_CREATE.
- **SimonWoolf** — [keep flag/mode numbers in sync with protocol](https://github.com/ably/specification/pull/279#discussion_r1996046334) (textile/features.textile:1561)
  - Noted that a flag/mode position number had changed since the PR was raised and needs updating.
- **SimonWoolf** — [keep protocol document in sync with implementation](https://github.com/ably/specification/pull/279#discussion_r1996051975) (textile/protocol.textile:86)
  - Flagged that the mentioned connectionSerial field is no longer present in the protocol, and noted the protocol document is out of date.
- **SimonWoolf** — [specify string-parsing rules precisely](https://github.com/ably/specification/pull/279#discussion_r1998534806) (textile/protocol.textile:88)
  - Corrected a suggestion: split on the first colon, not the last, since the sync id is guaranteed not to contain a colon while the object-id cursor might.
- **SimonWoolf** — [make implicit parsing rules explicit](https://github.com/ably/specification/pull/279#discussion_r1998538328) (textile/protocol.textile:88)
  - Added that while the existing examples hint at first-colon splitting, the relevant spec item should say so explicitly.
- **lawrence-forooghian** — [define terms introduced in spec](https://github.com/ably/specification/pull/279#discussion_r1998776708) (textile/features.textile:1428)
  - Asked whether "origin timeserial" is a defined term anywhere.
- **lawrence-forooghian** — [define terms introduced in spec](https://github.com/ably/specification/pull/279#discussion_r1998777053) (textile/features.textile:1429)
  - Asked whether "site code" has a formal definition anywhere.
- **lawrence-forooghian** — [reference encoding/decoding rules for binary fields](https://github.com/ably/specification/pull/279#discussion_r1998786930) (textile/features.textile:1449)
  - Asked where the spec defines encode/decode rules for binary ProtocolMessage properties.
- **lawrence-forooghian** — [use consistent terminology for data types](https://github.com/ably/specification/pull/279#discussion_r1998799036) (textile/features.textile:1536)
  - Preferred consistent use of "binary" across the PR and re-raised the encoding question.
- **lawrence-forooghian** — [justify why SDK needs to know each field](https://github.com/ably/specification/pull/279#discussion_r1998799571) (textile/features.textile:1535)
  - Asked how the library is meant to use a field; if the SDK never consumes it, why is it in the spec?
- **SimonWoolf** — [hide server-side implementation details from SDK spec](https://github.com/ably/specification/pull/279#discussion_r2002992179) (textile/features.textile:1428)
  - Argued that originTimeserial/timeSerial/siteCode are server-side concepts that should not be exposed in the SDK spec; the field should simply be described as "a string uniquely identifying this StateMessage".
- **SimonWoolf** — [document only what SDK devs need to know](https://github.com/ably/specification/pull/279#discussion_r2003000877) (textile/features.textile:1429)
  - Stated general principle: don't document serverside implementation details unnecessary for SDK implementation; explain fields in the SDK's data-model context.
- **SimonWoolf** — [pick consistent, natural-reading terminology](https://github.com/ably/specification/pull/279#discussion_r2003003310) (textile/features.textile:1419)
  - Complained about churn between terms "State" and "Objects" in new type names and suggested renaming StateMessage to ObjectsMessage; also noted "objects message" reads awkwardly.
- **SimonWoolf** — [treat serial encoding as implementation detail; use 'serial' only](https://github.com/ably/specification/pull/279#discussion_r2003011940) (textile/features.textile:1428)
  - Advised against using the term "timeserial" in spec or public API; just use "serial" since the wire encoding is an implementation detail and has changed before.

### PR #277 — Refactor: Spec updates for Typing presence to heartbeat-based changes

- **lawrence-forooghian** — [specify return timing and error semantics of methods](https://github.com/ably/specification/pull/277#discussion_r2021021551) (textile/chat-features.textile:431)
  - Asked that keystroke()'s return timing and error behaviour (does it await publish completion, no-op when typing in progress, etc.) be made explicit.
- **lawrence-forooghian** — [specify return timing and error semantics of methods](https://github.com/ably/specification/pull/277#discussion_r2021022717) (textile/chat-features.textile:445)
  - Same kind of question for stop(): await/throw behaviour should be specified.
- **lawrence-forooghian** — [separate overview (non-normative) from concrete rules](https://github.com/ably/specification/pull/277#discussion_r2021028332) (textile/chat-features.textile:429)
  - Suggested making the overview spec point non-normative and moving concrete rules to CHA-T13b1 to avoid overlap between two points describing the same behaviour.
- **lawrence-forooghian** — [mark leaf testable requirements as Testable](https://github.com/ably/specification/pull/277#discussion_r2021030831) (textile/chat-features.textile:462)
  - Asked whether sub-points should also be marked Testable.
- **lawrence-forooghian** — [specify concrete errors; justify if not a rethrow](https://github.com/ably/specification/pull/277#discussion_r2024621718) (textile/chat-features.textile:431)
  - Asked for the thrown error to be made specific, or for a clear reason it's not simply a rethrow of the publish error.

### PR #276 — Add docstring for `Message.connectionKey`

- **lawrence-forooghian** — [document inbound-only vs outbound-only properties](https://github.com/ably/specification/pull/276#discussion_r1974234157) (textile/api-docstrings.md:673)
  - Added that the property is only populated on publish, never on inbound messages; referenced a prior PR proposing split inbound/outbound types and noted ably-js now has InboundMessage to reflect this.

### PR #275 — fix TM2p: remove sentence about populating version from channelSerial

- **SimonWoolf** — [retain conditions that clarify intent, even if redundant](https://github.com/ably/specification/pull/275#discussion_r1956198138) (textile/features.textile:1348)
  - Acknowledged a conditional is technically removable but kept it because it helps make intent clearer.

### PR #274 — Specify how to track usage of Chat SDK

- **lawrence-forooghian** — [scope PR discussion to its change](https://github.com/ably/specification/pull/274#discussion_r1959652454) (textile/chat-features.textile:33)
  - Noted that the spec point merely documents current behaviour and suggested proposed changes belong elsewhere, not on this PR.

### PR #273 — Add API for tracking usage of wrapper SDKs

- **lawrence-forooghian** — [ground spec decisions in ADR/requirements](https://github.com/ably/specification/pull/273#discussion_r1952714751) (textile/features.textile:916)
  - Discussed the requirements assumption baked into the spec (not attributing realtime connections to wrapper SDKs) and tied it back to an ADR discussion.
- **lawrence-forooghian** — [explicitly decide which APIs belong in shared spec vs per-SDK](https://github.com/ably/specification/pull/273#discussion_r1952721533) (textile/features.textile:917)
  - Acknowledged an unaddressed use case (mutating agents after construction) and floated whether to specify it or implement JS-only.
- **lawrence-forooghian** — [prefer generalised rules over enumerated lists, but handle edge cases](https://github.com/ably/specification/pull/273#discussion_r1952760102) (textile/features.textile:924)
  - Acknowledged it would be nice to generalise a list of operations (so the spec doesn't need updating per new billable op), but struggled to find a clean formulation because some REST calls (token requests, push registration) aren't cleanly attributable.
- **lawrence-forooghian** — [avoid enumerations that require spec updates per-feature](https://github.com/ably/specification/pull/273#discussion_r1952812446) (textile/features.textile:924)
  - Agreed the per-operation list is not great as a maintenance burden; committed to rewording.
- **lawrence-forooghian** — [weigh private-API exposure costs of alternatives](https://github.com/ably/specification/pull/273#discussion_r1954387767) (textile/features.textile:921)
  - Explained why a suggested implementation approach (composition via a common interface) would be hard because the wrapper proxy uses private APIs of the underlying client; wanted to avoid widening the private interface just for this.
- **lawrence-forooghian** — [allow optional per-platform capabilities in spec](https://github.com/ably/specification/pull/273#discussion_r1958729491) (textile/features.textile:921)
  - Softened a requirement to "A wrapper SDK proxy client does not need to provide a createWrapperSDKProxy method" so platforms can implement if useful.
- **lawrence-forooghian** — [iterate on spec wording based on feedback](https://github.com/ably/specification/pull/273#discussion_r1958748117) (textile/features.textile:924)
  - Noted that the spec point was reworded in response to the maintenance-burden feedback.

### PR #268 — features/spec: add sandbox backward compatibility to endpoint spec

- **SimonWoolf** — [prefer explicit if/else waterfall to 'unless' phrasing](https://github.com/ably/specification/pull/268#discussion_r1918509020) (textile/features.textile:81)
  - Rejected ambiguous "Unless X then Y" phrasing; suggested inserting a new REC1b5 between b3 and b4 so it's part of the same if/else waterfall, or extending REC1b3 to include the 'sandbox' routing policy name.

### PR #264 — [chat-spec] Removed transient timeout references for delayed ATTACHING state

- **lawrence-forooghian** — [follow modification guidance once points are implemented](https://github.com/ably/specification/pull/264#issuecomment-2586971787)
  - Insisted lifecycle spec-point changes must follow modification guidance now that points are implemented in Swift.

### PR #261 — Port api reference to specification repo

- **SimonWoolf** — [pick renderer that handles spec content correctly](https://github.com/ably/specification/pull/261#issuecomment-2573492559)
  - Switched the markdown renderer from redcarpet to kramdown to avoid a long-standing redcarpet bug.

### PR #259 — Refactored RTN22, added missing details

- **SimonWoolf** — [spec must state SDK requirements, not server facts](https://github.com/ably/specification/pull/259#discussion_r1890228871) (textile/features.textile:505)
  - Rejected adding informational statements that impose no SDK requirements; spec should only state what SDK devs must do differently. Elevating discretionary server behaviour to a guaranteed contract requires a good reason.
- **SimonWoolf** — [treat protocol guarantees as load-bearing commitments](https://github.com/ably/specification/pull/259#discussion_r1890339227) (textile/features.textile:505)
  - Reiterated that moving server behaviour from discretionary to guaranteed is a weighty change requiring justification, even if the value has never changed in practice.

### PR #238 — Update/Limit default typing timeout

- **lawrence-forooghian** — [mark replaced points, don't silently mutate](https://github.com/ably/specification/pull/238#discussion_r1856512161) (textile/chat-features.textile:405)
  - Asked that the spec point be marked as replaced (per CONTRIBUTING.md) rather than silently changed, since it's already implemented in Swift.

### PR #237 — Add some spec points about disabled chat features

- **lawrence-forooghian** — [specify ordering where relevant](https://github.com/ably/specification/pull/237#discussion_r1852066252) (textile/chat-features.textile:198)
  - Asked what ordering is required for remaining contributors after some are removed; spec doesn't say.
- **lawrence-forooghian** — [encode verbal agreements into spec text](https://github.com/ably/specification/pull/237#discussion_r1852091117) (textile/chat-features.textile:198)
  - Asked the author to add the ordering requirement in prose rather than just describing it in review.

### PR #235 — Update field names for mutable messages, and specify how message.serial is set from channelSerial

- **SimonWoolf** — [don't expose limits SDKs can't act on](https://github.com/ably/specification/pull/235#discussion_r1851943792) (textile/features.textile:1338)
  - Argued SDKs don't need to know about a server-side limit at this point because they can't do anything with it; generally SDKs don't need to know limits they don't enforce.
- **SimonWoolf** — [spec is for SDK devs, not end users](https://github.com/ably/specification/pull/235#discussion_r1851947835) (textile/features.textile:1336)
  - Reminded that this is an SDK spec, not customer documentation; SDK devs don't need to know what a field represents, they just need to handle it.

### PR #232 — chat: add CHA-RL9 to explain "attaching piggyback"

- **lawrence-forooghian** — [mark spec points Testable to support SDK tooling](https://github.com/ably/specification/pull/232#discussion_r1852614633) (textile/chat-features.textile:147)
  - Asked that spec points be marked Testable so that the Swift repo's test-coverage tooling (which warns about annotations for non-Testable points) works cleanly.

### PR #222 — Features spec: only emit a leave if there was an existing matching member

- **SimonWoolf** — [communicate priority/urgency of spec changes](https://github.com/ably/specification/pull/222#issuecomment-2520768579)
  - Provided priority guidance: this is a small, low-priority change to chuck in next time someone is making modifications.
- **lawrence-forooghian** — [follow CONTRIBUTING.md spec-point language conventions](https://github.com/ably/specification/pull/222#discussion_r1860566955) (textile/features.textile:760)
  - Asked the author to stick to the language prescribed by CONTRIBUTING.md for features spec points.
- **lawrence-forooghian** — [mark removed spec points as deleted/replaced](https://github.com/ably/specification/pull/222#discussion_r1860568610) (textile/features.textile:779)
  - Noted that removed spec points (RTP2e, RTP2f) need to be marked as deleted or replaced so IDs are not re-used.
- **lawrence-forooghian** — [confirm understanding by summarising functional change](https://github.com/ably/specification/pull/222#discussion_r1860581693) (textile/features.textile:781)
  - Summarised the functional change, splitting RTP2g into two rules (one for LEAVE, one for other actions), to check understanding.

### PR #213 — Updates for ADR-119: updated ClientOptions for new domains

- **SimonWoolf** — [remove redundant conditions already implied by context](https://github.com/ably/specification/pull/213#discussion_r1815798805) (textile/features.textile:83)
  - Questioned whether a new guard condition is distinct from the already-true antecedent, pointing at a redundant branch.
- **SimonWoolf** — [don't hardcode environment values; reuse definitions](https://github.com/ably/specification/pull/213#discussion_r1815802816) (textile/features.textile:127)
  - Argued the spec shouldn't hardcode the main production cluster and that the rule looked redundant to RSC25.
- **SimonWoolf** — [reference previously-defined abstractions](https://github.com/ably/specification/pull/213#discussion_r1815803694) (textile/features.textile:125)
  - Suggested referencing the previously defined "primary domain" (or RSC25) instead of hardcoding the production endpoint.
- **SimonWoolf** — [refer to named definitions over literal values](https://github.com/ably/specification/pull/213#discussion_r1815805546) (textile/features.textile:173)
  - Replaced a prose mention of "main.realtime.ably.net" with a reference to "the REC1 Primary Domain".
- **SimonWoolf** — [simplify spec when legacy distinctions no longer apply](https://github.com/ably/specification/pull/213#discussion_r1815810052) (textile/features.textile:87)
  - Questioned whether libraries still need to distinguish rest vs realtime hosts; suggested simplifying the spec to let libs coalesce them.
- **SimonWoolf** — [remove spec points that no longer apply to a section](https://github.com/ably/specification/pull/213#discussion_r1815810972) (textile/features.textile:436)
  - Suggested removing RTC1e entirely because the environment option no longer behaves differently for realtime vs rest clients, so it doesn't belong in a realtime-only section.
- **SimonWoolf** — [reuse named definitions consistently](https://github.com/ably/specification/pull/213#discussion_r1815811258) (textile/features.textile:472)
  - Again urged referencing the REC1 Primary Domain instead of duplicating.
- **SimonWoolf** — [place spec points in the correct namespaced section](https://github.com/ably/specification/pull/213#discussion_r1815812019) (textile/features.textile:592)
  - Flagged that three points should be numbered RTNxx (realtime section) rather than RSCxx.

### PR #212 — Spec: SUBSCRIBE mode renamed to MESSAGE_SUBSCRIBE

- **SimonWoolf** — [when introducing synonyms, identify canonical vs deprecated](https://github.com/ably/specification/pull/212#issuecomment-2430469206)
  - Asked that the spec make clear which name is the main one going forward and which is the deprecated synonym, especially for exposing via channel.modes, while noting backwards compat matters less for RTL4m than for channel options.
- **SimonWoolf** — [preserve backwards compatibility for existing constants](https://github.com/ably/specification/pull/212#pullrequestreview-2383382096)
  - Insisted backwards compatibility: the existing SUBSCRIBE mode should retain its current meaning as a synonym for MESSAGE_SUBSCRIBE rather than breaking existing users.

### PR #210 — Messages: Add new message fields to message spec

- **SimonWoolf** — [use RFC2119 levels; avoid internal server names](https://github.com/ably/specification/pull/210#discussion_r1821615817) (textile/features.textile:303)
  - Raised three issues: (1) spec items shouldn't describe things the SDK has no reason to set on publish; (2) don't use "can" — it isn't an RFC2119 level, use "may", but only when some libraries should and some shouldn't; (3) don't say "realtime will..." — use "the server" since "realtime" is a type of SDK in the spec.
- **SimonWoolf** — [avoid synonyms for existing terms; use 'must' only for SDK requirements](https://github.com/ably/specification/pull/210#discussion_r1821622687) (textile/features.textile:1310)
  - Rejected using "type" as a synonym for "action" because it invites confusion; also noted that "must" is a normative SDK requirement and should not be used when describing what the server will do.
- **SimonWoolf** — [write spec from SDK implementer perspective](https://github.com/ably/specification/pull/210#discussion_r1821632482) (textile/features.textile:1318)
  - Reminded that the spec is for SDK implementers; describing server behaviour is not actionable. Suggested a crisp form: `@serial@ string, an opaque string that uniquely identifies this message`.
- **SimonWoolf** — [expose typed substructs, not opaque JSON](https://github.com/ably/specification/pull/210#discussion_r1821643704) (textile/features.textile:1323)
  - Objected to typing the operation field as JsonObject; the optional substruct has three known fields and should be exposed as a proper typed class in languages with static typing.
- **SimonWoolf** — [follow existing IDL conventions for new enums](https://github.com/ably/specification/pull/210#discussion_r1821652076) (textile/features.textile:2174)
  - Pointed to the IDL's existing convention for defining enums (e.g. PresenceAction) as the template to follow.
- **SimonWoolf** — [follow naming conventions for spec points and IDL refs](https://github.com/ably/specification/pull/210#discussion_r1830242852) (textile/features.textile:1317)
  - Noted two conventions: spec-point letters after the section prefix should be lowercase (e.g. TM2p), and the IDL should reference a spec point listing the actions.

### PR #209 — Tighten up `attachOnSubscribe == false` behaviour

- **lawrence-forooghian** — [record resolution of semantic debates in spec](https://github.com/ably/specification/pull/209#discussion_r1793331972) (textile/features.textile:692)
  - Recorded a cross-team discussion resolution that the optional callback is not meant to signal the add-a-listener operation's result.
- **lawrence-forooghian** — [prefer case-based API rules over language-generic wording](https://github.com/ably/specification/pull/209#discussion_r1793332656) (textile/features.textile:692)
  - Noted "accepts an optional callback" wording was found confusing; planned to rework to describe cases (optional callback vs anything else).
- **lawrence-forooghian** — [structure spec by behavioural cases](https://github.com/ably/specification/pull/209#discussion_r1793366461) (textile/features.textile:693)
  - Reworded spec into two cases (optional callback vs not) rather than the prior "non-optional callback" language.
- **lawrence-forooghian** — [write spec in language-agnostic terms](https://github.com/ably/specification/pull/209#discussion_r1793367421) (textile/features.textile:693)
  - Preferred writing the spec in language-agnostic terms rather than listing each language's concrete return type (e.g. ably-go returns an unsubscribe function).
- **lawrence-forooghian** — [allow per-language idioms for programmer errors](https://github.com/ably/specification/pull/209#discussion_r1793698634) (textile/features.textile:692)
  - Accepted the Swift approach (programmer errors are irrecoverable) and asked peers for suggestions of appropriate statusCode/code for a programmer-error ErrorInfo in other languages.

### PR #208 — Fixed spec for channel subscribe with optional callback

- **lawrence-forooghian** — [define exactly what callback 'success' means](https://github.com/ably/specification/pull/208#discussion_r1781376154) (textile/features.textile:691)
  - Asked the author to clarify what "success" refers to; ambiguous nouns in a completion callback need explicit referent.
- **SimonWoolf** — [simplify API when an option removes callback semantics](https://github.com/ably/specification/pull/208#discussion_r1783221574) (textile/features.textile:691)
  - Proposed either banning callback usage when attachOnSubscribe=false or calling it immediately with success, since there is no reason to accept a callback in that case.
- **SimonWoolf** — [don't future-proof by adding speculative asynchrony](https://github.com/ably/specification/pull/208#discussion_r1783255349) (textile/features.textile:691)
  - Argued subscribe with attachOnSubscribe=false is conceptually synchronous; rejected pre-emptively making it async for hypothetical future changes.
- **lawrence-forooghian** — [handle optional attach callback per language idioms](https://github.com/ably/specification/pull/208#discussion_r1784424111) (textile/features.textile:691)
  - Laid out a framework: adding a listener is synchronous, the attach-callback is a legacy of subscribe being async, and in languages that allow opting out, passing the callback when attachOnSubscribe=false should be a programmer error; in languages that don't allow opting out (promises), we bite the bullet and signal success.
- **lawrence-forooghian** — [ground spec interpretation in public documentation](https://github.com/ably/specification/pull/208#discussion_r1790255796) (textile/features.textile:691)
  - Rebutted the view that the subscribe callback represents the subscribe operation as a whole; public docs explicitly tie it to attach() success, and ambiguity about what a callback-with-error means shows the whole-operation framing is broken.
- **lawrence-forooghian** — [weigh API naming/historical meaning when changing semantics](https://github.com/ably/specification/pull/208#pullrequestreview-2337976005)
  - Expressed ambivalence about the change: finishes off a pending callback cleanly, but muddies the meaning of the callback, which historically and even by method name (subscribeWithAttachCallback:) means "the channel has attached".

### PR #206 — Add opt-out of implicit attach when subscribing

- **SimonWoolf** — [avoid asymmetric implicit lifecycle behaviour](https://github.com/ably/specification/pull/206#issuecomment-2341337421)
  - Endorsed making non-implicit-attach the default in a future major version, disliking the asymmetry of implicit attach on first subscribe but no implicit detach on last unsubscribe.
- **lawrence-forooghian** — [respect existing API contracts / backwards compatibility](https://github.com/ably/specification/pull/206#issuecomment-2341964192)
  - Rejected a simplification because it would be a breaking API change; current expectation is that subscribe triggers attach.

### PR #205 — Spec: ban warning on unknown fields for spec v3

- **lawrence-forooghian** — [check for existing coverage before adding new points](https://github.com/ably/specification/pull/205#issuecomment-2334679537)
  - Pointed out that the existing RSF1 already requires unknown fields to be ignored, questioning whether this new spec item is necessary.
- **SimonWoolf** — [fix SDK bugs rather than duplicate spec items](https://github.com/ably/specification/pull/205#issuecomment-2338130023)
  - Agreed that if ably-java is logging a warning on unknown fields, it is already in breach of RSF1 and that should be fixed rather than amended in the spec.
- **SimonWoolf** — [distinguish log levels when specifying behaviour](https://github.com/ably/specification/pull/205#issuecomment-2340079452)
  - Noted the existing log is VERBOSE, not warn/error, so wouldn't violate the proposed new item; i.e. level matters to spec interpretation.
- **lawrence-forooghian** — [interpret 'ignore' strictly, even for verbose logs](https://github.com/ably/specification/pull/205#issuecomment-2342067534)
  - Argued the verbose log still violates RSF1 because it is not "ignoring" the unknown field, hence it is an SDK bug.

### PR #200 — chat: room lifecycle specification

- **lawrence-forooghian** — [test spec sufficiency via implementation in isolation](https://github.com/ably/specification/pull/200#issuecomment-2312944877)
  - Deliberately implementing the spec in Swift without consulting the JS implementation in order to surface ambiguities and ensure the spec is self-sufficient.
- **lawrence-forooghian** — [avoid renaming spec points once implementations reference them](https://github.com/ably/specification/pull/200#issuecomment-2447816994)
  - Asked that spec points not be renamed once SDKs have begun referring to them; reverted a rename commit.
- **lawrence-forooghian** — [follow CONTRIBUTING.md rules for spec point modification](https://github.com/ably/specification/pull/200#issuecomment-2448171793)
  - Restored deleted spec point IDs and pointed contributors at CONTRIBUTING.md guidance on modifying the spec; argued that now that the spec has SDK implementations, the modification rules must be followed strictly.
- **lawrence-forooghian** — [distinguish non-normative summary text from normative requirements](https://github.com/ably/specification/pull/200#discussion_r1733151076) (textile/chat-features.textile:70)
  - Suggested highlighting when statements are non-normative summaries whose meaning will be fleshed out by later spec points, so readers don't try to implement vague prose as-is.
- **lawrence-forooghian** — [prefer describing APIs via signatures/types/IDL](https://github.com/ably/specification/pull/200#discussion_r1734217662) (textile/chat-features.textile:53)
  - Asked whether it was a conscious choice not to describe the SDK API in terms of signatures/types and IDL, as the core features spec does.
- **lawrence-forooghian** — [avoid reusing state names for operation names](https://github.com/ably/specification/pull/200#discussion_r1734220038) (textile/chat-features.textile:74)
  - Suggested replacing the word ATTACHED in a prose description of the ATTACH operation, because ATTACHED is also the name of a state and the overlap is confusing.
- **lawrence-forooghian** — [make implicit type references explicit](https://github.com/ably/specification/pull/200#discussion_r1734225993) (textile/chat-features.textile:76)
  - Asked that error specifications be explicit about which type is used (e.g. ErrorInfo) rather than relying on implicit knowledge from other SDKs.
- **lawrence-forooghian** — [specify both code and statusCode for every thrown error](https://github.com/ably/specification/pull/200#discussion_r1734229702) (textile/chat-features.textile:76)
  - If ErrorInfo is reused everywhere, the spec should specify statusCode in all places it describes throwing such an error, not only code.
- **lawrence-forooghian** — [define ambiguous procedural adverbs like 'in sequence'](https://github.com/ably/specification/pull/200#discussion_r1734234918) (textile/chat-features.textile:80)
  - Asked for clarification of the word "in sequence": does it mean awaiting each attach() call's success before starting the next?
- **lawrence-forooghian** — [distinguish call-return success from state-observation](https://github.com/ably/specification/pull/200#discussion_r1734236379) (textile/chat-features.textile:81)
  - Asked whether success means the attach() call completed successfully or some observable state was reached; the reader shouldn't have to guess whether to monitor channel state.
- **lawrence-forooghian** — [add spec-point cross-references for referenced behaviour](https://github.com/ably/specification/pull/200#discussion_r1734239629) (textile/chat-features.textile:87)
  - Asked for a cross-reference to the spec point that describes the behaviour referred to here, so the reader doesn't have to search.
- **lawrence-forooghian** — [flag forward references to later spec points](https://github.com/ably/specification/pull/200#discussion_r1734245075) (textile/chat-features.textile:85)
  - Asked that when a term like "must be rolled back" is used, the spec should signal that a subsequent spec point will define what it means.
- **lawrence-forooghian** — [define failure conditions precisely](https://github.com/ably/specification/pull/200#discussion_r1734247036) (textile/chat-features.textile:85)
  - Asked whether "fails to attach" is defined as "the attach() call threw an error".
- **lawrence-forooghian** — [spec should be self-contained, not reference SDKs](https://github.com/ably/specification/pull/200#discussion_r1734259831) (textile/chat-features.textile:86)
  - Requested that information be inlined rather than referring the reader to another SDK's implementation, citing prior cleanup of "see Ruby for more info" in the main spec.
- **lawrence-forooghian** — [spell out procedural steps and error fields](https://github.com/ably/specification/pull/200#discussion_r1734270939) (textile/chat-features.textile:87)
  - Suggested expanding a terse rule into explicit steps (when channel.attach() fails, inspect state, then transition using errorReason as the cause) and asking what code/statusCode that transition's error should carry.
- **lawrence-forooghian** — [specify completion semantics and ordering for operations](https://github.com/ably/specification/pull/200#discussion_r1734279604) (textile/chat-features.textile:91)
  - Asked how a room ATTACH operation should end when a channel entered FAILED, including timing relative to room state transitions.
- **lawrence-forooghian** — [group related spec points structurally](https://github.com/ably/specification/pull/200#discussion_r1734304458) (textile/chat-features.textile:127)
  - Suggested moving a spec point about RETRY into the same "Room Lifecycle Operations" section alongside ATTACH/DETACH/RELEASE, for consistency with an earlier enumeration.
- **lawrence-forooghian** — [specify inter-operation interaction when one triggers another](https://github.com/ably/specification/pull/200#discussion_r1734317817) (textile/chat-features.textile:88)
  - Asked what "enter the recovery loop" refers to, and how one operation initiating another interacts with operations that are already queued.
- **lawrence-forooghian** — [qualify 'when X happens' triggers by scope](https://github.com/ably/specification/pull/200#discussion_r1734330635) (textile/chat-features.textile:88)
  - Asked whether "When the room enters the SUSPENDED status" means whenever or only in the context of a specific triggering point.
- **lawrence-forooghian** — [specify exact error codes, not generic errors](https://github.com/ably/specification/pull/200#discussion_r1735808191) (textile/chat-features.textile:153)
  - Asked whether a thrown error refers to a specific ErrorInfo code rather than an unspecified error.
- **lawrence-forooghian** — [disambiguate scope (per-entity vs global)](https://github.com/ably/specification/pull/200#discussion_r1735847299) (textile/chat-features.textile:152)
  - Asked whether the rule is scoped to "the same room ID" or applies universally.
- **lawrence-forooghian** — [model concurrency via explicit queue semantics](https://github.com/ably/specification/pull/200#discussion_r1755213859) (textile/chat-features.textile:88)
  - Suggested expressing sequencing in terms of a queue of operations picked off one-by-one, because "asynchronously" is too vague.
- **lawrence-forooghian** — [always specify statusCode alongside error code](https://github.com/ably/specification/pull/200#discussion_r1755222945) (textile/chat-features.textile:76)
  - Asked that status codes be specified everywhere an error code is specified, including the Chat-specific Error Codes section and any in-text numeric error codes.
- **lawrence-forooghian** — [name the exact property when referring to errors](https://github.com/ably/specification/pull/200#discussion_r1755231822) (textile/chat-features.textile:87)
  - Asked that the spec explicitly reference contributor.errorReason rather than use the ambiguous phrase "the Realtime Channel error".
- **lawrence-forooghian** — [clarify whether effects are in-operation or after](https://github.com/ably/specification/pull/200#discussion_r1755240496) (textile/chat-features.textile:91)
  - Asked whether a subpoint describes post-operation behaviour, i.e. whether side-effects happen outside the context of the lifecycle manager operation itself.
- **lawrence-forooghian** — [justify divergent error choices between related points](https://github.com/ably/specification/pull/200#discussion_r1755252586) (textile/chat-features.textile:92)
  - Asked why an error differs from the one used in a closely related state transition, suggesting consistency or an explicit justification is needed.
- **lawrence-forooghian** — [every error needs code and statusCode](https://github.com/ably/specification/pull/200#discussion_r1755253765) (textile/chat-features.textile:93)
  - Requested explicit code and statusCode for an error that is mentioned without those fields.
- **lawrence-forooghian** — [centralise error definitions and reference them](https://github.com/ably/specification/pull/200#discussion_r1755279543) (textile/chat-features.textile:80)
  - Suggested that spec points that throw errors should refer to entries in the "Chat-specific Error Codes" section rather than declaring codes inline.
- **lawrence-forooghian** — [apply clarifications consistently across symmetric points](https://github.com/ably/specification/pull/200#discussion_r1755533396) (textile/chat-features.textile:104)
  - Noted that clarifications applied to ATTACH should apply to DETACH, which has parallel language; parallel spec points need parallel treatment.
- **lawrence-forooghian** — [when a point has multiple errors, disambiguate references](https://github.com/ably/specification/pull/200#discussion_r1763664413) (textile/chat-features.textile:92)
  - Noted ambiguity when a spec point describes two errors and later text refers to "the error from CHA-RL1h2" without saying which.
- **lawrence-forooghian** — [remove stale/duplicate prose from spec points](https://github.com/ably/specification/pull/200#discussion_r1763677847) (textile/chat-features.textile:94)
  - Flagged a sentence that seems to duplicate or contradict earlier language about how the cause field is populated, suggesting it might be a leftover.
- **lawrence-forooghian** — [automate detection of duplicate spec-point IDs in CI](https://github.com/ably/specification/pull/200#discussion_r1763770348) (textile/chat-features.textile:115)
  - Found duplicate spec point IDs (e.g. CHA-RL3c) and asked for the find-duplicate-spec-items CI script to be updated to cover Chat, providing a ready implementation.
- **lawrence-forooghian** — [mirror clarifying language across symmetric operations](https://github.com/ably/specification/pull/200#discussion_r1763786383) (textile/chat-features.textile:107)
  - Requested that DETACH spec points inherit the same clarifying language that was added to ATTACH (e.g. defining "fails to detach" in terms of the call throwing an error).
- **lawrence-forooghian** — [prefer call-return semantics over state polling](https://github.com/ably/specification/pull/200#discussion_r1763790455) (textile/chat-features.textile:108)
  - Asked whether the spec really requires polling for channel state DETACHED, or merely means to wait until detach() returned or the channel became FAILED.
- **lawrence-forooghian** — [clarify whether to subscribe or read state](https://github.com/ably/specification/pull/200#discussion_r1763795558) (textile/chat-features.textile:110)
  - Asked whether "enters another state" is an event-listener thing or merely means reading the channel state after detach() fails.
- **lawrence-forooghian** — [clarify scope of rules across retries](https://github.com/ably/specification/pull/200#discussion_r1763797142) (textile/chat-features.textile:110)
  - Asked whether a general failure spec point also applies to the retry case introduced in the same section.
- **lawrence-forooghian** — [avoid introducing undefined domain terms](https://github.com/ably/specification/pull/200#discussion_r1763798318) (textile/chat-features.textile:110)
  - Asked for an alternative to the undefined term "detachment cycle".
- **lawrence-forooghian** — [specify concrete durations for waits/retries](https://github.com/ably/specification/pull/200#discussion_r1763799223) (textile/chat-features.textile:110)
  - Asked why the duration of a "short pause" is left unspecified.
- **lawrence-forooghian** — [specify concrete durations for waits/retries](https://github.com/ably/specification/pull/200#discussion_r1763822207) (textile/chat-features.textile:118)
  - Same question about an unspecified "short wait" duration.
- **lawrence-forooghian** — [avoid undefined domain terms](https://github.com/ably/specification/pull/200#discussion_r1763829706) (textile/chat-features.textile:118)
  - Asked for an alternative to the undefined term "channel detach sequence".
- **lawrence-forooghian** — [define failure in terms of call return/throw](https://github.com/ably/specification/pull/200#discussion_r1763838700) (textile/chat-features.textile:118)
  - Requested the same clarification of "fails to detach" (i.e. that detach() threw) applied elsewhere.
- **lawrence-forooghian** — [specify retry termination conditions](https://github.com/ably/specification/pull/200#discussion_r1763846633) (textile/chat-features.textile:118)
  - Asked whether retry is indefinite (until detach succeeds or FAILED) rather than a single attempt.
- **lawrence-forooghian** — [clarify rule applicability under retries](https://github.com/ably/specification/pull/200#discussion_r1763857263) (textile/chat-features.textile:123)
  - Asked whether a given rule also applies to retry attempts described elsewhere.
- **lawrence-forooghian** — [distinguish channel-level vs room-level operations](https://github.com/ably/specification/pull/200#discussion_r1763876128) (textile/chat-features.textile:99)
  - Asked whether "the detach operation" refers to the individual channel detach or the outer room detach operation.
- **lawrence-forooghian** — [prefer call-completion to state-observation, avoid internal contradictions](https://github.com/ably/specification/pull/200#discussion_r1763886125) (textile/chat-features.textile:119)
  - Asked whether "once all channels have entered DETACHED" really means we check state, or rather that detach() returned successfully on each non-FAILED channel; raised contradiction concerns.
- **lawrence-forooghian** — [specify exact order of steps in retry loops](https://github.com/ably/specification/pull/200#discussion_r1765372854) (textile/chat-features.textile:118)
  - Asked for explicit ordering of checks around a wait: does the FAILED-check happen before the wait, after, or both?
- **lawrence-forooghian** — [flag potentially redundant spec points](https://github.com/ably/specification/pull/200#discussion_r1765476610) (textile/chat-features.textile:91)
  - Asked whether a spec point adds any new requirement beyond what neighbouring spec points already say, raising redundancy concerns.
- **lawrence-forooghian** — [enumerate all possible states at a decision point](https://github.com/ably/specification/pull/200#discussion_r1765479528) (textile/chat-features.textile:94)
  - Asked the author to enumerate the full set of possible channel states at this point so the spec is exhaustive.
- **lawrence-forooghian** — [match exact field names in prose](https://github.com/ably/specification/pull/200#discussion_r1775546564) (textile/chat-features.textile:138)
  - Corrected a field name (resumed not resume) used in several spec points.
- **lawrence-forooghian** — [prefer unambiguous, implementable phrasing](https://github.com/ably/specification/pull/200#discussion_r1775552624) (textile/chat-features.textile:139)
  - Said a spec point was too vague to implement as written; asked for clarification of whether "attached" means the initial call succeeded or the channel eventually reached ATTACHED.
- **lawrence-forooghian** — [unify duplicated conditions across spec points](https://github.com/ably/specification/pull/200#discussion_r1775609475) (textile/chat-features.textile:143)
  - Asked whether a condition is merely a reworded negation of a prior condition, suggesting duplication should be unified.
- **lawrence-forooghian** — [collapse convoluted nested conditions into clear statements](https://github.com/ably/specification/pull/200#discussion_r1775788715) (textile/chat-features.textile:149)
  - Suggested consolidating a convoluted conditional into a single clear spec point that states the timeout, the trigger, and the room state transition explicitly.
- **lawrence-forooghian** — [use the correct layer (room vs channel) consistently](https://github.com/ably/specification/pull/200#discussion_r1777117407) (textile/chat-features.textile:143)
  - Flagged that "channel lifecycle operation" is probably used where "room lifecycle operation" is meant.
- **lawrence-forooghian** — [separate non-normative principle from normative details](https://github.com/ably/specification/pull/200#discussion_r1777212960) (textile/chat-features.textile:142)
  - Argued a spec point is redundant because the sub-points already specify the same preconditions; if its purpose is to state the guiding principle, it should be presented as non-normative context.
- **lawrence-forooghian** — [avoid redundant contrapositive spec points](https://github.com/ably/specification/pull/200#discussion_r1777365677) (textile/chat-features.textile:145)
  - Questioned whether negative spec points that merely say "if the conditions above aren't met, don't do the action" are necessary at all.
- **lawrence-forooghian** — [explicitly name the negated action](https://github.com/ably/specification/pull/200#discussion_r1777385499) (textile/chat-features.textile:138)
  - Asked that the vague phrase "no action should be taken" be rewritten to explicitly name the action it is negating.
- **lawrence-forooghian** — [specify concurrency and failure semantics of bulk operations](https://github.com/ably/specification/pull/200#discussion_r1777471810) (textile/chat-features.textile:148)
  - Asked for rules governing how concurrent detaches should happen (sequential vs parallel) and what happens on per-contributor failure.
- **lawrence-forooghian** — [specify state-cleanup after event emission](https://github.com/ably/specification/pull/200#discussion_r1781917231) (textile/chat-features.textile:88)
  - Asked whether pending discontinuities are cleared after emission so they don't fire again.
- **lawrence-forooghian** — [specify replacement vs accumulation semantics](https://github.com/ably/specification/pull/200#discussion_r1781927850) (textile/chat-features.textile:140)
  - Asked whether a contributor may hold multiple pending discontinuity events, or whether a new one replaces the previous.
- **lawrence-forooghian** — [use distinct terms for status vs composite state](https://github.com/ably/specification/pull/200#discussion_r1783542331) (textile/chat-features.textile:642)
  - Suggested using the term "status" (rather than "state") in error names/messages, to match the convention reserved for a room's status vs its larger composite state.
- **lawrence-forooghian** — [name errors consistently](https://github.com/ably/specification/pull/200#discussion_r1783543926) (textile/chat-features.textile:642)
  - Suggested renaming an error to RoomIsFailed for consistency with RoomIsReleasing/RoomIsReleased.
- **lawrence-forooghian** — [mark descriptive vs normative sentences](https://github.com/ably/specification/pull/200#discussion_r1793968834) (textile/chat-features.textile:121)
  - Asked whether a sentence is a normative requirement (SDK must monitor its own state) or a non-normative description whose implementation is provided by other points.
- **lawrence-forooghian** — [define coined terms or replace with known terms](https://github.com/ably/specification/pull/200#discussion_r1793973971) (textile/chat-features.textile:122)
  - Asked that the undefined term "retry loop" be either defined or substituted for "RETRY operation" with an added non-normative explanation of its looping nature.
- **lawrence-forooghian** — [avoid internal contradictions between neighbouring points](https://github.com/ably/specification/pull/200#discussion_r1793977899) (textile/chat-features.textile:123)
  - Sought clarification that the retry applies only when the cause is "channel entered a state other than FAILED", to avoid an internal contradiction with a neighbouring spec point.
- **lawrence-forooghian** — [specify sequential vs parallel for bulk actions](https://github.com/ably/specification/pull/200#discussion_r1793996381) (textile/chat-features.textile:122)
  - Asked whether attaches should be sequential or parallel, citing prior prescriptive sequencing in a related spec point.
- **lawrence-forooghian** — [spec must describe complete flow, no missing steps](https://github.com/ably/specification/pull/200#discussion_r1794005346) (textile/chat-features.textile:125)
  - Asked whether a step is missing in the described flow; after detach, it's unclear how channels naturally become ATTACHED.
- **lawrence-forooghian** — [scope conditions temporally to referenced points](https://github.com/ably/specification/pull/200#discussion_r1794016836) (textile/chat-features.textile:126)
  - Asked for more explicit temporal scoping like "If, during the CHA-RL5d wait...".
- **lawrence-forooghian** — [explicitly describe operation termination](https://github.com/ably/specification/pull/200#discussion_r1794019536) (textile/chat-features.textile:128)
  - Asked explicitly whether the RETRY operation terminates at this point.
- **lawrence-forooghian** — [avoid undefined terms; prove procedures don't deadlock](https://github.com/ably/specification/pull/200#discussion_r1794047652) (textile/chat-features.textile:127)
  - Objected to the undefined term "attachment cycle"; if it meant "do the ATTACH operation again" there would be a deadlock with the CHA-RL1d queue rule, so the term must mean something else and needs defining.
- **lawrence-forooghian** — [specify concrete wait durations](https://github.com/ably/specification/pull/200#discussion_r1825086288) (textile/chat-features.textile:129)
  - Asked for a concrete duration for a "short wait".
- **lawrence-forooghian** — [specify sequencing for all bulk operations](https://github.com/ably/specification/pull/200#discussion_r1827732026) (textile/chat-features.textile:122)
  - Clarifying follow-up: should detaches (in CHA-RL5a) also happen in sequence?
- **lawrence-forooghian** — [every transition must specify its error](https://github.com/ably/specification/pull/200#discussion_r1827819961) (textile/chat-features.textile:130)
  - Asked "with what error?" when the spec calls for a state transition without specifying the accompanying error.
- **lawrence-forooghian** — [every transition must specify its error](https://github.com/ably/specification/pull/200#discussion_r1829344042) (textile/chat-features.textile:132)
  - Asked "with what error?" for a FAILED transition.
- **lawrence-forooghian** — [every transition must specify its error](https://github.com/ably/specification/pull/200#discussion_r1829875412) (textile/chat-features.textile:135)
  - Asked which error accompanies a FAILED transition.
- **lawrence-forooghian** — [every transition must specify its error](https://github.com/ably/specification/pull/200#discussion_r1829875903) (textile/chat-features.textile:136)
  - Asked which error accompanies a SUSPENDED transition.
- **lawrence-forooghian** — [enumerate reused sub-points explicitly](https://github.com/ably/specification/pull/200#discussion_r1829964805) (textile/chat-features.textile:127)
  - Suggested that when a new operation reuses behaviour from another (ATTACH), the spec should explicitly enumerate which sub-points apply rather than relying on implicit reuse.
- **lawrence-forooghian** — [avoid contradictory error specifications](https://github.com/ably/specification/pull/200#discussion_r1831374744) (textile/chat-features.textile:135)
  - Flagged that a newly specified error contradicts a different error already specified in a neighbouring spec point.
- **lawrence-forooghian** — [avoid contradictory error specifications](https://github.com/ably/specification/pull/200#discussion_r1831375738) (textile/chat-features.textile:136)
  - Flagged another contradiction with a neighbour's error specification.
- **lawrence-forooghian** — [flag or drop ambiguous intro prose](https://github.com/ably/specification/pull/200#discussion_r1831426583) (textile/chat-features.textile:91)
  - Suggested either removing the non-normative-sounding sentence or flagging that it will be fleshed out by following spec points.
- **lawrence-forooghian** — [proofread negation language carefully](https://github.com/ably/specification/pull/200#discussion_r1831431062) (textile/chat-features.textile:143)
  - Flagged a likely typo ("no call" where "a call" was meant) in a negated condition.
- **lawrence-forooghian** — [flag intro sections as purely descriptive](https://github.com/ably/specification/pull/200#discussion_r1831445508) (textile/chat-features.textile:121)
  - Asked that the introductory CHA-RL5 text be explicit that it merely describes behaviours implemented by other existing spec points rather than adding new requirements.
- **lawrence-forooghian** — [resolve terminology before merging](https://github.com/ably/specification/pull/200#discussion_r1831481306) (textile/chat-features.textile:122)
  - Asked whether the author intended to tidy up the retry-loop vs RETRY-operation terminology in this PR or a later one.
- **lawrence-forooghian** — [specify which sub-steps of reused operations apply](https://github.com/ably/specification/pull/200#discussion_r1831483708) (textile/chat-features.textile:127)
  - Asked whether a specific ATTACH sub-step (CHA-RL1h5 detach) is also meant to happen during RETRY.
- **lawrence-forooghian** — [cover edge cases for non-existent resources](https://github.com/ably/specification/pull/200#discussion_r1837154563) (textile/chat-features.textile:178)
  - Raised an unspecified edge case: what happens if rooms.release() is called with a room ID not present in the room map?

### PR #198 — Clarify how `echoMessages` should be implemented

- **lawrence-forooghian** — [specify explicit type conversions, don't rely on obviousness](https://github.com/ably/specification/pull/198#discussion_r1682723244) (textile/features.textile:447)
  - Noted that mapping a boolean client option (echoMessages) to a string connection parameter (echo="true"/"false") is not obvious and should be specified explicitly.

### PR #195 — RSA7f: clarify that send clientId regardless of basic/token auth

- **SimonWoolf** — [align spec with implemented reality rather than historical fiction](https://github.com/ably/specification/pull/195#issuecomment-2211162067)
  - Decided to edit RSA7e in place rather than adding RSA7f and deprecating the old one, arguing that since no SDK actually implemented the old RSA7e as written, the spec should just reflect the implemented reality rather than pretend older versions were valid.
- **SimonWoolf** — [keep a single canonical spec point per definition (DRY)](https://github.com/ably/specification/pull/195#discussion_r1666995784) (textile/features.textile:206)
  - Objected to duplicating clientId validity restrictions on DRY grounds; RSA7c is the single place where a valid clientId is defined, so any additional restrictions should be added there.

### PR #194 — TO3g editing in place for clarity.

- **SimonWoolf** — [use consistent terminology; avoid contradictory conditionals](https://github.com/ably/specification/pull/194#discussion_r1651014402) (textile/features.textile:1609)
  - Rejects inventing terms ('publish message' as a noun is not used elsewhere), flags a contradictory 'If x, y, otherwise z' structure whose logic is inverted, and notes each sibling clause states a slightly different condition, making the overall requirement ambiguous.

### PR #192 — Update RTL7c

- **SimonWoolf** — [enumerate applicable states explicitly](https://github.com/ably/specification/pull/192#discussion_r1642977014) (textile/features.textile:679)
  - Suggests listing concrete states (INITIALIZED, DETACHING, DETACHED) for when implicit attach applies, since it doesn't make sense for already-attached/attaching/suspended channels.

### PR #191 — Added forgotten test case for RTL2f

- **SimonWoolf** — [spec should describe behaviour, not prescribe tests](https://github.com/ably/specification/pull/191#issuecomment-2123003416)
  - Reiterates dislike of 'A test should exist...' spec items; spec should specify behaviour and leave test design to implementers.

### PR #182 — Added RTP17i spec point.

- **lawrence-forooghian** — [don't silently edit spec points](https://github.com/ably/specification/pull/182#discussion_r1486624999) (textile/features.textile:742)
  - Asserts the wording change doesn't justify the referenced implementation commit and that spec points can't be silently edited; must follow the Modification guidelines.
- **lawrence-forooghian** — [eliminate ambiguous state-transition language](https://github.com/ably/specification/pull/182#discussion_r1486688354) (textile/features.textile:742)
  - Argues 'moves into' is ambiguous; people interpret it differently. Either clarify the spec point precisely or accept that a parenthetical that seems to refine behaviour needs rewording.
- **SimonWoolf** — [prefer wire-event triggers over derived state triggers](https://github.com/ably/specification/pull/182#discussion_r1486698167) (textile/features.textile:742)
  - Agrees wording became ambiguous; suggests simplifying by removing channel state references and keying behaviour off receipt of an ATTACHED ProtocolMessage.
- **SimonWoolf** — [avoid self-contradictory wording](https://github.com/ably/specification/pull/182#discussion_r1490849057) (textile/features.textile:742)
  - Points out a proposed wording introduces a contradiction ('whenever' + exception) and the current proposal is itself a behaviour change from the existing spec; asks for non-contradictory phrasing.
- **lawrence-forooghian** — [state exceptions with 'except' rather than separate sentences](https://github.com/ably/specification/pull/182#discussion_r1491414576) (textile/features.textile:742)
  - Proposes non-contradictory wording: 'should perform automatic re-entry whenever the channel receives an ATTACHED ProtocolMessage, except in the case where the channel is already attached and the ProtocolMessage has the RESUMED bit flag set.'

### PR #181 — Updated the spec so that it reflects the behaviour implemented in ably-cocoa PR #1847

- **lawrence-forooghian** — [match spec fully to behaviour; follow modification rules](https://github.com/ably/specification/pull/181#discussion_r1486632090) (textile/features.textile:1210)
  - Points out that the proposed change only partially describes the actual SDK behaviour (other spec points would also need changing) and that spec point modification rules must be followed.

### PR #179 — Spec on what should happen when the recover option is malformed.

- **lawrence-forooghian** — [specify explicit fallback behaviour](https://github.com/ably/specification/pull/179#discussion_r1453240418) (textile/features.textile:536)
  - Suggests wording: 'If the recovery key ... cannot be deserialized due to malformed data, then an error should be logged and the connection should be made like no recover option was provided.'
- **SimonWoolf** — [weigh ergonomics vs cross-SDK implementation cost](https://github.com/ably/specification/pull/179#pullrequestreview-1830062473)
  - Agrees with simple spec but notes a richer behaviour (e.g., adding an error to the next connected state change event) would be better ergonomically; rejected due to implementation cost across SDKs.

### PR #173 — Bump protocol version to 3

- **SimonWoolf** — [align protocol bumps with semver-major library releases](https://github.com/ably/specification/pull/173#issuecomment-1836544679)
  - Notes that a protocol version bump that changes a response shape is a breaking API change for users of rest.request() and should be paired with a library major version bump per semver.
- **lawrence-forooghian** — [clean up obsolete requirements when bumping](https://github.com/ably/specification/pull/173#issuecomment-1836604048)
  - Raises that bumping protocol should be accompanied by removing stale related requirements (e.g., the newBatchResponse query param mandate).

### PR #170 — Improve wording in RTN15a

- **SimonWoolf** — [keep spec points normative, drop rationale](https://github.com/ably/specification/pull/170#discussion_r1369215876) (textile/features.textile:504)
  - Argues that a spec point waffling on the rationale should be pared down to just the normative requirement; rationale-only digressions dilute the spec.

### PR #167 — connection resume/recover

- **SimonWoolf** — [respect parent-child semantics of subclauses](https://github.com/ably/specification/pull/167#discussion_r1326118316) (textile/features.textile:515)
  - Explains that a new sub-item added in the middle of a parent whose children each list one outcome of a disjunction breaks the structure; a shared requirement across siblings shouldn't be a sibling itself.
- **SimonWoolf** — [preserve meaning when rewording](https://github.com/ably/specification/pull/167#discussion_r1326121336) (textile/features.textile:558)
  - Pushes back on a tense change (past → present): the original phrasing said 'don't change it in this case', which is lost in the rewrite.
- **SimonWoolf** — [use precise, established terminology](https://github.com/ably/specification/pull/167#discussion_r1326254626) (textile/features.textile:556)
  - Warns against defining terms ad hoc; 'transport' is OSI terminology (e.g., a websocket), not a connection; RTN19a applies to any new transport, not just a new connectionId.
- **SimonWoolf** — [remove redundancy as spec evolves](https://github.com/ably/specification/pull/167#discussion_r1330652598) (textile/features.textile:559)
  - Notes a spec item is obsolete due to other items (RTN15c6/7) handling attach, and that the detach portion is no longer needed; recommends trimming to just the still-relevant behaviour.
- **SimonWoolf** — [don't repeat conditions; reference defining spec point](https://github.com/ably/specification/pull/167#discussion_r1330652646) (textile/features.textile:558)
  - Insists on DRY: referring back to the spec item defining a condition rather than repeating it with slightly different wording, so requirements can't drift.
- **SimonWoolf** — [add explanatory sentences where implementation is ambiguous](https://github.com/ably/specification/pull/167#discussion_r1330652919) (textile/features.textile:530)
  - Suggests adding an explanatory sentence to the spec because current wording is unclear about how the library can detect whether recover succeeded without a connectionId to compare.
- **SimonWoolf** — [enumerate state properties rather than leaving implicit](https://github.com/ably/specification/pull/167#discussion_r1330653186) (textile/features.textile:514)
  - Suggests the spec could explicitly enumerate which properties are part of 'connection state' that should be cleared, for clarity.

### PR #166 — Refactor realtime presence spec

- **SimonWoolf** — [avoid implying extra state not actually required](https://github.com/ably/specification/pull/166#discussion_r1320071282) (textile/features.textile:726)
  - Warns that phrasing 'discarding related changes' wrongly implies the SDK must remember and revert to the pre-sync presence set; this isn't necessary.
- **SimonWoolf** — [don't conflate event timing with sync timing](https://github.com/ably/specification/pull/166#discussion_r1320075332) (textile/features.textile:746)
  - Objects to adding a 'during sync' qualifier because sync just surfaces changes that may have happened at any time during suspension; the wording misrepresents when the events happened.
- **SimonWoolf** — [keep prose grammatical and precise](https://github.com/ably/specification/pull/166#discussion_r1320077183) (textile/features.textile:748)
  - Notes a new addition is unclear ('conditions side effects', 'while enter presence message').
- **SimonWoolf** — [spec should describe behaviour, not prescribe tests](https://github.com/ably/specification/pull/166#discussion_r1320080062) (textile/features.textile:746)
  - Objects to 'A test should exist that...' spec items: the spec should specify behaviour and let implementers decide tests. Spec isn't exhaustive about tests anyway.
- **SimonWoolf** — [make section titles specific and unambiguous](https://github.com/ably/specification/pull/166#discussion_r1326085355) (textile/features.textile:748)
  - Suggests a clearer section heading like 'Effect of channel state on enter(), update(), and leave() methods' rather than the vaguer 'enter, update, and leave presence messages'.

### PR #160 — Added RSH3e2c spec point

- **lawrence-forooghian** — [keep IDL and prose in sync on renames](https://github.com/ably/specification/pull/160#discussion_r1269571462) (textile/features.textile:1187)
  - Flags mismatch between prose and IDL ('The callback is still named updateFailedCallback in the IDL').
- **lawrence-forooghian** — [prefer additive deprecation over breaking changes](https://github.com/ably/specification/pull/160#discussion_r1269582740) (textile/features.textile:1190)
  - Explains that changing an existing callback's type and behaviour is a breaking change that requires a major version bump and should target the integration branch. Suggests deprecating the old callback and adding a new optional one instead.
- **lawrence-forooghian** — [place optional args last; keep IDL syntax consistent](https://github.com/ably/specification/pull/160#discussion_r1269914953) (textile/features.textile:2327)
  - Prefers an optional argument at the end of a signature for readability; also pushes for consistent optional-syntax in the IDL.
- **lawrence-forooghian** — [pair spec changes with sdk-api-reference updates](https://github.com/ably/specification/pull/160#pullrequestreview-1543364735)
  - Requests that a corresponding PR be opened in sdk-api-reference, signalling that spec changes should propagate to the API reference.

### PR #156 — RFC: Distinguish the different meanings of a "message"

- **SimonWoolf** — [avoid spec constructs that don't map to target languages](https://github.com/ably/specification/pull/156#issuecomment-1641002950)
  - Argues against splitting publish and subscribe Message into two classes in the spec; many SDK languages don't represent nullability, so requiring two nearly identical classes would be redundant. Suggests IDL notes like 'optional for Message objects provided by the user' so each SDK can idiomatically choose. Also floats pulling the protocol page into the feature spec, since a clean split between public behaviour and wire protocol has failed in practice.
- **lawrence-forooghian** — [use IDL nullability; keep protocol rationale](https://github.com/ably/specification/pull/156#issuecomment-1642506069)
  - Argues the IDL does represent nullability, so the marker should be 'guaranteed to be populated for messages received from Ably'. Also argues that a separate protocol spec can still be valuable didactically, to help implementers understand the motivation behind the feature spec.

### PR #154 — refactor(RSC19f1): mention that protocol version is specified by CSV2

- **lawrence-forooghian** — [link to spec points that actually define the concept](https://github.com/ably/specification/pull/154#discussion_r1415995434) (textile/features.textile:153)
  - Notes an 'as specified by CSV2' reference is misleading because CSV2 doesn't define the concept of protocol version; suggests making any deviation from CSV2 explicit.

### PR #152 — Add `ChannelStateChange.hasBacklog` and return `ChannelStateChange` from attach/subscribe

- **lawrence-forooghian** — [avoid overloading 'may'; minimise optionality](https://github.com/ably/specification/pull/152#discussion_r1245133197) (textile/features.textile:592)
  - Questions making a feature 'optional', since all spec points are at SDKs' discretion anyway. Also notes 'may' is overloaded: once describing server behaviour, once describing optional SDK API choice, making it harder to read.
- **lawrence-forooghian** — [reconcile new behaviour with existing invariants](https://github.com/ably/specification/pull/152#discussion_r1245137382) (textile/features.textile:620)
  - Invokes an existing constraint (RTL2g: never emit a state change for same-state) to narrow available choices to either an UPDATE event or null, aligning with EventEmitter semantics.
- **lawrence-forooghian** — [cross-reference to avoid duplicate requirements](https://github.com/ably/specification/pull/152#discussion_r1245335789) (textile/features.textile:1466)
  - Suggests adding a cross-reference ('This attribute should be set as defined by RTL2i') to make clear that the SDK doesn't independently decide the value.
- **lawrence-forooghian** — [align wording with sibling spec points](https://github.com/ably/specification/pull/152#discussion_r1245340438) (textile/features.textile:671)
  - Recommends aligning wording to the 'optional callback' language used in RTL7c, and updating to match changed wording in the corresponding #attach spec point, for consistency.
- **lawrence-forooghian** — [avoid differently-worded duplicate spec points](https://github.com/ably/specification/pull/152#discussion_r1246542067) (textile/features.textile:613)
  - Flags what looks like a differently-worded duplicate of another spec point (RTL4d1).

### PR #149 — Untyped stats

- **lawrence-forooghian** — [clarify units, meaning, and idiomatic conversion](https://github.com/ably/specification/pull/149#discussion_r1198266356) (textile/features.textile:1380)
  - Asks multiple clarification questions about a timestamp field's meaning, copy-paste errors in wording, and whether the SDK should convert raw values to Time objects.
- **SimonWoolf** — [don't convert identifier-shaped values to Time](https://github.com/ably/specification/pull/149#discussion_r1200472854) (textile/features.textile:1380)
  - Explains an id-shaped field isn't a Time and shouldn't be converted; distinguishes identifier-format fields from time-format ones. Notes that most users only need the 'set or not' semantic regardless of internal interpretation.
- **SimonWoolf** — [include fields needed to interpret other fields](https://github.com/ably/specification/pull/149#discussion_r1200476493) (textile/features.textile:1381)
  - Suggests including additional fields (schema, appId) in the response type because they are useful for interpreting other fields.

### PR #139 — [SDK-3561] New batch specs

- **lawrence-forooghian** — [distinguish REST API behaviour from SDK behaviour](https://github.com/ably/specification/pull/139#discussion_r1181569260) (textile/features.textile:162)
  - Asks whether described behaviour is that of the REST API or behaviour that the SDK must implement; these should be clearly distinguished in the spec.
- **lawrence-forooghian** — [use specific, unambiguous type names](https://github.com/ably/specification/pull/139#discussion_r1181570663) (textile/features.textile:1511)
  - Suggests making a class name more specific (BatchPublishSpec rather than the generic BatchSpec) since it's only used for publishes.
- **lawrence-forooghian** — [specify result shape and input-output mapping](https://github.com/ably/specification/pull/139#discussion_r1181574584) (textile/features.textile:1520)
  - Asks for clarification on result structure (how many BatchPublishResult objects correspond to a BatchSpec for m messages and n channels) and whether users can associate results with input messages.
- **lawrence-forooghian** — [ensure naming consistency within a spec point](https://github.com/ably/specification/pull/139#discussion_r1181578881) (textile/features.textile:1521)
  - Flags inconsistency between type name in header (BatchPublishResult) and body text (BatchPublishChannelResult).
- **lawrence-forooghian** — [align terminology with existing docs](https://github.com/ably/specification/pull/139#discussion_r1181595293) (textile/features.textile:1542)
  - Suggests aligning a type name with terminology already used in REST API documentation ('target specifier') to avoid using 'target' and 'target specifier' interchangeably.
- **SimonWoolf** — [accommodate idioms of diverse target languages](https://github.com/ably/specification/pull/139#discussion_r1182377129) (textile/features.textile:162)
  - Suggests making a method overload (single-arg variant) optional because it doesn't translate cleanly to languages without overloading (e.g., Go).
- **SimonWoolf** — [avoid client-side validation that blocks future values](https://github.com/ably/specification/pull/139#discussion_r1182387667) (textile/features.textile:1546)
  - Warns against SDK-side validation on a 'type' field beyond 'nonempty string', since Ably may add more types in future.
- **SimonWoolf** — [express type unions rather than optional fields](https://github.com/ably/specification/pull/139#discussion_r1182392443) (textile/features.textile:1556)
  - Suggests encoding stronger type guarantees (tagged union of two concrete shapes) rather than marking many fields optional, for languages that support it.
- **SimonWoolf** — [disambiguate optionality of overloads and arguments](https://github.com/ably/specification/pull/139#discussion_r1182798342) (textile/features.textile:162)
  - Points out ambiguous wording: phrasing made the return overload seem optional while still mandating the argument overload. Proposes explicit rewording that marks the overload itself optional in idiomatic languages.
- **lawrence-forooghian** — [specify flattening/ordering explicitly](https://github.com/ably/specification/pull/139#discussion_r1184152628) (textile/features.textile:1520)
  - Requests explicit specification of how a 2D input (messages x channels) maps to a 1D result array — 'same order' is insufficient without defining the flattening.
- **lawrence-forooghian** — [don't leak internal concepts into public API](https://github.com/ably/specification/pull/139#discussion_r1194185306) (textile/features.textile:1531)
  - Argues against exposing internal (ProtocolMessage) identifiers in the public API without explanation; suggests renaming messageId to messageIdPrefix with accompanying documentation.
- **SimonWoolf** — [keep naming coherent across related APIs](https://github.com/ably/specification/pull/139#discussion_r1262700652) (textile/features.textile:1531)
  - Notes that renaming the property in the batch API but not the (identical) normal publish response would be bad API coherence; breaking-change churn must be justified.
- **lawrence-forooghian** — [audit optionality and redundancy between subclauses](https://github.com/ably/specification/pull/139#discussion_r1269523776) (textile/features.textile:2434)
  - Questions whether a field is intentionally optional, and whether a qualifying phrase like 'if the request succeeded' in a sibling spec point is thereby redundant.
- **lawrence-forooghian** — [keep IDL and prose consistent](https://github.com/ably/specification/pull/139#discussion_r1269529397) (textile/features.textile:1568)
  - Flags that IDL and prose disagree on field types (types of appliesAt and issuedBefore swapped between IDL and text).
- **lawrence-forooghian** — [specify HTTP status codes alongside error codes](https://github.com/ably/specification/pull/139#discussion_r1269856856) (textile/features.textile:263)
  - Notes that an error description should probably include the HTTP statusCode explicitly.
- **lawrence-forooghian** — [pair spec changes with user-facing docs](https://github.com/ably/specification/pull/139#pullrequestreview-1407588432)
  - Argues that documentation comments and sdk-api-reference PRs should be created alongside the spec PR, so reviewers can understand how users will interact with new functionality while reviewing.

### PR #120 — Versioning

- **lawrence-forooghian** — [follow documented conventions for removal text](https://github.com/ably/specification/pull/120#discussion_r1036273554) (textile/features.textile:514)
  - Notes that adding a parenthetical cross-reference like '(redundant to RTN19a)' isn't strictly allowed by the Removal format in CONTRIBUTING.md; suggests either adjusting the contribution rules or following them.
- **lawrence-forooghian** — [contributing guide must cover real-world cases](https://github.com/ably/specification/pull/120#discussion_r1036275444) (textile/features.textile:532)
  - Points out that listing multiple spec points as replacements isn't covered by the CONTRIBUTING format for 'Replacement'; flags mismatch between contributing rules and usage.
- **lawrence-forooghian** — [document edge cases in contributing guide](https://github.com/ably/specification/pull/120#discussion_r1036278233) (textile/features.textile:708)
  - Suggests adding guidance to CONTRIBUTING.md about how to handle removal of a clause that has subclauses.
- **lawrence-forooghian** — [apply new conventions consistently across spec](https://github.com/ably/specification/pull/120#discussion_r1039463870) (textile/features.textile:708)
  - Suggests retroactively applying newly added guidance (restoring subclauses marked as removed) for consistency with the new rule.
- **lawrence-forooghian** — [justify versioning via concrete use cases](https://github.com/ably/specification/pull/120#pullrequestreview-1199494533)
  - Questions the purpose of a Specification version number, arguing that feature spec compatibility could be expressed as the set of immutable feature spec points a library implements. Also raises that the release process is undocumented, making it unclear how a writer should know which version to cite when removing a feature.
- **SimonWoolf** — [name concepts accurately; avoid overloaded terminology](https://github.com/ably/specification/pull/120#pullrequestreview-1208703534)
  - Argues that 'Service version' is a misleading name since a given Ably service version supports multiple protocol versions, and 'protocol version' is more natural. Also questions putting protocol version in meta.yaml as metadata, since protocol changes are concrete changes that should use spec item replacement.

### PR #113 — Define API for accessing Agent identifier and its components

- **lawrence-forooghian** — [distinguish library-level from instance-level APIs](https://github.com/ably/specification/pull/113#discussion_r1022824364) (textile/features.textile:2364)
  - Clarifies that a new ClientLibraryInfo class provides library-level information without instantiating a client, distinct from per-instance ClientOptions.agents. Responds to concern about needing runtime info by suggesting a method instead of a property if needed.
- **lawrence-forooghian** — [link conditional API requirements explicitly](https://github.com/ably/specification/pull/113#discussion_r1023977349) (textile/features.textile:1667)
  - Ties method existence conditionally to another API: 'The client library must offer this method if and only if it offers the ClientOptions#agents property'.

### PR #106 — Clarify the circumstances under which RTP8f applies

- **lawrence-forooghian** — [behavioural changes need new spec points](https://github.com/ably/specification/pull/106#issuecomment-1286029806)
  - Notes that a clarifying behavioural change should be a new spec point rather than modifying an existing one.

### PR #105 — Versioning and Release Process

- **SimonWoolf** — [spec should be self-contained, avoid external indirection](https://github.com/ably/specification/pull/105#discussion_r1000849566) (textile/features.textile:60)
  - Defining components 'in the spec repo at the commit' is unclear; readers of the spec shouldn't need to consult the README or package.json to determine what the spec is referring to.
- **lawrence-forooghian** — [keep replaced spec points adjacent to replacements](https://github.com/ably/specification/pull/105#discussion_r1010894097) (textile/features.textile:101)
  - Questions why a removed/replaced spec point was moved from its previous position rather than kept alongside its replacement.
- **lawrence-forooghian** — [reference values indirectly through other spec points](https://github.com/ably/specification/pull/105#discussion_r1010894901) (textile/features.textile:432)
  - Suggests defining the protocol version value by referencing another spec point rather than hard-coding it, so it can be updated in one place.
- **lawrence-forooghian** — [order spec points for coherent reading](https://github.com/ably/specification/pull/105#discussion_r1012852549) (textile/features.textile:434)
  - Replaced spec points should be ordered alongside the thing they've been replaced by so the sequence makes coherent sense.
- **SimonWoolf** — [don't hide behavioural changes via metadata indirection](https://github.com/ably/specification/pull/105#pullrequestreview-1149574735)
  - Objects to putting the protocol version string in package.json; effectively annexes metadata to be part of the spec. Argues that a protocol version change is a genuine behavioural change that should follow spec point replacement, not be hidden via indirection.

