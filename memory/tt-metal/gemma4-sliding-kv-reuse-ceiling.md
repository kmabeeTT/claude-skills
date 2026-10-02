---
name: gemma4-sliding-kv-reuse-ceiling
description: "Sliding-window SDPA K/V DRAM re-reads cost only ~2% at 8k (probe with zero re-reads: 118.1 -> 115.8 ms); K/V chains for sliding are not worth building"
metadata:
  type: project
---

Measured 2026-09-30 (bh-glx-120-c03u08, 130 W, branch kmabee/gemma4-prefill-0930): a JIT-only probe in
`ring_joint_reader.cpp` that fetches sliding K/V from DRAM for each unit's first chunk only (stale CB data after,
wrong numerics) moved the traced demo 8192 first chunk 118.1 -> 115.8 ms (-1.9%), 2048 58.5 -> 58.0 ms.

**Why:** the 09-29 handoff ranked "sliding K/V reuse (~40 MB/layer from DRAM at 8k)" as the biggest structural
lever from a bytes estimate alone; the re-reads are mostly overlapped with compute.

**How to apply:** before starting any data-movement kernel project, bound it with a probe that removes the traffic
(patch at /data/kmabee/runs_0930/probe_sliding_no_kv_reads.patch shows the pattern). Related:
[[gemma4-sliding-sdpa-ksplit]] (the sliding op at 2k is mostly fixed cost), [[mistral4-movement-bound-not-flop-bound]].
