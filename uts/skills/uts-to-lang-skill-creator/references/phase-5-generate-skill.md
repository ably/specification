# 7. Phase 5: generate the skill files

Part of the `uts-to-lang-skill-creator` skill: read [SKILL.md](../SKILL.md) first (ground rules, stop points, path convention). Links that climb out of the skill directory are spec-repo paths: resolve them against the spec clone, not against this file's installed location.

Contents:

- [7.1 Step 5a: create the layout and the mapping file](#71-step-5a-create-the-layout-and-the-mapping-file)
- [7.2 Step 5b: write the resolver](#72-step-5b-write-the-resolver)
- [7.3 Step 5c: write the audit](#73-step-5c-write-the-audit)
- [7.4 Step 5d: fill the construct catalogue](#74-step-5d-fill-the-construct-catalogue)
- [7.5 Step 5e: write the module notes](#75-step-5e-write-the-module-notes)
- [7.6 Step 5f: write `SKILL.md`](#76-step-5f-write-skillmd)

Generate the files in this order: each one depends on the previous ones. `SKILL.md` comes last because it references all the others; its outline is fixed by the guide, so you can draft it early, but finish it last.

## 7.1 Step 5a: create the layout and the mapping file

1. Create the directory layout from guide [3.1](../../../docs/writing-uts-spec-translator-skills.md#31-layout) (plus the working-records directory, D-24). Then create the `.agents/skills/uts-to-<lang>` link (or the copy and its CI check) that D-01 chose, so Codex loads the skill too.
2. Write `uts-package-mapping.json` from D-03, in the shape of guide [3.2](../../../docs/writing-uts-spec-translator-skills.md#32-the-mapping-file).
3. Record tier readiness as data in the mapping (guide 3.2 allows per-module defaults as data, and guide [4, step C](../../../docs/writing-uts-spec-translator-skills.md#phase-1-selection-steps-0-and-af) refuses unready tiers), so the skill can read it without the working records. *Procedure recommendation:* an `unready` object per module, e.g. `"unready": {"proxy": "G-16: ProxySession not built"}`, which the resolver reports as `tiers.<tier>.ready: false` with `blockedBy`.

**Acceptance:**

- [ ] Every module the user wants has an entry; every tier value is one path relative to the repo (or a declared root), never machine-absolute.
- [ ] Every derived namespace is unique (a module segment after the tier, or a module-specific prefix).
- [ ] `notes` paths are relative to the skill directory and the files exist (placeholders at this point are fine).
- [ ] Hand-maintained entries are marked (e.g. in `_comment`) and listed in the Design record.
- [ ] Every tier the harness design marks unready has an `unready` entry with the blocking gap-table row.
- [ ] The mapping has a `harness` entry (root, README, per-tier sources and the complete smoke-test and self-test command), every path in it exists, no harness test lies inside any tier `targetDir`, and no `targetDir` lies inside the harness root (guide [3.2](../../../docs/writing-uts-spec-translator-skills.md#32-the-mapping-file), [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must)).
- [ ] The file is valid JSON, UTF-8, LF line endings.

## 7.2 Step 5b: write the resolver

Implement `scripts/resolve_uts.py` (or the language chosen in D-02) to every row of guide [8.1](../../../docs/writing-uts-spec-translator-skills.md#81-resolver-resolve_utspy-must). It prints exactly one JSON object.

Output contract: the fields of guide 8.1, including `harness` (the mapping's harness entry with paths validated, still repo-relative), `testRoot` when the mapping declares a root, including `testFile` wherever the target file name isn't `<className>.<ext>`, plus `ready` and `blockedBy` per tier (*procedure recommendation*: from the mapping's `unready` data, [7.1](#71-step-5a-create-the-layout-and-the-mapping-file)). Also implement the optional `specRepo` (`{sha, dirty, dirtyFiles}`; making it mandatory is a *procedure recommendation*), so the skill takes the clone's state for headers and reports ([8.1](../../../docs/writing-uts-spec-translator-skills.md#81-resolver-resolve_utspy-must), [9.1](../../../docs/writing-uts-spec-translator-skills.md#91-record-what-you-translated-from-must), [9.4](../../../docs/writing-uts-spec-translator-skills.md#94-local-clone-vs-fetching-main)) from the script rather than recomputing it. Choose the namespace and build-target field names and document them in `SKILL.md`. For example:

```json
{
  "ok": true,
  "sourceModule": "realtime",
  "specRepo": { "sha": "<full-sha>", "dirty": false, "dirtyFiles": [] },
  "mapped": true,
  "translationNotes": "<abs path to references/realtime-mapping.md, or null if none declared>",
  "harness": {
    "root": "<repo-relative harness root>",
    "readme": "<repo-relative harness README>",
    "tiers": { "unit": { "sources": ["..."], "tests": "<command>" }, "integration": { "...": "..." }, "proxy": { "...": "..." } }
  },
  "tiers": {
    "unit": {
      "present": true,
      "sourceDir": "<spec-clone>/uts/realtime/unit",
      "targetDir": "<repo-relative target dir>",
      "namespace": "<derived namespace/package, if the language has one>",
      "buildTarget": "<derived test project/target/module>",
      "ready": true,
      "specs": [ { "file": "connection/connection_failures_test.md", "className": "ConnectionFailuresTests" } ]
    },
    "integration": { "present": true, "...": "..." },
    "proxy": { "present": true, "ready": false, "blockedBy": "G-16: ProxySession not built", "...": "..." }
  }
}
```

Errors are `{"ok": false, "code": "<CODE>", "message": "<text>"}`, with a distinct code for each failure guide 8.1 describes (not a UTS module path, directory not found, no tier directories, mapping missing or malformed, bad target name; the guide's example codes are a fine naming), plus one for a declared notes file that is missing (e.g. `NOTES_NOT_FOUND`) and one for a name collision (e.g. `NAME_COLLISION`).

**Acceptance** (each verified by running the script in [8.1](phase-6-validate-skill.md#81-run-the-resolver-on-every-module)):

- [ ] Every row of guide 8.1 is implemented: validation, error objects, output contract, path-only tier detection (including specs in tier sub-directories, e.g. `realtime/integration/channels/`), exclusions relative to the tier base, deterministic runner-collectable naming (D-04), collision detection (D-05, including file-name uniqueness where the runner needs it), validate-then-write `--create` writing the D-03 default layout, an error for a missing notes file.
- [ ] `harness` matches the mapping, with every path validated (repo-relative) and existing; `ready`/`blockedBy` match the mapping's `unready` data; `testFile` is present wherever the file name isn't derived from `className`.
- [ ] Never crashes: any exception becomes `ok: false` with a code.

## 7.3 Step 5c: write the audit

Implement `scripts/audit_translation.py` to every row and the parsing contract of guide [8.2](../../../docs/writing-uts-spec-translator-skills.md#82-audit-audit_translationpy-must). The spec-side parser is language-independent; write it yourself from the parsing contract (never by porting another SDK's audit, [2.1](../SKILL.md#21-your-inputs)). The test side needs four language-specific patterns, taken from the Design record, the harness and the construct catalogue:

| Test-side pattern | Source |
|---|---|
| Tag marker (`UTS:` after the line-comment marker) | D-06 |
| Assertion calls (every assertion form the catalogue maps `ASSERT …`, `FAILS WITH`, `THROWS`, `EXPECT THROW` and `AWAIT_ERROR` to) | [7.4](#74-step-5d-fill-the-construct-catalogue) |
| Wait calls (every harness helper the catalogue maps `AWAIT`, `AWAIT_STATE`, `poll_until`, … to) | [7.4](#74-step-5d-fill-the-construct-catalogue); the harness README |
| Comment syntax (line and block), so commented-out assertions are ignored | P-01 |

Write these as data at the top of the script, so a catalogue change is a one-line edit. Match the longest keyword first on both sides.

Output: use the shape in guide 8.2 "Output shape (SHOULD)", including `notVerifiable` for a spec with no `**Test ID**` lines (not zero tests); if you depart from it, document your shape in `SKILL.md`. Use one exit code for clean, a distinct one for ID problems (missing, orphan, duplicate) and another for "couldn't run".

**Acceptance** (verified in [8.2](phase-6-validate-skill.md#82-test-the-audit-itself)):

- [ ] Every MUST row and the whole parsing contract of guide 8.2 are implemented, including the end-at-heading rule (a guide SHOULD that this procedure requires: *procedure recommendation*): ID coverage (`missing`, `orphan`, `duplicate`, distinct non-zero exit), per-test ledger, separate assert and await counts (spec-side `FAILS WITH` / `THROWS` / `EXPECT THROW` / `AWAIT_ERROR` lines counted as assertions, awaited or not, and `poll_until` / `poll_until_success` / `POLL_UNTIL` / `AWAIT UNTIL` / `WAIT_FOR` lines counted as waits, matching the test side), commented-out assertions ignored, never crashes, unverifiable specs reported.
- [ ] Where your parsing differs from the contract, `SKILL.md` says so (guide 8.2 "Implement exactly this, or say where yours differs").
- [ ] SHOULD items you implemented are listed in `SKILL.md`; the ones you didn't are listed in the Final report.

## 7.4 Step 5d: fill the construct catalogue

This step produces the construct table that goes into `SKILL.md` (and, for module-specific rows, into the notes).

1. **Start from every row of guide [section 6](../../../docs/writing-uts-spec-translator-skills.md#6-pseudocode-construct-catalogue)** (6.1 to 6.6) and the notes in [6.7](../../../docs/writing-uts-spec-translator-skills.md#67-notes-on-the-catalogue). Copy the "Construct" and "Meaning" columns; replace the Swift and Kotlin columns with one column for this repo.
2. **Fill the rendering for each row** from the harness you built and the SDK: the exact helper or framework call, with its real signature (read it from the source). Don't copy the guide's Swift or Kotlin cells, or anything seen in a reference-implementation read ([2.1](../SKILL.md#21-your-inputs)); they illustrate other SDKs.
3. **Scan the corpus for constructs the guide doesn't list** (guide section 6 says the catalogue isn't exhaustive). Run the scanner below over each module the skill covers, and add a row for every uppercase keyword or snake_case call you can't account for.
4. **Give every row a status:**
    - `mapped`: a direct rendering;
    - `mapped (inferred)`: an *(undocumented)* construct, meaning inferred from its uses (list one use);
    - `stand-in`: a sanctioned harness stand-in, disclosed in the file header (guide [7.2](../../../docs/writing-uts-spec-translator-skills.md#72-harness-stand-ins-are-not-deviations));
    - `not available`: the harness lacks the capability; the rendering says what the skill does (extend the mock, or record a Mock Infrastructure Limitation; never substitute a similar mock outcome, guide [5.2](../../../docs/writing-uts-spec-translator-skills.md#52-fidelity)), and the Final report has a plan;
    - `n/a`: no spec in the covered modules uses it (say so after scanning).
5. **No blank cells.** Collect every row the skill can't render and has no plan for, from one scan, into a single **STOP-9**.

Corpus scanner: run `python3 <skill-dir>/scripts/scan_constructs.py <spec-clone>/uts/<module>`. It prints the uppercase keywords and snake_case calls used in `pseudo` fences, outside comments and string literals, with counts; compare its output with the catalogue, and use it in Phase 2 to list the harness symbols the corpus uses.

The keyword list also contains wire constants and enum values (`ATTACHED`, `MAP_SET`, `LWW`); classify those under the guide's "wire constants" and enum rows rather than as new constructs. The scanner sees only `snake_case(` calls; method-style harness calls such as `mock_ws.active_connection.send_to_client(…)` are caught, but camelCase members (`onConnectionAttempt`) are not, so also read the helper specs' interfaces. Ship it in the generated skill as `scripts/scan_constructs.py` (copy this skill's script; it is language-independent), as guide [section 6](../../../docs/writing-uts-spec-translator-skills.md#6-pseudocode-construct-catalogue) and [3.1](../../../docs/writing-uts-spec-translator-skills.md#31-layout) recommend (SHOULD), because a re-sync re-scans the corpus (guide [9.2](../../../docs/writing-uts-spec-translator-skills.md#92-a-re-sync-mode-should) step 2); record the choice in the Design record (D-19).

**Acceptance:**

- [ ] Every guide section 6 row is present with a rendering and a status; none blank.
- [ ] Every scanner hit in the covered modules is either a catalogue row, a wire constant or enum value, a spec-local name, or internal pseudocode of a helper spec or `objects/PLAN.md` (implemented as harness or ignored, never translated).
- [ ] Every rendering names a symbol that exists in the harness or the SDK (you read it), or is marked `not available` with a plan.
- [ ] The guide's flagged traps are rendered correctly: `CONTAINS_IN_ORDER` as a subsequence; `poll_until` returns the settled value; `poll_until_success` as a separate helper; `AWAIT_STATE` race-free and failing fast on FAILED; both `AWAIT_STATE` spellings; `create_proxy_session(endpoint:)` per `proxy.md`, with the endpoint defaulted when a spec passes only `rules:` (guide [5.7](../../../docs/writing-uts-spec-translator-skills.md#57-waits-must-catch-events), [6.7](../../../docs/writing-uts-spec-translator-skills.md#67-notes-on-the-catalogue)).

## 7.5 Step 5e: write the module notes

Write `references/<module>-mapping.md` for every module chosen in D-23. Cover the thirteen items in guide [3.4](../../../docs/writing-uts-spec-translator-skills.md#34-recommended-outlines-should) ("A module notes file should cover"), in that order. For each item, either fill it or write "Not applicable: <reason>". The items that most need evidence:

- **Item 1 (source of truth and runtime status):** name the IDL the notes apply (for `objects`, check whether the SDK follows `objects-features.md` in the clone or another variant; guide 3.4 item 1 explains the typed-SDK case) and whether the module is implemented, which decides whether evaluate mode is possible.
- **Item 5 (type mapping):** for every polymorphic or union type in the pseudocode, the SDK type and which conversions throw or return null. Read the SDK source for each.
- **Item 8 (internal access):** the ladder from D-12 and the list of white-box specs. To find candidates, look for specs that construct internal classes or call members the public API doesn't have (the guide's white-box row in [6.6](../../../docs/writing-uts-spec-translator-skills.md#66-mocks-fixtures-and-harness) lists examples), then confirm each against the SDK's public surface.
- **Item 9 (helper-spec coverage):** the module's rows of the symbol tables from [4.3](phase-2-design-harness.md#43-step-2c-map-each-helper-spec-to-native-code), as built, with each fixture helper's scope and every sanctioned stand-in.
- **Item 12 (worked example):** translate one short real test from the module by hand, name each mechanical rewrite, and make sure it compiles (it becomes one of the skill's examples; [8.7](phase-6-validate-skill.md#87-verify-the-skills-own-examples)).

A module whose mapping you can't author yet gets a **placeholder** notes file that says so; the skill must then refuse that module (guide [4](../../../docs/writing-uts-spec-translator-skills.md#phase-1-selection-steps-0-and-af), "If the module's notes file exists but is only a placeholder").

**Acceptance:**

- [ ] All thirteen items present or marked not applicable with a reason.
- [ ] Every SDK and harness symbol named in the notes exists at the recorded repo SHA.
- [ ] Overrides of the generic flow (reading list, naming rendering, deviations location, expected audit shortfalls) are explicit, and no naming override drops the spec point from test names (guide [5.1](../../../docs/writing-uts-spec-translator-skills.md#51-traceability)), so the skill can say "the notes win" (guide [4, step 1](../../../docs/writing-uts-spec-translator-skills.md#phase-2-per-spec-steps-17)).
- [ ] No line numbers; cite symbols and headings (guide [12](../../../docs/writing-uts-spec-translator-skills.md#12-lessons-learned)).

## 7.6 Step 5f: write `SKILL.md`

Follow the outline in guide [3.4](../../../docs/writing-uts-spec-translator-skills.md#34-recommended-outlines-should). Write each part as the language rendering of the guide's rule, and link to the UTS doc that defines the meaning rather than copying it (guide ["What the skill owns, and what it defers"](../../../docs/writing-uts-spec-translator-skills.md#what-the-skill-owns-and-what-it-defers)).

| Part of `SKILL.md` | Content | Guide |
|---|---|---|
| Frontmatter | The portable fields of guide 3.3: `name: uts-to-<lang>`, equal to the directory name; a pushy, third-person `description` of at most 1,024 characters with trigger phrases, a "Not for …" boundary and no `<` or `>`; `license`; `compatibility`; `allowed-tools` from D-22; string-valued `metadata` with `short-description`. Claude Code-only fields only as decided in D-26; the model statement in the opening lines | [3.3](../../../docs/writing-uts-spec-translator-skills.md#33-frontmatter-and-arguments) |
| Usage guard | No argument → print the usage line and stop, without relying on `$ARGUMENTS` (read the argument from the user's words); the skill's own scripts and files named relative to the skill directory, never `.claude/skills/…`; placeholder paths only | [3.3](../../../docs/writing-uts-spec-translator-skills.md#33-frontmatter-and-arguments) |
| Required reading (step 0) | As guide 4 step 0 (including the "Pseudocode Conventions" section of `uts/README.md`), from the same clone as the module; record its SHA and dirty state (the resolver's `specRepo`); for each selected spec in `dirtyFiles`, stop and ask, and if the user proceeds stamp its blob (guide 9.1) | [4](../../../docs/writing-uts-spec-translator-skills.md#phase-1-selection-steps-0-and-af), [9.1](../../../docs/writing-uts-spec-translator-skills.md#91-record-what-you-translated-from-must), [9.4](../../../docs/writing-uts-spec-translator-skills.md#94-local-clone-vs-fetching-main) |
| Generated-skill Phase 1 (selection), steps A–E | As guide 4, with this repo's resolver commands; step C offers only tiers the resolver reports `present` and `ready`, and names `blockedBy` for the others | [4](../../../docs/writing-uts-spec-translator-skills.md#phase-1-selection-steps-0-and-af) |
| Harness preflight (step F) | As guide 4 step F: compile (or collect) the harness and the test target; run the chosen tier's smoke tests and self-tests with the resolver's `harness` command; check the harness README's Known gaps against the selected specs; on red, stop and report a harness or environment problem, never an SDK deviation; record the result for the final report | [4](../../../docs/writing-uts-spec-translator-skills.md#phase-1-selection-steps-0-and-af), [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must) |
| Harness reference | Per tier, from the resolver's `harness` output: harness root and README (full repo path), helper sources to read, smoke-test and self-test locations and run commands, the generated-test run command, and a pointer to the README's Known gaps; no inlined helper signatures; smoke tests named as wiring examples only. Also the mid-run harness-change rule (guide 5) | [3.4](../../../docs/writing-uts-spec-translator-skills.md#34-recommended-outlines-should), [2.7](../../../docs/writing-uts-spec-translator-skills.md#27-harness-smoke-tests-and-self-tests-must) |
| Generated-skill Phase 2 (per spec), steps 1–7 | As guide 4, with this repo's commands; the harness README and helper sources from the resolver's `harness` output; for the reference test per tier, write `none yet` until [8.8](phase-6-validate-skill.md#88-name-the-reference-tests) names one | [4](../../../docs/writing-uts-spec-translator-skills.md#phase-2-per-spec-steps-17), [8.3](../../../docs/writing-uts-spec-translator-skills.md#83-review-checklist-must-after-the-audit) |
| Translation rules | The language rendering of every rule in 5.1–5.9, including the decisions D-04 to D-18 | [5](../../../docs/writing-uts-spec-translator-skills.md#5-translation-rules) |
| Construct table | The catalogue from [7.4](#74-step-5d-fill-the-construct-catalogue), with the stop-and-ask rule for anything unmapped | [6](../../../docs/writing-uts-spec-translator-skills.md#6-pseudocode-construct-catalogue) |
| File template per tier | Header, imports, suite (serialised if D-14 says so), per-test shape; from the outline in 3.4 | [3.4](../../../docs/writing-uts-spec-translator-skills.md#34-recommended-outlines-should) |
| Evaluation | Guide 7 rendered with D-08 to D-11 and D-21 | [7](../../../docs/writing-uts-spec-translator-skills.md#7-evaluation-and-deviations) |
| Integration tiers | Direct-sandbox and proxy wiring with this harness's symbols (D-15, D-18); file templates | [2.3](../../../docs/writing-uts-spec-translator-skills.md#23-sandbox-provisioning-and-fixtures-must-for-integration-tiers), [2.4](../../../docs/writing-uts-spec-translator-skills.md#24-the-proxy-must-for-the-proxy-tier), [5.5](../../../docs/writing-uts-spec-translator-skills.md#55-integration-tier-hygiene) |
| Verification | Guide 10 with the exact commands from the Repo profile | [10](../../../docs/writing-uts-spec-translator-skills.md#10-verification-and-ci) |
| Re-sync mode | Guide 9.2 and 9.3, with D-19 | [9.2](../../../docs/writing-uts-spec-translator-skills.md#92-a-re-sync-mode-should), [9.3](../../../docs/writing-uts-spec-translator-skills.md#93-renamed-merged-and-added-ids) |
| Final report | The format, including the model line | [11](../../../docs/writing-uts-spec-translator-skills.md#11-final-report-format) |
| Commits | No commits by default; list changed files and hand-maintained project files (D-20) | [10](../../../docs/writing-uts-spec-translator-skills.md#10-verification-and-ci) |

**Acceptance:**

- [ ] Every part in the table is present.
- [ ] The skill is module-generic: module-specific rules live in the notes.
- [ ] No inline copy of a semantic rule where a link to its source would do; in particular the `deviations.md` format is referenced, not redefined.
- [ ] No line numbers; no personal or machine-absolute paths; no reference to other SDKs' skills (reference-implementation reads during creation are recorded in the working records, never cited in the skill).
- [ ] None of the guide's [Patterns to avoid](../../../docs/writing-uts-spec-translator-skills.md#patterns-to-avoid) appears in the skill, its notes, its scripts or the harness.
- [ ] The Harness reference names only files, filters and commands that exist, and doesn't inline helper signatures.
- [ ] Every command in it is one the Repo profile records as run. (Running each through the skill, and compiling every example, are Phase 6 checks: [8.5](phase-6-validate-skill.md#85-exercise-the-skills-other-paths), [8.7](phase-6-validate-skill.md#87-verify-the-skills-own-examples).)
- [ ] Every helper or SDK symbol it names exists.
- [ ] The frontmatter passes a standard validator (for example skill-creator's `quick_validate.py`): only portable fields unless D-26 says otherwise, `name` equal to the directory, description of at most 1,024 characters with no `<` or `>`, string `metadata` values.
- [ ] No `.claude/skills/` path in `SKILL.md`, the notes or the scripts; the scripts find the mapping and notes relative to their own file, not the working directory.
