---
name: no-force-push-after-undraft
description: "Once a PR is out of draft, never force-push; address review feedback in one concise new commit and wait for Kyle before pushing or replying"
metadata:
  node_type: memory
  type: feedback
  originSessionId: cb89ff89-ab05-41ba-9023-e1edff8e6e47
  modified: 2026-10-09T00:08:14.779Z
---

Once Kyle undrafts a PR, no more force pushes. All review feedback (Copilot, the Tenstorrent / Matt Pocock skills reviewers that fire on ready_for_review) goes into a single new commit with a concise message. Prepare the fix locally, then wait for Kyle's OK before pushing it or replying on the threads.

**Why:** reviewers' "changes since last review" view and line comments break on force pushes. Kyle wants to see the batched fix before anything goes out. (Said 2026-10-09 on #59939.)

**How to apply:** while a PR is a draft, rebasing and force-with-lease are fine (see [[tt-metal-push-routes]]). After undraft: commit on top, show Kyle the diff and the planned replies, push only on his go. Related: [[ask-before-opening-prs]].
