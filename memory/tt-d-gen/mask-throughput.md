---
name: mask-throughput
description: "Galaxy host mask throughput with real schemas (Nov 12 2026): per-core fill capacity, worker numbers, the open required-rate question, and where the runs and doc are"
metadata:
  type: project
---

Mask throughput on a Galaxy host, measured Nov 12 2026 on bh-glx-120-b08u02 (EPYC 9354P), on the `-auto` + shared-queue stack. Doc: debug-docs `tt_dgen_structured_outputs-2212/mask_throughput_plan_1112.md` (pushed 71f7c1c). Runs and drivers: `/data/kmabee/glx_sharedq_1112/` (`bin/maskrate{2,3,4}.sh`, `bin/mr_tables.py`).

- **Capacity:** XGrammar fills with GLM-5.3's vocabulary scale linearly at about 33-39K masks/s per physical core. 16 cores give about 520-565K masks/s on real schemas. SMT adds about 15%. The four slow schemas (mlc-ai/xgrammar#1043) manage 7K per core.
- **Through the worker:** about 230-245K masks/s on typical schemas, where the mock pipeline itself is the limit. Use `GUIDED_BENCH_NO_MASK_LOG=1`, or the mock's 19 KB-per-mask log under its mutex caps the worker at about 20-48K.
- **GLM rates:** typical schemas cost ≤0.7% (steady state). The four slow schemas cost 2-15% even when no mask is late. A second mask thread removes late masks; more threads do nothing.
- **Required rate:** each Blaze token page carries one user, so masks/s = guided tok/s ≤ the model's decode rate. For GLM-5.3 on SC20 (32 slots, 80 × 69 µs) that is ≤5.8K/s (14.5K/s with a token every tick): one core. The voice chat's "64 users per 120 µs step, 550K/s" was never real. The open input is the decode-throughput target for later models. With the XGrammar fork it is 54K masks/s per core. The report is `mask_throughput_report_1112.md`, the page https://claude.ai/artifact/4KLX1ZbBqoSMJFcN1n5aFX, and the quick reproduction `engine/tools/mask_rate.sh` on branch `kmabee/so-maskrate-bench`.

- **Nov 13 deep dive:** best build is kmabeeTT/xgrammar `v0.2.9-plus-1043-fast-miss` @ 656e2c5 (parser row cache + counted-pattern fix): `mask_rate.sh` typical 259K masks/s on 1 core, 4.36M on 16, realistic replay 396K/core, masks bit-identical. The mask memo (`v0.2.9-plus-1043-mask-memo` @ c62215e, 205K/core) only helps random walks once misses are cheap. Findings: debug-docs `tt_dgen_structured_outputs-2212/mask_rate_deep_dive_findings_1113.md`. Work dir `/data/kmabee/mask_deep_1113` (harness `harness/xfb.cpp`, `cmpwalk.py` correctness gate, `xrl.sh` flock bench lock).

**Why:** at standup Kyle was asked for "masks/s on a Galaxy, with real schemas, up to 16 CPUs".

**How to apply:** quote per-core capacity and the tail, not the toy 0 µs roofline; derive the need from decode tok/s. Related: [[cpu-pinning-auto]], [[structured-outputs-work]].
