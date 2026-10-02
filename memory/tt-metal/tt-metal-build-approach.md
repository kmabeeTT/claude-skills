---
name: tt-metal-build-approach
description: Kyle builds tt-metal from source on the host (not Docker) because the work is editable kernel/C++/binding iteration
metadata: 
  node_type: memory
  type: project
  originSessionId: 5655c723-ac00-46e5-9902-829201b86c19
  modified: 2026-08-14T16:55:30.088Z
---

For tt-metal work, the source/host build path is the right one, not the container path:
`INSTALLING.md` scopes containers to quick eval and demos, and the source path to "changing
tt-metal source code / editable local builds / iterating on kernels, C++, or Python bindings" —
which is what this work is.

Docker is also actively unhelpful on these boxes: the available dev containers bind-mount the
home/data tree read-write, so tt-metal inside is the *same checkout* as the host — no isolation
benefit, just an extra layer.

**Why:** this conclusion was re-derived independently on two different machines (QB2 4x p150, and
[[build-host-bh-glx-110-a10u08]]), so it's the standing default rather than a per-box call.

**How to apply:** `git submodule update --init --recursive` (checkouts predating
`--recurse-submodules` have all 4 uninitialized), then `./build_metal.sh`, then `./create_venv.sh`.
Two undocumented traps: piping the build through `tee` makes `$?` report tee's status, hiding a
failed CMake configure — use `(./build_metal.sh; echo "EXIT=$?") | tee build.log`; and the SFPI
toolchain FetchContent download hits transient network failures (`REFUSED_STREAM`) that just need
a retry.
