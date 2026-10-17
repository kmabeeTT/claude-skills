---
name: gemma4-perf-gate-4096-host-variance
description: "Gemma4 CI perf gate fails \"< min, update the baseline\" on 4096 cells on fast hosts (d07u02); Kyle chose to rerun and reopen #60461 only if it hits main"
metadata:
  node_type: memory
  type: project
  originSessionId: acd61426-ceec-4183-81e4-9c1da88001f8
  modified: 2026-10-15T02:13:51.586Z
---

`test_model_perf_glx.py` 4096 cells run faster on bh-glx-120-d07u02 than main's baselines allow (10-14: 1k dev 73.8 < 74.3, 10k wall 231.4 < 234.6, 10k dev 225.4 < 226.7, 100k dev 2194.6 < 2201.5). Same root cause as #60461 (Kyle filed, closed by #60549, which only dropped the 1k wall gate). Seen on several branches, and on main nightly 38684481291 (10-15, d07u02); reopen comment drafted in ~/debug-docs/gemma4_perf_gate_host_variance-60461/.

**Why:** Kyle (2026-10-15) chose to leave it alone for now: rerun failed jobs on PRs and reopen #60461 only if it shows up on main.

**How to apply:** a 4096-only "faster than min" gate failure on a PR is this, not a regression: rerun the failed jobs (`gh run rerun <id> --failed`). If a main/nightly run shows it, propose reopening #60461 with the run, host and cells. Related: [[ci-status-only-when-verified]].
