---
name: gemma4-sdpa-qchunk-occupancy
description: "Gemma4 global RingJointSDPA prefill is MAC-throughput-bound on QK^T/PV (fidelity LoFi 0.79x, HiFi4 1.76x); bytes, softmax exp and k_chunk all ruled out; q_chunk optimum moves 32/64/128 for GLOBAL layers, but on SLIDING layers it is not a floor lever at all and q=32 is illegal"
metadata: 
  node_type: memory
  type: project
  originSessionId: caf0f877-ab74-4d6c-afd4-5752b6f99c70
  modified: 2026-09-16T21:20:45.495Z
---

**Gemma4 CP prefill: the global layers' `RingJointSDPA` SCALING with chunk size is Q-chunk
work-unit occupancy, not fabric.** Measured 2026-09-16, BH galaxy 8x4 (CP8/TP4), branch
`kmabee/gemma4-swa-multihop-halo`. (The op's internal composition is a separate, still-open
question — see the retraction below.)

`ring_joint_sdpa_program_factory.cpp`: `all_heads_num_q_chunks = B*NH*num_q_chunks` and
`max_q_per_core = div_up(all_heads_num_q_chunks, num_cores)`. `NH` = 8 local q heads (32/TP4),
`num_q_chunks = ceil((chunk/CP)/q_chunk_size)`, SDPA grid = `(compute_grid.x-1) x .y` ~= **110
cores** (avail 120; the op reports 113-114 incl. fused CCL workers). **Cores with no Q chunks are
NOT skipped** — the factory says so explicitly: they run padded handshake iterations
(`loop_q_count = *_max_q_per_core`). So runtime is `max_q_per_core` iterations for every core.

    cost per chunk-index  ~  depth(C) * C,   depth = ceil(NH*(C/CP)/q_chunk / 110)
    whole-prompt prefix   ~  depth(C) * q_chunk / C

At **fixed `q_chunk`** this has **zero free parameters** and predicts all five measured prefix terms
within 5% and every adjacent slope ratio within 3% — including the non-power-law sequence
2.05x / 4.00x / 3.09x / 3.40x, which is just `depth*C`. Occupancy: 29% at chunk 2048 (32 units),
58% at 4096 and 8192, 78% at 16384, 93% at 32768.

**`q_chunk_size` is hardcoded to 64 in `ring_prefill_program_config` and the optimum MOVES with
chunk size.** Measured, one global layer, depth curves:

| chunk | q=64 slope | alternative | ratio |
|---|---|---|---|
| 2048 | 0.1460 | q=32 -> 0.1233 | **0.845x** (q=32 better) |
| 4096 | (prior sweep) | q=32 and q=128 both worse | 64 is best |
| 8192 | 1.2272 | q=128 -> **1.1239** | **0.916x** (q=128 better), and `a` 5.87 -> 5.34 |

At the deployed 8192, q=128 is worth **-4.8% on a 256k prefill and -1.9% TTFT, free**. Real but
**modest — 8-16%, NOT the 34-50% a pure-occupancy reading predicts**, so the `div_up` depth
penalty is real yet costs far less than a full extra unit of work: a core holding 2 units
overlaps most of the second. The in-tree comment claiming "q=64 is a true optimum, worse in both
directions" was measured **at chunk 4096** — correct there, does not generalise.

**RETRACTED (same session): a "69% movement / 31% math" split.** Reading the chunk-2048 q64->32
ablation through `cost = depth*(q*m' + r')` gives `r' = 142*m'`; the chunk-8192 q64->128 ablation
gives `r' = 13*m'`. An order of magnitude apart, so no single two-term model fits both and the
split was unfounded. The 2048 ablation changes rows/core AND q_chunk together, so it cannot
separate per-unit overhead from "per-row efficiency depends on q_chunk" (at `Sq_chunk_t==1` the
per-row work is simply less efficient). **The 8192 ablation is the better design** — it holds
rows/core fixed at 128 and changes only units/core 2->1 — and it gives **per-unit overhead ~17%**,
per-row work ~83%.

