---
name: gemma4-2k-attack-1008
description: "Gemma4 chunk-2048 overnight attack 2026-10-08 on RevC d07u08 — wins, dead ends, ceilings, and where the record lives"
metadata:
  node_type: memory
  type: project
  originSessionId: cb89ff89-ab05-41ba-9023-e1edff8e6e47
  modified: 2026-10-08T06:07:00.647Z
---

Record: prefill-docs `gemma4/perf_understand/CHUNK_2K_ATTACK_RESULTS.md` (branch `kmabee/gemma4-2k-attack-plan`) — every experiment with verdict, knobs, ceilings and the ranked blocker list. Read it before any 2k work.

- **Final (08:20 UTC):** 53.2 → 52.5 ms first chunk, 3.31 → 3.23 s at 100k, 10.31 → 9.64 s at 256k, KV PCC 0.983871 / 0.1799 / 0.9463; knobs on `kmabee/gemma4-2k-exp-knobs` @ `518e9eadbd6` are **2k-only** (sliding-ksplit and GEGLU knobs break 4k/8k).
- **Wins:** global ring SDPA at 2k as q128 x5 K-split bands + bfp8 Q (tt-metal `kmabee/gemma4-2k-global-q128` @ `202ff4b87ed`, with the K-split reducer fix first): 256k 10.31 → 9.91 s. Rectangle K-split bands (6 x 16 cores, one 2D K/V mcast per band) + a second q64 trace for chunks < 24: 9.72 s, TTFT unchanged; +LoFi attention projections 9.63 s. Knobs on `kmabee/gemma4-2k-exp-knobs` @ `8f4ee4e2e37` (LOCAL, env-gated).
- **Dead (don't redo):** sliding halo over the ring wrap, sliding Q-first, sliding halo buffers in L1, RS/AG in the norm's sharded layout (worse), QK 1x8/1x4 subblock, MOP vs no-MOP SDPA matmul, single-buffered V (deadlocks), row-segment / split-rectangle band layouts (each extra injector re-reads the band's K from DRAM; injectors in one physical column are much worse), MLP bf16 DST / 2D configs / fused gate+up (slices eat the gain) / moe_fused_swiglu (L1 at hidden 5376, slower at 2688).
- **More wins:** sliding K split 2 bands; fused gate+up with interleaved weights + `generic_op` GEGLU kernel writing straight into down's sharded input (`tt/experimental/geglu_shard.py`).
- **Ceilings measured:** TP collectives = 8 ms/chunk (removing them: −15% TTFT, −11% at 256k) — the #1 floor item, link-bound store-and-forward, needs CCL-team work; SDPA matmul is operand-unpack bound (~30–40 cyc/tile-mm; HiFi2 adds only ~5, DST wait ~20 cyc) — LLK question worth ~−1.2 s @256k; global SDPA data movement is hidden at q128 x5; sliding halo + reads ≈ 80 µs/layer and the window-1024 halo costs 3.3 ms/chunk total; MLP 1D reader tops out at ~390 GB/s on RevC.

**Why:** the night's value is as much the ruled-out list as the wins. **How to apply:** start from the tracker's "Top blockers" section; use the wrong-output probes (`G4X_RJ_SKIPDM`, `G4X_SWA_OVERRIDE`) to get a ceiling before building anything. Related: [[gemma4-ksplit-band-monotonicity]], [[gemma4-sdpa-qchunk-occupancy]], [[gemma4-m256-matmul-limits]].
