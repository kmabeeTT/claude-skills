---
name: mistral4-l36-chunked-padded-layer32-cliff
description: "The L36 chunked_padded layer-32 PCC cliff is a raw-PCC measurement artifact of Mistral4's massive activations, not a device defect — gate on nPCC"
metadata:
  type: project
---

`test_mistral4_prefill_transformer_chunked_padded` at **L36 notrace** used to fail `decoder-output min PCC < 0.88`: a smooth bf8_b decay 0.999 (layer 0) -> 0.967 (layer 31), then an apparent **cliff at layer 32** (0.162 / 0.171 / 0.180 for layers 32/33/34).

**It is a measurement artifact, fully explained and fixed.** Mistral Small 4 develops massive activation channels — measured absmax/std **252 at layer 31, 220 at 32** against a std of ~2. A raw PCC over the whole hidden state is then dominated by a few hundred outlier channels rather than the layer. Per-token RMS-normalised PCC (`nPCC`) over the same 840 (chunk, layer) comparisons is **0.9727 / 0.9722 / 0.9721** at layers 32/33/34 — a smooth continuation of layer 31's 0.9721, no discontinuity anywhere.

**The repo already knew this for the single-shot path.** `test_prefill_transformer.py` computes both scores (`_token_normalized`, `_compare_intermediate_pcc`) and `MISTRAL4_THRESHOLDS` sets `metric="npcc"`; `_threshold_for` gates hidden-state stages on nPCC while KV rows stay raw. The CI leg "Mistral-Small-4-119B prefill transformer accuracy 5k" **passes at 36 layers while logging the identical cliff** (layer 32 raw PCC 0.331, nPCC 0.9908) — proof the cliff is metric-side, not device-side.

`test_prefill_transformer_chunked.py` had simply never adopted the policy: it used raw `comp_pcc` against module-level `LAYER_PCC_THRESHOLD = 0.88`. Fixed 2026-08-29 by adding `_token_normalized` + `_NPCC_GATED_VARIANTS = {"mistral_small_4"}` and gating on nPCC for listed variants only (Kimi/DeepSeek/GLM keep the raw score); both scores are always logged. L36 mid15k and full55k then pass at min 0.973 / 0.972.

**Two traps around this test:**
- **L1 validates almost nothing.** `n_decoder_layers = num_layers - 1`, so at L1 the decoder assert covers zero layers and only one layer-0 KV number prints. Layer-0 KV depends only on token ids, so `mid15k` and `full55k` print *identical* PCC (nope=0.999923 pe=0.999949).
- The **traced** L36 rows fail separately and legitimately: `llama4 query scale on the metadata path needs ChunkMetadata.llama4_scale (allocate with RotarySetup.make_llama4_scale_buffer, refresh via write_chunk_metadata)` — genuinely unimplemented plumbing, unrelated to any golden or metric.

Neither Blaze CI nor `run_mistral4_base_suite.sh` runs this test above L1, which is why the raw-PCC gap survived.

**Why:** the obvious reading — a new golden broke deep layers — is wrong in two ways at once, and both goldens and the device are fine.

**How to apply:** when a deep-layer PCC collapses on this model, check nPCC before suspecting the device. See [[mistral4-55k-golden]].
