---
name: gemma4-pp4-scoping
description: Gemma4 PP=4 x [8,1] measured 1.17x at 256k; the compute model was right, the pipeline overhead was not
metadata:
  type: project
---

Implemented 2026-09-07 on bh-glx-120-b03u02 (branch `gemma4-pp4` off `gemma4-prefill-pr`), then
**ported 2026-09-08 to `kmabee/svuckovic/gemma4-prefill-freeze-sep-07`** (off
`svuckovic/gemma4-prefill-freeze-sep-07` @ 71616da612c, 186 commits / 513 C++ files diverged) and
fully re-verified: baseline 13.6 s / 19,253, PP=4 warm 11.79 s / 22,236 = **1.15x**, all split and
concat checks still bit-exact with IDENTICAL ref_std, so the port moved code not behaviour. The
freeze branch's `prefill_weights_only` (KV-only mode) is the same idea as `is_last_rank` at the
model tail; they collapse into `Gemma4Model._build_head`, and since the runtime passes
prefill_weights_only=True for every rank, NO rank builds a head there -- so `--last` no longer
exercises a final norm. Docs: `models/demos/gemma4/docs/GEMMA4_PP4_{PLAN,RESULTS}.md` in
/data/kmabee/tt-metal-2. Commits d111b70f6a9, 5dc9f467e1b, 0ff66e527c4.

**Result:** 256k chunk8192 in **11.64 s / 22,517 tok/s** vs the 8x4 baseline's 13.6 s / 19,287
(re-run same session) = **1.17x**; 23,912 tok/s (1.24x) at 4 in-flight requests. Stage compute
alone is 9.78 s = 1.39x of a predicted 1.44x ceiling, and TP=1 compute is AT THEORY (predicted 295
ms/chunk, measured 277-303) -- nothing left to recover there. The 16% shortfall is pipeline bubble,
now attributed by a phase breakdown in run_request_loop (under PREFILL_TIMING_DIR): 0.67 s fill +
**0.56 s inbound socket sync (~18 ms/chunk, an untraced device op)** + 0.64 s residual imbalance.
The fabric-link lease cycle, the prime suspect, measures **0.1 ms** -- not the problem. And
_d2d_send's own timer says 0.31 ms only because it ENQUEUES; the bytes move while the host runs on.

Five things worth not rediscovering:

1. **TP=1 breaks `nlp_concat_heads`, not the matmuls.** Its src0 CB is `2 x heads x head_dim/32`
   tiles with NO sequence dependence, so a global layer is 0.5 MB at TP=4 and 2.0 MB at TP=1
   against BH's 1.5 MB L1. Fixed by head-grouping in gemma4's `concat_heads`; TP>=2 computes one
   group and is byte-identical (baseline reproduced to the digit).
2. **`Gemma4DecoderLayer` DEALLOCATES its input** (layer.py, the residual, freed after the add).
   A later PP rank must CLONE the activation it receives or it frees the persistent trace buffer.
   Symptom is a segfault in the NEXT forward's first rms_norm, and only on a stage whose first
   layer is global -- a stage starting on a sliding layer read the freed buffer and "passed".
3. **Gemma4 wants plain FABRIC_2D, not Mistral's torus_y.** `ring_joint_scaled_dot_product_
   attention` passes `topology=Topology.Linear` unconditionally and the 8x4 baseline opens
   FABRIC_2D. Match the fabric mode to the descriptor's dim_types AND to what the collectives
   actually ask for. See [[tt-galaxy-fabric-run-hygiene]].
4. **Stage balance by global-layer count is real, quantified and CLOSED.** Per-layer cost summed
   over 32 chunks at 256k: sliding 0.301 s, global 2.234 s (7.4x). Fitted on 15/15/15/15, predicts
   17/13/17/13 to under 1%. `tests/perf/pp4/optimal_layer_split.py` enumerates all 32,509
   contiguous 4-way splits: 17/13/17/13 is the UNIQUE minimum. Residual 3.9% is structural (10
   globals don't divide by 4). Contrast [[mistral4-per-layer-moe-variance]], where balance was a
   non-issue. Don't re-spend time here.
5. **"Chunk 16384 is worse" was a COLD-JIT ARTIFACT.** First read 18.19 s with rank 0 at +5.5 s;
   rank 0's FIRST chunk alone was 5,904 ms and every later chunk matched its peer to 1%. Warm it
   does the same stage compute as 8192 and loses only 1.0 s, on fill. A cold cell is not a slow
   measurement, it is a wrong one -- re-run any new shape warm before believing it.
6. **Ruled out by measurement, don't retry:** the fabric-link lease (0.1 ms), PP=2 x [8,2]
   (modelled ~12.2 s stage period vs 9.71), and the layer split. What's left is the socket sync and
   the global layers themselves (7.4x a sliding layer, 10 of 60 layers, ~60% of a stage's cost).

**Correctness (audited 2026-09-07):** Gemma4 has ~15 PCC test files but NONE touch the
context-parallel prefill path -- they all run decode / non-CP paged prefill on small meshes. The
surviving CP test asserts finiteness + non-degeneracy only; `cpu_prefill_reference.py` was deleted
in e56882c307b. The common runner's multi-rank golden-KV harness
(`common/prefill/runners/ci/run_multirank_pcc.sh`) is the right check and IS multi-rank aware, but
Gemma4 is not wired into it: no golden trace (`prefill_trace_default = ""`), and the producer's
`_read_slot_kv_and_check_pcc` falls through to the MLA reader, which would misread Gemma4's
packed-global CP-sharded ring cache. **So there was no numerical gate on this path at ANY rank
count, before or after PP.**

What PP itself is now proven not to break, via `tests/perf/pp4/verify_pp_split.py` (one stage vs
two on different galaxy columns, host relay using the D2D socket's own mapper) -- all **bit-exact**:
[0,17) vs [0,8)+[8,17); [0,30) vs [0,17)+[17,30) (the real boundary, stage B starting on global
layer 17); and the same with `--last` on both sides, exercising the final-norm gate. Plus
`verify_concat_heads.py`: the TP=1 head-grouped concat matches `permute(0,2,1,3).reshape` exactly at
all 8 head shapes. NOT established: that Gemma4 CP prefill is right in the first place (inherited),
the D2D transport itself (host relay), TP=1-vs-TP=4 end to end, and migration.

Related: [[mistral4-pp4-real-d2d-results]], [[pp4-perf-harness-traps]],
[[pp4-stage-shape-sp-beats-tp]], [[gemma4-prefill-box-setup]], [[tt-cache-mesh-mismatch-deadlock]].
