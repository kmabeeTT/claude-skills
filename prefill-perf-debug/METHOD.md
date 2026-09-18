# The method, and the traps behind each assertion

The procedure is in [`SKILL.md`](SKILL.md). This file is *why* — the incidents that each
assertion exists to prevent, and the teaching-mode material. An assertion whose reason
has been forgotten gets deleted the first time it is inconvenient.

Source: the Gemma4-31B prefill chunk-size investigation, 2026-09. Full record in the
tt-metal tree at `tech_reports/Gemma4PrefillChunkSize/` (`README.md`,
`CHUNK_SIZE_ANATOMY.md`, `PER_OP_TABLES.md`) on branch `kmabee/gemma4-swa-multihop-halo`.

---

## The two-term model

Prefill time splits exactly into a cost paid once per chunk and a cost that grows with
how much context precedes each chunk:

```
t_i = a(C) + slope(C)·i                     per-chunk device time at chunk index i
T(ISL, C) = N·a(C) + slope(C)·N(N−1)/2      N = ISL/C
```

`a` **is** TTFT. `slope` is what kills long-context throughput. On Gemma4 the fit gives
R² ≥ 0.9996 from a single `ctx_32k` run per chunk size, and extrapolates to 256k within
1% of independent 256k runs. **No profiler is involved**, which is why it is the
instrument of record and why every deeper level has to close against it.

Two independent effects, in different layers, needing different fixes:

| | 2048 vs 8192 | cause | whose |
|---|---|---|---|
| **per-chunk term** | **2.16x** | a ~94 ms cost that does not shrink with the chunk, paid 4x more often | ~83–85% the **50 sliding** layers, *by count* |
| **prefix term** | **1.99x** | the attention op leaves **71% of the grid idle** at chunk 2048 and pays 4x as many steps | **100%** the **10 full-attention** layers |
| | **= 2.09x** | | |

Neither is the sliding-window halo, and neither is the fabric.

## Why Tracy is used only for "which op", never "why"

Its utilization columns (`NOC UTIL`, `DRAM BW UTIL`, `ETH BW UTIL`,
`DEVICE COMPUTE CB WAIT FRONT`) are **entirely empty on this path**: they need
`--analyze-noc-traces` plus a built tt-npe, and `ETH BW UTIL` is *modelled* from NoC
event traces even then. Every mechanism finding in the investigation came from causal
ablations instead. A profiler tells you where the time is; only an ablation tells you
what it is.

---

## A1 — refuse "bound by X" unless an ablation varied X

**What happened.** The global attention op's FLOPs, priced at the same-layer matmul's
per-core rate, "should" have taken 17.57 ms; it took 37.22 ms; the residual 53% was
attributed to fabric movement. **Retracted.**

Three things were wrong. Anchoring on a matmul rate and attributing the residual to
fabric assumes nothing else can starve the math — but the op was running 128 work units
on 110 cores at depth 2, so ~42% of core-time was *structurally* idle before any byte
moved. The two "independent" estimates were calibrated on the same pair of chunk sizes.
And the profiler could not settle it, because of the empty columns above.

**What actually answered it**, once each knob was varied one at a time:

| vary | changes | measured | conclusion |
|---|---|---:|---|
| K/V dtype bfp8→bfp4 | halves **bytes** | 0.998x | not byte-bandwidth-bound |
| `exp_approx_mode` | softmax exp path | 1.007x | softmax negligible |
| fidelity HiFi2→LoFi | halves **MAC passes** | 0.786x | MAC-bound |
| fidelity HiFi2→HiFi4 | doubles MAC passes | 1.755x | same, and HiFi4 is strictly dominated |
| `k_chunk` 256→128 | inner-loop blocking | 1.156x worse | 256 already optimal; 512 overflows L1 |

**Scope discipline.** bfp4 halves bytes but not tile count, so it refutes *byte-bandwidth*
bound, not per-tile overhead. Only the fidelity response positively rules math **in**.
And no precise MAC percentage is claimed: fitting `time = passes·k + c` gives 43% on the
(LoFi, HiFi2) pair and 76% on (HiFi2, HiFi4). The two disagree, so the relationship is
not linear in fidelity passes and a single share would repeat the same two-point-model
error.

