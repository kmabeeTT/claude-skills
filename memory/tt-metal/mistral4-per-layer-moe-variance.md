---
name: mistral4-per-layer-moe-variance
description: Mistral4's "stage-1 PP outlier" is really LAYER 1; per-layer MoE cost varies +54% across consecutive layers while MLA is flat, and PP stage balance is a non-issue
metadata:
  type: project
---

Measured 2026-09-04 from a full-model PP=4 capture (36 layers, 9/stage) on `bh-glx-110-a04u02`.

**Every 1-layer-per-stage capture confounds stage index with layer index**: with N layers on N ranks
the even split puts layer *r* on stage *r*, so "stage 1 is slow" and "layer 1 is slow" are the SAME
measurement. At 9 layers/stage, stage 1 holds layers 9..17 and layer 1 moves to stage 0 — and the
outlier moves with the **layer**.

Per-layer cost in stage 0 (keyed by `forward_layer_N` signposts, mean over 8 chips x 9 chunks):

| layer | 0 | **1** | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| total ms | 11.03 | **13.54** | 10.46 | 11.93 | 10.63 | 11.79 | 12.92 | 13.47 | 11.76 |
| MoE ms | 6.28 | **8.77** | 5.70 | 7.17 | 5.87 | 7.03 | 8.16 | 8.71 | 7.00 |
| MLA ms | 2.96 | 2.96 | 2.96 | 2.96 | 2.96 | 2.96 | 2.96 | 2.96 | 2.96 |

- **PP stage balance is CLOSED.** Per-layer stage means 11.96 / 12.97 / — / 13.36 ms = **11.7%**
  spread, not the 40% a 1-layer capture shows (that 40% was stage 3's un-amortised norm + LM head).
  Rebalancing layers across stages buys ~5% at most.
- **Per-layer MoE variance is the target**: 5.70 -> 8.77 ms (**+54%**) across nine consecutive
  layers, while MLA is flat to three digits. That is per-layer expert-routing imbalance.
- SDPA's KV ramp reproduces at full scale: **5.48x** over 9 chunks vs 5.46x from the 1-layer capture.

**Why:** it kills a tempting-but-worthless optimisation (stage rebalancing) and replaces it with a
real one, and it explains why a "stage" anomaly reproduced across machines — it was never the stage.

**How to apply:** never attribute a per-stage anomaly to pipeline position from a 1-layer-per-stage
capture; either use 9 layers/stage, or set `PREFILL_PP_LAYER_COUNTS` (e.g. NUM_LAYERS=5,
counts 2,1,1,1) to put a different single layer on the stage. See
[[mistral4-movement-bound-not-flop-bound]], [[pp4-stage-shape-sp-beats-tp]], [[pp4-perf-harness-traps]].
