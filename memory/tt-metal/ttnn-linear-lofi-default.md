---
name: ttnn-linear-lofi-default
description: "ttnn.linear silently drops to LoFi when given a program_config or core_grid; bf16 accumulation, not fidelity, drove Gemma4 KV drift"
metadata:
  node_type: memory
  type: project
  originSessionId: 9cf77546-dee6-4647-9f1d-84d1e9f5bb83
  modified: 2026-09-24T19:15:33.598Z
---

`ttnn.linear`'s default math fidelity is HiFi2 only when it gets neither a `program_config` nor a `core_grid` (and the
inputs are not both bfp8/bfp4); otherwise LoFi. `packer_l1_acc` defaults on for bf16 output
(`matmul_device_operation.cpp` ~2826). So adding an explicit config or a core grid quietly lowers fidelity.

Measured on Gemma4-31B 256k prefill (2026-09-24):
- MLP: the deep-layer KV drift came from bf16 accumulation of K-block partials with explicit blocking. Restoring HiFi2
  with bf16 made it WORSE; LoFi + fp32 dest fixed it (fp32 halves the subblock budget, 8 -> 4 tiles).
- Attention: needs HiFi2 AND fp32; LoFi + fp32 still drifts badly. HiFi2 costs ~10 ms/chunk at chunk 8192, fp32 ~2 ms.
- #56862's MLP `core_grid` moved main's MLP HiFi2 -> LoFi (overall PCC 0.9752 -> 0.9734).

**Why:** a "blocking only" config change was assumed numerics-neutral; it was not, and the cost was misattributed to fp32.
**How to apply:** whenever a PR adds a program_config or core_grid to a matmul, state the fidelity explicitly and check
long-context KV PCC (see [[gemma4-kv-pcc-early-layer-method]]). Vary fidelity / fp32 / packer one at a time.
