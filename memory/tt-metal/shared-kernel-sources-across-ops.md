---
name: shared-kernel-sources-across-ops
description: "Before changing a kernel's named args, grep for every factory that compiles that source — rotary_embedding_llama's compute kernel is also built by deepseek_prefill/rotary_embedding_indexed"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 5ecff3cb-0b03-4794-9f83-de74c864ae69
  modified: 2026-10-03T09:25:24.768Z
---

A kernel `.cpp` can be compiled by program factories outside its own op directory. `rotary_embedding_llama/.../compute/rotary_embedding_llama.cpp` is also built by `experimental/deepseek_prefill/rotary_embedding_indexed` (via the shared `kComputeSource` path constant), which passes its own per-core `n_heads` runtime arg. Op 2's rotary head split made the kernel read `head_start`/`head_end`; every indexed-rope user (GPT-OSS, Kimi/Mistral/GLM MLA, MiniMax, Llama-3.1-8B) then failed JIT with `'head_start' is not a member of 'args'` in Blaze CI, while all local tests passed.

**Why:** named runtime args are generated per program spec, so a kernel change compiles fine for the factories you edited and breaks only at JIT time for the others. Grepping for the file path misses users that reach it through a path constant in a shared header.

**How to apply:** before changing a kernel's arg contract, grep both the kernel file name and any path constant/header that names it (`git grep -n "kComputeSource\|<op>/device/kernels"`), and run one test of each consumer. Prefer keeping the kernel's existing contract and adapting the factory (here: pass per-core `n_heads` from the llama factories, as the indexed op does). Related: [[kernel-source-edits-break-queued-runs]].