**The op is NOT bandwidth-bound — measured 2026-09-17.** Changing only the GLOBAL KV cache dtype
bfp8_b -> bfp4_b (**-47% bytes/tile**, 1088 -> 576 B) moved the whole-model prefix slope from
11.83 to **11.81 (0.998x)**. bf16 could not run: CBs overflow L1 (1 635 456 B vs 1 572 864 B max)
-- which is the control proving the dtype reaches the op's own L1 buffers, so bfp4 really did
halve the bytes through DRAM, the fabric gather, L1 and the per-work-unit streaming.
=> **the prefix cost scales with element COUNT, not byte count.** Kills "fabric-bound", kills the
retracted "69% K/V re-streaming", and kills "deduplicate the K/V streaming" as a lever.
Remaining candidate: per-element compute (unpack rate, MAC issue, softmax) or per-tile overhead
-- which needs kernel `DeviceZone` zones to resolve.

**Apply the override to the GLOBAL cache only** (`row_dim == GLOBAL_PACKED_DIM`): the sliding path
hard-requires BFP8_B K/V (`ring_joint_sdpa_device_operation.cpp:589`), but that TT_FATAL block is
gated on `if (args.has_sliding_window())` at line 553, so global layers are unconstrained -- and
the prefix term is 100% global layers anyway.

**End-to-end verified (whole model, ctx_32k):** q=128 @ chunk 8192 gives **-4.6% at 256k**
(slope 11.87 -> 10.73) and q=32 @ chunk 2048 gives **-8.0%** (slope 1.4543 -> 1.1782), with
**TTFT unchanged** in both. Single-layer projections were -4.8%/-6.9%, so projecting single-layer
deltas to whole-model is good to ~1-4%.

*Confound ruled out:* `Sq_chunk_t==1` does NOT trigger `kt_inplace_v` here — that needs
`v_shares_k_buffer = !input_v.has_value()`, and Gemma4 passes `cache_v` explicitly.

**How to apply:** when tuning Gemma4 prefill, set `q_chunk_size` per chunk size for GLOBAL
layers — the `q in {64,128}` / `k == 128` allowlist lives inside
`if (args.has_sliding_window())`, so global layers are unrestricted. Sliding layers cannot use
this and do not need to: their slope is exactly zero, measured -0.0001 ms/index over a full 256k
prefill. Expect single-digit-to-mid-teens percent, not a factor.

**Method lesson:** an ablation that changes two things at once (rows/core AND q_chunk) cannot be
read through a two-term model — it will produce a confident, wrong split. Prefer the variant that
holds one quantity fixed, and always test the model on a SECOND ablation before believing it.

Full record, scripts and per-op tables in `~/debug-docs/gemma4_chunk_size_anatomy-noissue/`.
See [[gemma4-prefill-chunk-size-win]], [[gemma4-prefill-rmsnorm-row-parallel-floor]],
[[tracy-device-trace-profiler-trap]]. The production per-chunk-size q choice measured later (q 32/64/96 at chunk 2k/4k/8k, 2026-09-24) is in [[gemma4-ring-sdpa-qchunk-by-slab]].

**The occupancy model passed a PRE-REGISTERED discriminating test (2026-09-17).** Profiled one
global + one local layer at a **matched prior context of 49152 tokens** (sz8192 idx 6, sz4096
idx 12, sz2048 idx 24 — hold the CONTEXT fixed, not the chunk index, or the comparison is
confounded by ring depth). At matched context the prefix work is proportional to the chunk, so
chunk 2048 does exactly **0.25x** the work of 8192. Predictions written down first: **0.50x**
if cost tracks work-unit depth, **0.25x** if the op is efficiency-neutral. **Measured 0.443x**
=> 2048 is **1.77x less efficient per unit of prefix work**.

**CORRECTED 2026-09-18 by an independent blind re-run (single sha 3bd2c2bbe29, matched prior
context 57344 = idx 28/14/7, all six captures on one build).** Two fixes to the above:

1. **0.443x is the diluted number.** It divides the op's TOTAL device time at depth
   (3661.9/8266.0). The quantity that actually explains level 0's `slope` is the
   **depth-0-subtracted growth**, which gives **0.4995x** — dead on the 0.500 prediction.
   Including the depth-0 term pulls the ratio down because the global SDPA's depth-0 cost
   scales at **0.144x** (better than the 0.25x ideal: with no history it computes only the
   causal diagonal block, ~quadratic in C). Use growth, not total; growth is also what
   reconciles against level-0 slope to -0.1/-1.1/-3.0% at 2048/4096/8192.
