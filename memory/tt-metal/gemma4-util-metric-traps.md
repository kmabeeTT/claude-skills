---
name: gemma4-util-metric-traps
description: "Gemma4 prefill perf numbers that mislead - layer-perf trace includes per-chunk preamble, SDPA util is HiFi2-normalised, 8k matmuls throttle clock"
metadata:
  node_type: memory
  type: project
  originSessionId: 2fa57800-1a62-46a1-941d-21c04b7114f3
  modified: 2026-09-30T10:17:55.365Z
---

Measured 2026-09-30 on combined-main (87ab006f63e), 130 W:
- `test_prefill_layer_perf_chunk_n` traces the per-chunk preamble (embed+tilize, MeshPartition, RoPE embedding lookups,
  pack_rope gathers) inside every layer's signposts: ~365 us of a 2,439 us 8k sliding "layer" is really per-chunk.
- PR #58135 SDPA "math util" assumes 2048 FLOP/cycle (HiFi2); production global SDPA is LoFi, so halve it for the real
  fraction (values >100% are possible).
- tt-perf-report / harness FLOPs% assume 1350 MHz; sustained 8k matmuls run ~1050 MHz (TDP), 2k ones hold ~1345.
Details: ~/debug-docs/gemma4_prefill_chunk_sizing-57836/HANDOFF_SASHA_0930.md (Sasha items sections). Related:
[[stale-chip-locks-look-like-container]].
