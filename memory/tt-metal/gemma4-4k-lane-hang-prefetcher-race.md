---
name: gemma4-4k-lane-hang-prefetcher-race
description: The Gemma4 4k-lane trace hang is a prefetcher race (exec_buf trid-1 DRAM read in flight past EXEC_BUF_END on shorter device ranges); one-line patch passes; not SDPA/CCL
metadata:
  type: project
---

Root cause found 2026-10-15 on bh-glx-110-d08u02: the mesh trace buffer is padded to the longest device range, so shorter devices have pages after EXEC_BUF_END; `process_exec_buf_cmd` (cq_prefetch.cpp) returns with an async trid-1 trace prefetch still in flight, which overwrites the next host commands in cmddat_q. Patch `noc_async_read_barrier_with_trid(1)` at its end: same-box A/B hang 7/7 → pass 6/6 (Gemma), test_lane_widths sync CCL hang 1/1 → pass 2/2, no step-time cost. Gemma-free repro: 2048 local point_to_point copies on device (0,0) in one trace (tests/ttnn/distributed/test_trace_exec_buf_tail_local.py, untracked; copy in the doc folder) hangs at replay 1, 3/3, passes with the fix. Filed as #60817 (assignees kmabeeTT, jbaumanTT). Fix branch kmabee/issue_60817_prefetch_exec_buf_end_drain @ 58a24d95eec (PR not opened yet; draft PR_DRAFT_PREFETCH_EXEC_BUF_END_DRAIN.md has CI run links), repro branch kmabee/issue_60817_repro @ 56d6016929a. Kyle's branch convention: kmabee/issue_<N>_<short_desc>, created after the issue is opened.

**Why:** earlier docs and the issue draft blamed the lanes SDPA, CCL semaphores, then a worker-count wait; all wrong.

**How to apply:** read ~/debug-docs/gemma4_batching_poc-noissue/HANG_4K_LANES_1015.md (evening section) first. Owners are dispatch/prefetcher. The GEMMA4_CCL_ASYNC workaround in test_lane_widths can go once the fix lands. Related: [[gemma4-batching-poc-traps]], [[tt-triage-at-the-stall]].

**Update 2026-10-16:** #60817 is a duplicate of #60338; its fix PR #60339 (ezaiakinTT, same trid-1 barrier in the EXEC_BUF_END case) was A/B'd on BH Galaxy d02u14 and fixes our hang (unit, Gemma4 repro, test_lane_widths). #60819 closed in its favour. Drop PR 5's GEMMA4_CCL_ASYNC workaround once #60339 merges.

**It also corrupts results silently (2026-10-16, c01u02):** after rebasing onto main `f53ef8d99f1`, four traced batched KV checks moved 0.01-0.03 min head for the middle lanes; bisected to #60337, but every op output (op tests, eager model layer 0) is bit-identical with and without #60337, and applying #60339's `cq_prefetch.cpp` change restores every value exactly with and without #60337 (#60337 only shifted the trace command layout). So a kernel-size change anywhere can move traced numbers until #60339 merges: on an unexplained traced-only PCC shift, apply `/data/kmabee/hang_1015_d08u02/pr60339_kernel.patch` (JIT kernel, no rebuild) before bisecting further. Mixed 4k+2k lane steps stay run-to-run nondeterministic even with the fix (separate issue, test/demo only). Write-up: debug-docs gemma4_batching_poc-noissue/OVERNIGHT_1016_REBASE.md.
