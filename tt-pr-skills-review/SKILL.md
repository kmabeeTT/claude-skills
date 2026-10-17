---
name: tt-pr-skills-review
description: This skill should be used when the user wants tt-metal's "Skills reviewers" (the Tenstorrent Skills Reviewer and the Matt Pocock Skills Reviewer bots that post when a PR is opened non-draft or marked ready for review) run locally on a branch, a draft PR or an unpushed commit, so they can fix the findings before pushing or undrafting. Triggers on "run the skills review locally", "pre-review my branch", "what will the skills bots say", "skills reviewer on my draft PR", or a batch of PR branches to check before opening.
version: 1.0.0
---

# Local tt-metal Skills review

tt-metal has two gh-aw review workflows: `.github/workflows/tenstorrent-skills-reviewer.md` and `mattpocock-skills-reviewer.md`. They only run on `pull_request` `opened` / `ready_for_review`, with base `main`, a non-draft PR and a same-repo head branch. So a draft never gets them, and neither does a PR whose base is another branch (a stacked PR). There's no dispatch trigger.

This skill runs the same workflow prompts with the same pinned skills locally, on any `base...head` diff, and writes the findings to files. **It never posts to GitHub.**

## Steps

1. **Stage the run** with `prepare.py`, which needs no GitHub writes. One call per branch:

   ```bash
   python3 ~/.claude/skills/tt-pr-skills-review/prepare.py \
     --tree /data/kmabee/tt-metal \
     --head origin/<branch>         # or a local branch, or HEAD for unpushed work
     [--base origin/main]           # the PR base; for a stacked PR, the branch below it
     [--body-file <PR_DRAFT.md>]    # draft with **Title:** / **Body** sections (body ends at a --- line)
     [--pr N]                       # existing PR: also read its review comments, so the review skips repeats
     [--out-root DIR]               # default ~/.cache/tt-pr-skills-review/runs
   ```

   It prints the run directory and a `PROMPT.md` per reviewer. It skips a reviewer whose path filter wouldn't fire on the diff (`--all` overrides that). It reads the workflows from `origin/main`, so the pinned skills track what the bot runs today. Run `git fetch origin main` first if the tree is stale, but not in a tree a device queue is running from. Use refs that are current: `origin/<branch>` after a fetch, or the local branch you're about to push.

   Without `--body-file`, the title is the head commit's subject and the body is empty. Pass the draft body when there is one: `tt-perf-claim-review` and `/grill-with-docs` both read it.

2. **Run each reviewer as a subagent, all in one message so they run in parallel.** Use the Agent tool with `model: "sonnet"` (the bots run Claude Sonnet) and this prompt:
   `Read <run>/<reviewer>/PROMPT.md and follow it exactly. Do not post anything to GitHub.`
   Each agent writes `<run>/<reviewer>/FINDINGS.md` and `triage.json`. For several branches, stage them all first, then launch every reviewer agent together.

3. **Merge and triage** into `<run>/REVIEW.md`, then show the user a short summary:
   - Each finding: severity, skill, `file:line`, the issue in one line, and your verdict:
     - **fix** (with the proposed change);
     - **reply** (a drafted answer for when the bot raises it on GitHub);
     - **false positive** (why).
   - Check each finding against the code at the head sha before agreeing. The bots are advisory and sometimes wrong. The false-positive guards in `tt-review-core/references/false-positive-guards.md` are the first place to look.
   - Say where the local run may differ from the bot: the 2,000-line patch cap (the prompt warns about truncation, and `data/pr-diff.full` holds the whole diff), routing that picks at most two domain skills, and run-to-run variation.

4. **Fixes follow the user's normal rules.** Edit or amend only when they agree, never push or reply on GitHub without their OK, and once a PR is out of draft, all feedback goes in one commit on top.

## Notes

- **Re-run after fixing:** a fresh `prepare.py` makes a new timestamped run directory. Nothing is deleted, and the skill repos are cached under `~/.cache/tt-pr-skills-review/repos/<owner>__<repo>@<sha>`.
- **Stacked PRs:** pass `--base` as the branch below. The script notes that on GitHub neither bot would review that PR until it's retargeted to `main` and undrafted.
- **Split check:** for diffs of 20 or more files, the Tenstorrent reviewer's CODEOWNERS split check gets its inputs too: CODEOWNERS from the base and branch rules from read-only `gh api`.
- **If a workflow's prompt changes shape upstream** (new pre-fetched files, renamed outputs), update the path rewrites and the preamble in `prepare.py` `adapt_prompt()`. The preamble maps each safe-output (inline comment, overall review, summary comment, noop) to a section of `FINDINGS.md`.
