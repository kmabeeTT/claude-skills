---
name: mistral4-precision-census
description: Mistral Small 4 on device is 97.5% BFLOAT4_B by parameter count — the MoE routed experts — not BF16 or BFP8
metadata: 
  node_type: memory
  type: project
  originSessionId: 197d2be2-411b-4a5f-b4e2-1feb588af108
  modified: 2026-09-03T17:27:21.060Z
---

Asked "is Mistral4 BF16 or BFP8", the answer is **neither, in the part that matters**. Census
computed 2026-09-03 from the dtype constants plus the live weight-cache filenames (`as_tensor`
encodes dtype in the name, e.g. `..._dtype_BFLOAT4_B_layout_TILE.tensorbin`), 119 B params total:

| group | params | dtype | share of params |
|---|---:|---|---:|
| MoE routed experts (128/layer x gate,up,down) | 115.96 B | **BFLOAT4_B** | **97.47%** |
| MLA projections (q_a,q_b,kv_a,wkv_b1,wkv_b2,o) | 1.01 B | BFLOAT8_B | 0.85% |
| shared expert (1/layer) | 0.91 B | BFLOAT8_B | 0.76% |
| embedding + LM head | 1.07 B | BFLOAT16 | 0.90% |
| router gate + RMSNorm weights | 0.02 B | BFLOAT16 | 0.02% |

Total on-device weights **64.7 GiB**, ~2.0 GiB/chip across 32 chips. Promoting routed experts to
BFP8 would cost **+54 GiB (1.83x)** — so expert precision, not activations, is the whole memory story.

Other facts that go with it:
- Source checkpoint is **fp8, per-tensor** (`quantization_config.weight_block_size = null`),
  dequantized on host at cache-build time — the fp8 never reaches the device.
- Activations: routed-expert **bfloat8_b**, shared-expert **bfloat16**, MLA matmul outputs
  **bfloat16** except `wkv_b2` which is **bfloat8_b**. Dense KV cache is **bfloat8_b**
  (`MlaKvCacheFormat.BFP8_TILE` via `allocate_mla_kvpe_cache`).
- Math fidelity: MLA + **RingJointSDPA** run `HiFi2, fp32_dest_acc_en=False`; routed experts
  `LoFi`. SDPA sees a **bf16 query** against **bfp8 K/V**.
- The dtype is set once, `DEFAULT_ROUTED_EXPERT_WEIGHTS_DTYPE = ttnn.bfloat4_b` in
  `tt/moe/tt_routed_expert.py`, and nothing in the runner path overrides it. A cache BUILT at one
  dtype and CHECKED at another silently loads the empty placeholder as weights and yields a
  meaningless PCC, so vary it only by passing `routed_expert_weights_dtype` everywhere at once.

**Why:** "what precision is this model" has no single answer here, and the intuitive one (BF16/BFP8)
is wrong for 97% of the weights. Optimisation effort aimed at activation precision is aimed at ~3%
of the bytes.

**How to apply:** for a precision/perf lever, start at the routed experts (BFP4, LoFi) and at
SDPA's HiFi2-on-bf16-query. See [[mistral4-pp4-real-d2d-results]].
