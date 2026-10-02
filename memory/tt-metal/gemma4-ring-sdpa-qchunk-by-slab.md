---
name: gemma4-ring-sdpa-qchunk-by-slab
description: Gemma4 ring SDPA global-layer q_chunk must scale with the per-rank Q slab; one fixed value (#57702's 96) costs up to +7 s per 256k prefill at small chunks
metadata:
  type: project
---

Measured 2026-09-24/25 on BH Galaxy 8x4 (CP8), 256k prefill, #57454+packer on main 41a38c6: the best **global**-layer ring SDPA q_chunk (k 256) grows with the per-rank Q slab (chunk / CP): chunk 2048 -> q 32 (21.7 s vs 24.0 at q64, 28.7 at q96, 33.2 at q128); chunk 4096 -> q 64 (14.1 s vs 17.4 at q32, 16.2 at q96); chunk 8192 -> q 96 (11.1 s vs 12.8 at q64). Sliding-layer q (64 vs 128) moves results <1%. The effect is almost entirely in the context-depth slope, not the first chunk — so a single-chunk or first-chunk benchmark will not see it.

**Why:** #57702 tuned q/k at 256k ISL (effectively chunk 8192) and applied it to every chunk size; it regressed chunk 2048/4096 end-to-end while looking neutral on TTFT.

**How to apply:** any change to Gemma4 SDPA chunk sizes (or the halo/prefill chunk) needs a full 256k run at every chunk size, compared on total time and per-chunk slope. The selection lives in `ring_sdpa_chunk_sizes` (ring_prefill.py, #57453). Sweep logs: `/data/kmabee/gemma4_256k_logs_0924/q_chunk_sweep/`. Mechanism: [[gemma4-sdpa-qchunk-occupancy]]. Constraint: keep units <= SDPA cores or segmented accumulation silently turns off, see [[ring-sdpa-seg-accum-one-q-per-core]]. Related: [[gemma4-ring-sdpa-ksplit]].
