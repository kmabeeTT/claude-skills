---
name: tt-metal-pr-body-edits
description: Edit tt-metal PR descriptions from the live body; a bot appends a CI Status section and rewrites the body on every push
metadata:
  node_type: memory
  type: feedback
  originSessionId: 8f985f1d-292b-4c2b-ba24-7719ec3e62ae
  modified: 2026-09-28T23:51:04.414Z
---

On tenstorrent/tt-metal PRs a bot appends a "### CI Status" section (6 workflow badges for the PR's branch) and regenerates the whole body on every push, from the body it read at push time.

**Why:** 2026-09-28 I edited #58033/#58223/#58224 right after a force-push; the bot's post-push rewrite clobbered all three edits, and later `gh pr edit --body-file <local draft>` dropped the bot section from #58223/#58224 (the user noticed; restored from GraphQL `userContentEdits`).

**How to apply:** fetch the live body (`gh pr view N --json body --jq .body`), edit that, then `gh pr edit --body-file`; after a push, wait ~1 min for the bot before editing, and re-read the body to confirm the edit stuck. See [[tt-metal-push-routes]].

Same race right after `gh pr create` (2026-09-27): the bot rewrote #58032's body from its copy and reverted an edit made seconds earlier. Edit from the live body and re-check a minute later.
