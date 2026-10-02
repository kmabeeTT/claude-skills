---
name: data-quota-tracy-captures
description: "/data has a per-user quota: tracy captures are ~15 GB each and silently exhaust it; symptoms are a truncated/0-byte .git/index and failed builds"
metadata:
  node_type: memory
  type: feedback
  originSessionId: ecf73b36-1b7e-42d3-8c9f-6038bb920bb7
  modified: 2026-09-27T00:15:37.655Z
---

/data (NFS) enforces a per-user quota even when `df` shows TBs free. On 2026-09-27 six gemma4 layer-perf tracy captures (~15 GB of raw `profiler/` each) plus old ones filled it: writes then fail at close with "Disk quota exceeded", which showed up as `fatal: .git/index: index file smaller than expected` / `unknown index entry format`, a failed `cmake --build`, and a capture with no CSV.

**Why:** `quota` is not installed and `df` is filesystem-wide, so nothing warns before writes start failing.

**How to apply:** test with `dd if=/dev/zero of=/data/kmabee/.wtest bs=1M count=50` (it reports "Disk quota exceeded" on close). After each capture keep only the ops_perf_results CSV and the tt-perf-report summaries; /data/kmabee/prof_0925/capture.sh now trims its raw `profiler/` dir automatically. Repair a truncated index with `rm .git/index && git read-tree HEAD` once space is back. Other big items in the share: gemma4_runs (118 GB), wt_newbase / wt_57422 worktrees.
