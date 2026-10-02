---
name: host-only-model-tests-have-no-ci-home
description: "models/demos/deepseek_v3_d_p/tests/torch/ is in zero CI rows, and the models team has no CPU budget grant, so host-only tests cannot be gated as-is"
metadata:
  node_type: memory
  type: project
---

`models/demos/deepseek_v3_d_p/tests/torch/` appears in **zero** pipeline or workflow files — the deepseek legs name specific dirs (`tests/pcc/`, `tests/op_unit_tests/`, `tests/cache/`, `tests/perf/`) and never that one. Four files predate any of my PRs (three from Marko Bezulj 2026-03-24, one from Iva Potkonjak 2026-08-11), so ungated host-only tests are established practice here, not an oversight I introduced. Repo-wide, roughly 796 of 1,534 `test_*.py` under `models/` are unreachable from any CI pytest path (prefix-match estimate, so approximate).

The reason it cannot simply be fixed: in `.github/time_budget.yaml`, **`scaleout` is the only team with a CPU grant** (`merge_gate.cpu_medium=10`, `unit.cpu_medium=235`). All eleven other teams, `models` included, have none — so there is no budget line for a CPU-only leg for a `team: models` test, even though the mechanism (`cpu_medium` + `tests/pipeline_reorg/fabric_cpu_only_unit_tests.yaml`) exists.

**Why:** reviewers ask "is there a point in these tests if we don't run them?" on essentially every host-only test file — it came up on both #54526 (nbabinTT) and #54529 (pavlepopovic) within days. The answer needs the precedent *and* the budget blocker, or it reads as an excuse.

**How to apply:** don't promise to gate a host-only test without checking the team's CPU grant first. The cheap route that needs no budget bump is to hang the file off a leg that already boots a device — a no-device test rides along for milliseconds. Related: [[blaze-prefill-ci-time-budget]], [[mistral4-branch-suites]].
