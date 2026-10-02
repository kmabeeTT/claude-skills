---
name: data-checkout-venv-home-pin
description: "A tt-metal checkout on shared /data has a python_env pinned to $HOME, so it breaks on every other box; repoint it at /usr/bin/python3.10 (the old /data/kmabee/uv-python target was deleted 2026-09-06); stale CMakeCache and PCH entries need the same targeted repair"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 197d2be2-411b-4a5f-b4e2-1feb588af108
  modified: 2026-09-03T17:26:52.126Z
---

A tt-metal checkout under `/data/kmabee/` travels between bh-glx boxes (NFS) but its
`python_env` does **not**: uv writes the base interpreter as an absolute `$HOME` path, and
`$HOME` is local disk per machine. Symptom on the second box is
`python_env/bin/python: No such file or directory` — the venv looks present (`bin/`, `lib/`,
`pyvenv.cfg` all there), only the interpreter symlink dangles.

Fix, no rebuild and no re-pip (current version, since `/data/kmabee/uv-python` was **deleted** on
2026-09-06 mid-session on bh-glx-120-b03u02, breaking `tt-metal-2` and `tt-metal-3` at once):

```bash
cd <checkout>/python_env
ln -sfn /usr/bin/python3.10 bin/python
sed -i 's|^home = .*|home = /usr/bin|' pyvenv.cfg
```

It is 3.10.12 rather than the venv's original 3.10.19 — same `cp310` ABI, so the existing
site-packages and the locally built `_ttnn.so` load fine (verified: `import ttnn` plus a full
32-chip run). The original fix repointed at the shared `/data/kmabee/uv-python/cpython-3.10.19-...`
copy; do not use that path any more.

**Why:** it reads as a corrupt or half-built venv, so the reflex is to rebuild the environment —
tens of minutes — when it is a two-line repoint. Same root cause as `~/.local/bin` and
`~/debug-docs` not travelling between boxes.

**How to apply:** on any box, before assuming a checkout needs a rebuild, check
`ls -l <checkout>/python_env/bin/python` and `pyvenv.cfg`'s `home =`; if either points under
`/home/` (or the deleted `/data/kmabee/uv-python`), repoint both. See [[tt-galaxy-fabric-run-hygiene]].

**Update 2026-09-08 — the SAME dead paths are also baked into `build_Release/CMakeCache.txt`,
and the venv fix does not reach them.** A rebuild after a branch switch fails at configure with:

```
Could NOT find Python3 (missing: Interpreter Development.Module)
  Interpreter: Cannot run "/data/kmabee/tt-metal/python_env/bin/python3"
  Development: Cannot find "/data/kmabee/uv-python/cpython-3.10.19-.../include/python3.10"
```

Note the interpreter path is a **different checkout** (`tt-metal`, not `tt-metal-2`) — the cache
was seeded from wherever it was first configured. Three `UNINITIALIZED` entries need repointing;
wiping `build_Release` also works but costs a full rebuild instead of an incremental one:

```bash
sed -i \
 -e 's|^Python3_EXECUTABLE:UNINITIALIZED=.*|Python3_EXECUTABLE:UNINITIALIZED=<checkout>/python_env/bin/python3|' \
 -e 's|^Python3_INCLUDE_DIR:UNINITIALIZED=.*|Python3_INCLUDE_DIR:UNINITIALIZED=/usr/include/python3.10|' \
 -e 's|^Python3_LIBRARY:UNINITIALIZED=.*|Python3_LIBRARY:UNINITIALIZED=/usr/lib/x86_64-linux-gnu/libpython3.10.so|' \
 <checkout>/build_Release/CMakeCache.txt
```

Check `python_env/bin/python3` exists too (it is a symlink to `python`, so the venv fix covers it).

**Update 2026-09-15 — a third targeted build-tree repair: STALE PRECOMPILED HEADERS.** An
incremental build after a large rebase (812 files) failed with every object dying at once:

```
fatal error: file '<build>/CMakeFiles/metal_common_pch.dir/cmake_pch.hxx' has been modified since
the precompiled header 'cmake_pch.hxx.pch' was built: size changed (was 444, now 612)
```

The re-configure regenerated `cmake_pch.hxx`, but **ninja thought the `.pch` was current because its
mtime was NEWER than the regenerated header's** — NFS clock skew on `/data` inverts the timestamps,
so only clang, which records the source size, caught it. `-Winvalid-pch -Werror` makes it fatal
rather than a silent fallback. Fix:

```bash
find <checkout>/build_Release -name '*.pch' -delete   # two of them: metal_common_pch, ttnn_pch_full
cmake --build build_Release --target install -- -j 48
```

~7 minutes vs ~1 hour for a `build_Release` wipe. Same lesson as the CMakeCache entry above: on
these NFS checkouts, a build failure after a branch switch is almost always a stale *specific*
artifact, not a corrupt tree.
