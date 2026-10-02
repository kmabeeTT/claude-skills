---
name: gemma4-sliding-sdpa-ksplit
description: "Sliding-window ring SDPA K split + local-first halo overlap (branch kmabee/gemma4-0929-dev): correct, but only -1% each at 2k; the sliding op's ~180 us at 2k is mostly fixed cost, not splittable math"
metadata:
  node_type: memory
  type: project
  originSessionId: 170463d4-8ab0-424a-a66a-5dd1fd442cbc
  modified: 2026-09-29T04:19:50.642Z
---

2026-09-29, Gemma4 BH galaxy 8x4:
- Halo overlap: the sliding reader waited for the whole halo before any compute (ring_joint_reader.cpp). Plan now puts local K chunks first and waits before the first halo chunk. Stale-halo upper bound was -3.6% at 2048; real version -1% (63.7->63.1), 8192 -1.6%.
- Sliding K split (bands split each unit's work plan; needs oldest-first order so the reducer band holds the diagonal; restore CBs must be allocated for sliding; short plans < 2 chunks/band stay whole on the reducer, because a 2-item plan split into 1-item bands with a local-only sender gave wrong output at chunk 0). 11/11 sliding tests pass incl. new test_ring_joint_attention_gemma_sliding_ksplit_accuracy. Perf: 2048 -1.4%, 4096 -0.6%.
- Implication: sliding math is only ~25-30 us of the ~180 us op at 2k; halo ~45 us; the rest is per-op fixed cost. Q64 also only -1.3%.
- Stack (overlap + GEMMA4_IN0_WS + KSPLIT=3) PCC 256k @2048: overall 0.98145 (base 0.98267), min 0.9398 (base 0.9417), early-layer err ratio 1.01.
Related: [[gemma4-sdpa-qchunk-occupancy]], [[ring-joint-kernel-config-buffer-cap]].
