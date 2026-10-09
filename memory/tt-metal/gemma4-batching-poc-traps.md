---
name: gemma4-batching-poc-traps
description: "Gemma4 continuous-batching PoC (phase 1, 2026-10-09) results and the three traps hit: trace capture ordering, ring gather without backpressure, batched residual L1 clash"
metadata:
  node_type: memory
  type: project
  originSessionId: c1085a93-2f92-4200-b358-e797de20b737
  modified: 2026-10-09T06:59:20.904Z
---

Phase 1 of continuous batching (dense once on stacked rows, one ring SDPA per request) works with no kernel changes: tree /data/kmabee/wt-batching, branch kmabee/gemma4-batching-poc @ f79363b5c00 (local only), writeup ~/prefill-docs/gemma4/perf_understand/BATCHING_POC.md. 2k x4 = 135.9 ms vs 218.2 unbatched; all 28 points within +6% of the cost model's pessimistic bound. Phase 2 (batched ring SDPA, op change) awaits Kyle's OK.

Traps, each cost a debug cycle:
1. **Compile every trace shape before capturing any trace.** A compile pass after a capture lazily allocates persistent tensors (gather-index constants, per-lane buffers) onto the earlier trace's freed intermediates; each replay of that trace then clobbers them. Symptom: global K rotary heads at PCC ~0, layer 1 KV at 0.93, while an eager run matches to 0.9999.
2. **The ring SDPA gather has no backpressure** (senders push, all-gather reader resets its semaphore on exit). Back-to-back ring SDPA calls in one layer need separate receive buffers and semaphores per call; #58585 fixed the same race between sliding layers with 5 halo buffer pairs.
3. **Batched (stacked-row) residual lands lower in L1** and clashes with the 2k global SDPA CBs (end 1,414,272; L1 top 1,572,864). Fixed by spilling the residual to DRAM across attention. Find such clashes with ttnn._ttnn.reports.get_buffers(device) before the failing op (G4B_L1DUMP=1 in the PoC), not by guessing — the first guess (lane semaphores) was wrong.

Also: batched vs unbatched KV is never bit-exact (stacked rows take different matmul programs), divergence grows smoothly from 0.9999/layer; judge mechanism bugs by abrupt per-layer drops, and anchor to the GPU golden. Relates to [[gemma4-kv-pcc-early-layer-method]], [[gemma4-pcc-not-bit-reproducible]].
