---
name: ttnn-build-symlink-missing
description: "ImportError _ttnncpp.so not found with an intact build_Release = the tree's build -> build_Release symlink is gone; _ttnn.so RUNPATH goes through it"
metadata:
  type: project
---

2026-11-02 in /data/kmabee/tt-metal: `import ttnn` failed with `_ttnncpp.so: cannot open shared object file` although build_Release/lib had every library. `_ttnn.so` RUNPATH is `$ORIGIN/build/lib:$ORIGIN/../../build/lib:$ORIGIN`, and the repo-root `build -> build_Release` symlink had vanished (worked 10-26). `ln -s build_Release build` fixed it, no rebuild.

**Why:** pytest exits rc=4 in seconds from conftest, so a perf queue silently records "no data".

**How to apply:** on that error, `ldd ttnn/ttnn/_ttnn.so | grep "not found"` and check `ls -la build` before rebuilding. Canary a scheduled queue's first run. Related: [[ninja-target-does-not-install]].
