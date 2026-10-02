---
name: build-host-bh-glx-110-a10u08
description: "Constraints of the shared build host bh-glx-110-a10u08 (32-chip BH Galaxy, no sudo, NFS checkout, Forge pool outside SLURM)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5655c723-ac00-46e5-9902-829201b86c19
  modified: 2026-08-14T16:55:22.750Z
---

`bh-glx-110-a10u08` (the box holding `/data/kmabee/tt-metal`) is a **shared** 32-chip Blackhole
Galaxy — one ethernet-linked mesh, not independent cards like the QB2 4x p150 box. Constraints:

- **No general sudo.** Only a narrow NOPASSWD allowlist of TT cluster scripts (`tt_rm_shm.sh`,
  `tt_clear_metal_cache_on_alloc_node.sh`, etc.). `install_dependencies.sh` hard-requires EUID 0
  *even for `--validate`*, so it cannot be run at all — validate deps manually with
  `dpkg-query -W -f='${Package} ${Status}\n' <pkgs>`.
- **Not SLURM-managed.** Not in any of the ~50 partitions (those are bh-glx-*120* / bh-lb nodes);
  membership in group `bh_forge_machines_allowed` means it's allocated out-of-band from the
  Forge/tt-shield pool. Device arbitration is therefore social, not `salloc` — check for other
  users' containers before opening devices.
- **Repo lives on NFS** (`/data` = `10.32.13.1:/data`, chronically ~91% full). `/home/kmabee` is
  local ext4 with far more headroom; `build_metal.sh --build-dir` can put build output there.
- Ubuntu 22.04 / Python 3.10, so the clang-20 default toolchain applies (`gcc` is 11.4 — ignore it).

**Why:** the constraints differ enough from the QB2 box that the QB2 build handoff can't be
followed verbatim — see [[tt-metal-build-approach]].

**How to apply:** build freely (compilation never touches devices), but treat anything that opens
`/dev/tenstorrent` as needing coordination with whoever currently holds the box.
