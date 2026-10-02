---
name: gemma4-prefill-rmsnorm-row-parallel-floor
description: "ttnn.rms_norm parallelises over rows only, so Gemma4's four hidden-width norms are width-bound: ~26ms of every prefill chunk on 8 of 120 cores. FIXED 2026-09-18 by block sharding (4.36x on the op, -16.6ms on a) -- and the single-tile-shard-height limit is NOT a ttnn constraint"
metadata: 
  node_type: memory
  type: project
  originSessionId: caf0f877-ab74-4d6c-afd4-5752b6f99c70
  modified: 2026-09-16T21:02:11.739Z
---

**`ttnn.rms_norm` parallelises over ROWS ONLY, so it is WIDTH-bound and barely shrinks when the
prefill chunk does.** Measured 2026-09-16, BH galaxy 8x4, per-op tracy, chunk index 0, both
captures on the same build.

The four hidden-width norms per layer are `(rows x 5376)` = 168 tiles wide, at HiFi4 +
`fp32_dest_acc_en`. The per-device slab is `chunk/CP` rows:

| chunk | rows | row-tiles | CORE COUNT | us per norm call |
|---|---|---|---|---|
| 2048 | 256 | 8 | **8** | **110.3** |
| 8192 | 1024 | 32 | **32** | **134.2** |

One core per 32 rows does the whole 168-tile-wide reduction, so **4x the rows on 4x the cores
costs only 1.22x the time — 0.30x per token.** Width-bound, not chunk-bound. The 4 calls within
a capture agree to +-2%.

**4 norms x 60 layers = 26.5 ms of every chunk at 2048** (32.2 ms at 8192), of which **18.4 ms
does not scale** — 20% of chunk 2048's entire 131 ms TTFT, on 8 of 120 cores. The per-head q/k/v
norms are `(rows x 256)` and are cheap (6-27 us).

**CAUTION, and it bit this claim:** an earlier same-session draft put the ratio at **0.98,
"exactly chunk-invariant"**, from comparing against a chunk-8192 capture on an OLDER BUILD where
the identical norm (same shape, same 32 cores) took **99.3 us instead of 134.2**. Never compare
per-op timings across builds -- a same-shape/same-core-count op is not a safe cross-build anchor.

**Fix: measured ~2x, NOT the ~8x a width argument suggests.** Off-model microbenchmark at the
exact shapes: default row-parallel 170 us @(256x5376); best sharded **0.076 ms (2.25x)** at
6x8=48 cores block 1x28t; at (1024x5376) best is 8x8=64 cores block 4x21t, 1.83x. **More cores is
NOT better** -- 12x8=96 cores (0.177 ms) LOSES to 6x8=48. `subblock_w <= 3` in fp32 mode when
`dst_full_sync_en` is false, or it TT_FATALs. Treat ~2x as the expectation => saves ~12.6 ms/chunk.
And it needs a **block-sharded input activation**, so the surrounding ops must produce/consume
sharded tensors: moderate integration work, not a config flip.

**Precision is NOT the cost:** LoFi vs HiFi4+fp32 is only 19% (138 vs 170 us). Do not trade
accuracy for it.

**Matmul is downgraded as a lever:** a naive standalone `M=256,K=N=5376` bfp8 matmul takes 243 us
vs the in-model 193 us -- the model's config is already better than a default, so "~150 GB/s vs
peak implies easy headroom" was too optimistic.

`LayerNormShardedMultiCoreProgramConfig` (`compute_with_storage_grid_size`, `block_h`,
`block_w`, `subblock_w`) is in
`ttnn/cpp/ttnn/operations/normalization/layernorm/device/layernorm_types.hpp` and splits the
width across cores; it requires a block-sharded input activation. Precision-neutral, and it
helps every chunk size and every context length. Dropping HiFi4/fp32 would also help but is an
accuracy decision — `rms_norm.py` deliberately matches the reference's FP32 prefill norm, and
its comment notes the TILE-gamma "large-tensor RMSNorm path" was chosen to bound L1 for the
5376-wide case.

**The other half of the same floor: matmul weight-DRAM reads.** The 3 MLP matmuls go 193 us at
M=256 -> 285 us at M=1024 (4x the math, 1.48x the time). 127 MB of bfp8 weights per layer per
device (TP=4), and since the bytes are identical at both M the weight read cannot exceed the
smaller time: achieved rate **>= ~159 GB/s**, roughly a third of plausible peak, so there is real
headroom rather than physics. (An affine solve says ~190 GB/s, but a(C) is concave so do not
trust a C=0 intercept.)

**Per-op share of the floor** (excess over perfect token scaling, `t2048 - t8192/4`, x50 sliding
layers): **Matmul 26.7 ms (43%)**, **LayerNorm 15.7 ms (26%)**, RingJointSDPA 8.4 ms (14%), and
**TP collectives only 2.5 ms (4%)** — the collectives scale ~properly (3.3x for 4x tokens), so
"CCL is 30% of a layer" is true of a layer's total at depth but is NOT what makes small chunks
inefficient. Total 61.4 ms, against a ~70 ms whole-model measured excess (closes to 1.1% once
the 1.18x isolated-layer inflation is removed).

