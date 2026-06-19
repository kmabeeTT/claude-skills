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
  - Who holds it: `fuser -v /dev/tenstorrent/*` or `for d in /dev/tenstorrent/*; do echo "$d"; fuser "$d"; done` (empty = free). Confirm which device a PID holds with `ls -l /proc/<pid>/fd | grep tenstorrent`.
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
