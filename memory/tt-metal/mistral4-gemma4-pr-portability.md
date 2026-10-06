---
name: mistral4-gemma4-pr-portability
description: Which Gemma4 prefill PRs can help Mistral4 (mostly none) and the measured null result from the ring-SDPA K split / segmented accumulation
metadata:
  type: project
---

2026-10-06. Checked the 13 PRs in Kyle's Gemma4 perf-journey gist (`70784f19e26b2aec34ae7499be648dc3`) against Mistral Small 4, using a layer profile to weight them. **Almost none port.**

Mistral4 layer-0 cost at 256k (asif+alina build): **RingJointSDPA 7,427 us (68%)**, MoE 2,179 (20%), collectives 759 (7%), matmul 261 (2.4%), norm 90. At chunk 1 it inverts: MoE 2,075 of 3,702 (56%).

Dead on arrival, verified in code:
- **No sliding window.** Mistral4 is 100% global attention; the alternating sliding/global machinery (`tt/v4/block.py`, `TtSWA`) is DeepSeek-V4 only and the Mistral4 adapter never reaches it. Kills #57453, #57979, #59214 and the sliding half of #59222.
- **No GELU.** `hidden_act="silu"`; expert FFN is SwiGLU (`tt/moe/tt_routed_expert.py:357`). Kills #59049 and the fast-gate-GELU half of #59222.
- **Fabric is already a torus.** The 1rank yaml sets `PREFILL_FABRIC_MODE: 2d_torus_xy` -> `FABRIC_2D_TORUS_XY`, descriptor `RING, RING` on 8x4, so `get_usable_topology` has nothing to downgrade. #57931's win is unavailable. (One exception by design: the MoE shared-expert reduce-scatter is forced Linear when overlap is on, `tt/moe/tt_moe.py:362`.)
- The remainder (#57454 matmul/norm configs, #59221 small ops, #59195 idle-core head ops) target <3% of the layer.

**#58032 K split and #58223 segmented accumulation: supported by the op, enabled, and measured NULL.** They are `SDPAProgramConfig` fields (`sdpa_config.hpp:24,31`), unset by Mistral4; only Gemma4 sets them. The op's gate needs `max_q_per_core == 1`, which at q_chunk=32 fails (8 local heads x 20 chunks = 160 units > 120 cores), so raising q_chunk to 64 is a prerequisite. Measured from asif+alina (14.54 s at 261k): **q_chunk 64 alone costs +2.3% (14.87 s)**; +`max_k_splits=4` 14.86 s; +`segmented_accumulation` 14.87 s — all within noise of each other.

**They really did engage** — don't record this as "never applied". Proof: with `max_k_splits=1` and `segmented_accumulation=true`, the `TT_FATAL` that fires only when `max_q_per_core > 1` did **not** fire, so the gate passes. The layer profile independently shows SDPA getting *worse*, 7,427 -> 7,678 us. Note the profile's `Cores` column reads **114 both before and after**, so it cannot be used to detect engagement (same trap as [[gemma4-sdpa-qchunk-occupancy]]).

**Why null:** consistent with [[mistral4-movement-bound-not-flop-bound]] — K split buys compute parallelism, and Mistral4's ring SDPA is bound by ring communication, not FPU work.

**How to apply:** don't port Gemma4 attention work to Mistral4 on the strength of a shared op name; weight a PR by the layer profile first. The untouched lever is MoE (Combine 917 us + Dispatch 652 us per layer), which no Gemma4 PR addresses because Gemma4 is dense. Branches kept: `kmabee/m4-exp-qc64{,-ksplit4,-ks4-segacc,-segacc-only}`. See [[mistral4-tp4-perf-compare-1005]].
