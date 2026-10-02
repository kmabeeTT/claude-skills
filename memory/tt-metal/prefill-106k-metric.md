---
name: prefill-106k-metric
description: The "100k" prefill metric in Gemma4 tables/PRs is 106,496 tokens (13 chunks of 8k), not 100k or 102,400
metadata:
  type: feedback
---

Report the mid-context prefill number as the first 106,496 tokens (13 x 8192; 26 x 4096; 52 x 2048), labelled "106k", in tables, MD files and PR descriptions. Kyle tracks this in offline discussions and other PRs.

**Why:** on 2026-09-26 I had reported "100k" as chunks ending at or before 102,400, which is 12 chunks (98,304 tokens) at 8192, so it did not match the tracked number.

**How to apply:** sum the traced per-chunk device times with chunk end <= 106496 from the 256k run (runs_0925/lib.sh does this and prints `106k=`), and say it is a prefix of the 256k run, not a standalone run.
