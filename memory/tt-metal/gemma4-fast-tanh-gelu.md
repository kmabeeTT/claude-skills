---
name: gemma4-fast-tanh-gelu
description: "GELU_TANH param 1 (x/(1+exp(-2u)), unbiased BF16-exact exp poly) is PCC-neutral and -0.9/-1.0/-1.8% first chunk at 2k/4k/8k; FP32 constants cost 2 SFPLOADI each; a biased fit costs x1.05 deep-layer error"
metadata:
  type: project
---

Branch kmabee/gemma4-prefill-0930 (2026-09-30), flag GEMMA4_GELU=tanh_fast (default tanh; `lut` = the old
6-segment LUT, -0.015 min PCC). Same build, 130 W: first chunk 58.5 -> 58.0 (2k), 78.8 -> 78.0 (4k),
118.1 -> 116.0 ms (8k). PCC neutral at 2048/4096/8192 (error ratio 0.95-1.03).

Three lessons that cost device runs:
- Op count misleads on SFPU: each non-BF16-exact FP32 constant is 2 SFPLOADIs per element. V0 (22 ops, 7 FP32
  constants) got only a third of the LUT's gain; moving 3 constants into vConstFloatPrgm0-2 and snapping the rest to
  BF16 doubled the gain.
- The 2^f polynomial behind exp_21f's bit trick must stay in [1, 2) for every mantissa (setexp overwrites the
  exponent); a degree-3 fit with c0 < 1 was off by 2x near f = 0. Check exhaustively over all 2^23.
- Fit for zero MEAN error too: a fit with 3.0e-5 max but +2.6e-6 mean raised deep-layer KV error x1.05 at 8192;
  the unbiased refit (same cost) was neutral. Bias accumulates through the residual stream.
Also: the "accurate" GELU_TANH cancels for x < ~-4 (1 + tanh(u)); a fast-vs-accurate ULP test must exclude the tail.
exp_21f itself is 1.7e-3 relative, not the 21 bits its comment claims. See [[gemma4-m256-matmul-limits]].
