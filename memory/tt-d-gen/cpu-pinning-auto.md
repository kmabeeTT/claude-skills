---
name: cpu-pinning-auto
description: "Automatic spinner/mask-thread CPU placement replacing the worker CPU keys (Nov 10-12 2026) — where the code, results, findings doc and v2 page are"
metadata:
  node_type: memory
  type: project
  originSessionId: d1ede8c9-76f1-4c9d-b17c-e83a968a497e
  modified: 2026-11-12T08:20:00.000Z
---

CPU pinning for decode workers, Nov 10-12 2026, on bh-glx-120-b09u08. The findings doc that covers everything (the whole-host cost, the 0 µs mask roofline, automatic placement, design decisions, the Nov 12 robustness runs, and Aleks's "one place / no config surface" feedback) is debug-docs `tt_dgen_structured_outputs-2212/cpu_pinning_findings_1111.md` (last pushed in aa74b11), with the per-day reports beside it.

- **Code:** branch `kmabee/structured-outputs-cpu-pinning-auto`, pushed to tenstorrent/tt-d-gen on Nov 12, with no PR opened. It is `fac22027` (the pinning commit) plus `efdb4ce6` (mask pages), on the mask-delivery PR head `adab75f2` (restacked Nov 12 after the shared-queue commit `962d78f8` landed on #2473). All placement logic is in `engine/src/runtime/thread_cpus.{hpp,cpp}`. The worker picks the three least-loaded idle cores of one cache from a 1 s `/proc/stat` sample, claims them per core in `/dev/shm`, puts the mask threads on the rest of that cache, and has no worker keys. The off switch is `TT_DGEN_THREAD_CPUS=off`. The bench variants are `kmabee/so-auto-thread-cpus-bench` and `kmabee/so-auto-revert-bench`. The PR body draft is debug-docs `pr_c_auto_description.md`, and the Slack draft is `/data/kmabee/glx_autopin_1111_0353/slack_auto_pinning.md`.
- **Pages:** v1 is https://claude.ai/artifact/CQcXP8yVahQEKHM6kGLCsV (opt-in keys). Leave it alone unless Kyle says otherwise. v2 is https://claude.ai/artifact/UtzJHexouLhadQK7xJqwp3 (automatic, private), from `/data/kmabee/glx_autopin_1111_0353/artifact/decode_worker_cpu_placement.html`.
- **Results:**
  - **Galaxy:** at GLM-5.3's rate it costs ~0, as today. At a 3 µs step the guided cost goes from 15-20% to 5%. The 0 µs roofline goes from 248K to ~350K masks/s.
  - **QB2:** it is even with today at realistic rates, and takes a 4-CPU budget from −3.4% to −0.8%. WEKA's light poller on CPU 1 is why the pick uses the least-loaded cores.
  - **Nov 12 robustness:**
    - Off measured the same as a revert build.
    - Two workers started together took different caches, and both kept the gain.
    - With 28 or 80 busy loops on the host it matched off. Most workers then find no room and fall back.
    - At 80 stages (SC20) with 16-32 users the cost is ~0 in any layout. A 4-CPU worker with a full 80-stage pipeline costs −2.2% unpinned and −0.1% pinned.
    - One unexplained 0 µs collapse on the fallback path (code identical to off) did not recur.
- **Mask-thread placement:** keeping the mask thread on the spinners' cache is what helps at fast steps; pinning the spinners alone does not.

**Why:** Aleks (code owner and manager) asked to ship pinning on by default with no new config, tested on mocks, and reverted if it regresses.

**How to apply:** opening a PR, or folding this into PR C, is Kyle's call, so ask first. Prefill workers also get placement, unmeasured; this is flagged, not changed. Decode and prefill workers still get no cpuset from a launcher; see [[structured-outputs-work]].
