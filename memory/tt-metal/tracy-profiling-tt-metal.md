---
name: tracy-profiling-tt-metal
description: How to Tracy-profile a tt-metal model here, and the CSV/CLI traps that silently produce wrong or empty results
metadata:
  type: reference
---

Device profiling on `/data/kmabee/tt-metal` needs **no rebuild** — `build_Release` already has `ENABLE_TRACY:BOOL=ON` and `libtracy.so`. Verify with `grep ENABLE_TRACY build_Release/CMakeCache.txt` before assuming a rebuild is required.

Invocation: `./python_env/bin/python -m tracy -v -r -p -o <outdir> -n <name> -m pytest "<exact::node::id>" -s`

Four traps, each of which produces a **plausible-looking wrong answer** rather than an error:

1. **Tracy splits a quoted `-k "a and b"`** into separate argv entries → pytest dies on a bare `and` (`file or directory not found: and`) → **tracy still exits 0**. A "successful" run that profiled nothing. Tell-tale: `No device logs found` and a tiny trace (`Zones: 7`). Use an exact node id. Same family as the `-m` mis-parse documented at `models/demos/deepseek_v3_d_p/utils/perf_utils.py:376` (never inline `KEY=VAL` before `-m pytest`; export instead).
2. **Signposts in the ops CSV carry NaN `DEVICE ID` and NaN `GLOBAL CALL COUNT`** — host-side markers ordered ONLY by CSV row position. Any signpost-bounded analysis must walk rows in order.
3. **`GLOBAL CALL COUNT` is unique per (op, device)** — a global dispatch counter, NOT a cross-device op id. Grouping on it yields one "logical op" per row and a **~32x inflated total** on a galaxy. The cross-device identity is the op's **ordinal within its own device**.
4. **Always bound by signposts.** Unbounded totals include one-time weight tilize/typecast at construction, which can exceed the layer itself (measured 60 ms of weight load vs 32 ms of layer). Models here emit `MLA_START/END`, `MoE_START/END`, `forward_layer_<i>_start/end`; `perf_utils.run_model_device_perf_test_with_merge(between_signposts=...)` consumes them.

Multi-device merge convention (from `perf_utils`): **collectives → MEAN** across devices (each chip moves a share of one logical transfer), **everything else → MAX** (chips run in parallel; slowest is the critical path).

Working setup + measured Mistral-4 results (TP=4 vs PP=4, one layer deep): `~/debug-docs/mistral4_prefill_planning-noissue/part2/HANDOFF_TRACY_PERF_SINGLE_LAYER.md`. Reusable summarizer: `models/demos/deepseek_v3_d_p/tests/perf/summarize_mistral4_profile.py`. See also [[device-usage-visibility]].
