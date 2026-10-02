---
name: mistral4-branch-suites
description: "Which Mistral Small 4 runner script goes with which branch lineage, and what test coverage each branch actually has"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4a32c6c7-bb91-4128-8043-4f1a02a525bc
  modified: 2026-08-28T15:48:18.083Z
---

Two Mistral Small 4 branch lineages with **different test inventories** — a runner written for one produces misleading results on the other.

| | `kmabee/mistral4-prefill-full*` | `kmabee/mistral4-prefill-base` (shared) |
|---|---|---|
| runner | `/data/kmabee/run_mistral4_suite.sh`, `/data/kmabee/run_pp4_256k.sh` | `/data/kmabee/run_mistral4_base_suite.sh` |
| PP / e2e tier | yes (`test_prefill_pipeline_stages.py`, `test_prefill_pipeline_concurrent.py`) | **absent** — no PP_* env, no throughput numbers |
| perf tier | yes | **absent** |
| host fixes test | `tests/torch/test_shared_prefill_fixes.py` | split into `test_mla_matmul_configs.py`, `test_prefill_layer_kwargs.py`, `test_reference_rope.py` |

The shared branch tops out at the full transformer plus chunked prefill. Seven of its rows are wired to the Blaze CI leg (`tests/pipeline_reorg/blaze_models_prefill_tests.yaml`) — that set is the authoritative known-good baseline, and the base-suite script mirrors its `-k` expressions.

Three gotchas the base-suite script encodes, all of which silently produce wrong results rather than errors:

1. **`pytest.ini` sets a global `timeout = 300`.** Only tests carrying their own `@pytest.mark.timeout` escape it. Pass `--timeout=0` and bound the stage with a shell `timeout` instead.
2. **Never set `PREFILL_TORUS_XY_CERTIFIED` locally.** `tests/conftest.py` gates the torus skip on `on_ci and cluster_type in [GALAXY,...]`; off CI, `torus_xy` rows run under mesh auto-discovery and pass. Setting the flag additionally *requires* `TT_MESH_GRAPH_DESC_PATH` or conftest calls `pytest.exit(rc=2)`.
3. **The root `tt_telemetry_server` holds all 32 chips permanently.** Any `fuser`-based "devices must be free" preflight fails 100% of the time; filter root-owned `tt_telemetry_*` holders. See [[device-usage-visibility]].

A stage that collects zero cases must be reported as its own verdict, never as PASS — with this much mesh/variant gating that is the most likely way a broken tree looks green. `test_prefill_combine.py`'s mistral4 row is QuietBox-only (`ONLY_PROXY_QB_MESH = {(2,2)}`) and can never run on a 32-chip Galaxy.

**Why:** running the -full suite against the shared branch yields a wall of missing-file errors, and the reverse quietly under-tests.

**How to apply:** pick the runner by branch. See [[mistral4-variant-rename-cache-trap]] for the weight-cache symlink that both lineages now need, and [[mistral4-bringup-workspace]] for paths.
