---
name: common-prefill-tests-dir-opens-chips
description: models/demos/common/prefill/tests is NOT host-only — test_producer_runner_e2e launches a GLM-5.3 runner on the Galaxy (>15 min)
metadata:
  type: project
---

`models/demos/common/prefill/tests/test_producer_runner_e2e.py` spawns a real prefill runner (GLM-5.3 weights from Weka, 8x4 mesh) and loads to device; it took >15 min and was hard-killed by a 900 s timeout on 2026-10-17 (b08u02). The rest of that dir (test_step_message etc.) is host-only, but the modules import ttnn and the root conftest queries the cluster.

**Why:** running "the host tests" for a PR touching prefill_producer/runner grabbed the chips and needed a reset check.
**How to apply:** for host-only checks run `-k "not e2e"` (or name files explicitly), and still take the device queue's flock; treat the e2e test as a device job with a 1 h budget. Related: [[gemma4-unit-dir-opens-chips]].