## A2 — `Total %` and `Op-to-Op Gap` are unusable on these captures

Each trace replay's first op carries a host-side gap measured from *before* the signpost
— **1,121,464 µs** in one capture, against a median of 0.53 µs everywhere else. It
swamps the percentage column: the 8.27 ms SDPA, the single most expensive op in the
capture, is shown as **`0.7 %`**. Use `Device Time`. The skill's per-op code never sums
`Total %` at all.

## A3 — `Cores` is grid size, not occupancy

The global SDPA reports **114 cores at every chunk size**, including chunk 2048 where
only 32 of ~110 cores hold a work unit. `ring_joint_sdpa_program_factory.cpp` splits work
into `q_chunk_size`-row × one-head units, `div_up`s them over the grid, and **does not
skip cores without a unit** — they run padded handshake iterations, so every core loops
`max_q_per_core` times.

| chunk | q chunks | work units | depth | slots | useful | `Cores` reports |
|---:|---:|---:|---:|---:|---:|---:|
| 2048 | 4 | 32 | 1 | 110 | **29%** | 114 |
| 4096 | 8 | 64 | 1 | 110 | 58% | 114 |
| 8192 | 16 | 128 | 2 | 220 | 58% | 114 |
| 16384 | 32 | 256 | 3 | 330 | 78% | 114 |
| 32768 | 64 | 512 | 5 | 550 | 93% | 114 |

Occupancy has to be computed from the op's own work-unit math. The skill does that from
the profile's `growing_op.occupancy` block and prints both numbers side by side.

## A5 — never `--device-trace-profiler`

It profiles only trace regions, empties `OP NAME`, and kills post-processing with
`AssertionError: Device data missing`.

## A6 / A12 — re-render both sides, from raw, with one tool

**What happened.** A cross-branch check reported the sliding SDPA moving 0.38 → 0.46 ms
(**+21%**) and concluded the multi-hop halo had cost the sliding path. It had compared a
**published table value** against a freshly rendered `tt-perf-report` number. Re-deriving
the *same capture* with the same tool gives 0.447 ms — a **+1.9%** delta.

The per-device spread is what makes this easy to get wrong. For one op across the 32
devices:

```
min 382.9 µs | median 434.5 µs | device 0 394.0 µs | max 446.8 µs      spread 17%
```

`tt-perf-report` merges devices and reports the **slowest**. The 17% spread is the same
size as the effects being chased, so a figure lifted from someone's summary table can
manufacture or hide a regression on its own.

A12 is the same trap across builds. "`rms_norm` is exactly chunk-invariant" — once the
most solid-looking number in the investigation — came from comparing a 2026-09-09 capture
against a later branch, where the **same** norm on the **same** shape and core count took
99.3 µs instead of 134.2 µs. Same-branch it is 1.22x, not 0.98x. A same-shape,
same-core-count op is **not** a safe cross-build anchor.

## A7 / A8 — a prediction written first, and a control

These two are why the occupancy result means anything.

**A7, the prediction, recorded before the captures finished:** at matched prior context
the prefix work is proportional to chunk tokens, so chunk 2048 does exactly 0.25x the
work of 8192. An efficiency-neutral op predicts **0.25x** the time. The occupancy model
(cost ∝ depth) predicts **0.50x**. Measured: **0.443x** — a 1.77x efficiency loss.
Falsifiable, and it survived.

Note which pair can discriminate — and this was got backwards in the first writeup.
The grid passes are 1 / 1 / 2 at 2048 / 4096 / 8192, so:

| pair | neutral predicts | occupancy predicts | verdict |
|---|---|---|---|
| 2048 vs 8192 | 0.250 | 0.500 | discriminates |
| 4096 vs 8192 | 0.500 | 0.500 | **blind — this is the useless pair** |
| 2048 vs 4096 | 0.500 | **1.000** | **discriminates hardest** |

