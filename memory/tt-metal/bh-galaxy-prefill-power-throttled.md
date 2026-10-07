---
name: bh-galaxy-prefill-power-throttled
description: Gemma4 256k traced prefill on BH Galaxy runs power-throttled (AICLK ~1100-1250 of 1350); data-dependent speed; zero/stale-data hacks look falsely fast; bh-glx-120-c03u08 TDP raised 115 -> 130 W on 2026-09-29
metadata:
  node_type: memory
  type: project
  originSessionId: 8f985f1d-292b-4c2b-ba24-7719ec3e62ae
  modified: 2026-09-27T06:40:02.194Z
---

Measured 2026-09-27 with `tt-smi -s` sampled ~2 Hz during the traced 256k demo (8x4 BH Galaxy): per-chip power
mean 100-125 W vs `tdp_limit` 115 W (spikes to ~268 W), AICLK drops from 1350 to ~1043-1250 MHz for the whole
run. Idle/compile phases read 1350 MHz / ~55 W.

Consequences:
- Speed is data-dependent. Any perf hack that leaves a buffer stale or zero (skip a gather, send nothing)
  runs faster because zeros toggle fewer bits, NOT because the skipped work was the bottleneck. The
  "ring all-gather costs 0.9 s" claim came from such hacks; the real append-only gather (DPRINT-verified to send
  one slab) gained nothing.
- The isolated-layer benchmark (`test_prefill_layer_perf_chunk_n`, one ~25 ms burst) barely throttles
  (zeros vs randn cache: only -3.6%), so it understates energy-saving changes. Judge those with the full demo.
- Energy-cutting levers (LoFi, bfp8 activations/CCL payloads, fewer round trips) pay twice.

**How to apply:** before crediting a perf win, check the change didn't make data stale/zero; sample
`tt-smi -s` (aiclk, power) during long runs. Related: [[pp4-latency-metric-contaminated]],
[[per-op-perf-compare-same-renderer]].

**Update 2026-09-29: the TDP limit on bh-glx-120-c03u08 went from 115 W to 130 W** (all 32 chips, `tt-smi -s` -> `limits.tdp_limit`), sometime between ~12:50 and 15:07 UTC. Same build, base combined-main: 8192 126.8 -> 122.9 ms first chunk, 256k device 7.18 -> 6.83 s; 4096 256k 8.06 -> 7.70 s; 2048 barely moves (never reached either cap). 8k AICLK ~1140 -> ~1210 MHz.
**How to apply:** numbers from before 2026-09-29 afternoon are at 115 W and are not comparable to later ones; re-baseline at the current cap, and log `tdp_limit` with every baseline.


**2026-10-07, bh-glx-110-d07u02 (14 kW RevC, 130 W), Gemma4 2k/4k/8k sweep with sysfs telemetry every 0.5 s:** late chunks at 4096 / 8192 (long-context global attention) sit at the cap (131–135 W mean per chip) with AICLK ~1205–1220 MHz (min 1100); early chunks and all of 2048 stay ~1300–1340 MHz. That is why a 190 W box (b05u08) wins only at long context (8192 @256k 6.19 vs 6.59 s at 130 W) and first chunks match everywhere. RevC was 2–3% slower than c03u02 at long context (DRAM power vs board variation unresolved). Sampler: read `/sys/class/tenstorrent/tenstorrent!N/tt_aiclk` and `device/hwmon/hwmon*/power1_input` (µW), safe beside a live run; script kept at d07u02 `/home/kmabee/g4perf_d07u02/telemetry_sampler.py`.
