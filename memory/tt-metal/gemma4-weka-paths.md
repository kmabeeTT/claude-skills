---
name: gemma4-weka-paths
description: Gemma4-31B weight cache and 256k golden KV reference are on /mnt/weka (since 2026-10-02); the two env vars that select them, and how to refresh them
metadata:
  type: reference
---

Both Gemma4 datasets were mirrored to Weka by the storage team on 2026-10-02 and verified: listing + sizes match the
sources, `gate_check.py` passes. Use them instead of /data and /mnt/models, which are slow cold NFS (220-700 MB/s
vs ~2.9 GB/s on Weka).

```bash
export TT_CACHE_PATH=/mnt/weka/model-cache/scratch/google/gemma-4-31B-it-Cache       # code appends tensor_cache_bf16_mesh8x4
export PREFILL_TRACE_DIR=/mnt/weka/model-weights/llm/ref-data/gpu_traces/gemma4_d_p/gutenberg-135   # PCC test golden
```

- Weight cache: 685 files, 39.43 GB, root:cache-writers 2775/0664, includes `.weights_complete.0f5bd28a03de` +
  `.host_weights.pt` (the warm-cache gate needs both). Matches the all-bfp8 `precision_overrides.json`; a different
  precision/layout writes a different marker and needs a NEW cache, not an in-place update.
- Golden: 63 files (60 in `kv_cache/`), 228.18 GB, root:storage-wg. Read by test_prefill_migration[mock-256k] only.
- Files are root-owned (storage convention), so `rsync -a` can't update them in place. To refresh, ping Vincent Du
  (storage) rather than re-running rsync. The request format they liked: one mkdir + `rsync -rt --chmod=D2775,F664`
  + an expected file count per group (cache-writers for model-cache/scratch, storage-wg for model-weights).
- `g4_env` (debug-docs `gemma4_prefill_perf.sh`) defaults to these; override ONLY via `G4_TT_CACHE_PATH` /
  `G4_PREFILL_TRACE_DIR`. A plain exported TT_CACHE_PATH is ignored on purpose: a stale /data export left by the old
  g4_env made a sweep take 16.5 min (538 s cold weight load) instead of 4:04 (2026-10-02).
- Defaults in code still point at /data / /mnt/models (`adapters/gemma4.py` `prefill_trace_default`), so CI and
  anyone not setting the vars is unchanged.
- Host-only check before using a new copy: `/data/kmabee/gemma4_weka/gate_check.py` (TT_CACHE_PATH=...), no chips.
- Measured gain (cold PCC 8192, pre-#59039 code): 26.6 -> 12.5 min, weights 210 -> 53 s, compare 892 -> 184 s.
- Staging leftovers: /data/kmabee/weka_trial (hard links, no space) and ~/weka_trial (267 GB real copy, read-only).

Related: [[gemma4-perf-run-time-budget]], [[gemma4-pcc-test-gate-and-shm]]

#59039 + Weka PCC (2026-10-02, combined branch c1d8b726768 + c76c2a178d2, pytest s, cold / warm):
8192 457 / 399 (that window had host contention: prefill+compile slow too), 4096 280 / 309, 2048 271 / 274.
Same code on /data + /mnt/models: 454 / 271, 316 / 327, 339 / 325. Asif's warm (PR): 252 / 261 / 286.
Weka mainly cuts the compare phase (102-129 s vs 119-170 s) and makes cold == warm.
