---
name: structured-output-tracker
description: "Where the structured-output (tt-d-gen#2212) effort's top-level tracker lives, and to update it when statuses change"
metadata:
  type: project
---

The structured-output effort has one top-level tracker for Kyle: debug-docs `tt_dgen_structured_outputs-2212/STRUCTURED_OUTPUT_TRACKER.md`, started Nov 13 2026. It covers:
- the tt-d-gen PRs in flight (#2473, #2474, #2476) and their next steps;
- the CPU-placement PR that is ready but not raised;
- the tt-d-gen issues;
- XGrammar upstream (#1043, #1052-1055, #1071-1073, the prepared row cache);
- performance and the waiting-on list;
- links to every page and status doc.

The folder `README.md` and `PR_RAISE_PLAN.md` point to it. Performance follow-ups live in `STRUCTURED_OUTPUT_PERF_TODO.md` beside it.

**Why:** Kyle found it hard to keep track of the effort across sessions.

**How to apply:** start from the tracker. When a PR, issue or upstream item changes state, update its row, and keep its "Status in one paragraph" current. See [[mask-throughput]], [[cpu-pinning-auto]], [[structured-outputs-work]].
