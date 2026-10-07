---
name: bashrc-sourcing-gh-token
description: "`source ~/.bashrc` DOES load GH_TOKEN (line 7, deliberately above the interactive-shell check) but not fixagent; gh auth is per-machine via ~/.gh-token.env -> dotfiles"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 677747a2-f27b-478b-944b-26aaf6be33ca
  modified: 2026-10-06T23:53:43.126Z
---

**Correction to the standing "`source ~/.bashrc` is a NO-OP in Claude Code's Bash tool" rule — it is only half true.** Kyle put the gh token *above* the interactive-shell guard on purpose, with the comment "non-interactive shells (scripts, Claude Code's Bash tool) need gh auth too":

```
line  7:  [ -f ~/.gh-token.env ] && . ~/.gh-token.env
line 12:        *) return;;          <- the non-interactive early return
line 230: fixagent() { ... }         <- never reached
```

So in this tool:

- **`source ~/.bashrc` DOES give you `GH_TOKEN`** → `gh auth status` reports logged in as kmabeeTT. It must be in the *same* Bash call as the `gh` command, since each call is a fresh shell.
- **It does NOT give you a working ssh-agent.** `fixagent` is at line 230, far below the return. The inherited `SSH_AUTH_SOCK` usually points at a dead socket (verified: set, but `ssh-add -l` fails), so for pushes keep using the hunt loop:
  `for s in $(command ls -t /tmp/ssh-*/agent.* 2>/dev/null); do [ -S "$s" ] && SSH_AUTH_SOCK=$s ssh-add -l >/dev/null 2>&1 && export SSH_AUTH_SOCK=$s && break; done`

**`gh` auth is per-machine.** `~/.gh-token.env` is a symlink into `~/dotfiles`, and both live on per-machine `/home`; there is no `~/.config/gh/hosts.yml` and no copy on `/data`. On a freshly-provisioned box `gh` reports "not logged into any GitHub hosts" until the dotfiles are in place — that is not a broken token, and the fix is to source bashrc, not to re-auth. Asked 2026-10-06 on bh-glx-120-c01u08, where `gh` looked unauthenticated and the dotfiles were present all along.

**How to apply:** before any `gh` call, `source ~/.bashrc >/dev/null 2>&1;` in the same command. Never print the token (`gh auth status` masks it; redact any output that could carry it). Related: [[tt-metal-push-routes]] (SSH vs HTTPS push routes and the workflow-scope refusal), [[telegram-two-way]] (same per-machine dotfiles pattern for the Telegram env).
