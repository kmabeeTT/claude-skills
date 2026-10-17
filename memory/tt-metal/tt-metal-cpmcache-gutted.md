---
name: tt-metal-cpmcache-gutted
description: "/data/kmabee/tt-metal/.cpmcache was gutted (deleted files, broken .git) by 10-14; a configure fails with CPack 'license file not found' or 'Cannot find source file' under .cpmcache"
metadata:
  type: project
---

On 2026-10-14 the CPM source cache of `/data/kmabee/tt-metal` had ~30 entries with tracked files deleted and 14 with broken `.git` dirs (likely the /data cleanups, see [[data-cleanup-1010-symlinked-copies]]). Symptom: `cmake --build build_Release --target install` reconfigures and fails with `CPack license resource file ... LICENSE.txt could not be found` (nanomsg) or `Cannot find source file ... .cpmcache/protobuf/...`.

Fix used: `mv .cpmcache .cpmcache_broken_1014` and rebuild; CPM re-downloads everything into the same path (configure took ~18 min, the build itself was short because paths did not change). The broken copy is still there (1.4 GB) and can be deleted.

**Why:** the error names one dependency, so it looks like a single bad download, but most entries were damaged; fixing them one by one wastes rebuild cycles.

**How to apply:** on a CPM error under `.cpmcache` in a /data checkout, check other entries (`git -C <entry> status --porcelain | grep -c '^ D'`, and whether `git rev-parse --show-toplevel` resolves to the entry) before repairing one; if several are bad, move the whole cache aside.

`/data/kmabee/tt-metal-3/.cpmcache` is gutted the same way (nanomsg LICENSE.txt, seen 2026-10-14 building journey tags in new worktrees). Worktrees can instead pass `build_metal.sh --cpm-source-cache /data/kmabee/worktrees/cpmcache_remeasure_1014` (a fresh, now-populated cache). **Trap when switching caches:** a build_Release left by the failed configure keeps `CPM_DIRECTORY:INTERNAL` pointing at the old cache, and the next configure fails with `Unknown CMake command "CPMAddPackage"`. Move that build_Release aside and configure fresh.
