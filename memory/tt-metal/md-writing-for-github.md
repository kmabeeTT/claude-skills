---
name: md-writing-for-github
description: "MD files Kyle pastes into GitHub: no hard wrapping, drafted replies unquoted (no '> '), PR descriptions use bullet results not tables (squash commit)"
metadata:
  type: feedback
---

Merged 2026-10-02 from `md-no-hard-wrapping`, `md-drafted-replies-no-quote-prefix` and `pr-desc-no-tables`. Most MD written in these checkouts (PR descriptions, PR comments, planning docs, handoffs) ends up pasted into GitHub, so three rules apply to all of it.

**1. No hard wrapping.** Each paragraph, bullet or table row is one long line; blank lines separate blocks. Hard wraps at ~100 chars render as ragged mid-sentence breaks in GitHub and soft-wrapping editors, and make diffs noisy because one edited word rewraps a paragraph. Asked twice (once for the PR-A description, then as a standing rule for all future files), so it is the default, not a per-file request.

**2. Drafted replies are plain text, never `> ` quoted.** When drafting PR review replies into an MD file, put a bold heading naming the comment being answered (e.g. `**ring_prefill.py:21** (...)`) and the reply text below it unquoted, including any table rows. Kyle pastes the reply straight into GitHub; a `> ` prefix renders as a quote and he had to strip it by hand (2026-09-25, PR_57453_REBASE_PLAN_AND_REPLIES.md).

**3. PR descriptions: results as bullets, not tables.** tt-metal squash-merges with the PR title and description as the commit message, and a markdown table reads badly in `git log`. One bullet per config in a fixed column order stated once in the lead-in, e.g. `- chunk 2048: 92.6 -> 86.6 ms (-6%), 5.93 -> 5.63 s, 21.4 -> 20.6 s`. Tables are fine in PR comments, issues and Slack. Kyle asked for the rewrite on 2026-09-25 (the Gemma4 fabric PR). The full PR-description style guide is in CLAUDE.md ("PR descriptions").

Related: [[ci-status-only-when-verified]], [[tt-metal-pr-body-edits]], [[allcaps-names-for-reference-docs]].
