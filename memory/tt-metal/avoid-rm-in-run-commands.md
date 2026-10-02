---
name: avoid-rm-in-run-commands
description: "Don't put rm -rf / rm -f cleanup in test-run commands; use fresh timestamped paths and unique names instead"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 2fa781d6-0050-442b-9254-4c2bb39af9f9
  modified: 2026-09-26T00:39:11.182Z
---

Build run commands so they need no deletion: give pytest a new `--basetemp=<dir>_$(date +%H%M%S)` instead of `rm -rf <dir>` first, and a unique `PREFILL_LAYER_COMPLETION_RING=/tt_prefill_layer_completion_ring_kmabee_<ts>` instead of `rm -f /dev/shm/...`.

**Why:** Kyle rejected a 256k PCC launch on 2026-09-26 because it contained an `rm -rf` ("There was a dangerous RM command can we avoid that").

**How to apply:** any time a harness would clean up before a run, pick a new path or name. Old harness scripts (clean_0925/matrix.sh, simplify_0925/run.sh, runs_0925/lib.sh) still contain rm lines, so don't copy those verbatim. Related: [[glx-hard-kill-needs-reset]].
