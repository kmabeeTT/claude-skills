---
name: kernel-source-edits-break-queued-runs
description: "Device kernel .cpp/.hpp are JIT-compiled at each run's start, so editing them mid-queue breaks queued model runs; also discarded if-constexpr in kernel_main still compiles"
metadata:
  node_type: memory
  type: feedback
  originSessionId: ecf73b36-1b7e-42d3-8c9f-6038bb920bb7
  modified: 2026-09-25T23:07:02.811Z
---

Device kernel sources (ttnn/.../kernels/**) are compiled by the JIT at the start of every run, from the tree as it is at that moment. Editing a kernel (or a model .py) while perf/PCC runs are queued makes the next runs compile the new kernel against the old host .so (missing compile-time args -> static_assert / get_arg failures) or import a half-edited model file. Lost ~6 runs this way on 2026-09-25.

**Why:** host factory changes need a rebuild, kernel changes do not, so the two drift apart the moment the source is saved.

**How to apply:** while a queue is running, write kernel/model edits as patch files (git diff > x.patch; git checkout the files) and apply them in a gap, then rebuild (`cmake --build build_Release --target install`, ~1.5 min incremental) before relaunching. Never rebuild while a pytest holds _ttnn.so. Default every new env toggle to the old behaviour and never pass None into a ttnn kwarg that rejects it.

Git ops count as edits (2026-09-26): `git rebase <upstream> <branch>` CHECKS OUT <branch> in the shared tree and contaminated a queued PCC run. While a queue owns the tree, move branches only with plumbing (`git rebase --onto` is unsafe; use `git branch -f`, or `GIT_INDEX_FILE=tmp git read-tree/update-index/write-tree/commit-tree` + `git update-ref`). Worktrees on NFS take >2 min to add/remove and a timed-out `worktree remove` leaves a half-deleted dir.

JIT cache across branches (2026-09-26): switching between a branch whose kernel uses named compile-time args and one that doesn't can reuse the same `~/.cache/tt-metal-cache/*/kernels/<kernel>/<hash>` dir; the dephash forces a recompile but `named_ct_arg_map_generated.h` is not regenerated -> "'get_named_compile_time_arg_val' was not declared". Purge `kernels/ring_joint_{reader,writer,sdpa}` after each branch switch in a queue.

Related trap: `if constexpr` inside a non-template `kernel_main` does NOT discard the branch, so `constexpr get_tile_size(cb)` on an inactive CB (UINT32_MAX) breaks every other mode's build. Alias to a live CB (`ksplit_enabled ? cb_sum_in : cb_out`). See [[ring-joint-kernel-config-buffer-cap]].
