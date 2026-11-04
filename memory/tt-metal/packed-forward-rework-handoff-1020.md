---
name: packed-forward-rework-handoff-1020
description: "Gemma4 batching PR 5/6 ported to MiniMax's packed-forward format (#60943/#60998/#60999) and validated on c02u08 10-20; local branches only, push awaits Kyle; read RESULTS_PACKED_FORWARD_REWORK_1020.md"
metadata:
  node_type: memory
  type: project
  originSessionId: 07c0e114-c7a1-4bfb-acc1-0b1757bef34d
  modified: 2026-10-20T21:44:25.792Z
---

2026-10-20: PR 5 (#61264) and PR 6 (#61265) were ported off our step message (PR 3 #61238, retired) onto the shared packed-forward format, because Kyle was told to let MiniMax lead. Done and validated on bh-glx-120-c02u08 the same day: every check green, F=1 bit-identical to plain main. Pushed 23:35 UTC 10-20 (old tips tagged `kmabee-{deps,pr5,pr6}-pre-packed-1020`); PR 3 #61238 and issue #60873 closed, notes on #61264/#61265, umbrella #60861 updated; CI 39516145143 / 39516147884 dispatched. No comments on the #60943/#60998/#60999 drafts (Kyle: they keep moving; rebase when they land). Branches: `kmabee/gemma4-batching-packed-{deps,pr5,pr6}` in `/data/kmabee/worktrees/wt_packed_1020_1802` (built). Still pending: CI results into the PR bodies, Slack V3.

Read first: `~/debug-docs/gemma4_batching_poc-noissue/RESULTS_PACKED_FORWARD_REWORK_1020.md` (results, push plan, drafts list). The original plan: `HANDOFF_PACKED_FORWARD_REWORK_1020.md`.

**Why:** #60594 made D2H ack records name their chunk with the first 12 B of the metadata. The old PR 5 passed the whole step message, so lanes 1-3's acks decoded as lane 0's chunk, with no error and a matching count.

**How to apply:** the fix is one 12 B `(slot, start, end)` ack tensor per entry. The serving test now checks completion identity, not count; a negative control proves the check catches the bug. `test_prefill_migration[mock-8k]` misses the 0.928 min-head gate on plain main too (0.923203), so it is not a regression. Related: [[batching-prs-maintenance-handoff-1017]].
