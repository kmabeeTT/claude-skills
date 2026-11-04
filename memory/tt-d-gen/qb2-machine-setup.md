---
name: qb2-machine-setup
description: "Kyle's QB2 host (qb2-120-p02t05) quirks for building/running tt-d-gen and a 4-chip health-check job"
metadata:
  node_type: memory
  type: project
  originSessionId: 9df419b8-8805-43ac-af03-137441bdb53c
  modified: 2026-11-02T20:43:48.736Z
---

Host qb2-120-p02t05: 4x Blackhole p300c (2x P300 cards, tt-metal SKU `bh_quietbox_2`, MESH_DEVICE=P300x2), 1G hugepages mounted, Slurm alloc that is lost if idle (user wants a periodic job that uses all 4 chips).

- No passwordless sudo; libzmq3-dev is NOT installed → build tt-d-gen with `--no-kvm-client` (drops KvmClient only).
- Local weights: /mnt/models/meta-llama/Llama-3.1-8B-Instruct is HF revision 0e9e39f2…, the exact pin of tt-metal `models/demos/llama31_8b_qb2` → set LLAMA_MODEL_PATH to it.
- Scripts in ~/scripts (git repo kmabeeTT/scripts, commit style "file - desc"): qb2_health.sh (`--quick` ≈3 min, `--reset`; fails on skips), qb2_chat.sh streaming chat (`--prefill-bucket 1024` default cuts later-turn TTFT 5-13 s → ~50 ms). Never run device jobs while the user may be chatting — check for running qb2_chat/pytest first. Wraps tt-metal `models/demos/llama31_8b_qb2/tests` (pytest, no vLLM needed); full CI flow in tests/pipeline_reorg/agentic_research_model_tests.yaml (~10 min, needs vLLM plugin).
- There is no full on-device model path in tt-d-gen yet; on QB2 the engine runs against the `pipeline_loopback` kernel (token+1) via `--blaze`.

- Pushing: GH_TOKEN (dotfiles/.gh-token.env, same on every box) lacks `workflow` scope, so HTTPS pushes of commits touching .github/workflows are refused. Push over SSH with Kyle's forwarded agent instead; Claude's shell may inherit a stale SSH_AUTH_SOCK, so find the live one with `for s in /tmp/ssh-*/agent.*; do SSH_AUTH_SOCK=$s ssh-add -l; done` (the dotfiles `fixagent` logic) and export it before `git push origin`.

**Why:** discovered during the 2026-11-02 setup session; saves re-deriving.
**How to apply:** use these defaults when building/running on this host; see [[structured-outputs-work]].
