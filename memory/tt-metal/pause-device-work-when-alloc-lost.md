---
name: pause-device-work-when-alloc-lost
description: "Stop queuing device runs when Kyle's SLURM allocation on the box is gone or another user holds chips; ~/scripts/alloc_guard.sh enforces it"
metadata:
  node_type: memory
  type: feedback
  originSessionId: acd61426-ceec-4183-81e4-9c1da88001f8
  modified: 2026-10-15T17:03:57.915Z
---

If another real user is using chips on the box, or Kyle no longer has the SLURM allocation for it, pause all further device work: it means Kyle lost the machine. This applies in general, not only to one box.

Exception: Alina (`akhan`) and Asif (`mmanzoor`) are Kyle's teammates and sometimes share his machines. Their holding chips is sharing, not a lost machine, so keep queuing.

**Why:** Kyle's boxes are SLURM allocations with an end time (e.g. bh-glx-110-d06u02, job #130974, 1-day limit). Unattended queues can keep running after the allocation ends and collide with the next user's jobs.

**How to apply:**
- Before each device step, check both:
  - `squeue -h -u $USER -t RUNNING -o '%i %N'` lists this node. `squeue -w <node>` fails here with "Can't find plugin for select/graph", so filter %N instead.
  - `~/scripts/tt-devs.sh` holder lines (`^ +PID ... user=X`) show only `user=kmabee`, `akhan` or `mmanzoor`. Don't grep the whole output: its help text contains "user=NAME".
- For unattended queues, run `~/scripts/alloc_guard.sh <queue_pid> [60]` beside the queue. Teammates are allowed by default (`ALLOW_USERS`, default `akhan mmanzoor`). It kills the queue script, so no new step starts, and lets the running step finish. Don't glx_reset someone else's chips.
- Not optional for short timeboxed sessions either: on 2026-10-15 (c05u08) the alloc ended ~16:30 UTC, ~1 h before its listed end, and I kept queuing (with glx_resets) for 30+ min on another user's job until Kyle stopped me. A start-of-session check is not enough; start alloc_guard with every queue, or put the squeue check at the top of each queued step.
- Kyle checks from slurm-login-01 with `~/scripts/slurm_free.py | grep kmabee`.
- Related: [[device-usage-visibility]], [[shared-tree-multi-session]].
