# <Model> prefill: time to reach N tokens of context, <chunk sizes>

Data comes from the per-chunk `[traced_perf]` lines in <link to the logs / source gist>. Each curve is the running sum of per-chunk traced device time from the first chunk up to <max context> (<tokens> tokens). <Model>, <hardware + mesh>, <box>.

## TLDR
- Shape: <quadratic, not exponential — per-chunk time is linear in prefix (fit residual ≤ X ms)>.
- Latest at <max>: **<a> s** (<chunk>), … . <Earliest milestone> took <…>.
- <The one comparison a reader should remember, e.g. "latest 2k ≈ baseline 8k">.
- <Which term each step moved: fixed per-chunk cost vs growth with context, from the fit in stats.md>.

## Milestones
- **<name>**: <row/tag/sha, power>. <Any substitution, and the evidence it is fair.>
- <Power or test differences between milestones, quantified.>

## Charts
### 1. <title>
![<alt>](https://gist.githubusercontent.com/<user>/GIST_ID/raw/<file>.png)

## Numbers
Cumulative device time at <checkpoints> (s):
- <chunk>: <milestone> a / b / c / d, …

Linear fit of per-chunk device time = fixed + slope × prefix (ms, ms per 1k tokens of prefix):
- <chunk>: <milestone> F + S, …

## Log
`<model>_latest_<what>_log.tar.gz` holds the raw log behind the latest curves: `<row>/<file>.log`. <Test id>, <PASSED>. Built from <tag> (<sha>): <what is in it>, measured <date> on <box> at <power>. Its `[traced_perf] DEVICE` totals match the chart (<a / b / c ms>). The other milestones' logs are in <link>.

```
curl -sL https://gist.githubusercontent.com/<user>/GIST_ID/raw/<archive>.tar.gz | tar -xz
```

## Method and files
- Device time vs wall, and which tables match exactly.
- Which pass is plotted and the pass-to-pass spread.
- `per_chunk.csv` (everything extracted), `plotted_series.csv` (only the plotted points), `charts.json` (the config), `extract_traced_perf.py` / `plot_prefill_curves.py` (regenerate).
