---
name: no-worktrees-for-docs
description: "Work directly in ~/prefill-docs (branch there), never in a git worktree elsewhere; Kyle can't find worktrees"
metadata:
  node_type: memory
  type: feedback
  originSessionId: f15ee391-a244-49e1-b4c5-063c023b2fe6
  modified: 2026-10-07T22:17:30.795Z
---

For doc repos like `~/prefill-docs` (kmabeeTT/prefill-docs), branch and edit in the checkout itself (`git checkout -b kmabee/<topic>` in `~/prefill-docs`). Don't create a `git worktree` in another directory, and don't edit the NFS copy `/data/kmabee/prefill-docs-staging`.

**Why:** Kyle said "No work directly in ~/prefill-docs/ plz, worktrees are hard for me to find" (2026-10-07). The first half is a typo; he meant work directly in `~/prefill-docs`, not in a worktree. I had made a worktree under `/data/kmabee/` and he stopped me.

**How to apply:** when asked to save a doc "on my own branch", branch in `~/prefill-docs`. If `~/prefill-docs` is missing on a box (`~` is per-machine), ask before using another copy. Related: [[debug-docs-location]], [[allcaps-names-for-reference-docs]].
