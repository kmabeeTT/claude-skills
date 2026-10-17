---
name: batching-agentx-prs-handoff-1014
description: "Turning kmabee/gemma4-batching-main (batching PoC + AgentX tools) into upstream PRs: read the 10-14 handoff first"
metadata:
  type: project
---

On 2026-10-14 Kyle chose to split `kmabee/gemma4-batching-main` (main 836bf0b + AgentX simulator + batching PoC + demo + step message + AgentX replay driver) into upstream PRs in a dedicated session on bh-glx-120-c05u08. Start by reading `~/debug-docs/gemma4_batching_poc-noissue/HANDOFF_BATCHING_AGENTX_PRS.md`: branch/commit inventory, the 4-PR plan (update_padded_kv_cache row window, ring SDPA lanes, Gemma4 batched prefill, AgentX tools) plus a combined branch kmabee/gemma4-batching-combined for local testing, acceptance numbers, open accuracy items, traps.

**Why:** the PoC was re-validated on main but is one big branch; reviewers need small PRs. Sasha (10-14) wants the AgentX tool checked in with one very terse commands-only .md, no internals.

**How to apply:** one fresh worktree per PR; draft issue/PR MDs in debug-docs and show Kyle before raising. Related: [[batching-poc-session-1010]], [[gemma4-batching-poc-traps]], [[ask-before-opening-prs]].
