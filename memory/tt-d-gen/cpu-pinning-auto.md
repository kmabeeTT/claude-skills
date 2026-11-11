---
name: cpu-pinning-auto
description: "Automatic spinner/mask-thread CPU placement replacing the worker CPU keys (Nov 10-11 2026) — where the code, results and findings doc are"
metadata:
  node_type: memory
  type: project
  originSessionId: d1ede8c9-76f1-4c9d-b17c-e83a968a497e
  modified: 2026-11-11T06:20:22.334Z
---

CPU pinning for decode workers, Nov 10-11 2026, on bh-glx-120-b09u08. The findings doc that covers everything (the whole-host cost, the 0 µs mask roofline, automatic placement, design decisions, and Aleks's "one place / no config surface" feedback) is `/data/kmabee/glx_autopin_1111_0353/cpu_pinning_findings_nov10_11.md`. It still needs folding into debug-docs `tt_dgen_structured_outputs-2212/`.

- **Code:** local, unpushed branch `kmabee/so-auto-thread-cpus`, one commit `48f69b40` on the CPU-pinning PR head `c9116722`. It drops the `control_cpu`/`writer_cpu`/`reader_cpu` worker keys. The worker picks three idle cores on one cache (busy check from `/proc/stat`, flock claims in `/dev/shm`) and puts the mask threads on the rest of that cache. The off switch is `TT_DGEN_THREAD_CPUS=off`. The bench variant is `kmabee/so-auto-thread-cpus-bench`.
- **Results:** at GLM-5.3's rate it costs ~0, as today. At a 3 µs step the guided cost goes from 15-20% to 5%. The 0 µs roofline goes from 248K to ~350K masks/s.
- **Mask-thread placement:** keeping the mask thread on the spinners' cache is what helps at fast steps; pinning the spinners alone does not.

**Why:** Aleks (code owner and manager) asked to ship pinning on by default with no new config, tested on mocks, and reverted if it regresses.

**How to apply:** before any PR, fold this commit into the CPU-pinning PR, and ask Kyle first. Decode and prefill workers still get no cpuset from a launcher; see [[structured-outputs-work]].
