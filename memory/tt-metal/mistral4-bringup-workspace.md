---
name: mistral4-bringup-workspace
description: "Where the Mistral Small 4 prefill work lives — canonical checkout, checkpoint, caches, and how the branch was moved between worktrees"
metadata:
  node_type: memory
  type: project
  originSessionId: e0807dbd-fc99-40c9-8b3b-5b0292331694
  modified: 2026-08-17T17:58:06.617Z
---

Mistral Small 4 119B prefill bring-up (started 2026-08-17). Working state that is not derivable
from the repo:

- **Canonical checkout: `/data/kmabee/tt-metal`** (as of 2026-08-17). Branch
  `kmabee/mistral-small4-bringup` was moved here from the `/home/kmabee/ttm-main` worktree.
  `/home/kmabee/ttm-main` still exists, **detached at the same commit and still built**, as a
  fallback — that is how the move was done: git refuses to check out a branch that another worktree
  holds, so `git checkout --detach` in `ttm-main` frees the name without deleting its 28 GB build.
- **The rebuild after the move cost ~5.5 min, not the ~40 I expected** — 1679 C++/CMake files differ
  between the gemma4 and mistral branch bases (384 main-commits apart), but ccache already had the
  objects. Don't pre-emptively avoid a branch switch here on rebuild-cost grounds.
- **Checkpoint: `/data/kmabee/models/Mistral-Small-4-119B-2603`** — 113 GB, HF-format
  `model-*.safetensors` only. `HF_TOKEN` is already in the environment.
- **Caches live outside every checkout, in `/home/kmabee/`**: `mistral4_ttnn_cache` (65 GB) and
  `mistral4_ref_cache`. Keyed `{variant}_{arch}_{N}dev/{sp}x{tp}`, not by path, so they survive
  moving the branch. Without `TT_MISTRAL4_PREFILL_TTNN_CACHE` the 36-layer row costs 870 s not ~54 s.
- **The venv is uv-managed and has no `pip`.** Install extras with
  `VIRTUAL_ENV=$PWD/python_env ./python_env/bin/uv pip install <pkg>`. `create_venv.sh` refuses to
  overwrite an existing `python_env` without `--force`, which is usually what you want.
- Scripts kept outside git at `/data/kmabee/mistral4_repro_logs/`: `00_build.sh`, `10_reproduce.sh`,
  `20_serve.sh`, plus one log per reproduced row.
- A `git worktree add` onto `/data` (NFS) times out and leaves stale file handles — put new worktrees
  on local disk (`/home/kmabee`).

**Why:** the checkout, the caches and the venv tooling are all in non-obvious places, and getting any
of them wrong yields either an 870 s run or plausible-but-untrustworthy numbers from a stale tree.

**How to apply:** `cd /data/kmabee/tt-metal && export TT_METAL_HOME=$PWD PYTHONPATH=$PWD`, export the
two cache vars and `MISTRAL4_HF_MODEL`, then `./python_env/bin/pytest ...`. Branch doc:
`MISTRAL_SMALL4_BRINGUP.md` at the repo root. Session record:
`~/debug-docs/mistral4_prefill_planning-noissue/training_log_2026-08-17.md`.
See [[build-host-bh-glx-110-a10u08]] and [[tt-metal-build-approach]].
