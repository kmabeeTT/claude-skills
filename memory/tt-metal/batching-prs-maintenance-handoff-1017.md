---
name: batching-prs-maintenance-handoff-1017
description: From 10-17 the Gemma4 batching PRs are in maintenance (open, CI, review); read debug-docs HANDOFF_PR_MAINTENANCE_1017.md first
metadata:
  type: project
---

Development and testing of the five Gemma4 continuous-batching PRs (umbrella tenstorrent/tt-metal#60861) finished 2026-10-17: all ready to open (PR_READINESS_1017.md). Ongoing work is opening them, dispatching CI, wiring PR numbers into #60861 / sub-issues / gist, and handling review feedback.

**Why:** Kyle moved this to a fresh, cheaper session on 10-17.
**State 2026-10-18:** PR 1-3 are open as drafts #61236 / #61237 / #61238 (Copilot fixed, CI dispatched). PR 5 is pushed and hardened but not opened (Kyle opens it). Read `SESSION_SUMMARY_1018.md` in the same folder first for shas, CI run ids and what is open.

**How to apply:** then `~/debug-docs/gemma4_batching_poc-noissue/HANDOFF_PR_MAINTENANCE_1017.md` (state table, CI commands per PR, rules, known not-ours failures). Supersedes [[overnight-1015-state]] and [[batching-agentx-prs-handoff-1014]] for this work.
