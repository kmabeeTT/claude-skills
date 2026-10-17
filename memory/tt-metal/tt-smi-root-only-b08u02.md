---
name: tt-smi-root-only-b08u02
description: On bh-glx-120-b08u02 (10-16) the system tt-smi package dir is root-only, so tt-smi, -glx_reset and is_high_power() fail; a private pip copy in ~/venvs/ttsmi works
metadata:
  type: reference
---

2026-10-16 on bh-glx-120-b08u02, `/usr/local/bin/tt-smi` fails with `ImportError: cannot import name 'main' from 'tt_smi' (unknown location)`: `/opt/tenstorrent/tt-tools/tt-smi/.venv/lib/python3.10/site-packages/tt_smi` was reinstalled 18:13 with `drwxr-x--- root root`. Consequences: no `tt-smi -glx_reset` after a hard kill, and `is_high_power()` (models/demos/deepseek_v3_d_p/utils/smbus_telemetry.py, used by the ring SDPA Gemma4 perf checks) returns False, so those checks silently SKIP on a 130 W box.

Fix without sudo: `uv venv --python /usr/bin/python3.10 ~/venvs/ttsmi && VIRTUAL_ENV=~/venvs/ttsmi uv pip install tt-smi==6.6.0`, then run it from `/` (`cd / && ~/venvs/ttsmi/bin/tt-smi -glx_reset`) or put `~/venvs/ttsmi/bin` first on PATH for the perf checks. After a reset, stale `/dev/shm/TT_UMD_LOCK.CHIP_IN_USE_*` from the killed PID stay: move them aside (see [[stale-chip-locks-look-like-container]]). Related: [[glx-hard-kill-needs-reset]], [[bh-galaxy-power-tier-measurement-validity]].
