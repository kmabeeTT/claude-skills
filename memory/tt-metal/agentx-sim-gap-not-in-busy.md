---
name: agentx-sim-gap-not-in-busy
description: "AgentX sim tail TTFT: the demo's busy_s excludes a ~0.8 ms inter-step gap; calibrating to busy makes the sim's clock ~1% fast under load and queue tails 8% low"
metadata:
  node_type: memory
  type: project
  originSessionId: 4d440b9b-3db4-4768-bc1e-ca40ec882d3f
  modified: 2026-10-15T19:39:18.907Z
---

The batching demo's `busy_s` sums only the time inside `runner.step`. Admit/plan/log between steps costs 0.82 ms batched and ~0.7 ms serial, very stable. A sim calibrated to busy time must still advance its clock by this gap, or saturated-window p90 TTFT reads ~8% low. Fixed for batched in PR 4 patch `9c9ae3efaaa` (local branch kmabee/gemma4-batching-pr4-simtail, 2026-10-15, not pushed); write-up in debug-docs SIM_TAIL_ACCURACY_1015.md.

**Why:** a near-saturated queue amplifies a ~1% service-rate error about tenfold. Per-step noise (sd 2.5%) adds nothing, because step-size variety already dominates the service variance. Only the mean matters.

**How to apply:**
- Per-step silicon residuals can be rebuilt exactly from the demo log: admit each request at the first step whose midpoint follows its measured `started` (steps.py in debug-docs sim_tail_1015/).
- Check the inter-step gap and the lanes x depth bias before reaching for noise models.
- The level is per box. On 2026-10-15, bh-glx-110-d08u02 (RevC, 14 kW) ran device steps 1.5% faster than bh-glx-120-c05u08 (RevB, the calibration box). The difference is in attention (sliding -6%), not dense, so it looks like clock rather than DRAM bandwidth. The predictions recorded beforehand then read saturated p90 +6 to +10% high. One level factor fixed it (p90 within 0.4%). Quote saturated tails with a ±5-10% box band, or set the level per box from one replay.
- Serial 8k at saturation is still -8% on p50 (open). Related: [[batching-agentx-prs-handoff-1014]].
