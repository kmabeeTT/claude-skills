---
name: tt-metal-test-command-ci-selector
description: "tt-metal has a /test PR-comment command (.github/workflows/test-command.md) that picks CI pipelines from the diff; it documents which workflow covers what, incl. mandatory L2 nightly categories"
metadata:
  node_type: memory
  type: reference
  originSessionId: 5ecff3cb-0b03-4794-9f83-de74c864ae69
  modified: 2026-10-02T19:08:29.150Z
---

`.github/workflows/test-command.md` in tenstorrent/tt-metal defines **`/test`**: comment it on a PR and an agent reads the
diff and dispatches only the matching optional pipelines (max 8) against the PR branch, then posts one summary comment.
It needs write/maintain/admin rights on the repo. A hint narrows hardware, e.g. `/test blackhole`.

The file also works as the best map of which CI covers what:
- **`Nightly tt-metal L2 tests` is mandatory** for any change under `ttnn/cpp/ttnn/operations/<family>/**` or its tests.
  Pass `additional_test_categories` comma-joined, e.g. `eltwise,matmul`. Families: eltwise, data_movement, conv,
  matmul, pool, reduction, fused, transformers, sdpa, ccl, moreh, experimental, misc, kernel_lib. These suites run on
  **WH + BH**, are not covered by pr-gate or post-commit, and their source of truth is
  `tests/pipeline_reorg/ops_unit_tests.yaml`. Its `run_wormhole` / `run_blackhole` inputs default to true.
- **`Sanity tests`** (WH + BH + simulator) bundles 9 suites: ttnn, ops, fabric, t3000, umd, ttsim, BH multi-card,
  models, and LLK (opt-in, `run-llk-sanity-tests` only for `tt_metal/tt-llk/**`). Select only the relevant suites.
- Other selectable pipelines: blackhole-e2e, galaxy-sanity / galaxy-tests, t3000-tests, models-t1/t2/t3 (need `model`),
  perf-device-models, ttnn-run-sweeps, runtime-*.

**How to apply:** when recommending or dispatching CI for a tt-metal op change, read this file (and
`ops_unit_tests.yaml`) first. It is the most direct way to get a Wormhole run of an op test from a BH-only box, and
`/test` can be suggested to the user as the low-effort route. 
**Trap: a plain L2 dispatch runs no tests and still goes green** (merged 2026-10-02 from tt-metal-3's `l2-nightly-dispatch-runs-no-tests`). `gh workflow run tt-metal-l2-nightly.yaml --ref <branch>` with no inputs builds and runs triage, but all 20 test jobs (ops-unit-tests, ttnn-integration-tests, ...) are skipped: their `if:` needs a schedule event, `additional_test_categories != ''`, `run_cpp_tests` or `run_ccl_tests`. The run still concludes "success" in ~30 min. Seen 2026-09-26 on run 36221370589, and #57979's cited PASS 36176239947 was such a hollow green. For SDPA/CCL op PRs dispatch with `-f additional_test_categories=sdpa,transformers -f run_ccl_tests=true` (plus any other touched categories), and before writing PASSED count job conclusions, not the run's: `gh run view <id> --json jobs --jq '.jobs | group_by(.conclusion)[] | "\(.[0].conclusion): \(length)"'`.

Related: [[tt-metal-push-routes]], [[ci-status-only-when-verified]], [[merge-gate-gcc12-sweep]].
