---
name: bh-glx-b02u08-dev16-dead
description: "bh-glx-120-b03u08 device 24 is a repeatable hardware fault (hangs fabric collectives, POST_RESET fails); b02u08 dev 16 died the same way 2026-10-06"
metadata:
  node_type: memory
  type: project
  originSessionId: 677747a2-f27b-478b-944b-26aaf6be33ca
  modified: 2026-10-06T12:53:03.678Z
---

**bh-glx-120-b03u08, device 24: repeatable fault, confirmed over two independent attempts (2026-10-06, 02:44 and 12:28 UTC).** Both times, on a box whose `tt-smi -ls` showed all 32 rows and whose only chip holder was the root telemetry collector:

1. The Mistral4 1-rank 8x4 run loaded weights and captured the trace normally (setup 7-9 min).
2. It then **hung on the first traced chunk with no error** (`CHUNK_START c=0`, then nothing for 11+ min; producer pushes slowed from ~0.3 s to 18 s apart; runner spinning at ~85% CPU). This is the fabric-collective hang.
3. `tt-smi -glx_reset` afterwards failed with `POST_RESET failed for device 24`, leaving `Read 0xffffffff over PCIe ID 24` until something (infra or a power cycle) restored it hours later — at which point the cycle repeated exactly.

**The hang precedes any kill or reset, and it is always device 24**, so the reset is not the cause: the chip is bad. Don't spend resets on it, and don't conclude "fleet-wide problem" from it. `bh-glx-120-b02u08` was separately dead on arrival the same night with the identical signature on **device 16** (`Read 0xffffffff over PCIe ID 16`), also unrecoverable.

Nothing recovers it: `-glx_reset`, `-glx_reset_auto` (3 retries), `tt-smi -r <dev>`. `-glx_reset_tray` is **no longer supported** ("use tt-smi -glx_reset or tt-smi -r"). `tt-smi -r` on Galaxy warns **CPLD FW v1.16+ is required** — worth raising with the admin. `lspci -d 1e52:` still lists 32 while the chip is dead, so **lspci is not a health check**.

**Before resetting anything, rule out a colleague:** under `hidepid` a third holder shows in `tt-devs.sh` as `? (hidden)`. One PID on **all 32** chips plus `curl localhost:18080` returning 200 is the benign root telemetry collector, and `ls /dev/shm | grep CHIP_IN_USE` showing only your own user confirms no other UMD job.

**How to apply:** `tt-smi -ls` showing 32 rows does NOT predict a healthy fabric — the first real run is the health test, so arm a **stall detector** (poll `grep -c CHUNK_START` on the runner log; a silent hang emits nothing otherwise). On b03u08, expect the hang; ask for a different galaxy. See [[device-usage-visibility]], [[glx-hard-kill-needs-reset]], [[mistral4-tp4-perf-compare-1005]].
