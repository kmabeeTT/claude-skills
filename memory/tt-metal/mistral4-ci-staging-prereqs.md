---
name: mistral4-ci-staging-prereqs
description: "Which Mistral Small 4 prefill CI legs are self-contained vs blocked on /mnt staging, and where the staged MLA reference cache lives"
metadata: 
  node_type: memory
  type: project
  originSessionId: 23fe3dc2-d0c3-4ecc-9cb8-80454b8386e8
  modified: 2026-08-22T00:08:09.008Z
---

For Mistral Small 4 119B prefill, whether a Blaze CI leg is addable depends on whether it needs staged artifacts, and only the MoE module leg does not:

- **MoE module (`test_mistral4_moe`) — self-contained.** Reference is the upstream `Mistral4MoE` loaded from the same seeded draw as the device weights, the config is hand-built by `mistral4_hf_config` (no HF download), the golden-trace input path is gated on DeepSeek's 7168 hidden dim so Mistral falls through to synthetic input, and the weight cache is rebuilt in-run. Measured 3 min 41 s warm / ~6 min cold on torus-xy-8x4.
- **MLA module — blocked on a reference cache.** `test_mla` *asserts* `"We should not execute CPU computation in the CI for max sl, output cache is missing"`, and `scale_down_sl` is a no-op on the production 8x4 mesh (`seq_len = (seq_len // production_mesh[sp]) * mesh_shape[sp]`), so there is no CI-safe way to compute the CPU reference in-run. Needs `MISTRAL4_MLA_REF_CACHE` pointed at a staged directory, the way Kimi's row points at `/mnt/models/kimi-prefill-cache/test_mla_output`.
- **Prefill block on real weights — blocked on checkpoint + TTNN weight cache on `/mnt`.** No Mistral cache exists there.

The MLA reference artifact is **already generated**: `random_seq5120.pt` (45 MB) and `random_seq25600.pt` (226 MB), staged durably at `/data/kmabee/mistral4_mla_ref_cache/` (copied 2026-08-22 from `/tmp/mistral_small4_mla_ref_cache/`, md5-verified). The cache filename is `{weight_type}_seq{seq_len}.pt` with no mesh or fabric in the key, so one copy serves every mesh shape.

**Why:** a leg whose artifacts are missing does not fail loudly — fabric/mesh and missing-trace cases SKIP with rc=0, which reads as a pass. Adding such a row costs signal instead of adding coverage, so the staging state has to be settled before the row is written.

**How to apply:** propose only the self-contained leg first; for the others, hand over the artifact path plus a "copy this to /mnt" ask rather than a row that cannot run. Related: [[blaze-prefill-ci-time-budget]], [[mistral4-bringup-workspace]].
