---
name: ask-before-opening-prs
description: Never open (even draft) PRs without asking the user first; push branches + draft descriptions instead
metadata:
  type: feedback
---
Do not open GitHub PRs (including drafts) on the user's behalf without asking first, even when they said "turn it into
a PR" or "do all the things". Push the branch, write the PR description to a file, and ask.
**Why:** On 2026-10-01 I opened draft PR #58650 overnight while the user was away; they asked me not to do that without
telling them.
**How to apply:** Before `gh pr create`, stop and ask. Branch pushes and local draft files are fine.
