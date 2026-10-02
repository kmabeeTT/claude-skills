---
name: pp4-stage-shape-sp-beats-tp
description: "Inside a Mistral4 PP stage, spend chips on sequence parallelism: [4,2] ties [8,1] at one chunk and loses 45% at ISL 102,400"
metadata:
  type: project
---

Measured 2026-09-04, PP=4 Mistral Small 4, same 4 ranks and 8 chips per stage, only the split moved.

| ISL | PP `[8,1]` SP8xTP1 | PP `[4,2]` SP4xTP2 |
|---:|---:|---:|
| 5,120 | 48,481 tok/s | 49,508 (**+2%**) |
| 25,600 | 44,121 | 34,264 (-22%) |
| 102,400 | 26,808 | 14,629 (**-45%**) |

At 102,400 `[4,2]` is also 35% slower than the 32-chip single rank. Per-layer capture says why:

- **SDPA 2.788 -> 8.159 ms (2.93x worse)**, KV ramp steepening 5.46x -> 7.27x. Halving SP doubles
  per-chip attention input; ring attention over 4 chips also overlaps worse than over 8.
- **Routed-expert FFN 1.875 -> 1.878 ms — UNCHANGED.** Experts spread over the whole stage, so
  128/8 = 16 per chip either way. TP buys nothing here; the 4x seen against the single rank is a
  *chip-count* effect (32 vs 8 per stage), not a TP effect.
- TP=2 does buy 2.5x on projections and 1.4x on routing, but both are **flat in context**, and it
  hands back 1.25 ms/layer of tensor-parallel collectives that TP=1 does not pay at all.

Related: collectives are 21% of the layer at TP=4 and **0.2% at TP=1** — PP=4 `[8,1]` beating the
single rank is partly that it *deletes* a fifth of every layer, not just pipelining.

**Why:** halving a set of constants cannot pay for near-tripling the one term that grows, so the
crossover is structural, not tunable.

**How to apply:** within a stage, maximise SP. Two traps when trying a new shape: the control plane
rejects a Z-chain over row-major quadrants (`q01`->`q10` is diagonal — snake to `q00,q01,q11,q10`)
with a message naming the unplaced meshes and never the impossible pair; and check for an existing
`{sp}x{tp}` weight cache before assuming a 65 GB rebuild (`cp -al` across the `Ndev` namespace).
See [[mistral4-movement-bound-not-flop-bound]], [[pp4-perf-harness-traps]].
