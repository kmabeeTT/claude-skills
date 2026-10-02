---
name: ttdgen-prefill-migration-prebuilt
description: tt-metal's prefill KV-migration stack is already built and model-agnostic, and mistral_small_4 is already registered in it — items 1-3 of the d-gen disagg ask are wire+verify, not implement
metadata:
  type: project
---

Scoped 2026-09-20 for the Mistral Small 4 disaggregated P&D ask (Aleks, 2026-09-19; Kyle owns prefill, Sungjoon decode, Het chunk tables). The seed handoff assumed the prefill side needed building. It does not: `models/demos/common/prefill/runners/prefill_runner.py` already brings up layer-ack routing, device-map export, chunk-table build and the migration-worker handshake for any registered model, `mistral_small_4` is in `ADAPTER_PATHS` with a manifest, and the DeepSeek/Kimi runtime Mistral inherits implements every migration hook. Layer acks are unconditional now — `PREFILL_ENABLE_LAYER_ACK` no longer exists (the gemma4 binding still sets it; dead config).

Three findings worth not re-deriving:
- The chunk table expresses prefill's contiguous and decode's round-robin layouts **directly, no re-shard**. `migration_strategy_builder.cpp` pairs chunks by (config, slot, layer, position) and enforces only matching `chunkNTokens`, per-chunk `sizeBytes`, config coverage per layer, and a shared global layer-id space. Slot, position offset, chip, bank and mesh shape are all free to differ.
- Mistral's numbers for that contract: 1 config, 36 layers, `chunk_n_tokens=32`, `chunk_size_bytes=10880` (320-wide bfp8 = 10 tiles x 1088).
- d-gen `main` does NOT have KV migration (docs/disaggregated_prefill_and_decode_with_dynamo.md says so outright), so e2e is blocked on someone else's branch. Gemma's whole model integration was 4 files + one `chunk_aligned_start` engine change; `anatarajan/kimi-prefill-disagg-20260919` is a single bug fix, not a template.

**Why:** the ask reads as four build items and is really one build-free verification path plus two people-blocked decisions.
**How to apply:** start from the two gates in `models/demos/common/prefill/docs/PREFILL_MIGRATION_TESTING.md` (mock, then loopback) — Gate 1 needs the tt-metal tree only. Full write-up: `~/debug-docs/mistral4_prefill_planning-noissue/part3/TTDGEN_DISAGG_PREFILL_PLAN.md`. Related: [[mistral4-disagg-reload-ring-260919]], [[mistral4-prefill-has-no-lm-head]].
