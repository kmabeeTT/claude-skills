---
name: tt-sbatch-build-time-limit
description: tt-sbatch's default 2 h build request exceeds cpu_only's 1 h MaxTime, so the build pends forever with PartitionTimeLimit; pass --build-time 01:00:00
metadata:
  type: reference
---

`tt-sbatch run`/`build` (Exabox login nodes, /usr/local/bin/tt-sbatch) defaults `BUILD_TIME=02:00:00`, but the `cpu_only` partition has `MaxTime=01:00:00` (checked 2026-10-26). The build then sits PENDING with reason `PartitionTimeLimit` and the chained test pends on Dependency behind it, which looks like a normal queue wait.

**How to apply:** submit with `--build-time 01:00:00` (or `export TT_SBATCH_BUILD_TIME=01:00:00`); to rescue a queued one, `scontrol update JobId=<build> TimeLimit=01:00:00` (users may lower their own limit). Other tt-sbatch traps: the build rsyncs `build_Release/` and `runtime/` back over the source tree with `--delete`, so use a dedicated checkout (`/data/kmabee/worktrees/tt-metal-sbatch`), never a tree you also build on the host; untracked files in the tree are rsynced every job. Gemma4 perf cmd file: `/data/kmabee/jobs/cmds/gemma4-galaxy-prefill-perf-sweep.sh`.

**Plain sbatch from slurm-login (no tt-sbatch) needs `ulimit -S -u "$(ulimit -Hu)"` in the job script.** slurm-login caps nproc at 512 and `PropagateResourceLimits=ALL` carries that into the job, so the tt-metal kernel JIT dies with `lto-wrapper: fatal error: posix_spawnp: Operation not permitted` (job 155161, 2026-10-26). With the fix, `/data/kmabee/jobs/gemma4_sweep_host.sbatch` (g4_perf all on the NFS tree, host not container) ran in 6:53 Slurm start-to-end incl. a 33 s glx_reset.
