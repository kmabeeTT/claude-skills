---
name: helpers-on-data-shared-repos
description: Personal repos (claude-skills, debug-docs, prefill-docs, scripts, claude-code-history) live in /data/kmabee/helpers (mode 700) with ~ symlinks since 2026-10-13; dotfiles stays a local clone
metadata:
  type: project
---

Since 2026-10-13 the personal repos live on NFS at `/data/kmabee/helpers/<repo>` and `~/<repo>` is a symlink to it. Every box on the same /data mount sees one working copy, so switching machines needs no push. `dotfiles` stays a local clone in `~` (a hung /data must not hang login; it also holds the gh/Telegram tokens). The tt-metal worktree moved to `/data/kmabee/wt-batching-clean` (`git worktree repair` done).

- `helpers` and everything in it is mode 700 / go-rwx: `/data/kmabee` itself is 755 (world-readable). NFS is `sec=sys`, so root on any client can still read it.
- The Claude memory links in `/data/kmabee/.claude/projects/*/memory` point at `/data/kmabee/helpers/claude-skills/memory/tt-metal`.
- `dotfiles/install.sh` picks the mode: shared if `/data/$USER` exists (creates helpers 700, copies an existing `~` checkout over, links), else clones into `~` (off-mount boxes like exabox).
- Old copies were kept as `~/.<repo>.moved-20261013-*`; safe to delete once the new layout is trusted.
- Several sessions on different boxes now write one working copy: index.lock keeps commits safe, but concurrent edits to the same doc / MEMORY.md can clobber.
- Still push periodically as backup (`~/claude-skills/sync-all-repos/sync_all.sh`): NFS is not a backup.

Related: [[debug-docs-location]], [[shared-tree-multi-session]], [[tt-metal-push-routes]].

**Worktrees (2026-10-13):** every linked tt-metal / tt-metal-2 / tt-metal-3 worktree now lives in `/data/kmabee/worktrees/<name>`; main checkouts stay at `/data/kmabee/<name>`. Built ones keep a symlink at the old `/data/kmabee/<name>` path because build dirs and venvs hold absolute paths. `wt-batching` (the batching PoC build tree, venv rebuilt 10-13) moved last, also symlinked back. Move a worktree with `~/scripts/move_worktree.py [--apply] [--symlink] OLD NEW`, never `git worktree move` (it refuses trees with submodules). The script rewrites submodule gitdir/core.worktree links as absolute paths, because the relative ones break when the depth changes.
