---
name: bh-glx-b09u08-single-channel-links
description: bh-glx-120-b09u08 has 8 inter-tray edges with 1 eth channel (tray1<->3, tray2<->4 at loc 3/4); Gemma4 8x4 runs die at TP reduce-scatter link 1; survives glx_reset
metadata:
  type: project
---

On 2026-11-07 bh-glx-120-b09u08 (130 W) could not run Gemma4 `test_prefill_migration[mock-256k]`: fabric discovery logs `Relaxed mode: target graph edge ... requires 2 channels, but physical edge ... only has 1` for 8 directed edges (trays 1<->3 and 2<->4, loc 3 and 4), and the first TP reduce-scatter dies with `TT_FATAL ... Requested link index 1 is out of bounds. 1 ethernet channels available ... (M0, D0) and (M0, D3)` (fabric.cpp:162) about 4 min in. Still there after a `tt-smi -glx_reset`, so it's hardware/cabling, not training.

**Why:** a run fails only after model load, so finding this costs ~5 min per attempt, and the cause looks like a code bug.

**How to apply:** before a 2-link (num_links=2) 8x4 job on b09u08, grep the runner log or a fabric bring-up for `Relaxed mode: target graph edge`; any hit means pick another box. Related: [[bh-glx-b02u08-dev16-dead]], [[bh-glx-b08u02-dev4-5-flaky]].
