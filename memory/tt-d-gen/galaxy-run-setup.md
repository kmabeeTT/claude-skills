---
name: galaxy-run-setup
description: "How to run QB2-built tt-d-gen binaries on a BH Galaxy host (container, chip selection, ctest path), and its PCIe x8/x1 chips"
metadata:
  node_type: memory
  type: project
  originSessionId: e9b80ae1-64f9-43f6-adc8-6d8bbf96baaf
  modified: 2026-11-05T07:38:28.812Z
---

QB2 (qb2-120-p02t05, Ubuntu 24.04, glibc 2.39) and the BH Galaxy hosts (e.g. bh-glx-120-b08u02, Ubuntu 22.04, glibc 2.35) share `/data` over NFS, so a Galaxy session can run QB2's build dirs, but not natively: the binaries and tt-metal's libraries need GLIBC_2.38 / GLIBCXX_3.4.32. Verified Nov 4: they run unchanged in `ghcr.io/tenstorrent/tt-metal/tt-metalium/ubuntu-24.04-dev-amd64`. The wrapper `/data/kmabee/glx_device_runs_20261104_190912/bin/incont.sh <name> <chip|none> <workdir> "<cmd>"` passes one chip through and sets `TT_VISIBLE_DEVICES` to its BDF. Inside a container that sees one chip, the host index fails ("Valid integer IDs are between 0 and 0"). A 1x1 mesh opens with no mesh descriptor. QB2 build dirs call ctest at `/opt/ttmlir-toolchain/...` (CMake 4.4.3); the wrapper mounts a pip `cmake==4.4.3` there. The in-tree Dynamo venv needs `/usr/bin/python3.12`, which the Galaxy lacks; make a separate one with `setup_router_env.sh --venv <dir>`.

Building on the Galaxy also works in that container (verified Nov 5; recipe in `/data/kmabee/glx_inbox/build_probe_report.md`). Use cmake directly, not `build_dgen.sh`, which repoints the repo-root `compile_commands.json`. Set `-DCPM_SOURCE_CACHE` outside the tree. A `--dynamo` build writes `_tt_engine.abi3.so` / `_tt_dynamo_kv.abi3.so` into the source tree, so while another host owns the tree, build from a `git archive <sha>` snapshot. The image has no libzmq; build it from the CPM cache into a prefix and set `PKG_CONFIG_PATH` (there is one at `/data/kmabee/glx_build_probe_1105_0230/zmq-prefix`). The container venv `/data/kmabee/glx_device_runs_20261104_190912/venv` has `tt_engine.pth` pointing at `/data/kmabee/tt-d-gen/bindings/python`. Running a snapshot's tests with it needs `PYTHONPATH=<snap>/bindings/python:<snap>/adapters/dynamo`; without it, workers die with "Critical nanobind error".

On each of a Galaxy's 4 PCIe roots, one chip is Gen4 x8 (bus 06/46/86/c6; device 5 on b08u02) and seven are x1. Device-pull masks: about 115K masks/s on x8, about 67K on x1 (link-bound). See [[structured-outputs-work]].

**Why:** a fresh Galaxy session spent its setup time rediscovering all of this.
**How to apply:** for Galaxy device or bench runs from QB2's trees, use the container wrapper, a BDF for the chip, and an x8 chip for mask throughput.

Nov 5 (b09u08): never run two chip test containers at once. Socket ids (`dgen_h2d_<pid>_N` in /dev/shm) are keyed on the PID, containers share /dev/shm (`--ipc=host`) but each has its own PID namespace, so two containers can pick the same id: one test then waits forever for its descriptor (AbortUnderConcurrency timed out at 600 s). Two ctests on one build dir also double-register gtest discovery. /home is per box: the container venv's interpreter (`~/.local/share/uv/python/cpython-3.12.12`) must be installed on each host (`uv python install 3.12.12`). The 24.04 image must be pulled per host by digest. Same chip layout as b08u02: device 5 = x8 `0000:06:00.0`, device 4 = x1.
