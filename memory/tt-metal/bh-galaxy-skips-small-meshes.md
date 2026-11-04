---
name: bh-galaxy-skips-small-meshes
description: "On a BH Galaxy, op tests parametrized with requires_mesh_topology 2x2/2x4 SKIP (\"Blackhole only supports 32-device mesh configs\"), so a \"passes on 1x1 and 2x2\" claim from a Galaxy run is really 1x1 only"
metadata:
  node_type: memory
  type: project
  originSessionId: f68b287c-f996-4c93-ad60-43f350bc893e
  modified: 2026-10-18T05:47:36.034Z
---

On bh-glx boxes, an op test's `pytest.param((2, 2) or (2, 4), marks=pytest.mark.requires_mesh_topology(...))` is SKIPPED with "Blackhole only supports 32-device mesh configs (requested 4/8)". Only 1x1 and 8x4 (and plain unmarked params some files use) actually run. Found 2026-10-18 on PR #61236: a reply claimed bit-exact "on both meshes" when 2x2 had skipped; corrected in a follow-up reply.

**Why:** pytest's summary line just says "N skipped", which reads like "shapes this box lacks" and hides that the multi-chip case never ran.

**How to apply:** before claiming a multi-chip result from a Galaxy op-test run, grep the log for `SKIPPED [` reasons (`-rs`). To get multi-chip coverage on a Galaxy, add an 8x4 param. Also check the CI selector: L2 `dp_op_unit_tests` (tests/pipeline_reorg/ops_unit_tests.yaml) keeps only `2x4` cases for `update_padded_kv_cache` / `rotary_embedding_indexed`, so a new test without a 2x4 id gets no CI. See CLAUDE.md ("never write PASSED until gh shows it").
