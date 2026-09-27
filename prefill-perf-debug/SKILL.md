---
name: prefill-perf-debug
description: This skill should be used when the user asks to "debug prefill performance", "improve prefill perf", "why is TTFT high", "why is long-context throughput bad", "compare chunk sizes", "per-chunk vs prefix cost", "profile prefill ops", "is this a prefill perf regression", or discusses where chunked-prefill time goes on a TT model, especially when accuracy (PCC) gates the change.
version: 2.0.0
---

# Prefill perf debug

The method lives in a human-readable runbook. Read it first, in full:

```bash
cat ~/debug-docs/PREFILL_PERF_RUNBOOK.md      # method, traps, lever catalogue
ls  ~/debug-docs/prefill_perf_tools/          # queue helpers, fit, PCC compare, power sampler, accum sim
```

Then follow it. These gates are not optional:

1. **Baseline on the same build first.** Never credit a change against a number from a doc or an older build.
2. **Report first chunk / mid-context / full context per chunk size**, and say whether the floor or the prefix
   term moved (`fit_chunks.py`).
3. **Sample power during long runs** (`smi_sample.sh`). If the chips sit at the TDP limit, judge levers by energy
   (FPU passes, toggles), not by idle time.
4. **No conclusion from a hack that leaves data stale or zero.** Build the real change and measure it.
5. **Any arithmetic change gets a PCC run and a per-layer error ratio vs a same-build base** (`cmp_pcc.py`), not
   just the absolute gate.
6. **One knob at a time, measured end to end.** Record nulls in the runbook's lever catalogue when done.

At the end of a session, add what was learned to the runbook (section 2 for traps, section 5 for levers).
