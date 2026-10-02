---
name: merge-gate-gcc12-sweep
description: "PR CI (Sanity/L2/Blaze) builds only with clang; the gcc-12 Release sweep runs only in Merge Gate, which skips on pull_request - dispatch it before merging C++ changes"
metadata:
  node_type: memory
  type: project
  originSessionId: 002d1d50-3012-49ce-a585-e77c4d0e6f00
  modified: 2026-10-02T03:03:16.583Z
---

`merge-gate.yaml` skips every job on `pull_request`; it runs on `merge_group` and `workflow_dispatch`. Its `build-sweeps`
matrix is the only place gcc-12 (Ubuntu 22.04 Release), gcc-14, clang-20 libc++ and Debug builds run. Sanity, L2 and
Blaze build once with clang-20. Local build_Release here is clang and has tests OFF (gtests never compile locally).

**Why:** 2026-10-02 #57998 (green on all PR CI) failed in the merge queue: gcc-12 `-Werror=range-loop-construct` on
`for (const auto [a, b] : {std::pair{...}, ...})` in a new gtest. Clang and gcc-14 accept it. Fix: `const auto&`.

**How to apply:** before asking the user to merge a PR with new/changed C++ (esp. gtests), run
`gh workflow run merge-gate.yaml --ref <branch>` and wait for the build-sweeps jobs. Quick local check for a light
TU: `g++-12 -std=c++20 -Wall -Werror -fsyntax-only -I ttnn/cpp -I ttnn -I . -isystem <.cpmcache gtest include> file.cpp`.
A PR in the merge queue rejects pushes; dequeue via GraphQL `dequeuePullRequest` first.
