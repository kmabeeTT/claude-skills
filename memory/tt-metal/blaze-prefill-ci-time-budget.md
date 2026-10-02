---
name: blaze-prefill-ci-time-budget
description: "Adding any model leg to blaze-models-prefill-tests is gated by a nearly-exhausted (team, sku) time budget, not by the test code"
metadata: 
  node_type: memory
  type: project
  originSessionId: 23fe3dc2-d0c3-4ecc-9cb8-80454b8386e8
  modified: 2026-08-22T00:07:54.997Z
---

Adding a row to `tests/pipeline_reorg/blaze_models_prefill_tests.yaml` is gated by a shared time budget that is already almost fully consumed, so the binding constraint on a new model leg is budget, not test code. As of 2026-08-21 the matrix summed to **479 of 488 min** for `(models, bh_sc1)` and **166 of 166** for `(models, bh_sc1_high_power)` — i.e. 9 min of headroom on one SKU and zero on the other. The impl workflow runs `python3 .github/scripts/utils/verify_time_budget.py <matrix> .github/time_budget.yaml "demo"` under `set -e`, so an over-budget row fails the leg outright rather than just running long. Note the workflow name is **`demo`** (budget lives at `models: demo: bh_sc1` in `.github/time_budget.yaml`), which is not guessable from the pipeline's name.

**Why:** two people can each add a "small" 20-minute leg and the second one breaks CI for reasons that have nothing to do with their test. Raising `time_budget.yaml` is a cross-team ask (#tt-metal-infra), so it belongs in the plan up front, not discovered at review time.

**How to apply:** before promising a CI leg, run the three validators locally — `verify_time_budget.py` (workflow name `demo`), `validate_test_type_selection.py`, and `prepare_test_matrix.py` — since they are exactly what CI runs and they need no hardware. Size the timeout from a measured run rather than a guess, and if the budget bump is refused, quote the alternative: a tighter timeout that fits under the existing ceiling with less headroom. Related: [[mistral4-bringup-workspace]], [[mistral4-ci-staging-prereqs]].
