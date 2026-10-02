---
name: stale-chip-locks-look-like-container
description: A killed pytest leaves /dev/shm CHIP_IN_USE locks naming a dead PID; tt-devs.sh then reports "holder unresolvable ... likely a container" -- it is my own dead run, reset + rm the locks
metadata:
  type: feedback
---

When a device run is hard-killed (e.g. pytest `timeout` after a kernel hang), all 32 `/dev/shm/TT_UMD_LOCK.CHIP_IN_USE_*_PCIe` files keep the dead PID as owner. `~/scripts/tt-devs.sh` then prints "IN USE (holder unresolvable: lock pid N not in our namespace ... likely a container)" for every chip. On 2026-09-25 I misread that as another user and idled the queue for over an hour.

**Why:** hidepid hides other users' PIDs, so a dead PID and a foreign PID look the same in /proc.

**How to apply:** check the owner PID (bytes 52..55 of the lock file) with `kill -0 <pid>`: "No such process" = dead (another user's live PID gives "Operation not permitted"). If every lock names a dead PID: `tt-smi -glx_reset` (needed after a hard kill anyway) then `rm -f /dev/shm/TT_UMD_LOCK.CHIP_IN_USE_*_PCIe`. /data/kmabee/runs_0925/lib.sh `waitchips` does this automatically. See [[tt-galaxy-fabric-run-hygiene]].

**Foreign-owned lock files make `waitchips` reset in a loop (2026-09-30, c03u08).** The `/dev/shm/TT_UMD_LOCK.CHIP_IN_USE_*` files can be owned by another account (here `akhan`, who created them first), so `rm -f` fails with "Operation not permitted". After my own pytest timed out, the files kept my dead PID; `waitchips` saw all-dead owners, reset, failed to rm, and reset again every ~80 s (12 resets in 16 min). It harmed no one, since the locks named only my dead PID, but it blocks the queue forever. Fix: when the only owner is your own dead PID and rm is not permitted, skip `waitchips` and just run (UMD recovers stale locks on open, per `tt-devs.sh`). Check with `kill -0 <pid>`: "No such process" = dead; another user's live PID gives "Operation not permitted".

**Merged 2026-10-02 from tt-metal-3's `waitchips-stale-foreign-locks`:** on bh-glx-120-c03u08 the lock files are owned by `akhan` (mode 0666), so this applies to every run there. A dead PID of ours in them makes `tt-devs.sh` report "32/32 claimed (STALE)" and the stock `runs_0925/lib.sh` `waitchips` (which only accepts " 0/32 chips claimed") never returns; it cost 30 min on 2026-09-30. `runs_sasha/env.sh` overrides `waitchips` to proceed after one glx_reset when every claim is STALE: reuse that override for new run dirs, and check queue logs for repeated "stale locks" lines. Never let a waitchips queue wait while another session owns the machine; see [[shared-tree-multi-session]].
