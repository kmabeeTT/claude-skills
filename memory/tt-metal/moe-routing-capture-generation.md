---
name: moe-routing-capture-generation
description: How to generate expert_routing_<model>.safetensors for the dispatch/combine perf test, and the three traps that silently produce a wrong capture
metadata:
  type: project
---

`test_dispatch_combine_perf` replays a captured MoE routing file, `expert_routing_<model>.safetensors`
(validated by name in `tt/moe/init_helpers.py`). **No generator exists in the tree** — the dsv3 /
kimi26 / glm52 files came from a local patch on PR #51426 and were shared as PR attachments. The
format is documented in commit `91209fb1ea3`'s body.

To generate: hook `indices` where the gate returns it in `tt/moe/tt_moe.py` (`scores, indices,
gate_logits = self.gate(...)`), `ttnn.to_torch` each device shard, and save one int32 key per layer
named `expert_ids_layer_<N>`, shaped `(dispatch_group_size, seq_len_per_chip, num_experts_per_tok)`,
holding **raw global** expert ids — the per-column remap happens in `load_captured_routing`.

**Why:** three traps each produce a plausible, non-erroring, wrong capture, and cost 4 galaxy runs to find.

**How to apply:**
1. Capture from the **padded** test, not `..._chunked_no_pcc` — the no_pcc leg uses *synthetic* token
   ids by design, so its routing is meaningless. For mistral4 use
   `test_mistral4_prefill_transformer_chunked_padded -k "... full55k and notrace"`.
2. **Every chunk is padded to the full window on device**, so tensor width cannot distinguish real
   from padded (a 1,024-token chunk still reads 640 tokens/chip). Gate on `actual_isl` — it carries
   the per-chunk real length — and take the first chunk where `actual_isl == chunk_size`.
3. Identify the SP shards **by mesh coordinate** (row-major, so column 0 is device indices 0,4,..,28),
   never by value-deduplicating the 32 device tensors: two chips can route identically. Use equality
   only to assert the 4 TP columns of a row are replicas.
4. The padded leg builds `kv_only_last_layer=True`, so the **last layer's MoE never runs** — you get
   N-1 layers. For mistral4 that is layers 0..34, not 0..35.

Validate by calling `load_captured_routing(...)` directly and checking all experts appear.
Related: [[mistral4-per-layer-moe-variance]], [[pp4-perf-harness-traps]].