2. **2048-vs-4096 is the SHARPEST discriminator, not a blind pair.** Both are depth-1, so
   occupancy predicts they cost the **SAME (1.000)** while efficiency-neutral predicts 0.500.
   Measured **0.9997x** on growth (0.956x on the diluted total). The genuinely blind pair is
   **4096-vs-8192**, where both models predict 0.500. The old note had this backwards and
   dismissed its own strongest evidence.

**The prefix term is NOT the bigger half of the chunk-2048 problem at the deployed context.**
Level 0 at ISL 262144: 2048 totals 28.56s vs 8192's 13.73s = 2.08x, and that deficit is
**61% per-chunk floor / 39% prefix**. Prefix excess only overtakes floor excess above
**ISL ~= 416k tokens**. The 2048/8192 ratio is nearly FLAT in context length (2.18x at 32k
-> 2.04x at 512k), so "throughput collapses at long context" is the wrong frame: 2048 is
~2.1x behind everywhere, and its TTFT win (131 vs 242 ms) simply never compounds. Whole-model
occupancy check with no profiler: 29.1% vs 58.2% useful predicts prefix-term ratios 2.00x/1.00x
for 2048/4096; level 0 measured **1.97x/1.01x**.

**Per-op, exactly ONE op in the model grows with context:** `RingJointSDPADeviceOperation` is
**99.8-100.0%** of a global layer's growth from prior context 0 -> 49152. The **sliding layer is
context-invariant to within 0.8%** (+0.2 / +0.8 / -0.1% at chunk 2048/4096/8192) and its SDPA
sits at 405/454/461 us regardless of depth. Taking that one op x10 global layers reconstructs
the whole-model prefix slope to **1.05-1.15x**. This replaces the curve-fit inference with a
direct measurement.

**Trap: `Cores` cannot show the occupancy loss.** The global SDPA reports **114 cores at every
chunk size**, including 2048 where only 32 of ~110 cores hold a work unit — the rest run padded
handshake iterations rather than being dropped. Occupancy must be computed from the factory's
work-unit math. Also **`Total %` and `Op-to-Op Gap` are unusable** on these trace captures: each
replay's first op carries a host gap measured from before the signpost (1.12 s in one case),
which crushes every real op to 0.0%. Use `Device Time`.

Commands and tables: in-tree `tech_reports/Gemma4PrefillChunkSize/PER_OP_TABLES.md`. The demo is
`gemma4_d_p`, the sliding signpost is named **`local`** (not `sliding`), chunk index is a test
parameter (not `GEMMA4_PERF_CHUNK_IDX`), and `layer_type=both` does both layers in one session.

**SLIDING-layer `q_chunk` measured 2026-09-18 (Exp 3, session A) — it is NOT a floor lever.**
Everything above concerns the GLOBAL layers and the prefix slope. The sliding layers own 17.8 ms
of the per-chunk FLOOR, and the standing hypothesis was that `q_chunk=64` occupancy caused it.
**Falsified.** Whole-model `a` at ctx 32k, on top of the MLP matmul patch, q=64 -> q=128:

| chunk | q=64 `a` | q=128 `a` | |
|---|---|---|---|
| 2048 | 119.0 | 120.2 | **+1.0% — a REGRESSION** |
| 4096 | 145.6 | 143.1 | -1.7% |
| 8192 | 225.7 | 219.8 | -2.6% |

Monotonic in chunk width, crossing zero just above 2048 — the wrong shape for an occupancy
argument, which would help the narrowest chunk most. **`q=32` is ILLEGAL on the sliding path**:
`ring_joint_sdpa_device_operation.cpp:603` TT_FATALs with "Chunked sliding attention supports Q
chunks 64/128 and K chunk 128" (the allowlist is inside `if (args.has_sliding_window())`, which
is exactly why the global layers above *could* sweep q=32). So the planned {32,64,128} sweep had
only two legal points.

**How to apply:** do not spend time on sliding `q_chunk` — at the ISL-1.5k target width (chunk
2048) q=64 is already optimal, and the remaining suspect for the sliding floor is the constant
1024-token halo. Gate any override on `sliding_window_size` so the global layers keep their own
optimum. Also note run-to-run drift on this box is **~0.1%** (two cross-session reproductions:
145.6 vs 145.5, 119.0 vs 119.1), which is what makes a 1% effect readable at all — but measure a
same-session control before believing one. Session A record:
`~/debug-docs/gemma4_prefill_chunk_floor-noissue/RESULTS_LOG.md` Exp 3.
