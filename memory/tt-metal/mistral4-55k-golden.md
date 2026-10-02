---
name: mistral4-55k-golden
description: "The Mistral Small 4 56,320-token golden: staged on /mnt under blaze/mistralai and CI-green, generated with SDPA via PREFILL_REF_ATTN"
metadata:
  type: project
---

**Staged and CI-green as of 2026-08-29.** Lives at `/mnt/models/blaze/mistralai/Mistral-Small-4-Cache/golden/mistral4_56320_36L`, wired via the adapter's `prefill_trace_default` (no `PREFILL_TRACE_DIR` export), with CI row "Mistral-Small-4-119B chunked prefill padded accuracy 55k@5k (no trace)" (`test_type: mistral4_chunked_padded`, L36, timeout 24, budget `bh_sc1` 585 -> 609). Green on run 33231961362 in 11:31 — `1 passed`, `collected 8 items / 7 deselected / 1 selected`, scores **bit-identical to a local run** (decoder min 0.972055, KV min 0.963408, asserted layers 0..10 min 0.989793).

**`/mnt` IS the filesystem CI sees** — the handoff doc left this unverified. The CI row exports no `PREFILL_TRACE_DIR`, so a pass is only reachable if the runner read the golden through the adapter default on `/mnt`.

**Staging notes that cost time:** the handoff's suggested `deepseek-prefill-cache/golden/` is **not writable by kmabee** (`ipotkonjak:1002`, and no subdir of it is writable either). Everything Mistral moved under `blaze/mistralai` (ssalice, 2026-08-28) — checkpoint, `Cache/CI` weight cache already in the `mistral_small_4` spelling, `Cache/mla_ref`, `Cache/host_ref` — group `tt-cache`, which kmabee is in. After `rsync -a`, **fix the group**: it preserves local ownership and drops the setgid bit the rest of the tree uses (`chgrp -R tt-cache`, dirs `2775`, files `664`).

Source copy: `/data/kmabee/mistral4_golden_traces/mistral4_56320_36L` — 34 GB, 36 layers, 56,320 real tokens (no padding), fp32 `kv_cache/` + `hidden_states/`, `next_token_id=2837` @ pos 56319. Prompt: `/data/kmabee/mistral4_prompts/test_prompt_60k.json` (InfiniteBench longbook_qa_eng id=111, 60,000 tokens). Wrapper: `/data/kmabee/mistral4_prompts/run_golden_55k.sh`. (This /data copy is the source; the /mnt copy above is what CI reads.)

**Why 34 GB and not the ~18 GB the handoff estimated:** that estimate scaled the archived 15,360 golden, which stores `hidden_states` in bf16. Current code writes fp32 (~233 MB/layer, not 119 MB). Took 25 min at 32 threads, not the projected 1-2 h — the projection extrapolated from eager.

**Two source changes were needed, both default-preserving** (`utils/transformer_helpers.py`):
1. `_ref_attn_implementation()` reads `PREFILL_REF_ATTN` (default `eager`), used at all three `_attn_implementation` sites. Eager needs 378 GiB for one score matrix at isl 56320 and OOM-kills the box.
2. `get_4d_causal_mask(causal_only=True)` returns **None** under a non-eager backend. This is not optional: transformers' `sdpa_attention_forward` computes `is_causal = q_len > 1 and attention_mask is None`, so passing the explicit mask silently downgrades SDPA to the masked kernel, and that mask is `[1,1,seq,seq]` fp32 = 12.7 GB at 56320 plus ones/tril temporaries. Verified the two paths are bit-identical (maxabs diff exactly 0.0).

**The 0.999999 equivalence bar in the handoff is unachievable and is not the right test.** Measured at 15,360 x 36L:

| comparison | what differs | worst PCC |
|---|---|---|
| eager vs sdpa | attention backend | 0.9999959 |
| sdpa@24thr vs sdpa@9thr | thread count only | 0.9999977 |
| eager@24thr vs eager@9thr | thread count only | **0.9999874** |

Changing the backend perturbs the reference **less** than re-running identical code at a different `OMP_NUM_THREADS`. A 1e-6 layer-0 rounding difference compounds through 36 bf16 layers and flips top-4 router assignments on ~0.26% of tokens (40 of 15,360 by layer 35). **Always run the thread-count control before treating a deep-model PCC delta as a real signal** — the model's own run-to-run spread is the floor. For scale, the thresholds this golden is used against are 0.96 / 0.88 / 0.85.

Also established: the archived `mistral4_15360_36L_fp32rope` golden's `kv_cache` is **bit-identical** to a fresh eager run, i.e. zero code drift on the KV path since 2026-08-20. Its `hidden_states` differ at a flat ~0.9999982 with no depth accumulation — that is purely its bf16 storage.

**Why:** regenerating this costs 25 min of CPU plus the whole equivalence argument, and the SDPA gate looks like a shortcut until the thread control is run.

**How to apply:** set `PREFILL_TRACE_DIR` to the dir; the `full55k` rows of `test_prefill_transformer_chunked.py` need it (they skip without a 56,320 golden). See [[mistral4-l36-chunked-padded-layer32-cliff]], [[mistral4-branch-suites]], [[mistral4-variant-rename-cache-trap]].
