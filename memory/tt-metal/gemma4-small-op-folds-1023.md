---
name: gemma4-small-op-folds-1023
description: "Gemma4 small-op folds re-measured 2026-10-23 on main 8c4b47a4bd5 (b08u08, RevB): all three together only -0.3% at 256k; only the gather->one-hot matmul is above noise (2k)"
metadata:
  node_type: memory
  type: project
  originSessionId: d769d672-592d-4fc4-9390-3b2e5fe0401b
  modified: 2026-10-23T18:14:14.953Z
---

Re-measured 2026-10-23 on bh-glx-120-b08u08 (14 kW RevB), main `8c4b47a4bd5`, logs `/data/kmabee/runs_folds_1023` (parse with `parse_sweep.py` there):
- All three folds: −0.3% at 256k at every chunk size; first chunk −0.5 to −0.9%. The 10-09 figure (−2.1% 8k first chunk) did not hold.
- FPU GEGLU multiply alone: only 4096 moves (−0.6% / −0.3%); 0 at 2048.
- Gather → one-hot matmul alone: 2048 53.75 → 53.5 ms, 10.308 → 10.284 s; bit-exact (new device test). Same code as #60157's `_permute_columns`.
- LLK QKV blockings: null end to end.
- Noise: 2048 repeats to 0.1 ms; 8192 first chunk varies 0.6% between passes.

**Why:** the reviewer said on #60157 that the permutation is a "small win for lots of code", and the user wants to avoid PRs like that. Branches: `kmabee/gemma4-kv-permute-matmul` (gather only, plus test), `kmabee/gemma4-small-op-folds-polish` (all three, after /simplify). Neither is pushed. Drafts: prefill-docs `gemma4/perf_understand/{pr,issue}_draft_small_op_folds.md`.

**Decision (10-23):** none raised as PRs, no issue; polished commits force-pushed to `kmabee/gemma4-small-op-folds` (old tip tagged `kmabee/gemma4-small-op-folds-1009`); results in gist 803c6c9b2f928980867b3fc2501bca0a.

**How to apply:** don't re-measure or re-propose the FPU multiply or the LLK blockings as standalone PRs without new evidence. The root-cause fix for the gather is in the op (`ttnn.gather` reads per element). Related: [[gemma4-prefill-chunk-size-win]].
