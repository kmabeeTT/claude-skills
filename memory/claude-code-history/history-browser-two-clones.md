---
name: history-browser-two-clones
description: The history browser's two clones were consolidated; ~/claude-code-history now pushes to kmabeeTT, the single live repo.
metadata:
  node_type: memory
  type: project
  originSessionId: 4ea4dfad-6f0b-402b-92ff-7f40c8c52acc
  modified: 2026-09-17T00:00:00.000Z
---

The history-browser tool used to exist in two clones pushing to different
GitHub repos (`kmabee/claude-code-history` and `kmabeeTT/claude-code-history`)
with unrelated git histories. On 2026-09-03 all 24 commits of newer work were
replayed onto kmabeeTT with `git rebase --onto main bcd2da1` and pushed.

**As of 2026-09-17 the consolidation is done:** `~/claude-code-history` has
`origin = git@github.com:kmabeeTT/claude-code-history.git`, and
`~/claude-code-history-kmabeeTT` no longer exists. One working copy, one remote.

**Why:** the duplicate-clone hazard (a plain fetch+merge between them can never
fast-forward) is gone, but an old note claiming this directory pushes to
`kmabee/...` would send a future session looking for a second remote that isn't
there.

**How to apply:** treat `~/claude-code-history` as the only clone and push
straight to `main` over SSH — the repo is solo-authored with a linear
direct-to-main history and no `.github/workflows`, so no branch/PR dance is
expected unless the user asks for one. If a second clone ever reappears, move
work between them by replaying commits
(`git rebase --onto <target-tip> <last-common-content-commit> <branch>`), never
`merge --allow-unrelated-histories`.
