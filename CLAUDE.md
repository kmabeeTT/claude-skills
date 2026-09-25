# Working notes (kmabee)

Operational lessons to avoid re-paying time already spent. Keep this lean.

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
  - **Since 2026-09-15, empty output does NOT mean the device is free** — only that *you*
    aren't holding it. A `dev-sec` hardening baseline mounts `/proc` with `hidepid=2`, so
    `ps`/`fuser`/`pkill` see only your own PIDs and another user's `EngineCore` on that chip
    is invisible. If a device won't acquire but `fuser` shows nothing, suspect an unseen
    other-user holder instead of debugging tt-xla/tt-metal. Needs root to fix; the ask is
    `hidepid=2,gid=slurmusers` (the role's supported escape hatch) or `hidepid=1`. Config
    management reverts a manual remount.
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

## Git push & CI dispatch (shared TT boxes)
- **Two different push blockers; the rejection text tells them apart.** `Permission denied
  (publickey)`, or a hang non-interactively, means this shell's `SSH_AUTH_SOCK` points at an agent
  that died on reconnect — `source ~/.bashrc` re-points at a live one (that block probes each
  candidate with `ssh-add -l`, since a live agent holding no keys fails identically).
  `remote rejected ... 'workflows' scope may be required` is NOT that: the `gh` HTTPS token carries
  `gist, read:org, repo` but no `workflow`, so any push whose branch changes `.github/workflows/*`
  relative to the default branch is refused — e.g. moving a branch onto an older base. The message
  says "timeout" and retrying does nothing; **push over SSH**, which OAuth scopes don't gate.
- **`source ~/.bashrc` is a NO-OP in Claude Code's Bash tool** — so the agent fix above needs
  running by hand here. bashrc returns at line 8 (`case $- in *i*) ;; *) return;;`) because the
  shell is non-interactive, and never reaches the probe at line 218; you then wrongly conclude
  there is no agent. Run the loop directly:
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
- **A branch that conflicts with its base makes GitHub skip every `pull_request` workflow.** It
  cannot build `refs/pull/N/merge`, so PR Gate / Sanity / pre-commit never run, while
  `pull_request_target` ones still do. It presents as "CI mysteriously never ran", never as a
  conflict warning. Check `gh pr view N --json mergeable` FIRST — a rebase fixes it; close/reopen,
  force-push and recreating the PR all do nothing.
- Squash-merge here uses the **PR title and body**, not the branch commits (`squash_merge_commit_
  title: PR_TITLE`), and GitHub appends the **PR** number to the subject. So `Fixes #N` belongs in
  the PR description, and an issue number in the PR title would collide with the appended one.

## PR descriptions (what reviewers praised)
Model: tenstorrent/tt-metal#57931 ("perfect description"). The body becomes the squash commit, so:
- **Summary = the causal chain, then the fix in one sentence.** What the code asked for, what it
  actually got, where (name the files / entry points affected), the silent mechanism
  (`get_usable_topology` downgrades Ring to Linear), and the one observation that proves it
  (Ring and linear give identical timings). Then "This PR does X." No history, no "we tried".
- **One context line states the measurement once:** model, hardware + mesh, metric (traced device
  time), base sha, "same build before and after", and what each column means in bullet order.
- **Results as bullets, one per config, same column order**: `- chunk 2048: 92.6 -> 86.6 ms (-6%),
  5.93 -> 5.63 s, 21.4 -> 20.6 s`. % only on the headline column. No markdown tables.
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
  local path) downloads a second copy of a model already on `/data`; 223G in one case. Fixed
  permanently with `~/.cache/huggingface -> /data/kmabee/hf_cache`. Leave `~/.cache/tt-metal-cache`
  local: it is thousands of small JIT files and NFS would slow every build.
- When `/` is full the Claude Code Bash tool cannot run **at all** (it needs `/tmp` for scratch), so
  free space from a normal shell first.

## Claude Code quirks here
- **`pgrep -f` / `pkill -f` match the tool's own wrapper shell**, whose command line contains the
  entire script text. A wait-loop grepping for its own target string sees itself and never exits;
  `pkill -f <pattern>` can kill the wrapper (exit 144). Act on a PID, not a pattern.
- `--collect-only` still loads the deepseek conftest and **opens all 32 chips**, so it is not safe
  to run alongside a live job. Read the test source instead.
