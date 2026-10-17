---
name: tt-triage-at-the-stall
description: Run tt-triage AT a hang via TT_METAL_OPERATION_TIMEOUT_SECONDS + TT_METAL_DISPATCH_TIMEOUT_COMMAND_TO_EXECUTE; a triage minutes later can mislead; gdb the host; per-replay logging makes trace hangs deterministic
metadata:
  type: feedback
---

For a device hang, take tt-triage at the stall, not minutes later: `TT_METAL_OPERATION_TIMEOUT_SECONDS=30 TT_METAL_DISPATCH_TIMEOUT_COMMAND_TO_EXECUTE="python tools/tt-triage.py --skip-version-check > triage.txt 2>&1"`, then kill the process (teardown then times out device by device, ~30 s each). Also `gdb -p <pid> -batch -ex "thread apply all bt 25"` on the host process.

**Why:** on 2026-10-14 a late triage blamed CCL semaphores; on 10-15 a triage 7 min after the stall showed every device idle, and only the at-stall triage showed the real state (one device's dispatcher in `process_wait` on the worker-completion count). That cost a wrong root cause in docs/drafts. See [[gemma4-batching-poc-traps]].

**How to apply:** wrap device runs in a stall detector (log quiet N s → triage → kill → glx_reset → clean own CHIP_IN_USE locks; ~/runs_agentx/hang/lib.sh is a template). Bisect with cheap env switches in a local probe test, and add per-replay host logging: it made a timing-dependent trace hang hit the same replay every run. tt-triage needs the tt-exalens in tools/triage/requirements.txt (0.4.1 on 10-15, venv had 0.3.32): side install at /data/kmabee/exalens041 + tt-umd 0.9.12 at /data/kmabee/exalens041_umd (uv pip --target), used via `PYTHONPATH=/data/kmabee/exalens041:/data/kmabee/exalens041_umd` in the timeout command; with it the full triage incl. callstacks of every dispatcher/prefetcher works. Read prefetcher callstacks too: on 10-15 the real cause showed as a prefetcher that had left its main loop, not the dispatcher wait the old triage suggested. "brisc is not halted" on some devices' `dump_fast_dispatch` is normal noise.
