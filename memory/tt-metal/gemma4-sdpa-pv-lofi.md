---
name: gemma4-sdpa-pv-lofi
description: "Global ring SDPA QK^T and softmax@V at LoFi are each accuracy-neutral, -20% at 256k together; LoFi no-MOP replay bakes in matmul shape (reinit hang); gate is base-limited at >=8192"
metadata:
  node_type: memory
  type: project
  originSessionId: 8f985f1d-292b-4c2b-ba24-7719ec3e62ae
  modified: 2026-09-27T11:56:44.056Z
---

Measured 2026-09-27 (traced 256k demo, 8x4 BH Galaxy), global layers only, rest of SDPA at HiFi2:
- PV at LoFi: 8192 256k 9.7 -> 8.7 s. QK^T at LoFi alone: also 8.7 s. BOTH: 7.8 s (-19.6%), 106k 2.59 -> 2.28 s.
- PCC error ratio vs base, every layer: PV 1.00-1.03, QK 1.00-1.03 (2048 min 0.9419, 8192 min 0.9123), both
  1.00-1.05 (8192 min 0.9097 vs base 0.9110). The old "all-LoFi fails at 0.815" came from the sliding layers /
  SALAD eltwise, not from global QK/PV.
- LoFi on sliding PV: no speed gain. Keep sliding at HiFi2.
- Gate: 8192 base has 0.001 margin (0.9110); 16384 base fails (0.9070). Only 2048/4096 (K split) have margin.
- Attention projections at LoFi (QKV -4.6%, O -2.3% first chunk) cost x1.06-1.3 error.

TRAP (hang): the no-MOP matmul replay image at LoFi ends with an MVMUL that clears SrcA or SrcB chosen by
`reuse_a = ct_dim >= rt_dim` at INIT time. `mm_no_mop_reinit_short` only restores addrmods, so reinit'ing a LoFi
replay for a differently shaped matmul (PV after a QK^T init) hangs the device. At HiFi2 the tail is
shape-independent, which is why the stock QK->PV reinit is safe. A LoFi PV must full-init every time.

**How to apply:** judge fidelity changes by the per-layer error ratio ([[gemma4-kv-pcc-early-layer-method]]);
the demo is power-capped so FPU-pass cuts pay in full ([[bh-galaxy-prefill-power-throttled]]).
Implementation: `SDPAProgramConfig.qk_lofi` / `pv_lofi` (branches kmabee/gemma4-prefill-0928-stack,
kmabee/wip-sdpa-qk-lofi).
