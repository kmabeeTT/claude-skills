---
name: ci-status-only-when-verified
description: Never write PASSED (or any result) for a CI run in a PR description or comment until gh shows the run completed with that conclusion
metadata:
  node_type: memory
  type: feedback
  originSessionId: 2fa781d6-0050-442b-9254-4c2bb39af9f9
  modified: 2026-09-25T19:05:18.450Z
---

Only mark a CI link PASSED / FAILED after `gh run view <id> --json status,conclusion` shows `completed` with that conclusion, and check the jobs that matter (a run can show most jobs green while the model leg is still queued). Until then, list the link with no status, or say "pending".

**Why:** Kyle marked #57931's Blaze run PASSED early while its Gemma4 sanity leg was still queued (2026-09-25), and said: in general don't do that yourself.

**How to apply:** when drafting PR descriptions or comments, re-check each linked run just before handing the text over. A green run can also be hollow: a plain L2 nightly dispatch skips every test job, see [[tt-metal-test-command-ci-selector]]. Related: [[md-writing-for-github]].
