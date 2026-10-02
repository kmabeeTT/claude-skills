---
name: stack-merge-campaign-1001
description: "Live state of the #58223/#58224 stack merge (2026-10-01): read debug-docs SESSION_STATE.md first after a compaction"
metadata:
  type: project
---

On 2026-10-01 the Gemma4 PR stack was mid-merge: #58032 and #58033 merged; #58223 (approved, head 232f6528d1a) next;
#58224 after it. Background jobs (local SDPA suite, Telegram watchers, CI on #58224) were running from
/data/kmabee/runs_ringsdpa on bh-glx-120-c03u08.

**Why:** a context compaction loses which detached jobs and watchers exist and what the user was promised.

**How to apply:** after a compaction in that session, read
~/debug-docs/gemma4_prefill_chunk_sizing-57836/SESSION_STATE.md before acting. It lists the running jobs, the
pending Telegrams, the drafts to fill, the known-failure list and the c03u08 gotchas (HTTPS push, tg_send.sh, no
waitchips). Delete this memory once #58224 merges.

**Status checked 2026-10-02:** #58223 merged 2026-10-01 20:37 UTC; #58224 still open.
