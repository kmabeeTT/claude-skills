---
name: ccl-one-worker-per-link-and-semaphore
description: Two hard constraints when adding a second concurrent fabric exchange to a tt-metal op - one worker per (link, direction) EDM channel, and one incrementer per fused-op semaphore
metadata:
  type: reference
---

Adding a **second concurrent fabric exchange** to an existing op (done 2026-09-16 for the Gemma4
multi-hop SWA halo) hits two limits that present as silent hangs, not errors:

1. **One worker core per (fabric link, direction).** Two workers that both
   `append_fabric_connection_rt_args(src, dst, link=0, ...)` on the same direction stall: the first
   sender opens the connection, sends, and then blocks mid-transfer; its reader fills the CB behind
   it and the op wedges with the host in `completion_queue_wait_front`. Give each concurrent
   exchange its own link. The convention is visible in `all_gather_async` (one core per link *per
   direction*) and stated in `reduce_scatter_minimal_direct_factory.cpp`.
2. **One incrementer per fused-op signal semaphore.** `Semaphore::up` is a NoC atomic increment whose
   own header warns that on WH/BH "multiple cores incrementing simultaneously may lead to lost
   updates". Two workers signalling the same semaphore loses a signal ~1 device in 4, timing
   dependent. `AllGatherFusedOpSignaler` carries one semaphore per all-gather direction, so two
   exchanges can take one each (`push_all_gather_fused_op_rt_args(..., direction)`).
   Related: `Semaphore<>` defaults to **LOCAL_NONATOMIC**, so `down()` is a plain read-modify-write —
   wait for all arrivals and decrement once rather than once per arrival.

Together these cap **concurrent** exchanges at min(num_links, 2) on BH — but that is a
*connection-slot* limit, not a bandwidth one, and there are two supported ways past it:

* **A fabric mux core.** `high_bw_all_gather_unicast_factory.cpp:403` states it outright: with more
  than one worker per link "the workers of a direction can't each open a direct connection (an ERISC
  exposes one worker sender channel per direction), so they share a fabric mux: one mux core per
  direction per link owns the connection and multiplexes their traffic." This is how all_gather
  scales past num_links cores.
* **Sequential hand-off of the channel** (what the multi-hop halo does). `open_start()` reads "the
  cursor block left by the previous producer on this channel" and `close_start()` persists it "for
  the next connection on this channel" (`edm_fabric_worker_adapters.hpp`), so one worker may close
  and another open. Gate the later worker on a local semaphore incremented after the predecessor's
  `close()` — not after its last send, since the cursor is persisted in `close_start()`.

**How to apply:** when a new op needs N simultaneous fabric sends per device, first ask whether it is
actually bandwidth-bound — for the SWA halo the payload was invariant at 1024 tokens per device
however many hops it was split into, so links were never the constraint. Then pick: one link per
send, a mux core, or sequential hand-off. See
`~/debug-docs/gemma4_swa_multihop_halo-noissue/MULTIHOP_SWA_HALO.md` §8.4.
Debug tooling notes in the same doc: the **watcher is unusable on ring_joint SDPA** (ACTIVE_ETH
kernel-config overflow, fires on unmodified code too), DPRINT is printf-style with
`api/debug/dprint.h`, and `TT_METAL_DPRINT_CORES` needs `"(11,0),(11,1)"` form.
