# tools

Small tools for the prefill perf method in [../RUNBOOK.md](../RUNBOOK.md). The run helpers use the Gemma4 test
ids (`models/demos/gemma4_d_p`); edit them for another model. Everything else is model-agnostic.

- `lib.sh`: run-queue helpers (`perf`, `pcc`, `lp`, `t`, `mkb`, `sw`, `waitchips`, `purge`). Source it from a queue
  script. Settings: `TT_METAL_HOME` (required), `PY`, `PREFILL_RUNS` (log dir, default `~/prefill_runs`),
  `PREFILL_ENV` (optional file with model paths), `PURGE_KERNELS`. See the header of the file.
- `fit_chunks.py`: fit floor `a` and prefix `slope` from a perf log (stdlib only).
- `cmp_pcc.py`: per-layer (1 - PCC) error ratio between two PCC runner logs; `minpcc.py`: min per-head PCC.
- `smi_sample.sh`: sample tt-smi power / AICLK during a run (`smi_sample.sh [seconds] [outfile]`).
- `sdpa_accum_sim.py`: CPU simulation of the streaming SDPA's bf16 accumulation error (needs torch).
- `sdpa_accum_sim2.py`: which accumulator dominates (denominator vs output, fp32/fp16/bf16, K splits).
- `sdpa_accum_sim_vmean.py`: the same with V = mean + noise (realistic); reports the error left after removing a
  per-row scale (what a post-attention norm leaves). Shows output-accumulator saturation that zero-mean V hides.

Example queue script:

```bash
#!/bin/bash
export TT_METAL_HOME=/path/to/tt-metal PREFILL_RUNS=~/prefill_runs/today
source ~/.claude/skills/prefill-perf-debug/tools/lib.sh
perf base 8192
pcc base 8192
perf lofi 8192 MY_EXPERIMENT_KNOB=1
pcc lofi 8192 MY_EXPERIMENT_KNOB=1
python3 $TOOLS/cmp_pcc.py $O/pcc_base_c8192.runner.log $O/pcc_lofi_c8192.runner.log
```
