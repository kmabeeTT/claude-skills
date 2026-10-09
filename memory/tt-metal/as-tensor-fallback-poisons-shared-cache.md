---
name: as-tensor-fallback-poisons-shared-cache
description: A failed cache load on the warm path makes ttnn.as_tensor rewrite the shared .tensorbin from a torch.empty placeholder (all zeros); how to find and restore one
metadata:
  type: reference
---

On a warm weight cache, the state dict holds `torch.empty` placeholders (`CachedStateDict`). If `load_tensor_flatbuffer` raises, `ttnn.as_tensor` logs only `Failed to load cache for ...` and dumps the placeholder over the cache file: valid header, all-zero payload. A truncated file does NOT take this path (it loads garbage silently). The 2026-10-08 Blaze Gemma4 KV PCC failure (#60134, 0.9219 on every branch) was layer_15/mlp/gate_proj in the /mnt/models CI cache; restored 2026-10-09, zeroed backup in /data/kmabee/gemma4_ci_cache_backup_1009.

- Detect: a zero-scan of 64 KB blocks at 1/4, 1/2, 3/4 and the end of each .tensorbin; one bad layer shows as per-layer KV PCC falling off at the NEXT layer.
- Restore with exact bytes: the payload is deterministic across builds (same tail md5 in CI, Weka and /data caches); the header changed in #56434 (2026-09-15) but is weight-independent within one cache, so splice a same-shape sibling's header (first 3006 B for Gemma4 tp4 MLP) + the payload. The `.weights_complete.*` marker lists names only, so a swap triggers no rebuild. Swap via temp name without `.tensorbin` + mv.
- kmabee is in group tt-cache: a symlink overlay of a shared cache can write through. Copy instead (36 GB, ~1 min).
