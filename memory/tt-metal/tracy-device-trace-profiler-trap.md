---
name: tracy-device-trace-profiler-trap
description: python -m tracy --device-trace-profiler destroys op-level attribution and breaks post-processing; omit it and traced replays are profiled per-op anyway
metadata: 
  node_type: memory
  type: reference
  originSessionId: caf0f877-ab74-4d6c-afd4-5752b6f99c70
  modified: 2026-09-16T21:01:22.420Z
---

**Do not pass `--device-trace-profiler` to `python -m tracy` when you want per-op device data.**
It sets `TT_METAL_TRACE_PROFILER=1`, which profiles **only trace regions**: you get one CSV row
per `execute_trace` with an empty `OP NAME`, and eager ops end up with host records but no
device rows, which then kills post-processing with

    process_ops_logs.py:683 AssertionError: Device data missing: Op N not present in
    cpp_device_perf_report.csv

The run completes and prints its measurements, then exits 1 during report generation.

**Omit the flag.** `python -m tracy -r -p -v -o <dir> -m pytest <nodeid>` profiles traced
replays per-op perfectly well, and signposts inside the test then bracket each replay cleanly.

Related gotchas measured the same session: `DEVICE KERNEL DURATION PER CORE MIN/MAX` are empty
on the `cpp_device_perf_report.csv` path, and the per-RISC durations are *elapsed*, not busy,
time (every RISC reads the full op duration) — neither gives utilization. Signpost rows carry
no `DEVICE ID`, so a device filter must keep them or signpost segmentation silently falls back.

**The utilization columns are empty too (confirmed 2026-09-16).** `NOC UTIL (%)`,
`MULTICAST NOC UTIL (%)`, `DRAM BW UTIL (%)`, `ETH BW UTIL (%)` and
`DEVICE COMPUTE CB WAIT FRONT/RESERVE BACK [ns]` all exist as CSV columns but are **entirely
null** on this path, and `PM IDEAL [ns]` is a stub (median 1 ns). The BW ones are populated only
with `--analyze-noc-traces` **and** a built tt-npe on `$PYTHONPATH`, and even then they are
*modelled* from NoC event traces, not measured. So do not plan an investigation around reading
a utilization column.

**What to use instead of a FLOP anchor.** Comparing achieved TFLOP/s against a dense matmul in
the same layer is an *inference*, not a measurement — it attributes the whole residual to
whatever you guessed, and that conclusion was successfully challenged. Prefer a **causal
ablation that varies one cost term and leaves the others alone** (e.g. change `q_chunk_size` to
scale per-row math while holding bytes-per-work-unit fixed, then solve for the split). Needs no
spec-sheet peak and no utilization column. See [[gemma4-sdpa-qchunk-occupancy]].

**Cost of a profiled run (BH galaxy, 60-layer model, chunk-0 single-layer test):** ~7.5 min of
device time, then a **4.8 GB** `profile_log_device.csv` and **5.7 GB** `tracy_ops_times.csv`
and several minutes of post-processing. Also, `python -m tracy` launches a Tracy **WASM web-UI
server** before `generate_report`, so the run looks hung after the test passes. Budget ~15 min
and a generous `timeout`, or the report is killed after the device work is already done —
`--process-logs-only` recovers it from the `.logs` folder without re-running.

See [[gemma4-prefill-chunk-size-win]], [[gemma4-sdpa-qchunk-occupancy]].
