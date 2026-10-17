---
name: skills-reviewers-local-run
description: "tt-metal's Skills reviewer bots skip drafts and non-main bases; run them locally with ~/claude-skills/tt-pr-skills-review before undrafting"
metadata:
  node_type: memory
  type: reference
  originSessionId: f68b287c-f996-4c93-ad60-43f350bc893e
  modified: 2026-10-17T17:00:08.253Z
---

tt-metal's two gh-aw Skills reviewers (`tenstorrent-skills-reviewer.md`, `mattpocock-skills-reviewer.md`) fire only on `pull_request` opened / ready_for_review, base `main`, non-draft, same-repo head. They have no dispatch trigger. So drafts never get them, and a stacked PR (base = another branch) never does either, even after it's undrafted. PR Gate and Merge Gate also skip drafts (dispatch them by hand), and the auto-Copilot ruleset has `review_draft_pull_requests: false` (request Copilot by hand).

The local replacement, built 2026-10-17, is `~/claude-skills/tt-pr-skills-review/` (`prepare.py` stages the pinned skills + pre-fetched data + adapted prompt per reviewer; then run one Sonnet subagent per PROMPT.md). Runs go to `~/.cache/tt-pr-skills-review/runs/`. Its first run on the batching PR 1 found a real uint32 wrap in the row-window bounds check.

Kyle's 10-17 plan: handle the local skills review + the Copilot review + CI on the draft head, then undraft. See [[batching-prs-maintenance-handoff-1017]], [[ask-before-opening-prs]].
