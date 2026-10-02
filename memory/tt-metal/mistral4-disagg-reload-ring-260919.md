---
name: mistral4-disagg-reload-ring-260919
description: "2026-09-19 re-run of the disagg prefill->decode experiment on the blaze reload ring - prefill leg green, decode leg written but never exercised"
metadata: 
  node_type: memory
  type: project
  originSessionId: 739afd67-235a-4cd0-87e1-9e4707ba469e
  modified: 2026-09-19T17:30:26.703Z
---

Re-run of the 2026-08-28 disagg experiment ([[mistral4-disagg-prefill-decode]]) against newer code: tt-metal `akhan/issue_53688_mistral_4_small_prefill_followup` + tt-blaze `sshon/wip-mistral-reload-piepline-260915`.

**Outcome 2026-09-19: GREEN, and interactive.** Both legs rebuilt, both patches reworked, 7/7 generated tokens matching the 2026-08-28 reference (`1784 8961 1307 5498 1395 6993 1046` = "The capital of France is Paris.") plus a clean EOS. Then 3 live chat turns off the seeded cache at ~40-60 ms per reply.

- tt-metal `5f7ff1c5fc2`: reworked exporter (handoff v2), `serve_hook` re-added to `run_model`, `demo/conftest.py` fixture bridge, `mistral_small4` -> `mistral_small_4`.
- tt-blaze `kmabee/mistral4-disagg-decode-260919` @ `77e99d38f` (single squashed commit: ring seeding + interactive chat + JSONL events).
- `~/scripts/disagg_demo.sh` orchestrates both legs end to end.
- Handoff: `/data/kmabee/disagg_kv/run_sept19` (552 tok) and `demo_20260919_184445` (550 tok), 13 MB each, reusable.

**Numbers that matter.** Decode went ~20 min/token (TemporalPipeline, August) -> **2.4 ms/token**. Warm prefill is ~5 min, of which the forward is **3.4 s** (JIT cache 1127/1127 hits) -- the 194 s first-run forward was a cold-cache artifact. Ring capture ~9 min warm and is now the dominant startup term: `setup(load+build)` is 82% of it, ~110 s per decoder image, and m0 is the critical path because the head lands there giving it 4 images against everyone else's 3. The blaze weight cache read happens INSIDE that 110 s (the separately-reported "weights staging 7 s" is DRAM staging, not the cache read), and the 64 GB cache is on NFS -- moving it local is the cheapest untested win. The real fix is caching the captured images themselves, which would make startup install-only.

**The control run was never needed and never passed.** Gating against August's token ids is an independent reference and cheaper; the self-prefill control stalled at page 503/558 and that is still unexplained. Nothing in the disagg path goes near it (8 pages vs 558).

**Why:** the decode engine changed completely. The old `KvPersistence.load` seeding hook belongs to `TemporalPipeline`; this branch runs the reload ring (8 x 2x2 stages, 2 layers/visit, 25 images, 3 laps). The old tt-blaze commit `918537034` cherry-picks cleanly but cannot run, so it was dropped rather than carried.

**How to apply:** seed from `golden.sample(ctx, binding)` — the only window where an image's `mla_transients["ttnn_kv_cache"]` is reachable AND the write survives. `release_compute` frees only L1 and retains DRAM pins, but it clears `_pinned_tensors`, so after an image's capture pass the cache cannot be reached at all. Every image owns its own KV cache (a 3-visit stage at 2 layers/visit holds six), and two-layer visits publish layer 1 under `mla_transients_l1`. Blaze's weight cache is ~126 GB and cold-builds at ~250–300 s per decoder image; keep `/data/kmabee/mistral4_blaze_weight_cache` (was at 59 GB when the run died). See also [[mistral4-prefill-has-no-lm-head]].
