---
name: gemma4-pcc-not-bit-reproducible
description: "Gemma4 256k KV PCC at chunk 8192 is NOT bit-reproducible: layers 0-12 match exactly run to run, drift starts at layer 13 (~0.00003 overall); compare layers 0-12 for value-identity claims"
metadata:
  node_type: memory
  type: project
  originSessionId: 170463d4-8ab0-424a-a66a-5dd1fd442cbc
  modified: 2026-09-30T01:36:25.487Z
---

Measured 2026-09-30 on bh-glx-120-c03u08 (tree tt-metal-3, branch kmabee/gemma4-prefill-0930 88729027a34):
`test_prefill_migration[mock-256k]` at GEMMA4_TEST_CHUNK_SIZE=8192, same build and code twice gave
0.981365 / min 0.9395 and 0.981330 / min 0.9393. In both, and against 0929's 0.981454 / 0.9398 run on a
different tree, layers 0-12 are equal to 6 decimals and the first difference is layer 13 (a sliding layer);
per-layer error ratio stays 0.98-1.01.

**Why:** an earlier "bit-identical to the dev branch" PCC claim (09-29) was read as proof the test is deterministic,
and the first 8192 mismatch today looked like a code bug in a value-identical cleanup.

**How to apply:** to show a change is value-identical, compare per-layer minima for layers 0-12 (use
/data/kmabee/runs_0930/errratio.py and a first-differing-layer check), not the final overall PCC. Final-PCC
differences of a few 1e-5 (overall) / 1e-4 (min) are run-to-run noise. Not checked at 2048/4096. See
[[gemma4-kv-pcc-early-layer-method]], [[gemma4-pcc-test-gate-and-shm]].
