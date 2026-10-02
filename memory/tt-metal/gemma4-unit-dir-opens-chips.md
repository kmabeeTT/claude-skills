---
name: gemma4-unit-dir-opens-chips
description: pytest on the whole models/demos/gemma4_d_p/tests/unit/ dir opens the galaxy chips; only test_prefill_configs.py / test_prefill_dispatch.py are host-only
metadata:
  node_type: memory
  type: feedback
  originSessionId: 5ecff3cb-0b03-4794-9f83-de74c864ae69
  modified: 2026-10-02T02:21:53.683Z
---

`pytest models/demos/gemma4_d_p/tests/unit/` (the directory) opens /dev/tenstorrent/* (192 fds seen on 2026-10-02) — some
files there are device tests. I ran it next to a live base perf run; killed it, the run survived (8k 6.85 s = reference).

**Why:** "unit" in the path suggests host-only, but it isn't for the whole dir.

**How to apply:** while a device run is live, run only `test_prefill_configs.py` and `test_prefill_dispatch.py` (host-only,
~5 s). Run anything else through the queue lock. Related: [[shared-tree-multi-session]].
