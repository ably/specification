---
name: commit
description: Generate a commit message for the current staged changes and commit
disable-model-invocation: true
allowed-tools: Bash(git diff *), Bash(git status), Bash(git commit *), Bash(git log *), Bash(curl *), AskUserQuestion
---

# Commit Staged Changes

Generate a high-quality commit message for the currently staged changes, present it
for approval, then commit.

## Step 1: Gather context

Run these commands to understand the staged changes:

1. `git diff --cached --stat` to see which files are staged
2. `git diff --cached` to see the full diff
3. `git status` to check overall state (never use -uall flag)

If there are no staged changes, tell the user and stop.

## Step 2: Determine the intent

Determine the **intent** of the change from the diff. If the intent is
not clear from the code alone, use AskUserQuestion to ask the user to
clarify the purpose of the change before writing the message.

## Step 3: Generate the commit message

Write a commit message following ALL of the guidance below. Where the
project-specific guidance conflicts with the general guidance, the
project-specific guidance takes precedence.

### General commit guidance

!`curl -sf https://raw.githubusercontent.com/ably/engineering/refs/heads/main/best-practices/commits.md`

### Project-specific guidance (takes precedence)

This repository contains the Ably specification. Commit messages should
follow the conventions established in the existing history.

#### Summary line style

Specification changes use one of two styles depending on the nature of the
change:

- **Spec content changes** (adding, modifying, or removing spec points):
  Use a `spec/<product>:` prefix where `<product>` identifies the
  specification being changed (e.g. `ait` for AI Transport, `chat` for
  Chat, `objects` for Objects). Follow with an imperative sentence.
  Reference spec point IDs when relevant.
  Examples:
  - `spec/ait: add initial AI Transport features specification`
  - `spec/ait: clarify AIT-CT2 send semantics`
  - `spec/chat: extract shared tombstonedAt calculation into RTLO6`
  - `spec/objects: delete RTO5c1b1c (redundant to RTO5f3)`

- **Non-spec changes** (build, CI, tooling, formatting): Use a conventional
  commit prefix such as `chore:` or `build:`.
  Examples:
  - `chore: fix typographical errors and improve consistency in features.md`
  - `chore: migrate project to Hugo and restructure build pipeline`
  - `build(deps-dev): bump braces from 3.0.2 to 3.0.3 in /build`

#### Body

- Keep the body concise. Explain **what** changed and **why**, not just
  restate the diff.
- If the commit resolves a Jira ticket, add it on its own line in the body
  (e.g. `Resolves AIT-466`). Do NOT include the ticket ID in the summary.
- Omit the body entirely if the summary alone is sufficient.
- Further paragraphs come after blank lines.
  - Bullet points are okay, too
  - Typically a hyphen (-) is used for the bullet, followed by a single
    space

## Step 4: Present the message

Show the complete commit message to the user in a fenced code block.

Then ask: **"Do you want to commit with this message, edit it, or cancel?"**

## Step 5: Act on the response

- **Accept / looks good / yes**: Run the commit using a heredoc:
  ```
  git commit -m "$(cat <<'EOF'
  <the message>
  EOF
  )"
  ```
- **Edit**: The user will provide a revised message or describe changes.
  Apply their edits and show the updated message for confirmation again
  (return to Step 3).
- **Cancel**: Do nothing.

After a successful commit, run `git log -1` to confirm.
