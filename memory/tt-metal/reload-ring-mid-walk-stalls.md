---
name: reload-ring-mid-walk-stalls
description: Blaze reload-ring runs intermittently stop mid-walk blocked in read_output waiting for a D2H page that never arrives; how to diagnose it live
metadata: 
  node_type: memory
  type: project
  originSessionId: 739afd67-235a-4cd0-87e1-9e4707ba469e
  modified: 2026-09-20T14:38:56.037Z
---

On 2026-09-19 (bh-glx-120-b03u02, Mistral Small 4, 8 stages x 2x2) **two of four walk-driving reload-ring runs stopped inside `_drive` with no diagnostic at all** — last log line complete, no traceback, no `MPI_ABORT`, no pytest summary, capture and install fully finished beforehand.

| run | pages | outcome |
|---|---|---|
| disagg decode | 8 | completed |
| chat #1, 3 turns | 83 of 512, retired cleanly at 512 | completed |
| control, self-prefill 552+6 | stalled at **503**/558 | stopped |
| chat #2, seeded, 556-tok prompt | stalled at **~4**/512 | stopped |

The two failures are at wildly different page counts, so it is not a fixed limit. Both happened in the evening, many device runs after the last `tt-smi -glx_reset`.

**2026-09-20: caught one LIVE, with a stack.** A fourth occurrence (bh-glx-120-b03u08, fresh box, board smoke-tested healthy beforehand) stalled during the *retirement* pad-page phase after a correct 7/7 turn. All 8 ranks pinned at ~100% CPU with the MAIN thread in `R` and worker threads in `futex_wait` — a busy completion poll, not a deadlock. `kill -ABRT` on rank 0 gave:

```
blaze/models/pipeline_block.py:988 in read_output
blaze/models/pipeline.py:209     in read_output
blaze/reload/pipeline.py:866     in _drive        <- ctx.pipeline.read_output(page)
```

So the host is blocked waiting for a **D2H output page that never arrives**: the ring stopped producing output mid-walk while the host kept driving. That is the shared signature to report upstream; root cause still unknown. Note this run had a ~300 s idle (blocked `inputs` callback) between the last real page and the first pad page — but chat #1 on 2026-09-19 survived a 900 s idle and retired 429 pad pages cleanly, so idle length alone does not explain it.

**After a hard kill the chips read as held even though they are usable.** `tt-smi -glx_reset` re-inits the boards, but 32 stale `/dev/shm/TT_UMD_LOCK.CHIP_IN_USE_*_PCIe` files remain with dead owner pids, so `tt-devs.sh` shows 0/32 free. UMD recovers them via EOWNERDEAD on next acquire (a mesh smoke test passes on all 32 in that state), but to make the holder check honest again: verify the pids are dead and yours, then `rm -f /dev/shm/TT_UMD_LOCK.CHIP_IN_USE_*_PCIe`.

**Why it is hard to read:** a SIGKILL and a wedged collective leave an identical log. Also, ranks 1-7 going silent is NOT a symptom — only m0 drains and logs tokens (`watch=False, log_every_token=False`), so every other rank legitimately stops logging after `table filled`. Do not read simultaneity into that.

**The stale-board hypothesis is now WEAK.** It was the leading guess after 2026-09-19 (both failures late in a long session, many runs since the last reset). The 2026-09-20 occurrence contradicts it: a fresh box, a `tt_mesh_smoke.py` pass on all 32 chips immediately beforehand, and a cold session. A degraded board is still worth ruling out with a reset before believing any *numerics* result (see [[glx-hard-kill-needs-reset]] and the retraction in [[mistral4-disagg-prefill-decode]]), but it does not explain these stalls. Treat the cause as open, and the `read_output` stack above as the thing to report.

**How to apply — diagnose at the moment it stalls, in this order:**

1. **Is it alive?** `ps -eo pid,etime,stat,pcpu,cmd | grep -E "mpirun|pytest"` plus `~/scripts/tt-devs.sh`. This one check splits "killed" from "hung" and is the thing whose absence made 2026-09-19 undiagnosable. Do it before anything else, and before the allocation goes away.
2. **If alive, get the stack:** `kill -ABRT <a rank pid>` — pytest enables faulthandler, so it prints the frame. That is how the tile-unaligned `actual_isl` collective hang was cornered.
3. **Re-run after `tt-smi -glx_reset` before believing any conclusion.**

**Do NOT set `TT_MISTRAL_RING_LIVE_PROGRESS=1` to investigate.** `test_mistral_ring_reload.py`'s own docstring records that polling those worker cores wedged the sender's linked mcast at t90 while the identical 615 positions completed with the reads absent. It manufactures the failure being chased. Related: [[mistral4-disagg-reload-ring-260919]].
