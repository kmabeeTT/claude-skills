---
name: mistral4-prefill-campaign-harness
description: The PP=4 prefill perf campaign driver lives on tt-metal-3 branch kmabee/mistral4-routing-capture, renamed from tests/perf/pp4
metadata:
  type: project
---

The `run_campaign.sh` driver that generates the three MISTRAL4_PP4 tables (throughput, warm latency, per-layer budget) is at `models/demos/deepseek_v3_d_p/tests/perf/pipeline_prefill_harness/` on **`/data/kmabee/tt-metal-3`, branch `kmabee/mistral4-routing-capture`**. It was **renamed from `tests/perf/pp4/`**, which is why the old shell-history path `tests/perf/pp4/run_campaign.sh` no longer resolves. Deliberately never merged ("working material, not proposed for merge", `d0972011a6f`), so it must be copied into whatever repo you are measuring and left untracked.

Its companion pytest `test_mistral4_profile_single_layer.py` IS committed, as `18cb77fdc1b`, and can be restored with `git show 18cb77fdc1b:<path>` from any repo whose object store has that branch.

**Durable archive (use this first): `~/debug-docs/mistral4_prefill_planning-noissue/perf/pp4_campaign_scripts/`** — harness, wrappers, host bindings and a tested `restore.sh <checkout>` that also recovers the pytest from `18cb77fdc1b`. It is an archive, not runnable in place: `env.sh` walks six levels up for `TT_METAL_HOME`.

**How to apply:** copy the harness dir in, restore the pytest, regenerate BOTH host bindings (the `_profile` one needs an explicit `--template` or it overwrites the e2e binding), then `run_campaign.sh --check`. Write run artifacts to `/data`, never the Claude `/tmp` scratchpad — it was deleted mid-run on 2026-09-14. See [[glx-hard-kill-needs-reset]].
