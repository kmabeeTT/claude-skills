---
name: tt-galaxy-fabric-run-hygiene
description: Non-obvious operational rules for running multi-rank fabric jobs on the bh-glx galaxy boxes
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0c820d14-3b90-4af7-95a5-f68eb71decb3
  modified: 2026-08-31T08:19:36.820Z
---

Running multi-rank tt-fabric jobs (tt-run / prefill_runner) on a Blackhole galaxy has three traps
that each cost a wasted run:

1. **Any SIGKILL of a job mid-fabric-transfer requires a reset before the next launch** (on a galaxy that is `tt-smi -glx_reset`; plain `-r` is per-PCIe-device and not the galaxy path, see [[device-usage-visibility]]). The next
   mesh open otherwise dies with `Timed out while waiting for active ethernet core N-N to become
   active again`. This is not a hardware fault and not a topology bug — it is un-idled ethernet cores.
2. **Never launch a device run in the Claude Code Bash foreground.** The tool's 2-minute cap kills the
   wrapper (even a `timeout 900` one), which is itself a SIGKILL mid-transfer and therefore triggers
   trap 1. Use `setsid nohup ... &` and poll the log.
3. **`release_fabric_links()` GRANTS the fabric links to the socket service; `wait_for_fabric_links()`
   RECLAIMS them.** The naming reads backwards. Omitting the grant raises nothing: the push returns,
   no data moves, and every downstream rank blocks forever in a `recv` that has no timeout.

**Why:** all three present as something else — a hardware/topology problem, a hang, a "flaky board" —
so time goes into debugging the wrong layer.

**How to apply:** reset after every hard kill (and budget for a slow, degraded board, see [[glx-hard-kill-needs-reset]]); background every device run; when writing anything that
drives D2D sockets directly, copy `prefill_runner._lease_reclaim` / `_compute_and_send` ordering
rather than reasoning about the API names. See [[mistral4-pp4-real-d2d-results]].
