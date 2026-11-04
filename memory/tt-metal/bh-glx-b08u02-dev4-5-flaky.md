---
name: bh-glx-b08u02-dev4-5-flaky
description: bh-glx-120-b08u02 Metal devices 4/5 (T1:N5/N6) failed secondary bus reset and were invisible to tt-triage during 3 hangs on 2026-10-19; clean for 12+ runs after a second glx_reset
metadata:
  type: project
---
On 2026-10-19 (the day after the box came back from an outage), 3 of the first ~15 Gemma4 runs hung on bh-glx-120-b08u02 between 05:28 and 06:00. Two were triaged at the stall:
- one inside ring SDPA, with halo writers blocked in fabric sends on devices 12-15;
- one with all devices idle and no op running.
In both, tt-triage's op mesh shows "Metal Device 4 (no exalens map)", and in the first device 5 too. `glx_reset` printed "Secondary bus reset not completed" for /dev/tenstorrent/4 and /5. After the second reset (~06:00), 12+ runs had no hangs.

**Why:** cost about 30 min of chasing a "lanes + two halo slots" op bug that wasn't one. The op-level test passed, and the same configs passed after the reset.
**How to apply:** on this box, a hang where triage can't map devices 4/5 is the board, not your change. Reset and rerun before debugging. If it recurs, file an infra ticket. Related: [[glx-hard-kill-needs-reset]], [[tt-triage-at-the-stall]], [[bh-glx-b02u08-dev16-dead]].
