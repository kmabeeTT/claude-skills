---
name: gemma4-variable-chunk-poc
description: Per-request Gemma4 prefill chunk width works and is worth 1.42x-5.28x; the admission policy is a sawtooth, not a threshold
metadata:
  type: project
---

Built 2026-09-17 on `kmabee/gemma4-swa-multihop-halo` (commits 3904f52f50d, 6372f24b38a,
d70303c78b1 in /data/kmabee/tt-metal-2 — **local only, not pushed**). One model, one KV cache, one
captured trace per width, width chosen at admission from prompt length.

**Two non-obvious things worth not rediscovering:**

1. **Small chunks are never intrinsically better.** `a(C)` is *sublinear* to 16384 — one 8192
   chunk costs 242.7 ms where four 2048 chunks cost 534 ms for the same tokens. The entire
   short-ISL win is **padding waste** (`ceil(P/C)`), so a PoC must run a prompt that does NOT fill
   the wide chunk, not merely a short prompt. Measured: 175.8 ms vs 928.6 ms for the same 4096
   tokens = 5.28x.
2. **The admission policy is a SAWTOOTH, not a threshold.** With {4096, 32768} the choice flips
   4096 -> 32768 at 24576, **back to 4096 at 36864**, and to 32768 again at 45056, because padding
   waste recurs at every wide-chunk boundary. Measured at 36864: 1693 ms (c4096) vs 1985 ms
   (c32768). Any `narrow if P < T else wide` policy is wrong in that band.

**Measured (8x4, both widths run for every prompt):** selector picked the cheaper width 4/4;
1.42x over pinning 4096, 1.68x per-request geomean (range 1.00-5.28x) over pinning 32768. The
fitted cost model predicts each measurement to 0.9-4.2%.

**Padding is bit-exact** (PCC 1.0): serving a prompt in a bucket wider than it fills gives exactly
the answer a fitting chunk would. So a too-wide bucket is wasteful, never wrong — and padded perf
runs are honest. Replay across two traces sharing one cache is also exactly 1.0.

**Functionally BROKEN and blocked** — a multi-width build does not reproduce a single-width
build's answer at a shared width (PCC 0.869); see [[gemma4-prefill-not-width-invariant]] for the
retraction and the lead.

**Perf reality check (added after measuring fixed 8192, the SHIPPING config):** {4096, 32768} is
**0.69x at 16k and 0.79x at 36.8k** — SLOWER than fixed 8192 mid-range. It wins only at the
extremes (1.38x at 4k, 1.20x at 256k). My "beats either fixed width" claim was scoped to its own
two buckets; **a bucket set can only be judged against widths it does NOT contain.** Projected
{4096, 8192, 32768} dominates 8192 everywhere (1.39/1.00/1.00/1.25x). Also: the short-prompt win is
fully available from a single fixed 4096 with no new machinery, so the only incremental case for
variable width is the 1.25x long-context term. Partial final chunks via `valid_global` do NOT help
— the trace is fixed-shape, so the device does identical work either way.

**Architectural objections worth weighing (user's, and I agree):** buckets make the scheduling
quantum non-uniform (175 ms at chunk 4096 vs 930 ms at 32768 -> head-of-line blocking under
continuous batching, invisible in single-request exclusive-mesh numbers), per-slot width becomes
state that must cross the disagg boundary, and both a mid-request change and a wrong decode period
are SILENT corruption. Also not done: the migration/decode boundary must carry the width in slot metadata.
`iter_cache_chunk_locations` already takes `chunk_size`. Known waste: the per-width chunk-major 4D
RoPE tables (~67 MB/device each) are never read on the traced path (it gathers by absolute position
from the width-independent 2D tables); make them lazy.

Related: [[gemma4-prefill-chunk-size-win]], [[precommit-stashes-unstaged-work]].
