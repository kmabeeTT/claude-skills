---
name: shared-tree-multi-session
description: "Several Claude sessions share /data/kmabee/tt-metal-2 and the galaxy; check for another session's queue before mkb/checkout/device runs"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 8f985f1d-292b-4c2b-ba24-7719ec3e62ae
  modified: 2026-09-29T22:06:03.326Z
---

Kyle runs more than one Claude session on bh-glx at once, and they share the build tree `/data/kmabee/tt-metal-2` (`/data/kmabee` is NFS, so a session on ANOTHER bh-glx box can hold it too) and the 32 chips.

**Why:** 2026-09-29 02:13 my `mkb` (checkout + build) in the shared tree swapped the build under another session's overnight perf queue (`/data/kmabee/runs_0929n`, session tt-metal-2-4d), which it had to rebuild.

**How to apply:** before any checkout/build in the shared tree or a device run, check `ListAgents` for another tt-metal-2 session and look for a queue lock (seen: `/data/kmabee/runs_0929n/queue.lock` for tt-metal-2, `/data/kmabee/runs_0930/queue.lock` for a session on the separate tree `/data/kmabee/tt-metal-3`; all flock, and the chips are shared even when the trees are not) or a running queue script; if one exists, message that session and slot in through its lock instead of acting directly. 32/32 chips claimed with no process of mine means someone else is running.

**`waitchips` (runs_0925/lib.sh) auto-runs `tt-smi -glx_reset` when every chip lock names a dead PID** — between another session's runs that is exactly the state, so a queued script of mine reset the chips 4 s into the other session's next run (02:29). Never leave a waitchips-based queue waiting while another session owns the machine; go through that session's lock instead. See [[kernel-source-edits-break-queued-runs]], [[stale-chip-locks-look-like-container]].


**Second build tree:** `/data/kmabee/tt-metal-3` also has `build_Release` + a working `python_env` (python 3.10.12 from `/usr/bin`, so it travels between boxes). On 2026-09-29 evening the user said tt-metal-2 was in use from another machine: work in tt-metal-3 until told otherwise. The helpers in `runs_0925/lib.sh` / `runs_0927/common.sh` default `W=/data/kmabee/tt-metal-2` and `PY=` its venv: override both (`W=/data/kmabee/tt-metal-3; PY=$W/python_env/bin/python3`) AFTER sourcing.
**Tree-per-box split (user, 2026-09-29 ~21:50 UTC):** tt-metal-3 is for the other box, bh-glx-120-c03u08; a session on bh-glx-120-c02u02 sticks to tt-metal-2. Don't borrow the other box's tree to build in parallel, even when it looks idle.

**tt-metal-3 configure is slow on NFS:** `cmake build_Release` took 12 min on the first configure after a main
checkout (emsdk, the Tracy WASM viewer's SDK, unpacks 1.7 GB into `.cpmcache/emsdk`; unconditional on main since
~09-29) and 20+ min in a later generate step (`rules.ninja` / `compile_commands.json` written slowly, process in
`rpc_wait_bit_killable`). Other configures took 41 s. It is not hung if those tmp files keep growing; don't kill it.
