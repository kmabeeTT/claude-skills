---
name: mistral4-prefill-has-no-lm-head
description: "Since ~2026-09 the deepseek_v3_d_p prefill transformer ends at the block stack - no LM head, no sampling, so prefill cannot produce a token"
metadata: 
  node_type: memory
  type: project
  originSessionId: 739afd67-235a-4cd0-87e1-9e4707ba469e
  modified: 2026-09-19T17:30:10.464Z
---

On `akhan/issue_53688_mistral_4_small_prefill_followup` (and later), `tt_prefill_transformer.forward` ends at the block stack. Its docstring is explicit: *"there is no norm / LM-head / sampling tail: decode owns the processing ... the populated KV cache is the output."* `_lm_head_and_extract`, `_sample` and `_sample_token` existed only on the serve branch `kmabee/mistral4-prefill-full-rebased` and are gone, along with `demo/serve_mistral4_interactive.py` and `run_model`'s `temperature` argument.

**Why:** this is the disaggregated split done properly, not a regression — but it silently breaks anything that expected prefill to emit a token. Any code sampling from prefill (a first token, a greedy reference continuation, a demo server) has to move that responsibility to the decode stack.

**How to apply:** for a prefill→decode handoff, prefill owns KV for `[0, prompt_len)` and nothing else. Resume by seeding rows `[0, prompt_len-1)` and feeding `prompt_token_ids[-1]` at position `prompt_len-1`, so decode recomputes that one position with its own kernels and its own head emits the first generated token. State the resume point in the handoff metadata — an off-by-one here is silent, since decode still emits fluent text from a cache that is one position short or stale. Grading then needs a *decode-side* control (the same engine self-prefilling the same ids), because there is no prefill-side continuation to compare against. See [[mistral4-disagg-prefill-decode]] and [[mistral4-disagg-reload-ring-260919]].
