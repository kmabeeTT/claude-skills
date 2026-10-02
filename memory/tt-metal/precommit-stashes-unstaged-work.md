---
name: precommit-stashes-unstaged-work
description: "pre-commit stashes unstaged changes before running, so a killed first commit in a fresh checkout leaves that work only in ~/.cache/pre-commit/patch*"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 197d2be2-411b-4a5f-b4e2-1feb588af108
  modified: 2026-09-03T18:03:22.216Z
---

`git commit` in a tt-metal checkout runs pre-commit, and pre-commit **stashes unstaged changes
first** (`[WARNING] Unstaged files detected. [INFO] Stashing unstaged files to
~/.cache/pre-commit/patch<epoch>-<pid>`). On the FIRST commit in a fresh checkout it then installs
~10 hook environments ("This may take a few minutes...") — which exceeds the Claude Code Bash
tool's 2-minute default. The kill lands **after** the stash and **before** the restore, so:

- the commit does not happen (HEAD unchanged), and
- unstaged work is gone from the working tree, recoverable only from
  `~/.cache/pre-commit/patch*` via `git apply <patch>`.

Nearly lost a local uncommitted fix this way on 2026-09-03.

Two further gotchas in this repo:
- **Hooks rewrite files.** Never let pre-commit run while a device job is executing one of the
  scripts being committed — that is the byte-offset trap. Commit with `--no-verify` and verify
  formatting by hand instead.
- **black version skew.** `.pre-commit-config.yaml` pins **black 23.10.1**; the venv ships
  26.3.1, which additionally demands a blank line after a module docstring. So
  `python_env/bin/black --check` reports pre-existing files as dirty. Check whether `git show
  HEAD:<file>` is equally dirty before "fixing" formatting — applying the newer style would fail
  the repo's own hook.

**Why:** the failure is silent and destructive in the one direction that matters (working-tree
changes), and the obvious reading — "the commit just failed, retry" — leaves the stash unrecovered.

**How to apply:** pass a long timeout for the first commit in a checkout, or use `--no-verify` plus
manual `black --check` / trailing-whitespace / EOF checks; either way, back up uncommitted work you
did not author before committing, and check `~/.cache/pre-commit/patch*` if the tree looks wrong
afterwards. See [[pp4-perf-harness-traps]].
