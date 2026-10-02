---
name: mistral4-pp4-real-d2d-results
description: Mistral4 now runs on the real D2D pipeline runner; PP_HANDOFF=none is not a ceiling
metadata: 
  node_type: memory
  type: project
  originSessionId: 0c820d14-3b90-4af7-95a5-f68eb71decb3
  modified: 2026-08-31T08:19:52.384Z
---

As of 2026-08-31, Mistral Small 4 runs through the real pipeline-parallel prefill runner
(`models/demos/common/prefill/runners/prefill_runner.py`) both single-rank (KV PCC gated) and as a
4-stage device-to-device pipeline of `[8,1]` column sub-meshes. This closed the longest-standing open
item in the mistral4 prefill investigation.

The headline correction: **`PP_HANDOFF=none` is not a ceiling on PP=4 throughput.** Real D2D is 1.34x
FASTER than `none` at window 5,120 (46,269 vs 34,583 tok/s), because `none`'s single-process harness
carries a fixed ~37.5 ms/chunk host cost (4 metadata copies + 4 trace replays + 4 syncs per iteration
on one Python thread) that a 4-process runner does not. Being a fixed offset, its relative size shrinks
with window: 34% at 5,120, 7% at 25,600, ~0% at 261,120. So `none` numbers *understate* PP=4 at short
context. `PP_HANDOFF=host` measured only its own D2H/H2D relay; real fabric is ~11 ms/hop.

Two facts worth not re-deriving:
- The TTNN weight cache path's device-count component (`..._{N}dev/{sp}x{tp}`) is **namespacing only** —
  `32dev/8x1` and `8dev/8x1` files are byte-identical, so caches can be hardlinked across it instead of
  rebuilt. Cache keys are *global* layer indices, so all PP ranks share one directory.
- A logical `[8,1]` column of the galaxy **spans two trays**, so its device set cannot come from tray or
  slice discovery; read it off a live 8x4 mesh with `create_submeshes(MeshShape(8,1))`.

**Where:** results + reproduction scripts + logs in
`~/debug-docs/mistral4_prefill_planning-noissue/perf/RESULTS_PP4_REAL_D2D.md` (and
`pp4_real_d2d_scripts/`); in-tree write-up is §10 of
`models/demos/deepseek_v3_d_p/docs/MISTRAL4_PREFILL_PERFORMANCE.md`. See
[[tt-galaxy-fabric-run-hygiene]].