Two equal-pass chunk sizes should cost the *same*, not half as much, so 2048-vs-4096
coming in at **0.956x** was the single strongest piece of evidence for occupancy and was
originally dismissed as uninformative. A blind re-run on 2026-09-18 measured the same
pair at **0.9997x** on depth-subtracted growth. Always derive the predicted ratio for
every pair from the work-unit math before choosing the capture matrix.

**A8, the control:** the sliding layer being flat to **+0.2% / +0.8% / −0.1%** across a
prior context of 0 → 49,152 tokens is what made the global layer's +119% credible rather
than a harness artifact.

## A9 — match prior context, not chunk index

Chunk index 7 is 57k of history at chunk 8192 and 14k at 2048. Comparing at a fixed index
compares different amounts of prefix work. All the per-op comparisons use a prior context
of **49,152 tokens**: `sz8192` idx 6, `sz4096` idx 12, `sz2048` idx 24, each confirmed by
the harness' own `kv_actual_global`. That is what turns a comparison into a test with a
predicted number.

## A10 — close against level 0, and state the residual

Per-op sums **overstate**: the isolated-layer harness has no inter-layer overlap and pays
staging ops the real model pays once per chunk. Measured inflation is ~1.13–1.15x on
Gemma4 (the skill's reconciliation reports +12.9% / +15.0% / +14.0% at chunk
2048 / 4096 / 8192). Use isolated-layer numbers for **attribution and ratios**, not
absolute totals — and print the residual rather than hiding it.

The prefix side closes much tighter: the growing op's growth per chunk-index × 10 global
layers reproduces the whole-model slope to **−0.6% / +1.1% / −3.0%**.

## A11 — two different numbers, both called "the floor"

For `cost = F + k·tokens` compared at a chunk-size ratio r, the *excess over ideal token
scaling* is

```
a(C) − a(rC)/r = (1 − 1/r)·F           at r = 4:  excess = ¾·F
```

The Gemma4 floor was published as **~70 ms**. That is the excess. The **chunk-invariant
cost is ~94 ms**. They differ by 4/3, and quoting one as the other is a 33% error.

A further caveat the skill enforces by reporting the spread: `a(C)` is **concave**, not
affine. Solving the intercept on (2048,4096) versus (4096,8192) disagrees by 39% for
Matmul, 39% for the SDPA and 17% for LayerNorm — and Matmul's (4096,8192) intercept even
*exceeds* its total measured cost at chunk 2048, which is impossible for a real fixed
component. **Never extrapolate a fitted cost model outside its fitted range**, and prefer
the in-range excess measure.

The skill reports the floor attribution three ways — in-range excess, an affine fit of
the layer total, and the published per-op clamped fit — because their agreement (82.8% /
84.8% / 85.0% on Gemma4) *is* the evidence. None is authoritative alone.

---

## Teaching mode: the three failures worth telling

1. **The false +21% regression** (A6). A number lifted from a writeup, compared against a
   freshly rendered one. The real delta was +1.9%, and the 17% per-device spread on that
   op is larger than either.
2. **The retracted fabric conclusion** (A1). A FLOP-rate mismatch has many causes. Here
   most of it was structural core idleness, which the same profiler could have shown and
   the "fabric" story never tested.
3. **Two numbers both called "the floor"** (A11). 70 ms and 94 ms, differing by exactly
   4/3, one of them published as the other.

A fourth, smaller, worth knowing: a retracted **"69% movement / 31% math"** split, from
fitting a two-term model to an ablation that changed two things at once. The chunk-2048
`q_chunk` ablation moved rows/core *and* `q_chunk` together; the chunk-8192 one held
rows/core fixed and is the better design. Only the second licenses a number
(per-unit overhead ≈ 17% of the op).

**The general lesson in one line:** the failures all came from comparing two things that
differed in more than one way. Every assertion here is a way of noticing that before
publishing.

---

## Cross-validation is the point

On Gemma4 the floor was reached three independent ways — whole-model fit, layer-count
differencing, per-op summation — agreeing to **0.3%**. "The prefix term is 100% global
layers" was confirmed three ways — depth curves, per-op capture, layer-count differencing
— agreeing to **0.6–3.4%**. One measurement is an anecdote; the report should say how
many ways each claim was reached.
