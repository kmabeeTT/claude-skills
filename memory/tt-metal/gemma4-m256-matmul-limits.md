---
name: gemma4-m256-matmul-limits
description: "Gemma4 chunk-2048 projections (M=256 per device) sit on two coincident ~100 us limits; bfp4 weights, fused gate+up, subblocks, fidelity, async/prefetcher all null; only width-sharded in0 helped (-1 ms/chunk)"
metadata:
  node_type: memory
  type: project
  originSessionId: 170463d4-8ab0-424a-a66a-5dd1fd442cbc
  modified: 2026-09-29T04:19:44.308Z
---

Measured 2026-09-29 (single-chip microbench /data/kmabee/mm_0925/in0_shard_bench*.py, gateup_bench.py, plus in-model runs):
- 1D in0-mcast with interleaved in0 has ONE in0 sender core (matmul_multicore_reuse_mcast_1d_program_factory.cpp:269). In-model fit: t ~ 15 us + 36 us/MB of in0.
- Width-sharding in0 over K/8 cores (LOCAL knob GEMMA4_IN0_WS) gives up 112->97, qkv 99->79, o 48->42 us; in the traced demo 2048: 63.1 -> 62.1 ms. Reshard costs ~8.5 us.
- But at M=256 the weight stream is ALSO ~100 us (~317 GB/s effective for the 1D pattern): bfp4 weights 103 vs bfp8 106 us; in-model bfp4 down/up null. Fused gate+up (N=10752) = exactly 2x one projection. At M=64 it is purely weight-bound (bfp4 64 / bfp8 89 / bf16 155 us).
- Subblock shape, LoFi vs HiFi2, bf16 vs fp32 dest: null. dst_full_sync_en + fp32 dest + 4x2/8x1 subblock gives WRONG results (PCC 0.64): a matmul bug worth reporting.
- BH tensor prefetcher (gather_in0 ring, 64 cores, in0_block_w=1) would leave a ~compute-bound matmul of the same time: not worth integrating for M=256.
**How to apply:** don't re-sweep matmul configs at 2k; the remaining matmul lever needs a new kernel (multi-sender in0 plus bank-local weight streaming together). See [[gemma4-prefill-chunk-size-win]].
