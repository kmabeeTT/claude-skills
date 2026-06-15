---
name: pr-review-approvers
description: This skill should be used when the user asks "who reviews this PR", "who approves PRs for this team/group", "which code owners am I waiting on", "top approvers", "who normally signs off", or wants to know — given a PR — which code-owner teams are still pending review and who in each team usually approves. Triggers on questions about review assignment, code owner teams, or finding the right reviewer for a tt-mlir (or any GitHub) PR.
version: 1.0.0
---

# PR Review Approvers

Given a PR, report which code-owner **teams** are still waiting to review it, and
for each team list the **top approvers** based on that team's recent reviewed PRs.

## When to use

- "Who do I need a review from on PR #8777?"
- "Who normally approves for `forge-developers-mlir-stablehlo`?"
- "Which groups am I waiting on, and who should I ping?"

## Usage

```bash
python3 ~/.claude/skills/pr-review-approvers/pr_review_approvers.py <pr-number-or-url> [options]
```

Pass a full PR URL, or a bare number with `--repo owner/name`. From inside a repo
checkout, a bare number resolves to the current repo automatically.

Options:
- `--prs N`     last N reviewed PRs to tally per team (default 10)
- `--scan N`    how many recent merged PRs to scan for history (default 200)
- `--teams a,b` analyze specific team slugs instead of the PR's outstanding requests
                (handy for "who approves for team X" even after the request is satisfied)

Examples:
```bash
# Outstanding code-owner teams on a PR + their top approvers
python3 ~/.claude/skills/pr-review-approvers/pr_review_approvers.py \
    https://github.com/tenstorrent/tt-mlir/pull/8777

# Ad-hoc: top approvers for specific teams regardless of PR state
python3 ~/.claude/skills/pr-review-approvers/pr_review_approvers.py 8777 \
    --repo tenstorrent/tt-mlir \
    --teams forge-developers-mlir-runtime,forge-developers-mlir-stablehlo
```

## What it reports

1. Code-owner **teams** still requested on the PR (from the PR's `requested_reviewers`),
   plus anyone who has already approved.
2. Per team: the **changed files that team owns** (resolved via CODEOWNERS), members
   who have already approved *this* PR, and a ranked list of the team's **top approvers**
   — among the most recent `--prs` PRs that any team member approved, how many each
   member approved.
3. A trailing summary of any changed files owned by **other** teams or by **individual**
   code owners, so the full ownership picture is visible.

### File → team mapping

The repo's CODEOWNERS (checked at `.github/CODEOWNERS`, then `CODEOWNERS`, then
`docs/CODEOWNERS`) is parsed with gitignore-style, last-match-wins semantics — the
same rules GitHub uses to compute reviewer requests — and each changed file is
attributed to the team(s) on its last matching rule.

## How "top approvers" is defined

An APPROVED review by a team member is the signal that the team's code-owner review
was satisfied. The script scans recent merged PRs, and for each team finds the most
recent N PRs that at least one member approved, then counts approvals per member.
This avoids needing CODEOWNERS path matching (review-request records are removed once
satisfied, but the approval record persists with the approver).

## Requirements

- `gh` CLI authenticated with **org read** access (needed for `orgs/<org>/teams/<slug>/members`).
- The org is inferred from the PR's owner.

## Notes

- A member in multiple teams is counted under each team they belong to.
- Increase `--scan` if a low-traffic team shows few/no approvals (it scans further back).