So the floor is essentially **weight movement + norms**, and it is why a 4x smaller chunk is only
1.85x cheaper.

**How to apply:** the per-chunk floor — not the halo, not attention — is what makes small prefill
chunks inefficient. Attack norms first (cheapest, precision-neutral). Full record in
`~/debug-docs/gemma4_chunk_size_anatomy-noissue/`. See [[gemma4-sdpa-qchunk-occupancy]],
[[gemma4-prefill-chunk-size-win]].

**Two different numbers both get called "the floor" — keep them apart (2026-09-17).** The
figure derived here is the **excess over perfect token scaling** at chunk 2048,
`t2048 - t8192/4`. For `cost = F + k*tokens` that excess is exactly **¾·F**, so the
*chunk-invariant* cost is `70.4/0.75 = ` **~94 ms**, not 70 ms. Confirmed two more ways: an
affine fit of the measured whole-model `a(C)` over 2048-8192 gives **94.2 ms**, and a per-op
`F + k*tokens` fit over three `tt-perf-report` captures gives 113 ms (105 ms after removing
staging ops only the isolated-layer harness pays). Rebasing the components by 1.335x puts
`rms_norm` at **24 ms**, which the per-op fit independently reproduces at **24.3 ms**, and
matmul at ~41 ms. The in-tree README/anatomy docs are now on the 94 ms basis.

**`tt-perf-report` confirms the mechanism visually** — `LayerNormDeviceOperation` shows
**8-32 cores** in the `Cores` column and costs only **0.77x** for a 4x smaller chunk, while
`AllGather`/`BinaryNg` sit at 0.27-0.29x against an ideal 0.25x. See in-tree
`tech_reports/Gemma4PrefillChunkSize/PER_OP_TABLES.md`.

**FIXED AND MEASURED IN-MODEL 2026-09-18 (Exp 4). Block-sharding is worth 4.36x on the op and
-16.6 ms on `a` at chunk 2048 — more than the ~2x this note predicted.** Env-gated patch in
`models/demos/gemma4_d_p/tt/rms_norm.py`: `to_memory_config` into a block-sharded L1 tensor ->
`ttnn.rms_norm(program_config=LayerNormShardedMultiCoreProgramConfig, memory_config=<same
spec>)` -> `sharded_to_interleaved`. Config `block_h=4` tiles, `grid_x=8` (`block_w=21`),
`subblock_w=3`; 16/32/64 cores at chunk 2048/4096/8192.

| chunk | `a` before | `a` after | per-op norm block |
|---|---|---|---|
| 2048 | 119.2 | **102.6** (-13.9%) | 443 -> 176 us incl. both reshards (2.52x); op alone 4.36x |
| 4096 | 145.6 | **133.5** (-8.3%) | |
| 8192 | 225.7 | **216.6** (-4.0%) | |

**TWO CORRECTIONS to what this note and the reference impls imply:**

1. **`SHARD_HEIGHT = TILE` ("rms_norm requires shard height to be a single tile") is NOT a ttnn
   constraint.** It is the three reference implementations' own decode-shaped usage, where
   `Mt = 1` and a single tile is the only option. `layernorm_device_operation.cpp` validates
   `block_h == div_up(Mt, num_cores_r)` and `block_w == div_up(Kt, num_cores_c)` — **both
   axes** — and `block_h = 4` tiles runs fine at the prefill shape. Reading that constant as an
   op limitation is what made this item look like the riskiest of the four.
2. **The defect is NOT the core count.** The fix uses **16 cores against the default's 8** (2x)
   and is **4.36x** faster; 48/64/96-core configs measured *slower*, standalone and consistently.
   So "8 of 120 cores" mis-frames it as under-parallelism — the row-parallel path is inefficient
   **per core** (it re-reads from DRAM), and chasing core count makes it worse.

**Limits:** no effect at chunk >= 16384 — at `Mt=64` the grid is capped at 8 rows (`block_h>=8`)
and 12 cols (`block_w>=14`), so per-core block >= 112 tiles, above the **~84-tile ceiling** where
`dataflow_buffer.cpp` throws; the patch falls back and was measured at exact parity. Both
reshards are still paid (74.5 us/layer against 341 us saved = 22% of the gross win given back);
removing them needs the next op to consume a sharded tensor.

**Method trap, now 5-for-5:** two standalone probes of the same configs on the same build,
differing only in iteration count, **disagreed by up to 2.5x and inverted the ranking** — one
predicted a *net loss* at chunk 4096 where the model measured a clear win. At 30-100 us/op the
standalone is host-dispatch-bound. **Use it for legality only** (it correctly gave the `gy <= 10`
grid limit, the 84-tile block ceiling, and that TILE-layout gamma is accepted); never for speed.

Session record: `~/debug-docs/gemma4_prefill_chunk_floor-noissue/` RESULTS_LOG.md Exp 4; the
applyable patch for all four diagnostic changes is in that archive under `logs/sessionB/`.
