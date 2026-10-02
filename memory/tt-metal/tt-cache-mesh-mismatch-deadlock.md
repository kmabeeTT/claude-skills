---
name: tt-cache-mesh-mismatch-deadlock
description: "Before debugging any tt-metal model hang, verify the weight cache was built for the mesh you are running — a mismatched cache deadlocks silently and looks like a fabric/CCL bug"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 61e9cb32-a815-42b5-b7e2-d459066fef96
  modified: 2026-09-07T19:45:36.051Z
---

**When a tt-metal model hangs on a multi-device mesh, check the weight-cache provenance
BEFORE touching fabric, CCL, topology or geometry.** A tensor cache built on a different
MeshShape does not raise — it **deadlocks**, usually in the first decoder layer, and every
symptom points at the interconnect.

The trap in gemma4 (`Gemma4ModelArgs.weight_cache_path` ->
`_resolve_mesh_qualified_weight_cache`, `model_config.py:76`): the loader prefers
`tensor_cache_{dtype}_mesh{RxC}`, but if that dir is empty and the unqualified
`tensor_cache_{dtype}` is populated it **silently falls back** to the legacy one, warning only
"required if legacy was built for a different MeshShape". Shared caches under
`/mnt/models/huggingface/tt_cache/...` are exactly this hazard: they accumulate entries from
whatever mesh whoever ran them last used (e.g. a 1x4 QB2-era tp4 cache), and the TP tag in the
filename does **not** encode the mesh.

Three things that make it stick:
- `ttnn.as_tensor` loads an existing cache file and **ignores the torch tensor passed in**, so
  a "load the full weights" flag does not override stale entries — it only fills in missing ones.
- File sizes look right. A full-logical-tensor-sized `.tensorbin` tells you nothing about the
  per-device shard layout. Do not use size to argue a cache is mesh-independent (I did; it was
  wrong).
- Plain `ttnn.all_gather` / `all_reduce` pass on every mesh axis while the model hangs, so a
  green CCL probe is not evidence of anything.

**How to apply:** grep the run log for `tensor_cache_{dtype}_mesh{RxC}` matching your mesh and
for the absence of any "reusing legacy" line. Prefer a private `TT_CACHE_PATH` (e.g.
`/data/kmabee/hf_cache/tt_cache/<model>`) over a shared one, or set
`GEMMA4_WEIGHT_CACHE_MESH_ONLY=1` to force a mesh-qualified rebuild.

**Why:** this cost a full session and it has cost other people time too. The failure mode is a
hang with a completely plausible fabric signature (host parked in `all_reduce ->
reduce_scatter -> create_global_semaphore -> wait_for_outstanding_reads`, completion queue in
`completion_queue_wait_front`), so the natural reflex — sweep CCL topology, num_links, torus
descriptors, mesh transpose — burns hours and finds nothing, because all of them are innocent.

**Worked example (Gemma4, 2026-09-07; merged 2026-10-02 from `gemma4-prefill-cp8-hang`).** An earlier note claimed "CP=8 / 8x4 is broken on this box" — WRONG. A clean 8x4 run does 256k in **13.6 s device / 19.3k tok/s** (32 chunks, warmup 43 s, capture 2.2 s), faster than 4x8. On `/mnt/models/huggingface/tt_cache/google--gemma-4-31B-it` the only dirs were `tensor_cache_bf16` (legacy, 1x4/QB2-era tp4) and `tensor_cache_bf16_mesh1x4`; loading the legacy entries on 8x4 deadlocked layer 0's sliding attention after ~204 `program_compile_finished` (last program `bmm_large_block_zm_fused_bias_activation`). A whole session went into CCL topology, halo/slab geometry, mesh transpose, torus MGDs, `FABRIC_2D_TORUS_Y`, `GEMMA4_NUM_LINKS=1` and the Tracy build, all innocent. 4x8 only appeared to "work" because TP=8 had no cached entries, so its cache was built fresh on the 4x8 mesh. `GEMMA4_PREFILL_LOAD_FULL_WEIGHTS=1` does not save you (it only fills missing entries). Verify in the log: you want `tensor_cache_bf16_mesh8x4` and no "reusing legacy" line.

**Unrelated bug from the same session (may since be fixed):** `test_prefill_layer_perf_chunk_n` failed at HEAD on both meshes and both layer types, ~60 s in, with `prefill.py:452 RuntimeError: packed {sliding,global} ring attention requires pre-gathered ... RoPE tensors` — the packed-KV commits build `packed_global_rope`/`packed_sliding_rope` inside `Gemma4Model.__call__`, and the test's `_make_forward` hand-mirrors the layer loop without the packing step.

See [[gemma4-prefill-box-setup]] for the box paths.
