---
name: tt-board-smoke-test
description: "~/scripts/tt_board_smoke.py (sub-second, dependency-free galaxy health check) and tt_fleet_smoke.py (same check across many hosts over ssh stdin, ~1 s for 7 boxes)"
metadata:
  node_type: memory
  type: reference
  originSessionId: 677747a2-f27b-478b-944b-26aaf6be33ca
  modified: 2026-10-06T14:35:03.890Z
---

Written 2026-10-06 at Kyle's request, replacing the venv-bound `~/scripts/tt_mesh_smoke.py`, which dies inside `ttnn.get_num_devices()` on exactly the boxes it is meant to diagnose.

**`/home/kmabee/scripts/tt_board_smoke.py`** — stdlib only, system `python3`, **~0.4 s** (`--no-http --window 0` is instant). Exit `0` good / `1` bad / `2` inconclusive, so it gates a run; `--json --quiet --csv --window N --expect N --lenient-nodata --no-http`.

**`/home/kmabee/scripts/tt_fleet_smoke.py`** — the same check across many machines, **7 boxes in ~1 s**. It **pipes the checker over ssh stdin** (`ssh host /usr/bin/python3 - --json`), so nothing is deployed or synced and every box runs identical bytes; the local host runs without ssh. Hosts come from args, `-f file` (`~/scripts/tt_hosts.txt`), or stdin. `--only-bad`, `--json`, `--csv`, `-j N`. It prints a `usable:` line of healthy hosts. **It needs a live SSH agent** — in Claude Code's non-interactive bash `source ~/.bashrc` is a no-op, so run the agent-hunt loop first (see [[tt-metal-push-routes]]).

What the signals mean, with the evidence behind each:

- **HUNG — definitive.** sysfs `tt_heartbeat`/`tt_aiclk` reading `4294967295`, or `tt_asic_id` = `FFFFFFFFFFFF`. Same all-ones read that makes UMD raise `Read 0xffffffff over PCIe ID <n>`. **The attributes are directly under `/sys/class/tenstorrent/tenstorrent!<N>/`, NOT under `device/`** — the `device/` path silently reads nothing.
- **MISSING — definitive.** Fewer chips enumerate than expected (from the collector's `tt_expected_chip_count`, or `--expect`). b02u08 on 2026-10-06 had **24 of 32** in sysfs, `/dev` and `lspci` alike: a whole tray off the bus. Without this check the box reads "24/24 live" and looks perfect, which is why `live == present` is not health.
- **NODATA — fails by default.** A healthy galaxy publishes telemetry for all 32 (c03u08: 32 live, 0 nodata, accessible=1, readable=100%); b03u08 with one dead chip gave 16 live / 15 nodata / accessible=0. Two-box basis, so `--lenient-nodata` downgrades it to a warning.
- **STUCK** — heartbeat not advancing in the window; re-check with `--window 2`.
- **Collector `:18080`** — `tt_all_devices_accessible` / `tt_all_devices_metrics_readable_percent` see chips sysfs may not. `tt_chip_count`/`tt_pci_device_count`/`lspci` only count PCIe presence, so they are useless as health on a wedged chip (though they do catch MISSING).

**Safe against a live workload, verified by strace:** zero `/dev/tenstorrent` opens, every `tenstorrent` open `O_RDONLY`, zero `/dev/shm` (so it never touches UMD `CHIP_IN_USE` locks), no reset path; the only ioctls are `TCGETS`/`TIOCGWINSZ` on stdio. Not measured: whether a telemetry read perturbs a running workload's own ARC traffic — expected to be negligible since the root collector polls continuously, but run it before a measured window if a number must be untouchable.

Both PASS and FAIL paths are validated against real boxes. Wired in as a preflight in `/data/kmabee/runs_m4tp4_1006/run_variant.sh` (aborts exit 9 rather than burning a 15-minute run). See [[bh-glx-b02u08-dev16-dead]], [[device-usage-visibility]].
