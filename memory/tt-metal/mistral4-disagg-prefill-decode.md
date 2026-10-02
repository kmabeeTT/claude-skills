---
name: mistral4-disagg-prefill-decode
description: Mistral Small 4 disagg prefill→decode — DEMONSTRATED WORKING 2026-08-28 (6/6 tokens); how the handoff is done and what is still open
metadata:
  type: project
---

Mistral Small 4 119B is being split: **prefill** in tt-metal `models/demos/deepseek_v3_d_p` (Kyle, branch `kmabee/mistral4-prefill-full-rebased`), **decode** in tt-blaze (Het Shah, branch `hshah/mistral-4`, read-only checkout at `/data/kmabee/tt-blaze`). A future `tt-d-gen` will orchestrate them; as of 2026-08-26 there is no orchestrator, so any integration is a hand-rolled file handoff.

Non-obvious facts worth not re-deriving:
- The `/data/kmabee/tt-blaze` checkout has **no build** — `tt-metal` submodule uninitialized, no `python_env`. Using it at all means a full `UV_LINK_MODE=copy ./install.sh` (it builds its own pinned `origin/blaze-metal` tt-metal), plus a ~240 GB bf16 dequantized checkpoint that blaze needs and prefill does not.
- The KV handoff point already exists in both stacks and needs no new plumbing: blaze reloads every decoder's KV cache from disk before each temporal sweep (`tools/temporal_pipeline.py:696-699`, kernels stopped = the only legal host->device write window) and supports resuming at `Stream(start_position=N)`; prefill already reads its cache to host in natural order (`tt/runners/prefill_kv_validation.py:212-228`).
- Both sides store the same logical MLA latent: 320 wide (256 kv_lora + 64 qk_rope), `bfloat8_b` TILE. Het confirmed `MlaKvCacheFormat.BFP8_TILE` matches decode.
- Meshes are incompatible for co-residency: prefill is `(8,4)` = all 32 chips with a 284 GB cache keyed to that shape; blaze wants a `(4,2)` submesh. Sequential processes only.
- **DONE 2026-08-28: the disagg demo works.** tt-metal prefill (8x4 galaxy, 552-token prompt) → KV cache as files → tt-blaze decode (4x2 mesh) produced *"The capital of France is Paris."*, **6/6 tokens identical** to the monolithic model. Both sides greedy (`use_argmax=True` / `temperature=0.0`), which is what makes token-for-token comparison meaningful.
- Two bugs were found and fixed en route: blaze treated **every prompt page as position 0** (Het's `174121d0a`; independently cornered here as 64 pages in → 1 KV row out holding position 63's value), and a still-open **pe duplication in blaze's KV write path** (32 values duplicated across the 64 rope dims) — isolated to the write path by a write-back round-trip, since seeding 64 distinct pe values round-trips at `pcc=1.000000`. Inert at 6/558 dilution; matters for sustained decode.
- Decode cost here is ~17 min/token, which is **~8000x harness overhead, not decode speed**: `TemporalPipeline` K=1 keeps one stage resident and `make_weight_provider("state_dict", cache_path=None)` re-derives all 37 stages' weights per sweep. The easy fix (untried) is blaze's write-through `MistralSmall4CacheWeightProvider`.
- Blaze branch is now `hshah/mistral-4-emule-rebased` (tt-metal pin `d103fddd`), rebuilt and working.

Full scoping (transform math, file:line anchors, ranked risks, questions for Het) is in `~/debug-docs/mistral4_prefill_planning-noissue/part2/DISAGG_PREFILL_DECODE_HANDOFF.md`. See [[mistral4-bringup-workspace]], [[debug-docs-location]].
