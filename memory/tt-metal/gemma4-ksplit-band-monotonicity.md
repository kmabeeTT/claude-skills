---
name: gemma4-ksplit-band-monotonicity
description: "Ring SDPA K split with ≥5 bands silently dropped work (fixed 2026-10-08); whole-model KV PCC did not catch it, the op test did"
metadata:
  node_type: memory
  type: feedback
  originSessionId: cb89ff89-ab05-41ba-9023-e1edff8e6e47
  modified: 2026-10-08T06:07:05.485Z
---

`ksplit_range(n, i, count)` slices are not monotone in n: at 5 bands, band 2 owns [0,1) of 2 chunks and nothing of 3. The reducer judged sender emptiness from the largest per-ring-iteration count, so it discarded real work (op test chunk 2 PCC 0.898). Exhaustive check: safe up to 4 bands, broken from 5. Fixed in tt-metal `3eff8f6bb13` (reducer records a per-ring-iteration sender bitmask).

**Why:** the whole-model KV PCC (0.983653 / min head 0.9455) PASSED with the bug, because only a few early chunks are hit.
**How to apply:** for any ring-SDPA scheduling change, run `tests/nightly/blackhole/sdpa/test_ring_joint_sdpa.py -k "gemma4_global or gemma_sliding_ksplit"` (and add a case for the new config) before trusting KV PCC. Related: [[gemma4-2k-attack-1008]].
