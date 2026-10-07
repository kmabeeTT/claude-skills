---
name: prefill-whatif
description: This skill should be used when the user asks for an "interactive what-if", "sliders for perf", "what if matmuls hit 70%", "where are we vs target perf", "gap to target by area", "compare baseline vs week1 vs week2 per layer", or wants an interactive HTML page (artifact) that reconstructs chunked-prefill time from per-layer captures and lets them change per-area efficiency (matmul / SDPA / collectives / small ops) to see TTFT, 100k and 256k totals. Works for any model with per-layer captures; Gemma4 and Mistral4 have ready profiles.
version: 2.0.0
---

# Prefill what-if explorer

Turns per-layer profile captures into one interactive page: preset views from measured stacks, plus a what-if view whose sliders change each area's efficiency and a button that jumps to a target (e.g. 70% matmul / 70% SDPA util). Published with the Artifact tool.

Published pages:
- Gemma4: https://claude.ai/artifact/P17DZRTy5sA8mC3b44KvcL (`profiles/gemma4_bh_glx_8x4.json`; presets Baseline / Week 1 / Week 1 + Week 2; chunk 2048 / 4096 / 8192).
- Mistral4: https://claude.ai/artifact/Vg5e2C2qG2CAcQBzVMw9sm (`profiles/mistral4_bh_glx_8x4_revc.json`; presets Baseline / + Asif + Alina; chunk 5120).

Republish an existing page by passing its URL as `url`, so the link people have keeps working.

## Pieces
- `tools/render_whatif.py PROFILE.json OUT.html`: generic. Validates the profile and embeds it in `tools/whatif_template.html`. Needs only python3.
- `tools/whatif_template.html`: the page (Chart.js 4.4.1 from cdnjs, everything else inline). The model runs in the browser.
- `tools/build_gemma4_profile.py --out profiles/gemma4_bh_glx_8x4.json [--docs DIR]`: the Gemma4 adapter. Reads `LAYER_PROFILES_3SETS.md`, `harness/perf_vs_target/perf_vs_target.json` and `targets.txt` from `gemma4/perf_understand/`. It prints first-chunk reconstruction vs measured; expect +3–4%.
- `tools/build_mistral4_profile.py --out profiles/mistral4_bh_glx_8x4_revc.json [--docs DIR]`: the Mistral4 adapter. Reads `harness/perf_vs_target/perf_vs_target_m4.json` from `mistral4/perf_understand/` (both variants, layer 0 and layer 18, chunk 1 and 50). It prints the reconstruction, which should equal that folder's `target.py` (136.5 ms / 3.75 s / 13.79 s for Asif + Alina).
- `tools/jstest_headless.py PAGE.html`: runs the page script with DOM stubs and prints every view's tiles, the target, and the gap table.
- **Docs location:** the adapters look in `~/prefill-docs/<model>/perf_understand` first, then `/data/kmabee/prefill-docs-staging/<model>/perf_understand` (the NFS copy, since `~` is per-box).
- `profiles/`: built profiles. Keep one per model x hardware.

## Steps
1. **Refresh or build the profile.** After new captures, rerun the model's adapter. For a new model, write `build_<model>_profile.py` that emits the schema below. Copy the Mistral4 adapter if the captures carry per-op work (GFLOP / MB / reference); copy the Gemma4 one if they're category tables. Captures come from the layer-profile harness (`~/prefill-docs/gemma4/perf_understand/harness/layerprof/`): one capture per layer type, at the first chunk and near full depth, per chunk size and per stack.
2. **Render**: `python3 -I tools/render_whatif.py profiles/<p>.json <scratchpad>/<name>.html`.
3. **Check the math headless before publishing** (no browser on the TT boxes). `python3 -m venv <scratch>/jsvenv && <scratch>/jsvenv/bin/pip install mini-racer`, then `<scratch>/jsvenv/bin/python tools/jstest_headless.py OUT.html`. Confirm four things:
   - the latest preset's tiles equal the adapter's reconstruction;
   - each preset's 256k is within ~4% of its measured value;
   - the What-if view before any knob moves equals the `whatif_base` preset to 0.1%;
   - "Set target" gives the totals you expect.
