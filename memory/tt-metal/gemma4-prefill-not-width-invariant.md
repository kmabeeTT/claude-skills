---
name: gemma4-prefill-not-width-invariant
description: "RETRACTED: Gemma4 prefill width-invariance was NOT broken; the real bug was multi-width model construction. Always run the single-vs-multi-width control before claiming a cross-width defect."
metadata:
  type: feedback
---

**2026-09-17, retracted same day.** I claimed Gemma4 CP prefill was inherently not chunk-width
invariant, that it predated my work, and that it invalidated the published 8192->32768 throughput
win ([[gemma4-prefill-chunk-size-win]]). **All three were wrong.**

What was actually true: **a model built with several widths does not reproduce a single-width
build's answer at a width they share.** Chunk 8192, one layer, identical `ring_cache` geometry
(65536 both ways): a `(8192,)` build gives std 0.883347, a `(4096,8192,32768)` build gives
0.928255 — **PCC 0.869, max_abs_diff 29.9**. The bug is in the variable-chunk implementation
(see [[gemma4-variable-chunk-poc]]), not the model.

**Why I got it wrong, and the lesson:** every cross-width comparison I made was taken *inside one
multi-width build*, i.e. inside the bug. A same-width replay control (PCC 1.0000) and a PCC-vs-depth
curve both looked like clean evidence of a real width dependence, and neither could see a defect
that is constant within a build. `ring_joint` passing against torch at every width and both ring
sizes should have been the tell that the op was fine.

**How to apply:** when two configurations of one model disagree, the control is not "re-run one of
them" — it is **build each configuration in isolation, in its own process, and compare the shared
case**. Only that separates "the configurations genuinely differ" from "constructing both perturbs
one". Cost here was ~2 min per process; I identified the control as missing, reported a conclusion
before running it, and it inverted the finding. Do not publish a cross-configuration defect without
it.

**Lead for whoever fixes the real bug:** single-build@8192 (0.883347) matches multi-build@**4096**
(0.883675), not multi-build@8192 (0.928255). Looks like per-width resources bound by
position-in-tuple or by `prefill_chunk_sizes[-1]` rather than the requested width. Suspects:
`VariableChunkPrefill.capture()` capturing N traces sequentially with overlapping intermediate
addresses, or the per-width RoPE tables. Repro: `_diag_singlewidth.py` pattern in
`tech_reports/Gemma4VariableChunkSize/` §4.
