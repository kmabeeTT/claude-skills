---
name: visible-process-is-not-my-process
description: "Under hidepid, a visible PID means same UID, not same session — other Claude sessions run as kmabee too, from other checkouts"
metadata:
  node_type: memory
  type: feedback
  originSessionId: b34dfc31-38f0-4e7c-8b63-50c10a063c91
  modified: 2026-09-24T17:50:39.317Z
---

On these boxes `/proc` is `hidepid`, so the instinct is "if I can see the PID, it is mine." That is wrong. Visibility proves the process shares my **UID**, not that it belongs to **this session**. Several Claude sessions run concurrently as `kmabee`, each from a different checkout (`/data/kmabee/tt-metal`, `tt-metal-2`, …), and all of them are fully visible to each other.

**Why:** on 2026-09-24 I found a leftover chip holder after killing my own run, tested `[ -d /proc/$p ]`, concluded "visible, so mine", and `kill -9`'d it. It was another session's `tt-metal-2` gemma4 pytest, mid-run. Its `run_e2e.sh` parent survived and relaunched, so the cost was one lost iteration plus a confusing failure in their log — but the reasoning would have destroyed hours-long work just as easily. The earlier device-attribution lessons all concerned *other users*, so "visible" had always correlated with "mine" until it didn't.

**How to apply:** before killing any PID, read `/proc/<pid>/cmdline` (or `ps -o cmd=`) and confirm the **checkout path and program** match the run you started — never infer ownership from visibility, uid, or `pgrep` matching a generic pattern like `python3`. Kill by the process group you launched (`setsid` gives you one; record its PGID at launch) rather than by scanning for holders afterwards. Also do not treat another session's handoff marker as authoritative about *current* device state: on the same day, `tt-metal-2/DONE_WORK` was an empty file from 17:19 while that session was actively running new work at 17:47. Check what is running, not what a marker claims. Related: [[device-usage-visibility]].
