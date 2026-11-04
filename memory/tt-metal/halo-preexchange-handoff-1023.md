---
name: halo-preexchange-handoff-1023
description: PR 2 lanes vs "halo exchange up front + CCL-free SDPA per request" prototype; read debug-docs HANDOFF_HALO_PREEXCHANGE_1023.md first
metadata:
  type: project
---

2026-10-23: the SDPA owners asked whether PR 2's lanes change to ring SDPA is needed. A traced A/B showed a loop of single-request calls loses ~65 µs per call to its own halo wait (lanes_vs_loop_ab_1023.md). The follow-up question ("persistent output buffers") leads to a prototype: exchange all requests' halos in a separate op, then run SDPA without CCL. The standalone ring_attention_all_gather_async does full gathers only; the compact sliding halo exists only fused inside ring_joint SDPA.

**Why:** this decides the batched-SDPA contract (SDPA lanes vs a multi-request halo op).

**How to apply:** read `~/debug-docs/gemma4_batching_poc-noissue/HANDOFF_HALO_PREEXCHANGE_1023.md`. Prototype on a new local branch in `/data/kmabee/worktrees/wt_pr2_rebase_1023` (that tree's branch is PR 2's pushed head). Don't push. Related: [[batching-prs-maintenance-handoff-1017]].
