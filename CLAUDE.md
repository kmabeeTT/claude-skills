# Working notes (kmabee)

Operational lessons to avoid re-paying time already spent. Keep this lean.

## Where notes go (rules and memories)
Everything Claude saves goes in the claude-skills repo (`~/claude-skills` ->
`/data/kmabee/helpers/claude-skills`), in exactly one place. Pick the place yourself; don't wait to be asked.
- **Applies in any project** (how Kyle wants work done, git / PR / doc conventions, shell hygiene, box and
  cluster facts): this file, in the matching section, as one bullet with its why. Never auto-memory, even
  when the current project has a memory dir: that is how a rule learned in one repo goes missing in the rest.
- **About one repo** (its state, quirks, handoffs, measured results): that project's auto-memory dir. It must
  be a symlink into `memory/<dir>/` of the repo: check `readlink -f <memory dir>`. If it isn't, add the
  project key to `memory/PROJECTS` and run `./install.sh` (`--force` if a real dir is in the way; it merges
  the notes in first), then write.
- **Before writing,** grep `CLAUDE.md` and `memory/*/` for the topic and update the entry that exists.
- **After writing,** commit in claude-skills (`CLAUDE.md: ...` / `memory: ...`), one commit per topic, staging
  only your own paths, since other sessions write there at the same time. Push when the session's notes are
  done, or let `sync-all-repos` do it.

## Working conventions (Kyle)
- **Never open a PR, even a draft, without asking.** Pushing the branch and writing the description to a file is fine.
- **MD for GitHub:** no hard wrapping (one line per paragraph); drafted replies go under a bold heading, never `> `-quoted.
- **Never write PASSED for a CI run** until `gh` shows it completed with that conclusion; count job conclusions too (a plain
  L2 nightly dispatch skips every test and still goes green).
- **No `rm -rf` / `rm -f` in run commands;** use fresh timestamped paths and unique names instead.
- **Never edit a running bash script** — bash reads by offset, so the live run dies on a phantom syntax error.
  That includes drivers several levels up. Edit between runs, or copy to a new path for the next invocation.
- **Before `kill`, confirm the PID's cmdline matches your own run.** Other Claude sessions run as the same UID; visible ≠ mine.
  Prefer killing the process group you launched (`setsid`, record the PGID). Another session's "done" marker
  file says nothing about what is running now.
- ALL_CAPS filenames for living reference docs (runbooks, trackers); snake_case for one-off records.
- **Docs:** session, handoff and findings docs get one canonical copy, in `~/debug-docs/<topic>/`; two copies
  drift. Edit doc repos (debug-docs, prefill-docs) in the checkout itself, on a branch, never in a worktree
  elsewhere: Kyle can't find worktrees.
- debug-docs: commit locally, push per milestone/topic, not per tracker tweak. **prefill-docs: never
  push without Kyle's OK.**
- **Once a PR is out of draft: no force-pushes.** All feedback goes in one commit on top; show Kyle the
  diff and the planned replies before pushing or replying. Drafts can be amended and force-pushed with lease.
  Before a PR is opened, keep stacked branches linear (fold fixes into the commit they belong to, replay the
  stack): Kyle prefers a force-push with lease over merge commits, even after saying "avoid force push" (Nov 10).
  If a request seems to force a choice between the two, ask.
- **Don't name or @-tag people in issue/PR text without asking;** refer to roles. PR labels: topic only,
  never `pr-priority` / `pr-risk` / `pr-complexity`. Issue labels: copy the closest sibling issue's.
