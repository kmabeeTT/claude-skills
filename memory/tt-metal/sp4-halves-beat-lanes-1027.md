---
name: sp4-halves-beat-lanes-1027
description: Gemma4 batched 4x2k step: two SP4x TP4 halves beat SP8 lanes by 8-18% throughput, but a lone request is 1.38x slower per chunk
metadata:
  type: project
---

Measured 2026-10-27 on b09u08 with the SDPA owners' branch skrstic/gemma4-sliding-lanes-profiling (test_request_parallel_local.py, GEMMA4_ALLOW_SUBMESH=1, 4x4 cache at /data/kmabee/gemma4_tt_cache_mesh4x4_1027). B=4 step ms at 2k/32k/128k prefix: SP8 loop 141.9/168.4/248.4, SP8 lanes 130.4/156.3/237.0, 2xSP4 loop 120.6/137.7/197.1, 2xSP4 lanes 115.2/132.3/194.0. Lone request SP8 54.1/60.5/80.3 vs SP4 74.9/83.6/111.0.

AgentX sim 10-28 (debug-docs sp4_agentx_sim_1028): halves tie below saturation (worse p99), +11-24% useful tok/s past saturation.

**Why:** answers the SDPA owners' "is SP8 per request a must?" for lanes PR #61237; their profile showed lanes win by filling idle cores after the halo (16 units on 110 cores), not by overlapping the halo.
**How to apply:** the lanes-vs-no-op-change argument is now throughput (SP4 halves) vs latency (SP8). SP4 accuracy is unchecked. Record: debug-docs gemma4_batching_poc-noissue/sp4_halves_vs_lanes_1027.md. Related: [[halo-preexchange-loses-1023]]

10-28 full study (b08u08, ring + linear fabric): commit 8ab751942b6 (amended 10-29 with 14 ring replays, 256k accuracy, ring loop grids) on local branch kmabee/gemma4-sp4x2-vs-sp8 in wt_rebase_1023 (on PR5 head; push needs the forwarded SSH agent — HTTPS refused on workflow scope for a new branch). Write-up models/demos/gemma4_d_p/docs/SP4X2_VS_SP8.md + raw data in debug-docs gemma4_batching_poc-noissue/sp4x2_vs_sp8_1028/. Key: sim +16-21% under load; lone 256k 2x slower at best accurate chunk; half at chunk C = SP8 accuracy at 2C (half can't serve 8k: segmented accumulation overflows L1); same KV capacity (6 x 256k slots); SP8 5-6 lanes L1 clash.

10-29 exploration (commit 28ed241e491, local; remote still 8ab751942b6 until force-pushed): the SP4x2 gain NEEDS ONE PROCESS — a 4x4 half has no wrap link (2x4x4 descriptor: CP axis LINE); in-process on the 8x4 ring fabric its ring closes through the other half; as its own process it runs linear (87/138 vs 77/116 ms) and the sim gain falls to +5-7% (+1-2% w/ cache), worse p99. SP8 at 6 lanes doesn't close the gap (31.8 vs 32.7 ms/chunk; 5 lanes L1 clash in MLP down). SP4xTP8 (4x8) slower than SP8 on both throughput and latency. Placement (alternate/random/balanced) within 2%.
