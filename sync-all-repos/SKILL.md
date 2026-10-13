---
name: sync-all-repos
description: Commit and push every git repo under the home directory so nothing is lost when moving to another machine. Use when the user says "commit and push all my repos", "sync everything before I switch machines", "I'm moving boxes", "push all projects", or similar.
---

# Sync all repos before switching machines

Home directories on the BH Galaxy boxes are node-local, so anything only in `~` stays behind on the old box. This skill commits and pushes every repo under `~` with one script, safely.

## Steps
1. Source the shell so `gh` has a token: `source ~/.bashrc >/dev/null 2>&1`.
2. Dry run first and show the user the table:
   ```bash
   ~/claude-skills/sync-all-repos/sync_all.sh
   ```
3. Apply with a message that ends with this session's commit attribution line:
   ```bash
   ~/claude-skills/sync-all-repos/sync_all.sh --apply -m "sync: $(hostname -s) before moving machines

   Co-Authored-By: ..."
   ```
4. Report every row that isn't "pushed" / "up to date", and what the user should do about it. Exit code 1 means something was left unsynced.
5. Also list what is NOT covered: non-git directories in `~` (`ls ~`, e.g. `runs_*`, `bin`) and repos outside `~` the user cares about (pass them in `SYNC_EXTRA="/data/... /data/..."`). `/data` is NFS and survives a machine move; `~` does not.

## What the script does (see the header of `sync_all.sh`)
- **Personal repos** (origin `github.com:$SYNC_OWNER/*`, default `kmabeeTT`): `git add -A`, commit, pull `--rebase` if behind, push. It refuses new untracked files over 50 MB or with secret-looking names, and skips the repo instead.
- **Shared repos** (e.g. a tt-metal worktree): never commits. It pushes existing local commits only as a fast-forward and only when no open non-draft PR uses the branch. `--no-shared` leaves them alone.
- Never force-pushes, never skips hooks; skips detached HEAD, rebase or merge in progress, and repos without an origin.

## Traps
- **SSH push needs the forwarded agent key** on tt boxes (the on-disk key fails SAML). If pushes fail with a permission error, tell the user to reconnect with agent forwarding; don't switch remotes.
- **A pre-commit hook that fails** leaves the repo committed nowhere: report it, don't retry with `--no-verify` unless the user says so.
- **Never pass `--force`-style workarounds** to get a push through. A rejected push is reported.
