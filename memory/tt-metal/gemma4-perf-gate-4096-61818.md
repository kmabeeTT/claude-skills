---
name: gemma4-perf-gate-4096-61818
description: Gemma4 perf gate SLOW at chunk 4096 since 10-31 is a real regression from #61818 (matmul 2D mcast helpers), not host drift; one-commit A/B proven 11-03
metadata:
  type: project
---
The 11-02/11-03 chunk-4096 SLOW failures of test_model_perf_glx are #61818 (66e7771ec01): one-commit A/B on b08u08 gives +1.5-2.4% on every 4096 device cell, 2048 flat, 8192 +0.3%. Gemma4 uses the 1D short-M config at 2048 and 2D mcast at 4096/8192. Main nightlies per host show the step between 7aad8aacd and 73c6483da. Data + issue draft in ~/debug-docs/gemma4_perf_gate_host_variance-60461/ (STATE_PERF_GATE_4096_1103.md).

Op level (11-04): the loss is MatmulMultiCoreReuseMultiCast (2D) at per_core_M=2 (sliding QKV +12%, MLP up/gate +6-9%), per_core_M=4 flat; issue #64190 (assigned to the PR author), repro pushed as kmabee/repro-2d-mcast-short-m @ eb22916fcde; source-guard fences and in0 location ruled out.

**Why:** the handoff framed it as host drift vs #61353 calibration; per-host main history plus a chunk-2048 control separated it in minutes.
**How to apply:** for perf-gate drift, tabulate main nightlies per host first (same host before/after), and use the chunk-size pattern to pick the op path. See [[gemma4-perf-gate-4096-host-variance]], [[gemma4-perf-gate-total-is-wall]].