- **Private shorthand ("PR A/B/C/D", "sub-issue 7") is fine in Kyle's own docs, never in text others read**
  (PR and issue bodies, Slack, docs shared with the org): there, name the PR by what it does ("the
  mask-delivery PR", `#<mask-delivery PR>` until it has a number), or add a legend that defines the letters.
- **A feature's open design questions go in its issue draft** (an "Open questions" section), not in the handoff
  or chat; the handoff points there. One place to answer them, and they travel with the issue when it's filed.
- **Questions Kyle forwards to another team: check every premise in our code first,** and drop any the code or
  docs already answer. Ask only what decides the current work. Give the draft in a message of its own, never
  between tool calls. (A tt-d-gen draft once assumed the prefill worker samples the first token; there the decode
  worker does.)
- **Reaching Kyle.** He chats with Claude over the Telegram channel plugin. When an unattended run is blocked
  on his call, send with `/data/kmabee/runs_ringsdpa/tg_send.sh "msg"` and poll `~/scripts/tg_read.sh --wait N`
  instead of stopping; a reply there is his answer. Both read `~/dotfiles/.tt-telegram.env` (override with
  `TELEGRAM_ENV_FILE`). Slack (claude.ai connector) is only for messages to teammates: show Kyle the exact text
  first. `slack_send_message` adds a "Sent using @claude" footer that can't be removed, so use
  `slack_send_message_draft` if he wants none. His self-DM is `DSZ9BLRK6`.

## TT serving servers (tt-inference-server / tt-media-server + tt-xla)
- **Launch must run from the tt-xla venv**, because `venv/activate` and `TT_METAL_HOME`
  resolve from `$(pwd)`:
  `cd /home/kmabee/tt-xla && source venv/activate && cd /home/kmabee/tt-inference-server/tt-media-server && NUM_HIDDEN_LAYERS=1 DEVICE_IDS='(0)' PORT=8009 ./launch_qwen3_8b.sh`
  (`uvicorn: command not found` / exit 127 means this wasn't done.)
- **Single layer** (`NUM_HIDDEN_LAYERS=1`) isolates decode/serving behavior from model
  depth and compiles in ~2 min. First real request triggers a long kernel compile —
  poll until a generate returns `"text"`, don't trust `/v1/models` 200.
- **Pin the chip with `DEVICE_IDS='(N)'`, never `TT_VISIBLE_DEVICES`** for the *server*
  (the runner overwrites the latter from the worker's device_id).
- **Standalone tt-xla** (pytest / benchmark / repro scripts, no tt-media-server) is the
  opposite: on a box with multiple `/dev/tenstorrent/*` devices you MUST pick one and
  give it the mesh descriptor for that board, e.g.:
  `TT_VISIBLE_DEVICES=0 TT_MESH_GRAPH_DESC_PATH=/home/kmabee/tt-xla/third_party/tt-mlir/src/tt-mlir/third_party/tt-metal/src/tt-metal/tt_metal/fabric/mesh_graph_descriptors/p150_mesh_graph_descriptor.textproto`
  (match the descriptor to the hardware — `p150_...` here). Without both, it errors or
  grabs the wrong/busy chip.
- Default API key is `your-secret-key` (`Authorization: Bearer your-secret-key`).
- **Stale-server teardown is the #1 time sink.** Front-end procs are `uvicorn main:app`
  (NOT `uvicorn.*<port>`); engine is `VLLM::EngineCore`. Before any relaunch:
  `pkill -9 -f "VLLM::EngineCore"; pkill -9 -f "uvicorn main:app"; pkill -9 -f "launch_qwen3"; fuser -k <port>/tcp; sleep 6`
  then verify `ss -ltnp | grep :<port>` is clear AND the device is free (see below). An
  `address already in use` on relaunch leaves an **orphan EngineCore holding the device**.
- **Find/kill a process stuck holding a TT device** (next run can't acquire the chip):
  - Who holds it: `fuser -v /dev/tenstorrent/*` or `for d in /dev/tenstorrent/*; do echo "$d"; fuser "$d"; done`. Confirm which device a PID holds with `ls -l /proc/<pid>/fd | grep tenstorrent`.
  - **Empty output does NOT mean the device is free** (hidepid, see "Shared TT boxes"): another user's
    `EngineCore` on that chip is invisible. Suspect it before debugging tt-xla/tt-metal.
  - The holder is usually a `VLLM::EngineCore` (or a crashed pytest/python). Kill by PID: `kill -9 <pid>`; if it's a defunct/zombie, kill its parent.
  - Note: `ps` may show many `<defunct>` uvicorn zombies from prior runs — harmless; the live ones to kill are the non-defunct `VLLM::EngineCore` / `uvicorn main:app` / `python ...repro`.
- **Env propagation:** custom env vars reach the EngineCore subprocess, but NOT the
  `vllm_runner` worker reliably (only vars it reads explicitly, e.g. `CPU_SAMPLING`,
  `ENABLE_TRACE`, `NUM_HIDDEN_LAYERS`). To force a vLLM config for a test, hardcode in
  `config/vllm.py` / `vllm_runner.py` rather than via a new env var.
- `vllm_tt.*` loggers (model_runner, metadata) are at **WARNING** — use `logger.warning`
  for probe output or it won't print. Revert all debug probes clean when done.

## Debugging methodology (general)
- Before blaming a layer, **build the smallest pure repro and confirm a FLAT control.**
  Isolate one variable at a time (A/B), e.g. standalone `AsyncLLMEngine` vs the server,
  or one sampling param toggled. Re-verify "known" baselines instead of trusting a prior
  summary — several conclusions here flipped (device→async engine→tt-media-server→a
  sampling default).
- **"Same graph/IR ⇒ same device time" is FALSE.** Host-side glue *outside* the compiled
  graph (e.g. per-step tensor construction) can dominate and grow with sequence length
  while the device graph is fixed-shape and constant. Measure host vs device separately.
- Watch for **O(N)-per-step host work → O(N²)** in decode loops (penalty/token-count
  rebuilds, re-detokenization). Symptom: per-step time grows linearly with tokens
  generated, resets per request, independent of context/KV depth.

## Benchmark hygiene
- **Send sampling params explicitly** (`temperature`, `repetition_penalty`, …) so server
  defaults don't silently shape results. tt-media-server defaults `repetition_penalty=1.1`,
  which triggers the O(N²) decode regression (issue #4278); `temperature=0` does NOT
  disable penalties. `~/scripts/test_all_llm_servers.sh` has `--rep-penalty`/`--temperature`.
- **Prefix caching** is on — repeated/overlapping prompts return cached KV and report bogus
  TTFT. Use distinct per-run tokens.
- **Don't display the requested value where a measured one can catch a shortfall** (e.g.
  show actual generated token count, not `max_tokens`) — masking it hides real bugs.

## Shared TT boxes (SLURM, devices, other sessions)
- **`/proc` is mounted `hidepid=2`** (a `dev-sec` hardening baseline, since 2026-09-15), so `ps` / `fuser` /
  `pkill` see only your own PIDs. An empty holder check means *you* don't hold it, not that it's free; the
  cross-user source is `~/scripts/tt-devs.sh` (UMD locks in `/dev/shm`). Fixing it needs root (the ask is
  `hidepid=2,gid=slurmusers` or `hidepid=1`); config management reverts a manual remount.
- **The SLURM Epilog deletes every top-level `/tmp` entry you own whenever any of your jobs ends** (a
  `scancel`, a short `srun` finishing): tmux sockets, `/tmp/ssh-*` agent sockets, `/tmp/claude-4140`. Keep
  long-lived things off `/tmp` (bashrc sets `TMUX_TMPDIR=~/.tmux-tmp`). It is not a tmp cleaner; aging is off.
- **Lost allocation = stop device work.** Before each device step check that `squeue -h -u $USER -t RUNNING
  -o '%i %N'` lists this node (`squeue -w` is broken here) and that `~/scripts/tt-devs.sh` holder lines name
  only `kmabee`, `akhan` or `mmanzoor` (teammates who share his boxes). Anyone else, or no allocation, means
  Kyle lost the machine. Run `~/scripts/alloc_guard.sh <queue_pid> [60]` beside every unattended queue: an
  allocation ended an hour early once and queuing (with glx_resets) went on for 30 min on another user's job. Device work inside a docker container shows up in `tt-devs.sh` as `(exited - stale lock) user=-` (the PIDs live in the container's namespace), so the guard strikes on your own run: allow `-` (`ALLOW_USERS="akhan mmanzoor -"`) for container queues. A container's in-namespace PID can also match a host kernel thread, so your own run shows as `kworker ... user=root ... held ~239h`: add `root` too (`ALLOW_USERS="akhan mmanzoor - root"`), after checking the chip is the one your queue uses.
- **Other Claude sessions share the checkouts, build trees and chips**, across boxes too (`/data` is NFS).
  Before a checkout or build in a shared tree, or a device run, check `ListAgents` and any running queue's
  lock; go through that session's lock instead of acting directly.
- **Ask Kyle before running anything on a machine other than the session's own** (`ssh <host> ...`: builds,
  tests, chip runs), and say what will run there. He wants a heads-up and to approve it; a QB2 re-test once
  ran over ssh from a Galaxy session without one.
- **TSAN binaries die in docker on these hosts** (kernel 6.8 ASLR: "incompatible memory layout but was unable to disable ASLR"). The default seccomp profile blocks `personality()`, so `setarch -R` fails too. Run only the TSAN step with `--security-opt seccomp=unconfined` plus `setarch $(uname -m) -R`; the container still runs as your user.
- **Never run a device job in the Bash tool foreground.** The 2-minute cap SIGKILLs it mid-transfer, and on a
  galaxy that needs a `tt-smi -glx_reset` before the next run works. `setsid nohup ... &`, then poll the log.
  `$!` after `setsid nohup X &` is setsid's own PID when it forks, and it exits at once: an `alloc_guard.sh $!`
  then reports the queue finished and guards nothing. Take the PID from the driver's cmdline in `/proc`.

## Git push & CI dispatch (shared TT boxes)
- **Two different push blockers; the rejection text tells them apart.** `Permission denied
  (publickey)`, or a hang non-interactively, means this shell's `SSH_AUTH_SOCK` points at an agent
  that died on reconnect. In an interactive shell, `fixagent` (from bashrc) re-points at a live one;
  it probes each candidate with `ssh-add -l`, since a live agent holding no keys fails identically.
  `remote rejected ... 'workflows' scope may be required` is NOT that: the `gh` HTTPS token carries
  `admin:public_key, gist, read:org, repo` but no `workflow`, so a push whose pushed range changes
  `.github/workflows/*` is refused — e.g. moving a branch onto an older base. The message may say
  "timeout"; retrying does nothing. **Push over SSH**, which OAuth scopes don't gate.
- **For tenstorrent/tt-metal over SSH, only the forwarded `macbook` key is SAML-SSO authorized.**
  The on-disk `~/.ssh/id_ed25519` authenticates (`ssh -T` says hi) but org pushes fail with a SAML
  error. With the agent found (below), also set
  `GIT_SSH_COMMAND="ssh -o IdentitiesOnly=no -o IdentityFile=/dev/null"` so the on-disk key isn't
  offered first. No forwarded agent at all: personal repos still push over HTTPS
  (`git -c credential.helper= -c credential.helper='!gh auth git-credential' push https://github.com/kmabeeTT/<repo>.git main:main`).
- **`source ~/.bashrc` in Claude Code's Bash tool gives `gh` its token, but not an agent.**
  `~/.gh-token.env` is sourced at line 7, above the non-interactive `return`, so `gh` works when
  it's sourced in the same Bash call. `fixagent` and the startup agent probe are below the return,
  so they never run. Get an agent with `bash -ic 'fixagent; echo $SSH_AUTH_SOCK'` and export the
  socket it prints, or run the loop directly:
  `for s in $(command ls -t /tmp/ssh-*/agent.* 2>/dev/null); do [ -S "$s" ] && SSH_AUTH_SOCK=$s ssh-add -l >/dev/null 2>&1 && export SSH_AUTH_SOCK=$s && break; done`
- **Don't inherit "push is blocked" from a handoff — test it.** One `ssh-add -l` settles it.
  A stale blocker in a doc cost a whole session's worth of "can't push" here.
- **After a rebase, a non-fast-forward rejection is expected, not a warning.** The remote holds
  the pre-rebase lineage. Confirm nothing is lost by comparing **trees** (file lists + blob
  shas), not `git cherry` — patch-ids drift across a rebase and it reports false positives.
  Then `git push --force-with-lease=<branch>:$(git rev-parse FETCH_HEAD)`, never bare `--force`,
  and tag the overwritten remote tip first so it stays recoverable past reflog expiry.
- **Verify the push landed before dispatching CI against it** — `git ls-remote` sha == local sha.
  A rejected push plus a fired `gh workflow run` silently tests stale remote content.
- **Stacked PR whose lower PR just merged: retarget to `main` BEFORE pushing the rebased head.** Pushing a head
  rebased onto new main while the PR still targets the old stack branch makes the diff, for a few seconds, every
  main commit since that branch: CODEOWNERS auto-requested 78 reviewers on #61265 (2026-11-06), and removing the
  requests can't unsend the notifications. The `pull_request` static checks (`check-doc`, `check-spdx-licenses`,
  `check-metal-kernel-count`) also only start on a push to a main-based PR, and a retarget is not a push, so the
  PR then can't be queued. Order: `gh pr edit N --base main`, check it took, then push.
- **A branch that conflicts with its base makes GitHub skip every `pull_request` workflow.** It
  cannot build `refs/pull/N/merge`, so PR Gate / Sanity / pre-commit never run, while
  `pull_request_target` ones still do. It presents as "CI mysteriously never ran", never as a
  conflict warning. Check `gh pr view N --json mergeable` FIRST — a rebase fixes it; close/reopen,
  force-push and recreating the PR all do nothing.
- Squash-merge here uses the **PR title and body**, not the branch commits (`squash_merge_commit_
  title: PR_TITLE`), and GitHub appends the **PR** number to the subject. So `Fixes #N` belongs in
  the PR description, and an issue number in the PR title would collide with the appended one.
- **No issue numbers in commit messages,** above all on branches still being iterated: every pushed commit
  that names `#N` adds a cross-reference to that issue, and rebases repeat it. PR descriptions can and should
  reference issues.
- **`gh` auth comes from `~/.gh-token.env` (a dotfiles symlink, per box).** "Not logged into any hosts" on a new
  box means the dotfiles aren't in place, not a bad token. Never print the token.

## PR descriptions (what reviewers praised)
Model: tenstorrent/tt-metal#57931 ("perfect description"). The body becomes the squash commit, so:
- **Summary = the causal chain, then the fix in one sentence.** What the code asked for, what it
  actually got, where (name the files / entry points affected), the silent mechanism
  (`get_usable_topology` downgrades Ring to Linear), and the one observation that proves it
  (Ring and linear give identical timings). Then "This PR does X." No history, no "we tried".
- **One context line states the measurement once:** model, hardware + mesh, metric (traced device
  time), base sha, "same build before and after", and what each column means in bullet order.
- **Results as bullets, one per config, same column order**: `- chunk 2048: 92.6 -> 86.6 ms (-6%),
  5.93 -> 5.63 s, 21.4 -> 20.6 s`. % only on the headline column. No markdown tables (they read badly in
  `git log`; fine in PR comments, issues and Slack).
- **One sentence explaining the trend** (why the gain grows with chunk size), so the numbers read
  as a consequence rather than noise.
- **Accuracy stated with its metric names and gate** (overall / RRMSE / min per-head, gate 0.91).
- **Notes for reviewers answer the questions they would ask:** why a metric moved (and that it
  moved both ways), the obvious alternative and its measured result (async: ~1 ms slower), what was
  NOT measured and why (2D torus hangs without a descriptor), interactions with other PRs, and CI
  links pinned to a sha with what each leg exercises.
- Concrete over adjectives: every claim carries a number, a file, or a flag name. Short sentences.

## Disk on shared boxes
- **`/` is shared with hundreds of users and fills without warning.** `du` under-reports badly:
  other users' home dirs are unreadable, so `du` totalling 45G against `df` 613G is expected, not a
  mystery. Only your own share is actionable.
- **The HuggingFace cache is the usual culprit** — any `from_pretrained("<repo id>")` (rather than a
  local path) downloads a second copy of a model already on `/data`; 223G in one case. The fix is
  `~/.cache/huggingface -> /data/kmabee/hf_cache`, but `/home` is per box, so it exists only where
  it was made (not on bh-glx-120-b08u02, checked 2026-10-17): `ls -ld ~/.cache/huggingface` first. Leave `~/.cache/tt-metal-cache`
  local: it is thousands of small JIT files and NFS would slow every build.
- **`/data` has a per-user quota that `df` doesn't show** (`quota` isn't installed). When it's full, writes fail
  at close with "Disk quota exceeded", which surfaces as a truncated `.git/index` or a failed build. Test with
  `dd if=/dev/zero of=/data/kmabee/.wtest bs=1M count=50`. Tracy captures (~15 GB raw each) are what filled it.
