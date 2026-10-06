---
name: mistral4-tp4-perf-compare-1005
description: "Mistral4 1-rank 8x4 256k prefill A/B (PR #56307 baseline vs Asif vs Alina) — branches, harness, results so far, what is still unmeasured"
metadata: 
  node_type: memory
  type: project
  originSessionId: 677747a2-f27b-478b-944b-26aaf6be33ca
  modified: 2026-10-06T03:09:40.360Z
---

Started 2026-10-05 for Kyle. Baseline = PR #56307 head `3c93c8b7` (head later moved to `762283d2`, a PCC-script-only commit, so the baseline stays at `3c93c8b7`). All four local branches in tt-metal-2 share that base:

- `kmabee/mistral4-tp4-perf-baseline` `3c93c8b7`
- `kmabee/mistral4-tp4-perf-asif` `7efb3143` = `mmanzoor/mistral4-L1-oct-1` (base + 1 commit; claims -2.95% at 256k)
- `kmabee/mistral4-tp4-perf-alina` `2980eefc` = `akhan/m4-perf-run-0928` (base + 3: LoFi chunked ring SDPA claiming -10.4%, 8256 B fabric packets, padding-aware GPT_DEVICE gate that only moves PARTIAL chunks so a full-chunk run should not change)
- `kmabee/mistral4-tp4-perf-asif-alina` `6fd8974f` — Alina's 3 cherry-picked onto Asif's; **no conflicts** even though both touch `mla.py`.

Harness: `/data/kmabee/runs_m4tp4_1005/` and `runs_m4tp4_1006/` (`run_variant.sh <name> <tree> <cache> <model>`, `queue.sh`, `summarize.py`). Runner is `run_mistral4_prefill_256k.sh` MODE=1rank; numbers come from the **warm 2nd request**. The runner logs no CHUNK_END, so chunk 51 is extrapolated from the 46-50 slope (~3% of the 256k total) — state that whenever quoting 261,120.

**Measured on c03u08 2026-10-05** (first chunk / 102,400 tok / 261,120 tok / steady tok-s):
- baseline x2: 157.8 and 156.9 ms / 4.22 and 4.20 s / ~15.36 and ~15.35 s / 16,573 and 16,622
- asif x1: 154.2 ms / 4.15 s / ~15.20 s / 16,796 — i.e. **-1.0% at 256k against a baseline whose two runs agree within 0.6%**, well short of the -2.95% claimed.

**Not yet measured:** Alina, Asif+Alina, and the NFS-vs-local-disk question (Asif builds on /home). Evidence so far says disk location should move **setup only, not per-chunk device time**: the runner reads the TTNN cache + config files and never the safetensors, and setup alone varied 12m50s (c03u08) vs 7m15s (b03u08) on NFS. The 65 GB cache is `/mnt/models/blaze/mistralai/Mistral-Small-4-Cache/CI`; the `/mnt/weka` mistralai dirs are permission-denied for kmabee (groups storage-wg / cache-writers).

Blocked 2026-10-06 by hardware: see [[bh-glx-b02u08-dev16-dead]]. Also note `tg_send.sh` needs `~/.tt-telegram.env`, which lives on per-machine `/home` and is absent on a fresh box.
