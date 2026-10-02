---
name: gemma4-prefill-chunk-size-win
description: Gemma4 CP prefill chunk size trades TTFT against throughput; 32768 is the 256k throughput optimum, 4096 the best single setting; fitted cost models must not be extrapolated
metadata:
  type: project
---

Gemma4 256k CP prefill on a BH galaxy (measured 2026-09-09, branch
`svuckovic/gemma4-prefill-model` / PR #55748, 8x4): **chunk 8192 -> 32768 is +24.3% tok/s
(13.63 s -> 10.96 s) with no code change.** Holds at every context: +14.4% (32k), +18.3%
(64k), +20.9% (128k). 4x8 gains +18.5% too, so it is not mesh-specific.

**Why:** a global (full-attention) layer ring-gathers the *entire valid prefix* of K/V once
per chunk. That cost tracks the **prefix, not the chunk**, so a bigger chunk amortises it over
more tokens while attention FLOPs stay fixed. The gather is **fused inside
`RingJointSDPADeviceOperation`** — there is no separate AllGather op to point at, so op-name
attribution cannot see it; only cost-scaling across chunk sizes can.

Cost model `T(n,C) = (rho*C^2 + alpha*C + K) + n*(beta*C^2 + gamma*C)` fitted at 256k predicts
32k-256k and the chunk-65536 *reversal* to <2.3%. `rho` is intra-chunk causal self-attention,
O(C^2), which creates a real optimum: **~34k tokens at 256k, so 32768 is the practical best.**
Chunk can never equal context (single chunk TT_FATALs), so max usable is L/2.

**The other end (measured 2026-09-16, 8x4, one ctx-32k sweep).** Chunk 0's device time IS the
TTFT for any prompt that fits one chunk, and per-chunk times are linear in chunk index, so ONE
ctx-32k run per chunk size gives both coefficients and extrapolates 256k to <1%:
2048 -> 131.3 ms TTFT / 28.66 s at 256k; 4096 -> 174.2 / 17.19; 8192 -> 242.7 / 13.71;
16384 -> 443.7 / 11.55; 32768 -> 928.2 / 10.96. As a SOLE deployed setting the worst-case ratio
to the per-ISL best is 1.61x for 4096, 1.85x for 8192, 2.61x for 2048 — **4096 is the best single
setting**, 32768 is the throughput optimum. Chunks below 8192 need a multi-hop sliding-window halo,
which costs only ~4-5 ms; what makes small chunks inefficient is a **~69 ms fixed per-chunk floor**.

**Do NOT extrapolate the fitted cost model outside its fitted range.** It interpolates 32k-256k
well, but evaluating a fit built on chunks 8192-32768 down at 2048-4096 mispredicted by ~13 ms and
produced two confidently wrong conclusions in one session. Measuring all five chunk sizes takes
9m53s; do that instead.

**How to apply:** when tuning Gemma4 prefill throughput, set chunk before touching anything
else. Full record, scripts and per-op tables in
`~/debug-docs/gemma4_prefill_chunk_scaling-noissue/`; the TTFT/small-chunk side and the multi-hop
halo in `~/debug-docs/gemma4_swa_multihop_halo-noissue/`. See [[tracy-device-trace-profiler-trap]],
[[ccl-one-worker-per-link-and-semaphore]].

**CORRECTION 2026-09-18: the 16384 and 32768 numbers above came from too few fit points and
are superseded.** The whole table was fitted from a single **ctx_32k** sweep, where N per
chunk is 16 / 8 / 4 / **2** / **1**. A slope cannot be fitted from N=1 at all, and N=2 is
exactly-determined and fragile. Direct **ctx_256k** runs on `kmabee/gemma4-swa-multihop-halo`
give:

| chunk | published a / slope / T(256k) | **measured a / slope / T(256k)** | N, R² |
|---|---|---|---|
| 16384 | 443.7 / 37.100 / 11.55 s | **436.2 / 40.33 / 11.82 s** | 16, 0.99960 |
| 32768 | 928.2 / 126.2 / 10.96 s | **917.9 / 140.69 / 11.28 s** | 8, 0.99962 |

**Not a regression.** Refits of the surviving 2026-09-09 pre-halo logs (`base_c16384`,
`ctx128k_c32768`, branch `d3064a5fd6b`) give 40.91 and 139.7 — agreeing with the new values to
1.4% and 0.7%, while the published ones are the outliers. Consistent with the per-op check at
chunk 8192, which found every op within 2% across those two branches.

Conclusions that survive: chunk **32768 is still the 256k throughput optimum** (11.28 s vs
16384's 11.82 s), and 2048 is still 2.09x worse than 8192 — the 2048/4096/8192 rows reproduce
to **0.03%**. What changes: the margin over 16384 narrows (5.4% -> 4.6%) and both large-chunk
totals are ~2-3% higher than published.

**This is the same lesson as the "never extrapolate the fit" note above, one level down:
don't trust a fitted PARAMETER whose point count you haven't checked.** Record N alongside
every fit and refuse to report a slope from N<3. Found because the `prefill-perf-debug` skill
refused to validate the 32768 slope against any surviving log rather than re-deriving it.
