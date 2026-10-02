---
name: ring-sdpa-seg-accum-one-q-per-core
description: ring_joint_sdpa silently disables segmented accumulation when any core gets >1 Q chunk (units > SDPA cores); Gemma4 12288/q96 fails PCC because of it
metadata:
  type: project
---
`ring_joint_sdpa_program_factory.cpp` enables segmented accumulation only if `max_q_per_core == 1` (and no K split).
If ceil(rows_per_device / q_chunk) x local heads > SDPA cores (110 on BH Galaxy), it silently runs unsegmented and long-
prefix global attention drifts. Found 2026-10-01: Gemma4 chunk 12288 / q96 (128 units) failed PCC (0.9693, RRMSE 0.248);
q128 (96 units) passes (0.981). Op repro: packed K/V + kv_mean_offset 1.0 over 6 chunks (RMSE 0.071 vs 0.035).
**How to apply:** when choosing global q for a new chunk size, keep units <= SDPA cores. Details:
~/debug-docs/gemma4_prefill_chunk_sizing-57836/RESULTS_NIGHT_1001.md. Related: [[gemma4-util-metric-traps]].
