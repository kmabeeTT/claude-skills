---
name: gemma4-perf-gate-total-is-wall
description: "Gemma4 perf gate \"[traced_perf] TOTAL\" is wall time incl. host staging that swings ~110 ms/run at 256k@2k; A/B on the DEVICE line, and route ops via a pytest -p plugin for same-build A/Bs"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 08ccb5d7-967e-4013-9a15-2e893bfee6c6
  modified: 2026-10-31T03:13:19.509Z
---

`test_model_perf_glx.py`'s `[traced_perf] TOTAL` is wall time: device + host staging (tokens/metadata/rope copies between chunks). At 256k@2048 staging varied 162-271 ms run to run regardless of the code under test, while device time had sd ~1-3 ms. A 2-run A/B on TOTAL showed a fake +0.27% "regression" for the Gemma4 sliding SDPA fork (2026-10-31); 4 runs each flipped the sign, and the DEVICE line showed no change.

**Why:** host staging noise is ~10x the device noise, so a small TOTAL delta is meaningless with few runs.

**How to apply:** compare `[traced_perf] DEVICE ... | staging ... | wall ...` (device column) across >=4 alternating runs. For a same-build A/B of an op swap, a pytest plugin (`pytest -p name`, module on PYTHONPATH) that reassigns the ttnn function works; with runs_fork_1030/lib.sh `rjob`, pass PYTHONPATH via `env PYTHONPATH=... $PY -m pytest` inside the command, because rjob's r_env resets PYTHONPATH. Also print a marker from the plugin and grep it, to prove the routing happened. Related: [[gemma4-perf-gate-4096-host-variance]].
