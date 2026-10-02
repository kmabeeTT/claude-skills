---
name: gemma4-pcc-test-gate-and-shm
description: "test_prefill_migration's 0.91 gate is a min per-head PCC, not overall; stale /dev/shm ring from another user blocks runs; the test strips PREFILL_* env"
metadata:
  node_type: memory
  type: reference
  originSessionId: 9cf77546-dee6-4647-9f1d-84d1e9f5bb83
  modified: 2026-09-24T19:15:38.366Z
---

`test_prefill_migration[mock-256k]` (Sasha's #57383; only on the combined branch until it merges):
- `GPU_PCC_THRESHOLD = 0.91` gates the MIN per-head PCC over all 60 layers (always layer 39's V head, ~0.91), not the
  overall PCC (~0.973) that reviewers quote. Report overall PCC + relative RMSE alongside the gate; quoting only min
  values caused reviewer confusion on #57454. Base clears the gate by only ~0.001.
- Runs take ~12-20 min at 256k (first run after a rebuild compiles kernels).
- `/dev/shm/tt_prefill_layer_completion_ring_<rank>` has a fixed name; another user's leftover causes
  `PermissionError` at startup. Override with `PREFILL_LAYER_COMPLETION_RING=/tt_prefill_layer_completion_ring_kmabee`,
  but the test drops all `PREFILL_*` env except an allowlist, so it must be added to that list locally.
- A one-off host `Bus error` in `fetch_queue_write` right after model load was transient; a plain retry was clean.

Related: [[gemma4-kv-pcc-early-layer-method]], [[ttnn-linear-lofi-default]].

**Chunk size comes ONLY from `GEMMA4_TEST_CHUNK_SIZE`** (adapter `tt/runners/adapters/gemma4.py`, default 8192). The old `pcc` helper in `/data/kmabee/runs_0925/lib.sh` sets `GEMMA4_PCC_CHUNK_SIZE`, which nothing reads: on 2026-09-29 a whole night of "2k/4k" PCC runs silently ran 8192. Always pass `GEMMA4_TEST_CHUNK_SIZE=<chunk>` and check `CHUNK_SIZE` in runner.log.

