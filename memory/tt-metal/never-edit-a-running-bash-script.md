---
name: never-edit-a-running-bash-script
description: Editing a bash script while it is executing corrupts that run; long campaign drivers must be edited only between runs
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b34dfc31-38f0-4e7c-8b63-50c10a063c91
  modified: 2026-09-15T23:27:41.462Z
---

Never edit a shell script that is currently executing — including a driver several levels up the call chain from the thing being edited. Bash reads a script incrementally from a file offset rather than loading it into memory, so rewriting the file shifts the byte offsets underneath the live interpreter and it resumes parsing mid-token. The failure is a `syntax error near unexpected token` pointing at a line that is perfectly valid, and `bash -n` on the same file passes, which makes it look like a phantom.

**Why:** cost a cell of the 2026-09-15 PP=4 prefill campaign. I added ISL 15,360 to `run_matrix.sh` while `run_campaign2.sh` had it mid-flight; the cell itself completed `rc=0`, then the wrapper died at exit 2 on a stale offset and the driver filed a healthy cell as `FAILED.pass1`. Nothing was wrong with the measurement or the edit — only the timing.

**How to apply:** before editing any harness script, check whether a driver is live (`ps -p <pid>`, or the campaign's own master log). If it is, either wait for the gap between cells, or copy the script to a new path and point the *next* invocation at that. Long multi-hour drivers re-invoke their inner scripts fresh per cell, so an edit landing between cells is safe and an edit landing during one is not — the window is not visible from outside, so do not try to time it. Related: [[mistral4-prefill-campaign-harness]].
