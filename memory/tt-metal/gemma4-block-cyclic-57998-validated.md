---
name: gemma4-block-cyclic-57998-validated
description: "Sasha's Gemma4 block-cyclic test passes at 2k/4k/8k with PR #57998 cherry-picked, but only after two Gemma-side edits (2 halo slots, drop the unaligned-start guard)"
metadata:
  node_type: memory
  type: project
  originSessionId: f58eafdb-d9cf-4059-92c0-30e5770388ce
  modified: 2026-10-01T14:24:17.955Z
---

2026-10-01, bh-glx-120-c01u20: `svuckovic/gemma4-block-cyclic` @ f8f5cdedc06 + PR #57998 (1dd97bbce62, clean cherry-pick)
= local branch `kmabee/sasha_block_cyclic_with_57998` @ 874517ff971 in tt-metal-2.
`test_block_cyclic_vs_aligned.py::test_block_cyclic_matches_aligned_256k` (gate 0.99): 8k 0.99139, 4k 0.99217, 2k 0.99248, all pass.
Logs: /data/kmabee/runs_1001/bc_fix_chunk*.log.

The op fix alone is NOT enough; two uncommitted model edits were needed:
- `ring_prefill.py`: sliding gather buffer always `2 * halo` (branch gave 2 slots only when halo <= local slab, i.e. 8k).
- `prefill_metadata.py`: remove the ValueError rejecting unaligned starts when local slab < 1024.

**Why:** issue #58685 (Sasha) = part 1 traced path derives end = start+chunk (NOT fixed by #57998) + part 2 wrapped multi-hop (= my #57823, fixed by #57998). Because of part 1, nearly every unaligned request is treated as wrapping on device, so 2 slots are mandatory, and 2 slots + >1 hop uses per-hop unicast, not multicast (perf cost unmeasured).

**How to apply:** when this lands in Gemma, carry both edits; perf at 2k/4k with unicast still needs measuring. Related: [[gemma4-ring-sdpa-ksplit]], [[gemma4-sliding-sdpa-ksplit]].
