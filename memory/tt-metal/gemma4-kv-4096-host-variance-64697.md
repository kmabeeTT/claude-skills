---
name: gemma4-kv-4096-host-variance-64697
description: Gemma4 mock-256k KV flake at chunk 4096 (#64697) = multi-hop sliding halo shared-semaphore race (since #57453); fix branch kmabee/gemma4-sliding-halo-arrival-sems, PR not opened; read FINDINGS_1107.md
metadata:
  type: project
---
Root cause (established 2026-11-07): every predecessor of a multi-hop sliding halo increments one shared rendezvous semaphore (`semaphores[2]`, same handle for every sliding layer) and the reader waits `wait_min(sem, arrivals_expected)`. A CP rank already on the next sliding layer can supply an arrival before the other predecessor's halo lands, so one rank's 512-row slab in one late chunk of one sliding layer is computed from a stale halo block, then propagates. Host-dependent rate: d02u02 / d04u20 hit it on almost every run, d02u14 / b08u08 never. NOT a fixed layer-6 defect (that was the first event on early runs).

Evidence: alternating the halo semaphore between consecutive sliding layers gave 0/11 events vs 11/11 baseline on event hosts (fork build) and 0/6 vs 3/6 on pre-fork main forced to 4096; forcing an early SDPA signal locally reproduces the block signature (error in the slab rows fed by rank r-2). Introduced by #57453 (2026-09-25, ring joint op); #63837 (11-05, 4096 default) only made it the default path; the fork (#63571) copied it.

Fix: per-predecessor arrival semaphores (key = source % hop_count on source-keyed layouts, hop-1 otherwise); model passes `sliding_ring_attention_ccl_semaphore_handles` (2 + CP size). Branch `kmabee/gemma4-sliding-halo-arrival-sems` (`0ef3bd214f1` on main `54effbfbb42`), pushed, PR NOT opened (needs Kyle's OK); description at `~/debug-docs/gemma4_migration_kv_host_variance-64697/PR_DESCRIPTION_SLIDING_HALO_ARRIVAL_SEMS.md`. Perf-neutral (within 0.2% at 2k/4k/8k). The parent `ring_joint` op still has the race (follow-up).

**How to apply:** read `~/debug-docs/gemma4_migration_kv_host_variance-64697/FINDINGS_1107.md` (results, rounds 1-6, origin, fix) before touching this; scratch tooling (per-slab KV hash diag, `KV64697_FAST_DIAG`, `diag_events.py`) is on branch `kmabee/scratch-kv64697-diag` and in `/data/kmabee/runs_kv64697/`. Related: [[gemma4-sliding-sdpa-fork-handoff-1030]], [[lazy-fabric-buffer-zero-fill-race]].
