---
name: prefill-perf-charts
description: This skill should be used when the user asks to "plot prefill time vs context", "chart time to max context", "graph the perf journey", "make charts from the traced_perf logs", "compare chunk sizes on one plot", "baseline vs latest prefill curves", "put the prefill charts in a gist", or otherwise wants line charts of chunked-prefill time from the first chunk to full context (one or more milestones, one or more chunk sizes), optionally published as a GitHub gist.
version: 1.0.0
---

# Prefill perf charts

Turns `[traced_perf] chunk i/N [start, end) device=…ms` log lines into time-to-context line charts, one curve per (milestone, chunk size), with a README, and publishes them as a gist with the README listed first.

Tools are in `tools/` in this skill's directory. A complete worked config is `examples/gemma4_journey_1006.json` (3 milestones x 3 chunk sizes, 7 charts). Its published result is https://gist.github.com/kmabeeTT/d4907ee9d2a2d94953a3ea9bdfd71bdd.

## Steps

Work in the session scratchpad. Use fresh, timestamped directories, and never `rm`.

1. **Get the logs.**
   - From a gist with `*.tar.gz.b64` log bundles (e.g. the perf journey gist `70784f19e26b2aec34ae7499be648dc3`): `tools/fetch_gist_logs.sh <gist id or url> <fresh dir>`. It decodes each bundle into its own folder and lists the folders that hold `[traced_perf]` logs.
   - From local runs: point straight at the run directories. One folder per build is the "row".
2. **Extract**: `python3 -I tools/extract_traced_perf.py --src LABEL=DIR [...] --out per_chunk.csv`. The printed table (source, row, chunk, pass, chunks, first_ms, max_ctx, cum_device_s) is how you map milestones to runs. **Cross-check the cum/first numbers against the source doc's tables before plotting.** If they disagree, you picked the wrong run or pass.
3. **Pick the milestones with the user's words in mind**, and write the config (copy the example).
   - A run that is missing a chunk size (a build that cannot run it, or a crashed log with fewer than N chunks) must be substituted explicitly. Use the nearest row that runs it, and say so in the milestone `note`, the chart `note` and the README. Never leave a silent gap or a silent stand-in.
   - Prefer milestones measured with the same test and power setting. When they differ (e.g. 115 W vs 130 W TDP), state it in the milestone name and quantify it in the README.
   - Default to pass 1 when a row has several passes (it is usually what doc tables quote). Note the pass spread in the README.
4. **Plot**: `python tools/plot_prefill_curves.py --csv per_chunk.csv --config charts.json --out OUT_DIR` (needs matplotlib; `/data/kmabee/tt-metal/python_env/bin/python -I` has it). This also writes `stats.md` (checkpoint values, first chunk, linear fit of per-chunk time vs prefix) and `plotted_series.csv`.
5. **Look at every PNG** (Read tool) for label collisions or clipped text before publishing. The validator-free parts (layout) are only caught by eye.
6. **Write the README** from `README_TEMPLATE.md`, filling numbers from `stats.md` (don't retype from memory). Use GitHub markdown with no hard wraps. Image links are `https://gist.githubusercontent.com/<user>/GIST_ID/raw/<file>.png`, and the publish script fills in GIST_ID.
7. **Stage and publish**. Put the PNGs, README, `per_chunk.csv`, `plotted_series.csv`, the config and copies of the two python tools in one dir. Add the raw log behind the newest milestone as `<model>_latest_<what>_log.tar.gz`, keeping its row folder inside the tar so the path in the README matches. Grep it for tokens/keys first. Describe it in a `## Log` section of the README: tag/sha, test id, PASSED, and the `[traced_perf] DEVICE` totals that match the chart. Point to where the other milestones' logs live. Then, then run `tools/publish_gist.sh --dir DIR --readme NAME.md --desc "…"`. That creates a secret gist (`--public` only if asked) and uploads the README as `0_NAME.md` so it is listed first. It then verifies that every image URL returns 200 image/png and that the README is the first file on the page. Report the URL only after it prints `OK`.

## Chart types (config `charts[].type`)
- `by_chunk`: one milestone, every chunk size. Answers "what does the stack look like now".
- `compare`: several milestones x every chunk size on one plot. Colour = chunk, style = milestone. Six curves read fine. Nine get busy, so pair it with `small_multiples`.
- `small_multiples`: one panel per chunk size with every milestone, sharing a y axis. The readable form for 3+ milestones.
- `per_chunk`: y = this chunk's device time. It shows the cost grows linearly with prefix, which is why the cumulative curves bend (quadratic, not exponential).

All charts in one config share the y range, so separate PNGs compare by eye.

## Traps
- `gh` not logged in on a box: `gh auth status` says so, and `~/.config/gh/hosts.yml` is per box (`/home` is local). Have the user run `! gh auth login --insecure-storage` in this session, since a headless box has no keyring.
- `gh gist create` refuses PNGs. The publish script works around it with a git push. Don't try to upload images with `gh gist edit`.
- Gists list files by name, so a README named `GEMMA4_….md` lands after `1_….png`. Hence the `0_` prefix.
- Week-1-style logs print the running total rounded to 0.1 s. The extractor recomputes `cum_device_ms` from per-chunk ms, so use that, not the logged total.
- Device time vs wall: the curves are summed traced device time. Doc tables may quote wall totals, which add host time (≈2% at 256k). Say which one each number is.
- Fit residuals in `stats.md` above ~5 ms mean per-chunk time isn't linear in the prefix (a cliff, throttling, or a mid-run hiccup). Look at the `per_chunk` chart before claiming a slope.
