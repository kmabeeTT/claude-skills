---
name: pp4-latency-metric-contaminated
description: "Every PP=4 single-request latency/TTFT number before 2026-09-14 is wrong: E2E_CLOCK includes trace capture at the head and the shutdown drain at the tail, both asymmetric between topologies"
metadata:
  node_type: memory
  type: project
  modified: 2026-09-15T00:00:00.000Z
---

The PP=4 latency metric is the interval between the two `E2E_CLOCK` fields in
`models/demos/common/prefill/runners/prefill_runner.py` (shared by Gemma4 and Mistral 4 Small), and
**both endpoints are wrong**:

* **Head** — `first_compute_start` is `t_start` at `_compute_and_send:310`, taken *before*
  `runtime.prefill_chunk:314`, which captures the trace on its first call. Cost ~**4.0 s on
  single-rank vs ~0.14 s per PP stage** (Mistral: 36 layers in one process vs 9 per stage,
  captured concurrently) — a ~30x asymmetry *in PP=4's favour*.
* **Tail** — `last_compute_end` is stamped at `_drain_and_log_e2e:352`, called at `:397`, i.e. after
  `_forward_shutdown:389` plus `wait_for_fabric_links()` + `synchronize_device()`. 5.6 s / 374 ms /
  200 ms at 1 / 51 / 20 chunks.

Worse: **the code never records when the last chunk finished.** `_compute_and_send` returns the
chunk's *start*; `_record_chunk_timing` only fires under `SYNC_PER_CHUNK`, which perf runs do not set
because it disables overlap. So per-chunk intervals come from differencing `CHUNK_START` stamps —
N−1 intervals for N chunks — and a single-chunk ISL cannot be measured at all.

Consequence: the published "PP=4 wins latency by 2.86x" (`MISTRAL4_PP4_BRINGUP_RERUN.md` §1.2) is
substantially the capture asymmetry. `RESULTS_PP4_RERUN_2026-09-14.md` §1.2b found and decomposed
it; ex-capture the ratios are 0.69x / 1.10x / 1.15x and **the conclusion inverts at short context**.

Three independent estimates agree that PP=4 only beats single-rank on single-request latency above
**~7 chunks** (Gemma4: 7 chunks / 57,344 tokens, simulated from measured per-chunk stage CSVs). At
one chunk PP=4 is ~2.6x *slower*.

The root misconception: "each PP=4 [8,1] stage runs 1/4 the time of the full model". False — PP=4
gives each chip 1/4 the layers but 4x the width per layer (TP 4->1), so **per-chip work is
conserved**, which is why the change is memory-neutral. A stage measures 0.72x the full model per
chunk, and the whole gain is TP collectives being dropped.

**Why:** throughput numbers survived three re-derivations, so latency felt equally safe; it was not,
and the error flatters PP=4 in exactly the direction people wanted to believe.

**How to apply:** never quote a PP latency/TTFT figure without an ISL attached and without checking
it came from a process-warm request (request 2 of 2 in ONE process — running the cell twice does not
help, each run re-captures). Fix plan and gates: `~/debug-docs/pp4/HANDOFF_NEW_CAMPAIGN.md`; doc
trust table: `~/debug-docs/pp4/PROVENANCE.md`. Do NOT assert that PP's implied ms/chunk (latency/N)
is monotonic in ISL — it legitimately dips (fill/N decays), so that check false-positives on clean
data. See [[pp4-perf-harness-traps]], [[gemma4-pp4-scoping]].
