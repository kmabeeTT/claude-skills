---
name: gemma4-sliding-sdpa-fork-handoff-1030
description: SDPA owners rejected landing PR 2 lanes in the shared ring joint op; plan is a Gemma4-owned fork (PR A) then lanes on it (PR B); read the debug-docs handoff first
metadata:
  type: project
---

2026-10-30: SDPA owners asked Kyle not to land #61237 (lanes in shared ring_joint_sdpa: sliding/Gemma4-only) and approved forking. Plan: PR A = fork `ttnn.experimental.gemma4.sliding_ring_sdpa` at `ttnn/cpp/ttnn/operations/experimental/gemma4/sliding_ring_sdpa/` (no functional change, Gemma4 sliding layers bit-identical), PR B = lanes on the fork, replacing #61237 (close it with links, don't rewrite). PR 5 then calls the fork; PR 7 #63438 independent.

**Why:** keeps the shared op one request per call for GPT-OSS sliding and others; Gemma4 owners can iterate alone.
**How to apply:** read `~/debug-docs/gemma4_batching_poc-noissue/HANDOFF_GEMMA4_SLIDING_SDPA_FORK_1030.md` first (scope, file map, CODEOWNERS, test plan, traps). Ask Sasha about his `svuckovic/gemma4-varlen-sdpa-pr` `experimental/gemma4/rjsdpa` namespace before creating the dir. Related: [[lazy-fabric-buffer-zero-fill-race]], [[ring-joint-kernel-config-buffer-cap]], [[sp4-halves-beat-lanes-1027]].
