---
name: debug-docs-location
description: "Write session/handoff docs to ~/debug-docs/<topic>/ (one canonical copy), not /data/kmabee; copy to /data only as a throwaway for another box"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 23fe3dc2-d0c3-4ecc-9cb8-80454b8386e8
  modified: 2026-08-25T14:26:30.285Z
---

Author all session, handoff, and findings docs in `~/debug-docs/mistral4_prefill_planning-noissue/part2/` and keep that as the single canonical copy. Do not leave duplicates in `/data/kmabee/` — kmabee asked for the debug-docs version to be the one that survives (2026-08-25), and the `/data/kmabee/*.md` files already there pre-date that and should be left alone.

**Why:** two copies of the same doc on a shared NFS mount drift, and the handoff docs are the record of what was actually measured. One home means one version.

**Scope update 2026-10-02:** the part2 folder was the Mistral4 home; later work uses its own topic folders (e.g. `~/debug-docs/gemma4_prefill_chunk_floor-noissue/`, `gemma4_prefill_chunk_sizing-57836/`). The rule is the same: one canonical copy under `~/debug-docs/<topic>/`.

**How to apply:** the tension to remember is that `~/debug-docs` lives on `/home/kmabee`, which is **not** visible to the 12 kW box — `/data/kmabee` is the shared mount. So when someone on the other machine has to *execute* from a doc, copy it to `/data/kmabee` as an explicit throwaway and delete it once the run is done; never treat that copy as a second version to maintain. For docs that are only read by kmabee or the team, debug-docs alone is enough. Related: [[mistral4-bringup-workspace]], [[md-writing-for-github]].
