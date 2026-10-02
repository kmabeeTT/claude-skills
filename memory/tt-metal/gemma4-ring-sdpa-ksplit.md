---
name: gemma4-ring-sdpa-ksplit
description: "K split for chunked global ring SDPA (Gemma4) -- 256k at chunk 2048 20.1->14.3 s, better PCC; design, limits (8192 doesn't fit L1), where it lives"
metadata:
  node_type: memory
  type: project
  originSessionId: ecf73b36-1b7e-42d3-8c9f-6038bb920bb7
  modified: 2026-09-25T23:07:18.063Z
---

Built 2026-09-25 on branch kmabee/gemma4-prefill-work-0925 (tt-metal-2), now SDPAProgramConfig.max_k_splits (Gemma default 3 via GEMMA4_GLOBAL_KSPLIT; global q = slab/4 for slabs <= 512).

- Why: at chunk 2048 the global layer has 8 heads x 8 q32 chunks = 64 one-tile units on ~110 cores, each over the full K; per-history-token cost is sublinear in Q height (1/2/3 tiles = 0.58/0.79/1.26 us), so the slope was occupancy bound.
- Design: grid rows split into bands (rows_per_split = ceil(units / grid.x)); band b attends to [b*n/s, (b+1)*n/s) of every ring iteration's valid K chunks (n derived on device, trace safe); the last band (reducer) owns the diagonal chunk, pulls senders' (max, sum, out) L1 to L1 (same CB offsets on every core, one ready-semaphore byte per sender), merges with SALAD primitives, normalizes. Row-wide GQA multicast keeps working because a band is whole rows; idle cores in a band row must use the band's range.
- Measured (256k traced, with configs): 2048 20.1 -> 14.3 s, 4096 13.1 -> 10.9 s. PCC at 2048 improved (overall 0.9744 -> 0.9830, min head 0.9129 -> 0.9428), since each partial accumulates bf16 over fewer chunks.
- 8192: q256 needs 2.27 MB of CBs, q192 1.87 MB even unsplit (limit 1.57 MB); q128 gives 64 units = one band. Dead without shrinking the ring SDPA L1 footprint. Receiving the reducer's input into cb_q_in RACES with the Q push; guarding it cost 0.7 s at 256k (kills the pull/compute overlap).
- Final stack (with SP residual, 2026-09-26): 256k 2048 13.6 s, 4096 10.4 s, 8192 9.8 s; PCC min head 0.943 at 2048/4096. Handoff: ~/debug-docs/gemma4_prefill_chunk_floor-noissue/HANDOFF_0926_NEXT.md.

Status 2026-09-27: restructured into Ops PR `kmabee/ring_sdpa_ksplit_ops` (K split + causal skip, head-op batching, packed latent V) and Model PR `kmabee/gemma4_prefill_small_chunks` (+ model, + ring_mla on the packed cache); not pushed yet. Final main->both: 2048 256k 20.1->13.2 s, 4096 13.1->10.2 s, 8192 10.4->9.7 s (8192 still short of -10%). Next-session seed: ~/debug-docs/gemma4_prefill_chunk_floor-noissue/HANDOFF_0927_NEXT.md.

See [[ring-joint-kernel-config-buffer-cap]], [[gemma4-ring-sdpa-qchunk-by-slab]].
