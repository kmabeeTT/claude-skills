---
name: lazy-fabric-buffer-zero-fill-race
description: "A fabric receive buffer created lazily with ttnn.zeros can have peers' writes erased by a lagging device's fill; looks like intermittent lost tail rows, first use only"
metadata:
  node_type: memory
  type: project
  originSessionId: c1085a93-2f92-4200-b358-e797de20b737
  modified: 2026-10-09T23:31:55.548Z
---

Gemma4 batching PoC lanes SDPA (2026-10-09, c04u02): "lost V halo tail rows" on some devices were NOT an op/fabric bug. `CCLManager.get_ring_gather_buffer` creates halo receive buffers lazily with `ttnn.zeros`; the fill is an op in each device's queue, while peers write into the buffer over fabric from their own first use. A device running ahead lands rows, then the lagging receiver's fill zeroes them. Fix: `ttnn.synchronize_device` after creating the buffer (wt-batching `2a8062e2540`).

Signatures that identify it: only the FIRST step that uses a new buffer loses data (repeat the same step: repeat 0 bad, 1..n clean); lost data is exact zeros; slow host dispatch (program cache off, host-side work per call) hides it; a sync BEFORE the op does not help (the fill is enqueued after it). Upstream per-request path is exposed too but its first use is a prefix-0 chunk whose halo is masked.

**Why:** cost ~2 h of chasing multicast/unicast/links/semaphores first.
**How to apply:** for any intermittent cross-device data loss, first run the same step N times in one process (`G4B_LANES_REPEAT`) and see whether only the first repeat fails; check what gets allocated/filled lazily during that step. Related: on program-cache hits only buffer bindings + factory scalar patches update — plain uint32 args (e.g. global semaphore addresses) keep the creating call's values ([[gemma4-batching-poc-traps]]).

**Second instance, 2026-10-30 (PR 2 #61237 test):** `test_ring_joint_attention_sliding_lanes_cache_hit_and_trace_replay` failed intermittently on QB2 (SP4xTP1, 1D ring): the test's `stage()` zero-fills halo buffers with non-blocking `ttnn.copy_host_to_device_tensor` before each reordered call; a neighbour's halo exchange overwrote/was overwritten -> last lane's last KV head reads zeros (end of buffer is filled last). Fix: `ttnn.synchronize_device` after staging (PR 2 `afd6c65943c`). Took ~1 h; I again chased fabric VCs / semaphore counts first. The decisive A/B: skip the zero fill -> 0 failures.
**Emulating a QB2 on a BH Galaxy:** `TT_VISIBLE_DEVICES=0,4,8,12` (a 2-link 4-chip ring; find others by 4-cycles in `build_Release/tools/umd/topology -f out.yaml`) + monkeypatch the test's mesh config to SP4xTP1 non-galaxy (tests count /dev/tenstorrent, not visible devices). A 1x4 submesh with 32 chips visible does NOT work: fabric ring handshake times out (no wrap), then glx_reset.
