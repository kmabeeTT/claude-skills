---
name: tt-device-broker-300s-silence-kill
description: "tt-device-mcp broker SIGINTs a job after 300 s with no stdout; redirecting pytest to a file looks like \"kernel build failed\" with empty logs"
metadata:
  node_type: memory
  type: reference
  originSessionId: 08ccb5d7-967e-4013-9a15-2e893bfee6c6
  modified: 2026-11-03T18:26:24.477Z
---

On boxes with the tt-device-mcp broker (bh-glx-120-b07u08, 2026-11-03), device jobs go through `tt_device_job_run_bg`. The broker marks a job `hung` after **300 s with no stdout** and sends SIGINT (exit 130).

A wrapper that sends pytest output only to a file (`>> $log 2>&1`) gets killed at exactly t+300 s. The SIGINT lands mid kernel-JIT, so the visible symptom is `TT_THROW: trisc2 build failed. Log:` with an **empty** compiler log and no .o file — it looks like a toolchain/PCH race or OOM, but the same compile command succeeds by hand.

**How to apply:** always `tee` job output to stdout with `PYTHONUNBUFFERED=1` (runs_fork_1030/devjob_1103b.sh does this). The broker env file also needs `PYTHON_ENV_DIR` when the worktree has no python_env. A 32/32 "claimed" from tt-devs.sh with a dead lock PID is normal there; trust `tt_device_queue_status`. Related: CLAUDE.md ("Shared TT boxes: lost allocation").
