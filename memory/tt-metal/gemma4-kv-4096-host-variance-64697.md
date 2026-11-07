---
name: gemma4-kv-4096-host-variance-64697
description: Gemma4 mock-256k disaggregated KV accuracy fails on some CI Galaxies at chunk 4096 (#64697); diverges from layer 6 forward; read the handoff first
metadata:
  type: project
---
Since #63837 (4096 default, 2026-11-05), `test_prefill_migration[mock-256k]` gives host-dependent, slightly nondeterministic results at 4096: d04u08 / d08u14 fail (min head 0.919-0.924, gate 0.928), others 0.935; 8192 is clean on every host including d08u14. Per-layer KV: layers 0-6 bit-identical, first difference at layer 7, i.e. layer 6's forward (first sliding layer after the first global layer). Hypothesis: race between the global ring SDPA and the sliding fork's multi-hop halo (4096-only). Not caused by the batching PRs (main == PR to 6 digits).

**How to apply:** read `~/debug-docs/gemma4_migration_kv_host_variance-64697/HANDOFF_KV_4096_HOST_VARIANCE_1107.md` first (data, plan, held #64697 comment). Related: [[lazy-fabric-buffer-zero-fill-race]], [[gemma4-sliding-sdpa-fork-handoff-1030]].
