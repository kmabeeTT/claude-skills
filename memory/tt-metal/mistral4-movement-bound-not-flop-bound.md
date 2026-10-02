---
name: mistral4-movement-bound-not-flop-bound
description: Mistral4 prefill is movement/launch-bound, not FLOP-bound — SDPA LoFi and capacity-factor changes both do nothing, and identical matmuls vary 6.4x in efficiency by stage shape
metadata:
  type: project
---

Measured 2026-09-04 on `bh-glx-120-b03u02`, PP=4 Mistral Small 4 prefill. Three independent
attempts to buy speed with cheaper math or smaller buffers all came back **<1%, inside noise**:

| knob | change | result |
|---|---|---|
| `MISTRAL4_SDPA_MATH_FIDELITY` | HiFi2 -> LoFi on RingJointSDPA | 191.0 -> 192.7 ms @ISL 102,400 |
| `PREFILL_CAPACITY_FACTOR` | 8 -> 5 (the reference worst case for top-k 4) | 105.6 -> 105.7 ms @5,120 |
| `PREFILL_OVERLAP_SHARED_EXPERT` | on -> off | 105.6 -> 105.4 ms @5,120 |

Halving SDPA's arithmetic changing nothing means **SDPA is not FLOP-bound** — and it is the only op
whose cost grows with context (5.2x over 9 chunks; matmul is 1.00x flat). Corroborated by the same
11 MLA projections running at **6.4x different efficiency per unit of work** (`tokens/chip x 1/TP`)
across three stage shapes: 8.24 us/unit at SP8xTP4, 3.26 at SP8xTP1, 1.28 at SP4xTP2.

**Why:** it retires a whole category of optimisation. Anything that buys cheaper math — math
fidelity, and most compute-side precision work — is aimed at a resource that is not the constraint.
It also reframes the MoE routing cost (dispatch+combine = 3.1x the routed-expert FFN it feeds, 26%
of the layer): that is not slack to tune away, it is the model paying to move tokens.

**How to apply:** on this model, go after **fewer/larger ops** (the 11 projections fused), **less
movement** (SDPA's bf16 query against bfp8 K/V; dispatch/combine volume), and **overlap** — not
fidelity or buffer sizing. Before believing any knob's "no effect", confirm it reached the ranks:
see [[pp4-perf-harness-traps]] and [[mistral4-precision-census]].
