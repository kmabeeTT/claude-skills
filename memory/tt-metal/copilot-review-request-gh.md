---
name: copilot-review-request-gh
description: "Request Copilot on a tt-metal draft with `gh pr edit N --add-reviewer @copilot`; the REST requested_reviewers call with the bot login silently does nothing, and the request list reads empty once Copilot starts"
metadata:
  node_type: memory
  type: reference
  originSessionId: f68b287c-f996-4c93-ad60-43f350bc893e
  modified: 2026-10-18T05:47:40.723Z
---

`gh pr edit <N> -R tenstorrent/tt-metal --add-reviewer @copilot` requests a Copilot review (works on drafts; the ruleset's auto-review skips drafts). `gh api -X POST .../pulls/N/requested_reviewers -f 'reviewers[]=copilot-pull-request-reviewer[bot]'` returns OK but requests nothing. Verify with the timeline, not `reviewRequests` (empty once Copilot picks it up): `gh api repos/tenstorrent/tt-metal/issues/N/timeline -q '.[]|select(.event|test("review|copilot"))|.event'` should show `review_requested` then `copilot_work_started`. Copilot's review lands in ~5-10 min. Its suggested code is not always valid: on #61236 its suggested test lane broke an op invariant (`cache_seq % written_seq == 0`), so run every suggestion. See [[skills-reviewers-local-run]].
