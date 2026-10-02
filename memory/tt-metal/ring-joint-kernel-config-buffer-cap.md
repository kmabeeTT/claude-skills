---
name: ring-joint-kernel-config-buffer-cap
description: "Ring joint SDPA program near the 70,656 B kernel-config buffer; KernelDescriptor.opt_level=O2 cuts the compute ELFs ~30% but the JIT kernel hash ignores opt_level (purge the cache to see it); reuse LLK instantiations; K skips must match on every compute path"
metadata:
  node_type: memory
  type: feedback
  originSessionId: ecf73b36-1b7e-42d3-8c9f-6038bb920bb7
  modified: 2026-09-25T23:07:10.179Z
---

The ring joint SDPA program (reader + writer + 3 TRISC ELFs) must fit the TENSIX kernel config buffer (70,656 B). The chunked global compute kernel is ~31 KB of .text across TRISCs; a K-split merge written with generic compute_common helpers (max_block, sub_exp_block, mul_block_bcast_cols, fill_tile) doubled it to 63 KB -> "Program size (80592) too large". Making helpers noinline made it worse. Rebuilding the merge from primitives the K loop already instantiates (sub_exp_first_col_blocks<false, scale>, salad_correct_fused<qktv_h, vDHt, dst_size> with qktv_h = streaming_qktv_h(out_subblock_h, out_subblock_w, DEST_AUTO_LIMIT, Sq), normalize_row_streaming with the kernel's exact template args incl. cb_attention_sink) brought it to ~44 KB.

**Why:** each new LLK init / SFPU op pulls several KB into all three TRISCs; template args that differ by one value create a second copy.

**Opt level (2026-09-26):** compute kernels default to O3. Setting `KernelDescriptor.opt_level = KernelBuildOptLevel::O2` for the K-split compute cut the q128 TRISC text 19.9/16.7/17.5 KB -> 13.1/11.7/12.9 KB and fixed "Program size (71200) too large". BUT `Kernel::compute_hash()` does not include opt_level, so a cached O3 binary with the same hash is silently reused and the size comes out identical -- that is why an earlier "Os has no effect" result was wrong. Purge the matching `~/.cache/tt-metal-cache/*/kernels/<kernel>/<hash>` dirs (grep named_ct_arg_map_generated.h) before measuring.

**How to apply:** check ELF sizes in ~/.cache/tt-metal-cache/<hash>/kernels/ring_joint_sdpa/<hash>/trisc*/trisc*.elf (size -A) after adding compute code.

Deadlock trap: any change to which K chunks the reader sends must be mirrored in BOTH compute paths (sdpa_ring_v2 streaming and sdpa_ring in compute_common for fp32_dest_acc). A reader-only skip hung test_ring_joint_attention_sdpa_chunked_accuracy[kimi50k-...-fp32_acc] until pytest's timeout killed it holding the galaxy. Gate reader behaviour on a compile-time flag that says which compute path runs. See [[kernel-source-edits-break-queued-runs]], [[gemma4-ring-sdpa-ksplit]].
