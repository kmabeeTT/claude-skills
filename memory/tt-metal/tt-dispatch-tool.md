---
name: tt-dispatch-tool
description: ~/scripts/tt_dispatch.py (pushed a589bfc, 2026-10-26) dispatches a command via Slurm to a healthy machine filtered by measured power cap / rev; guide in ~/scripts/TT_DISPATCH.md
metadata:
  type: reference
---

`~/scripts/tt_dispatch.py` (guide `~/scripts/TT_DISPATCH.md`) is the way to run device work on Exabox from a slurm-login node: `list --power '>=130'`, `run [--build] --power '>=130' -C <tree> -- '<cmd>'`, `tt-sbatch ... -- <tt-sbatch args>`, `status`, `logs ID -f`. Standalone (no slurm_free.py / allocation sheet): read-only ssh probe of sysfs, cached 4 h in /data/$USER/.cache/tt-dispatch/hosts.json; in-job re-check resubmits away from bad boxes; ends with a grep-able `TT-DISPATCH SUMMARY` line.

Facts it rests on (2026-10-26): per-chip cap is `.../device/hwmon/*/power1_max` (75/130/160/190 W on galaxies) and 6 of 20 boxes disagreed with the sheet's kW label; serial digits 5-8 `0471` = Rev A/B, `0473` = Rev C. Gemma4 sweep via `run --power '>=130'` matched the ssh run on b08u08 within 1.5%. Related: [[tt-sbatch-build-time-limit]], [[bh-galaxy-power-tier-measurement-validity]].

Shared with the team via the private kmabeeTT/scripts GitHub repo only (people with access); a /data/kmabee/shared symlink was tried and reverted 2026-10-26 because it needed helpers/ opened to traversal.
