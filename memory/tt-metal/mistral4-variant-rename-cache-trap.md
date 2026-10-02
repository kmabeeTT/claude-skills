---
name: mistral4-variant-rename-cache-trap
description: "The shared mistral4 branch renamed the variant to mistral_small_4, which orphans every weight cache built by the -full branch"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4a32c6c7-bb91-4128-8043-4f1a02a525bc
  modified: 2026-08-28T15:48:01.880Z
---

The two Mistral Small 4 branch lineages spell the variant differently, and the weight-cache directory is keyed on that spelling:

- `kmabee/mistral4-prefill-full*` (Kyle's PP/perf line): variant `mistral_small4`, config module `reference/mistral_small4_config.py`
- `kmabee/mistral4-prefill-base` (the shared/Alina line, rebased 2026-08-28): variant `mistral_small_4`, config module `reference/mistral_small_4_config.py`

The cache path is `$TT_MISTRAL4_PREFILL_TTNN_CACHE/{adapter.name}_{arch}_{N}dev/{sp}x{tp}` (`tt/runners/adapters/mla.py:85`, `arch="bh"`). So every cache under `/data/kmabee/mistral4_caches/` — all built as `mistral_small4_bh_32dev` — is **invisible to the shared branch**, which looks for `mistral_small_4_bh_32dev`. The failure mode is not an error: the pretrained rows just start rebuilding 65 GB of weights (hours), or a completeness assert fires.

**Fix, already applied:** a symlink per cache root, e.g. `ln -s mistral_small4_bh_32dev /data/kmabee/mistral4_caches/ttnn_cache_pp/mistral_small_4_bh_32dev`. Safe because the cache is content-addressed — the files are `layer_10.mla.kv_a_proj_..._dtype_BFLOAT8_B_layout_TILE.tensorbin`, with no manifest and nothing keyed by variant name. Links exist now in `ttnn_cache_8x4`, `ttnn_cache_pp` and `ttnn_cache_stage`.

Same rename breaks the untracked scratch files `demo/dump_mistral4_prefill_kv.py` and `tests/perf/test_mistral4_profile_single_layer.py` at import time when they sit in a shared-branch worktree — they hardcode the old module path and variant string.

**Why:** the cache is 65-213 GB and takes hours to build; silently rebuilding it looks like "the test is just slow" rather than a path mismatch, and switching between the two branch lineages is routine.

**How to apply:** after any branch switch between the two lineages, check `find -L $CACHE/<variant>_bh_32dev/8x4 -name '*.tensorbin' | wc -l` resolves to ~975 before trusting a pretrained row's runtime. See [[mistral4-bringup-workspace]] and [[mistral4-branch-suites]].
