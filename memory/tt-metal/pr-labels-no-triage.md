---
name: pr-labels-no-triage
description: tt-metal PR labels — suggest topic labels only; never set pr-priority / pr-risk / pr-complexity
metadata:
  type: feedback
---

When suggesting or applying labels to Kyle's tt-metal PRs, use topic labels only (e.g. `perf`, `model: gemma-4`).
Do NOT set `pr-priority:*`, `pr-risk:*` or `pr-complexity:*`.

**Why:** Kyle said so explicitly (2026-10-03) when labelling the Gemma4 perf-sweep PR; those triage labels are not ours to set.

**How to apply:** for issues, mirror the closest sibling issue's labels (e.g. #58874 for test-speedup work); for PRs, only topic labels. Related: [[ask-before-opening-prs]]
