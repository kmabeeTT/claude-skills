---
name: ring-sdpa-metadata-silent-prefix-fallback
description: ring SDPA metadata path silently treats an invalid kv_actual_isl (non-tile, or a wrapping Q with a one-slot halo) as prefix 0; host validation is the only guard
metadata:
  type: project
---
On the ring joint SDPA metadata path, `bounded_kv_actual_isl` / `bounded_sliding_kv_actual_isl` (`sdpa/device/kernels/dataflow/metadata_scalar_read.hpp`) ASSERT (compiled out in release) and then fall back to prefix 0 on every consumer: a non-tile-aligned prefix, or a mid-slab start whose Q wraps a slab while the halo buffer has only one slot (`gather_seq = halo`). The KV writer (`update_padded_kv_cache`) still uses the real start, so attention is silently wrong. The halo slot count is inferred from the gather buffer's rows / halo rows.

**Why:** found while scoping Gemma4 mid-chunk resume on 2026-10-19 (handoff: ~/debug-docs/gemma4_mid_chunk_resume-noissue/HANDOFF_GEMMA4_MID_CHUNK_RESUME.md, "Findings"). Also, `update_padded_kv_cache` has no capacity clamp: a padded chunk starting within one chunk of the cache end writes into the next head or slot.

**How to apply:** any caller that relaxes chunk-aligned starts must size the sliding halo for two slots and validate tile alignment and the cache end on the host. K split plus a mid-slab start is untested in the op, so run an op-level test before trusting it. Related: [[gemma4-ring-sdpa-ksplit]], [[gemma4-batching-poc-traps]].
