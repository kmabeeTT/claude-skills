---
name: gemma4-kv-pcc-early-layer-method
description: Gemma4 mock-8k KV PCC final numbers are chaotic and non-additive; compare layers 0-20 instead
metadata:
  node_type: memory
  type: project
  originSessionId: 63dd7621-3b47-4a0b-a1cf-74cf0026d469
  modified: 2026-09-23T03:55:41.630Z
---

`test_prefill_migration[mock-8k]` (lives on #57383/#56862 branch, not main) final/overall PCC moves ±0.01 under ANY arithmetic change and is non-additive (norm-alone and MLP-alone fine, together 0.969). Base itself fails the 0.91 per-head min gate at chunk 4096/2048. Runs are bit-deterministic, so this is amplification, not noise. Placement-only changes (L1 vs DRAM) are bit-identical — a good harness control.

**Why:** single overall-PCC runs cannot rank configs; the 0.91 gate flips on noise-level differences.

**How to apply:** judge numerics on layers 0-20 (PCC 0.999+, before mid-stack amplification): count layers >= base and the (1-PCC) error ratio at L10/L20. That separated a real regression (bf16 attention matmul config, 1.25x error) from noise and justified fp32 accumulation. See [[per-op-perf-compare-same-renderer]].
