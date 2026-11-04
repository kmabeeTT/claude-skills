---
name: halo-preexchange-loses-1023
description: Gemma4 sliding halo exchange is ~95 us/request link-bound; splitting it out of ring SDPA (exchange op + CCL-free SDPA) loses to PR 2 lanes and to the loop
metadata:
  node_type: memory
  type: project
  originSessionId: c96c24b1-69f5-4c57-91ab-c2001efc1e49
  modified: 2026-10-24T01:01:08.852Z
---

Measured 2026-10-23/24 on b06u08 (traced, Gemma4 sliding TP4xCP8 Linear, 2k chunk): exchange-only = 92/96/99/99 us per request at B=1/2/4/8, i.e. linear in B, no overlap between requests' transfers. CCL-free SDPA ks3 = 80 us/request. Split (exchange + B calls) at B=4 = 679 us vs lanes 486, loop 621. SUPERSEDED mechanism (10-27 SDPA-owner device zones): SDPA cores are blocked for the whole halo even in lanes; lanes win by filling idle cores after the halo. Bit-exact prototype (`halo_mode` attr) on branch kmabee/halo-preexchange-proto-1023 (8e30511, pushed 10-24, in wt_pr2_rebase_1023); secret gist https://gist.github.com/kmabeeTT/dc4b542879a1f904fb23baf344f27773 posted to the SDPA-owner Slack thread.

**Why:** answers the SDPA owners' "loop / persistent buffers" alternative to PR 2 (#61237).
**How to apply:** don't re-propose moving the halo out of SDPA unless the exchange runs concurrently with attention. Full record: debug-docs gemma4_batching_poc-noissue/halo_preexchange_result_1023.md. Related: [[batching-prs-maintenance-handoff-1017]]
