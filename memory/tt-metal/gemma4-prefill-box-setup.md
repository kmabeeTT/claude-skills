---
name: gemma4-prefill-box-setup
description: "Where gemma4-4-31B weights and the TP-tagged tt_cache live on the bh-glx boxes, and the env that makes Sasha's prefill test run"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 61e9cb32-a815-42b5-b7e2-d459066fef96
  modified: 2026-09-06T04:10:28.597Z
---

Sasha's gemma4 commands use `/localdev/svuckovic/huggingface`, which **does not exist** on
the bh-glx boxes. The local equivalents:

```
HF_HOME=/mnt/models/huggingface            # hub/models--google--gemma-4-31B-it (62 GB, 2 safetensors)
TT_CACHE_PATH=/mnt/models/huggingface/tt_cache/google--gemma-4-31B-it
HF_HUB_OFFLINE=1
```

`/mnt/models/...tt_cache/...` is **group-writable** and shared. `weight_cache_path()` looks
for `tensor_cache_bf16_mesh<RxC>` first; if that is empty it warns and silently falls back to the
legacy `tensor_cache_bf16`. **Do not rely on that fallback** (corrected 2026-09-07): the legacy dir
there is a 1x4-era tp4 cache, and reusing it on an 8x4 mesh HANGS the model. File size does not
capture the per-device shard layout; only the **TP factor** is in the filename (`_tp4_` / `_tp8_`),
not the mesh. Use a cache whose `..._mesh{RxC}` dir matches the mesh; see
[[tt-cache-mesh-mismatch-deadlock]].

- A run on a mesh whose cache entries are missing needs `GEMMA4_PREFILL_LOAD_FULL_WEIGHTS=1`
  once (~6-9 min, reads 62 GB over NFS and writes the cache); afterwards ~45 s from cache.
- As of 2026-09-06 both `_tp4_` (8x4) and `_tp8_` (4x8) were populated there, including the
  branch's `wqk_packed640_*` tied-QKV entries.

**Why:** the paths in the shared snippet look authoritative but are another user's local
disk, and the "incomplete cache" skip message sends you toward rebuilding a 219 GB cache
that already exists.

**How to apply:** export the three vars above (but prefer a private, mesh-matched `TT_CACHE_PATH` such as `/data/kmabee/hf_cache/tt_cache/<model>` over the shared `/mnt` one), drop `HF_HUB_OFFLINE` only if you need a
download. Always background device runs and reset after a hard kill — see
[[tt-galaxy-fabric-run-hygiene]]. For which mesh actually works, see
[[tt-cache-mesh-mismatch-deadlock]]. If `python_env/bin/python` dangles, see
[[data-checkout-venv-home-pin]].
