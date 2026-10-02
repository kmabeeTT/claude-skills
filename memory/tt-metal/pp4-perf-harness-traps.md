---
name: pp4-perf-harness-traps
description: "Two silent-failure bugs in the mistral4 pp4 perf harness — the driver hides rank crashes, and gen_pp4_binding.py --profile clobbers the plain binding"
metadata: 
  node_type: memory
  type: project
  originSessionId: 197d2be2-411b-4a5f-b4e2-1feb588af108
  modified: 2026-09-03T17:27:03.989Z
---

Two defects in `models/demos/deepseek_v3_d_p/tests/perf/pp4/`, both found 2026-09-03 while
re-running the matrix on the sept1 branch. Neither errors; both corrupt results quietly.

1. **`run_pp4_model.sh` exits with the PRODUCER's rc, not the runner's.** The producer pushes
   chunks into a socket and exits 0 whether or not the ranks survived, so a runner-side crash
   (e.g. the #55126 assert killing all 4 ranks) reports `rc=0`. `run_matrix.sh` then records the
   cell as complete, **skips its own `tt-smi` recovery path** (which only runs on non-zero rc), and
   on a later re-run skips the cell entirely because `runner.log` exists and is non-empty. A failed
   cell therefore looks like a passing one twice over. Check `grep -c AssertionError`/`Traceback` in
   `runner.log` rather than trusting the matrix's rc.

2. **`gen_pp4_binding.py --profile` does not switch template.** README says it emits
   `..._torus_y_profile.<host>.yaml`; the code only adds `TT_METAL_PROFILER_DIR` and writes to the
   same `<template stem>.<host>.yaml`. Running it after the plain invocation **overwrites the plain
   binding with a profiler-enabled one**, so every later "e2e" cell runs instrumented. Pass the
   profile template explicitly:
   `--template .../pipeline_prefill_request_intragalaxy_4rank_8x1_torus_y_profile.yaml --profile`.

3. **`TT_METAL_PROFILER_PROGRAM_SUPPORT_COUNT` defaults to 1000** program executions per RISC, and a
   9-layers-per-stage Tracy capture needs ~3,700. Past the limit the run LOOKS successful — producer
   rc=0, ~19 GB of capture on disk — but device records are silently dropped and report generation
   dies with `AssertionError: Device data missing: Op N not present in cpp_device_perf_report.csv`.
   Unrecoverable after the fact: the data was never written, so re-processing fails identically.
   Raising it took `cpp_device_perf_report.csv` from 17,745 to 33,129 rows and the assertion vanished.
   Costs 48 B per program per RISC of DRAM, so size it (layers x chunks x ~110) rather than maximise.
   minimax_m3 hit the same wall at 62 layers and abandoned Tracy per-op for its real model, so this is
   a general large-model limitation in this repo, not a Mistral one.

4. **A capture run needs a longer post-sentinel wait than a perf cell.** The tracy report step runs
   INSIDE each rank after the sentinel drains; `run_pp4_model.sh` terminated the runner at 5 min and
   killed tracy mid-write, truncating one rank's `.logs` beyond recovery. `RUNNER_EXIT_WAIT_TICKS`.

5. **Report layout differs by path.** A normal in-rank tracy run writes `reports/<name>/<timestamp>/`;
   `--process-logs-only` writes `reports/<timestamp>/`. A fixed-depth glob finds nothing for one of
   them and reads as "report generation failed" on a capture that succeeded.

Also: skipping the assert crash leaves the fabric wedged, and the next launch dies in
`RiscFirmwareInitializer::assert_active_ethernet_cores_to_reset` — that is trap 1 of
[[tt-galaxy-fabric-run-hygiene]], not a new bug.

**Why:** both turn a wasted run into a *plausible-looking* result, which is worse than a failure.

**How to apply:** after any matrix run, verify each cell's `runner.log` has no `Traceback` and that
`analyze_ttft.py`/`analyze_pp.py` actually parse it, before quoting a number. See
[[mistral4-pp4-real-d2d-results]].
