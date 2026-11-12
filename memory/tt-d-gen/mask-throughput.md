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
- **Open:** the required rate depends on how many users Blaze GLM samples per LM-head step: one user per 69 µs tick needs 14.5K/s, 64 users per 120 µs step needs 550K/s. The device team has to answer this.

**Why:** at standup Kyle was asked for "masks/s on a Galaxy, with real schemas, up to 16 CPUs".

**How to apply:** quote per-core capacity and the tail, not the toy 0 µs roofline, and say which required-rate model is assumed. Related: [[cpu-pinning-auto]], [[structured-outputs-work]].
