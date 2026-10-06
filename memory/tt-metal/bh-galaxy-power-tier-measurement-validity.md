---
name: bh-galaxy-power-tier-measurement-validity
description: "Which prefill measurements stay valid on a low-TDP BH Galaxy — the clock collapses ~26% after ~40 s of sustained load, so long runs inflate ~20% while isolated layer profiles are unaffected"
metadata:
  node_type: memory
  type: project
  originSessionId: 677747a2-f27b-478b-944b-26aaf6be33ca
  modified: 2026-10-06T20:20:15.872Z
---

2026-10-06, Mistral4 asif+alina measured on two boxes: **bh-glx-120-c01u08 (75 W)** vs **bh-glx-120-b05u08 (190 W)**, identical sha `6fd8974f5c9`, same NFS tree, same CI weight cache.

**The throttle is time-based, not depth-based.** Sampling `tt_aiclk` every 5 s through the producer window on the 75 W box:

```
t+2s .. t+37s   1350 MHz   (max)
t+42s           1215
t+47s           1073
t+52s           1030
t+57s..t+72s    ~1000-1050   (collapsed, stays there)
```

~40 s at full clock, then a ~26% drop. Mean over the whole window 1201 MHz vs 1329 MHz on the 190 W box.

What that does to each metric:

| metric | 75 W | 190 W | delta |
|---|---|---|---|
| full 256k run | 17.52 s | 14.54 s | **+20.5%** |
| first chunk (in the full run) | 156.9 ms | 157.6 ms | −0.4% |
| layer profile, SDPA at chunk 50 | 7,425 us | 7,427 us | **+0.03%** |
| layer profile, matmul / norm | 258 / 89 | 261 / 90 | ~0% |

**Valid on a low-TDP box:** per-layer/per-op tracy profiles (the layerprof replays a layer for seconds, finishing long before the onset, so both boxes report the same unthrottled device time), first-chunk/TTFT, and anything under ~40 s of load. **Not valid:** absolute long-context wall time, and — the subtler trap — **long-run A/B deltas**, because two variants run for different durations and therefore accumulate different amounts of throttling. Corroborating evidence that deltas do not transfer between boxes: Asif's commit measured −1.0% on c03u08 but −3.2% on b05u08 on identical code.

**How to apply:** pick the instrument by duration, not by box. For op-level work use the layer profile even on a weak box. For anything quoting seconds at 256k, re-baseline on the same box in the same session and say which box it was. Sample `tt_aiclk` alongside the run (the wrapper in `runs_m4tp4_1006/run_variant.sh` does, chips 0/8/16/24 every 5 s) so the clock is part of the record — a number without its clock is unreadable later. Note the layer profile's own renderer warns that FLOPs% assumes 1350 MHz.

Related: [[bh-galaxy-prefill-power-throttled]] (the 115→130 W re-baseline, and that an isolated-layer bench understates energy wins — the same effect seen from the other side), [[mistral4-tp4-perf-compare-1005]], [[tt-board-smoke-test]] (health is not occupancy: use tt-devs.sh for holders).
