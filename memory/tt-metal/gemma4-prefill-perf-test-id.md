---
name: gemma4-prefill-perf-test-id
description: "#58620 (main, 2026-10-01) renamed the Gemma4 canonical perf test id (no readback_final) and switched TOTAL to ms; lib.sh perf auto-detects"
metadata:
  type: project
---

#58620 (merged 2026-10-01, `4e6b44299ed`) simplified the canonical Gemma4 prefill benchmark:
- The test id lost the `readback_final` param: `test_prefill_long_context_traced[blackhole-ctx_256k-chunk8192-text-8x4]` (was `[blackhole-readback_final-ctx_256k-chunk8192-text-8x4]`).
- `[traced_perf] TOTAL 262144 tokens in ...` prints **ms** now (was s), and there is a new `[traced_perf] DEVICE 262144 tokens in ...ms` line. The per-chunk `device=...ms` lines (used for the 106k number) and `first=` are unchanged.

**Why:** a hard-coded old id makes pytest select nothing on a post-#58620 tree, and an `[0-9.]*s` TOTAL regex silently matches nothing.

**How to apply:** `runs_0925/lib.sh` `perf` picks the id by grepping the tree's `text_demo_prefill.py` for `readback_final`, and matches TOTAL in s or ms. Copies of the old command in `runs_sasha/*.sh` (the other session's) were not changed. See [[gemma4-prefill-chunk-size-win]].
