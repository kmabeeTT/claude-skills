---
name: glx-hard-kill-needs-reset
description: Hard-killing a wedged TT galaxy run silently degrades perf 2-5x until tt-smi -glx_reset; budget two resets
metadata:
  type: feedback
---

After SIGKILLing a wedged multi-rank run on a bh-glx galaxy, the board is left **degraded but not broken**: runs still succeed and report rc=0, they are just 2-5x slower. Measured 2026-09-14 on bh-glx-120-b03u02: 1rank@25,600 prefill latency read 7.970 s on the degraded board vs 0.820 s after reset; pp4@25,600 1.761 s vs 1.029 s.

**Why:** there is no error to notice. The first hard failure came later (`Bus error (non-existent physical address)`, then `check_board` unable to map an 8x4 mesh). Any measurement taken in between is silently wrong, and comparing it against a reference looks like a real regression.

**How to apply:** after ANY hard kill of a device run, `tt-smi -glx_reset` BEFORE measuring again, then confirm with `pipeline_prefill_harness/check_board.sh` (rc=0). **Budget two resets** — the first reported success and re-initialised 32 boards, but the next run still bus-errored; only the second reset made check_board pass. The diagnostic tell for contamination is a split in the data by kill time: cells measured before the kill faster than reference, every cell after it slower. See [[mistral4-prefill-campaign-harness]].

**The board check right after a reset is NOT authoritative — in either direction.** 2026-09-15, same box: both glx_resets printed `Error: POST_RESET failed for device 30`, and the `check_board.sh` run immediately after each one failed to map 8x4. That reads as "two resets did not fix it, escalate to IT". A check a few minutes later passed cleanly and the galaxy ran fine. Combined with the known inverse (a reset reporting success while the fabric is still unmappable), the rule is: **wait and re-check before concluding anything about a freshly reset board.** This matters because `run_matrix.sh`'s recovery path ABORTs the whole campaign on exactly that immediate check, so a board that was about to be fine abandons a matrix.

**A wedged board has a second, free signature:** `/proc/driver/tenstorrent/*/pids` normally lists the root `tt_telemetry_collector` on all 32 chips. When the fabric went down that daemon died too, leaving the pid files empty. "No holder at all, including the root daemon" reads like an idle board and is actually the opposite — and it is much cheaper to check than opening a mesh. See [[device-usage-visibility]].

**A sysmem race, not a determinism, is what wedged it:** `run_matrix.sh` launched the next cell ~1 s after the previous returned and rank 0 hit `RuntimeError: Sysmem mapped at unexpected NOC address (likely a stale process holding sysmem)`; that failure is what took the fabric down. The identical 1-second gap had worked on the preceding pass. Poll `/proc/driver/tenstorrent/*/pids` for your own uid's PIDs and wait for them to clear between cells — a gap that works once is not a gap.

**Same family, merged 2026-10-02 from `sysmem-unexpected-noc-reset`:** the sysmem error also appears with NO kill and no live holder. On bh-glx-120-c03u08 (2026-10-02 11:16), right after a clean PCC run, the next full-mesh run failed at device open with `RuntimeError: Sysmem mapped at unexpected NOC address (likely a stale process holding sysmem)`, and a single-chip test then failed with `Query mappings failed on device 0: No such device`; the UMD locks showed no holders. Treat it as stale device state, not a code bug: `tt-smi -glx_reset` (~1 min), then give the boards a minute or run a small single-chip test first. A full-mesh run started seconds after the reset failed again with `Query mappings failed`; one a minute later worked. Related: [[stale-chip-locks-look-like-container]], [[tt-galaxy-fabric-run-hygiene]].