- **Check `df -h /` before a `docker pull` on a Galaxy host.** Images land on the shared `/`, and on
  bh-glx-120-b08u08 it had under 10 GB free (2026-11-07): one 10 GB tt-metalium pull took it to 0 and broke the Bash
  tool. `docker rmi` the image you just pulled gives it back. Where an image is missing and `/` is tight, run on
  a host that already has it, or ask Kyle.
- When `/` is full the Claude Code Bash tool cannot run **at all** (it needs `/tmp` for scratch), so
  free space from a normal shell first.

## Claude Code quirks here
- **`pgrep -f` / `pkill -f` match the tool's own wrapper shell**, whose command line contains the
  entire script text. A wait-loop grepping for its own target string sees itself and never exits;
  `pkill -f <pattern>` can kill the wrapper (exit 144). Act on a PID, not a pattern.
- **The first `git commit` in a fresh checkout can outlive the 2-minute cap** while pre-commit installs its hook
  envs. The kill lands after pre-commit stashed unstaged changes and before it restores them, so that work then
  exists only in `~/.cache/pre-commit/patch*` (`git apply` it back). Give that commit a long timeout.
- **Personal repos live on NFS** at `/data/kmabee/helpers/<repo>` (claude-skills, debug-docs, prefill-docs,
  scripts, claude-code-history), with `~/<repo>` symlinks; one working copy for every box. `dotfiles` stays a
  local clone in `~`. NFS is not a backup: push.
- `--collect-only` still loads the deepseek conftest and **opens all 32 chips**, so it is not safe
  to run alongside a live job. Read the test source instead.
