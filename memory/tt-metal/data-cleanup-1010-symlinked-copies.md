---
name: data-cleanup-1010-symlinked-copies
description: "2026-10-10 /data/kmabee cleanup freed 578 GB; Mistral checkpoint, gemma HF hub and Mistral 8x4 cache are now symlinks to read-only shared copies"
metadata:
  node_type: memory
  type: project
  originSessionId: 3a339383-928c-4e61-b3f2-dafdcd1c3855
  modified: 2026-10-10T02:31:46.774Z
---

On 2026-10-10 /data (shared NFS) was full, so Kyle approved a cleanup. It freed 578 GB. Report and per-file deletion log: `~/debug-docs/data_disk_cleanup-noissue/`.

Three paths are now **symlinks to shared copies**, so they are read-only:
- `/data/kmabee/models/Mistral-Small-4-119B-2603` -> Weka `model-weights/llm/mistralai/...`
- `/data/kmabee/hf_cache/hub/models--google--gemma-4-31B-it` -> `/mnt/models/huggingface/hub/...`
- `/data/kmabee/mistral4_caches/ttnn_cache_8x4/mistral_small4_bh_32dev` -> Weka `Mistral-Small-4-Cache/CI/mistral_small_4_bh_32dev`

Also gone:
- the gemma tt_cache mesh8x1 and mesh4x8 dirs (only mesh8x4 remains, all precisions)
- `mistral4_blaze_weight_cache`
- the raw tracy CSVs in the Mistral4 capture dirs (`ops_perf_results` and `.tracy` were kept)

Kyle said to leave all worktrees alone.

**Why:** a run that needs to *write* one of those caches (new precision, rebuild) now hits a read-only root-owned target and fails, instead of quietly adding to the old cache.

**How to apply:** for a Mistral 8x4 cache rebuild or a variant change, point `TT_MISTRAL4_PREFILL_TTNN_CACHE` at a fresh private dir. Don't replace the symlink with a copy unless space allows. Related: [[gemma4-weka-paths]], [[mistral4-variant-rename-cache-trap]], [[data-quota-tracy-captures]].

**Unexplained deletions overnight 2026-10-11 to 10-12 (about 22:26-01:39 UTC):** something outside this box's Claude sessions removed many things under /data/kmabee:
- the three symlinks above
- every tree's `build -> build_Release` symlink (`_ttnn.so` RUNPATH needs it: `_ttnncpp.so: cannot open shared object file`)
- `wt-batching/python_env`
- the `mistral4_mla_ref_cache` contents, `ttnn_cache_stage`, `ref_cache`, `mistral4_moe_cache` and `hf_cache/datasets`

/data went from 80T to 65T used over the same window. There are no NFS snapshots. Fix for an import failure: `ln -s build_Release build` (done in tt-metal-2 on 10-12). Smoke loop now uses `~/runs_smoke/smoke_loop3.sh` (TREE=tt-metal-2).
