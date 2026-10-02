---
name: debug-docs-batch-commits
description: debug-docs commits - batch them into a few logical commits per milestone instead of one push per tracker tweak
metadata:
  node_type: memory
  type: feedback
  originSessionId: 002d1d50-3012-49ce-a585-e77c4d0e6f00
  modified: 2026-10-02T00:38:36.997Z
---

Don't commit + push debug-docs after every small edit (tracker row, wording tweak). Commit locally and push at
milestones, one commit per topic (e.g. "issue draft", "merge state", "tracker + comments", "runbook").

**Why:** on 2026-10-02 the user had me squash 28 pushed micro-commits ("tracker", "tracker update", ...) into 4; that
needed a force-push to a repo other sessions also push to.

**How to apply:** if a squash of pushed commits is still needed: tag the old tip `backup/...` and push the tag, rebuild
in a temp worktree with `git checkout <old> -- <files>` per group, verify `git diff <old> <new>` is empty, then
`push --force-with-lease=main:<old>`. Check the range holds only this session's commits first. See [[shared-tree-multi-session]].
