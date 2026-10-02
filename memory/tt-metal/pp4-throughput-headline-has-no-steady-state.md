---
name: pp4-throughput-headline-has-no-steady-state
description: "The PP=4 261,120 tok/s headline is the median of a 3.2x ramp, not a steady state, and slides 10% with the analyzer's warmup argument"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9504d613-4814-44fd-8edb-e8639b38373b
  modified: 2026-09-12T04:30:14.387Z
---

`analyze_prefill_throughput.py` reports "steady-state" throughput as `chunk_size / median(interval after warmup)`, and its docstring asserts "in steady state one chunk retires per interval". **That premise is false for chunked prefill.** Measured on rank 3 of a 261,120-token PP=4 run (`chunks=[51,51]`, 2026-09-12), the chunk-to-chunk interval ramps monotonically **135 ms -> 435 ms within each request** as KV depth grows, then resets at the request boundary. Per-bin throughput spans 37,960 -> 11,776 tok/s. There is no flat region anywhere in the run.

Consequence: the headline is whatever slice of the ramp the median lands on, so it moves with the analyzer's optional second argument (`warmup`, default 4). Same log, rank 3, old build: warmup=0 -> 17,877 · 2 -> 17,862 · 4 -> 17,418 · 8 -> **16,996** · 16 -> 16,218. A 10% span from one CLI argument. Raising warmup drops the fast shallow-KV intervals and slides the median down the ramp.

This is how `16,996 vs published 17,059, -0.37%` got into the PR #56307 description as a clean-build reproduction: that reading is **warmup=8**, not the default. At default warmup=4 the same log reads 17,418, i.e. +2.1% vs published, not -0.37%. The agreement was a coincidence of a non-default argument.

**Why:** the number is still a fine *benchmark* (fixed config reproduces to 0.2% - request 1 vs request 2 medians agreed at 18,065 / 18,095), but it is not a steady-state rate and is not comparable across different chunk counts, chunk sizes, or warmup values.

**How to apply:** always state the warmup and the chunk config alongside any quoted tok/s, or quote the whole-run `span incl. fill` figure instead. When comparing two builds, hold warmup fixed and compare per-bin - that showed the post-rebase build ~2-3% faster at every warmup. See [[mistral4-branch-suites]] and [[build-host-bh-glx-110-a10u08]].
