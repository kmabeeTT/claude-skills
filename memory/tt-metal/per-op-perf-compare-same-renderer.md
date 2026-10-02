---
name: per-op-perf-compare-same-renderer
description: "A cross-branch per-op perf comparison is only valid if BOTH sides are re-rendered from the raw captures by the same tool; per-device spread on one TT op is ~17%, so a number lifted from a summary table can manufacture a regression"
metadata:
  node_type: memory
  type: project
---

**Never compare a per-op device time against a figure lifted from an earlier summary table,
writeup or gist — re-render both sides from the raw captures with the same tool.** Learned
2026-09-17 on Gemma4 prefill (BH galaxy 8x4), where doing it wrong produced a **false +21%
regression report** that I gave the user before checking.

What happened: a 2026-09-10 gist reported the sliding `RingJointSDPA` at 0.38 ms; the new
branch measured 0.455 ms via `tt-perf-report`, so it looked like the multi-hop halo had cost
the sliding path 21%. Re-rendering **the gist's own capture** with `tt-perf-report` gives
**0.447 ms** — the real delta is **+1.9%**. Nothing had regressed.

**Why it is so easy to get wrong: the per-device spread is bigger than the effect.** For that
one op across the 32 devices of one capture:

    min 382.9 us | median 434.5 | device 0 394.0 | max 446.8      spread 17%

`tt-perf-report` merges devices and reports the **slowest**. The gist's number sat near the
**minimum**. Different aggregations of the same capture differ by more than any regression
worth catching. (The gist's deeper values could not be reproduced from its own CSV by ANY
per-device aggregation of `DEVICE KERNEL DURATION` — its 480 us exceeded the max of 459.4 —
so its column was computed some third way that was never pinned down. Another reason not to
trust a transcribed number.)

**How to apply:** before claiming any per-op delta across branches/builds/dates, find the raw
`ops_perf_results_*.csv` for BOTH sides and run the same renderer over both with the same
signpost window. If the old raw capture is gone, the comparison cannot be made — say so
instead of comparing against the old writeup. Keep old captures for exactly this reason: the
Gemma4 pre-multi-hop-halo baselines are at
`/data/kmabee/gemma4_runs/attn_op_captures/` on bh-glx-120-b03u02 (marked `DO_NOT_DELETE.md`;
the 17 MB CSVs are what matters, the 183 MB `.tracy` files are optional).

Same family as the earlier `rms_norm` retraction, which compared per-op timings across two
builds — except there the difference was real tooling/build skew, and here re-rendering showed
the hardware had not changed at all. Both point the same way: **the comparison is only as
valid as the weakest-controlled side of it.**

See [[gemma4-sdpa-qchunk-occupancy]], [[gemma4-prefill-rmsnorm-row-parallel-floor]],
[[tracy-device-trace-profiler-trap]].
