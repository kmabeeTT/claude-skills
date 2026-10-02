---
name: cross-worktree-pytest-syspath-trap
description: Running pytest with PYTHONPATH pointing at another worktree silently imports models from the cwd tree
metadata:
  node_type: memory
  type: feedback
  originSessionId: 63dd7621-3b47-4a0b-a1cf-74cf0026d469
  modified: 2026-09-23T03:55:45.991Z
---

pytest (prepend import mode) inserts the test rootdir at sys.path[0], ahead of PYTHONPATH, so `models.*` comes from whatever tree you `cd` into, not the one PYTHONPATH names. ttnn is a regular package under `<tree>/ttnn/ttnn`, so PYTHONPATH must name `<tree>/ttnn` explicitly (the editable install otherwise wins).

**Why:** nearly measured the wrong code when reusing one C++ build for several Python trees (2026-09-23).

**How to apply:** run each config FROM its own tree (cd + TT_METAL_HOME = that tree), put only the built tree's `ttnn/` first on PYTHONPATH, and log `models.__file__` / `ttnn.__file__` per run as a witness. Also: a device-job wrapper must BLOCK until `/dev/tenstorrent/*` is free, not just report it — see [[tt-galaxy-fabric-run-hygiene]].

**Kernel sources resolve from the cwd too (2026-10-02):** `resolve_path` in `tt_metal/impl/kernels/kernel.cpp` tries `cwd/<relative kernel path>` BEFORE TT_METAL_HOME. Running a full worktree with another tree's build compiled the worktree's `ring_joint_writer.cpp` against TT_METAL_HOME's headers -> `redefinition of 'struct KVPadRotationContext'` in the ncrisc/brisc JIT, and the test fails with "Runner exited with code 1". For a Python-only worktree, sparse-checkout it without kernels: `git sparse-checkout set --no-cone '/*' '!/tt_metal/' '!/ttnn/cpp/'`.
