---
name: agentx-simulator-pr60867
description: "PR #60867 (merged 2026-10-21): host-only AgentX prefill simulator for Gemma4 on BH Galaxy 8x4; cost model = measured per-layer data + silicon calibration; validated within ~2% on held-out replays"
metadata:
  node_type: memory
  type: project
  originSessionId: d769d672-592d-4fc4-9390-3b2e5fe0401b
  modified: 2026-10-27T15:42:45.872Z
---

#60867 (Kyle's, merged 2026-10-21, closes #60862, part of #60408) adds `models/demos/gemma4_d_p/agentx_sim/`: replays the AgentX coding-agent traces (HF `semianalysisai/cc-traces-weka-062126-256k`, 393 sessions, 68,266 requests) against a step-cost model, host only, ~3 s per config over the whole corpus.

- Cost model (`cost_model.py` + `model_data_revc.json`): step = dense(rows per device) + sum over requests of attention at its own prefix depth, x10 global + x50 sliding layers. Dense is piecewise linear in M; global attention is a + b·prefix per chunk size; sliding is flat. Base data: tracy captures + host-timed layer replays on bh-glx-110-d07u08 (RevC 130 W, 10-08), chunks 1k-16k.
- Calibration: scale factors + host ms per step (+0.82 ms gap for batched) fitted to silicon replays of AgentX slices (serial on d06u02, batched 2k lanes on c05u08, 12,837 steps); 8k/4k scales refit 10-18 for LoFi projections.
- Simulator (`agentx_sim.py`): closed-loop session DAGs (sub-agents, think time capped by --max-think-s), prefix cache (inf or LRU, 64-token blocks, resume rounded down to chunk), configs `UNITxBUDGET:fcfs|pack`. `agentx_slice.py` cuts windows for silicon replay and compares. `plot_ttft_cdf.py` draws TTFT CDFs (reviewer loved these).
- Accuracy: batched held-out busy within 0.2%, TTFT p50/p90/p99 within 1.7%; serial is in-sample; box-to-box ~1.5% speed moves saturated tails ±10%.
- Findings in #60408 comment 6297198831: 2k x4 lanes beat 8k (p50 0.40 vs 5.3 s at 64 sessions); shortest-first cuts p90 to 0.65 s but starves >16K requests (p99 401 s); cache capacity (2.2M tokens) matters more than any scheduling choice.
- Not modelled: loading a cached prefix onto device, clock throttling beyond calibration, first decode token.

- Silicon coverage: 10 slices on c05u08 (10-14/15), ~108 min of trace, ~23.5k request-replays, ~2.6 h device replay (~3.5 h with compile); plus 3 x 10-min batched windows on d08u02. Full corpus would take 8.3-9.6 h per design at heavy load, 64 sessions, ~31-35 h light (replay is real time); the 32-run sweep would be ~650 h on silicon. Replay JSONs: /data/kmabee/agentx_tail_1015/mirror/{combined,depth}; sweeps: /data/kmabee/datasets/agentx/sweeps/.

Teaching artifact (2026-10-27): https://claude.ai/artifact/1QDXQaQaKGSVNQeJiaQh9f. Related: [[batching-agentx-prs-handoff-1014]].
