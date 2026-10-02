---
name: gemma4-8192-pcc-floor-source
description: "Gemma4 8192-chunk PCC floor enters at global L5 attention; matmul fidelity, Q chunk, bf16 denominator fixes and bfp4 MLP all ruled out (2026-09-27)"
metadata:
  node_type: memory
  type: project
  originSessionId: 8f985f1d-292b-4c2b-ba24-7719ec3e62ae
  modified: 2026-09-27T21:06:14.062Z
---

Gemma4 256k PCC at chunk 8192 (min 0.911, gate 0.91) vs 4096 (0.941): per-layer error is identical through L5 and
x1.65-2.2 from L6, so the extra error enters in the first global layer's attention. Ruled out 2026-09-27 (all
same-build per-layer comparisons, logs in /data/kmabee/runs_0927):
- matmul fidelity: sliding / projections / global SDPA at HiFi4 change nothing; MLP HiFi2 x0.8 early only.
- Q chunk: q128 at 8192 == q96 (0.9113).
- bf16 softmax-denominator saturation: real at op level (per-row scale drifts past ~65k keys unsplit), but
  Gemma4's post_attention_layernorm normalizes each token, so per-row scale errors barely reach the model
  (a 1.029 output rescale moved error x1.00). An SFPU two-sum compensation fix (branch kmabee/wip-sdpa-sum-comp)
  made the model WORSE (0.873), like the segmented accumulator before it. Suspect a model-path bug in both.
- bfp4 MLP weights: -3.7% at 4096 but error x8 (PCC 0.856).
Open: the K split (4096/2048 split 3 ways, 8192 unsplit) is the remaining difference.

**Why:** these were the candidate routes to 8192 accuracy headroom (to afford attention-projection LoFi, ~-7%
floor); don't re-run them without a new reason.
**How to apply:** see PROGRESS_0927.md "Session 3" in ~/debug-docs/gemma4_prefill_chunk_floor-noissue. Related:
[[gemma4-kv-pcc-early-layer-method]], [[gemma4-pcc-test-gate-and-shm]].
