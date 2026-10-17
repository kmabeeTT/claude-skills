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

Lane rounding spread (measured 2026-10-11): the same 2k chunk computed as lanes 0-3 of one step is bit-identical at layer 0's KV and differs from layer 1 (2-3 bfp8 steps), lanes SDPA on or off; likely the TP reduce-scatter's per-device ring order (4 stacked lanes = one lane per TP device). Against the GPU it scores 0.876-0.906 min per head by lane (serial 0.905), so a 2k prompt cannot reliably pass the 0.91 gate in any mode. Use "same tokens in every lane" as a cheap lane-equivalence probe.

**4k-lane trace hang (re-dug 2026-10-15; the earlier "sync RS semaphore under SDPA CBs" cause was WRONG):** a `(4096, 4096)` two-lane trace with the default sync CCL ops hangs at the start of a replay (one trace alone, ~replay 5). Early tt-triage shows one device (TP-row column 3) idle with its dispatcher in `process_wait` on the worker-completion stream; its row waits in the first all-gather. Semaphores moved to L1_SMALL still hang; a one-lane 8k trace passes; `GEMMA4_CCL_ASYNC=1` passes. Suspect: trace worker-count accounting (dispatch), triggered by the 4k lanes programs. Write-up + repro: debug-docs gemma4_batching_poc-noissue/HANG_4K_LANES_1015.md. Lessons: a late tt-triage (minutes after the stall) shows everything idle; set `TT_METAL_OPERATION_TIMEOUT_SECONDS=30` + `TT_METAL_DISPATCH_TIMEOUT_COMMAND_TO_EXECUTE=<tt-triage>` to dump at the stall, then kill (teardown times out device by device). Per-replay host logging made it nearly deterministic. Trace capture DOES run the CB-vs-L1-buffer check, so "persistent buffer under a captured program's CBs" throws rather than hangs.

**5 lanes (1280 rows/device) measured 2026-10-15, keep 4:** the single-chip matmul sweep's "10240 rows ~15% cheaper" does not survive the model. As built, 5 lanes is −3 to −7% per lane, but the MLP down matmul's CBs end at 1,111,680 B, just above the MLP's L1 intermediates, so it clashes ("static dataflow buffers clash with L1 buffers") depending on compile history; intermediates in DRAM above 1024 rows make it robust and leave only −1 to −2%. Sim: +3% saturated throughput, median TTFT +15-20%. Write-up in prefill-docs BATCHED_PREFILL_SERVING.md "Measured: 5 lanes vs 4"; patches + scripts in ~/runs_agentx/lanes5/. A failed trace capture can hang in teardown: kill, glx_reset, rm own stale CHIP_IN_USE locks.
