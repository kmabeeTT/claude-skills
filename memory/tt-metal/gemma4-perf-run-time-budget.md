---
name: gemma4-perf-run-time-budget
description: "Where a Gemma4 256k perf run's wall time goes, the one-process sweep, the L1 clash trap when reusing a device across models, and /mnt/weka"
metadata:
  node_type: memory
  type: project
  originSessionId: be9f7d6c-9a78-4b66-9d65-c26032ba8c15
  modified: 2026-10-02T17:38:28.155Z
---

Warm single run (2026-10-02, 8192): ~121 s pytest / ~153 s wall = ~28 s python/pytest startup + device open,
~65 s weight load, 20-30 s eager compile, 2 s capture, ~7 s prefill. First run after a kernel change adds ~40 s JIT.

- Weight load is NOT disk: 34 GB of tensorbins read in 4 s warm; load_tensor_flatbuffer host-only is 1 ms/file
  (mmap). It is host->device writes (~7 GB/s aggregate; each TP shard written to all 8 CP rows). Already
  thread-pooled per chip. Only real fix: write one CP row and broadcast on-device (a project).
- Cold page cache on /data NFS (~220 MB/s) makes the load ~300 s. /mnt/weka (~2.9 GB/s cold) now holds the cache
  and the PCC golden — use them, see [[gemma4-weka-paths]].
- `test_prefill_chunk_sweep_traced` (text_demo_prefill.py) runs GEMMA4_SWEEP_CHUNK_SIZES in one process,
  memoizing `ttnn.as_tensor(cache_file_name=...)` device weights: 3 chunk sizes in 237 s wall, per-chunk numbers
  within 0.3% of separate runs. `g4_perf all` uses it.
- Trap: building a second model on the same device fails with "Statically allocated circular buffers ... clash
  with L1 buffers" unless `mesh_device.clear_program_cache()` runs between builds — cached programs keep
  op-allocated L1 semaphores (640 B/bank) that fragment L1. Model itself was freed (weakref check).

Related: [[bh-galaxy-prefill-power-throttled]], [[gemma4-prefill-perf-test-id]]

PCC test (test_prefill_migration[mock-256k], 8192, 2026-10-02 11:00, 16 min): runner weight load 182 s cold (same 671
files as perf), compile+capture ~145 s, prefill ~30 s, KV compare ~9.5 min = readback 200 s + "comparison" 348 s.
The comparison reads the 228 GB golden trace PREFILL_TRACE_DIR (default
/mnt/models/huggingface/gpu_traces/gemma4_d_p/gutenberg-135, NFS 100% full, 240-700 MB/s) lazily via mmap: ~2.4 s of
the ~3.5 s per sliding layer is I/O when cold. The test reads PREFILL_TRACE_DIR before stripping PREFILL_* and
passes it on explicitly; TT_CACHE_PATH reaches the runner too.

PCC storage A/B (2026-10-02, chunk 8192, pre-#59039 code, both cold via fadvise eviction), PCC bit-identical:
- A today (/data weights + /mnt/models golden): 1599 s; weights 210 s; compare phase 18 min (comparison 892 s).
- B local copy (~/weka_trial, mirrors /mnt/weka layout): 749 s; weights 53 s; compare 6.2 min (comparison 184 s).
Readback (~205 s) is chip->host and unaffected. #59039 (Asif, parallel preadv + prefetch) is measured warm only.

2026-10-03 speedups (sweep 2k/4k/8k warm on Weka: 307 s -> 177 s wall):
- Rebuild host waste: `create_rope_caches` randn(1, max_seq_len, hidden) dummy (6 s) and `load_attention_weights`
  reshuffling placeholder Q/K/V/O on a warm cache (~8 s). Fixed in cfa37bc3147 on kmabee/gemma4-perf-chunk-sweep:
  rebuild 22.7 -> 5.6 s, first build 67.6 -> 50 s. Profile builds with a pytest plugin that patches the module from
  `pytest_collection_modifyitems` (item.module) -- patching in pytest_configure hits a different module object.
- NFS venv imports cost 46-54 s per process even warm; local copy 4.6 s (`g4_localvenv`, ~/venvs/<tree>-python_env).
- CP-split weight write + all_gather: 145 ms -> 3.3 ms per 122 MB weight, bit-identical 32/32, but needs a second
  cache variant; deliberately not pursued.
