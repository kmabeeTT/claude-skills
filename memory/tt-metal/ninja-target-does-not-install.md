---
name: ninja-target-does-not-install
description: In tt-metal, `ninja <target>` links into build_Release/ttnn/ but Python keeps loading the stale build/lib copy; only `--target install` updates it
metadata:
  type: feedback
---

Building a single tt-metal target (`ninja -C build_Release ttnncpp`) reports
"Linking CXX shared library ttnn/_ttnncpp.so" and exits 0, but that writes
`build_Release/ttnn/_ttnncpp.so`. Python loads a *different* file:
`ttnn/ttnn/_ttnn.so` has a DT_NEEDED on `../../build/lib/_ttnncpp.so`, and nothing in
build.ninja copies between the two. `build_metal.sh` uses `target="install"`, so the
only command that refreshes what the tests import is:

    cmake --build build_Release --target install

**Why:** a partial-target build looks completely successful while every device test
silently runs the previous binary. Here it cost ~40 min and three misleading device
results — two tests "passing" on old code, and a third failing on a `TT_FATAL` that had
already been deleted from the source.

**How to apply:** after editing tt-metal C++ host code, build with `--target install`,
and confirm with `ls -la build_Release/lib/_ttnncpp.so` that its mtime is newer than the
edit before trusting any device run. Kernel (.cpp under `kernels/`) edits are JIT-compiled
and do NOT need this — which is what makes the mixed case so confusing, since a kernel
change can take effect while the host change beside it does not. See
[[tt-galaxy-fabric-run-hygiene]].
