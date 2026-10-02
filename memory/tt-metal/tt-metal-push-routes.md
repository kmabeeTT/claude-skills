---
name: tt-metal-push-routes
description: "Pushing to tenstorrent/tt-metal from bh-glx boxes: SSH needs the SSO-authorized forwarded agent key (on-disk key fails SAML), HTTPS gh token lacks workflow scope; SAML state flips per box/day, so probe with one real push and verify with ls-remote"
metadata:
  type: reference
---

Merged 2026-10-02 from three per-checkout notes (tt-metal 09-16..09-25, tt-metal-2 09-08..09-30, tt-metal-3 09-30). CLAUDE.md's "Git push & CI dispatch" section has the general rules; this is the box-level detail.

**Two routes, two different blockers.**

- **SSH** is the route for anything whose pushed commits touch `.github/workflows/*`, because OAuth scopes do not gate it. Two SSH identities reach GitHub as `kmabeeTT` from a bh-glx box, and only one can push to the org:
  - `~/.ssh/id_ed25519` authenticates (`ssh -T git@github.com` prints `Hi kmabeeTT!`) but is **not SAML-SSO authorized**. Pushing with it fails with *"The 'tenstorrent' organization has enabled or enforced SAML SSO"* (fetch/ls-remote still work; push reads "Could not read from remote repository"). Authentication succeeding is why a plain auth probe looks healthy.
  - The **forwarded `macbook` RSA key** in a live agent socket is SSO-authorized. Find it with the probe loop (`source ~/.bashrc` is a no-op in the Bash tool, and on 2026-09-08 it pointed at a dead socket anyway):
    ```bash
    for s in $(command ls -t /tmp/ssh-*/agent.* 2>/dev/null); do [ -S "$s" ] && SSH_AUTH_SOCK=$s ssh-add -l >/dev/null 2>&1 && export SSH_AUTH_SOCK=$s && break; done
    export GIT_SSH_COMMAND="ssh -o IdentitiesOnly=no -o IdentityFile=/dev/null"   # else the on-disk key is offered first and wins
    ```
  - The forwarded agent **vanishes when Kyle's SSH session drops** (seen 2026-09-30, c03u08): no live `/tmp/ssh-*/agent.*`, and SSH push fails with a publickey error. Then use HTTPS, or hand the push to Kyle.
- **HTTPS** (`gh` token: `admin:public_key, gist, read:org, repo`, **no `workflow`**):
  ```bash
  git -c credential.helper='!gh auth git-credential' push https://github.com/tenstorrent/tt-metal.git <sha>:refs/heads/<branch>
  ```
  Refused with `refusing to allow an OAuth App to create or update workflow ... without workflow scope` (or the misleading `Unable to determine if workflow can be created or updated due to timeout`) when the push would change `.github/workflows/*`.

**What triggers the workflow-scope refusal.** Observed cases: a force-push rebasing onto an OLDER main (2026-09-16, refused); a new branch whose own commits include a merge touching workflows (2026-09-25 evening, refused); a fast-forward of one non-workflow commit onto a day-old-main branch (2026-09-25, accepted); a `--force-with-lease` of a branch rebased onto latest main (accepted). So the trigger looks like the **pushed range** rather than the whole branch diff. When checking a branch, compare against main's **tip** with two dots — `git diff --name-only origin/main HEAD -- .github/workflows`; the three-dot form diffs the merge-base and reported 0 on a branch that 14 workflow files separated from the tip (2026-09-17).

**SAML state is per key and per box, and flips.** SSH was blocked 2026-09-16 (b03u02), worked 2026-09-18, blocked 2026-09-25 morning on c03u08, worked again that evening after the agent loop, and lapsed again 2026-09-30. Never trust the last note: probe with one real push.

**Order that works:** HTTPS for commits that touch no workflows; SSH via the forwarded agent for anything that does; otherwise hand the push to Kyle (he pushed a doubly-blocked branch himself on 2026-09-18). Permanent unblocks both need a browser: `gh auth refresh -h github.com -s workflow`, or authorize the on-disk key at github.com/settings/keys → Configure SSO.

**Verification traps:**
- `git push --dry-run` does not catch the workflow rejection (it printed `* [new branch]`, then the real push was refused). Always confirm with `git ls-remote <remote> refs/heads/<branch>` == local sha.
- **Gate CI dispatch on that ls-remote check in the same command.** A failed push followed by `gh workflow run` tested the stale head (2026-09-30); the runs had to be cancelled.
- `git checkout -b mine origin/theirs` sets upstream to **theirs**, so a bare `git push` targets their branch. Push with an explicit `HEAD:refs/heads/<mine>` and `-u`.

Related: [[tt-metal-pr-body-edits]], [[build-host-bh-glx-110-a10u08]], [[data-checkout-venv-home-pin]].
