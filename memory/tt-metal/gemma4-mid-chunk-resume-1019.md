---
name: gemma4-mid-chunk-resume-1019
description: "Gemma4 mid-chunk resume: #61878 MERGED 10-24 (877db37d18c, slab starts, 1 halo slot); PR 5/6 rebased onto it and pushed 10-24, CI green; read PR5_REBASE_PLAN_1023.md"
metadata:
  node_type: memory
  type: project
  originSessionId: dfb81da7-b2f8-46d7-9909-fb90dc45d7e6
  modified: 2026-10-21T04:04:24.998Z
---

**2026-10-24:** #61878 merged as `877db37d18c`. PR 5/6 rebased onto main (deps `10cffd6d250`, PR 5 `6c3cb363de7`, PR 6 `5c0987c8ed5`), old tips tagged `kmabee-{deps,pr5,pr6}-pre-rebase-1023`, CI 40054056338 / 40054058174 PASSED. Rebase worktree `/data/kmabee/worktrees/wt_rebase_1023` (own build). Deps still hold our 10-20 snapshot of #60943/#60998/#60999 (upstream moved 10-21; Kyle's call). Details: debug-docs `PR5_REBASE_PLAN_1023.md`.

**2026-10-22:** review comment rejected the per-chunk-size rule; Kyle posted a reply conceding it (continuous batching 4x2k is the case that matters). Now slab starts at every chunk size, one halo slot, ring_prefill.py back to main. Local unpushed commits: #61878 `fd73866e376`, PR 5 `7718cbfa518`, PR 6 re-applied `bf22ef08269` (branches `*-resume-slab` in wt_resume_b_1021). All device tests pass on a03u02 (8192 now bit-identical, 8192 mid-chunk cost +2%). Drafts + results: debug-docs `RESULTS_1022_SLAB.md`, `PR_BODY_RESUME_SLAB_1022.md`, `PR_COMMENT_SLAB_1022.md`, `PR5_BODY_EDITS_SLAB_1022.md`. Personal explainer: https://claude.ai/artifact/QooNpLeE3jRsE4vFfxid1m. Facts below about 2 slots / tile at 8k are history.

2026-10-21 state: A is draft PR #61878, B local. Read ~/debug-docs/gemma4_mid_chunk_resume-noissue/RESULTS_1021.md first. That folder also holds the PR, issue and review-triage drafts.
- **A** pushed as `kmabee/issue_61808_gemma4_mid_chunk_resume` (`e911f7d5f7c` on main `6d09c4bc52c`; issue #61808; draft PR #61878 opened 10-21 with the lean follow-up comment; CI run 39612308560); local name `kmabee/gemma4-mid-chunk-resume-unbatched`; worktree `/data/kmabee/worktrees/wt_resume_a_1021` with its own Release build.
- **B (batched)** pushed 10-21 into #61264 as `331926f18f4` (deps branch now carries a #61878 cherry-pick; PR 6 #61265 re-applied at `38a7c81bc51`); pre-push tips tagged `kmabee-{deps,pr5,pr6}-pre-resume-1021`. Device logs `/data/kmabee/runs_resume_1021b/` (bh-glx-110-a03u08).
- Logs: `/data/kmabee/runs_resume_1021/`.
- The 10-19 prototype (`kmabee/gemma4-mid-chunk-resume` on old PR 5) is superseded. It still holds the two op tests.

Facts:
- A start that wraps a slab needs 2 sliding halo slots. With 1 slot it is silently attended as prefix 0 (min head 0.53-0.57 at 8k on 10-21). See [[ring-sdpa-metadata-silent-prefix-fallback]].
- 2 slots cost +5.5% at 2048, +2% at 4096 and 0 at 8192 (the halo exchange loses multicast). So the default is 1 slot at 2k/4k with resumes on 256/512-token slab multiples, and 2 slots at 8k with any tile.
- **A resume must be allowed to rewind into what the slot holds:** a cache hit rounded down lands below `slot_ends`. The old rule accepted only 0 or the exact end, and a Skills reviewer caught it.
- The packed-forward format already rotates entries and accepts 32-aligned starts, so no shared code changes.
- **Time:** chunks are padded, so a resume saves time only when it saves a whole chunk (~-50% for that turn). Otherwise a mid-chunk chunk costs +1% at 2k and +4-5% at 8k, bracketed by aligned chunks at the same depth.

**How to apply:** the engine contract is `align_down(cached, runtime.resume_granularity)`. Tile granularity at 2k without the cost needs an op change (multicast with per-receiver slots). Nothing is pushed or opened without Kyle.