4. **Publish** with the Artifact tool (`icon: chart`). Republish from the same file path to keep the URL. The page is private until the user shares it.

## Profile schema v2 (what the page reads; `"schema": 2`)
- `layer_types`: `[{id, label, count}]`. Gemma4: global x 10, sliding x 50. Mistral4: L0 x 1, L18 x 35, and `host` x 1 for the time outside the layers.
- `components`: what the sliders and charts show, `{id, label, model, color?, peak?, hint?}`. `color` names a CSS token (`--c-matmul`, `--c-gsdpa`, `--c-lsdpa`, `--c-coll`, `--c-small`, `--c-extra1`, `--c-extra2`, `--c-host`). `model` is one of:
  - `roofline`: knob `util` = % of roofline. Per op, t = max(GFLOP / (u x peaks[fid]), MB / (u x bandwidth)), where `bw` is `"dram"` (the page's DRAM selector) or `"fabric"` (`fabric_gbs`). Needs `work[L][id].ops[] = {gflop?, fid?, mb?, bw?, t_us}`. Component time not covered by the ops (routing, etc.) stays at today's.
  - `sdpa_rate`: knobs `util` (% of `peaks[peak]`) and `fixed` µs per layer. t = fixed + GFLOP(k) / (u x peak), GFLOP linear in chunk index between `work[L][id].gflop_first` and `gflop_depth`. Today's values are fitted from the two captures (layer-count weighted). When first and depth GFLOP are equal (a sliding window), `sdpa_fallback_rate_tflops[id]` gives the rate.
  - `ref_ratio`: knob `eff` = % of a reference speed (`work[L][id].ref_us`); scales today's time.
  - `scale`: knob `pct` = % of today's time; `"target"` resolves to `work[L][id].target_us / today`.
- `peaks` (TFLOP/s by fidelity and by SDPA peak name), `dram_options` (`[{label, gbs}]`), `fabric_gbs`.
- `presets`: `[{id, label, desc, measured_note}]`; `whatif_base` = the preset the sliders start from (it needs `work`).
- `target_presets`: `[{label, values: {component: {knob: value | "target"}}}]`. Each one becomes a button.
- `chunks[C]`: `{first_index?, depth_index, checkpoints: [{label, tokens, measured_key, unit}], presets: {id: {layers: {L: {first: {component: us}, depth: {...}}}, measured: {...}}}, work: {L: {component: {...}}}}`. `first_index` / `depth_index` are the **1-based** chunk numbers the captures sit at (default first 1). Mistral4's captures are 0-based chunks 1 and 50, so 2 and 51; getting this wrong shifts the whole curve by one chunk.
- `notes`, `sources`: shown at the bottom of the page.

## Model and its limits (say these when presenting numbers)
- Reconstruction = sum over layer types of count x per-layer time, linear in chunk index between the two captures, summed over ceil(tokens / C) chunks.
  - Gemma4: device time without op-to-op gaps, within ~4% of measured.
  - Mistral4: includes a `host` bucket (measured per-chunk time minus the layers), so it matches measured to ~1% partly by construction. The bucket is 53 ms per chunk at depth in the baseline and 11 ms in Asif + Alina; the target claims no gain there.
- Only the latest stack has per-op work, so the what-if always starts from `whatif_base`. Older presets are fixed views.
- No clock or power model. Long context runs under the 130 W cap, so a target at long context is on the captures' clock basis.
- **At small M (Gemma4 chunk 2048, M = 256 per device) matmuls are weight-streaming.** "70% FLOP util" is unreachable there (max ~37% LoFi at full DRAM bandwidth), which is why the matmul knob is % of roofline. Say so when someone asks for a FLOP-util target.
- The measured numbers in a preset may come from a different TDP or harness (Gemma4 Baseline is 115 W, 106k). Keep that in `measured_note` so the page shows it.
